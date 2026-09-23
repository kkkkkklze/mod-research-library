# mortuusars/Horseman 源码分析报告

## 1. 基本信息

- Mod 名：Horseman；mod_id：`horseman`；作者 mortuusars；版本 1.5.13；MIT
- 目标：MC 1.21.1（`minecraft_version_range=[1.21,)`，`supported_minecraft_versions=1.21,1.21.1`）/ **Fabric + NeoForge 双加载器**（`enabled_platforms=fabric,neoforge`）
- 构建：Architectury 体系 —— `architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.7-SNAPSHOT` + `shadow 8.1.1` + `mod-publish-plugin 0.8.4`；三模块 `include("common"/"fabric"/"neoforge")`；Parchment `1.21.1:2024.11.17`
- 依赖：Fabric API 0.102.1+1.21.1 / Fabric Loader 0.16.9；NeoForge 21.1.129；**ForgeConfigAPIPort 21.1.0**；MixinExtras 0.4.1（`compileOnly annotationProcessor(mixinextras-common)` + `implementation(include(mixinextras-neoforge))`）；JEI 19.19.0.220（modCompileOnlyApi）、Jade（仅 runtime，curse id）。无 API 对外输出。

## 2. 源码规模与包结构

98 个 `.java`，5543 行（实测）。`common/src/main/java/io/github/mortuusars/horseman/` 为主体，`fabric/`、`neoforge/` 各 10 个左右的薄壳。包：根（`Horseman/Register/PlatformHelper/Config`）、`mixin/`（**按功能分子包 25 个**）、`world/`（`summoning/` 7 文件、`item/`）、`network/`（`packet/` + `handler/`）、`client/`（4）、`event/`、`advancement/`、`integration/jei/`（3）。
最大文件：`Config.java`(407)、`world/summoning/Summoning.java`(284)、`world/item/CopperHornItem.java`(206)、`Horseman.java`(148)、`fabric/RegisterImpl.java`(141)、`world/summoning/SummoningStorage.java`(139)、`mixin/hitching/HorseInventoryMenuMixin.java`(133)。

## 3. 入口与注册

- NeoForge：`neoforge/.../neoforge/HorsemanNeoForge.java:17` `@Mod(Horseman.ID)`，构造器 `Horseman.init()` → `container.registerConfig(SERVER/COMMON/CLIENT, ...)` → 从 `container.getEventBus()`（`Preconditions.checkNotNull`）逐个 `RegisterImpl.XXX.register(modEventBus)`，共 15 个 `DeferredRegister`（BLOCKS/BLOCK_ENTITY_TYPES/ENTITY_TYPES/ITEMS/MENU_TYPES/RECIPE_TYPES/RECIPE_SERIALIZERS/CRITERION_TRIGGERS/ITEM_SUB_PREDICATES/SOUND_EVENTS/COMMAND_ARGUMENT_TYPES/WORLD_GEN_FEATURES/DATA_COMPONENT_TYPES/PARTICLE_TYPES/CUSTOM_STATS），最后按 `FMLEnvironment.dist == Dist.CLIENT` 调 `HorsemanNeoForgeClient.init`（只注册 `IConfigScreenFactory -> ConfigurationScreen::new`）。
- Fabric：`fabric/.../fabric/HorsemanFabric.java` + `HorsemanFabricClient.java`，`RegisterImpl` 用 Fabric 的 `Registry.register`。
- **统一注册抽象**：`common/.../Register.java` 全部方法标 `@ExpectPlatform`（`dev.architectury.injectables.annotations.ExpectPlatform`），body 为 `throw new AssertionError()`，覆盖 block/blockEntityType/item/entityType/soundEvent/menuType/recipeType/recipeSerializer/criterionTrigger/itemSubPredicate/commandArgumentType/worldGenFeature/dataComponentType/particleType；平台实现见 `fabric/.../fabric/RegisterImpl.java`、`neoforge/.../neoforge/RegisterImpl.java`。同理 `PlatformHelper.java`（`canShear/isModLoaded/isModLoading`）。
- 主类 `Horseman.java` 用**内部静态类分组注册**（`Items.COPPER_HORN`、`RecipeSerializers.COMPONENT_TRANSFERRING`、`SoundEvents.LEASH_BREAK`、`CriteriaTriggers.HORSE_SUMMONED`、`Tags.EntityTypes.*`），另有 `Stats.register()` 特例：先填 `Map<ResourceLocation, StatFormatter>` 再 `Registry.register(BuiltInRegistries.CUSTOM_STAT, ...)` 并 `Stats.CUSTOM.get(location, formatter)`（Horseman.java:100-113）。

## 4. 核心系统

**（1）马匹牵引（Hitching）——接口注入范式**
`common/.../world/HitchableHorse.java` 定义 `horseman$getLead/setLead/isHitched/setHitched/getLeadAccess` 抽象方法 + 大量 `static` 工具（`isHitchable` 用 `CANNOT_BE_HITCHED` 标签、`canHitch` 读 Config、`syncHorseDataToTrackingClients`）。实现靠 `mixin/hitching/AbstractHorseMixin.java`：`@Mixin(AbstractHorse.class) public abstract class ... extends Animal implements HitchableHorse`，用 `@Unique` 字段 `horseman$leadAccess/horseman$leadItem/horseman$isHitched`，并 `@Unique private static Container horseman$createLeadAccess(...)` 返回匿名 `ContainerSingleItem` 让马拥有"缰绳槽位"；NBT 存取靠 `@Inject(method="addAdditionalSaveData", at=@At("RETURN"))` / `readAdditionalSaveData`。

**（2）铜号角召唤马匹——SavedData 快照方案**
`world/summoning/Summoning.java`(284) 持 `SummoningStorage`（`extends SavedData`，`server.overworld().getDataStorage().computeIfAbsent(factory(), "horseman_horse_calling")`，结构 `Map<UUID, Map<ResourceKey<Instrument>, StoredBoundHorse>>` + `unboundHorses` + `horsesToRemove` 两个 UUID 列表）。`StoredBoundHorse` 保存整头马的 `CompoundTag`（`EntityType.getKey` + `horse.saveWithoutId(tag)`）+ 位置 + 维度 + `isDead`，注释说明它是"快照式"存储。绑定信息写在马自身 NBT（`BoundData` record → `HorsemanCallingOwner/HorsemanCallingInstrument`）。调用流程 `Summoning.call(ServerPlayer, ResourceKey<Instrument>)` 用 `CallResult` 枚举返回 `NO_BOUND_HORSE / HORSE_IS_DEAD / ERROR_HORSE_IS_NOT_BOUND / INVALID_DIMENSION / TOO_FAR`，且**优先让马自己走过来**（`canWalkInsteadOfResummoning` → `walkToPlayer`）而不是重新召唤。马侧数据由 `mixin/summoning/AbstractHorseMixin.java` 实现 `SummonableHorse`（该接口注释明确"注入的接口所有方法必须是 default"）。号角道具 `CopperHornItem extends InstrumentItem`，直接复用原版 `Instrument` 注册表 + `InstrumentTags.GOAT_HORNS` 作 key。

**（3）每功能一个 mixin 包**
25 个语义化子包（`fix_moved_wrongly / less_wander / no_rearing / momentum / ride_though_leaves / fits_in_boat / swim / hitching / summoning / creative_taming / tame_with_item / shears_remove_chest / rotate_horse_when_mounting / free_camera_when_mounted / dismount / leash_sounds / horse_powder_snow / render / attribute_modifiers / switch_inventory / fix_camera_lag / fix_water_jump_meter / lower_horse_head` 等），每个独立可配置开关。

**（4）属性修饰符驱动玩法改动** — `mixin/attribute_modifiers/EntityMixin.java`
`@Mixin(value = Entity.class, priority = 950)`，注入 `startRiding` 内 `addPassenger` 调用点，给马加 `Horseman.EntityAttributes.MOUNTED_STEP_HEIGHT/MOUNTED_BREAK_SPEED` 两个自定义 `ResourceLocation` 的 `addTransientModifier`（先查 `instance.getModifier(id) == null` 防重复）。

**（5）MixinExtras 高级用法**
`mixin/hitching/LeashableMixin.java`：`@Mixin(Leashable.class) public interface ...`（接口式 mixin）用 `@Inject(head)` + `@Share("preventDrop") LocalBooleanRef` 在静态注入点传值，再用 `@WrapWithCondition` 包住 `Entity.spawnAtLocation` 阻止缰绳掉落；`mixin/fix_moved_wrongly/ServerGamePacketListenerImplMixin.java` 用 `@ModifyConstant(... args="doubleValue=0.0625")` 直接改原版常量（0.0625 → 0.36）。

**（6）JEI / 配方集成**
`integration/jei/HorsemanJeiPlugin.java`（`@JeiPlugin`）用 `InstrumentSubtypeInterpreter` 把所有 instrument 变体暴露给 JEI，并用 `ComponentTransferringShapelessExtension` 扩展原版无序配方展示；`world/item/crafting/recipe/ComponentTransferringRecipe` + `ComponentTransferringRecipeSerializer` 是自定义"数据组件搬运"配方。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：统一抽象接口 `network/packet/Packet.java` = `interface Packet extends CustomPacketPayload { boolean handle(PacketFlow flow, Player player); }`，即**方向由 `PacketFlow` 判断而非分两个方法**。`C2SPackets/S2CPackets.getDefinitions()` 返回 `List<CustomPacketPayload.TypeAndCodec<? extends FriendlyByteBuf, ?>>`（当前仅 `SyncHorseDataS2CP`）。发送侧 `network/Packets.java` 用 `@ExpectPlatform`（`sendToServer/sendToClient/sendToAllClients/sendToPlayersTrackingEntity`）+ 平台无关便捷方法 `sendToClients/sendToOtherClients(Predicate<ServerPlayer>)`；平台实现 `network/fabric/PacketsImpl`、`network/neoforge/PacketsImpl`（NeoForge 侧 `PacketsImpl.handle` 直接把 `context.flow()` 透传给 `packet.handle`）。`SyncHorseDataS2CP` 是 record，`StreamCodec.composite(ByteBufCodecs.VAR_INT, ..., ItemStack.OPTIONAL_STREAM_CODEC, ..., ByteBufCodecs.BOOL, ...)`。
- 配置：单一 `Config.java` 内三个静态类 `Server / Common / Client`，各持独立 `ModConfigSpec`，共 40+ 项（含 `EnumValue<SummonDimensionHandling>`、`EnumValue<LeavesCollisionMode>`、`ConfigValue<List<? extends String>> HORSE_SUMMONING_DIMENSIONS`）；NeoForge 侧全类型注册，并通过 `IConfigScreenFactory` 挂 NeoForge 配置 UI。
- 数据驱动：行为开关由 `Horseman.Tags.EntityTypes` 的 4 个标签（`CANNOT_BE_HITCHED / CANNOT_SWIM / FORBIDS_HORSES / SUMMONABLE`）与数据包 JSON 控制；`SummonDimensionHandling` / `LeavesCollisionMode` 为枚举型策略。
- datagen：**无** datagen 代码；本副本 `common/src/main/resources` 仅含 `horseman-common.mixins.json`、`horseman.accesswidener`、`hotswap-agent.properties`（另两个 mixin json 在各自平台模块）。
- 其他：`neoforge.mods.toml` 里声明 `[[dependencies.horseman]] modId="horsebuff" type="incompatible"`，与 mixin 插件里的条件判断互相呼应。

## 6. Mixin

三份配置 + 三个插件：

- `common/src/main/resources/horseman-common.mixins.json` — `package io.github.mortuusars.horseman.mixin`、`plugin io.github.mortuusars.horseman.mixin.HorsemanMixinPlugin`、`compatibilityLevel: JAVA_17`、`injectors.defaultRequire: 1`、client 段 11 个 / mixins 段 30 个（`required: true`）。
- `fabric/src/main/resources/horseman-fabric.mixins.json`（client 段 `mount_gui.GuiMixin`，plugin `HorsemanFabricMixinPlugin`）、`neoforge/.../horseman-neoforge.mixins.json`（同结构，plugin `HorsemanNeoForgeMixinPlugin`）。两份都在平台 `build.gradle` 的 `mixin { config "..." }` 中附加。
- 插件 `HorsemanMixinPlugin.java`：`ImmutableMap<String, Supplier<Boolean>> CONDITIONS` 以**完整 mixin 类名**为键做条件开关，`shouldApplyMixin` 返回 `CONDITIONS.getOrDefault(mixinClassName, () -> true).get()`；`onLoad` 里调 `MixinExtrasBootstrap.init()`（手写 MixinExtras 引导）。当前只有一条规则：`fix_moved_wrongly.ServerGamePacketListenerImplMixin` 在检测到正在加载 `horsebuff` 时不应用。
- 代表性 hook 目标：`AbstractHorse.addAdditionalSaveData/readAdditionalSaveData`（NBT）、`AbstractHorse.mobInteract`（HEAD + cancellable，让铜号角接管交互）、`Leashable.dropLeash(Entity,ZZ)V`（`@WrapWithCondition` 包 `Entity.spawnAtLocation`）、`ServerGamePacketListenerImpl.handleMoveVehicle`（`@ModifyConstant doubleValue=0.0625`）、`Entity.startRiding`（`@At(INVOKE addPassenger)`）、`InventoryScreen`/`AbstractContainerScreen`（`switch_inventory` 双端换背包）、`HorseModelMixin`/`HorseArmorLayerMixin`/`LlamaDecorLayerMixin`（渲染层）。命名与配置全部集中，`mixins.json` 是唯一"索引"。

## 7. 值得学的 5 条具体做法

1. **"一个功能 = 一个 mixin 子包 + 一条 Config 开关 + 一条混入清单项"**：25 个包一一对应；`common/src/main/java/io/github/mortuusars/horseman/mixin/`。适合把一批小 QOL 修改做成可逐条关闭的集合。
2. **接口注入 + `horseman$` 前缀命名 + `@Unique` 字段**：`HitchableHorse`/`SummonableHorse` 由 mixin 实现，接口内所有方法必须 default，并 `@SuppressWarnings("AddedMixinMembersNamePattern")`；`world/HitchableHorse.java`、`mixin/hitching/AbstractHorseMixin.java`。是给原版实体加数据与行为的干净做法。
3. **用 `ModConfigSpec` 三档（Server/Common/Client）分文件内静态类**，并让 `@ExpectPlatform` 的注册方法把平台差异完全挡在 `common` 之外；`Config.java:15/266/282`、`Register.java`。适合任何双加载器项目。
4. **`SavedData` + 实体整包 NBT 快照做"召唤/存档实体"**：`SummoningStorage.loadOrCreate` 用 `computeIfAbsent(factory(), "horseman_horse_calling")`，`StoredBoundHorse` 保存 `saveWithoutId` 出来的 tag；`world/summoning/SummoningStorage.java:57-66`、`StoredBoundHorse.java`。适用于"把实体收进道具再放出"的机制。
5. **行为返回枚举 `CallResult` 而非布尔**：`Summoning.call` 用 `NO_BOUND_HORSE/HORSE_IS_DEAD/INVALID_DIMENSION/TOO_FAR` 精确区分失败原因，便于客户端显示提示；`world/summoning/CallResult.java`。适用于交互类 API。
6. （补充）**用 `IMixinConfigPlugin` 的类名→条件表做跨模组兼容开关**（`horsebuff` 冲突时自动禁用某个 mixin）；`mixin/HorsemanMixinPlugin.java:17-20`。

## 8. （库/前置类 mod 专项）

非前置库，无对外 API 包。`common` 里可复用但与"扩展点"无关的工具：`Register`/`PlatformHelper` 的 `@ExpectPlatform` 模式、`network/Packets` 的跨平台发包封装、`mixin` 插件条件表。接入第三方仅通过标签（`Horseman.Tags.EntityTypes`）与 JEI 插件实现，未提供 `@Mod` 级互操作注册接口。
