# Order to Cook 源码分析报告

路径缩写（全文一致，便于复核）：`$N/` = `neoforge-1.21.1/src/main/java/cn/breezeth/ordertocook/`，`$NC/` = `neoforge-1.21.1/src/client/java/cn/breezeth/ordertocook/`，`$CM/` = `common/src/main/java/cn/breezeth/ordertocook/`。本报告除规模统计外全部以 NeoForge 1.21.1 模块为分析对象；工程结构对照句放在第 2 节。

## 1. 基本信息

- mod_id：`ordertocook`（`neoforge-1.21.1/src/main/resources/META-INF/neoforge.mods.toml:7` 与 `forge-1.20.1/src/main/resources/META-INF/mods.toml:7` 双证）。作者：breezeth-CN（仓库 owner，中文 mod）。许可证：GPL-3.0（`LICENSE.txt:1-3`）。
- 目标版本：MC 1.21.1 / NeoForge 21.1.228（`neoforge-1.21.1/gradle.properties:1-3`）；另有 forge-1.20.1（Forge 47.4.0，`forge-1.20.1/gradle.properties:2`）与 fabric-1.20.1/1.21.1（loader 0.18.2，`fabric-1.21.1/gradle.properties:2-4`）。mod 版本 1.3.7a（三个 loader 模块 gradle.properties 一致）。
- Gradle 插件与工程结构（速览卡片写 "loom+multiloader"，需更正）：这是**手写的四副本多开工程，不是 Architectury 也不是统一 loom**。根 `settings.gradle:11-27` 按 `gradle.properties` 里 `enable_neoforge_subprojects/enable_forge_subprojects/enable_fabric_subprojects` 三个开关决定是否 include 各模块；fabric 两版注释明示"已冻结在 1.3.7a"。模块清单：`common`、`fabric-1.20.1`、`fabric-1.21.1`、`forge-1.20.1`、`neoforge-1.21.1`（另有 `settings.gradle:29` 引用了 `ordertocook-sable-neoforge-1.21.1` 子工程，本地磁盘无此目录——疑为姊妹分支工程或被稀疏检出裁掉，未验证）。
- 各模块构建插件互不相同：fabric 用 fabric-loom 1.11.8（`fabric-1.21.1/build.gradle:2`），forge 用 ForgeGradle 6.0.53 + spongepowered mixin 插件（`forge-1.20.1/build.gradle:2-3`），neoforge 用 net.neoforged.moddev 2.0.134（`neoforge-1.21.1/build.gradle:2`）。`common/` 模块只装 4 个文件（菜单同步编解码 + IDataAccessor），**不是**共享逻辑层，仅通过各模块 `sourceSets.main.resources.srcDirs` 把 common 资源目录拼在前面以便覆盖（`neoforge-1.21.1/build.gradle:36-45`）。
- Java 版本：JAVA_21（`neoforge-1.21.1/src/main/resources/ordertocook.mixins.json:6` 与 fabric 侧），forge-1.20.1 侧 JAVA_17（其 mixins.json）。
- 发布坐标：group `cn.breezeth`，artifact 基础名 `ordertocook`（`neoforge-1.21.1/gradle.properties:8-10`）；依赖 GeckoLib 4.8.4（NPC 动画）、可选 JEI/Just Enough Jobs 兼容。

## 2. 源码规模与包结构

实测（`find`+`wc -l`，不含 `.git`）：全仓 **.java 558 个、85,668 行**（卡片写 86,226，偏高约 558 行，以实测为准）。分模块：

| 模块 | .java | 行数 |
|---|---|---|
| neoforge-1.21.1 | 140（main 89 + client 51） | 21,364 |
| forge-1.20.1 | 139 | 21,403 |
| fabric-1.20.1 | 139 | 21,812 |
| fabric-1.21.1 | 136 | 20,886 |
| common | 4 | 203 |

即同一套玩法代码按 loader × MC 版本复制了 4 份，每份约 2.1 万行，四份间有分叉（OrderNpcManager 实测三份 1706 / 1703 / 1587 行）。工程结构对照一句（vs `TelepathicGrunt__Bumblezone.md`）：Bumblezone 是"common 装 723 文件/78k 行全部玩法 + loader 侧薄适配 + ServiceLoader 平台接口"的正统 multiloader；Order to Cook 恰是反面——每个 loader×版本模块整套复制约 140 文件的源码树自行分叉，`common` 只放 4 个真正共享的类（`$CM/` 的菜单同步编解码 + `IDataAccessor`），行数差就是维护税的可视化。对要长期演进的单 loader 工程（求仙问道）无直接参考价值，但对"要不要开第二 loader"是个量化警示。

neoforge-1.21.1 主源码包分布（文件数）：`core` 15（订单/ NPC/声望/排行心脏区）、`block` 12、`block/entity` 10、`api` 9（对外扩展点）、`registry` 8、`item` 7、`screen`(ScreenHandler) 5、`util`/`mixin`/`advancement` 各 4、`network`/`entity`/`config` 各 2、`command`/`compat*`/`vehicle.motorcycle` 等零散；client 侧：`renderer` 16、`screen`(GUI) 6、`gecko` 7、`mixin/client/*` 11。

最大源文件（neoforge 侧 `wc -l` 实测行数）：`$N/core/OrderNpcManager.java` 1706、`$N/block/entity/OrderMachineBlockEntity.java` 1026、`$N/item/TakeoutBagItem.java` 868、`$N/block/entity/RefrigeratorBlockEntity.java` 596、`$N/config/ConfigManager.java` 589、`$NC/screen/OrderMachineScreen.java` 557、`$N/vehicle/motorcycle/MotorcycleEntity.java` 544、`$N/entity/CustomerEntity.java` 543、`$NC/client/OrderToCookModClient.java` 543、`$N/block/entity/StoveBlockEntity.java` 481、`$N/block/entity/TakeoutBoxBlockEntity.java` 478、`$N/network/ModNetworking.java` 430。

**源码树不完整（务必注意）**：本地为稀疏检出（`git status` 报 59%）。四个 loader 模块的 `src/main/resources` 只剩 `META-INF/*mods.toml` + 两个 `*.mixins.json`——语言文件、advancement JSON、贴图、`fabric.mod.json` 全部未检出。因此本报告不描述任何 JSON 资源格式；grep `DataProvider|gatherData` 在已检出源码中 0 命中，**datagen 有无未验证**（可能随资源一起被裁掉）。

## 3. 入口与注册

入口 `$N/OrderToCookMod.java:59-89`，`@Mod(ModConstants.MOD_ID)` 构造器一次性完成装配：

```java
@Mod(ModConstants.MOD_ID)
public OrderToCookMod(IEventBus modBus) {
    ConfigManager.load();
    ModBlocks.registerModBlocks(modBus);      // 8 个 registry 类各自 DeferredRegister.register(bus)
    ...
    modBus.addListener(ModNetworking::registerPayloadHandlers);
    modBus.addListener(this::registerCapabilities);   // ItemHandler cap 挂到冰箱 BE
    if (ModList.get().isLoaded("touhou_little_maid")) { ...RefrigeratorWirelessIOBinding.register(); }
    NeoForge.EVENT_BUS.addListener(this::onLevelTick);
    NeoForge.EVENT_BUS.addListener(this::onServerTick);
```

注册方式：mod bus 上全是 NeoForge `DeferredRegister` 家族（`$N/registry/` 8 个类）+ `RegisterPayloadHandlersEvent`（网络包）+ `RegisterCapabilitiesEvent` + `EntityAttributeCreationEvent`（顾客实体属性，`:106-108`）。游戏事件订阅在类内直挂：`PlayerInteractEvent.EntityInteract`（递交订单的三路分发 seat/NPC/walk-in，`:114-134`）、`BlockEvent.BreakEvent`（创造模式砸订单机警告，`:201-209`）、`LevelTickEvent.Post`（NPC 补完动画与每 100 tick 的过期清扫，`:322-333`）、`ServerTickEvent.Post`（摩托车外卖每 10 tick 轮询 `trySpawnDeliveryWhenNearby`，`:335-369`）。命令 `ModCommands.registerCommands`。

## 4. 核心系统

### 4.1 订单表示与生成（订单=物品栈 NBT）

订单不是 SavedData 记录而是一件 **ItemStack**（`ModItems.ORDER`，`OrderItem`）。`$N/core/OrderGenerator.java:85-140` 在生成时把订单全部内容写进该栈的 CompoundTag：

- `OrderId`：`dd%06d` 自增串，由 SavedData 分配器 `$N/core/OtcRuntimeIdState.java:35-40` 发号，全维度单调递增、可指认可对账；
- 顾客名 + `CustomerId`（`gk%06d`，同一发号器 `:42-47`），另有 `CustomerProfileLibrary` 写入的画像子 NBT（`:71/132`）；
- `Type` 0-4：白绿蓝紫红五档稀有度，决定菜品种类数（1~6 种）与基价；
- `Delivery`/`Urgent`/`IsLongDistance` 三开关 + `delivery_pos`（外卖目标 XZ）与 `delivery_dist`；
- `ExpiryTick` + `ExpiryTime`：游戏刻与真实毫秒**双时钟**冗余（`:124-125`，见 4.5）；
- `FoodList`：物品注册名→份数的嵌套 CompoundTag（`:291-299`）；
- `Prestige`：票面应付金币（键名沿用旧版"声望"，`:126` 注释自认）。

外卖落点坐标生成时即避开海洋/河流生物群系：极坐标随机取点、采样噪声生物群系判 `path.contains("ocean"/"river")`，失败留 fallback 点（`OrderGenerator.java:194-245`）。菜品池来自"菜单板"方块（`getMenuFoodsForMachine`，`$N/block/entity/OrderMachineBlockEntity.java:502-509`），先按注册名去重、`Collections.shuffle`（以世界随机源派生种子，可复现）后取 K 种、每种随机 1~maxCount 份（`OrderGenerator.java:261-300`）；无菜单板时兜底苹果（`:272-274`）。类型权重由配置驱动且随餐厅等级加权紫/红（`:154-192`）。奖励 = 基价 + 加急定值 + 外卖/长距离乘倍率（`:302-324`），再叠加"订单总饥饿值 × 等级系数"的食量加成（`computeOrderHunger` + `baseHungerBonusRate`，`:326-355`）。**刷新节奏**：订单机 BE 每 `orderMachineRefreshSeconds`（默认 600s，`$N/config/ModConfig.java:13`）`refreshOrders()`——`inventory.clear()` 后整槽重掷（`OrderMachineBlockEntity.java:402-407, 441-482`），即旧订单票直接作废、不做结算，属于"看板刷新"而非"到港清算"。

### 4.2 完成判定链：备餐→打包→递交

完成判定**不在递交时校验菜品**，而是在打包台。全链路五步：

1. 玩家从订单机 GUI 取走订单票（票就躺在 BE 的 `inventory` 槽位里）。
2. 做菜：灶台直接复用原版 `SmokingRecipe`——`$N/block/entity/StoveBlockEntity.java:54` 用 `RecipeManager.CachedCheck<SingleRecipeInput, SmokingRecipe>` 查配方，多车道并行、无自定义配方类型，任何 datapack 往 smoking 里加菜即可被订单点到（数据驱动、零配方代码）。
3. 封装：`$N/block/entity/TakeoutBoxBlockEntity.java:379-389` `getFoodListIfSatisfied` 汇总"打包盒槽位 + 半径 24 格自动化货源"（`IngredientSourceCompatApi.countAllNearby`，`:390-403`）逐项对比 FoodList，缺一样返回 null；满足后 `consumeFoodList`（`:405-418`）先抽远处货源再抽槽内扣料，把订单 NBT 原样拷进 `TakeoutBagItem`（`:105-148`）产出"封装好的外卖袋"；堂食分支产出 `FoodPlateItem`。餐盘/包装材料也走同款"就近抽取"（`:420-430`）。
4. 递交：对 `otc_npc` 标签顾客右键，`$N/item/TakeoutBagItem.java:277-302`（外卖）与 `:304-349`（堂食）先验过期、再用 `OrderNpcManager.isNpcForOrder` 按 `otc_order:<id>` 实体标签匹配（含骑乘/坐骑双向探查，`$N/core/OrderNpcManager.java:975-1002`）。
5. 结算：`completeDelivery`（`TakeoutBagItem.java:416-466`）——奖励 = 票面 `Prestige` + 概率小费（加急/彩蛋顾客/雨天各档概率，`:427-435`）；发金币（`CoinUtils.giveCoins`）、`PrestigeManager.addPlayerPrestige`、触发 4 个自定义 advancement 判据（`$N/advancement/OrderCompletedCriterion.java` 等）、按 machineId 累进餐厅统计（4.4）、发射 `OrderLifecycleApi` COMPLETED 事件，最后 `stack.shrink(1)` 消费凭证（`:465`）。

原版进食耦合顺带一提：外卖袋自身注册了 `FoodProperties`（营养 4，`alwaysEdible`，`TakeoutBagItem.java:33-39`），过期后可"吃掉"泄愤——`finishUsingItem` 拦截过期分支只播嗝声 + 触发 `EXPIRED_BAG_EATEN` 判据并销毁（`:41-57`），未过期时吃到的是袋子的普通食物效果；菜品本身的 buff 没有二次加工——营养值只作为**奖励计算输入**经 `MenuFoodCompatApi.resolve(..., Purpose.REWARD)` 读取原版 FOOD 组件（`OrderGenerator.java:334-335`），不做 buff 叠加系统。

### 4.3 幂等处理（对读者最关心的点）

本 mod 没有"每日结算"，它的防重复计入靠**三件套**，全部有行号可查：
1. **一次性物理凭证**：结算函数最后 `stack.shrink(1)`（`TakeoutBagItem.java:412/465/509` 三条结算路径各自收敛前消费）——同一张票无法进两次账。
2. **投递 NPC 只生成一次**：外卖订单靠玩家身带，接近目标坐标 48 格内才动态生成收货 NPC；守卫是订单 NBT 上的布尔位 `delivery_spawned`——读取处直接 return（`TakeoutBagItem.java:772`），成功生成后才置位回写（`:808-809`）；**若生成失败则改走 `settleDirectly` 直接结款**（`:802-806`），保证"要么正常投递要么兜底结算"，订单不会悬空被轮询第二次。
3. **NPC↔订单映射的单消费**：`orderToNpc` 静态 `ConcurrentHashMap<String,UUID>`（`OrderNpcManager.java:30`），完成动画入口第一件事 `orderToNpc.remove(orderId)`（`:440`），过期清扫同样先 remove；且过期清扫对"正在播完成动画"的 NPC 有 `pendingCompatCompletions.containsKey` 豁免（`OrderNpcManager.java:205-208`），防"结算中/过期踢出"竞态。
另有取票即标的 walk-in 幂等标签 `otc_walkin_interacted`（`OrderToCookMod.java:218-224`：先查后打，双保险）。**但要指出：以上只保证单调用路径内不重复，不存在"已处理 OrderId 集合"**——若 ItemStack 被外部 mod 复制（dupe/拷贝 NBT），金币与统计会双计（见第 7 节反面条目）。

### 4.4 持久状态三层：玩家 / 维度 SavedData / 实体标签

"状态存哪里"的答案分四层：

- **玩家层（声望）**：不走 Attachment 而是 mixin 注入字段——`$N/mixin/PlayerEntityMixin.java` 给 `ServerPlayer` 加 `private int prestige` 并在 `addAdditionalSaveData/readAdditionalSaveData` 的 TAIL 注入读写（`:37-47`），`$N/core/PrestigeManager.java:7-24` 只是强转 `IPrestigeData` 接口的门面。
- **维度层（SavedData ×3）**：`ordertocook_runtime_ids`（订单/顾客发号，`OtcRuntimeIdState.java:14-20`）、`ordertocook_machine_ranking`（餐厅排行榜，machineId→Stats{accepted, delivery, longDistance, totalProfit, walkIn, maxDeliveryDist...}，`MachineRankingState.java:14-33`，含 posToId 反查表）、`RestaurantPersistentState`（machineId→统计快照，BE 被拆也不丢，`RestaurantPersistentState.java:11-20`）。
- **方块实体层**：订单机 BE 只存"当前看板票"物品栈 + `ensureMachineId` 绑定全局排行榜 ID（`OrderMachineBlockEntity.java:897`）；GUI 同步走 BE 的 `getUpdateTag`/`syncToClients`（`:974/1002`）。
- **实体标签层（运行时会话态）**：NPC 与订单的对应、过期时刻塞在 entity tag：`otc_order:<id>`、`otc_order_expiry_tick:<t>`、`otc_order_expiry_sys:<ms>`（`OrderNpcManager.java:38-40`），`tagNpc` 打标签前先 strip 旧订单/过期标签保证"一 NPC 一订单"（`:1079-1113`）；另有进程内 `orderToNpc` ConcurrentHashMap 做快速索引（`:30`，put 于 `:1690`）——映射真相在 tag，内存表可重建（`checkOrderNpcDespawn` 每 100 tick 全扫描回注册，`:140-146`），重启不丢单。

### 4.5 双时钟过期与懒迁移

有效期：加急 `URGENT_DURATION_TICKS`、普通 `NORMAL_DURATION_TICKS`（`OrderGenerator.java:97`），到期判定与清算分散在四处（票 tooltip、NPC 扫描、外卖袋 use、BE 定时）。关键工程点：游戏刻与真实毫秒互为权威——离线/换服务器后 tick 基准漂移，于是 `OrderItem.ensureExpiryTick`（`$N/item/OrderItem.java:186-204`）用 `ExpiryTime` 反推当前游戏刻基准，`OrderNpcManager.java:183-194` 在扫描时把只有 sys 标签的实体就地换算回 tick 标签并**替换旧标签**；过期/临期提示用 NBT 布尔位 `ExpiryExpiredNotified`/`ExpiryWarned5m`/`ExpiryWarned1m` 保证每票各提示一次（`OrderItem.java:128-159`）。

### 4.6 NPC 与"村庄"联动：实际是订单来源三通道 + 声望进度

**没有村民/村庄职业联动**。订单来源三条：

1. 看板定时刷新（4.1，机器驱动，玩家主动取票）；
2. walk-in 到店客：机器每 `walkInAttemptIntervalSeconds`（60s，`ModConfig.java:16`）按餐厅等级概率掷客（`OrderMachineBlockEntity.java:409-416, 433-438`，等级概率表 `ModConfig.java:22-36`：Lv3=0.1 到 Lv8=0.35），生成的顾客实体身上贴机器坐标/等级/spawn 时刻标签，玩家首次互动即现场生成一张必加急的到店订单票塞进背包（`OrderToCookMod.java:213-319`，`OrderGenerator.generateWalkInOrder` 恒 delivery=false/urgent=true，`:38-46`）；
3. 外卖收货 NPC：不是预生成，而是玩家携封装袋进入目标坐标 48 格半径时才 spawn（4.3），长距离单另走 `LongDistanceDeliveryNpcManager`（`TakeoutBagItem.java:799-801`）。

进度线：餐厅等级 1-8 驱动权重/槽位/倍率（`OrderGenerator.java:343-377` 三张 switch 等级表），升级材料是"看板累计饥饿值"档位表（`ModConfig.java:19` `orderMachineUpgradeBoardHunger = [0,40,...,600]`），等级与统计喂给排行榜 SavedData，达标时 `RestaurantRegistry.tryGrantGoldenRestaurant`（`RestaurantRegistry.java:83`）授予金餐厅成就；彩蛋顾客（模拟真人皮肤的顾客，生成率与小费概率独立，`ModConfig.java:79-88`）提高小费概率。第三方联动全在 `$N/compat/`：东方小魔女坐店客（`touhoulittlemaid` 包 + 5 个客户端 mixin）、Jade 提示、JEI 配方页。

### 4.7 客户端表现

GUI 是常规 `AbstractContainerScreen` 手写布局（`$NC/screen/OrderMachineScreen.java:33-60`）：按钮全部经 `handleInventoryButtonClick(menuId, code)` 走原版窗口协议的"按钮信令"，没有值得抄的声明式写法；订单面板本身（票列表）由 ScreenHandler 同步 BE 库存实现。真正有设计含量的是**自定义菜单同步协议**：服务端把 `custom_menu_items.json5` 配置打包成 gzip+SHA-256 摘要，按 24KB 分块经 4 种 payload（request/manifest/chunk/invalidated，`$N/network/ModNetworking.java` 尾部 `CustomMenuSync*` record）推给客户端，编解码与限额在 `$CM/network/CustomMenuSyncCodec.java:13-41`（原始 ≤8MB、压缩 ≤2MB、≤128 块），客户端缓存于 `$CM/network/CustomMenuSyncServerCache.java`。这是"配置驱动内容需要上屏"时避免手写 NBT 同步的完整方案。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 自定义包：`$N/network/ModNetworking.java` 定义约 14 个 `CustomPacketPayload` record（声望查询 C2S/S2C、排行榜 JSON 字符串 S2C、餐厅改名、菜单同步四件套、骑手音效/动画等），全部 `StreamCodec`（unit / ofMember），`writeUtf(x, 64)` 带长度上限。排行榜直接 `buf.writeUtf(payload.json())`——用 JSON 字符串省去结构 codec，换实现快。
- 数据驱动程度：**低-中**。配方侧完全借用原版 `SmokingRecipe`（灶台）；但**订单/菜品/奖励没有 datapack JSON、没有 Codec**——全部是 `CompoundTag` 自由键（`$N/core/ModConstants.java` 的 NBT_ 键表）+ java 常量 + json5 配置三件套。菜品池由"菜单板方块内玩家摆放的物品"决定（运行时注册名收集），自定义可点菜项走配置文件 `custom_menu_items.json5`（`ConfigManager.java:52`）。
- 配置：手写 Gson 方案而非 loader ConfigSpec——`$N/config/ConfigManager.java:50-70` 读写 `config/ordertocook/ordertocook.json5`（`.json5` 后缀为暗示支持注释），`ModConfig` 是带 `@Comment` 的公有字段 POJO（约 60+ 项：权重 `:39-47`、刷新 `:13`、外卖/加急/长距离概率与倍率 `:50-71`、小费档 `:86-88` 等），改完可热重载（按 lastModified 判断）。
- datagen：**无**（已检出源码 0 命中；受稀疏检出所限，不能排除被裁掉的资源目录里有，未验证）。

## 6. Mixin

注册清单：`neoforge-1.21.1/src/main/resources/ordertocook.mixins.json`（服务端 3 条，`defaultRequire:1`）+ `ordertocook.client.mixins.json`（客户端 7 条，`defaultRequire:0`），两者都挂自定义插件 `cn.breezeth.ordertocook.mixin.MixinPlugin`（`$N/mixin/MixinPlugin.java:12,36` 的 `IMixinConfigPlugin.shouldApplyMixin`）做条件开关（小魔女/摩托车相关）。

- 服务端：`PlayerEntityMixin`（给 ServerPlayer 注入声望字段 + 存档读写 TAIL 挂钩，兼作 4.4 的玩家存储层——这是"核心逻辑唯一依赖 mixin 之处"）、`MotorcycleFallDamageMixin`（骑乘免摔落伤害）、`ItemEntityMixin`（掉落物行为补丁，具体注入点未逐条复读）。
- 客户端 7 条服务两件事：摩托车骑乘表现（`client.vehicle` 包 6 条：Camera/HeldItemRenderer/ItemRenderer/PlayerEntityRenderer/ArmorFeatureRenderer/ClientPlayerInteractionManager）与东方小魔女吃饭动画/坐姿（`client.compat.touhoulittlemaid` 5 条，`GeckoMaidEatingAnimationMixin.java`、`BedrockMaidEatingAnimationMixin.java`、`MaidEatingSwingStatusMixin.java`、`EntityChairGetYawMixin.java` 等）。

注入点目的均为表现层与第三方补丁，**订单/结算逻辑不依赖 mixin**（除声望存储——NeoForge 1.21.1 有 Attachment 可用却选了 mixin 字段，属跨版复用的历史包袱）。forge-1.20.1 侧 refmap 配置见 `fabric-1.21.1/build.gradle` 的 loom 段（`defaultRefmapName = "ordertocook-refmap.json"`）。

## 7. 值得学的 5 条

1. **近场惰性生成 + 一次性标志 + 失败兜底**：`$N/item/TakeoutBagItem.java:772/802-809`——外卖收货人只在玩家携袋接近目标 48 格时才生成，`delivery_spawned` 位防重，生成失败立即 `settleDirectly` 改走无 NPC 结算。值得抄：对"到港订单"，把触发从全局轮询改成携带者近场惰性结算，且失败路径与成功路径同样消费凭证，不留可重试的悬挂态。
2. **双时钟有效期与懒迁移**：`$N/item/OrderItem.java:186-204` + `$N/core/OrderNpcManager.java:183-194`——tick 与 wall-clock 互为备份，读取时以真实时间为权威重锚游戏刻并替换旧标签。值得抄：每日结算跨离线日/关服时，单存 tick 必坏；"记录绝对时刻 + 使用时换算 + 换算后回写"是可直接搬的三步式。
3. **带 ID 与优先级的规则链扩展点**：`$N/api/MenuFoodCompatApi.java:27-49`——`register(ResourceLocation id, int priority, Rule)` 三段返回 PASS/ALLOW/DENY，异常吞掉并记日志、重复 ID 抛错，最后兜底原版 FOOD 组件。值得抄：给"哪些物品能进菜单/订单池"留一个可被别的 mod 注册规则的链，比硬编码黑名单可扩展得多（同型的只读生命周期钩子见 `$N/api/OrderLifecycleApi.java`，注释明言"监听者不能取消结算"——扩展面收敛得很干净）。
4. **配置内容的分块哈希同步协议**：`$CM/network/CustomMenuSyncCodec.java:13-41` + manifest/chunk/invalidated payload——gzip、SHA-256 指纹、24KB 分块、raw/compressed/chunks 三重限额、`unchanged` 短路。值得抄：任何"服务端可变表需要进客户端 GUI"（价格表、订单池）都适用，且限额意识防了恶意超大包。
5. **发号器 SavedData 模式**：`$N/core/OtcRuntimeIdState.java:12-41`——一个 20 行的 `nextOrderId/nextCustomerId` 单调计数器 + `computeIfAbsent`，给世界内所有订单/顾客稳定可追溯 ID，成就与排行榜统计都按 ID 聚合。值得抄：殖民地订单系统需要"可指认的单号"做对账与去重，这比 UUID 短且可比大小。

**反面（给 newstar 的警示）**：餐厅统计走 `$N/core/RestaurantRegistry.java:85-110` 的 `applyCompletedDeltaById`——同一次结算把增量**双写**进 SavedData 与静态 `ONLINE` 缓存，`accepted+1`、`totalProfit+coin` 都是无键增量累加，去重完全依赖上游"票已消费"这一条路径；一旦有第二条调用路径（复制票、事件重放、未来的自动化管道）统计即双计。这正是"同一结算周期被重复计入"的教科书式隐患：增量落账处不认单号。搬法建议：到港订单结算在 `MachineRankingState` 层面记"已入账 OrderId 有界集合/上次结算日"，让累加入口自身幂等，而不是把幂等全部外推给凭证消费。

## 8. 公开 API

`$N/api/` 9 个类构成本 mod 的第三方扩展面（根目录另有 `COMPATIBILITY_API.md` 说明文档，内容未逐条核对）：

- `OrderLifecycleApi`：GENERATED/ACCEPTED/PACKED/COMPLETED/EXPIRED/CANCELLED 六态只读事件，`register(id, priority, listener)` 带重复 ID 抛错、监听异常吞掉记日志（`$N/api/OrderLifecycleApi.java` 类注释明言"监听者不能取消结算"）。
- `MenuFoodCompatApi`：菜单准入与营养判定规则链（PASS/ALLOW/DENY）。
- `IngredientSourceCompatApi`：打包台的"附近货源"抽象，可被存储类 mod 实现（`countAllNearby`/`extractNearby`，调用见 `$N/block/entity/TakeoutBoxBlockEntity.java:392/407`）。
- `RestaurantSupplyCompatApi`：餐盘/包装材料供给（`SupplyType.PACKAGING`/`CLEAN_PLATE`，`TakeoutBoxBlockEntity.java:420-430`）。
- `CountertopAutomationApi`：自动化操作的前置状态查询 `getAutomationStatus`，细粒度 Status 枚举（NO_ORDER/EXPIRED/MISSING_FOOD/MISSING_PACKAGING/MISSING_PLATE/OUTPUT_BLOCKED…，`TakeoutBoxBlockEntity.java:61-62`）。
- `PhysicalRestaurantCompatApi`/`PhysicalRestaurantCompat`：外部"移动餐厅"世界的坐标换算与密度维护（`OrderGenerator.java:195` 的 `toWorldPosition`；`OrderMachineBlockEntity.java:391-400` 的兼容巡检）。
- `OrderToCookApi`、`IDataAccessor`：总门面与 1.20.1/1.21.1 NBT-API 差异薄封装（common 亦有副本）。

跨 loader 的兼容代码路径按 `ModList.get().isLoaded(...)` 门控（`$N/OrderToCookMod.java:79-81`）。
