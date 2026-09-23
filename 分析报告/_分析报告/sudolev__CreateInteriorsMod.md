# Create: Interiors 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Create: Interiors / `interiors`（mod_version 0.6.1）
- 作者：sudolev, rdh
- 目标版本（多平台单源码）：`1.20.1-forge`、`1.20.1-fabric`、`1.21.1-neoforge`（`settings.gradle.kts` stonecutter `vcsVersion = "1.20.1-forge"`）
- 构建：Gradle Kotlin DSL + **Stonecutter 0.7.11**（多版本工程）+ **Manifold 预处理插件**（`manifold_version=2025.1.31`，源码里用 `#if forge/#elif neoforge/#elif fabric` 甚至 `#error "Unsupported platform"` 做条件编译）；`buildSrc/` 自带 `fabric-defaults.gradle.kts`/`forge-defaults.gradle.kts`/`neoforge-defaults.gradle.kts` 与 `prop()` 跨层属性读取（`buildSrc/src/main/kotlin/buildSrc.kt`）
- 许可证：`src/main/resources/META-INF/mods.toml` 写 MIT，README 徽章写 GPL-3.0（**冲突，未确认**）
- 依赖（它是 Create 附属）：Create `6.0.8-289`(forge) / `6.0.10-217`(neoforge) / `6.0.8.1+build.1744`(fabric)，Ponder 1.0.81~1.0.91、Flywheel 1.0.5/1.0.6、Registrate `MC1.20-1.3.3`/`MC1.21-1.3.0+67`、MixinExtras 0.4.1、fabric-api 0.92.6、Fabric 端靠 porting_lib（`io.github.fabricators_of_create.porting_lib.*`）与 loom

## 2. 源码规模与包结构
16 个 `.java`，1308 行（实测）。包 `com.aesefficio.interiors`：
- 根：`CreateInteriors.java`(138)、`Utils.java`(95)
- `content/block/`：`CushionBlock`、`WallMountedTable`；`content/block/chair/`：`ChairBlock`(166)、`DirectionalSeatBlock`(81)、`BigChairBlock`、`FloorChairBlock`、`BigSeatMovementBehaviour`(55)
- `content/entity/BigSeatEntity.java`(64)
- `content/registry/`：`CIBlocks`(335)、`CITab`(73)、`CITags`(42)、`CIEntities`(24)
- `foundation/mixin/`：`SeatBlockMixin`(65)、`AbstractContraptionEntityMixin`(32)
- 资源只有 `interiors.mixins.json` + `META-INF/mods.toml`（无 assets，贴图/模型来自 Create 或未入库）

## 3. 入口与注册
`CreateInteriors.java:56` 用 Create 的注册框架：`CreateRegistrate REGISTRATE = CreateRegistrate.create(ID)`，静态块里设 `setTooltipModifierFactory(new Modifier(item, Palette.STANDARD_CREATE))` 并在 1.21 上 `defaultCreativeTab(null)`。平台入口在同一个类里用预处理分支：forgelike 是 `@Mod` 构造器（`REGISTRATE.registerEventListeners(modBus)` + `gatherData`），fabric 是 `implements ModInitializer, DataGeneratorEntrypoint`（`REGISTRATE.register()` / `REGISTRATE.setupDatagen(pack, efh)`）。`init()` 依次 `CITags/CIEntities/CIBlocks.register()`。
`content/registry/CIBlocks.java` 是范例式的 Registrate 链：`REGISTRATE.block("name", Ctor).initialProperties(SharedProperties::wooden).transform(axeOnly()).blockstate(...).recipe(...).onRegister(movementBehaviour(...)).onRegister(interactionBehaviour(new SeatInteractionBehaviour())).transform(displaySource(AllDisplaySources.ENTITY_NAME)).onRegisterAfter(Registries.ITEM, v -> ItemDescription.useKey(v, "block.interiors.chair")).item().model(...).build().register()`；16 色方块用 Create 的 `DyedBlockList` + lambda 批量生成（`:94` FLOOR_CHAIRS、`:148` CHAIRS、`:283` CUSHION_BLOCKS），另有 kelp 单色变体。创造标签 `CITab` 不在 16 色里硬编码，而是遍历 `REGISTRATE.getAll(Registries.BLOCK)` 自动填充。

## 4. 核心系统
1. **方向化座椅**（`content/block/chair/DirectionalSeatBlock.java`）：直接 `extends com.simibubi.create...SeatBlock implements IWrenchable`，新增 `FACING`，并拦截 `useItemOn/use`：手持 `AllItems.WRENCH` 时返回 `PASS_TO_DEFAULT_BLOCK_INTERACTION`，把扳手交互让给 IWrenchable。
2. **扶手/靠背状态机**（`ChairBlock.java:84-138`）：`EnumProperty<ArmrestConfiguration> ARMRESTS`(BOTH/NONE/LEFT/RIGHT) + `BooleanProperty CROPPED_BACK`；`onWrenched` 按 `switch(state.getValue(FACING))` 结合点击偏移 `pos.getCenter().subtract(clickLocation)` 决定改左还是右扶手，`onSneakWrenched` 切靠背裁剪——一个方块里塞进 4×2 变体。
3. **"大椅子"寄生 Create 座椅**（`foundation/mixin/SeatBlockMixin.java`）：不改 Create 逻辑而是用 MixinExtras 精准替换 —— `@Inject(isSeatOccupied, HEAD, cancellable)` 让 `BigSeatEntity` 也算占用；`@ModifyExpressionValue(method="sitDown", at=@At(value="NEW", target=DESC))` 把 `new SeatEntity` 换成 `new BigSeatEntity`（1.20.1/1.21 描述符用字符串拼接 `#if MC < 21.0` 兼容）；`@ModifyArg` 给 `setPos` 的 Y 加 0.34；`@ModifyExpressionValue` 换 `DyedBlockList.get(color)` 返回自家方块，使 Create 的染色/座椅替换逻辑自动指向本 mod）。
4. **大座椅实体**（`content/entity/BigSeatEntity.java` + `CIEntities.java`）：`extends SeatEntity`，覆盖 `getDismountLocationForPassenger` 与 `positionRider`（1.21 用 `Entity.MoveFunction` lambda，1.20.1 用 `getPassengersRidingOffset`）统一 +0.34 抬升；内嵌 `Render extends EntityRenderer` 且 `shouldRender=false`；注册用 Registrate 的 `EntityEntry`，`.sized/.dimensions`、`.setTrackingRange/.trackRangeChunks` 等平台差异全部在链里用 `#if` 切。
5. **装置上的座椅行为**（`BigSeatMovementBehaviour.java`）：`extends SeatMovementBehaviour`，`visitNewPosition` 时检查该座位下方是否实心（`canOcclude()` 或下半 slab），满足则让乘客 `stopRiding` 并 `teleportTo(中心+1)`，同时删除 `PersistentData/CustomData` 的 `ContraptionDismountLocation`；配套 `AbstractContraptionEntityMixin` 在 `getPassengerPosition` TAIL 注入，为 BigChairBlock 乘客位置 +0.34。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**自建包；配置：**无**。
- datagen：forgelike 端在 `@Mod` 构造器注册 `GatherDataEvent`（`EventPriority.HIGH`），只做"默认 lang 注入"——`FilesHelper.loadJsonResource("assets/interiors/lang/default/tooltips.json")` → `REGISTRATE.addRawLang`（`CreateInteriors.java:123-133`）；fabric 端在 `onInitializeDataGenerator` 里用 porting_lib 的 `ExistingFileHelper`/`MinecraftExtension` 构造 efh（注释说明 "false disables validation, which causes fabric datagen is weird"）→ `REGISTRATE.setupDatagen(...)`，并用 `addDataGenerator(ProviderType.ITEM_TAGS, ...)` 生成染料标签。
- 方块模型/配方全部在 `CIBlocks` 的 `.blockstate()/.recipe()` 回调里用生成器 API 写（`chairModels(...)` 用 `p.models().withExistingParent(path+detailer+specifier, modLoc(path+specifier))` 组装 `top/side/side_top/side_front` 纹理，`:317-334`）。
- 跨平台标签命名：`CITags.java:24-34` 用 `#if forge → "forge:dyes/<color>"`、`#elif neoforge → "c:dyes/<color>"`、`#else → "c:<color>_dyes"`。

## 6. Mixin
配置：`src/main/resources/interiors.mixins.json`（`package: com.aesefficio.interiors.foundation.mixin`，`compatibilityLevel: JAVA_17`，`injectors.defaultRequire=1`），mods.toml 里 `[[mixins]] config="interiors.mixins.json"`。
- `SeatBlockMixin` → 目标 `com.simibubi.create...actors.seat.SeatBlock`，hook：`isSeatOccupied`(HEAD)、`sitDown`(NEW SeatEntity / `SeatEntity.setPos` ModifyArg)、`useItemOn`(1.20.1 为 `use`，ModifyExpressionValue `DyedBlockList.get`)
- `AbstractContraptionEntityMixin` → `AbstractContraptionEntity.getPassengerPosition`(TAIL, cancellable) + `@Shadow(remap=false) contraption` + `@Local BlockPos seat`

## 7. 值得学的 5 条做法
1. **用 MixinExtras 做"外科手术式"扩展 Create**：`@ModifyExpressionValue` 只替换 `new SeatEntity(...)`，不用重写 `sitDown`（`SeatBlockMixin.java:41-51`）。
2. **Mixin 描述符跨版本拼接**：把 `DESC` 写成本地常量并用 `#if MC < 21.0` 插参数字符串，一份源码兼容 1.20.1/1.21.1（`SeatBlockMixin.java:37-39`）。
3. **Stonecutter + Manifold 条件编译**：平台/版本差异全部落在 `#if`，工程结构（buildSrc `*-defaults.gradle.kts`、`platform`/`forgelike` 常量）值得照抄，见 `build.gradle.kts` 的 `stonecutter.constants { match("platform"(), "fabric","forge","neoforge") }`。
4. **DyedBlockList + lambda 批量注册 16 色**：方块、物品、配方、blockstate、tag 全在一个 lambda 里成对生成，新增颜色零改动（`CIBlocks.java:94-146`）。
5. **把附属行为挂到 Create 的 API 静态入口**：`movementBehaviour/interactionBehaviour/displaySource` 三个静态 import 直接把行为注册到已有方块上（`CIBlocks.java:57-59`、`:138-141`）。
6. 补充：物品提示不走 lang 文件，而是 `.onRegisterAfter(Registries.ITEM, v -> ItemDescription.useKey(v, "block.interiors.chair"))` 复用 Create 的 tooltip 键。

## 8. 是否库/前置
非库 mod。其"扩展点"完全是 Create 的（`SeatBlock`/`SeatEntity`/`SeatMovementBehaviour`/`DyedBlockList`/`CreateRegistrate`），没有对外 API 包。
