# Draconic Evolution 源码分析报告

> 展开综述《深挖__BOSS引擎调研__六样本共性模式》中一句带过的 DE 护盾/晶体/多资源条。本报告读的是 NeoForge 1.21.1 移植线（3.1.4），非旧 1.12/1.16 版。
> 路径缩写：`~/` = `src/main/java/com/brandon3055/draconicevolution/`，其余路径相对仓库根。

## 1. 基本信息

- mod_id：`draconicevolution`，作者 brandon3055（`src/main/resources/META-INF/neoforge.mods.toml` [[mods]] 段；入口常量 `~/DraconicEvolution.java:23`）。
- 目标平台：MC 1.21.1 / NeoForge 21.1.72（`gradle.properties:2-4`），mod 版本 3.1.4。加载器 NeoForge（modLoader=javafml）。
- 许可证："Don't Be a Jerk"（CoFH 式，LICENSE.md 首段；mods.toml 第 3 行 `license` 字段同）。商用/分发受限，只取思想不搬代码。
- 依赖分工（mods.toml dependencies 段 + build.gradle）：
  - **BrandonsCore**（required, ordering=AFTER）提供 TileBCore 方块实体基类与 `ManagedData`/`DataFlags` 声明式同步引擎、多方块引擎（`MultiBlockManager`/`MultiBlockDefinition`）、WorldEntity（非实体的服务端管理器）、OP 能量接口（`IOPStorage`/`IOTracker`）、BCoreNetwork。
  - **CodeChicken Lib**（required）提供 PacketCustom 低层通道、ConfigFile 配置、modular GUI 体系。
  - DE 本体的"同步"能力大半是 BrandonsCore 的 flags 系统，评估边界时不要记在 DE 头上。
- 构建：`net.neoforged.gradle.userdev` 7.0.165（build.gradle:7），单模块工程；Java toolchain 21（build.gradle:10-14）；`src/main/generated` 挂进 resources（build.gradle:27）；accesstransformer（build.gradle:31）；mixin 配置走 jar manifest `MixinConfigs`（build.gradle:174）。

## 2. 源码规模与包结构

实测：全仓 498 个 .java / 74,921 行；其中 src/main/java 486 文件 / 74,578 行。
src/api 11 文件（AE2 `IMovableTile` 与 Funky Locomotion API 的随包副本），src/test 1 文件（`OPStorageOPTest`，恰好是 BigInteger 能量存储的单测）。
速览卡片写 75,419 行，与实测有约 500 行偏差，以本处实测为准。

稀疏检出缺失：
- `src/main/resources` 下除 META-INF（mods.toml + accesstransformer.cfg）外为空；
- datagen 产物目录 `src/main/generated` 不在仓库；
- `mixins.draconicevolution.json` 只在 build.gradle:174 出现文件名而文件本身缺失——资源/生成产物类结论一律标注"未验证"。

| 包（src/main/java 下） | 文件数 | 包 | 文件数 |
|---|---|---|---|
| client（含 render/gui） | 125 | datagen | 14 |
| api（含 modules 62） | 93 | handlers | 13 |
| blocks（tileentity 32） | 79 | init | 12 |
| items | 31 | blocks/energynet | 10 |
| entity（guardian 22） | 30 | lib | 11 |
| integration | 26 | mixin / network / world / command | 6/5/5/4 |

最大源文件（实测行数）：`datagen/RecipeGenerator.java` 1847、`items/Debugger.java` 1384、`blocks/reactor/tileentity/TileReactorCore.java` 1114、`datagen/LangGenerator.java` 995、`client/gui/modular/itemconfig/PropertyContainer.java` 958、`entity/guardian/DraconicGuardianEntity.java` 937、`blocks/energynet/tileentity/TileCrystalBase.java` 691、`blocks/tileentity/TileCelestialManipulator.java` 665、`entity/projectile/DraconicArrowEntity.java` 656、`api/modules/lib/ModuleEntity.java` 639、`blocks/tileentity/TileDislocatorReceptacle.java` 629、`datagen/MultiBlockGenerator.java` 622。

## 3. 入口与注册

入口 `~/DraconicEvolution.java:28-52`，构造器即全部装配流程：

```java
public DraconicEvolution(IEventBus modBus) {
    proxy = Utils.unsafeRunForDist(() -> ClientProxy::new, () -> CommonProxy::new);
    DEConfig.load();
    DETags.init(); ItemData.init(modBus); DEContent.init(modBus); DEModules.init(modBus);
    ... DraconicNetwork.init(modBus); DEEventHandler.init(modBus);
    Utils.loadOptionalMod("computercraft", ...);
    Utils.unsafeRunWhenOn(Dist.CLIENT, () -> () -> DEClient.init(modBus));
    DraconicAPI.addModuleProvider(MODID);
}
```

- 注册方式：NeoForge `DeferredRegister` 全家桶（DEContent.java:78-89：Block/Item/BlockEntity/Menu/EntityType/RecipeType/RecipeSerializer/IngredientType），外加一个**自定义同步注册表** `modules`——`NewRegistryEvent` 时 `event.create(new RegistryBuilder<>(MODULE_KEY).sync(true))`（DEModules.java:63-67），模块可被其他 mod 通过 `DraconicAPI.addModuleProvider` 注入（DraconicEvolution.java:51）。
- 能力注册：NeoForge `RegisterCapabilitiesEvent`，每个 tile 一个静态 `register(event)` 汇总在 `init/CapabilityData.java`（如 `~/blocks/tileentity/TileEnergyCore.java:110-112`）；物品侧能力用 `DataComponentAccessor.itemStack(stack)` 把 data component 当存储后端（CapabilityData.java:38-59）。
- 事件订阅：`DEEventHandler.init`（ServerTickEvent.Post → CrystalUpdateBatcher.tickEnd，handlers/DEEventHandler.java:59）、`ModularArmorEventHandler.init`（伤害干预见 4.2）、客户端 `DEClient.java:86` 调 `CustomBossInfoHandler.init()` 挂 `CustomizeGuiOverlayEvent.BossEventProgress` 与 `ClientPlayerNetworkEvent.LoggingOut`（client/CustomBossInfoHandler.java:65-68）。

## 4. 核心系统

### 4.1 多方块（能量核心）：识别、校验、降级

- **结构定义是 JSON**：datagen 用 ASCII 图逐行搭出八层配方（`datagen/MultiBlockGenerator.java:28-80`，`key('X', ENERGY_CORE)` + `key('D', 方块tag)`）。
- 运行时 BrandonsCore `MultiBlockManager.getDefinition("draconicevolution:energy_core_N")` 按 RL 取回（TileEnergyCore.java:406-412，带 tier 感知缓存 definitionCache）。校验 = `definition.test(level, worldPosition)` 返回 `List<InvalidPart>`，空即合法（:305-315）。
- **激活即占位**：`toggleActivation` 遍历定义内所有坐标，把真实方块替换成隐形 `STRUCTURE_BLOCK` 占位，并在 `TileStructureBlock.blockName`（ManagedResource）里记住原方块 RegistryName、`controllerOffset`（ManagedPos, SAVE_NBT_SYNC_TILE）指回控制器（TileEnergyCore.java:189-210；TileStructureBlock.java:37-38）。激活前若发现残留占位块，直接反激活并 log error——防崩溃残留（TileEnergyCore.java:197-203）。
- **破坏降级**是三层自愈：
  - 占位块 `neighborChanged` → 控制器不存在或 `!isStructureValid()` → `revert()`（StructureBlock.java:61-81）；`revert` 用 `level.scheduleTick(pos, STRUCTURE, 1)` 延迟一 tick 还原 + 静态 `buildingLock` 防止激活流程自触发（StructureBlock.java:46,83-92；TileStructureBlock.java:88-89）。
  - 玩家挖方块时 `onDestroyedByPlayer` 还原原块、`popResource` 掉出原件、再调 `controller.validateStructure()` 让核心当场降级（StructureBlock.java:84-103）。
  - 稳定器（四方位×3 轴×16 格搜索）失效时 `releaseStabilizers` 解绑重找（TileEnergyCore.java:321-387）。
- **自动建造**是同一引擎的副产物：GUI 里点"build"→ `attemptAutoBuild` 造一个 `MultiBlockBuilder`（lib/MultiBlockBuilder.java:29-49，工作队列按序消耗），核心 tick 里每 tick `updateProcess()` 放一格材料，玩家离场/死亡则判定 isDead 丢弃（TileEnergyCore.java:117-124,414-423）。
- **容量按 tier 查配置表**，不是逐块聚合：`getCapacity() = DEConfig.coreCapacity[tier-1]`（TileEnergyCore.java:395-401；DEConfig.java:88，tier1=45.5M…tier7=2.14T，tier8=-1=无限）。跨端表达：能量存储 `OPStorageOP` 注册进 BrandonsCore capManager，`.saveTile().syncContainer()`——NBT 落盘、开 GUI 时按容器同步（TileEnergyCore.java:88,96），GUI 关闭外的渲染只靠 `fillPercent`（SYNC_TILE，每 tick 服务端算一次，:76,126-131）。

### 4.2 玩家护盾：不是 Attribute，是"装备组件 + 双事件介入"

- 全库无任何自定义 Attribute（grep `AttributeSupplier` 仅 guardian 的 MAX_HEALTH，DraconicGuardianEntity.java:151-153）。护盾值是模块实体 `ShieldControlEntity` 的私有 `ShieldSaveData`（8 个字段：points/boost/maxBoost/boostTime/capacity/coolDown/envDmgCoolDown/visible，ShieldControlEntity.java:436-490，Codec+StreamCodec 齐全）。
- 两个"动画量"与逻辑量分离：`shieldAnim`（展开/收起淡变，每 tick ±0.05，:161-165）和 `shieldHitIndicator`（受击闪光，每 tick -0.1 衰减，:156-158）是纯渲染状态，随实体一起序列化（CODEC 字段 :82-83），玩家身周的护盾泡泡由胸甲模型读 `getShieldState()` 走专用 `ShieldShader`（Activation/BaseColor uniform，client/DEShaders.java:51；client/model/ModularChestpieceModel.java:160）。
- **服务端每 tick 仿真**（:134-210）：容量每 10 tick 才从"全身装备聚合"刷新一次（`ModuleHelper.getCombinedEquippedData` 按 ModuleType fold，api/modules/ModuleHelper.java:78-83），带 `shieldCache` 脏失效；被动耗电 `points²*shieldPassiveModifier` 用 `passivePowerCache` 小数累积避开每 tick 取整（:181-189）；没电时 60 秒匀速放光（:192）；回充从装备 IOPStorage 抽能量（:202-209）。装两个护盾模块=冲突，容量清零（:174-178）。
- **伤害介入两个点、两条路径**：`LivingIncomingDamageEvent`（完整吸收则整事件 cancel，ModularArmorEventHandler.java:184-214 → ShieldControlEntity.java:247-262）与 `LivingDamageEvent.Pre`（护盾不够时按可吸收部分扣减、`event.setNewDamage(余量)`，ModularArmorEventHandler.java:216-240 → ShieldControlEntity.java:300-318）——注释明说第二点是为了兜"跳过 Incoming 直接进 Damage"的 mod。优先级上 undying（免死图腾）先于护盾（:203,229）。环境伤害有独立倍率表（火/岩浆/仙人掌等，ENV_SOURCES :47-57,264-289），`BYPASSES_INVULNERABILITY` 与溺水/饿死/卡墙/`/kill` 不可挡（:46,249），`/kill` 甚至被改写成合法击杀路径（ModularArmorEventHandler.java:196-201）。魔法×2、穿甲×3 的惩罚乘区（:345-349）。
- **客户端表现零自定义包**：`saveEntityToStack` 把 capacity/points/coolDown 写进三个 `networkSynchronized` 的 DataComponent（ShieldControlEntity.java:404-411；ItemData.java:100-102），原版物品堆组件同步自然送达；HUD 与护盾泡泡直接读客户端 ItemStack 上的 host。唯一相关 C2S/S2C 包是命中特效 `C_SHIELD_HIT`（DraconicNetwork.java:68）。

### 4.3 Boss 护盾条：ShieldedServerBossInfo 讲到底

- 混沌守卫的护盾值走 `SynchedEntityData` FLOAT（DraconicGuardianEntity.java:71,159-162），受击流程重写 `hurt()` → `attackEntityPartFrom`（:578-580）：先 5-tick `hitCoolDown` 同强度过滤（:532-537，防连击每帧全吃）、护盾优先扣减、封顶单发 500 护盾伤/100 本体伤、非头部部位伤害÷4（:544-558）。阶段免疫由 `phaseManager.getCurrentPhase().isInvulnerable()` 供给（:539-544）。
- `world/ShieldedServerBossInfo.java` 全文 85 行，就是一条"旁路属性条"的完整协议：
  - 服务端三个 setter 全部**脏检查**，值没变不发包；变了也只发 1 个数值（float/byte/boolean）给 players 集合（:22-53）。
  - **进世界快照**：override `addPlayer`——先手动发原版 `ClientboundBossEventPacket.createAddPacket`，再补发 op0 快照包（shield+crystals+immune 三合一）（:70-76）；`setVisible(true)` 时向全体 players 重发快照（:55-68）；`removePlayer` 发 op1 移除。op 码：0=Add 快照、1=Remove、2/3/4=单字段更新（client/CustomBossInfoHandler.java:185-201）。
  - 包体 `{UUID barId, byte op, payload}`，走 CCL PacketCustom 通道 `C_BOSS_SHIELD_INFO`=10（DraconicNetwork.java:76,218-224）。血量仍走原版 boss bar 协议，只有附加属性走旁路——与综述里 ACBossEvent/CMBossInfoServer 同族，但多了快照/移除 op。
- 客户端 `client/CustomBossInfoHandler.java`：`Map<UUID, BossShieldInfo> events` 持有旁路状态（:46）；`preDrawBossInfo` 命中 UUID 即 `setCanceled(true)` 全自绘（:70-73）——血量条用自绘 sprite（照抄原版 bars.png 182px 布局，:162-175，血量 lerp 直接复用原版传入的 `LerpingBossEvent.getProgress()` :71,87），护盾是覆盖在条上的**着色器矩形**（shieldActivation uniform 喂插值后的 shield 值，:92-103），晶体数是一坨 3D 旋转水晶模型 + "xN" 文本（:105-152）。
- **插值在客户端、用 wall-clock**：`BossShieldInfo.getShield()` 记录 setTime=`Util.getMillis()`，`(now-setTime)/100ms` 钳到 [0,1] 做 `Mth.lerp(lastPower, targetPower)`（:241-245）——100ms 固定收敛，与服务端 tick 频率彻底解耦。**进出世界重建**：客户端 `ClientPlayerNetworkEvent.LoggingOut` 清空 events map（:177-179），重进世界靠服务端 `addPlayer` 快照包重建（ShieldedServerBossInfo.java:70-76）。
- bar 的生命周期由 `GuardianFightManager`（BrandonsCore WorldEntity，服务端每局战斗一个）驱动：
  - tick 里 setVisible / 玩家扫描（20 tick 一次）/ 晶体扫描（100 tick 一次 `findAliveCrystals` → `setCrystals`）（entity/guardian/GuardianFightManager.java:81-118,256-271）。
  - `guardianUpdate` 在每次受伤后设 progress、shieldPower（归一化 `/DEConfig.guardianShield`）、immune、并按有无盾切 RED/PURPLE（:226-239；bossInfo 构造 :57-59）。
- 玩家 HUD 侧（护盾+能量+图腾三合一）是另一套：`client/render/hud/ShieldHudElement.java`，继承 BrandonsCore `AbstractHudElement`（注册见 init/DEClient.java:54-55），每客户端 tick 直接读装备 host 组件值算比例（:120-147），带配置菜单与 NBT 持久化的用户设置（:71-79,330-344）。能量条还会把背包里所有电容器的储能并入总量（energyMode 三态，:153-178）——多来源聚合同一条。

### 4.4 反应堆：仿真型玩法样本

- **状态机**：`ManagedEnum<ReactorState>` 七态（INVALID/COLD/WARMING_UP/RUNNING/STOPPING/COOLING/BEYOND_HOPE，:83,1069-1114），SAVE_NBT_SYNC_TILE 全端可见；`updateCoreLogic` 一个 switch 按态分派仿真函数（:246-287），转态条件全是显式阈值（如 STOPPING→COOLING 温度≤2000，:272-274；COOLING→COLD ≤100，:278-280）。
- **参数表达**：仿真变量全部 ManagedData 声明——燃料 reactable/converted（SAVE_BOTH_SYNC_TILE :88-94）、温度/盾充 SAVE_NBT_SYNC_TILE、而 saturation、generationRate、fieldDrain、fuelUseRate 等**仅 SYNC_CONTAINER**（:99-110）——GUI 要看的过程量只在有人开界面时同步。启动时按装料量锚定 maxShieldCharge/maxSaturation（`totalFuel * 96.45061728395062 *100/1000`，:313-329）。
- **熔毁计算**：RUNNING 中每 tick 四段联算（:331-414）——温度=饱和亏缺的三次方升功率 减 四次方热阻（作者自评注释 "This is just terrible... I cant believe i wrote this stuff" :343）；温度>8000 盾消耗按平方加速（:382）；`shieldCharge≤0 && temp>2000` → BEYOND_HOPE，立即在 6 个组件位各来一发 4 级小爆（:403-412）；BEYOND_HOPE 态 `MathHelper.approachExp` 温度逼近 1.2×MAX、盾值随机抖动、倒计时后大爆（:416-429）。结构被破坏时按温度三档惩罚：>2000 直接熔毁、≥350 minimalBoom、否则安全 INVALID（componentBroken :663-691）。
- **tick 成本与安全检查**：NBT 落盘限频 `dataManager.setMaxSaveInterval(10)`（:144）；异物侵入检测 `checkBlockIntrusions` 只在 WARMING/RUNNING/STOPPING/BEYOND_HOPE 执行且内部 `tick % 100 == 0` 才扫核心包围立方（:692-706）；failSafe 自动停机（temp<2500 且饱和≥99%）:261-264。
- **玩家可控 vs 配置分层**：世界内玩家可调的是 failSafe 开关（:118 附近 `failSafeMode` ManagedBool）与每个组件的红stone 模式/信号阈值（`TileReactorComponent.java:29-30` 的 rsMode/rsPower，TRIGGER_UPDATE 即时生效）；注能/抽取的具体调速在本检出的 injector/stabilizer 里未见独立字段（1.21 移植进行中，未验证）。全局平衡在 `DEConfig.reactorOutputMultiplier` / `reactorFuelUsageMultiplier`（:373,394）；结构常数是代码硬编码（燃料锚 :316-317）。

### 4.5 能量网（晶体网格）与大规模数值性能纪律

- 传输模型：能量晶体间按**存储百分比均衡**而非固定 FE/t——每 tick 对每条 link 算占比差、`balanceTransfer` 按 `flowRate=min(1, diff*10)` 一次到位（TileCrystalBase.java:115-173），有最小流量保底（:164-168）。无线版跨维度走 `ENetFXHandlerServerWireless`。
- **限频与批量的实锤**：每条 link 维护 `int[20]` 环形 transferRatesArrays 记录 20 tick 流量历史（:72,137-146,175-182）；流量字节（flowRates）每 10 个服务端 tick 才重算一次（:104-110）；光束视觉同步是**按玩家排队 + tickEnd 统一 flush**——服务端把每晶体的 (id, capacity, 每 link 方向字节) 塞进 `CrystalUpdateBatcher.queData`（blocks/energynet/rendering/ENetFXHandlerServer.java:57），`ServerTickEvent.Post → tickEnd()` 把同一玩家当 tick 的全部更新合成一个 varint 计数的批量包（network/CrystalUpdateBatcher.java:22-43；handlers/DEEventHandler.java:59）。
- 大数纪律：`OPStorageOP` = long 主存储 + BigInteger 溢出计数（:39-45），无限容量模式下进出跨 Long.MAX 时翻 overflow 位（:60-132）。
- 对外 `getOPStored()` 封顶 `Long.MAX_VALUE/2`，注释明说为了兼容"先查余量再推能"的发送方（:134-144）；同步侧实现 `IValueHashable`，值哈希含 overflow 与 IO 速率，脏检查后才进容器包（:241-256）。
- tier8 核心 GUI 的 fillPercent 直接钉 0 走特殊渲染（TileEnergyCore.java:126-128），可读文本按 10³ 步长拼 "x.xE{3n}×(2^64)" 记法（OPStorageOP.java:278-300）。

### 4.6 模块/装备框架（一览）

`~/api/modules/`（62 文件）是装备能力内核：自定义同步注册表 ModuleTypes + ModuleEntity（tick/Codec/StreamCodec 三件套基类，lib/ModuleEntity.java）+ ModuleHost（try-with-resources，close 即 save-dirty，api/capability/ModuleHost.java:182 附近）+ 网格槽位（gridX/Y）。数值表在 init/ModuleCfg.java、init/EquipCfg.java 走配置文件。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **自定义包**：一个 CCL PacketCustom 通道（DraconicNetwork.java:42-47，optional + versioned），14 个 C2S + 12 个 S2C opcode（:51-78），全部 int 操作码 + 手写序列化（MCDataInput/Output），未用 NeoForge StreamCodec payload 注册——这是 CCL 生态的包袱，勿照抄。
- **配方数据驱动**：fusion 配方有 `MapCodec` Serializer（api/crafting/FusionRecipe.java:130-146）和自定义 `StackIngredient` IngredientType（DEContent.java:89 注册 INGREDIENT_TYPES），全部 JSON datapack 可改；配方本体由 datagen 生成。
- **结构数据驱动**：多方块定义是 datagen 出的 JSON（4.1）；能量/装备**不**数据驱动——模块是代码注册表（DEModules 静态声明 + 配置数值层），能量是自有 OP 体系无 FE 兼容层（CapabilityOP 来自 BrandonsCore）。
- **配置**：CCL `ConfigFile` 手写格式（DEConfig.java:25-33），三层分卡：server 段（可同步、如 `coreCapacity` LongList，DEConfig.java:88,328-346 onSync 热改）、client 段、以及 EquipCfg/ModuleCfg 两个数值子文件（load 时挂进同一 config 树，:31-32）。
- **datagen**：有，14 个 provider（`datagen/` 目录：Recipe/Lang/MultiBlock/BlockState/BlockTag/Loot/Biome/DamageType/ItemModel×2/Curios/DynamicTextures + DataGenEventHandler 汇总），输出到 `src/main/generated`（build.gradle:44-48 的 data run）。本检出无产物。

## 6. Mixin / ASM / 接口注入

6 个 mixin（`~/mixin/`；配置 json 缺失，仅在 build.gradle:174 以 manifest 属性引用，配置内容未验证）：

- `ServerEntityMixin.java:29-76`：3 处 @Redirect `ServerEntity.sendChanges/sendPairingData`——仅对 `DraconicArrowEntity` 把原版量化 move/velocity 包换成 BrandonsCore 全精度速度包（高速箭矢同步补丁）。
- `EndIslandDensityFunctionMixin.java:19-33` / `TheEndBiomeSourceMixin.java:27+`：@Inject 终界地形密度与生物群系查询，按配置挤出混沌岛（DEConfig.chaosIslandEnabled）。
- `PlayerModelMixin.java:23-31`：setupAnim 尾部注入，法杖持握姿态覆写；`CapeLayerMixin.java:22+`：披风渲染替换取消。
- `ServerboundSetCreativeModeSlotPacketMixin.java` 整体被注释弃用。
- 另有 142 行 accesstransformer.cfg（BaseSpawner.isNearPlayer、LivingEntity.onEffectRemoved、ExperienceOrb.age 等，末影罐/刷怪笼联动用）。无核心插件 ASM。

## 7. 值得学的 5 条

1. **旁路 boss 条协议全套**（`~/world/ShieldedServerBossInfo.java:22-53,55-84`）：setter 脏检查 + addPlayer/setVisible 双路径 op0 快照 + removePlayer op1——85 行解决"附加状态怎么不重造 boss bar 还同步得准"。值得抄：这是多端一致性最小协议，快照/增量分离可以直接搬。
2. **HUD 插值用 wall-clock 100ms**（`~/client/CustomBossInfoHandler.java:234-245`）：setTime=Util.getMillis()，渲染时 clamp 到 [0,1] 做 lerp。值得抄：不依赖 tick 计数，掉帧/服务器卡顿时条依然平滑，且天然抗"事件乱序到达"。
3. **护盾作为装备 DataComponent，零包同步**（`~/api/modules/entities/ShieldControlEntity.java:404-411` + `~/init/ItemData.java:100-102`）：服务端 tick 仿真后写三个 networkSynchronized 组件，客户端 HUD/渲染直接读组件。值得抄：玩家自资源条根本不需要专用包——原版组件同步顺路带走了整条链路。
4. **占位块多方块的全生命周期**（`~/blocks/StructureBlock.java:61-106` + `~/blocks/tileentity/TileStructureBlock.java:37-39,83-106`）：隐形占位块记住原方块名与 controllerOffset，neighborChanged/控损/控制器消失三路各自 revert（scheduleTick 延迟 1 tick + buildingLock 防重入）。值得抄：比"每次破坏全量重扫结构"便宜一个数量级，且天然处理了崩溃残留。
5. **按玩家聚批量 + tickEnd flush 的特效同步**（`~/network/CrystalUpdateBatcher.java:22-43`，flush 挂点在 `~/handlers/DEEventHandler.java:59`）：每 tick 内多晶体对同一玩家的所有更新聚成一个批量包。值得抄：所有"多方块/多实体对同一观察者发同类小更新"的场景都适用这个两行模式（que + flush）。

**结论（面向本项目）**

- Colossus 护盾条，形状 1：`ShieldedServerBossInfo` 整套照搬进 Colossus 的 boss bar 层——`ServerBossEvent` 子类加脏检查 setter + op0 快照 + 客户端 UUID→状态 map + `CustomizeGuiOverlayEvent` 取消自绘；Colossus 需要的"护盾段"可用 DE 的 `getShield()` 插值 + 覆盖矩形，连 100ms 常数都可以先不动。
- Colossus 多资源条，形状 2：`ShieldHudElement` 的"每 tick 读源、算比例、纯 rect 拼条 + 可配置化菜单 + 用户设置 NBT 持久化"结构（`~/client/render/hud/ShieldHudElement.java:107-213,224-298`）适配 Colossus 的灵力/怒气/盾值多条 HUD；DE 里资源值走组件同步、Colossus 里换 SynchedEntityData 喂同一渲染函数即可。
- 求仙问道·灵力护体：抄 `ShieldControlEntity` 的"非 Attribute 介入层"——护体值放角色数据而非原版属性，双事件介入（Incoming 全挡 + Damage.Pre 部分吸收）保证与任何法术伤害 mod 兼容（`~/api/modules/entities/ShieldControlEntity.java:247-318`），被动耗电用 `passivePowerCache` 小数累积（:181-189）避免每 tick 取整误差；环境伤害表（:47-57）适合映射"雷劫/心火不被护体所挡"的设定。
- 求仙问道·大型法阵：DE 多方块三件套——datagen ASCII 图→JSON 定义（`~/datagen/MultiBlockGenerator.java:28-80`）、占位块降级自愈（第 7.4 条）、`MultiBlockBuilder` 渐进自动建造（`~/lib/MultiBlockBuilder.java:29-49` + TileEnergyCore.java:414-423）——直接支撑"法阵逐步点亮/被破坏局部塌缩"的玩法。
- **做坏的一处**：`~/blocks/reactor/tileentity/TileReactorCore.java:386-387` `fieldInputRate.set(fieldDrain.get() / fieldNegPercent)`——`shieldCharge` 达到 `maxShieldCharge` 时 `fieldNegPercent=0`，除零产生 Inf/NaN 并写进一个 SYNC_CONTAINER 的 ManagedDouble；且该字段纯供 GUI 显示，一处显示量可为炸。另外 `tick()` 开头 156-181 行整段注释掉的调试仿真残留进主线，说明 1.21 移植的反应堆尚在半成品状态——数值模型可参考，工程完成度别参考。

## 8. 公开 API

- `~/api/`（93 文件）是对外契约：`IModularItem/IModularArmor/IModularEnergyItem`（装备接口）、`api/capability/`（ModuleHost/ModuleProvider/DECapabilities，附件即 ItemStack 数据组件视图，CapabilityData.java:38-59）、`api/crafting/`（IFusionRecipe/IFusionStateMachine/IFusionInventory——第三方注入 fusion 配方与注入器的口子）、`api/modules/`（ModuleType/ModuleData/ModuleEntity 全家族，别的 mod 注册自己的模块经 `DraconicAPI.addModuleProvider(MODID)` + 同步注册表 DEModules.java:63-67，这是"装备系统可被 addons 扩展"的完整样板）。
- 与 BrandonsCore 的边界：一切"声明式同步"（ManagedData + DataFlags、capManager.syncContainer/syncTile）、多方块 JSON 引擎、WorldEntity、OP 能量抽象都住在 BrandonsCore；DE 提供的是玩法装配与协议补丁。Colossus 若要移植本报告结论，需要把 BrandonsCore 那半（尤其 ManagedData 脏检查与 `IValueHashable` 哈希同步，`~/lib/OPStorageOP.java:241-256`）用 NeoForge Data Attachments / SynchedEntityData 重写等价层。
- 集成面：`~/integration/`（JEI、CraftTweaker、CC 计算机接口、EquipmentManager 槽位整合）。
