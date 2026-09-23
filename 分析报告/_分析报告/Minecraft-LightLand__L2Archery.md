# Minecraft-LightLand / L2Archery 源码分析

## 1. 基本信息

- Mod 名：L2 Archery；mod_id：`l2archery`（`src/main/resources/META-INF/mods.toml:5`）；作者 `lcy0x1 and LightLand team`
- 目标环境：MC **1.19.2** + Forge **43.2.0**（`gradle.properties`），Java 17；mod 版本 1.2.5
- 构建：ForgeGradle `5.1.+` + MixinGradle `0.7-SNAPSHOT` + Mixin `0.8.5`（`build.gradle:1-18`），无 jarJar
- 许可证：LGPL v2.1（mods.toml:3）
- 依赖（关键）：`implementation` **l2library 1.9.1**、**l2complements 1.2.3**、modulargolems 1.7.7（mods.toml 中为 optional）、JEI、Curios；`runtimeOnly` l2artifacts 1.5.0、l2backpack 1.7.0。另有 `flatDir { dirs 'libs' }` 放同名 jar（`libs/l2library-1.9.1.jar` 等）——**该系列统一以本地 jar + publish 到 maven 的方式复用 L2Library**，不是子项目聚合

## 2. 源码规模与包结构

`src/main` 下 **95 个 .java / 4887 行**（含 test 共 109 文件 5917 行）。包（`dev.xkmc.l2archery`）：

`content/{client, config, controller, crafting, effects, enchantment, energy, entity, explosion, item, stats, upgrade}`、`content/feature/{arrow, bow, core, types}`、`events`、`init/{data, registrate}`、`mixin`、`compat`。

最大文件：`content/item/GenericBowItem.java`(416)、`init/data/RecipeGen.java`(410)、`init/registrate/ArcheryItems.java`(266)、`content/upgrade/BowUpgradeBuilder.java`(187)、`content/config/BowArrowStatConfig.java`(158)、`content/entity/GenericArrowEntity.java`(147)、`content/feature/FeatureList.java`(143)。

## 3. 入口与注册

`init/L2Archery.java:26` `@Mod("l2archery")`，第 32 行 `public static final L2Registrate REGISTRATE = new L2Registrate(MODID);` —— 直接复用 L2Library 的 registrate 封装（`dev.xkmc.l2library.base.L2Registrate`，其内部 repack 了 Registrate）。构造函数中 `registerRegistrates()` 依次调用 `ArcheryRegister/ArcheryItems/ArcheryEffects/NetworkManager.register()`，datagen 也用 L2Library 的 ProviderType：

```java
REGISTRATE.addDataGenerator(ProviderType.RECIPE, RecipeGen::genRecipe);
REGISTRATE.addDataGenerator(ProviderType.LANG, LangData::genLang);
REGISTRATE.addDataGenerator(ProviderType.ADVANCEMENT, AdvGen::genAdvancements);
```
（`init/L2Archery.java:40-42`）

自定义注册表用 `L2Registrate.newRegistry`：`ArcheryRegister.java:19-22` 建 `stat_type`(BowArrowStatType) 与 `upgrade`(Upgrade) 两个注册表，物品/实体/配方序列化器走 registrate builder（`ArcheryRegister.java:31-44`）。

## 4. 核心系统

1. **组合式 Feature 系统**（`content/feature/FeatureList.java`）：一张表按 `Stage.INHERENT/UPGRADE/ENCHANT` 分组，`add()` 时按接口分桶缓存 `pull/shot/hit/flight`；`canMerge(bow,arrow)` 用 `Map<Class<?>,BowArrowFeature>` + `allowDuplicate()` 判冲突，`merge()` 固定注入 `DefaultShootFeature.INSTANCE`。工具提示按阶段着色（GREEN/GOLD/LIGHT_PURPLE）。
2. **弓箭数值配置**（`content/config/BowArrowStatConfig.java`）：`@SerialClass` + `@ConfigCollect(CollectType.MAP_COLLECT)` 的 `HashMap<ResourceLocation, HashMap<BowArrowStatType,Double>>`，datagen 写入、运行时按 id 查询，可被其他数据包/附属叠加合并。
3. **数据驱动弓本体**：`GenericBowItem`(416 行) 以 NBT 存 `upgrades`(ListTag)，配合 `content/upgrade/Upgrade.java`（`extends NamedEntry<Upgrade>`，注册于自定义注册表）与 `BowUpgradeBuilder` 组织"弓+箭+升级"三合一数值。
4. **能量弓**：`content/energy/IFluxItem.java` 非自建能量系统，而是包装 `ForgeCapabilities.ENERGY`（`IEnergyContainerItem`），客户端用 `BowFluxBarRenderer` 通过 `RegisterItemDecorationsEvent` 画能量条（`init/L2ArcheryClient.java:42-45`）。
5. **实体与客户端表现**：`GenericArrowEntity` 单实体承载所有箭型；`ItemProperties.register` 为每把弓注册 `pull`/`pulling` 属性（`init/L2ArcheryClient.java:34-38`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络全部复用 L2Library：`init/NetworkManager.java` 定义 `enum NetworkManager { STATS }` + `PacketHandlerWithConfig(new ResourceLocation(MODID,"main"), 1, "archery_config")`，`HANDLER.addCachedConfig(STATS.getID(), new ConfigMerger<>(BowArrowStatConfig.class))`——配置即包，自动同步与合并。
- 序列化用 `dev.xkmc.l2library.serial.SerialClass/SerialField`（l2serial 的 repack）。
- datagen：`init/data/ConfigGen`、`RecipeGen`、`LangData`、`AdvGen`、`TagGen`（后者含 `TAG_ENERGY`）。
- 配置：`init/data/ArcheryConfig.java` 用原生 `ForgeConfigSpec` 分 CLIENT/COMMON。

## 6. Mixin

`src/main/resources/l2archery.mixins.json`：`package dev.xkmc.l2archery.mixin`，`mixins: []`，`client: ["ItemInHandRendererMixin"]`，`compatibilityLevel JAVA_16`，`defaultRequire: 1`。
`mixin/ItemInHandRendererMixin.java:37` `@Inject(at=@At("HEAD"), method="renderArmWithItem", cancellable=true)`，对 `GenericBowItem` 完全重写第一人称拉弓位移/缩放，末尾 `ci.cancel()`。

## 7. 值得学的 5 条做法

1. **"配置即包"的同步**：把数值表做成 `BaseConfig` 子类交给 `PacketHandlerWithConfig`，注册表只写一行 `addCachedConfig`，序列化/下发/合并全部由 L2Library 负责 —— `init/NetworkManager.java:18, 27`。
2. **Feature 冲突用类名做唯一键**：`allowDuplicate()` 决定同类 feature 能否共存，避免属性互相覆盖 —— `content/feature/FeatureList.java:63-66`。
3. **接口分桶 + 阶段分组**：同一批 feature 同时维护 `all/inherent/upgrade/enchant` 与四个行为接口列表，运行时只遍历需要的那一桶。
4. **单实体 + NBT 变体**：一个 `GenericArrowEntity` 承担全部箭种，靠 datagen 配置表区分，减少注册量。
5. **datagen 只挂 ProviderType**：`REGISTRATE.addDataGenerator(ProviderType.X, ...)` 一行接入 L2Library 数据生成管线（`init/L2Archery.java:40-42`）。

## 8. 面向外部 mod 的扩展点

内容 mod。可复用点：`ArcheryRegister.STAT_TYPE` / `UPGRADE` 两个公开 `RegistryInstance` 允许附属注册新的弓箭属性与升级；`compat/GolemCompat.java` 演示了 `ModList.get().isLoaded(...)` 条件下的兼容注册。
