# shedaniel/ClothConfig 源码分析报告

## 1. 基本信息

- Mod 名：Cloth Config API v8.3（`archives_base_name=cloth-config`）；`mod_id = cloth_config`（`forge/src/main/resources/META-INF/mods.toml:11`，`ClothConfigInitializer.MOD_ID`）。
- 作者：shedaniel；许可证 GNU LGPLv3（`LICENSE.md`）。
- 目标版本：`minecraft_version=1.19.1`、`supported_version=1.19-1.19.2`、`base_version=8.3`、`fabric_loader_version=0.14.8`、`fabric_api_version=0.58.5+1.19.1`、`forge_version=42.0.1`（`gradle.properties`）。
- Gradle 插件：architectury-plugin 3.4-SNAPSHOT + dev.architectury.loom 0.12.0-SNAPSHOT（多平台 common/fabric/forge 三模块）、shadow 7.0.0、unified-publishing、cadixdev.licenser；`options.release = 16`（`build.gradle:31`）。
- 编译依赖：ModMenu 4.0.5（compileOnly+localRuntime）、`me.shedaniel.cloth:basic-math:0.6.1`、jankson 1.2.0、toml4j 0.7.2、snakeyaml 1.27（后三者 shadow 并 relocate 到 `me.shedaniel.clothconfig.shadowed.*`，见 `fabric/build.gradle:62-64`）。它是众多 mod 的**前置 API**，自身不依赖其他 mod 的 API。

## 2. 源码规模与包结构

150 个 `.java`，20567 行（`find -name '*.java' | wc -l` / `-exec cat | wc -l`）。主要包（common 模块）：

- `me.shedaniel.clothconfig2.gui.entries` 30 个（各种配置条目控件）
- `me.shedaniel.clothconfig2.impl.builders` 27 个（各控件 Builder 实现）
- `me.shedaniel.clothconfig2.api` 23 个（公开 API）
- `me.shedaniel.clothconfig2.api.animator` 13、`clothconfig2.impl` 9、`clothconfig2.gui` 6、`clothconfig2.gui.widget` 6
- `me.shedaniel.autoconfig`（含 `serializer` 7 / `gui` 3 / `gui.registry` 3 / `gui.registry.api` 3 / `annotation` 2 / `event` 1）

最大文件：`api/animator/RecordValueAnimatorArgs.java` 1583、`gui/entries/DropdownBoxEntry.java` 791、`gui/widget/DynamicEntryListWidget.java` 746、`autoconfig/gui/DefaultGuiProviders.java` 579、`impl/builders/DropdownMenuBuilder.java` 556、`gui/GlobalizedClothConfigScreen.java` 497、`gui/ClothConfigScreen.java` 451、`gui/AbstractConfigScreen.java` 428。

## 3. 入口与注册

纯客户端 UI 库，**无 DeferredRegister**。Forge 入口 `forge/src/main/java/me/shedaniel/clothconfig/ClothConfigForge.java:30-35`：

```java
@Mod(ClothConfigInitializer.MOD_ID)
public class ClothConfigForge {
    public ClothConfigForge() {
        ModLoadingContext.get().registerExtensionPoint(IExtensionPoint.DisplayTest.class, ...IGNORESERVERONLY...);
        DistExecutor.safeRunWhenOn(Dist.CLIENT, () -> ClothConfigForgeDemo::registerModsPage);
    }
}
```

Fabric 侧只有 `fabric/src/main/java/me/shedaniel/clothconfig2/fabric/ClothConfigModMenuDemo.java`；本仓库快照中**未包含 `fabric.mod.json`**（`fabric/build.gradle:64` 引用它生成，文件未确认）。真正的"注册"是第三方调用 `AutoConfig.register(...)`（`common/src/main/java/me/shedaniel/autoconfig/AutoConfig.java:48-70`）。

## 4. 核心系统

1. **注解驱动配置（AutoConfig）**：`autoconfig/AutoConfig.java` + `ConfigManager.java`。`ConfigManager` 构造时 `load()`，失败则 `resetToDefault()`；`load()/save()` 前后触发 `ConfigSerializeEvent.Load/Save` 监听器并支持 `InteractionResult.FAIL/PASS` 中断（`ConfigManager.java:73-113`）；`ConfigData.validatePostLoad()` 做加载后校验，校验抛错即回退默认值。
2. **序列化层**：接口 `autoconfig/serializer/ConfigSerializer.java`，实现 Gson/Toml4j/Yaml/Jankson/Dummy；`GsonConfigSerializer` 路径 = `getConfigFolder().resolve(definition.name() + ".json")`；`PartitioningSerializer.wrap(inner)` 把顶层字段按类型拆成 `config/<name>/<子配置名>.json` 多文件（`PartitioningSerializer.java:45-70`），并用匿名 `Config` 注解实现动态配置名。
3. **反射→GUI 生成**：`autoconfig/gui/ConfigScreenProvider.java`。`Arrays.stream(configClass.getDeclaredFields())` 按 `ConfigEntry.Category` 分组（`LinkedHashMap` 保序），逐字段调 `registry.getAndTransform(optionI18n, field, config, defaults, registry)`，i18n key 固定为 `text.autoconfig.<name>.option.<field>`。
4. **GuiProvider/GuiTransformer 注册表**：`autoconfig/gui/registry/GuiRegistry.java`，`Priority` 枚举 + `firstPresent()` 短路匹配，`registerAnnotationProvider` 同时要求字段类型谓词与注解存在（见 `DefaultGuiProviders.java` 中 BoundedDiscrete/ColorPicker 等），transformer 可串联改写生成结果。
5. **UI 框架**：接口 `clothconfig2/api/ConfigBuilder.java`（`ConfigBuilder.create()`）与 `ConfigEntryBuilder.java`（`startIntSlider/startStrField/startSubCategory/...`，共 25+ 个 start 方法），实现分别在 `impl/ConfigBuilderImpl.java`、`impl/ConfigEntryBuilderImpl.java`；屏幕基类 `gui/AbstractConfigScreen.java` → `ClothConfigScreen`/`GlobalizedClothConfigScreen`，列表容器 `gui/widget/DynamicEntryListWidget.java`，条目基类 `api/AbstractConfigListEntry.java`。
6. **动画与滚动**：`api/animator/RecordValueAnimatorArgs.java`（泛型 record 动画参数，最大文件）、`api/scroll/ScrollingContainer.java` + `impl/EasingMethod.java`，滚动参数集中在 `ClothConfigInitializer`（duration 600、step 16.0、bounce -10）。

## 5. 网络 / 数据驱动 / 配置 / datagen

无网络包与同步代码（`ConfigHolder`/`ConfigData` 中无 sync/Packet）。无 datagen、无 JSON 资源数据驱动（`src/main/resources` 仅 accessWidener 与 `mods.toml`）。配置即上述序列化层；平台差异用 Architectury `@ExpectPlatform`（`autoconfig/util/Utils.java:38`）→ `forge/.../forge/UtilsImpl.java`、`fabric/.../fabric/UtilsImpl.java`。混合访问用 `common|fabric/src/main/resources/cloth-config.accessWidener` 与 `forge/.../accesstransformer.cfg`。

## 6. Mixin

**无**。全仓库 grep `mixin`（java/gradle/json）零命中，无 `*.mixins.json`。

## 7. 值得学的 5 条做法

1. **第三方库 shadow + relocate**：把 gson 依赖（jankson/toml4j/snakeyaml）重定位进 `me.shedaniel.clothconfig.shadowed.*`，避免与宿主 mod 冲突 —— `fabric/build.gradle:62-64`；适用：任何要打包第三方库的前置 lib。
2. **反射 + Unsafe 构造默认值**：`Utils.constructUnsafely(configClass)` / `getUnsafely` / `setUnsafely`，使用户配置 POJO 无需无参构造与 setter —— `autoconfig/util/Utils.java`；适用：注解配置类。
3. **注解 + 类型谓词注册 GUI 生成器**：`registry.registerAnnotationProvider(provider, field -> type 判断, AnnotationClass)`，新增控件类型不用改主流程 —— `autoconfig/gui/DefaultGuiProviders.java`；适用：可扩展的 UI/序列化工厂。
4. **接口 + Impl 分离且构造入口在接口静态方法**：`ConfigBuilder.create()` → `new ConfigBuilderImpl()`，外部只 import `clothconfig2.api` 包 —— `api/ConfigBuilder.java:35-37`；适用：给他人用的库 API 面收敛。
5. **加载失败自动回退默认值并原地重写文件**：`ConfigManager` 构造时 `if (load()) save();`，反序列化异常即 `resetToDefault()` —— `autoconfig/ConfigManager.java:53-55,108-112`；适用：所有 mod 配置文件读写。

## 8. 公开 API 与接入方式

- 高层（零样板）：`me.shedaniel.autoconfig.api` → `@Config(name="x")` + `implements ConfigData` + `AutoConfig.register(MyConfig.class, GsonConfigSerializer::new)` + `AutoConfig.getConfigScreen(MyConfig.class, parent).get()`。
- 低层（自建界面）：`me.shedaniel.clothconfig2.api`（ConfigBuilder、ConfigEntryBuilder、ConfigCategory、AbstractConfigListEntry、Modifier/ModifierKeyCode、ScissorsScreen）与 `gui.entries.*`；扩展点 = `GuiRegistry`（通过 `AutoConfig.getGuiRegistry(Class)` 注入自定义 GuiProvider/GuiTransformer）、`ConfigSerializer.Factory`、`ReferenceProvider`。
