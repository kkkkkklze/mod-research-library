# mortuusars/ExposurePolaroid 源码分析报告

## 1. 基本信息
- Mod 名 Exposure Polaroid（Exposure 的"拍立得/即时相机"附属）/ `mod_id=exposure_polaroid` / 作者 mortuusars / 版本 `1.1.6` / MIT
- 目标：MC 1.21.1，**双平台 Architectury**（`enabled_platforms=fabric,neoforge`）；Fabric loader 0.16.9 / Fabric API 0.102.1+1.21.1；NeoForge 21.1.129，parchment `1.21:2024.07.28`
- 构建：`dev.architectury.loom 1.7-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + `shadow 8.1.1` + `mod-publish-plugin`；三模块 `common/ fabric/ neoforge/`
- 关键依赖：**Exposure 1.9.18（前置 API，`required_exposure_version_range_*` 强制 ≥1.9.0）**、JEI 19.19、Jade、Carry On、Exposure Catalog；Architectury `@ExpectPlatform`

## 2. 源码规模与包结构
- 38 个 `.java`，2351 行（`find common fabric neoforge -name '*.java' -exec wc -l {} +`）
- 包（`io.github.mortuusars.exposure_polaroid.*`）：根 5（`ExposurePolaroid`、`ExposurePolaroidClient`、`Register`、`Config` 等）、`client/camera/viewfinder` 4、`network/packet` 3、`client/gui/screen/camera/button` 3、`world/item` 2、`world/item/camera` 2
- 最大文件：`world/item/InstantCameraItem.java`(383)、`ExposurePolaroid.java`(188)、`client/gui/screen/camera/button/ExposureSliderButton.java`(153)、`fabric/.../RegisterImpl.java`(141)、`neoforge/.../RegisterImpl.java`(132)、`Register.java`(131)、`Config.java`(99)

## 3. 入口与注册
- common 入口 `common/.../ExposurePolaroid.java:22`（无 `@Mod`/`@Mod` 平台中立），`init()` 依次调用内部静态类的 `init()`：`Blocks/BlockEntityTypes/EntityTypes/Items/DataComponents/CriteriaTriggers/ItemSubPredicates/MenuTypes/RecipeSerializers/SoundEvents/ArgumentTypes`，内容物以静态 `Supplier` 字段就地声明（如 `Items.INSTANT_CAMERA = Register.item("instant_camera", ...)`）。
- **跨平台注册抽象**：`common/.../Register.java:36` 全类为 `@ExpectPlatform` 静态方法（block/item/entityType/menuType/recipeType/criterionTrigger/itemSubPredicate/commandArgumentType/worldGenFeature/dataComponentType/particleType 及 `BlockEntitySupplier`、`MenuTypeSupplier` 函数接口）。
- NeoForge 实现 `neoforge/.../RegisterImpl.java:36-50`：**15 个 `DeferredRegister`**（BLOCKS/BLOCK_ENTITY_TYPES/ITEMS/ENTITY_TYPES/MENU_TYPES/SOUND_EVENTS/RECIPE_TYPES/RECIPE_SERIALIZERS/CRITERION_TRIGGERS/ITEM_SUB_PREDICATES/COMMAND_ARGUMENT_TYPES/WORLD_GEN_FEATURES/`DeferredRegister.DataComponents`/PARTICLE_TYPES/CUSTOM_STATS），每个 `@ExpectPlatform` 方法转发到对应 register 调用；Fabric 侧 141 行直接 `Registry.register`。

## 4. 核心系统
1. **平台抽象注册层**：`Register`（声明）+ `fabric|neoforge/RegisterImpl`（实现）——两种加载器共享一份 `ExposurePolaroid.Items/SoundEvents` 声明。
2. **一份定义两端注册的网络层**：`common/network/packet/{S2CPackets,C2SPackets,CommonPackets}.getDefinitions()` 返回 `TypeAndCodec` 集合，平台侧统一遍历并 `playToClient/playToServer/playBidirectional`（`neoforge/.../event/NeoForgeCommonEvents.java:41-60`，注册版本号 `"1"`，handler 统一为 Exposure 的 `PacketsImpl::handle`）；`network/handler/ClientPacketsHandler` 处理入站。
3. **相机物品与取景逻辑**：`world/item/InstantCameraItem`（383 行，持 `Exposure.DataComponents.CAMERA_ACTIVE`）、`world/item/InstantSlideItem`（按 `ExposureType.COLOR/BLACK_AND_WHITE` + `FilmStyle` 数据组件构造，`ExposurePolaroid.java:63-99`）。
4. **取景器 UI**：`client/camera/viewfinder/InstantCameraControlsScreen`、`client/gui/screen/camera/button/{ExposureSliderButton,SlideCounterWidget}`——滑块/计数控件自绘（PoseStack + PoseStack 变换）。
5. **与前置的深度集成**：直接引用 `io.github.mortuusars.exposure.*` 的 `Exposure.DataComponents`、`FilmStyle/Levels/HSB/ColorBalance`、`ExposureType`、`PlatformHelperClient`，并把物品注入前置的创造标签页（`BuildCreativeModeTabContentsEvent` 中判断 `Exposure.resource("exposure")`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：见上（S2C/C2S/Common 三类 + 集中注册，无自定义同步协议）。
- 数据驱动：使用原版数据组件 `DataComponents`（`RegisterImpl.DATA_COMPONENT_TYPES`）与 Exposure 的 film style；无自研数据包加载器（依赖 Exposure 的 `catalog`/资源）。
- 配置：`common/.../Config.java`(99 行)，走 Architectury/Forge Config API（`forge_config_api_port_version=21.1.0`）。
- datagen：**无**（无 `src/generated`、无 DataProvider）。

## 6. Mixin
- 通用 client mixin 目录 `common/src/main/java/io/github/mortuusars/exposure_polaroid/mixin/client/`：`ItemRendererMixin` — `@Mixin(ItemRenderer.class)` + `@ModifyVariable(method="render", at=@At("HEAD"), argsOnly=true)`，当物品是 `INSTANT_CAMERA` 且 `displayContext == GUI` 时用 `PlatformHelperClient.getModel(ExposurePolaroidClient.Models.INSTANT_CAMERA_GUI)` + `getOverrides().resolve(...)` 替换 BakedModel。
- 平台配置：`neoforge/src/main/resources/exposure_polaroid-neoforge.mixins.json`（`client`/`mixins` 数组为空，但声明 `plugin: io.github.mortuusars.exposure_polaroid.neoforge.ExposurePolaroidMixinPlugin`）与 `fabric/.../exposure_polaroid-fabric.mixins.json`——**用 mixin plugin 做条件加载**是架构上唯一的手法。

## 7. 值得学的 5 条做法
1. **`@ExpectPlatform` + 每平台 RegisterImpl**：注册声明集中在一处，平台差异全在实现类（`common/.../Register.java`）——多平台附属的标准写法。
2. **"一份 packet 定义表 + 平台循环注册"**（`NeoForgeCommonEvents.java:41-60`）——避免为 forge/fabric 各写一遍包注册。
3. **物品能力全靠数据组件表达**（`Exposure.DataComponents.FILM_STYLE` + `FilmStyle.create()...` 链式 builder，`ExposurePolaroid.java:63-99`）——同一物品类就能产出多种胶片效果，无需子类。
4. **GUI 交互控件自绘**（`ExposureSliderButton`/`SlideCounterWidget`）——需要风格统一的相机取景器界面时可直接参考。
5. **附属 mod 把入口物品塞进前置已有的创造标签页**（`BuildCreativeModeTabContentsEvent` + `Exposure.resource("exposure")`）——附属整合体验做法。

## 8. （库/前置类）
非库 mod；它**消费** Exposure 的 API（`Exposure.DataComponents`、`ExposureType`、`FilmStyle`、`PlatformHelperClient`、`io.github.mortuusars.exposure.Register.*Supplier`、`exposure.network.packet.Packet`），可作为"如何写 Context 前置的附属 mod"的范例，但不对外暴露 API。
