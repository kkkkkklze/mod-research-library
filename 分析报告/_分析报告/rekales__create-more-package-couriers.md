# rekales/create-more-package-couriers 源码分析报告

## 1. 基本信息

- Mod 名：Create More: Package Couriers；mod_id `cmpackagecouriers`；作者 Krei；版本 2.3.0
- 目标：Minecraft 1.21.1 / NeoForge（`neo_version=21.1.219`，`loader_version_range=[4,)`）；Parchment 2024.11.17
- Gradle：Kotlin DSL + `net.neoforged.moddev` 2.0.78（`build.gradle.kts`），另用 `accesstransformer.cfg`
- 许可证：Lambda License（`LICENSE.txt`）
- 编译依赖：Create 6.0.10-280（slim，`isTransitive = false`）、Ponder 1.0.82、Flywheel 1.0.6（api compileOnly）、Registrate `MC1.21-1.3.0+67`；jarJar 内置 `ru.zznty:create_factory_abstractions:1.4.9`；JEI 19.21.0.247
- 可选/软依赖（compileOnly + runtimeOnly）：create_factory_logistics、Curios API、CC:Tweaked（core-api/forge-api）、Supplementaries、create-more-pipe-bombs（curse maven）、createfluidlogistic；runtimeOnly `create-mobile-packages` 0.7.4

## 2. 源码规模与包结构

实测：52 个 `.java`，合计 5044 行。包分布（第 3 层）：

| 包 | 文件数 |
| --- | --- |
| `com.kreidev.cmpackagecouriers`（根） | 8 |
| `...compat`（含 7 个子包） | 12 |
| `...mixin` | 6 |
| `...plane` | 11 |
| `...stock_ticker` | 12 |
| `...transmitter` | 2 |
| `...ponder` | 1 |

最大文件：`stock_ticker/PortableStockTickerScreen.java` 1229、`ponder/PonderScenes.java` 615、`plane/CardboardPlane.java` 258、`CourierTarget.java` 180。

## 3. 入口与注册

入口 `src/main/java/com/kreidev/cmpackagecouriers/PackageCouriers.java:33`，注册框架是 Registrate：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)
        .defaultCreativeTab(AllCreativeModeTabs.BASE_CREATIVE_TAB.getKey());
public static final DeferredRegister.DataComponents DATA_COMPONENTS =
        DeferredRegister.createDataComponents(Registries.DATA_COMPONENT_TYPE, MOD_ID);   // :48
```

构造函数（:51-78）里条件注册是关键：`if (!Mods.CREATE_MOBILE_PACKAGES.isLoaded()) PortableStockTickerReg.register();`，再用 `Mods.CURIOS/SUPPLEMENTARIES/CRATE_FACTORY_LOGISTICS.executeIfInstalled(...)` 挂兼容初始化，最后 `modContainer.registerConfig(ModConfig.Type.SERVER, ServerConfig.SPEC)`。物品/实体/菜单分散在 `plane/CardboardPlaneReg`、`stock_ticker/PortableStockTickerReg`、`transmitter/LocationTransmitterReg` 三个 `register()` 静态方法中。

## 4. 核心系统

**A. 纸板飞机投递（`plane/`）**：`CardboardPlane` 是纯数据对象（`MapCodec CODEC`，:38，字段 ID/Delta/Pos/Dim/Target/Box），`CardboardPlaneManager.serverTick`（:28-66）在 `ServerTickEvent.Pre` 驱动每架飞机 tick，并按区块是否 ticking 动态 add/remove 仅用于渲染的 `CardboardPlaneEntity`；持久化用 `CardboardPlaneSavedData`（`Codec.list(CardboardPlane.CODEC)` + NbtOps，挂在 overworld 的 `"cardboard_planes"` data storage，:61-68）。

**B. 地址→目标解析（`CourierTarget.java`）**：`activeTargets: Map<CourierTarget,Integer>` 带 20 tick 超时（`TIMEOUT_TICKS=20`），`getActiveTarget` 用 `PackageItem.matchAddress` 线性匹配并优先实体目标（:162-175）。特殊地址语法：`<addr>` 与 `@player`（`CardboardPlaneManager.java:86-99`）。

**C. 便携股票终端（`stock_ticker/`）**：PortableStockTicker 物品 + Menu + 1229 行 Screen，`LogisticallyLinkedItem` 用 `CMP_FREQ` 数据组件存 `Freq` UUID，复用 Create 的 `LogisticallyLinkedBehaviour` 接入物流网络。

**D. 兼容层**：`compat/Mods.java` 枚举 + `executeIfInstalled(Supplier<Supplier<Runnable>>)`，7 个兼容子包彼此隔离。

**E. 接口注入而非行为注册**：`CourierDestination`（`cmpc$onReachedDestination` / `cmpc$hasSpace`）由 mixin 直接在 Create 的 `BeltBlock`/`DepotBlock` 上实现；`UnpackEffect`/`EjectorLaunchEffect` 由 `PackageCouriersApi.registerUnpackEffects` 暴露给外部 mod。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：复用 Create 的 Catnip 网络库，`PortableStockTickerReg.PortableStockTickerPackets` 枚举实现 `BasePacketPayload.PacketTypeProvider`，`CatnipPacketRegistry.registerAllPackets()` 统一注册 5 个包（:68-102）；包体用 `StreamCodec.composite`（`stock_ticker/SendPackage.java:23`），服务端实现 `ServerboundPacketPayload.handle(ServerPlayer)`。
- 数据驱动：无 JSON 内容注册（配方/模型走 Create 与外部资源）。
- 配置：`ServerConfig.java` 用 `ModConfigSpec`，5 个布尔项，静态字段缓存 + `onLoad/onReload` 刷新。
- datagen：无 data run（`build.gradle.kts` 只注册 Client/AltClient/Server），Two 个物品用 `.model((ctx, prov) -> {})` 跳过模型生成改走自定义渲染器。

## 6. Mixin

配置 `src/main/resources/cmpackagecouriers.mixins.json`（`required: true`、`priority: 1000`、JAVA_17），6 个类全部 `remap = false`：`SignBlockEntityMixin` 注入 `tick` HEAD（壁牌每 5 tick 扫描牌后方的 `CourierDestination` 方块并登记地址）、`BeltDeployerCallbacksMixin` 注入 `activate` 中 `TransportedItemStack;clearFanProcessingData()` 调用点、`EjectorBlockEntityMixin.addToLaunchedItems` HEAD（可取消，交给 `EjectorLaunchEffect`）、`SawBlockEntityMixin.applyRecipe` HEAD（纸板飞机部件回收）、`BeltBlockMixin`/`DepotBlockMixin` 实现 `CourierDestination` 接口。AT：开放 `SignRenderer.renderSignWithText`。

## 7. 值得学的 5 条具体做法

1. 用接口注入替代行为注册：`CourierDestination.java:7` 注释写明"比 behaviours 更通用，避免给子类逐个加行为"，配套 `BeltBlockMixin`/`DepotBlockMixin`。适用于给第三方方块加能力。
2. 逻辑数据与渲染实体分离：`plane/CardboardPlane`（SavedData 持久化，不会卸载）+ `CardboardPlaneEntity`（`noSave()`，只在区块 ticking 时存在，`CardboardPlaneManager.java:53-64`）。适用于长距离飞行的投递物。
3. 实体同步做兜底：`CardboardPlaneEntity.tick` 每 20 tick `setPos(plane.getPos())` 纠偏（:82），而非常规每 tick 同步。
4. 条件注册避免功能重复：检测到 `create-mobile-packages` 已加载就跳过自己的便携终端注册（`PackageCouriers.java:52`），并提供 `@key` 打开终端（`PackageCouriersKeys`）。
5. 给外部 mod 留 3 行 API：`PackageCouriersApi`（:26-40）用 `Map<Item, UnpackEffect>` 注册拆包效果，pipe-bomb 等附属通过它扩展。

## 8. 公开 API / 扩展点

- `com.kreidev.cmpackagecouriers.PackageCouriersApi`：`registerUnpackEffects(Item, UnpackEffect)`、`hasUnpackEffects`、`handleUnpackEffects`。
- `com.kreidev.cmpackagecouriers.CourierDestination`：任意方块/方块实体实现后可被纸板飞机投递（如 `cmpc$hasSpace` 判空）。
- `plane/UnpackEffect`、`plane/EjectorLaunchEffect` 函数式/行为接口，配合外部方块（发射器、锯等）的 mixin 生效。
- `CourierTarget` + `activeTargets` 是跨 mod 共享的"地址目标注册表"。
