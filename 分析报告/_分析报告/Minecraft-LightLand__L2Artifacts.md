# Minecraft-LightLand / L2Artifacts 源码分析

## 1. 基本信息

- Mod 名：L2 Artifacts；mod_id `l2artifacts`（`src/main/resources/META-INF/mods.toml:5`）；作者 `lcy0x1 and LightLand team`；credits "Thanks to GenshinImpact for ideas"
- 目标环境：MC **1.20.1** + Forge **47.1.3**，Java 17（`gradle.properties`）；mod 版本 2.4.28
- 构建：ForgeGradle `[6.0,6.2)` + MixinGradle + `librarian.forgegradle`（parchment）+ **jarJar 开启**（`gradle.properties: lljij = true`，因此产出 fat `l2artifacts-x.jar` 与 `-slim.jar` 两种）+ curseforgegradle / minotaur 发布（`build.gradle:16-30, 123-138`）
- 许可证：LGPL v2.1（mods.toml:3）
- 依赖（`build.gradle:141-190`）：`l2library 2.4.24-slim`、`l2serial 1.2.2`、`l2tabs 0.3.1`、`l2screentracker 0.1.4`、`l2complements 2.4.34-slim`、`l2hostility 2.4.29-slim`；jarJar 内嵌 `l2itemselector 0.1.8` 与 `l2damagetracker 0.3.7`；MixinExtras `0.2.0-beta.8`；Registrate `MC1.20-1.3.11`；Curios、JEI；runtime 里跑遍同系列（l2weaponry/l2archery/l2backpack/modulargolems）。`libs/` 下放全部同名 jar 走 flatDir

## 2. 源码规模与包结构

`src/main` **225 个 .java / 11740 行**（含 test 共 228）。包：`content/{client/{select,tab,tooltip}, config, core, effects/{attribute,core,persistent,v1..v5}, misc, mobeffects, search/{augment,common,dissolve,filter,recycle,shape,sort,tabs,token,upgrade}, swap, upgrades}`、`events`、`init/{data/{loot,slot}, registrate/{entries,items}}`、`network`、`compat`。

最大文件：`content/core/ArtifactSet.java`(238)、`init/data/ConfigGen.java`(216)、`content/search/shape/ShapeMenu.java`(207)、`search/augment/AugmentMenuScreen.java`(204)、`search/common/StackedScreen.java`(202)、`init/registrate/items/LAItem4.java`(183)、`LAItem5.java`(178)。

## 3. 入口与注册

`init/L2Artifacts.java:31` `@Mod(MODID)` + `@Mod.EventBusSubscriber(bus=MOD)`, 第 37 行 `public static final ArtifactRegistrate REGISTRATE = new ArtifactRegistrate();` —— **子类化 L2Library 的 L2Registrate 扩展注册体系**，构造里按序 `ArtifactTypeRegistry / ArtifactItems / ArtifactMenuRegistry / ArtifactEffects / ArtifactConfig.init / NetworkManager.register()`，并挂 datagen（`ProviderType.LANG/RECIPE/LOOT`）。跨 mod 钩子也在此注册：`SelectionRegistry.register(-5000, ArtifactSel.INSTANCE)`、`AttackEventHandler.register(3000, new ArtifactAttackListener())`（`init/L2Artifacts.java:52-53`）。

自定义注册表：`init/registrate/ArtifactTypeRegistry.java:20-24` 用 `newRegistry` 建 `slot / set / set_effect / linear` 四个注册表，套装与线性函数都是**注册对象**而非硬编码。

## 4. 核心系统

1. **SetBuilder 连锁注册**（`init/registrate/entries/SetBuilder.java:61-85`，`ArtifactRegistrate.java:28-35`）：`regSet(id,...).setSlots(...).regItems().buildConfig(...)` 的 builder 链，`regItems()` 按 `slots × (min_rank..max_rank)` 矩阵一次性生成物品，并自动打上 `curios:artifact_<slot>`、`rank_<r>`、`artifact` 四个 tag + 生成双层贴图模型 + 语言键，最终产出 `SetEntry` 同时写入 `REGISTRATE.SET_MAP/SET_LIST`。
2. **套装计数与档位**（`content/core/ArtifactSet.java:64-101`）：`getCountAndIndex` 查询 Curios 库存，按 `rank[]` 累加后 `remapRanks` 得出"几件套解锁到第几档"，`SetContext(count, ranks, current_index)` 驱动被动效果。
3. **效果树**：`content/effects/` 按版本分裂 v1..v5 + `attribute/persistent`，基类 `SetEffect` 注册进 `set_effect` 注册表；`SetEffectBuilder` 由 `ArtifactRegistrate.setEffect()` 提供。
4. **搜索/合成容器族**（`content/search/*`）：9 个子包（filter/augment/dissolve/recycle/shape/sort/upgrade/tabs/token），菜单用 `l2screentracker` 的 `ScreenTracker` + `SlotClickHandler` 打开（`events/ArtifactSlotClickListener.java:32-40`），标签页用 `l2tabs`，选择界面用 `l2itemselector`。
5. **战利品注入**：`init/data/loot/` 的 `ArtifactGLMProvider` + `ArtifactLootModifier` / `AddLootTableModifier` 通过 Forge GlobalLootModifier 序列化器（`ArtifactTypeRegistry.java:32-36`）在数据包层加掉落。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络仍复用 L2Library 的 `PacketHandlerWithConfig`（`network/NetworkManager.java:15-19`），构造函数变体里额外注册两个自定义包 `ChooseArtifactToServer`、`SetFilterToServer`（PLAY_TO_SERVER），并用 `ConfigTypeEntry` 声明 4 种配置：`artifact_sets / slot_stats / stat_types / linear`。
- 服务端→客户端的效果同步用 l2library `EffectSyncEvents.TRACKED.add(...)`（`init/L2Artifacts.java:59-60`）。
- 配置：`init/data/ArtifactConfig.java`（ForgeConfigSpec，如 `COMMON.maxRank`）。
- datagen：`ConfigGen`(216 行，属性/技能键值)、`SlotGen`、`RecipeGen`、`LangData`、`ArtifactTagGen`、`ArtifactGLMProvider`、`PatchouliLang`；对 l2complements 的 tag 生成做 `ModList.get().isLoaded` 条件判断（`init/L2Artifacts.java:65-66`）。

## 6. Mixin

`src/main/resources/l2artifacts.mixins.json` 中 `mixins` 与 `client` **均为空数组** —— 本 mod 无自有 mixin；MixinExtras 通过 `jarJar`/`implementation` 提供给依赖链使用（`build.gradle:184-190`）。

## 7. 值得学的 5 条做法

1. **把注册表做成数据类型**：套装/槽位/线性函数/效果全部是 `RegistryInstance`，附属可用数据包或注册扩展 —— `init/registrate/ArtifactTypeRegistry.java:20-24`。
2. **builder 链内一次性生成矩阵资源**：`SetBuilder.regItems()` 里 item+tag+model+lang 全自动，新增套装只写一行 `regSet(...)`。
3. **自定义 Registrate builder 接管注册副作用**：`ArtifactRegistrate` 重写 `entry()/regSet()`，把 `SET_MAP/LINEAR_LIST` 缓存与注册耦合在一起，避免"注册完再手动收集"的顺序问题（`init/registrate/entries/ArtifactRegistrate.java:24-36`）。
4. **jarJar 极简发行**：`lljij=true` 时 `jar` 改 classifier `slim`，fat 包内嵌 l2itemselector/l2damagetracker，用户只装一个 jar —— `build.gradle:123-138`。
5. **跨 mod 排序钩子统一登记**：`SelectionRegistry.register(优先级, impl)`、`AttackEventHandler.register(3000, listener)`，用数字优先级仲裁多 mod 冲突。

## 8. 面向外部 mod 的扩展点

内容 mod，但示范了标准的 L2Library 接入姿势：`ArtifactRegistrate extends L2Registrate` + `newRegistry` 建自定义注册表 + `addDataGenerator(ProviderType)` 挂 datagen + `PacketHandlerWithConfig` 做配置同步；发布元数据里把 l2library/curios/attributefix 标 required，l2-complements/modulargolems/patchouli 标 optional（`build.gradle:235-241`、`build.gradle:255-260`）。
