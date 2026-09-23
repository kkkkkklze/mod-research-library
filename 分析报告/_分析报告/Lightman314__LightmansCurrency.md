# Lightman's Currency 源码分析报告

分析的仓库快照:`源码库\_参考仓库\_bulk\Lightman314__LightmansCurrency`(shallow clone,唯一提交 `2f882ed "26.1 rework part 2"`,sparse checkout)。
重要前提:这份树是 **MC 26.1.2 大重构中途版**,与整合包里实际跑的 1.21.1 时代发布版差异很大——税收、银行账户、ATM 完整流程、配方自动定价等在旧版存在,但本快照中要么被注释掉、要么尚未回填(下文逐节标注)。所有断言以本树为准。

## 1. 基本信息

- mod_id:`lightmanscurrency`(`gradle.properties:25`);显示名 "Lightman's Currency"(`:27`);作者 Lightman314(GitHub 仓库主)。
- 许可证:Apache License 2.0(`gradle.properties:29`,并经 `build.gradle:237` 展开进 `META-INF/neoforge.mods.toml`)。
- 目标平台:Minecraft 26.1.2、NeoForge 26.1.2.76(`gradle.properties:12,18`;版本范围 `[26.1.2,26.2)`,`:16`);加载器仅 NeoForge,无 Forge/Fabric 双载。
- Gradle 插件:`net.neoforged.gradle.userdev` 7.1.27(`build.gradle:4`),工程结构 single(单 module),`srcDir('src/generated/resources')` 接入 datagen 产物(`build.gradle:19-26`);含 `accesstransformer.cfg`(经 `minecraft.accessTransformers.file`,`build.gradle:68`)。
- Java 版本:toolchain Java 25(`build.gradle:64-65`),mixin `compatibilityLevel: JAVA_25`(`src/main/resources/lightmanscurrency.mixins.json`)。
- 发布坐标:group `io.github.lightman314.lightmanscurrency`、version `26.1-1.0.0.0`(`gradle.properties:31,35`),`maven-publish` 发布到项目内 `repo/` 目录(`build.gradle:248-259`)。
- 编译期依赖只有 NeoForge 本体;JEI/REI/Curios/Create/ComputerCraft 等全部依赖被注释(`build.gradle:138-221`)——本快照是"纯净核"。

## 2. 源码规模与包结构

实测:`src` 下 **604 个 .java、32,037 行**(`find + wc -l` 复核;速览卡片写 32,641,差 604 恰为文件数,应是"每文件补一行"的计数口径差异,以本报告实测为准)。

一级目录(文件数/行数):

| 目录 | 文件 | 行数 | 说明 |
|---|---|---|---|
| `api/` | 476 | 24,835 | 对外 API 与全部核心系统实现 |
| `features/` | 50 | 3,269 | 内建内容(钱包、物品商人、API 实现) |
| 根文件 | 3 | 1,203 | `LCConfig.java`(1,119)+ 主类 |
| `core/` | 33 | 1,152 | 各 DeferredRegister 与注册装配 |
| `datagen/` | 12 | 587 | 打进主 jar 的 datagen |
| `network/` | 15 | 479 | 自定义包框架与 6 个消息类 |
| `client/` | 10 | 383 | 客户端事件/代理 |
| `mixin/` | 5 | 129 | 全部是 UI 槽位补丁 |

api 主要子包(文件数):`api/trader` 128、`api/client` 54、`api/coins` 47、`api/helpers` 46、`api/config` 45、`api/world` 38、`api/money` 32、`api/ownership` 17、`api/upgrades` 14、`api/icon` 13、`api/codecs` 11、`api/text` 10、`api/bank_account` 8、`features/trader` 23、`features/wallet` 9、`features/api_impl` 9。

最大源文件(行数):`api/codecs/StreamHelper.java` 1151、`LCConfig.java` 1119、`api/config/ConfigFile.java` 704、`features/api_impl/CoinAPIImpl.java` 591、`api/coins/data/ChainData.java` 558、`api/trader/data/TraderData.java` 472、`api/money/values/MoneyValue.java` 344、`api/bank_account/BankAccount.java` 332、`api/helpers/data/PlayerReference.java` 286、`api/helpers/network/FancyPacketMap.java` 275、`api/coins/display/builtin/NumberDisplay.java` 264、`api/client/gui/helpers/FancyGuiExtractor.java` 261。

**树不完整声明**:sparse 白名单(`.git/info/sparse-checkout`)只收 java/gradle/properties/toml/mixins.json/yml/cfg/txt 等,**普通 `.json` 资源不在检出范围**:

- `src/main/resources/data` 实测仅剩 `computercraft/` 一个目录:lang、模型、配方、战利品等普通 JSON 全部缺失;
- `build.gradle:19-26` 声明的 `src/generated/resources`(datagen 产物)目录在本树不存在;
- `datagen/helpers` 包内只剩 package-info(`find` 实测)。

本报告不引用任何缺失 JSON 的内容,涉及"资源是否存在"的结论均限定在 Java 代码层面。

## 3. 入口与注册

主类 `LightmansCurrency.java:18-32`,构造器极薄:

```java
@Mod(LCApi.MODID)
public LightmansCurrency(ModContainer modContainer, IEventBus eventBus) {
    LCConfig.init();                          // :28 自研配置框架先起
    LCRegistrySetup.initialize(eventBus);     // :31 注册一切
}
@SubscribeEvent
private void commonSetup(FMLCommonSetupEvent event) {
    ConfigFile.loadServerFiles(ConfigFile.LoadPhase.SETUP);  // :38
    BuiltInPermissions.intialize();                          // :40
}
```

`core/LCRegistrySetup.java:13-54` 是唯一的注册总线,分三段:

1. 原版侧 8 个 DeferredRegister(Items/Blocks/BlockEntities/Sounds/CreativeGroups/DataComponents/MenuTypes/CommandArguments);
2. NeoForge 的 `ATTACHMENT_TYPES`(仅 1 个 wallet,见 4.5);
3. 20 余个 **mod 自有注册表**——`MoneyValueType`、`TradeDataType`、`TraderNodeType`、`PermissionType`、`FancyDataType`、`FancyPacketType` 等(`api/LCRegistries.java:33-110`,多数 `.sync(true)` 随网络同步注册表 ID,这是第 8 节扩展性的地基)。

事件订阅采用分散的 `@EventBusSubscriber` 自订阅:LCPacketHandler、CoinAPIImpl、WalletAttachment、FancySaveData、LCDatagenEntry 各自挂静态方法,没有集中 event 类。命令在 `features/commands/LCCommandSetup.java:17` 订阅 `RegisterCommandsEvent`,分 admin/debug 两类。

## 4. 核心系统

### 4.1 货币值模型(MoneyValue)

`api/money/values/MoneyValue.java`。钱是不可变抽象值:`@Range(0,Long.MAX_VALUE)` 的内部 long(`:149-150`)+ 懒生成的 `MoneyKey`(`:105-109`,缓存于字段),空值/免费值是单例(`:79-80,115`)。Codec 与 StreamCodec 都走注册表按类型 dispatch(`:31,67`),另有命令字符串风格的 `LENIENT_CODEC`(`:54-65`)。加减乘全部基于 `fromInternalValue` 重建(`:194-295`),`percentageOfValue` 是税/折扣的唯一百分比原语(`:256-274`,整数、默认向下取整、封顶 1000%)。跨端流转只需 VALUE_TYPE 注册表同步 + `STREAM_CODEC`。内建实现是 `api/coins/value/CoinValue`(链条面额组合,继承 `ItemBasedValue`,能分解为 ItemStack 掉入世界,`MoneyValue.java:308` + `ItemBasedValue.java:12-15`)。

### 4.2 货币链与面额价值(数据驱动)

`api/coins/data/ChainData.java` + `coin/CoinEntry|MainCoinEntry|SideBaseCoinEntry.java`。链条定义**不是 datapack,而是服务器磁盘 JSON 文件**:`config/lightmanscurrency/coin_data/*.json`(`api/coins/CoinAPI.java:21`)。

- 加载:`CoinAPIImpl.reloadCoinData:83-134` 在服务器启动(`:547`)与玩家加入(`:550-555`)时读目录;目录为空则用 `generateDefaultCoinData()` 生成默认链并回写文件(`:97-101`),"main" 链必须最先解析、解析失败强制回填默认值(`:105-126`)。
- 求值时机在**构造/解析时一次**:`defineEntryCoreValues`(`ChainData.java:221-245`)沿核心链单向递推 `coreValue *= entry.getExchangeRate()` 写入各 entry 缓存,side chain 从父币价值起算;`CoinEntry.setInternalValue:35-43` 显式拒绝二次覆写并打错误日志。
- 兑换边(`ChainData.java:365` `cacheCoinExchanges`)与找零/合并的贪心算法(`CoinValue.java:121-131,165,209`,借助 `ChainData.SORT_HIGHEST_VALUE_FIRST`,`ChainData.java:45`)都在载入期备好,查询期零计算。
- 跨端:`SPacketSyncCoinData`(整包 Map<String,JsonObject>)由 `CoinAPIImpl.getSyncPacket/syncCoinDataWith:495-524` 发送,客户端 `handleSyncPacket:526-545` 重解析并校验默认链存在后才采纳。

**没有递归配方展开,也就没有环的问题**——面额是声明式线性链,不是从合成表推出来的。
注意:1.21.1 旧版被广泛引用的"按配方递归算物品价值"在本快照**完全不存在**(全库 grep `CraftingRecipe|RecipeHolder` 仅命中 datagen;无 costcalculation 包)。旧版行为本树无法证实,标注**未验证**。

### 4.3 商人实体(TraderData + Node 组合)

`api/trader/data/TraderData.java:46-56`:一个商人 = 注册表类型 + 全局自增 long ID + 一组 `TraderNode` 的组合,整体 Codec 序列化,交易上限 `GLOBAL_TRADE_LIMIT = 100`(`:49`,注意它是 `public static int` 而非 final,节点数在 `AbstractItemTradesNode.java:46` 用 `Math.clamp` 夹逼)。节点即扩展点(`api/trader/nodes/builtin/`:TradingNode、MoneyStorageNode、OwnerNode、WorldNode、NetworkNode、UpgradeNode…),权限系统也是节点聚合(`getPermission:396-402`,对 `IPermissionSource` 节点取最高值)。

持久化侧:`features/api_impl/data/TraderDataCache.java:25-31` 是一种 `FancyData`,由 `FancySaveData` 统一映射成每类型一个 `SavedData` 文件(`lightmanscurrency_trader_data`),并集中驱动 tick/sync/服务器启停生命周期(`FancySaveData.java:44-56,79-111`);新商人注册即自增 ID 并向全体玩家广播创建包(`TraderDataCache.java:60-71`)。

BE 侧 `TraderBlockEntity.java` **只存 traderID**(`:56-68,149-152`),GUI 更新标签也只同步 ID(`:163-168`);物品形态摆放时用 `STORED_TRADER` 数据组件携带 ID(`:106-131`,`LCDataComponents.java:40`),`onLoad` 时做位置回写与"孤儿商人回收"(`:171-213`,依据 `WorldNode.TraderState.allowRecovery`)——状态机(NORMAL/ITEM 等,`TraderState`)在数据侧而非 BE 侧。

### 4.4 交易管线与服务端权威

交易入口是菜单消息而非专用包:`AbstractCustomerMenu.attemptTrade:72-88`——客户端只发 `(traderIndex, tradeIndex)` 两个 int,服务端用自己上下文里真实的 `TraderData`、真实玩家背包/钱包构建 `TradeContext`(`buildContext:67`),作弊面只有"索引"这一个可伪造量,且索引会被服务端边界检查(`TraderData.java:451,466-467`)。

资金/货物的移动全部包在 NeoForge 官方 **Transaction** 里:`MoneyPrice.transferFromCustomerToTrader:48-73` 在同一事务内 extract(顾客)→insert(商人),任一步数量不符直接返回失败、事务不 commit 自动回滚(`TradeContext.java:62-89` close/commit;`WalletAttachment` 本身是 `SnapshotJournal`,回滚即还原钱包 ItemStack,`WalletAttachment.java:96-99`)。物品侧同构:`AbstractItemTradesNode.executeTrade:66-107`(扣款成功才转移物品,给不进输出槽则整笔回退)。成功收尾统一走 `TradingNode.finishSuccessfulTrade:168-177`(commit + Post 事件)。

**税在本版本是 TODO**(`MoneyPrice.java:59,83` `//TODO pay taxes`,`taxesPaid` 恒为 empty)——旧版"税收集器"只剩配置项(`LCConfig.java:746-751,1053`)与警告开关(`:57-58,180-186`),无对应方块/逻辑。

### 4.5 钱包与玩家资金

钱有三种形态共存:① 物品形态现金(硬币,`CoinValue` 即 ItemStack 列表);② 钱包物品(`features/wallet/WalletItem|WalletStorage`,内容存 `WALLET_CONTENTS` 数据组件,`LCDataComponents.java:37`,升级槽数也是数据组件 `:36,43-45`);③ 玩家实体 attachment。

`core/neoforge/LCDataAttachments.java:21-27` 注册唯一的 `wallet` attachment,构建参数三连:`.serialize(CODEC).sync(STREAM_CODEC).copyOnDeath()`——序列化保换存档,`copyOnDeath` 保死亡,attachment 跟人走保跨维度。`WalletAttachment.java:29` 同时实现 `ItemAccess + SnapshotJournal<ItemStack>`,使"装备中的钱包"本身成为事务的一部分(`:71-99`);每 tick 末对比 `wasChanged()` 才做脏同步(`:127-140`),避免广播洪流。

统一查询/收支口是 `MoneyAPI.getPlayersMoneyHandler`(`api/money/MoneyAPI.java:22-38`,由 `MoneyAPIImpl` 聚合钱包+背包+带 money 能力的物品),对外则暴露 `lightmanscurrency:money_handler` 的 Block/Entity/Item 三套 capability(`api/LCCapabilities.java:16-18`,经 `ItemCapabilityResourceWrapper.java:21-41` 逐槽迭代),展示侧有 `MoneyDisplayHelper.contentsAsTooltip/getCyclingValue`(`api/money/MoneyDisplayHelper.java:23-93`)。银行账户(非物品数字钱包)在本版被砍:类声明与 Codec 整段注释(`BankAccount.java:33-78`),`BankAPIImpl:14-22` 返回 `List.of()` 空壳。

### 4.6 价格调控(倍率叠加审计)

针对读者铁律"倍率只能生效一次"专门核查,结论:**本实现结构上不可能重复乘**。`TradeData.getPrice(context):49-54` 每次询价只 post **一个** `TradeEvent.Cost`;该事件不携带任意函数,只聚合一个 int `pricePercentage`(初值 100),外部只能通过 `giveDiscount/hikePrice/setPricePercentage` 做**加减法**合并(`TradeEvent.java:87-91`),最终 `getCostResult():95` 对整个原价调用**一次** `percentageOfValue`。多个 10% 折扣得到的是 70% 价而非 0.9³ 复合价,天然免重复乘;`forceFree`/percentage≤0 短路为免费(`:94`)。倍率的"载入期一次生效"另一例是硬币链 exchangeRate(见 4.2,`CoinEntry.java:37-41` 防覆写)。上下限方面:`percentageOfValue` 注释封顶 1000%(`MoneyValue.java:241,251`),`multiplyValue` 用 BigDecimal 夹逼到 `[0, Long.MAX_VALUE]`(`:286-291`)。通胀/商店税/全局折扣乘区在本快照未迁移(只有上面的事件框架与 TODO)。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **自定义包**:`network/LCPacketHandler.java:22-45` 注册共 6 个 payload(协议版本 "2",`:18`):金币数据 S2C、钱包可见性/创造模式钱包 C2S、菜单消息双向 `BPacketMenuMessage`、FancyData S2C、调试 S2C。真正的同步粒度在自研 **FancyPacketMap**(`api/helpers/network/FancyPacketMap.java`,sealed 的 `Map<String,{type,data}>` 增量包)与 `LCFancyPacketTypes` 注册表之上:节点级增量、交易级增量(`TradingNode.setTradeChanged:61-74` 用 `modifyListEntry("trades",…,tradeIndex,…)` 只发被改的那一条;删除用 `setFlag("remove")` 截断后缀 `:76-86,116-121`),接收端 `onDataSync` 按索引补齐/删除(`:108-133`)。GUI 同步粒度还按玩家 **TrackingLevel**(NONE/CUSTOMER/STORAGE,`api/trader/tracking/TrackingLevel.java:5-8`)分层:同一商人,交易页看精简包、仓库页看全量包;完整初始包只在请求升级时发(`TraderData.requestTracking:99-120`),并有 `removedPlayerTracking` 防"降级又升级"的重发包抖动(`:75-78,109-112`)。
- **数据驱动程度**:货币值、交易数据、价格类型、节点类型、权限全部是注册表 dispatch Codec(见 3/4 节引行);硬币链是磁盘 JSON(服务器生成、可编辑、整包 S2C 同步)而非 datapack。物品→价格的数据驱动文件(旧版 itemcost JSON)在本树不存在(见 2 节缺失声明与 4.2)。
- **配置**:自研三文件框架 client/common/server(`LCConfig.java:29,232,650`),基类 `api/config/ConfigFile.java`(LoadPhase 两段加载 SETUP/GAME_START,`:50-84`;服务器文件 `SyncedConfigFile` 登录后同步给客户端,登录钩子 `:702`)。值得注意:**配置值类型直接就是 MoneyValue**——`MoneyValueOption`/`MoneyValueListOption`(`api/config/options/builtin/`),如认领价格 100 金币、强制加载 1,000,000 金币(`LCConfig.java:761,765`)、附魔修补定价带类型校验 lambda(`:707-708`)、拍卖上架费(`:721`)。价格进配置而非 datapack,且编译期保证同链可比。
- **datagen**:有,且打进主 jar——`datagen/LCDatagenEntry.java:14-36` 以 `@EventBusSubscriber` 订阅 `GatherDataEvent.Client`,挂模型(`LCModelProvider`+自研 `LCModelTemplates/LCTextureSlots`)、语言文件、配方(`LCRecipeProvider`)三个 provider;`clientData` 运行配置见 `build.gradle:109-115`。

## 6. Mixin

`src/main/resources/lightmanscurrency.mixins.json` 列出 5 个,**全部是 GUI 槽位适配,无一条注入游戏逻辑**(所以服务端权威与反作弊完全不依赖 mixin):
- `mixin/InventoryMenuMixin.java`:注入 `InventoryMenu.<init>` TAIL(`:28-36`),经 accessor 往玩家物品栏菜单塞一个配置坐标的 `WalletSlot`;注入 `quickMoveStack` HEAD 可取消(`:38-58`),让 shift+点击把钱包物品精确送进钱包槽(复制 1 个、原槽 shrink,不复制组件)。
- `mixin/AbstractContainerMenuAccessor.java:11-12`:`@Invoker("addSlot")`,上一条的实现依赖。
- `mixin/client/SlotWrapperMixin.java:20-28`:创意模式屏 `SlotWrapper` 构造尾,当被包装的是 WalletSlot 时改用创意模式专用坐标;`client/CreativeModeInventoryScreenAccessor`、`client/SlotWrapperAccessor` 为字段访问器。
配置项 `LCConfig.CLIENT.walletSlot/walletSlotCreative` 提供坐标偏移(`InventoryMenuMixin.java:33`、`SlotWrapperMixin.java:24`),TODO 注明 Curios 存在时让位(`InventoryMenuMixin.java:30`)。

## 7. 值得学的 5 条

1. **单累加器询价事件** — `api/trader/event/TradeEvent.java:87-95` + `TradeData.java:49-54`。折扣/涨价以"加减百分点"合并进一个 int,整个价格只被 `percentageOfValue` 乘一次。「倍率只能生效一次」靠**数据结构**保证而不是靠约定——新星殖民地的到港奖励倍率、nextCard 的保底价格修正应抄这个骨架。
2. **交易全程 Transaction 包裹** — `api/trader/trade/data/price/builtin/MoneyPrice.java:48-73`、`TradeContext.java:62-89`、`WalletAttachment.java:65-99`。扣款+入库+发货在同一事务树里,任何一步数量不符即失败,未 commit 自动回滚到快照;防作弊不靠校验客户端,而是客户端只报索引、服务端自己组上下文(`AbstractCustomerMenu.java:72-88`)。每日结算发钱/发货这种"多步必须全成"的逻辑直接可搬。
3. **attachment 三连 + tick 脏对比同步** — `core/neoforge/LCDataAttachments.java:21-27`、`features/wallet/WalletAttachment.java:57-63,127-140`。`serialize+sync+copyOnDeath` 一次解决换存档/跨维度/死亡三问;每 tick 比较新旧值才 `syncData`,避免持续广播。
4. **载入期递推定价 + 防覆写缓存** — `api/coins/data/ChainData.java:221-245`、`coin/CoinEntry.java:35-43,53-63`。面额价值在链加载时单向累乘一次算好写进 entry,查询期零计算;`setInternalValue` 二次写入直接报错,把"倍率被重复乘"变成可发现错误。
5. **配置项即货币值** — `api/config/options/builtin/MoneyValueOption.java` + `LCConfig.java:707-708,761-765`。定价配置带 MoneyValue 类型与 `compatibleTypes` 校验 lambda,改币种/改面额协议不用动代码;比"配置里放 double"的 mod 强一个量级。

## 8. 公开 API

- **入口包**:`io.github.lightman314.lightmanscurrency.api`,总闸 `api/LCApi.java:19-24` 暴露 `getMoneyAPI()/getCoinAPI()/getConfigAPI()/getBankAPI()(空壳)/getTraderAPI()` 五个接口单例,实现在 `features/api_impl/`(即接口与实现分包,外部只 import `api.*`)。
- **价值/收支扩展点(重点)**:任何人可以把自家方块/实体/物品注册为"有钱":capability 键 `lightmanscurrency:money_handler`,有 Block(带 Direction)、Entity、Item(带 `SidedItemAccess` 上下文)三套(`api/LCCapabilities.java:14-18`),契约接口是 `api/money/resource/MoneyResourceHandler`(insert/extract 返回实际成交的 `MoneyValue`,天然接进 4.4 的 Transaction;`SortableMoneyResourceHandler`/`DeferredMoneyResourceHandler` 提供排序与懒加载变体)。注册后即可被钱包、ATM 页签、`MoneyAPI.getPlayersMoneyHandler`(`api/money/MoneyAPI.java:31-38`)、`getContainersMoneyHandler/Viewer`(`:44-62`)自动纳管,无需碰本 mod 界面代码。
- **自定义货币类型**:向同步注册表 `LCRegistries.Money.VALUE_TYPE`(`api/LCRegistries.java:36-37`)注册 `MoneyValueType`(自带 Codec/StreamCodec,`MoneyValue.java:31,67` dispatch),再覆写 `getTypedHelper()`(`:90`)接上显示与求和;`MoneyValueType` 同时是命令参数类型(`api/command/arguments/MoneyValueArgument.java`)。
- **交易侧扩展**:`TraderType`/`TraderNodeType`/`TradeDataType`/`TradePriceType`/`PermissionType` 全注册表化(`LCRegistries.java:77-97`),配合 `TradeEvent.Pre/Cost/Post`(`api/trader/event/TradeEvent.java`)与 `TraderEvent` 做行为注入;`CoinAPI.registerCoinContainerFilter`(`api/coins/CoinAPI.java:84`)允许外 mod 声明非硬币物品"可入钱包"。
- **对 JEI**:本快照**没有** JEI/REI 插件类(grep 无命中、依赖注释于 `build.gradle:137-151`),旧版靠 JEI 显示货币配方的路径在本树无证据,**未验证**。

## 结论:给新星殖民地 / nextCard 的可搬做法与反面教材

**新星殖民地(每日结算货币经济)**:
1. 搬 `TradeEvent.Cost` 的"单累加器"结算模型:每日结算时把所有加成(建筑、到港、通胀)先合并为一个百分数,最后对基数乘一次(`TradeEvent.java:87-95`)——与读者铁律同构,且天然可展示"合计 +x%"给玩家。
2. 搬"结算动作全入 Transaction"的做法(`MoneyResourceHandler.extract/insert` + 未 commit 即回滚,`MoneyPrice.java:52-72`):每日结算发币+发货多步操作,任一步失败整笔还原,配合去重标记才能既幂等又不半发;数字账户形态则参考 `UnlimitedMoneyStorage`(按 `MoneyKey` 分桶的 Map,`api/money/resource/builtin/UnlimitedMoneyStorage.java`),不必做物品现金。

**nextCard(抽卡货币与保底)**:
- 搬 `MoneyValueOption`:抽卡价格/保底计数换算成"货币值+类型校验"的配置对象(`LCConfig.java:707-708`),校验 lambda 保证保底货币与池子货币同 Key 可比,防止热重载后两种货币静默错配。

**做坏了的一处(带行号)**:`api/trader/trade/TradeContext.java:110-113` —— `Builder.addResource(Map map, …)` 的 `map` 参数被完全忽略,函数体硬编码 `this.customerResources.computeIfAbsent(...)`,于是 `addTraderResource`(`:108`)收集来的**商人资源全部串进顾客资源表**,`traderResources` 恒空、`getResource(TRADER, …)` 退化为 `type.empty()`(`:51-60`)。这条直接击穿 4.4 节"商人侧扣款"的正确性,是本快照最实的缺陷。

同树质量佐证(抄设计时须绕开):

- `TraderData.attemptTrade:457` 的 `if(tradeCount < tradeIndex)` 比较方向写反(应为 `tradeIndex < tradeCount`),正常索引路径会落入 `:466` 抛 `FAIL_INVALID_TRADE`;
- `MoneyValue.multiplyValue:292-293` 的进位分支漏 `return`,结果被丢弃;
- `BankAccount.java:109,125` 与 `api/trader/nodes/builtin/DisplayNode.java` 引用的 `ModLazyPackets`/`LazyPacketData` 符号在全树无定义,加上 `BankAccount.java:81` 处接口继承被注释却残留 `@Override`,这些文件在此树应无法编译(未实跑构建,静态判读)。

以上印证 "26.1 rework part 2" 是中途快照:**抄它的骨架设计,别抄这些行**。
