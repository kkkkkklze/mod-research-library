# Deimos 源码分析报告

## 1. 基本信息
- Mod 名 Deimos / mod_id `deimos` / 作者 Mars / 版本 2.7 / 许可证 MIT（`LICENSE.txt:1`、`gradle.properties`）
- 目标平台：multiloader 四模块 `common`/`fabric`/`forge`/`neoforge`（`settings.gradle`）；MC 1.21.1（`minecraft_version_range=[1.21,1.22)`）、Fabric Loader 0.16.9、Forge 52.0.28、NeoForge 21.1.80。Java 21
- Gradle 插件：`fabric-loom 1.8-SNAPSHOT` + `net.neoforged.moddev 2.0.62-beta`（`build.gradle`），自研 `buildSrc/src/main/groovy/multiloader-common.gradle`（archivesName = `mod_id-mcver-project.name`，暴露 `commonJava`/`commonResources` 两个 artifact）
- 编译依赖：`compileOnly` mixin 0.8.5、mixinextras-common 0.3.5 + annotationProcessor（`common/build.gradle:16-23`）。自身是前置库，被 `maven.modrinth:deimos` 坐标消费（见 More-Music-Discs）

## 2. 源码规模与包结构
实测 14 个 `.java`、1414 行。包（`common/src/main/java/com/mars/deimos/`）：`config`（DeimosConfig 720 行）、`datagen`（DeimosRecipeGenerator 455 行）、`mixin`（RecipeManagerMixin 32）、`platform`（Services 12）+ `platform/services`（IPlatformHelper 9）、根包 `Constants`/`CommonClass`。加载器侧：`neoforge/.../Deimos.java` 33、`forge/.../Deimos.java` 35、`fabric/.../Deimos.java` 10 + `config/ModMenuApiImpl.java` 26 + 三个 `PlatformHelper` 各 20-21 行。

## 3. 入口与注册
NeoForge 侧 `neoforge/src/main/java/com/mars/deimos/Deimos.java:18`：

```java
@Mod(MOD_ID) public class Deimos {
    public Deimos(IEventBus eventBus) { CommonClass.init(); }
    @EventBusSubscriber(modid = MOD_ID, bus = Bus.MOD, value = Dist.CLIENT)
    public static class ClientModEvents {
        @SubscribeEvent public static void onPostInit(FMLClientSetupEvent event) {
            ModList.get().forEachModContainer((modid, mc) -> {
                if (DeimosConfig.configClass.containsKey(modid))
                    mc.registerExtensionPoint(IConfigScreenFactory.class, (c, screen) -> getScreen(screen, modid));
            });
        } }
}
```

**没有自己的 DeferredRegister**——Deimos 不注册任何游戏内容，只在 `common/.../CommonClass.java:7` 用 `Services.load(IPlatformHelper.class)`（ServiceLoader）拿平台实现。Forge 用 `ConfigScreenHandler.ConfigScreenFactory`、Fabric 用 `ModMenuApiImpl` 走 ModMenu 提供同一配置界面。注意：本地拷贝中未见 `META-INF/services/com.mars.deimos.platform.services.IPlatformHelper` 文件，ServiceLoader 的实际装配方式**未确认**。

## 4. 核心系统
1. **注解式 JSON 配置**（`common/.../config/DeimosConfig.java:63`）：`@Entry`（width/min/max/name/isColor/isSlider/category）、`@Comment`、`@Server`、`@Hidden`、`@Client` 五个运行时注解；`init(modid, class)` 反射扫 `config.getFields()`，把客户端可见字段登记为 `EntryInfo`（含 `field/dataType/defaultValue/value/tempValue/inLimits`，行 68-113），配置写在 `config/<modid>.json`，用 Gson（`excludeFieldsWithModifiers(PRIVATE, TRANSIENT)` + 自定义 `HiddenAnnotationExclusionStrategy` 只序列化 `@Entry` 字段 + `ResourceLocation.Serializer` + setPrettyPrinting，行 117-123）；文件不存在/JSON 损坏时自动 `write(modid)` 重建。
2. **配置界面**（同文件 300-660）：`DeimosConfigScreen`（用原版 `TabManager`/`TabNavigationBar` 分页）、`DeimosConfigListWidget extends ContainerObjectSelectionList<ButtonEntry>`、`DeimosSliderWidget extends AbstractSliderButton`；布尔值渲染为 yes/no 按钮、枚举循环切换、数字用 `INTEGER_ONLY`/`DECIMAL_ONLY`/`HEXADECIMAL_ONLY` 正则校验并在失焦前保持 `tempValue`。
3. **运行时配方生成**（`datagen/DeimosRecipeGenerator.java:12` 静态 `List<JsonObject> RECIPES` + 24 个 `createShapedRecipeJson/createSmeltingJson/createStoneCuttingJson` 等重载，同时支持 String 与 `ResourceLocation` 两种入参），配合 `mixin/RecipeManagerMixin.java:17` `@Inject(method = "apply*", at = @At("HEAD"))`（`@Mixin(value = RecipeManager.class, priority = 1100)`）把 JSON 以 `deimos:deimosgeneratedcraftingN` 为 id 塞进原版 map——**不做真 datagen，纯运行时注入**。
4. **多加载器抽象**（`platform/Services.java:9` + `platform/services/IPlatformHelper.java`：`getConfigDirectory()`、`isClientEnv()`），三个平台各一个实现（`FMLPaths.CONFIGDIR` / `FabricLoader#getConfigDir`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：无。数据驱动：仅上面的配方 JSON 注入。配置：见 4.1/4.2（Gson 手写，非 ModConfigSpec）。datagen：无 `DataGenerator`/`GatherDataEvent`，`datagen` 包名下的类实为运行时工具。

## 6. Mixin
配置 `common/src/main/resources/deimos.mixins.json`（package `com.mars.deimos.mixin`，`compatibilityLevel: JAVA_18`，`refmap: ${mod_id}.refmap.json`），仅 `RecipeManagerMixin`；三平台各自还有空的 `deimos.<loader>.mixins.json`（`neoforge.mods.toml` 里 `[[mixins]]` 同时挂载 common + loader 两份）。

## 7. 值得学的 5 条具体做法
1. 用注解 + 反射一次性解决"多 mod 共用一套配置系统"：`DeimosConfig.init(modid, MyConfig.class)` 即可让任意 mod 拥有 JSON 配置与配置界面（`config/DeimosConfig.java:133`）。
2. 配置界面通过 `registerExtensionPoint(IConfigScreenFactory)` 挂到**所有**已加载 mod 容器上，而不是自己的 mod（`neoforge/.../Deimos.java:24-29`），使库可以为下游 mod 提供配置页。
3. Gson 的 `ExclusionStrategy` 白名单序列化（只导出 `@Entry` 字段），避免把 GUI 状态写进文件（`DeimosConfig.java:663-670`）。
4. 极端轻量的"伪 datagen"：静态 `RECIPES` 列表 + `apply*` 注入（`mixin/RecipeManagerMixin.java:17`），适合附属 mod 快速生成配方而不用搭 data generator。
5. 平台差异只保留 `getConfigDirectory()`/`isClientEnv()` 两个方法（`platform/services/IPlatformHelper.java`），多加载器库可以做到极小表面积 + 三方 copy 的 buildSrc 插件结构。

## 8. 公开 API（库/前置类）
入口 `com.mars.deimos.config.DeimosConfig`（继承即可获得配置）、`com.mars.deimos.datagen.DeimosRecipeGenerator`（24 个静态建配方方法）、`com.mars.deimos.platform.Services`/`IPlatformHelper`、`com.mars.deimos.Constants`。下游接入方式见 `Mars-The-Planet/More-Music-Discs`：`common/build.gradle` 里 `implementation "maven.modrinth:deimos:1.21.5-neoforge-2.1"`，`neoforge.mods.toml` 声明 `modId = "deimos"` 为 required 依赖。
