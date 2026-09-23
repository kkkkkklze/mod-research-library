# baiyin1223/Kaleidoscope_bloodwine 源码分析报告

## 1. 基本信息
- Mod 名：Kaleidoscope Bloodwine（森罗酒馆血酒附属）；mod_id：`kaleidoscope_bloodwine`；作者 baiyin1223；版本 1.1.0；许可证 MIT。
- 目标：**Forge 1.20.1**（`gradle.properties`: `minecraft_version_range=[1.20.1,1.20.2)`、`forge_version=47.3.0`、Java 17、Parchment `2023.08.20-1.20.1`；README 另称有 neoforge 1.21.1 分支，本快照不含）。
- Gradle 插件：`net.minecraftforge.gradle [6.0.16,6.2)` + `org.parchmentmc.librarian.forgegradle 1.+` + `org.spongepowered.mixin 0.7.+`；单模块工程，`sourceSets.main.resources { srcDir 'src/generated/resources' }`（预留 datagen 输出目录）。
- 编译依赖：**`fg.deobf(files("libs/kaleidoscopetavern-1.2.0.jar"))`——主模组森罗酒馆以本地 jar 引入**（非 maven）；`compileOnly fg.deobf("de.teamlapen.vampirism:Vampirism:1.20.1-1.10.11:api")`（Vampirism 仅编译期 API）。依赖声明在 `mods.toml`：`kaleidoscope_tavern` mandatory+AFTER，`vampirism` optional(`mandatory=false`)+AFTER。

## 2. 源码规模与包结构
实测 17 个 `.java`，1646 行。包（`src/main/java/com/github/kaleidoscope_bloodwine/`）：`init/` 4（`ModBlocks`/`ModItems`/`ModFluids`/`ModCreativeTabs`）、`item/` 5、`mixin/` 2、`block/` 1、`blockentity/` 1、`fluid/` 1、`compat/` 1、`event/` 1、根 1。
最大文件：`compat/VampirismCompat.java` 359、`mixin/PressingTubBlockEntityMixin.java` 156、`block/BloodDrinkBlock.java` 144、`init/ModBlocks.java` 141、`item/HunterDrinkBlockItem.java` 111。
快照只含 `kaleidoscope_bloodwine.mixins.json` 与 `META-INF/mods.toml`，无 assets/data（模型贴图不在库内，未确认）。

## 3. 入口与注册
`@Mod(KaleidoscopeBloodwine.MOD_ID) public class KaleidoscopeBloodwine`（`KaleidoscopeBloodwine.java:12`），构造器取 `FMLJavaModLoadingContext.get().getModEventBus()` 后 `ModBlocks.BLOCKS / BLOCK_ENTITIES / ModItems.ITEMS`（均为 `DeferredRegister.create(...)`）各自 `.register(modBus)`；`modLoc(String)` 生成 `ResourceLocation`。
- 方块：`ModBlocks` 注册 11 个血酒方块（`BloodDrinkBlock(4|3, VoxelShape...)`）+ 1 个 `LiquidBlock`（`blood`）+ 1 个 `BlockEntityType`（`drink`，11 个方块共用 `BloodDrinkBlockEntity`）。形状数组（`WINE_SHAPES`/`VODKA_SHAPES`/`FLASK_SHAPES`…）按数量提供多段 `VoxelShape`。
- 流体：`ModFluids` 用 `@Mod.EventBusSubscriber(bus=MOD)` + `RegisterEvent`（`event.register(Keys.FLUID_TYPES/Keys.FLUIDS, helper -> ...)`），`RegistryObject.create(id, registry)` 手工建对象引用 + `ForgeFlowingFluid.Properties(..., bucket)`；`fluid/BloodFluidType` 继承 `FluidType`，在 `initializeClient` 里用 `IClientFluidTypeExtensions` 提供 `block/<name>_still|_flow` 贴图。
- 物品：11 个血酒用自定义 `BloodDrinkBlockItem`（继承主模组 `BottleBlockItem`），血桶复用主模组 `JuiceBucketItem`。
- 创造栏：不建新栏，`ModCreativeTabs` 监听 `BuildCreativeModeTabContentsEvent`，比对 `ResourceKey.create(Registries.CREATIVE_MODE_TAB, kaleidoscope_tavern:tavern_main)` 后 `event.accept(BottleBlockItem.getMaxLevelDrink(item))`（只放满级酒）。

## 4. 核心系统
1. **血酒方块（复合方块实体替代品）** `block/BloodDrinkBlock.java` + `blockentity/BloodDrinkBlockEntity.java`：因为 `BloodDrinkBlockEntity` 不继承主模组的 `DrinkBlockEntity`，凡是 `instanceof DrinkBlockEntity` 的分支都必须重写——`tryIncreaseCount`（堆叠时 `be.addItem`）、`use`（空手 `removeItem` + `ItemHandlerHelper.giveItemToPlayer` + 按 count 递减/移除方块）、`onProjectileHit`（遍历 4 格取 `maxBrewLevel` → `DrinkBlockItem.makeThrownPotion`）、`getDrops`（从 `LootContextParams.BLOCK_ENTITY` 取出全部 `ItemStack`）。方块实体内部是 `NonNullList.withSize(4)` + `ContainerHelper.loadAllItems/saveAllItems`，`refresh()` = `setChanged()` + `level.sendBlockUpdated(..., 3)`，配 `getUpdatePacket/getUpdateTag` 做客户端同步。
2. **Vampirism 可选兼容层** `compat/VampirismCompat.java`：对外只暴露 `isLoaded()`（`ModList.get().isLoaded`）与转发方法，**所有 Vampirism 类引用集中在 `private static class Impl` 内**，用双检锁 + `volatile` 懒创建，保证未装 Vampirism 时不触发类加载/`ClassNotFoundException`；实现内用 `VampirismAPI.getFactionPlayerHandler(player).map(isInFaction(VAMPIRE_FACTION/HUNTER_FACTION))`、`getVampirePlayer(player).ifPresent(vp -> vp.drinkBlood(10, 0.5f, context))`，`IDrinkBloodContext` 用匿名类只实现 `getStack()`；防晒效果不走 API 类而是 `ForgeRegistries.MOB_EFFECTS.getValue(vampirism:sunscreen)` 按 ID 取。
3. **brewLevel 驱动的效果分级**：`applySunscreenEffect/applyHealthBoostEffect/applyStrengthEffect` 都是 `switch(brewLevel) case 3..6` 给 (amplifier, duration秒)，boss 级酒在 `onDrinkEternalNight` 里 `drinkBlood(100, 1.0f, ...)` 模拟"喝饱"；`getPoisonDuration/getNauseaDuration` 同行做负面效果分级。
4. **事件式饮用处理** `event/DrinkEventHandler.java`：`@Mod.EventBusSubscriber(bus=FORGE)` 监听 `LivingEntityUseItemEvent.Finish`，服务端过滤 → 判定 `getBloodWineItems()`（**懒初始化的 `Set.of(...)`**，避免类加载时 `RegistryObject.get()` 空指针）→ `VampirismCompat.isVampire(player)` 后 `onDrinkBloodWine(player, stack, BottleBlockItem.getBrewLevel(stack))`。
5. **与主模组酿造链路的 mixin 衔接**：`mixin/BarrelBlockEntityMixin.java` 针对 KT 1.2.0 重写后的 `doTapExtract`——`@Inject(HEAD)` 保存 `brewLevel` 与输出槽快照，`@Inject(TAIL)` 检查下方方块是否为 `BloodDrinkBlockEntity` 且全空，再 `BottleBlockItem.setBrewLevel(输出, 保存等级)` + `bloodDrink.addItem(...)` + `refresh()`（注释写明新 `placeBottleResult()` 只写 `DrinkBlockEntity`，故附属方块被跳过）；`mixin/PressingTubBlockEntityMixin.java` 在 `playSuccessPressEffect(stack, ci)`/`playFinishedPressEffect` 的 HEAD 取消，用 `DustParticleOptions(0.8,0.05,0.05)` 替代原版 `RAIN` 粒子并重放 `SLIME_BLOCK_FALL`/`HONEY_BLOCK_HIT` 音效，判定血流体时同时兼容本 mod 的 `ModFluids.BLOOD` 与 `vampirism:blood`。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无自定义包；同步靠 `BlockEntity.getUpdatePacket/getUpdateTag`。
- 数据驱动：无（无 reload listener、无 `data/` JSON 逻辑，配方等内容未在快照中体现）。
- 配置：**无**（没有 config 类，`mods.toml` 也无 config 项），所有数值硬编码在 item/compat 类里。
- datagen：无生成器代码（仅 `build.gradle` 预留了 `src/generated/resources`）。

## 6. Mixin
配置：`src/main/resources/kaleidoscope_bloodwine.mixins.json`，`package: com.github.kaleidoscope_bloodwine.mixin`、`compatibilityLevel: JAVA_17`、`refmap: kaleidoscope_bloodwine.refmap.json`；在 `mods.toml` 用 `mixins=[{config=...}]` 登记，且 jar manifest 里也写 `MixinConfigs`。
- `BarrelBlockEntityMixin` → `@Mixin(BarrelBlockEntity.class)`，`@Inject(method="doTapExtract", at=HEAD/TAIL, remap=false)`，`@Shadow(remap=false) private int brewLevel`，`@Unique` 前缀字段 `bloodwine$savedBrewLevel`/`bloodwine$savedOutput`。
- `PressingTubBlockEntityMixin` → `@Mixin(PressingTubBlockEntity.class) extends BlockEntity`（需 dummy 构造器 `super(null, BlockPos.ZERO, null)` 过编译），`@Shadow private FluidTank fluid`，注入 `playSuccessPressEffect`、`playFinishedPressEffect` 的 HEAD（cancellable）。
- **注意**：配置里第三个条目 `BarrelBlockEntityAccessor` 在仓库源码中不存在（`grep` 只命中 mixins.json），猜测为遗留声明，装 mixin 时会因找不到类而报错，使用时需删掉或补上。

## 7. 值得学的 5 条具体做法
1. **可选依赖的"内部 Impl 类"隔离**：`VampirismCompat` 外层无任何 Vampirism import，`Impl` 内部才用全限定名（`compat/VampirismCompat.java:133`）——比 `@Optional`/反射更简洁，是附属 mod 兼容别的 mod 的标准姿势。
2. **懒初始化注册表集合**：`static Set<Item> BLOOD_WINE_ITEMS` 在首次事件时 `Set.of(RegistryObject.get())`（`event/DrinkEventHandler.java:26`），规避静态初始化早于注册完成导致的 NPE。
3. **不建新创造栏，向主模组分类追加**：`BuildCreativeModeTabContentsEvent` + `ResourceKey` 比对主模组 tab（`init/ModCreativeTabs.java:22`）——附属模组的正确接入方式。
4. **手工 4 格同步方块实体**：`NonNullList.withSize(4)` + `ContainerHelper.save/loadAllItems` + `refresh()`（`sendBlockUpdated(...,3)`）+ `getUpdatePacket/getUpdateTag`（`blockentity/BloodDrinkBlockEntity.java`）——小容量展示型方块的最省事同步模板。
5. **针对主模组内部重构写"HEAD 快照 + TAIL 补写"mixin**：`BarrelBlockEntityMixin` 在 HEAD 存下 `brewLevel`/输出，在 TAIL 判断目标方块实体为空后补写（`mixin/BarrelBlockEntityMixin.java:48`），并且注释里标注了主模组版本（KT 1.2.0）改动原因——升级主模组时的可维护写法。
