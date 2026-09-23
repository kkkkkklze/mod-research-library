# AllenSeitz/DimDungeons 源码分析报告

## 1. 基本信息

- Mod 名/ID：Dimensional Dungeons / `dimdungeons`；作者 Catastrophe573；version `1.16.4-1.13.1`（gradle `1.13.1`）
- 目标版本与加载器：**Minecraft 1.16.5 + Forge 36.0.1**，`ForgeGradle 3.+`（buildscript + jcenter），mappings `official 1.16.5`，Java 8（`sourceCompatibility = 1.8`）
- 许可证：All rights reserved（`src/main/resources/META-INF/mods.toml`）
- 依赖：仅 Forge（`versionRange=[35,)`）与 Minecraft（`[1.16.4,1.17)`），无第三方前置；有 `META-INF/accesstransformer.cfg`，**无 mixin**
- 快照完整性注意：`src` 下只有 29 个 java + mods.toml（无 assets/structures/loot_tables），且 `dimension/DungeonDimension.java:5,38` 引用了不存在的 `com.catastrophe573.dimdungeons.biome.BiomeProviderDungeon`（快照缺该包）

## 2. 源码规模与包结构

- 29 个 `.java`，**8583 行**。包：`block`(10)、`structure`(5)、`item`(5)、`utils`(3)、`dimension`(3)、根包(3)
- 全部文件按行数：`DungeonConfig.java` 1209、`structure/DungeonBuilderLogic.java` 953、`structure/DungeonPlacementLogicAdvanced.java` 693、`…Debug.java` 646、`block/BlockGoldPortal.java` 576、`…LogicBasic.java` 563、`item/ItemPortalKey.java` 562、`block/BlockPortalKeyhole.java` 558、`item/ItemSecretBell.java` 331、`structure/DungeonBuilderTestShapes.java` 323、`utils/DungeonUtils.java` 241

## 3. 入口与注册

`DimDungeons.java:42` `@Mod("dimdungeons")`，用旧式 `FMLJavaModLoadingContext.get().getModEventBus().addListener(...)` 挂 6 个生命周期回调，`MinecraftForge.EVENT_BUS.register(eventHandler)`（`PlayerDungeonEvents` 单例），`ModLoadingContext.registerConfig` 注册 **SERVER / CLIENT / COMMON 三份 ForgeConfigSpec**（`:72-74`），`RegisterCommandsEvent` → `CommandDimDungeons.register`。注册表用老写法 + `@ObjectHolder`：`block/BlockRegistrar.java`（`RegistryEvent.Register<Block>`，其中 `BlockKeyCharger` 用同一类注册 3 个 id）、`item/ItemRegistrar.java`（含循环注册 8 个 trophy 物品、`ItemGroup` 创造栏）；`DimDungeons.java:155-170` 在 `RegistryEvent.Register<TileEntityType<?>>` 里建 3 个 TE 并**顺手** `Registry.register(Registry.CHUNK_GENERATOR, "dimdungeons:dimdungeons_chunkgen", DungeonChunkGenerator.myCodec)`。

## 4. 核心系统

- **独立地牢维度 + 空生成器**：`dimension/DungeonChunkGenerator.java:30` 继承 `ChunkGenerator`，codec 直接复用 `FlatGenerationSettings.CODEC`（`:32`）；`applyBiomeDecoration/applyCarvers` 全空，只有 `makeBase`（`:153-209`）干活：`isDungeonChunk/isEntranceChunk` 为真的 chunk 铺 0-2 基岩 + 1-50 砂岩（入口 chunk 用黑石），非地牢 chunk 只在 `x%16==0||z%16==0` 处填屏障防掉出世界；布局判定纯靠坐标哈希（`DungeonPlacementLogicBasic.isDungeonChunk:115`）
- **房间布局算法**：`structure/DungeonBuilderLogic.java` 定义 `enum RoomType{ENTRANCE,END,CORNER,HALLWAY,THREEWAY,FOURWAY,LARGE,LARGE_DUMMY,NONE}` 与内部类 `DungeonRoom{structure,rotation,type}`；用 `hasDoorNorth()/hasDoorSouth()`（`:44-...`）把"类型+旋转"映射成门的朝向做连接校验；地牢最大 8x8 chunk，Basic/Advanced/Debug 三套《placement logic》
- **原子式写入 + 结构数据块分发**：`DungeonPlacementLogicBasic.place(ServerWorld, long x, long z, DungeonGenData)`（`:68`）一次写出整个 8x8 区域；`putRoomHere`（`:158`）用 `TemplateManager.get(ResourceLocation)` 取结构 NBT、`template.placeInWorld(...)` 放置，并按 rotation 修正偏移（`:180-200`）；随后遍历 `filterBlocks(...STRUCTURE_BLOCK)`，对 `StructureMode.DATA` 的方块调 `handleDataBlock(name,pos,…)`（`:238`）分发语义：`ReturnPortal`→金传送门 TE、`BackToEntrance`→本地传送器、`FortuneTeller`→发射器抽签、`ChestLoot1/2`→不同战利品表、`LockIt/LockItStoneBrick`→门锁、`spawnEnemyHere`→刷怪（`EntityType` 字符串 + 血量缩放）
- **传送与钥匙**：`dimension/CustomTeleporter.java`、`item/ItemPortalKey.java`（`getDungeonTopLeftX/Z`、warp 坐标存 NBT、`keytype` 模型属性驱动贴图）、`block/BlockGoldPortal.java` + `TileEntityGoldPortal.setDestination(x,y,z,dim)`、`BlockLocalTeleporter` + `TileEntityLocalTeleporter`、`BlockPortalKeyhole/BlockPortalCrown` 组成入口多方块；生成期数据用 `utils/DungeonGenData.java`（keyItem/returnPoint/returnDimension/dungeonTheme）
- **规则与保护**：`DungeonDimension.canMineBlock` 默认 `false`，只白名单门/活板门/按钮/拉杆/箱子/桶/keyhole 与 gravestone、tombstone、shulker 等外来方块；`PlayerDungeonEvents.explosionModify` 把 `ExplosionEvent.Detonate` 的破坏列表裁剪到仅 `cracked_stone_bricks/trapped_chest/tnt`；维度内禁止睡觉、禁止重生点、地图不旋转
- **配置**：`DungeonConfig.java` 把 S/C/Common 三个 `ForgeConfigSpec` 用 `Pair<Config,Spec>` 静态初始化，另用一大片 `public static` 字段做运行时缓存（`:64-102`：logLevel、globalBlockProtection、hardcoreMode、roomsTier1/2 的 `List<List<String>>`、basicEnemySet1/2、dungeonTheme1..99…），`ModConfigEvent` 触发 `refreshClient()/refreshServer()` 重读

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**自定义包（无 network 包，跨维度靠方块 TE + 服务端逻辑）
- 数据驱动：房间池来自配置（结构名列表）+ 结构 NBT 内的 DATA 标记；战利品表用 `ResourceLocation("dimdungeons:chests/chestloot_basic_easy")` 引用；有 `data` runConfig 与 `src/generated/resources` srcDir，但仓库内无 datagen 类
- 配置：三层 ForgeConfigSpec（Server/Client/Common），带 `translation("config.dimdungeons.*")` 本地化键

## 6. Mixin

无。全部改造走 Forge 事件（`BreakEvent`、`ExplosionEvent`、`RightClickBlock`、`LivingEntityUseItemEvent`、`EnderTeleportEvent`、`FillBucketEvent`…）与 `accesstransformer.cfg`。

## 7. 值得学的 5 条做法

1. 用"坐标哈希 + 空 ChunkGenerator"造独立地牢维度：自己决定哪些 chunk 是房间、其余留 void 并只在外围填屏障（`DungeonChunkGenerator.java:153-209`）。
2. 结构 NBT 内嵌 `StructureMode.DATA` 标记 + 字符串分发（`handleDataBlock`），一个结构文件自带刷怪/宝箱/传送门/门锁语义，作者不必写代码就能加房间（`DungeonPlacementLogicBasic.java:238`）。
3. 房间池做成配置里的 `List<List<String>>`（按房间类型分组列结构名），整合包可无损替换地牢内容（`DungeonConfig.java:1066-1086`）。
4. 配置"Spec + 静态缓存字段 + ModConfigEvent refresh"三件套，业务代码直接读静态字段（`DungeonConfig.java:33-102`、`DimDungeons.java:119-130`）。
5. 维度级规则集中处理：`canMineBlock` 白名单 + 爆炸破坏列表裁剪，而不是逐方块写保护逻辑（`DungeonDimension.canMineBlock`、`PlayerDungeonEvents.java:32-60`）。

## 8. 公开 API

非库模组，无对外 API。
