# Low-Drag-MC/LDLib-Architectury 源码分析报告

## 1. 基本信息

- Mod 名：LowDragLib；mod_id `ldlib`；作者 KilaBash、WarmthDawn；version `1.0.52.a`
- 目标版本：**MC 1.20.1**，`enabled_platforms = fabric,forge`（`gradle.properties:9-13`）——即本快照**没有 NeoForge 子项目**，目录名带 Architectury 指的是工具链
- Gradle 插件：`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.6-SNAPSHOT` + `loom-vineflower` + `io.github.p03w.machete`（打 jar 时自动压缩）；映射用 `loom.layered{}` 叠 quilt-mappings + parchment `1.20.1:2023.09.03` + mojmap（`build.gradle:6-11, 52-60`）
- 许可证：GPL-3.0；maven_group `com.lowdragmc.ldlib`
- 编译依赖（`forge/build.gradle:89-119`）：`modCompileOnly` JEI / REI / EMI（可选兼容）、`modImplementation` AE2 + KubeJS、`include` MixinExtras `0.3.5`、lombok、architectury `@ExpectPlatform`。**LDLib 本身是给别的 mod 用的库**（GTCEu / Multiblocked 等 GUI+渲染+同步底层）

## 2. 源码规模与包结构

实测：**744 个 `.java`，72,669 行**（含 common/fabric/forge 三模块）。

按到第 3 层的包（文件数）：`gui/widget` 35、`gui/editor/*` 约 80（accessors 27 / configurator 26 / annotation 10 / runtime / ui/sceneeditor）、`utils` 43、`syncdata` 系列 69（含 accessor 25、managed 16、payload 12、field 5、annotation 8、rpc 1）、`core/mixins` 17（+accessor 8）、`gui/texture` 16、`gui/graphprocessor/*` 约 50、`client/scene` 7、`client/shader/management` 5、`jei` 11、`misc` 11、`networking` 11。

最大的文件：`client/scene/WorldSceneRenderer.java` 972、`gui/widget/WidgetGroup.java` 868、`SlotWidget` 787、`TankWidget` 746、`gui/graphprocessor/data/BaseNode.java` 722、`SceneWidget` 667、`client/utils/RenderBufferUtils` 663、`gui/compass/CompassSectionWidget` 652、`Widget` 648。

## 3. 入口与注册

**Forge**：`forge/.../LDLibForge.java:8-14` 只有 `LDLib.init()` + `DistExecutor.unsafeRunForDist(() -> ClientProxyImpl::new, () -> CommonProxyImpl::new)`。真正注册在 `CommonProxyImpl.java:36-70`：`DeferredRegister<Block/Item/BlockEntityType>` 注册一个 `renderer` 方块+BE（仅在 `Platform.isDevEnv()` 时额外注册 `test`/`test_2` 测试方块），然后 `CommonProxy.init()`，最后用 `ReflectionUtils.findAnnotationClasses(LDLibPlugin.class, ...)` **扫描 classpath 找 `@LDLibPlugin` 类并反射实例化**（异常直接 `catch (Throwable ignored)`）。

```java
// CommonProxy.java:11-21
LDLNetworking.init();
UIFactory.register(BlockEntityUIFactory.INSTANCE);
UIFactory.register(HeldItemUIFactory.INSTANCE);
UIFactory.register(UIEditorFactory.INSTANCE);
if (LDLib.isKubejsLoaded()) { UIFactory.register(BlockUIJSFactory.INSTANCE); ... }
AnnotationDetector.init();
TypedPayloadRegistries.init();
```

**Fabric**：`LDLibFabric.java:24-78` 用 `Registry.register` 直注册，插件入口走 `FabricLoader.getInstance().getEntrypoints("ldlib_pugin", ILDLibPlugin.class)`（字符串拼写就是 `ldlib_pugin`，是既定 API 名）。注册顺序模式：`init()` → 注册对象 → `CommonProxy.init()` → 加载插件 → `TypedPayloadRegistries.postInit()`。

## 4. 核心系统

1. **syncdata 字段级同步（全库最有价值）**：`syncdata/annotation/` 提供 8 个注解——`@DescSynced`（同步到客户端）、`@Persisted`（存档，可 `key()` 改名）、`@DropSaved`、`@LazyManaged`（不每 tick 检查）、`@ReadOnlyManaged`（自定 onDirty/serialize/deserialize 方法名）、`@RequireRerender`、`@UpdateListener`、`@RPCMethod`。`ManagedFieldUtils.getManagedFields(Class)`（`ManagedFieldUtils.java:21-33`）反射扫字段生成 `ManagedKey`；`ManagedFieldHolder(clazz, parent)`（`field/ManagedFieldHolder.java:39-42`）用 `merge()` 把父类字段并进来，所以 BE 可以是继承链。运行时 `FieldManagedStorage` 用 **`BitSet dirtySyncFields` + `ReentrantLock`** 记录脏字段，`getFieldRefs()` 给每个字段包一个 `IRef` 并挂 `setOnSyncListener` 回调，回调里取数组下标写 BitSet。
2. **自动同步的 BE 接口族**：`syncdata/blockentity/` 的 `IAutoSyncBlockEntity.defaultServerTick()`（`IAutoSyncBlockEntity.java:38-49`）遍历 `getNonLazyFields()` 调 `field.update()`，有脏字段就发 `SPacketManagedPayload.of(this, false)` 到 tracking chunk；`syncNow(force)` 支持强制全量；`IAsyncAutoSyncBlockEntity` 允许工作线程改字段；`IRPCBlockEntity` + `RPCSender` 走 `SPacketRPCMethodPayload`，把 `@RPCMethod` 方法当 RPC 调。
3. **TypedPayload 多态序列化**：`ITypedPayload<T>` 同时有 `writePayload(FriendlyByteBuf)` 与 `serializeNBT()`；`TypedPayloadRegistries` 用 `Byte2ObjectMap<Supplier<ITypedPayload<?>>>` 做 **byte id ↔ Class 双向表**（`payload/` 下 12 个实现：Primitive/String/NbtTag/ItemStack/FluidStack/BlockPos/UUID/Enum/Array/ObjectTyped），网络包里只写 `byte id + 数据`。
4. **Accessor 体系（类型分派）**：`syncdata/accessor/` 25 个 `IAccessor` 按类型处理（`PrimitiveAccessor` 拆 8 种原语、`BuiltinRegistryAccessor<Block/Item/Fluid>`、`ArrayAccessor`/`CollectionAccessor` 用 `Util.memoize` 缓存复合 accessor，`IManagedAccessor` 递归进嵌套 `IManaged`）。
5. **GUI 体系**：`gui/widget/`（`Widget`/`WidgetGroup`/`SlotWidget`/`TankWidget`/`SceneWidget`）+ `gui/texture`（`IGuiTexture` + Gson TypeAdapter，可 JSON 描述）+ `gui/editor`（**数据驱动的 UI 设计器**：`annotation` 声明可配置字段、`configurator` 25 个 UI 属性编辑器、`runtime/AnnotationDetector` 扫描 `@Configurator`）。`UIFactory.openUI()`（`gui/factory/UIFactory.java:38-66`）是关键：mixin accessor 拿 `containerCounter`，把 holder 同步数据和 `mainGroup.writeInitialData()` **合并进同一个 buffer** 再发 `SPacketUIOpen`，减少一次握手。
6. **客户端渲染**：`client/scene/WorldSceneRenderer`（972 行，把世界渲染进 GUI/FBO，含 `FBOWorldSceneRenderer`/`ImmediateWorldSceneRenderer` 两种后端 + `ParticleManager`）、`client/shader/management`（`ShaderManager`/`ShaderProgram`/`ShaderUBO`/`ShaderSSBO`/`Shader` 自建 shader 抽象）、`client/renderer`（`IRenderer`+`ISerializableRenderer` + `IItemRendererProvider`/`IBlockRendererProvider` 让外部注册自定义渲染）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`networking/INetworking` 用 `@ExpectPlatform` 分平台实现；`LDLNetworking.init()` 注册 4 个 S2C（`SPacketUIOpen`/`SPacketUIWidgetUpdate`/`SPacketManagedPayload`/`SPacketRPCMethodPayload`）+ 1 个 C2S（`CPacketUIClientAction`）；`IPacket` 抽象 + `PacketIntLocation` 基类（BlockPos 定位）。`SPacketManagedPayload` 用 NBT 中转：`"p"` 坐标 / `"t"` BE 类型 / `"c"` `BitSet.valueOf(byte[])` 变更位 / `"l"` payload 列表 / `"e"` 自定义附加数据（`writeCustomSyncData`）。
- 数据驱动：`gui/editor` 的 UI/场景可存成 JSON，靠 `LDLib.GSON`（自定义 `IGuiTextureTypeAdapter`、`FluidStackTypeAdapter`、`ItemStackTypeAdapter`、`ResourceLocation`）序列化；静态配置落在游戏目录 `ldlib/`（`LDLib.getLDLibDir()`）。
- 配置：无独立 config 系统；`test/` 包内是开发环境测试用 Block/BE/UI。
- datagen：**无**（无 `data/`、无 DataProvider）。

## 6. Mixin

- `common/src/main/resources/ldlib-common.mixins.json`：`package com.lowdragmc.lowdraglib.core.mixins`，带 **`plugin: LDLibMixinPlugin`**；client 段 11 个（`BlockEntityRendererDispatcherMixin`、`BlockModelShaperMixin`、`ItemModelShaperMixin`、`ParticleEngineMixin`、`SpriteResourceLoaderMixin`、`TextureAtlasMixin`、`WorldRendererMixin`、`LanguageMixin` + 5 个 accessor + EMi 2 个）；mixins 段 `BlockEntityMixin`、`PackConfigMixin`、`ReloadableResourceManagerMixin`、`WorldLoaderMixin` + `AbstractContainerMenuAccessor`/`ServerPlayerAccessor`/`SlotAccessor` + JEI/EMI 各若干
- `forge/src/main/resources/ldlib.mixins.json`：另加 `BlockRenderDispatcherMixin`、`ModelBakerImplMixin`、`kjs.SlotWidgetMixin`
- 条件加载：`core/mixins/MixinPluginShared.java:22-31` 用 `@ExpectPlatform isModLoaded()` 静态常量 `IS_IRIS_LOAD / IS_OCULUS_LOAD / IS_OPT_LOAD / IS_SODIUM_LOAD`，供 mixin plugin 在 `shouldApplyMixin` 里按环境取舍

## 7. 值得学的 5 条具体做法

1. **注解 + 反射 + BitSet 的"零样板字段同步"**：BE 只要 `implements IAutoSyncBlockEntity` + 字段打 `@DescSynced`，其余全自动（`syncdata/blockentity/IAutoSyncBlockEntity.java:30-49`）。是替代 `getUpdateTag/saveAdditional` 手写 NBT 的最佳模板。
2. **`ManagedFieldHolder(clazz, parentHolder)` 支持继承链**（`field/ManagedFieldHolder.java:39-42`）：父类字段自动并入子类，允许 BE 继承（Create/LDLib 系 BE 都这么写）。
3. **payload 用 byte id 而非类名序列化**：省带宽、避免 refmap/包名问题，`TypedPayloadRegistries.nextId()` 到 `Byte.MAX_VALUE` 抛异常（`TypedPayloadRegistries.java:46-53`）。
4. **`UIFactory` 集中管理"打开界面"协议**：`ResourceLocation → 工厂` 注册表 + 单一 `openUI()` 入口，把容器 ID 申请、数据打包、Forge 事件顺序都封在一处（`gui/factory/UIFactory.java:38-66`）。
5. **反射扫描注解类做插件发现**（`@LDLibPlugin` + `ReflectionUtils.findAnnotationClasses`，Forge）与 **fabric entrypoint `ldlib_pugin`** 并存：前者零配置、后者显式，跨平台各取所长（`CommonProxyImpl.java:54-61`、`LDLibFabric.java:57-59`）。

## 8. 库 / API 说明

对外扩展点（其他 mod 的接入面）：
- 同步与 BE：`com.lowdragmc.lowdraglib.syncdata.*`——`IManaged`/`IManagedStorage`/`IRef`、`syncdata.annotation.*`、`syncdata.blockentity.IAutoSyncBlockEntity / IAsyncAutoSyncBlockEntity / IAutoPersistBlockEntity / IRPCBlockEntity`、`syncdata.rpc.RPCSender`
- GUI：`gui.widget.*`（`Widget`/`WidgetGroup`/`SlotWidget`/`TankWidget`）、`gui.modular.ModularUI`、`gui.factory.UIFactory` + `BlockEntityUIFactory`/`HeldItemUIFactory`/`UIEditorFactory`
- 渲染：`client.renderer.IRenderer` / `ISerializableRenderer` / `IItemRendererProvider` / `IBlockRendererProvider`、`client.scene.ISceneBlockRenderHook`/`ISceneEntityRenderHook`、`gui.texture.IGuiTexture`
- 插件：`plugin.ILDLibPlugin` + Forge 侧 `@LDLibPlugin` 注解 / Fabric 侧 entrypoint 名 `ldlib_pugin`；另有 `plugin.ILDLibPlugin`（原文如此）
- 脚本：`kjs/` 包提供 KubeJS 插件与 `BlockUIJSFactory`/`ItemUIJSFactory`，UI 可从 JS 构建；注释里用 `dev.latvian.mods.rhino.util.HideFromJS` 控制 JS 可见性
- 平台抽象：`Platform` 类（`isClient/isRemote/getGamePath/isModLoaded/isForge/isDevEnv`），实现由 `PlatformImpl` 分平台提供
