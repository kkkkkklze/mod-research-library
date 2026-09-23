# Forsteri123/CreateLiquidFuel 源码分析

## 1. 基本信息
- Mod 名：Create Liquid Fuel；mod_id `createliquidfuel`；作者 Forsteri（`mods.toml` 未填 authors 字段）；mod 版本 2.1.1（`file.jarVersion` 注入）
- 目标：MC 1.18.2 + Forge（loaderVersion `[40,)`，minecraft `[1.18.2,1.19)`）；`displayTest="IGNORE_SERVER_VERSION"`
- 编译依赖：Create `0.5.+`（maven 坐标 `com.simibubi.create:create-1.18.2:0.5.+:slim`，`transitive=false`）、Flywheel `0.6.+`、Registrate `MC1.18.2-1.1.3`（后两者声明但源码未直接使用）；mixingradle 0.7-SNAPSHOT（`build.gradle:150-171`）。运行时硬依赖 create `[0.5.1.a,)`
- 许可证：`mods.toml` 写 "All Rights Reserved"（仓库另有 LICENSE 文件，未确认内容与二者是否一致）

## 2. 源码规模与包结构
仅 10 个 `.java`，合计 391 行。包分布：
- 根 `com.forsteri.createliquidfuel` 1；`core` 3；`eventhandlers` 2；`mixin` 2；`util` 2
- 最大文件：BurnerStomachHandler 101、MixinBlazeBurnerTileEntity 78、LiquidBurnerFuelJsonLoader 72、DrainableFuelLoader 53
- 资源目录只有 `CreateLiquidFuel.mixins.json` 与 `META-INF/mods.toml`，无 assets/data（无方块物品，纯行为改造）

## 3. 入口与注册
`src/main/java/com/forsteri/createliquidfuel/CreateLiquidFuel.java:12-21`：仅有 `@Mod` 构造，把 `ForgeEventHandler` 挂到 `MinecraftForge.EVENT_BUS`、`ModEventHandler` 挂到 mod 事件总线。本模组不新增任何注册表条目（无 DeferredRegister / Registrate 使用），全部功能靠"两种事件 + 两个 mixin"实现。

## 4. 核心系统
1. 液体燃料总表：`core/BurnerStomachHandler.java:23` 定义 `Map<Fluid, Pair<ResourceLocation, Triplet<Integer,Boolean,Integer>>>`，值三元组为（burnTime, superHeat, amountConsumedPerTick）。`tick(SmartBlockEntity)`（:25-66）从 blaze burner 的 SmartFluidTank 取液、按 superHeat 调 `invokeSetBlockHeat(SEETHING/FADING)`、累加 `remainingBurnTime` 并扣液；`tryUpdateFuel(...)`（:68-100）让"装着燃料的桶/容器物品"也能灌入，支持 `simulate`/`forceOverflow` 并 `cir.setReturnValue(true)` 覆盖原逻辑。
2. 能力注入 mixin：`mixin/MixinBlazeBurnerTileEntity.java:28-77`，`@Mixin(BlazeBurnerBlockEntity.class, remap=false) extends SmartBlockEntity`；`@Unique` 字段 `createliquidfuel$stomach` 是 1000mB 的 `SmartFluidTank`，在 `addBehaviours` 中创建并把 `isFluidValid` 限制为燃料表内液体（:44-53）；覆写 `getCapability` 暴露 `FLUID_HANDLER_CAPABILITY`（:36-42）；`tick`/`read`/`write` 用 `@Inject(at=TAIL)` 持久化到 NBT 键 `"Stomach"`（:55-72）；`tryUpdateFuel` HEAD cancellable 转发到 `BurnerStomachHandler`（:74-77）。
3. 访问器 mixin：`mixin/BlazeBurnerAccessor.java:10-19`，用 `@Accessor("remainingBurnTime")` + `@Invoker("setBlockHeat")` 拿到 Create 的私有状态，所有成员加 `createliquidfuel$` 前缀防冲突。
4. JSON 数据驱动：`core/LiquidBurnerFuelJsonLoader.java:19-71` 继承 `SimpleJsonResourceReloadListener`，监听 `blaze_burner_fuel` 目录；字段 fluid/burnTime/superHeat/amountConsumedPerTick，缺省值（superHeat 时 32、按 Create 原版 10mB/t 逻辑）以内联注释形式引用了 Create 源码位置（BlazeBurnerBlockEntity#tryUpdateFuel 第 193 行）。注册在 `ForgeEventHandler.addReloadListeners`（`eventhandlers/ForgeEventHandler.java:11-14`）。
5. 原版燃料自动推导：`core/DrainableFuelLoader.java:15-52` 遍历 `ForgeRegistries.ITEMS`，用 `ForgeHooks.getBurnTime` + 物品流体能力推导（burnTime, superHeat, 消耗量），用 `util/MathUtil.gcd` 约分 burnTime/amount 得到每 mB 燃烧时间；JSON 定义的条目优先级更高（:33-35）。由 `FMLCommonSetupEvent.enqueueWork` 触发（`eventhandlers/ModEventHandler.java:12-15`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无
- 数据驱动：唯一数据源为 datapack 目录 `blaze_burner_fuel`（SimpleJsonResourceReloadListener，见 4.4）；仓库内未附带示例 JSON
- 配置：无（无 ForgeConfigSpec）
- datagen：无

## 6. Mixin
配置 `src/main/resources/CreateLiquidFuel.mixins.json`：required、JAVA_8、`refmap: CreateLiquidFuel.refmap.json`、`defaultRequire: 1`，mixins 列表为 `BlazeBurnerAccessor`、`MixinBlazeBurnerTileEntity`（均 `remap=false`）。hook 目标：`BlazeBurnerBlockEntity.tick/read/write/tryUpdateFuel`、`remainingBurnTime` 字段、`setBlockHeat` 方法。

## 7. 值得学的 5 条
1. 用"一个行为 mixin + 一个 accessor 接口"给已有方块加流体能力，不替换原方块、不注册新 BlockEntity：`mixin/MixinBlazeBurnerTileEntity.java:28`、`mixin/BlazeBurnerAccessor.java:10`。
2. 所有注入成员统一加 mod 前缀（`createliquidfuel$`、`@Unique`），降低与其它 mixin 的冲突概率：`MixinBlazeBurnerTileEntity.java:30`。
3. 自定义数据用 `SimpleJsonResourceReloadListener`（简单、可被数据包覆盖），代价是需要写完整缺省值注释说明数值来源：`core/LiquidBurnerFuelJsonLoader.java:19-58`。
4. 从原版数据（物品燃烧时间 + 流体容器容量）自动推导兼容参数，让任何其它 mod 新增的燃料桶都能"免费"支持，并允许 JSON 覆盖：`core/DrainableFuelLoader.java:33-49`。
5. 用 `FMLCommonSetupEvent.enqueueWork` 把所有注册表遍历类工作挪出并行阶段：`eventhandlers/ModEventHandler.java:12-15`。注意坑点：tank 在 `addBehaviours` 才创建，因此 `getCapability` 必须容忍未初始化状态（`MixinBlazeBurnerTileEntity.java:39-40` 未做 null 检查，属可改进处）。

## 8. 库/API 扩展点
不适用（非库/前置模组）。
