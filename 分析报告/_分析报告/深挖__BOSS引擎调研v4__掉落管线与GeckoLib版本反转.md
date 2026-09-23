# 深挖：BOSS 引擎调研 v4——掉落管线 + GeckoLib 版本取证（含一处反转）

> 两个后台子 agent 的产出合并（2026-09-23）。服务 Colossus v0.2 第五批（已落地）与动画适配层定案。

## 一、反转：不存在 "GeckoLib 3 for 1.20.1"，适配目标应为 GL4

前轮把"GL3 on 1.20.1"列为未验证风险；取证结论（证据链完整）：

- 本机实据：`PCL2/.minecraft/versions/*/mods/geckolib-forge-1.20.1-4.8.3.jar`；gradle 缓存里有 **geckolib-forge-1.20.1-4.4.9 的 sources jar**（一手源码）；`bernie-g__geckolib` 远端 `origin/1.20.1` 分支 `gradle.properties` 写明 `GeckoLib 4 / 4.8.4`。**GL3 止步 1.19.2**（唯一 3.0.31 是 1.12.2 的）。
- GL4 同步内核（`software.bernie.geckolib.`，源码证据）：
  - 服务端触发口 = `GeoEntity.triggerAnim(controller, animName)` → `EntityAnimTriggerPacket{entityId, controller writeUtf, anim writeUtf}`——**纯字符串协议**（GL5 才改成注册表 int）；Colossus 的"名字即协议"再得一个独立佐证。
  - **无服务端动画时钟**：`AnimatableManager`/`GeoModel.handleAnimations` 入口全在 `Minecraft.getInstance()` 之下，GL 零订阅服务端 tick；6 个 packet 全部 S→C，**没有 C→S 通道**；`hasAnimationFinished()/PlayState` 都是客户端查询。
  - 服务端影响客户端动画决策的唯一内置通道：`SerializableDataTicket`（`setAnimData` 广播任意值给客户端 `AnimationStateHandler`）。

**对 Colossus 的定案影响**：
1. "服务端权威时间线（MoveDef 帧表）+ GL 只当显示层"**从设计偏好升级为唯一可行架构**——GL 根本不告诉你动画何时结束/进行到第几帧。
2. GL4 适配器（未来批次）职责收窄为两件事：`AttackState.onStart → triggerAnim("main", move.animName())`；视觉旗标走 `SerializableDataTicket`。**不需要**名字→索引层。
3. AnchorSampler 真要骨骼世界坐标：只有 (a) **离线解析 `.animation` JSON 烘焙进帧表**（服务端纯计算，契合现有架构）或 (b) 自研 C→S 回传（延迟+反作弊风险）。裁决：走 (a)，(b) 拒绝。
4. ⚠ 若照 GL3 老直觉（Animatable/AnimationTickHandler/setAnimation 发包）写适配器会全错——GL4 是 GeoAnimatable/AnimationController/triggerAnim。

## 二、掉落管线调研（TF 缓冲入箱 / ES 玩家袋 / Cataclysm 首杀）

- **TF 缓冲防的四种丢失**：演出期物品被火/岩浆/摔落/清理；6000t 过期；崩档/区块卸载（缓冲在实体 NBT 随存档走）；原版即时 dropAll 的满包/不在场问题。时序：**die() 即 roll 入 27 格缓冲**（`ContainerHelper.saveAllItems/loadAllItems`，1.20.1 两参签名实证于 IBossLootBuffer:40）→ tickDeath 演 175t → **remove() 时才放箱**（动画期箱子不存在，无从挖箱）。
- **TF 留下的两个洞（Colossus 已修）**：① 溢出兜底子列表起点 28 的 off-by-one 会静默丢第 28 堆——我们按"前 27 进缓冲、超出即时落地"处理；② 家点被玩家放不可替换方块时 `setBlock` 失败 → 缓冲 loot **静默丢失**——我们放箱失败退化为落地+延长寿命，绝不静默丢。放箱后无防熊（普通箱子），暂不复制。
- **ES 玩家袋（1.21.1，需降级翻译）**：loot 不做预 roll，而是把 loot table key+挑战次数烧进 DataComponents、**右键开袋才 roll**（自定义 LootContextParam 注入）；防抢用 `setTarget(owner)` 原版机制；`IMPORTANT_ITEM` mixin 免伤。1.20.1 对应：ItemStack NBT、`LootParams/LootContextParams`（复数→单数改名发生在 1.20.2+）、`EntityItemPickupEvent#setCanceled`。**裁决：v0.3**（需 loot condition 注册表与自定义 param set）。
- **Cataclysm 首杀**：SavedData 按维度存 `DefeatedOnce` bool（永不复位）；首杀才遍历全服玩家 `displayClientMessage(..., actionbar)`。Colossus 用 KillBoard.recordKill 的 `first` 返回值 + 全服播报，同形。

## 三、已落地（v0.2 第五批，构建绿）

`loot/LootDelivery{DROP_NOW, INTO_CHEST, INTO_BAG(占)}`；`ColossusBossEntity`：`shouldDropLoot()` 门控、`rollDeathLoot`（1.20.1 实测形态 `LootParams.Builder+LootContextParams+getRandomItems(params, seed, consumer)`，Hullbreaker/Luxtructosaurus 同构）、缓冲 NBT 键 `ColossusDeathItems`、`deliverLoot`（脚下向上 3 格找可替换位放箱→`WorldlyContainer.setItem`，失败落地兜底）、`broadcastFirstKill`。ExampleColossus 切 INTO_CHEST + `data/colossus/loot_tables/entities/example_colossus.json`（钻石+铁锭池，含 looting_enchant）。

**1.20.1 API 坑记录（本轮编译器抓到）**：`getLootTable()` 返回 **ResourceLocation**（不是 LootTable，要 `server.getServer().getLootData().getLootTable(id)`）；`LootContextParamSets/LootContextParams` 在 `...loot.parameters.` 包；`ItemEntity.pickupDelay` 私有且 1.20.1 无公开 setter（用默认 30t）；`NonNullList.withSize` 定长不能 add（读档侧预分配 27 格配合 `loadAllItems`，写入侧 `createWithCapacity`）。**未验证项**：1.20.1 实体 loot table 的自动派生路径（`entities/<注册名>`）按惯例放置，进游戏开箱验一次。
