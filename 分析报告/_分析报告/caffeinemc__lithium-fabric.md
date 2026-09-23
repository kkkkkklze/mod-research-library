# caffeinemc/lithium-fabric 源码分析报告

## 1. 基本信息
Lithium，mod_id `lithium`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`），作者 2No2Name、JellySquid，LGPL-3.0-only。目标 MC 26.2（根 `build.gradle.kts`：`MINECRAFT_COMPILE_VERSION="26.2"`、`MOD_VERSION="0.25.3"`），NeoForge 26.2.0.0-beta、Fabric Loader 0.19.3、Fabric API 0.152.1+26.2，Java 25。Gradle：Fabric Loom 1.15-SNAPSHOT、mod-publish-plugin、自研 `net.caffeinemc.mixin-config-plugin`（`settings.gradle.kts` 里 `includeBuild("components/mixin-config-plugin")`）。编译依赖仅 Fabric transfer/gametest/registry-sync API + loader，无任何注册框架。

## 2. 规模与包结构
642 个 `.java` / 31,370 行；`common` 599 文件 29,265 行（内含 `api`、`gametest` sourceSet），`fabric` 24、`neoforge` 14、`components` 5；其中 `common/.../mixin` 434 文件 17,427 行。common 一级包：`ai`、`alloc`、`block`、`chunk`、`collections`、`entity`、`gen`、`math`、`hopper`、`shapes`、`tracking`、`util`、`world`、`services`、`config`。最大文件：`HopperBlockEntityMixin.java`(902)、`NearbyPointOfInterestStream.java`(475)、`ItemEntityList.java`(445)、`ServerExplosionMixin.java`(430)、`LithiumEntityCollisions.java`(325)、`LithiumStackList.java`(301)、`PoiManagerMixin.java`(299)、`LithiumConfig.java`(293)。

## 3. 入口与注册
无方块/物品注册，注册面只有三样：mixin 配置、配置规则、平台服务。公共入口 `common/.../common/LithiumMod.java`（只有 `onInitialization(String version)`）；Fabric `fabric/.../LithiumFabricMod.java` `implements ModInitializer`，NeoForge 对应 `LithiumNeoForgeMod`。平台差异走 `common/.../common/services/Services.java` 的 `ServiceLoader.load(clazz)` + 四个接口 `PlatformMixinOverrides / PlatformEntityAccess / PlatformModCompat / PlatformRuntimeInformation`，各接口内写 `INSTANCE = Services.load(X.class)`（`PlatformMixinOverrides.java:9`）。仓库内未见 `META-INF/services/*` 文本文件（未确认）；也无 `fabric.mod.json` 源文件，`fabric/build.gradle.kts:199` 仍对其做 version 替换。

## 4. 核心系统
1. **漏斗/容器**：`mixin/block/hopper/HopperBlockEntityMixin.java:52` 声明 `implements UpdateReceiver, LithiumInventory, InventoryChangeListener, SectionedEntityMovementListener`，用 `insertStackListModCount/extractStackListModCount`（:86）跳过“容器未变”的失败传输；`common/hopper/LithiumStackList.java:16` 继承 `NonNullList<ItemStack>`，增量维护 `occupiedSlots/fullSlots/cachedSignalStrength/cachedComparatorUpdatePattern`。
2. **变更订阅**：`common/util/change_tracking/{ChangePublisher,ChangeSubscriber}.java`，`LithiumStackList` 构造时对每个非空堆 `lithium$subscribe(this, slot)`，替代每 tick 轮询。
3. **实体分组**：`common/entity/EntityClassGroup.java` 用 `BiPredicate<Class,Supplier<EntityType>>` + `Reference2ByteOpenHashMap`（0/1/2/缺省3）缓存判定，写时复制 + volatile 保并发；`mixin/chunk/entity_class_groups/ClassInstanceMultiMapMixin.java:36` 以 `@ModifyVariable` 给原版 `ClassInstanceMultiMap` 挂 `EntityClassGroup → ReferenceLinkedOpenHashSet` 索引并懒建。
4. **POI 搜索**：`common/world/interests/iterator/NearbyPointOfInterestStream.java` + `mixin/ai/poi/PoiManagerMixin.java`、`ai/poi/fast_portals/`。
5. **形状/碰撞**：`mixin/shapes/`（blockstate_cache、optimized_matching、precompute_shape_arrays…）+ `common/entity/LithiumEntityCollisions.java`。
6. **分配削减**：`mixin/alloc/*`、`common/util/collections/HashedReferenceList.java`、`util/tuples`。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络与 datagen：无。配置是重点：`common/.../config/LithiumConfig.java` 从 jar 内 `/assets/lithium/lithium-mixin-config-default.properties` 与 `...-dependencies.properties` 读默认规则与依赖（:28、:41）；规则名即 mixin 包路径，`getEffectiveOptionForMixin()`（:198-221）沿包路径下钻，任一父级禁用即整棵子树禁用（管理员关一大类无需逐条列举）；`applyDependencies()`（:230-244）定点迭代收敛规则依赖；用户文件 `./config/lithium.properties`（:38）。其他 mod 可通过自身元数据键 `lithium:options` 强制开关规则（Fabric：custom value；NeoForge：config element），且“禁用优先于启用”（`Option.java:31-67`）。

## 6. Mixin
配置：`common/src/main/resources/lithium.mixins.json`（`:2-8`：`package net.caffeinemc.mods.lithium.mixin`、`required true`、`JAVA_25`、`mixinextras.minVersion 0.5.3`、`plugin LithiumMixinPlugin`、`defaultRequire 1`），另有 `lithium-fabric.mixins.json`/`lithium-neoforge.mixins.json`（NeoForge 的 `mods.toml` 用两条 `[[mixins]]` 声明）。数量：common 258 条、fabric 6、neoforge 6（`mixin/` 按 ai、alloc、block、chunk、entity、shapes、world 等目录切分）。插件 `common/.../mixin/LithiumMixinPlugin.java:56-111`：把 mixin 类名去前缀后查配置规则，匹配不到即“视为外来 mixin 禁用”，支持 `-Dlithium.test.disable_all_mixins=true` 跑原版对照测试（:18）。访问器：`common/src/main/resources/lithium.accesswidener` + NeoForge `META-INF/accesstransformer.cfg`。

## 7. 值得学的 5 条做法
1. 配置规则以 mixin 包路径为键、父级禁用级联（`LithiumConfig.java:198`）——mixin 多的优化 mod 不必逐条列开关。
2. 用 Gradle 插件生成配置与文档：`components/mixin-config-plugin/` 的 `@MixinConfigOption(enabled,depends,description,nonVanillaBehavior)` 打在 `package-info.java`，`CreateMixinConfigTask` 扫描编译产物生成默认 properties、依赖表与 `lithium-*-mixin-config.md`。
3. 允许他 mod 声明式开关你的优化（元数据 `lithium:options`，`FabricMixinOverrides.java` / `NeoForgeMixinOverrides.java`）——兼容问题从改代码变改元数据。
4. 变更订阅 + modCount 快照替代轮询（`HopperBlockEntityMixin.java:64-86`）——可直接用于 Create 附属的库存/物流逻辑。
5. 给原版集合挂自定义索引（`ClassInstanceMultiMapMixin`），懒建并按需增长，天然与区块实体列表同步。

## 8. 公开 API
`common/src/api/java/net/caffeinemc/mods/lithium/api/inventory/`：`LithiumInventory`、`LithiumDefaultedList`、`LithiumCooldownReceivingInventory`、`LithiumTransferConditionInventory`（`common/build.gradle.kts` 里 `apiJar` 任务并打进主 jar）。这些接口由 mixin 直接实现在原版类上（如 `HopperBlockEntityMixin implements LithiumInventory`），第三方只需 `instanceof` 判断即可接入优化路径，无需注册。平台扩展点即 `common/services/` 的四个 `Platform*` 接口。
