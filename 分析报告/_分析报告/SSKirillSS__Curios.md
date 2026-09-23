# SSSKirillSS/Curios 源码分析报告

## 0. 与 TheIllusiveC4/Curios 的关系（结论）
**上游原样快照镜像，未改代码**：仓库仅 1 个提交 `d0874d5 2024-10-25 "Version bump - 9.0.15"`，提交者仍是原作者 `C4 <29991504+theillusivec4@users.noreply.github.com>`（`git rev-list --count HEAD`=1）；包名/groupId/mod_id/README 全保留上游 `top.theillusivec4.curios`、`curios`。唯一 fork 痕迹是 `gradle.properties` 的 `issues_url`/`sources_url` 指向 SSSKirillSS（全仓库 `grep -ril kirill` 仅命中该文件）。版本线不同：本仓库 1.21.1 分支 `9.0.15+1.21.1`；`_bulk/TheIllusiveC4__Curios` 是默认分支 26.2 / `16.0.0+26.2`，无法直接 diff，故"是否逐字节等同上游 9.0.15"未确认。异常：`settings.gradle` `include("forge")` 但无 `forge/`（`git ls-files | grep -c '^forge/'`=0，可能无法直接构建）。

## 1. 基本信息
Curios API / `curios` / C4 / 9.0.15+1.21.1 / LGPL-3.0-or-later / group `top.theillusivec4.curios` / Java 21。MC 1.21（1.21.1），NeoForge 21.1.60、Forge 51.0.8（模块缺失）。Gradle：`buildSrc` 提供 `multiloader-common`/`multiloader-loader`，neoforge 用 `net.neoforged.gradle.userdev 7.0.165`，common 用 `org.spongepowered.gradle.vanilla`；发布 maven.octo-studios.com。依赖：JEI 17.3.0.49 仅 compileOnly。

## 2. 规模与包结构
`.java` 125 个 / 15611 行（neoforge 87 main + 15 test，common 23）。包：`api`（+`type/{capability,inventory,data}`、`event`、`client`）32、`common` 43、`client`（+`gui`、`render`）11、`mixin` 15、`server` 4、`platform` 3。最大：`CuriosEventHandler.java` 658、`CurioStacksHandler.java` 630、`CurioInventoryCapability.java` 561、`CuriosContainer.java` 545、`CuriosApi.java` 522。

## 3. 入口与注册
`neoforge/.../Curios.java`：`@Mod(CuriosConstants.MOD_ID)` 构造器里 `CuriosRegistry.init(eventBus)`、注册 CLIENT/COMMON/SERVER 三份 `ModConfig`；`setup` 设 `CuriosApi.setCuriosHelper(new CuriosHelper())` 并注册 `CuriosEventHandler`；`registerCaps`（`:90-135`）**遍历整个 `BuiltInRegistries.ENTITY_TYPE`/`ITEM`** 注册 `CuriosCapability.INVENTORY`（`EntityCapability<ICuriosItemHandler,Void>`）、`ITEM_HANDLER`（`IItemHandler`）、`ITEM`（`ItemCapability<ICurio,Void>`），不支持时返回 `null`；`AddReloadListenerEvent` 里重建 `CuriosSlotManager.SERVER`/`CuriosEntityManager.SERVER`；内部类 `ClientProxy` 注册按键、`CuriosScreen`、`CuriosLayer`。

## 4. 核心系统
1. **capability 体系**：实体持 `ICuriosItemHandler`，物品持 `ICurio`；实现类 `CurioItemHandler`/`ItemizedCurioCapability`/`CurioInventoryCapability`，统一入口 `CuriosApi.getCuriosInventory(livingEntity)`。
2. **数据驱动槽位**（`common/data/CuriosSlotManager.java`）：`SimpleJsonResourceReloadListener(GSON,"curios/slots")`，`apply()` 遍历 `resourceManager.listPacks()` 按包序加载 `data/<ns>/curios/slots/*.json`，用 `ICondition.conditionsMatched` 支持数据包条件，同名槽位按 id 合并（`SlotType.Builder`）；物品→槽位用 vanilla tag。
3. **同步网络**（`common/network/NetworkHandler.java`）：`PayloadRegistrar` 注册 6 个 `CPacket*`（playToServer）与 9 个 `SPacket*`（playToClient）；`SPacketSyncCurios` 由 `ICurioStacksHandler.getSyncTag()` 取 `CompoundTag`，编码 `writeInt(entityId)+writeInt(entrySize)+每项 writeUtf(key)+writeNbt(tag)`（`:36-55`）。
4. **容器/槽位实现**：`CurioStacksHandler`(增删槽、render 开关)、`CurioSlot`/`CosmeticCurioSlot`、`DynamicStackHandler`、`CuriosContainer`（页面切换、快速移动），配套 `SPacketQuickMove`/`SPacketPage`。
5. **兼容层**：`common/integration/jei/*` 让 JEI 识别 Curios 槽；mixin 包处理掠夺附魔计数、Mending、细雪、猪灵金饰等原版行为；`MixinV1460` 做 1.21 数据修复。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络见上（1.21 `CustomPacketPayload`+`StreamCodec`，handler 单例）。数据驱动：槽位 JSON + `CuriosEntityManager` 实体白名单（同为 reload listener）+ 物品 tag。配置：NeoForge `ModConfig` 三份。datagen：公开 `api/CuriosDataProvider`；`neoforge/src/test` 内含完整示例 mod `curiostest`（`sourceSets.test { runs { modIdentifier 'curiostest' } }`），并有 `curiostest/data/CuriosGenerator`+`CuriosTestProvider` 示范。

## 6. Mixin
`common/src/main/resources/curios.mixins.json`：`AccessorEntity`、`MixinCuriosTriggers`、`MixinCuriosTriggersEquip`。`neoforge/src/main/resources/curios.neoforge.mixins.json`：`MixinApplyBonusCount`、`MixinCuriosApi`、`MixinCuriosDataProvider`、`MixinEnchantedCountIncreaseFunction`、`MixinInventory`、`MixinLivingEntity`、`MixinNbtPredicate`、`MixinPiglinAi`、`MixinPowderSnowBlock`、`MixinV1460`（均 `package top.theillusivec4.curios.mixin.core`、`refmap curios.refmap.json`）。hook 以原版为主，逻辑中转在 `mixin/CuriosImplMixinHooks.java`(309) 与 `CuriosUtilMixinHooks.java`。

## 7. 值得学的 5 条
1. capability 注册遍历全注册表、不支持返回 null：`Curios.java:90-135`。
2. `SimpleJsonResourceReloadListener` + `listPacks()` 手动保序 + `ICondition` 条件：`CuriosSlotManager.java:60-120`。
3. 同步包统一 `getSyncTag()` NBT 序列化：`SPacketSyncCurios.java`、`CurioStacksHandler.java`。
4. mixin 只做转发、逻辑集中到 `*MixinHooks` 静态类：`CuriosImplMixinHooks.java`。
5. 库模组自带可运行示例源集 + datagen provider：`neoforge/src/test/...`、`CuriosDataProvider`。

## 8. 公开 API（库/前置类）
- 主入口 `top.theillusivec4.curios.api.CuriosApi`（`getCuriosInventory`、`getEntitySlots`、`getPlayerSlots`、`getItemStackSlots`、`isStackValid`、`registerCurio`、`registerCurioPredicate`、`getAttributeModifiers`、`addSlotModifier`、`broadcastCurioBreakEvent`）与 `CuriosCapability`（INVENTORY/ITEM_HANDLER/ITEM）。
- 扩展接口：`api/type/capability/{ICurio,ICurioItem,ICuriosItemHandler}`、`api/type/{ISlotType,ICuriosMenu}`、`api/type/inventory/{ICurioStacksHandler,IDynamicStackHandler}`、`api/type/data/{IEntitiesData,ISlotData}`、`api/{SlotContext,SlotAttribute,CurioAttributeModifiers,CuriosTooltip,CuriosTriggers}`。
- 事件：`api/event/`（CurioChangeEvent、CurioDropsEvent、DropRulesEvent、CurioAttributeModifierEvent、CurioCanEquip/UnequipEvent、SlotModifiersUpdatedEvent）。
- 客户端：`api/client/{CuriosRendererRegistry,ICurioRenderer,ICuriosScreen}`、`IIconHelper`。
- 接入：`top.theillusivec4.curios:curios-neoforge:<version>`（maven.octo-studios.com），多加载器由 `platform/Services.java`+`ICuriosPlatform` 派发；数据生成用 `CuriosDataProvider`。
