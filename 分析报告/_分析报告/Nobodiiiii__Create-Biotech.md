# Nobodiiiii/Create-Biotech 源码分析报告

## 1. 基本信息

- Mod 名：Create: Biotech（中文：机械动力：生物工艺） / **mod_id：`create_biotech`** / 作者：Nobodiiiii（含内嵌 `com.yision.allay` 悦灵模块） / 版本 1.2.0
- 目标版本：**Minecraft 1.20.1 + Forge 47.1.33**（源码内 `mods.toml` 声明 `[1.20.1,1.21)`，主类是 `net.minecraftforge.fml.common.Mod`）
- Gradle 插件：**`net.neoforged.moddev.legacyforge` 2.0.107**（注意：NeoForge 的 legacyforge 插件跑 Forge，可直接给 NeoForge 1.21.1 迁移项目抄配置）；parchment 2023.09.03；Java 17
- 许可证：MIT（`LICENSE.md` 说明含第三方改编资源，另有 `THIRD_PARTY_NOTICES.md`）
- 编译依赖（`build.gradle:91-113`）：`com.simibubi.create:create-1.20.1:6.0.8-291:slim`（`transitive=false`）、`com.tterrag.registrate:Registrate:MC1.20-1.3.3`、Flywheel 1.0.5（api/impl 分离）、`net.createmod.ponder:Ponder-Forge` 1.0.91、Mixinextras 0.4.1（annotationProcessor 也挂了 mixin processor）。JEI/Jade 为 compileOnly。
- 它把 Create 当 API 用（`CreateBuiltInRegistries`、`MovementBehaviour.REGISTRY`、`IHaveGoggleInformation` 等），本身不是库。

## 2. 源码规模与包结构

实测：`src/main/java` 共 **423 个 .java，61832 行**（`com.nobodiiiii` 371 个 + 内嵌 `com.yision.allay` 52 个）。

主要包（到第 3 层，括号内为该目录直属文件数）：`mixin`(35)、`mixin/client`(24)、`compat/jei`(19)、`ponder/generated/scenes`(15)、`content/*`（28 个功能子包，如 `ghasthotairballoon`15、`experience`15、`shulkerpackager`12、`cardboardbox`12、`spiderassemblytable`10、`powerbelt`10）、`registry`(13)、`client`(9)、`infrastructure`(3)、`foundation`(advancement/gui/item/ponder/render)、`allay/{block,entity,item,logistics,client,config,registry}`。

最大文件：`content/creeperblastchamber/CreeperBlastChamberBlockEntity.java` 3165 行、`ponder/generated/GeneratedPonderSupport.java` 2179 行、`allay/logistics/courier/AllayCourierTask.java` 1305 行、`content/spiderassemblytable/SpiderAssemblyTableBlockEntity.java` 1198 行、`content/slimebelt/transport/SlimeBeltInventory.java` 1165 行。

## 3. 入口与注册

主类 `src/main/java/com/nobodiiiii/createbiotech/CreateBiotech.java`（96 行，很薄），构造器中一行一个注册入口（`CreateBiotech.java:45-64`）：

```java
CBConfigs.register();          CBBlocks.register(modEventBus);
CBItems.register(modEventBus); CBFluids.register(modEventBus);
CBPoiTypes.register(modEventBus); CBCreativeModeTabs.register(modEventBus);
CBBlockEntityTypes.register(modEventBus); CBEntityTypes.register(modEventBus);
CBMenuTypes.register(modEventBus); CBParticleTypes.register(modEventBus);
CBRecipeTypes.register(modEventBus); ButterCatModule.init(modEventBus);
CBPackets.register();
```

- 注册框架是**混合式**：主 mod 用 `DeferredRegister`（`CBBlocks.java:52-53` 为 `DeferredRegister<Block> BLOCKS = DeferredRegister.create(ForgeRegistries.BLOCKS, CreateBiotech.MOD_ID)`）；只有 `content/buttercat` 子模块用 Registrate（`ButterCatModule.REGISTRATE = CreateRegistrate.create(MODID)`，见 `content/buttercat/ButterCatModule.java:25`，全仓库仅 5 个文件出现 Registrate）。`CBItems`/`CBFluids` 等文件即注册表清单，13 个 `CB*` 类构成 `registry` 包。
- 事件分层：`onCommonSetup`（`CreateBiotech.java:73-86`）里往 **Create 的注册表**注入行为，`onRegister(RegisterEvent)`（`:88-91`）里注册机械臂交互点与创造模式下的 `ContraptionType`。
- `asResource(String)`（`:93-95`）是全仓库统一的 ResourceLocation 工厂。

## 4. 核心系统

**A. Create API 扩展点注入（最值得抄的一层）**：`ExploreOpenPipeEffectHandler` 把经验流体接进 Create 的开放管道效果（`content/experience/ExperienceOpenPipeEffectHandler.java:19-22`：`OpenPipeEffectHandler.REGISTRY.register(CBFluids.EXPERIENCE...)`）；`ExplosionProofItemVaultCompat.register()`（`content/explosionproofitemvault/ExplosionProofItemVaultCompat.java:16-22`）用 `MountedItemStorageType.REGISTRY` + `InventoryIdentifier.REGISTRY` 让自研防爆物品保险库被 Create 打包机/物流网络当成原版 vault；`ShulkerPackagerArmInteractions`（`content/shulkerpackager/ShulkerPackagerArmInteractions.java:20-24`）用静态块向 `CreateBuiltInRegistries.ARM_INTERACTION_POINT_TYPE` 注册机械臂交互点。

**B. 自定义 Contraption（实体化机械）**：`registry/CBContraptionTypes.java` 通过 `CreateBuiltInRegistries.CONTRAPTION_TYPE` 注册 `ghast_hot_air_balloon`；`content/ghasthotairballoon` 下 15 个文件实现气球实体、绳索交互（`GhastBalloonRopeShearsInteraction` 注册到 `AllBlocks.ROPE/PULLEY_MAGNET` 的 `MovingInteractionBehaviour.REGISTRY`，`CreateBiotech.java:82-84`）与 `GhastHelmMovementBehaviour`。

**C. SlimeBelt/PowerBelt 传送带系**：`content/powerbelt`、`content/slimebelt`（含 `transport/SlimeBeltInventory` 1165 行）、`content/beltsurface`、`content/magmabelt` 四套自定义"带"，各自实现 `BeltMovementHandler`/判面，配 mixin 改 Create 漏斗与带行为（`mixin/BeltFunnelBlockMixin`、`BeltFunnelShapeMixin`、`BeltFunnelBlockStateMixin` 三连，是"给已有方块加新状态"的现成范例）。

**D. BufferPad 碰撞（卡车/矿车抗冲击）**：`content/bufferpad/BufferPadCollisionHelper.java`（640 行）为**静态世界方块 + 动态大陆动结构**做 AABB 采样与推出，用 `NBT` 标记 `CreateBiotechBufferPadEscapePushNormal*` 跨 tick 传递法线（`:32-36`），并通过 `mixin/AbstractContraptionEntityBufferPadMixin.java:14-17` 在 `AbstractContraptionEntity.tick()` 的 `@At("RETURN")` 挂载。

**E. 悦灵物流（内嵌模块，工程化最好是它）**：`com.yision.allay` 自成一套（`CreateAllay.java` + 自己的 registry/config/network）。核心是**任务持久化 + 实体按需生成**：`logistics/courier/AllayCourierTaskManager.java:19-20` 持有静态 `AllayCourierTaskSavedData` 与 `Map<UUID, AllayCourierEntity>`；`:35` 每 tick 由 `ServerTickEvent` 驱动；`:97 addTask` 写入 `SavedData`；`AllayCourierTaskSavedData.java:14` 用 `SavedData` + `ListTag("Tasks")` 存全服任务，任务是**纯数据**（`AllayCourierTask.save/load`），实体只是执行者，可随时 `spawnCourier/removeCourier` 重建 → 服务端重启/区块卸载安全。HUD 走 `AllayCourierHudPacket` 推送。

**F. 思索（Ponder）代码生成**：`ponder/generated/` 全部由外部工具 **The Ponderer** 导出（文件头注明"下次导出会被覆盖"），`GeneratedPonderForgeClient.java:19-22` 在 `FMLClientSetupEvent` 里 `PonderIndex.addPlugin(new GeneratedPonderPlugin())`；场景类如 `generated/scenes/GeneratedSlimeBeltConnector_c6a43e38.java` 只做注册，真实动作是 `GeneratedPonderSupport.showStructure/modifyBlockEntity(NBT字符串)` 还原（2179 行支持库），NBT 资源在 `assets/create_biotech/ponder/generated/ponderer/*.nbt`（29 个），并带 `tag` 归因（`GeneratedPonderAttribution`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：单文件 `network/CBPackets.java`，Forge `SimpleChannel`，网络版本字符串 `"12"`（`:32`），`messageBuilder(type, packetId++, direction)` + `consumerNetworkThread`（`:104-108`）全部走网络线程不切主线程（各 handler 内部自行 `enqueueWork`）。13 个包，13 个包分 PLAY_TO_SERVER/TO_CLIENT（`register()` `:43-83`），提供 `sendToServer/sendToPlayer/sendToTrackingEntity/send` 四个出口；**同类多包写在一个类里**（`ShulkerPackagerPlacementPacket.ClientBoundRequest` 作为嵌套类再注册一次，`:64-67`）。
- **配置**：`registry/CBConfigs.java`（29KB）三级 `ForgeConfigSpec`：CLIENT/COMMON/SERVER（`:15-20`），Server 段再拆 `Experience`/`CreeperBlastChamber`/`PowerBelt`/`PetriDish`/`GhastHotAirBalloon` 等 12 个内部类（`:97-110`），每台机器一个配置子类。
- **数据驱动**：无自定义 recipe 类型 datagen 输出，但有 `CBRecipeTypes`（Create `ProcessingRecipe` 系列）+ 空 `src/generated/resources`（datagen data run 已配置 `build.gradle` 中 `programArguments --all`，但仓库无 provider，属未完成）。资源侧：本地工作树为**稀疏检出**，`assets/` 只在 git 索引里（484 个资源文件、29 个 ponder NBT、`lang/en_us.json`+`zh_cn.json`）。
- 版本迁移有专门处理：`infrastructure/CBRemapHelper.java:26-40` 用 `MissingMappingsEvent` 把旧 `experience_pipe/experience_tank` 重映射到 Create 原版管道、`mini_allay` → `ALLAY_COURIER`。

## 6. Mixin

两个配置：`src/main/resources/create_biotech.mixins.json`（package `com.nobodiiiii.createbiotech.mixin`，35 个 + client 24 个）与 `create_biotech_allay.mixins.json`（`com.yision.allay.mixin`，1 个 `PackagerBlockEntityMixin`），共用同一 refmap `create_biotech.refmap.json`，`injectors.defaultRequire=1`，jar manifest 里声明 `MixinConfigs`。

代表性 hook：`AbstractContraptionEntityBufferPadMixin` → `AbstractContraptionEntity#tick()V` @At RETURN；`SmartBlockEntityLegacyRefreshMixin`、`BlockEntityConfigurationPacketMixin`（改 Create BE 配置/刷新路径）；`AbstractVillagerSlimeMimicTradesMixin`+`AbstractVillagerAccessor`（Accessor 取私有字段以扩展交易）；`client.CameraMixin`/`GameRendererMixin`/`ItemApplicationCategoryMixin`(JEI)。

## 7. 值得学的 5 条具体做法

1. **主类只做"一行一注册"的清单**：`CreateBiotech.java:45-64`，把每个子系统注册收敛到 `CB*` 静态类，主类保持 <100 行。适用于任何注册项多的 mod。
2. **用 Create 官方注册表接自家方块，而不是 mixin 硬改**：`ExplosionProofItemVaultCompat.register()`（`content/explosionproofitemvault/ExplosionProofItemVaultCompat.java:16-22`）让自研保险库直接进打包机/物流；`ExperienceOpenPipeEffectHandler.register()` 同理。做 Create 附属时先查 `CreateBuiltInRegistries` 有没有对应 Registry。
3. **任务数据与执行实体解耦**：`allay/logistics/courier/AllayCourierTaskSavedData.java` + `AllayCourierTaskManager.java:19-20,35,97`，`SavedData` 存任务、实体按 tick 校验（`isCurrentCourier/canShowEntity`）后生成 → NPC 型自动化不丢单。
4. **老 ID 用 MissingMappingsEvent 平滑迁移**：`infrastructure/CBRemapHelper.java:26-40`，把废弃方块/物品/BE 重映射到 Create 原版或新 ID，避免存档报错。适用于任何改过 ID 的 mod。
5. **机器代码可用外部工具生成 + 归因**：`ponder/generated/*`（生成时写入英文/中文双语免责头、`GeneratedPonderAttribution` 打 tag），运行时只由 `PonderIndex.addPlugin` 装载，人工与生成界线清楚。

> 补充可抄项：`build.gradle` 的 `net.neoforged.moddev.legacyforge` 多套 run 配置（data/client/server + 自定义 `quickPlayClient` Exec 任务调 python 脚本）；`docs/optimization/00~07*.zh-CN.md` 是一份现成的仓库自审清单（依赖/网络/mixin/资源/性能/测试六主题），可直接当重构 checklist。
