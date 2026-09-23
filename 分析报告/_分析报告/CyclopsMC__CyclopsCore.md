# Cyclops Core 源码分析报告

> 本地树: `源码库\_参考仓库\_bulk\CyclopsMC__CyclopsCore`,git HEAD `50dcfd8`(2026-09-11,"Bump mod version")。
> **重要版本警示**: 本地检出是 mod 1.31.0 / MC 26.1.2 的多加载器新架构,**不是**读者在 1.20.1 生态里见到的单模块 Forge 版 CyclopsCore;凡是"1.20.1 时代行为"的推断一律标注未验证。文中路径均相对仓库根。

## 1. 基本信息

- **mod_id**: `cyclopscore`;作者 `rubensworks (aka kroeser)`;许可证 MIT(根 `LICENSE.txt`,与速览卡片一致)。
- **目标 MC 与加载器**(出处 `gradle.properties:3-40`): MC `26.1.2`,NeoForge `26.1.2.22-beta`,Forge `64.0.4`,Fabric loader `0.18.5` + Fabric API `0.146.1+26.1.2`,mod 版本 `1.31.0`,**Java 25**(`java_version=25`,`buildSrc/src/main/groovy/multiloader-common.gradle:86` 用 toolchain 钉死)。
- **Gradle 插件与工程结构**: 根 `build.gradle:12-17` 声明 fabric-loom `1.15-SNAPSHOT`、neoforge moddev `2.0.141`、MinecraftForge gradle `[7.0.21,8.0)`、accesstransformers、curseforgegradle、modrinth minotaur。`settings.gradle:67-70` 切 4 个模块:`loader-common`(加载器无关主体)、`loader-fabric`、`loader-forge`、`loader-neoforge`。多加载器切法是 **MultiLoader-Template 的"源码注入"式**(注释自认:`buildSrc/src/main/groovy/multiloader-loader.gradle:1`):`loader-common` 用 `commonJava/commonResources` 两个 consumable configuration 导出源目录(multiloader-loader-common.gradle:24-38),每个 loader 模块把这些目录直接 `source()` 进自己的 compileJava(multiloader-loader.gradle:28-31)——公共码**编进每个 jar**,不做 shading。另有 `extra-mods/` 目录自动平铺为 runtime 依赖(multiloader-loader-neoforge.gradle:8-35,自称受 AE2 启发)。
- **发布坐标**: group `org.cyclops.cyclopscore`,artifactId 由 `archivesName = "${mod_id}-${minecraft_version}-${loader名}"` 生成(multiloader-common.gradle:82),maven-publish 推到 env `MAVEN_URL`/filesmaven 私有仓(multiloader-common.gradle:199-228)。

## 2. 源码规模与包结构

实测(本轮 `find`/`wc`,修正速览卡片的 69,907 行):**761 个 .java,共 69,146 行**。分布:

| 模块 | main 文件/行 | test 文件/行 |
|---|---|---|
| loader-common | 258 / 17,737 | 0 |
| loader-neoforge | 290 / 22,901 | 87 / 23,225 |
| loader-forge | 59 / 2,854 | 0 |
| loader-fabric | 67 / 2,429 | 0 |

测试全部集中在 neoforge 模块且占全库 1/3 行数(33.9%),这是底座库"用测试锁行为"的信号。主要包(loader-common main,按文件数):`config` 61(注册+配置合体,见 §4/§5)、`helper` 39、`inventory` 33、`client` 27、`block` 19(含多方块 `block/multi` 14 文件)、`network` 16、`command` 11、`datastructure` 9、`advancement` 7、`persist` 6。loader-neoforge main:`ingredient` 54(6,495 行)、`infobook` 47、`nbt` 37(`nbt/path` NBT 路径查询)、`helper` 25、`config` 19、`metadata` 9。loader-fabric 特征包:`mixin` 14、`events` 12(手写 Fabric 事件回调接口)。loader-forge 特征包:`config` 18、`mixin` 4。

最大 main 源文件:IngredientStorageHelpers **1,255**、InfoBookParser **756**、NBTClassType **670**、ContainerExtended **533**、ScreenInfoBook **527**、PacketCodecs **494**、InfoSection **471**、CubeDetector **471**、ModBaseNeoForge **441**、CapabilityConstructorRegistry **335**、DeferredHolderCommon **320**、SimpleInventory **299**(路径见 §4~§5 各处引用)。

**树完整性**: 稀疏检出缺资源——各 loader 的 `src/main/resources` 只剩 `META-INF/*.mods.toml`,`neoforge.mods.toml:17` 引用了 `mixins.${mod_id}.json` 但**该 mixin 配置 json 不在树内**(全库 find 无 `*mixin*.json`);lang/模型/datagen 产物同样缺失。根 `resources/` 只有 changelog。文本断言全部来自 .java 与 gradle 脚本,可靠;涉及 mixin 生效范围的判断受限。

## 3. 入口与注册

入口 `loader-neoforge/src/main/java/org/cyclops/cyclopscore/CyclopsCoreNeoForge.java:54-75`:`@Mod(Reference.MOD_ID)` 类直接**继承** `ModBaseNeoForge<CyclopsCoreNeoForge>` 自举类,构造器即完成一切:

```java
@Mod(Reference.MOD_ID)
public class CyclopsCoreNeoForge extends ModBaseNeoForge<CyclopsCoreNeoForge> {
    public CyclopsCoreNeoForge(IEventBus modEventBus) {
        super(Reference.MOD_ID, (instance) -> { _instance = instance; ... }, modEventBus);
        getRegistryManager().addRegistry(IInfoBookRegistry.class, new InfoBookRegistry());
```

父构造(`init/ModBaseNeoForge.java:85-117`)按序装配 proxy(客户端/服务端二选一,88 行)、configHandler、packetHandler、capabilityConstructorRegistry、IMCHandler,然后订阅事件:`FMLCommonSetupEvent→setup`、`NewRegistryEvent@LOWEST→afterRegistriesCreated`、`RegisterEvent@HIGHEST→beforeRegistriedFilled`、`RegisterGameTestsEvent`、客户端 `FMLClientSetupEvent`/`RegisterKeyMappingsEvent`(96-103 行),游戏总线挂 server 启停/命令(104-107)。注册抽象分三层:(a) MC 注册表延迟注册见 §4-1;(b) **逻辑注册表**(与 MC 无关的 mod 内注册)极简:`RegistryManager` 就是 `Map<Class<? extends IRegistry>, IRegistry>`(init/RegistryManager.java:12-40),infoBook/容器位置/exportable 元数据各占一个接口;(c) 引用侧 `DeferredHolderCommon`(config/DeferredHolderCommon.java:31)实现 `Holder<R>`,构造只存 ResourceKey、访问时才 bind(107-114、144-161)。事件订阅点全部收敛在 ModBase* 构造器,内容 mod 只需覆写 `onConfigsRegister`/`setup` 等模板方法(CyclopsCoreNeoForge.java:110-176 即活例)。

## 4. 核心系统

### 4-1. ExtendedConfig 注册底座(config 包,loader-common 61 文件)

**数据表示**: 每个要注册的东西(block/item/entity/gui/data component/loot function…共 35 种类型,ConfigurableTypeCommon.java:13-50 静态表)对应一个 `ExtendedConfigCommon<C,I,M>` 对象(extendedconfig/ExtendedConfigCommon.java:29),携带 namedId、惰性 `elementConstructor`(74-87 行首次 getInstance 时才 new 实例)、以及一个 `Map<String, ConfigurablePropertyData>` 用户可配置属性(42)。它是"配置对象兼注册描述符"的合体——名字里的 config 不是历史包袱而是设计本体。
**何时算**: `ConfigHandlerCommon` 把统一生命周期切成 4 个相位并逐 config 广播给类型专属 Action:构造期 `loadModInit`、`NewRegistryEvent` 后 `loadRegistriesCreated`、`RegisterEvent` 填表期 `loadRegistriesFilled`、`FMLCommonSetupEvent` 期 `loadSetup`(config/ConfigHandlerCommon.java:78-114;Action 相位定义 configurabletypeaction/ConfigurableTypeActionCommon.java:28-55)。真正的注册动作由 loader 侧 `registerToRegistry` 抽象(140-142 行)完成:NeoForge/Forge 把 (config, callback) 暂存进按 registry key 分组的 Multimap,等对应 `RegisterEvent` 到达时统一 `event.register(...)` 并回调,且**晚到即抛**(ConfigHandlerNeoForge.java:51-89;Forge 同构 ConfigHandlerForge.java:52-77);Fabric 没有分事件,直接同步注册(ConfigHandlerFabric.java:18-28)。block+blockitem 的顺序耦合由 BlockAction 处理:注册 block 时现场合成配套 ItemConfigCommon 并挂 callback 等 item 注册完才触发 `onRegistryRegistered`(configurabletypeaction/BlockAction.java:40-70)。
**跨端**: 该层纯启动期,无运行期流量;客户端专属部分走 `BlockClientConfig/ItemClientConfig/EntityClientConfig` 挂在同一 config 对象上按 side 取用。

与 DeferredRegister/Registrate 的取舍:DeferredRegister 要每个 registry 一个静态实例并记得 `register(bus)`,Registrate 是回调式 builder;ExtendedConfig 的收益是 (1) 引用与注册解耦——`DeferredHolderCommon` 允许"先拿 holder、注册事件随便何时",(2) 每个条目自动获得 config 文件属性 + 命令热改 + GUI 显示(见 §5-3),(3) 类型扩展点(加一种可注册物 = 写一个 Action + 一个 Config 子类,ConfigurableTypeCommon.java:104 `setAction` 还能整段替换)。**代价**是每注册一个 block 要继承 3 层泛型类并重写 `getConfigurableType/getTranslationKey/getRegistry`(BlockConfigCommon.java:28-40 构造签名 4 个泛型/函数参数),样板比 DeferredRegister **多**而不是少,外加反射收集注解属性的隐式约定——见 §7/§8 的边界判断。

### 4-2. 容器与 GUI 抽象(inventory/container,loader-common 33 文件)

`GuiConfigCommon` 把一个 `MenuType` 注册进 `BuiltInRegistries.MENU`,并在 `onRegistryRegistered` 里客户端侧 `MenuScreens.register`(extendedconfig/GuiConfigCommon.java:40-53),配套 `IContainerFactoryCommon`(inventory/container/IContainerFactoryCommon.java:10-17)统一带 `FriendlyByteBuf` 的客户端构造。`ContainerExtended`(533 行)继承 `AbstractContainerMenu`,附带 phantom slot/快捷移动/按钮动作表(container/ContainerExtended.java:455-467 + `ButtonClickPacket`)。

### 4-3. ValueNotifier 定点同步(见 §5-1 网络细节)与 SyncedGuiVariable

`ContainerExtended` 实现 `IValueNotifier/IValueNotifiable`(container/ContainerExtended.java:36-37):`registerSyncedVariable(clazz, serverSupplier)`(527-531)登记任意可 NBT 化变量,`broadcastChanges` 每 tick 调各变量 `detectAndSendChanges`(79-86);变量实现见 §5-1。初始下发挂在 `addSlotListener → initializeValues`(97-112)。

### 4-4. 能力抽象层(loader-neoforge)

`modcompat/capabilities/CapabilityConstructorRegistry.java:33-58`:按 BE/Block/Entity/Item 四类暂存 (supplier, ICapabilityConstructor) 对,外加三个"按父类/MobCategory 泛匹配"的慢表(141-196 行,注释自认 less efficient);首次 `RegisterCapabilitiesEvent` 到达时 `bake()` 定型并禁止再注册(66-70、207-218),`baked` 后新事件也能重放。跨版本 API 抖动被挡在这里的**下面还是上面**?实测:该类 import 的是 NeoForge 原生 `BlockCapability/ItemCapability/RegisterCapabilitiesEvent`(12-20 行)——**新版 loader 原生能力 API 不被本层翻译,只被延迟收集**;真正挡抖动的是 CommonCapabilities 的 `IngredientComponent` 抽象(ingredient 包全部 import `org.cyclops.commoncapabilities.api.*`,IngredientStorageHelpers.java:8-11)和 data component 化(`component/DataComponentInventoryConfig.java` 等)。对 1.20.1 读者:此树的 capability 层形状可抄(延迟+按父类批量注册),但"能直接借用的 API"边界很窄,1.20.1 的老 CyclopsCore 用 Forge CapabilityHooks,形态完全不同(未验证,本树无该版本)。

### 4-5. NBTClassType 反射持久化(persist/nbt,NBTClassType.java 670 行)

`Class → NBTClassType` 注册表(NBTYPES,42 行起),按字段类型反射读写 NBT,供 `CyclopsBlockEntity` 的 `@NBTPersist` 字段自动存盘、以及 SyncedGuiVariable 的线格式(见 5-1)。26.x 下已迁到 `ValueInput/ValueOutput` 新 API(4-5 行 import)。

### 4-6. Infobook / metadata / advancement 等外设

infobook(47 文件)是数据驱动的 XML 说明书解析+渲染;metadata 的 `RegistryExportable*`(9 文件)把"注册表内容"导出给 `/cyclopscore dump_registries` 类命令;advancement 提供 3 个通用触发器(`RegistryEntriesCommon.java:19-21` 用 §3 的 holder 引用它们)。

## 5. 网络 / 数据驱动 / 配置 / datagen

**包注册与序列化**: `PacketBase<T> implements CustomPacketPayload`,静态 `getCodec(Supplier<T>)` 把 `write/decode` 包成 `StreamCodec.ofMember`(network/PacketBase.java:71-84),解码异常统一包装 `PacketCodecException`(76-80)。`PacketHandlerNeoForge` 构造期收集 `pendingPacketRegistrations`,`RegisterPayloadHandlersEvent` 时统一 `registrar.playBidirectional`,registrar 为 `versioned("1.0.0").executesOn(HandlerThread.NETWORK).optional()`;每个包自带 `isAsync()` 决定是否 `ctx.enqueueWork` 回主线程(network/PacketHandlerNeoForge.java:39-82)。发送侧 `IPacketHandler` 抽象 sendToPlayer/AllAroundPoint/Dimension/All(56-115),对 Forge/Fabric 各有一份实现——**跨加载器只抽象了分发,序列化完全共用 MC StreamCodec**。
**注解式字段编解码**: `PacketCodec` 反射收集 `@CodecField` 字段,且**显式按字段名排序**并注明原因("getDeclaredFields 顺序不保证,不排序 SMP 下会 class cast",network/PacketCodec.java:34-44)——一个值得记住的真坑。类型分派在 `PacketCodecs`:`Class → ICodecAction` 表,找不到就沿接口/父类上溯(42-62 行)。
**大包拆分/压缩策略**: 全库 grep 无 split/compress/gzip——**它不做分包也不压缩**。它的对策是三点:①值级 diff:`ContainerExtended.setValue` 先比对旧值,变了才发 `ValueNotifyPacket`,且按 side 双向路由(container/ContainerExtended.java:477-490);②变量级脏检测:`SyncedGuiVariable.detectAndSendChanges` 服务端每 tick 把 supplier 值写成 CompoundTag 与 `lastTag` 比对,不等才 setValue(container/SyncedGuiVariable.java:42-53)——这就是"脏集合+定点补发"的对应物,**粒度是 GUI 变量而非 slot**;slot 物品栈脏检测直接复用 vanilla `AbstractContainerMenu.broadcastChanges`(79-80 行 super 调用),没有另造。`ValueNotifyPacket` 载荷仅 (containerType, valueId, CompoundTag) 三元组,客户端校验 `player.containerMenu` 类型匹配才应用(network/packet/ValueNotifyPacket.java:29-63);③稀疏编码:List codec 只写非 null 项并带显式下标+`-1` 终止符,全 null 写 `__noclass` 哨兵(PacketCodecs.java:395-466);持久化侧 `LargeInventory.writeToNBT` 只存非空槽(LargeInventory.java:44-54)。26.x 树里 ItemStack codec 已用 `HashedStack`(340-351)。Map/Pair codec 把**类名字符串写上线再 Class.forName**(264-268、284 行)——能跑但等于信任对端类路径,反例。
**数据驱动与 Codec**: `ListCodecStrict`(loader-neoforge codec/ListCodecStrict.java:24+,复制 vanilla ListCodec 但"元素失败不许静默跳过"并聚合错误消息)是对 DFU 静默容错的标准补丁;`nbt/path`(37 文件)实现 NBT 路径查询供配方/条件用;infobook 是 XML 数据驱动。
**配置体系**: 声明 = 配置类上的 `@ConfigurablePropertyCommon` 注解静态字段(GeneralConfig.java:15-19 活例;注解定义 config/ConfigurablePropertyCommon.java:16-70:category/comment/isCommandable/requiresWorldRestart/min-max/showInGui/configLocation)。收集 = `ConfigHandlerCommon.generateConfigProperties` 沿继承链反射扫字段(148-177)。**loader 差异只挡在 `ConfigHandlerCommon.registerToRegistry + onConfigPropertyInit` 两个抽象方法以下**:NeoForge 用 `ModConfigSpec.Builder` 按 `ModConfigLocation→ModConfig.Type` 映射建 COMMON/CLIENT/SERVER/STARTUP 四份 spec(ConfigHandlerNeoForge.java:95-150);Fabric 干脆整层复用 ForgeConfig API Port(依赖 loader-fabric/build.gradle:14),ConfigHandlerFabric 只有 29 行。加载/热重载时 `syncProcessedConfigs→saveToField` 把值**反射写回静态字段**(159-167),`isCommandable` 的属性进 `/cyclopscore config get|set` 命令运行时改(command/CommandConfig.java:32-43,改完 set+save)。相比读者手写的 TOML config:省掉"声明-读取-落盘-重载"四份样板并白送热改命令与 GUI 标记;赔上反射魔法、静态字段可变性(测试必须重置)、类型安全只剩"默认值类型即 schema"。
**datagen**: 无。全树无 GatherDataEvent/Provider 类,lang/配方全靠运行时与 infobook 资源;资源缺失也佐证此库不产出 generated resources(multiloader-loader-neoforge.gradle:38 引用了 `src/generated/resources` 目录但目录不存在)。

## 6. Mixin / ASM / 接口注入

三处 mixin 包,合计 21 个类:fabric `mixin/` 14(如 MixinRegistry、MixinServerLevel、MixinPlayerList、MixinLootTable——Fabric 侧用 mixin 补事件缺口,配合 `events/` 包的 12 个手写回调接口)、forge 4、neoforge 3。已读的两例说明目的:(1) `loader-neoforge/.../mixin/MixinRegistry.java:12-40` 注入 `Registry#safeCastToReference` HEAD,把 `DeferredHolderCommon` 这类代理 holder 经 `IHolderCommon.getDelegate` 解包后再做 `Holder.Reference` cast——**§4-1 的惰性 holder 方案必须配一个 vanilla 注入点才成立**,注释明说这是把 NeoForge 自家 patch 换成统一路径;(2) `MixinPacketDistributor.java:15-21` 拦截发往 `test-mock-player` 的包以保 GameTest 不炸。另有反射注入两处:GameTest 环境注册表靠 `getDeclaredField("environmentsRegistry")` 硬取(ModBaseNeoForge.java:311-314,字段改名即断,属脆弱点);`PlayerRingOfFire` 是纯白名单彩蛋(event/PlayerRingOfFire.java:21-35)。注意 mixin 配置 json 不在本地树(§2),挂载点全集未验证。

## 7. 值得学的 5 条

1. **GUI 变量"diff→定点小包"双向同步**: `loader-common/.../inventory/container/ContainerExtended.java:477-490` + `container/SyncedGuiVariable.java:42-53`。任意复杂对象经 NBTClassType 序列化成 tag、逐 tick 比对、变化才发 (type,id,tag) 小包,初始值挂 `addSlotListener`(ContainerExtended.java:97-102)。求仙问道的灵气/境界面板、蜂群的群落状态 HUD 可直接照搬这个 30 行的形状,替代整屏广播。
2. **注册暂存-事件冲刷-迟到即抛**: `loader-neoforge/.../config/ConfigHandlerNeoForge.java:51-89`。按 registry key 分桶缓存待注册项,等 `RegisterEvent` 统一冲刷,过了事件再注册立刻抛 IllegalStateException——把"注册时机错"从偶发炸服变成启动期硬错。对"同一代码发多加载器"的读者,这个 Multimap 加 `registryEventPassed` 哨兵是三个 loader 共用一套注册时序的最小公共核。
3. **反射字段包编码的确定性排序**: `loader-common/.../network/PacketCodec.java:34-44`。用 `@注解` 字段自动收发时按**字段名**排序并留注释解释 getDeclaredFields 顺序不保证——任何打算写注解式包序列化的 mod 都会踩的坑,这里给出修法。
4. **ListCodecStrict**: `loader-neoforge/.../codec/ListCodecStrict.java:24-60`。复制 vanilla ListCodec、把"元素解码失败→静默降级"改成"聚合全部错误消息→硬失败",并保留 upstream 注释标 ADDED 行。这是对付 DFU optional/部分失败吞错的标准手法(与本机记忆 dfu-optional-field-swallows-errors 同一条教训的库内实证)。
5. **extra-mods 目录即装即跑**: `buildSrc/src/main/groovy/multiloader-loader-neoforge.gradle:8-35`。往 `extra-mods/` 丢 jar 自动成为 runServer/gameTestServer 的依赖(文件名解析 artifactId:version)。多加载器工程想"本地塞个依赖 mod 跑集成测试",这比写死 build.gradle 省事。

## 8. 公开 API

被依赖方式(本树实测):内容 mod 的入口类**必须继承** `ModBaseNeoForge<T>`/`ModBaseForge<T>`/`ModBaseFabric<T>`(T 为自身,自举泛型),即接入第一步是绑死它的 mod 基类;然后按模板方法覆写 `constructCommonProxy/constructClientProxy/constructModCompats/onConfigsRegister/constructBaseCommand`(ModBaseNeoForge.java:119-121、CyclopsCoreNeoForge.java:77-176)。每个可注册物再各继承一层 `XxxConfigCommon`(4 泛型,BlockConfigCommon.java:33-37),能力注册继承 `BlockEntityCapabilityRegistrar`(capability/registrar/BlockEntityCapabilityRegistrar.java:18-40,`populate()` 里 add 各 capability),GUI 容器继承 `ContainerExtended`(抽象 `getSizeInventory` 等,533 行基类)、方块实体继承 `CyclopsBlockEntity`(挂 NBTClassType 反射持久化)。**接入成本评价:高。** 为省注册样板,你要继承约 5~7 层基类、吃下 `IModBase` 全家桶(proxy/logger/registryManager/packetHandler 从 mod 实例上拿,IModBase.java:22-41),泛型参数密度远超 Registrate。它给底座 mod 族的真实价值不在单点 API,而在**"一族 mod 长得一样"**:同一生命周期、同一 config 命令面、同一包形状——这只有当你真有第二个、第三个 mod 要共享时才回本。反面账:1.20.1↔26.x 之间该库自身 API 剧变(能力→data component、单模块→四模块),说明这层抽象并未挡住 MC/加载器抖动,它只是把抖动集中进了底座库自己;追版本时底座变成瓶颈(其下游 IntegratedDynamics/EvilCraft 每次跟版本都要先等 CyclopsCore,此为本树之外的常识性判断,未验证)。

**给「求仙问道」自建底座的 3 条建议**:
1. **抄形状不抄骨架**: 把 §7-2 的"注册暂存-冲刷-迟到抛"和 §7-1 的 diff 同步两块(合计 <200 行)以自有工具类落进 1.20.1 工程;**不要**引入 ExtendedConfig 式"配置对象=注册描述符"的合体层——单 mod 阶段它只是把 DeferredRegister 变复杂,它的收益(35 种类型统一热配)要到第三个内容 mod 才出现。
2. **多加载器用源码注入而非依赖注入**: 若真要"同一份代码发 Forge+NeoForge",照抄 MultiLoader-Template 的 `commonJava` configuration 方案(§1,multiloader-loader.gradle:18-48),公共码编进各 jar;同时把 loader 差异**只**压在 `registerToRegistry`/config handler/包分发三个方法级抽象上(CyclopsCore 的 258/59/67 文件比例说明:合理设计中 loader 侧代码量约为 common 的 1/4~1/5)。
3. **远程行为开关进底座要设死边界**: `tracking/ImportantUsers.java:23` 服务端启动 HTTP 拉白名单控制游戏内效果(彩蛋用)。底座库留这种通道等于给作者一个远程开关,整合包环境(离线/内网)还会拖启动;若求仙问道要运营侧远配,配置项必须本地默认可跑、远配只做加法。
4. **(反面判断)不要建"包抽象层"**: CyclopsCore 的 `PacketBase/PacketCodec/PacketCodecs` 三件套(§5)在 26.x 已退化——真正发送全走 loader 的 `PacketDistributor` 与 vanilla `StreamCodec`,它只剩注解字段编码还在自我维持。1.20.1→1.21 迁移期自建"跨加载器网络抽象层"是最亏的一笔:两个加载器的 payload API 都还年轻,抽象层每个版本都要重写,不如每个 loader 各留一个 30 行的 send() 门面。

## 遗留与不确定性

- mixin 配置 json、lang、net.xml 等资源不在稀疏检出内(§2),mixin 全量清单未验证。
- 1.20.1 时代的 CyclopsCore 形态(单模块 Forge、CapabilityHooks)不在本树,相关对比句均标未验证。
- 速览卡片"761 个 .java,69,907 行"中文件数复核为 761(一致),行数实测 69,146(卡片偏差 ~760 行,以本报告为准);卡片"工程结构=single"与实测 4 模块不符,应以 `settings.gradle:67-70` 为准。
