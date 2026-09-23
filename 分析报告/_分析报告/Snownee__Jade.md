# Snownee/Jade 源码分析

仓库路径：`源码库\_参考仓库\Jade`

## 1. 基本信息

- Mod 名 / mod_id：Jade / `jade`（Hwyla fork，描述见 `src/main/resources/fabric.mod.json`）
- 作者：Snownee（contributors：TehNut、ProfMobius、kalkafox）
- 版本 / 目标：`mod_version=15.10.6`，`minecraft_version=1.21.1`，`loader_version=0.16.14`，archives 前缀 `1.21.1-Fabric-`（`gradle.properties`、`build.gradle`）
- Gradle 插件：`fabric-loom 1.10-SNAPSHOT` + `me.modmuss50.mod-publish-plugin 2.+`；Java 21；mappings `loom.officialMojangMappings()`；mixin refmap `jade.refmap.json`；`accessWidenerPath = src/main/resources/jade.accesswidener`；有 `apiJar` 任务，只把 `snownee/jade/api/**` 打进 `-api` 分类 jar（`build.gradle:80-90`）
- 依赖：Fabric API 0.115.6+1.21.1、ModMenu 11.0.1（impl）、JEI 19.8.5.117（`modCompileOnlyApi`）、`teamreborn:energy 4.1.0`（`modApi`，Fe/Reborn Energy 兼容）；cloth-config 依赖已被注释掉；pack 格式有 `pack.mcmeta`
- 许可证：CC-BY-NC-SA-4.0（`LICENSE.md`）
- 注意：本 checkout 是 **Fabric 分支**（`src/main/resources` 下只有 `fabric.mod.json`，无 `META-INF/neoforge.mods.toml`），Forge/NeoForge 由其它分支/源集产出，未确认

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **252 文件，23457 行**。按包（第 2-3 层，文件数）：

`snownee/jade/addon` 67（core、vanilla、universal、access、debug、harvest）、`api` 59、`impl` 48、`gui` 19、`util` 12、`test` 11、`mixin` 11、`network` 7、`overlay` 5、`track` 4、`compat` 4、根 3（`Jade`、`JadeClient`、`JadeInternals`）、`command` 2。

最大文件：`impl/config/WailaConfig.java` 693、`util/CommonProxy.java` 660、`gui/config/OptionsList.java` 643、`impl/WailaClientRegistration.java` 569、`gui/config/NotUglyEditBox.java` 550、`overlay/DisplayHelper.java` 485、`api/ui/BoxStyle.java` 475、`api/ui/Color.java` 451。

## 3. 入口与注册

`fabric.mod.json` entrypoints：`main=snownee.jade.util.CommonProxy`、`client=snownee.jade.util.ClientProxy`、**自定义 `jade` 入口点** `= [CorePlugin, VanillaPlugin, UniversalPlugin, AccessibilityPlugin, DebugPlugin]`、`modmenu=ModMenuCompat`、`jei_mod_plugin=JEICompat`；`mixins: jade.mixins.json`、`accessWidener: jade.accesswidener`。

没有 DeferredRegister，注册体系是自研的两阶段 provider 注册 + 入口点扫描（`CommonProxy.loadComplete()`）：

```java
FabricLoader.getInstance().getEntrypointContainers(Jade.ID, IWailaPlugin.class).forEach(entrypoint -> {
    WailaPlugin a = plugin.getClass().getDeclaredAnnotation(WailaPlugin.class);
    if (a != null && !Strings.isNullOrEmpty(a.value()) && !isModLoaded(a.value())) return;   // @WailaPlugin("modid") 可选依赖
    if (className.startsWith("snownee.jade.") && !metadata.getId().startsWith(Jade.ID))
        throw new IllegalStateException("Mod %s is not allowed to register built-in plugins...");
    common.startSession(); plugin.register(common);
    if (isPhysicallyClient()) { client.startSession(); plugin.registerClient(client); client.endSession(); }
    common.endSession();
});
Jade.loadComplete();
```

`Jade.loadComplete()` 随后 `priorities.sort(...)` → `WailaCommonRegistration.loadComplete()`（一次性排序冻结）→ `FROZEN = true`（`Jade.java:24-33`）。`test/` 下的 `ExamplePlugin`（11 个文件）是 dev 环境自注册的官方示例插件。

## 4. 核心系统

1. **Provider 层级查找与排序**：`impl/lookup/HierarchyLookup`（`Class → List<T>` 的 ArrayListMultimap + Guava Cache 缓存查询结果，`getInternal` 沿父类链递归收集，`loadComplete` 检测同一 class 下重复 UID、用 `ImmutableListMultimap.orderValuesBy(priorityStore::byValue)` 冻结排序、`idMapped()` 时建 `IdMapper` 供网络 ID 复用）。`PairHierarchyLookup` 处理"Block + BlockEntity 两级合并"（`getMerged`），`WrappedHierarchyLookup` 用于 ItemStack/Fluid/Energy/Progress 通用视图。`PriorityStore` 支持配置化排序（key `jade/sort-order`，支持 primary key 让子条目跟随父条目）。
2. **Accessor 抽象**：`api/Accessor` + `BlockAccessor`/`EntityAccessor` + `Builder`（`BlockAccessorImpl.Builder`，链式 + `requireVerification()`），`record SyncData(showDetails, hit, blockState, fakeBlock)` 用 `StreamCodec.composite` + `ByteBufCodecs.idMapper(Block.BLOCK_STATE_REGISTRY)` 序列化；`Accessor.verifyData` 校验服务端返回数据与当前命中目标是否匹配。
3. **网络**（`network/`，全部 `CustomPacketPayload` + `StreamCodec`）：`RequestBlockPacket`/`RequestEntityPacket` 把 `SyncData` + `List<IServerDataProvider>`（用 provider `IdMapper` 序列化）发往服务端；服务端 `BlockAccessorImpl.handleRequest` 校验 `distSqr > (blockInteractionRange+21)^2` 或未加载区块就丢弃，再逐个 provider `appendServerData` 后回 `ReceiveDataPacket`；`ReceiveDataPacket` 限制 16KB，超限时 `removeLargest` 递归删除最大子 tag（最多 10 轮）；`ServerPingPacket` 在 `ServerPlayConnectionEvents.JOIN` 下发服务器 JSON 配置 + shearable blocks + block/entity provider id 列表，客户端 `remapIds` 对齐 ID 并应用服务器配置。
4. **每 tick 主流程**（`overlay/WailaTickHandler.tickClient()`）：`RayTracing.INSTANCE.fire()` → 自实现射线追踪（扩展 reach、`PerspectiveMode.EYE` 从眼睛起点、液体模式 NONE/FALLBACK、`canBeTarget` 过滤弹射物/隐身/载体等）→ 由 `IWailaClientRegistration.blockAccessor()/entityAccessor()` builder 造 Accessor → `JadeRayTraceCallback` 链可替换目标 → `ObjectDataCenter.set(accessor)`（目标变化才清 serverData，`rateLimiter = 250ms` 限流请求）→ `AccessorClientHandler.shouldRequestData/requestData` → `gatherComponents` 收集工具提示 → `BoxElement` + `JadeTooltipCollectedCallback` → `OverlayRenderer` 渲染；另配 `Narrator` 朗读（500ms 节流 + 去重）。
5. **工具提示模型与主题**：`impl/Tooltip` 内部是 `List<Line>`，每行按 `Align` 三分（`starts[]`/`widths[]` 数组实现左中右对齐），元素按 `ResourceLocation tag` 可被其它插件 `add/append/remove/replace/get`；主题数据驱动：`assets/jade/jade_themes/{waila,dark,top,create}.json`（`version: 100` + `tooltipStyle`），由 `impl/theme/ThemeHelper`（`SimpleJsonResourceReloadListener`）热重载。
6. **UI 元素体系**：`api/ui`（`IElement`/`IBoxElement`/`ITextElement`/`BoxStyle`/`Color`/`ColorPalette`/`ProgressStyle`/`ScreenDirection`/`TooltipRect`）+ `impl/ui` 17 个实现（ItemStackElement、FluidStackElement、ArmorElement、HealthElement、ProgressElement、SpecialTextElement…）+ `ElementHelper` 单例工厂 + `overlay/DisplayHelper` 实际绘制；`track/`（ProgressTracker + ProgressTrackInfo/HealthTrackInfo）做进度条按 tick 的平滑插值（`TrackInfo.alive/updatedThisTick`）。
7. **额外功能**：`addon/harvest/HarvestToolProvider`（数据驱动的采集工具提示，`ToolHandler`/`ShearsToolHandler`/`LootTableMineableCollector`，随 SERVER_DATA 资源包重载）、`addon/universal`（ItemCollector/ItemIterator 递归收集容器内容）、`command/JadeClientCommand`、`compat/{JEI,REI,ModMenu,TechRebornEnergy}`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：5 个 packet，注册在 `CommonProxy:638-643`（`PayloadTypeRegistry`）+ 客户端 `ClientPlayNetworking.registerGlobalReceiver`（`ClientProxy.java:333-344`）。
- 配置：`impl/config/WailaConfig`（客户端 `IWailaConfig`，`JsonConfig<WailaConfig>` + Codec）、`PluginConfig`（`jade/plugins.json`，`addConfig` 注册的命名空间键，可被服务器配置覆盖 `applyServerConfigs`），配置 UI 为自绘 `gui/`（`OptionsList`/`BaseOptionsScreen`/`HomeConfigScreen`，未用 Cloth Config）。
- 数据驱动：主题 JSON（客户端资源包）+ harvest SERVER_DATA 重载监听 + `overlay/DatapackBlockManager` 追踪数据包方块实体。
- datagen：`build.gradle` 声明了 `src/generated/resources` 源集，但本 checkout 中 `src/generated` 不存在（未生成）。

## 6. Mixin

配置：`src/main/resources/jade.mixins.json`（`package snownee.jade.mixin`、`compatibilityLevel JAVA_16`、`refmap jade.refmap.json`、`defaultRequire 1`）。

- 通用：`AbstractFurnaceBlockEntityAccess`（`@Accessor litTime`）、`AbstractHorseAccess`、`EntityAccess`、`HarvestToolProviderMixin`（改 Jade 自身类以扩展采集工具判定）
- client：`BossHealthOverlayMixin`（`@Inject(method="render(Lnet/minecraft/client/gui/GuiGraphics;)V", at=HEAD, cancellable)` 避让 boss 血条）、`ClientLevelMixin`（`addEntity` HEAD → DatapackBlockManager 追踪）、`FontMixin`（`renderChar` HEAD cancel）、`StringRenderOutputMixin`（`<init>` RETURN + `accept` 处 `Style;isObfuscated`）、`SessionSearchTreesMixin`（`getTooltipLines` HEAD 注入 mod 名）、`ThemeHelperMixin`、`KeyAccess`（`@Accessor InputConstants.Key`）
- 另有大量用 **accessWidener 而非 mixin** 的取用：`jade.accesswidener` 打开 `BrewingStandBlockEntity.brewTime/fuel`、`MultiPlayerGameMode.destroyProgress/destroyBlockPos`、`AbstractSelectionList.hovered`、`Allay.duplicationCooldown`、`Tadpole.getTicksLeftUntilAdult` 等

## 7. 值得学的 5 条做法

1. **自定义 loader 入口点 + 注解声明可选依赖 + 冒名防护**：`@WailaPlugin("modid")` 让插件随其依赖 mod 缺席自动跳过，并禁止非 jade 的 mod 注册 `snownee.jade.*` 内置插件类（`util/CommonProxy.java:445-495`）。适用：做插件式 API 的库 mod。
2. **注册会话 + 冻结语义**：`startSession()/endSession()` 包裹每个插件的注册、`loadComplete()` 后 `FROZEN=true` 拒绝再注册，既能在加载期分批注册又能一次性排序冻结（`impl/WailaCommonRegistration.java:151-165`、`Jade.java:24-33`）。适用：需要保证注册顺序与性能的注册中心。
3. **Class 层级 lookup + 缓存 + 父类链聚合**：注册只记 `Class → provider`，查询时沿 superclass 链收集并缓存结果（`impl/lookup/HierarchyLookup.java:74-142`）。适用：父类即"通用行为"的按类型分派（比逐实例判断高效）。
4. **网络数据自愈 + ID 映射对齐**：超限数据递归裁剪而不是丢弃、provider 用 `IdMapper` 传索引、连服务器时下发 id 列表让客户端 `remapIds`（`network/ReceiveDataPacket.java:38-79`、`ServerPingPacket.java:47-60`）。适用：客户端要与服务端"同一份 provider 集合"协作的场景。
5. **服务端数据契约校验**：`Accessor.verifyData` 比对坐标，`ObjectDataCenter.getServerData` 校验失败即重新请求；`requireVerification()` 由调用方显式开启（`impl/BlockAccessorImpl.java:141-150`、`impl/ObjectDataCenter.java:55-72`）。适用：异步/延迟到达的服务端数据防串帧。
6. **tag 化的 hint 元素 API**：所有元素可带 `ResourceLocation` tag，别的插件能按 tag 增删改（`impl/Tooltip.java` 的 add/append/remove/replace/get + `IElement#getTag`）。适用：多插件共同拼装 UI 的场景。

## 8. 公开 API（库/前置类 mod）

- 公开包：`snownee.jade.api`（`apiJar` 只包含它，作为 `-api` artifact 发布）；`snownee.jade.api.JadeIds` 保存全部内置 UID 常量
- 扩展点：`IWailaPlugin`（`register(IWailaCommonRegistration)` 双端 / `registerClient(IWailaClientRegistration)` 客户端）、`@WailaPlugin(modid)` 注解
- 注册接口：`IWailaCommonRegistration`（registerBlockDataProvider / registerEntityDataProvider / registerItemStorage / registerFluidStorage / registerEnergyStorage / registerProgress）、`IWailaClientRegistration`（addConfig / registerBlockComponent / registerEntityComponent / registerBlockIcon / registerEntityIcon / hideTarget / usePickedResult / addXxxCallback / blockAccessor() / entityAccessor() / createPluginConfigScreen / markAsClientFeature）
- Provider 接口：`IJadeProvider`（`getUid()`、`getDefaultPriority()`）、`IToggleableProvider`、`IComponentProvider<T>`（`appendTooltip(ITooltip, T, IPluginConfig)`、`getIcon(...)`）、`IBlockComponentProvider` / `IEntityComponentProvider`、`IServerDataProvider#appendServerData(CompoundTag, Accessor)`
- 通用视图接口：`api/view/IServerExtensionProvider` + `IClientExtensionProvider` + `ItemView`/`FluidView`/`EnergyView`/`ProgressView`/`ViewGroup`/`ClientViewGroup`/`HideThingsExtensionProvider`（Jade 负责网络与渲染，接入方只写收集/展示逻辑）
- 回调：`api/callback/` 下 6 个（JadeAfterRender / JadeBeforeRender / JadeBeforeTooltipCollect / JadeTooltipCollected / JadeItemModName / JadeRayTrace），均有带 priority 的重载
- 其它：`api/ui/**`（自绘元素与 BoxStyle/Color）、`api/config/{IWailaConfig,IPluginConfig,IgnoreList}`、`api/theme/**`、`api/fluid/JadeFluidObject`、`api/Accessor*`
- 外部接入方式：自己在 `fabric.mod.json` 声明 `"entrypoints": {"jade": ["your.pkg.YourPlugin"]}`（或 Forge/Neo 对应入口），插件类实现 `IWailaPlugin` 并加 `@WailaPlugin("optionalmodid")`
