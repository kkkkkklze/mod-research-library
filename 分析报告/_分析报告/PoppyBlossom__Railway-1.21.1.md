# PoppyBlossom/Railway-1.21.1 源码分析报告

## 1. 基本信息

- Mod 名：Create: Steam 'n' Rails 1.21.1（Steam 'n' Rails 的 1.21.1 非官方移植）；mod_id `railways`；作者 PoppyBlossom、Chameleon538、gblfxt；mod_version `0.3.0-beta.2`
- 目标版本：**MC 1.21.1 + NeoForge 21.1.233**（`neoforge_version_range=[21.1,)`，注释写明"为满足 Create 最低 21.1.200+"），Java 21
- 加载器：**实际只构建 NeoForge**，但源码完整保留了多加载器抽象层——`multiloader/Loader.java` 枚举仍有 `FORGE/NEOFORGE/FABRIC/QUILT`，`multiloader/` 下每个接口都有 `neoforge/*Impl`。`gradle.properties` 中 `fabric_api_version` 已被注释、`fabric_recipe_viewer` 仍在
- Gradle 插件（Kotlin DSL）：`net.neoforged.moddev 2.0.141`、`mod-publish-plugin`、`dev.ithundxr.silk`（changelog）、`net.kyori.blossom`（源码模板）、`idea-ext`；accessTransformer 走 `src/main/resources/META-INF/accesstransformer.cfg`，parchment 已注释掉（回退 Mojmap）
- 许可证：LGPL-3.0
- 依赖（`neoforge.mods.toml` + `build.gradle.kts`）：**Create 6.0.10-281**（`versionRange="[6.0.7,)"`）、Catnip `0.8.54`、Ponder `1.0.85`、Flywheel `1.0.6`、Registrate `MC1.21-1.3.0+67`、MixinExtras `0.5.4`；可选 compat：Hex Casting（`ordering="AFTER"`）、BYG/BOP/Natures Spirit/Create: D&D/Quark/TFC/JourneyMap/VoiceChat/Tweakeroo/SecurityCraft/Sodium+Iris

## 2. 源码规模与包结构

实测：**761 个 `.java`，71,222 行**（单模块 `src/main`）。

- `content/` 46 个子包（`conductor`、`coupling/coupler`、`custom_bogeys`、`custom_tracks`、`buffer`、`smokestack`、`semaphore`、`switches`、`shadow_realm`、`fuel/tank`、`schedule`、`animated_flywheel`、`bogey_menu`、`roller_extensions`、`distant_signals` 等）
- `mixin/` **181 个 java 文件**（含 `mixin/client`、`mixin/compat`、`mixin_conductor_possession`、`mixin_interfaces`）、`registry/` 37 个 `CR*.java` + `commands/` 14 个、`base/data/`（datagen）、`compat/`（tracks/mods、journeymap、tweakeroo、create）、`multiloader/` 18、`neoforge/`（`asm/`、`datagen/`、`events/`、`mixin/`）、`ponder/scenes/`、`api/bogeymenu/v0/`、`impl/bogeymenu/v0/`、`annotation/`

最大文件：`content/conductor/ConductorEntity.java` 1628、`ponder/scenes/TrainScenes.java` 1053、`registry/CRBlocks.java` 875、`registry/CRPalettes.java` 841、`base/data/neoforge/BuilderTransformersImpl.java` 826、`content/coupling/coupler/TrackCouplerBlockEntity.java` 681、`base/data/recipe/RailwaysStandardRecipeGen.java` 659。

## 3. 入口与注册

主类拆成两份：**`Railways`**（无注解，纯初始化逻辑）+ **`neoforge/RailwaysImpl`**（`@Mod(Railways.MOD_ID) @EventBusSubscriber`，构造注入 `IEventBus` + `ModContainer`）。

```java
// neoforge/RailwaysImpl.java:57-...（简化）
public RailwaysImpl(IEventBus modEventBus, ModContainer modContainer) {
    bus = modEventBus;
    CRCreativeModeTabsImpl.register(RailwaysImpl.bus);
    modEventBus.addListener(CREntityAttributesImpl::registerAttributes);
    Railways.init();
    CRConfigsImpl.register(modContainer);
    CRParticleTypesParticleEntryImpl.register(bus);
    modEventBus.addListener(RailwaysDataPackImpl::onBuiltinPackRegistration);
}
```

`Railways.init()`（`Railways.java:74-104`）顺序固定：**先配置迁移**（`migrateConfig()` 读旧 toml，内容含 `#General settings`/`[general]` 就整体重写为新格式）→ `ModSetup.register()` → `RailwaysImpl.finalizeRegistrate()` → 开发环境打印 Registrate 条目数 → `registerCommands(CRCommands::register)` → `CRPackets.PACKETS.registerC2SListener()` → dev 环境 `MixinEnvironment.audit()`（且显式排除 NeoForge/BYG/Sodium/数据生成）。

**注册体系 = Create 的 `Registrate`**：`Railways.java:57` 静态字段 `private static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)`，静态块里 `REGISTRATE.setTooltipModifierFactory(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE).andThen(TooltipModifier.mapNull(KineticStats.create(item))))` 统一注入 Create 风格 tooltip。`ModSetup.register()`（`ModSetup.java:29-72`）手工编排注册顺序，并在注册不同类别前**切换 Registrate 当前创造标签页**（`useBaseTab()` / `useTracksTab()` / `usePalettesTab()`），保证轨道方块进 Tracks 页、调色板物品进 Palettes 页。compat 轨道注册用 `GenericTrackCompat.isDataGen() || CRConfigs.getRegisterMissingTracks() || mod.isLoaded` 三重条件。

## 4. 核心系统

1. **网络抽象 `multiloader/PacketSet`**（`multiloader/PacketSet.java`）：抽象类 + `Builder`，`c2s(C.class, C::new)` / `s2c(...)` 链式注册；发送时 `写 VarInt 类型下标 + packet.write(buf)`，`Object2IntMap<Class,Integer>` 做类→id 映射（`Builder.s2c` 用 `indexOf(factory)` 生成）。`builder(id, version)` 内置 **`CheckVersionPacket` 版本握手**，`onPlayerJoin()` 时下发，版本不一致直接 `mc.getConnection().onDisconnect(...)`。`CRPackets.PACKETS = PacketSet.builder("railways", 13)` 注册 28 个包（12 C2S + 14 S2C），并额外提供 `send(Object)`/`sendTo(..., Object)` 重载**直接转发 Create 自己的包**。
2. **条件 Mixin 的 ASM 反射判定**（`util/ConditionalMixinManager.java:26-69`）：`CRMixinPlugin.shouldApplyMixin` 委托它，后者用 `MixinService.getService().getBytecodeProvider().getClassNode(className)` 取字节码，读**类级与方法级**注解：`@ConditionalMixin(mods={Mods.X}, applyIfPresent=true)` 决定"有 mod 才生效/没 mod 才生效"，`@DevEnvMixin` 只在开发环境生效（`annotation/mixin/`）。
3. **Conductor 实体系统**（`content/conductor/ConductorEntity.java` 1628 行）：自定义 AI 实体 + 远程视角/相机（`remote_lens`、`util/packet/CameraMovePacket`）、工具箱（`toolbox/`、`MountedToolbox*Packet`）、口哨指挥（`whistle`）、通风管（`vent`）。是本仓库最大的单文件，AI/实体方向可直接对照。
4. **车辆/转向架体系**：`content/custom_bogeys/`（`blocks/base/be` 里各种 Bogey BE + 尺寸 gauge）、`registry/CRBogeyStyles.java`、`registry/CRBlockPartials.java`（Flywheel 模型部件）、API 侧 `api/bogeymenu/v0`。耦合器在 `content/coupling/coupler/`（`TrackCouplerBlockEntity` 681 行）。
5. **Ponder 教学场景**：`ponder/scenes/`（`TrainScenes` 1053 行）+ `CRPonderIndex`/`CRPonderTags`，用 Create 的 Ponder 注册交互式教程——Create 附属做"新手引导"的范本。
6. **跨版本存档兼容**：`Railways.DATA_FIXER_VERSION = 2` + `registry/CRDataFixers.java` + `base/datafixerapi/` + `base/datafixers/`，方块 ID 变更时写 DataFixer（注释明确"一个版本内不要多次 bump"）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见上，`multiloader/{C2SPacket,S2CPacket,PlayerSelection}` + `util/packet/` 25 个包实现；`neoforge/RailwaysNetworking.java` 做 neo 侧落地；`PlayerSelection` 抽象"发给谁"（单人/tracking）
- 数据驱动：无自定义 datapack 注册表；主要靠 Registrate 的 `ProviderType` 生成 tag/lang；EMI 兼容生成器 `base/data/compat/emi/Emi{ExcludedTag,RecipeDefaults}Gen`
- 配置：`config/CRConfigs.java` 用 **Catnip 的 `ConfigBase` + `ModConfigSpec`**，按 `ModConfig.Type` 存 `EnumMap`（client/common/server 三份 `CClient/CCommon/CServer`），平台实现 `config/neoforge/CRConfigsImpl`；迁移用 nightconfig 的 `CommentedConfig`/`TomlParser`
- datagen：`neoforge/datagen/`（`DataGenerators`、`RailwaysGeneratedEntriesProvider`、`Compat{Track}{LootTable,Recipe,Tag}Provider`）+ `base/data/recipe/`（`RailwaysStandardRecipeGen` 659 行、`RailwaysSequencedAssemblyRecipeGen`、`RailwaysItemApplicationRecipeGen`、`RailwaysMixingRecipeGen`）+ `CRLangGen`/`CRTagGen`
- 额外：`neoforge/asm/` 有运行时 ASM 改写（`RollingModeEnumAdder` 给枚举加常量、`ContainerLevelAccessASM`）；`src/main/resources/railways.accesswidener` 存在（但 NeoForge 用 accesstransformer.cfg）

## 6. Mixin

- `src/main/resources/railways-common.mixins.json`：`package com.railwayteam.railways.mixin`，`plugin: com.railwayteam.railways.mixin.CRMixinPlugin`，`compatibilityLevel JAVA_21`，mixins 列表很长（`Accessor*` 系列 20+ 个 accessor + `MixinContraption`、`MixinBezierConnection`、`MixinGlobalStation`、`MixinTrainRelocator` 等），另有 client 段；`railways.mixins.json` 是 NeoForge 侧（`com.railwayteam.railways.neoforge.mixin`，`ChunkMapAccessor`、`TrainMixin`、`TrainRelocationPacketMixin`、`client.TrainHUDMixin` 等），两份都在 `neoforge.mods.toml` 用 `[[mixins]]` 显式挂载
- `CRMixinPlugin`（`mixin/CRMixinPlugin.java` 与 `neoforge/mixin/CRMixinPlugin.java` 两份）只实现 `shouldApplyMixin`，其余全 NO-OP
- `mixin_interfaces/` 放 duck interface（如给 Train/Carriage 加方法），`mixin_conductor_possession/` 专管"玩家操控 Conductor"这套独立 mixin 集

## 7. 值得学的 5 条具体做法

1. **注册顺序 + 创造标签页上下文显式编排**：`ModSetup.register()` 里在注册轨道/调色板前先切 tab 上下文，避免事后往 tab 里塞物品（`ModSetup.java:29-72`）。
2. **注解驱动的条件 mixin**：`@ConditionalMixin(mods=..., applyIfPresent=...)` / `@DevEnvMixin` + ASM 字节码读注解，比在 plugin 里写一长串 `if (modLoaded)` 可维护得多（`util/ConditionalMixinManager.java:26-69`）。
3. **网络协议自带版本号 + 握手包**：`PacketSet.builder(id, 13)` 自动注册 `CheckVersionPacket`，客户端版本不符直接断开并给出人类可读提示（`multiloader/PacketSet.java:158-186`）——联机多人环境必备。
4. **API 与实现分包 + 版本化包名**：`api/bogeymenu/v0/`（`BogeyMenuManager` 接口 + `INSTANCE = new BogeyMenuManagerImpl()`）与 `impl/bogeymenu/v0/` 分离，Javadoc 明确要求外部 mod 用 `BogeyMenuEvents` 或声明 load-after 来规避加载顺序（`api/bogeymenu/v0/BogeyMenuManager.java:30-38`）。
5. **配置迁移内建**：启动时检测旧格式 toml 并整文件重写（`Railways.java:59-72` `migrateConfig`），配合 `DATA_FIXER_VERSION` 形成"配置+存档"双迁移策略。

## 8. 库 / API 说明

非通用库，但对 Create 附属开发者是**最高价值参考**（同为 Create 6.x/1.21.1）：`api/bogeymenu/v0/{BogeyMenuManager, entry/BogeyEntry, entry/CategoryEntry, neoforge/BogeyMenuEvents}` 是转向架菜单扩展点；`multiloader/`（`PacketSet`/`Loader`/`Env`/`PlayerSelection`/`CommonTag(s)`/`PlatformAbstractionHelper`）是可抄的多加载器骨架，接新平台只需补 `*Impl`；`base/data/BuilderTransformers` + `Registrate` 封装了 Create 风格方块/物品注册与 datagen。
