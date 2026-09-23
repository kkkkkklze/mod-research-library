# Railcraft 源码分析报告

> 重要校准：本检出不是 NeoForge 1.20/1.21 的 "Railcraft Reborn"，而是**经典 Forge 1.12.2 版 Railcraft**（version 12.1.0-beta-8，`gradle.properties:5`；MC 约束 `[1.12.2,1.13)`，`src/main/java/mods/railcraft/common/core/Railcraft.java:54`）。速览卡片标题 "Railcraft Reborn / NeoForge" 有误。本报告因此恰好是"一个内容铺得很宽的老 mod 如何组织代码、背了哪些历史包袱"的一手样本。

## 1. 基本信息

- mod_id：`railcraft`（`src/main/java/mods/railcraft/common/core/Railcraft.java:53`）
- 作者/维护者：CovertJaguar（README.md；每个文件头 `Copyright (c) CovertJaguar, 2011-2020`）
- 许可证：私有 "Railcraft Mod License"（`LICENSE.md:1-25`）——源码公开但禁止分发修改版；关键例外：**API 按 MIT 自由使用**（`LICENSE.md:5`），addon 可借此盈利（`LICENSE.md:19`）——这是它 addon 生态的法律基础
- 目标平台：**Forge**（不是 NeoForge）：依赖 `forge@[14.23.5.2779,)`（`Railcraft.java:41`），映射 MCP（`build.gradle:70`）
- Gradle 插件：ForgeGradle `2.3-SNAPSHOT`（`build.gradle:18`，`apply plugin: 'net.minecraftforge.gradle.forge'` 于 26 行）+ cursegradle 发布插件（22-24 行）
- 工程结构：单 Gradle 工程、四个源根：`src/main/java`、`src/api/java`（vendored 第三方 API）、`src/test/java`、`extras/`（死代码与美术草稿，不进编译）。
- API 本体在**独立仓库 `api-railcraft/`**，经 `apply from: 'api-railcraft/gradle.properties'`（`build.gradle:28`）与 `dirApi`（50 行）接入，本检出缺失该目录（见第 2 节）
- Java 版本：1.8（`build.gradle:30`）
- 发布坐标：group `com.headlamp-games`、artifact `railcraft`（`build.gradle:32-33`）；产物 jar/devJar/apiJar/apiSourceJar 四件（`build.gradle:451-455`），主 jar 清单声明 AT：`FMLAT: railcraft_at.cfg`（346-350 行）

## 2. 源码规模与包结构

实测（`find` + `wc -l`）：全仓 1485 个 `.java`，其中真实代码 1483 个（另 2 个是 `.idea/` 模板文件）；`src/` 下 1442 个、共 **134,526 行**。卡片写的"140,874 行 / broken 33 个"复核不符（extras/code/broken 实测 29 个文件），以实测为准。

| 源根/包 | 文件数 | 说明 |
|---|---|---|
| `src/main/java/mods/railcraft/common` | 1122 | 服务端+公共逻辑主体 |
| `src/main/java/mods/railcraft/client` | 190 | 渲染、GUI、proxy |
| `.../common/blocks` | 431 | 最大包：方块 + TE + logic |
| `.../common/util` | 168 | 自研基础设施（network/charge/routing/…） |
| `.../common/gui` | 101 | GUI 容器/界面 |
| `.../common/plugins` | 100 | 对 Forge 与第三方 mod 的适配层 |
| `.../common/items` | 93 | 物品 |
| `.../common/carts` | 92 | 矿车实体与编组 |
| `.../common/modules` | 35 | 模块系统（29 个 Module 类） |
| `.../common/worldgen` | 29 | 矿脉/地形生成 |
| `.../common/fluids` | 21 | 流体（仅 CREOSOTE/STEAM 两种，`fluids/RailcraftFluids.java:49-64`） |
| `.../common/core` | 16 | 入口、配置、对象容器 |
| `src/api/java` | 119 | 全是 **vendored 第三方 API**（thaumcraft/atomicstryker dynamiclights），不含 Railcraft 自己的 API |
| `src/test/java` | 11 | 纯 JUnit 工具类测试 |
| `extras/` | 41 | 29 个 broken 代码 + 美术脚本 |

最大的源文件（实测 `wc -l`，均在 `src/main/java/mods/railcraft/` 下）：
`common/carts/EntityTunnelBore.java` 1170、`common/carts/EntityLocomotive.java` 894、
`common/util/charge/ChargeNetwork.java` 859、`common/core/RailcraftConfig.java` 725、
`common/blocks/tracks/outfitted/TrackKits.java` 649、`common/blocks/RailcraftBlocks.java` 625、
`common/carts/Train.java` 590、`common/util/routing/RoutingLogic.java` 577、
`common/modules/ModuleFactory.java` 565、`common/blocks/tracks/outfitted/BlockTrackOutfitted.java` 551、
`common/blocks/logic/StructureLogic.java` 532、`common/util/inventory/InvTools.java` 531。

**源码树不完整声明**：`api-railcraft/`（公共 API + 部分运行时基类，如 `EntityMinecartContainer`、`TrackRegistry`、`Charge` API）缺失——`src/main` 有 **653 处 `import mods.railcraft.api.*`**（实测 grep），覆盖 10 个 api 子包（carts/charge/core/crafting/events/fuel/helpers/items/signals/tracks），单拉本目录不能编译。资源同理：`src/main/resources` 只剩 `META-INF/railcraft_at.cfg` 与 3 个 txt，**没有 assets/lang/recipes JSON**，本报告不引用任何资源 JSON。客户端包 190 个文件分布在 `client/{render,gui,core,particles,emblems,util}`，其中 TESH 类渲染器（如 `client/render/tesr/TESRSignals.java`）与模型构建依赖的 JSON 均不在本检出，客户端部分只能按代码结构描述。

## 3. 入口与注册

入口类 `mods/railcraft/common/core/Railcraft.java`：老式 `@Mod` + `@Instance` 单例 + `@SidedProxy`（57-60 行），构造器里即把静态类挂上事件总线：

```java
@Mod(modid = Railcraft.MOD_ID, ..., certificateFingerprint = "a0c255...",
        guiFactory = "mods.railcraft.client.core.RailcraftGuiConfigFactory", ...)
public final class Railcraft {
    @Instance(Railcraft.MOD_ID) public static Railcraft instance;
    @SidedProxy(...) public static CommonProxy proxy;
    public Railcraft() { MinecraftForge.EVENT_BUS.register(RailcraftSoundEvents.class); }
```

preInit 的核心动作只有一个：**把整个 mod 交给自研模块系统**——`RailcraftModuleManager.loadModules(event.getAsmData())`（`Railcraft.java:111`），随后 `RailcraftConfig.preInit()`、`PacketHandler.init()`、`Metal.init()`（114-119 行）。init 阶段 `TrackRegistry.TRACK_TYPE/TRACK_KIT.finalizeRegistry()` 冻结运行时注册（130-131 行）；`FMLServerStartingEvent` 注册根命令（152-156 行）。

注册方式**不是 DeferredRegister**，三件套：
1. **模块扫描用 Forge 运行期 ASMDataTable**：`asmDataTable.getAll(@RailcraftModule 全名)` → `Class.forName + newInstance`（`modules/RailcraftModuleManager.java:56-68`）；实测 29 个文件带该注解，即 `modules/` 包下全部 29 个 `Module*` 类。
2. **内容注册用"枚举容器 + BlockDef 建造器"**：`blocks/RailcraftBlocks.java:83` 是 133 个枚举常量的 enum，常量携带 `BlockDef.build(tag, class).item(...).condition(...)`（84-107 行示范阶梯/ slab 依赖 condition）；`items/RailcraftItems` 73、`carts/RailcraftCarts` 34、`tracks/outfitted/TrackKits` 24、`tracks/behaivor/TrackTypes` 7 个常量（实测 grep）。底层落 `plugins/forge/RailcraftRegistry`（`ForgeRegistries` + `GameRegistry.registerTileEntity`，`RailcraftRegistry.java:93`）。
3. **生命周期由模块驱动**：`modules/RailcraftModulePayload.java:71-102` 在 CONSTRUCTION→PRE_INIT→INIT→POST_INIT 四阶段依次 `register()` → `defineRecipes()` → `finalizeDefinition()`；配方遍历用 `definedContainers` 集合去重（87-93 行，经 `modules/RailcraftModuleManager.java:50`）；`add()` 只允许 LOADING 阶段否则抛异常（`RailcraftModulePayload.java:39-43`）。模块依赖做拓扑排序定加载序（`RailcraftModuleManager.java:161-179`）。

事件订阅点：`MinecartHooks` 一组 `@SubscribeEvent`（`carts/MinecartHooks.java:90-457`）、`TokenManager` 的 WorldTick（`blocks/machine/wayobjects/signals/TokenManager.java:50-52`）、IMC 事件（`Railcraft.java:87-99`）。

**老代码血统点名（回答③）**：`@Instance/@SidedProxy`（`Railcraft.java:57-60`）、三幕式 FML 事件（110-150 行）、静态 `Configuration`（`RailcraftConfig.java:89-113`）、`@SideOnly` 212 处（实测 grep）、`updateJSON` 指自家 http 站点（`Railcraft.java:40`）、ForgeGradle 2.3 + jcenter + `http://` maven（`build.gradle:6,10`）。最典型的化石是 `core/Remapper.java:36-77`：用 `MissingMappings` 事件把历次改名（`track_abandoned→TRACK_FLEX_ABANDONED`、`brick_(.*)→$1` 正则表）硬编进静态块——1.7 ID 制留下的存档兼容债。迁移到现代加载器时这些全要重写：DeferredRegister 化 6 张枚举、删旧映射器、Configuration→ModConfig——后来的 Reborn 分支确实把工程整个推倒（另仓，本检出未验证）。

**内容规模账（回答④）**：全部命名对象只有 6 张枚举容器 ≈ 273 个常量，命名规范为 `railcraft:snake_case` tag，registry 名与翻译键由 tag 统一派生（`RailcraftBlocks.java:520-522`）。爆炸点靠三招压住：组合系（轨型×套件、Metal×形态、`BlockGeneric/ItemMaterial` 杂物袋方块）、变体内置（`IVariantEnum`，`core/RailcraftObjects.java:37-50` 统一遍历 block×variant）、模块条件（不满足 condition 的对象干脆不实例化，`RailcraftBlocks.java:540-542`）。登记规范一句话：**先进枚举（声明）、再挂模块（归属）、后三阶段落 registry（时序）**。

## 4. 核心系统

### 4.1 车辆与编组（回答①前半）
车辆是**纯实体**，不是"方块+实体"混合：`CartBase extends EntityMinecartContainer`（`carts/CartBase.java:72`，基类在缺失的 api-railcraft），移动沿用原版矿车沿轨逻辑，转向读方块形态（`blocks/tracks/TrackTools.java:79-103`）。大型车辆（钻探机 1170 行）仍是实体侧，用"主实体 + `EntityTunnelBorePart[]` 复合碰撞盒部件"撑体积（`carts/EntityTunnelBore.java:184-210`，部件自带 `getCollisionBoundingBox`，`EntityTunnelBorePart.java:50`）；维护类车直接以代码铺轨（`CartBaseMaintenance.java:210` `TrackToolsAPI.placeRailAt`）。
编组（Train）是**世界级聚合对象**：`Train` 持 UUID 成员表（`carts/Train.java:47-58`），存进 `Train.Manager`——挂在 `world.getPerWorldStorage()` 上的 `WorldSavedData("railcraft.trains")`（489-497 行）；每辆车 NBT 只存 `rcTrain` UUID（48、155 行），车与车的链扣也只是互存对方 UUID（`LinkageManager.java:64-75,173-190`）。
**跨区块存活**由此而来：成员实体随各自所在 chunk 存盘，编组组成存在世界数据里，半列车进未加载区不会撕裂编组；`Manager.tick()` 惰性清理失效成员（508-518 行），断链以"更长的一方"为准重建（`repairTrain`，192-193 行）。需持续加载的机车/钻探车走 Forge 票据（`util/misc/ChunkManager.java:24-40,147-151`）。

### 4.2 轨道方块（回答①后半）
轨道是**方块+TE 混合体**：`BlockTrackOutfitted extends BlockTrackTile<TileTrackOutfitted>`（`blocks/tracks/outfitted/BlockTrackOutfitted.java:70`），用 **ExtendedBlockState 的 unlisted property** 把"材质轨型×功能套件"塞进方块状态：listed 的 `SHAPE/TICKING` 之外，`TRACK_TYPE/TRACK_KIT/STATE` 均为 `IUnlistedProperty`（74-78 行），TE（`TileTrackOutfitted` + `TrackTileFactory`）持套件实例。7 轨型 × 24 套件只占 1 个方块类，互配配方由 `defineRecipes()` 对 `TrackRegistry.getCombinations()` 笛卡尔积自动生成（91-98 行）。
道岔/激活不做寻路：套件（Activator/Control/OneWay/Locking…）在车辆压过该格时改写下一格 shape（`TrackTools.setTrackDirection`，114 行）；轨既是电荷节点也是信号检测源（`BlockTrackOutfitted.java:72` CHARGE_SPECS）。轨道路径本身**没有缓存**——因为根本没有路径计算，车按局部规则走，全局调度交给信号令牌（4.4）。

### 4.3 多块结构：高炉/焦炉/锅炉/储罐（回答⑤）
每种多块机器的每个 TE 持一个 `StructureLogic`（`blocks/logic/StructureLogic.java:58`）。**数据表示**：`StructurePattern` 是代码里手写的 `char[][][]`（`blocks/structures/StructurePattern.java:37-67`，Builder 于 244-328 行），字符语义 `A`=空气、`B/W`=必须同方块、`O`=任意非己、`*`=任意（`StructureLogic.java:334-355`）。**何时算**：只有 `isPotentialMaster` 的方块在 `updateServer()` 里测试（244-253 行）；状态机 UNTESTED/VALID/INVALID/UNKNOWN（526-531 行），遇未加载区块记 UNKNOWN、用 `RECHECK=40` tick 计时器退避重试（59、246 行），避免每 tick 全量扫描。**缓存失效**：成员方块变化时 `onBlockChange()` 沿"同 structureKey 的逻辑"BFS 扩散 `spreadChange`，途经节点打回 UNTESTED 并回溯 master 再外扩，访问集以 maxSize 封顶（367-391 行）。**破坏降级**：pattern 测试失败 → master 复位、`spewInventory` 喷出容器内容（305 行；非 master 换 pattern 时同喷，177-181 行），方块本身保留、只退回单块形态。**跨端**：客户端不跑结构，master 把 state/marker/patternIndex/posInPattern 写进 TE 同步包（465-474 行）；客户端收到 VALID 却查不到 master 时反发 `PacketTileRequest` 重拉（237-240、492-494 行）。功能逻辑挂在与结构树分离的 `kernel` 树上（66 行注释、132-147 行），仅 master 激活——高炉的烧炼逻辑因此只写一份。

### 4.4 信号与路由
闭塞区间用令牌环：`TokenRing`（`blocks/machine/wayobjects/signals/TokenRing.java:34`）登记在又一个 `WorldSavedData` 承载者 `TokenManager.TokenWorldManager`（`TokenManager.java:32-55,113-119`）——与 Train.Manager 同一套"世界级聚合"手法。
- 信号机基类 `TileSignalBase extends TileMachineBase implements IAspectProvider, ITileRotate, ITileLit`（`signals/TileSignalBase.java:35`），双头信号另有 `IDualHeadSignal`；`wayobjects/boxes/` 11 个 Tile（Controller/Receiver/Relay/Interlock/Capacitor/Sequencer/Analog/ActionManager…）构成信号逻辑盒网络。
- _aspect_ 枚举与交换协议在 `api.signals.SignalAspect`（api-railcraft，本检出未验证其色灯表），主仓只做"提供方 + 消费者"。
- 路由表是一枚**小型解释器**：`RoutingLogic` 把 GUI 写的文本行解析成 IF/NOT/AND 表达式树（`util/routing/RoutingLogic.java:45-261`），机车过路由轨时 `evaluate(tile, cart)` 返回路由槽位号（109 行），解析错误带 ToolTip 反馈给玩家（169-184 行）。
- 数据驱动程度低（自定义 DSL，非 JSON），但对玩家可编程性极高；机车模式/速度等状态用 `IStringSerializable` 枚举落 NBT（`carts/EntityLocomotive.java:812,823`）。

### 4.5 电荷（Charge）网络
世界级 `ChargeNetwork`：节点表 + 变更队列（`util/charge/ChargeNetwork.java:58-59`）。
- **什么时候算**：每 tick 从队列消费，**硬限 500 节点/tick**（82-96 行）；新节点入网时反向扫邻居并网（98-104 行），随后 `grids.removeIf(invalid)` + 逐 grid tick（106-108 行）。
- **连通规则**：静态矩阵 `CONNECTION_MAPS`（ConnectType → 相对向量 → 允许的对方 ConnectType 集合，56、114-129 行）——"什么能接什么"是数据表不是 if-else。
- **图的增删**：加节点时原格若有活跃 grid 直接并入，否则新建（135-158 行）；删节点整 grid 销毁重建（161-166 行）——**无增量分裂算法**，拆一段电网代价是全区重算（老代码的偷懒点，明确记录）。
- **记账**：电池账本进 WorldSavedData（141-145 行），用电器 `startUsageRecording(ticksToRecord, consumer)` 按采样窗口记平均负载（566 行），电荷不足通过 `zap` 电伤玩家（645 行）。FE 互转靠 `blocks/logic/ChargeToFEAdapterLogic` 组件挂在需要的 TE 上。

### 4.6 方块实体基类族与逻辑组件（自研框架，回答②）
TE 是薄壳，行为树才是主体：
- 继承链：`TileRailcraft extends TileEntity`（`blocks/TileRailcraft.java:55`，实现自研 `INetworkedObject<RailcraftInputStream, RailcraftOutputStream>`，同步协议内建于基类）→ `TileRailcraftTicking` → `TileLogic`（`blocks/TileLogic.java:55`，实现 `ISmartTile, IActionReceptor, ILogicContainer, ITileCompare`）。
- 行为组件：可组合的 `Logic` 树（`blocks/logic/Logic.java:48-92`：children 列表 + `getLogic(Class)` 按接口查询 + `update()/interact()/writePacketData()` 生命周期广播），约等于自研 ECS；30 余个现成 Logic 组件在 `blocks/logic/`（实测 38 个文件，含 Logic 基类与 BlastFurnaceLogic、BoilerLogic、ChargeLogic、FluidPushLogic、ItemPullLogic 等）。
- 查询门面：`TileManager`（`blocks/TileManager.java:39-60`）"按接口探测方块对应 TE 类再执行动作"，内部带 classMapper 缓存；方块侧同构，`BlockContainerRailcraft(Subtyped)` 把"方块类↔容器枚举项"封成双向映射。
- **取舍**：换来内容 mod 需要的横切能力（同步、结构、GUI、比较器输出都做成可插 Logic 组件，一台机器 = 若干 Logic 的装配表），付出的是新人上手成本、调试栈穿透层数、以及每个现代 API（BlockEntity capabilities、attachments）出现时都要重做一遍适配——这正是老框架 mod 迁移时代价的最大来源。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络**：单通道 `FMLEventChannel`，频道名只有俩字 `"RC"`（`util/network/RailcraftPacket.java:23`；`PacketHandler.java:35` 用 `NetworkRegistry.newEventDrivenChannel` + 自身 `@SubscribeEvent` Server/ClientCustomPacketEvent 接收，37-53 行）。分发是手写字节 ID + switch：`PacketType[] packetTypes = PacketType.values()`，包体首字节直接下标反查枚举再逐类 new（`PacketHandler.java:32,59-97`）；21 个包类同目录平铺。序列化用自研 `RailcraftInputStream/OutputStream` 包 `ByteBufInputStream`。TE 同步协议自研：`INetworkedObject` + `PacketTileRequest/PacketTileExtraData` 推拉双工。GUI 交互也是包协议：`PacketGuiReturn/PacketGuiInteger/PacketGuiString/PacketGuiWidget` 四件套对接 `IGuiReturnHandler`（机车等实体直接实现该接口，`carts/EntityLocomotive.java:85`）。无 SimpleChannel/payload 注册制——纯 1.12 遗产。

**数据驱动程度**：配方与机器燃烧**全代码驱动**——高炉/焦炉/碎石机配方在模块 init 用建造器硬编（`modules/ModuleFactory.java:77-92` blastRecipe；133-155 行 rock crusher，输出带概率 `addOutput(stack, 0.25f)`），且受配置开关（99 行 `getRecipeConfig`）与内容可用性 condition 双向门控。自研配方类型集中于 `util/crafting/`（23 个类：BlastFurnaceCrafter、RockCrusherCrafter、CompoundIngredient、ModuleCondition、OreTagCondition、RecipeBuilder 等），序列化器在 api-railcraft（未验证）。世界生成配置驱动较深：`worldgen/OreGeneratorFactory.java:53-267` 以 Configuration + 维度 provider 黑名单 + BiomeDictionary 黑白名单批量造 GeneratorMine/RuledGenerator/Diffuse。流体燃料等外部投喂走 IMC 字符串键：`"fluid-fuel"`（`ModuleCore.java:401`）、`"ballast"`（`carts/ItemTunnelBore.java:54`）、`"rock-crusher"`（`ModuleFactory.java:470`）。矿脉无 JSON，全部 cfg + 代码。

**配置**：5 个静态 `Configuration` 文件（railcraft/blocks/items/entities/client.cfg，`core/RailcraftConfig.java:89-113`，全文 725 行）+ **每个模块一个 .cfg**（`RailcraftModuleManager.java:262-285`，禁用后果写进配置描述文案）。

**datagen**：无。grep `DataProvider|DataGenerator` 命中 0（实测）；1.12 时代资源 JSON 手写，且不在本检出。

## 6. Mixin / ASM / 接口注入

- **无 Mixin、无 coremod**：全仓无 mixin 配置；grep `IFMLLoadingPlugin` 命中 0（实测）。
- **Access Transformer**：`src/main/resources/META-INF/railcraft_at.cfg` 共 15 行，集中在原版矿车与玩家：`EntityMinecart field_70500_g # MATRIX`（矿车渲染矩阵，11 行）、`EntityMinecart.isInReverse`、`EntityMinecartFurnace.fuel`、`TileEntity.REGISTRY`、`NBTTagList.tagList` 等——靠提权直读原版字段实现车辆姿态与燃料同步，这是没有 Mixin 年代的"接口注入"。
- **编译期注解处理器：没有**（回答②）。`compileJava` 显式 `-proc:none`（`build.gradle:304-308`），注解全走 Forge 运行期 ASMDataTable 扫描（`RailcraftModuleManager.java:56-68`）与反射读取（`getAnnotation`，88-91 行）。API 单例注入用反射工具：`Code.setValue(Crafters.class, null, BlastFurnaceCrafter.INSTANCE, "blastFurnace")`（`ModuleFactory.java:72-74`）。任务书提到的 annotations/processor 模块属 Reborn 重写版，本代不存在；取舍是"一个 jar 通吃、零构建期代码生成"，代价是拼写错误延迟到运行时才炸。
- **替代"防篡改"手段是 jar 签名而非字节码注入**：`@Mod(certificateFingerprint=...)` + `FMLFingerprintViolationEvent` 直接抛错（`Railcraft.java:37,101-107`），签名任务 `JarSigner` 挂在构建尾（`build.gradle:360-392`）——当年用签名护城，而不是 Mixin 改引擎。

## 7. 值得学的 5 条

1. **阶段闸门防注册乱序**——`modules/RailcraftModulePayload.java:39-43`：对象与功能域的绑定只允许 LOADING 阶段，越界即抛带说明的异常。47 种内容类型最容易死在"谁先注册"，用异常把时序写死比文档约定可靠。
2. **聚合状态放 WorldSavedData、实体只存 UUID 引用**——`carts/Train.java:489-497` + 48 行。编组/门派/法阵这类多实体聚合体若把状态存成员 NBT，一半成员 unload 就撕裂；世界级 Manager + 惰性清尸（508-518 行）是通用解。
3. **结构缓存失效 = BFS 扩散 + 退避重测**——`blocks/logic/StructureLogic.java:367-391` 沿同类逻辑扩散 UNTESTED（maxSize 封顶）+ 244-253 行（仅 potential master 测、UNKNOWN 走 40-tick 计时器）。大规模多块结构 mod 的性能命门就在这两处。
4. **图网络的每 tick 变更预算**——`util/charge/ChargeNetwork.java:82-96`：增删节点先入队，tick 限处理 500 个。玩家一次性放 5000 格电网不会卡死服务器；灵脉网/物流网同理。
5. **组合正交化压注册**——`blocks/tracks/outfitted/BlockTrackOutfitted.java:74-78,91-98`：材质×功能用属性+TE 承载成 1 个方块类，配方对笛卡尔积自动生成。对"法器：材质×品阶×符文"这类组合内容思想仍然成立；但 1.20.1 已无 ExtendedBlockState 对应物，**抄思想不抄 API**。

**给「求仙问道」(Forge 1.20.1) 的结论（回答⑥）**。可搬两条：
(1) 功能域(module)分层 + 四阶段对象生命周期——即便不搬反射扫描，也搬 construction→preInit 注册→init 配方→postInit 收尾的三段推进（`RailcraftModulePayload.java:71-102`）与 definedContainers 去重（`RailcraftModuleManager.java:50`）：47 类内容平铺进 RegistryEvent 后配方依赖内容对象的时序迟早失控，这条流水线证明了能跑十年。
(2) 世界级聚合三件套：WorldSavedData 存聚合 + 成员存 UUID + 每 tick 限量维护 + BFS 失效传播（上文 2/3/4 条的组合），宗门、护山大阵、灵脉网络全部适用。
别学两处：
(1) **静态上帝容器**——`core/RailcraftConfig.java:89-125`（725 行静态可变配置字段，任何类随处读写）与 `core/Remapper.java:36-77`（把历次改名史硬编进静态块）：1.20.1 有 ModConfig + datagen，不要再造"知道全部历史"的类。
(2) **枚举下标当线上协议**——`util/network/PacketHandler.java:32,59-66`：`packetTypes[packetID]` 直接下标分发（66 行），前面只判 `packetID < 0`（62-63 行）不判上界，枚举顺序一变即协议错乱；现代 Channel/payload 注册制下这是纯负债。

## 8. 公开 API（addon 生态）

- **API 载体**：独立仓库 `api-railcraft/`（本检出缺失！）。发布时 API 类重打包进主 jar（`build.gradle:313-315` `from sourceSets.api.output`，330-332 行连 IC2 energy API 一并内嵌），另出 `apiJar/apiSourceJar` 供 addon 编译（394-412 行）。许可证上 API 部分按 MIT 自由使用（`LICENSE.md:5`）——addon 生态的法律+工程双支柱。
- **入口包**（由本仓 653 处 import 反推其公开面）：`mods.railcraft.api.core`（`RailcraftModule` 注解、`IVariantEnum`、`CollectionToolsAPI`）、`api.carts`（`ILinkableCart/IMinecart/ILinkageManager`，addon 可造可链车辆）、`api.tracks`（`TrackRegistry/TrackType/TrackKit`，init 前开放、`Railcraft.java:130-131` finalize 后关闭）、`api.charge`（`Charge/IBattery`）、`api.signals`（`SignalAspect/ITokenRing`）、`api.crafting`（`Crafters` 四台机器的配方接口，`ModuleFactory.java:12-14`）、`api.fuel/items/events/helpers`。
- **扩展点三件套**：① IMC 字符串键处理器——无编译期依赖即可投喂燃料/弹石/配方（`core/InterModMessageRegistry.java:20-27` + `Railcraft.java:87-99`，坏消息打 FATAL 日志再抛，95 行）；② 运行时 Registry（轨型/套件在 finalize 前开放）；③ 注解模块——addon 自己打 `@RailcraftModule` 即可被 ASMDataTable 扫进模块管线（`RailcraftModuleManager.java:56-68`），享受同一套阶段时序。
- **集成面**：`common/plugins/` 100 个文件按第三方 mod 一子包（forestry/ic2/thaumcraft/buildcraft/jei/dynamiclights/multipart），依赖全 compileOnly（`build.gradle:183-198`），缺 mod 时由模块 prerequisites 自动禁用（`RailcraftModuleManager.java:125-131`）；对外命令树统一挂 `/railcraft` 根命令（`Railcraft.java:55,154-155`）。

---
复核记录：全文数字均出自本次 find/grep/wc 与逐文件读取；卡片中"140,874 行、broken 33、Railcraft Reborn/NeoForge"三处与实测不符，已按实测修正。api-railcraft 内部实现与 Reborn 版注解处理器为"未验证"（目录缺失）。
