# Snownee/JadeAddons 源码分析报告（Jade 插件接入范例）

## 1. 基本信息

- Mod 名：Jade Addons；mod_id：`jadeaddons`；作者：Snownee；mod_version 6.1.1。
- 目标版本（`gradle.properties`）：`minecraft_version=1.21.1`、`neo_version=21.1.133`、Java 21、NeoForge；**单平台单模块**（无 common/fabric 拆分，`src/legacy/java` 目录未挂到任何 sourceSet，属历史遗留代码）。
- Gradle 插件：`net.neoforged.moddev 1.0.21`、`me.modmuss50.mod-publish-plugin 2.+`。许可证：ARR（`neoforge.mods.toml` license="ARR"）。
- 关键依赖（`build.gradle:121-146`）：Jade `maven.modrinth:jade:15.10.0+neoforge`（mods.toml 中 `[[dependencies.jadeaddons]] modId="jade" type="required" versionRange="[15.10, )"`）、Kiwi 15.4.1、JEI、Curios；Create `com.simibubi.create:create-1.21.1:6.0.3-48:slim`（`transitive = false`）+ Ponder + Flywheel（api compileOnly / 实现 runtimeOnly）+ Registrate。即：**Jade 是它的 API，Create 是它的适配目标**。

## 2. 规模与包结构

`find . -name '*.java' | wc -l` = **36**，总行数 **1990**。最大文件：`general/TargetModifierLoader.java`(203)、`create/GogglesProvider.java`(185)、`create/CreatePlugin.java`(176)、`general/GeneralPlugin.java`(85)、`create/ContraptionExactBlockProvider.java`(83)。

包结构：`snownee/jade/addon`（入口 3 个类）、`addon/create`(13)、`addon/lootr`(5)、`addon/general`(2)、`addon/enderio`(1)、`addon/mixin/create`(3)、`src/legacy/java` 下 `tconstruct`/`deep_resonance`/`mcjty_lib`（编译外，仅存档）。资源极少：全仓非 java 文件只有 `src/main/resources/jadeaddons.mixins.json` 与 `META-INF/neoforge.mods.toml`（**无 assets/lang**，提示文本复用 Jade 的 key 与 `IThemeHelper`）。

## 3. 入口与注册：如何接入 Jade

入口 `snownee/jade/addon/JadeAddonsBase.java`，`@Mod` 类 `JadeAddons.java` 只负责 FML 侧（客户端调 `JadeAddonsClient.init()` 注册 `IConfigScreenFactory` 指向 Jade 的 `PluginsConfigScreen`）。Jade 侧入口靠注解 + Jade 自己的扫描：

```java
@WailaPlugin                                                    // JadeAddonsBase.java:20
public class JadeAddonsBase implements IWailaPlugin {
    public static final Map<String, Supplier<Supplier<IWailaPlugin>>> PLUGIN_LOADERS = Maps.newHashMap(); // :22
    static {
        PLUGIN_LOADERS.put(JadeAddons.ID, () -> GeneralPlugin::new);   // :27
        PLUGIN_LOADERS.put("create", () -> CreatePlugin::new);         // :28
        PLUGIN_LOADERS.put("lootr", () -> LootrPlugin::new);
        PLUGIN_LOADERS.put("enderio", () -> EnderIOPlugin::new);
    }
```

构造函数按 `CommonProxy.isModLoaded(modid)` 逐个实例化，`try/catch(Throwable)` 记日志；`register(IWailaCommonRegistration)` 用 `plugins.removeIf(...)`：**某个子插件注册失败即从列表移除，不牵连其他插件**。没有 `DeferredRegister`/Registrate，本模组不添加任何游戏内容。

## 4. 核心系统

- **双子插件模型（服务端数据 / 客户端渲染分离）**：`IWailaPlugin` 的 `register(IWailaCommonRegistration)` 只注册数据侧 `registerBlockDataProvider / registerEntityDataProvider / registerItemStorage / registerFluidStorage`；`registerClient(IWailaClientRegistration)` 注册展示侧 `registerBlockComponent / registerBlockIcon / registerEntityComponent / registerEntityIcon / registerItemStorageClient / registerFluidStorageClient`。两侧 UID 必须一致：如 `BlazeBurnerProvider` 同时 `implements IBlockComponentProvider, IServerDataProvider<BlockAccessor>`，`getUid()` 返回同一 `CreatePlugin.BLAZE_BURNER`（`create/BlazeBurnerProvider.java:63-66`）。
- **服务端→客户端数据通道**：`appendServerData(CompoundTag data, BlockAccessor accessor)` 只 put 必需字段（`fuelLevel`/`burnTimeRemaining`/`isCreative`），客户端 `appendTooltip` 从 `accessor.getServerData()` 读；不需要同步的信息干脆不发（`BlazeBurnerProvider.java:41-54`）。
- **插件自带配置项**：`registration.addConfig(REQUIRES_GOGGLES, true)`、`addConfig(GOGGLES_DETAILED, false)`、`addConfig(EQUIPMENT_REQUIREMENT, "", validator)` + `addConfigListener(id, consumer)` + `markAsClientFeature(id)`（`CreatePlugin.registerClient`、`GeneralPlugin.registerClient`）。配置项 UID 定义成常量集中放 Plugin 类（`CreatePlugin.java:55-77`），Provider 通过 `IPluginConfig config` 与 `IWailaConfig.get().getPlugin().get(...)` 读取。
- **回调链**：`addRayTraceCallback(priority, callback)` 可在渲染前替换/取消 `Accessor`（`GeneralPlugin` 用 10000 优先级做"未装备指定 tag 物品则不显示"）；`addTooltipCollectedCallback` 在 tooltip 组装完成后改写 `IBoxElement`；两者都被 `TargetModifierLoader` 复用。客户端还直接改 Jade 静态过滤链：`RayTracing.ENTITY_FILTER = RayTracing.ENTITY_FILTER.and(e -> ...)`（`CreatePlugin.java:98` 起）让铁路轨道 Bezier 命中、Create 动态装置（Contraption）内部方块也能被方块级检测。
- **数据驱动覆盖规则**：`general/TargetModifierLoader.java` 是 `SimpleJsonResourceReloadListener`（`super(JsonConfig.GSON, "jade/target_modifier")`），支持 `type=remove_elements`（按 tag 移除 tooltip 元素）与 `type=replace`（把目标伪装成另一个方块，含 `Blocks.AIR` = 完全隐藏），target 支持 `"block"`/`"entity"` 且 `#` 前缀解析为 tag。重载由 `TagsUpdatedEvent`（CLIENT_PACKET_RECEIVED）触发，另有 `reload()` 手动 `prepare + apply(InactiveProfiler.INSTANCE)` 复用原版逻辑。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无自建网络通道**，全部复用 Jade 的同步机制（`IServerDataProvider` 的 CompoundTag）。`CreatePlugin` 中 `registration.hideTarget(EntityType.byString("create:super_glue").orElse(null))`（`CreatePlugin.java:96`）用软查询避免硬依赖该实体。
- 数据驱动：见上 `jade/target_modifier/*.json`（`TargetModifierLoader:41`）。
- 配置：无独立 config 文件；用 Jade 的插件配置（`addConfig` / `IWailaConfig`）与 `JadeAddonsClient` 注册的配置界面入口。
- datagen：有 `data` run（`build.gradle:73-80`，输出 `src/generated/resources`），但仓库内 `src/generated` 不存在、无 datagen 代码 → 未实际使用。

## 6. Mixin

配置 `src/main/resources/jadeaddons.mixins.json`（`defaultRequire: 0`，即注入失败不崩游戏——对第三方 mod 兼容类 mixin 的稳妥选择）：`mixins` 里 `create.BacktankBlockEntityAccess`，`client` 里 `create.BlueprintOverlayRendererAccess`、`create.FilterItemAccess`。

三个 mixin 全是**只读访问器，不改逻辑**、都带 `remap = false`（Create 是第三方 mod）：
- `BacktankBlockEntityAccess`：`@Accessor("capacityEnchantLevel")` 取私有字段。
- `FilterItemAccess`：`@Invoker callMakeSummary(ItemStack)` 调私有方法。
- `BlueprintOverlayRendererAccess`：`@Accessor static List<ItemStack> getResults()`（静态访问器方法体 `throw new AssertionError()`）。

## 7. 值得学的 5 条做法

1. 用 `Map<String, Supplier<Supplier<IWailaPlugin>>>` + `isModLoaded` 做可选兼容插件的集中注册，并给每个插件独立 try/catch 隔离故障（`JadeAddonsBase.java:22-46`，场景：一个兼容包同时支持十几个 mod）。
2. 服务端只发"必要字段"进 `CompoundTag`、客户端再组装展示（`BlazeBurnerProvider.java`，场景：任何 HUD/信息面板同步）。
3. 对第三方 mod 的私有成员一律用 `@Accessor`/`@Invoker` 只读接口 mixin，不注入逻辑（`mixin/create/*.java`，场景：跨 mod 取数）。
4. mixin 配置 `defaultRequire: 0`，让兼容 mixin 失败只退化不崩溃（`jadeaddons.mixins.json`）。
5. 把"显示什么"下沉为可在数据包里改写的 JSON 规则（`remove_elements`/`replace`），代码只留解析与回调（`TargetModifierLoader.java`，场景：给玩家/整合包留接口）。

## 8. 公开 API / 接入方式

本模组**不对外提供 API**，它是 Jade 的消费者：对外契约就是 `IWailaPlugin` + `@WailaPlugin`。给其他 mod 的扩展面只有数据包路径 `data/<namespace>/jade/target_modifier/*.json`（schema：`type` 必填，`target:{block|entity}` 二选一、`#` 前缀为 tag，`remove_elements` 需 `tag`（字符串或数组），`replace` 需 `with:{block}`）。反向依赖者（Create/Lootr/EnderIO）只需在 `PLUGIN_LOADERS` 加一项并在 `create` 包施加 Provider。
