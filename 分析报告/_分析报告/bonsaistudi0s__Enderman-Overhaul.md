# Enderman Overhaul 源码分析报告

## 1. 基本信息

- Mod 名：Enderman Overhaul；mod_id：`endermanoverhaul`；作者：Alex Nijjar、Joosh（`src/main/resources/META-INF/neoforge.mods.toml`）
- 目标版本：MC 1.21.1 / NeoForge 21.1.90（`gradle.properties`）
- Gradle 插件：`net.neoforged.moddev` 2.0.62-beta（ModDevGradle）+ `maven-publish`；Java toolchain 21
- 许可证：ARR（All Rights Reserved）
- 编译依赖（关键）：`resourcefullib 3.0.11`（注册/网络/创造标签框架）、`resourcefulconfig 3.0.7`（配置）、`geckolib 4.7`（模型动画）、`mekanism 10.7.8.70`（含 additions，做兼容）。即本 mod 自身**不是**库，而是 Resourceful Lib 的消费者。

## 2. 源码规模与包结构

- 96 个 `.java`，共 8012 行（`find . -name '*.java' -exec wc -l {} +`）
- 包结构（第 3 层）：`common/entities` 19、`common/entities/projectiles` 9、`common/items/pearls` 8、`common/registry` 7、`datagen/provider/server` 4、`common/entities/pets` 4、`client/renderer/base` 4、`client/renderer` 4、`mixins/common` 3、`client/config/info` 3
- 最大文件：`common/entities/base/BaseEnderman.java` 540 行、`common/entities/pets/BasePetEnderman.java` 513、`common/entities/projectiles/EnderBullet.java` 361、`common/registry/ModEntityTypes.java` 301、`common/entities/CoralEnderman.java` 296、`datagen/provider/server/ModLootTableProvider.java` 229
- 注意：仓库内 `src/main/resources` 仅含 `endermanoverhaul.mixins.json` 与 `neoforge.mods.toml`，**assets/data 资源不在本仓库**（未确认原因，可能是资产单独托管），资源见 `datagen` 生成逻辑。

## 3. 入口与注册

主类 `src/main/java/tech/alexnijjar/endermanoverhaul/EndermanOverhaul.java:14`：

```java
@Mod(EndermanOverhaul.MOD_ID)
public class EndermanOverhaul {
    public static final Configurator CONFIGURATOR = new Configurator(MOD_ID);
    public EndermanOverhaul(IEventBus bus) {
        CONFIGURATOR.register(EndermanOverhaulConfig.class);
        NetworkHandler.init();
        ModDataComponents.DATA_COMPONENT_TYPES.init();
        ModBlocks.BLOCKS.init();
        ModArmorMaterials.ARMOR_MATERIALS.init();
        ModItems.ITEMS.init();  ModItems.TABS.init();
        ModEntityTypes.ENTITY_TYPES.init();
        ...
```

- 注册框架：Resourceful Lib 的 `ResourcefulRegistries.create(BuiltInRegistries.X, MOD_ID)`，每个注册类在构造尾部调用 `.init()`（`common/registry/`）。
- 分组注册很值得抄：`ModEntityTypes.java:29-31` 用 `ResourcefulRegistries.create(ENTITY_TYPES)` 派生 `ENDERMEN`、`PEARLS` 子注册表，`ModItems.java:26-29` 派生 `PEARLS`、`SPAWN_EGGS`、`TABS`，便于批量遍历/建标签。
- 实体属性与生成点用 `@EventBusSubscriber(modid=..., bus=MOD)` + `EntityAttributeCreationEvent` / `RegisterSpawnPlacementsEvent`（`ModEntityTypes.java:243`、`:268`）。

## 4. 核心系统

1. **Enderman 变体继承体系**（`common/entities/base/BaseEnderman.java:53`）：`BaseEnderman extends EnderMan implements GeoEntity`，把 20+ 变体差异全部抽成可覆写方法（`canTeleport/getVisionRange/hasParticles/getCustomParticles/getHitEffect/getAreaEffect/getCarriableBlockTag/speedUpWhenAngry/isProvokedByEyeContact` 等，行 102-197），子类只覆写差异项，例如 `CoralEnderman.canTeleport()` 返回 `isCreepy() || getAirSupply() <= 20`。新变体 ≈ 一个 100-200 行子类。
2. **仇恨/凝视 AI（内嵌 Goal 类）**：`BaseEnderman` 内部类 `EndermanFreezeWhenLookedAt`、`EndermanLookForPlayerGoal`、`EndermanTakeBlockGoal`、`EndermanLeaveBlockGoal`（行 357-539）把原版 EnderMan.Goal 复制进来以支持可配置参数；`EndermanLookForPlayerGoal` 里有 `aggroTime=adjustedTickDelay(5)` 与 `teleportTime++ >= adjustedTickDelay(30)` 的两段式"凝视→延迟仇恨→追击传送"节拍，用 `adjustedTickDelay` 保证难度自适应。
3. **跨变体 AI 行为的 mixin 补丁**：`mixins/common/EnderManMixin.java` 三处 `@Inject`——`aiStep` HEAD 取消原版逻辑（仅当有自定义粒子时）、`setTarget` TAIL 移除 `SPEED_MODIFIER_ATTACKING` 以关闭"愤怒加速"、`isLookingAtMe` HEAD 返回 false。所有注入方法名带 `endermanoverhaul$` 前缀。
4. **投掷珍珠 / 绑定实体**：`common/items/pearls/SoulPearlItem.java` 用数据组件 `ModDataComponents.BOUND_ENTITY` 存实体 id（`networkSynchronized(ByteBufCodecs.VAR_INT)`，**刻意不持久化**，注释说明 id 不跨存档），`inventoryTick` 每 100 tick 校验一次绑定实体是否失效；`EndermanOverhaulClient.getLevel()` 被服务端共享类引用（谨慎点，客户端类被 common 引用）。
5. **宠物 enderman**：`common/entities/pets/BasePetEnderman.java:63` 同时 `implements GeoEntity, OwnableEntity`，复制原版 Wolf 的 `DATA_OWNERUUID_ID` 同步数据 + `setOwnerUUID`、`EndermanHurtByTargetGoal`，并提供 `(type, level, owner)` 构造器便于直接生成已驯服个体。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：Resourceful Lib 的 `Network`（`common/network/NetworkHandler.java:9`），`new Network(ResourceLocation(...), 1)` + `channel.register(TYPE)`。仅有 1 个包：`ClientboundFlashScreenPacket`（`network/messages/ClientboundFlashScreenPacket.java`），实现 `ClientboundPacketType.handle()` 返回 `Runnable`，用 `DatalessPacketType` 表示无载荷；发送点 `ModUtils.teleportTarget` 中 `CHANNEL.sendToPlayer(new ClientboundFlashScreenPacket(), player)`（受player 传送时闪屏）。
- 数据驱动：无自定义 JSON 类型/编解码器；生成点、标签、掉落全部走 datagen。
- 配置：Resourceful Config，注解式（`common/config/EndermanOverhaulConfig.java`）：`@Config("endermanoverhaul")` + `@ConfigInfo.Provider(EndermanOverhaulConfigInfo.class)`（客户端 UI 元数据在 `client/config/info/`），字段用 `@ConfigEntry(id=..., type=EntryType.BOOLEAN/FLOAT, translation=...)` + `@Comment`，静态字段直接读（`EndermanOverhaulConfig.spawnCoralEnderman`）。约 25 项：一个总开关 `allowSpawning` + 每种变体一个 `spawnXxxEnderman`。
- datagen：`datagen/EndermanOverhaulDataGenerator.java` 在 `GatherDataEvent` 注册 6 个 provider（Lang、ItemModel、LootTable、BlockTag、ItemTag、EntityTypeTag），输出到 `src/generated/resources`（build 脚本加为 resource srcDir）。

## 6. Mixin

- 配置：`src/main/resources/endermanoverhaul.mixins.json`（`package: tech.alexnijjar.endermanoverhaul.mixins`，`compatibilityLevel: JAVA_21`，`injectors.defaultRequire=1`，`client: []`），通过 `[[mixins]] config = ...` 在 mods.toml 声明。
- `mixins/common/EnderManMixin.java`：`EnderMan#aiStep`(HEAD, cancellable)、`EnderMan#setTarget`(TAIL)、`EnderMan#isLookingAtMe`(HEAD，穿 HoodItem 时返回 false)；用 `(Object) this instanceof BaseEnderman` 兼容写法避开跨 mixin 类型检查。
- `mixins/common/IronGolemMixin.java`：`IronGolem#lambda$registerGoals$0`(HEAD) —— 直接注入 lambda 合成方法名，阻止铁傀儡攻击 `PassiveEnderman`/`PetEnderman`。
- `mixins/common/LivingEntityMixin.java`：`LivingEntity#blockUsingShield`(TAIL)，手持 `CORRUPTED_SHIELD` 时按 75% 概率把攻击者传送走并造成 2 点摔落伤害；`attacker.getType().is(Tags.EntityTypes.TELEPORTING_NOT_SUPPORTED)` 做前置排除。

## 7. 值得学的 5 条具体做法

1. **变体差异 = 可覆写 getter，而不是 if-else**：`common/entities/base/BaseEnderman.java:102-197`，20+ 变体共享一套 AI，新增变体只需覆写几个方法。适用：多生物/多工具的"家族式"实体。
2. **子注册表分组**：`ResourcefulRegistries.create(已经存在的注册表)` 派生子表（`ModEntityTypes.java:29-31`、`ModItems.java:26-29`），一石二鸟拿到"全部物品"与"仅珍珠"两类遍历入口。
3. **把原版内部 Goal 类内联到基类**，换取参数可配置化：`BaseEnderman.java:357-425`（取放方块、凝视），比 mixin 原版 Goal 更可控。
4. **数据组件存非持久运行时状态**：`ModDataComponents.java` 注释明确 `networkSynchronized` 而**不** `persistent`，因为实体 id 不跨存档；配 `inventoryTick` 定期校验失效（`SoulPearlItem.java`）。
5. **mods.toml 用 `$placeholder` + Gradle `expand` 注入版本号**：`build.gradle.kts` 的 `processResources { filesMatching("META-INF/neoforge.mods.toml") { expand(properties) } }`，版本只在 `gradle.properties` 维护一处；moddev 的 data run 用 `--all --output src/generated/resources --existing src/main/resources`。

## 8. 公开 API

非库模组，无对外 API 包。可被外部模组复用的稳定入口：`common/entities/base/BaseEnderman.java`（`isProvokedByEyeContact()/canTeleport()/getCarriableBlockTag()/getAreaEffect()` 全是 public 扩展点）与实体类型注册（第三方若继承需自行注册 EntityType）。
