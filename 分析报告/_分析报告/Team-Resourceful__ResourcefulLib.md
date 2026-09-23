# Team-Resourceful / ResourcefulLib 源码分析报告

> 分析对象为本地 checkout 的 `26.x` 分支（HEAD: `6729699 Released v5.0.4`）。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Resourceful Lib / `resourcefullib`（`common/src/main/java/com/teamresourceful/resourcefullib/ResourcefulLib.java:6`） |
| 作者 | ThatGravyBoat, Epic_Oreo（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`） |
| 目标 MC / 加载器 | `gradle/libs.versions.toml`: `minecraft = "26.2"`、`neoforge = "26.2.0.0-beta"`、`fabric-api = "0.152.1+26.2"`；`version.properties`: `currentMCVersion=1.23`（大写 1.19.1 起始）、`version=5.0.4`。**注意：这是 MC 26.2 分支，不是 1.21.1/1.20.1；1.21.1 需另取对应分支（未确认本地是否存在）** |
| 版本号 | 5.0.4（`version.properties`） |
| Gradle 插件 | 自研全家桶：`com.teamresourceful.resourcefulsettings`、`com.teamresourceful.resourcefulgradle`、`com.teamresourceful.plugins.minecraft`（`build.gradle.kts`、`settings.gradle.kts`）。子项目 `common/fabric/neoforge` **没有各自的 build.gradle.kts**，全靠平台插件按 `gradle.properties` 的 `enabledPlatforms=fabric,neoforge` 生成 |
| 许可证 | MIT |
| 编译依赖 | `com.teamresourceful:yabn`（YAML/NBT 抽象）、`com.teamresourceful:bytecodecs`（自研 ByteCodec 序列化框架）；两者通过 `api()` 暴露给下游，并在 fabric 用 `include`、neoforge 用 `jarJar` 内嵌（`build.gradle.kts` 子项目 dependencies 块）。编译期还有 `resourceful-service-plugin`（javac 注解处理器 + `-Xplugin:ServicePlugin`） |

## 2. 源码规模与包结构

- `.java` 文件 **214** 个，总行 **9790**：common 158 / fabric 32 / neoforge 24。
- 主包 `com.teamresourceful.resourcefullib` 下第二层为 `common` 与 `client`。

主要包（第三层，common 侧）：

| 包 | 说明 |
|---|---|
| `common/network`（含 `base`、`defaults`、`internal`） | 跨平台封包注册/收发抽象，7 个类 |
| `common/registry`（含 `builtin`、`builtin/base`） | 跨平台注册表抽象，13 个类 |
| `common/codecs`（含 `yabn`、`maps`、`predicates`、`recipes`、`tags`、`bounds`、`deferred`） | Codec 工具箱，约 20 个类 |
| `common/nbt`（含 `validators/{list,numeric,object,string}`） | NBT 校验器体系，24 个类 |
| `common/fluid`（`data`、`registry`）+ `client/fluid` | 流体数据驱动属性 + 客户端渲染注册 |
| `common/menu`、`common/item/tabs`、`common/inventory` | 菜单内容序列化、创造模式标签页、`IntContainerData` |
| `common/utils`（`files`、`modinfo`） | `GlobalStorage`、`CodecSavedData`、`GenericMemoryPack`、`Scheduling` |
| `client/highlights`、`client/screens`、`client/sysinfo`、`client/closables` | 方块描边高亮、屏幕状态栈、系统信息上报、PoseStack/Scissor 的 AutoCloseable 封装 |

最大文件（行数）：`common/color/Color.java` 291、`common/codecs/yabn/YabnOps.java` 256、`common/fluid/data/FluidProperties.java` 213、`common/collections/WeightedCollection.java` 188、`common/color/ConstantColors.java` 163、`common/fluid/ResourcefulFlowingFluid.java` 152、`client/fluid/data/ClientFluidProperties.java` 151、`client/highlights/HighlightHandler.java` 142、`common/codecs/CodecExtras.java` 135、`neoforge/.../ResourcefulLibNeoForgeClient.java` 133。

## 3. 入口与注册

公共入口极薄，`ResourcefulLib.java` 全文只有 9 行，只做 `GlobalStorage.init()`。真正的初始化分平台：

NeoForge（`neoforge/src/main/java/com/teamresourceful/resourcefullib/neoforge/ResourcefulLibNeoForge.java:14`）：

```java
@Mod(ResourcefulLib.MOD_ID)
public class ResourcefulLibNeoForge {
    public ResourcefulLibNeoForge(IEventBus bus) {
        ResourcefulLib.init();
        if (!FMLLoader.getCurrent().getDist().isClient()) {
            ApiProxy.setInstance(NeoForgeServerApiProxy.INSTANCE);
        }
        bus.addListener(ResourcefulLibNeoForge::onNetworkSetup);   // RegisterPayloadHandlersEvent
    }
}
```

客户端另有 `@Mod(value = MOD_ID, dist = Dist.CLIENT)` 的 `ResourcefulLibNeoForgeClient`，在构造里挂 5 个事件监听（流体客户端扩展、流体模型、客户端 reload listener、描边高亮、命令）。

Fabric 侧是 3 个入口：`ResourcefulLibFabricClient`（`ClientModInitializer`）、`ResourcefulLibFabricServer`（`DedicatedServerModInitializer`）、`FabricClientProxy/FabricServerProxy`（注意包里没有 `fabric.mod.json`，由构建插件生成）。

**注册框架是自研的 `ResourcefulRegistry`**，而非直接用 `DeferredRegister`：`ResourcefulRegistries.create(registry, id)` → `SERVICE.make(...)`，`SERVICE` 来自 `@PlatformService` 接口 + 编译期插件注入（见第 7 条）。NeoForge 实现 `NeoForgeResourcefulRegistry` 内部包 `DeferredRegister`，Fabric 实现 `FabricResourcefulRegistry` 直接 `Registry.register`，两者都返回统一的 `RegistryEntry<T>`/`HolderRegistryEntry<T>`。

## 4. 核心系统

**(1) 跨平台网络抽象**（`common/network/`）。`PacketType<T>` 只声明 `id()/encode()/decode()`，并由默认方法产出 `CustomPacketPayload.Type` 与 `StreamCodec`；`ClientboundPacketType` 多一个 `Runnable handle(T)`，`ServerboundPacketType` 多 `Consumer<Player> handle(T)`。`Network.java:45-101` 提供 `sendToPlayer / sendToPlayers / sendToAllPlayers / sendToPlayersInLevel / sendToAllLoaded(chunkMap) / sendToPlayersInRange` 六个分发粒度。`NeoForgeNetworking.java:24` 用静态 `LISTENERS` 列表解决"Network 实例可能在 `RegisterPayloadHandlersEvent` 之后才创建"的顺序问题。

**(2) 三套包类型（策略模式）**。`defaults/` 下并列 `DatalessPacketType`（无 payload）、`CodecPacketType`（带 `StreamCodec`，且重载接受自研 `ByteCodec`）、`AbstractPacketType`。`CodecPacketType` 还内嵌 `Client/Server` 抽象类并提供静态 `create(id, codec, handler)` 工厂，让下游用一行 lambda 定义完整包类型。

**(3) 流体数据驱动体系**（`common/fluid/data/` + `client/fluid/`）。`FluidProperties.java`（213 行）是纯数据描述（颜色、声音、物理），`InternalFluidData`/`ImmutableFluidProperties` 分离可变/不可变；`ResourcefulFluidRegistry` 接口由 `FabricResourcefulFluidRegistry`/`NeoForgeResourcefulFluidRegistry` 实现（后者内部 `DeferredRegister.create(NeoForgeRegistries.FLUID_TYPES, id)` 并维护 `ConcurrentHashMap GLOBAL_REGISTRY`）。整个流体只需在注册期填一份 properties，平台专属的 `FluidType` 由库内 mixin 懒加载（见第 6 节）。

**(4) 方块描边高亮**（`client/highlights/HighlightHandler.java:35`）。继承 `SimpleJsonResourceReloadListener`，从 `resourcefullib/highlights` 目录读 JSON，按"是否含 `lines` 字段"把资源分成 自定义盒模型 与 方块状态映射 两类；用 `Reference2ReferenceOpenHashMap` 以 `BlockState` 为 key 缓存 `float[]`，并有静态 `HIGHLIGHT_CODEC = Identifier.CODEC.xmap(HighlightHandler::getOrThrow, Highlight::id)` 让其他 mod 能在自己的 data 里按 id 引用。

**(5) Codec / YABN 工具箱**（`common/codecs/`）。`YabnOps.java`（256 行）把自研 YABN（YAML-As-Binary-NBT）树接到 Mojang 的 `DynamicOps`，使同一份 `Codec<T>` 能同时从 JSON、NBT、YAML 解析；`CodecExtras`、`EnumCodec`、`PrimitiveCodecHelper`、`UniformedNumberCodecs`（bounds）、`DispatchMapCodec`、`DeferredCodec`、`HolderSetCodec`、`ItemStackCodec`、`LazyHolders` 覆盖了大量常见序列化场景。

**(6) 客户端屏幕状态栈**（`client/screens/`）。`ScreenHistory` + `ScreenStateManager` + `ScreenState`/`PageState` 管理"返回上一屏"的栈式导航，配套 `HistoryScreen`、`PriorityScreen`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：统一走原版 `CustomPacketPayload`（`internal/NetworkPacketPayload.java` 是唯一 payload 承载体，record 持 `T packet` + `Type`）。通道名为 `channel.withSuffix("/v" + protocolVersion)`，包 id 为 `channel + "/" + namespace + "/" + path`（`PacketType.java:31`）。`optional` 通道在发送前用 `player.connection.hasChannel(...)` 做能力探测（`NeoForgeNetworking.java:64`），`Network.sendToPlayer` 会因此静默跳过。Fabric 侧实现见 `fabric/.../common/network/`（未逐一读取，未确认细节）。
- **数据驱动**：`HighlightHandler`（方块描边，JSON，reload listener）；`FluidProperties`（流体属性，主要由代码注册而非资源文件）；`menu/MenuContentSerializer` + `CodecMenuContentSerializer`（菜单内容 codec 化）；`nbt/validators/` 24 个类构成声明式 NBT 结构校验器（list/numeric/string/object 四族）。
- **配置**：本库自身无配置文件；提供 `utils/files/GlobalStorage`（按 OS 给出 `LOCALAPPDATA`/`~/Library/...`/`XDG_*` 下的 cache 与 data 目录，首次运行写 `README.txt`）与 `CodecSavedData`（用 `Codec<T>` + `Identifier` 建 `SavedData` 工厂，支持 `alwaysDirty`）。
- **datagen**：极简，仅 `common/datagen/CodecRecipeBuilder.java` 一个类（未发现完整 DataGenerator provider 体系）。

## 6. Mixin

- Fabric：`fabric/src/main/resources/resourcefullib.mixins.json`，包 `com.teamresourceful.resourcefullib.mixins.fabric`，`compatibilityLevel: JAVA_17`，client 4 个 + mixins 4 个。
- NeoForge：`neoforge/src/main/resources/resourcefullib.mixins.json`，仅 1 个 `ResourcefulFlowingFluidMixin`（在 mods.toml 用 `[[mixins]] config=` 声明）。

代表性 hook：

- `mixins/fabric/EntityMixin.java:30` — `@Mixin(Entity.class)`，`@Inject(method="updateFluidInteraction", at=@At("HEAD"))` 写入 `@Unique FluidState rlibEyesFluid`，并让 Entity 实现 `EntityFluidEyesHook` 暴露 `rlib$getEyesFluid()`（原版只按 tag 判断"眼中有液体"，这里改成按具体 fluid 判断）。
- `mixins/fabric/ScreenEffectRendererMixin.java:26` — `@Inject(method="submit", at=@At(value="INVOKE", target="...LocalPlayer;isEyeInFluid(Lnet/minecraft/tags/TagKey;)Z", shift=BEFORE))`，配合 mixinextras 的 `@Local PoseStack` 取局部变量，调用 `ClientFluidProperties.renderOverlay(...)` 渲染自定义液体遮罩。
- `mixins/neoforge/ResourcefulFlowingFluidMixin.java:10` — `@Mixin(ResourcefulFlowingFluid.class)`，覆写 `getFluidType()` 并 `@Unique FluidType rlib$fluidType` 懒加载缓存，null 时抛 `IllegalStateException`。
- 其余：`DedicatedServerMixin`、`MinecraftServerMixin`、`LevelExtractorMixin`、`LevelRendererMixin`、`FogRendererMixin`、`BlockOutlineRenderStateMixin`（都在 fabric）。

## 7. 值得学的 5 条具体做法

1. **用编译期注解处理器代替反射做跨平台服务发现**：`@PlatformService` 接口里写 `static X create() { throw new NotImplementedException(); }`，javac 参数带 `-Xplugin:ServicePlugin --service-plugin-platform=neoforge --service-plugin-platform-class=...`（`build.gradle.kts` 子项目块），由 `resourceful-service-plugin` 在编译期把方法体替换为平台实现查找。位置：`common/registry/ResourcefulRegistriesService.java:15`、`common/network/NetworkService.java:15`、`common/lib/PlatformService.java`。适用：多平台库想避免 `ServiceLoader` 文件手写与运行期反射。
2. **平台检测不依赖加载器 API**：`common/lib/Platform.java:27` 用 `Class.forName("net.neoforged.fml.loading.FMLLoader", false, cl)` 判断平台，common 源码不需要编译期依赖任何加载器。
3. **发送前做通道能力探测**：`optional` 通道在 `Network.sendToPlayer` 里先 `canSendToPlayer` 再发（`common/network/Network.java:51`、`NeoForgeNetworking.java:64`），使"服务端有、客户端没装该功能的包"不会崩连接。
4. **分发粒度齐全的 Network 门面**：`Network.java:55-86` 一次性提供 player/players/allPlayers/inLevel/loadedChunk/inRange 六种发送目标，下游 mod 不用自己写 chunkMap 广播逻辑。
5. **静态 LISTENERS 化解事件时序**：`NeoForgeNetworking.java:24` 把每个 `Network` 实例的注册回调塞进静态列表，`setupNetwork` 一次性执行——库在 `RegisterPayloadHandlersEvent` 之后被下游调用也安全。适用：任何"平台事件只发一次但调用方可能在之后初始化"的库。

## 8. 公开 API / 外部 mod 接入方式

- **网络**：下游不继承任何类，实现 `Packet<T>`（`type()` 返回自己的 `PacketType`），用 `CodecPacketType.Client.create(id, codec, msg -> () -> ...)` / `.Server.create(id, codec, msg -> player -> ...)` 一行注册；构造 `new Network(Identifier.fromNamespaceAndPath(MODID, "main"), 1, /*optional*/ true)` 后 `network.register(type)`。
- **注册**：`ResourcefulRegistries.create(BuiltInRegistries.ITEM, "modid")` 或 `createForItems/createForBlocks(id)` / `ResourcefulRegistries.create(ResourcefulRegistryType.FLUID, id)`；返回的 `RegistryEntry` 实现 `Supplier`，可直接当延迟取值用。
- **流体**：`common/fluid/registry/ResourcefulFluidRegistry`（接口）+ `common/fluid/data/FluidProperties`，客户端配 `client/fluid/registry/ResourcefulClientFluidRegistry`。
- **序列化**：`common/codecs/CodecExtras`、`common/bytecodecs/ExtraByteCodecs`（`ByteCodec`↔`StreamCodec` 桥 `StreamCodecByteCodec`）对外开放。
- **数据文件**：`resourcefullib/highlights/*.json`；`GlobalStorage.getCacheDirectory/getDataDirectory(modid)` 给下游 mod 存缓存。
- **客户端工具**：`client/highlights/Highlightable`（方块实现该接口即可获得描边）、`client/closables/CloseablePose`、`CloseableScissor`、`client/sysinfo/SystemInfo.buildForDiscord()`、`common/inventory/IntContainerData`、`common/menu/ContentMenuProvider`。
- 未发现 `@ApiStatus.Internal` 之外的稳定 API 白名单机制；`common/lib/Constants`（LOGGER/GSON/PRETTY_GSON）作为公共常量入口。
