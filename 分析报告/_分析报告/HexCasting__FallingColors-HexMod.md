# Hex Casting（FallingColors/HexMod · 0.11.4 · MC 1.20.1）源码分析报告

> 分析对象：https://github.com/FallingColors/HexMod（main 分支，`modID=hexcasting`，`modVersion=0.11.4`，MC **1.20.1**，Kotlin 2.2.21 为主）
> 源码位置：`Mod源码研究汇总\源码库\_参考仓库\_bulk\FallingColors__HexMod`（浅克隆，含 java+kt+json）
> 方法：三名分析员分头精读"解释器核心 / 注册与 API 与文档管线 / 客户端渲染与同步"三块（草稿在 `Downloads/_hex/parts/`），关键论断由我二次核验（标 ✅ 处）。
> 特别之处：**这个 mod 的作者自己写了 VM 设计文档**——`api/casting/eval/README.md`，本文第 3 节直接引用它。

---

## TL;DR

**Hex Casting 是把"编程语言"做进 Minecraft 的魔法 mod**：玩家在六边形格上画出图案（pattern）当作指令，图案序列进一台**栈式虚拟机**执行，操作法术书/世界/实体。它的工程价值不在"魔法特效"，而在于**用最小的原语实现了一套完整的可编程系统**，并且把这套系统的对外接口、错误模型、文档管线都做成了可持续维护的形态。

| 关键数字 | 值 |
|---|---|
| 内建指令（`Op*`） | **113 个**，按域分包（spells 22 / arithmetic 13 / rw 8 / escaping 8 / stack 6 / great spells 5 / queryentity 5 / eval 5 / types 4 / sentinel 4 / lists 4 / selectors 3 / raycast 3 …）✅ |
| iota（值类型） | **11 种**：Boolean / Double / Vec3 / Entity / List / Pattern / Continuation / Null / Garbage / IotaType 基类 |
| Mishap（错误类型） | **29 个**（每个错误一个类，如 `MishapDivideByZero`、`MishapNotEnoughArgs`、`MishapUnenlightened`） |
| 代码规模 | Common 513 文件（Kotlin+Java）、Fabric 52、Forge 45 |
| 文档 | Patchouli 书 `thehexbook`（patterns 18 + items 18 + spells 9 + great_spells 8 + lore 8 + greatwork 8 + casting 7 + categories 7 + templates 5）+ **hexdoc（Python）自动生成网页版魔法书** |
| 多加载器 | `Common/` + `Fabric/` + `Forge/`，平台差异走 `xplat/` 抽象 |

**三条最值得学的设计**（详见第 4 节）：
1. **状态与模拟器分离**：`CastingImage`（唯一被序列化的"内存快照"）vs `CastingVM`（每次需要时重建的瞬态模拟器）vs `CastingEnvironment`（抽象"谁在施法"：法杖 / 饰品 / 法阵）——存档/网络只碰 Image，逻辑都在 VM。
2. **错误即值 + 副作用列表**：一次执行返回 `OperationResult{ 剩余 continuation, 新的 CastingImage, List<OperatorSideEffect> }`，**扣媒介、放法术、报错（Mishap）都是副作用**，按顺序应用；任何副作用要求停止就停止。
3. **用链表当调用栈**：`SpellContinuation` 是链表实现的调用栈，只有 3 种帧（`FrameEvaluate` 顺序执行、`FrameForEach` 遍历、`FrameFinishEval`），却足以表达 call / 删帧 / foreach 三种控制流——即游戏内三个"Gambit"法术（Hermes 调用、Charon 删帧、Thoth 遍历）。

---

## 1. 基本信息

| 项 | 值 |
|---|---|
| mod id / 名称 | `hexcasting` / **Hex Casting**（"六边形法术"） |
| 版本 / MC | 0.11.4 / **1.20.1** |
| 语言 | **Kotlin**（2.2.21）与 Java 混排；构建用 Gradle Kotlin 支持 |
| 模块 | `Common/`（共享逻辑 513 文件）+ `Fabric/`（52）+ `Forge/`（45）；根目录另有 `doc/`（hexdoc 配置）与 `pyproject.toml`（Python 打包） |
| 依赖 | `paucal 0.6.0-pre-118`（Hex 生态的"按需加载/延迟注册"库）、`patchouli 83`（游戏内书）、`jei`/`emi`、`pehkui`、`cloth config 11.1.106`、JetBrains 注解 23.0.0 |
| 作者/维护 | 代码作者 `at.petrak`（包名 `at/petrak/hexcasting`），组织 FallingColors；文档站（hexdoc-hexcasting）由 object-Object / Alwinfy 维护 |
| 设计文档 | **`Common/src/main/java/at/petrak/hexcasting/api/casting/eval/README.md`**（作者自述"because I keep forgetting"），本文第 3 节引用 |

---

## 2. 规模与包结构

- 包根：`at.petrak.hexcasting`，分三块——**`api/`（对外稳定面）/ `common/`（内容与实现）/ `client/`（客户端）**，另有 `xplat/`（平台抽象）。
- `api/casting/` 是语言本身的定义：`eval/`（VM）、`iota/`（11 种值）、`mishaps/`（29 种错误，含 `circle/`）、`arithmetic/`（含 `operator/`）、`math/`、`castables/`（能施法的物品/实体）、`circles/`（大法术/法阵）、`PatternShapeMatch.java`、`ActionRegistryEntry.java`、`RenderedSpell.kt`、`ParticleSpray.kt`、`SpellList.kt`。
- `api/` 其余：`addldata/`（数据附件）、`pigment/`（颜料）、`player/`、`item/`、`block/`、`misc/`、`utils/`、`HexAPI.java`、`mod/`（兼容与元数据）。
- `common/`：`casting/`（`PatternRegistryManifest` + `actions/` 113 个 Op + `arithmetic/`）、`blocks/`、`entities/`、`items/`、`recipe/`、`loot/`、`particles/`、`msgs/`（网络）、`command/`、`impl/`、`lib/`、`misc/`。
- `client/`：`render/`（含 `PatternRenderer` / `RenderLib.kt` 的 `makeZappy`）、`gui/`、`particles/`、`model/`、`sound/`、`ktxt/`。
- `eval/vm/`：`CastingVM.kt`、`CastingImage.kt`、`SpellContinuation.kt`、`ContinuationFrame.kt`、`FrameEvaluate.kt`、`FrameForEach.kt`、`FrameFinishEval.kt`、`FunctionalData.kt`。
- `eval/env/`（"谁在施法"的实现）：`StaffCastEnv`（法杖）、`PackagedItemCastEnv`（饰品/卷轴）、`CircleCastEnv`（法阵）、`PlayerBasedSpiralPatternCastEnv`、以及配套的 `*MishapEnv`。

---

## 3. 架构总览（引作者的设计文档）

`eval/README.md` 把流水线写得比任何二手描述都清楚，要点：

- **`CastingVM` = 模拟器**（"figure out what to do with an incoming iota"，瞬态，每次需要时重建）；
- **`CastingImage` = 内存快照**（"the only thing serialized to NBT"）；
- **`CastingEnvironment` = 谁在施法**（抽象类，Hex 自己与 addon 都继承它来定义新的施法载体）。
- **一次执行（11 步，原文顺序）**：iota（或 iota 列表）进入 `CastingVM#queueAndExecuteIotas` → 包进 `FrameEvaluate` → 循环取栈顶帧 → 帧回调 `executeInner` → 预检查（intro/retro/consideration、转义内嵌 iota）→ `executePattern`（图案匹配到 action 或特殊处理器并执行）→ 得到 `OperationResult{剩余 continuation, 新 CastingImage, List<OperatorSideEffect>}` → 附加显示信息（GUI 里图案颜色、音效）→ **逐个应用副作用**（若要求停止就停止）→ 继续下一个 iota 或返回上一层帧 → 帧栈空则结束。
- **Continuation = 链表实现的调用栈**，帧有三种：`FrameEvaluate`（要执行的 iota 列表；法杖每次只放 1 个图案、饰品放全部、Hermes' Gambit 压入新帧）、`FrameForEach`（Thoth's Gambit 的遍历状态：模板栈 + 剩余列表 + 累积输出）、`FrameFinishEval`。
- 帧可以**压入新帧、弹出自身、甚至移除下方的帧**——这就是 Hermes（调用）/ Charon（删帧）/ Thoth（遍历）三个 gambit 的实现方式。

**为什么这个设计值得学**：它把"一门语言要有的东西"拆到了最小可组合的原语——值与类型（iota）、指令（Op/action）、控制流（continuation 帧）、错误（Mishap）、代价（media 副作用）、宿主（Environment）——每一块都能被 addon 扩展，而核心 VM 不需要知道具体有哪些法术。

---

## 4. 子系统详解（三个角度）

### 4.1 解释器 / 虚拟机核心（施法如何执行）

#### Hex Casting 施法解释器 / 虚拟机核心

路径均在 `Common/src/main/java/at/petrak/hexcasting/` 下简写。

##### 1. 执行模型

**裸栈式（postfix / RPN）+ 显式 continuation 栈的混合虚拟机**，没有 AST、没有编译器，源程序就是"被画出来的 pattern 序列"。

核心类：

| 类 | 职责 |
|---|---|
| `CastingImage`（`api/casting/eval/vm/CastingImage.kt:19`） | 不可变 VM 状态：`stack: List<Iota>`、`parenCount/parenthesized/escapeNext`、`opsConsumed`、`userData: CompoundTag` |
| `CastingVM`（`vm/CastingVM.kt:25`） | 解释器主体：持有 image + `CastingEnvironment`，跑主循环 |
| `SpellContinuation`（`vm/SpellContinuation.kt:12`） | sealed 类型 `Done` / `NotDone(frame, next)`，本质是**帧栈（CPS）** |
| `ContinuationFrame`（`vm/ContinuationFrame.kt:25`） | 三种帧：`FrameEvaluate`（顺序执行一段 pattern 列表）、`FrameForEach`（Thoth/foreach）、`FrameFinishEval`（Hermes 边界标记） |
| `CastResult` / `OperationResult`（`eval/*.kt`） | 单步执行结果：新 image + 新 continuation + sideEffects + 声音 |
| `Action`（`api/casting/castables/Action.kt:31`） | 一个"指令"的行为，`operate(env, image, cont)` |

主循环 `CastingVM.queueExecuteAndWrapIotas`（`vm/CastingVM.kt:41`）：
1. 把待执行 iota 包成 `FrameEvaluate` 压入 continuation（:43）；
2. `while (continuation is NotDone && !earlyExit)`（:47）取栈顶帧 `frame.evaluate(...)`；
3. 结果做两道体检：栈序列化超限 → `MishapStackSize`（:55）、`opsConsumed > env.maxOpCount()` → `MishapEvalTooMuch`（:62）；
4. 写回 `this.image`、`env.postExecution`、`performSideEffects`（:75-87）；
5. `earlyExit = !lastResolutionType.success`（:88）——**任何失败立即终止本 tick 的循环**，但 continuation 保留。

单 iota 分派在 `executeInner`（:108）：先处理 `escapeNext`（Consideration 逃逸，:115）、再处理括号态 `executeInParens`、否则 `execute`；整段包在 `try/catch(Exception)`，任何未预期异常降级为 `MishapInternalException`（:142-161）。

**一次施法完整链路（法杖）**：客户端 `GuiSpellcasting.drawEnd()` 画完一笔 → `MsgNewSpellPatternC2S`（`client/gui/GuiSpellcasting.kt:302`；`common/msgs/MsgNewSpellPatternC2S.java:22`）→ 服务端 `StaffCastEnv.handleNewPatternOnServer`（`eval/env/StaffCastEnv.java:80`，含 pattern 重叠反作弊 :82-100）→ `getStaffcastVM`（Forge 从玩家 persistentData 读 `TAG_VM`，`ForgeXplatImpl.java:290`）→ `vm.queueExecuteAndWrapIota(new PatternIota(...))`（:108）→ 把 image 存回玩家/tick 归零 ops（:114）→ 回发 `MsgNewSpellPatternS2C` 让客户端渲染栈（:121）。另外两条入口复用同一 VM：物品 `ItemPackagedHex.use`（`CastingVM.empty` + `queueExecuteAndWrapIotas`，`:131-132`）、法阵石板 `BlockSlate.acceptControlFlow`（`common/blocks/circles/BlockSlate.java:96-103`）。

Pattern 的语义查找在 `PatternIota.lookupAndOperate`（`api/casting/iota/PatternIota.java:92-185`）：查表 → `env.precheckAction` → 取 `Action` → `action.operate(...)`，这是"一条指令"的真正执行点。返回值 `CastResult` 里同时携带"下一步该跑什么"（`continuation`）、"栈变成什么样"（`newData`，为 null 表示不改）和"给客户端看什么"（`resolutionType` + 声音），因此同一个 pattern 在"普通执行 / 括号内收集 / 元求值"三种语境下走的是三个不同的分派口（`execute` / `executeInParens` / `operateInParens`），规则集中、不必在每条指令里 if-else。

另外注意 `env.postExecution` 是**每一步**都调用（`CastingVM.kt:78`），`postCast` 只在整次施法结束时调用一次（`:100`）——音效去重、螺旋 pattern 展示、堆栈 UI 广播都挂在这两个钩子上（`eval/env/PlayerBasedSpiralPatternCastEnv.java:31-50`）。

##### 2. Iota 类型系统

内置 9 种（`common/lib/hex/HexIotaTypes.java:36-44`）：`null / double / boolean / entity / list / pattern / garbage / vec3 / continuation`。抽象基类 `Iota`（`api/casting/iota/Iota.java:23`）用 `(IotaType, Object payload)` 泛化，子类提供 `isTruthy / toleratesOther / serialize`。

- **判等不是 `equals` 而是 `tolerates`**：`Iota.tolerates(a,b) = a.toleratesOther(b) || b.toleratesOther(a)`（`Iota.java:155`），且先比类型（`typesMatch`，按注册表 key）。double/vec 用容差 `DoubleIota.TOLERANCE = 0.0001`（`DoubleIota.java:14,36`）；`ListIota` 逐元素递归（`ListIota.java:61-86`）；EntityIota 比对象引用（`EntityIota.java:30-34`）。
- **类型检查在两层**：① 指令参数层——`List<Iota>.getDouble/getEntity/getList/...` 扩展函数（`api/casting/ActionUtils.kt:25-120`）失败抛 `MishapInvalidIota`，并带"相对栈顶倒序下标"用于把肇事值改成 garbage；② 算术层——`IotaPredicate` / `IotaMultiPredicate`（`arithmetic/predicates/`）声明式描述参数类型，由 `ArithmeticEngine` 匹配（见 §7）。
- **序列化**：统一 `{ "hexcasting:type": id, "hexcasting:data": tag }`（`IotaType.serialize`，`iota/IotaType.java:62-81`）。只走 NBT，网络也发 NBT（`ExecutionClientView.stackDescs` 是 `List<CompoundTag>`，`eval/ExecutionClientView.kt:8`），客户端拿 tag 自行 `display`，避免"服务端翻译好的字符串无法换行"。
- **尺寸保护**：`MAX_SERIALIZATION_DEPTH = 256`、`MAX_SERIALIZATION_TOTAL = 1024`（`HexIotaTypes.java:25-26`），超限直接降级为 `GarbageIota`；反序列化未知类型→`GarbageIota`、返回 null→`NullIota`（`IotaType.java:127-144`）——**永不抛异常，静默降级**。
- `PatternIota` 是唯一"可执行"的普通 iota（`executable()=true`，`PatternIota.java:69-82`）；`ContinuationIota` 把 continuation 升为一等值（`iota/ContinuationIota.java:22-57`），供可中断 eval 使用。

##### 3. 错误模型 Mishap：异常外壳、值内核

`Mishap : RuntimeException`（`api/casting/mishaps/Mishap.kt:23`），但在 VM 里被**强制实体化**：

1. `Action.operate` 抛 mishap；
2. `PatternIota.lookupAndOperate` 的 `catch (Mishap)`（`PatternIota.java:170-184`）把它转成 `CastResult(sideEffects = [OperatorSideEffect.DoMishap], resolutionType = mishap.resolutionType(env), sound = MISHAP)`，且 `newData = null`（**保留旧 image**，即被中断的那一刻的栈）；
3. `CastingVM.performSideEffects`（`CastingVM.kt:167`）调用 `DoMishap.performEffect`（`OperatorSideEffect.kt:56-71`）：喷粒子 + `mishap.execute(env, ctx, stack)` **直接改栈**。

也就是说 mishap 既是异常、也是"值"，还是一段**对玩家的惩罚脚本**：`MishapInvalidIota` 把肇事参数换成 `GarbageIota`（`MishapInvalidIota.kt:23-25`）、`MishapBadEntity` 把手持物扔向目标（`MishapBadEntity.kt:17-19`）、`MishapEvalTooMuch` 让施法者溺水（`MishapEvalTooMuch.kt:56-58`）、`MishapStackSize` 清空栈塞一个 garbage（`MishapStackSize.kt:37-40`）。

- **冒泡**：`resolutionType` 默认 `ERRORED`，可覆盖为 `INVALID`（"你没资格/画错了"，`MishapUnenlightened.kt:18`、`MishapInvalidPattern.kt:20`）或 `ERRORED`（"能算但失败了"）。两者 `success=false`，触发 `earlyExit` 终止本 tick 循环（`CastingVM.kt:88`）。
- **能看到**：玩家路径 `PlayerBasedCastEnv.postExecution → sendMishapMsgToPlayer`（`eval/env/PlayerBasedCastEnv.java:84-92, 224-229`，走 `mishap.errorMessageWithName` 加指令名前缀）；法阵路径 `CircleCastEnv.postExecution → impetus.postMishap`（`CircleCastEnv.java:94-104`；`BlockEntityAbstractImpetus.java:96`）把错误**写进方块展示**。
- **与继续/中断的关系**：失败中断"当前这次 `queueExecuteAndWrapIotas`"，但 `StaffCastEnv` 仍把 image 存回玩家并 `withOverriddenUsedOps(0)`（`:114`），所以下一个 pattern 会在**保留栈**的状态上继续——除 mishap 自己主动改栈之外。这就是"画错一笔不用重开"的机制。

##### 4. continuation / 延迟执行

为什么需要：① **元求值**（`OpEval` 动态执行栈上的列表，需要返回点；`OpForEach` 需要循环状态）；② **可中断**（`OpHalt` 沿 `breakDownwards` 一路弹帧直到 `FrameFinishEval`/`FrameForEach` 边界，`eval/actions/OpHalt.kt:14-27`）；③ **可持久化**（帧全部实现 `serializeToNBT`，`SpellContinuation.serializeToNBT`，`vm/SpellContinuation.kt:19-30`；带类型 id 由 `HexContinuationTypes` 注册表还原，`ContinuationFrame.kt:62-107`）。

与 MC tick 的配合，base mod 里**靠"一 tick 一步"而不是 tick 内暂停**：

- 法杖：每 tick 一个 pattern = 一次 `queueExecuteAndWrapIota`，`CastingImage` 序列化进玩家 persistentData（`ForgeXplatImpl.java:223, 290, 588`），`opsConsumed` 每 tick 归零（`StaffCastEnv.java:106,114` 的 TODO 就是在讨论这个）。
- 法阵：`CircleExecutionState.tick`（`api/casting/circles/CircleExecutionState.java:244`）每 tick 执行一个方块组件，`BlockEntityAbstractImpetus.tickExecution` 用 `level.scheduleTick(..., state.getTickSpeed())` 驱动（`:131`），速度 `max(2, 10-(reachedSlate-1)/3)`（`:320-322`），每过一块 `withOverriddenUsedOps(0)`（`:310`）。
- 代码中已有"delays, where we pause execution"的注释（`ContinuationFrame.kt:41`），但本仓库**没有 OpDelay 实现**（未确认是否在其他分支）——帧序列化能力是为它/为存档预留的。
- `ContinuationIota` + `OpEvalBreakable`（`common/casting/actions/eval/OpEvalBreakable.kt:11-19`）把"当前 continuation"压栈，使脚本可以自己操纵控制流（相当于 `call/cc` 的受限版）。

##### 5. 成本系统（media / 紫水晶）

- **成本来源**：写死在 Action 里。`ConstMediaAction.mediaCost`（`castables/ConstMediaAction.kt:19`）固定值，`SpellAction.Result(effect, cost, particles, opCount)`（`SpellAction.kt:74`）动态算；常见量级 `DUST_UNIT=10000`、`CRYSTAL_UNIT=10*DUST_UNIT`（`api/misc/MediaConstants.java:4-9`），例：大传送 `10*CRYSTAL_UNIT`（`great/OpTeleport.kt:59`）。
- **两段式扣费**：先 `env.extractMedia(cost, simulate = true)` 预检，不足抛 `MishapNotEnoughMedia`（`ConstMediaAction.kt:41`、`SpellAction.kt:52`）；成功后生成 `OperatorSideEffect.ConsumeMedia`，在副作用阶段真正扣（`OperatorSideEffect.kt:43-47`）。**代价：失败时 mishap 自己也会再 `extractMedia(cost,false)`，media 照样白花**（`MishapNotEnoughMedia.kt:16-18`）。
- **修饰**：`CastingEnvironment.precheckAction` 设置 `costModifier`（`CastingEnvironment.java:191-213`，config 单 action 缩放 × 全局缩放），玩家再乘 `MEDIA_CONSUMPTION_MODIFIER` 属性（`PlayerBasedCastEnv.java:73-79`），带 `cannot_modify_cost` 标签的除外。
- **媒体来源**：玩家背包/饰品里的 `ADMediaHolder`（`MediaHelper.scanPlayerForMediaStuff`，`api/utils/MediaHelper.kt:65`），耗尽后可 **overcast 用血换 media**（`PlayerBasedCastEnv.java:172-192`，速率 `mediaToHealthRate`，需要成就解锁 `canOvercast`）；法阵从 `BlockEntityAbstractImpetus` 的 media 池取，`media < 0` 表示创造模式无限（`CircleCastEnv.java:113-129`）。
- 运行时额度：`maxOpCount` 默认 100000（`api/mod/HexConfig.java`，`DEFAULT_MAX_OP_COUNT`），超限 → `MishapEvalTooMuch`（`CastingVM.kt:62`）。
- 一个反直觉点：**算术运算符不花 media**（`OperatorBasic.operate` 只 `opsConsumed + 1`，`arithmetic/operator/OperatorBasic.kt:24`），media 只跟"法术类"指令挂钩；而"步数"上限是全局共享的（`CastingImage.opsConsumed` 随 image 存进 NBT），跨 tick 的法杖施法靠 `withOverriddenUsedOps(0)` 手动清零，等价于"每个 pattern 一份新预算"。

##### 6. Great Spell 与法阵（circles 包）

这是**两套独立机制**，容易混：

1. **Great Spell** = 同一个 pattern 体系里的"高级法术"。数据上用 tag 标记：`requires_enlightenment` + `per_world_pattern` + `can_start_enlighten`（`datagen/tag/HexActionTagProvider.java:25-36`，覆盖 lightning/teleport/great/brainsweep 等）。执行时 `PatternIota` 检查标签与 `env.isEnlightened()`，不满足抛 `MishapUnenlightened`（`PatternIota.java:108-117`，会丢手持物+破音效）。`per_world_pattern` 的图案由 `ScrungledPatternsSave` 按世界随机生成，查表顺序：普通签名 → 每世界 → special handler（`common/casting/PatternRegistryManifest.java:92-127`）。
2. **法阵（spell circle）** = 用方块搭出的"多步仪式程序"，建模为**图灵机式的方块游走**：`ICircleComponent.acceptControlFlow(imageIn, env, enterDir, pos, bs, world)` 每个方块拿到当前 image、返回 `ControlFlow.Continue(新image, 出口集合)` 或 `Stop`（`api/casting/circles/ICircleComponent.java:48-49, 156-169`）。`CircleExecutionState.createNew` 用 flood fill 从 impetus 出发验证闭环并顺带算出 AABB 与长度上限（`maxSpellCircleLength` 默认 1024，`CircleExecutionState.java:95-177`）；`tick` 每 tick 只推进一步并做"出口必须唯一，否则报 many_exits"的检查（`:275-311`）。环境是 `CircleCastEnv`：extra denylist（`isActionAllowedInCircles`）、media 从方块扣、mishap 变成方块文字（`CircleCastEnv.java:69-129`）。石板 `BlockSlate` 就是"一条 pattern 指令"（`BlockSlate.java:79-104`）。

##### 7. Operation 注册

构成 = `ActionRegistryEntry(prototype: HexPattern, action: Action)`（`api/casting/ActionRegistryEntry.java:14`），注册进 `HexActions.ACTIONS` 并由 `register(BiConsumer)` 交给平台注册表（`common/lib/hex/HexActions.java:68-70, 635`，例：`OpEval` :417、`OpHalt` :421、`OpForEach` :584）。

四类 Action 模板：
- `Action`（最底层，自己维护栈与 op 计数；`Action.kt:31-73` 含默认 `operateInParens`，在括号里默认只把 pattern 塞进 parenthesized 列表）；
- `ConstMediaAction`（`argc` + 固定 `mediaCost` + `execute(args, env)`，`ConstMediaAction.kt:17-48`）；
- `SpellAction`（`execute` 返回 `RenderedSpell` + 成本 + 粒子，实际效果在副作用阶段 `cast(env, image)`，`SpellAction.kt:17-74`）；
- `OperationAction`（算术多态转发给 `ArithmeticEngine`，`castables/OperationAction.kt:16-23`）。

匹配用**角度签名**（`HexPattern.getAngles()`，起点方向不算）做 O(1) 索引（`PatternRegistryManifest.processRegistry`，`:41-58`；`NORMAL_ACTION_LOOKUP` :26）。`SpecialHandler`（`castables/SpecialHandler.java:19-40`）先于签名匹配，base 里用于数字字面量与 Bookkeeper's Gambit 掩码（`HexSpecialHandlers.java:17-20`）。算术重载：`Arithmetic` 接口（`arithmetic/Arithmetic.java:11`）声明 `opTypes()/getOperator()`，`ArithmeticEngine` 建 `pattern→OpCandidates(arity, operators)`，用 `IotaMultiPredicate` 匹配并用 `HashCons`（`HexPattern/i类型组合`）缓存解析结果（`arithmetic/engine/ArithmeticEngine.java:28-109`）。

##### 8. 值得学的 6 条做法

1. **状态不可变 + 结果值化**：`CastingImage` 是 data class，每步 `copy()` 出新状态；执行结果 `OperationResult(newImage, sideEffects, continuation, sound)` 一次性描述"发生了什么"。这让回滚、录制、序列化、跨线程都很便宜。
2. **效果与表现延迟到 side-effect 阶段**：指令本身不碰世界，只产出 `OperatorSideEffect`（`ConsumeMedia/Particles/AttemptSpell/DoMishap`，`OperatorSideEffect.kt:19-71`），由 VM 统一执行——声音、粒子、扣费、惩罚全部集中可控。
3. **错误"异常进、值出"**：内部用异常打断（写法简单），边界立刻转成 `DoMishap` 副作用 + `resolutionType`（`PatternIota.java:170-184`），玩家惩罚、错误消息、UI 变色三件事解耦。
4. **一切可序列化**：iota、image、continuation frame、pattern 全有 NBT 形式且有注册表 type id；因此同一套 VM 能跑在玩家 persistentData、物品 NBT、方块 BE 里。
5. **注册表 + 标签 + config 三层治理**：注册表定义"存在什么"，tag 定义"谁能用/是否每世界随机/是否禁止改价"（`api/mod/HexTags.java:73-102`），config 定义"费用缩放与上限"，addon 只需注册不改核心。
6. **硬上限与降级策略**：序列化深度/总量、op 数、法阵长度、栈大小、pattern 重叠反作弊（`StaffCastEnv.java:82-100`）、`HexUtils.fixNAN` —— 每个可能被玩家"玩坏"的维度都有闸门，且超限时降级成 garbage/null 而不是崩服。

##### 9. 三个坑

1. **性能**：主循环是同一 tick 内的 `while`，Thoth 大循环 + 大列表可以瞬间跑满 10 万 op；`OperationResult` 每步都 `toMutableList()` 复制整个栈；`PatternRegistryManifest.processRegistry` 官方 TODO 自认"每次连接都重建索引"（`:36-40`）。想做大世界/大列表必须自己加预算与分片。
2. **同步**：所有状态在服务端，客户端只拿 `stackDescs`（NBT 列表）+ `resolutionType` 渲染（`ExecutionClientView.kt:8`）；忘了回写 `setStaffcastImage` 或漏发 `MsgNewSpellPatternS2C` 就会"本地 UI 与服务端栈不一致"。客户端还会把已画的 pattern 列表回传（`ResolvedPattern`），服务端必须自行校验 origin/重叠，不能信任客户端（`StaffCastEnv.java:82-100` 就是补的这道）。
3. **可玩性 / 版本兼容**：mishap 惩罚重（丢物品、溺水、扣血）与"参数变 garbage 但栈保留"的组合，容易让玩家觉得"莫名其妙的报错"；`IotaType.deserialize` 的静默降级（`IotaType.java:127-144`）意味着你改了 iota 结构后旧存档里的值会变成 garbage/null 而不报错；再叠加"每 tick 一步 + ops 归零"的额度模型，数值平衡（cost × 上限 × overcast）非常难调。

#### 4.2 注册体系 / 公开 API / 数据与文档管线 / 多加载器

#### B. Hex Casting 注册体系 / 公开 API / 数据-文档管线 / 多加载器抽象

源码：`源码库\_参考仓库\_bulk\FallingColors__HexMod`（main 分支，MC 1.20.1，Kotlin+Java 混排）。
代码规模（`find` 统计）：Common 513 个 `.java/.kt` + 713 个 json；Fabric 52 个类 + 405 json；Forge 45 个类 + 437 json。
注意：本工作树是部分检出，`doc/src/**`（hexdoc Python 插件，27 个文件）与 `*/META-INF/services/*` 在磁盘上缺失但被 git 跟踪，本文相关引用取自 `git show HEAD:<path>`。

---

##### 1. Pattern → Action：注册、规范化与匹配

**数据模型**
- `api/casting/ActionRegistryEntry.java:14`：`record ActionRegistryEntry(HexPattern prototype, Action action)`。`prototype` 的 `startDir` 只是"书里画出来的规范起始方向"，注释明确写了 per-world 情况下"angle signature 只是形状，未必是图案本身"。
- `api/casting/math/HexAngle.kt:3-23`：6 个枚举 `FORWARD, RIGHT, RIGHT_BACK, BACK, LEFT_BACK, LEFT`，`fromChar` 只认小写 `w/e/d/s/a/q`（**没有**大写分支，本树中不存在"大小写双轨"）。`HexAngle.rotatedBy` 就是模 6 加法。
- `api/casting/math/HexDir.kt`：6 个方向枚举，`CODEC` 序列化为 `NORTH_EAST` 这种大写名（`HexDir::name`），而 `fromString` 走 `HexUtils.getSafe`（`api/utils/HexUtils.kt:105-111`）做 **lowercase 容错**，所以 json 里写 `north_east` 也能读。签名串必须小写、方向名大小写不敏感——这就是"大小写规则"的全部。
- `api/casting/math/HexPattern.kt`：`anglesSignature()`（84-99）把角度表转成 `"qaq"` 这种串（仅用于显示/日志/文档）；`sigsEqual`（119）比较的是角度表；`compose CODEC`（134-139）字段名与内容**是反的**（`start_dir` 存 angles 串、`angles` 存方向名），靠 `fromAnglesUnchecked` 参数顺序自洽 round-trip，外部（`interop/inline/InlinePatternData.java:83`）也在用这个格式。

**解析/规范化**
- `HexPattern.fromAngles(signature, startDir)`（`HexPattern.kt:161-190`）边解析边维护 `linesSeen` 集合检测自交（"loop back on itself"）并抛 `IllegalStateException`；`fromAnglesUnchecked`（199-209）只查非法字符。注册表里全部用小写签名走这两个入口。
- 运行时"变形"：`api/casting/math/EulerPathFinder.kt:11-31` `findAltDrawing(original, seed)` 把图案转成图、用 `Random(seed)` 做随机 Euler 走查（`walkPath`），得到**同形状、不同起笔/走笔顺序**的新 `HexPattern`。seed 用世界种子 → 同一 Great Spell 每个存档笔画不同。

**匹配（运行时查找是哈希表）**
- `common/casting/PatternRegistryManifest.java:26-27`：`ConcurrentMap<List<HexAngle>, ResourceKey<ActionRegistryEntry>> NORMAL_ACTION_LOOKUP`，key 是 **角度列表**（`entry.prototype().getAngles()`，见 :51），不含 startDir → 匹配天然平移/旋转无关，只对形状敏感，O(1)。
- `processRegistry(ServerLevel)`（:41-65）在客户端/服务器首次启动时扫行动作注册表：打了 `PER_WORLD_PATTERN` 标签的跳过（交给 `ScrungledPatternsSave`），其余塞进 lookup；撞签名只 warn 后覆盖（:53）。注释里作者自己承认 "this should not be run every time the client/server connects"（:36-39 TODO），也是 CHANGELOG 0.11.4 "double pattern registration log spam" 的来源。
- `matchPattern(pat, env)`（:92-119）优先级明确写死：**普通 action → 每世界图案 → special handler**，注释 `I am PURPOSELY checking normal actions before special handlers` 是为了避免"phial 数字字面量事件"；`checkForAlternateStrokeOrders=true` 直接 `NotImplementedException`（:109-111）。返回 `sealed class PatternShapeMatch`（`api/casting/PatternShapeMatch.java:9-57`）四态：`Nothing` / `Normal(key)` / `PerWorld(key, certain)` / `Special(key, handler)`；`certain` 在服务端表示"精确命中，可以真施法"，客户端恒 false。
- 每世界图案存 `server/ScrungledPatternsSave.java`（`SavedData`，键 `hexcasting.per-world-patterns.0.1.0`）：`createFromScratch(seed)` 对所有带 `per_world_pattern` 标签的动作跑 `findAltDrawing`，存 `签名 → (key, canonicalStartDir)`，并维护反向表 `lookupReverse`；`PatternRegistryManifest.getCanonicalStrokesPerWorld`（:130-139）用它还原"书里该画的笔画"。
- `SpecialHandler`（`api/casting/castables/SpecialHandler.java`）是"形状匹配的最后一道"：`Factory.tryMatch(pattern, env) → @Nullable T`，注释把它类比成 `BlockEntityType` vs `BlockEntity`（客户端可以持有 handler，但只在服务端 `act()`）。基模用它做数字字面量与 Bookkeeper's Gambit。

##### 2. 注册表分层与扩展方式

六个自定义注册表：`common/lib/HexRegistries.java:15-22` —— `action` / `special_handler` / `iota_type` / `arithmetic` / `continuation_type` / `eval_sound`，全部是 `ResourceKey.createRegistryKey(modLoc(...))` 的自建注册表（不是 vanilla `Registries`）。

内建内容入口都在 `common/lib/`（不在 `api/`）：
- `common/lib/hex/HexActions.java:74` 拿注册表，`:76` 一个 `LinkedHashMap` 暂存，`:82` 起上百个 `make("get_caster", new ActionRegistryEntry(HexPattern.fromAngles("qaq", HexDir.NORTH_EAST), OpGetCaster.INSTANCE))`；`make` 重名直接抛异常；末尾 `register(BiConsumer)` 把 map 灌进注册表；静态块里按 `PehkuiInterop.isActive()` 条件注册兼容 action。
- `HexSpecialHandlers.java`、`HexIotaTypes.java`、`HexArithmetics.java`、`HexContinuationTypes`、`HexEvalSounds` 同构；`HexItemHolderHandlers.java` 则是普通 `HashMap`（`register(EntityType, Function<Entity,ItemStack>)`）。
- 装填点：Fabric `fabric/FabricHexInitializer.kt:151-156` 用 `bind(IXplatAbstractions.INSTANCE.actionRegistry)`，`bind` 就是 `BiConsumer { t, id -> Registry.register(registry, id, t) }`（:227-228）；Forge `forge/ForgeHexInitializer.java:138` 用 `bind(HexRegistries.ACTION, HexActions::register)`，其 `bind` 挂在 `RegisterEvent` 上（:154-161）。

**外部 mod 注册自己的 action**：拿注册表直接 `Registry.register` 即可（两边通用、和 loader 无关）：
```java
Registry<ActionRegistryEntry> reg = IXplatAbstractions.INSTANCE.getActionRegistry();
Registry.register(reg, new ResourceLocation("mymod", "my_action"),
    new ActionRegistryEntry(HexPattern.fromAngles("qaq", HexDir.NORTH_EAST), MyAction.INSTANCE));
// 想参与标签（需要启发/每世界）就再往 data/mymod/tags/hexcasting/action/*.json 里写 id
```
算符重载另有捷径：`OperationAction(pattern)`（`api/casting/castables/OperationAction.kt`）只存一个图案，执行时转发给 `HexArithmetics.getEngine().run(pattern, ...)`，addon 只需注册新的 `Arithmetic` 就能给 `add` 这类图案加类型分派。
⚠️ 不要调 `HexActions.make(...)`：它只写 Hex Casting 自己的私有 map，只有在 `HexActions.register` 之前调用才会被带上，顺序一错就静默不生效。

##### 3. 公开 API（`api/` 包，149 个文件）

- `api/HexAPI.java`：唯一"门面"。`INSTANCE`（:39-48）用 `Class.forName("at.petrak.hexcasting.common.impl.HexAPIImpl")` 反射加载实现，失败就退回匿名 dummy —— 让 Common 侧代码在没装平台实现时也能跑（`common/impl/HexAPIImpl.java` 只存两张 `ConcurrentMap`：特殊速度 getter、brainsweep 行为）。暴露的东西：i18n key/Component（:57-89）、`getEntityLookDirSpecial`（修 MC-112474 / MC-134707 的投射物/幻翼朝向 bug，:94-96 + HexAPIImpl:39-51）、`registerSpecialVelocityGetter`、`registerCustomBrainsweepingBehavior`/`brainsweep`、`getSentinel`、`findMediaHolder`、`getColorizer`、`robesMaterial()`（`DUMMY_ARMOR_MATERIAL` 占位 + 平台覆写）、以及 userdata 路径常量（`ravenmind`/`op_count`/`impulsed`）。
- `api/addldata/`（package-info 写明设计）：**AD = Additional Data**，即"Forge capability / Fabric cardinal component 的统一抽象"，`ADFooBar` 接口由 `CCFooBar`（Fabric）或私有 record（Forge）实现。`ADIotaHolder`（read/write + `writeable()`）、`ADMediaHolder`（`getMedia/setMedia` + `withdrawMedia/insertMedia` 的负值=全量/补满语义 + `getConsumptionPriority`，优先级常量 800~4000 注在文件尾）、`ADHexHolder`、`ADPigment`（含 `morphBetweenColors` 静态工具）、`ADVariantItem`，以及把实体委托给物品的 `ItemDelegatingEntityIotaHolder`（ToItemEntity/ToItemFrame/ToWallScroll）。
- 挂载方式对 addon 极友好：`api/item/{IotaHolderItem, MediaHolderItem, HexHolderItem, PigmentItem, VariantItem}.java` 是普通接口，注释说明"注册表会被扫描，凡是实现该接口的物品都会自动挂上对应 cap/CC"——实际扫描见 `fabric/cc/HexCardinalComponents.java:91/97/114` 的 `registry.register(i -> i instanceof IotaHolderItem, ...)`。
- `api/mod/`：`HexTags`（Items/Blocks/Entities/**Actions** 四组；`Actions.create` 用 `IXplatAbstractions.INSTANCE.getActionRegistry().key()` 建 TagKey，:99）、`HexConfig`（三组接口 Common/Client/Server + `setXxx` 静态注入，平台各写实现）、`HexStatistics`（自建 `CUSTOM_STAT` 并注册 formatter）、`HexApiMessages.java` 整个文件被注释掉（作者原话 "Don't understand what this does"）。
- `api/utils/`：`HexUtils.kt`（`isOfTag(registry,key,tag)` 提供者判标签，:306-315）、`MediaHelper.kt`（`extractMedia` 等面向 addon 的媒质抽放）、`NBTHelper/NBTDsl`（NBT 读写 DSL）、`TreeList.java`（3431 行不可变树，函数式列表）、`MathUtils/ChunkScanning`。
- `api/` 还含 `casting/{eval,iota,iota/*,mishaps,arithmetic,circles,castables}`、`block/`、`client/`（`ClientCastingStack`、`ScryingLensOverlayRegistry`）、`player/`、`pigment/`、`advancements/`。README 原话："只使用 `at.petrak.hexcasting.api` 包里的东西（我们尽量保持稳定，但做得不太好）"。

##### 4. 多加载器抽象（`xplat/`）

`xplat/` 只有 6 个文件，是典型的"接口 + ServiceLoader + 平台实现"三层：
- `IXplatAbstractions.java`：巨型平台接口 —— 发包三通道（`sendPacketToPlayer/Near/Tracking`）、`IMessage → Packet` 转换、六个注册表 getter、AD 查找器（`findMediaHolder/findDataHolder/findHexHolder/findVariantHolder`）、玩家状态（sentinel/flight/altiora/pigment/staffcast image/patterns）、`createBlockEntityType`、`isCorrectTierForDrops`、`isBreakingAllowed/isPlacingAllowed`。`INSTANCE = find()` 用 `ServiceLoader.load(...)` 并要求**恰好一个**实现，否则抛异常（这是"平台实现唯一性"的硬校验）。
- 实现注入靠 ServiceLoader 文本文件（`git show HEAD:` 可见）：`Fabric/src/main/resources/META-INF/services/at.petrak.hexcasting.xplat.IXplatAbstractions → at.petrak.hexcasting.fabric.xplat.FabricXplatImpl`；Forge 同理；`Common/src/test/resources/...` 指向 `DummyXplatAbstractions.kt`（让 Common 的 3 个单测能跑，`DummyXplatAbstractions` 里还自己 `Bootstrap.bootStrap()`）。
- `IClientXplatAbstractions.java` 独立一份（渲染层/物品属性/客户端施法栈），同样 ServiceLoader；`IXplatTags` 抽公共 tag（`c:amethyst_dusts` 等）；`Platform.java` 只有 `FORGE, FABRIC` 两值，用于少量 `if (platform == FABRIC)` 分支（如 `HexActionTagProvider` 的路径 hack）；`IForgeLikeBlock` 给 Forge 风格的方块行为留口。
- **网络统一**：Common 定义 `common/msgs/IMessage.java`（`serialize(FriendlyByteBuf)` + `getFabricId()`，注释解释"Fabric 必须声明 ID，Forge 自动递增"），11 个消息类；Fabric `FabricPacketHandler` 用 `ServerPlayNetworking/ClientPlayNetworking.registerGlobalReceiver`，Forge `ForgePacketHandler` 用 `SimpleChannel.registerMessage(idx++, ...)`，两边各自把同名的 `handle` 接上，业务代码只依赖 `IXplatAbstractions.sendPacket*`。
- **注册表实现差异**：Fabric `fabric/xplat/FabricXplatImpl.java:413-450` 用 `FabricRegistryBuilder.from(new MappedRegistry<>(...)).buildAndRegister()`（iota_type / continuation_type / eval_sound 用 `DefaultedMappedRegistry` 带默认项）；Forge `forge/xplat/ForgeXplatImpl.java:466-490` 通过 **mixin 访问器** `forge/mixin/ForgeAccessorBuiltInRegistries.java` 的 `@Invoker("registerSimple"/"registerDefaulted")` 把注册表塞进 `BuiltInRegistries`；两边都用 `Suppliers.memoize` 懒建。
- 玩家附加数据：Fabric 用 Cardinal Components（`fabric/cc/CC*`+`adimpl/CC*` 共 16 个类），Forge 用 Capability（`forge/cap/Cap*`+`adimpl/Cap*` 共 10 个类）；Forge 侧还要额外注册 4 个 ack 包（`MsgBrainsweepAck` 等）来同步 cap，Fabric 侧靠 CC 自身同步——**这正是 AD 层存在的理由**。

##### 5. 数据与资源驱动

`Common/src/main/resources/data/hexcasting/` 本身很小（recipes 1、loot_tables 3、patchouli_books 1、tags 2、worldgen 3、advancements 1、item_modifiers 1）：`recipes/patchi_book.json`、`loot_tables/{grant_patchi_book,random_cypher,random_scroll}.json`、`patchouli_books/thehexbook/book.json`（只有书名/纹理/macros，`"i18n": true`）、`tags/entity_types/{cannot_teleport,sticky_teleporters}.json`。真正的数据几乎全在**生成目录**：Fabric/Forge 各自 `src/generated/resources/data/hexcasting/**`（如 `recipes/brainsweep/*.json`、`recipes/pride_colorizer_*.json`、`tags/hexcasting/action/*.json`、`advancements/recipes/**`），由 `datagen/` 生成：`HexAdvancements`、`HexLootTables`、`recipe/HexplatRecipes`（含 Create/FarmersDelight 兼容配方）、`tag/HexActionTagProvider`；平台侧 `FabricHexDataGenerators` / `ForgeHexDataGenerators`+`ForgeHexLootModGen`，根 `build.gradle` 的 `runAllDatagen` 一次跑三份。
值得学的两处"条件化数据"：`IXplatConditionsBuilder` 抽象出 Fabric resource condition 与 Forge `mod_loaded` 两套；`HexActionTagProvider.ersatzActionTag` 专门绕开 "1.20.1 vanilla/Fabric 把自定义注册表标签写到 `tags/action` 而不是 `tags/hexcasting/action`" 的 bug —— 所以磁盘上 Fabric 是 `tags/action/*.json`、Forge 是 `tags/hexcasting/action/*.json`。
**不是数据驱动而是代码注册**（并说明原因）：action、special handler、iota 类型、算符、续延帧、音效——它们必须与 Java/Kotlin 行为类一一绑定，注册表里存的是对象而不是可序列化原型，因此无法用 json 描述（`Action.kt` 注释明说"客户端只为了满足 MC 注册表系统才持有 Action 实例，但永远不用它"）；物品/方块/药水/属性等同样是用 `BiConsumer<T, ResourceLocation>` 模式在 init 里灌进 vanilla 注册表；loot 在 Forge 走 `ForgeHexLootMods` 的 LootModifier（json 生成于 `data/hexcasting/loot_modifiers/`），在 Fabric 只能靠 `LootTableEvents.MODIFY` + `FabricHexLootModJankery` 代码改写。**patchouli 书页则是数据驱动**：`assets/hexcasting/patchouli_books/thehexbook/en_us/{categories,entries,templates}` 共 82 个 entry、195 个 `op_id` 页面，页面只写 `{"type":"hexcasting:pattern","op_id":"hexcasting:circle/impetus_pos",...}`，运行时由 `interop/patchouli/LookupPatternComponent` 从 action 注册表**反查原型图案**，并按 `PER_WORLD_PATTERN` 标签决定要不要显示笔画顺序（`LookupPatternComponent.java:30-34`）。

##### 6. hexdoc 文档管线（"从注册表自动生成网页魔法书"的范例）

配置：`doc/hexdoc.toml` + 根 `pyproject.toml`。
- `pyproject.toml` 把门槛降到最低：`[project.entry-points.hexdoc] hexcasting = "hexdoc_hexcasting._hooks:HexcastingPlugin"`，靠 `hatch-gradle-version` 从 `gradle.properties` 取 mod 版本拼 Python 版本；`doc/src/hexdoc_hexcasting` 是真正的插件包，`_export` 子包在构建时生成。
- `doc/hexdoc.toml` 声明 modid、书 `hexcasting:thehexbook`、`resource_dirs`（`{_common.src}/main/resources`、`{_fabric.src}/generated/resources`… 以及 `{ modid="minecraft" }`、`{ modid="hexdoc" }` 两个外部 jar），并允许 addon 通过发布 `export_dir` 里的元数据复用同一套渲染。
- 数据流（`doc/src/hexdoc_hexcasting/_hooks.py` + `metadata.py` + `book/page/pages.py`）：
  1. hexdoc 起插件 → `hexdoc_update_context` 钩子构造 `HexContext(...).load_patterns(loader)`；
  2. `load_patterns`（metadata.py）在 1.20+ 走 `_add_patterns_0_11`：先按 `registry="action"` 载入 `hexcasting:per_world_pattern` 标签，再逐条执行 `pattern_stubs`；
  3. stub 类型 `regex`：hexdoc.toml 的 `_pattern_regex` 直接**正则抓 `HexActions.java` 源码**，抽出 `name / signature / startdir`（`[aqweds]+` 小写签名 + `HexDir.\w+`），`RegexPatternStubProps._iter_patterns` 逐条产出 `PatternInfo(id, startdir, signature, is_per_world)`；因为注册表是代码注册、没有 json，抓源码是唯一现实解；
  4. 去重（id 重复直接报错，签名重复可按 `allow_duplicates` 降级为 warn）后**导出** `hexcasting.patterns.hexdoc.json` 到 `export_dir`，再 `load_metadata(name_pattern="{modid}.patterns")` 合并其它 mod 的同类文件 —— 这就是"注册数据"跨 mod 共享的接口；
  5. 书本体照常按 patchouli 解析：页面类型 `hexcasting:pattern` 落到 `LookupPatternPage`，用 `op_id` 去 `patterns` 表查，查不到就抛 "Unknown pattern ID (check your pattern stubs in hexdoc.toml)"；`manual_pattern`/`manual_pattern_nosig` 则直接内联 `RawPatternInfo`；`crafting_multi`、`brainsweep`（`book/recipes.py` 里 `BrainsweepRecipe_0_11/0_10` 用 `IsVersion` 做版本分派）各自对应自定义 Jinja 模板；
  6. 模板 `_templates/pages/hexcasting/pattern.html.jinja` → `manual_pattern.html.jinja` 把每条 pattern 渲染成 `<canvas data-string="{{pattern.signature}}" data-start="{{pattern.startdir.name.lower()}}" data-per-world="{{pattern.is_per_world}}">`；`hexcasting.js.jinja` 里的 `startAngle/offsetAngle` 用小写方向名和小写角度字母画六边形，`data-per-world` 用于提示"此图案每世界随机"；
  7. 另有 `hexdoc_validate_format_tree` 钩子做**内容校验**：正文里 `$(action)` 宏后面必须跟链接（除白名单 `FAKE_ACTIONS`），把"文档里每个 action 都要可跳转"变成构建期错误。

##### 7. 值得学的 6 条 + 2 个坑

**值得学**
1. **AD 抽象**（`api/addldata/package-info.java`）：把 Forge capability 与 Fabric cardinal component 统一成 `AD*` 接口，addon 只实现普通接口（`IotaHolderItem` 等），平台侧"扫注册表自动挂载"（`HexCardinalComponents.java:91`），扩展者完全不必写 loader 代码。
2. **注册表 + 预处理缓存分离**：`Registry<ActionRegistryEntry>` 是唯一真源，`PatternRegistryManifest` 只做 `角度表 → key` 的 O(1) 缓存（`PatternRegistryManifest.java:26-65`），并且明确把"每世界图案"分流到 `SavedData`，让世界种子只影响一小撮数据。
3. **sealed 状态机返回值**：`PatternShapeMatch{Nothing,Normal,PerWorld,Special}` 用类型携带"命中什么/确定性"，调用方 `PatternIota.java:99-121` 一次 `instanceof` 链就消化掉全部语义，比返回 null+枚举清晰得多。
4. **特殊匹配优先级写进注释**：`matchPattern` 明确 normal→per-world→special 且注明了历史事故（phial 数字字面量），把"为什么是这个顺序"留在代码里。
5. **文档管线读"注册/数据"而不是手写**：hexdoc 用 `pattern_stubs` + `per_world_pattern` 标签生成 `hexcasting.patterns.hexdoc.json` 并允许 addon 复用（`_hooks.py` 的 export + `load_metadata`），再配 Jinja 模板把同一份数据渲染成交互图（`manual_pattern.html.jinja` 的 `data-per-world`）。文档与代码同时更新，不会腐化。
6. **平台差异做成可测的边界**：`IXplatAbstractions` 的 `ServiceLoader` "恰好一个实现"断言 + `Common/src/test/resources` 里的 `DummyXplatAbstractions`，让最核心的 Common 代码能在无 MC 环境跑单测（`Common/src/test/java/EulerPathFinderTest.kt` 等）。

**坑**
1. **注册表何时处理没定数**：`processRegistry` 在客户端/服务端启动时都可能跑（`FabricHexInitializer.kt:92-95`、`ForgeHexInitializer.java:234`、客户端 `FabricHexClientInitializer.kt:50` / `ForgeHexClientInitializer.java:57`），作者自己留了 TODO（`PatternRegistryManifest.java:36-39`），历史上导致"同形状签名互相覆盖只 warn"（:53）与重复注册日志刷屏。并且它只按**形状**而非完整图案索引，两个不同起笔顺序的同形状图案会冲突；`createFromScratch` 的 TODO 也承认 Great Spell 与普通图案同形时没有重叠保护。
2. **平台 hack 会泄漏到数据目录**：`HexActionTagProvider.ersatzActionTag` 为绕 vanilla/Fabric 的标签路径 bug 造了个假注册表 key（`foobar:hexcasting/tags/action`），于是 Fabric 产物是 `data/hexcasting/tags/action/*.json`、Forge 是 `data/hexcasting/tags/hexcasting/action/*.json`；同一份代码产出两套路径，写 addon 或写文档工具时极易踩空（hexdoc 的 `Tag.load(registry="action", ...)` 也得配合这个现实）。另外 `HexPattern.CODEC`（`HexPattern.kt:134-139`）两个字段名和内容是对调的（`start_dir` 存角度串、`angles` 存方向名），虽能 round-trip，但任何按字面理解它的外部工具都会读错。

#### 4.3 客户端渲染 / 特效 / GUI / 同步

#### C. 客户端渲染 / 特效 / 音效 / GUI / 同步

分析对象：Hex Casting（HexMod）main 分支，MC 1.20.1，Kotlin + Java 混排。所有路径相对仓库根，行号以当前 clone 为准。

##### 0. 全局渲染入口

客户端渲染挂点很少，两个 loader 各一处：Fabric 在 `WorldRenderEvents.AFTER_TRANSLUCENT` 调 `HexAdditionalRenderers.overlayLevel`，另注册 `HudRenderCallback`（`Fabric/src/main/java/at/petrak/hexcasting/fabric/FabricHexClientInitializer.kt:37-40`）；Forge 对应 `RenderLevelStageEvent.Stage.AFTER_PARTICLES` 与 `RenderGuiEvent.Post`（`Forge/src/main/java/at/petrak/hexcasting/forge/ForgeHexClientInitializer.java:62-70`）。两者都进 `HexAdditionalRenderers.overlayLevel/overlayGui`（`Common/.../client/render/HexAdditionalRenderers.java:36-48`），只负责"哨兵标记 + 透镜覆盖层"。

真正的大头在世界渲染阶段内部：`MixinPlayerRenderer` 注入 `PlayerRenderer.render` 头部（`Common/.../mixin/client/MixinPlayerRenderer.java:14-20`）画施法螺旋；方块实体图案走 BE 渲染器；GUI 走自己的 `Screen`。

##### 1. 世界内 Pattern 渲染

核心是四件套：`PatternRenderer`（决策）、`PatternSettings`（形状/尺寸）、`PatternColors`（颜色）、`HexPatternPoints`（几何缓存）。作者在 `client/render/PATTERN_RENDER_LORE.md` 里自己写了设计说明，值得先读。

**双轨渲染**：`PatternRenderer.renderPattern`（`client/render/PatternRenderer.java:42-98`）先算静态点（`:44`），若"速度为 0 且内外色各自纯色"（`:49-53`）就尝试纹理路径，失败或条件不满足才退回动态几何路径（`:54-78`）。纹理路径就是画两个 quad（`:103-143`），动态路径则用 `RenderLib.drawLineSeq` 按段生成三角带。

**线条几何**（`client/render/RenderLib.kt`）：`drawLineSeq(:62-198)` 把每段折线当成"六边形"用普通三角形拼出 `TRIANGLE_FAN` 语义（`:105-144`，注释直接点名 alwinfy 的 TRIANGLE_FAN 实现），拐角处按夹角拆成若干扇形补洞（`:146-180`，`CAP_THETA = 180/10`，`:41`），两端补半圆帽（`:184-197`）。抖动（zappy）由 `makeZappy(:249-334)` 用 SimplexNoise（`:33-38`）按 `i, j`（段号/子段号）+ `zSeed`（游戏时间）采样扰动，参数化出 hops/variance/speed/flowIrregular/readabilityOffset/lastSegmentLenProportion；`STATIC/READABLE/WOBBLY` 三档预设（`client/render/PatternSettings.java:69-71`），其中 READABLE 会把最后一个线段截短、拐角内缩，专门提高"读法"可读性。重复点用 `findDupIndices(:336-349)` 识别，配合 daisyChain 让自交图案在交叉处断开，视觉上像真的手写线。

**发光怎么来的**：没有后处理 bloom。一是内外双层描边——外层粗、内层细且用 `screenCol()` 把 RGB 各 `(n+255)/2` 提亮（`:377-386`），叠出"芯亮边暗"的发光错觉；二是 `PatternColors.glowyStroke`（`client/render/PatternColors.java:37-39`）把同色提亮当内层；三是像素级 Z 分层：outer 0.0005f / inner 0.001f / 圆点 0.0011f（`PatternRenderer.java:100-101,82`）避免 z-fighting。混合模式两套：GUI 用 `POSITION_COLOR_TEX` + `SRC_ALPHA/ONE_MINUS_SRC_ALPHA`（`client/render/VCDrawHelper.kt:49-70`）；世界内用 `NEW_ENTITY` + `RenderType.entityTranslucentCull`，并手动开光照层、`blendFuncSeparate`、必要时切 `translucentTarget`（`:72-141`）——即把图案当"会受光照的实体"画，而不是自我发光面片。

**纹理化加速**：`PatternTextureManager`（`client/render/PatternTextureManager.java`）在后台线程池（`:26`）用 AWT `Line2D.ptSegDist` 做距离场抗锯齿光栅化（`:99-114`）生成 inner/outer 两张 `DynamicTexture`（`:62-76`），主线程注册（`:50-58`）；缓存键是 `settingsName + patternName + seed + resPerUnit`（`:31`，`PatternSettings.getCacheKey`）。拿不到就返回空 → 上层退回动态路径，所以是"渐进式升级质感"。`repaint()`（`:122-126`）在资源重载时清缓存。

**摆位**：`HexPatternPoints.java:36-104` 负责缩放、对齐（`AxisAlignment` 六档，`PatternSettings.java:79-96`）、padding 与描边宽补偿，静态点全局缓存（`:128-133`）。世界的四种场景预设集中在 `client/render/WorldlyPatternRenderHelpers.java:27-49`（scroll / scroll_readable / worldly / wobbly_world），另有卷轴（`:51-61`）、石板（`:68-104`，通电时换 WOBBLY 抖动 + 紫色发光色，可用 config `staticActiveSlates` 关掉抖动）、书架（`:106-125`）三个专门函数；通用 `renderPattern(:130-154)` 里用 `noNormalInv`（scale(1,1,-1)）修法线（`:146-148`）。

**玩家头顶的螺旋图案**：`api/client/ClientRenderHelper.kt:23-85`，每个已执行 pattern 不同半径/转速/浮动（`:33-37`），颜色取玩家 pigment（`:70-73`），寿命末段线性淡出（`:75-78`），内层再次用 `screenCol` 提亮。

**"法阵"**：没有专门的法阵渲染器。法术圈 = 一圈 Slate 方块（`client/render/be/BlockEntitySlateRenderer.java:16-24`）+ akashic_connector 方块靠 OptiFine CTM 拼接（`Common/src/main/resources/assets/hexcasting/optifine/ctm/akashic_ligature/akashic_ligature.properties`，`tiles=0-46`）。玩家自己的哨兵标记是另一路：`HexAdditionalRenderers.renderSentinel(:50-131)` 用 `LINES` + `lineWidth(5f)` 手搓二十面体线框，颜色随 pigment、位置随相机。

##### 2. 粒子与施法反馈

`api/casting/ParticleSpray.kt:13-29`：data class `ParticleSpray(pos, vel, fuzziness, spread, count)`，两个工厂 `burst`（球面爆散）/`cloud`（云团），`sprayParticles` 只是把包发给 128 格内玩家（`:26-28`）。全库 98 处引用，凡"破坏/爆炸/位移/传送/点燃"的 action 都会 `Result(..., particles = listOf(ParticleSpray.burst(...)))`（如 `common/casting/actions/spells/OpBlink.kt:59-60`、`OpExplode.kt:46`）。

粒子类型只有一个：`ConjureParticleOptions`（`common/particles/ConjureParticleOptions.java:14-65`，带 `color`，有 codec/命令/网络三套序列化），注册在 `common/lib/HexParticles.java:27-46`；客户端 `client/particles/ConjureParticle.java:23-124` 是 `TextureSheetParticle`，自定义 `ParticleRenderType`（`:92-121`）用 `SRC_ALPHA/ONE` 加色混合、`depthMask(false)`、临时关纹理过滤（`setFilterSave`）做糊光；alpha 随寿命线性衰减再乘 0.3（`:60-62`），`quadSize` 每 tick ×0.96 收缩。整套思路抄 Botania 的 FXWisp（注释里的链接）。

**反馈链路统一在 `OperatorSideEffect`**（`api/casting/eval/sideeffects/OperatorSideEffect.kt:49-71`）：`Particles` 用当前 pigment 喷；`DoMishap` 则喷两次——一次主色、一次强制红色染料（`:61-67`），这就是"施法失败时总有一圈红光"的来源。成功反馈：每画对一个 pattern，服务端就在玩家上方喷一次（`api/casting/eval/env/StaffCastEnv.java:133-138`，注释说明是为了避免饰品刷屏）；法术圈走 `ICircleComponent.java:125-131`，成功 30 粒/失败 100 粒红色，还按 `semitoneFromScale` 给音高（`:140-145`）。个别玩法会硬换色，如飞行失控时叠红黑双喷（`common/casting/actions/spells/OpFlight.kt:113-115`）。

另外两处世界粒子：召唤方块在客户端 tick 里持续冒粒子（`common/blocks/BlockConjured.java:44-58` + `common/blocks/entity/BlockEntityConjured.java`，渲染形状 `INVISIBLE`，见 `BlockConjured.java:105-106`）；紫水晶芽的粒子靠 mixin 注入 `ClientLevel.doAnimateTick`（`mixin/client/MixinClientLevel.java`）。

##### 3. GUI：法术书 / 画板

GUI 只有两个类：`client/gui/GuiSpellcasting.kt` 与 `client/gui/PatternTooltipComponent.java`。**是原版 `Screen` 全自绘，没有容器菜单**（`GuiSpellcasting.kt:42-48`），`isPauseScreen` 返回 false（`:527`）。打开路径：法杖右键 → 服务端 `ItemStaff.use` 打包当前 VM 的堆栈描述发 `MsgOpenSpellGuiS2C`（`common/items/ItemStaff.java:43-51`）→ 客户端 `setScreen`（`common/msgs/MsgOpenSpellGuiS2C.java:58-66`）。也就是说"法术书页"其实只是物品 NBT（`ItemSpellbook` 的 `page_idx/pages/page_names/sealed_pages`），翻页用滚轮（`client/ShiftScrollListener.java:19-59` + `client/Keybinds.java:21-56`，键位+滚轮双通道）。

**鼠标轨迹 → pattern**：坐标是六边形轴向系，`coordToPx/pxToCoord` 在 `api/utils/HexUtils.kt:86-105`（√3 展开 + 最近邻取整），屏幕像素↔格子；`hexSize()` 随屏幕面积与 `GRID_ZOOM` 属性自适应（`:530-537`）。输入用三态状态机 `PatternDrawState`（`:547-556`）：`BetweenPatterns / JustStarted / Drawing`。

关键在 `drawMove(:204-275)`：把鼠标位置换算到格子，与锚点距离超过 `hexSize²·2·clamp(gridSnapThreshold,0.5,1)` 才认一次输入（`:216-218`）；`atan2` 取整到 6 个方向（`:219-223`）；随后把锚点吸附到"理论正确位置"以容忍手抖（`:226-227`）；若目标格已被 `usedSpots` 占用就不动（`:228`）；方向与上一段完全相反时做回退删段（`:238-246`）；否则 `wipPattern.tryAppendDir`（`:248`），成功才响 `ADD_TO_PATTERN` 并带 ±5% 随机音高（`:257-270`）。起笔音 `START_PATTERN`（`:170-181`）；`clickingTogglesDrawing` 配置可切换"按住拖拽"与"点击切换"两种操作（`:150-161,191-202`）。

**提交**：`drawEnd(:286-312)` 把 wipPattern 塞进 `patterns` 与 `usedSpots`，然后发 `MsgNewSpellPatternC2S(hand, pattern, patterns)`（`:301-307`）——注意发的是**整份已画图案列表**，不是单条。

**绘制**：`render(:366-524)` 先按光标位置画半径 3 的提示点阵，亮度/大小随距离插值且跳过已占用格（`:380-408`）；已画图案按 `ResolvedPatternType` 上色并决定抖动强度（成功 0.2、失败 0.9，`:410-427`，颜色定义在 `api/casting/eval/ResolvedPatternType.kt:5-11`）；正在画的图案用固定蓝/粉双色（`:448-457`）；左侧 70% 宽度画栈描述、右侧 15% 画 ravenmind（呼吸透明度 `:499-521`），常数在 `:558-560`。**注意 GUI 走的是 legacy 动态路径 `drawPatternFromPoints`（`RenderLib.kt:211-242`），没有用 `PatternRenderer`**，类头还留着 `TODO winfy: fix this class to use ExecutionClientView`（`:41`）。物品 tooltip 里的图案则用新渲染器（`PatternTooltipComponent.java:49-68`）。

##### 4. 音效

`common/lib/HexSounds.java:12-61`：全部 `SoundEvent.createVariableRangeEvent` 动态创建，21 个事件（起笔/加段/氛围/施法四档/失败/法阵/卷轴/Impetus/飞行…，`:21-50`）。

触发点分三类：
- **GUI 内**：起笔/加段音走 `SimpleSoundInstance` 且坐标借用氛围音实例的坐标（`GuiSpellcasting.kt:170-181,258-269`）——因为 GUI 时玩家没动，声音贴在"眼球前方"更自然。
- **氛围音**：`client/sound/GridSoundInstance.kt:34-51`，`AbstractTickableSoundInstance` 循环，每 tick 把音源挪到玩家视线前方，再按鼠标归一化坐标在垂直于视线的两个平面上做 ±0.5 格声像平移（`PAN_SCALE`），屏幕一关就 `stop()`（`:37-38`）。
- **服务端权威**：`HexEvalSounds.java:17-32` 把 `EvalSound` 映射到具体事件（NORMAL/SPELL/HERMES/THOTH/MISHAP），`StaffCastEnv.postExecution(:36-47)` 单次播放并限制 100 次；法阵音带音高（`ICircleComponent.java:135-145`）。客户端本地也播（法杖重置 `ItemStaff.java:33-34`）。

未确认：仓库内没有 `sounds.json` 与 ogg（`Common/src/main/resources/assets/hexcasting/` 只有 models/optifine/particles/patchouli，共 103 个文件），二进制音频资源不在本 clone。

##### 5. 物品 / 方块 / 实体渲染

**物品完全没有 BEWLR/自定义 ItemRenderer**，全靠 model predicate + ItemColor。`client/RegisterClientStuff.java:57-146` 注册了一串 item property：`overlay_layer`（空/填充/封印三态）、`variant`、`has_patterns`、`ancient`、`funny_level`、`gaslighting`、电池 media 等，再由 datagen 展开成 24 个 spellbook 变体模型（`Common/src/generated/resources/assets/hexcasting/models/item/spellbook.json` 的 `overrides`）。染色只是 `ItemColor` 的 `idx==1` 层（`RegisterClientStuff.java:154-189`，`IotaType.getColor`）。法杖彩蛋皮肤按物品名匹配 old/cherry（`:222-237`）；gaslighting 则由 `client/render/GaslightingTracker.java:15-27` 驱动（40 tick 冷却后每帧自增），实现"盯着看就会变"的诡异效果，配合 BE 渲染器换模型。

方块实体渲染器只注册三个（`RegisterClientStuff.java:239-251`）：石板、书架、quenched allay。前者分别转调 `WorldlyPatternRenderHelpers.renderPatternForSlate/ForAkashicBookshelf`（`client/render/be/BlockEntitySlateRenderer.java:16-24`、`BlockEntityAkashicBookshelfRenderer.java:16-24`）；quenched allay 用 `BlockRenderDispatcher` 手绘同一方块的随机变体并带 Fabric 专属视锥检查（`client/render/be/BlockEntityQuenchedAllayRenderer.java:27-49`）。

实体只有一个：`WallScrollRenderer`（`client/entity/WallScrollRenderer.java:22-135`），手搓 6 面 cuboid + `entityCutout`（`:66-94`，注释"我按 PaintingRenderer 的路子来"），再叠图案（`:98-99`）；贴图按卷轴尺寸/远古与否六选一（`:107-125`）。护甲：`AltioraLayer` 借 `ElytraModel` 当滑翔披风（`client/model/AltioraLayer.java:27-51`），长袍模型是 Blockbench 生成的 `LayerDefinition`（`client/model/HexRobesModels.java`），经 `HexModelLayers.java:19-34` 注册。

`client/render/shader/HexRenderTypes.java:27-43` 有灰度 RenderType + `assets/minecraft/shaders/core/hexcasting__grayscale.json`，`FakeBufferSource.java` 也在——但全库 grep 无调用者，是死代码（未确认是否有 Forge 侧反射用途）。`client/PatternShapeMatcher.java` 是空类。

##### 6. 同步与预测

**数据流**：GUI 画完 → `MsgNewSpellPatternC2S`（`common/msgs/MsgNewSpellPatternC2S.java:22-57`）→ 服务端 `StaffCastEnv.handleNewPatternOnServer`（`api/casting/eval/env/StaffCastEnv.java:80-139`）→ 服务端 VM 执行（`:108`）→ 回 `MsgNewSpellPatternS2C`，载荷是 `ExecutionClientView(isStackClear, resolutionType, stackDescs, ravenmind)`（`api/casting/eval/ExecutionClientView.kt:8-16`）→ GUI `recvServerUpdate(:67-86)` 改图案颜色 + 重算栈显示。**服务端是唯一权威，客户端不做本地执行预测**——只有显示层乐观更新：`EntityWallScroll.interactAt` 在客户端先自己 `recalculateDisplay()` 抢在包前面（`common/entities/EntityWallScroll.java:114-133`）。

**螺旋图案同步**：`MsgNewSpiralPatternsS2C` 由服务端发了两次——给自己一次 + 追踪包给周围（`StaffCastEnv.java:124-131`），客户端入 `ClientCastingStack`（`api/client/ClientCastingStack.kt:13-60`，按 hashCode 去重、上限 100 条、`slowClear` 收缩寿命）；清空走 `MsgClearSpiralPatternsS2C`（`:34-45`）。渲染所需的时间基准是客户端自己的 `ClientTickCounter`（`client/ClientTickCounter.java:6-22`，渲染帧头/客户端 tick 尾各更一次）。

**防伪造校验**：唯一的显式校验在 `StaffCastEnv.java:82-100`——把已画图案的点集汇总，检查新图案的点是否与之重叠，重叠即 `cheatedPatternOverlap = true` 并**直接 return**（`:93-100`）。此外就是常规的服务端权威：`executeMediaEnvironment(:62-68)` 按模拟结果扣 media、Mishap 在服务端抛出、快捷栏/方块交互也在服务端判定（`CastingEnvironment` 那一套）。也就是说：**pattern 本身的内容、形状合法性、发送频率都不校验，只校验"别和已画的图案空间重叠"**。客户端侧另有一份 pattern 注册表（`PatternRegistryManifest.processRegistry` 在客户端 join 时跑，`Fabric/src/main/java/at/petrak/hexcasting/fabric/FabricHexClientInitializer.kt:48-53`），但 `PatternShapeMatch.PerWorld.certain` 在客户端恒为 false（`api/casting/PatternShapeMatch.java:33-37`），只用于 tooltip 显示世界专属图案名。

##### 7. Pigment（颜料）

不是数据驱动 JSON，而是"物品 + 接口 + 快照"三件套：
- `PigmentItem.provideColor(stack, owner)`（`api/item/PigmentItem.java`）由物品实现，返回 `ColorProvider`。
- `FrozenPigment(item, owner)`（`api/pigment/FrozenPigment.java:18-53`）是可序列化快照（`TAG_STACK/TAG_OWNER`，`:20-21,29-48`），因为要过网络（`MsgCastParticleS2C` 就带它，`common/msgs/MsgCastParticleS2C.java:58`），也因为 Forge capability 查询慢——类注释明说"拿一次，然后反复查询"（`:12-16`）。
- `ColorProvider.getRawColor(time, position)` 是唯一需要实现的方法，`getColor()` 再套一层最低亮度保护：算相对亮度，< 0.05 就叠一个六色色轮（`api/pigment/ColorProvider.java:13-42`），避免纯黑颜料"看不见"。

真正的花样在 `ADPigment.morphBetweenColors`（`api/addldata/ADPigment.java:13-37`）：`time + gradientDir·position` 取模得到色轮下标，cubic ease 插值——**位置参与取色**，所以同一帧不同粒子颜色不同，形成流动渐变。实现类：染料（`ItemDyePigment.java:31-36` 单色）、骄傲旗（`ItemPridePigment.java:14-32` 硬编码旗面色）、UUID 颜料（`ItemUUIDPigment.java:27-71`：优先读 Paucal 贡献者数据里的 `hexcasting:colorizer` 数组，否则用 UUID 位做种子生成两色）。应用点很统一：粒子（`MsgCastParticleS2C.handle:71-106`）、施法螺旋（`ClientRenderHelper.kt:70-73`）、哨兵（`HexAdditionalRenderers.java:87-91`）、法术圈（`ICircleComponent.java:105-111`）、召唤方块（`BlockEntityConjured`）。服务端选色入口 `StaffCastEnv.getPigment(:75-78)` → `HexAPI.getColorizer`。

##### 8. 值得学的 6 条 + 3 个坑

**6 条做法**
1. **几何与外观彻底解耦 + 三级缓存**：`HexPatternPoints.getStaticPoints` 按 `(pattern名, settings名, seed)` 全局缓存（`HexPatternPoints.java:128-133`），`PatternSettings` 只管形状、`PatternColors` 只管颜色（`PatternColors.java:3-10`），因此纹理能跨颜色复用；图案几何一帧只算一次，噪声只在"需要动"时才展开。
2. **两层描边 + 提亮 = 免后处理的发光**：外层粗描边 + 内层 `screenCol()` 提亮细线，再用 0.0005/0.001/0.0011 的 Z 阶梯防 z-fight（`PatternRenderer.java:100-101,82`）。省掉 bloom pass 却能骗过眼睛，且 GUI/世界通用。
3. **顶点消费者抽象（VCDrawHelper）**：同一份 `drawLineSeq/makeZappy` 通过接口注入不同 `VertexConsumer` 装配方式——GUI 走 `POSITION_COLOR_TEX`，世界走 `NEW_ENTITY + entityTranslucentCull` 并附带光照与法线（`VCDrawHelper.kt:21-47,72-141`）。几何代码写一次，两处复用。
4. **高频静态图形"烘焙成动态纹理"**：后台线程池用 AWT `Line2D` 做抗锯齿光栅化生成 `DynamicTexture`，主线程注册（`PatternTextureManager.java:26,50-97`）；未就绪时自动降级回动态路径（`PatternRenderer.java:49-53`）。对"画面上几百个同样的静态图案"这类需求是通用解法。
5. **把声音当位置化 UI**：循环氛围音每 tick 跟随玩家视线 + 鼠标归一化坐标做声像平移（`GridSoundInstance.kt:34-51`）；法阵用 `semitone → 2^(n/12)` 算音高（`ICircleComponent.java:140-145`）。听觉反馈和鼠标/几何状态绑定，比"播个固定音效"自然得多。
6. **能力探测式的渐进渲染**：纹理路径只在"速度=0 且纯色"时启用（`PatternRenderer.java:49`），BE 渲染器区分 Fabric/Forge 的视锥行为（`BlockEntityQuenchedAllayRenderer.java:41-48`），`staticActiveSlates` 让玩家能关掉抖动。功能可用性靠"探测+降级"，而不是硬依赖。

**3 个坑**
1. **反作弊只查重叠，且失败静默**：`StaffCastEnv.java:82-100` 发现重叠就 `return`，不发任何包、不提示。客户端 GUI 会永远停在 UNRESOLVED 状态，玩家体验成"卡住/无响应"；pattern 内容与服务端可达性完全不校验。
2. **GUI 与世界用两套渲染代码**：`GuiSpellcasting` 仍走 legacy `drawPatternFromPoints`（`GuiSpellcasting.kt:412,448`；`RenderLib.kt:211-242` 里 hop=10 / variance=2.5f / 线宽 5f、2f 全是硬编码），而世界/BE 走 `PatternRenderer`。类里还留着"fix this class to use ExecutionClientView"的 TODO（`:41`）——图案观感在 GUI 与世界间注定会漂移。
3. **`VCDrawHelper.Worldly` 手改 GL 状态且假设唯一**：它自己 `turnOnLightLayer`/`blendFuncSeparate`/切 `translucentTarget`/`bindWrite` 主目标（`VCDrawHelper.kt:76-141`），字段注释承认"假设同一时刻只有一个 helper 在用"（`:74`）；`RenderSystem.setShader { lambda }` 的延迟求值 + `Tesselator.end()` 组合在别的 mod 混排渲染（或光影包接管状态机）时很容易漏状态。作者自己在 `PATTERN_RENDER_LORE.md` 里也吐槽 "We do a silly with this one lol"。

**未确认项**：贴图/音频资源不在本 clone（`Common/src/main/resources/assets/hexcasting/` 仅 103 个文件，无 `sounds.json`/`textures/`）；`HexRenderTypes`、`FakeBufferSource` 未见调用者，疑为死代码；`PatternShapeMatcher` 为空类。


---

## 5. 值得学的做法（跨三块汇总）

1. **模拟器 / 状态 / 宿主三分离**（`CastingVM` / `CastingImage` / `CastingEnvironment`）：只有"内存快照"需要序列化与同步，VM 每次重建——存档兼容性与网络开销都因此可控。任何"游戏内可编程系统"都建议照抄这个切分。
2. **错误即值（Mishap）而非异常**：29 个 Mishap 类各带自己的显示与后果，"法术失败"因此是**可设计的内容**（`MishapUnenlightened`、`MishapOthersName` 这类既解释机制又给世界观的做法值得学）。
3. **副作用列表化**：一次执行不直接改世界，而是产出 `List<OperatorSideEffect>`（扣媒介 / 放法术 / 报错），由宿主按序应用并可中断——天然可测试、可预测、可回放。
4. **用 3 种帧表达完整控制流**：链表调用栈 + `FrameEvaluate/FrameForEach/FrameFinishEval`，把 call / 删帧 / foreach 都做成"数据驱动的帧操作"，而不是给 VM 加阻塞式指令。
5. **宿主抽象（Environment）开放给 addon**：法杖 / 饰品 / 法阵 / 他人物品都只是 `CastingEnvironment` 子类（已核验 `StaffCastEnv extends PlayerBasedSpiralPatternCastEnv`，含 `handleNewPatternOnServer` 做服务端权威处理）。
6. **指令按域分包**：113 个 Op 分布在 `actions/{akashic,circles,environment,escaping,eval,lists,local,math,queryentity,raycast,spells,stack,types,selectors,rw}` 下，一个域一个目录——指令集变大后唯一活路。
7. **注册表自动生成文档**：`doc/` + `pyproject.toml`（hexdoc-hexcasting，Python ≥3.11）从 mod 注册数据生成网页魔法书，与游戏内 Patchouli 书同源；`staticdata/architecture_extensions` 等 json 是给文档管线的补充数据。
8. **客户端表现的两处巧思**：`RenderLib.makeZappy`（已核验存在于 `client/render/RenderLib.kt:249`）用噪声扰动把规整线条变得"手绘颤抖"；图案颜色/音效作为执行结果的显示信息与逻辑解耦。
9. **服务端权威 + 客户端预测**：客户端画图案只发"新图案"消息，服务端校验并执行（防伪造）；客户端渲染态 `ExecutionClientView` 只做展示。
10. **生态化**：核心小而稳（`api/` 是稳定面），扩展放 addon（同组织的 Hexal、MoreIotas 等），并有 `paucal`（延迟注册库）这类生态工具支持。

## 6. 坑与风险

- **解释器性能边界**：VM 每帧步进 + 效果列表逐条应用，遇到大列表循环（Thoth's Gambit 遍历）开销随元素线性增长；有 `MishapEvalTooMuch` 之类护栏，自研同类系统必须自己设预算。
- **服务端安全**：可编程系统等于给玩家一个 API，任何"新图案/新参数"消息都必须服务端校验（本 mod 做了，但 addon 很容易漏）。
- **存档兼容**：只有 `CastingImage` 进 NBT，意味着改 iota 序列化格式要写迁移；中间态（`FunctionalData`）不进存档算是保护。
- **Kotlin + 多加载器**：Common 513 文件跨 Fabric/Forge 两套，平台相关行为（事件、网络、渲染入口）容易漏一边。
- **文档管线是额外工程**：hexdoc 用 Python 读 mod 数据，收益是"注册表即文档"，成本是多一条要维护的构建链。

## 7. 对你（修仙 mod）的启示

1. **"可编程法术"路线可行性验证**：若你考虑"符箓 / 阵图 / 结印"这类可组合玩法，Hex 已证明**栈式 VM + 图案作指令 + 副作用列表**在 MC 里跑得通，且 113 条指令的量级个人项目可承受（按域分包、每条一个文件）。
2. **`Mishap` 模型直接可用**：把"施法失败"做成有名字、有反馈的失败类型（"心境不足""印记冲突"），比统一报"无法施法"有质感得多——也与你"数值裁定模型 / 禁止特例化"的原则一致。
3. **`makeZappy` 抖动线条**：画符/结印的线条表现可直接借鉴（噪声扰动 + 端点半透明），比纯直线更有"手绘法器"感。
4. **hexdoc 式"注册表即图鉴"**：你有 47 个类型 + 大量法器/功法需要图鉴，Hex 的做法（同一份注册数据同时产出游戏内 Patchouli 书与网页）值得抄；最省事的近似方案是把注册表导出成 json 再喂给静态站点生成器。
5. **宿主抽象**：把"谁来施法"抽象成 Environment（法杖/法器/阵法/他人），你的"御剑 / 傀儡代施"等玩法天然适配这个结构。

## 8. 复现与源码位置

- 源码（浅克隆 main，含 java/kt/json）：`Mod源码研究汇总\源码库\_参考仓库\_bulk\FallingColors__HexMod`
- 关键入口速查：VM 与帧 `Common/src/main/java/at/petrak/hexcasting/api/casting/eval/{vm,README.md}`、值类型 `api/casting/iota/`、错误 `api/casting/mishaps/`、指令 `common/casting/actions/`、客户端渲染 `client/render/`、平台抽象 `xplat/`、文档管线 `doc/` + `pyproject.toml`
- 三份精读草稿：`~/Downloads\_hex\parts\`（本报告第 4 章基于其事实并做二次核验）
