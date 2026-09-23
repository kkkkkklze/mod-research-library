# SuperMartijn642's Core Lib 源码分析

## 1. 基本信息

- Mod 名：SuperMartijn642's Core Lib；mod_id：`supermartijn642corelib`；作者：SuperMartijn642；版本 1.1.24
- 目标环境（`gradle.properties`、`fabric.mod.json`）：Minecraft 1.18.2（`minecraft_dependency=1.18.x`）、Fabric Loader ≥0.14.0（编译 0.15.11）、Fabric API 0.77.0+1.18.2、Java 17；同时兼容 Quilt（`build.gradle:47-53` 引 quilt-loader/json5/config，`CoreLibPreLaunch` 里反射区分 QuiltLoaderImpl/FabricLoaderImpl）
- 本仓库检出分支为 `fabric-1.18`（`git rev-parse --abbrev-ref HEAD`），源码无 Forge/common 分离源集；其他分支是否含 Forge 实现未确认
- Gradle：fabric-loom 1.14-SNAPSHOT + mod-publish-plugin 0.5.2，Gradle 9.2.1，officialMojangMappings，发布到 CurseForge(454372)/Modrinth(rOUBggPv)
- 许可证：`All rights reserved`；编译依赖：Fabric API、Architectury API（`architectury_file=4521464`，作为**可选**依赖：`CoreLib.isArchitecturyLoaded = CommonUtils.isModLoaded("architectury")`，`CoreLib.java:31`）
- 定位：库/前置模组，作者全部 mod 共用

## 2. 规模与包结构

126 个 `.java`，18170 行（`find src -name '*.java' | wc -l` / `-exec wc -l {} +`）。

包（第 3 层，文件数）：`core/gui` 28（另 `gui/widget` 12、`gui/widget/premade` 6）、`core/mixin` 15、`core/generator` 15、`core/data` 14、`core/render` 9、`core/util` 8、`core/registry` 8、`core/block` 7、`core` 7、`core/network` 6、`core/item` 5、`core/extensions` 4。

最大文件：`generator/RecipeGenerator.java` 1584、`generator/ModelGenerator.java` 983、`generator/BlockStateGenerator.java` 706、`registry/ClientRegistrationHandler.java` 693、`generator/TagGenerator.java` 688、`generator/LootTableGenerator.java` 586、`gui/CustomSlotImpl.java` 556、`registry/RegistrationHandler.java` 510、`gui/ScreenUtils.java` 393。

## 3. 入口与注册

- `fabric.mod.json` entrypoints：`main = com.supermartijn642.core.CoreLib`，`preLaunch = CoreLibPreLaunch`
- `CoreLib.onInitialize()`（`CoreLib.java:33`）只注册自己的东西：条件配方序列化器、5 个资源条件、自定义标签条目序列化器、3 个内置生成器
- **关键技巧**：`CoreLibPreLaunch`（`CoreLibPreLaunch.java:34+`）在 preLaunch 阶段用反射拿到 `FabricLoaderImpl.entrypointStorage`/`QuiltLoaderImpl.entrypointStorage` 的 `entryMap`，把 `RegistryEntryPoints` 追加进 `main`/`client` 列表。因为追加在最后，`CoreLib.afterInitialize()`（`RegistryEntryPoints.onInitialize` → `CoreLib.afterInitialize`）会在**所有其他 mod 初始化完之后**执行，从而做 `RegistrationHandler.registerInternal()`（统一提交注册）与 `RegistryEntryAcceptor.reportMissing()`
- 注册框架不是 DeferredRegister/Registrate，而是自研三层：
  1. `RegistryEntryAcceptor` 注解（`registry/RegistryEntryAcceptor.java`）：附属 mod 在主类里声明 `public static` 非 final 字段（或单参静态方法），标 `@RegistryEntryAcceptor(namespace, identifier, registry)`；`Handler.gatherAnnotatedFields()` 在 preLaunch 后扫描所有依赖 `supermartijn642corelib` 的 mod 的 main entrypoint，校验类型/可见性并缓存，再用 Fabric `RegistryEntryAddedCallback` + 反射回填字段值
  2. `RegistrationHandler.get(modid)`（`registry/RegistrationHandler.java:53`）：按 modid 单例，`registerBlock/Item/EntityType/...`（含 `registerXxxOverride(namespace, id, ...)` 跨命名空间覆盖、`registerXxxCallback(Consumer<Helper<T>>)` 便于注册后补挂属性），内部 `entryMap: Map<Registries.Registry<?>, Map<ResourceLocation,Supplier<?>>>`；`addEntry` 里所有参数做 `RegistryUtil.isValidNamespace/isValidPath` 校验并拒绝重复 id；提交顺序由 `Registries.REGISTRATION_ORDER` 固定（BLOCKS→FLUIDS→ITEMS→…→RECIPE_SERIALIZERS→自定义 registry）
  3. `Registries`（`registry/Registries.java`）：用接口 `Registry<T>` 包原版注册表（`VanillaRegistryWrapper`）或自建 map（`MapBackedRegistry`，用于资源条件/标签条目序列化器）；`Registry<T>` 暴露 getRegistryIdentifier/getIdentifier/getValue/getEntries 等，抹平原版差异

## 4. 核心系统

**A. 原版注册表条目覆盖**（学习价值最高）
- `Registries.VanillaRegistryWrapper.register`：若 id 已存在且底层是 `MappedRegistry`，用 `registerOrOverride(OptionalInt.of(oldId), key, object, Lifecycle.stable())` 保持原数字 id，并临时打开 `CoreLibMappedRegistry.supermartijn642corelibSetRegisterOverrides(true, overrideConsumer)`
- `mixin/MappedRegistryMixin.java` 在 `registerMapping(...)` 的 HEAD 缓存被覆盖的 `Holder.Reference`，TAIL 里调 overrideConsumer、把旧 value 放回 `byValue`、并调 `CoreLibHolderReference.supermartijn642corelibOverride` 让**旧 Holder 引用改指向新对象**（否则已持有 Holder 的代码仍拿到旧实例）
- `registry/RegistryOverrideHandlers.java` 用反射列出需要改的原版字段（`BlockBehaviour.Properties.canOcclude` 等）；`generator/standard/CoreLibAccessWidenerGenerator.java` 把这些反射找到的字段名字生成 accesswidener 条目，`build.gradle:81-85` 在 `processResources` 里把生成结果 `filter` 注入 `modid.accesswidener` 的 `# generated` 处

**B. GUI 框架**
- `gui/widget/Widget.java`：完整生命周期接口——`initialize/update/discard` + 五段渲染 `renderBackground|render|renderForeground|renderOverlay|renderTooltips` + 输入 `mousePressed/Released/Scrolled、keyPressed/Released、charTyped`，**每个输入都带 `hasBeenHandled` 参数并返回 boolean**，形成责任链（父容器可拦截）
- `gui/widget/BaseWidget.java`：自带子 widget 列表与 `focusedWidget`，在 `renderBackground` 里用鼠标位置做悬停聚焦，`setFocused` 记录 `nextNarration = Util.getMillis()+750` 实现延迟旁白（`NarratorChatListener`）
- `gui/WidgetScreen.java` 把单个 Widget 包成 `Screen`（`/of(widget)`）；`gui/WidgetContainerScreen.java:23` 继承 `AbstractContainerScreen`，`render`（第 85 行起）自己实现槽位绘制、光标物品拖拽（`draggingItem`/`isSplittingStack`/`quickCraftSlots`/`snapback*`，靠 accesswidener 开放）、并用 `RenderSystem.getModelViewStack().translate(offsetX,offsetY,0)` 把 widget 局部坐标原点搬到屏幕中心
- 容器侧：`gui/BaseContainer.java`（player/level 字段、`addSlots(Player)`、`addPlayerSlots`、`stillValid` 恒 true）、`gui/BaseContainerType.java`（`ExtendedScreenHandlerType` + 一对 `BiConsumer<T,FriendlyByteBuf>`/`BiFunction<Player,FriendlyByteBuf,T>` 描述"打开界面时下发的数据"），打开流程在 `CommonUtils.openContainer`（`CommonUtils.java:63`）用 `ExtendedScreenHandlerFactory.writeScreenOpeningData` 下发
- `gui/CustomSlot.java` + `CustomSlotImpl.java`（556 行）：槽位可自定义宽高、背景、是否显示物品

**C. 网络**（`network/PacketChannel.java`）
- `PacketChannel.create(modid, name)`：基于 Fabric `ClientPlayNetworking`/`ServerPlayNetworking` 的 custom payload，包体第一位写 `int index`，由 `packetsByIndex` 反查类
- `registerMessage(Class, Supplier, PacketDirection, shouldBeQueued)`；`BasePacket` 接口 `write/read/verify/handle`，`PacketContext` 提供 `getHandlingSide/getPlayer/getWorld/queueTask`（服务端 `server.submit`，客户端 `ClientUtils.queueTask`）
- 发送封装齐全：`sendToServer/sendToPlayer/sendToAllPlayers/sendToDimension(ResourceKey|Level)/sendToAllTrackingEntity/sendToAllNear(pos|xyz)`，并在发送前 `checkRegistration` 校验方向；另有 `BlockPosBasePacket`/`BlockEntityBasePacket` 基类

**D. 数据驱动**（`core/data`）
- 资源条件：`ResourceCondition`（`test` + `getSerializer` + `negate/or/and` 组合子）、`ResourceConditionSerializer`、实现类 `ModLoaded/Not/Or/And/TagPopulatedResourceCondition`；注册进 `Registries.RESOURCE_CONDITION_SERIALIZERS` 时**同时桥接** Fabric 的 `ResourceConditions.register`（`Registries.java` 内匿名子类）
- `data/recipe/ConditionalRecipeSerializer.java`：把普通配方 JSON 包进 `{"type":"...conditional","conditions":[...],"recipe":{...}}`，加载时逐条测试条件，不满足则丢弃
- 自定义标签条目：`CustomTagEntry`/`CustomTagEntrySerializer` + `TagEntryAdapter implements Tag.Entry`，因为自定义条目解析时需要 Registry 上下文，用 `TagLoaderMixin`（注入 `TagLoader.build` HEAD）和 `TagManagerMixin` 把 registry 塞进去；内置 `NamespaceTagEntry`（按命名空间整批匹配）

**E. Datagen 框架**（`core/generator`，15 文件 / 约 6000 行）
- 自研 `ResourceGenerator`（抽象 `generate()/save()`）+ `ResourceCache`（`HashCacheWrapper` 包装原版 `HashCache`，并支持 `getManualResource` 从手写目录回退）+ `ResourceType{DATA,ASSET}`
- 生成器：Recipe/Model/BlockState/LootTable/Tag/Advancement/Language + `aggregator/TranslationsAggregator`（多 mod 语言文件合并）+ `standard/` 下 CoreLib 自己的采矿标签、语言、accesswidener 生成器
- 接入方式很巧：`mixin/FabricDataGenHelperMixin.java` 用 `@ModifyVariable(method="runInternal", at=STORE, ordinal=0)` 改写 Fabric datagen 的 entrypoint 列表，把 `GeneratorRegistrationHandler` 注入每个附属 mod 的 `DataGeneratorEntrypoint`（通过 `CoreLibDataGenerator` 接口），附属 mod 只要在 `onInitializeDataGenerator` 里往 handler 里 `addGenerator` 即可

## 5. Mixin / access widener

- 配置：`src/main/resources/modid.mixins.json`（`required:true`、`package ${mod_package}.mixin`、`defaultRequire:1`），common 6 个、client 8 个、server 1 个
- 代表：`MappedRegistryMixin`（`registerMapping` HEAD/TAIL，覆盖 Holder 引用）、`HolderReferenceMixin`、`TagLoaderMixin`（`build` HEAD）、`TagBuilderMixin`、`TagManagerMixin`、`ServerPlayerGameModeMixin`；客户端 `AbstractContainerScreenMixin`、`ModelManagerMixin`（在 `apply` 中 `ProfilerFiller.popPush` 调用点前注入模型覆盖，并 try/catch 免得模型加载反复失败）、`MinecraftMixin`、`MultiPlayerGameModeMixin`、`FabricDataGenHelperMixin`、`DataGeneratorMixin`；服务端 `ServerMainMixin`
- `modid.accesswidener`：打开 `AbstractContainerScreen` 私有拖拽字段与方法、`BlockBehaviour.Properties` 全部属性字段、`BlockBehaviour.getLootTable` extendable、`AbstractContainerMenu.containerId` mutable、`Slot.x/y` mutable、`Tag$Builder.entries`、`Ingredient.values`、`HashCache.newCache/oldCache` 等，并在构建期追加自动生成条目

## 6. 值得学的 5 条

1. **反射追加 entrypoint 抢"最后执行权"**：`CoreLibPreLaunch.java:34` + `registry/RegistryEntryPoints.java`，无需 Mixin 就获得跨 mod 的全局收尾时机（统一提交注册、检查未匹配注解）
2. **注解 + 反射字段注入做注册**：`registry/RegistryEntryAcceptor.java` + `Handler.gatherAnnotatedFields()`，附属 mod 声明 `@RegistryEntryAcceptor` 字段即可拿到注册对象，比 DeferredRegister 少写模板块
3. **覆盖原版注册表条目的完整闭环**：`Registries.VanillaRegistryWrapper.register`（保 id 的 `registerOrOverride`）+ `MappedRegistryMixin`/`CoreLibHolderReference`（重定向旧 Holder）+ `CoreLibAccessWidenerGenerator`（自动生成 accesswidener 条目）三者配合，替换原版方块/物品时不破坏既有引用
4. **HashCache 包装 + 手写目录回退的 datagen 设计**：`generator/ResourceCache.java`（`HashCacheWrapper`、`getManualResource`、`trackToBeGeneratedResource`），既能只重写变化文件，又允许用户手写文件覆盖生成结果
5. **Widget 五段渲染 + hasBeenHandled 责任链**：`gui/widget/Widget.java`、`gui/WidgetContainerScreen.java`，把"Inventory 界面里的自定义 GUI"从 AbstractContainerScreen 的渲染细节里解耦出来，槽位尺寸可变（`CustomSlot`）也一并解决

## 7. 公开 API 与接入方式

- 公开 API 根包：`com.supermartijn642.core.*`（约定 `mod_package=com.supermartijn642.core`）
- 扩展点：`RegistryEntryAcceptor`（注解）、`RegistrationHandler`/`ClientRegistrationHandler`/`GeneratorRegistrationHandler`（均为 `get(modid)` 单例，`ClientRegistrationHandler` 覆盖实体/方块实体渲染器、`CustomItemRenderer`、模型覆盖、RenderType、图集贴图、MenuScreen 注册）、`Registries.Registry<T>`、`PacketChannel`/`BasePacket`、`Widget`/`BaseWidget`、`BaseContainer`/`BaseContainerType`、`ResourceGenerator`/`ResourceCache`、`ResourceCondition`/`CustomTagEntrySerializer`、`RegistryOverrideHandlers`、`supermartijn642corelib` 的 mixin 扩展接口（`core/extensions`）
- 外部 mod 接入：在 `fabric.mod.json`/`mods.toml` 声明依赖 `supermartijn642corelib`，主类里调用上述静态 API；CoreLib 会自动发现依赖它的 mod 并接管注册收尾
- 无独立配置文件/Forge 配置系统（配置功能由作者的另一个库 Config Lib 承担，本仓库未见）
