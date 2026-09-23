# Trinkets and Baubles 源码分析报告

> 分析对象：`_参考仓库/_bulk/jinqinxixi__Trinkets-and-Baubles-Forge-1.20.1`，分支 `main`，HEAD `6586ca8`（Merge PR #17）。
> **先说结论性的偏差**：本仓库虽然名字里有 Trinkets/Baubles，但它**不是**一个槽位系统实现。槽位、饰品 GUI、穿戴容器、死亡掉落规则**全部外包给 Curios 5.11.1**（`build.gradle:154-155`），本仓库只做"内容 + 效果挂载"。因此下文第 4.1 节回答的是"槽位形状在 Curios 之上如何被声明"，第 5 节回答"数据驱动在哪一层"，第 8 节末给出与 Curios 路线的取舍对比。
> 所有行号相对仓库根。运行时行为（是否真在游戏中生效）除明确注明外**未验证**。

## 1. 基本信息

| 项 | 值 | 出处 |
|---|---|---|
| mod_id | `trinketsandbaubles` | `gradle.properties:45`；常量在 `src/main/java/com/jinqinxixi/trinketsandbaubles/TrinketsandBaublesMod.java:63` |
| 显示名 / 版本 / 作者 | Trinkets and Baubles Reforked / 1.3.1 / jinqinxixi | `gradle.properties:47,51,57` |
| 许可证 | **两处矛盾**：`gradle.properties:49` 写 `All Rights Reserved`，git 索引里的 `LICENSE` 文件（`git show HEAD:LICENSE`）是 GNU LGPL v3 正文；该文件在本地磁盘不存在 | 见左 |
| 目标 MC / Forge | 1.20.1（范围 `[1.20.1,1.21)`）/ Forge 47.3.0（`[47,)`） | `gradle.properties:10,16` |
| 映射 | parchment `2023.09.03-1.20.1` | `gradle.properties:35,38` |
| Gradle 插件 | ForgeGradle `[6.0,6.2)` + `org.spongepowered.mixin 0.7.+` + `org.parchmentmc.librarian.forgegradle 1.+` + eclipse/idea/maven-publish；buildscript 里另拉 `mixingradle:0.7-SNAPSHOT` | `build.gradle:1-17` |
| 工程结构 | 单 source set（single module），无 api/impl 拆分；`settings.gradle` 只有 pluginManagement + foojay toolchain | `build.gradle`、`settings.gradle:1-14` |
| Java 版本 | 17（`java.toolchain.languageVersion`），mixin `compatibilityLevel: JAVA_17` | `build.gradle:29`、`src/main/resources/trinketsandbaubles.mixins.json:6` |
| 编译依赖 | **Curios 是本 mod 的硬前置**：`compileOnly curios-forge:5.11.1+1.20.1:api` + `implementation curios-forge:5.11.1+1.20.1`（`build.gradle:154-155`）。另有 Pehkui（implementation，体型缩放）、JEI/FirstAid/Caelus/Iron's Spellbooks/Patchouli/Botania/GeckoLib/PlayerAnim/ApothicAttributes 为 compileOnly 或 runtimeOnly | `build.gradle:150-186` |
| 元数据 | mods.toml 只声明 `forge` 与 `minecraft` 两个依赖，**没有声明 curios 依赖块**——前置缺失时不会给出友好报错 | `src/main/resources/META-INF/mods.toml:47-66` |
| 模板残留 | `mods.toml`/`build.gradle` 保留 Forge MDK 模板注释、`changelog.txt`(69KB) 与 `CREDITS.txt` 是模板文件、`mod_description=Example mod description.`（`gradle.properties:59`）；根目录 git 索引里还有 `hs_err_pid26660.log` | 见左 |

## 2. 源码规模与包结构

实测：`find src -name "*.java" | wc -l` = **126**；总行数 **19,686**（速览卡片写 19,812，偏高 126 行，以实测为准）。其中约 **1,766 行**是以 `//` 开头的注释行（≈9%），且高度集中在几处"整文件注释掉"的死代码（`modifier/CurioAttributeEvents.java` 262 行、`mixin/CuriosTooltipMixin.java`、3 个未登记的 mixin，详见第 6 节）。

**检出完整性问题（重要）**：本仓库是 sparse checkout（`.git/info/sparse-checkout` 存在，`core.sparseCheckout=true`）。`git ls-files` = **388** 个文件，磁盘只有 **136** 个。缺失的正是学习价值很高的部分：`src/main/resources/assets/**`（193 个文件：模型、贴图、`lang/en_us.json`、`lang/zh_cn.json`）与 `src/main/resources/data/**`（52 个文件，含 `curios/slots/ring.json`、`curios/entities/shipin.json`、9 个 `curios/tags/items/*.json`、40 个 `recipes/*.json`）。本报告凡引用这些文件处均以 `git show HEAD:<path>` 读出的内容为准，并标注"(git 索引)"。`src/generated/` 在 git 索引里计数为 0 → 无 datagen 产物。

按包（3 层，文件数 / 行数）：

| 包 | 文件 | 行 | 职责 |
|---|---|---|---|
| `items/baubles` | 27 | 5,911 | 全部饰品物品类，本 mod 主体 |
| `modEffects`（包名实际为 `modeffects`） | 12 | 2,985 | MobEffect 子类 + 注册表 |
| `config` | 3 | 1,603 | ForgeConfigSpec：通用、种族属性、词条 |
| `capability/impl` | 7 | 1,470 | 7 个种族 capability 实现 |
| `potion` | 11 | 975 | 11 个药水物品 |
| `util` | 4 | 615 | 种族戒指查询、体型缩放、扫描 |
| `modifier` | 3 | 657 | `ModifiableBaubleItem`（活的）、`CurioAttributeEvents`（死的） |
| `mixin` | 8 | 551 | 4 个启用、4 个整文件注释 |
| `event` | 5 | 579 | 客户端按键/渲染 + 龙环服务端 tick |
| `capability/event` | 1 | 514 | `RaceEventHandler`：attach/clone/tick 中枢 |
| `capability/api` | 8 | 257 | `IBaseRaceCapability` + 7 个种族接口 |
| `capability/base` | 2 | 452 | 抽象 capability + provider |
| 其余（block/client/compat/loot/items 根/recast/network/capability 杂项） | 35 | 3,117 | — |

最大源文件（行数为 `wc -l` 实测）：`items/baubles/ArcingOrbItem.java` 1457、`config/ModConfig.java` 777、`config/RaceAttributesConfig.java` 740、`capability/event/RaceEventHandler.java` 514、`modEffects/FaelesEffect.java` 484、`capability/impl/DragonCapability.java` 457、`modEffects/DragonsEffect.java` 449、`modEffects/TitanEffect.java` 424、`capability/base/AbstractRaceCapability.java` 418、`modEffects/FairyDewEffect.java` 409、`items/baubles/PolarizedStoneItem.java` 402、`capability/mana/hud/ManaHudOverlay.java` 389。

工程卫生缺陷（值得当反面教材）：包名与目录大小写不一致——目录是 `modEffects/`，`package` 声明是 `com.jinqinxixi.trinketsandbaubles.modeffects`（如 `modEffects/ModEffects.java:1`），全仓 14 个文件按此 import（`TrinketsandBaublesMod.java:58`）。Windows 区分不出，Linux CI/他人 checkout 会直接编译失败。另有拼写类文件名 `modEffects/IceResistanceEffet.java`（应为 Effect）。

## 3. 入口与注册

入口 `TrinketsandBaublesMod`（`@Mod(MOD_ID)`，`TrinketsandBaublesMod.java:60-109`）构造函数承担全部装配：

```java
IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
NetworkHandler.register();                       // :68  两个 SimpleChannel 之一
ModItem.register(modEventBus);                   // :70-73 四个 DeferredRegister
ModBlocks.register(modEventBus); EFFECTS.register(modEventBus);
modEventBus.register(ModConfig.class);           // :74
MinecraftForge.EVENT_BUS.register(LootTableHandler.class);   // :76
RaceCapabilityNetworking.init();                 // :81  第二个 SimpleChannel
ModLoadingContext.get().registerConfig(Type.COMMON, ModConfig.SPEC, "trinketsandbaubles-common.toml");  // :85-94 两份 COMMON 配置
if (FMLEnvironment.dist == Dist.CLIENT) { modEventBus.addListener(this::clientSetup);
    MinecraftForge.EVENT_BUS.addListener(EventPriority.NORMAL, false,
        RenderLevelStageEvent.class, DragonsEyeRenderer::onRenderWorld); }   // :100-108
```

注册方式三条并存：(a) `DeferredRegister`（物品 `items/ModItem.java:24`、方块 `block/ModBlocks.java:16`、创造标签 `items/ModCreativeModeTab.java:15-26`、效果 `modEffects/ModEffects.java:9-10`）；(b) `@Mod.EventBusSubscriber` 静态类自动挂到 Forge 总线（`capability/event/RaceEventHandler.java:43`、`modifier/ModifiableBaubleItem.java:32`、`loot/LootTableHandler.java:19`、`recast/AnvilRecastHandler.java:14`、`capability/mana/ManaData.java:16`）；(c) 手动 `EVENT_BUS.register`。软依赖兼容走"检测 + 反射加载类"：`TrinketsandBaublesMod.java:111-123` 先 `FMLLoader.getLoadingModList().getModFileById("firstaid") != null`，再 `Class.forName("...FirstAidLivingDamageEvent")`，成功才 `register(new FirstAidCompat())`。

事件订阅点清单（与槽位/装备相关的）：`AttachCapabilitiesEvent<Entity>`（`RaceEventHandler.java:58`）、`LivingDeathEvent`（:94）、`PlayerEvent.Clone`（:127）、`PlayerLoggedIn/ChangedDimension/Respawn`（:282/:288/:298）、`LivingTickEvent`→驱动 `cap.tick()`（:359-365）、`BlockEvent.BreakEvent`（:335）、`EntityMountEvent`（:482）、`LivingChangeTargetEvent`（:496）、`PlayerChangeGameModeEvent`（:507）；`LootTableLoadEvent`（`loot/LootTableHandler.java:24`）、`AnvilUpdateEvent`（`recast/AnvilRecastHandler.java:31`）、`RegisterKeyMappingsEvent`（`event/ClientEvents.java:13`）、`InputEvent.Key`（`event/ClientForgeEvents.java:30`）、`RenderGuiEvent.Post`（`event/ClientRenderEvents.java:14`）。

三处"看着注册了其实没生效"：`TrinketsandBaublesMod.java:228-247` 的 `onPlayerTick` 是外层 `@Mod` 类的静态方法，而外层类从未 register 到任何总线 → 不触发；`commonSetup` 里 `CurioAttributeEvents.init()` 被注释掉（:212）；`ManaData`（`ManaData.java:16` 注解 + `TrinketsandBaublesMod.java:79` 手动 register）与 `LootTableHandler`（:19 注解 + :76 手动）被**重复注册两次**。

## 4. 核心系统

### 4.1 槽位层：完全委托 Curios，声明在数据文件里

槽位类型不在 Java 里出现一次：全仓 grep `"ring"|"head"|"curio:"` 等槽位字面量在 `.java` 里零命中。声明只发生在 4 类 JSON（git 索引，磁盘缺失）：

- **槽位数量/外观**：`src/main/resources/data/trinketsandbaubles/curios/slots/ring.json` 内容仅 `{"size": 1, "add_cosmetic": false}` —— 把 Curios 的 `ring` 槽改成 1 格、禁用装饰槽。其余 9 种槽位类型不提供，沿用 Curios 自带定义。
- **谁能有哪些槽**：`data/trinketsandbaubles/curios/entities/shipin.json` = `{"entities": ["player"], "slots": ["back","body","belt","bracelet","charm","curio","hands","head","necklace","ring"]}`（文件名 `shipin`="饰品"拼音）。
- **哪件物品进哪个槽**：`data/curios/tags/items/<slot>.json`，例如 `ring.json` 收 9 个戒指、`head.json` 收 5 个龙眼/头冠、`curio.json` 收 4 个石头/泰迪熊。
- **解锁/增长**：无。没有任何"进度→槽位 +1"的代码；`add_cosmetic` 与 `size` 都是静态 JSON。

Java 侧只**读**槽位，统一走 `CuriosApi.getCuriosInventory(living)`（全仓 38 处调用），两种读法：`findFirstCurio(...)`（`compat/FirstAidCompat.java:22-25`、`network/message/Messages/PolarizedStoneToggleMessage.java:36-38`）与手遍历 `getCurios().forEach((id, h) -> for i < h.getSlots() -> h.getStacks().getStackInSlot(i))`（`util/RaceRingUtil.java:17-30`、`items/baubles/ArcingOrbItem.java:214-224`）。

### 4.2 装备交互与"生效"判定

穿戴（右键装备 / 拖拽 / GUI 按钮 / Shift 搬运 / 死亡保留 / 掉落规则）本仓库**一行都没写**，全由 Curios 的容器与 `ClientScreenEventHandler` 提供。本 mod 只在 Curios 回调里填内容：

- 允许右键穿戴：`items/baubles/DwarvesRingItem.java:148-151` `canEquipFromUse → true`；穿戴音效 `:153-156` 返回 `ICurio.SoundInfo(AMETHYST_BLOCK_CHIME,...)`（6 个种族戒指各有一份同样的实现）。装备准入 `items/baubles/StoneofNegativeGravityItem.java:94`。
- 生命周期回调：`onEquip` / `onUnequip` / `curioTick` 在每个戒指类里成对出现（`DwarvesRingItem.java:71-147`、`TitanRingItem.java:72-118`、`WitherRingItem.java:37-58`、`StoneoftheSeaItem.java:98-128`、`TeddyBear.java:95-101` 等）。
- 死亡/切维度保留：`RaceEventHandler.java:93-123`（`LivingDeathEvent` 把 `WasActive` + 当时最大魔力写进 `player.getPersistentData()` 的 `DwarvesCapability` 等 7 个键）、`:126-180`（`PlayerEvent.Clone` 分死亡/非死亡两支）、`:282-299`（登录/换维度/重生后 refresh+sync）。注意这管的是"种族能力状态"，不是饰品物品本身——物品保留规则没被覆盖（槽位 JSON 里没有 `drop_rule`），跟随 Curios 默认。
- "装备中"的判定方式是**全槽扫描**，不是槽位索引：`DwarvesRingItem.java:38-43` `isEquipped()` = `findFirstCurio(stack -> stack.getItem() instanceof DwarvesRingItem).isPresent()`。互斥规则也靠扫描计数：`RaceRingUtil.hasMultipleRaceRings` > 1 时所有种族能力都不激活（`DwarvesRingItem.java:49-57,77-85`）。

### 4.3 种族能力栈（本 mod 真正的"效果挂载"）

数据表示：7 个 `Capability<? extends IBaseRaceCapability>`（`capability/registry/ModCapabilities.java:18-37`，`CapabilityManager.get(new CapabilityToken<>(){})`）+ 一张 `Map<String, Capability<?>> RACE_CAPABILITIES`（:16,40-48，静态块填 7 条）。

挂载：`AttachCapabilitiesEvent<Entity>` 里对 `instanceof Player` 逐个 `addCapability(new ResourceLocation(MOD_ID, raceName), new BaseRaceCapabilityProvider<>(impl, cap))`（`RaceEventHandler.java:58-91`）。持久化用 `BaseRaceCapabilityProvider implements ICapabilitySerializable<CompoundTag>`（`capability/base/BaseRaceCapabilityProvider.java:10-34`），`serializeNBT/deserializeNBT` 直接转发给能力对象（`AbstractRaceCapability.java:197-213`），落盘的就是 `{active, permanentManaDecrease, CurrentMaxMana}` 三个字段。**没有** `RegisterCapabilitiesEvent`，也不需要——因为 provider 自己可序列化，绕开了 Forge 1.20.1 "capability 必须注册 storage 才能存 NBT" 这一步。

何时算：属性不是每 tick 重算，而是**状态机式一次性应用**。`setActive(true/false)`（`AbstractRaceCapability.java:122-152`）依次做 applyScaleFactor → applyAttributes → ManaData.modifyMaxMana(±bonus) → sync()；`applyAttributes`（:56-79）遍历 `attributeValues`（`Map<String, AttributeValueProvider>`，:43；由子类的 `registerAttributeValues()` 用方法引用把 TOML 配置项绑进来，例 `capability/impl/DwarvesCapability.java:27-55`）。`IBaseRaceCapability.validateAndFixAttributes()`（:93-110）设计上是"自愈"入口，但除 `ElvesCapability.java:127`、`FaelesCapability.java:207` 重写外**无任何调用点** → 死 API。真正的驱动是 `LivingTickEvent → updateRaceCapabilities → cap.tick() → onTick()`（`RaceEventHandler.java:359-383`，`AbstractRaceCapability.java:188-194`），`onTick()` 里靠 `player.addEffect(new MobEffectInstance(ModEffects.DWARVES, 30, 0, false,...))` 续一个 30tick 标记效果（`DwarvesCapability.java:73-80`），把"能力已激活"物化成可被别的 mod 看见的 MobEffect。

跨端流转：服务端只同步**两个标量** —— `SyncRaceCapabilityPacket{raceId, isActive, scaleFactor}`（`capability/network/SyncRaceCapabilityPacket.java:14-38`，encode 为 `writeUtf/writeBoolean/writeFloat`）。客户端 `ClientPacketHandler.handlePacket` 按 raceId 的 7 分支 switch 调 `updateStateOnly(active, scale)`（`capability/network/ClientPacketHandler.java:14-53`，`AbstractRaceCapability.java:249-255`），后者**只**改字段 + 设体型，故意不重算属性——因为属性在服务端算完后由原版 `Attribute` 同步包带给客户端。体型缩放依赖 Pehkui（`build.gradle:162`；`RaceScaleHelper.setSmoothModelScale`）。

带额外状态的能力靠子类覆写 `sync()` 补包：`capability/impl/DragonCapability.java:382-391` 在 `super.sync()` 之前先 `NetworkHandler.INSTANCE.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> serverPlayer), new SyncAllDragonStatesMessage(flightEnabled, dragonBreathActive, serverPlayer.getId()))` —— 这是全仓唯一一次"把饰品状态广播给周围玩家"（为了让旁观者看到龙息/飞行表现），也是 1.20.1 上 `PacketDistributor` 选型的一个现成例子。对应 handler（`network/message/DragonRingMessage/SyncAllDragonStatesMessage.java:39-62`）在客户端按 `entityId` 反查玩家后**调用 toggle 方法**对齐本地状态（`if (message.flightEnabled != cap.isFlightEnabled()) cap.toggleFlight();`），而不是直接写字段——与 4.3 主路线的 `updateStateOnly` 是两种风格。`setActive(false)` 也被覆写成"先广播全 false，再回收 `Player.getAbilities().mayfly/flying` 并 `onUpdateAbilities()`"（`DragonCapability.java:350-379`），说明飞行这类"必须动 PlayerAbilities 的能力"无法只靠 AttributeModifier 表达。

### 4.4 词条（random modifier）系统 + 铁砧重铸

活的那套在 `modifier/ModifiableBaubleItem.java`：抽象类 `extends Item implements ICurioItem`（:33），子类只需给出候选池（`getModifiers()`，:43；如 `DwarvesRingItem.java:28-33` 直接 `Modifier.values()`）。随机结果落到 ItemStack NBT 子标签 `BaubleModifier{Attribute,TranslationKey,Value,UUID}` + 根标签 `IsInitialized`（:89-96,73-82）。初始化时机有两处：`inventoryTick` 里服务器端且 `entity instanceof Player` 时（:64-71），和 `onEquip` 时兜底（:103-108）。

挂载/卸载与去重：`applyModifier`（:133-172）从 NBT 读回属性与 **UUID**，`if (!attr.hasModifier(mod)) addTransientModifier(mod)`；`removeModifier`（:174-193）按 UUID 移除，且对 `MAX_HEALTH` 特判把血量夹回上限。防抖靠比对**堆叠间 UUID**：`onEquip` 时若 `prevStack` 与新 `stack` 词条 UUID 相同就直接 return（:110-114），`onUnequip` 时若 `newStack` 同词条则不移除（:124-127）——这正是"同种饰品换槽/重排导致属性抖动"的标准解法。Operation 选择集中在 :195-201（攻速/移速/攻击力用 `MULTIPLY_BASE`，其余 `ADDITION`）。

重铸：`recast/AnvilRecastRegistry.registerAllRecipes()` 在 `commonSetup` 的 `enqueueWork` 里把 24 件饰品注册成"本体 + glowing_ingot → 本体"的配方（`recast/AnvilRecastRegistry.java:9-42`），`AnvilRecastHandler.onAnvilUpdate`（`recast/AnvilRecastHandler.java:31-62`）复制 left 堆叠、只删 `IsInitialized` 与 `BaubleModifier` 两个标签、按配置设经验/材料花费；`ModConfig.isModifierEnabled()` 为 false 时整条链路短路（:28-30）。注意输出堆叠保留原 UUID 之外的一切 NBT，重铸后由 `inventoryTick` 重新随机。

死掉的那套：`modifier/CurioAttributeEvents.java` 全文 291 行只有第 1 行 package 和第 28-29 行类声明是活的，**其余 262 行整块注释**，内容是用 `CurioAttributeModifierEvent` / `CurioChangeEvent` 走 Curios 原生属性通道 + `ModifierConfig` 白名单 + `AnvilRepairEvent` 重随的早期方案；配套还有 `modifier/ModifierTooltipHelper.java`（74 行）与 `config/ModifierConfig.java` 仍在，但入口 `init()` 已被注释（`TrinketsandBaublesMod.java:212`）。

### 4.5 魔力值（另一条持久化路线：PersistentNBT）

`capability/mana/ManaData.java` 不是 capability，全部状态写在 `player.getPersistentData()` 的 `trinketsandbaubles_mana` / `_maxMana` / `_lastManaRegenTime` / `_lastManaChangeTime` 四个键（:20-23,26-70）。写操作在服务端做完后立刻 `ManaNetworkHandler.syncManaToClient`（`capability/mana/ManaData.java:108-120` 定义，:40-41/:64-65/:81-82 三处调用），且以 `serverPlayer.connection != null && !isRemoved()` 作为"玩家已完全加载"的守卫——这是对 1.20.1 登录期空连接崩溃的实用防御。同步包 `ManaSyncMessage{mana,maxMana}` 两端都注册（`network/handler/NetworkHandler.java:54-58`），handler 用 `DistExecutor.unsafeRunWhenOn(Dist.CLIENT, ...)` 落到 `ClientManaNetworkHandler.handleManaSync`（`network/message/ManaMessage/ManaSyncMessage.java:38-47`）。HUD 是纯客户端单例 `ManaHudOverlay`，位置可拖拽并存成 JSON 文件（`capability/mana/hud/ManaHudOverlay.java:92-127`）。回复/重生/克隆分支在 :131-190、:209-257、:258-289。

### 4.6 效果与主动技能按键链路

12 个 MobEffect 由 `modEffects/ModEffects.java:9-46` 的 `DeferredRegister<MobEffect>` 注册。两类实现：一类是"标记 + 事件订阅"型（`modEffects/BleedingEffect.java:18-27` 用 `applyEffectTick` + `isDurationEffectTick` 实现每 20tick 1 点 magic 伤害），一类是巨型"每族一个效果"型（`FaelesEffect.java` 484 行、`DragonsEffect.java` 449 行、`TitanEffect.java` 424 行；这些类同时带 `@Mod.EventBusSubscriber` 自己在事件总线里挂逻辑，`FaelesEffect.java:41-42`，并且 `addAttributeModifiers` 覆写被整段注释在 `FaelesEffect.java:46-58`——属性改由 4.3 的 capability 负责）。

主动技能的链路是"原版 KeyBinding → 自定义包 → 服务端改状态 → 回同步"：按键在 `client/keybind/KeyBindings.java` 定义 9 个（冲刺 V/Y/U/H/J/K/I/R/L，全部 `KeyConflictContext.IN_GAME`，分类 `key.categories.trinketsandbaubles`），在 `event/ClientEvents.java:13-25` 注册（注意 `TOGGLE_DRAGONS_EYE_VISION` 被注释掉未注册），`event/ClientForgeEvents.java:30-45` 统一分发；每个动作前先读客户端侧 capability 的 `isActive()` 门控（如 :74-96 龙息、:100-107 仙女飞行）。服务端侧的持续状态放在capability（`capability/impl/DragonCapability.java` 457 行）并在 `event/DragonCapabilityServerHandler.java:117-206` 的 ServerTick/LivingTick 里推进。

渲染这块几乎是空的：全仓无 `RenderCurioEvent`/`ICurioRenderer`/`LayerDefinition`/`AddLayerDefinitionsEvent`/`EntityRenderers` 命中（grep 零结果），也**没有任何 `AbstractContainerMenu` / `MenuType` / `IContainerFactory` / `Screen` 代码** → 饰品不画在实体身上（外观交给 Curios 默认槽位图标 + 物品模型），GUI 布局一行都不在本仓库里。Java 侧唯一的"外观随状态变化"手段是 `ItemProperties.register`：`TrinketsandBaublesMod.java:186-204` 在 `FMLClientSetupEvent` 的 `enqueueWork` 里给 `POLARIZED_STONE` 注册两个 `attraction_mode`/`deflection_mode` 布尔属性，lambda 直接读 `stack.getTag().getBoolean(...)`，即"NBT 标志 → 模型切换"（对应 `build.gradle` 之外还需 assets 里 `override` 模型，本地检出缺失）。世界内叠加渲染只有一处：`client/renderer/DragonsEyeRenderer.java:60-61` 订阅 `RenderLevelStageEvent` 并卡在 `Stage.AFTER_TRANSLUCENT_BLOCKS`，由 `TrinketsandBaublesMod.java:102-107` 以方法引用手动注册（不是 `@EventBusSubscriber`）。HUD 侧是 `capability/mana/hud/ManaHudOverlay.java:238+` 的 `render(GuiGraphics)`，由 `event/ClientRenderEvents.java:14-17` 在 `RenderGuiEvent.Post` 调；扫描/透视类反馈走 `util/ScanSystem.java`（:66 玩家 tick、:75 夜视开关、:146 从配置读矿物分组、:188 把配置里的方块 id 编成集合）。

## 5. 网络 / 数据驱动 / 配置 / datagen

**两条 SimpleChannel 并存**（选型：作者选了 `SimpleChannel` + 手写 encode/decode，没有用 1.20.1 也能用的 `EventNetworkChannel`，也没用 `Advanced` 变体）：

- `network/handler/NetworkHandler.java:27-32`：`NetworkRegistry.newSimpleChannel(rl(mod_id,"main"), () -> "1.0", "1.0"::equals, "1.0"::equals)`；`register()` 按"两端共同 / server-bound / client-only"三段注册 13 个包（:38-145），每个包提供 `encode/decode/handle` 三个静态方法，consumer 全用 `consumerMainThread`。
- `capability/network/RaceCapabilityNetworking.java:13-24`：`rl(mod_id,"races")`、协议版本 `2.6`，用旧 `registerMessage(id, cls, enc, dec, handler)` 五参重载注册 1 个同步包。

两处缺陷可当反例：`packetId` 计数器与 `register()` 里的局部 `int id = 0`（`NetworkHandler.java:25,39`）并存，局部变量是废的；`PolarizedStoneToggleMessage` 是 client→server 包（其 handler 用 `context.getSender()` 取 `ServerPlayer`，`network/message/Messages/PolarizedStoneToggleMessage.java:29-32`），却只在 `registerClientOnlyMessages()` 里注册（`NetworkHandler.java:135-145`），而该函数由 `DistExecutor.unsafeRunWhenOn(Dist.CLIENT, ...)` 调用（:48）→ 服务端侧没有该包类型的 handler。客户端确实在发（`network/handler/ClientNetworkHandler.java:51`）。

**数据驱动分三层**：槽位/入槽靠 Curios JSON（见 4.1，手写、无 datagen）；**掉落靠 TOML**——`config/ModConfig.java:110-160` 为 43 个原战利品表各定义一个 String 配置项，格式 `item,weight,minRolls,maxRolls;...`，`loadLootConfig()`（:695-708）解析成 `Map<ResourceLocation, List<LootEntry>>`（`lootConfig` 字段在 :708，`LootEntry` 在 :711-724，`LOOT_MAPPING`（表 id → 配置项）在 :641-690，解析器手工 split 在 :725-747），再由 `loot/LootTableHandler.java:24-46` 在 `LootTableLoadEvent` 里拼 `LootPool`/`LootItem.lootTableItem(...).setWeight(...)` + `setRolls(UniformGenerator.between(...))` 注进表；**数值靠 TOML**——`config/RaceAttributesConfig.java` 用 7 个内部类（`DwarvesAttributes` 等，字段声明 :11-33，构造里 `builder.push("dwarves")` + `defineInRange` :35-90，实例在 :718-724）暴露每族 17 个属性倍率 + scale + manaBonus，被 4.3 的 `registerValue("MAX_HEALTH", RaceAttributesConfig.DWARVES.MAX_HEALTH::get)` 直接引用，所以配置改完不需重启逻辑。`ModConfig` 还有约 90 个开关，含总开关 `MODIFIER_ENABLED`（:163）、`SPEC = BUILDER.build()`（:624）、`isModifierEnabled()`（:767）。`TrinketsandBaublesMod.java:97` 用 `ModConfigEvent.Loading` 在配置重载时重跑 `ScanSystem.initializeOreGroups()`（`util/ScanSystem.java:146`）。

**datagen**：无。`build.gradle:72-78` 保留了模板的 `data` run 与 `--output src/generated/resources`，`build.gradle:80` 也把 generated 目录挂进 resources，但 `src/generated` 在 git 里不存在任何文件，Java 里也没有 `DataProvider`/`GatherDataEvent`。**客户端配置持久化**没有走 `FMLPaths.CONFIGDIR`，而是 `new File("config/trinketsandbaubles_mana_hud.json")` + Gson 相对路径（`capability/mana/hud/ManaHudOverlay.java:66,92-127`）。

Forge 1.20.1 基础设施取证（四项逐条给实例）：

- **capability 注册 + provider**：声明 `capability/registry/ModCapabilities.java:18-37`（`CapabilityManager.get(new CapabilityToken<>(){})`）、挂载 `capability/event/RaceEventHandler.java:58-91`（`AttachCapabilitiesEvent<Entity>` + `addCapability`）、provider `capability/base/BaseRaceCapabilityProvider.java:10-34`（`ICapabilitySerializable` + `capabilityType.orEmpty(cap, optional)`）。注意全仓 `grep -rn "invalidate"` 零命中 → `LazyOptional` 从不失效（`BaseRaceCapabilityProvider.java:12-19` 只建不关），这是 1.20.1 上常见写法但不规范，是否真产生运行期告警**未验证**。
- **DeferredRegister / RegistryObject**：物品 `items/ModItem.java:24`（`DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID)`）+ `:44` `ITEMS.register(name, () -> constructor.create(props))`，创造标签 `items/ModCreativeModeTab.java:15-26`（`Registries.CREATIVE_MODE_TAB`，走的是原生注册表 key 而非 `ForgeRegistries`，因为 1.20 起 tab 是 datapack registry），效果 `modEffects/ModEffects.java:9-10`，全部在 `TrinketsandBaublesMod.java:70-73` 用 `register(modEventBus)` 收口。
- **容器菜单 / `IContainerFactory`**：**仓库内无实例**（`.java` 里 `MenuType`/`AbstractContainerMenu`/`IContainerFactory`/`ScreenManager`/`registerMenuScreens` 全部零命中，见 4.6）。这不是遗漏而是分工——菜单与 `IContainerScreen` 由 Curios 的 `curios_container` 提供，本 mod 连一行菜单代码都不需要。若 nextCard 要自建槽位，这一项就是必须自己补的第一块。
- **`SimpleChannel` vs `EventNetworkChannel`**：选 `SimpleChannel`，两个实例（`network/handler/NetworkHandler.java:27-32`、`capability/network/RaceCapabilityNetworking.java:13-18`），全部用 `FriendlyByteBuf` 手写 codec（`consumerMainThread` 新式 :54-58 与 `registerMessage` 五参旧式 `RaceCapabilityNetworking.java:22-28` 混用），无 `EventNetworkChannel`、无 `PlayToClientPayload`。协议一致性靠 `PROTOCOL_VERSION::equals` 双向严格相等（`NetworkHandler.java:30-31` 是 `"1.0"`，`RaceCapabilityNetworking.java:12` 是 `"2.6"`）。

## 6. Mixin / ASM / 反射

配置文件 `src/main/resources/trinketsandbaubles.mixins.json`：`package: com.jinqinxixi.trinketsandbaubles.mixin`、`refmap: trinketsandbaubles.refmap.json`、`mixins: [PlayerMixin, BlockStateMixin, LivingEntityAccessor, CuriosTooltipMixin]`、`client: [CameraMixin]`、`defaultRequire: 1`；`build.gradle:81-86` 配 `add sourceSets.main, refmap` 与 `debug.export = true`，`annotationProcessor mixin:0.8.5:processor`（:157）；另在 client run 里设 `mixin.env.remapRefMap=true` + `refMapRemappingFile=build/createSrgToMcp/output.srg`（`build.gradle:35-36`），这是 mixingradle + ForgeGradle 在 1.20.1 的标准配套。

启用的 5 个注入点及目的：

- `mixin/PlayerMixin.java:21-27` `@Inject(Player#getDigSpeed, RETURN, cancellable, remap=false)` 追加矮人挖矿速度（按 `defaultDestroyTime()*0.5` 乘算，:38-59，且带 1 秒限流的 `LOGGER.info` 调试输出没删）；`PlayerMixin.java:65-74` `@Inject(isSwimming, HEAD)` 让泰坦能力者不进入游泳姿态。
- `mixin/BlockStateMixin.java:14-17` `@Mixin(Player.class)` + `@Inject(hasCorrectToolForDrops, HEAD, cancellable)` —— **文件名与注入目标完全不符**，且类被声明为 `abstract`。
- `mixin/LivingEntityAccessor.java:8-11` `@Accessor("jumping")` 读 LivingEntity 私有字段。
- `mixin/CameraMixin.java:16-20` `@ModifyVariable(Camera#getMaxZoom)` 服务于龙眼夜视/透视的拉远。
- `mixin/CuriosTooltipMixin.java:21` 名义上 `@Mixin(ClientEventHandler.class)`（Curios 的客户端类），`@Redirect CuriosApi.getAttributeModifiers`（:26-48）——**整个方法体是注释**，即"用 mixin 屏蔽 Curios 自带词条 tooltip"的尝试已废弃。

未登记进 mixins.json 因而**根本不会加载**的 3 个：`mixin/PlayerFallDamageMixin.java`（:13-16 注入点也是注释）、`mixin/WolfInteractionMixin.java`（:14-16 注释）、`mixin/WolfMovementMixin.java`（:26,44 注释）——合计约 250 行死代码。反射使用面很窄：只有软依赖探测的 `Class.forName`（`TrinketsandBaublesMod.java:115`、`items/baubles/ArcingOrbItem.java:140`）。未发现 `getDeclaredMethod`/`setAccessible` 级别的字段方法反射，也没有 ASM/`Unsafe`/字节码生成。跨 mod 的魔力适配不是反射，而是"编译期直调 + 运行期探测把关"：`ArcingOrbItem.java:46-49` 定义私有 `ManaSystem` 接口与三个内部类（`IronsSpellsManaSystem` :54-73 用全限定名直调 `io.redspace.ironsspellbooks.api.magic.MagicData`、`BotaniaManaSystem` :92-119 直调 `vazkii.botania.api.mana.ManaItemHandler`、`InternalManaSystem` :75-90 落到本 mod 的 ManaData），选路前先 `ModList.get().isLoaded("botania")`（:133-135）/ `Class.forName("...MagicData")`（:138-145）且受 `ModConfig.USE_BOTANIA_MANA`/`USE_IRONS_SPELLS_MANA` 控制（`config/ModConfig.java:34-35`）——这也是为什么 `build.gradle:176-183` 把它们放在 `compileOnly`（+`runtimeOnly` 只在 dev 跑）。

## 7. 值得学的 5 条

1. **`capability/base/BaseRaceCapabilityProvider.java:10-34`** — Forge 1.20.1 上让"玩家身上的自定义数据"落盘的最短路径：provider 直接 `implements ICapabilitySerializable<CompoundTag>` 并把序列化转发给数据对象，于是不需要 `RegisterCapabilitiesEvent` + `IStorage` 三件套。比"capability 里塞逻辑"清爽，值得照抄成模板。
2. **`capability/base/AbstractRaceCapability.java:281-291` + `capability/attribute/AttributeRegistry.java:63-160`** — 属性挂载的"固定 UUID + 值漂移检测"写法：一个 `Map<名字, (Attribute, UUID, Operation, isPercentage, 翻译键)>` 单表管住 17 个属性，`addTransientModifier` 前先 `getModifier(uuid)`，只在"没有 / 金额差 > 0.0001"时才 remove+re-add。任何"装备/丹药/buff 加属性"的系统都需要这套去重，直接抄表结构最省事。
3. **`capability/event/RaceEventHandler.java:152-180`** — `PlayerEvent.Clone` 里用 `server.tell(new TickTask(server.getTickCount()+1, ...))` 延后一 tick 再恢复能力与魔力。1.20.1 上新 `ServerPlayer` 的 capability attach 时机晚于 Clone 事件，这是该坑的最小代价绕法（并区分 `event.isWasDeath()` 走死亡/传送两条路）。
4. **`modifier/ModifiableBaubleItem.java:99-131` 配合 `:46-62`** — 用"词条 UUID 是否相同"决定 `onEquip`/`onUnequip` 要不要真的加/删属性：`prevStack` 同 UUID 就不重复 apply，`newStack` 同 UUID 就不 remove。换槽、整理背包、跨维度导致的 equip/unequip 抖动是饰品 mod 最常见的属性翻倍 bug 源，这段是可直接搬的通用解法。
5. **`config/ModConfig.java:110-160,695-724` + `loot/LootTableHandler.java:24-46`** — 不写 datagen、不改数据包，就把掉落塞进 43 张原版箱子表并让整合包作者可配：`LootTableLoadEvent` + `LootPool.lootPool().name(...).add(LootItem.lootTableItem(item).setWeight(w))` + `setRolls(UniformGenerator.between(min,max))`。`name("trinketsandbaubles_config_loot")` 给池子起名，便于冲突排查。

反面教材（同样值得记）：`TrinketsandBaublesMod.java:228` 的 `@SubscribeEvent` 挂在未注册的 `@Mod` 类上（静默失效）；同一 handler 类既 `@Mod.EventBusSubscriber` 又手动 `register`（:76,:79）；包名大小写与目录不一致（见第 2 节）；约 600 行整文件注释代码保留在仓库里（`modifier/CurioAttributeEvents.java`、`mixin/CuriosTooltipMixin.java`、3 个未登记 mixin）。

## 8. 公开 API

饰品槽系统由 Curios 承担，所以本 mod 的"给别人用"分两种情形：**给别人接它的词条/种族框架**，以及**它自己作为 Curios 的下游**。

入口包与可复用类型：

- `top.theillusivec4.curios.api.CuriosApi` / `SlotContext` / `type.capability.ICurio` / `ICurioItem` / `type.inventory.ICurioStacksHandler` —— 读槽位的唯一正路，本 mod 全部 38 处 `getCuriosInventory` 调用即示例。
- `com.jinqinxixi.trinketsandbaubles.capability.registry.ModCapabilities:18-48` —— 7 个 `Capability<...>` 常量 + `RACE_CAPABILITIES` 名字表，外部用 `player.getCapability(ModCapabilities.DWARVES_CAPABILITY)` 查"玩家当前是什么族/是否激活"。
- `com.jinqinxixi.trinketsandbaubles.capability.api.IBaseRaceCapability:9-88` —— 能力契约：`applyAttributes/removeAttributes/validateAndFixAttributes/isActive/setActive/getScaleFactor/setScaleFactor/tick/sync/getRaceId/getRaceName/getPermanentManaDecrease/forceRemoveAllModifiers/applyPermanentManaModifier`。
- `com.jinqinxixi.trinketsandbaubles.modifier.ModifiableBaubleItem:33-43,263-292` —— 词条化饰品的抽象基类，内含 `public enum Modifier`（18 个词条，:264-281）与 `MODIFIER_TAG="BaubleModifier"` / `INITIALIZED_TAG="IsInitialized"` 两个公开 NBT 键（:34-35）。
- `com.jinqinxixi.trinketsandbaubles.capability.mana.ManaData:26-101` —— 静态魔力门面：`getMana/setMana/getMaxMana/setMaxMana/modifyMaxMana/consumeMana/addMana/hasMana/restorePlayerMana`，外部饰品可直接扣蓝而不必自己存状态。
- `TrinketsandBaublesMod.MOD_ID:63`。

一件饰品要提供什么（本 mod 的约定）：①继承 `ModifiableBaubleItem` 并实现 `getModifiers()`（`items/baubles/DwarvesRingItem.java:25-33`）；②可选覆写 `onEquip/onUnequip/curioTick/canEquipFromUse/getEquipSound/appendHoverText`（同一文件 :71-156）；③在 `items/ModItem.java:36-55` 的 `registerCurio(name, ctor)` 注册（自动带 `stacksTo(1).rarity(UNCOMMON).fireResistant()` 模板，:28-33）；④把 `ResourceLocation` 加进 `data/curios/tags/items/<slot>.json`（git 索引）——**没有这一步，物品永远进不了饰品槽**，这是接入流程里最容易被忽略的一步；⑤若要新槽位类型，新增 `data/<modid>/curios/slots/<name>.json` + 在 `curios/entities/shipin.json` 的 slots 数组里追加。

需要提醒接入方的两个坑：`ModifiableBaubleItem.java:203-231` 手工覆写了 `initCapabilities`（`CuriosApi.createCurioProvider(new ICurio(){...})`），但那个匿名 `ICurio` 只转发了 `curioTick/onEquip/onUnequip/canEquip` 四项。子类在 Item 层覆写的 `canEquipFromUse`（`DwarvesRingItem.java:148`）与 `getEquipSound`（:153）能否仍被 Curios 走到，取决于 Curios 5.11.1 的取值路径是查 capability 还是查 `instanceof ICurioItem`——**未验证**（本仓库无 Curios 源码，且该 override 看起来是 `ICurioItem.initCapabilities` 默认实现尚未提供前的遗留）。若你继承本基类发现右键装备失效，第一嫌疑就是这段覆写少了转发。

与 Curios 路线的取舍对比：库里 `TheIllusiveC4__Curios.md` 分析的是 26.x/NeoForge 分支（该检出只有 `origin/26.x`，1.20.1 世代的 5.11.1 细节未确认），但架构分层是稳定的：Curios 侧有 `AttachmentType<CurioInventory>.serializable().copyOnDeath()`、`MenuType`、`CriterionTrigger`、`DataComponentType<attribute_modifiers>`（见该报告第 4 节，出自 `impl/CuriosRegistry.java:46-88`），槽位/掉落规则/条件/渲染/事件全套对外可扩；本 mod 一行槽位代码都没写，等于**验证了"下游 mod 不必自建槽位"这条路在 1.20.1 Forge 上完全成立**，代价是：把 `getCuriosInventory(...).resolve()` + `findFirstCurio(instanceof X)` 的全槽扫描放进 `curioTick`（`DwarvesRingItem.java:38-43,88`）、再叠一层 `hasMultipleRaceRings` 全表遍历（`util/RaceRingUtil.java:14-31`），每 tick 每戒指各跑一次，比 Curios 自带的 `CachedStack` 查询重得多；效果侧则用 `Map<String, Provider>` + 手写 UUID 表（4.3），而 Curios 自己已提供 `CurioAttributeModifierEvent` 数据组件路线（本 mod 试过又注释掉了，`modifier/CurioAttributeEvents.java:76-109`）。就"简陋"程度看：容量增长/解锁、槽位渲染（无 `RenderCurioEvent`/layer 代码，见第 4.2/6 节的 grep 零命中）、耐久消耗（全仓 `getDamageValue/hurtRandomly/maxDamage(` 零命中，且 `ModItem.java:28-33` 从不调 `.durability()` → 饰品无耐久、不会损坏）、死亡掉落（无 `drop_rule`）四项均缺，这四块若需要只能在 Curios 数据层解决。

给 nextCard / 求仙问道的两条建议：

1. **先分家再动手**：卡牌 gacha 与修仙的"装备容器"需求其实分两层——槽位/穿戴/掉落/同步这层**直接用 Curios 5.11.1**（它是 Forge 1.20.1 成熟前置，且求仙问道已有附魔/属性体系，接 `CurioAttributeModifierEvent` 比自己维护 UUID 表安全）；自己写的只有"词条池 + 效果挂载"这层。本仓库最有价值的骨架恰好是这层：`ModifiableBaubleItem` 的 NBT 词条 + UUID 去重 + equip/unequip 对称（第 7 节第 4 条），约 290 行、零侵入。
2. **玩家状态别再写 `getPersistentData()`**：ManaData（第 4.5 节）用整块 `Player.getPersistentData()` 存 4 个键，这在 1.20.1 上会被 Forge 整个 `PersistentNBT` 随实体同步、且永不裁剪，跨 mod 冲突也常见；求仙问道若要做"灵力/真气"这类高频变化的数值，照第 7 节第 1 条的 `ICapabilitySerializable` provider（或直接在 1.21 路线上用 `AttachmentType`）来放，并按第 7 节第 3 条处理 `PlayerEvent.Clone`。nextCard 的卡册收藏同理：**"状态机式 setActive() + 只在漂移时重建 modifier"** 比"每 tick 重算"更省，也天然规避了本仓库每 tick 全槽扫描的性能债。
