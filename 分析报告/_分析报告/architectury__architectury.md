# Architectury API（architectury/architectury）源码分析报告

仓库根目录：`源码库\_参考仓库\_bulk\architectury__architectury`
（本检出为 1.19.2 分支，commit `cd74016`；报告内路径均为相对该根目录）

## 1. 基本信息

- Mod 名：Architectury API；mod_id：`architectury`；作者：`shedaniel`
- 目标 MC 版本：1.19.2（`gradle.properties`：`minecraft_version=1.19.2`、`supported_version=1.19.2`、`base_version=6.6`）；加载器：`platforms=fabric,forge`（**本检出无 NeoForge 模块**，NeoForge 支持在其它分支）
- Gradle 插件：`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.0-SNAPSHOT`（`build.gradle:10-11`）、`com.github.johnrengelman.shadow 7.1.2`、`org.cadixdev.licenser`、`me.shedaniel.unified-publishing`；Java 17（`options.release = 16`，`build.gradle:47-50`）
- 许可证：LGPL-3（`LICENSE.md`、`forge/src/main/resources/META-INF/mods.toml`）
- 编译依赖（它依赖谁）：`common` 仅 `net.fabricmc:fabric-loader:0.14.19`（注释明确"只为了用 `@Environment` 注解，不要用 fabric loader 其它类"，`common/build.gradle:5-8`）；`fabric`：fabric-loader + `fabric-api:0.66.0+1.19.2` + `modmenu:3.1.0`（compileOnly）；`forge`：`net.minecraftforge:forge:1.19.2-43.2.0`
- 谁是它的 API：它本身就是 API/前置库（README："An intermediary api aimed to ease developing multiplatform mods"），下游 mod 通过 Architectury Plugin + Architectury Loom 接入
- 注：`fabric/src/main/resources/fabric.mod.json`、`common/src/main/resources/architectury.common.json` 只存在于 git HEAD，工作树副本缺失，本报告中其内容取自 `git show HEAD:<path>`

## 2. 源码规模与包结构

实测（排除 `.git`）：**332 个 `.java`、24981 行**
按模块（文件数 / 行数）：`common` 144 / 11182；`fabric` 106 / 6504；`forge` 59 / 5660；`testmod-common` 22 / 1602；`testmod-forge` 1 / 33；`testmod-fabric` 0（只有 build.gradle）

主要包（到第 3 层，按文件数）：
- common：`event/events/{common,client}` 25；`hooks/*` 约 30（`hooks/level` 10、`hooks/item` 5、`hooks/fluid` 3…）；`extensions/injected` 9；`registry/registries` 8；`registry/client` 8；`mixin/inject` 8；`utils/value` 7；`networking/{simple,transformers}` 11；`registry/level/*` 5；`core/{item,fluid,block}` 流体/桶物品基类
- fabric（顶层目录）：`mixin` 54、`registry` 18、`hooks` 17、`event` 3、`core` 3、`networking` 2、`init` 2
- forge（顶层目录）：`registry` 18、`hooks` 14、`mixin` 8、`event` 6、`core` 5、`platform` 2、`networking` 2

最大的文件：`forge/.../registry/registries/forge/RegistriesImpl.java` 786 行；`common/.../core/fluid/ArchitecturyFluidAttributes.java` 638；`forge/.../registry/level/biome/forge/BiomeModificationsImpl.java` 556；`forge/.../event/forge/EventHandlerImplCommon.java` 446；`common/.../hooks/level/biome/BiomeHooks.java` 396；`common/.../core/fluid/SimpleArchitecturyFluidAttributes.java` 380；`forge/.../event/forge/EventHandlerImplClient.java` 356；`fabric/.../registry/level/biome/fabric/BiomeModificationsImpl.java` 324；`fabric/.../registry/registries/fabric/RegistriesImpl.java` 291

## 3. 入口与注册

三个入口（同一套 common 代码）：
- Fabric（`git show HEAD:fabric/src/main/resources/fabric.mod.json`）：entrypoints `main = dev.architectury.utils.fabric.GameInstanceImpl::init`、`server = dev.architectury.init.fabric.ArchitecturyServer::init`、`client = dev.architectury.init.fabric.ArchitecturyClient::init`、`modmenu = dev.architectury.compat.fabric.ModMenuCompatibility`；mixins 挂 `architectury-common.mixins.json` + `architectury.mixins.json`
- Forge：`forge/src/main/java/dev/architectury/forge/ArchitecturyForge.java:28` 的 `@Mod("architectury")`，构造函数只做三件事（33-37 行）：

```java
public ArchitecturyForge() {
    EventBuses.registerModEventBus(ArchitecturyForge.MOD_ID, FMLJavaModLoadingContext.get().getModEventBus());
    EventHandler.init();
    BiomeModificationsImpl.init();
}
```

- Fabric 侧 `init/fabric/ArchitecturyClient.java` 只调 `LifecycleEvent.SETUP.invoker().run()` 与 `ClientLifecycleEvent.CLIENT_SETUP`，即"用 common 事件接口代替 loader 入口"。

注册框架是自研的 `Registries/Registrar/RegistrySupplier/DeferredRegister`（`common/src/main/java/dev/architectury/registry/registries/`），**不用** Forge `DeferredRegister`，也不用 Registrate。用法（示例见 `testmod-common/src/main/java/dev/architectury/test/registry/TestRegistries.java`）：`Registries.get(modId).get(Registry.ITEM_REGISTRY)` 或 `DeferredRegister.create(modId, key).register("id", Supplier)` 最后 `register()`。注册时机由平台决定：`Registries.java:66-72` 的 javadoc 写明"Forge 在 `RegistryEvent.Register` 之后回调，Fabric 立即回调"。

## 4. 核心系统

### 4.1 @ExpectPlatform 机制（本仓库最核心）
- 职责：让 common 里的静态方法在编译期"空壳"，运行时被替换为当前加载器的实现。
- 关键点 1：注解本体**不在本仓库**，位于 `dev.architectury.injectables.annotations.ExpectPlatform`（由 Architectury Plugin gradle 插件的 "Injectables" 生成/处理）。本仓库共 93 处 `@ExpectPlatform`，分布在 common 的 38 个文件中。
- 关键点 2：约定 = common 类 `dev.architectury.platform.Platform` 中 `@ExpectPlatform public static Path getGameFolder() { throw new AssertionError(); }`（`common/src/main/java/dev/architectury/platform/Platform.java:69-72`），平台实现放"同包 + 平台子包 + `<SimpleName>Impl`"：`fabric/src/main/java/dev/architectury/platform/fabric/PlatformImpl.java:39`、`forge/src/main/java/dev/architectury/platform/forge/PlatformImpl.java:44`（同类还有 `RegistriesImpl`、`ItemStackHooksImpl`、`NetworkManagerImpl`、`PlayerHooksImpl`…共 79 个 `*Impl.java`）。
- 关键点 3：运行期目标平台用注入的 `dev.architectury.injectables.targets.ArchitecturyTarget.getCurrentTarget()` 判断并缓存（`Platform.java:37-58`，`isFabric()/isForge()`）。
- 关键点 4：仅单侧存在的 API 用独立类隔离，如 `forge/src/main/java/dev/architectury/platform/forge/EventBuses.java`（`registerModEventBus` / `onRegistered` / `getModEventBus`，让 mod 以字符串 modId 拿到自己的 `IEventBus` 而不在 common 里 import Forge 类）。common 侧兜底异常类型 `common/src/main/java/dev/architectury/utils/PlatformExpectedError.java`。

### 4.2 事件系统（跨加载器事件总线）
- 职责：common 定义事件接口 + 字段，各平台把原生事件桥接进来。
- 关键点 1：`Event<T>`（`Event.java`）只有 `invoker/register/unregister/isRegistered/clearListeners`；实例由 `EventFactory` 用 JDK 动态代理 + `MethodHandles.lookup().unreflect` 生成（`common/src/main/java/dev/architectury/event/EventFactory.java:47-53`），四种原型：`createLoop`（循环调用全部监听器）、`createEventResult`（遇 `interruptsFurtherEvaluation()` 提前返回）、`createCompoundEventResult`、`createConsumerLoop`；实现类 `EventImpl` 在 `EventFactory.java:197`。
- 关键点 2：返回值协议 `EventResult`（`pass()/interrupt(Boolean)/interruptTrue()/interruptFalse()/interruptDefault()`，提供 `asMinecraft()` 直接转 `InteractionResult`）与泛型的 `CompoundEventResult<T>`、`EventActor<T>`。
- 关键点 3：事件清单共 113 个 `Event<...>` 字段，`event/events/common` 13 个接口（LifecycleEvent/TickEvent/PlayerEvent/InteractionEvent/BlockEvent/EntityEvent/ChatEvent/CommandRegistrationEvent/ExplosionEvent/LootEvent/ChunkEvent/LightningEvent）、`event/events/client` 12 个（ClientLifecycleEvent/ClientTickEvent/ClientGuiEvent/ClientRawInputEvent/ClientTooltipEvent…）。
- 关键点 4：桥接方向 —— Fabric 把 Fabric API 事件 1:1 转发（`fabric/src/main/java/dev/architectury/event/fabric/EventHandlerImpl.java:64`：`ServerLifecycleEvents.SERVER_STARTING → LifecycleEvent.SERVER_BEFORE_START`，`UseBlockCallback → InteractionEvent.RIGHT_CLICK_BLOCK` 等）；Forge 用 `@SubscribeEvent(priority = EventPriority.HIGH)` 的适配器类转发（`forge/.../EventHandlerImplCommon.java:66` 起 446 行），并提供反向入口 `attachToForge / attachToForgeEventActor / attachToForgeEventActorCancellable`（`forge/.../event/forge/EventFactoryImpl.java:37-68`）把 arch 事件 post 到 `MinecraftForge.EVENT_BUS`（Fabric 侧同名方法为空实现）。`EventHandler.init()` 只注册 client/common/server 三个 `@ExpectPlatform` 方法，按 `Platform.getEnvironment()` 分派。

### 4.3 注册表抽象
- 职责：common 一套 `Registries.get(modId) → Registrar<T> → RegistrySupplier<T>`，屏蔽 Forge `IForgeRegistry` 与 Fabric 直接 `Registry.register`。
- 关键点 1：Fabric 实现直接写注册表 + 用 `RegistryEntryAddedCallback` 实现 `listen`（`fabric/.../registry/registries/fabric/RegistriesImpl.java:44-56`，按 `(RegistryKey, id)` 存入 `LISTENERS` 多重映射，注册后才回调）。
- 关键点 2：Forge 实现把注册推迟到 `RegisterEvent`，用内部类 `Data<T>`（`forge/.../RegistriesImpl.java:47-95`）在注册前只收集 `Supplier`，`registerForForge`/`register` 在事件触发时才真正 register 并派发监听器；同一文件还负责用 `RegistryBuilder` 动态创建自定义 registry（`RegistrarBuilder` + 8 个 `registry/registries/options/*` 选项类）。
- 关键点 3：`DeferredRegister`（`common/.../registries/DeferredRegister.java:46-79`）静态收集条目、`register()` 一次性提交；`registered` 标记后可继续 `register` 并立即落地；`RegistrySupplier` 提供 `isPresent/getOrNull/toOptional/listen`。
- 关键点 4：`Registries.getId(object, fallback)` 处理"Forge 用 `IForgeRegistryEntry.getRegistryName()`、Fabric 用 Registry 反查"的差异。

### 4.4 网络抽象（含分片管线）
- 职责：`NetworkManager`（common）+ `PacketTransformer` 管线 + `SimpleNetworkManager`/`NetworkChannel` 两层易用封装。
- 关键点 1：统一 API `registerReceiver(Side, ResourceLocation id, List<PacketTransformer>, NetworkReceiver)`、`sendToPlayer/sendToPlayers/sendToServer`、`canPlayerReceive/canServerReceive`、`createAddEntityPacket(Entity)`（`common/.../networking/NetworkManager.java:31-112`，多个方法 `@ExpectPlatform`）。
- 关键点 2：Fabric 用 `ServerPlayNetworking/ClientPlayNetworking` 自定义通道；Forge 用自建通道 `architectury:network`（`NetworkRegistry.newEventChannel`）+ `NetworkDirection.buildPacket`（`forge/.../networking/forge/NetworkManagerImpl.java:88-113`），并用自定义 `architectury:sync_ids` 报文下发"服务器能收哪些 id"，从而在 Forge 上模拟出 `canServerReceive`。
- 关键点 3：`SplitPacketTransformer` 把超长负载切包，4 个标记字节 `START/PART/END/ONLY`（`common/.../networking/transformers/SplitPacketTransformer.java:37-40`），配合 `PacketCollector/PacketSink/SinglePacketCollector` 抽象发送目标（测试用例见 `testmod-common/.../networking/TestModNet.java:36-46`，发送 100 万字符字符串）。
- 关键点 4：`NetworkChannel` 用类名生成稳定报文 id（`UUID.nameUUIDFromBytes(type.getName()...)`，`NetworkChannel.java:58-70`），注册 c2s 并在客户端环境额外注册 s2c。

### 4.5 Hooks 与接口注入（injected interfaces）
- 职责：把"原版类上平台特有的行为"包装成 common 静态方法，或直接把接口注入原版类。
- 关键点 1：`common/src/main/java/dev/architectury/hooks/**` 每个类 = 一组 `@ExpectPlatform` 静态方法 + fabric/forge 各一个 `*Impl`（如 `ItemStackHooks`、`PlayerHooks`、`ExplosionHooks`、`BiomeHooks`、`FoodPropertiesHooks`、`HoeItemHooks`、`ScreenHooks`、`FluidStackHooks`）。
- 关键点 2：`architectury.common.json` 的 `injected_interfaces` 字段（用 intermediary 名如 `net/minecraft/class_1792`）把 `dev/architectury/extensions/injected/InjectedItemExtension` 等 8 个接口注入原版类；平台侧以最小 mixin 落地：`common/src/main/java/dev/architectury/mixin/inject/MixinItem.java:26-28` 仅 `@Mixin(Item.class) public class MixinItem implements InjectedItemExtension {}`。
- 关键点 3：`extensions/network/EntitySpawnExtension` 配合 `NetworkManager.createAddEntityPacket` 解决"跨加载器自定义实体生成包 + 额外数据同步"。

### 4.6 BiomeModifications（跨加载器世界生成修改）
- 职责：一套"谓词 + 属性修改器"API 同时驱动 Fabric `BiomeModification` 与 Forge `BiomeModifier`。
- 关键点 1：common `BiomeModifications.addProperties/postProcessProperties/removeProperties/replaceProperties(Predicate<BiomeContext>, BiConsumer<BiomeContext, BiomeProperties.Mutable>)`（`common/.../registry/level/biome/BiomeModifications.java:55-89`）。
- 关键点 2：Fabric 直接映射 4 个 `ModificationPhase`（ADDITIONS/POST_PROCESSING/REMOVALS/REPLACEMENTS，`fabric/.../BiomeModificationsImpl.java:81-85`）。
- 关键点 3：Forge 注册一个"空 Codec 的 BiomeModifier"以在没有数据包的情况下也生效：`Codec.unit(BiomeModifierImpl.INSTANCE)` 注册进 `ForgeRegistries.Keys.BIOME_MODIFIER_SERIALIZERS` 与 `BIOME_MODIFIERS`（`forge/.../BiomeModificationsImpl.java:63-125`），并在 server 启动时遍历 `Registry.BIOME_REGISTRY` 应用（同文件 148 行附近）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.4，Common 提供 `NetworkManager`（channel 级）+ `SimpleNetworkManager`（`BaseC2SMessage/BaseS2CMessage` + `MessageType`，`common/.../networking/simple/`）。
- 数据驱动：有 `LootEvent.MODIFY_LOOT_TABLE`（配 `LootTableModificationContextImpl`）与 `ReloadListenerRegistry`（Fabric `ResourceManagerHelper`/Forge `AddReloadListenerEvent`），但**不定义自己的数据包/Codec 格式**。
- 配置：**无**配置 API。仅 `Mod` 容器提供 ModMenu 配置屏钩子（fabric `PlatformImpl.CONFIG_SCREENS`；forge `container.registerExtensionPoint(ConfigScreenHandler.ConfigScreenFactory.class, ...)`，`forge/.../platform/forge/PlatformImpl.java:181`）。
- datagen：**无**（未发现 `DataProvider`/`GatherDataEvent`，测试 mod 也是手写注册）。
- 资源/字节码：`common/src/main/resources/architectury.accessWidener`（354 行，v2 named）+ `common/build.gradle:44` 起的 `generateAccessWidener` 任务：用 ASM 扫描合并后的 MC jar，自动生成"非 public 的 `Item`/`Block` 构造函数"与 `RenderStateShard` 字段的 `transitive-accessible` 条目写入 `.gradle/generated.accesswidener`。Forge 模块 `convertAccessWidener = true` 转成 AT（`forge/build.gradle:12-16`）。

## 6. Mixin

三份配置：
- `common/src/main/resources/architectury-common.mixins.json`：package `dev.architectury.mixin`，`mixins` 9 个（`inject.MixinItem/MixinBlock/MixinEntityType/MixinFluid/MixinGameEvent/MixinBucketItem/MixinLiquidBlock/MixinFoodPropertiesBuilder` + `MixinLightningBolt`），`required=true`，`maxShiftBy=5`，`defaultRequire=1`
- `fabric/src/main/resources/architectury.mixins.json`：package `dev.architectury.mixin.fabric`，**client 18 + mixins 35**，`plugin: dev.architectury.plugin.fabric.ArchitecturyMixinPlugin`
- `forge/src/main/resources/architectury.mixins.json`：package `dev.architectury.mixin.forge`，client 3 + mixins 5，`plugin: dev.architectury.plugin.forge.ArchitecturyMixinPlugin`

代表性类与注入目标：
- 接口注入：`mixin/inject/MixinItem`、`MixinBlock`、`MixinEntityType`、`MixinFluid`、`MixinBucketItem`、`MixinLiquidBlock`、`MixinGameEvent`、`MixinFoodPropertiesBuilder`（均实现 `Injected*Extension`）；forge 侧 `mixin/forge/MixinItemExtension`、`MixinEntitySpawnExtension`
- 事件触发（Fabric，调用 invoker）：`mixin/fabric/MixinLivingEntity`（`LivingDeathInvoker`）、`MixinPlayer`/`MixinServerPlayer`/`MixinPlayerList`（玩家加入/退出/重生）、`MixinServerLevel`、`MixinNaturalSpawner`/`MixinPhantomSpawner`/`MixinCatSpawner`/`MixinPatrolSpawner`（生成）、`MixinChunkSerializer`、`MixinCommands`、`MixinDedicatedServer`、`MixinResultSlot`/`MixinFurnaceResultSlot`；客户端 `mixin/fabric/client/MixinScreen`/`MixinMinecraft`/`MixinKeyboardHandler`/`MixinTextureAtlas` 等
- 条件禁用：`fabric/src/main/java/dev/architectury/plugin/fabric/ArchitecturyMixinPlugin.java:36-38` 在检测到 `satin` 模组时不应用 `MixinEffectInstance`（避免与光影类 mod 冲突）
- 跨加载器共用的注入点通过 `common/.../mixin/inject/*` + `architectury-common.mixins.json` 打包进 common jar，由平台 jar 携带

## 7. 值得学的 5 条做法

1. **@ExpectPlatform + 平台子包 `*Impl` 命名约定**：common 只留 `throw new AssertionError()`，平台实现按"同包 + `<platform>` 子包 + `<类名>Impl`"命名，构建期由 plugin 改写调用点。文件：`common/.../platform/Platform.java:69` ↔ `fabric/.../platform/fabric/PlatformImpl.java:39`。适用：任何多加载器库/前置的 loader 差异封装。
2. **事件桥接 + 高优先级适配器**：Forge 侧所有转发方法统一 `@SubscribeEvent(priority = EventPriority.HIGH)`，保证 Arch 事件先于普通 mod 监听器执行；反向 `attachToForgeEventActorCancellable` 让 Arch 事件可被 `MinecraftForge.EVENT_BUS` 消费。文件：`forge/.../event/forge/EventHandlerImplCommon.java:66`、`forge/.../event/forge/EventFactoryImpl.java:37-68`。适用：自建事件系统的库。
3. **注册延迟 + 注册后回调（listen）两段式**：注册前只持 `Supplier`，Fabric 用 `RegistryEntryAddedCallback`、Forge 用 `RegisterEvent`，把 `Registrar.listen` 统一成"条目真正存在时回调"。文件：`fabric/.../RegistriesImpl.java:44`、`forge/.../RegistriesImpl.java:47-95`。适用：需要跨加载器注册且条目间互相引用的内容注册。
4. **网络 transformers 管线 + 分片**：把"发送目标"抽象成 `PacketSink`、"出/入站改写"抽象成 `PacketTransformer`，`SplitPacketTransformer` 解决 1MB 包上限；Forge 侧用一条 sync_ids 报文补齐 `canSend` 语义。文件：`common/.../networking/transformers/SplitPacketTransformer.java:37`、`forge/.../networking/forge/NetworkManagerImpl.java:90-113`。适用：需要统一渠道 / 发大包的自定义网络。
5. **ASM 扫描 MC jar 自动生成 accessWidener/AT**：`common/build.gradle:44` 起的 `generateAccessWidener` 遍历 `net/minecraft/world/item|level/block` 找非 public 构造函数、`RenderStateShard` 找非 public 静态字段，输出 `transitive-accessible`；Forge 侧 `convertAccessWideners = true` 自动转 AT。适用：库模组要向外部开放原版构造器/字段。
6. （补充）**用"空 Codec"的 Forge BiomeModifier** 让无数据包场景也能走 Forge 的 worldgen 修改框架：`common Codec.unit(...)` 注册 `BIOME_MODIFIER_SERIALIZERS`。文件：`forge/.../registry/level/biome/forge/BiomeModificationsImpl.java:63-125`。

## 8. 公开 API 与外部 mod 接入（库/API 类 mod）

- 公开 API 包（common，均在 `common/src/main/java/dev/architectury/`）：
  - `platform`（`Platform`、`Mod`）、`utils`（`Env`、`EnvExecutor.runInEnv/getEnvSpecific`、`GameInstance`、`Amount`）
  - `event` + `event/events/{common,client}`（113 个事件字段）、`EventFactory/EventResult/CompoundEventResult/EventActor`
  - `registry`：`registry/registries`（`Registries/Registrar/RegistrarBuilder/DeferredRegister/RegistrySupplier`）、`CreativeTabRegistry`、`ReloadListenerRegistry`、`registry/menu/MenuRegistry`、`registry/level/{biome.BiomeModifications, entity.EntityAttributeRegistry/SpawnPlacementsRegistry, entity.trade.TradeRegistry}`、`registry/item/ItemPropertiesRegistry`、`registry/client/*`
  - `networking`：`NetworkManager`、`NetworkChannel`、`networking/simple/*`、`networking/transformers/*`
  - `hooks/*`（对原版 API 的平台化包装）、`fluid/FluidStack`、`core/*`（`ArchitecturyFluidAttributes`、`ArchitecturySpawnEggItem`、`ArchitecturyBucketItem` 等基类）
- 扩展点接口：`extensions/injected/*`（8 个，经 `architectury.common.json:injected_interfaces` 注入原版类，平台用 `@Mixin` 落地）、`extensions/network/EntitySpawnExtension`（实体生成包额外数据）、`networking/simple/BaseC2SMessage|BaseS2CMessage`、`networking/transformers/PacketTransformer`、`registry/registries/options/RegistrarOption`（自定义 registry 属性）、`Registries.RegistryProvider`（`@ApiStatus.Internal`，非外部扩展）
- 外部 mod 接入方式：Gradle 需 `architectury-plugin`（提供 `@ExpectPlatform` 的 Injectables）与 `architectury-loom`（`architectury { common(...)/fabric()/forge() }` 与 `transformProduction*` 配置）；common 里写 `@ExpectPlatform` 静态方法（**只支持静态方法**），各平台模块提供 `<包>.<平台>.<类名>Impl`；运行时依赖：Fabric 侧 `fabric.mod.json` depends `minecraft ~1.19.2 / fabricloader >=0.14.0 / fabric-api >=0.66.0`，Forge 侧 `mods.toml` depends `minecraft [1.19.2,) / forge [43.2.0,)`。完整用法示例见 `testmod-common/src/main/java/dev/architectury/test/`（`TestMod.initialize()` 里依次调用注册/事件/网络/世界生成示例）
- 打包要点：common jar 内含 mixin 配置 + accessWidener + `architectury.common.json`；平台模块用 shadow 打包 common 并用 `relocate` 覆盖 common 中的平台类（`forge/build.gradle:56-65`：把 `dev.architectury.core.fluid.forge.imitator` 等重定位为 common 包名），Fabric 侧 `remapJar { injectAccessWidener = true }`。

未确认项：`@ExpectPlatform` 注解本体与 `ArchitecturyTarget` 的具体实现（在 `architectury-plugin` 仓库，不在本检出）；NeoForge 与本仓库无关联（本检出仅 1.19.2 + Fabric/Forge）。
