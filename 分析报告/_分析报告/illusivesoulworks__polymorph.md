# illusivesoulworks/polymorph 源码分析

分析对象：`_参考仓库/_bulk/illusivesoulworks__polymorph`（1.21.1 分支，版本 1.2.0+1.21.1）

## 1. 基本信息

| 项 | 值 |
| --- | --- |
| Mod 名 / mod_id | Polymorph / `polymorph` |
| 作者 / 许可 | Illusive Soulworks / LGPL-3.0-or-later |
| 目标 | MC 1.21.1，Java 21，三加载器：Fabric Loader 0.15.11、Forge 52.0.1、NeoForge 21.1.8 |
| 构建 | 多模块 Gradle：`common` / `fabric`(loom 1.7) / `forge` / `neoforge`(userdev 7.0.145)，约定插件在 `buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`；mappings 用官方 + Parchment 2024.07.28 |
| 编译依赖（compileOnly / modCompileOnly） | JEI `jei-1.21.1-common-api`、EMI、REI；Shadowsoffire 系 `FastWorkbench`、`Placebo`（仅 neoforge 模块）；Fabric 端 `modApi + include` Cardinal Components API(CCA) 6.1.0 |
| 依赖它的 | 反过来说，Polymorph 是"被依赖方"：它通过自己的 API 被其它含自定义合成台的 mod 接入 |

## 2. 规模与包结构

实测：`.java` 文件 118 个，总 6991 行。分模块：common 75 / fabric 21 / neoforge 13 / forge 9。
common 包文件数（前三层）：`mixin/core` 16、`common/capability` 7、`common/network/server` 5、`server/wrapper` 4、`api/common/base` 4、`api/client/base` 4、`platform/services` 3、`common/network/client` 3、`common/integration` 3、`client` 3、`api/client/widgets{,/children}` 各 3。

最大文件：`common/.../common/capability/AbstractRecipeData.java`(213)、`api/client/widgets/children/SelectionWidget.java`(178)、`common/integration/PolymorphIntegrations.java`(167)、`server/PolymorphCommands.java`(163)、`forge/.../common/CommonEventsListener.java`(156)、`api/client/base/AbstractRecipesWidget.java`(154)、`common/capability/RecipeCache.java`(144)、`common/capability/PlayerRecipeData.java`(137)、`forge/.../PolymorphForgeChannel.java`(133)、`common/PolymorphApiImpl.java`(130)。

## 3. 入口与注册

无内容注册（无 DeferredRegister / Registrate），"注册"指的是工厂注册。三阶段入口 `PolymorphCommonMod`（`common/.../PolymorphCommonMod.java:33-63`）：

```java
public static void setup() {
  PolymorphApi api = PolymorphApi.getInstance();
  api.registerBlockEntity(blockEntity -> {
    if (blockEntity instanceof AbstractFurnaceBlockEntity) return new FurnaceRecipeData(...);
    else if (blockEntity instanceof CrafterBlockEntity)  return new CrafterRecipeData(...);
    return null; });
  api.registerMenu(menu -> { for (Slot s : menu.slots) if (s.container instanceof BlockEntity be) return be; ... });
  PolymorphIntegrations.setup(); }
```

- NeoForge：`PolymorphNeoForgeMod` 构造器注入 `IEventBus`，`eventBus.addListener(this::registerPayload)` 用 `PayloadRegistrar.playToClient/playToServer` 注册 7 个包（`neoforge/.../PolymorphNeoForgeMod.java:62-82`）。
- Fabric：`PolymorphFabricMod implements ModInitializer`，`PayloadTypeRegistry.playC2S/playS2C()` 注册类型，`ServerPlayNetworking.registerGlobalReceiver` 内统一 `server.execute(...)` 切主线程执行（`fabric/.../PolymorphFabricMod.java:52-85`）。
- 能力/组件：Forge 用 `RegisterCapabilitiesEvent` + `AttachCapabilitiesEvent<BlockEntity|Entity>` + `ICapabilitySerializable`；NeoForge 用 `PolymorphNeoForgeCapabilities`；Fabric 用 CCA 的 `PolymorphFabricComponents`。

## 4. 核心系统

**(a) 配方选择数据层** `common/capability/AbstractRecipeData.java`。持有 `SortedSet<IRecipePair> recipesList`、`Map<UUID,ServerPlayer> listeners`、`selectedRecipe`。`getRecipe()` 遍历候选配方产出 `RecipePair(id, output)`，列表只保留前 15 项（`recipesList.size() < 15 || flag`，`:112`），选中的那条强制保留；空输入时清空并回 null。NBT 只存 `SelectedRecipe` 的 id 存进 `loadedRecipe`，下次 `getRecipe` 时按 id 反查（`:79-82`），避免直接序列化配方对象。

**(b) 配方缓存** `common/capability/RecipeCache.java`：定长 10 的数组 LRU + `moveEntryToFront`；key 是 `copyWithCount(1)` 后的物品列表；`WeakReference<RecipeManager>` 变化即整体清空（`:47-54`）；`CraftingEntry` 额外比较 `width/height`。`MixinRecipeCache` 把原版同名的 `RecipeCache.get` 改成直接 `compute`（`:22-38`）。

**(c) 选择粘滞与线程安全** `common/capability/PlayerRecipeData.java:50-87`：用 `tickCount/lastAccessTick + cachedSelection` 解决"同一 tick 内输出被查询两次（含/不含容器剩余物）导致结果回退"的问题；`validateThread()` 限定只有服务端主线程才写入缓存，防竞态。

**(d) 隐式上下文传递** `mixin/core/MixinRecipeManager.java` 让 `RecipeManager` 实现 `IRecipeContext`（`polymorph$setContext/getContext`），并在 `getRecipeFor` HEAD 处若上下文是 BlockEntity 就改走 Polymorph 的 `getBlockEntityRecipe`。上下文由 `MixinServerLevel.tickBlock`、`MixinLevelChunk$BoundTickingBlockEntity.tick`、`MixinCrafterMenu.refreshRecipeResult` 在调用前后 set/clear，从而"原版配方查询天然知道是哪个方块实体在问"。

**(e) 客户端界面** `api/client/base/AbstractRecipesWidget`（`SelectionWidget` + `OpenSelectionButton` 组合，偏移常量 `BUTTON_Y_OFFSET=-22`）、`client/PolymorphWidgetsImpl.java:44-56` 用 switch 模式匹配按菜单类型选 widget，找不到工厂就 `findResultSlot` 兜底找 `ResultContainer` 槽并构造 `PlayerRecipesWidget`；`client/RecipesWidget.java` 单例 + `pendingData` 缓存（界面尚未创建时先存 S2C 数据）+ 关闭时发 `CPacketBlockEntityListener(false)`。

**(f) 集成模块** `common/integration/PolymorphIntegrations.java`：枚举 `Mod(id, 默认开, 支持加载器…)` 列出 REI/JEI/EMI/QuickBench/FastFurnace/FastWorkbench/FastSuite；`Services.INTEGRATION_PLATFORM.createCompatibilityModules()` 返回 `Supplier<Supplier<AbstractCompatibilityModule>>`；`selectRecipe/openContainer` 逐个模块试，命中即返回。

## 5. 网络 / 数据驱动 / 配置

- 7 个 `record implements CustomPacketPayload`，手写 `StreamCodec.composite`：C2S `CPacketPlayerRecipeSelection`/`CPacketPersistentRecipeSelection`/`CPacketBlockEntityListener`；S2C `SPacketRecipesList`/`SPacketPlayerRecipeSync`/`SPacketHighlightRecipe`/`SPacketUpdatePreview`。
- 加载器适配统一在 `IPolymorphNetwork`：Fabric `ClientPlayNetworking/ServerPlayNetworking`、NeoForge `PacketDistributor.sendToServer/sendToPlayer`、Forge `ChannelBuilder.simpleChannel()` + `consumerNetworkThread + enqueueWork + DistExecutor.unsafeRunWhenOn`（`forge/.../PolymorphForgeChannel.java`）。
- 同步策略：S2C 只下发 `(配方 id, ItemStack 输出)` 集合 + 选中 id，服务端 `sendRecipesListToListeners()` 广播给监听者；客户端开界面时 C2S 订阅（`PersistentRecipesWidget` 才订阅），离线/关界面退订，`BlockEntityTicker` 每 5 game tick 清一次失效方块实体（`common/util/BlockEntityTicker.java`）。数据是 `RecipePair` 的 `compareTo`（先按物品注册名，再按数量、组件哈希；`minecraft` 命名空间排最后）。
- 数据驱动 / datagen / 配置：无（无 config 类、无 JSON 数据加载）。仅有 `/polymorph conflicts` 命令扫描配方冲突并写 `logs/polymorph-conflicts.log`（`server/PolymorphCommands.java:58-76`）。

## 6. Mixin

配置文件：`common/src/main/resources/polymorph.mixins.json`（core，required=true，`maxShiftBy:3`）、`polymorph-compatibility.mixins.json`（integration，required=false，`"plugin": "...mixin.IntegratedMixinPlugin"`）；每加载器另有 `polymorph.{fabric,neoforge}.mixins.json`、`polymorph-compatibility.neoforge.mixins.json`。

代表性注入：
- `MixinCraftingMenu`：`@Redirect` 到 `RecipeManager.getRecipeFor(...)` 于 `slotChangedCraftingGrid`，改为 `PolymorphApi...getPlayerRecipe(...)`。
- `MixinSmithingMenu`：`@ModifyVariable` 两处，`createResult` 中 `INVOKE_ASSIGN getRecipesFor` 抓取候选列表；`java/util/List.get` + `shift = At.Shift.BY, by = 3` 改写最终选中配方。
- `MixinRecipeManager`（`priority = 900`，`@Inject HEAD getRecipeFor`，cancellable）、`MixinServerLevel.tickBlock`、`MixinLevelChunk$BoundTickingBlockEntity.tick`、`MixinCrafterMenu.refreshRecipeResult`（HEAD/TAIL 设清上下文）。
- Accessor 系列：`AccessorCraftingMenu`、`AccessorInventoryMenu`、`AccessorCrafterMenu`、`AccessorAbstractFurnaceBlockEntity`、`AccessorSmithingScreen(@Invoker)`、`AccessorSmithingTransformRecipe`、`AccessorSmithingTrimRecipe`。
- API 单例注入：`MixinPolymorphApi` / `MixinPolymorphWidgets` 在 `getInstance` HEAD 处 `cir.setReturnValue(...Impl.INSTANCE)`（`remap = false`），即 API 抽象类的实现由 mixin 绑进 `common` 层，无需加载器感知。
- Fabric 侧 `MixinServerPlayer.openMenu` RETURN 注入触发 `openContainer` 事件（Forge/NeoForge 用 `PlayerContainerEvent.Open`）。

## 7. 值得学的 5 条

1. **集成 mixin 动态开关 + 失败降级**：`IntegratedMixinPlugin.shouldApplyMixin` 按类名前缀取 modid，`PolymorphIntegrations.isActive(modid) && Services.PLATFORM.isModFileLoaded(modid)` 才应用；`onApplyError` 里 `disable(modId)` 并返回 `ErrorAction.WARN`，单个集成编译失败不崩游戏（`common/.../mixin/IntegratedMixinPlugin.java:49-105`）。
2. **ServiceLoader 平台抽象**：`platform/Services.java:26-40` 用 `ServiceLoader.load(IPlatform.class).findFirst()`，接口只有 `IPlatform/IClientPlatform/IIntegrationPlatform` 三个，比 ABC/Architectury 轻量，适合小 mod 抄。
3. **同 tick 缓存 + 主线程校验**：解决"一 tick 内原版重复查询输出"导致选中配方抖动（`common/capability/PlayerRecipeData.java:57-87`），凡是 hook 原版容器结果的地方都能用。
4. **弱引用失效的定长 LRU 缓存**：`RecipeCache` 用 `WeakReference<RecipeManager>` 做整体失效键，避免 datapack reload 后拿到旧配方（`common/capability/RecipeCache.java:47-54`）。
5. **隐式上下文而非改签名**：不改 `RecipeManager.getRecipeFor` 的调用方，而是用 `IRecipeContext` + tickBlock/chunk tick 的前后 set/clear 传递"当前方块实体"（`MixinServerLevel.java:36-70`），是给原版方法补上下文的通用套路。
6. （附）多加载器资源模板化：`multiloader-common.gradle:101-129` 对 `fabric.mod.json`、`META-INF/neoforge.mods.toml`、`*.mixins.json` 统一 `expand expandProps` 注入版本变量。

## 8. 公开 API（本 mod 是"被接入方"）

- 包路径：`com.illusivesoulworks.polymorph.api`。入口 `PolymorphApi`（抽象类 + `getInstance()`，实现为 `common/PolymorphApiImpl.java`）。
- 扩展点：`registerBlockEntity(Class<? extends BlockEntity>, IRecipeDataFactory)`、`registerBlockEntity(IRecipeDataFactory)`(已废弃)、`registerMenu(IBlockEntityFactory)`、`getPlayerRecipeData/getBlockEntityRecipeData`；客户端 `api/client/PolymorphWidgets.registerWidget(IRecipesWidgetFactory)`，基类 `api/client/base/AbstractRecipesWidget`（自定义偏移即可适配任意输出槽）。
- 扩展接口：`api/common/capability/{IRecipeData,IPlayerRecipeData,IBlockEntityRecipeData}`、`api/common/base/{IPolymorphNetwork,IPolymorphRecipeManager,IRecipeContext,IRecipePair}`、`api/client/base/{IRecipesWidget,ITickingRecipesWidget,PersistentRecipesWidget}`。
- 外部接入方式：外部 mod 只需在自身初始化时调用 `PolymorphApi.getInstance().registerBlockEntity(...)` / `registerMenu(...)`；内部容器用 `CopyOnWriteArrayList` + `ConcurrentHashMap` 保证线程安全（`common/PolymorphApiImpl.java:30-36`）。
