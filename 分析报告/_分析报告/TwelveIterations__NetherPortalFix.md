# TwelveIterations/NetherPortalFix 源码分析报告

> 本报告基于本地克隆分支 `26.2`（最后提交 2026-09-08，`094a1cd`），目标 MC 26.2 / NeoForge 26.2.0.0-beta，Java 25。极小体量的多加载器 mod，是"Balm 抽象 + MixinExtras"路线的范本；逻辑本身（返回门记录）与 1.20.1/1.21.1 版本基本一致，只是原版 API 名称随版本变化。

## 1. 基本信息

- Mod 名：NetherPortalFix；mod_id：`netherportalfix`；作者：BlayTheNinth（TwelveIterations）；许可证 **All Rights Reserved**（`gradle.properties: license=All Rights Reserved`），源码公开但不可再分发 —— 参考写法可以，别抄代码。
- 版本：`version = 26.2.0.1`（与 MC 版本对齐的版本号方案）；`mod_name=NetherPortalFix`，`include_fabric=true` / `include_neoforge=true` / `include_forge=false`（仓库里有 `forge/` 模块，但当前构建不含它）。
- 目标与依赖（`gradle/libs.versions.toml`）：`minecraft = "26.2"`、`neoForge = "26.2.0.0-beta"`、`forge = "63.0.2"`、`fabricApi = "0.152.1+26.2"`、`fabricLoader = "0.19.3"`、**`balm = "26.2.0.1"`（硬依赖，见 `neoforge.mods.toml` 的 `modId="balm" type="required"`）**；`java_version = 25`。
- Gradle：自建 `build-logic`（groovy 插件 `multiloader-common` / `multiloader-loader`）+ `net.neoforged.moddev` 2.0.141（NeoForge/common）、`net.fabricmc.fabric-loom` 1.14-SNAPSHOT（Fabric）、MixinGradle 0.7-SNAPSHOT、`net.darkhax.curseforgegradle` 1.1.26、`com.modrinth.minotaur`；MixinExtras `0.3.6` 在 common 里是 `compileOnly(annotationProcessor(...))`，forge 模块额外 `jarJar` 内嵌。
- 谁是它的 API：**Balm**（`net.blay09.mods.balm.*`）提供跨平台事件、注册器、persistent data、网络开关；本 mod 自身几乎不碰加载器 API。

## 2. 源码规模与包结构

实测：14 个 `.java`，293 行（全部逻辑仅 4 个实体类 + 2 个 mixin）。

- `common/src/main/java/net/blay09/mods/netherportalfix`：`NetherPortalFix.java`、`ReturnPortal.java`、`ReturnPortalManager.java`（核心）；`mixin/LivingEntityAccessor.java`、`mixin/NetherPortalBlockMixin.java`、`package-info.java`(2)。
- `fabric/...`：`FabricNetherPortalFix.java`（ModInitializer）。
- `forge/...`：`ForgeNetherPortalFix.java`。
- `neoforge/...`：`NeoForgeNetherPortalFix.java`（18 行）、`package-info.java`(2)。
- 最大文件即上面三个核心类（均 <100 行）；无客户端专有代码。

## 3. 入口与注册

平台入口只有一行实质代码，统一回调 common 的 `initialize(BalmRegistrars)`：

```java
// neoforge/.../NeoForgeNetherPortalFix.java
@Mod(NetherPortalFix.MOD_ID)
public class NeoForgeNetherPortalFix {
    public NeoForgeNetherPortalFix(ModContainer modContainer, IEventBus modEventBus) {
        final var context = new NeoForgeLoadContext(modContainer, modEventBus);
        Balm.initializeMod(NetherPortalFix.MOD_ID, context, NetherPortalFix::initialize);
    }
}
```

common 侧 `NetherPortalFix.initialize(BalmRegistrars registrars)`：`Balm.networking().allowServerOnly(MOD_ID)`（纯服务端 mod 允许客户端不装），然后注册 `ServerPlayerCallback.DimensionChange.EVENT` 回调。**没有注册任何方块/物品/实体** —— 该 mod 完全靠事件 + mixin。Fabric 侧入口是 `FabricNetherPortalFix implements ModInitializer`，用 `FabricLoadContext.INSTANCE`；`fabric.mod.json` 在本次克隆的工作区缺失（`git ls-files` 中有记录，疑似克隆裁剪）。

## 4. 核心系统

1. **返回门记录（事件驱动）**：`NetherPortalFix.initialize`（`common/.../NetherPortalFix.java:19`）只在 `主世界 ↔ 下界` 的维度切换时工作（其它维度直接 `return`）；用 `((LivingEntityAccessor) player).getLastPos()` 取传送**前**坐标（为 null 说明刚出生，跳过）；`ReturnPortalManager.findPortalAt(player, fromDim, lastPos)` 判定玩家原本是否站在门里；是则 `storeReturnPortal(player, toDim, player.blockPosition(), fromPortal)`。全程用 `logger.debug` 输出跳过原因（可排查性很好）。
2. **数据存储**：`ReturnPortalManager`（`common/.../ReturnPortalManager.java`）把返回门列表塞进**玩家 persistent data**（`Balm.hooks().getPersistentData(entity)`），不新建 SavedData、不发网络包。NBT 结构：list `ReturnPortalList`，每项 `UID`（`UUIDUtil.CODEC`）、`FromDim`（`ResourceKey.identifier()` 字符串）、`FromPos` / `ToPos`（`BlockPos.asLong()`，即压缩 long）。查找条件：`FromDim` 相等 **且** `portalTrigger.distSqr(fromPos) <= MAX_PORTAL_DISTANCE_SQ`（=16，即 4 格内）；命中后构造 `record ReturnPortal(UUID uid, BlockPos pos)`。`storeReturnPortal` 先删同位置旧记录再写入；`removeReturnPortal` 按 UID 遍历匹配删除（注释里自认"不校验 toDim 但重叠概率极低"）。
3. **传送目标改写**：`mixin/NetherPortalBlockMixin.java` 用 MixinExtras 的 `@ModifyExpressionValue` 挂在 `NetherPortalBlock#getExitPortal(...)` 里对 `PortalForcer#findClosestPortalPosition(...)` 的调用点上，拿到原版 `Optional<BlockPos>` 结果后：找到记录的门 → 若该坐标仍是 `Blocks.NETHER_PORTAL` 则返回 `Optional.of(returnPortal.pos())`（强制回到原门），否则 log 并返回 `original`（回退原版就近搜索）。
4. **坐标判定复用原版搜索**：`findPortalAt` 不自己扫方块，而是拿 `ServerLevel.getPortalForcer().findClosestPortalPosition(pos, false, worldBorder)` 的 `Optional` 是否非空来判断"玩家在门里"，零自定义区块扫描开销。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义 payload；只用 `Balm.networking().allowServerOnly(MOD_ID)` 声明服务端 mod 的版本检查豁免（NeoForge 侧等价于 `displayTest="NONE"`，见 `neoforge.mods.toml`；Forge 侧用 `context.registerDisplayTest(IExtensionPoint.DisplayTest.IGNORE_ALL_VERSION)`）。
- 数据驱动 / 配置 / datagen：**均无**。数据全部挂玩家 persistent data。

## 6. Mixin

- 配置：`common/src/main/resources/netherportalfix.mixins.json`（`package net.blay09.mods.netherportalfix.mixin`、`required: true`、`minVersion 0.8`、`compatibilityLevel: JAVA_17`、`injectors.defaultRequire: 1`），数组 `["LivingEntityAccessor", "NetherPortalBlockMixin"]`；另有 `neoforge` / `fabric` 各自一份**空壳** mixins.json（`netherportalfix.neoforge.mixins.json`、`netherportalfix.fabric.mixins.json`），neoforge.mods.toml 里两份都注册（平台留白）。
- 代表 hook：
  - `LivingEntityAccessor`：`@Mixin(LivingEntity.class)` + `@Accessor @Nullable BlockPos getLastPos()`（读传送前位置的关键）。
  - `NetherPortalBlockMixin`：`@ModifyExpressionValue(method = "getExitPortal(...)", at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/portal/PortalForcer;findClosestPortalPosition(...)Ljava/util/Optional;"))`；注入方法签名只保留需要的参数 `(Optional<BlockPos> original, ServerLevel level, Entity entity)` —— MixinExtras 允许裁剪未使用参数。

## 7. 值得学的 5 条具体做法

1. **平台入口 18 行 + Balm 抽象**：common 模块零加载器 import（`common/dependencies.gradle` 只有 `balm-common`），平台差异全部由 Balm 的 `*LoadContext` 吸收（`neoforge/.../NeoForgeNetherPortalFix.java`）。
2. **用 `@ModifyExpressionValue` 改返回值**：比 `@Redirect`/`@Overwrite` 兼容性好且不影响其它注入（`mixin/NetherPortalBlockMixin.java:24`），配 MixinExtras 才能裁参数。
3. **持久数据挂玩家 NBT，而不是 SavedData**：`Balm.hooks().getPersistentData(entity)`（`ReturnPortalManager.java:44`），无生命周期/同步成本 —— 适合"每个玩家一份的小状态"。
4. **坐标匹配用距离平方阈值 + 维度键双条件**：`MAX_PORTAL_DISTANCE_SQ = 16` + `entryFromDim == fromDim`，避免精确坐标匹配失败（`ReturnPortalManager.java:68`）。
5. **整个仓库强制 null 安全**：build-logic 提供 `generateNullMarkedPackageInfos` 任务，为每个包自动生成 `@NullMarked` 的 `package-info.java`（`build-logic/src/main/groovy/multiloader-common.gradle:6`），可直接抄到自己的多加载器工程。

## 8. 库/API 相关

非库模组，无对外 API。其"平台层"完全外包给 Balm（`net.blay09.mods.balm.*`）；若要复用此结构，需要先按 Balm 的 `initializeMod(modId, LoadContext, Consumer<BalmRegistrars>)` 约定接入。
