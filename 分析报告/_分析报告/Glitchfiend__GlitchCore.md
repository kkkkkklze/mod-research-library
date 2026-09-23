# GlitchCore 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：GlitchCore / `glitchcore`（`gradle.properties:25-26`）
- 作者 / 维护：Adubbz（Glitchfiend Team，即 Biomes O' Plenty / 系模组团队）
- 许可证：`mod_license=All Rights Reserved`（`gradle.properties:29`），仓库内**无 LICENSE 文件**，属"源码可见但不授权"（注意：不可直接抄代码，只可学结构）
- 目标版本（`gradle.properties:5-22`）：`minecraft_version=26.2`、Forge `65.0.1`、NeoForge `26.2.0.7-beta`（NeoForm `26.2-1`）、Fabric loader `0.19.3` + Fabric API `0.153.0+26.2`
- 构建：**多加载器多工程**（`settings.gradle:24` `include("common","forge","neoforge","fabric")`，并把工程名改成大写 `Common/Forge/NeoForge/Fabric`）。common 与 neoforge 用 `net.neoforged.moddev 2.0.141`（NeoGradle），fabric 用 `net.fabricmc.fabric-loom 1.15-SNAPSHOT`；根工程用 Forge 的 `gitversion` + `changelog` 插件算版本号；Java **25** toolchain（`build.gradle:47-52`）；发布用 `de.maxhenkel.cursegradle` + Minotaur
- 编译依赖：`com.electronwill.night-config:toml/core:3.6.7`、`net.jodah:typetools:0.6.3`（Fabric 侧 `include` 打包进 jar）、`org.spongepowered:mixin:0.8.5` + `mixinextras-common:0.3.5`（仅 common 的 compileOnly + annotationProcessor）。**无 Preprocessor/无 Stonecutter**，靠手写 mixin 做平台差异（见第 4 节）
- 它是 BOP 系的**前置库**，本身不注册任何方块/物品

## 2. 源码规模与包结构

实测：`.java` 文件 **91 个**，共 **4180 行**。分模块：`common` 36 文件 / 1975 行；`neoforge` 20 / 778；`fabric` 16 / 780；`forge` 19 / 647。

`common/src/main/java/glitchcore/`（平台无关）：
- `config/`（2）：`Config.java`(221，最大文件)、`ConfigSync.java`
- `core/`（1）：`GlitchCore.java`
- `data/`（1）：`ModelProviderBase.java`(186)
- `event/`（7 顶层 + 子包）：`Event`、`EventManager`、`RegistryEvent`、`TickEvent`、`TagsUpdatedEvent`；`event/client/`（8，`RenderHudEvent`、`RenderTooltipEvent`、`RegisterColorsEvent`…）、`event/entity/`、`event/player/`、`event/server/`
- `mixin/`（3 + `client/` 2）
- `network/`（4）：`CustomPacket`、`PacketHandler`、`SyncConfigPacket`、`SyncConfigTask`
- `util/`（6）：`Environment`、`RegistryHelper`、`BlockHelper`、`RenderHelper`、`GuiUtils`、`Remapper`

各加载器模块结构**完全同构**：`<loader>/glitchcore/<loader>/` 下有 `GlitchCore<Loader>` 主类、`handlers/`（11 个 `*EventHandler`，把 GC 事件桥接到该加载器事件总线）、`mixin/`（同名 `MixinServerPlayer`、`client/MixinHud`、`client/MixinGuiGraphicsExtractor`）、`mixin/impl/`（`MixinBlockHelper`/`MixinEnvironment`/`MixinPacketHandler`/`MixinRenderHelper`）、`network/GCPayloadFactory`。

## 3. 入口与注册

common 侧 `common/src/main/java/glitchcore/core/GlitchCore.java:10-25`：

```java
public class GlitchCore {
    public static final String MOD_ID = "glitchcore";
    public static final Logger LOGGER = LogManager.getLogger(MOD_ID);
    private static final Identifier CHANNEL = Identifier.fromNamespaceAndPath(MOD_ID, "main");
    public static final PacketHandler PACKET_HANDLER = new PacketHandler(CHANNEL);
    public static void init() { registerPackets(); }
    private static void registerPackets() {
        PACKET_HANDLER.register(Identifier.fromNamespaceAndPath(MOD_ID, "sync_config"), new SyncConfigPacket());
    }
}
```

各加载器入口极薄，仅调用 `GlitchCore.init()`：`neoforge/.../GlitchCoreNeoForge.java:10-19`（`@Mod(value = GlitchCore.MOD_ID)`，另留一个 `@Deprecated` 空方法 `prepareModEventHandlers(IEventBus)` 作为依赖方的兼容壳）、`forge/.../GlitchCoreForge.java`、`fabric/.../GlitchCoreInitializer.java`。

**没有注册框架**：库本身不注册内容；给下游提供的是 `util/RegistryHelper.java`（`implements Consumer<RegistryEvent>`，`create()` + 内部 `interface Registrar<T>`），由下游在加载器 `RegistryEvent` 中注册。

## 4. 核心系统

**(a) "common 桩 + 子模块 mixin @Overwrite" 的平台差异方案（本仓库最有价值的设计）**
`common/.../util/Environment.java:9-25` 的方法体全是 `throw new UnsupportedOperationException()`；对应的平台实现在 `*/mixin/impl/MixinEnvironment.java` 中以 `@Mixin(value = Environment.class, remap = false)` + `@Overwrite` 写实数（NeoForge 版转调 `FMLEnvironment.getDist()`、`FMLPaths.CONFIGDIR`、`ModList.get().isLoaded()`）。同理 `PacketHandler`（`neoforge/.../mixin/impl/MixinPacketHandler.java`）、`BlockHelper`、`RenderHelper`。优点：common 代码零加载器 API、调用点全静态；代价：用 mixin 改 mod 自己的类，属"自 Overwrite"。

**(b) 自建跨加载器事件总线**
`common/.../event/EventManager.java:15-53`：`Map<Class<? extends Event>, Consumer<? extends Event>[]>` + 独立 `lock` 对象，`addListener(Consumer<T>)` 用 `TypeResolver.resolveRawArgument(Consumer.class, …)` 从 lambda 反推事件类型；`fire(T)` 顺序遍历，遇到 `isCancellable() && isCancelled()` 立即 break。`Event.java:6-22` 提供 `isCancellable/setCancelled`（不可取消的事件调用 setCancelled 抛异常）。下游用 `EventManager.getRequiredEvents()` 决定要监听哪些原版事件。

**(c) 网络抽象**
`common/.../network/CustomPacket.java`：`interface CustomPacket<T extends CustomPacket<T>>` 只要 `encode(FriendlyByteBuf)/decode/handle(T, Context)`，`Context` 给 `isClientSide()`、`getPlayer()`，另有 `enum Phase { PLAY, CONFIGURATION }` 支持配置阶段包。`PacketHandler`（构造 `new PacketHandler(Identifier.fromNamespaceAndPath(modid,"main"))`）暴露 `register/sendToPlayer/sendToAll/sendToHandler/sendToServer`。NeoForge 实现里用 `Map<Class<?>, CustomPacketPayload.Type<?>> ids` 以"数据类"为键（`getPacketDataType` → `TypeResolver`），并用 `container.getEventBus().addListener(RegisterPayloadHandlersEvent…)` + `registrar.versioned(modid)` 注册，`sendToHandler` 里按 `handler.getConnection().getSending()`（`ClientboundCustomPayloadPacket`/`ServerboundCustomPayloadPacket`）分方向发包。

**(d) 自带 TOML 配置系统（不用加载器配置 API）**
`common/.../config/Config.java`（221 行）：`abstract class Config implements UnmodifiableConfig, CommentedConfig`，包一层 night-config `TomlFormat`；构造时 `readToml → parse → load()(抽象，子类声明字段) → write()` 即"缺键补默认值并回写"；`add(key, def, comment, validator)` 校验失败回退默认并 warn，`addNumber(key, def, min, max, comment)` 做区间校验。`ConfigSync.java` 维护 `Map<String, Config>`，`createPackets()` 把每个配置编成 `SyncConfigPacket(path, tomlBytes)`，`reload(path, toml)` 在客户端热应用 —— 服务端配置同步是自带实现，不依赖加载器。

**(e) 数据生成基类**：`common/.../data/ModelProviderBase.java`（186 行）为下游提供跨平台模型/blockstate 生成骨架。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4(c)；实际只有 1 个内置包 `glitchcore:sync_config`（`GlitchCore.registerPackets`）。
- 配置：见 4(d)；`ConfigSync.register(config)` 是下游接入点。
- 数据驱动：无（自身无内容）。datagen：仅 `ModelProviderBase`；各加载器 `build.gradle` 里配了 `runData`（neoforge 侧 `--mod glitchcore --all --output src/generated/resources`）与 `sourceSets.main.resources { srcDir 'src/generated/resources' }`。
- 资源：`common/src/main/resources/` 有 `glitchcore.mixins.json`、`glitchcore.accesswidener`、`META-INF/`。

## 6. Mixin

四份配置：`common/src/main/resources/glitchcore.mixins.json`、`glitchcore.neoforge.mixins.json`、`glitchcore.forge.mixins.json`、`glitchcore.fabric.mixins.json`（均 `required: true`、`compatibilityLevel: JAVA_17`、`refmap: glitchcore.refmap.json`、`injectors.defaultRequire: 1`）；toml 同时声明两份（`[[mixins]] config="${mod_id}.mixins.json"` + 加载器版）。

- common：`MixinItemStack`、`MixinServerConfigurationPacketListenerImpl`（为 CONFIGURATION 阶段发包服务）、`MixinServerLevel`；client 段 `MixinKeyboardHandler`、`MixinMinecraft`（68 行，转发 `InputEvent`）
- neoforge / forge / fabric：`MixinServerPlayer`（neoforge 版 33 行）、`client/MixinHud`、`client/MixinGuiGraphicsExtractor`，加 `impl.*` 四个"平台实现覆盖"mixin（`@Overwrite` 目标是自己 mod 的类，`remap = false`）
- 具体注入方法名未逐文件确认（本报告只读预算内已知 `@Overwrite` 与类级 `@Mixin` 目标）

## 7. 值得学的 5 条具体做法

1. **平台差异 = common 抛异常 + 子模块 mixin Overwrite**：`common/.../util/Environment.java:11-24` 与 `neoforge/.../mixin/impl/MixinEnvironment.java:11-27`。适用：想在 NeoForge/Forge/Fabric 之间共享一份业务代码、又不愿引 Preprocessor/Stonecutter 时。
2. **事件类从 lambda 反推泛型**：`event/EventManager.java:60-68` 用 `TypeResolver` 免去 `addListener(EventType, Consumer)` 的重复类型参数；同一个技巧也用于网络包类型键 `MixinPacketHandler.getPacketDataType`。
3. **配置"缺键即补 + 校验回退"**：`config/Config.java:38-62`，`add(key, def, comment, validator)` 让非法值自动还原默认并 warn，避免用户改坏配置崩溃。
4. **配置同步走自己的包**：`config/ConfigSync.java:27` `createPackets()` + `network/SyncConfigPacket.java`，把 TOML 文本整体下发、客户端 `reload` 重解析。适用：需要服务端权威配置且客户端要读的 mod。
5. **加载器模块目录同构**：`neoforge/`、`forge/`、`fabric/` 三个模块的包名、类名一一对应（`GlitchCore<Loader>`、`handlers/*EventHandler`、`mixin/impl/*`），改一个平台即可照抄到另两个，diff 成本极低。适用：多加载器维护。

## 8. 公开 API（GlitchCore 是纯前置库）

- 工具/平台抽象：`glitchcore.util.Environment`（`isClient/getConfigPath/isModLoaded`）、`RegistryHelper`（`create()` + `Registrar<T>`）、`BlockHelper`、`RenderHelper`、`GuiUtils`、`Remapper`
- 事件：`glitchcore.event.EventManager` + `Event`/`RegistryEvent`/`TickEvent`/`TagsUpdatedEvent`，以及 `event/client/*`（渲染、Tooltip、颜色、粒子图集、图层定义、HUD）、`event/player/PlayerEvent`、`PlayerInteractEvent`、`event/entity/LivingEntityUseItemEvent`、`event/server/RegisterCommandsEvent`
- 网络：`glitchcore.network.CustomPacket<T>`（+ `Context`、`Phase`）、`PacketHandler`（`register/sendToPlayer/sendToAll/sendToHandler/sendToServer`）
- 配置：`glitchcore.config.Config`（继承它 + 实现 `load()`）、`ConfigSync.register(config)`
- 数据生成：`glitchcore.data.ModelProviderBase`
- 接入方式：下游 mod 编译期依赖 GlitchCore，`@Mod` 构造里不要自己 `GlitchCore.init()`（主类已调），改用 `EventManager.addListener(...)` 订阅事件、`RegistryHelper.create()` 在 `RegistryEvent` 中注册内容、`new PacketHandler(自己的 channel)` 建自己的通道（Channel namespace 必须属于某个 mod，否则 NeoForge 实现会 `orElseThrow`）。NeoForge 侧保留 `GlitchCoreNeoForge.prepareModEventHandlers(IEventBus)` 空方法供老版本下游兼容。
