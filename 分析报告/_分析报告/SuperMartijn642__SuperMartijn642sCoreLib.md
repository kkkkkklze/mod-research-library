# SuperMartijn642/SuperMartijn642sCoreLib 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：SuperMartijn642's Core Lib / `supermartijn642corelib`（`gradle.properties`：`mod_version=1.1.24`、`maven_group=com.supermartijn642`、`mod_package=com.supermartijn642.core`）
- 作者 / 许可证：SuperMartijn642；**All rights reserved**（`gradle.properties:mod_license`）
- 目标版本：Minecraft **1.18.2**、Java 17、resource_pack_format 8；加载器 = **Fabric + Quilt**（`fabric_loader_version=0.15.11`、`fabric_api_version=0.77.0+1.18.2`、`quilt-loader 0.20.0-beta.3` 仅 `modCompileOnly`）
- Gradle：`fabric-loom 1.14-SNAPSHOT` + `me.modmuss50.mod-publish-plugin 0.5.2`（CurseForge/Modrinth 发布，`curseforge_project_id=454372`、`modrinth_project_id=rOUBggPv`）；`fabric.mod.json`、`modid.mixins.json`、`pack.mcmeta` 全由 `build.gradle` 的 `expand` 占位符生成并 `rename` 去 `modid` 前缀
- 编译依赖（重点）：`minecraft 1.18.2` + `loom.officialMojangMappings()`；`fabric-loader`、`fabric-api`；**architectury-api**（`curse.maven:architectury-api-419699:4521464`，`modImplementation`）——但代码里只用 `CommonUtils.isModLoaded("architectury")`（`CoreLib.java:30`）探测，发布元数据 required 仅 fabric-api，故 architectury 实际是可选兼容项
- 定位：库模组（`fabric.mod.json` 的 `modmenu.badges=["library"]`），同作者 mod 的公共前置

## 2. 源码规模与包结构

实测 **126 个 `.java` / 18170 行**。

包（第 3 层，文件数）：`gui/widget` 16、`mixin` 15、`gui` 12、`generator` 10、`render` 9、`registry` 8、`util` 8、`data/condition` 8、`block` 7、根包（CoreLib/CommonUtils/ClientUtils/CoreSide/TextComponents/EnergyFormat/CoreLibPreLaunch）7、`network` 6、`item` 5、`data/tag` 5、`extensions` 4、`generator/standard` 3、`generator/aggregator` 2、`data/recipe` 1。

最大文件：`generator/RecipeGenerator.java` 1584、`generator/ModelGenerator` 983、`BlockStateGenerator` 706、`registry/ClientRegistrationHandler` 693、`generator/TagGenerator` 688、`LootTableGenerator` 586、`gui/CustomSlotImpl` 556、`AdvancementGenerator` 529、`registry/RegistrationHandler` 510、`gui/widget/premade/TextFieldWidget` 407。

## 3. 入口与注册

`fabric.mod.json` entrypoints：`main = com.supermartijn642.core.CoreLib`、`preLaunch = com.supermartijn642.core.CoreLibPreLaunch`。注册框架是自研的"按 modid 分发"三个 Handler，**无 DeferredRegister / Registrate**：

```java
// CoreLib.java:34-40
RegistrationHandler handler = RegistrationHandler.get("supermartijn642corelib");
handler.registerRecipeSerializer("conditional", ConditionalRecipeSerializer.INSTANCE);
handler.registerResourceConditionSerializer("mod_loaded", ModLoadedResourceCondition.SERIALIZER);
```

时序靠 preLaunch 反射改写 loader 的入口点表拿到：`CoreLibPreLaunch.onPreLaunch()` 反射取 `FabricLoaderImpl.entrypointStorage` / `EntrypointStorage.entryMap`（Quilt 走 `QuiltLoaderImpl` 同名字段），把 `RegistryEntryPoints` 塞进 `main` 与 `client` 列表（`CoreLibPreLaunch.java:61-86`）；`RegistryEntryPoints implements ModInitializer, ClientModInitializer`，只负责调用 `CoreLib.afterInitialize()` / `afterInitializeClient()`（`registry/RegistryEntryPoints.java:9-19`）。完整时序：`CoreLib.beforeInitialize()`（收集 `@RegistryEntryAcceptor` 字段）→ 各 mod initializer → `afterInitialize()`（`RegistrationHandler.registerInternal()` 真正注册 + `reportMissing()`）。

## 4. 核心系统

1. **注册系统**（`registry/RegistrationHandler.java`）：每 modid 单例，`REGISTRATION_HELPER_MAP.computeIfAbsent`（:64）；容器只存 `Supplier<?>`（`entryMap`）与回调（`callbacks`），真正注册延后到 `registerInternal()`；`registerXxxOverride(namespace, id, ...)` 允许注册/覆盖其它命名空间；`registerXxxCallback(Consumer<Helper<T>>)` 让调用方在注册时拿到成品对象做二次加工（:68-69、:91）。
2. **注解式注册项注入**（`registry/RegistryEntryAcceptor.java`）：先筛出"metadata 里依赖 supermartijn642corelib 的 mod"（:65-78），再扫描这些 mod 的 main 入口点类中 public、非 final、类型匹配的 `@RegistryEntryAcceptor(namespace, identifier, registry)` 字段/方法，注册后统一注入；字段必须在 mod 初始化前完成收集。
3. **网络**（`network/PacketChannel.java`，319 行）：通道 = modid + name；包体 = `int index + payload`，index 就是注册顺序（`packetsByIndex` / `packetsByClass`，:252-285），两侧注册顺序必须一致；`registerMessage(Class, Supplier, PacketDirection, boolean shouldBeQueued)` 为每个包声明允许方向与"是否回主线程"（:106-114），发送/接收双方都用 `checkRegistration` 校验；`BasePacket#verify` 可静默丢弃；发送便捷方法 `sendToPlayer/sendToAllPlayers/sendToDimension/sendToAllTrackingEntity/sendToAllNear`（内部用 Fabric `PlayerLookup`，:157-242）。
4. **GUI 框架**（`gui` 12 + `gui/widget` 16 + `premade`）：`BaseContainer`/`BaseContainerType` + `Item|Object|BlockEntityBaseContainer`、`WidgetScreen`/`WidgetContainerScreen`、`CustomSlot`/`CustomSlotImpl`（:556 行，复刻原版槽位点击/拖拽逻辑），配 `modid.accesswidener:4-13` 打开 `AbstractContainerScreen` 的 `draggingItem`/`isSplittingStack`/`snapback*` 私有字段；premade 控件含 `TextFieldWidget`(407)、`ScrollbarWidget`(330)。
5. **datagen 生成器层**（`generator/*`）：抽象 `ResourceGenerator` + `ResourceCache` + `ResourceType`，具体实现 Recipe/Model/BlockState/Tag/LootTable/Advancement/Language（含 `generator/standard` 里 CoreLib 自用 3 个、`generator/aggregator`）；入口 `GeneratorRegistrationHandler.get(modid).addGenerator(cache -> …)`，内部 `Either<Function<ResourceCache,ResourceGenerator>, Function<FabricDataGenerator,DataProvider>>` 同时兼容自研生成器与原生 Fabric DataProvider（`registry/GeneratorRegistrationHandler.java:56`）；`generateFaceModels` 等之外，`mixin/DataGeneratorMixin.java:47-99` 改 `HashCache.keep/purgeStaleAndWrite` 支持增量与手工资源目录。
6. **数据驱动条件**（`data/condition` 8 个）：`ResourceCondition` + `ResourceConditionSerializer`，内置 `mod_loaded`/`not`/`or`/`and`/`tag_populated`；配 `data/recipe/ConditionalRecipeSerializer` 做条件配方。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络、datagen 见 4-(3)(5)。数据驱动 = `ResourceCondition`（配方/数据文件条件）+ `CustomTagEntry`（自研 tag entry 类型 `"namespace"`，由 `TagBuilderMixin`/`TagLoaderMixin`/`TagManagerMixin` 三处 hook 支撑解析）+ `RegistryOverrideHandlers`（注册表条目覆盖）。**配置：无**自研 config 系统（`fabric.mod.json` 无 ModMenu config 入口）。

## 6. Mixin

配置：`src/main/resources/modid.mixins.json`（构建时重命名为 `supermartijn642corelib.mixins.json`），分 `mixins`/`client`/`server` 三段共 15 个类，refmap 由 loom 生成（`defaultRefmapName`）。

代表 hook：
- `MappedRegistryMixin`（`@Mixin(MappedRegistry.class)`）：`registerMapping(...)` 的 `HEAD`/`TAIL` 注入，`registeringOverrides` 时移除旧 `Holder.Reference`、把旧 reference 重定向到新值（`CoreLibHolderReference.supermartijn642corelibOverride`），这是 `registerXxxOverride` 的实现基础（:38-65）
- `TagBuilderMixin` → `Tag.Builder#parseEntry`；`TagLoaderMixin#build`；`TagManagerMixin`（自定义 tag entry）
- `ServerPlayerGameModeMixin` / `MultiPlayerGameModeMixin#useItemOn`（`@Redirect` `Player.getMainHandItem`）
- `LevelRendererMixin#renderLevel`（`@ModifyVariable` + `@Inject` 到 `pushPose`/`mulPoseMatrix` 区间）、`GameRendererMixin#render`、`ModelManagerMixin#apply`
- `DataGeneratorMixin#run`、`FabricDataGenHelperMixin`、`ServerMainMixin`（`@Mixin(Main.class)`）、`MinecraftMixin#<init>`、`AbstractContainerScreenMixin#isHovering`

其他访问手段：`src/main/resources/modid.accesswidener` 放开 `AbstractContainerScreen` 私有字段、`Slot.x/y` mutable、`Tag$Builder.entries`、`Ingredient.values` 等，且 `build.gradle:66-70` 会把 datagen 生成的额外 AW 条目 filter 回该文件。

## 7. 值得学的 5 条具体做法

1. **preLaunch 反射把自己插进 loader 的 entrypoint 表**，从而拿到"所有 mod 初始化前 / 后"两个精确时机：`CoreLibPreLaunch.java:61-86` + `registry/RegistryEntryPoints.java`。适合需要前置收集或后置统一注册的库。
2. **注册容器只放 Supplier，真正注册延后**，并同时提供 Override 与 Callback 两套扩展口：`registry/RegistrationHandler.java:68-69、:91-93`。库模组要让别人也能注册/覆盖时必用。
3. **注解 + 反射只扫描"依赖我的 mod 的入口点类"** 做字段注入，避免遍历全体类：`registry/RegistryEntryAcceptor.java:65-116`。
4. **网络包用注册顺序索引分发** + 每包声明方向与 `shouldBeQueued`：`network/PacketChannel.java:106-114、252-285`，新增包无需维护 packet id 表。
5. **用 accesswidener 代替大量 `@Accessor` mixin**，并让 datagen 生成 AW 条目后 filter 合并：`modid.accesswidener` + `build.gradle:66-70`。容器 GUI 类魔改的通用省钱手法。

## 8. 公开 API 与外部接入方式（库模组）

- 公开包：`com.supermartijn642.core.*`（`mod_package`），外部 mod 在 `fabric.mod.json` 的 `depends` 加 `supermartijn642corelib`，然后在自己的 main entrypoint 里 `RegistrationHandler.get("<yourmodid>").registerItem(...)`；字段式注册用 `@RegistryEntryAcceptor` + `CoreLib.beforeInitialize()` 时机。
- 网络扩展点：`PacketChannel.create(modid[, "main"])` + `registerMessage(...)`；基类 `BasePacket`/`BlockPosBasePacket`/`BlockEntityBasePacket`；`PacketContext`（side/player/server + `queueTask`）；`PacketDirection`。
- 数据扩展点：`ResourceCondition`/`ResourceConditionSerializer`（+ `data/condition/*` 现成实现）、`ConditionalRecipeSerializer`、`CustomTagEntrySerializer`。
- GUI / 渲染扩展点：`gui/*`（继承 `BaseContainer`/`WidgetScreen` 得到跨版本一致 API）、`render/CustomItemRenderer`、`CustomBlockEntityRenderer`、`CustomRendererBakedModelWrapper`、`RenderConfiguration`/`RenderStateConfiguration`、`render/RenderUtils`。
- 生成器扩展点：`GeneratorRegistrationHandler.get(modid).addGenerator(cache -> new YourGenerator(...))` + `ResourceCache`（按 `ResourceType` 去重/合并）。
- 注册覆盖：`RegistryOverrideHandlers`、`Registries.Registry<?>` 描述对象（含 `ValueClass` 与 `RegistryUtil` 命名校验），外部可直接复用做类型安全注册。
- 依赖它的具体 mod 名单与接入代码不在本仓库（**未确认**）；`fabric.mod.json` 无 `custom.modmenu.parent`。
