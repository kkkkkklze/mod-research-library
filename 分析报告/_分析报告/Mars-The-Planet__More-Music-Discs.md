# More Music Discs 源码分析报告

## 1. 基本信息
- Mod 名 More Music Discs / mod_id `morediscs` / 作者 Mars / 版本 35 / 许可证 MIT（`gradle.properties`）
- 目标平台：multiloader 四模块 `common`/`fabric`/`forge`/`neoforge`（`settings.gradle`）；MC 1.21.5（`minecraft_version_range=[1.21.5,1.22)`）、Fabric Loader 0.16.10 / Fabric API 0.119.5+1.21.5、Forge 55.0.1、NeoForge 21.5.4-beta，Java 21，Parchment 2025.03.23
- Gradle 插件：`fabric-loom 1.10-SNAPSHOT` + `net.neoforged.moddev 2.0.62-beta`（`build.gradle`）+ 自研 `buildSrc/src/main/groovy/multiloader-common.gradle`/`multiloader-loader.gradle`
- 编译依赖：**Deimos 2.1**（`common/build.gradle:24` `implementation "maven.modrinth:deimos:1.21.5-neoforge-2.1"`，fabric/forge 模块各自对应坐标），`neoforge.mods.toml` 声明 `modId = "deimos"` required —— 本仓库是 Deimos 的官方示范消费者

## 2. 源码规模与包结构
实测 14 个 `.java`、655 行，是四仓库中最小者。分布：`common`（`com/mars/morediscs/`：`CommonClass.java` 128、`MoreDiscsConfig.java` 47、`Constants.java` 11、`mixin/MixinMinecraft.java` 16、`platform/Services.java` 15、`platform/services/IPlatformHelper.java` 13）、`fabric`（`MoreDiscs.java` 96 + `FabricPlatformHelper` 22）、`forge`（`MoreDiscs.java` 67 + `DiscAdder.java` 64 + helper 23）、`neoforge`（`MoreDiscs.java` 68 + `DiscAdder.java` 62 + helper 23）。
资源目录（本地拷贝）`common/src/main/resources` 下仅有 `morediscs.mixins.json`，未发现 assets/data 文件（**未确认**是 bulk 拷贝剔除了资源，还是资源在别处）。

## 3. 入口与注册
三个加载器各写一份入口，逻辑一致。NeoForge 版 `neoforge/src/main/java/com/mars/morediscs/MoreDiscs.java:22`：

```java
@Mod(MOD_ID) public class MoreDiscs {
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(MOD_ID);
    public static final DeferredRegister<CreativeModeTab> CREATIVE_MODE_TAB = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);
    public static final HashMap<String, DeferredItem<Item>> ITEM_LIST = new HashMap<>();
    public static final DeferredRegister<MapCodec<? extends IGlobalLootModifier>> GLOBAL_LOOT_MODIFIER_SERIALIZERS = ...;
    public static final Supplier<MapCodec<DiscAdder>> MY_LOOT_MODIFIER = GLOBAL_LOOT_MODIFIER_SERIALIZERS.register("disc_adder", () -> DiscAdder.CODEC);
    public MoreDiscs(IEventBus bus) { CommonClass.init(); MUSIC_DISCS_NAMES.forEach(MoreDiscs::registerItem); ITEMS.register(bus); ... }
}
```

注册方式：物品全部由 `CommonClass.MUSIC_DISCS_NAMES`（110+ 条硬编码字符串名，如 `music_disc_tragicdecision`）循环生成，`registerItem` 里 `new Item(new Item.Properties().stacksTo(1).rarity(Rarity.RARE).jukeboxPlayable(registerJukeboxSong(name + "_sound")))`，同时写入 `ITEM_LIST` 供后续查找；创造标签用 `.withTabsBefore(CreativeModeTabs.COMBAT)` + `displayItems` 遍历。Fabric 版改为 `Registry.register(BuiltInRegistries.CREATIVE_MODE_TAB, ...)` + `FabricItemGroup.builder()`。

## 4. 核心系统
1. **Deimos 配置消费**（`common/src/main/java/com/mars/morediscs/MoreDiscsConfig.java`）：`public class MoreDiscsConfig extends DeimosConfig`，字段加 `@Entry`（`enable_loot_modifiers`、`discs_loot_list` 为 `List<String>`），`CommonClass.init()` 第一行就是 `DeimosConfig.init(MOD_ID, MoreDiscsConfig.class)` —— 这是"库如何被接入"的最小可用示例。
2. **字符串驱动的掉落配置**：`discs_loot_list` 每行格式 `"<loot_table>, <disc1>, <disc2>, <5|1|S>"`（如 `"minecraft:chests/desert_pyramid, music_disc_tragicdecision, music_disc_desert, ..., 5"`）；末尾 `5` 表示 1/5 概率、`1` 表示必掉、`S` 表示仅骷髅击杀掉落。
3. **NeoForge 全局掉落修改器**（`neoforge/src/main/java/com/mars/morediscs/DiscAdder.java:22`）：`extends LootModifier`，`CODEC = RecordCodecBuilder.mapCodec(inst -> LootModifier.codecStart(inst).apply(inst, DiscAdder::new))`，`doApply` 里用 `lootContext.getQueriedLootTableId()` 匹配配置行，`random.nextIntBetweenInclusive(...)` 抽取，`S` 分支用 `LootContextParams.DAMAGE_SOURCE.getEntity() instanceof Skeleton` 判断。Forge 版同结构（用旧签名 `doApply(LootTable, ObjectArrayList, LootContext)`，需 `@NotNull`）。
4. **Fabric 走事件而非 GLM**（`fabric/src/main/java/com/mars/morediscs/MoreDiscs.java:49+`）：用 `LootTableEvents.MODIFY` + `LootPool.lootTableItem` / `LootItemRandomChanceCondition` / `LootItemEntityPropertyCondition` + `EntityTypePredicate.of(EntityTypeTags.SKELETONS)` 手工搭等价的掉落池，说明"同一份字符串配置、三套平台实现"的多加载器写法。
5. **空 mixin 占位**：`common/.../mixin/MixinMinecraft.java` 对 `Minecraft.<init>` 做 `@At("TAIL")` 注入但方法体为空，仅证明 mixin 管线可用（`morediscs.mixins.json` 里 `mixins: []`、`client: ["MixinMinecraft"]`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：无。数据驱动：仅数据包战利品表（由 GLM/Fabric 事件在运行时改写，无自带 json）。配置：完全委托 Deimos（注解式 JSON 配置 + 自动配置界面，见 `Mars-The-Planet__Deimos.md`）。datagen：无；物品/唱片曲目（`JUKEBOX_SONG` 注册键 `morediscs:<name>_sound`）均为代码注册 + 资源文件，本地拷贝中未见对应 json（**未确认**）。

## 6. Mixin
`common/src/main/resources/morediscs.mixins.json`（package `com.mars.morediscs.mixin`，`compatibilityLevel: JAVA_18`，`refmap: ${mod_id}.refmap.json`，`injectors.defaultRequire: 1`），内容物仅上文第 4.5 条的空 `MixinMinecraft`；三平台另有 `morediscs.fabric/forge/neoforge.mixins.json`，`neoforge.mods.toml` 通过两个 `[[mixins]]` 块同时挂载 common + 平台配置。

## 7. 值得学的 5 条具体做法
1. 用"名字列表 + 循环注册"批量生成上百个同类物品并同时填 `HashMap<String, DeferredItem<Item>>` 索引，避免手写上百个常量（`neoforge/.../MoreDiscs.java:47`）。
2. 把行为差异（概率/必掉/仅骷髅）编码进一行配置字符串，玩家可自行改掉落表而不改代码（`MoreMusicDiscsConfig.discs_loot_list`）。
3. 同一个功能按平台选最合适的机制：NeoForge/Forge 用 `IGlobalLootModifier`，Fabric 用 `LootTableEvents.MODIFY`，公共逻辑（配置解析）留在 `common`（`fabric/.../MoreDiscs.java:49`）。
4. 第三方库（Deimos）的接入只写两行：`extend DeimosConfig` + `DeimosConfig.init(MOD_ID, ...)`，其余（JSON 读写、配置界面）由库代管（`common/.../MoreDiscsConfig.java:6-9`、`CommonClass.java:10`）。
5. 三平台构建脚本共用 `buildSrc` 的 `multiloader-common.gradle`/`multiloader-loader.gradle`（依赖 `common` 的 `commonJava`/`commonResources` capability），跨加载器工程只需维护一份 common 源码。

## 8. 公开 API（库/前置类）
本体不是库；它演示了 Deimos 的对外用法：`com.mars.deimos.config.DeimosConfig`（父类 + `@Entry`/`@Comment`/`@Server` 注解）、`DeimosConfig.init(String modid, Class<? extends DeimosConfig>)`，并需在 mods.toml 里声明 `deimos` 为 required 依赖。
