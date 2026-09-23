# TelepathicGrunt/StructureLayoutOptimizer 源码分析报告

## 1. 基本信息
- Mod 名：Structure Layout Optimizer（描述"An attempt at optimizing jigsaw generation"）；mod_id：`structure_layout_optimizer`；作者 TelepathicGrunt；版本 1.1.4；许可证 MIT。
- 目标：MC **26.1**（`gradle.properties`），NeoForge 26.1.0.1-beta，Fabric Loader 0.18.4 / Fabric API 0.144.0+26.1；**Java 25**（`build.gradle: javaVersion = 25`，mixin `compatibilityLevel: JAVA_${java_version}`）。
- Gradle 插件：`net.neoforged.moddev 2.0.141`（neoforge 模块）、`net.fabricmc.fabric-loom 1.15-SNAPSHOT` + **`net.fabricmc.fabric-loom-companion 1.14.4`**（fabric 模块）、`me.modmuss50.mod-publish-plugin`；common/fabric/neoforge 三模块，无 architectury。
- 编译依赖：`org.spongepowered:mixin 0.15.4+mixin.0.8.7`、`mixinextras 0.4.1`、ASM 9.7；运行期**必需依赖 `resourcefulconfig`**（`neoforge.mods.toml` 里 `type="required"`）。

## 2. 源码规模与包结构
实测 20 个 `.java`，1164 行（极小但技术密度极高）。包（`common/src/main/java/telepathicgrunt/structure_layout_optimizer/`）：`mixins/` 6、`utils/` 7、`services/` 1、根 2（`StructureLayoutOptimizerMod`/`SloConfig`）；`fabric/.../fabric/{entrypoints,services}`、`neoforge/.../neoforge/{entrypoints,services}` 各 2。
最大文件：`utils/PalettedStructureBlockInfoList.java` 272（+`PalettedStructureBlockInfoListIterator` 75）、`utils/BoxOctree.java` 183、`mixins/JigsawPlacementPlacerMixin.java` 175、`utils/StructureTemplateOptimizer.java` 115、`utils/GeneralUtils.java` 91。
快照说明：本仓库快照只含 1 个 mixins.json 与 `META-INF/neoforge.mods.toml`，未见 `fabric.mod.json` 与 `assets/`、`data/`（快照缺失，未确认）。

## 3. 入口与注册
无任何游戏内容注册（纯优化 mod）。唯一入口是 `StructureLayoutOptimizerMod.init()`（`StructureLayoutOptimizerMod.java:12`）：仅 `CONFIGURATOR.register(SloConfig.class)`（ResourcefulConfig 的 `Configurator`）。平台入口：`fabric/.../fabric/entrypoints/Main.java`（`ModInitializer`）、`neoforge/.../neoforge/entrypoints/Main.java`（`@Mod` + `ModContainer` 参数构造器），都只调 `init()`。
平台差异用 **ServiceLoader**：`services/PlatformService.java` 的 `INSTANCE = GeneralUtils.loadService(PlatformService.class)`，实现类 `fabric/services/FabricPlatformService`、`neoforge/services/NeoPlatformService`（当前均为空实现，是留好的扩展点）。

## 4. 核心系统
1. **用八叉树替换 VoxelShape 碰撞检测**：`utils/TrojanVoxelShape.java`（继承 `VoxelShape`，构造传 0 大小的 `BitSetDiscreteVoxelShape`，`getCoords()` 返回 `null` 阻断原版消费）+ `utils/BoxOctree.java`（`subdivideThreshold=10`、`maximumDepth=3`，8 个子节点按 AABB 半切，提供 `boundaryContains/withinAnyBox/withinBoundsButNotIntersectingChildren`）。`JigsawPlacementMixin` 在 `lambda$addPieces$2` 把 `Shapes.join(...)` 的返回值换成 `TrojanVoxelShape`，从此原版拼接巨型 VoxelShape 的开销被 O(1) 的盒查询取代。
2. **Jigsaw 连接判定微优化**：`JigsawPlacementPlacerMixin` 里 `@Redirect` `JigsawBlock.canAttach` → `GeneralUtils.canJigsawsAttach()`，只读 `ORIENTATION` 状态 + `getStringMicroOptimised(tag,"target"/"name"/"joint")`（用 `tag.get(key) instanceof StringTag(String value)` 模式匹配，避免 `getString` 的默认值与异常开销）；`isRollableJoint` 内联了原版 joint 逻辑。
3. **提前剪枝**：`@ModifyExpressionValue` 拦截 `tryPlacingChildren` 中 `getShuffledJigsawBlocks(..., ordinal=1)`，若 `childrenFree` 已是 `TrojanVoxelShape` 且候选 piece 为 `Projection.RIGID` 且目标点越界/已在盒内，直接返回空 List 跳过整段放置逻辑；`WrapOperation` 把 `Shapes.joinIsNotEmpty` 换成 `!octree.withinBoundsButNotIntersectingChildren(AABB.of(pieceBounds).deflate(0.25D))`（deflate 0.25 是为了与原版行为对齐）。
4. **Palette 位压缩存储**：`utils/PalettedStructureBlockInfoList.java`（注释声明源自 Glacier）——把 `List<StructureBlockInfo>` 压成 `long[]`，`bits(maxX/maxY/maxZ/states-1/tags-1)` 逐字段定位宽，`Entry.compress()` 左移拼接，`64/bitsPerEntry` 条挤进一个 long，`bitsPerEntry>64` 直接抛异常；读操作靠 `WeakReference` 缓存的还原列表，写操作（`add/set/clear`）抛 `UnsupportedOperationException` 并附带"请找 SLO 作者排查兼容问题"的定制文案。装配点：`StructureTemplatePaletteMixin` 在 `StructureTemplate.Palette.<init>` 的 TAIL 用 `@Shadow @Mutable @Final` 直接换掉 `blocks` 字段。
5. **只处理包围盒内的方块**：`StructureTemplateMixin` 把 `Palette.blocks()` 重定向到 `StructureTemplateOptimizer.getStructureBlockInfosInBounds()`：先反射检查 processor 是否覆写 `finalizeProcessing`（结果缓存于 `Object2BooleanMaps.synchronize(Object2BooleanOpenHashMap)`），若有则放弃优化；否则逐块做 `mirror/rotation/pivot` 变换 + `move(offset)`，只保留 `boundingBox.isInside()` 的方块；**关键边界处理**：结果为空但原列表非空时塞回第一个元素，否则 `placeInWorld` 返回 false 会让该 piece 从 structure start 中被移除。
6. **池去重（可选、破坏种子一致性）**：`SloConfig.deduplicateShuffledTemplatePoolElementList` 开时用 `LinkedHashSet` 去重 `getShuffledTemplates()`；关闭时改用 `utils/TrojanArrayList` 记录已遍历 piece，在 `Rotation.getShuffled` 处短路（并通过预调用 `getShuffledJigsawBlocks(..., BlockPos.ZERO, rotation, random)` **重放被跳过的随机数消耗**以保持与原版随机序列一致）。
7. **选择优先级洗牌**：`SinglePoolElementMixin` 把 `Util.shuffle` + `sortBySelectionPriority` 两个调用替换为 `GeneralUtils.shuffleAndPrioritize()`（第二个 Redirect 直接空实现）：用 `Int2ObjectArrayMap` 按 `selection_priority` 分桶 → 桶内 `Util.shuffle` → 键降序拼接，一趟完成"洗牌+排序"。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无。数据驱动：无（无 reload listener、无自定义注册表）。
- 配置：`SloConfig.java` 用 **ResourcefulConfig 注解式配置**（`@Config(MODID)`、`@ConfigInfo(title/description/icon/links)`、`@Comment(textBlock, translation)`、`@ConfigEntry(id, translation)`），仅一个 `public static boolean deduplicateShuffledTemplatePoolElementList = false`，由 `Configurator.register` 载入。
- datagen：无。

## 6. Mixin
配置：`common/src/main/resources/structure_layout_optimizer.mixins.json`（6 个 mixin，全在公共段，`defaultRequire: 1`），通过 `neoforge.mods.toml` 的 `[[mixins]] config=...` 登记（fabric 侧配置文件在快照中缺失）：
- `JigsawPlacementMixin` → `JigsawPlacement.lambda$addPieces$2`，`@WrapOperation` 目标 `Shapes.join(VoxelShape,VoxelShape,BooleanOp)`（用 `@Local(name="aabb")`/`@Local(argsOnly=true, ordinal=0)` 取参数）。
- `JigsawPlacementPlacerMixin` → `@Mixin(targets = "...JigsawPlacement$Placer")`，9 处注入均在 `tryPlacingChildren(...)`：2 个 `@Redirect`(`canAttach`、`MutableObject.setValue`×2)、1 个 `@WrapOperation`(`Shapes.joinIsNotEmpty`)、1 个 `@Redirect`(`Shapes.joinUnoptimized`→`Shapes.empty()`)、1 个 `@Redirect`(`StructureTemplatePool.getShuffledTemplates`)、1 个 `@Redirect`(`Lists.newArrayList`)、2 个 `@ModifyExpressionValue`(`getShuffledJigsawBlocks`、`Rotation.getShuffled`)。
- `SinglePoolElementMixin` → `getShuffledJigsawBlocks` 内 `Util.shuffle`、`SinglePoolElement.sortBySelectionPriority`。
- `StructureTemplateMixin` → `placeInWorld` 内 `StructureTemplate$Palette.blocks()`；`StructureTemplatePaletteMixin` → `Palette.<init>` TAIL；`StructureTemplatePoolAccessor` → `@Accessor getRawTemplates()`。

## 7. 值得学的 5 条具体做法
1. **"Trojan 类型"思路替换重型数据结构**：继承原版 `VoxelShape` 但只携带自己的 `BoxOctree`，让 `getCoords()` 返回 null 把原版行为关掉（`utils/TrojanVoxelShape.java:12`）——任何"原版 API 昂贵但调用点不可改"的场景都可借用。
2. **优化前先反射探测兼容性**：`isFinalizeProcessor` 用 `getMethod("finalizeProcessing", ...)` 判断 processor 是否覆写，结果按实例缓存（`Object2BooleanMaps.synchronize`），把"不确定就放弃优化"做成显式分支（`utils/StructureTemplateOptimizer.java:33`）——写性能 mod 时的必备防御。
3. **跳随机调用必须补齐随机数消耗**：`structureLayoutOptimizer$skipDuplicateTemplatePoolElementLists2` 在短路前先跑一遍被跳过的 `getShuffledJigsawBlocks` 以保持 RandomSource 序列一致（`mixins/JigsawPlacementPlacerMixin.java:153`）——所有"优化后结构布局不变"的 mod 都应遵守这条。
4. **位压缩 List 做内存优化的完整实现范式**：`PalettedStructureBlockInfoList`（bits-per-field + `long[]` 打包 + `WeakReference` 惰性还原 + 写操作抛定制异常文案），可直接参照用于任何"大量同质记录"的存贮。
5. **ServiceLoader 替代 architectury `@ExpectPlatform`**：`PlatformService.INSTANCE = loadService(PlatformService.class)`，平台实现类零注解、可直接被 mixin 或测试替换（`services/PlatformService.java:7`、`utils/GeneralUtils.java:21`）——三模块 mod 更轻的跨平台方案。
