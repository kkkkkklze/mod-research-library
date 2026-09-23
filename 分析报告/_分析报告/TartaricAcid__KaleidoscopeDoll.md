# TartaricAcid/KaleidoscopeDoll 源码分析报告

## 1. 基本信息

- Mod 名：Kaleidoscope Doll（森罗物语：玩偶）；mod_id `kaleidoscope_doll`，`archivesBaseName = kaleidoscopedoll`
- 作者：`mod_authors=ysbbbbbb`（仓库挂在 TartaricAcid 名下）；版本 `1.4.1-forge+mc1.20.1`
- **本地检出为 Forge 47.3.0 / MC 1.20.1，Java 17**（`gradle.properties`、`src/main/resources/META-INF/mods.toml`）；`README.md` 徽章自称 Forge | NeoForge | Fabric × 1.20.1 | 1.21.1（多加载器项目，本仓库内未确认其它加载器源码）
- 许可证：`mod_license=All Rights Reserved`（README 徽章写 “BSD 3 Clause | All Rights Reserved”，仓库根目录无 LICENSE 文件）
- Gradle 插件：`net.minecraftforge.gradle [6.0.16,6.2)`、`parchmentmc.librarian.forgegradle`、`spongepowered.mixin 0.7.+`；**未配置 AccessTransformer**
- 依赖：compileOnly JEI 15.20.0.105 / EMI 1.1.22 / Curios 5.9.1 API；implementation Jade 11.13.1；runtimeOnly 东方小女仆（touhou-little-maid）、Curios；Create/Ponder 依赖被注释掉；仓库声明 `flatDir { dir 'libs' }` 优先本地 jar（多加载器项目常见做法）

## 2. 源码规模与包结构

- `.java` **91 个，7775 行**（`find src -name '*.java' | wc -l` / `wc -l` 汇总）；`src/generated/resources` 由 datagen 产出
- 包结构（全部在 `com/github/ysbbbbbb/kaleidoscopedoll/` 下）：`block`＋`block/entity`、`client/{bedrock(+model,pojo), custom, event, gui, render, resources}`、`command/subcommand`、`compat/{curios,emi,jade,jei}`、`config`、`data/{custom,resources}`、`datagen`、`entity`、`event`、`init/registry`、`inventory`、`item/crafting`、`network/message`、`utils`
- 最大文件：`event/ModRegisterEvent.java` 713 行（占全仓近 10%）、`entity/DollEntity.java` 635、`client/gui/ComputerMenuScreen.java` 335、`item/DollEntityItem.java` 323、`client/gui/TweaksToolScreen.java` 291、`client/bedrock/BedrockModel.java` 290、`client/custom/CustomDollLoader.java` 244、`block/DollMachineBlock.java` 213、`client/render/DollEntityRender.java` 181、`client/bedrock/model/BedrockPart.java` 165、`inventory/ComputerMenu.java` 164、`block/DollBlock.java` 152

## 3. 入口与注册

主类 `src/main/java/com/github/ysbbbbbb/kaleidoscopedoll/KaleidoscopeDoll.java:14`，8 个 DeferredRegister（含 `ModContainer.CONTAINER_TYPE`）；`init/ModBlocks.java:21-26` 只注册机器类方块（doll_machine、三种 gift_box、computer、custom_doll），`init/ModItems.java` 同类；`init/ModEntities.java:14` 注册 `DollEntity`（`MobCategory.MISC`，0.75×0.75）；`init/registry/CommonRegistry.java:13` 在 `FMLCommonSetupEvent` 里 `enqueueWork(CuriosCompat::commonSetup)` + `NetworkHandler::init`。

**核心特征：694 个玩偶不在 DeferredRegister 里，而是 `RegisterEvent` 里循环注册**——`event/ModRegisterEvent.java:671-695`：

```java
private static final int MAX_DOLL_COUNT = 694;
if (event.getRegistryKey().equals(ForgeRegistries.BLOCKS.getRegistryKey())) {
    IntStream.range(0, MAX_DOLL_COUNT).forEach(i -> {
        ResourceLocation name = new ResourceLocation(KaleidoscopeDoll.MOD_ID, "doll_" + i);
        DollBlock block = new DollBlock();
        DOLL_BLOCKS.put(name, block);
        event.register(ForgeRegistries.BLOCKS.getRegistryKey(), name, () -> block);
    });
}
// 紧接着对 ITEMS 注册表再来一遍，从 DOLL_BLOCKS 取方块构造 DollItem(block, 提示文本)
```

同文件顶部维护三张提示表：`VANILLA_TOOLTIPS`（引用其它 mod 主题）、`SPECIAL_TOOLTIPS`（赞助者署名）、`AUTHOR_DOLLS`，配合 `registerVanillaTooltips/registerAuthorTooltips/registerSpecialTooltips` 三个小工具方法按 `doll_<n>` 编号登记。

## 4. 核心系统

**A. 700 级贴图变体的“同款方块 + 编号注册”** `event/ModRegisterEvent.java:21-27,671-695`
同一 `DollBlock`/`DollItem` 类靠 `doll_0..doll_693` 资源路径区分外观（模型/贴图为 datagen 或手写资源），提示文本用 `Map<ResourceLocation, String>` 注入而不是子类化。`datagen/TagItem.java`（170 行）、`datagen/BlockStateGenerator/BlockModelGenerator` 配合批量产出；`compat/jei/EntityDollRecipeMaker.java` + `EntityDollSubtype.java` 用 JEI subtype 把 694 个变体压成一个“信息页”。

**B. Bedrock 模型解析渲染（本仓库最有复用价值的一块）** `client/bedrock/`
- POJO 层 `client/bedrock/pojo/`：`BedrockModelPOJO/BedrockVersion/GeometryModel/Description/BonesItem/CubesItem/FaceItem/FaceUVsItem`，即 Blockbench “基岩版几何模型” JSON 的完整数据模型
- 构建层 `client/bedrock/BedrockModel.java:31`（`extends Model`）：`HashMap<String, BedrockPart> modelMap` + `HashMap<String, BonesItem> indexBones`，逐 bone/逐 cube 转换，工具方法 `convertPivot/convertOrigin/convertRotation`（度数→`Math.PI/180`）、`getVisibleBounds*` 处理可见边界；`BedrockModelUtil` 提供共享 GSON
- 结果：可用资源包/配置目录里的 `.geo.json` 驱动任意玩偶外观（`client/render/CustomDollRender`、`DollEntityRender`）

**C. 自定义玩偶的“配置目录 + zip + 热重载 + 同步”全链路** `client/custom/CustomDollLoader.java:29`、`data/custom/ServerCustomDollLoader.java:21`
- 根目录 `FMLPaths.CONFIGDIR/kaleidoscope_doll/custom`，内含 `models/`、`lang/`、`textures/`；既支持目录遍历也支持 `.zip`（`Pattern.compile("^(?:[^/]+/)?models/[^/]+\\.json$")` 等三条正则做 zip 内过滤）
- 贴图用 MD5 命名注册成动态纹理：`String md5Name = Md5Utils.md5Hex(name); new ResourceLocation(MOD_ID, "custom/" + md5Name); new DynamicTexture(image); Minecraft.getInstance().getTextureManager().register(id, texture)`（`:210-217`）
- 数据流：服务端只持有模型 ID 集合（`ServerCustomDollLoader.MODELS`）→ `ServerCustomDollReloadListener`（`AddReloadListenerEvent` 注册，`init/registry/DatapackRegistry.java:12`）或玩家登录时（`event/EnterServerEvent.java:15`）通过 `CustomDollReloadMessage` 同步 ID 列表给客户端 → 客户端按 ID 从本地配置目录加载模型/贴图；`/kaleidoscope_doll reload` 子命令（`command/subcommand/ReloadCommand.java:25`）服务端重载后 `PacketDistributor.ALL` 全服重发（服务端不传模型内容，省带宽且避免版权分发）

**D. 玩偶实体（投掷/物理/骑乘/挂载）** `entity/DollEntity.java:46`（`extends Entity` 而非 `LivingEntity`，635 行）
- 全同步数据走 `SynchedEntityData`：`DATA_BLOCK_STATE`（`EntityDataSerializers.BLOCK_STATE` 直接同步方块状态决定外观）、`DATA_SCALE/DATA_TRANSLATION`（VECTOR3）、手持物 `DATA_HOLD_ITEM/DATA_ITEM_SCALE/DATA_ITEM_TRANSLATION/DATA_ITEM_ROTATION`、`CUSTOM_DOLL_ID`（字符串）
- NBT 键：`doll_block_state`/`custom_doll_id`/`doll_scale`/`doll_translation`/`drop_from_phantom`（+`_time`）/`hold_item`/`item_scale`/`item_translation`/`item_rotation`
- 交互细节：`tick()` 里 `tickCount > 2` 才开始击退检测（避免刚丢出就撞到投掷者，`:144`）、`bounce()`＋`bounceTime`、`knockbackCount/lastKnockbackTick` 防连击、`rideTick()/getMyRidingOffset()` 支持被骑/挂载其它实体；行为全部由 `config/GeneralConfig` 开关控制
- 同族物品两件：`item/DollEntityItem.java`（323 行，投掷物）与 `item/crafting/DollEntityCraftingRecipe`（`SimpleCraftingRecipeSerializer` 注册，实现“方块玩偶 ↔ 实体玩偶”互转的特殊合成，`init/ModRecipes.java:15`）

**E. 幻翼挂玩偶（趣味事件示范）** `event/PhantomSpawnEvent.java:26`
`EntityJoinLevelEvent` 里过滤 `Phantom` + `ServerLevel`，按 `PHANTOM_DOLL_SPAWN_CHANCE`(0.03) 掷骰，**用 `serverLevel.getServer().tell(new TickTask(5, () -> attachRandomDollToPhantom(...)))` 延迟 5 tick 等幻翼完全生成**再做挂载；`dropFromPhantom`/`dropFromPhantomTick` 配合 `PHANTOM_DOLL_EXIST_TICKS`(-1 = 不消失)。

**F. 电脑方块 + 菜单式图鉴** `block/ComputerBlock.java`、`inventory/ComputerMenu.java`、`client/gui/ComputerMenuScreen.java`（335 行）、`network/message/ComputerDollClickMessage.java`
用 `MenuType` + Screen 做玩偶浏览/取用界面，点击走 C2S 消息；同类还有 `TweaksToolItem` + `TweaksToolScreen` + `DollTweakersMessage`（调整玩偶尺寸/旋转/手持物）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkHandler.java:17` `SimpleChannel`（version "1.0.0"），3 个包：`DollTweakersMessage(0, C2S)`、`ComputerDollClickMessage(1, C2S)`、`CustomDollReloadMessage(2, S2C)`；S2C 用手写 `buf.writeVarInt(size) + writeUtf` 序列化字符串集合
- 数据驱动：无 datamap/JSON 配方体系，只有 `ServerCustomDollReloadListener`（`ResourceManagerReloadListener`）从配置目录/zip 读模型 ID；资源包层面由 `client/resources/CustomDollReloadListener` 处理客户端重载
- 配置：`config/GeneralConfig.java` 单一 COMMON，全部 `push("doll")`，注释中英双语（如 `builder.comment("玩偶是否会被水流推动")`），含投掷/水流/重力/粒子/击退力度(0-10)/能否放置在实体上、赞助玩偶开关、幻翼生成概率与存在时长
- datagen：`datagen/DataGenerators.java:17-40`，用 `LootTableProvider(pack, Set.of(), List.of(new SubProviderEntry(LootTableGenerator.BlockLootTables::new, LootContextParamSets.BLOCK)))`，`vanillaPack.addProvider` 出 TagBlock/TagItem，另有 `ModRecipeProvider`、`ForgeAdvancementProvider`、Item/BlockState/BlockModel 生成器

## 6. Mixin

`src/main/resources/kaleidoscope_doll.mixins.json`：`required: false`、`compatibilityLevel: JAVA_17`、package `com.github.ysbbbbbb.kaleidoscopedoll.mixin.compat`、**`refmap` 写成 `kaleidoscope_cookery.refmap.json`（从厨房仓库复制后未改）**；`mixins` 与 `client` 列表均为空，仓库内**无任何 `@Mixin` 类**、无 `mixin` 包目录。`build.gradle` 的 `mixin {}` 块也只保留 `add sourceSets.main` 与 `config` 两行（未开 hotSwap/debug）。

## 7. 值得学的 5 条具体做法

1. **大量同构内容用循环注册 + 单一类 + 数据表驱动差异**：`IntStream.range(0, 694)` + `DOLL_BLOCKS`/三张 tooltip Map，`event/ModRegisterEvent.java:671-695`；适用：几百个变体方块/物品（旗帜、贴纸、变体装饰）。
2. **直接内嵌 Blockbench 基岩版几何模型（`.geo.json`）当渲染数据源**：`client/bedrock/` 的 POJO + `BedrockModel`（含 pivot/origin/角度换算），比自研模型格式省事且美术友好；适用：装饰/雕像类 mod。
3. **服务端只同步“ID 清单”，模型与贴图由客户端本地配置目录加载**：`ServerCustomDollLoader` + `CustomDollReloadMessage`；适用：用户自上传资源（皮肤/立绘）且不想让服务器分发内容。
4. **动态纹理用 MD5 命名注册**：`Md5Utils.md5Hex(name)` → `kaleidoscope_doll:custom/<md5>` + `DynamicTexture`（`client/custom/CustomDollLoader.java:210-217`），天然去重、避免非法字符 ID。
5. **实体外观直接同步 `BlockState` 而非自建外观枚举**：`EntityDataSerializers.BLOCK_STATE` + `DATA_BLOCK_STATE`（`entity/DollEntity.java:47`），配合 `tickCount > 2` 才做击退判定、延迟 `TickTask` 挂载等稳健细节；适用：把方块“变成”实体的投掷/挂载玩法。

## 8. 公开 API

无独立 `api` 包，也未提供注册表式扩展点（`DOLL_BLOCKS`/`DOLL_ITEMS`/`AUTHOR_DOLLS` 均为 mod 内部静态集合）。对外接入主要靠：Curios 饰品渲染（`compat/curios/CuriosCompat` + `DollItemRenderer`）、JEI/EMI/Jade 插件（`compat/{jei,emi,jade}`）、自定义模型目录（`config/kaleidoscope_doll/custom/{models,lang,textures}` + zip）、指令 `/kaleidoscope_doll reload`。若做多加载器拆分，本仓库未见 common/fabric 源集，属未确认。
