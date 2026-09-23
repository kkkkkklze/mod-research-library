# klinbee/Aetherial-Islands（以太岛）源码分析

## 1. 基本信息

- 名称：Aetherial Islands；作者 klinbee；**纯数据包（worldgen datapack）**，不是 Java mod
- 目标版本：`pack_format: 15`（1.20.1 起），`min_format: 15`、`max_format: 999`、`supported_formats: [15, 999]`（`Aetherial_Islands/pack.mcmeta`）
- 版本适配：用 `overlays.entries` 按 pack_format 挂载四套覆盖层 —— `overlay_1_20_5`(41+)、`overlay_1_21_4`(61+)、`overlay_1_21_5`(71+)、`overlay_1_21_9`(88+)
- Gradle / 编译依赖：**无**（无 `build.gradle`、无 `.java`）。唯一外部依赖是可选的 **Lithostitched**（README 说明：只影响水体生成；`lithostitched:add_surface_rule` / `replace_climate` / `replace_effects` 三个自定义类型需它才能解析）
- 许可证：仓库含 `Aetherial_Islands/LICENSE.txt`、`Aetherial_Islands_Clusters_Edit/LICENSE.txt`（未读全文）

## 2. 规模与目录结构

- 受版本控制文件 217 个（`git ls-files | wc -l`），`.java` 文件 **0 个**；本地工作区为 sparse checkout，只检出 README/LICENSE，资源须用 `git show HEAD:<path>` 读取
- `Aetherial_Islands/data/minecraft/` 98 个文件：`worldgen/noise_settings/overworld.json`（整体替换原版）、12 个 `structure_set/`、约 70 个 `placed_feature/`、3 个 `configured_carver/`、2 个 `configured_feature/`、1 个 `noise/`
- `Aetherial_Islands/data/aetherial_islands/` 55 个文件：`worldgen/density_function/` 48 个（按 `islands/layer1..layer5`、`continents/`、`ridges/`、`terrain/`、`oceanic/` 分目录）、`worldgen/noise/` 3 个、`lithostitched/worldgen_modifier/` 4 个
- `Aetherial_Islands/overlay_*/` 共 4 套 15 个文件；`Aetherial_Islands_Clusters_Edit/` 是变体包，把同一套密度函数树复制到 4 个命名空间（`aetherial_islands`、`skylands`、`skylands_over_the_sea`、`angel_islands`）+ `skylands_reducer`
- 最大文件：`islands/final.json`（约 100 行嵌套 range_choice）、`islands/layer1/offset_top.json`（约 90 行 spline）、`ridges/levels.json`、`lithostitched/worldgen_modifier/aquatic_surface_rules.json`、`data/minecraft/worldgen/noise_settings/overworld.json`

## 3. 入口与注册

数据包无代码入口；"入口"= `Aetherial_Islands/pack.mcmeta`（pack 定义 + overlays）与 `data/minecraft/worldgen/noise_settings/overworld.json`（**直接覆盖原版主世界 noise_settings**，这是它接管地形的唯一挂钩点）。该文件把原版 NoiseRouter 字段全部改指到自己的密度函数：

```json
"noise_router": {
  "temperature": "aetherial_islands:temperature",
  "vegetation": "aetherial_islands:vegetation",
  "continents": "aetherial_islands:continents/3d",
  "erosion": "aetherial_islands:erosion",
  "depth": "aetherial_islands:depth",
  "ridges": "aetherial_islands:ridges/final",
  "initial_density_without_jaggedness": 1,
  "final_density": "aetherial_islands:terrain/final",
  ... "barrier"/"fluid_level_*"/"lava"/"vein_*" 全为 0
}
```

同时 `noise: {min_y: -48, height: 368}`、`ore_veins_enabled: false`、aquifers 保留 true、`surface_rule` 为内联序列。1.21.9 覆盖层把 `initial_density_without_jaggedness` 换成 `preliminary_surface_level: 2048`。

## 4. 核心系统

**A. 五层 3D 浮岛叠加**（`data/aetherial_islands/worldgen/density_function/islands/`）。每层结构固定：`layerN/noise.json` = `cache_once(flat_cache(add(-0.425, shifted_noise(aetherial_islands:islands, xz_scale 0.85, y_scale 0)))`；`offset_top.json` = 以 `ridges/noise` 为坐标、`layerN/noise` 为值的二维 spline（纯 2D，所以岛"成片"）；`depth_top.json` = `add(y_clamped_gradient(-1→64, 0→-1), offset_top)`。`islands/final.json` 用嵌套 `range_choice` 按自定义 `y` 函数（`y_clamped_gradient(-1024→1024)` 再夹紧，使 `y` 可直接参与区间比较）分 y 带取**相邻两层的 `max`**，从而层间平滑过渡、不出现硬切。

**B. 有河流的山脊**（`ridges/final.json` + `ridges/levels.json` + `ridges/no_rivers.json`）。`continents/noise` 与 `ridges/levels` 两级 `range_choice` 决定输出 `ridges/noise`（带河）还是 `no_rivers`；`ridges/levels` 是一条以 y 为坐标的 spline，每 16~48 格 y 段切换成对应层的 `islands/layerN/noise` 并夹到 0/1 —— 这样"岛层"同时充当山脊层，浮岛上就有连绵山与原版式河流。`levels.json` 内层 spline 用 0.125 处的重复点做阶梯。

**C. 海洋与洞穴分流**（`terrain/final.json`）。三级决策：先看 `continents/oceanic_terrain_limiter`（y 在 -64..80 内用 `continents/no_mushroom` 否则 `continents/base`）决定区域是海洋地形（`islands/oceanic/final`：y 0..64 的斜带 + `oceanic/offset`）还是陆地；而山脊值落在 [-0.15,0.15) 时走 `terrain/no_caves`，否则用 `spline(coordinate: minecraft:y)` 在 `terrain/with_caves`（含 `terrain/custom_caves` + `terrain/pre_caves`）与 `no_caves` 之间过渡 —— 洞穴只在 y≈80~96 段开放，实现"浮岛底下的洞/平台"。

**D. Lithostitched 数据层补丁**（`data/aetherial_islands/lithostitched/worldgen_modifier/`）。`aquatic_surface_rules.json`（type `lithostitched:add_surface_rule`，`levels: ["minecraft:overworld"]`）在原版 surface rule 之外追加规则：仅当 `y_above 64` 为假且 biome 是 6 种 ocean 时才铺草/土（阈值 `noise_threshold(aetherial_islands:continentalness, -0.825, -0.82)`），解决浮岛海洋没有水底地面的问题；`cold_biome_climate_adjustment.json`（`replace_climate`）统一调 4 个寒冷群系温湿度；`stony_shore_color_adjustment.json` / `taiga_biome_color_adjustment.json`（`replace_effects`）改草/叶色。

**E. 原版数据覆盖**（`data/minecraft/`）。12 个 `structure_set`（villages、ocean_monuments、woodland_mansions、desert_pyramids、igloos、jungle_temples、ocean_ruins、pillager_outposts、ruined_portals、shipwrecks、trail_ruins、buried_treasures）改 spacing/separation/salt 与 `spread_type: "triangular"`，让建筑落在岛上而非虚空；`configured_carver/cave.json`（`overlay_1_20_5` 版）把 `probability` 设为 0、`y` 压到 `absolute: -128`，把洞穴权收归自己的密度函数；`configured_feature/disk_sand|disk_gravel` 改为按下方是 air/water 换沙岩；约 70 个 `placed_feature` 覆盖植被分布。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络、配置、datagen、Java 代码：**均无**
- 全部是数据驱动：48 个 density_function、3 个 noise（`islands.json` = `firstOctave -8, amplitudes [1,1,2,0,-2,1,0]`）、4 个 lithostitched modifier、内联 surface_rule、overlay 分层适配

## 6. Mixin

无（数据包）。

## 7. 值得学的 5 条具体做法

1. **自定义 `y` 密度函数参与区间判断** —— `density_function/y.json`（`y_clamped_gradient -1024..1024` 套 `cache_once`）；JSON 里无法直接对世界 y 做比较，先把 y 变成密度函数再喂给 `range_choice`。
2. **分层 noise + 相邻层 `max` 融合** —— `islands/final.json:1`；要"多层悬浮地形"时避免层间接缝硬切的标准写法。
3. **用 spline 的 `coordinate` 反查另一条曲线** —— `islands/layer1/offset_top.json`（coordinate=ridges/noise，value=layer noise）；一个二维噪声同时决定"在哪"和"多高"。
4. **`overlays.entries` 做单包多版本** —— `pack.mcmeta`；跨 1.20.1~1.21.9 只需给变化的 JSON 建 overlay，主数据不复制（对比 Cataclysm-Dimension 用代码挂多套内置包）。
5. **把"补充原版规则"外包给 Lithostitched 的数据类型** —— `lithostitched/worldgen_modifier/aquatic_surface_rules.json`；想在别人的 surface rule 上追加而不整体接管时，用 `add_surface_rule` / `replace_climate` / `replace_effects` 三个 type。

## 8. 库/API 类 mod

非库包。可作为"世界生成数据包工程化"的参考样板；接入方式：作为 datapack（或 mod jar 的 data 目录）放入世界，可选装 Lithostitched 以启用 4 个 modifier 文件（缺它时会因未知 type 报数据包加载错）。
