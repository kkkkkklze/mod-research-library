# BluSunrize/ImmersiveEngineering 源码分析报告

## 1. 基本信息

- Mod 名：Immersive Engineering；mod_id `immersiveengineering`
- 作者：BluSunrize and Damien A.W. Hazard（`src/main/templates/META-INF/neoforge.mods.toml`）
- 目标版本/加载器：Minecraft **1.21.1** + **NeoForge 21.1.164**（`gradle.properties:4-6`）
- Gradle 插件：`net.neoforged.moddev`（MDG）2.0.30-beta（`build.gradle:4`），非 ForgeGradle
- 许可证："Blu's License of Common Sense"（自定义许可证，`neoforge.mods.toml:6`）
- 编译依赖（`build.gradle:128-146`）：**全部 compileOnly /可选**——JEI（`jei-1.21.1-neoforge-api`）、CraftTweaker（仍指向 forge-1.20.1）、CC:Tweaked、The One Probe、Curios、Jade、OpenComputers2；jarJar 内嵌自家工具库 `malte0811:BlockModelSplitter`、`malte0811:DualCodecs`
- 结论：它不是库 mod，但自带 `src/api` sourceSet 作为对外 API（171 个公开类），供附属/兼容 mod 编译期接入

## 2. 源码规模与包结构

实测 `find ... | wc -l` / `wc -l`：

| sourceSet | 文件数 | 行数 |
|---|---|---|
| src/main/java | 948 | 116,679 |
| src/api/java | 212 | 21,167 |
| src/datagen/java | 85 | 15,240 |
| src/manual/java | 24 | — |
| src/main/oldjava | 22 | —（CrT 兼容，已移出编译） |
| src/gametest/java | 4 | 239 |

合计约 1249 个参与编译的 java 文件、15.3 万行。

主要包（main，文件数）：`common/blocks/multiblocks` 102、`common/util/compat` 92、`common/blocks/metal` 81、`common/items` 50、`client/models/obj` 40、`client/gui` 38、`common/gui` 36、`common/network` 30、`common/crafting/serializers` 29、`client/render/tile` 28、`common/blocks/wooden` 26、`mixin/accessors` 25、`common/util` 23、`common/crafting` 22、`common/register` 18、`common/entities` 18。

最大文件：`common/register/IEBlocks.java`(1050)、`datagen/.../blockstates/BlockStates.java`(1017)、`datagen/.../recipes/MiscRecipes.java`(866)、`common/blocks/metal/FluidPipeBlockEntity.java`(826)、`common/util/Utils.java`(808)、`api/shader/ShaderRegistry.java`(778)、`common/gui/IESlot.java`(768)。

## 3. 入口与注册

主类 `src/main/java/blusunrize/immersiveengineering/ImmersiveEngineering.java:79-115`，构造注入 `(ModContainer, Dist, IEventBus)`：

```java
@Mod(ImmersiveEngineering.MODID)
public ImmersiveEngineering(ModContainer container, Dist dist, IEventBus modBus) {
    modBus.addListener(this::setup);
    modBus.addListener(this::setupNetwork);
    RecipeSerializers.RECIPE_SERIALIZERS.register(modBus);
    container.registerConfig(Type.STARTUP, IECommonConfig.CONFIG_SPEC);
    container.registerConfig(Type.CLIENT,  IEClientConfig.CONFIG_SPEC);
    container.registerConfig(Type.SERVER,  IEServerConfig.CONFIG_SPEC);
    IEContent.modConstruction(modBus);
    IEWorldGen.init(modBus); IECompatModules.onModConstruction(modBus);
}
```

注册框架：原生 **DeferredRegister**（main+api 共 34 处 `DeferredRegister.create`）+ 自定义包装类 `BlockEntry`/`ItemEntry`（定义在 `common/register/IEBlocks.java` 内部），把"方块 + BlockItem + BlockEntity + 属性"打包成一句声明：`BlockEntry.simple("cokebrick", PROPS)`（`IEBlocks.java:157`）。注册类集中在 `common/register/`（18 个：IEBlocks/IEItems/IEFluids/IEParticles/IEMenuTypes/IEBlockEntities/IEDataComponents/IEDataAttachments/IEEntityTypes/IEPotions/IEIngredients/IEMultiblockLogic/…）。

## 4. 核心系统

**(1) 多结构（Multiblock）组件化框架** — 学习价值最高
- `api/multiblocks/blocks/MultiblockRegistration.java`（record）+ `MultiblockRegistrationBuilder.java`：DSL 式声明 `stone(new CokeOvenLogic(), "coke_oven", true).structure(...).gui(...).build()`（`common/register/IEMultiblockLogic.java:50`）
- 三段职责分离：`logic/IMultiblockLogic<State>`（业务）、`component/IMultiblockComponent` + `StateWrapper<State, ComponentState>`（可插拔组件，把组件状态包进主 State）、`registry/MultiblockBlockEntityMaster` + `MultiblockBlockEntityDummy`（一个主 BE 承载全结构，其余部件是 dummy BE）；`env/IMultiblockBEHelper*` 屏蔽主/从差异
- 结构来源两代并存：`TemplateMultiblock`（.nbt 结构模板）+ `MultiblockHandler`、`BlockMatcher`（旧式方块匹配）

**(2) 电线/电网 API**（`src/api/.../api/wires`）
- `GlobalWireNetwork`（按 level 存于 `IESaveData` SavedData）+ `LocalWireNetwork` 分块子图
- 扩展点 `localhandlers/LocalNetworkHandler`：内建 `EnergyTransferHandler`、`redstone/RedstoneNetworkHandler`、`WireDamageHandler`；`WireType`/`IConnectionTemplate`/`IImmersiveConnectable` 决定可连接性与损耗

**(3) 配方体系**（`src/api/.../api/crafting`）
- `IESerializableRecipe implements Recipe<RecipeInput>`，但 `isSpecial()=true`、`matches()` 返回 false、`assemble()` 只返回 `outputDummy`——IE 配方**不参与原版合成匹配**，仅作数据容器 + 自己的索引/查询
- `IERecipeTypes` 用 `TypeWithClass<T>`（DeferredHolder + Class 成对）把类型与实现的 Class 绑在一起；19 个配方类型
- `cache/CachedRecipeList<R>`：以 level 为键缓存配方列表，靠静态 `reloadCount`（由 `TagsUpdatedEvent`/`RecipesUpdatedEvent` 在 `EventPriority.HIGH` 自增）失效，通用性极强

**(4) Compat 模块热插拔**（`common/util/compat/IECompatModules.java`）
- `MODID -> Class` 映射（EARLY / STANDARD 两档时机），`ModList.get().isLoaded()` 后反射构造；`abstract sealed class IECompatModule permits EarlyIECompatModule, StandardIECompatModule` 限定层级；每个模块有独立 config 开关

**(5) 游戏内手册**：`resources/assets/immersiveengineering/manual/en_us/*.txt` 114 篇 + `client/manual/`（`IEManualInstance`、`ManualElementMultiblock`、`ManualElementBlueprint`…）+ datagen `data/manual/ManualDataGenerator`，把机器结构/配方渲染成图文页

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`RegisterPayloadHandlersEvent` → `ev.registrar(MODID)`，28 个 `IMessage extends CustomPacketPayload` 包（`common/network/`），统一 `registerMessage(registrar, T.ID, T.CODEC, direction)` 按 `PacketFlow` 分派到 `playToClient/playToServer/playBidirectional`（`ImmersiveEngineering.java:206-270`）。`MessageMultiblockSync`/`MessageBlockEntitySync`（含 NBT 增量同步）、`MessageContainerData`、`MessageWireSync`；`PacketUtils` 提供 `readList/writeList/readRegistryElement`（用 ResourceKey 传注册项）
- 配置：三份 ModConfigSpec，STARTUP/CLIENT/SERVER 分类型注册；`IEClientConfig` 客户端专用
- datagen：`datagen/.../data/IEDataGenerator.java:38` 单入口 `GatherDataEvent`，含 tags、loot（`AllLoot`）、recipes（按机器拆成 MiscRecipes/DeviceRecipes/DecorationRecipes）、blockstates、ItemModels、DynamicModels、StructureUpdater、ManualDataGenerator、WorldGenerationProvider
- 数据结构：`IEDataComponents`（DataComponent）、`IEDataAttachments`（AttachmentType）、`IEEntityDataSerializers`

## 6. Mixin

- 配置：`src/main/resources/immersiveengineering.mixins.json`，package `blusunrize.immersiveengineering.mixin`，compatibilityLevel `JAVA_17`，`injectors.defaultRequire=1`；**plugin** = `blusunrize.immersiveengineering.common.mixin.IEMixinConfig`
- 该 plugin 在 `onLoad` 里注册**自定义注入点** `InjectionInfo.register(CaptureOwnerInjectionInfo.class)`（`IEMixinConfig.java:24`），配套 `CaptureOwner.java` / `CaptureOwnerInjector.java`
- 25 个 accessors（`AbstractArrowAccess`、`BaseContainerBEAccess`、`ShapedRecipeAccess`、`BETypeAccess`…）+ 15 个 client accessors；`coremods/` 6 个行为 mixin：`AbstractBlockStateMixin`、`BreezeDeflectionMixin`、`ServerWorldMixin`、`TemplateMixin`、`WallMixin`、`WaterwheelBoundsMixin`；client 侧 `BipedModelMixin`、`MinecartRendererMixin`、`SoundEngineMixin`
- 代表 hook：`WaterwheelBoundsMixin` 注入原版 `FlowingFluid.canPassThrough(...,BlockGetter;Fluid;BlockPos;BlockState;Direction;BlockPos;BlockState;FluidState)Z` 的 `@At("HEAD")` + `cancellable=true`，水流进入水车所在轴平面时直接返回 false（`mixin/coremods/WaterwheelBoundsMixin.java:36-60`）

## 7. 值得学的 5 条具体做法

1. **方块注册包装类把 4 件事合并成一句**：`BlockEntry.simple(name, props)` 内部同时登记 Block/BlockItem/BlockEntity/默认属性，避免"注册三件套"分散——`common/register/IEBlocks.java:157`；适用任何方块数量 100+ 的 mod
2. **配方缓存统一失效计数**：`CachedRecipeList` 用静态 `reloadCount` + 两个事件监听替换逐处重载逻辑，可直接抄——`api/crafting/cache/CachedRecipeList.java:33-63`
3. **配方只做数据容器**：`IESerializableRecipe` 让 `matches()` 恒 false、`isSpecial()` 恒 true，把自己从原版合成路径摘出去，自己管查询——`api/crafting/IESerializableRecipe.java:31-52`
4. **兼容模块用"ModID→Class 映射 + ModList 判定 + 反射构造 + 独立 config 开关"**，避免附属 mod 硬依赖——`common/util/compat/IECompatModules.java:26-49`；写 Create/Curios 兼容时直接套用
5. **多结构用"主 BE + Dummy BE + 组件 StateWrapper"**：把 N 个方块的位置信息压到一个主 BlockEntity 里，组件状态用嵌套结构而非分散字段——`api/multiblocks/blocks/MultiblockRegistration.java:27-40`、`api/multiblocks/blocks/component/IMultiblockComponent.java`；适合大型多方块机器

## 8. 公开 API（对外接入方式）

`src/api/java`（sourceSet `api`，171 个类）为对外 API，包根 `blusunrize.immersiveengineering.api`：

- `IEApi`（矿词优先 mod 列表 `modPreference`、`prefixToIngotMap` 锭换算表、`getPreferredTagStack`）、`IETags`、`Lib`、`IEProperties`
- 扩展点接口：`api/tool/conveyor/IConveyorType` + `api/tool/conveyor/ConveyorHandler`（注册自定义传送带）、`api/wires/WireApi` / `WireType` / `localhandlers/LocalNetworkHandler`（自定义电网负载）、`api/multiblocks/` 整套多方块框架、`api/tool/assembler/AssemblerHandler`、`api/tool/upgrade/*`、`api/shader/ShaderRegistry` + `CapabilityShader`
- 接入方式：把 `src/api` 当独立 artifact 依赖后注册实现类；同时提供 Forge `InterModComms` 通道（`IEIMCHandler.handleIMCMessages(InterModComms.getMessages(MODID))`，`ImmersiveEngineering.java:200`）
