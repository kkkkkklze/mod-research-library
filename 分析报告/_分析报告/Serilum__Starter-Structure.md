# Serilum/Starter-Structure 源码分析

## 1. 基本信息

Starter Structure / `starterstructure`；作者 Rick South（Serilum，命名空间 `com.natamus`）；版本 4.7；目标 MC `26.2`（`gradle.properties:minecraft_version=26.2`）、Java 25；同时构建 Fabric（fabric_api `0.152.1+26.2`）/ Forge `65.0.0` / NeoForge `26.2.0.1-beta`。Gradle：`net.fabricmc.fabric-loom 1.15-SNAPSHOT` + `net.neoforged.moddev 2.0.141` + 自研约定插件 `buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`。许可证 All Rights Reserved（`license.md`，Copyright Natamus 2026）。编译依赖：`com.natamus.collective-ml:collective-common:26.2.0-8.30`（compileOnly）；**Collective 即其 API**（`DuskConfig`、`ParseSchematicFile`、`TaskFunctions`、`WorldFunctions`、`Collective*Events`），且为 required 前置（`neoforge.mods.toml` `versionRange="[8.30,)"`）。

## 2. 规模与包结构

实测 `find . -name '*.java'` = **20 个文件 / 1277 行**。`Common/src/main/java/com/natamus/starterstructure/`：`ModCommon.java`(15)、`config/ConfigHandler.java`(129)、`events/`（`StructureCreationEvents` 55、`StructureProtectionEvents` 107、`StructureSpawnPointEvents` 71）、`mixin/PlayerMixin.java`(22)、`util/`（`Util.java` **385 行，全仓最大**、`Reference.java` 8）。`Fabric/`(2 文件)、`Forge/`(5)、`NeoForge/`(5) 各只放 12~86 行的事件/配置桥。

## 3. 入口与注册

`ModCommon.init()`（`Common/.../ModCommon.java:8`）= `ConfigHandler.initConfig()` + `Util.initDirs()`（建 `config/starterstructure/schematics`、`signdata`）。NeoForge `ModNeoForge.java`：`@Mod(Reference.MOD_ID)`，构造器先 `ShouldLoadCheck.shouldLoad` 早退，再 `ModCommon.init()`，最后在 `FMLLoadCompleteEvent` 中 `NeoForge.EVENT_BUS.register(NeoForge*Events.class)`。Fabric `ModFabric implements ModInitializer` 把同一批事件挂到 Fabric API 与 Collective 桥。**无 DeferredRegister / Registrate，不注册任何游戏对象**，只有事件、配置、mixin——"零注册表 mod"骨架。

## 4. 核心系统

- **出生点结构生成**（`events/StructureCreationEvents.java:16`、`util/Util.java:63`）：监听 `LevelEvent.CreateSpawnPosition`，随机取 `config/starterstructure/schematics` 下 `.schem/.schematic/.nbt`，经 `ParseSchematicFile.getParsedSchematicObject(...)` 解析；按配置跳过 `JigsawBlock/StructureBlock/StructureVoidBlock`；用 `serverLevel.setRespawnData(RespawnData.of(...))` 改写世界出生点；放置包在 `TaskFunctions.enqueueCollectiveServerTask(server, task, 1)` + 嵌套 `minecraftServer.execute` 中，方块与 `placeBlockEntitiesInWorld` 分两批执行。
- **结构保护**（`Util.java:42` `protectedMap`、`:286` `writeProtectedList`、`:309` `readProtectedList`）：生成时收集坐标 → 落盘 `<world>/data/starterstructure/protection/<dim>/blocks.txt`（纯文本 `x,y,z`）→ 维度加载时读回。判定集中在 `StructureProtectionEvents`：`onBlockBreak:21`、`onBlockPlace:38`、`onPistonMove:53`、`onTNTExplode:63`、`onEntityAttack:87`（实体以 `entityTags` 含 `starterstructure.protected` 标记），统一"返回 true = 放行"。
- **精确出生/重生**（`StructureSpawnPointEvents.java`）：先用 `findRespawnPositionAndUseSpawnBlock(..., TeleportTransition.DO_NOTHING)` 判断床/锚可用性，可用则不干预；首次进服判定用 `PlayerFunctions.isJoiningWorldForTheFirstTime(player, MOD_ID, false)`，且仅在距出生点 50 格内才 `teleportTo`。
- **配置**（`config/ConfigHandler.java`）：继承 Collective `DuskConfig`，字段 `@Entry(min,max)` + `configMetaData` 注释 map，`DuskConfig.init(NAME, MOD_ID, Class)` 生成界面；Fabric/Forge/NeoForge 各有 12~19 行 `Integrate*` 适配。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：**无**。datagen：**无**。数据驱动仅存档内 `data/starterstructure/` 的 `blocks.txt` 与 `signdata/`。配置即 4 末条的 DuskConfig。

## 6. Mixin

`Common/src/main/resources/starterstructure.mixins.json`（`compatibilityLevel: JAVA_25`，`defaultRequire: 1`）。唯一类 `mixin/PlayerMixin.java:13`：`@Mixin(value = Player.class, priority = 1001)` + `@Inject(method = "attack", at = @At("HEAD"), cancellable = true)`，服务端玩家攻击实体时调 `StructureProtectionEvents.onEntityAttack`，返回 false 则 `ci.cancel()`。选 mixin 而非事件，因原版无"玩家攻击实体"可取消事件。

## 7. 值得学的 5 条做法

1. 多加载器共用一套源码：约定插件把 `Common` 的 `commonJava`/`commonResources` configuration 直接 `source` 进各 loader 编译（`buildSrc/.../multiloader-loader.gradle`），不复制代码。
2. 公共层返回平台无关语义值，loader 层翻译：`onLevelSpawn` 返回 `InteractionResult.SUCCESS`，NeoForge 侧才 `e.setCanceled(true)`（`neoforge/events/NeoForgeStructureCreationEvents.java`）。
3. 上千方块分帧放置：外层 `TaskFunctions.enqueueCollectiveServerTask(...)` + 内层 `minecraftServer.execute`（`Util.java:126` 附近）。
4. 坐标集合型存档数据用扁平文本持久化：`Util.java:286-307` 写、`:309-340` 读，零序列化框架。
5. 配置屏按加载器拆 15 行小适配类，主逻辑零平台判断。

## 8. 公开 API / 扩展点

非库/前置 mod，无对外 API 包；反向依赖明确——它是 Collective 的消费者，可作为接入 Collective（DuskConfig / ParseSchematicFile / Collective 事件桥）的参考样例。
