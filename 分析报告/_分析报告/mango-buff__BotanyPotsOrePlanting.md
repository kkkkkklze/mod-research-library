# mango-buff/BotanyPotsOrePlanting 源码分析报告

## 0. 本地副本状况（重要）

本地路径 `_参考仓库/_bulk/mango-buff__BotanyPotsOrePlanting` 为**稀疏检出**（`.git/info/sparse-checkout` 只保留 `**/*.java`、`**/*.gradle`、`**/*.toml`、`**/*.md` 等），且只检出 `main` 分支；`main` 上仅有 `README.md` 与 `ModOreSupportList.md` 两个文件（共 38 个文件含 .git），README 原文："This is the main branch. Please switch to the corresponding branch for the version source code."

因此本报告基于**远端版本分支 `1.21.1`**（`git ls-remote --heads origin` 显示分支：main、Forge-1.16.5、1.18.2、1.18.2-1.20.4、1.19.2、1.20、1.20.1、1.21.1；通过 GitHub API/raw 拉取，`curl -k` 绕本机 CA 问题）。下列文件路径均为该分支内路径。

## 1. 基本信息

- Mod 名：Botany Pots Ore Planting；mod_id `botany_pots_ore_planting`；作者 mango_buff；许可证 MIT（`neoforge/src/main/resources/META-INF/neoforge.mods.toml` license="MIT License"）
- 目标版本（1.21.1 分支 `gradle.properties`）：`mc_version=1.21.1`、`neoforge_version=21.1.197`、`neoforge_mod_version=14.35.1`、`fabric_mod_version=14.14.0`、`yarn_mappings=1.21.1+build.3`、`loader_version=0.16.2`、`fabric_api_version=0.102.1+1.21.1`
- 多加载器工程：`settings.gradle` include `common`/`fabric`/`neoforge`；neoforge 用 `net.neoforged.moddev 2.0.106`，fabric 用 `fabric-loom 1.7-SNAPSHOT`（各平台 `build.gradle` 的 `archivesBaseName` 相同，version 前缀 `NeoForge-`/`Fabric-`）
- 编译依赖：只有两个上游前置 —— `botanypots [21,)`（fabric 端 `botanypots >=21.0.0`）与 `bookshelf [21,)`，均 required（mods.toml / fabric.mod.json）。无 API 分模块、无 mixin、无 bytecode 依赖

## 2. 源码规模与包结构

Java 代码 **仅 2 个类**，且都是空壳：
- `neoforge/src/main/java/com/mango_buff/botany_pots_ore_planting/BotanyPotsOrePlanting.java`（6 行，`@Mod` + `MODID` 常量）
- `fabric/src/main/java/com/mango_buff/botany_pots_ore_planting/BotanyPotsOrePlanting.java`（`ModInitializer.onInitialize()` 空实现）

`common` 模块**没有任何 java**，只有 `common/src/main/resources/logo.png` 与 `pack.mcmeta`（pack_format 48）。全部功能是数据包 JSON（1.21.1 分支路径总数 916）：
- `neoforge/src/main/resources/data/botany_pots_ore_planting/` 共 539 文件：`recipe/crops` 176、`recipe/soil` 177、`tags/item/soil` 114
- `fabric/src/main/resources/data/botany_pots_ore_planting/` 共 338 文件：crops 108、soil 108、tags 85
- crop 覆盖 36 个命名空间目录：minecraft、gtceu、create、ae2、mekanism、mekanism_extras、thermal、immersiveengineering、mysticalagriculture、mythicbotany、tconstruct、techreborn、nuclearcraft、oritech、powah、silentgear、modern_industrialization、ad_astra、evilcraft、draconicevolution、iceandfire、forbidden_arcanus、industrialupgrade、alltheores、allthemodium、aether、pixelmon、epicsamurai、gobber2、enderitemod、superbwarfare、createnuclear、mtetm、mythicmetals 等
- `ModOreSupportList.md`（main 分支 131 行）用 Markdown 手工列举各 MC 版本已支持模组

两个平台各维护一份 data 副本（非共享到 common），维护成本较高。

## 3. 入口与注册

无任何 Java 注册内容（无 DeferredRegister、无 registry、无事件监听）。`neoforge/build.gradle` 里 `sourceSets.main.resources.srcDir project(':common').sourceSets.main.resources.srcDirs`，即只借用 common 的 logo/pack.mcmeta，data 数据仍各平台一份。datagen run 已配置（`--mod botany_pots_ore_planting --all --output src/generated/resources/`）但源码里没有 provider，JSON 为手写。

## 4. 核心系统（3 个数据驱动子系统）

1) crop 配方（如 `neoforge/.../recipe/crops/minecraft/iron_ore.json`）：`{"type":"botanypots:crop","input":{"item":"minecraft:iron_ingot"},"soil":{"tag":"botany_pots_ore_planting:soil/iron"},"grow_time":1200,"display":{"type":"botanypots:simple","block_state":{"block":"minecraft:iron_ore"}},"drops":[{"type":"botanypots:items","items":[{"result":{"id":"minecraft:raw_iron"},"chance":1.0}]}],"yield":2.5,"yield_scale":1.0}`。关键设计：**用矿物产物（铁锭）当"种子"**，`soil` 引用自定义 tag，`display.block_state` 直接复用原版矿石方块外观，掉落原矿。
2) soil 配方（如 `recipe/soil/gtceu/salt_block.json`）：`{"bookshelf:load_conditions":[{"type":"bookshelf:item_exists","values":["gtceu:salt_block"]}],"type":"botanypots:soil","input":{"item":"gtceu:salt_block"},"display":{...},"growth_modifier":0.0}`。用 Bookshelf 的 `bookshelf:item_exists` 加载条件让未安装 mod 的方块配方整体消失；`growth_modifier: 0.0` 表示矿土不加速生长。
3) item tag 归一化（如 `tags/item/soil/tin.json`）：`"values":[{"id":"gtceu:tin_block","required":false},{"id":"nuclearcraft:tin_block","required":false}, ...]`，把各 mod 的同种金属块聚成一个 tag，crop 只引用 `botany_pots_ore_planting:soil/<material>`，从而 1 个 crop 适配多 mod 的矿土。

## 5. 网络 / 数据驱动 / 配置 / datagen

无网络、无 config、无 mixin（1.21.1 分支无 mixins.json 及任何 mixin 相关文件）、无 mixin 配置。数据驱动即全部内容（recipe type 由 Botany Pots 提供、load condition 由 Bookshelf 提供）。datagen 目录未生成（`src/generated/resources` 未出现在分支树中）。

## 6. 值得学的 5 条做法

1. "零 Java mod"范本：只发数据包 + 依赖上游的 recipe type / load condition 即可成完整玩法（`neoforge/.../recipe/crops/minecraft/iron_ore.json`），适合做兼容/联动类小 mod。
2. 用 `{"id": "...", "required": false}` 写 tag 值，缺 mod 时静默跳过，比逐个 mod 出分支版本省事（`tags/item/soil/*.json`）。
3. 用 `bookshelf:load_conditions` + `item_exists` 按需关闭配方，替代 Java 侧条件判断（`recipe/soil/gtceu/salt_block.json`）。
4. 显示壳与产出分离：`display.block_state` 用原矿石方块，`drops` 用原矿物品 —— 把"长得像矿"和"产出什么"解耦。
5. 手写 JSON 时用"材料名 tag + 每 mod 一个 soil 配方"的两层结构，新增 mod 只需加 tag 值与少量 soil 文件（但注意 data 在 fabric/neoforge 各一份，可改为 common 共享）。

## 7. 对外 API

无。本 mod 是 Botany Pots + Bookshelf 数据驱动扩展的消费者，接入点是 `botanypots:crop` / `botanypots:soil` recipe type 与 `bookshelf:load_conditions`。其他分支抽查（GitHub tree API）：`1.20.1` 为 `common`+`fabric`+`forge` 三模块、2 个 java 类 + 598 个 json（同样数据驱动）；`Forge-1.16.5` 为单模块、1 个 java 类 + 176 个 json。各分支 Java 类内容未逐一打开（未确认其内部是否仍为空壳）。
