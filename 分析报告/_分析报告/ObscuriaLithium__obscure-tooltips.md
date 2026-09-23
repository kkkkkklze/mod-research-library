# ObscuriaLithium/obscure-tooltips 源码分析报告

## 1. 基本信息
- Mod 名：Obscure Tooltips；mod_id：`obscure_tooltips`；作者：Obscuria；版本 3.10.0；许可证：Obscuria-Limited（非开源许可，仅可参考思路）。
- 目标：MC 1.20.1，Java 17，多加载器三模块（`common` / `fabric` / `forge`），Forge 47.2.30、Fabric Loader 0.16.9 + Fabric API 0.92.1。
- Gradle 插件：`multiloader-common`、`net.neoforged.moddev.legacyforge`（common，见 `common/build.gradle`）；`multiloader-loader`、`fabric-loom`、`dev.obscuria.hekate`（fabric）；构建脚本在 `buildSrc/src/main/groovy/multiloader-*.gradle`。
- 编译依赖：**`dev.obscuria:fragmentum-api`（强制前置，`forge/src/main/resources/META-INF/mods.toml` 中 `modId="fragmentum"` mandatory）**——注册表、配置、GroupTooltip、资源包构建器都来自它；另 compileOnly `mixinextras-common`。

## 2. 源码规模与包结构
实测：92 个 `.java`，4372 行。主要包（`common/src/main/java/dev/obscuria/tooltips/`）：
- `client/tooltip/element/`（effect 7 / frame 3 / icon 5 / panel 3 / slot 3，共 21 文件）：渲染元素
- `client/tooltip/`（filter 14 / label 5 / layout 5 / particle 4）：过滤器、标签、布局、粒子
- `client/component/` 6、`client/registry/` 6、`config/` 4、`mixin/` 5；`fabric/`、`forge/` 各 2-4。
最大文件：`config/ClientConfig.java`(334)、`element/effect/GlintEffect.java`(238)、`ShimmerEffect.java`(155)、`client/TooltipHelper.java`(139)、`client/TooltipRenderer.java`(110)。

## 3. 入口与注册
主入口是接口 `common/.../ObscureTooltips.java:24` 的静态 `init()`，被两侧入口调用（`forge/.../ForgeObscureTooltips.java` 用 `@Mod` + `FMLEnvironment.dist.isDedicatedServer()` 提前返回；`fabric/.../FabricObscureTooltips.java` 实现 `ClientModInitializer`）：
```java
ClientConfig.init();
TooltipRegistries.init();
FragmentumClientRegistry.registerTooltipComponent(StackBuffer.class, StackBuffer::asClient);
BuiltInPackBuilder.resourcePack("packs/vibrant_tooltips").displayName(...).register(MOD_ID);
```
注册框架为 Fragmentum 的 `FragmentumRegistry.registrar(MOD_ID)` + `Registrar.createRegistry(ResourceKey)`，产出 `DelegatedRegistry<Codec<? extends X>>`（`client/registry/TooltipRegistries.java:28-36`）：把 9 类"编解码器"本身注册进 MC 注册表，各元素接口自带 `static void bootstrap(BootstrapContext)`（如 `filter/ItemFilter.java` 注册 13 种过滤器 `always/never/all_of/item/mod/rarity/nbt/...`）。

## 4. 核心系统
1. **Tooltip 渲染管线** `client/TooltipRenderer.java`：`render()` 返回 boolean 决定是否取消原版渲染；`layout.rawProcessPreWrap → TooltipHelper.wrapLines → rawProcessPostWrap`；绘制顺序固定为 panel → effects → frame（中间夹 `graphics.flush()` 以保证批次顺序），整体 `pose().translate(0,0,400)` 提到最前。
2. **布局状态机** `client/tooltip/layout/`：`DefaultLayout` / `ToolPreviewLayout` / `ArmorPreviewLayout`（单例 INSTANCE），按物品类型与配置白/黑名单切换；`extractState(stack)` 生成 `TooltipState`。
3. **物品栈标记协议** `client/component/StackBuffer.java` + `mixin/MixinItemStack.java`：以 `@Mixin(value = ItemStack.class, priority = Integer.MAX_VALUE)` 在 `getTooltipImage` 的 RETURN 注入，用 `GroupTooltip.maybeGroup(原组件, new StackBuffer(self))` 把 ItemStack 夹带进原版 TooltipComponent 列表，渲染端再用 `ClientGroupTooltip.findFirst(components, StackBuffer.class)` 取回。
4. **数据驱动元素体系** `client/registry/{ResourceKind,ResourceRegistry,TooltipManager}.java`：`ResourceRegistry` 维护双向 Map（key↔element），`byNameCodec()` = `ResourceLocation.CODEC.flatXmap(...)`；内部类 `Ordered` 在 `onReloadEnd()` 按 `Comparable` 逆序排序，供 `TooltipDefinition.aggregateStyleFor()` 按 priority 逐条 `style.merge()` 合成最终样式。
5. **配置** `config/ClientConfig.java`：全部为 `static final ConfigValue<T>` 字段（Fragmentum `ConfigBuilder`），并提供 `ARGBDelegate`（颜色字段强类型化）、`BooleanDelegate`。
6. **资源重载** `TooltipManager`（`ResourceManagerReloadListener`）：遍历 `ResourceKind` 枚举，`listResources("tooltips/<dir>", .json)` → `JsonOps` 解码 → `onReloadStart/End` 整体替换，单条失败仅记日志。

## 5. 网络 / 数据驱动 / 配置 / datagen
无网络包（纯客户端 mod）。数据驱动：全部配置走资源包 JSON，路径 `assets/<ns>/tooltips/{element/panel,element/frame,element/slot,element/icon,element/effect,style,definition,label}/*.json`，由 `ResourceKind.Spec` 定义目录与 codec，ResourceLocation 即注册键。datagen：无（仓库未含 `data/`、`assets/` 或生成器；`common/src/main/resources` 仅有 mixins.json，资源文件疑似由外部/发布产物提供，未确认）。

## 6. Mixin
配置：`common/src/main/resources/obscure_tooltips.mixins.json`（client 段 5 个）、`obscure_tooltips.forge.mixins.json`、`obscure_tooltips.fabric.mixins.json`；均 `defaultRequire: 1`，refmap `${mod_id}.refmap.json`。
- `MixinGuiGraphics#renderCustomTooltip` → `GuiGraphics.renderTooltipInternal`，`@At(INVOKE, target="List.isEmpty()")`，可取消。
- `MixinItemStack#injectStackBuffer` → `ItemStack.getTooltipImage` RETURN。
- `MixinMouseHandler#customScroll` → `MouseHandler.onScroll` HEAD，`TooltipScroll.shouldCaptureInput()` 时吞掉滚轮实现 tooltip 内滚动（priority=1）。
- Fabric 侧 `MixinMinecraft#init` → `Minecraft.<init>`，注入点 `NEW MobEffectTextureManager`（此时 `resourceManager` 已赋值）以注册 reload listener；forge 侧则在 `@Mod` 构造器里 `Minecraft.getInstance().getResourceManager()` 判断 `ReloadableResourceManager` 后注册。

## 7. 值得学的 5 条具体做法
1. **用 TooltipComponent 夹带数据而非全局变量**：`MixinItemStack` 把 ItemStack 塞进原版组件链，渲染端解包（`mixin/MixinItemStack.java`）——适合任何需要知道"当前 tooltip 属于哪个物品"的场景。
2. **泛型式"元素注册表"**：把 `Codec<? extends X>` 注册进自定义 Registry，再用 `dispatch(CODEC::codec, identity)` 做多态序列化（`filter/ItemFilter.java:12`）——NeoForge 1.21.1 写数据驱动子系统可直接照搬。
3. **重载期双向 Map 注册表 + flatXmap codec**（`client/registry/ResourceRegistry.java:30`）：让资源 JSON 里直接写 `namespace:path` 引用其他元素，且 reload 时全量重建。
4. **有序资源 + 合并式样式**：`Ordered.onReloadEnd()` 逆序排序 + `TooltipStyle.merge()`（Optional.or 逐字段覆盖、effects 带 `canApply` 去重）实现"多条定义叠加出最终外观"，见 `tooltip/TooltipStyle.java:27`。
5. **跨加载器注册 reload listener 的两种时机**：Fabric 用 `<init>` 注入点 `NEW MobEffectTextureManager` 拿 `resourceManager`，Forge 用 `@Mod` 构造器 + `instanceof ReloadableResourceManager` 判断（`fabric/.../MixinMinecraft.java:22`、`forge/.../ForgeObscureTooltips.java:19`）。
