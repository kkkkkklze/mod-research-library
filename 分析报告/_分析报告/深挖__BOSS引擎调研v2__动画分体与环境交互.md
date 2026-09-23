# 深挖：BOSS 引擎调研 v0.2 前置——动画系统 / 分体 Boss / 环境交互

> 续篇：《深挖__BOSS引擎调研__六样本共性模式.md》。三路并行源码分析（2026-09-23），服务 Colossus v0.2 的 AnimBackend、`entity.part`、`env` 三个新包设计。

## 一、动画/动作系统：v0.1 契约被反向验证，且有精确升级路径

库内盘点：GeckoLib 使用者 15 仓；但 `_bulk/bernie-g__geckolib` 快照是 **GL 5.5.5（com.geckolib 包）**，库内没有 GL3(1.20.1) 的 sync 源码——"GL3 用 entityData STRING+INT 同步动画"这一条是既有知识而非本库证据，落地前需反编译实际 GL3 jar 复核。

三个代表系统：
1. **Citadel/Lionfish（Cataclysm 血统）**：`AnimationMessage(entityId, indexOf(animations[]))` ——数组索引即线路协议，重排即静默错位。v0.1 拒绝字符串索引协议的裁决被第三个样本确认。
2. **Iron's Spells**：逻辑侧只用布尔 flag 同步（`DATA_CANCEL_CAST` 等），全库无 keyframe event 用于逻辑——"不用动画事件也能做 Boss"的最强证据。
3. **DBE animation_graph（1.21.1）**：服务端图执行器 + `GraphAnimationSyncSnapshot(entityId, graphId:ResourceLocation, params)` ——**按名字同步**的又一独立佐证；但引擎 2 万行级，Colossus 拒绝跟进。

**1.20.1 服务端"跟随动画"的真实替代方案 = Alex's Caves Forsaken（原生 Forge 1.20.1，最佳样本）**：
- 双端各自计 tick（同一起始包对齐后独立 `AnimationHandler.updateAnimations`），命中判定用**窗口** `tick∈[15,18]` 而非单帧等值；
- `getHandPos(animationTick)` 用**分段解析公式**在服务端近似手部骨骼位姿——不采样动画、纯轨迹表。

→ Colossus 结论表：吸收 名字协议/双端计数/窗口判定/轨迹预计算（AnchorSampler 兜底后端）/flag 驱动 Layer；拒绝 索引协议/keyframe event→逻辑（GL3 事件只在客户端触发，跨端语义不闭合）/服务端动画图。升级项：给 AttackState 的触发帧加 `[a,b]` 窗口形态 + 漂移纠偏。

## 二、分体 Boss：四种建法与一条"零包正解"

（样本：Cataclysm partentity+Leviathan、TF Naga/Hydra(+HeadContainer)、首领崛起 Sandworm/Kraken parts、Confluence DeadBodyPart）

**A. 建法谱系**：① Forge `PartEntity` 虚拟部件（主流；`getAddEntityPacket` 抛 UOE、不存档、尺寸归 0 = 失活而非删除、客户端 id = parentId+index 伪造）；② 虚拟部件 + **体外容器状态机**（TF `HydraHeadContainer` 不是实体，持 1 头 5 颈自 tick 自存档——分体逻辑收敛的最佳形状）；③ **真实体 squad 成员**（KrakenTentacle 有血条/NBT/die，内部又挂一层 PartEntity——嵌套）；④ 纯客户端尸体碎块（Confluence 从渲染骨骼快照生成，不进服务端）。

**B. 受击路由**：统一骨架 `part.hurt → parent.attackEntityFromPart(...)`，差别全在倍率与闸门位置：段伤 2/3（Naga）、弱点 ×1.5（Netherite part 侧生效——parent 侧同逻辑是死代码）、免伤闸门链（Hydra：自伤过滤+死头免伤+距离门+嘴张开姿态门）。护盾相位：Hydra 让本体 `hurt` 拒绝一切、只许部件路径进血；Kraken 用"8 触手全死才 setBossPhase(1)"。部件独立血两派：TF 伤害记账累加（`damageTaken vs HEAD_MAX_DAMAGE`，部件 health 字段近乎装饰）vs 首领崛起 **INT 位图无血量**（`DATA_DAMAGED_SEGMENTS`，受伤段叠伤害+反击弹道，潜水一次性洗掉）。

**C. 跟随算法三档**：骨骼采样（需 ServerAnimationPlayer，1.20.1 不可得）→ **状态表+数学插值**（Hydra：`Map<State,Float>[]` 四张表 + `clampedLerp(prev,cur,t)` + 5 点直连脖子——可泛化为 PartRig）→ 纯链式数学（Naga 脊椎：固定间距+直化权重 `0.05+1/(i+1)*0.5`+`atan2` 反推旋转）。**关键发现**：部件位置同步在 Forge 侧不需要任何包——Cataclysm 注册的 `MessageCMMultipart` 全仓从未被 send，部件是**两侧从已同步的 parent pos/rot+状态各自推导**；TF 需要发包只因它是 Fabric hook 了 ServerEntity。这正落在 v0.1"战斗状态零自定义包"铁律内：**部件状态挂 parent entityData（位图+每部件少量标量），客户端 onSyncedDataUpdated 回放**——正解而非妥协。

**D. 血条聚合**：队长制天然成立（部件伤害全转 parent 血）；真聚合只有 Kraken：`Σ(成员血比)/定义总数`（分母写死声明数防 bar 回弹，代价是重生中成员计 0）；**所有权教训**——父类每 tick 无条件 setProgress，子类靠同 tick 覆盖，脆弱；Colossus 应做 `bindBarOwner(FloatSupplier)` 单一所有权。Naga 中间态：血条→剩余段数读数表（段数=clamp(hp/(max/10)+2)，减段阶梯延迟爆散+按段数加速 modifier）。

**E. 重生**：Hydra（砍 1 长 2 倒计时、`-1` 哨兵天然限并发、死后 counter 全清、存档只写"活头数"）；Kraken（**绝对 gameTime 排序集**存 NBT，重启/卸载不漂移；死亡计数驱动增援波；结算点=实体真移除，动画期间仍占血条分子）。

## 三、环境交互：竞技场会话的空白确实存在，碎片可拼

**A. telegraph 危险区两形态**：① BR IceSpikeCluster——危险区是**实体自算的纯数据**（`getDangerZones()` 由同步的 delay 推导，零包），到期服务端 AABB 一次性结算（冻结+伤害），玩家不需要"踩中"事件；渲染 = GeoRenderLayer 贴地 quad+循环 easeOut 残影。② Cataclysm Lightning_Area——危险区是**真实体**（仿 AreaEffectCloud，同步 radius/waiting），等待期客户端撒粒子，到期起每 5t 周期结算、radiusPerTick 扩散。两形态覆盖 80% 需求。
**B. 破坏/改变方块**：NagaSmashGoal（扫 AABB 蹭碎叶子+mobGriefing 门控+防卡洞传送归位）；Yeti（玩家砸冰=开战触发器 `setCanceled+换AIR+INTRO`；拍地按 **BREAK_1..4 方向偏移表**逐帧破块；跳跃碾压用 destroySpeed 区间过滤硬块）；InfernalDragon（射线步进吐息点火 + 开战 `closeOffExit()` 深板岩封出口）。
**C. 锁区/会话**：TF ProgressionEvents（StructureStart bbox + advancement 不足→拦截 break/place/interact + 客户端红框包 + `ProtectionBox` 纯客户端画栏实体）；BR StructureDestructionEvents（取消破坏/放置/爆炸影响，**"已击败"判定用 POI 不读结构 NBT**——最便宜的做法，近乎可照搬）；HugeDoor（方块属性驱动开门动画）；CAT 重召石 `anyPlayerInRange(50)+LIT→19t→spawn+自毁`。
**D. 环境杀手**：Kraken 战斗期每 40t `setWeatherParameters(0,60,true,true)` 强制雷雨、死亡放晴（**相位=氛围开关**）；Scylla 水中浮力 `setDeltaMovement(+0.05y)`。
**E. 移动战场**：KrakenShipCache——离线 jigsaw 生成→前后快照 diff 出方块集→静态 `BLOCK_CACHE<Map<Vec3,BlockState>>` 按 chunkKey；受击 O(1) 换 destroyed 变体；全体局部坐标 `shipToWorldSpace(offset)`；`isArenaLoaded()`（±32 格步进 16 查加载）**未加载则卡相位不推进**——分阶段相位机的加载闸门。

## 四、v0.2 裁决汇总（进 Colossus）

- **优先级 1 TelegraphZone**（两形态 + `MoveDef` 帧表驱动 fire 时刻——BR 靠 GeckoLib 关键帧指令的部分，1.20.1 用我们已有的触发帧表替代，无缝）
- **优先级 1.5 触发帧窗口化**：`at(t)` 保留 + 新增 `between(a,b)` 单次窗口判定（Forsaken 实证 + 漂移容错）
- **优先级 2 entity.part**：`ColossusBossPart`（PartEntity+parent entityData 位图+`applyPose` 双侧同算）+ `PartRig`（Hydra 状态表泛化）+ `OffsetAnchor/ChainAnchor/BoneAnchor(空壳)`；`hurtPart/partGate` 挂现有基类；`bindBarOwner` 修血条所有权
- **优先级 3 env**：`ArenaBlockAccess`（clearBox/偏移表 pattern/mobGriefing+tag 豁免）、结构保护+POI 解锁（近照搬级）、closeOffExit/弹出会话
- **进 v0.3**：KrakenShipCache 方块缓存换块、服务端 squad 复杂增援
- **拒绝**：动画图/IK/root-motion、部件级自定义位置包、Fabric 式 ServerEntity ASM

## 五、样本路径索引（增量）
Forsaken：`_bulk/AlexModGuy__AlexsCaves/.../server/entity/living/ForsakenEntity.java`(:283 双端计数,:292-307 轨迹表)+`ForsakenAttackGoal.java:166`；Hydra 家族：`_bulk/marlester-dev__twilightforest-unofficial/.../entity/boss/Hydra{,Head,Neck,HeadContainer,Mortar}.java`、`Naga{,Segment}.java`、`entity/ai/goal/NagaSmashGoal.java`；parts：`_bulk/lender544__new1.20.1/.../entity/partentity/Cm_Part_Entity.java`+`The_Leviathan/`；BR parts/state：`_pack_decompiled/璇穹之歌/[首领崛起].../entity/boss/part/`、`geckolib/DangerZonesProvider.java`、`entity/boss/kraken/`、`entity/boss/sandworm/SandwormEntity.java:450-538`、`structures/KrakenShipStructure.java`、`event/StructureDestructionEvents.java`；Confluence 碎块：`_bulk/MagicHarp__confluence/.../common/entity/DeadBodyPartEntity.java`+`util/DeathAnimUtils.java`；Lionfish 协议：`_bulk/lender544__Lionfish-API/.../server/animation/AnimationHandler.java`；DBE：`_参考仓库/DBE-1.1.0-neoforge-1.21.1/` animation_graph。

**风险注记**：本轮 Agent C 引用了 `_pack_decompiled/璇穹之歌/L_Ender's Cataclysm 1.21.1-3.32`（新样本，非上轮 1.20.1 移植版）；GeckoLib3 同步形态在库内无一手证据，落地 GL3 适配前先反编译复核。

**⚠ 后续更正（2026-09-23 v4 取证）**："GL3 for 1.20.1" 不存在——GL3 止步 1.19.2，1.20.1 的官方适配是 **GeckoLib 4**（本机有 4.4.9 sources jar 一手证据）。GL4 同步内核=字符串 `triggerAnim` 包、无服务端动画时钟、无 C→S 通道——本文相关结论（"GL3 没有 ServerAnimationPlayer 所以要抽象后端"）方向不变但版本名错误，适配器按 GL4 API 写。详见《深挖__BOSS引擎调研v4__掉落管线与GeckoLib版本反转.md》。
