# CeoOfGoogle1/CreateClothes 源码分析

## 1. 基本信息

- Mod 名：Create Clothes；mod_id：`createclothes`；作者：CeoOfGoogle
- 目标：Minecraft 1.20.1 + Forge 47.3.0（`gradle.properties`：`minecraft_version=1.20.1`、`forge_version=47.3.0`、`mapping_channel=parchment` / `2023.09.03-1.20.1`）
- Gradle 插件：`net.minecraftforge.gradle` `[6.0,6.2)` + `org.parchmentmc.librarian.forgegradle` `1.+`（`build.gradle:1-6`）；许可证 MIT；版本 `1.0-1.20.1`
- 编译依赖：**实际上只有 forge + minecraft**。`build.gradle:143-158` 中 Create / Ponder / Flywheel / Registrate / Curios / JEI 依赖全部是注释；`src/main/resources/META-INF/mods.toml` 里 `modId="create"` 的依赖块也被注释掉。即"Create 附属"仅为命名与题材，运行时无 Create API 调用。

## 2. 源码规模与包结构

`find src -name '*.java' | wc -l` = **32 个文件，2631 行**。资源目录只有 `META-INF/mods.toml`，**仓库内没有 assets/data（无贴图、无 lang、无 recipe、无模型 json）**——物品贴图路径如 `createclothes:textures/models/armor/plains_layer_1.png` 在仓库中不存在。

- `net.ceoofgoogle.createclothes`（1 个，主类）
- `.init`（3 个）：`CreateClothesModItems`（142 行，最大）、`CreateClothesModModels`（29）、`CreateClothesModTabs`（85）
- `.item`（22 个）：10 套 "Camo/制服" 基类（每个 127/128 行）+ 帽子/靴类
- `.model`（9 个）：`ModelBucketHat/ModelCap/ModelCoat/ModelCrown/ModelHelmet/ModelOfficerCap/ModelTricorn/ModelTunic/ModelVest`

## 3. 入口与注册

主类 `src/main/java/net/ceoofgoogle/createclothes/CreateClothes.java:12`，纯 `DeferredRegister`（无 Registrate）：

```java
IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
CreateClothesModItems.REGISTRY.register(bus);
CreateClothesModTabs.REGISTRY.register(bus);
```

- `CreateClothesModItems.java:82` `DeferredRegister.create(ForgeRegistries.ITEMS, "createclothes")`，注册写在 `static {}` 块（:81-141），60 余个 `RegistryObject`。注意 mod id 用了字符串字面量而非 `MOD_ID` 常量。
- `CreateClothesModTabs.java:24` `DeferredRegister.create(Registries.CREATIVE_MODE_TAB, "createclothes")`，`CreativeModeTab.builder()` 手写 60 行 `tabData.accept(...)`（未用 `BuildCreativeModeTabContentsEvent`）。
- `CreateClothesModModels.java:9-28`：`@Mod.EventBusSubscriber(bus = MOD, value = {Dist.CLIENT})`，在 `EntityRenderersEvent.RegisterLayerDefinitions` 中注册 9 个 `ModelLayerLocation`。

## 4. 核心系统

**装甲物品族体系（唯一实质系统）**：每个地域迷彩 = 1 个抽象基类，例 `item/PlainsCamoItem.java:27-128`。

1. 匿名 `ArmorMaterial` 实现全套数值：耐久 `{13,15,16,11}[slot]*80`、防御 `{3,6,7,8}`、`getEnchantmentValue()=9`、`getEquipSound()` 取 `item.armor.equip_leather`、`getRepairIngredient()` 返回 `Ingredient.of()`（空）、toughness/knockback 0（:29-61）。
2. 基类内嵌 4 个 `static class Helmet/Chestplate/Leggings/Boots`，各自 `super(Type.X, new Item.Properties())` 并覆盖 `getArmorTexture`；`init/CreateClothesModItems.java:94-97` 把同一族的 4 个槽位注册成 4 个条目（`plains_helmet/plains_tunic/plains_pants/plains_boots`）。
3. 自定义外观走 Forge 的 `IClientItemExtensions#getHumanoidArmorModel`：用 `Minecraft.getInstance().getEntityModels().bakeLayer(...)` + `Map.of("body"/"head"/"left_arm"...)` 手拼 `HumanoidModel` 局部部件，其余部位给空 `ModelPart`；再同步 `crouching/riding/young`（`PlainsCamoItem.java:89-121`）。
4. 4 套 "cloth" 材料物品（`CLOTH`/`STURDY_CLOTH`/各迷彩 cloth）只是裸 `new Item(new Item.Properties())`，无用途逻辑（:130-140）。

## 5. 网络 / 数据驱动 / 配置 / datagen

均为**无**：无网络包、无 `ModConfigSpec`、无 datagen、无 JSON 数据驱动（`resources` 仅 mods.toml）。README 提到的 parachute、套装闪避等特性尚未实现。

## 6. Mixin

**无**（仓库内无 mixins.json、无 mixin 包）。

## 7. 值得学的具体做法

1. "一族 4 槽位 = 1 基类 + 4 内嵌子类"的装甲压缩写法：`item/PlainsCamoItem.java:64-127`，适配物品数多、逻辑重复的服装类 mod。
2. 用 `IClientItemExtensions#getHumanoidArmorModel` 单件替换原版装甲模型（不动 HumanoidModel 全量）：`item/PlainsCamoItem.java:89-100`，需自定义服饰外形时。
3. 客户端专属注册放 `@Mod.EventBusSubscriber(bus=MOD, value=Dist.CLIENT)`，`EntityRenderersEvent.RegisterLayerDefinitions` 集中注册层：`init/CreateClothesModModels.java:9-28`。
4. 反向教训：注册用字面量 `"createclothes"` 而非 `MOD_ID`（`init/CreateClothesModItems.java:82`），以及 `MinecraftForge.EVENT_BUS.register(this)` 后无任何 `@SubscribeEvent`（`CreateClothes.java:19`）。
5. 反向教训：依赖块整体注释但保留标识名（`build.gradle:143-148`、`mods.toml` create 依赖注释），且 assets 未入库 —— 属模板半成品，不建议照抄其工程结构。

## 8. 库/API 扩展点

不适用（非库/前置 mod，无对外 API 或扩展点）。
