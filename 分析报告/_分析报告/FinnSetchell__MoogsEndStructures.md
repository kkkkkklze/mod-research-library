# FinnSetchell/MoogsEndStructures 源码分析报告

> 本仓库**没有任何 Java 代码**，是纯数据驱动的结构内容包（mod_id `mes`，MC 1.21），因此本报告按模板结构改写"核心系统/注册"两节为数据层的对应物。

## 1. 基本信息

- Mod 名：MoogsEndStructures（显示名 "Moog's End Structures"）；mod_id `mes`；mod_version 2.1.0；作者 FinnDog，credit "Built by Phantax"。
- 目标版本：`gradle.properties` 中 `minecraft_version=1.21`，`.github/moogs-publish.yml` 的 targets 说明同时服务 `1.20-datapack`(1.20–1.20.6) 与 `1.21-datapack`(1.21–26.2) 两分支；`pack.mcmeta` 写 `pack_format=48`、`supported_formats [48,107]`、`max_format 107.1`。
- Gradle：只有一个 `java` 插件（`build.gradle`），无 loader 插件、无 mixin、无 accesswidener；产物是"universal jar"（`archivesName = "${modName}-universal-${mcVersion}"`）+ 一个 `buildDatapack` Zip 任务（把 `data/**` 与 pack.mcmeta 打成交付给玩家的配置数据包，图标复用为 pack.png）。许可证 LGPL-3.0（`LICENSE`/mods.toml）。
- 依赖：`mods.toml`/`neoforge.mods.toml` 里 `modId="moogs_structures"` mandatory，`versionRange=${structure_lib_version_range}`（`[1.1.0,)`）；`fabric.mod.json` depends `moogs_structures` + `fabric-resource-loader-v0`（即 Fabric 端需要 MSL 当 loader 载体）。发布元数据（CurseForge/Modrinth id、Discord 配色、依赖）集中在 `.github/moogs-publish.yml`。

## 2. 规模与包结构

无 `.java`（`git ls-files '*.java' | wc -l` = 0）。按扩展名统计（`git ls-files` 全量）：**json 125、nbt 115、yml 12、py 8、md 7、toml 2**。工作区是 git sparse-checkout（只落 `*.java/*.gradle/*.toml/*.yml/*.md` 等），json/nbt 需用 `git show HEAD:<path>` 读取。

数据目录（`src/main/resources/`）：`data/mes/worldgen/structure/`（**25** 个结构 JSON）、`worldgen/structure_set/`（**25**）、`worldgen/template_pool/`（**60**，含 `mega_ship/`、`decoration/` 子目录）、`data/mes/structure/1_21_0/**.nbt` 与 `1_21_5/**.nbt`（共 115 个 NBT，按 MC 版本分文件夹）、`loot_table/`（9，含 `archaeology/end_sand.json`）、`tags/worldgen/biome/has_structure/end_biomes.json`、`moogs_structures/replace_vanilla.json`、`assets/mes/lang/en_us.json`、四份平台元数据 `fabric.mod.json`/`quilt.mod.json`/`mods.toml`/`neoforge.mods.toml`（全部用 `${...}` 占位，由 `processResources expand()` 展开）。

## 3. 入口与"注册"

没有 `@Mod`。入口是各 loader 的元数据文件：Forge `mods.toml` 用 **`modLoader = 'lowcodefml'`**（数据包型 mod 的免代码 loader），NeoForge/Fabric 走常规 `javafml` + `fabric.mod.json`；Fabric 端当纯数据包靠 `fabric-resource-loader-v0` 与 `moogs_structures` 加载。`fabric.mod.json` 里 `custom.modmenu.parent = "moogs_structures"` 把本包挂到 MSL 的设置分组下。

## 4. 核心系统（数据层）

- **结构定义**：25 个 `worldgen/structure/*.json` 全部 `"type": "moogs_structures:moogs_structures_generic_jigsaw_structure"`（MSL 提供），字段实例：`start_pool`、`size`(1~10)、`biomes`(`#mes:has_structure/end_biomes`)、`project_start_to_heightmap: WORLD_SURFACE_WG`、`terrain_height_radius_check`、`allowed_terrain_height_range`、`y_allowance:{min_y_allowed:45}`、`start_height`（`minecraft:uniform` 的 absolute 30~60）、`spawn_overrides`（如 mega_ship 里刷 shulker）。
- **放置规则**：25 个 `structure_set/*.json` 统一用 `"type": "moogs_structures:advanced_random_spread"` + `salt/spacing/separation`（例：enderbloom_grove `spacing 36 / separation 12`）+ `min_distance_from_world_origin`（`1000`，让结构只出现在外岛）。
- **多版本 NBT 复用**：60 个 template pool 的 **全部** element 都是 `"element_type": "moogs_structures:versioned_single_pool_element"`，用 `locations` 版本映射指向不同版本的 NBT，例如 `{"1.21-1.21.4": "mes:1_21_0/mega_ship/mega_ship_middle", "1.21.5-26.2": "mes:1_21_5/..."}`——**一份 jar 覆盖 1.21 到 26.2**，避免为每个 MC 版本重导结构。
- **生物群系标签兼容**：`end_biomes.json` 用 `replace:false` + 条件项 `{"id":"#c:is_end","required":false}`（外加 `#c:is_outer_end_island`），通过 `required:false` 兼容可能不存在的 common tag。
- **原版替换/配置钩子**：`data/mes/moogs_structures/replace_vanilla.json` 只写 `structures:{mod_name, mod_slug:"end-structures"}`，即利用 MSL 的自动发现（扫描本 mod 的 structure_set 生成配置界面行）只补充显示名与在线预览 slug。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无。配置：不写 Java，靠 MSL 的 `config/moogs_structures.json` 与 Cloth 界面暴露禁用/间距开关。
- datagen：无 Gradle datagen；取而代之是 **Python 工具链**（`scripts/`，8 个脚本，`_paths.py` 自动从 `gradle.properties` 读 mod_id 并兼容 1.20 的复数目录 `structure`/`loot_table`）：`structure_index.py`（遍历 template pool 生成 STRUCTURES.md 索引）、`update_template_pools.py`（发布新 MC 版本时批量往 pool 里注入 `locations` 版本项，脚本头部常量 `VERSION_FOLDER`/`VERSION_RANGE` 手改）、`nbt_check.py`（用 `nbtlib` 校验全部 NBT 可加载并对 >500KB 报 size 警告，损坏则非零退出）、`fix_loot.py`、`strip_bow_enchants.py`、`nbt_string_search.py`/`nbt_string_replacer.py`。
- CI（`.github/workflows/validate.yml`）：checkout 本仓库 + 外部校验器 `FinnSetchell/moogs-structure-validator@v1`，跑 `validator.py --config project/validator.json --project-root project` 再跑 `nbt_check.py`；发布用 `moogs-publish.yml` 清单驱动的 publish/release workflow。

## 6. Mixin

无（无 Java、无 mixin 配置）。

## 7. 值得学的 5 条做法

1. **数据包型 mod 不发代码**：用 Forge `lowcodefml` + `fabric-resource-loader-v0` 就能让纯 JSON/NBT 内容上架（`src/main/resources/META-INF/mods.toml:1`，场景：结构/配方/战利品扩展包）。
2. 元数据全用 `${...}` 占位 + `processResources expand(meta)` 统一注入，并在 `inputs.properties(meta)` 声明输入（`build.gradle:29-49`；注释记录了一个真实坑：不声明则改版本号后 jar 里仍是旧版本串）。
3. 用"版本映射 element（`versioned_single_pool_element` + `locations`）+ 按版本分 NBT 文件夹"实现单 jar 跨多 MC 版本（`worldgen/template_pool/mega_ship/side_pool.json`）。
4. 为"纯数据仓库"配 Python 维护脚本而不是手改：批量注入版本项、NBT 校验、索引生成，且 `_paths.py` 统一探测路径与单/复数目录（`scripts/*.py`）。
5. 把发布/仓库标识从构建脚本里抽到 `.github/moogs-publish.yml`（含 CF/Modrinth projectId、slug 修正注释、targets 的 MC 窗口），Gradle 只负责 `build`/`buildDatapack`（`build.gradle:9-11`）。

## 8. 公开 API / 接入方式

本包不提供 API，它是 MoogsStructureLib 的**内容消费者**：靠 `moogs_structures` 的结构类型 `moogs_structures:moogs_structures_generic_jigsaw_structure`、放置类型 `moogs_structures:advanced_random_spread`、池元素类型 `moogs_structures:versioned_single_pool_element`，以及数据包 `data/<ns>/moogs_structures/replace_vanilla.json` 的 `structures` 块接入。其自身对外契约只有数据包路径（`data/mes/worldgen/**`、`data/mes/loot_table/**`）与 `mes:has_structure/end_biomes` 标签。
