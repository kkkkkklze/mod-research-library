# Chaolux1/LendersDelight（L_Ender's Delight）源码分析

## 1. 基本信息

- Mod 名 / mod_id：L_Ender's Delight / `lendersdelight`，版本 `1.20.1-1.0.10c`
- 作者 / 许可证：Chaolux, BF_Meow / MIT（`gradle.properties` 与 mods.toml）
- 目标版本与加载器：MC 1.20.1 + Forge 47.3.0（`minecraft_version_range=[1.20.1,1.21)`），Java 17
- Gradle：`net.minecraftforge.gradle [6.0,6.2)`、mappings `official`、无 mixin 插件、无 jarJar
- 编译依赖（重点）：**Farmer's Delight**（`curse.maven:farmersdelight-398521:8083474`，提供 `KnifeItem`/`ConsumableItem` 与烹饪体系）、**L_Ender's Cataclysm**（`curse.maven:cataclysm-551586:6769185`，本 mod 是它的食物扩展，"它依赖谁"= 这两个）。无 JEI/Curios 硬依赖
- 前置声明：`src/main/resources/META-INF/mods.toml`（`mod_license=MIT`，displayName、authors、description 全部由 `processResources` 的 `expand` 从 gradle.properties 注入）

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **30**，总行数 **1876**（全仓库仅 `src/main/java` 有代码，`src/main/resources` 只有 `META-INF/mods.toml`，无 assets/data）。包结构（根包 `net.chaolux.lendersdelight`）：

- `coomon`（原文如此，拼写笔误的 common）→ `coomon/item` 10、`coomon/stat` 8、`coomon/loot/modifier` 1、`coomon/utility` 1
- `registry` → `registry/item` 1、`registry/block` 1、`registry/stat` 3
- `client` 2（`ClientStatTooltipHelper`、`FovHandler`）
- 根 2（`LendersDelight`、`Config`）

最大文件：`registry/item/ModItems.java` 196、`coomon/stat/PlayerStatEvents.java` 159、`LendersDelight.java` 136、`coomon/stat/StatConsumableItem.java` 135、`coomon/item/ImprovedDogFoodItem.java` 123、`coomon/loot/modifier/AddLootTableModifier.java` 114。

## 3. 入口与注册

主类 `src/main/java/net/chaolux/lendersdelight/LendersDelight.java:22`（普通 `@Mod`，不用 `@EventBusSubscriber` 挂主逻辑）。

```java
IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
ModItems.ITEMS.register(modEventBus);          // DeferredRegister<Item>
ModBlocks.BLOCKS.register(modEventBus);        // DeferredRegister<Block>
ModNetwork.register();                          // SimpleChannel 手动注册
modEventBus.addListener(this::addCreative);     // BuildCreativeModeTabContentsEvent
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, Config.SPEC);
```

注册框架：**DeferredRegister**（`ModItems.java:118` `DeferredRegister.create(ForgeRegistries.ITEMS,"lendersdelight")`），物品字段声明与 `static{}` 块里的实例化分离，`registerWithTab(name, supplier)` 统一入口；创造标签页物品在 `addCreative`（`:46`）按 `CreativeModeTabs.FOOD_AND_DRINKS` / `COMBAT` 手动 accept（含 7 把刀）。`ModBlocks` 只有 1 个方块（`CRYSTALLIZED_CORAL_PIE`）。

## 4. 核心系统

**① 玩家属性 Capability**（`coomon/stat/`）：`IPlayerStat`（接口，含 `saveToNBT/loadFromNBT`）→ `PlayerStatCapability`（`EnumMap<StatType,Float> stats` + `Set<ResourceLocation> foods`）→ `PlayerStatProvider implements ICapabilitySerializable<CompoundTag>`（`PlayerStatProvider.java:21` `CapabilityManager.get(new CapabilityToken<IPlayerStat>(){})` + `LazyOptional`）。挂载在 `registry/stat/ModEvents.java:15` 的 `AttachCapabilitiesEvent<Entity>`，能力本体在 `ModCapabilities.java:12` 用 `RegisterCapabilitiesEvent#register(IPlayerStat.class)` 声明。

**② "吃食物永久加属性"**（`coomon/stat/StatConsumableItem.java` extends Farmer's Delight `ConsumableItem`）：`finishUsingItem` 里按 `StatMode` 分支——`ACCUMULATE` 每次累加、`ONCE` 用 `stats.hasConsumed(itemRL)`/`markConsumed` 去重、`LIMITED` 用 `isLimitReach` 与**实际 AttributeInstance.getValue()** 比较（`:117`，属性类加成走 attribute、跳劈/暴击/回血走自定义 stat）；每次变更后 `PlayerStatProvider.sync(player)`。

**③ 属性落地**（`coomon/stat/PlayerStatEvents.java:72`）：`TickEvent.PlayerTickEvent`（END 相位）里对 MOVEMENT_SPEED / ATTACK_SPEED / KNOCKBACK_RESISTANCE / ATTACK_DAMAGE / ARMOR / `ForgeMod.SWIM_SPEED` 逐个 `removeModifier(UUID)` 再按需 `addTransientModifier(new AttributeModifier(uuid,"...",value/100f,MULTIPLY_BASE))`；`PASSIVE_REGEN` 每 100 tick `player.heal(regen/100f)`；`LivingJumpEvent` 给 y 速度加 `jump/500f`；`CriticalHitEvent` 里 `setResult(ALLOW)+setDamageModifier(1.5f)` 实现暴击率。

**④ 死亡/重连同步**：`onDeath`（`:37`）把 `saveToNBT()` 存进静态 `Map<UUID,CompoundTag> SAVED_STAT`（受 `Config.RESET_ON_DEATH` 控制），`onRespawn` 取回 `loadFromNBT` + sync，`onLogin` 直接 sync。

**⑤ 战利品注入**（`coomon/loot/modifier/AddLootTableModifier.java:18`）：`@EventBusSubscriber(bus=Bus.FORGE)` 监听 `LootTableLoadEvent`，硬编码判断 `cataclysm:entities/<boss>`（约 17 个：the_leviathan、maledictus、ignis、scylla、cindaria…），用 `LootPool.lootPool().name("lendersdelight_xxx").setRolls(UniformGenerator.between(1,1)).add(LootItem.lootTableItem(...).apply(SetItemCountFunction.setCount(...)))` 追加肉/材料。非 GLM，属于"运行时改原版表"的简单做法。

**⑥ 网络**（`registry/stat/ModNetwork.java`、`coomon/stat/StatSyncPacket.java`）：`SimpleChannel`（`lendersdelight:main`，协议号 "1.0"）单包；`StatSyncPacket` 手写 `encode/decode`（`writeVarInt` 长度 + `writeEnum(StatType)` + `writeFloat` + `writeResourceLocation` 集合），`handle` 里 `enqueueWork` 并调用 `@OnlyIn(Dist.CLIENT)` 的 `applyToClient`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 ④⑥，单向 `PLAY_TO_CLIENT`，`PlayerStatProvider.sync(ServerPlayer)` 为唯一出口。
- 数据驱动：**无**（无 datagen、无 JSON 数据包、无 loot modifier JSON）。
- 配置：`Config.java:22` ForgeConfigSpec，`ENABLE_STAT`/`SHOW_TOOLTIP_STAT`/`RESET_ON_DEATH`/`STAT_MODE`(enum `StatMode`)+`Map<StatType,ForgeConfigSpec.DoubleValue> STAT_LIMITS`（9 项上限，`defineInRange`）；`ModConfigEvent` 里刷新静态字段 `showTooltipStat` 供 tooltip 快速读取。
- datagen：**无**。

## 6. Mixin

**无 mixin**（无 `*.mixins.json`、无 mixin gradle 插件、`AddLootTableModifier` 那条"改别人战利品表"的需求用 Forge 事件而非 mixin 完成）。

## 7. 值得学的 5 条具体做法

1. **客户端类用 `DistExecutor.unsafeCallWhenOn` 包一层**：`StatConsumableItem.java:106` 从 common 的 `appendHoverText` 调客户端 helper，避免服务端加载 `Minecraft` 类而崩溃；所有跨端调用都照抄这个模式（`client/ClientStatTooltipHelper.java`）。
2. **"永久属性"双轨制**：能映射成原版 attribute 的（速度/护甲/攻速…）走 `AttributeModifier`，其余（跳劈/暴击/回血）存自定义 stat，且 `LIMITED` 模式下用 attribute 真实值判上限（`StatConsumableItem.java:117`）；适合做任何"食物成长/属性堆叠"系统。
3. **Capability 三件套拆分**：接口（`IPlayerStat`）/实现（`PlayerStatCapability`）/提供者（`PlayerStatProvider implements ICapabilitySerializable`），并单独放 `registry/stat/` 做注册与事件（`ModCapabilities`+`ModEvents`）；这是 Forge 1.20.1 附加玩家数据的标准骨架。
4. **临时缓存 + 复活回填**：死亡时把 NBT 存静态 map、复活时回填（`PlayerStatEvents.java:37-69`），比 `copyOnDeath` 更可控，且能配合配置开关。
5. **网络包手写编码 + 常量长度上限**：`StatSyncPacket` 用 `writeEnum/writeFloat/writeResourceLocation` 显式编码，字段变更时不易静默错位；小 mod 单包即可，无需框架。
