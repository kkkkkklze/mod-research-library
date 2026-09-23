# FoggyHillside/End-s-Delight 源码分析报告

## 1. 基本信息

- Mod 名：End's Delight（末地乐事）/ mod_id：`ends_delight` / 作者：FoggyHillside（credits 含 GamingeckeSpace、Lobster0228 等）
- 目标：**NeoForge 1.21.1**（neo_version 21.1.219，`gradle.properties`；单模块，无 fabric 分支）
- 构建：`net.neoforged.gradle.userdev` 7.0.145（ModDevGradle）、Parchment 1.21/2024.07.28、Java 21、`options.encoding='UTF-8'`
- 许可证：MIT（`gradle.properties: mod_license`）
- 编译依赖（谁是 API）：**Farmer's Delight 1.3.1+（`curse.maven:farmers-delight-398521:8007613`，`neoforge.mods.toml` 中为 required）**；代码大量直接 extends/implements FD 的 `ConsumableItem`、`DrinkableItem`、`KnifeItem`、`AbstractStoveBlock(Entity)`、`ModDamageTypes`、`FoodValues`、`TextUtils`
- 快照说明：git 跟踪 376 文件，但本地工作区仅有 37 个 java + `META-INF/neoforge.mods.toml`（assets/data 未在本地检出，故未核对其 JSON 内容）

## 2. 源码规模与包结构

- **37 个 `.java`，2084 行**（实测命令输出）
- 包结构（`src/main/java/cn/foggyhillside/ends_delight/`）：`block`(5) + `block/entity`(1)、`item`(7)、`registry`(10)、`event`(1) + `event/loot`(6)、`utility`(1)、`worldgen`(1)、`client/renderer`(1)、根包 3（EndsDelight / FoodList / EDCommonConfigs / EndermanGristleTransport）
- 最大文件：`block/DragonLegBlock.java`(270)、`registry/ModItems.java`(160)、`registry/ModMaterials.java`(136)、`block/ChorusSucculentBlock.java`(120)、`utility/Utils.java`(96)、`item/EndermanGristleItem.java`(87)、`registry/ModCreativeTab.java`(83)

## 3. 入口与注册

主类 `cn/foggyhillside/ends_delight/EndsDelight.java:21-35`——构造注入总线，6 个 DeferredRegister 一次挂载，客户端渲染器放在 `@EventBusSubscriber(Dist.CLIENT)` 内嵌类：

```java
@Mod(EndsDelight.MODID)
public class EndsDelight {
    public static final String MODID = "ends_delight";
    public EndsDelight(IEventBus modEventBus, ModContainer modContainer) {
        TILES.register(modEventBus); BLOCKS.register(modEventBus); FEATURES.register(modEventBus);
        ITEMS.register(modEventBus); CREATIVE_MODE_TABS.register(modEventBus); LOOT_MODIFIERS.register(modEventBus);
        modContainer.registerConfig(ModConfig.Type.COMMON, EDCommonConfigs.SPEC);
    }
    @EventBusSubscriber(modid = MODID, value = Dist.CLIENT)
    public static class ClientSetupEvents { /* registerBlockEntityRenderer(END_STOVE, EndStoveRenderer::new) */ }
}
```

注册全部使用 **NeoForge 原生 DeferredRegister**：`DeferredRegister.createItems/createBlocks`（`registry/ModItems.java:18`、`ModBlocks.java:19`）、`DeferredRegister<Feature<?>>`（`ModBiomeFeatures.java:14`）、`GLOBAL_LOOT_MODIFIER_SERIALIZERS`（`ModLootModifiers.java:13`）；无 Architectury/Registrate。

## 4. 核心系统

1. **双格「盛宴」方块 `block/DragonLegBlock.java`（学习价值最高）**：`PART = BlockStateProperties.BED_PART` + `SERVINGS = IntegerProperty 0..6`；四朝向 × HEAD/FOOT 各 7 个 VoxelShape 数组（`SHAPES_NORTH_HEAD`…）按 servings 索引 `getShape`；`useItemOn` 只接受 `Items.BOWL` → `takeServing` **同时**更新 pairPos 与自身 SERVINGS（`:250-268`），servings==0 时 `destroyBlock`；`updateShape` 校验伙伴块朝向（`:177-183`）、`playerWillDestroy` 创造模式连带清除、`getStateForPlacement` 需前方可替换、`PushReaction.DESTROY`。
2. **末地烤炉 `block/EndStoveBlock(Entity)`**：继承 FD 的 `AbstractStoveBlockEntity`，只覆写适配点——`getInventorySlotCount()=6`、`getStoveItemOffset(int)` 返回 6 个 `Vec2` 偏移、`particleTick` → `addSmokeParticles()`（按 `FACING` 的 `get2DDataValue()%2` 交换 x/y 并投影到世界坐标，`:33-45`）；配方类型直接用 `RecipeType.CAMPFIRE_COOKING`。
3. **战利品注入（Global Loot Modifier）**：6 个 `LootModifier` 子类（`event/loot/*Modifier`）编码方式统一为 `Suppliers.memoize(() -> RecordCodecBuilder.mapCodec(inst -> codecStart(inst).and(BuiltInRegistries.ITEM.byNameCodec().fieldOf("item").forGetter(m -> m.item)).apply(inst, X::new)))`，`doApply` 里 `generatedLoot.add(new ItemStack(item, 2))`；数据侧只需写 JSON 条件（见 `DragonLegAdditionModifier.java:20-37`）。
4. **末影人传送食物（配置驱动的 player 传送）**：`item/EndermanGristleItem.java` 继承 FD `ConsumableItem`，`finishUsingItem` 中最多 16 次尝试，先过 `EventHooks.onChorusFruitTeleport`（可被其他 mod 取消），再调用自研 `EndermanGristleTransport.randomTeleport`（复刻紫颂果落地：向下找 `blocksMotion` 方块、`noCollision` 且不浸液才算成功，失败回滚原坐标；玩家且非创造时按 `getHealth() < 0.3*maxHealth` 分档扣血 `*1.5f` 或 `*damage`，`:15-68`）；成功给 20 tick 冷却、广播实体事件 46。
5. **世界生成**：`worldgen/ChorusSucculentFeature extends Feature<CountConfiguration>`，在 ±8 范围内按 `Heightmap.Types.WORLD_SURFACE` 取高度，随机 `SUCCULENT=1..3` 后 `canSurvive` 才 `setBlock(..., 2)`；注册于 `ModBiomeFeatures`，区块/生物群系 JSON 侧配置（本地未含）。
6. **配置驱动 mob 白名单**：`EDCommonConfigs.java:25-29`（`allowedMobs` 列表默认 enderman/endermite/ender_dragon/shulker）供 `event/DragonToothKnifeEvent` 判断龙牙刀额外伤害，`GRISTLE_TELEPORT/TELEPORT_RANGE_SIZE(24,1..32)/TELEPORT_MAX_HEIGHT(32,1..64)` 供传送食物读取。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**自研包（无 `Packet`/`PayloadRegistrar` 命中）
- 数据驱动：原版 JSON（recipes/loot_modifiers/tags/worldgen），本地快照未包含资源文件（未确认具体条目）；配置项 `allowedMobs` 使用资源 id 字符串列表，属"配置即数据"的做法
- 配置：NeoForge `ModConfigSpec`（COMMON，静态块构建 + `SPEC` 持有），全部 4 个键都真实影响玩法
- datagen：build.gradle 有 `data` run（输出 `src/generated/resources`）与 `sourceSets.main.resources { srcDir 'src/generated/resources' }`，但源码中**无 `GatherDataEvent`/`DataGenerator` 类**（未确认是否曾在历史版本使用）

## 6. Mixin

**无**。全仓库 `grep -rn "@Mixin"` 无命中，resources 下也无 mixins.json——兼容 FD 的方式完全是继承 + API 调用（`ConsumableItem`、`AbstractStoveBlockEntity`、`ModDamageTypes.getSimpleDamageSource`），是"友好附属"的典型范式。

## 7. 值得学的 5 条具体做法

1. 附属 mod 只继承父 mod 的基类、不 mixin：`EndStoveBlockEntity extends AbstractStoveBlockEntity` 仅覆写 `getInventorySlotCount`/`getStoveItemOffset`/`particleTick`（`block/entity/EndStoveBlockEntity.java:14-66`）；适用于给 FD/Create 等大 mod 写附属。
2. 双格大餐方块用「属性数组索引 VoxelShape」表达 6 档残余量 × 4 朝向（`block/DragonLegBlock.java:42-120`），状态只存 `PART/SERVINGS/FACING`，避免自定义 BlockEntity。
3. 全局战利品注入统一模板：`codecStart(inst) + BuiltInRegistries.ITEM.byNameCodec().fieldOf("item")`，产出数量写死在 `doApply`，JSON 只写条件（`event/loot/*.java`、`registry/ModLootModifiers.java`）。
4. 玩法高风险行为（传送/扣血）走配置 + 平台事件双保险：先 `EventHooks.onChorusFruitTeleport`（允许别人取消）再自己执行（`item/EndermanGristleItem.java`，`EndermanGristleTransport` 失败回滚）。
5. 「配置读值就地取用」而非传参：静态 `EDCommonConfigs.X.get()` 在物品/事件类内直接读取，减少分发层（`EDCommonConfigs.java`，注意仅服务端/COMMON 配置）。
