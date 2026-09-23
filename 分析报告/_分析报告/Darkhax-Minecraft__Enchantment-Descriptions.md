# Darkhax-Minecraft/Enchantment-Descriptions 源码分析报告

## 1. 基本信息
- Mod 名 EnchantmentDescriptions；mod_id `enchdesc`；作者 Darkhax；版本 20.1；许可 LGPL V2.1
- 目标 MC **1.20.4**，三加载器：Fabric（loader 0.15.3 / fabric-api 0.92.0）+ Forge 49.0.12 + NeoForge 20.4.60-beta；**纯客户端**（`fabric.mod.json` `environment: client`、mods.toml 依赖 `side = "CLIENT"`）
- Gradle：common 用 `org.spongepowered.gradle.vanilla 0.2.1`（不依赖加载器）；forge 用 ForgeGradle `[6.0,6.2)` + Sponge mixin 0.7 插件；neoforge 用 `net.neoforged.gradle.userdev 7.0.43`；fabric 用 fabric-loom 1.6；根 `build.gradle` 叠加 curseforgegradle 1.1.17、minotaur、idea-ext，并 apply `gradle/` 下 build_number、git_changelog、version_checker、minify_jsons、signing、patreon、property_loader 一整套发布脚本
- 编译依赖：唯一 API 是 **Bookshelf**（`net.darkhax.bookshelf:Bookshelf-{Common,Forge,NeoForge,Fabric}-1.20.4:23.0.1`），common 里为 compileOnly（`common/build.gradle:20`），mods.toml 声明 required

## 2. 规模与包结构
7 个 `.java`，共 **234** 行；包只有 `net.darkhax.enchdesc`（common 4 个类 + 每平台 1 个入口类）。行数：`EnchDescCommon.java` 73、`ConfigSchema.java` 69、`DescriptionManager.java` 29、`Constants.java` 10、三个入口 12~21。资源：`common/src/main/resources/assets/enchdesc/lang/` 下 **25 个语言文件**、`textures/logo.png`、`pack.mcmeta`。

## 3. 入口与注册
无任何注册体系（没有 DeferredRegister、没有注册表项）。三个入口都只做同一件事——`new EnchDescCommon(configDir)`：
- Fabric：`EnchDescFabric implements ClientModInitializer`，用 `FabricLoader.getInstance().getConfigDir()`（`fabric/src/main/java/net/darkhax/enchdesc/EnchDescFabric.java:9-12`）
- Forge：`@Mod` 构造器里注册 `IExtensionPoint.DisplayTest(IGNORESERVERONLY)`，再 `if (Environment.get().getDist().isClient()) new EnchDescCommon(FMLPaths.CONFIGDIR.get())`（`forge/.../EnchDescForge.java:12-20`）
- NeoForge：同上，`IGNORESERVERONLY` 改从 `NetworkConstants` 取（`neoforge/.../EnchDescNeoForge.java:13-21`）
`EnchDescCommon` 构造器是全部业务装配点：`ConfigSchema.load(...)` + `Services.EVENTS.addItemTooltipListener(this::onItemTooltip)`（`common/.../EnchDescCommon.java:25-29`）。

## 4. 核心系统
1. **tooltip 注入路径**：不写 mixin，改用 Bookshelf 事件 API `Services.EVENTS.addItemTooltipListener` 挂监听（EnchDescCommon.java:28）——这是"客户端显示类功能优先用事件而非 mixin"的范例。
2. **过滤链**（EnchDescCommon.java:31-73）：`enableMod` → stack 非空且 `hasTag()` →（`!onlyDisplayOnBooks && stack.isEnchanted()`）或 `Instanceof EnchantedBookItem` → `!onlyDisplayInEnchantingTable || Minecraft.getInstance().screen instanceof EnchantmentScreen` → `!requireKeybindPress || Screen.hasShiftDown()`；未按 Shift 时追加 `Component.translatable("enchdesc.activate.message").withStyle(DARK_GRAY)`。
3. **插入位置算法**：遍历已有 tooltip 行，匹配 `line.getContents() instanceof TranslatableContents` 且 key 等于 `enchantment.getDescriptionId()` 的那一行，然后 `tooltip.add(tooltip.indexOf(line) + 1, descriptionText)`（EnchDescCommon.java:47-59）——描述紧跟附魔名行，天然兼容其他 mod 的 tooltip 排版；`indentSize > 0` 时用 `StringUtils.repeat(' ', indentSize)` 前缀缩进。
4. **描述解析 + 缓存**：`DescriptionManager` 用 `static ConcurrentHashMap<Enchantment, MutableComponent>` + `computeIfAbsent`；主 key 为 `descriptionId + ".desc"`，`I18n.exists` 失败时回退 `+ ".description"`，统一 `DARK_GRAY`（`DescriptionManager.java:14-28`）。
5. **语言文件组织**（25 个：bg_bg、de_de、en_ca、en_us、es_ar、es_cl、es_es、es_mx、fil_ph、fr_fr、it_it、ja_jp、ko_kr、nl_be、nl_nl、pl_pl、pt_br、ru_ru、sv_se、ta_in、tr_tr、uk_ua、vi_vn、zh_cn、zh_tw）：结构为 `_comment` 首行 → 原版 `enchantment.minecraft.*.desc` 段 → `enchdesc.activate.message` → 各第三方 mod 分区，分区用伪 key `__support_<modid>`（值为项目链接，语言无关）作分隔，键名规则 `enchantment.<modid>.<enchid>.desc`（`en_us.json` 7.6KB、`es_es.json` 14.8KB、`ru_ru.json` 10.3KB）。
6. **构建期 JSON 压缩**：`gradle/minify_jsons.gradle:22-47` 在 `processResources.doLast` 用 JsonSlurper/JsonOutput 重写 `**/*.json` 与 `*.mcmeta`，源码保持可读、只压产物。

## 5. 网络 / 数据驱动 / 配置 / datagen
无网络、无 datagen。配置 `ConfigSchema`：Gson（`setPrettyPrinting` + `excludeFieldsWithoutExposeAnnotation`），5 个 `@Expose` 字段 `enableMod`、`onlyDisplayOnBooks`、`onlyDisplayInEnchantingTable`、`requireKeybindPress`、`indentSize`；读写 `config/enchdesc.json`，读取失败回退默认值并始终重写文件（`ConfigSchema.java:30-69`）——不依赖任何配置库的最小实现。

## 6. Mixin
无。仓库内不存在任何 `*.mixins.json`；`build.gradle:45` 保留 `project.ext.mixin_enabled = project.file("src/main/resources/${mod_id}.mixins.json").exists()` 的开关与 forge 侧 Sponge mixin 0.7 插件、refmap 配置，但当前未启用（探测结果为 false，构建日志会打印 "Mixin disabled"）。

## 7. 值得学的 5 条
1. 所有展示内容都做成 lang key（`enchantment.<modid>.<enchid>.desc`），零注册零网络即让任意第三方 mod 自带支持（`DescriptionManager.java:20-27`、README）。
2. tooltip 用"找到已有附魔名行再 insert 到它后面"而非 append 到末尾，最大化兼容其他 tooltip mod：`EnchDescCommon.java:47-58`。
3. 静态 `ConcurrentHashMap` + `computeIfAbsent` 缓存 `Enchantment → Component`：`DescriptionManager.java:14-18`。
4. 客户端功能优先用依赖库的事件总线（Bookshelf `Services.EVENTS`）代替 mixin，平台差异压到每个入口 2~20 行。
5. `processResources.doLast` 对所有 json/mcmeta 做产物期 minify，兼顾源码可读性与 jar 体积：`gradle/minify_jsons.gradle:22-47`。

## 8. 第三方接入方式
本 mod 不提供代码级 API：mod 作者只需在自己语言文件加 `enchantment.<modid>.<enchid>.desc`（或 `.description`）即可生效；其依赖的 `net.darkhax.bookshelf.api.Services` 才是 Darkhax 系列模组的公共 API 面。
