# YUNG-GANG/Paxi 源码分析报告

## 1. 基本信息

- Mod 名：Paxi；`mod_id = paxi`；作者 YUNGNICKYOUNG；版本 `6.1.0`（gradle.properties）；`mod_description = Drag-and-drop your data packs and let Paxi do the rest! Global data packs made easy.`
- 目标：**多加载器**——Fabric（`fabric_version=0.150.0`、loader `0.18.6`）+ **NeoForge**（`neoforge_version=26.1.2.75`，`neoforge_loader_version_range=[4,)`）；MC `26.1.2`（`mc_version_range=[26.1,)`），`java_version=25`
- Gradle：Fabric Loom `1.15.5` + ModDevGradle `2.0.141` + `net.darkhax.curseforgegradle` + `com.modrinth.minotaur`；同样是 **jaredlll08 Multiloader 模板**（`Common`/`Fabric`/`NeoForge` 三子项目 + `buildSrc` 的 `multiloader-common.gradle`）
- 许可证：**LGPLv3**（LICENSE.md）
- 编译依赖（`NeoForge/build.gradle` 与 `Fabric/build.gradle`）：**YUNG's API**（`com.yungnickyoung.minecraft.yungsapi:YungsApi:${mc_version}-{Fabric|NeoForge}-6.1.0`，neoforge.mods.toml 里作为 `required` 前置）；Fabric 侧额外 ClothConfig（`26.1.154`）、ModMenu（`18.0.0-beta.1`）、`org.reflections:reflections:0.10.2`（`include` 打包）

## 2. 源码规模与包结构

实测：`24` 个 `.java`，共 `945` 行。

包（`com.yungnickyoung.minecraft.paxi` 下）：Common——`paxi`(3)、`mixin/accessor`(1)、`module`(1)、`services`(1)；Fabric——`paxi`(1)、`client`(1)、`config`(1)、`config/gui`(1)、`mixin`(2)、`mixin/client`(1)、`module`(1)、`services`(1)、`util`(1)；NeoForge——`paxi`(1)、`config`(2)、`mixin`(1)、`module`(1)、`services`(1)。

最大文件：`Common/.../PaxiRepositorySource.java`(237)、`Fabric/.../mixin/MixinPackRepositoryFabric.java`(134)、`NeoForge/.../mixin/MixinPackRepositoryNeoForge.java`(107)、`Fabric/.../mixin/MixinModResourcePackCreatorFabric.java`(46)。

## 3. 入口与注册

- Fabric：`Fabric/src/main/java/com/yungnickyoung/minecraft/paxi/PaxiFabric.java`，`implements ModInitializer`；`onInitialize()` 里用 `FabricLoader` 填 `PaxiCommon` 的路径常量，然后 `ConfigModuleFabric.init()`
- NeoForge：`NeoForge/src/main/java/com/yungnickyoung/minecraft/paxi/PaxiNeoForge.java:14-33`，`@Mod(PaxiCommon.MOD_ID)`，构造器注入 `IEventBus` 与 `ModContainer`：

```java
PaxiCommon.BASE_PACK_DIRECTORY = new File(FMLPaths.CONFIGDIR.get().toString(), "paxi");
PaxiCommon.DATA_PACK_DIRECTORY = Paths.get(BASE_PACK_DIRECTORY.toString(), "datapacks");
PaxiCommon.DATAPACK_ORDERING_FILE = new File(BASE_PACK_DIRECTORY, "datapack_load_order.json");
ConfigModuleNeoForge.init(eventBus, container);
eventBus.addListener(PaxiNeoForge::addPaxiPackSource);   // AddPackFindersEvent
```

- **没有物品/方块注册**，注册的是"包源"：`addPaxiPackSource(AddPackFindersEvent)` 按 `PackType.CLIENT_RESOURCES` / `SERVER_DATA` 分别 `event.addRepositorySource(new PaxiRepositorySource(...))`。Fabric 没有对应事件，只能靠 mixin（见第 6 节）。

## 4. 核心系统

**4.1 Pack 源：重写仓库源而不是新建 registry** `Common/.../PaxiRepositorySource.java`
- `extends FolderRepositorySource`，构造时 `super(packsFolder, packType, PaxiPackSource.PACK_SOURCE_PAXI, null)`；父类字段是私有的，于是用 accessor（见第 6 节）读取：`((FolderRepositorySourceAccessor) this).getFolder()/getPackType()`（`PaxiRepositorySource.java:55、81、122`）。
- 重写 `loadPacks(Consumer<Pack>)`：先用 `PACK_FILTER`（zip 文件 **或** 含 `pack.mcmeta` 的目录）筛文件，再为每个 pack 构造 `PackLocationInfo(packName, Component.literal(packName), PACK_SOURCE_PAXI, Optional.empty())` 与

```java
PackSelectionConfig packSelectionConfig = new PackSelectionConfig(true, Pack.Position.TOP, false);
Pack pack = Pack.readMetaAndCreate(packLocationInfo, createPackResourcesSupplier(packPath),
                                   ((FolderRepositorySourceAccessor) this).getPackType(), packSelectionConfig);
```

即 **required=true + Position.TOP**，所以 Paxi 包永远启用且置顶——这正是"drop-and-play"的关键。
- `createPackResourcesSupplier(Path)` 按类型分派 `FilePackResources.FileResourcesSupplier`（zip）/ `PathPackResources.PathResourcesSupplier`（目录），否则抛 `IllegalArgumentException`。
- 排序：读 `datapack_load_order.json`（内部类 `PackOrdering`，`@SerializedName("loadOrder")`，经 YUNG's API 的 `JSON.loadObjectFromJsonFile`）；失败/键名写错时**不崩**，改为记录日志并按无序加载（`PaxiRepositorySource.java:137-146`）；最终顺序为 `Stream.of(unorderedPacks, orderedPacks).flatMap(...)`，即"未列出的在前、有序的在后"。`filesFromNames` 先在**游戏根目录**找（支持绝对路径/packwiz 布局），再退回 `config/paxi/datapacks`。
- 额外兼容：`PaxiCommon.CONFIG.loadFromBaseDatapacksDirectory` 为真且类型是 `SERVER_DATA` 时，把 `<game>/datapacks`（CurseForge 新数据包目录）也纳入（`PaxiRepositorySource.java:107-118`）。

**4.2 让有序包真正生效：注入 PackRepository** `NeoForge/.../mixin/MixinPackRepositoryNeoForge.java` / `Fabric/.../mixin/MixinPackRepositoryFabric.java`
- 两者都 `@Mixin(value = PackRepository.class, priority = 2000)`（注释说明：priority 2000 保证在所有其他 mixin 之后运行），`@Shadow @Final private Set<RepositorySource> sources;` 与 `@Shadow private Stream<Pack> getAvailablePacks(Collection<String>)`。
- `@Inject(at=@At("RETURN"), method="discoverAvailable", cancellable=true)`：从 `sources` 里 `filter(provider -> provider instanceof PaxiRepositorySource)` 找回 Paxi 源，然后按 `vanillaPackId.equals("file/" + paxiPackId)` 去掉重复项（**注意 vanilla 包 id 带 `file/` 前缀而 Paxi 包 id 只有文件名**，NeoForge 用 `LinkedHashMap`、Fabric 用 `TreeMap` 重建返回 map）。
- `@Inject(at=@At("RETURN"), method="rebuildSelected", cancellable=true)`：因为 vanilla 用 TreeMap 按字典序存包，会破坏用户指定顺序；于是把有序 Paxi 包先 `removeAll` 出来，再用 `pack.getDefaultPosition().insert(sortedEnabledPacks, pack, Pack::selectionConfig, false)` **按每个 pack 自己的 Position 插回**（NeoForge 版本还处理 `pack.getChildren()` 与 `Pack::streamSelfAndChildren`），最后 `cir.setReturnValue(ImmutableList.copyOf(...))`。
- Fabric 版额外有 `@Unique getPaxiRepositorySource()`：先找 `net.fabricmc.fabric.impl.resource.pack.ModResourcePackCreator` 并转 `IPaxiSourceProvider` 取源；取不到且是客户端时再走 `ClientMixinUtil.getClientRepositorySource(sources)`（**把客户端类调用隔离到单独 util，避免 dedicated server 上类加载崩溃**）。

**4.3 Fabric 侧无事件可用 → 从 Fabric API 内部挂源**
- `MixinModResourcePackCreatorFabric`：`@Mixin(ModResourcePackCreator.class) implements IPaxiSourceProvider`，在 `<init>(PackType;Z)` 的 RETURN 处按类型建 `PaxiRepositorySource`，并在 `loadPacks` 的 RETURN 处调用它（`paxi_loadPaxiPacksFabric`）。
- `mixin/client/MixinClientPackSourceFabric`：`@Mixin(BuiltInPackSource.class)`，`loadPacks` RETURN 时 `isClientPackSource(this)`（`instanceof ClientPackSource`）判断后才加载资源包。
- 两个 mixin 都用 `@Unique` 字段 + 实现自定义接口 `Fabric/.../util/IPaxiSourceProvider.getPaxiSource()`，把 mixin 类当作"附加数据容器"用——`@Mixin` 类实现 mod 自定义接口是被 Mixin 允许的正规用法（见 `Common/src/main/resources/paxi.mixins.json` 与 Fabric 两份 json）。

**4.4 展示层** `Common/.../PaxiPackSource.java`：`PackSource.create(decorateWithPaxiSource(), true)`，用 `Component.translatable("pack.nameAndSource", ...)` + `ChatFormatting.LIGHT_PURPLE` 让 Paxi 包在资源包界面显示为紫色并标注 "paxi"。

**4.5 双套配置结构**：公共侧 `Common/.../module/ConfigModule.java` 只有 POJO `public boolean loadFromBaseDatapacksDirectory = true;`；平台侧 `NeoForge/.../config/PaxiConfigNeoForge.java`（`ModConfigSpec` + `ConfigGeneralNeoForge`）与 `module/ConfigModuleNeoForge.java`：`container.registerConfig(ModConfig.Type.COMMON, SPEC, "paxi-neoforge-26_1.toml")`（**文件名带版本常量 `PaxiCommon.VERSION_CONFIG_STR`**，避免跨 MC 版本配置冲突），并监听 `ModConfigEvent`（热更新）与 `NeoForge.EVENT_BUS` 的 `LevelEvent.Load` 调 `bakeConfig()`，把 spec 值刷进 POJO。Fabric 侧对应 `config/PaxiConfigFabric`（ClothConfig）+ `config/gui/PaxiModMenu`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（不注册 channel/包）。
- 数据驱动：本身就是"数据包加载器"；对自身而言无新增 registry/无 codec，配置读取依赖 YUNG's API 的 `JSON.loadObjectFromJsonFile` / `JSON.createJsonFileFromObject`。
- 配置：见 4.5，公共 POJO + 平台 config（NeoForge ModConfigSpec / Fabric ClothConfig），配置文件首次运行自动创建。
- datagen：**无**（`NeoForge/build.gradle` 里保留了模板的 `data` runConfig 与 `src/generated/resources`，但本项目无 provider）。多加载器模板的 `processResources` 用 `expandProps` 把 gradle.properties 值展开进 `neoforge.mods.toml`/`fabric.mod.json`/`*.mixins.json`。

## 6. Mixin

三份配置：`Common/src/main/resources/paxi.mixins.json`（`compatibilityLevel JAVA_17`，mixins `accessor.FolderRepositorySourceAccessor`）、`Fabric/src/main/resources/paxi_fabric.mixins.json`（mixins `MixinModResourcePackCreatorFabric`、`MixinPackRepositoryFabric`；client `client.MixinClientPackSourceFabric`）、`NeoForge/src/main/resources/paxi_neoforge.mixins.json`（`MixinPackRepositoryNeoForge`）；`neoforge.mods.toml` 用两个 `[[mixins]]` 同时挂载 common + neoforge 两份。

代表性 hook：
- `Common/.../mixin/accessor/FolderRepositorySourceAccessor.java`：`@Mixin(FolderRepositorySource.class)` 接口 + `@Accessor getPackType()/getFolder()`，用来读父类私有字段（**比 `@Shadow` 更适合跨类复用**）。
- `PackRepository#discoverAvailable`（`@At("RETURN")`, cancellable）与 `PackRepository#rebuildSelected`（`@At("RETURN")`, cancellable）——`priority = 2000`。
- `ModResourcePackCreator#<init>(Lnet/minecraft/server/packs/PackType;Z)V` 与 `#loadPacks`（Fabric）。
- `BuiltInPackSource#loadPacks`（Fabric client）。

## 7. 值得学的 5 条做法

1. **用"自定义 RepositorySource + 强制 enabled/top"实现全局包加载**：`PaxiRepositorySource.loadPacks` 里 `new PackSelectionConfig(true, Pack.Position.TOP, false)`；适用：任何想"装了就生效、用户不用去界面勾选"的全局数据/资源包。
2. **有序加载靠 `Pack.getDefaultPosition().insert(...)` 重排，而不是新建数据结构**：`MixinPackRepositoryNeoForge.java:98-103`；适用：需要覆盖原版字典序、又要保留原版插入语义的场景。
3. **mixin `priority = 2000` 明确声明"我要最后一个跑"**：`MixinPackRepositoryNeoForge.java:33` / `MixinPackRepositoryFabric.java:34`（comments 已写明原因），避免与 Fabric API/其他 mod 的同点注入冲突。
4. **把客户端类引用隔离到 `ClientMixinUtil`**：`MixinPackRepositoryFabric.java:112` 的注释与 `Fabric/.../client/ClientMixinUtil.java`；适用：多加载器 mod 在通用代码里要碰客户端类，防止 dedicated server 崩。
5. **mixin 类实现自定义接口做"附加状态容器"**：`MixinModResourcePackCreatorFabric implements IPaxiSourceProvider` + `@Unique` 字段，让别处通过接口安全取回注入对象；适用：需要把 mod 对象挂到原版实例上，又不想用反射/静态 map。

## 8. 公开 API

非库 mod，无对外 API 包。对外的"接口"是文件系统约定：`<config>/paxi/datapacks`、`<config>/paxi/resourcepacks`、`datapack_load_order.json` / `resourcepack_load_order.json`（`{"loadOrder": ["a.zip", ...]}`），以及 `<game>/datapacks` 的额外扫描；编译期**反向依赖 YUNG's API**（`yungsapi` 为 required 前置，使用了其 `com.yungnickyoung.minecraft.yungsapi.io.JSON` 工具类与多加载器 `services` 骨架）。
