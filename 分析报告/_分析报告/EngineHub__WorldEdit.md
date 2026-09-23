# EngineHub/WorldEdit 源码分析报告

## 1. 基本信息

- Mod 名：WorldEdit；mod_id：`worldedit`（`worldedit-neoforge/src/main/resources/META-INF/neoforge.mods.toml:10`）；作者 EngineHub
- 版本：`7.4.6-SNAPSHOT`（`gradle.properties:2`，group `com.sk89q.worldedit`）
- 目标 MC / 加载器：当前检出分支为多平台。`gradle/libs.versions.toml:21` `neoforge-minecraft="26.2"`、`:104` `fabric-minecraft="com.mojang:minecraft:26.2"`、`:108` `neoforge=26.2.0.53-beta`；Bukkit 侧为 adapter‑1.21.4 ~ adapter‑26.2 多版本模块（`settings.gradle.kts` 中 `listOf("1.21.4", ...)`）
- 许可证：GPL-3.0-only（mods.toml `license="GPL-3.0-only"`）
- Gradle：Kotlin DSL + 复合构建 `build-logic/`，插件 `net.neoforged.gradle.userdev`、fabric-loom、`org.spongepowered.gradle.vanilla`、shadow、`org.enginehub.crankcase.*`（自研构建插件：许可头/校验/japicmp/publishing）
- 关键依赖（它依赖谁）：`worldedit-core` 依赖 `org.enginehub.piston`（命令引擎 0.6.0）、`org.enginehub.linbus`（NBT 读写）、`com.sk89q.lib:jlibnoise`、antlr4-runtime、rhino-runtime、Kyori adventure、Guava；`worldeditcui-protocol` 4.0.3（CUI 协议，jarJar 内嵌到 neoforge 产物）

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **1070**；总行数 **161232**。

模块分布：worldedit-core 867、worldedit-bukkit 111、worldedit-core-mc 37、worldedit-sponge 32、worldedit-cli 13、worldedit-fabric 6、worldedit-neoforge 4（`worldedit-mod` 为空壳聚合）。

主要包（`worldedit-core/src/main/java/com/sk89q/worldedit/`）：`extent` 67、`function` 101（mask 34 / pattern 14 / visitor 8）、`world` 107（registry 24 / storage 16 / snapshot 15）、`util` 115、`command` 105、`internal` 81、`math` 32、`regions` 41、`session` 15、`registry` 12、`extension/platform` 18。

最大文件：`EditSession.java` 3211、`PaperweightDataConverters`（各 bukkit adapter 2766~2807）、`worldedit-core-mc/.../CoreMcDataFixer.java` 2720、`world/item/ItemTypes.java` 1587、`LocalSession.java` 1322。

## 3. 入口与注册

主类（NeoForge）`worldedit-neoforge/src/main/java/com/sk89q/worldedit/neoforge/internal/NeoForgeWorldEdit.java:51`：

```java
@Mod(NeoForgeWorldEdit.MOD_ID)          // MOD_ID = "worldedit"
public class NeoForgeWorldEdit extends CoreMcMod {
    public NeoForgeWorldEdit(IEventBus modBus) {
        modBus.addListener(this::onFMLCommonSetup);
        NeoForge.EVENT_BUS.register(new EventHandler(this)); // 事件集中在内部类
    }
    private void onFMLCommonSetup(FMLCommonSetupEvent event) {
        PLATFORM = new NeoForgePlatform(this);
        init(PLATFORM, FMLPaths.CONFIGDIR.get());            // CoreMcMod 提供全部初始化
    }
}
```

Fabric 侧同构：`worldedit-fabric/.../internal/FabricWorldEdit.java`。

注册框架：**不使用 DeferredRegister/Registrate**（WorldEdit 不注册方块物品，而是操作既有方块）。它自建注册表 `com.sk89q.worldedit.registry.Registry<V extends Keyed>`（`Registry.java:113 register(key,value)`，键强制小写、重复注册直接 checkState 报错），`CommonRegistries`/平台 `CoreMcRegistries extends BundledRegistries`（`worldedit-core-mc/.../CoreMcRegistries.java:32`）在平台就绪时把 `BuiltInRegistries` 的方块/物品/生物群系/类别灌入 WorldEdit 自己的 BlockType/ItemType/BiomeType（`worldedit-core/.../world/registry/` 24 个文件）。

## 4. 核心系统

1. **Extent 管线（学习价值最高）**：`extent/Extent.java:38` `interface Extent extends InputExtent, OutputExtent`。一切世界读写都是 Extent 的装饰叠加（`extent/cache`、`extent/buffer`、`extent/validation`、`extent/reorder`、`extent/transform`、`extent/inventory`、`extent/clipboard`），`EditSession` 用构造链把 mask/buffering/reorder/survival 逐层包在 World 上，末尾暴露 getter（`EditSession.java:514 getMask`、:384 setReorderMode、:595 getBlockBag）。
2. **History/撤销**：`history/ChangeSet`、`history/change/BlockChange`、`changeset/` 三种实现（memory/disk），配合 `extent/buffer` 做"先写缓冲、后提交"的批量撤销。
3. **Session 系统**：`LocalSession.java`（1322 行）保存选区/剪贴板/画笔/历史，`session/SessionManager.java` 管理玩家→Session 映射，`session/storage/JsonFileSessionStore.java` + `SessionStore` 做 JSON 落盘。
4. **剪贴板/结构格式注册**：`extent/clipboard/io/ClipboardFormat.java` 为扩展点，`ClipboardFormats.registerClipboardFormat(...)`（`ClipboardFormats.java:49`）运行时注册；内置 `BuiltInClipboardFormat` 枚举（mcedit / sponge.1 / sponge.2 / sponge.3），各格式用 `isFormat(InputStream)` 探测、`getReader/getWriter` 产出读写器，Sponge v2/v3 读写器独立成类。
5. **命令系统**：注解式命令 `command/*.java`（105 个）基于外部 `org.enginehub.piston`，在游戏内合并进 Brigadier：`CoreMcMod.registerCommands`（`worldedit-core-mc/.../CoreMcMod.java:208`）取 `manager.getPlatformCommandManager().getCommandManager()` 再逐条注册；权限用 `command/util/PermissionCondition`。
6. **平台抽象 + CUI**：`Platform`/`AbstractPlatform`/`Capability`/`MultiUserPlatform` + `PlatformManager`；fabric 与 neoforge 共享 `CoreMcPlatform extends AbstractPlatform`（`CoreMcPlatform.java:56`，声明支持 VALIDATION/ENTITY_AI/LIGHTING/NEIGHBORS/UPDATE 五类 SideEffect），仅权限与适配差异由 `NeoForgePlatform`/`FabricPlatform` + `*Adapter` 覆盖。CUI 走协议库：`CUIPacketHandler.instance().registerServerboundHandler(this::onCuiPacket)`（`NeoForgeWorldEdit.java:81`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自研 payload，仅 CUI（client UI 协议，外部库 4.0.3，neoforge 侧 jarJar 内嵌并 relocate antlr/rhino/jlibnoise）。
- 配置：`worldedit-core-mc/src/main/resources/defaults/worldedit.properties`（内置默认值，注释会被剥除，故用 `#Don't put comments` 提示），由 `CoreMcConfiguration` 读写；语言文件来自 EngineHub 的 ivy 仓库（`language-files/` + `worldedit-lang`）。
- datagen：无（`worldedit-core/src/main/resources` 为空，资源靠构建期 `expose-resources` 从 core/core-mc 拷入）。数据格式转换靠 `CoreMcDataFixer`（2720 行，DFU 桥接）。

## 6. Mixin

配置：`worldedit-core-mc/src/main/resources/worldedit-coremc.mixins.json`（`required=true`、`compatibilityLevel=JAVA_8`、`defaultRequire=1`），在 neoforge.mods.toml 用 `[[mixins]] config=` 声明。成员 5 个 Accessor：`AccessorChunkMap`、`AccessorClientboundBlockEntityDataPacket`、`AccessorCommandSourceStack`、`AccessorMinecraftServer`、`AccessorServerPlayerGameMode`（`@Accessor("isDestroyingBlock")`）；1 个注入类 `MixinServerGamePacketListenerImpl`：`@Inject(method="handleAnimate", at=@At(value="INVOKE", target="...ServerPlayer;swing(...)"))`，把原版左键挥动改道给 WorldEdit 的交互钩子。

## 7. 值得学的 5 条做法

1. **Extent 装饰器链替代 if-else**：写世界前按需套 mask/buffer/validation 层，用例 `extent/Extent.java` + `EditSession.java:514`；适用于任何"批量改方块"系统。
2. **多加载器共享中间层**：把 90% 逻辑放平台无关的 `worldedit-core-mc`（`CoreMcPlatform`/`CoreMcWorld`/`CoreMcMod`），fabric/neoforge 只留 4~6 个薄适配类——1.21.1 单版本 mod 想留移植余地可照搬"core-mc + 薄壳"分层。
3. **格式注册 + 内容探测**：`ClipboardFormats.registerClipboardFormat` + `isFormat(InputStream)`，使新格式可插件化且能自动识别旧文件。
4. **构建逻辑抽成 composite build**：`settings.gradle.kts` `includeBuild("build-logic")` 复用许可头/校验/publishing 插件，避免多模块复制 gradle 脚本。
5. **事件集中到内部 EventHandler 类**：`NeoForgeWorldEdit.java:93` 注释明确说明是为了规避类加载器在 `@Mod` 构造期加载过多方法——规避 FML 类加载坑的实用写法。

## 8. 公开 API / 扩展点（WorldEdit 是"被依赖型"工具）

- API 包：`com.sk89q.worldedit.*` 内所有 public 类即 API（无独立 api 子包），另有 japicmp 校验保证向后兼容。
- 接入方式：实现 `extent/Extent`（自定义读写层）、`function/mask/Mask`、`function/pattern/Pattern`、`ClipboardFormat`、`Platform`/`AbstractPlatform`（新平台）、`Registries`（自定义注册表）；入口 `WorldEdit.getInstance()`（`WorldEdit.java:150`）、`WorldEdit.getPlatformManager()`、`WorldEdit.getInstance().newEditSession(...)`。
- 事件：`com.sk89q.worldedit.event.platform.*`（PlatformReadyEvent、ConfigurationLoadEvent、BlockInteractEvent 等）经 `util/eventbus/EventBus` 派发，第三方可监听；CUI 则通过 `org.enginehub.worldeditcui.protocol.CUIPacketHandler` 与客户端 UI 通信。
