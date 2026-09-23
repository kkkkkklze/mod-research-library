# CreativeMD/CreativeCore 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：CreativeCore / `creativecore`（`src/forge/resources/META-INF/neoforge.mods.toml:7`），作者 CreativeMD，版本 2.13.46。
- 目标平台：`neoforge.mods.toml` 依赖 `neoforge [21.1,)`、`minecraft [1.21.1,1.22)`；`gradle.properties` 无 MC 版本字段，实际由 `build.gradle` 的 `net.neoforged.gradle.userdev 7.0.+` + Java 21 决定（NeoForge 1.21.1）。
- 双加载器：`build.gradle`（NeoForge，sourceSets = `src/main/java` + `src/forge/java`）与 `build.fabric.gradle`（fabric-loom 1.6+，`src/main/java` + `src/fabric/java`，accessWidener `creativecore.accesswidener`，依赖 fabric-api/modmenu）。Fabric 侧额外 `include "net.neoforged:bus:7.2.+"`。
- 许可证 LGPL-3.0-only（`neoforge.mods.toml:4`）；`modProperties = ['displayTest="NONE"']`，即不参与客户端-服务端 mod 列表校验。
- 编译依赖：NeoForge implementation、`net.fabricmc:fabric-loader` compileOnly；无硬性 mod 依赖（README 列出的 AmbientSounds/LittleTiles/PlayerRevive 等均为其下游消费者，本仓库不依赖它们）。
- 额外 sourceSet：`api`（`src/api/java`），main 的 compile/runtime classpath 追加 api 输出（`build.gradle:30-40`），用于放"软依赖外部 mod 的桩类"。

## 2. 源码规模与包结构

实测：465 个 `.java`，50700 行。分布：`src/main/java` 392 文件/45241 行，`src/forge/java` 42/3269，`src/fabric/java` 30/2183，`src/api/java` 1/7。

- `team.creative.creativecore.common` 369 文件，为主战场，二级包：`gui`（control/creator/dialog/event/extension/flow/integration/manager/packet/parser/style/sync）、`config`（api/converation/core/field/group/gui/holder/key/premade/sync）、`network`（type）、`util`（math/type/ingredient/inventory/mc/text/registry/filter/argument/player/unsafe）、`level`、`loader`、`mod/sable`、`test`。
- `team.creative.creativecore.mixin` 9 文件，`client` 9 文件，根包 4 文件（`Side.java`、`ICreativeLoader.java`、`CreativeCoreConfig.java`、`CreativeCoreGuiRegistry.java`）。
- 最大文件：`common/util/math/matrix/Matrix4.java`(1913)、`Matrix3.java`(1903)、`common/util/math/geo/VectorFan.java`(1095)、`common/network/type/NetworkFieldTypes.java`(860)、`config/converation/ConfigTypeConveration.java`(835)、`common/gui/GuiParent.java`(658)、`GuiTextfield.java`(579)、`forge/client/render/box/RenderBox.java`(554)、`client/render/text/CompiledText.java`(522)、`util/math/base/Axis.java`(487)。

## 3. 入口与注册

NeoForge 入口 `src/forge/java/team/creative/creativecore/CreativeCore.java:56` `@Mod(CreativeCore.MODID)`；Fabric 入口 `src/fabric/java/.../CreativeCore.java`（`implements ModInitializer`）。两者共享静态字段：`NETWORK`、`CONFIG`、`LOADER`、`UTILS`、两个 `GuiCreatorBasic`。

注册方式非 DeferredRegister 全覆盖，而是"手写 + RegisterEvent + DeferredRegister 混用"：

- 只有命令参数用 `DeferredRegister`：`CreativeCore.java:74` `COMMAND_ARGUMENT_TYPES = DeferredRegister.create(Registries.COMMAND_ARGUMENT_TYPE, MODID)`，末尾用 `register(ModLoadingContext...getEventBus())`。
- 菜单自己 new：`CreativeCore.java:89` 匿名 `MenuType<>(null, FeatureFlags.VANILLA_SET)`，再在 `RegisterEvent` 里 `event.register(Registries.MENU, ...)`（`CreativeCore.java:102-104`）。
- 事件监听直接用 `ModLoadingContext.get().getActiveContainer().getEventBus().addListener(this::init)` 与 `NeoForge.EVENT_BUS.addListener(this::server)`（`CreativeCore.java:81-85`），不写 `@EventBusSubscriber`。

## 4. 核心系统

1. **平台抽象层**（最有价值）：`ICreativeLoader`（`src/main/java/team/creative/creativecore/ICreativeLoader.java`）以一组 `register*` 方法屏蔽加载器差异，如 `registerLevelTick(Consumer<ServerLevel>)`、`registerKeybind`、`getFluidViscosityMultiplier`；NeoForge 实现在 `src/forge/java/.../CreativeForgeLoader.java`（每个方法内部 `NeoForge.EVENT_BUS.addListener(...)` 再转发给 lambda，如 `:56` `registerClientTick` → `ClientTickEvent.Pre`）。配套接口 `common/CommonLoader`、`client/ClientLoader` 由下游 mod 实现，`ICreativeLoader.register(CommonLoader)` 负责在 `FMLCommonSetupEvent` 时回调 `onInitialize()`（`CreativeForgeLoader.java:43-45`）。
2. **网络系统**：`CreativeNetwork`（`src/main/java/.../common/network`）用「反射字段序列化 + 双方向 id」代替手写 codec。`CreativeCore.java:137-144` 在 `FMLCommonSetupEvent` 里 `NETWORK.registerType(X.class, X::new)`。`CreativeNetworkPacket` 构造时遍历 `classType.getFields()`，跳过 transient 与带 `@OnlyIn` 的字段（`CreativeNetworkPacket.java:30-40`），找不到 parser 直接抛异常；`CreativePacket` 抽象出 `executeClient/executeServer`，`execute(Player)` 自动按 `player.level().isClientSide` 分发（`CreativePacket.java:13-19`）。
3. **配置系统**：字段级注解 `@CreativeConfig(type = ConfigSynchronization.CLIENT, requiresRestart = ...)`（`config/api/CreativeConfig.java`），含 `@IntRange/@DecimalRange` 等子注解驱动滑块 GUI。`CreativeConfigRegistry.ROOT` 用 `Predicate<Field>` 只收「public、非 static、带注解」字段（`config/holder/CreativeConfigRegistry.java:19-20`），序列化为 JsonObject 并带 `HolderLookup.Provider`，支持按 `Side`/`ConfigSynchronization` 区分客户端与服务端值。配置 GUI 自动生成（`config/gui/ConfigGuiLayer.java`），并注册成 `GuiCreatorBasic`（`CreativeCore.java:69-72`），玩家用 `/cmdconfig` 打开。
4. **GUI 系统**：`common/gui/GuiControl` → `GuiParent`/`GuiLayer` 树，控件在 `gui/control/{simple,collection,inventory,menu,parent,timeline,tree}`（simple 下 27 个控件）；打开方式走 `gui/creator/GuiCreator`（`BlockGuiCreator`、`ItemGuiCreator`、`GuiCreatorBasic`），容器统一为 `gui/integration/ContainerIntegration` + 单例 `MenuType`。
5. **GUI 同步**：`gui/sync/GuiSyncHolder` 用路径字符串寻址（`global:` 前缀走全局，其余按 `控件路径:name` 找 layer 的 sync），`GuiSyncGlobal.sendAndExecute(control, tag)` 内部发 `ControlSyncPacket`（`GuiSyncGlobal.java`），调用方无需自定义包。
6. **假世界层**：`common/level/LevelAccessorFake.java`、`BlockGetterFake.java`、`IOrientatedLevel.java`、`NeighborUpdateCollector.java`，为"子维度/虚拟世界"提供 LevelAccessor 实现；网络层专门判断 `level instanceof ISubLevel` 来决定发给 holder 实体或区块（`CreativeNetwork.java:97-120`）。
7. **CreativeIngredient**：`common/util/ingredient/` 把 item、itemstack、tag、block、fuel 统一成"配方输入组"，配 `GuiCreativeIngredientHandler` 支持 GUI 编辑。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：手写 `CustomPacketPayload`（无 codec 生成），`registerType` 时同时注册 `playToServer` 与 `playToClient` 两个 `StreamCodec.ofMember`，注册器 `event.registrar(modid).versioned(version).optional()`（`CreativeNetwork.java:52-70`）；发送端有 `sendToServer/sendToClient/sendToClientTracking{AndSelf}/sendToClientAll` 全家桶。
- 配置：JSON 落盘 + 包同步，`common/config/sync/{ConfigurationPacket,ConfigurationChangePacket,ConfigurationClientPacket}` 是同步载体，`ConfigEventHandler` 按加载器分别实现（`src/forge/java/.../config/event/ConfigEventHandler.java`）。
- datagen：仓库中未发现 datagen（`data/` 生成器）代码，未确认存在。
- 测试设施：`common/test/`（`CreativeTestArgument`/`CreativeTestHelper`）提供 `/cmdtest` 内建自检框架，属少见设计。

## 6. Mixin

- 配置：`src/main/resources/creativecore.mixins.json`、`src/forge/resources/creativecore.forge.mixins.json`、`src/fabric/resources/creativecore.fabric.mixins.json`，refmap 统一 `creativecore.mixins.refmap.json`，`compatibilityLevel: JAVA_21`，`required: true`。
- 主集（6+2）：accessor 类为主——`VoxelShapeAccessor`（`@Accessor @Mutable setShape`）、`ShapesMixin`、`FilePackResourcesAccessor`、`PathPackResourcesAccessor`、`VanillaPackResourcesAccessor`、`MouseHandlerAccessor`、`StringSplitterAccessor`。
- 真正改行为的是 `ComponentSerializationMixin`：用 mixinextras 的 `@WrapOperation` 挂在 `ComponentSerialization.createLegacyComponentMatcher(...)` 调用点，把自定义 `ContentItemStack.TYPE` 追加进 `StringRepresentable[]`，从而让聊天组件支持物品栈内容（`common/util/text/content/ContentItemStack.java`）。
- Forge 侧：`ItemRendererMixin`、`QuadLighterMixin`、`ForgeModelBlockRendererAccessor`；Fabric 侧：`AbstractContainerScreenMixin`、`ArgumentTypeInfosAccessor`、`ModNioResourcePackAccessor`。

## 7. 值得学的 5 条具体做法

1. **用接口 + 加载器实现类收拢平台差异**：所有平台事件在 `ICreativeLoader` 实现里翻译成 lambda 回调，下游只写一份 common 代码（`src/main/java/.../ICreativeLoader.java` + `src/forge/java/.../CreativeForgeLoader.java`）。适用场景：任何要同时支持 NeoForge/Forge/Fabric 的库。
2. **给另一个加载器写编译期桩类**：`src/fabric/java/net/neoforged/fml/common/Mod.java` 是 `@Retention(SOURCE)` 的假 `@Mod`，`api/distmarker/{Dist,OnlyIn}.java` 同理，使 common 代码可直接引用这些注解而不必依赖 NeoForge。适用场景：跨加载器共享源码。
3. **反射驱动的包序列化**：包只声明 public 字段，字段顺序即协议顺序，`transient` 表示不发送，`@OnlyIn` 字段自动跳过（`CreativeNetworkPacket.java:30-40`）。适用场景：大量自定义包的 mod，省去逐包写 codec。
4. **软依赖用"独立 sourceSet 桩 API + ModList 判定"**：`common/mod/sable/SableManager.java` 静态 `INSTALLED = ModList.get().isLoaded("sable")`，桩类 `src/api/java/dev/ryanhcode/sable/companion/math/BoundingBox3d.java` 只声明签名、无实现，由 `sourceSets.api` 提供编译期类型。适用场景：与第三方 mod 的可选联动。
5. **GUI 同步用路径寻址代替自定义包**：`GuiSyncGlobal<C,T>`/`GuiSyncLocal` 只需给控件注册一个 sync 名称，`sendAndExecute` 即完成"发包 + 本地执行"，使服务端与客户端表现一致（`common/gui/sync/GuiSyncGlobal.java`）。

## 8. 公开 API（库 mod）

- 主要 API 包：`team.creative.creativecore.common.gui.*`（控件与 `GuiCreator`）、`team.creative.creativecore.common.config.*`（`@CreativeConfig`、`CreativeConfigRegistry`）、`team.creative.creativecore.common.network.*`（`CreativeNetwork`/`CreativePacket`）、`team.creative.creativecore.common.util.*`（数学/类型/物品过滤）、`team.creative.creativecore.common.level.*`（假世界）。
- 扩展点：实现 `common/CommonLoader`（`onInitialize()`）与 `client/ClientLoader`（`onInitializeClient()`），通过 `CreativeCore.loader().register(...)` / `registerClient(...)` 接入；`ICreativeLoader` 也暴露 `registerListener(Consumer)`、`postForge(Event)` 让下游直接接 NeoForge 事件。
- 接入方式：README 明确"可作为依赖使用，但不得把文件直接复制进自己的 mod"；下游 mod 的 loader 类里调用 `CreativeCore.loader().register(yourLoader)`，配置类注册用 `CreativeConfigRegistry.ROOT.registerValue(MODID, config)`（`CreativeCore.java:147` 的用法）。
