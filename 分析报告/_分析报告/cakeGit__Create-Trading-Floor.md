# cakeGit/Create-Trading-Floor 源码分析报告

## 1. 基本信息

- Mod 名：Create: Trading Floor（自动村民交易） / **mod_id：`trading_floor`** / 作者：Tazer & Cak / 版本 1.1.7
- 目标版本：**Minecraft 1.20.1 双平台**（`gradle.properties:4` `enabled_platforms = fabric,forge`；Forge 47.3.0，Fabric Loader 0.16.0 + Fabric API 0.92.2）
- 构建体系：**Architectury 多加载器**——根 `build.gradle` 用 `architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.9.420`，三层 mappings（quilt-mappings + parchment 2023.09.03 + 官方 mojmap 合成）；子项目 `include("common")/("fabric")/("forge")`。另用 `io.github.p03w.machete` 压 jar、`me.modmuss50.mod-publish-plugin` 发布
- 许可证：MIT（`mods.toml:4`）
- 依赖：Create Forge 6.0.0-74 / Create Fabric 0.5.1-f-build.1335、Registrate MC1.20-1.3.11、Flywheel 1.0.0-215、Catnip 0.8.44、Ponder 1.0.37、JEI（common-api，可选）。common 模块**只编译期依赖 Create Forge**（`common/build.gradle` 中 `modCompileOnly("com.simibubi.create:create-1.20.1:${create_forge_version}")`，注释警告"only Flywheel/Registrate are safe"）。

## 2. 源码规模与包结构

实测 **83 个 .java / 5557 行**：`common` 48、`fabric` 17、`forge` 17、`shelf` 1（一个废弃的 `PotentialVillagerTradeSerializer`，文件自带注释"I WORKED SO HARD ON THIS AND I REALISED ITS USELESS"，未在 `settings.gradle` 中 include）。

包：`com.cak.trading_floor`（`TradingFloor.java`、`TFExpectPlatform.java`）、`registry`（TFRegistry/TFPlatformRegistry/TFDisplaySources/TFPonderIndex/TFArmInteractionPointTypes/TFParticleEmitters/TFLangEntries）、`content.trading_depot`（Common 抽象层 + displays + renderer + behavior 接口）、`foundation`（advancement/access/ponder_scenes/ParticleEmitter/MerchantOfferInfo/AttachedTradingDepotFinder/TFLang/TFPlatformPackets/TFPlatformPredicates）、`mixin.item_listings`（10 个）、`compat.jei`（虚拟配方）。最大文件：`forge/.../TradingDepotBlockEntity.java` 367 行、`fabric` 同 362 行、`TradingDepotBehaviour.java` 357/358 行（for/fab 各一份）、`common/.../ponder_scenes/TradingDepotScenes.java` 245 行、`TFAdvancement.java` 212 行。

## 3. 入口与注册

公共入口 `common/.../TradingFloor.java:16-28`：`init()` 只做 `TFRegistry.init()` + 四个 register + `TFLangEntries.addEntries()`；`clientInit()` 只做 `PonderIndex.addPlugin(new TFPonderPlugin())`（`:27`）。平台侧各自调用：Forge `forge/.../TradingFloorForge.java:18-31`（**必须先把 REGISTRATE 挂到 mod event bus 再做注册**：`TFRegistry.REGISTRATE.registerEventListeners(eventBus)`，`:22`），Fabric `fabric/.../TradingFloorFabric.java:11-18`（`TFRegistry.REGISTRATE.register()` + `TFPackets.getChannel().initServerListener()`）。

注册框架是 **Registrate 单例**：`registry/TFRegistry.java:24` `CreateRegistrate.create(MOD_ID)`，方块与 BE 在 common 里定义、用 `@ExpectPlatform` 取平台构造器：

```java
public static final BlockEntry<CommonTradingDepotBlock> TRADING_DEPOT = REGISTRATE
    .block("trading_depot", TFPlatformRegistry.getTradingDepotBlock())   // TFRegistry.java:26-33
    .properties(BlockBehaviour.Properties::noOcclusion)
    .blockstate(BlockStateGen.horizontalBlockProvider(false))
    .transform(displaySource(TFDisplaySources.TRADE_COMPLETED_COUNT))
    .simpleItem().register();
```

`registry/TFPlatformRegistry.java`（`:10-17` 两个 `@ExpectPlatform` 静态方法）→ `forge/registry/forge/TFPlatformRegistryImpl.java` / `fabric/.../TFPlatformRegistryImpl.java` 返回各自的方块/BE 工厂。平台差异统一走 `TFExpectPlatform`（`common/.../TFExpectPlatform.java:19-23`）。

## 4. 核心系统

**A. 交易台行为树（Create BlockEntityBehaviour 的组合用法）**——`forge/.../content/depot/behavior/TradingDepotBehaviour.java`。`tick()`（`:62-101`）自己处理 `TransportedItemStack` 的 `beltPosition/angle` 插值，并把多余输入塞进 `incoming` 列表；`addAdditionalBehaviours`（`:119-124`）挂 `DirectBeltInputBehaviour.allowingBeltFunnels()` + `VersionedInventoryTrackerBehaviour`；`insert()`（`:161-189`）实现"满 64 就退回 + 同物品才能堆叠"。输出侧 `combineOutputs()`（`:276-296`）做同类合并，`result` 上限 8 条（由 BE 判断）。

**B. 交易撮合与多槽凑单**——`forge/.../content/depot/TradingDepotBlockEntity.java:187-314`：`tryTakeMerchantOffer` 先比 `offer.getBaseCostA()`，再在**同工作站点挂载的多个交易台**里凑 `costB`（`takeTotalFromSources`，`:222-238` 逐个扣减），成功后 `costASource.getResults().add(offer.assemble())`；`tryTradeWith`（`:240-314`）遍历 `villager.getOffers()`，一次调用只完成一种交易，最后统计 `tradeOutputSum/currentTradeCompletedCount` 并 `notifyUpdate()`。

**C. 村民 AI 钩子**——`common/.../mixin/WorkAtPoiMixin.java`：在 `WorkAtPoi.checkExtraStartConditions` 尾部 `@Inject`，若工作站点旁有交易台则 `lastCheck -= 2000`（`:47-49`）缩短工作冷却；在 `useWorkstation` 的 `@At("HEAD")` 注入，收集周围交易台并逐个 `tryTradeWith`（`:53-77`）。配套 `AttachedTradingDepotFinder.lookForTradingDepots`（`common/.../foundation/AttachedTradingDepotFinder.java:14-28`，只看 4 个水平方向 + FACING 匹配）与 `WorkAtComposterMixin`（农夫同理）。

**D. 自研成就行为（复制 Create 逻辑 + mixin 补数据）**——`common/.../foundation/advancement/TFAdvancementBehaviour.java`（144 行，"Mirror of AdvancementBehaviour"）：以 BE behaviour 形式记录 `playerId`（NBT `"Owner"`）并 `awardPlayerIfNear`；成就定义 `TFAdvancement.java`（212 行）通过 `TFParentableAdvancement` 支持父成就，Forge 侧靠 `forge/mixin/AdvancementAccessMixin.java:14-30` mixin `CreateAdvancement` 拿到 `datagenResult`（先 `save(a->{})` 强制生成）。

**E. JEI 虚拟配方（用 mixin 给原版内部类加接口）**——`common/.../foundation/access/ResolvableItemListing.java` 是鸭子接口，10 个 `mixin/item_listings/*AccessMixin` 用 `@Mixin(targets = "net.minecraft.world.entity.npc.VillagerTrades$ItemsForEmeralds")` 直接标注内部类并读取 `@Shadow @Final` 字段还原出 `PotentialMerchantOfferInfo`；`VillagerItemListingResolver.tryResolve` 用 `try { cast } catch (ClassCastException) { return null; }` 兜底（`:9-16`）。`compat/jei/TradingFloorJei.java` 注册 `POTENTIAL_TRADE_TYPE` 配方类型 + 交易台作催化剂，`CachedVillagerRenderer` 缓存村民渲染。

**F. 自定义粒子发射器工具**——`common/.../foundation/ParticleEmitter.java`（131 行，注释"MIT so go forth and copy"）：字段化 `volume / randomVelocityStrength / emitFromCenterStrength / sendPacketRange`，服务端 `emitToClients` 走平台包，客户端 `emitParticles(ClientLevel, Vec3, int)` 本地发射；经 `TFPlatformPackets`/`TFPlatformPredicates` 两个 `@ExpectPlatform` 门面分平台。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：平台各一份**同构 enum**。Forge `forge/.../network/TFPackets.java`：enum 常量携带 `SimplePacketBase` 子类 + `NetworkDirection`，`SimpleChannel`（`NETWORK_VERSION = 3`），内部类 `PacketType` 用 `T::write` 做编码、`consumerNetworkThread` 注册 handler，导出 `sendToNear(Level, BlockPos, range, msg)`（`:46-50`）。Fabric 同文件结构改用 Create Fabric 的 `me.pepperbell.simplenetworking.SimpleChannel` + `sendToClientsAround`（`fabric/.../network/TFPackets.java:44-56`）。上行无自定义包。
- **数据/资源驱动**：datagen 有 Forge `GatherDataEvent`（`forge/.../TradingFloorData.java:14-20`）只挂一个 provider `TFAdvancements(output)`（成就 JSON 由代码生成）；语言走 Registrate `ProviderType.LANG`（`TradingFloorForge.java:23`）+ common 的 `TFLangEntries.addEntries()`。`common/src/main/resources/trading_floor.accesswidener` 内容仅为头部（无实际条目）。`common/build.gradle` 把 `src/generated/resources` 加入 sourceSet 并 `exclude("assets/create/**")`（避免打包 Create 资产）。
- **配置**：无（无 config 文件/ConfigSpec）。**本地未找到 `fabric.mod.json`**（仓库里只有两个 mixins.json + mods.toml，注释掉的行表明 fabric 元数据可能在构建期生成）。**Mixin**：三份配置——`common/.../trading_floor-common.mixins.json`（12 个：WorkAtPoi/WorkAtComposter + 10 个 `item_listings.*AccessMixin`）、`forge/.../trading_floor.mixins.json` 与 `fabric/.../trading_floor.mixins.json`（各 3-4 个：`AdvancementAccessMixin`、`ChuteBlockEntityMixin`（`@Mixin(value = ChuteBlockEntity.class, remap = false)`，注释"Extends the fan reach of chutes by one block"）、`CreateCreativeModeTabMixin`，fabric 另有 `RegisterAdditionalMixin`）。

## 6. 值得学的 5 条具体做法

1. **多加载器差异只留一个缝**：common 写业务 + `@ExpectPlatform`（`registry/TFPlatformRegistry.java:10-17`、`foundation/TFPlatformPackets.java`、`TFPlatformPredicates.java`），平台侧只写 `*Impl`。做双端 Creato 附属的模板级方案。
2. **给原版内部类打标签接口**：`@Mixin(targets = "...VillagerTrades$ItemsForEmeralds")` + 鸭子接口（`mixin/item_listings/ItemsForEmeraldsAccessMixin.java:15-30`），调用端 `catch (ClassCastException)` 判定是否支持（`VillagerItemListingResolver.java:11-16`）。适用于任何要从原版私有内部类取数据的 JEI/展示需求。
3. **Create behaviour 三件套直接拿来接物流**：`DirectBeltInputBehaviour.allowingBeltFunnels()` + `FilteringBehaviour` + `VersionedInventoryTrackerBehaviour`（`forge/.../TradingDepotBehaviour.java:119-124`），自己只实现 `tryInsertingFromSide` 与 NBT 读写（`:217-245`）。
4. **村民 AI 用注入改数值而不是重写行为**：`WorkAtPoiMixin` 里 `lastCheck -= 2000`（`:47-49`）这一句就能显著加快工作站使用频率；业务逻辑放在 `useWorkstation` 的 `@At("HEAD")`。改造原版 AI 时成本最低的切入点。
5. **把 Create 的成熟机制"复制+补丁"而非继承**：`TFAdvancementBehaviour.java:19-22` 明确说明是 `AdvancementBehaviour` 的镜像，再 mixin `CreateAdvancement` 取 `datagenResult`（`forge/mixin/AdvancementAccessMixin.java:22-29`）实现父成就链。当 Create 内部类不可继承/字段私有时的通用应对。

> 另有工程化可抄：发布链（`mod-publish-plugin` + `changelog.yaml` + `.env` token + GitHub Run Number 拼版本号）、`machete` 只在 CI 压缩 jar、`forge_updates.json` 内置更新检查。

> 非库/前置 mod，无公开 API 包（第 8 节不适用）。
