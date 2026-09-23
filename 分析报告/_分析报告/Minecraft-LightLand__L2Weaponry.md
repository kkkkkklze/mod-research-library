# Minecraft-LightLand / L2Weaponry 源码分析

## 1. 基本信息

- Mod 名：L2Weaponry；mod_id `l2weaponry`（`gradle.properties` 与 `src/main/resources/META-INF/neoforge.mods.toml`，属性由 `ProcessResources` 的 `expand` 注入）；作者 `lcy0x1`；mod 版本 **3.1.4**
- 目标环境：MC **1.21 / 1.21.1** + **NeoForge 21.1.197**，Java 21；`loaderVersionRange=[2,)`
- 构建：**ModDevGradle `2.0.80`**（`build.gradle:8`，不是 ForgeGradle）+ curseforgegradle + minotaur + gradle-secrets；parchment MC1.20.6/2024.06.02；`sourceSets { client/server/data/common }` 声明但实质只用 main
- 许可证：LGPL-2.1
- 依赖（`build.gradle:126-160`）：**l2core 3.0.8+11**、l2serial 3.0.9、l2library 3.0.4、l2tabs、l2menustacker、l2itemselector、l2modularblocks、**l2damagetracker 3.0.2**、l2complements 3.1.2、modulargolems、Registrate `MC1.21-1.3.0+50`；`jarJar` 内嵌 `dev.xkmc:cataclysm_mux`；大量 `curse.maven:` 软兼容（暮色、Undergarden、Ice and Fire、ATM、L_Ender's Cataclysm…）。`libs/` 放**带 -sources 的**同系列 jar（l2core/l2library/l2serial/l2tabs/l2menustacker/l2itemselector/l2modularblocks/l2damagetracker），说明本地开发直接对源码调试——**这是该系列统一构建在 L2Library/L2Core 之上的方式：系列内每个库独立发版，业务 mod 平铺引用，`mavenLocal()` + flatDir 兜底**

## 2. 源码规模与包结构

`src/main` **155 个 .java / 8417 行**（含 test 共 167）。包：`content/{capability, client, enchantments, entity, item/{base,legendary,types}}`、`events`、`init/{data, materials, registrate}`、`compat/{atm, cataclysm, dragons, twilightforest, undergarden}`、`mixin`。

最大文件：`init/data/LWRecipeGen.java`(339)、`content/entity/BaseThrownWeaponEntity.java`(287)、`init/data/LWConfig.java`(169)、`init/materials/LWGenItem.java`(163)、`content/item/base/BaseShieldItem.java`(157)、`init/data/LangData.java`(150)、`LWToolTypes.java`(143)。

## 3. 入口与注册

`init/L2Weaponry.java:46` `@Mod(MODID)` + `@EventBusSubscriber(bus = MOD)`；**同时持有两套注册器**（3.x 的新旧过渡，第 52-55 行）：

```java
public static final Reg REG = new Reg(MODID);                    // l2core 轻量注册器
public static final L2Registrate REGISTRATE = new L2Registrate(MODID);
public static final PacketHandler HANDLER = new PacketHandler(MODID, 1);  // l2serial
```
构造函数（第 57-66 行）仅做四件事：`LWItems/LWEntities/LWDamageTypeGen/LWConfig.init/LWEnchantments.register()`、`ItemUseEventHandler.LIST.add(new LWClickListener())`、按 `ModList.isLoaded("modulargolems")` 注册 `GolemCompat`。`setup` 里以优先级 4000 注册 `LWAttackEventListener`（第 74 行）；`modifyAttributes` 通过 `EntityAttributeModificationEvent` 给玩家加 `SHIELD_DEFENSE/REFLECT_TIME` 两个自定义属性。

数据注册的分层很清晰：`LWItems` 用 `L2Registrate.simple(...Registries.ATTRIBUTE)`、`buildL2CreativeTab(...)`、`item(...)`；`LWEntities.java:17-19` 用 `AttReg.of(REG)` 注册玩家能力 `PLAYER = REG.player("shield", LWPlayerData.class, ...)`；`LWEnchantments.java:16` 用 `EnchReg.of(REG, REGISTRATE)` 注册附魔；`LWItems.java:69-76` 用 `DCReg.of(REG)` 注册 DataComponent（`reequip/hit_count/last_hit_time/blocked_damage/last_target/kill_count`）——**注册原语按游戏数据类型拆分成 Reg / AttReg / EnchReg / DCReg 四个门面**。

## 4. 核心系统

1. **材料 × 类型矩阵生成**（`init/materials/LWGenItem.java:28-51`）：`generate(ILWToolMats...)` 双重循环生成 `ItemEntry[][]`，每件武器一行链内完成 item 工厂（按材质 tier/`type().getToolConfig().sup().get(...)`）、`fireRes`、`asOptional()`、tag(`type.tag + matTag`)、模型、创造栏（可带默认附魔）、`clientExtension(WeaponBEWLR)`、lang。材质来源统一为 `IMatToolType`（`L2DamageTracker` 的 `VanillaMats`/`LCMats`）——`LWToolMats.java:16-25` 枚举即注册表。
2. **武器类型即属性定义**（`init/materials/LWToolTypes.java:27-37`）：`enum ... implements ITool`，每项带 tag、`RawToolFactory`、damage/speed/range、customModel、默认附魔；`configure(ItemAttributeModifiers.Builder,...)`（第 63 行）里决定盾类武器改用 `SHIELD_DEFENSE`。
3. **玩家能力数据**（`content/capability/LWPlayerData.java:15-48`）：`extends PlayerCapabilityTemplate<T>`，`@SerialField` 字段 + 手写 `network.toClient(sp)` 推送（第 35 行）；盾值随 tick 按 `getRecoverRate` 衰减。
4. **伤害管线**（`events/LWAttackEventListener.java:27-70`）：实现 `AttackListener` 的 `onCreateSource/setupProfile/onAttack`（第 33/56/65 行），把近战与投掷武器（`BaseThrownWeaponEntity`）统一到 l2damagetracker 事件里做 source 改写与免疫判断。
5. **外部 mod 兼容分发**（`compat/CompatDispatch.java:23-34`）：抽象类自注册进静态 `LIST`，`register()` 内逐个 `ModList.get().isLoaded(...)` 条件实例化 TFCompat/UGCompat/DragonCompat/ATMCompat/CataCompat；子类只需实现 `values()` 返回 `ILWToolMats[]`，即"给武器矩阵追加一批材质"。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`new PacketHandler(MODID, 1)`（来自 l2serial，非 l2library 的 `PacketHandlerWithConfig`）；能力同步走 l2core 的 `PlayerCapabilityNetworkHandler`。
- 数据生成：`REGISTRATE.addDataGenerator(ProviderType.LANG/RECIPE/BLOCK_TAGS/ITEM_TAGS/ENTITY_TAGS/DATA_MAP, ...)`（`init/L2Weaponry.java:87-92`），并用 `init.addDependency(ProviderType.RECIPE, L2TagGen.ENCH_TAGS)`（第 96 行）处理生成顺序；伤害类型用 `LWDamageTypeGen extends DamageTypeAndTagsGen` 生成 datapack 注册信息（`init/data/LWDamageTypeGen.java:27-41`）；`LWEnchantments.REG.addParent(LCEnchantments.REG)` 复用 l2complements 的附魔注册表。
- 配置：`init/data/LWConfig.java` 用 l2core 的 `ConfigInit` 分 Recipe/Server 两组 ModConfigSpec。
- 额外：`addPackFinders`（`init/L2Weaponry.java:106-138`）通过 `ModFilePackResources` 在 jar 内注册内置资源包 `old_weapon_model` —— 不额外发行资源包文件即可给玩家切换旧模型。

## 6. Mixin

`src/main/resources/l2weaponry.mixins.json`（`compatibilityLevel JAVA_17`，`defaultRequire 1`）：
- `DrownedMixin`(Drowned) `@Inject HEAD performRangedAttack` 可取消：让溺尸投掷其他武器；`DrownedTridentAttackGoalMixin`(内部类 targets) 与客户端 `DrownedModelMixin` 用 MixinExtras `@WrapOperation` 替换 `ItemStack.is` 调用
- `LivingEntityMixin` `@Inject HEAD canFreeze` / `isDamageSourceBlocked`（爪类格挡）
- `PlayerMixin` `@Inject HEAD hurtCurrentlyUsedShield / blockUsingShield / disableShield` 接管自定义盾
- `TargetGoalAccessor` `@Accessor` 暴露目标字段

## 7. 值得学的 5 条做法

1. **注册原语按数据类型拆分**：`Reg / DCReg / AttReg / EnchReg`（l2core）各自一个门面，"什么类型的东西用什么写法"一眼可辨（`init/registrate/LWItems.java:69-76`、`init/registrate/LWEntities.java:17-19`）。
2. **材质 x 类型矩阵 + 行内全自动生成**：新增一把武器=在 `LWToolTypes` 枚举加一行，资源/标签/模型/语言全自动（`init/materials/LWGenItem.java:28-51`）。
3. **兼容模块自注册 + 静态 LIST**：`CompatDispatch` 构造即入表，主类只写条件判断，无 switch（`compat/CompatDispatch.java:23-34`）。
4. **datagen 依赖显式声明**：`init.addDependency(ProviderType.RECIPE, L2TagGen.ENCH_TAGS)` 解决"配方引用 tag 但 tag 尚未生成"的顺序问题（`init/L2Weaponry.java:96`）。
5. **内置资源包切换模型**：用 `AddPackFindersEvent` + 自定义 `PackResources` 读取 jar 内 `resourcepacks/`，实现零额外文件的可选外观（`init/L2Weaponry.java:106-138`）。

## 8. 面向外部 mod 的扩展点

内容 mod；向系列内部提供的复用点：`ILWToolMats` / `ITool` / `IMatToolType` 三层接口（`init/materials/ILWToolMats.java`、`LWToolTypes`、l2damagetracker）让其他 mod 把自己的材质接进武器矩阵；`LWItems.DC` 的 `DCReg` 与 `LWEntities.PLAYER` 的 `AttReg` 可被附属引用；`CompatDispatch.LIST` 是官方认可的第三方接入入口。
