# fonnymunkey/SimpleHats 源码分析报告

## 1. 基本信息

- Mod 名：SimpleHats；mod_id：`simplehats`；作者：Fonnymunkey（代码）、ArtsyDy（贴图/模型）；版本 `0.3.2`
- 目标：**仅 Forge**，Minecraft `1.18.2` + Forge `40.1.30`（`gradle.properties`、`src/main/resources/META-INF/mods.toml` 声明 `minecraft [1.18.2,1.19)`、`forge [40,)`、`curios [1.18.2-5.0.6.3,)`）；Mixin `compatibilityLevel: JAVA_17`
- Gradle：`net.minecraftforge.gradle 5.1.+`，mappings 用 Parchment `2022.05.22-1.18.2`（`build.gradle:12,17,29`）
- 许可证：mods.toml 的 `license` 字段指向 GitHub URL（`SimpleHatsAux/blob/main/LICENSE`），非 SPDX 标识；本地 checkout 无 LICENSE 文件
- 编译依赖（关键）：`top.theillusivec4.curios:curios-forge:1.18.2-5.0.7.0`（compileOnly + runtimeOnly，且是**强制依赖**）、`mezz.jei:jei-1.18.2:9.5.5.174:api`（compileOnly + runtimeOnly）；**Curios 是它的运行时基座**（帽子靠 Curios 头部槽佩戴）

## 2. 源码规模与包结构

- `.java` **25 个文件，共 2374 行**（`find -name '*.java' -exec wc -l {} +`）
- 包结构（`fonnymunkey.simplehats`）：
  - 根：`SimpleHats.java`（主类）
  - `common/init/` 3 个：`ModRegistry`(6.4KB)、`HatJson`(**33.5KB，最大文件**)、`ModConfig`
  - `common/item/` 5 个：`HatItem`、`HatItemDyeable`、`BagItem`、`HatDisplayItem`
  - `common/entity/` 1 个：`HatDisplay`(12.8KB)
  - `common/loot/` 2 个、`common/recipe/` 2 个、`common/EventHandler`
  - `client/` 3 个：`ClientEventHandler`、`HatRepositorySource`、`hat/HatLayer`；`client/hatdisplay/` 3 个（Renderer/Model/Layer）
  - `mixin/core/` 2 个、`util/` 2 个（`HatEntry` 10KB、`UUIDHandler`）、`compat/JEIPlugin`
- 资源：`assets/simplehats/models/item/*.json` 每个帽子一个物品模型，`textures/item/hats/`，**132 个 `.mcmeta`**（动画贴图），外加 `assets/minecraft/optifine/emissive.properties`；共 373 json / 419 png

## 3. 入口与注册

主类 `src/main/java/fonnymunkey/simplehats/SimpleHats.java:21-42`，构造期完成配置注册、IMC、帽子 JSON 读取与四个 DeferredRegister：

```java
@Mod(SimpleHats.modId)
public class SimpleHats {
    public SimpleHats() {
        IEventBus eventBus = FMLJavaModLoadingContext.get().getModEventBus();
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, ModConfig.COMMON_SPEC);
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ModConfig.CLIENT_SPEC);
        eventBus.addListener(this::enqueueIMC);
        HatJson.registerHatJson();
        ModRegistry.ITEM_REG.register(eventBus); ModRegistry.ENTITY_REG.register(eventBus);
        ModRegistry.RECIPE_REG.register(eventBus); ModRegistry.LOOT_REG.register(eventBus);
    }
}
```

- `ModRegistry.java`：DeferredRegister 注册背包袋（8 种稀有度/节日）、帽子碎片、图标、`HatDisplayItem`、`special` 帽子、`EntityType<HatDisplay>`、2 个 `RecipeSerializer`（`SimpleRecipeSerializer`）、2 个 `GlobalLootModifierSerializer`。
- **帽子本体不用 DeferredRegister**：`common/EventHandler.java:33-43` 在 `RegistryEvent.Register<Item>` 里遍历 `HatJson.getHatList()`，按 `getUseDye()` 选择 `HatItemDyeable`/`HatItem` 注册，并把染色帽挂进 `CauldronInteraction.WATER.put(...)`。
- IMC：`SimpleHats.java:44-46` 用 `InterModComms.sendTo(CuriosApi.MODID, SlotTypeMessage.REGISTER_TYPE, () -> SlotTypePreset.HEAD.getMessageBuilder().cosmetic().build())` 向 Curios 注册 **cosmetic 头部槽**。

## 4. 核心系统

**a) 帽子即数据（`common/init/HatJson.java`）** 职责：从 `config/simplehats.json` 读取全部帽子定义。
- 无文件时用硬编码的 `private static final List<HatEntry> defaultHats`（`HatJson.java:23-318`，上百条）生成默认 JSON 并当作列表使用（`:324-355`）；有文件时 `gson.fromJson` 逐条读，`validateName` 用 `ResourceLocation.validPathChar` 校验名字、查重（`:389-395`），再 `validateDeserializedEntry()` 补默认值。
- `util/HatEntry.java` 字段：`hatName / hatRarity / hatWeight / variantRange / hatSeason`，内嵌 `HatDyeSettings(useDye, defaultColor)` 与 `HatParticleSettings(useParticle, particleTypeString, particleFrequency, HatParticleMovement{TRAILING_HEAD, TRAILING_FEET, TRAILING_FULL})`；`particleTypeParsed` 标 `transient` 避免序列化。

**b) Curios 接入（`common/item/HatItem.java` + `mixin/core/MixinCuriosHelper.java`）**
- `HatItem implements ICurioItem`，构造器里 `setRegistryName(entry.getHatName())` 让动态注册拿到配置中的 ID（`HatItem.java:37`）；`getDropRule` 依据 `ModConfig.COMMON.keepHatOnDeath` 返回 `DropRule.ALWAYS_KEEP`；`getEquipmentSlot` 依配置返回 `EquipmentSlot.HEAD`。
- mixin 让帽子天然属于头部 curios 标签：`@Inject(method = "getCurioTags", at = @At("RETURN"), cancellable = true, remap = false)`，若 `item instanceof HatItem` 则 `set.add("head")`。
- `common/EventHandler.java:47-57` 监听 `CurioEquipEvent`，给 `special` 帽子写入 `CustomModelData = UUIDHandler.getUUIDMap().getOrDefault(playerUUID, 0)`（按玩家 UUID 决定专属皮肤）。

**c) 渲染（`client/hat/HatLayer.java` + `mixin/core/MixinHumanoidArmorLayer.java` + `client/ClientEventHandler.java`）**
- `HatLayer extends RenderLayer`，被加到默认/纤细玩家渲染器（`ClientEventHandler.java:42-50`）；遍历 Curios 的 `cosmeticStacks`/`stacks` 与 `getRenders()` 可见性，用 `ItemInHandRenderer.renderItem(..., ItemTransforms.TransformType.HEAD, ...)` 把帽子当**物品模型**渲染，`translateToHead` 做 `-0.25F` 位移 + 180° Y 旋转 + `0.625` 缩放，婴儿/村民单独修正；忽略第一人称（`forceFirstPersonNoRender` 配置）。
- 粒子由 `HatParticleSettings` 驱动，按 `TRAILING_*` 选高度并在 `level.addParticle`。
- `MixinHumanoidArmorLayer.renderArmorPiece` HEAD 注入：头部槽存在帽子的 cosmetic 时 `ci.cancel()` 隐藏头盔。

**d) 运行期下载资源包（`util/UUIDHandler.java` + `client/HatRepositorySource.java`）**
- `UUIDHandler` 从 GitHub raw 拉 UUID→皮肤编号映射和 `simplehats_forge_1.18.2_hatdl.zip`（`:20,41-60`），存到配置目录。
- `HatRepositorySource implements RepositorySource`：扫描 `config/simplehats_hatdl/` 下的每个 zip，`Pack.create("resources/"+name, true, () -> new FilePackResources(path), constructor, Pack.Position.TOP, PackSource.BUILT_IN)`；由 `ClientEventHandler.java:52-56` 在 `AddPackFindersEvent` 中 `event.addRepositorySource(...)` 挂载。

**e) 战利品与配方（`common/loot/`、`common/recipe/`）**
- 2 个 `GlobalLootModifierSerializer`（箱子/实体注入），配 `data/simplehats/loot_modifiers/*.json`、`data/simplehats/loot_tables/inject/*` 与 `data/forge/loot_modifiers/global_loot_modifiers.json`；`HatScrapRecipe`/`HatVariantRecipe` 用 `SimpleRecipeSerializer` 实现"碎片回收/变体合成"。
- `compat/JEIPlugin.java` 实现 `IModPlugin`（`getPluginUid` + `registerRecipes`）。

**f) 展柜实体（`common/entity/HatDisplay.java`）** `LivingEntity` 子类，`NonNullList<ItemStack> hatItemSlots` 单槽 + `SynchedEntityData DATA_CLIENT_FLAGS`，属性在 `EntityAttributeCreationEvent` 注册（`EventHandler.java:27-30`），`interactAt` 支持换帽子，客户端有独立 `HatDisplayRenderer/Model/Layer`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包；仅原版 `SynchedEntityData`（`HatDisplay`）与 Curios 自带同步。
- 数据驱动：**帽子定义走配置文件（`config/simplehats.json`）而非 datapack**；战利品/配方走标准 datapack JSON（手写，非 datagen）。UI/模型资源走资源包，支持运行期注入外部 zip。
- 配置：2 个 `ForgeConfigSpec`（COMMON / CLIENT），键包括 `keepHatOnDeath`、`allowUpdates`、`seasonalBagChance`、`allowHatInHelmetSlot`、`hatYOffset`、`forceFirstPersonNoRender`（`common/init/ModConfig.java:20-62`）；主类里用 `manualAllowUpdateCheck()` 把更新检查提前到资源加载前（`SimpleHats.java:33-36`）。
- datagen：无（无 `data/` 生成源，资源全部手写）。

## 6. Mixin

- 配置：`src/main/resources/mixins.simplehats.json`（`package: fonnymunkey.simplehats.mixin.core`，`refmap: mixins.simplehats.refmap.json`，`mixins: [MixinCuriosHelper]`，`client: [MixinHumanoidArmorLayer]`）
- `MixinCuriosHelper` → **外部 mod** `top.theillusivec4.curios.common.CuriosHelper.getCurioTags`，`RETURN` 注入（`remap = false`，因目标非 MC 类）
- `MixinHumanoidArmorLayer` → `HumanoidArmorLayer.renderArmorPiece`，`HEAD` 注入 + `ci.cancel()`

## 7. 值得学的 5 条具体做法

1. **配置 JSON 即注册表 + 自愈默认值**：文件不存在就写出内置 `defaultHats` 全量模板，之后只用文件（`common/init/HatJson.java:324-355`），用户编辑即扩展内容；配合 `ResourceLocation.validPathChar` 校验 + 查重防坏档（`:389-395`）。适合"内容量大、想让服主自定义"的外观类 mod。
2. **`RegistryEvent.Register<T>` 里批量动态注册 + 构造器 `setRegistryName`**：`EventHandler.java:33-43` + `HatItem.java:37`，绕开 DeferredRegister 只能静态声明的问题（1.18 Forge 的经典手法；1.21 需换成 `DeferredRegister` + `RegistryBuilder`/数据驱动）。
3. **不写 datapack 也能进别人的槽位**：`IMC` 注册 curios 槽类型 + mixin 往 `getCurioTags` 返回集合里塞 `"head"`（`SimpleHats.java:44-46`、`MixinCuriosHelper.java`），避免强制玩家装数据包；调用非 MC 类时记得 `remap = false`。
4. **用物品模型代替自定义实体模型渲染装备**：`HatLayer` 用 `ItemTransforms.TransformType.HEAD` 走原版物品渲染管线（`client/hat/HatLayer.java`），帽子只需一个 `models/item/*.json` + 贴图即可，零额外建模成本；个体差异交给 `CustomModelData`。
5. **`AddPackFindersEvent` + 自定义 `RepositorySource` 做运行期内容分发**：把远程 zip 丢进配置目录即自动成为 `Position.TOP` 内置资源包（`client/HatRepositorySource.java:29-37`、`client/ClientEventHandler.java:52-56`），适合贴图/模型量大且需更新的 mod（注意 `UUIDHandler` 是明文 HTTP 拉取，生产环境须加校验）。

## 8. 公开 API

非库 mod。对外扩展点仅两类：`config/simplehats.json`（内容层自定义）与 GitHub 上的 `SimpleHatsAux` 资源仓库（资源层）；无 Java API 包或文档化扩展接口。
