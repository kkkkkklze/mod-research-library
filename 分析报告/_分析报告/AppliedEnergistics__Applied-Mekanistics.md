# AppliedEnergistics/Applied-Mekanistics 源码分析报告

## 1. 基本信息

- Mod 名：Applied Mekanistics；mod_id `appmek`；作者 ramidzkh（AppliedEnergistics 组织维护，并入了 AE2 官方附属体系）；版本 1.6.0（`build.gradle` version 默认值）
- 目标版本：MC 1.21.1 + NeoForge 21.1.172（`gradle.properties`），Java 21 toolchain
- Gradle 插件：`net.neoforged.moddev 2.0.78` + `com.matthewprenger.cursegradle` + `com.diffplug.spotless 7.0.3` + `com.modrinth.minotaur`（`build.gradle:1-6`），发布到 CurseForge(574300)/Modrinth(applied-mekanistics)
- 许可证：`src/main/resources/META-INF/neoforge.mods.toml` 写 "See GitHub repository for details"，具体协议未在仓库内确认
- 编译依赖（`build.gradle` dependencies）：AE2 19.2.10 **完整版**（注释原文："We depend on many AE2 internals, such as using their basic cell drive, thus not using classifier = api"）、Mekanism 10.7.14.79（`api` compileOnly + `all` runtimeOnly）、Jade compileOnly、JEI/EMI 由属性 `runtime_itemlist_mod` 决定谁进 runtime、`ae2-jei-integration`（CurseMaven）。mods.toml 声明 ae2/mekanism 均为 required 且 ordering=AFTER

## 2. 源码规模与包结构

实测：42 个 `.java`，2254 行。包（第 3 层）：`me/ramidzkh/mekae2` 根 6（AppliedMekanistics、AppliedMekanisticsClient、AMItems、AMMenus、AMText、MekCapabilities）、`ae2` 12、`ae2/stack` 6、`data` 6、`item` 3、`mixin` 2、`qio` 2、`integration/{jei,emi,jade}` 8。
最大文件：`ae2/ChemicalP2PTunnelPart.java` 194、`ae2/MekanismKey.java` 157、`data/RecipeProvider.java` 144、`AppliedMekanistics.java` 144、`AMItems.java` 134、`qio/QioStorageAdapter.java` 130、`ae2/AMChemicalStackRenderer.java` 121。

## 3. 入口与注册

`AppliedMekanistics.java:41-85` 的 `@Mod` 构造器拿到 `IEventBus`，按依赖库的扩展点注册：
- `AMItems.initialize(bus)` / `AMMenus.initialize(bus)`：NeoForge `DeferredRegister`（`AMItems.java:32-101` 注册 5 档 chemical cell + 5 档便携 cell + `chemical_p2p_tunnel` + `chemical_cell_housing` + CreativeModeTab）
- AEKeyType 注册时机很特别：在 `RegisterEvent` 中判断 `event.getRegistryKey().equals(Registries.BLOCK)` 才 `AEKeyTypes.register(MekanismKeyType.TYPE)`（`AppliedMekanistics.java:56-62`），用于控制与其他 AE2 附属的注册顺序
- `StackWorldBehaviors.registerImportStrategy/registerExportStrategy/registerExternalStorageStrategy(MekanismKeyType.TYPE, ...)`（:64-66）
- `ContainerItemStrategy.register`、`GenericSlotCapacities.register(TYPE, fluids 的表)`（:68-69）
- `EventPriority.LOWEST` 的 `registerGenericAdapters`：遍历 `BuiltInRegistries.BLOCK`，凡已注册 `AECapabilities.GENERIC_INTERNAL_INV` 的方块都补挂 chemical capability（:92-99、133-143）
- `QioSupport::onBlockEntityCapability`、`RegisterPartCapabilitiesEvent` 给 P2P part 挂 cap（:87-90）
- datagen 监听 + 客户端 `AppliedMekanisticsClient.initialize`（:82-84）

## 4. 核心系统

1) 新资源类型接入 AE2：`ae2/MekanismKey.java:33-157`（`extends AEKey`，`MAP_CODEC = RecordCodecBuilder...Chemical.HOLDER_CODEC.fieldOf("id")`，`equals/hashCode` 只比 chemical 本体不含数量，`addDrops` 触发 `IRadiationManager.dumpRadiation`）+ `ae2/MekanismKeyType.java:21-73`（`extends AEKeyType`，换算 "Copied from AEFluidKey"：`getAmountPerOperation = bucket*125/1000`、`getAmountPerByte = 8*bucket`、`getUnitSymbol()="B"`）。
2) 通用库存桥：`ae2/GenericStackChemicalStorage.java` 把 `GenericInternalInventory` 包成 Mekanism `IChemicalHandler`，容量用 `inv.getCapacity(TYPE)`，动作转换 `Actionable.of(action.toFluidAction())` / `Action.fromFluidAction`。这一招让化学品自动可被存储总线、接口等所有 AE2 通用库存调用。
3) 存储元件：`item/ChemicalStorageCell.java`（`extends BasicStorageCell`，只传 `MekanismKeyType.TYPE`）、`item/ChemicalPortableCellItem.java`（`extends PortableCellItem`），都在 `isBlackListed` 里用 `ChemicalAttributeValidator.DEFAULT.process(key.getStack())` 拦放射性物品。
4) P2P 隧道：`ae2/ChemicalP2PTunnelPart.java:17-100` 继承 `CapabilityP2PTunnelPart<..., IChemicalHandler>`，输入侧按输出隧道的均分 + 余数分配写入，执行成功才 `deductTransportCost(total, MekanismKeyType.TYPE)`。
5) 自动导入/导出：`ae2/stack/MekanismStackExportStrategy.java:27-99` 用 `BlockCapabilityCache` 缓存邻接 handler，先 `StorageHelper.poweredExtraction(SIMULATE)` → `insertChemical(SIMULATE)` → 再 MODULATE，溢出回写失败时记 error 日志；Import 对称实现。
6) Mekanism QIO 桥：`qio/QioStorageAdapter.java:34-129` 用 `<DASHBOARD extends BlockEntity & IQIOComponent & ISecurityObject>` 泛型参数避免引用 Mekanism 具体 BE 类，`getFrequency()` 依次校验正面朝向、频率有效、`ISecurityUtils` 安全模式，并用 `WeakHashMap` 缓存 hashed item → AEItemKey；`qio/QioSupport.java` 靠 `GridHelper.getNodeHost(level, pos.relative(side))` 反查网格节点拿 owner 再注册 `AECapabilities.ME_STORAGE`。

## 5. 网络 / 数据驱动 / 配置 / datagen

无自定义网络包与 config；序列化全靠 AEKey 自带的 `writeToPacket/toTag`（`MekanismKey.java:85-134`）。datagen 齐全：`data/MekAE2DataGenerators.java` 注册 BlockTags/ItemTags/ItemModel/Recipe 四个 provider，输出 `src/generated/resources`；配方从 AE2 原版 cell 配方模板生成（`data/RecipeProvider.java`）。集成包 `integration/jei|emi|jade` 各有一个 plugin（`ChemicalIngredientConverter` 把 chemical 变成 JEI/EMI 的 ingredient），JEI/EMI 谁在 runtime 由 gradle 属性选择。

## 6. Mixin

配置 `src/main/resources/appmek.mixins.json`（`required:true`，`package me.ramidzkh.mekae2.mixin`，`defaultRequire:1`，在 mods.toml 用 `[[mixins]] config=` 声明）。两个类：
- `mixin/MEInventoryHandlerMixin.java:14-27`：`@Mixin(MEInventoryHandler.class)`，用 MixinExtras `@ModifyExpressionValue` 改 `insert` 方法里的 `voidOverflow:Z` 字段读取，使放射性化学品不被 void
- `mixin/CondenserMEStorageMixin.java:15-27`：`@Mixin(targets="appeng.blockentity.misc.CondenserMEStorage")`，`@Inject(method="insert", at=@At("HEAD"), cancellable=true)`，放射性则直接返回 0

## 7. 值得学的 5 条做法

1. 加新资源类型的完整清单：`AEKey` 子类 + `AEKeyType` 子类 + `AEKeyTypes.register` + 三件套 Strategy + `ContainerItemStrategy` + `GenericSlotCapacities`（`AppliedMekanistics.java:56-71`）——写 Create/能量类 AE2 附属可按此逐项对照。
2. 只对接 `GenericInternalInventory`，让新类型自动获得全部 AE2 通用库存能力（`ae2/GenericStackChemicalStorage.java`），不必为每个 AE2 设备写适配。
3. 用 `BlockCapabilityCache` + SIMULATE→MODULATE 两步做外部推送，并处理溢出回滚（`ae2/stack/MekanismStackExportStrategy.java:31-82`）。
4. 需要 AE2 内部行为时只加 2 个 mixin 而不 fork（`mixin/`），用 MixinExtras 的 `@ModifyExpressionValue` 精确改一个字段读取。
5. 用泛型交叉约束（`<T extends BlockEntity & IQIOComponent & ISecurityObject>`）在不依赖第三方具体 BE 类的前提下拿它的接口（`qio/QioStorageAdapter.java:34`）。

## 8. 对外 API / 扩展点

本 mod 自身不提供对外 API 包，它扮演"AE2 扩展点消费者"：全部接口来自 `appeng.api.*`（`AECapabilities`、`AEKeyType/AEKeyTypes`、`StackWorldBehaviors`、`ContainerItemStrategy`、`GenericInternalInventory`、`RegisterPartCapabilitiesEvent`、`AECapabilities.ME_STORAGE`）与 Mekanism `mekanism.api.*`（`IChemicalHandler`、`ChemicalStack`、`IQIOComponent`、`IChemicalHandler` 相关 cap）。做 AE2 附属时可把 `MekCapabilities.java:17-27` 的 `CapSet` record（同时建 BlockCapability + ItemCapability）当作通用模板。
