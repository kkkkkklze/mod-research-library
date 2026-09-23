# 知名 Mod 源码分析库 — 总索引

本目录是「四个整合包的 mod 源码」分析成果，供学习 mod 工程化开发使用。

## 概览

- 覆盖整合包: 璇穹之歌(1.21.1 NeoForge)、暗涌：深岩恐惧(1.20.1 Forge)、星轨重铸：残响(1.21.1 NeoForge，航空学)、All the Mods 10(1.21.1 NeoForge)
- 唯一 GitHub 仓库: **591** 个（全部经 git ls-remote 验证 + 稀疏克隆到本地）
- **深度分析报告（子 agent 逐仓库阅读源码后撰写，含文件路径级引用）: 353 份**（其中 **332 份**与速览卡片一一对应，其余 21 份为专题/横向/设计/版本差异类）→ `_分析报告/<owner>__<repo>.md`（本文件所在目录）
- **速览卡片（脚本自动提取：文件数/行数/包结构/构建方式/主类/许可证）: 580 份** → `_分析报告/_卡片/<owner>__<repo>.md`
- 本地源码: `_参考仓库/`（15 个重点仓库）+ `_参考仓库/_bulk/`（其余全部，稀疏检出只含源码）
- **扩展覆盖（2026-09-20）**: TeaCon 2026（164 个 mod 全量反编译，394 万行）→ `_参考仓库/_teacon_decompiled/`；四包无源 mod 补漏（205 个，278 万行）→ `_参考仓库/_pack_decompiled/`；其余 15 个整合包（4478 个 jar）的 mod 清单 → `对照表/Mod清单__<包>.md`
- **下一步开挖**: [`深挖待办清单.md`](../../深挖待办清单.md)（18 条，每条含理由/起点/目标问题/体量）

> 说明：深度报告是 agent 逐个仓库读源码写出的（重点覆盖高频使用/教学价值高的 mod）；速览卡片覆盖全部仓库，给出可检索的结构数据。两者都以 `owner__repo` 命名，一一对应。

## 使用方式

1. 想系统学某个主题 → 看下文分类表，挑 `有深度报告` 的仓库报告阅读，报告内每条结论都带 `文件:行号`，可直接打开本地源码对照。
2. 想快速了解某个 mod 的规模/结构 → 打开对应速览卡片。
3. 想自己跑一遍：脚本已迁入库内 `../../研究脚本/`（`_make_cards.py` 卡片生成、`_pack_research.py` 包→仓库解析、`_bulk_clone.py` 批量稀疏克隆、`_downloader.py` 多镜像下载器、`_jar_diff.py` 类级 CRC 比对、`_missing_reports.py` 报告缺口盘点）。

## 性能优化 / 引擎底层（30）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [CaffeineMC/sodium](https://github.com/CaffeineMC/sodium) | Sodium | 3包 | [报告](./CaffeineMC__sodium.md) | [卡片](./_卡片/CaffeineMC__sodium.md) |
| [tr7zw/EntityCulling](https://github.com/tr7zw/EntityCulling) | Entity Culling | 1包 | [报告](./tr7zw__EntityCulling.md) | [卡片](./_卡片/tr7zw__EntityCulling.md) |
| [malte0811/FerriteCore](https://github.com/malte0811/FerriteCore) | FerriteCore | 3包 | [报告](./malte0811__FerriteCore.md) | [卡片](./_卡片/malte0811__FerriteCore.md) |
| [caffeinemc/lithium-fabric](https://github.com/caffeinemc/lithium-fabric) | Lithium | 2包 | [报告](./caffeinemc__lithium-fabric.md) | [卡片](./_卡片/caffeinemc__lithium-fabric.md) |
| [FlashyReese/sodium-extra-fabric](https://github.com/FlashyReese/sodium-extra-fabric) | Sodium Extra | 2包 | [报告](./FlashyReese__sodium-extra-fabric.md) | [卡片](./_卡片/FlashyReese__sodium-extra-fabric.md) |
| [embeddedt/ModernFix](https://github.com/embeddedt/ModernFix) | ModernFix | 4包 | [报告](./embeddedt__ModernFix.md) | [卡片](./_卡片/embeddedt__ModernFix.md) |
| [juliand665/Dynamic-FPS](https://github.com/juliand665/Dynamic-FPS) | Dynamic FPS | 1包 | [报告](./juliand665__Dynamic-FPS.md) | [卡片](./_卡片/juliand665__Dynamic-FPS.md) |
| [fxmorin/memoryLeakFix](https://github.com/fxmorin/memoryLeakFix) | Memory Leak Fix | 1包 | [报告](./fxmorin__memoryLeakFix.md) | [卡片](./_卡片/fxmorin__memoryLeakFix.md) |
| [Asek3/Oculus](https://github.com/Asek3/Oculus) | mekalus-mc1.20.1-1.8.0.1.jar | 1包 | [报告](./Asek3__Oculus.md) | [卡片](./_卡片/Asek3__Oculus.md) |
| [FiniteReality/embeddium](https://github.com/FiniteReality/embeddium) | Embeddium | 1包 | [报告](./FiniteReality__embeddium.md) | [卡片](./_卡片/FiniteReality__embeddium.md) |
| [Ezzenix/ChatAnimation](https://github.com/Ezzenix/ChatAnimation) | Chat Animation [Smooth Chat] | 1包 | [报告](./Ezzenix__ChatAnimation.md) | [卡片](./_卡片/Ezzenix__ChatAnimation.md) |
| [txnimc/SodiumDynamicLights](https://github.com/txnimc/SodiumDynamicLights) | Sodium Dynamic Lights | 2包 | [报告](./txnimc__SodiumDynamicLights.md) | [卡片](./_卡片/txnimc__SodiumDynamicLights.md) |
| [pop4959/Chunky](https://github.com/pop4959/Chunky) | Chunky | 1包 | [报告](./pop4959__Chunky.md) | [卡片](./_卡片/pop4959__Chunky.md) |
| [Schauweg/Smooth-Swapping](https://github.com/Schauweg/Smooth-Swapping) | Smooth Swapping | 1包 | [报告](./Schauweg__Smooth-Swapping.md) | [卡片](./_卡片/Schauweg__Smooth-Swapping.md) |
| [ITsMrToad/GpuTape](https://github.com/ITsMrToad/GpuTape) | GPUBooster | 1包 | [报告](./ITsMrToad__GpuTape.md) | [卡片](./_卡片/ITsMrToad__GpuTape.md) |
| [MoePus/Flerovium](https://github.com/MoePus/Flerovium) | Flerovium | 2包 | [报告](./MoePus__Flerovium.md) | [卡片](./_卡片/MoePus__Flerovium.md) |
| [kltyton/LightSpeedRe](https://github.com/kltyton/LightSpeedRe) | LightSpeedRe | 2包 | [报告](./kltyton__LightSpeedRe.md) | [卡片](./_卡片/kltyton__LightSpeedRe.md) |
| [ObscuriaLithium/Fragmentum](https://github.com/ObscuriaLithium/Fragmentum) | Fragmentum | 1包 | [报告](./ObscuriaLithium__Fragmentum.md) | [卡片](./_卡片/ObscuriaLithium__Fragmentum.md) |
| [ObscuriaLithium/obscure-tooltips](https://github.com/ObscuriaLithium/obscure-tooltips) | Obscure Tooltips | 1包 | [报告](./ObscuriaLithium__obscure-tooltips.md) | [卡片](./_卡片/ObscuriaLithium__obscure-tooltips.md) |
| [TelepathicGrunt/StructureLayoutOptimizer](https://github.com/TelepathicGrunt/StructureLayoutOptimizer) | Structure Layout Optimizer | 1包 | [报告](./TelepathicGrunt__StructureLayoutOptimizer.md) | [卡片](./_卡片/TelepathicGrunt__StructureLayoutOptimizer.md) |
| [RelativityMC/C2ME-neoforge](https://github.com/RelativityMC/C2ME-neoforge) | Concurrent Chunk Management Engine (NeoF | 1包 | — | [卡片](./_卡片/RelativityMC__C2ME-neoforge.md) |
| [RaphiMC/ImmediatelyFast](https://github.com/RaphiMC/ImmediatelyFast) | ImmediatelyFast | 2包 | — | [卡片](./_卡片/RaphiMC__ImmediatelyFast.md) |
| [404Setup/KryptonReno](https://github.com/404Setup/KryptonReno) | Krypton Reno | 1包 | — | [卡片](./_卡片/404Setup__KryptonReno.md) |
| [Olafski/FastLeafDecay](https://github.com/Olafski/FastLeafDecay) | a/[树叶快速腐烂] fastleafdecay-35.jar | 2包 | — | [卡片](./_卡片/Olafski__FastLeafDecay.md) |
| [someaddons/gpumemleakfix](https://github.com/someaddons/gpumemleakfix) | a/[修复GPU内存泄漏] gpumemleakfix-1.21-1.8.jar | 2包 | — | [卡片](./_卡片/someaddons__gpumemleakfix.md) |
| [pietro-lopes/AllTheLeaks](https://github.com/pietro-lopes/AllTheLeaks) | 内存泄漏alltheleaks-1.1.12+1.21.1-neoforge.j | 2包 | — | [卡片](./_卡片/pietro-lopes__AllTheLeaks.md) |
| [Shadows-of-Fire/FastFurnace](https://github.com/Shadows-of-Fire/FastFurnace) | a/[熔炉性能优化] FastFurnace-1.21.1-9.0.1.jar | 2包 | — | [卡片](./_卡片/Shadows-of-Fire__FastFurnace.md) |
| [Argon4W/AcceleratedRendering](https://github.com/Argon4W/AcceleratedRendering) | [加速渲染] acceleratedrendering-1.0.14-1.20. | 2包 | — | [卡片](./_卡片/Argon4W__AcceleratedRendering.md) |
| [Shadows-of-Fire/FastWorkbench](https://github.com/Shadows-of-Fire/FastWorkbench) | a/[工作台性能优化] FastWorkbench-1.21.1-9.1.3.j | 1包 | — | [卡片](./_卡片/Shadows-of-Fire__FastWorkbench.md) |
| [someaddons/smoothchunksave](https://github.com/someaddons/smoothchunksave) | a/[平滑区块保存] smoothchunk-1.21-4.1.jar | 1包 | — | [卡片](./_卡片/someaddons__smoothchunksave.md) |

## 库 / 前置 / API（69）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [shedaniel/ClothConfig](https://github.com/shedaniel/ClothConfig) | Cloth Config API (Fabric/Forge/NeoForge) | 4包 | [报告](./shedaniel__ClothConfig.md) | [卡片](./_卡片/shedaniel__ClothConfig.md) |
| [isXander/YetAnotherConfigLib](https://github.com/isXander/YetAnotherConfigLib) | YetAnotherConfigLib (YACL) | 2包 | [报告](./isXander__YetAnotherConfigLib.md) | [卡片](./_卡片/isXander__YetAnotherConfigLib.md) |
| [architectury/architectury](https://github.com/architectury/architectury) | Architectury API | 4包 | [报告](./architectury__architectury.md) | [卡片](./_卡片/architectury__architectury.md) |
| [bernie-g/geckolib](https://github.com/bernie-g/geckolib) | geckolib-forge-1.20.1-4.8.4.jar | 4包 | [报告](./bernie-g__geckolib.md) | [卡片](./_卡片/bernie-g__geckolib.md) |
| [Serilum/Collective](https://github.com/Serilum/Collective) | Collective | 2包 | [报告](./Serilum__Collective.md) | [卡片](./_卡片/Serilum__Collective.md) |
| [Fuzss/puzzleslib](https://github.com/Fuzss/puzzleslib) | Puzzles Lib | 2包 | [报告](./Fuzss__puzzleslib.md) | [卡片](./_卡片/Fuzss__puzzleslib.md) |
| [Keksuccino/Konkrete](https://github.com/Keksuccino/Konkrete) | Konkrete | 4包 | [报告](./Keksuccino__Konkrete.md) | [卡片](./_卡片/Keksuccino__Konkrete.md) |
| [TwelveIterations/Balm](https://github.com/TwelveIterations/Balm) | Balm | 3包 | [报告](./TwelveIterations__Balm.md) | [卡片](./_卡片/TwelveIterations__Balm.md) |
| [CreativeMD/CreativeCore](https://github.com/CreativeMD/CreativeCore) | CreativeCore | 2包 | [报告](./CreativeMD__CreativeCore.md) | [卡片](./_卡片/CreativeMD__CreativeCore.md) |
| [thedarkcolour/KotlinForForge](https://github.com/thedarkcolour/KotlinForForge) | kotlinforforge-5.12.0-all.jar | 4包 | [报告](./thedarkcolour__KotlinForForge.md) | [卡片](./_卡片/thedarkcolour__KotlinForForge.md) |
| [Keksuccino/Melody](https://github.com/Keksuccino/Melody) | Melody | 3包 | [报告](./Keksuccino__Melody.md) | [卡片](./_卡片/Keksuccino__Melody.md) |
| [glisco03/owo-lib](https://github.com/glisco03/owo-lib) | oωo (owo-lib) | 3包 | [报告](./glisco03__owo-lib.md) | [卡片](./_卡片/glisco03__owo-lib.md) |
| [Darkhax-Minecraft/Bookshelf](https://github.com/Darkhax-Minecraft/Bookshelf) | Bookshelf | 4包 | [报告](./Darkhax-Minecraft__Bookshelf.md) | [卡片](./_卡片/Darkhax-Minecraft__Bookshelf.md) |
| [MehVahdJukaar/Moonlight](https://github.com/MehVahdJukaar/Moonlight) | Moonlight Lib | 3包 | [报告](./MehVahdJukaar__Moonlight.md) | [卡片](./_卡片/MehVahdJukaar__Moonlight.md) |
| [fzzyhmstrs/fconfig](https://github.com/fzzyhmstrs/fconfig) | Fzzy Config | 3包 | [报告](./fzzyhmstrs__fconfig.md) | [卡片](./_卡片/fzzyhmstrs__fconfig.md) |
| [jaredlll08/searchables](https://github.com/jaredlll08/searchables) | Searchables-forge-1.20.1-1.0.3.jar | 2包 | [报告](./jaredlll08__searchables.md) | — |
| [AHilyard/Iceberg](https://github.com/AHilyard/Iceberg) | Iceberg [Neo/Forge] | 3包 | [报告](./AHilyard__Iceberg.md) | [卡片](./_卡片/AHilyard__Iceberg.md) |
| [maruohon/malilib](https://github.com/maruohon/malilib) | MaLiLib | 1包 | [报告](./maruohon__malilib.md) | [卡片](./_卡片/maruohon__malilib.md) |
| [Team-Resourceful/ResourcefulLib](https://github.com/Team-Resourceful/ResourcefulLib) | Resourceful Lib | 3包 | [报告](./Team-Resourceful__ResourcefulLib.md) | [卡片](./_卡片/Team-Resourceful__ResourcefulLib.md) |
| [TheIllusiveC4/Curios](https://github.com/TheIllusiveC4/Curios) | Refined Storage - Curios Integration | 3包 | [报告](./TheIllusiveC4__Curios.md) | [卡片](./_卡片/TheIllusiveC4__Curios.md) |
| [TeamMidnightDust/MidnightLib](https://github.com/TeamMidnightDust/MidnightLib) | MidnightLib | 1包 | [报告](./TeamMidnightDust__MidnightLib.md) | [卡片](./_卡片/TeamMidnightDust__MidnightLib.md) |
| [Team-Resourceful/Resourceful-Config](https://github.com/Team-Resourceful/Resourceful-Config) | Resourceful Config | 3包 | [报告](./Team-Resourceful__Resourceful-Config.md) | [卡片](./_卡片/Team-Resourceful__Resourceful-Config.md) |
| [Apollounknowndev/lithostitched](https://github.com/Apollounknowndev/lithostitched) | Lithostitched | 3包 | [报告](./Apollounknowndev__lithostitched.md) | [卡片](./_卡片/Apollounknowndev__lithostitched.md) |
| [Glitchfiend/GlitchCore](https://github.com/Glitchfiend/GlitchCore) | 四季前置GlitchCore-neoforge-1.21.1-2.1.0.2.j | 2包 | [报告](./Glitchfiend__GlitchCore.md) | [卡片](./_卡片/Glitchfiend__GlitchCore.md) |
| [KubeJS-Mods/Rhino](https://github.com/KubeJS-Mods/Rhino) | [犀牛] rhino-2101.2.7-build.81.jar | 4包 | [报告](./KubeJS-Mods__Rhino.md) | [卡片](./_卡片/KubeJS-Mods__Rhino.md) |
| [Cristelknight999/Cristel-Lib](https://github.com/Cristelknight999/Cristel-Lib) | Cristel Lib | 3包 | [报告](./Cristelknight999__Cristel-Lib.md) | [卡片](./_卡片/Cristelknight999__Cristel-Lib.md) |
| [AHilyard/Prism](https://github.com/AHilyard/Prism) | Prism [Neo/Forge] | 2包 | [报告](./AHilyard__Prism.md) | [卡片](./_卡片/AHilyard__Prism.md) |
| [SuperMartijn642/SuperMartijn642sCoreLib](https://github.com/SuperMartijn642/SuperMartijn642sCoreLib) | SuperMartijn642's Core Lib | 2包 | [报告](./SuperMartijn642__SuperMartijn642sCoreLib.md) | [卡片](./_卡片/SuperMartijn642__SuperMartijn642sCoreLib.md) |
| [Alex-the-666/Citadel](https://github.com/Alex-the-666/Citadel) | Citadel | 1包 | [报告](./Alex-the-666__Citadel.md) | [卡片](./_卡片/Alex-the-666__Citadel.md) |
| [Octo-Studios/octo-lib](https://github.com/Octo-Studios/octo-lib) | ShatterLib | OctoLib | 2包 | [报告](./Octo-Studios__octo-lib.md) | [卡片](./_卡片/Octo-Studios__octo-lib.md) |
| [wisp-forest/accessories](https://github.com/wisp-forest/accessories) | Accessories | 2包 | [报告](./wisp-forest__accessories.md) | [卡片](./_卡片/wisp-forest__accessories.md) |
| [Darkhax-Minecraft/PrickleMC](https://github.com/Darkhax-Minecraft/PrickleMC) | Prickle | 3包 | [报告](./Darkhax-Minecraft__PrickleMC.md) | [卡片](./_卡片/Darkhax-Minecraft__PrickleMC.md) |
| [rfresh2/XaeroPlus](https://github.com/rfresh2/XaeroPlus) | XaeroPlus | 1包 | [报告](./rfresh2__XaeroPlus.md) | [卡片](./_卡片/rfresh2__XaeroPlus.md) |
| [Creators-of-Aeronautics/Simulated-Project](https://github.com/Creators-of-Aeronautics/Simulated-Project) | Create Aeronautics | 2包 | [报告](./Creators-of-Aeronautics__Simulated-Project.md) | [卡片](./_卡片/Creators-of-Aeronautics__Simulated-Project.md) |
| [TheIllusiveC4/Caelus](https://github.com/TheIllusiveC4/Caelus) | Caelus API | 2包 | [报告](./TheIllusiveC4__Caelus.md) | [卡片](./_卡片/TheIllusiveC4__Caelus.md) |
| [team-abnormals/blueprint](https://github.com/team-abnormals/blueprint) | Blueprint | 1包 | [报告](./team-abnormals__blueprint.md) | [卡片](./_卡片/team-abnormals__blueprint.md) |
| [Octo-Studios/immersive-ui](https://github.com/Octo-Studios/immersive-ui) | Immersive UI | 1包 | [报告](./Octo-Studios__immersive-ui.md) | [卡片](./_卡片/Octo-Studios__immersive-ui.md) |
| [ryanhcode/sable](https://github.com/ryanhcode/sable) | Sable | 2包 | [报告](./ryanhcode__sable.md) | [卡片](./_卡片/ryanhcode__sable.md) |
| [lender544/Lionfish-API](https://github.com/lender544/Lionfish-API) | Lionfish-API | 3包 | [报告](./lender544__Lionfish-API.md) | [卡片](./_卡片/lender544__Lionfish-API.md) |
| [Minecraft-LightLand/L2Library](https://github.com/Minecraft-LightLand/L2Library) | L2 Library | 2包 | [报告](./Minecraft-LightLand__L2Library.md) | [卡片](./_卡片/Minecraft-LightLand__L2Library.md) |
| [Low-Drag-MC/LDLib-Architectury](https://github.com/Low-Drag-MC/LDLib-Architectury) | LDLib | 2包 | [报告](./Low-Drag-MC__LDLib-Architectury.md) | [卡片](./_卡片/Low-Drag-MC__LDLib-Architectury.md) |
| [0999312/MMLib](https://github.com/0999312/MMLib) | Mysterious Mountain Lib | 2包 | [报告](./0999312__MMLib.md) | [卡片](./_卡片/0999312__MMLib.md) |
| [BlakeBr0/Cucumber](https://github.com/BlakeBr0/Cucumber) | Cucumber Library | 2包 | [报告](./BlakeBr0__Cucumber.md) | [卡片](./_卡片/BlakeBr0__Cucumber.md) |
| [Shadows-of-Fire/Placebo](https://github.com/Shadows-of-Fire/Placebo) | Placebo | 3包 | [报告](./Shadows-of-Fire__Placebo.md) | [卡片](./_卡片/Shadows-of-Fire__Placebo.md) |
| [SSKirillSS/Curios](https://github.com/SSKirillSS/Curios) | Curios API Continuation | 1包 | [报告](./SSKirillSS__Curios.md) | [卡片](./_卡片/SSKirillSS__Curios.md) |
| [userenxv/create-aeronautics-toolgun](https://github.com/userenxv/create-aeronautics-toolgun) | Create Aeronautics: Toolgun | 2包 | [报告](./userenxv__create-aeronautics-toolgun.md) | [卡片](./_卡片/userenxv__create-aeronautics-toolgun.md) |
| [SShakusora/WaystonesSable](https://github.com/SShakusora/WaystonesSable) | Waystones: Sable (Create Aeronautics Add | 1包 | [报告](./SShakusora__WaystonesSable.md) | [卡片](./_卡片/SShakusora__WaystonesSable.md) |
| [sprocketaudio/Create-Aeronautics-Throwable-Rope-Connector](https://github.com/sprocketaudio/Create-Aeronautics-Throwable-Rope-Connector) | Create Aeronautics: Throwable Rope Conne | 1包 | [报告](./sprocketaudio__Create-Aeronautics-Throwable-Rope-Connector.md) | [卡片](./_卡片/sprocketaudio__Create-Aeronautics-Throwable-Rope-Connector.md) |
| [matejhozlar/Create-Aeronautics-Climbable-Ropes](https://github.com/matejhozlar/Create-Aeronautics-Climbable-Ropes) | Climbable Ropes for Create Aeronautics | 1包 | [报告](./matejhozlar__Create-Aeronautics-Climbable-Ropes.md) | [卡片](./_卡片/matejhozlar__Create-Aeronautics-Climbable-Ropes.md) |
| [blorbee1/createaerophysicsgantry](https://github.com/blorbee1/createaerophysicsgantry) | Create Aeronautics Physics Gantry | 1包 | [报告](./blorbee1__createaerophysicsgantry.md) | [卡片](./_卡片/blorbee1__createaerophysicsgantry.md) |
| [leon-o/Create-Dynamic-Lights](https://github.com/leon-o/Create-Dynamic-Lights) | Create Sable Dynamic Lights | 1包 | [报告](./leon-o__Create-Dynamic-Lights.md) | [卡片](./_卡片/leon-o__Create-Dynamic-Lights.md) |
| [MaxnessAWA/Wind-Tunnel](https://github.com/MaxnessAWA/Wind-Tunnel) | Aeronautics:Wind Tunnel | 1包 | [报告](./MaxnessAWA__Wind-Tunnel.md) | [卡片](./_卡片/MaxnessAWA__Wind-Tunnel.md) |
| [CinemaMod/mcef](https://github.com/CinemaMod/mcef) | MCEF (Minecraft Chromium Embedded Framew | 1包 | — | [卡片](./_卡片/CinemaMod__mcef.md) |
| [SuperMartijn642/AdditionalLanterns](https://github.com/SuperMartijn642/AdditionalLanterns) | Additional Lanterns | 1包 | — | [卡片](./_卡片/SuperMartijn642__AdditionalLanterns.md) |
| [Rew1nd-dev/sable-schematic-api](https://github.com/Rew1nd-dev/sable-schematic-api) | Sable Photomancy | 1包 | — | [卡片](./_卡片/Rew1nd-dev__sable-schematic-api.md) |
| [Raguto/Citadel-1.21.1](https://github.com/Raguto/Citadel-1.21.1) | Citadel (Unofficial Port) | 1包 | [报告](./Raguto__Citadel-1.21.1.md) | [卡片](./_卡片/Raguto__Citadel-1.21.1.md) |
| [Jaredlll08/Searchables](https://github.com/Jaredlll08/Searchables) | Searchables | 2包 | — | [卡片](./_卡片/Jaredlll08__Searchables.md) |
| [Fuzss/forgeconfigapiport](https://github.com/Fuzss/forgeconfigapiport) | Forge Config API Port | 1包 | — | [卡片](./_卡片/Fuzss__forgeconfigapiport.md) |
| [userenxv/aeronautics-utility-objects](https://github.com/userenxv/aeronautics-utility-objects) | Create Aeronautics: Transmission & Linka | 1包 | — | [卡片](./_卡片/userenxv__aeronautics-utility-objects.md) |
| [SuperMartijn642/Fusion](https://github.com/SuperMartijn642/Fusion) | Fusion (Connected Textures) | 2包 | — | [卡片](./_卡片/SuperMartijn642__Fusion.md) |
| [M-K2525/VS_Hose_Connectors](https://github.com/M-K2525/VS_Hose_Connectors) | VS / Sable Hose Connectors | 1包 | — | [卡片](./_卡片/M-K2525__VS_Hose_Connectors.md) |
| [MrCrayfish/Framework](https://github.com/MrCrayfish/Framework) | framework-neoforge-1.21.1-0.13.11.jar | 2包 | — | [卡片](./_卡片/MrCrayfish__Framework.md) |
| [Corosauce/CoroUtil](https://github.com/Corosauce/CoroUtil) | 看看你在干什么前置coroutil-neoforge-1.21.0-1.3.9. | 1包 | — | [卡片](./_卡片/Corosauce__CoroUtil.md) |
| [Rain156/disable-enderman-picking-up-blocks](https://github.com/Rain156/disable-enderman-picking-up-blocks) | [禁用末影人搬运] depub.jar | 1包 | — | [卡片](./_卡片/Rain156__disable-enderman-picking-up-blocks.md) |
| [KODU16/vsie](https://github.com/KODU16/vsie) | AeroIE-1.0.0-hotfix2.jar | 1包 | — | [卡片](./_卡片/KODU16__vsie.md) |
| [SuperMartijn642/SimpleMagnets](https://github.com/SuperMartijn642/SimpleMagnets) | Simple Magnets | 1包 | — | [卡片](./_卡片/SuperMartijn642__SimpleMagnets.md) |
| [SuperMartijn642/TrashCans](https://github.com/SuperMartijn642/TrashCans) | Trash Cans | 1包 | — | [卡片](./_卡片/SuperMartijn642__TrashCans.md) |
| [SuperMartijn642/ItemCollectors](https://github.com/SuperMartijn642/ItemCollectors) | Item Collectors | 1包 | — | [卡片](./_卡片/SuperMartijn642__ItemCollectors.md) |
| [SuperMartijn642/SuperMartijn642sConfigLib](https://github.com/SuperMartijn642/SuperMartijn642sConfigLib) | SuperMartijn642's Config Lib | 1包 | — | [卡片](./_卡片/SuperMartijn642__SuperMartijn642sConfigLib.md) |

## Create 机械动力及附属（53）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [Creators-of-Create/Create](https://github.com/Creators-of-Create/Create) | Sophisticated Backpacks Create Integrati | 3包 | [报告](./Creators-of-Create__Create.md) | [卡片](./_卡片/Creators-of-Create__Create.md) |
| [mrh0/createaddition](https://github.com/mrh0/createaddition) | Create Crafts & Additions | 3包 | [报告](./mrh0__createaddition.md) | [卡片](./_卡片/mrh0__createaddition.md) |
| [copycats-plus/copycats](https://github.com/copycats-plus/copycats) | Create: Copycats+ | 2包 | [报告](./copycats-plus__copycats.md) | [卡片](./_卡片/copycats-plus__copycats.md) |
| [Cannoneers-of-Create/CreateBigCannons](https://github.com/Cannoneers-of-Create/CreateBigCannons) | Create Big Cannons | 2包 | [报告](./Cannoneers-of-Create__CreateBigCannons.md) | [卡片](./_卡片/Cannoneers-of-Create__CreateBigCannons.md) |
| [talrey/CreateDeco](https://github.com/talrey/CreateDeco) | Create Deco | 2包 | [报告](./talrey__CreateDeco.md) | [卡片](./_卡片/talrey__CreateDeco.md) |
| [hlysine/create_connected](https://github.com/hlysine/create_connected) | Create: Connected | 2包 | [报告](./hlysine__create_connected.md) | [卡片](./_卡片/hlysine__create_connected.md) |
| [george8188625/Create-Diesel-Generators](https://github.com/george8188625/Create-Diesel-Generators) | Create: Diesel Generators | 2包 | [报告](./george8188625__Create-Diesel-Generators.md) | [卡片](./_卡片/george8188625__Create-Diesel-Generators.md) |
| [DragonsPlusMinecraft/CreateEnchantmentIndustry](https://github.com/DragonsPlusMinecraft/CreateEnchantmentIndustry) | Create: Enchantment Industry | 3包 | [报告](./DragonsPlusMinecraft__CreateEnchantmentIndustry.md) | [卡片](./_卡片/DragonsPlusMinecraft__CreateEnchantmentIndustry.md) |
| [DragonsPlusMinecraft/CreateCentralKitchen](https://github.com/DragonsPlusMinecraft/CreateCentralKitchen) | Create: Central Kitchen | 2包 | [报告](./DragonsPlusMinecraft__CreateCentralKitchen.md) | [卡片](./_卡片/DragonsPlusMinecraft__CreateCentralKitchen.md) |
| [sudolev/CreateInteriorsMod](https://github.com/sudolev/CreateInteriorsMod) | Create: Interiors | 2包 | [报告](./sudolev__CreateInteriorsMod.md) | [卡片](./_卡片/sudolev__CreateInteriorsMod.md) |
| [DragonsPlusMinecraft/CreateDragonsPlus](https://github.com/DragonsPlusMinecraft/CreateDragonsPlus) | Create: Dragons Plus | 3包 | [报告](./DragonsPlusMinecraft__CreateDragonsPlus.md) | [卡片](./_卡片/DragonsPlusMinecraft__CreateDragonsPlus.md) |
| [Arsenalists-of-Create/Create-Radar](https://github.com/Arsenalists-of-Create/Create-Radar) | Create: Radars | 2包 | [报告](./Arsenalists-of-Create__Create-Radar.md) | [卡片](./_卡片/Arsenalists-of-Create__Create-Radar.md) |
| [PedroRok/CreateHypertubes](https://github.com/PedroRok/CreateHypertubes) | Create: Hypertubes | 3包 | [报告](./PedroRok__CreateHypertubes.md) | [卡片](./_卡片/PedroRok__CreateHypertubes.md) |
| [Create-In-Locomotion/Create-Escalated](https://github.com/Create-In-Locomotion/Create-Escalated) | Create: Escalated | 2包 | [报告](./Create-In-Locomotion__Create-Escalated.md) | [卡片](./_卡片/Create-In-Locomotion__Create-Escalated.md) |
| [Forsteri123/CreateEnderTransmission](https://github.com/Forsteri123/CreateEnderTransmission) | Create: Ender Transmission | 1包 | [报告](./Forsteri123__CreateEnderTransmission.md) | [卡片](./_卡片/Forsteri123__CreateEnderTransmission.md) |
| [Propulsion-Team/create-propulsion-simulated](https://github.com/Propulsion-Team/create-propulsion-simulated) | Create Propulsion: Simulated | 2包 | [报告](./Propulsion-Team__create-propulsion-simulated.md) | [卡片](./_卡片/Propulsion-Team__create-propulsion-simulated.md) |
| [timplay33/Create-Mobile-Packages](https://github.com/timplay33/Create-Mobile-Packages) | Create: Mobile Packages | 2包 | [报告](./timplay33__Create-Mobile-Packages.md) | [卡片](./_卡片/timplay33__Create-Mobile-Packages.md) |
| [duckgun13476/Create-SchematicChecker](https://github.com/duckgun13476/Create-SchematicChecker) | Create: SchematicChecker | 1包 | [报告](./duckgun13476__Create-SchematicChecker.md) | [卡片](./_卡片/duckgun13476__Create-SchematicChecker.md) |
| [CeoOfGoogle1/CreateClothes](https://github.com/CeoOfGoogle1/CreateClothes) | Create: Clothes | 1包 | [报告](./CeoOfGoogle1__CreateClothes.md) | [卡片](./_卡片/CeoOfGoogle1__CreateClothes.md) |
| [ggrgg13/Create--Redstone-Link-GUI](https://github.com/ggrgg13/Create--Redstone-Link-GUI) | Create: Redstone Link GUI | 2包 | [报告](./ggrgg13__Create--Redstone-Link-GUI.md) | [卡片](./_卡片/ggrgg13__Create--Redstone-Link-GUI.md) |
| [DragonsPlusMinecraft/CreateIntegratedFarming](https://github.com/DragonsPlusMinecraft/CreateIntegratedFarming) | Create: Integrated Farming | 1包 | [报告](./DragonsPlusMinecraft__CreateIntegratedFarming.md) | [卡片](./_卡片/DragonsPlusMinecraft__CreateIntegratedFarming.md) |
| [KhloeLeclair/CreateAdditionalLogistics](https://github.com/KhloeLeclair/CreateAdditionalLogistics) | Create: Additional Logistics | 1包 | [报告](./KhloeLeclair__CreateAdditionalLogistics.md) | [卡片](./_卡片/KhloeLeclair__CreateAdditionalLogistics.md) |
| [MoePus/CreateBetterFPS](https://github.com/MoePus/CreateBetterFPS) | CreateBetterFps | 1包 | [报告](./MoePus__CreateBetterFPS.md) | [卡片](./_卡片/MoePus__CreateBetterFPS.md) |
| [duckgun13476/Create-FastCannon](https://github.com/duckgun13476/Create-FastCannon) | Create: FastSchematicCannon | 1包 | [报告](./duckgun13476__Create-FastCannon.md) | [卡片](./_卡片/duckgun13476__Create-FastCannon.md) |
| [Forsteri123/CreateLiquidFuel](https://github.com/Forsteri123/CreateLiquidFuel) | Create: Liquid Fuel | 1包 | [报告](./Forsteri123__CreateLiquidFuel.md) | [卡片](./_卡片/Forsteri123__CreateLiquidFuel.md) |
| [tom5454/Create-Ore-Excavation](https://github.com/tom5454/Create-Ore-Excavation) | Create Ore Excavation | 1包 | [报告](./tom5454__Create-Ore-Excavation.md) | [卡片](./_卡片/tom5454__Create-Ore-Excavation.md) |
| [JuniKnytt/CreateRailGrinding](https://github.com/JuniKnytt/CreateRailGrinding) | Create: Train Track Rail Grinding | 1包 | [报告](./JuniKnytt__CreateRailGrinding.md) | [卡片](./_卡片/JuniKnytt__CreateRailGrinding.md) |
| [cakeGit/Create-Ez-Stock-Ticker](https://github.com/cakeGit/Create-Ez-Stock-Ticker) | Create: Easy Stock Ticker | 1包 | [报告](./cakeGit__Create-Ez-Stock-Ticker.md) | [卡片](./_卡片/cakeGit__Create-Ez-Stock-Ticker.md) |
| [oierbravo/create-mechanical-spawner](https://github.com/oierbravo/create-mechanical-spawner) | Create Mechanical Spawner | 1包 | [报告](./oierbravo__create-mechanical-spawner.md) | [卡片](./_卡片/oierbravo__create-mechanical-spawner.md) |
| [hlysine/create_power_loader](https://github.com/hlysine/create_power_loader) | Create: Power Loader | 1包 | [报告](./hlysine__create_power_loader.md) | [卡片](./_卡片/hlysine__create_power_loader.md) |
| [george8188625/Create-Electro-Energetics](https://github.com/george8188625/Create-Electro-Energetics) | Create: Electro Energetics | 1包 | [报告](./george8188625__Create-Electro-Energetics.md) | [卡片](./_卡片/george8188625__Create-Electro-Energetics.md) |
| [MaliceZed/frequency-create](https://github.com/MaliceZed/frequency-create) | Frequency Create | 1包 | [报告](./MaliceZed__frequency-create.md) | [卡片](./_卡片/MaliceZed__frequency-create.md) |
| [LIUKRAST/SmartBounds](https://github.com/LIUKRAST/SmartBounds) | Create Smart Bounds | 1包 | [报告](./LIUKRAST__SmartBounds.md) | [卡片](./_卡片/LIUKRAST__SmartBounds.md) |
| [ZLT9/create-vibrant-vaults](https://github.com/ZLT9/create-vibrant-vaults) | Create: Vibrant Vaults | 1包 | [报告](./ZLT9__create-vibrant-vaults.md) | [卡片](./_卡片/ZLT9__create-vibrant-vaults.md) |
| [cff1028/create_schematics_fix](https://github.com/cff1028/create_schematics_fix) | Create Bugfix: Schematic Patch | 1包 | [报告](./cff1028__create_schematics_fix.md) | [卡片](./_卡片/cff1028__create_schematics_fix.md) |
| [ForgeStove/CreateCyberGoogles](https://github.com/ForgeStove/CreateCyberGoogles) | Create: Cyber Goggles | 1包 | [报告](./ForgeStove__CreateCyberGoogles.md) | [卡片](./_卡片/ForgeStove__CreateCyberGoogles.md) |
| [getItemFromBlock/Create-Tweaked-Controllers](https://github.com/getItemFromBlock/Create-Tweaked-Controllers) | Create: Tweaked Controllers | 1包 | [报告](./getItemFromBlock__Create-Tweaked-Controllers.md) | [卡片](./_卡片/getItemFromBlock__Create-Tweaked-Controllers.md) |
| [yision1/GearsandTavern](https://github.com/yision1/GearsandTavern) | Create: Gears and Tavern | 1包 | [报告](./yision1__GearsandTavern.md) | [卡片](./_卡片/yision1__GearsandTavern.md) |
| [TakeruDavis/CreateCardboardedConveynience](https://github.com/TakeruDavis/CreateCardboardedConveynience) | Create: Cardboarded Conveynience | 1包 | [报告](./TakeruDavis__CreateCardboardedConveynience.md) | [卡片](./_卡片/TakeruDavis__CreateCardboardedConveynience.md) |
| [Industrialists-Of-Create/Create-Bits-n-Bobs](https://github.com/Industrialists-Of-Create/Create-Bits-n-Bobs) | Create: Bits 'n' Bobs | 1包 | [报告](./Industrialists-Of-Create__Create-Bits-n-Bobs.md) | [卡片](./_卡片/Industrialists-Of-Create__Create-Bits-n-Bobs.md) |
| [CosmonauticsTeam/Create-Cosmonautics](https://github.com/CosmonauticsTeam/Create-Cosmonautics) | Create Cosmonautics | 1包 | [报告](./CosmonauticsTeam__Create-Cosmonautics.md) | [卡片](./_卡片/CosmonauticsTeam__Create-Cosmonautics.md) |
| [yision1/CreateFluidLogistic](https://github.com/yision1/CreateFluidLogistic) | Create: FluidLogistics | 1包 | [报告](./yision1__CreateFluidLogistic.md) | [卡片](./_卡片/yision1__CreateFluidLogistic.md) |
| [FionaTheMortal/better-biome-blend](https://github.com/FionaTheMortal/better-biome-blend) | [别创建新世界！] 0world2create-neoforge-1.21.1- | 2包 | [报告](./FionaTheMortal__better-biome-blend.md) | [卡片](./_卡片/FionaTheMortal__better-biome-blend.md) |
| [cakeGit/Create-Trading-Floor](https://github.com/cakeGit/Create-Trading-Floor) | Create: Trading floor | 1包 | [报告](./cakeGit__Create-Trading-Floor.md) | [卡片](./_卡片/cakeGit__Create-Trading-Floor.md) |
| [Nobodiiiii/Create-Biotech](https://github.com/Nobodiiiii/Create-Biotech) | Create: Biotech - 机械动力：生物科技 | 1包 | [报告](./Nobodiiiii__Create-Biotech.md) | [卡片](./_卡片/Nobodiiiii__Create-Biotech.md) |
| [ausmez/create-storage-neo-forge](https://github.com/ausmez/create-storage-neo-forge) | Create: Storage [Neo/Forge] | 1包 | [报告](./ausmez__create-storage-neo-forge.md) | [卡片](./_卡片/ausmez__create-storage-neo-forge.md) |
| [cakeGit/Pattern-Schematics-Multiloader](https://github.com/cakeGit/Pattern-Schematics-Multiloader) | Create: Pattern Schematics | 1包 | [报告](./cakeGit__Pattern-Schematics-Multiloader.md) | [卡片](./_卡片/cakeGit__Pattern-Schematics-Multiloader.md) |
| [MIKOALOPEX/Create-FireFightingAdd](https://github.com/MIKOALOPEX/Create-FireFightingAdd) | Create: FireFighting Additions | 1包 | [报告](./MIKOALOPEX__Create-FireFightingAdd.md) | [卡片](./_卡片/MIKOALOPEX__Create-FireFightingAdd.md) |
| [rekales/create-more-package-couriers](https://github.com/rekales/create-more-package-couriers) | Create More: Package Couriers | 1包 | [报告](./rekales__create-more-package-couriers.md) | [卡片](./_卡片/rekales__create-more-package-couriers.md) |
| [Maxenonyme/Create-Deep-Seas](https://github.com/Maxenonyme/Create-Deep-Seas) | Create Deep Seas | 1包 | [报告](./Maxenonyme__Create-Deep-Seas.md) | [卡片](./_卡片/Maxenonyme__Create-Deep-Seas.md) |
| [KubeJS-Mods/KubeJS-Create](https://github.com/KubeJS-Mods/KubeJS-Create) | kubejs-create-neoforge-2101.3.1-build.18 | 1包 | [报告](./KubeJS-Mods__KubeJS-Create.md) | [卡片](./_卡片/KubeJS-Mods__KubeJS-Create.md) |
| [oierbravo/mechanicals-lib](https://github.com/oierbravo/mechanicals-lib) | Mechanicals Lib | 1包 | — | [卡片](./_卡片/oierbravo__mechanicals-lib.md) |
| [CubesterYT/CBC-CompactMount](https://github.com/CubesterYT/CBC-CompactMount) | CBC: Compact Mount | 1包 | — | [卡片](./_卡片/CubesterYT__CBC-CompactMount.md) |

## 科技 / 工业 / 能源（40）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [Qelifern/IronFurnaces](https://github.com/Qelifern/IronFurnaces) | Iron Furnaces | 2包 | [报告](./Qelifern__IronFurnaces.md) | [卡片](./_卡片/Qelifern__IronFurnaces.md) |
| [AppliedEnergistics/Applied-Energistics-2](https://github.com/AppliedEnergistics/Applied-Energistics-2) | Applied Energistics 2 | 3包 | [报告](./AppliedEnergistics__Applied-Energistics-2.md) | [卡片](./_卡片/AppliedEnergistics__Applied-Energistics-2.md) |
| [mekanism/Mekanism](https://github.com/mekanism/Mekanism) | Refined Storage - Mekanism Integration | 3包 | [报告](./mekanism__Mekanism.md) | [卡片](./_卡片/mekanism__Mekanism.md) |
| [BluSunrize/ImmersiveEngineering](https://github.com/BluSunrize/ImmersiveEngineering) | Immersive Engineering | 3包 | [报告](./BluSunrize__ImmersiveEngineering.md) | [卡片](./_卡片/BluSunrize__ImmersiveEngineering.md) |
| [McJtyMods/InControl](https://github.com/McJtyMods/InControl) | In Control! | 2包 | [报告](./McJtyMods__InControl.md) | [卡片](./_卡片/McJtyMods__InControl.md) |
| [Xalcon/TorchMaster](https://github.com/Xalcon/TorchMaster) | TorchMaster | 3包 | [报告](./Xalcon__TorchMaster.md) | [卡片](./_卡片/Xalcon__TorchMaster.md) |
| [AppliedEnergistics/GuideME](https://github.com/AppliedEnergistics/GuideME) | GuideME | 3包 | [报告](./AppliedEnergistics__GuideME.md) | [卡片](./_卡片/AppliedEnergistics__GuideME.md) |
| [Darkhax-Minecraft/BotanyPots](https://github.com/Darkhax-Minecraft/BotanyPots) | Botany Pots | 2包 | [报告](./Darkhax-Minecraft__BotanyPots.md) | [卡片](./_卡片/Darkhax-Minecraft__BotanyPots.md) |
| [Mars-The-Planet/Deimos](https://github.com/Mars-The-Planet/Deimos) | Deimos | 1包 | [报告](./Mars-The-Planet__Deimos.md) | [卡片](./_卡片/Mars-The-Planet__Deimos.md) |
| [AlmostReliable/merequester](https://github.com/AlmostReliable/merequester) | ME Requester | 2包 | [报告](./AlmostReliable__merequester.md) | [卡片](./_卡片/AlmostReliable__merequester.md) |
| [BlakeBr0/MysticalAgriculture](https://github.com/BlakeBr0/MysticalAgriculture) | Botany Pots - Mystical Agriculture Compa | 2包 | [报告](./BlakeBr0__MysticalAgriculture.md) | [卡片](./_卡片/BlakeBr0__MysticalAgriculture.md) |
| [AppliedEnergistics/Applied-Mekanistics](https://github.com/AppliedEnergistics/Applied-Mekanistics) | Applied Mekanistics | 2包 | [报告](./AppliedEnergistics__Applied-Mekanistics.md) | [卡片](./_卡片/AppliedEnergistics__Applied-Mekanistics.md) |
| [TheCBProject/EnderStorage](https://github.com/TheCBProject/EnderStorage) | Ender Storage | 1包 | [报告](./TheCBProject__EnderStorage.md) | [卡片](./_卡片/TheCBProject__EnderStorage.md) |
| [mango-buff/BotanyPotsOrePlanting](https://github.com/mango-buff/BotanyPotsOrePlanting) | [BPOP]Botany Pots Ore Planting | 1包 | [报告](./mango-buff__BotanyPotsOrePlanting.md) | [卡片](./_卡片/mango-buff__BotanyPotsOrePlanting.md) |
| [TwistedGate/ImmersivePetroleum](https://github.com/TwistedGate/ImmersivePetroleum) | Immersive Petroleum | 1包 | [报告](./TwistedGate__ImmersivePetroleum.md) | [卡片](./_卡片/TwistedGate__ImmersivePetroleum.md) |
| [SonarSonic/Flux-Networks](https://github.com/SonarSonic/Flux-Networks) | [通量网络] FluxNetworks-1.20.1-7.2.1.15.jar | 1包 | [报告](./SonarSonic__Flux-Networks.md) | [卡片](./_卡片/SonarSonic__Flux-Networks.md) |
| [P3pp3rF1y/SophisticatedCore](https://github.com/P3pp3rF1y/SophisticatedCore) | a/[精妙核心] sophisticatedcore-1.21.1-1.4.33 | 2包 | [报告](./P3pp3rF1y__SophisticatedCore.md) | [卡片](./_卡片/P3pp3rF1y__SophisticatedCore.md) |
| [P3pp3rF1y/SophisticatedStorage](https://github.com/P3pp3rF1y/SophisticatedStorage) | a/[精妙存储] sophisticatedstorage-1.21.1-1.5 | 2包 | [报告](./P3pp3rF1y__SophisticatedStorage.md) | [卡片](./_卡片/P3pp3rF1y__SophisticatedStorage.md) |
| [P3pp3rF1y/SophisticatedBackpacks](https://github.com/P3pp3rF1y/SophisticatedBackpacks) | a/[精妙背包] sophisticatedbackpacks-1.21.1-3 | 2包 | [报告](./P3pp3rF1y__SophisticatedBackpacks.md) | [卡片](./_卡片/P3pp3rF1y__SophisticatedBackpacks.md) |
| [Team-EnderIO/EnderIO](https://github.com/Team-EnderIO/EnderIO) | Ender IO | 1包 | [报告](./Team-EnderIO__EnderIO.md) | [卡片](./_卡片/Team-EnderIO__EnderIO.md) |
| [CyclopsMC/IntegratedDynamics](https://github.com/CyclopsMC/IntegratedDynamics) | Integrated Dynamics | 1包 | — | [卡片](./_卡片/CyclopsMC__IntegratedDynamics.md) |
| [McJty/MFFS](https://github.com/McJty/MFFS) | Modular Force Field Systems (MFFS) | 1包 | — | — |
| [gigabit101/EnderStorage](https://github.com/gigabit101/EnderStorage) | Ender Storage 1.8.+ | 1包 | — | — |
| [McJty/XNet](https://github.com/McJty/XNet) | Flux Networks | 1包 | — | [卡片](./_卡片/McJty__XNet.md) |
| [ZeroNoRyouki/ExtremeReactors](https://github.com/ZeroNoRyouki/ExtremeReactors) | Extreme Reactors | 1包 | — | — |
| [CyclopsMC/IntegratedTunnels](https://github.com/CyclopsMC/IntegratedTunnels) | Integrated Tunnels | 1包 | — | [卡片](./_卡片/CyclopsMC__IntegratedTunnels.md) |
| [TeamPneumatic/pnc-repressurized](https://github.com/TeamPneumatic/pnc-repressurized) | PneumaticCraft: Repressurized | 1包 | [报告](./TeamPneumatic__pnc-repressurized.md) | [卡片](./_卡片/TeamPneumatic__pnc-repressurized.md) |
| [CyclopsMC/IntegratedCrafting](https://github.com/CyclopsMC/IntegratedCrafting) | Integrated Crafting | 1包 | — | [卡片](./_卡片/CyclopsMC__IntegratedCrafting.md) |
| [Buuz135/titanium](https://github.com/Buuz135/titanium) | Titanium | 1包 | — | — |
| [CyclopsMC/IntegratedTerminals](https://github.com/CyclopsMC/IntegratedTerminals) | Integrated Terminals | 1包 | — | [卡片](./_卡片/CyclopsMC__IntegratedTerminals.md) |
| [McJty/RFToolsBase](https://github.com/McJty/RFToolsBase) | RFTools Base | 1包 | — | — |
| [McJty/RFToolsBuilder](https://github.com/McJty/RFToolsBuilder) | RFTools Builder | 1包 | — | — |
| [klikli-dev/occultism](https://github.com/klikli-dev/occultism) | Occultism KubeJS | 1包 | [报告](./klikli-dev__occultism.md) | [卡片](./_卡片/klikli-dev__occultism.md) |
| [baileyholl/Ars-Nouveau](https://github.com/baileyholl/Ars-Nouveau) | Ars Nouveau | 1包 | [报告](./baileyholl__Ars-Nouveau.md) | [卡片](./_卡片/baileyholl__Ars-Nouveau.md) |
| [Technici4n/Modern-Industrialization](https://github.com/Technici4n/Modern-Industrialization) | Modern Industrialization | 1包 | — | — |
| [henkelmax/pipez](https://github.com/henkelmax/pipez) | Pipez | 1包 | — | [卡片](./_卡片/henkelmax__pipez.md) |
| [Ultramega/CableTiers](https://github.com/Ultramega/CableTiers) | Cable Tiers | 1包 | — | — |
| [owmii/Powah](https://github.com/owmii/Powah) | Powah! (Rearchitected) | 1包 | — | [卡片](./_卡片/owmii__Powah.md) |
| [XyCraft-Mods/XyCraft](https://github.com/XyCraft-Mods/XyCraft) | XyCraft: Override | 1包 | — | — |
| [Railcraft/Railcraft](https://github.com/Railcraft/Railcraft) | Railcraft Reborn | 1包 | — | [卡片](./_卡片/Railcraft__Railcraft.md) |

## 实体 / 生物 / AI（25）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [Glitchfiend/TerraBlender](https://github.com/Glitchfiend/TerraBlender) | TerraBlender-forge-1.20.1-3.0.1.10.jar | 3包 | [报告](./Glitchfiend__TerraBlender.md) | [卡片](./_卡片/Glitchfiend__TerraBlender.md) |
| [lender544/new1.20.1](https://github.com/lender544/new1.20.1) | L_Ender 's Cataclysm | 3包 | [报告](./lender544__new1.20.1.md) | [卡片](./_卡片/lender544__new1.20.1.md) |
| [AlexModGuy/AlexsMobs](https://github.com/AlexModGuy/AlexsMobs) | Alex's Mobs | 1包 | [报告](./AlexModGuy__AlexsMobs.md) | [卡片](./_卡片/AlexModGuy__AlexsMobs.md) |
| [Luke100000/ImmersiveAircraft](https://github.com/Luke100000/ImmersiveAircraft) | Immersive Aircraft | 1包 | [报告](./Luke100000__ImmersiveAircraft.md) | [卡片](./_卡片/Luke100000__ImmersiveAircraft.md) |
| [Exopandora/ShoulderSurfing](https://github.com/Exopandora/ShoulderSurfing) | Shoulder Surfing Reloaded | 1包 | [报告](./Exopandora__ShoulderSurfing.md) | [卡片](./_卡片/Exopandora__ShoulderSurfing.md) |
| [starfish-studios/Naturalist](https://github.com/starfish-studios/Naturalist) | Naturalist | 1包 | [报告](./starfish-studios__Naturalist.md) | [卡片](./_卡片/starfish-studios__Naturalist.md) |
| [TartaricAcid/TouhouLittleMaid](https://github.com/TartaricAcid/TouhouLittleMaid) | Touhou Little Maid | 2包 | [报告](./TartaricAcid__TouhouLittleMaid.md) | [卡片](./_卡片/TartaricAcid__TouhouLittleMaid.md) |
| [bonsaistudi0s/Creeper-Overhaul](https://github.com/bonsaistudi0s/Creeper-Overhaul) | Creeper Overhaul | 2包 | [报告](./bonsaistudi0s__Creeper-Overhaul.md) | [卡片](./_卡片/bonsaistudi0s__Creeper-Overhaul.md) |
| [bonsaistudi0s/Enderman-Overhaul](https://github.com/bonsaistudi0s/Enderman-Overhaul) | Enderman Overhaul | 2包 | [报告](./bonsaistudi0s__Enderman-Overhaul.md) | [卡片](./_卡片/bonsaistudi0s__Enderman-Overhaul.md) |
| [Miauczel/Legendary-Monsters-1.21.1-NeoForge](https://github.com/Miauczel/Legendary-Monsters-1.21.1-NeoForge) | Legendary Monsters | 2包 | [报告](./Miauczel__Legendary-Monsters-1.21.1-NeoForge.md) | [卡片](./_卡片/Miauczel__Legendary-Monsters-1.21.1-NeoForge.md) |
| [GaylordFockerCN/Cataclysm-Dimension](https://github.com/GaylordFockerCN/Cataclysm-Dimension) | Cataclysm Dimension | 1包 | [报告](./GaylordFockerCN__Cataclysm-Dimension.md) | [卡片](./_卡片/GaylordFockerCN__Cataclysm-Dimension.md) |
| [Raguto/AlexsMobs-1.21.1](https://github.com/Raguto/AlexsMobs-1.21.1) | Alex's Mobs (Unofficial Port) | 1包 | [报告](./Raguto__AlexsMobs-1.21.1.md) | [卡片](./_卡片/Raguto__AlexsMobs-1.21.1.md) |
| [Wall-ev/MaidsoulKitchen](https://github.com/Wall-ev/MaidsoulKitchen) | Maidsoul Kitchen | 1包 | [报告](./Wall-ev__MaidsoulKitchen.md) | [卡片](./_卡片/Wall-ev__MaidsoulKitchen.md) |
| [0999312/umapyoi](https://github.com/0999312/umapyoi) | Umapyoi | 1包 | [报告](./0999312__umapyoi.md) | [卡片](./_卡片/0999312__umapyoi.md) |
| [Chaolux1/LendersDelight](https://github.com/Chaolux1/LendersDelight) | L_Ender 's Cataclysm Delight | 1包 | [报告](./Chaolux1__LendersDelight.md) | [卡片](./_卡片/Chaolux1__LendersDelight.md) |
| [mortuusars/Horseman](https://github.com/mortuusars/Horseman) | Horseman | 1包 | [报告](./mortuusars__Horseman.md) | [卡片](./_卡片/mortuusars__Horseman.md) |
| [IAFEnvoy/IceAndFire-CE](https://github.com/IAFEnvoy/IceAndFire-CE) | [冰火传说社区版] iceandfire-2.1.jar | 1包 | [报告](./IAFEnvoy__IceAndFire-CE.md) | [卡片](./_卡片/IAFEnvoy__IceAndFire-CE.md) |
| [TeamTwilight/twilightforest](https://github.com/TeamTwilight/twilightforest) | a/[暮色森林] twilightforest-1.21.1-4.8.3345- | 2包 | [报告](./TeamTwilight__twilightforest.md) | [卡片](./_卡片/TeamTwilight__twilightforest.md) |
| [AlexModGuy/AlexsCaves](https://github.com/AlexModGuy/AlexsCaves) | 洞穴alexscaves-2.0.2.jar | 1包 | [报告](./AlexModGuy__AlexsCaves.md) | [卡片](./_卡片/AlexModGuy__AlexsCaves.md) |
| [sch246/MaidUseHandCrank](https://github.com/sch246/MaidUseHandCrank) | MaidUseHandCrank | 1包 | — | [卡片](./_卡片/sch246__MaidUseHandCrank.md) |
| [Corosauce/ZombieAwareness](https://github.com/Corosauce/ZombieAwareness) | Zombie Awareness | 1包 | — | [卡片](./_卡片/Corosauce__ZombieAwareness.md) |
| [WinExp/MaidTavern](https://github.com/WinExp/MaidTavern) | Maid Tavern | 1包 | — | [卡片](./_卡片/WinExp__MaidTavern.md) |
| [ExcessiveAmountsOfZombies/EpheroLib](https://github.com/ExcessiveAmountsOfZombies/EpheroLib) | EpheroLib-1.20.1-FORGE-1.2.0.jar | 1包 | — | [卡片](./_卡片/ExcessiveAmountsOfZombies__EpheroLib.md) |
| [TelepathicGrunt/Bumblezone](https://github.com/TelepathicGrunt/Bumblezone) | The Bumblezone (NeoForge/Forge) | 1包 | [报告](./TelepathicGrunt__Bumblezone.md) | [卡片](./_卡片/TelepathicGrunt__Bumblezone.md) |
| [marlester-dev/twilightforest-unofficial](https://github.com/marlester-dev/twilightforest-unofficial) | The Twilight Forest | 1包 | — | [卡片](./_卡片/marlester-dev__twilightforest-unofficial.md) |

## 战斗 / 枪械 / 装备 / 属性（25）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [MCModderAnchor/TACZ](https://github.com/MCModderAnchor/TACZ) | [TaCZ] Timeless and Classics Zero | 1包 | [报告](./MCModderAnchor__TACZ.md) | [卡片](./_卡片/MCModderAnchor__TACZ.md) |
| [Darkhax-Minecraft/AttributeFix](https://github.com/Darkhax-Minecraft/AttributeFix) | AttributeFix | 4包 | [报告](./Darkhax-Minecraft__AttributeFix.md) | [卡片](./_卡片/Darkhax-Minecraft__AttributeFix.md) |
| [ochotonida/artifacts](https://github.com/ochotonida/artifacts) | Artifacts | 2包 | [报告](./ochotonida__artifacts.md) | [卡片](./_卡片/ochotonida__artifacts.md) |
| [Wagers-of-Industrial-Warfare/RitchiesProjectileLib](https://github.com/Wagers-of-Industrial-Warfare/RitchiesProjectileLib) | Ritchie's Projectile Library | 2包 | [报告](./Wagers-of-Industrial-Warfare__RitchiesProjectileLib.md) | [卡片](./_卡片/Wagers-of-Industrial-Warfare__RitchiesProjectileLib.md) |
| [Darkhax-Minecraft/Max-Health-Fix](https://github.com/Darkhax-Minecraft/Max-Health-Fix) | Max Health Fix | 2包 | [报告](./Darkhax-Minecraft__Max-Health-Fix.md) | [卡片](./_卡片/Darkhax-Minecraft__Max-Health-Fix.md) |
| [MUKSC/TACZ-1.21.1](https://github.com/MUKSC/TACZ-1.21.1) | [UNOFFICIAL] TaCZ 1.21.1 NeoForge Port | 1包 | [报告](./MUKSC__TACZ-1.21.1.md) | [卡片](./_卡片/MUKSC__TACZ-1.21.1.md) |
| [Minecraft-LightLand/L2Artifacts](https://github.com/Minecraft-LightLand/L2Artifacts) | L2 Artifacts | 1包 | [报告](./Minecraft-LightLand__L2Artifacts.md) | [卡片](./_卡片/Minecraft-LightLand__L2Artifacts.md) |
| [Txt-Text/TaCZ-Labs](https://github.com/Txt-Text/TaCZ-Labs) | TaCZ-Labs | 1包 | [报告](./Txt-Text__TaCZ-Labs.md) | [卡片](./_卡片/Txt-Text__TaCZ-Labs.md) |
| [Shadows-of-Fire/Apotheosis](https://github.com/Shadows-of-Fire/Apotheosis) | Apotheosis | 3包 | [报告](./Shadows-of-Fire__Apotheosis.md) | [卡片](./_卡片/Shadows-of-Fire__Apotheosis.md) |
| [MUKSC/TaCZPackUpgrader](https://github.com/MUKSC/TaCZPackUpgrader) | TaCZ Pack Upgrader | 1包 | [报告](./MUKSC__TaCZPackUpgrader.md) | [卡片](./_卡片/MUKSC__TaCZPackUpgrader.md) |
| [Shadows-of-Fire/Apothic-Enchanting](https://github.com/Shadows-of-Fire/Apothic-Enchanting) | Apothic-Enchanting | 2包 | [报告](./Shadows-of-Fire__Apothic-Enchanting.md) | [卡片](./_卡片/Shadows-of-Fire__Apothic-Enchanting.md) |
| [Shadows-of-Fire/Apothic-Spawners](https://github.com/Shadows-of-Fire/Apothic-Spawners) | Apothic-Spawners | 3包 | [报告](./Shadows-of-Fire__Apothic-Spawners.md) | [卡片](./_卡片/Shadows-of-Fire__Apothic-Spawners.md) |
| [Iron431/irons-spells-n-spellbooks](https://github.com/Iron431/irons-spells-n-spellbooks) | Iron's Spells 'n Spellbooks | 2包 | [报告](./Iron431__irons-spells-n-spellbooks.md) | [卡片](./_卡片/Iron431__irons-spells-n-spellbooks.md) |
| [Shadows-of-Fire/Apothic-Attributes](https://github.com/Shadows-of-Fire/Apothic-Attributes) | ApothicAttributes-1.21.1-2.10.1.jar | 2包 | [报告](./Shadows-of-Fire__Apothic-Attributes.md) | [卡片](./_卡片/Shadows-of-Fire__Apothic-Attributes.md) |
| [Iron431/irons-jewelry](https://github.com/Iron431/irons-jewelry) | irons_jewelry-1.21.1-1.6.0.jar | 1包 | [报告](./Iron431__irons-jewelry.md) | [卡片](./_卡片/Iron431__irons-jewelry.md) |
| [CoFH/Ensorcellation](https://github.com/CoFH/Ensorcellation) | Ensorcellation | 1包 | — | [卡片](./_卡片/CoFH__Ensorcellation.md) |
| [Autovw/AdvancedNetherite](https://github.com/Autovw/AdvancedNetherite) | Advanced Netherite | 1包 | — | [卡片](./_卡片/Autovw__AdvancedNetherite.md) |
| [DawnOfTimeMC/armoreddoggo](https://github.com/DawnOfTimeMC/armoreddoggo) | Armored Doggo | 1包 | — | [卡片](./_卡片/DawnOfTimeMC__armoreddoggo.md) |
| [DawnOfTimeMC/armoroftheages](https://github.com/DawnOfTimeMC/armoroftheages) | Armor of the Ages | 1包 | — | [卡片](./_卡片/DawnOfTimeMC__armoroftheages.md) |
| [Fuzss/combatnouveau](https://github.com/Fuzss/combatnouveau) | Combat Nouveau | 1包 | — | [卡片](./_卡片/Fuzss__combatnouveau.md) |
| [Hidoni/Transmog](https://github.com/Hidoni/Transmog) | Transmog | 1包 | — | [卡片](./_卡片/Hidoni__Transmog.md) |
| [Cazsius/Spice-of-Life-Carrot-Edition](https://github.com/Cazsius/Spice-of-Life-Carrot-Edition) | [生活调味料：胡萝卜版] solcarrot-1.21.1-1.16.6.jar | 1包 | — | [卡片](./_卡片/Cazsius__Spice-of-Life-Carrot-Edition.md) |
| [Tfarcenim/OverloadedArmorBar](https://github.com/Tfarcenim/OverloadedArmorBar) | [护甲上限突破] overloadedarmorbar-1.20.1-1.jar | 1包 | — | [卡片](./_卡片/Tfarcenim__OverloadedArmorBar.md) |
| [zlainsama/CosmeticArmorReworked](https://github.com/zlainsama/CosmeticArmorReworked) | [时装盔甲重置版] cosmeticarmorreworked-1.20.1-v | 1包 | — | [卡片](./_卡片/zlainsama__CosmeticArmorReworked.md) |
| [Leclowndu93150/Corpse-Cosmetic-Armor-Compat](https://github.com/Leclowndu93150/Corpse-Cosmetic-Armor-Compat) | Cosmetic Armor Reworked | 1包 | — | [卡片](./_卡片/Leclowndu93150__Corpse-Cosmetic-Armor-Compat.md) |

## 世界生成 / 结构 / 维度（29）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [Glitchfiend/BiomesOPlenty](https://github.com/Glitchfiend/BiomesOPlenty) | Biomes O' Plenty | 1包 | [报告](./Glitchfiend__BiomesOPlenty.md) | [卡片](./_卡片/Glitchfiend__BiomesOPlenty.md) |
| [YUNG-GANG/YUNGs-API](https://github.com/YUNG-GANG/YUNGs-API) | YUNG's API (NeoForge) [1.20.4-1.21.1 ONL | 2包 | [报告](./YUNG-GANG__YUNGs-API.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-API.md) |
| [MattCzyr/NaturesCompass](https://github.com/MattCzyr/NaturesCompass) | Nature's Compass | 3包 | [报告](./MattCzyr__NaturesCompass.md) | [卡片](./_卡片/MattCzyr__NaturesCompass.md) |
| [YUNG-GANG/YUNGs-Better-Fortresses](https://github.com/YUNG-GANG/YUNGs-Better-Fortresses) | YUNG's Better Nether Fortresses (NeoForg | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Fortresses.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Fortresses.md) |
| [YUNG-GANG/YUNGs-Better-Ocean-Monuments](https://github.com/YUNG-GANG/YUNGs-Better-Ocean-Monuments) | YUNG's Better Ocean Monuments (NeoForge) | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Ocean-Monuments.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Ocean-Monuments.md) |
| [YUNG-GANG/YUNGs-Better-Dungeons](https://github.com/YUNG-GANG/YUNGs-Better-Dungeons) | YUNG's Better Dungeons (NeoForge) [1.20. | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Dungeons.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Dungeons.md) |
| [YUNG-GANG/YUNGs-Better-Mineshafts](https://github.com/YUNG-GANG/YUNGs-Better-Mineshafts) | YUNG's Better Mineshafts (NeoForge) [1.2 | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Mineshafts.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Mineshafts.md) |
| [YUNG-GANG/YUNGs-Better-Jungle-Temples](https://github.com/YUNG-GANG/YUNGs-Better-Jungle-Temples) | YUNG's Better Jungle Temples (NeoForge)  | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Jungle-Temples.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Jungle-Temples.md) |
| [yungnickyoung/YUNGs-Better-End-Island](https://github.com/yungnickyoung/YUNGs-Better-End-Island) | YUNG's Better End Island (NeoForge) [1.2 | 2包 | [报告](./yungnickyoung__YUNGs-Better-End-Island.md) | [卡片](./_卡片/yungnickyoung__YUNGs-Better-End-Island.md) |
| [YUNG-GANG/YUNGs-Better-Strongholds](https://github.com/YUNG-GANG/YUNGs-Better-Strongholds) | YUNG's Better Strongholds (NeoForge) [1. | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Strongholds.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Strongholds.md) |
| [YUNG-GANG/YUNGs-Better-Witch-Huts](https://github.com/YUNG-GANG/YUNGs-Better-Witch-Huts) | YUNG's Better Witch Huts (NeoForge) [1.2 | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Witch-Huts.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Witch-Huts.md) |
| [YUNG-GANG/YUNGs-Better-Desert-Temples](https://github.com/YUNG-GANG/YUNGs-Better-Desert-Temples) | YUNG's Better Desert Temples (NeoForge)  | 2包 | [报告](./YUNG-GANG__YUNGs-Better-Desert-Temples.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Better-Desert-Temples.md) |
| [YUNG-GANG/YUNGs-Bridges](https://github.com/YUNG-GANG/YUNGs-Bridges) | YUNG's Bridges | 1包 | [报告](./YUNG-GANG__YUNGs-Bridges.md) | [卡片](./_卡片/YUNG-GANG__YUNGs-Bridges.md) |
| [DynamicTreesTeam/DynamicTrees](https://github.com/DynamicTreesTeam/DynamicTrees) | Dynamic Trees | 1包 | [报告](./DynamicTreesTeam__DynamicTrees.md) | [卡片](./_卡片/DynamicTreesTeam__DynamicTrees.md) |
| [MattCzyr/ExplorersCompass](https://github.com/MattCzyr/ExplorersCompass) | [探险者指南针 修改] explorerscompass-edited-1.21 | 3包 | [报告](./MattCzyr__ExplorersCompass.md) | [卡片](./_卡片/MattCzyr__ExplorersCompass.md) |
| [McJtyMods/LostCities](https://github.com/McJtyMods/LostCities) | The Lost Cities | 1包 | [报告](./McJtyMods__LostCities.md) | [卡片](./_卡片/McJtyMods__LostCities.md) |
| [DynamicTreesTeam/DynamicTreesPlus](https://github.com/DynamicTreesTeam/DynamicTreesPlus) | Dynamic Trees Plus | 1包 | [报告](./DynamicTreesTeam__DynamicTreesPlus.md) | [卡片](./_卡片/DynamicTreesTeam__DynamicTreesPlus.md) |
| [MaxenceDC/sparsestructures](https://github.com/MaxenceDC/sparsestructures) | Sparse Structures | 1包 | [报告](./MaxenceDC__sparsestructures.md) | [卡片](./_卡片/MaxenceDC__sparsestructures.md) |
| [yungnickyoung/YUNGs-Menu-Tweaks](https://github.com/yungnickyoung/YUNGs-Menu-Tweaks) | YUNG's Menu Tweaks | 1包 | [报告](./yungnickyoung__YUNGs-Menu-Tweaks.md) | [卡片](./_卡片/yungnickyoung__YUNGs-Menu-Tweaks.md) |
| [AllenSeitz/DimDungeons](https://github.com/AllenSeitz/DimDungeons) | Dimensional Dungeons | 1包 | [报告](./AllenSeitz__DimDungeons.md) | [卡片](./_卡片/AllenSeitz__DimDungeons.md) |
| [klinbee/Aetherial-Islands](https://github.com/klinbee/Aetherial-Islands) | Aetherial Islands | 1包 | [报告](./klinbee__Aetherial-Islands.md) | [卡片](./_卡片/klinbee__Aetherial-Islands.md) |
| [FinnSetchell/MoogsStructureLib](https://github.com/FinnSetchell/MoogsStructureLib) | Moog's Structure Lib (moogs_structures) | 2包 | [报告](./FinnSetchell__MoogsStructureLib.md) | [卡片](./_卡片/FinnSetchell__MoogsStructureLib.md) |
| [FinnSetchell/MoogsEndStructures](https://github.com/FinnSetchell/MoogsEndStructures) | MES - Moog's End Structures | 2包 | [报告](./FinnSetchell__MoogsEndStructures.md) | [卡片](./_卡片/FinnSetchell__MoogsEndStructures.md) |
| [TelepathicGrunt/RepurposedStructures](https://github.com/TelepathicGrunt/RepurposedStructures) | Repurposed Structures - Neoforge/Forge | 2包 | [报告](./TelepathicGrunt__RepurposedStructures.md) | [卡片](./_卡片/TelepathicGrunt__RepurposedStructures.md) |
| [klinbee/No-Void-Structures](https://github.com/klinbee/No-Void-Structures) | No Void Structures | 1包 | [报告](./klinbee__No-Void-Structures.md) | [卡片](./_卡片/klinbee__No-Void-Structures.md) |
| [Penumbra-MC/Enderscape](https://github.com/Penumbra-MC/Enderscape) | Enderscape | 1包 | — | [卡片](./_卡片/Penumbra-MC__Enderscape.md) |
| [Corosauce/Weather2](https://github.com/Corosauce/Weather2) | Weather Storms & Tornadoes | 1包 | — | [卡片](./_卡片/Corosauce__Weather2.md) |
| [Glitchfiend/SereneSeasons](https://github.com/Glitchfiend/SereneSeasons) | a/[静谧四季／季节] SereneSeasons-neoforge-1.21. | 2包 | — | [卡片](./_卡片/Glitchfiend__SereneSeasons.md) |
| [The-Aether-Team/The-Aether](https://github.com/The-Aether-Team/The-Aether) | The Aether | 1包 | — | [卡片](./_卡片/The-Aether-Team__The-Aether.md) |

## 食物 / 农夫乐事生态（24）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [vectorwing/FarmersDelight](https://github.com/vectorwing/FarmersDelight) | Farmer's Delight | 4包 | [报告](./vectorwing__FarmersDelight.md) | [卡片](./_卡片/vectorwing__FarmersDelight.md) |
| [FoggyHillside/End-s-Delight](https://github.com/FoggyHillside/End-s-Delight) | End's Delight | 2包 | [报告](./FoggyHillside__End-s-Delight.md) | [卡片](./_卡片/FoggyHillside__End-s-Delight.md) |
| [Let-s-Do-Collection/Beachparty](https://github.com/Let-s-Do-Collection/Beachparty) | [Let's Do] Beachparty | 1包 | [报告](./Let-s-Do-Collection__Beachparty.md) | [卡片](./_卡片/Let-s-Do-Collection__Beachparty.md) |
| [Monad-Modding/BrewinAndChewin](https://github.com/Monad-Modding/BrewinAndChewin) | Brewin' And Chewin' | 2包 | [报告](./Monad-Modding__BrewinAndChewin.md) | [卡片](./_卡片/Monad-Modding__BrewinAndChewin.md) |
| [jkvin114/display-delight-neoforge](https://github.com/jkvin114/display-delight-neoforge) | Display Delight | 2包 | [报告](./jkvin114__display-delight-neoforge.md) | [卡片](./_卡片/jkvin114__display-delight-neoforge.md) |
| [Minecraft-LightLand/FruitsDelight](https://github.com/Minecraft-LightLand/FruitsDelight) | Fruits Delight | 1包 | [报告](./Minecraft-LightLand__FruitsDelight.md) | [卡片](./_卡片/Minecraft-LightLand__FruitsDelight.md) |
| [BmtUltra/Kaleidoscope-Compat](https://github.com/BmtUltra/Kaleidoscope-Compat) | Kaleidoscope Compat | 1包 | [报告](./BmtUltra__Kaleidoscope-Compat.md) | [卡片](./_卡片/BmtUltra__Kaleidoscope-Compat.md) |
| [KaleidoscopeMods/KaleidoscopeCookery](https://github.com/KaleidoscopeMods/KaleidoscopeCookery) | Kaleidoscope Cookery | 1包 | [报告](./KaleidoscopeMods__KaleidoscopeCookery.md) | [卡片](./_卡片/KaleidoscopeMods__KaleidoscopeCookery.md) |
| [WitherRedstone/Kaleidoscope-DimensionsWine](https://github.com/WitherRedstone/Kaleidoscope-DimensionsWine) | Kaleidoscope：Dimensions wine | 1包 | [报告](./WitherRedstone__Kaleidoscope-DimensionsWine.md) | [卡片](./_卡片/WitherRedstone__Kaleidoscope-DimensionsWine.md) |
| [TartaricAcid/KaleidoscopeDoll](https://github.com/TartaricAcid/KaleidoscopeDoll) | Kaleidoscope Doll | 1包 | [报告](./TartaricAcid__KaleidoscopeDoll.md) | [卡片](./_卡片/TartaricAcid__KaleidoscopeDoll.md) |
| [baiyin1223/Kaleidoscope_bloodwine](https://github.com/baiyin1223/Kaleidoscope_bloodwine) | Kaleidoscope_bloodwine | 1包 | [报告](./baiyin1223__Kaleidoscope_bloodwine.md) | [卡片](./_卡片/baiyin1223__Kaleidoscope_bloodwine.md) |
| [breezeth-CN/KaleidoscopeGrilling](https://github.com/breezeth-CN/KaleidoscopeGrilling) | Kaleidoscope Grilling | 1包 | [报告](./breezeth-CN__KaleidoscopeGrilling.md) | [卡片](./_卡片/breezeth-CN__KaleidoscopeGrilling.md) |
| [NightEpiphany/KaleidoscopeHodgepodge](https://github.com/NightEpiphany/KaleidoscopeHodgepodge) | Kaleidoscope Hodgepodge | 1包 | [报告](./NightEpiphany__KaleidoscopeHodgepodge.md) | [卡片](./_卡片/NightEpiphany__KaleidoscopeHodgepodge.md) |
| [KaleidoscopeMods/KaleidoscopeTavern](https://github.com/KaleidoscopeMods/KaleidoscopeTavern) | Kaleidoscope Tavern | 1包 | [报告](./KaleidoscopeMods__KaleidoscopeTavern.md) | [卡片](./_卡片/KaleidoscopeMods__KaleidoscopeTavern.md) |
| [Umpaz/NethersDelight](https://github.com/Umpaz/NethersDelight) | Nether's Delight | 1包 | — | [卡片](./_卡片/Umpaz__NethersDelight.md) |
| [0999312/Corn-Delight](https://github.com/0999312/Corn-Delight) | Corn Delight | 1包 | — | [卡片](./_卡片/0999312__Corn-Delight.md) |
| [Moralle/VanillaCookbook](https://github.com/Moralle/VanillaCookbook) | Vanilla Cookbook | 1包 | — | [卡片](./_卡片/Moralle__VanillaCookbook.md) |
| [SoyTutta/MyNethersDelight](https://github.com/SoyTutta/MyNethersDelight) | My Nether's Delight | 1包 | — | [卡片](./_卡片/SoyTutta__MyNethersDelight.md) |
| [Baisylia/Cultural-Delights-1.19.2](https://github.com/Baisylia/Cultural-Delights-1.19.2) | Cultural Delights | 1包 | — | [卡片](./_卡片/Baisylia__Cultural-Delights-1.19.2.md) |
| [Minecraft-LightLand/Cuisine-Delight](https://github.com/Minecraft-LightLand/Cuisine-Delight) | Cuisine Delight | 1包 | — | [卡片](./_卡片/Minecraft-LightLand__Cuisine-Delight.md) |
| [Let-s-Do-Collection/Candlelight](https://github.com/Let-s-Do-Collection/Candlelight) | [Let's Do] Candlelight - Farm&Charm comp | 1包 | — | [卡片](./_卡片/Let-s-Do-Collection__Candlelight.md) |
| [Let-s-Do-Collection/vinery](https://github.com/Let-s-Do-Collection/vinery) | [Let's Do] Vinery | 1包 | — | [卡片](./_卡片/Let-s-Do-Collection__vinery.md) |
| [Let-s-Do-Collection/Bakery](https://github.com/Let-s-Do-Collection/Bakery) | [Let's Do] Bakery - Farm&Charm Compat | 1包 | — | [卡片](./_卡片/Let-s-Do-Collection__Bakery.md) |
| [axperty/cratedelight](https://github.com/axperty/cratedelight) | Crate Delight | 1包 | — | [卡片](./_卡片/axperty__cratedelight.md) |

## GUI / HUD / 客户端体验（55）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [IrisShaders/Iris](https://github.com/IrisShaders/Iris) | Iris Shaders | 3包 | [报告](./IrisShaders__Iris.md) | [卡片](./_卡片/IrisShaders__Iris.md) |
| [Traben-0/Entity_Texture_Features](https://github.com/Traben-0/Entity_Texture_Features) | [ETF] Entity Texture Features | 1包 | [报告](./Traben-0__Entity_Texture_Features.md) | [卡片](./_卡片/Traben-0__Entity_Texture_Features.md) |
| [Traben-0/Entity_Model_Features](https://github.com/Traben-0/Entity_Model_Features) | [EMF] Entity Model Features | 1包 | [报告](./Traben-0__Entity_Model_Features.md) | [卡片](./_卡片/Traben-0__Entity_Model_Features.md) |
| [squeek502/AppleSkin](https://github.com/squeek502/AppleSkin) | AppleSkin | 4包 | [报告](./squeek502__AppleSkin.md) | [卡片](./_卡片/squeek502__AppleSkin.md) |
| [tr7zw/NotEnoughAnimations](https://github.com/tr7zw/NotEnoughAnimations) | Not Enough Animations | 2包 | [报告](./tr7zw__NotEnoughAnimations.md) | [卡片](./_卡片/tr7zw__NotEnoughAnimations.md) |
| [mezz/JustEnoughItems](https://github.com/mezz/JustEnoughItems) | Smithing Template Viewer for JEI/EMI | 4包 | [报告](./mezz__JustEnoughItems.md) | [卡片](./_卡片/mezz__JustEnoughItems.md) |
| [tr7zw/3d-skin-layers](https://github.com/tr7zw/3d-skin-layers) | 3D Skin Layers | 2包 | [报告](./tr7zw__3d-skin-layers.md) | [卡片](./_卡片/tr7zw__3d-skin-layers.md) |
| [PepperCode1/Continuity](https://github.com/PepperCode1/Continuity) | Continuity | 1包 | [报告](./PepperCode1__Continuity.md) | [卡片](./_卡片/PepperCode1__Continuity.md) |
| [henkelmax/simple-voice-chat](https://github.com/henkelmax/simple-voice-chat) | Simple Voice Chat | 1包 | [报告](./henkelmax__simple-voice-chat.md) | [卡片](./_卡片/henkelmax__simple-voice-chat.md) |
| [Snownee/Jade](https://github.com/Snownee/Jade) | Jade 🔍 | 4包 | [报告](./Snownee__Jade.md) | [卡片](./_卡片/Snownee__Jade.md) |
| [Keksuccino/FancyMenu](https://github.com/Keksuccino/FancyMenu) | FancyMenu | 3包 | [报告](./Keksuccino__FancyMenu.md) | [卡片](./_卡片/Keksuccino__FancyMenu.md) |
| [YaLTeR/MouseTweaks](https://github.com/YaLTeR/MouseTweaks) | Mouse Tweaks | 3包 | [报告](./YaLTeR__MouseTweaks.md) | [卡片](./_卡片/YaLTeR__MouseTweaks.md) |
| [Aizistral-Studios/No-Chat-Reports](https://github.com/Aizistral-Studios/No-Chat-Reports) | No Chat Reports | 2包 | [报告](./Aizistral-Studios__No-Chat-Reports.md) | [卡片](./_卡片/Aizistral-Studios__No-Chat-Reports.md) |
| [henkelmax/sound-physics-remastered](https://github.com/henkelmax/sound-physics-remastered) | Sound Physics Remastered | 2包 | [报告](./henkelmax__sound-physics-remastered.md) | [卡片](./_卡片/henkelmax__sound-physics-remastered.md) |
| [dzwdz/chat_heads](https://github.com/dzwdz/chat_heads) | Chat Heads | 1包 | [报告](./dzwdz__chat_heads.md) | [卡片](./_卡片/dzwdz__chat_heads.md) |
| [jaredlll08/Controlling](https://github.com/jaredlll08/Controlling) | [键位冲突显示] Controlling-forge-1.20.1-12.0.2 | 4包 | [报告](./jaredlll08__Controlling.md) | [卡片](./_卡片/jaredlll08__Controlling.md) |
| [CreativeMD/AmbientSounds](https://github.com/CreativeMD/AmbientSounds) | AmbientSounds | 2包 | [报告](./CreativeMD__AmbientSounds.md) | [卡片](./_卡片/CreativeMD__AmbientSounds.md) |
| [TreyRuffy/BetterF3](https://github.com/TreyRuffy/BetterF3) | BetterF3 | 2包 | [报告](./TreyRuffy__BetterF3.md) | [卡片](./_卡片/TreyRuffy__BetterF3.md) |
| [illusivesoulworks/cherishedworlds](https://github.com/illusivesoulworks/cherishedworlds) | Cherished Worlds | 1包 | [报告](./illusivesoulworks__cherishedworlds.md) | [卡片](./_卡片/illusivesoulworks__cherishedworlds.md) |
| [way2muchnoise/BetterAdvancements](https://github.com/way2muchnoise/BetterAdvancements) | Better Advancements | 3包 | [报告](./way2muchnoise__BetterAdvancements.md) | [卡片](./_卡片/way2muchnoise__BetterAdvancements.md) |
| [Tschipp/CarryOn](https://github.com/Tschipp/CarryOn) | Carry On | 2包 | [报告](./Tschipp__CarryOn.md) | [卡片](./_卡片/Tschipp__CarryOn.md) |
| [Fuzss/visualworkbench](https://github.com/Fuzss/visualworkbench) | Visual Workbench | 2包 | [报告](./Fuzss__visualworkbench.md) | [卡片](./_卡片/Fuzss__visualworkbench.md) |
| [TwelveIterations/NetherPortalFix](https://github.com/TwelveIterations/NetherPortalFix) | NetherPortalFix | 2包 | [报告](./TwelveIterations__NetherPortalFix.md) | [卡片](./_卡片/TwelveIterations__NetherPortalFix.md) |
| [xfl03/MCCustomSkinLoader](https://github.com/xfl03/MCCustomSkinLoader) | CustomSkinLoader | 2包 | [报告](./xfl03__MCCustomSkinLoader.md) | [卡片](./_卡片/xfl03__MCCustomSkinLoader.md) |
| [Keksuccino/Drippy-Loading-Screen](https://github.com/Keksuccino/Drippy-Loading-Screen) | Drippy Loading Screen | 2包 | [报告](./Keksuccino__Drippy-Loading-Screen.md) | [卡片](./_卡片/Keksuccino__Drippy-Loading-Screen.md) |
| [BloCamLimb/ModernUI-MC](https://github.com/BloCamLimb/ModernUI-MC) | Modern UI | 2包 | [报告](./BloCamLimb__ModernUI-MC.md) | [卡片](./_卡片/BloCamLimb__ModernUI-MC.md) |
| [CreativeMD/EnhancedVisuals](https://github.com/CreativeMD/EnhancedVisuals) | EnhancedVisuals | 1包 | [报告](./CreativeMD__EnhancedVisuals.md) | [卡片](./_卡片/CreativeMD__EnhancedVisuals.md) |
| [AHilyard/Highlighter](https://github.com/AHilyard/Highlighter) | Item Highlighter | 2包 | [报告](./AHilyard__Highlighter.md) | [卡片](./_卡片/AHilyard__Highlighter.md) |
| [Fuzss/pickupnotifier](https://github.com/Fuzss/pickupnotifier) | Pick Up Notifier | 2包 | [报告](./Fuzss__pickupnotifier.md) | [卡片](./_卡片/Fuzss__pickupnotifier.md) |
| [Theoness1/EatingAnimation](https://github.com/Theoness1/EatingAnimation) | Eating Animation | 1包 | [报告](./Theoness1__EatingAnimation.md) | [卡片](./_卡片/Theoness1__EatingAnimation.md) |
| [mortuusars/Exposure](https://github.com/mortuusars/Exposure) | Exposure | 3包 | [报告](./mortuusars__Exposure.md) | [卡片](./_卡片/mortuusars__Exposure.md) |
| [reserveword/IMBlocker](https://github.com/reserveword/IMBlocker) | IMBlocker | 3包 | [报告](./reserveword__IMBlocker.md) | [卡片](./_卡片/reserveword__IMBlocker.md) |
| [Motschen/Blur](https://github.com/Motschen/Blur) | Blur+ | 1包 | [报告](./Motschen__Blur.md) | [卡片](./_卡片/Motschen__Blur.md) |
| [EngineHub/WorldEdit](https://github.com/EngineHub/WorldEdit) | WorldEdit | 1包 | [报告](./EngineHub__WorldEdit.md) | [卡片](./_卡片/EngineHub__WorldEdit.md) |
| [YUNG-GANG/Paxi](https://github.com/YUNG-GANG/Paxi) | Paxi | 1包 | [报告](./YUNG-GANG__Paxi.md) | [卡片](./_卡片/YUNG-GANG__Paxi.md) |
| [AHilyard/LegendaryTooltips](https://github.com/AHilyard/LegendaryTooltips) | Legendary Tooltips | 1包 | [报告](./AHilyard__LegendaryTooltips.md) | [卡片](./_卡片/AHilyard__LegendaryTooltips.md) |
| [KosmX/emotes](https://github.com/KosmX/emotes) | Emotecraft | 1包 | [报告](./KosmX__emotes.md) | [卡片](./_卡片/KosmX__emotes.md) |
| [bl4ckscor3/Sit](https://github.com/bl4ckscor3/Sit) | Sit | 1包 | [报告](./bl4ckscor3__Sit.md) | [卡片](./_卡片/bl4ckscor3__Sit.md) |
| [DragonsPlusMinecraft/VisualityReforged](https://github.com/DragonsPlusMinecraft/VisualityReforged) | Visuality: Reforged | 1包 | [报告](./DragonsPlusMinecraft__VisualityReforged.md) | [卡片](./_卡片/DragonsPlusMinecraft__VisualityReforged.md) |
| [TwelveIterations/ForgivingVoid](https://github.com/TwelveIterations/ForgivingVoid) | Forgiving Void | 1包 | [报告](./TwelveIterations__ForgivingVoid.md) | [卡片](./_卡片/TwelveIterations__ForgivingVoid.md) |
| [TartaricAcid/NetMusic](https://github.com/TartaricAcid/NetMusic) | Net Music | 2包 | [报告](./TartaricAcid__NetMusic.md) | [卡片](./_卡片/TartaricAcid__NetMusic.md) |
| [mortuusars/ExposurePolaroid](https://github.com/mortuusars/ExposurePolaroid) | Exposure: Polaroid | 1包 | [报告](./mortuusars__ExposurePolaroid.md) | [卡片](./_卡片/mortuusars__ExposurePolaroid.md) |
| [sguest/jei-multiblocks](https://github.com/sguest/jei-multiblocks) | Just Enough Immersive Multiblocks | 1包 | [报告](./sguest__jei-multiblocks.md) | [卡片](./_卡片/sguest__jei-multiblocks.md) |
| [Snownee/JadeAddons](https://github.com/Snownee/JadeAddons) | Jade Addons (Neo/Forge) | 1包 | [报告](./Snownee__JadeAddons.md) | [卡片](./_卡片/Snownee__JadeAddons.md) |
| [Suel-ki/FoodEffectTooltips-Forge](https://github.com/Suel-ki/FoodEffectTooltips-Forge) | Food Effect Tooltips (Forge) | 1包 | — | [卡片](./_卡片/Suel-ki__FoodEffectTooltips-Forge.md) |
| [Xiaoyu-2009/visual_recipe_editor](https://github.com/Xiaoyu-2009/visual_recipe_editor) | Workstation Recipe Exporter | 1包 | — | [卡片](./_卡片/Xiaoyu-2009__visual_recipe_editor.md) |
| [villainous-j/toolbar-sounds](https://github.com/villainous-j/toolbar-sounds) | Toolbar Sounds | 1包 | — | [卡片](./_卡片/villainous-j__toolbar-sounds.md) |
| [zbx1425/WorldEditCUI-Arch](https://github.com/zbx1425/WorldEditCUI-Arch) | WorldEdit CUI (Unofficial Forge Port) | 1包 | — | [卡片](./_卡片/zbx1425__WorldEditCUI-Arch.md) |
| [leon-o/iris-veil-compat](https://github.com/leon-o/iris-veil-compat) | Iris Veil Compat | 1包 | — | [卡片](./_卡片/leon-o__iris-veil-compat.md) |
| [Fuzss/configureddefaults](https://github.com/Fuzss/configureddefaults) | Configured Defaults | 1包 | — | [卡片](./_卡片/Fuzss__configureddefaults.md) |
| [CancriRecoleta/NewVisualKebing](https://github.com/CancriRecoleta/NewVisualKebing) | New Visual Keybing | 1包 | — | [卡片](./_卡片/CancriRecoleta__NewVisualKebing.md) |
| [maDU59/FasterIrisShadowMapper](https://github.com/maDU59/FasterIrisShadowMapper) | Faster Iris Shadow Mapper [FISM] | 1包 | — | [卡片](./_卡片/maDU59__FasterIrisShadowMapper.md) |
| [MrCrayfish/Configured](https://github.com/MrCrayfish/Configured) | a/[配置界面] configured-neoforge-1.21.1-2.6. | 3包 | — | [卡片](./_卡片/MrCrayfish__Configured.md) |
| [Mrbysco/JustEnoughProfessions](https://github.com/Mrbysco/JustEnoughProfessions) | a/[JEI工作方块] JustEnoughProfessions-neofor | 2包 | — | [卡片](./_卡片/Mrbysco__JustEnoughProfessions.md) |
| [TeamJM/journeymap](https://github.com/TeamJM/journeymap) | JourneyMap | 1包 | — | [卡片](./_卡片/TeamJM__journeymap.md) |

## 其他 / 综合（241）

| 仓库 | 项目 | 包 | 深度报告 | 卡片 |
|---|---|---|---|---|
| [blackd/Inventory-Profiles](https://github.com/blackd/Inventory-Profiles) | Inventory Profiles Next | 1包 | [报告](./blackd__Inventory-Profiles.md) | [卡片](./_卡片/blackd__Inventory-Profiles.md) |
| [Darkhax-Minecraft/Enchantment-Descriptions](https://github.com/Darkhax-Minecraft/Enchantment-Descriptions) | Enchantment Descriptions | 4包 | [报告](./Darkhax-Minecraft__Enchantment-Descriptions.md) | [卡片](./_卡片/Darkhax-Minecraft__Enchantment-Descriptions.md) |
| [VazkiiMods/Patchouli](https://github.com/VazkiiMods/Patchouli) | Patchouli | 4包 | [报告](./VazkiiMods__Patchouli.md) | [卡片](./_卡片/VazkiiMods__Patchouli.md) |
| [blackd/libIPN](https://github.com/blackd/libIPN) | libIPN | 2包 | [报告](./blackd__libIPN.md) | [卡片](./_卡片/blackd__libIPN.md) |
| [Sinytra/ForgifiedFabricAPI](https://github.com/Sinytra/ForgifiedFabricAPI) | forgified-fabric-api-0.116.15+2.3.4+1.21 | 2包 | [报告](./Sinytra__ForgifiedFabricAPI.md) | [卡片](./_卡片/Sinytra__ForgifiedFabricAPI.md) |
| [MehVahdJukaar/Supplementaries](https://github.com/MehVahdJukaar/Supplementaries) | Supplementaries | 2包 | [报告](./MehVahdJukaar__Supplementaries.md) | [卡片](./_卡片/MehVahdJukaar__Supplementaries.md) |
| [EuphoriaPatches/EuphoriaPatcher](https://github.com/EuphoriaPatches/EuphoriaPatcher) | Euphoria Patches | 2包 | [报告](./EuphoriaPatches__EuphoriaPatcher.md) | [卡片](./_卡片/EuphoriaPatches__EuphoriaPatcher.md) |
| [terrarium-earth/Handcrafted](https://github.com/terrarium-earth/Handcrafted) | Handcrafted | 2包 | [报告](./terrarium-earth__Handcrafted.md) | [卡片](./_卡片/terrarium-earth__Handcrafted.md) |
| [TwelveIterations/Waystones](https://github.com/TwelveIterations/Waystones) | Waystones | 2包 | [报告](./TwelveIterations__Waystones.md) | [卡片](./_卡片/TwelveIterations__Waystones.md) |
| [Sinytra/Connector](https://github.com/Sinytra/Connector) | 信雅互联connector-2.0.0-beta.17+1.21.1-full. | 2包 | [报告](./Sinytra__Connector.md) | [卡片](./_卡片/Sinytra__Connector.md) |
| [illusivesoulworks/polymorph](https://github.com/illusivesoulworks/polymorph) | Polymorph | 4包 | [报告](./illusivesoulworks__polymorph.md) | [卡片](./_卡片/illusivesoulworks__polymorph.md) |
| [noobanidus/lootr](https://github.com/noobanidus/lootr) | Lootr (Forge & NeoForge) | 4包 | [报告](./noobanidus__lootr.md) | [卡片](./_卡片/noobanidus__lootr.md) |
| [KubeJS-Mods/KubeJS](https://github.com/KubeJS-Mods/KubeJS) | kubejs-neoforge-2101.7.2-build.368.jar | 4包 | [报告](./KubeJS-Mods__KubeJS.md) | [卡片](./_卡片/KubeJS-Mods__KubeJS.md) |
| [Tiviacz1337/Travelers-Backpack](https://github.com/Tiviacz1337/Travelers-Backpack) | Traveler's Backpack | 1包 | [报告](./Tiviacz1337__Travelers-Backpack.md) | [卡片](./_卡片/Tiviacz1337__Travelers-Backpack.md) |
| [AHilyard/AdvancementPlaques](https://github.com/AHilyard/AdvancementPlaques) | Advancement Plaques | 1包 | [报告](./AHilyard__AdvancementPlaques.md) | [卡片](./_卡片/AHilyard__AdvancementPlaques.md) |
| [xfl03/I18nUpdateMod3](https://github.com/xfl03/I18nUpdateMod3) | I18nUpdateMod | 2包 | [报告](./xfl03__I18nUpdateMod3.md) | [卡片](./_卡片/xfl03__I18nUpdateMod3.md) |
| [YesSteveModel/YSM-Wiki-Issues](https://github.com/YesSteveModel/YSM-Wiki-Issues) | Yes Steve Model | 1包 | [报告](./YesSteveModel__YSM-Wiki-Issues.md) | [卡片](./_卡片/YesSteveModel__YSM-Wiki-Issues.md) |
| [Towdium/JustEnoughCharacters](https://github.com/Towdium/JustEnoughCharacters) | JustEnoughCharacters | 3包 | [报告](./Towdium__JustEnoughCharacters.md) | [卡片](./_卡片/Towdium__JustEnoughCharacters.md) |
| [illusivesoulworks/elytraslot](https://github.com/illusivesoulworks/elytraslot) | Elytra Slot | 1包 | [报告](./illusivesoulworks__elytraslot.md) | [卡片](./_卡片/illusivesoulworks__elytraslot.md) |
| [MehVahdJukaar/DuMmmMmmy](https://github.com/MehVahdJukaar/DuMmmMmmy) | MmmMmmMmmMmm (Target Dummy) | 2包 | [报告](./MehVahdJukaar__DuMmmMmmy.md) | [卡片](./_卡片/MehVahdJukaar__DuMmmMmmy.md) |
| [sketchmacaw/Fences](https://github.com/sketchmacaw/Fences) | Macaw's Fences and Walls | 3包 | [报告](./sketchmacaw__Fences.md) | [卡片](./_卡片/sketchmacaw__Fences.md) |
| [Serilum/Starter-Kit](https://github.com/Serilum/Starter-Kit) | Starter Kit | 1包 | [报告](./Serilum__Starter-Kit.md) | [卡片](./_卡片/Serilum__Starter-Kit.md) |
| [decce6/Ixeris](https://github.com/decce6/Ixeris) | Ixeris | 2包 | [报告](./decce6__Ixeris.md) | [卡片](./_卡片/decce6__Ixeris.md) |
| [YUNG-GANG/Travelers-Titles](https://github.com/YUNG-GANG/Travelers-Titles) | Traveler's Titles | 1包 | [报告](./YUNG-GANG__Travelers-Titles.md) | [卡片](./_卡片/YUNG-GANG__Travelers-Titles.md) |
| [sketchmacaw/Bridges](https://github.com/sketchmacaw/Bridges) | Macaw's Bridges | 3包 | [报告](./sketchmacaw__Bridges.md) | [卡片](./_卡片/sketchmacaw__Bridges.md) |
| [illusivesoulworks/charmofundying](https://github.com/illusivesoulworks/charmofundying) | Charm of Undying | 1包 | [报告](./illusivesoulworks__charmofundying.md) | [卡片](./_卡片/illusivesoulworks__charmofundying.md) |
| [Luke100000/ImmersiveMelodies](https://github.com/Luke100000/ImmersiveMelodies) | Immersive Melodies | 2包 | [报告](./Luke100000__ImmersiveMelodies.md) | [卡片](./_卡片/Luke100000__ImmersiveMelodies.md) |
| [ItsBlackGear/Platform](https://github.com/ItsBlackGear/Platform) | Platform | 1包 | [报告](./ItsBlackGear__Platform.md) | [卡片](./_卡片/ItsBlackGear__Platform.md) |
| [Minenash/Enhanced-Attack-Indicator](https://github.com/Minenash/Enhanced-Attack-Indicator) | Enhanced Attack Indicator | 1包 | [报告](./Minenash__Enhanced-Attack-Indicator.md) | [卡片](./_卡片/Minenash__Enhanced-Attack-Indicator.md) |
| [TJT01/GlobalServerConfig](https://github.com/TJT01/GlobalServerConfig) | Global Server Config | 1包 | [报告](./TJT01__GlobalServerConfig.md) | [卡片](./_卡片/TJT01__GlobalServerConfig.md) |
| [CircuitLord/AdventureRedefined](https://github.com/CircuitLord/AdventureRedefined) | Reactive Music | 1包 | [报告](./CircuitLord__AdventureRedefined.md) | [卡片](./_卡片/CircuitLord__AdventureRedefined.md) |
| [way2muchnoise/JustEnoughResources](https://github.com/way2muchnoise/JustEnoughResources) | Just Enough Resources (JER) | 1包 | [报告](./way2muchnoise__JustEnoughResources.md) | [卡片](./_卡片/way2muchnoise__JustEnoughResources.md) |
| [fonnymunkey/SimpleHats](https://github.com/fonnymunkey/SimpleHats) | Simple Hats | 1包 | [报告](./fonnymunkey__SimpleHats.md) | [卡片](./_卡片/fonnymunkey__SimpleHats.md) |
| [Kitteh6660/DramaticDoors](https://github.com/Kitteh6660/DramaticDoors) | Dramatic Doors | 1包 | [报告](./Kitteh6660__DramaticDoors.md) | [卡片](./_卡片/Kitteh6660__DramaticDoors.md) |
| [Cheaterpaul/fallingleaves](https://github.com/Cheaterpaul/fallingleaves) | Falling Leaves (NeoForge/Forge) | 1包 | [报告](./Cheaterpaul__fallingleaves.md) | [卡片](./_卡片/Cheaterpaul__fallingleaves.md) |
| [samedifferent/Ecologics](https://github.com/samedifferent/Ecologics) | Ecologics | 1包 | [报告](./samedifferent__Ecologics.md) | [卡片](./_卡片/samedifferent__Ecologics.md) |
| [FoundationGames/Automobility](https://github.com/FoundationGames/Automobility) | Automobility | 1包 | [报告](./FoundationGames__Automobility.md) | [卡片](./_卡片/FoundationGames__Automobility.md) |
| [sketchmacaw/Paths-Pavings](https://github.com/sketchmacaw/Paths-Pavings) | Macaw's Paths and Pavings | 2包 | [报告](./sketchmacaw__Paths-Pavings.md) | [卡片](./_卡片/sketchmacaw__Paths-Pavings.md) |
| [Terrails/colorful-hearts](https://github.com/Terrails/colorful-hearts) | Colorful Hearts | 3包 | [报告](./Terrails__colorful-hearts.md) | [卡片](./_卡片/Terrails__colorful-hearts.md) |
| [decce6/Gnetum](https://github.com/decce6/Gnetum) | Gnetum | 2包 | [报告](./decce6__Gnetum.md) | [卡片](./_卡片/decce6__Gnetum.md) |
| [Minecraft-LightLand/L2Complements](https://github.com/Minecraft-LightLand/L2Complements) | l2complements-3.1.3.jar | 2包 | [报告](./Minecraft-LightLand__L2Complements.md) | [卡片](./_卡片/Minecraft-LightLand__L2Complements.md) |
| [Mari023/AE2WirelessTerminalLibrary](https://github.com/Mari023/AE2WirelessTerminalLibrary) | Applied Energistics 2 Wireless Terminals | 2包 | [报告](./Mari023__AE2WirelessTerminalLibrary.md) | [卡片](./_卡片/Mari023__AE2WirelessTerminalLibrary.md) |
| [Minecraft-LightLand/L2Hostility](https://github.com/Minecraft-LightLand/L2Hostility) | l2hostility-3.0.18.jar | 2包 | [报告](./Minecraft-LightLand__L2Hostility.md) | [卡片](./_卡片/Minecraft-LightLand__L2Hostility.md) |
| [PoppyBlossom/Railway-1.21.1](https://github.com/PoppyBlossom/Railway-1.21.1) | Steam 'n' Rails Neoforge | 2包 | [报告](./PoppyBlossom__Railway-1.21.1.md) | [卡片](./_卡片/PoppyBlossom__Railway-1.21.1.md) |
| [Mars-The-Planet/More-Music-Discs](https://github.com/Mars-The-Planet/More-Music-Discs) | More Music Discs | 1包 | [报告](./Mars-The-Planet__More-Music-Discs.md) | [卡片](./_卡片/Mars-The-Planet__More-Music-Discs.md) |
| [decce6/AsyncLogger](https://github.com/decce6/AsyncLogger) | Async Logger | 2包 | [报告](./decce6__AsyncLogger.md) | [卡片](./_卡片/decce6__AsyncLogger.md) |
| [TeamMetallurgy/Aquaculture](https://github.com/TeamMetallurgy/Aquaculture) | Aquaculture 2 | 2包 | [报告](./TeamMetallurgy__Aquaculture.md) | [卡片](./_卡片/TeamMetallurgy__Aquaculture.md) |
| [Minecraft-LightLand/L2Archery](https://github.com/Minecraft-LightLand/L2Archery) | L2 Archery | 2包 | [报告](./Minecraft-LightLand__L2Archery.md) | [卡片](./_卡片/Minecraft-LightLand__L2Archery.md) |
| [Prunoideae/ProbeJS](https://github.com/Prunoideae/ProbeJS) | ProbeJS | 2包 | [报告](./Prunoideae__ProbeJS.md) | [卡片](./_卡片/Prunoideae__ProbeJS.md) |
| [BlakeBr0/MysticalAgradditions](https://github.com/BlakeBr0/MysticalAgradditions) | Mystical Agradditions | 2包 | [报告](./BlakeBr0__MysticalAgradditions.md) | [卡片](./_卡片/BlakeBr0__MysticalAgradditions.md) |
| [Minecraft-LightLand/L2Weaponry](https://github.com/Minecraft-LightLand/L2Weaponry) | L2 Weaponry | 1包 | [报告](./Minecraft-LightLand__L2Weaponry.md) | [卡片](./_卡片/Minecraft-LightLand__L2Weaponry.md) |
| [starforcraft/Botany-Pots-Tiers](https://github.com/starforcraft/Botany-Pots-Tiers) | Botany Pots Tiers | 1包 | [报告](./starforcraft__Botany-Pots-Tiers.md) | [卡片](./_卡片/starforcraft__Botany-Pots-Tiers.md) |
| [Serilum/Starter-Structure](https://github.com/Serilum/Starter-Structure) | Starter Structure | 1包 | [报告](./Serilum__Starter-Structure.md) | [卡片](./_卡片/Serilum__Starter-Structure.md) |
| [Hunter19823/kubejsoffline](https://github.com/Hunter19823/kubejsoffline) | KubeJS Offline | 1包 | [报告](./Hunter19823__kubejsoffline.md) | [卡片](./_卡片/Hunter19823__kubejsoffline.md) |
| [mortuusars/SootyChimneys](https://github.com/mortuusars/SootyChimneys) | Sooty Chimneys | 1包 | [报告](./mortuusars__SootyChimneys.md) | [卡片](./_卡片/mortuusars__SootyChimneys.md) |
| [Alex-Hashtag/LegendarySurvivalOverhaul](https://github.com/Alex-Hashtag/LegendarySurvivalOverhaul) | Legendary Survival Overhaul | 1包 | [报告](./Alex-Hashtag__LegendarySurvivalOverhaul.md) | [卡片](./_卡片/Alex-Hashtag__LegendarySurvivalOverhaul.md) |
| [MrMelon54/draggable_lists](https://github.com/MrMelon54/draggable_lists) | Draggable Lists | 1包 | — | [卡片](./_卡片/MrMelon54__draggable_lists.md) |
| [Fuzss/mutantmonsters](https://github.com/Fuzss/mutantmonsters) | Mutant Monsters | 1包 | — | [卡片](./_卡片/Fuzss__mutantmonsters.md) |
| [teamfusion/rottencreatures](https://github.com/teamfusion/rottencreatures) | Rotten Creatures | 1包 | — | [卡片](./_卡片/teamfusion__rottencreatures.md) |
| [1foxy2/neo_mod_menu](https://github.com/1foxy2/neo_mod_menu) | Better ModList | 1包 | — | [卡片](./_卡片/1foxy2__neo_mod_menu.md) |
| [Lightman314/LightmansCurrency](https://github.com/Lightman314/LightmansCurrency) | Lightman's Currency | 1包 | — | [卡片](./_卡片/Lightman314__LightmansCurrency.md) |
| [TheCBProject/CodeChickenLib](https://github.com/TheCBProject/CodeChickenLib) | CodeChicken Lib | 1包 | — | [卡片](./_卡片/TheCBProject__CodeChickenLib.md) |
| [Serilum/Inventory-Totem](https://github.com/Serilum/Inventory-Totem) | Inventory Totem | 1包 | — | [卡片](./_卡片/Serilum__Inventory-Totem.md) |
| [juancarloscp52/spyglass-improvements](https://github.com/juancarloscp52/spyglass-improvements) | Spyglass Improvements | 1包 | — | [卡片](./_卡片/juancarloscp52__spyglass-improvements.md) |
| [alRex-U/ParCool](https://github.com/alRex-U/ParCool) | ParCool! | 1包 | — | [卡片](./_卡片/alRex-U__ParCool.md) |
| [LopyMine/Inventory-Particles](https://github.com/LopyMine/Inventory-Particles) | Inventory Particles | 1包 | — | [卡片](./_卡片/LopyMine__Inventory-Particles.md) |
| [CreativeMD/ItemPhysic](https://github.com/CreativeMD/ItemPhysic) | ItemPhysic | 1包 | — | [卡片](./_卡片/CreativeMD__ItemPhysic.md) |
| [Tictim/Paraglider](https://github.com/Tictim/Paraglider) | Paragliders | 1包 | — | [卡片](./_卡片/Tictim__Paraglider.md) |
| [progwml6/ironchest](https://github.com/progwml6/ironchest) | Iron Chests | 1包 | — | [卡片](./_卡片/progwml6__ironchest.md) |
| [LopyMine/MossyLib](https://github.com/LopyMine/MossyLib) | MossyLib | 1包 | — | [卡片](./_卡片/LopyMine__MossyLib.md) |
| [CoFH/CoFHCore](https://github.com/CoFH/CoFHCore) | CoFH Core | 1包 | — | [卡片](./_卡片/CoFH__CoFHCore.md) |
| [VsnGamer/ElevatorMod](https://github.com/VsnGamer/ElevatorMod) | ElevatorMod | 1包 | — | [卡片](./_卡片/VsnGamer__ElevatorMod.md) |
| [skyecodes/IBE-Editor](https://github.com/skyecodes/IBE-Editor) | IBE Editor | 1包 | — | [卡片](./_卡片/skyecodes__IBE-Editor.md) |
| [Fuzss/universalenchants](https://github.com/Fuzss/universalenchants) | Universal Enchants | 1包 | — | [卡片](./_卡片/Fuzss__universalenchants.md) |
| [MagicHarp/confluence](https://github.com/MagicHarp/confluence) | Terra Curio | 1包 | [报告](./MagicHarp__confluence.md) | [卡片](./_卡片/MagicHarp__confluence.md) |
| [DrexHD/quick-pack](https://github.com/DrexHD/quick-pack) | quick pack | 1包 | — | [卡片](./_卡片/DrexHD__quick-pack.md) |
| [ZhuRuoLing/startup-time](https://github.com/ZhuRuoLing/startup-time) | Startup Time | 1包 | — | [卡片](./_卡片/ZhuRuoLing__startup-time.md) |
| [Insane96/InsaneLib](https://github.com/Insane96/InsaneLib) | InsaneLib | 1包 | — | [卡片](./_卡片/Insane96__InsaneLib.md) |
| [Low-Drag-MC/Photon](https://github.com/Low-Drag-MC/Photon) | Photon Editor | 1包 | — | [卡片](./_卡片/Low-Drag-MC__Photon.md) |
| [btwonion/KotlinLangForge](https://github.com/btwonion/KotlinLangForge) | KotlinLangForge | 1包 | — | [卡片](./_卡片/btwonion__KotlinLangForge.md) |
| [afoxxvi/AsteorBarMod](https://github.com/afoxxvi/AsteorBarMod) | AsteorBar | 1包 | — | [卡片](./_卡片/afoxxvi__AsteorBarMod.md) |
| [Keksuccino/ModernWorldCreation](https://github.com/Keksuccino/ModernWorldCreation) | Modern World Creation | 1包 | — | [卡片](./_卡片/Keksuccino__ModernWorldCreation.md) |
| [iSeeEthan/voxy_worldgen_v2](https://github.com/iSeeEthan/voxy_worldgen_v2) | Voxy WorldGen | 1包 | — | [卡片](./_卡片/iSeeEthan__voxy_worldgen_v2.md) |
| [XiaoXianHW/EasyLAN](https://github.com/XiaoXianHW/EasyLAN) | EasyLAN | 1包 | — | [卡片](./_卡片/XiaoXianHW__EasyLAN.md) |
| [SettingDust/MoreEnchantmentInfo](https://github.com/SettingDust/MoreEnchantmentInfo) | More Enchantment Info | 1包 | — | [卡片](./_卡片/SettingDust__MoreEnchantmentInfo.md) |
| [Insane96/EnhancedAI](https://github.com/Insane96/EnhancedAI) | Enhanced AI | 1包 | — | [卡片](./_卡片/Insane96__EnhancedAI.md) |
| [JeremySeq/DamageIndicators](https://github.com/JeremySeq/DamageIndicators) | JeremySeq's Damage Indicator | 1包 | — | [卡片](./_卡片/JeremySeq__DamageIndicators.md) |
| [infernalstudios/Celestial-Configuration](https://github.com/infernalstudios/Celestial-Configuration) | Sun and Moon Celestial Configuration | 1包 | — | [卡片](./_卡片/infernalstudios__Celestial-Configuration.md) |
| [nonamecrackers2/ender-trigon](https://github.com/nonamecrackers2/ender-trigon) | Ender Trigon | 1包 | — | [卡片](./_卡片/nonamecrackers2__ender-trigon.md) |
| [bonsaistudi0s/Golem-Overhaul](https://github.com/bonsaistudi0s/Golem-Overhaul) | Golem Overhaul | 1包 | — | [卡片](./_卡片/bonsaistudi0s__Golem-Overhaul.md) |
| [yezhiyi9670/clear-void](https://github.com/yezhiyi9670/clear-void) | Clear Void | 1包 | — | [卡片](./_卡片/yezhiyi9670__clear-void.md) |
| [SettingDust/preloading-tricks](https://github.com/SettingDust/preloading-tricks) | Preloading Tricks | 1包 | — | [卡片](./_卡片/SettingDust__preloading-tricks.md) |
| [TUsama/Loot-Beams-Refork](https://github.com/TUsama/Loot-Beams-Refork) | Loot Beams: Refork | 1包 | — | [卡片](./_卡片/TUsama__Loot-Beams-Refork.md) |
| [jinqinxixi/Trinkets-and-Baubles-Forge-1.20.1](https://github.com/jinqinxixi/Trinkets-and-Baubles-Forge-1.20.1) | Trinkets and Baubles Reforked | 1包 | [报告](./jinqinxixi__Trinkets-and-Baubles-Forge-1.20.1.md) | [卡片](./_卡片/jinqinxixi__Trinkets-and-Baubles-Forge-1.20.1.md) |
| [dhyces/trimmed](https://github.com/dhyces/trimmed) | Trimmed | 2包 | — | [卡片](./_卡片/dhyces__trimmed.md) |
| [iMoonDay/Soulbound](https://github.com/iMoonDay/Soulbound) | Soulbound Enchantment | 1包 | — | [卡片](./_卡片/iMoonDay__Soulbound.md) |
| [Flemmli97/Flan](https://github.com/Flemmli97/Flan) | Flan | 1包 | — | [卡片](./_卡片/Flemmli97__Flan.md) |
| [DenisMasterHerobrine/TheAfterdark](https://github.com/DenisMasterHerobrine/TheAfterdark) | The Afterdark | 1包 | — | [卡片](./_卡片/DenisMasterHerobrine__TheAfterdark.md) |
| [Unixkitty/timecontrol](https://github.com/Unixkitty/timecontrol) | Time Control | 1包 | — | [卡片](./_卡片/Unixkitty__timecontrol.md) |
| [Povstalec/StellarView](https://github.com/Povstalec/StellarView) | Stellar View | 1包 | — | [卡片](./_卡片/Povstalec__StellarView.md) |
| [TUsama/NirvanaLib](https://github.com/TUsama/NirvanaLib) | Nirvana Library | 1包 | — | [卡片](./_卡片/TUsama__NirvanaLib.md) |
| [pitbox46/ItemBlacklist](https://github.com/pitbox46/ItemBlacklist) | Item Banning | 1包 | — | [卡片](./_卡片/pitbox46__ItemBlacklist.md) |
| [MeherBenSalem/Jauml](https://github.com/MeherBenSalem/Jauml) | Jauml | 1包 | — | [卡片](./_卡片/MeherBenSalem__Jauml.md) |
| [Ineffa/Truly-Treasures](https://github.com/Ineffa/Truly-Treasures) | Truly Treasures | 1包 | — | [卡片](./_卡片/Ineffa__Truly-Treasures.md) |
| [EnderTurret/PatchedMod](https://github.com/EnderTurret/PatchedMod) | Patched | 1包 | — | [卡片](./_卡片/EnderTurret__PatchedMod.md) |
| [GLDYM/ConstructionWand-KOTS](https://github.com/GLDYM/ConstructionWand-KOTS) | Construction Wand - KOTS | 2包 | — | [卡片](./_卡片/GLDYM__ConstructionWand-KOTS.md) |
| [Auviotre/Enigmatic-Legacy-Plus](https://github.com/Auviotre/Enigmatic-Legacy-Plus) | Enigmatic Legacy+ | 1包 | — | [卡片](./_卡片/Auviotre__Enigmatic-Legacy-Plus.md) |
| [Keksuccino/Panoramica](https://github.com/Keksuccino/Panoramica) | Panoramica | 1包 | — | [卡片](./_卡片/Keksuccino__Panoramica.md) |
| [Alvaro842DEV/AsyncLocator-Refined](https://github.com/Alvaro842DEV/AsyncLocator-Refined) | Async Locator Refined | 1包 | — | [卡片](./_卡片/Alvaro842DEV__AsyncLocator-Refined.md) |
| [Low-Drag-MC/KilaGraph](https://github.com/Low-Drag-MC/KilaGraph) | KilaGraph | 1包 | [报告](./Low-Drag-MC__KilaGraph.md) | [卡片](./_卡片/Low-Drag-MC__KilaGraph.md) |
| [klinbee/Diabolical-Islands](https://github.com/klinbee/Diabolical-Islands) | Diabolical Islands | 2包 | — | [卡片](./_卡片/klinbee__Diabolical-Islands.md) |
| [sam-makes-stuff/ping_system](https://github.com/sam-makes-stuff/ping_system) | Ping System | 1包 | — | [卡片](./_卡片/sam-makes-stuff__ping_system.md) |
| [TheFogIOF/AlloySmelter](https://github.com/TheFogIOF/AlloySmelter) | Alloy Smelter | 1包 | — | [卡片](./_卡片/TheFogIOF__AlloySmelter.md) |
| [MoePus/BiomeSpy](https://github.com/MoePus/BiomeSpy) | BiomeSpy | 1包 | — | [卡片](./_卡片/MoePus__BiomeSpy.md) |
| [djefrey/Colorwheel](https://github.com/djefrey/Colorwheel) | Colorwheel | 2包 | — | [卡片](./_卡片/djefrey__Colorwheel.md) |
| [djefrey/Colorwheel-Patcher](https://github.com/djefrey/Colorwheel-Patcher) | Colorwheel Patcher | 2包 | — | [卡片](./_卡片/djefrey__Colorwheel-Patcher.md) |
| [PierreChag/dawnoftimebuilder](https://github.com/PierreChag/dawnoftimebuilder) | Dawn of Time | 1包 | — | [卡片](./_卡片/PierreChag__dawnoftimebuilder.md) |
| [ascpixi/disconnect-packet-fix](https://github.com/ascpixi/disconnect-packet-fix) | Disconnect Packet Fix | 1包 | — | [卡片](./_卡片/ascpixi__disconnect-packet-fix.md) |
| [enjarai/do-a-barrel-roll](https://github.com/enjarai/do-a-barrel-roll) | Do a Barrel Roll | 1包 | — | [卡片](./_卡片/enjarai__do-a-barrel-roll.md) |
| [ZZZank/EfficientHashing](https://github.com/ZZZank/EfficientHashing) | EfficientHashing | 1包 | — | [卡片](./_卡片/ZZZank__EfficientHashing.md) |
| [nanite/Flat-Bedrock](https://github.com/nanite/Flat-Bedrock) | Flat Bedrock | 1包 | — | [卡片](./_卡片/nanite__Flat-Bedrock.md) |
| [remarxk/GUI-Tween](https://github.com/remarxk/GUI-Tween) | GUI Tween | 1包 | — | [卡片](./_卡片/remarxk__GUI-Tween.md) |
| [AlmostReliable/lootjs](https://github.com/AlmostReliable/lootjs) | LootJS: KubeJS Addon | 1包 | — | [卡片](./_卡片/AlmostReliable__lootjs.md) |
| [Craft1x/MedievalBuildingsEnder](https://github.com/Craft1x/MedievalBuildingsEnder) | Medieval Buildings [End Edition] | 1包 | — | [卡片](./_卡片/Craft1x__MedievalBuildingsEnder.md) |
| [TonimatasDEV/PacketFixer](https://github.com/TonimatasDEV/PacketFixer) | Packet Fixer | 1包 | — | [卡片](./_卡片/TonimatasDEV__PacketFixer.md) |
| [Leclowndu93150/Particular](https://github.com/Leclowndu93150/Particular) | Particular ✨ Reforged | 1包 | — | [卡片](./_卡片/Leclowndu93150__Particular.md) |
| [KosmX/fabricPlayerAnimation](https://github.com/KosmX/fabricPlayerAnimation) | playerAnimator | 2包 | — | [卡片](./_卡片/KosmX__fabricPlayerAnimation.md) |
| [starforcraft/Showcase-Item](https://github.com/starforcraft/Showcase-Item) | Showcase Item | 1包 | — | [卡片](./_卡片/starforcraft__Showcase-Item.md) |
| [lucko/spark](https://github.com/lucko/spark) | spark | 2包 | — | [卡片](./_卡片/lucko__spark.md) |
| [Faboslav/it-takes-a-pillage](https://github.com/Faboslav/it-takes-a-pillage) | It Takes a Pillage Continuation | 1包 | — | [卡片](./_卡片/Faboslav__it-takes-a-pillage.md) |
| [Fuzss/tinyskeletons](https://github.com/Fuzss/tinyskeletons) | Tiny Skeletons | 1包 | — | [卡片](./_卡片/Fuzss__tinyskeletons.md) |
| [LocusAzzurro/Ultramarine](https://github.com/LocusAzzurro/Ultramarine) | Ultramarine | 1包 | — | [卡片](./_卡片/LocusAzzurro__Ultramarine.md) |
| [MincraftEinstein/UsefulSlime](https://github.com/MincraftEinstein/UsefulSlime) | Useful Slime | 1包 | — | [卡片](./_卡片/MincraftEinstein__UsefulSlime.md) |
| [sketchmacaw/Trapdoors](https://github.com/sketchmacaw/Trapdoors) | Macaw's Trapdoors | 2包 | — | [卡片](./_卡片/sketchmacaw__Trapdoors.md) |
| [sketchmacaw/MacawsDoors](https://github.com/sketchmacaw/MacawsDoors) | Macaw's Doors | 2包 | — | [卡片](./_卡片/sketchmacaw__MacawsDoors.md) |
| [sketchmacaw/Macaws-Stairs](https://github.com/sketchmacaw/Macaws-Stairs) | Macaw's Stairs | 2包 | — | [卡片](./_卡片/sketchmacaw__Macaws-Stairs.md) |
| [breezeth-CN/OrdertoCook](https://github.com/breezeth-CN/OrdertoCook) | Order to cook下单了！ | 1包 | — | [卡片](./_卡片/breezeth-CN__OrdertoCook.md) |
| [Tower-of-Sighs/AUI](https://github.com/Tower-of-Sighs/AUI) | ApricityUI | 1包 | [报告](./Tower-of-Sighs__AUI.md) | [卡片](./_卡片/Tower-of-Sighs__AUI.md) |
| [ExpensiveKoala/Fishing-Real](https://github.com/ExpensiveKoala/Fishing-Real) | Fishing Real | 1包 | — | [卡片](./_卡片/ExpensiveKoala__Fishing-Real.md) |
| [xianziyu001-stack/End-Remastered-ProMax](https://github.com/xianziyu001-stack/End-Remastered-ProMax) | End Remastered ProMax | 1包 | — | [卡片](./_卡片/xianziyu001-stack__End-Remastered-ProMax.md) |
| [Jack-Bagel/End-Remastered](https://github.com/Jack-Bagel/End-Remastered) | End Remastered | 1包 | — | [卡片](./_卡片/Jack-Bagel__End-Remastered.md) |
| [LeoMinecraftModding/eternal-starlight](https://github.com/LeoMinecraftModding/eternal-starlight) | Eternal Starlight | 2包 | — | [卡片](./_卡片/LeoMinecraftModding__eternal-starlight.md) |
| [Lightning-64/Tide-2](https://github.com/Lightning-64/Tide-2) | Tide 2 | 1包 | — | [卡片](./_卡片/Lightning-64__Tide-2.md) |
| [Scouter456/Nether_Depths_Upgrade](https://github.com/Scouter456/Nether_Depths_Upgrade) | Nether Depths Upgrade | 1包 | — | [卡片](./_卡片/Scouter456__Nether_Depths_Upgrade.md) |
| [CreativeMD/PlayerRevive](https://github.com/CreativeMD/PlayerRevive) | PlayerRevive | 1包 | — | [卡片](./_卡片/CreativeMD__PlayerRevive.md) |
| [ZCRAFT-NPE/Presence-Footsteps-NeoForge](https://github.com/ZCRAFT-NPE/Presence-Footsteps-NeoForge) | Presence Footsteps (NeoForge) | 1包 | — | [卡片](./_卡片/ZCRAFT-NPE__Presence-Footsteps-NeoForge.md) |
| [FOOLSIX/ldip](https://github.com/FOOLSIX/ldip) | Limited Damage Indicator Particle | 1包 | — | [卡片](./_卡片/FOOLSIX__ldip.md) |
| [IAFEnvoy/Jupiter](https://github.com/IAFEnvoy/Jupiter) | Jupiter | 2包 | — | [卡片](./_卡片/IAFEnvoy__Jupiter.md) |
| [Fallen-Breath/fast-ip-ping](https://github.com/Fallen-Breath/fast-ip-ping) | Fast IP Ping | 1包 | — | [卡片](./_卡片/Fallen-Breath__fast-ip-ping.md) |
| [zhenshiz/ViScriptShop](https://github.com/zhenshiz/ViScriptShop) | ViScriptShop | 1包 | — | [卡片](./_卡片/zhenshiz__ViScriptShop.md) |
| [IanMods/SeasonHUD](https://github.com/IanMods/SeasonHUD) | SeasonHud | 1包 | — | [卡片](./_卡片/IanMods__SeasonHUD.md) |
| [WitherRedstone/Fox-Trot-Brew](https://github.com/WitherRedstone/Fox-Trot-Brew) | Fox Trot Brew | 1包 | — | [卡片](./_卡片/WitherRedstone__Fox-Trot-Brew.md) |
| [redtardis12/Tornado-Physics](https://github.com/redtardis12/Tornado-Physics) | Weather Physics (Wind, Sails & Tornadoes | 1包 | — | [卡片](./_卡片/redtardis12__Tornado-Physics.md) |
| [AzureDoom/Log-Begone](https://github.com/AzureDoom/Log-Begone) | Log Begone | 1包 | — | [卡片](./_卡片/AzureDoom__Log-Begone.md) |
| [Richy-Z/ThreatenGL](https://github.com/Richy-Z/ThreatenGL) | ThreatenGL | 1包 | — | [卡片](./_卡片/Richy-Z__ThreatenGL.md) |
| [hotsu0p/Trek-Issues](https://github.com/hotsu0p/Trek-Issues) | Trek | 1包 | — | [卡片](./_卡片/hotsu0p__Trek-Issues.md) |
| [Traverse-Joe/Baubley-Heart-Canisters](https://github.com/Traverse-Joe/Baubley-Heart-Canisters) | Baubley Heart Canisters | 2包 | — | [卡片](./_卡片/Traverse-Joe__Baubley-Heart-Canisters.md) |
| [frcvdt45g6by7hnj8ukm-nh8b7g6vtf5r4de3/FastQuit-Forge](https://github.com/frcvdt45g6by7hnj8ukm-nh8b7g6vtf5r4de3/FastQuit-Forge) | FastQuit-Forge | 1包 | — | [卡片](./_卡片/frcvdt45g6by7hnj8ukm-nh8b7g6vtf5r4de3__FastQuit-Forge.md) |
| [Bivrik/FancyToasts](https://github.com/Bivrik/FancyToasts) | Fancy Toasts | Better Advancements | 1包 | — | [卡片](./_卡片/Bivrik__FancyToasts.md) |
| [Okabintaro/UntitledDuckMod](https://github.com/Okabintaro/UntitledDuckMod) | Untitled Duck Mod | 1包 | — | [卡片](./_卡片/Okabintaro__UntitledDuckMod.md) |
| [maDU59/FancyWorldAnimations](https://github.com/maDU59/FancyWorldAnimations) | Fancy World Animations [FWA] | 1包 | — | [卡片](./_卡片/maDU59__FancyWorldAnimations.md) |
| [ChoiceTheorem/ChoiceTheorem-s-overhauled-village](https://github.com/ChoiceTheorem/ChoiceTheorem-s-overhauled-village) | ChoiceTheorem's Overhauled Village | 2包 | — | [卡片](./_卡片/ChoiceTheorem__ChoiceTheorem-s-overhauled-village.md) |
| [joshieman06/SunkenSpires](https://github.com/joshieman06/SunkenSpires) | Sunken Spires | 1包 | — | [卡片](./_卡片/joshieman06__SunkenSpires.md) |
| [KreloX/Duplicate-Entity-UUID-Fix](https://github.com/KreloX/Duplicate-Entity-UUID-Fix) | DEUF - Duplicate Entity UUID Fix [NeoFor | 1包 | — | [卡片](./_卡片/KreloX__Duplicate-Entity-UUID-Fix.md) |
| [weaversworkshop/grapplemod-skybound](https://github.com/weaversworkshop/grapplemod-skybound) | Grappling Hook Mod: Skybound | 1包 | — | [卡片](./_卡片/weaversworkshop__grapplemod-skybound.md) |
| [zhenshiz/ViScriptShop-Market](https://github.com/zhenshiz/ViScriptShop-Market) | ViScriptShop Market | 1包 | — | [卡片](./_卡片/zhenshiz__ViScriptShop-Market.md) |
| [xienaoban/minecraft-biology-dictionary](https://github.com/xienaoban/minecraft-biology-dictionary) | Biology Dictionary | 1包 | — | [卡片](./_卡片/xienaoban__minecraft-biology-dictionary.md) |
| [Corosauce/WATUT](https://github.com/Corosauce/WATUT) | What Are They Up To (Watut) | 1包 | — | [卡片](./_卡片/Corosauce__WATUT.md) |
| [LOVE-U987/Adaptive-Nemesis](https://github.com/LOVE-U987/Adaptive-Nemesis) | [AN]Adaptive Nemesis | 1包 | — | [卡片](./_卡片/LOVE-U987__Adaptive-Nemesis.md) |
| [Nova-Committee/0Pack2Reload](https://github.com/Nova-Committee/0Pack2Reload) | 0Pack2Reload | 1包 | — | [卡片](./_卡片/Nova-Committee__0Pack2Reload.md) |
| [FINDERFEED/FDLib](https://github.com/FINDERFEED/FDLib) | FDLib | 1包 | [报告](./FINDERFEED__FDLib.md) | [卡片](./_卡片/FINDERFEED__FDLib.md) |
| [zhenshiz/ViScriptRecipe](https://github.com/zhenshiz/ViScriptRecipe) | ViScriptRecipe | 1包 | [报告](./zhenshiz__ViScriptRecipe.md) | [卡片](./_卡片/zhenshiz__ViScriptRecipe.md) |
| [TerminalMC/ClientSort](https://github.com/TerminalMC/ClientSort) | clientsort-neoforge-3.89.0-beta.2+1.21.1 | 1包 | — | [卡片](./_卡片/TerminalMC__ClientSort.md) |
| [nutant233/Fast-Recipe-Search](https://github.com/nutant233/Fast-Recipe-Search) | fastrecipesearch-1.21.1-26.8.1-neoforge. | 1包 | — | [卡片](./_卡片/nutant233__Fast-Recipe-Search.md) |
| [FTBTeam/FTB-Library](https://github.com/FTBTeam/FTB-Library) | ftb-library-neoforge-2101.1.35.jar | 3包 | — | [卡片](./_卡片/FTBTeam__FTB-Library.md) |
| [FTBTeam/FTB-Teams](https://github.com/FTBTeam/FTB-Teams) | a/[FTB 团队] ftb-teams-neoforge-2101.1.10. | 3包 | — | [卡片](./_卡片/FTBTeam__FTB-Teams.md) |
| [FTBTeam/FTB-XMod-Compat](https://github.com/FTBTeam/FTB-XMod-Compat) | ftb-xmod-compat-neoforge-21.1.11.jar | 2包 | — | [卡片](./_卡片/FTBTeam__FTB-XMod-Compat.md) |
| [MrCrayfish/GoblinTraders](https://github.com/MrCrayfish/GoblinTraders) | goblintraders-neoforge-1.21.1-1.11.2.jar | 1包 | — | [卡片](./_卡片/MrCrayfish__GoblinTraders.md) |
| [MrCrayfish/MightyMail](https://github.com/MrCrayfish/MightyMail) | mighty_mail-neoforge-1.21.1-1.1.4.jar | 1包 | — | [卡片](./_卡片/MrCrayfish__MightyMail.md) |
| [Mrbysco/Retraining](https://github.com/Mrbysco/Retraining) | Retraining-neoforge-1.21-2.0.0.jar | 1包 | — | [卡片](./_卡片/Mrbysco__Retraining.md) |
| [FTBTeam/FTB-Quests](https://github.com/FTBTeam/FTB-Quests) | [FTB 任务] ftb-quests-neoforge-2101.1.34.j | 1包 | — | [卡片](./_卡片/FTBTeam__FTB-Quests.md) |
| [MrCrayfish/MrCrayfishFurnitureMod-Refurbished](https://github.com/MrCrayfish/MrCrayfishFurnitureMod-Refurbished) | [MrCrayfish 的家具：重制] refurbished_furnitur | 2包 | — | [卡片](./_卡片/MrCrayfish__MrCrayfishFurnitureMod-Refurbished.md) |
| [EccentricVamp/EccentricTome](https://github.com/EccentricVamp/EccentricTome) | [怪奇宝典] eccentrictome-1.21.1-1.2.0.jar | 1包 | — | [卡片](./_卡片/EccentricVamp__EccentricTome.md) |
| [Buuz135/FindMe](https://github.com/Buuz135/FindMe) | [找到我] findme-1.21.1-neoforge-1.3.0-test. | 1包 | — | [卡片](./_卡片/Buuz135__FindMe.md) |
| [Renyigesai/bakery](https://github.com/Renyigesai/bakery) | [烘焙坊] bakeries-1.21.1-NeoForge-1.0.3.jar | 1包 | — | [卡片](./_卡片/Renyigesai__bakery.md) |
| [AtomicStryker/atomicstrykers-minecraft-mods](https://github.com/AtomicStryker/atomicstrykers-minecraft-mods) | [稀有精英怪] infernalmobs-1.21.1.3NF.jar | 2包 | — | [卡片](./_卡片/AtomicStryker__atomicstrykers-minecraft-mods.md) |
| [henkelmax/corpse](https://github.com/henkelmax/corpse) | [遗体] corpse-neoforge-1.21.1-1.1.13.jar | 1包 | — | [卡片](./_卡片/henkelmax__corpse.md) |
| [breeze-devs/Settlements-Alpha](https://github.com/breeze-devs/Settlements-Alpha) | 万家烟火settlements-1.0.0-beta.1.jar | 1包 | [报告](./breeze-devs__Settlements-Alpha.md) | [卡片](./_卡片/breeze-devs__Settlements-Alpha.md) |
| [MoePus/SaveMyRecipeBook](https://github.com/MoePus/SaveMyRecipeBook) | 保存我的配方书smrb-1.0.0.jar | 1包 | — | [卡片](./_卡片/MoePus__SaveMyRecipeBook.md) |
| [Minecraft-LightLand/ModularGolems](https://github.com/Minecraft-LightLand/ModularGolems) | 傀儡装配modulargolems-3.1.43.jar | 1包 | [报告](./Minecraft-LightLand__ModularGolems.md) | [卡片](./_卡片/Minecraft-LightLand__ModularGolems.md) |
| [IAFEnvoy/Uranus](https://github.com/IAFEnvoy/Uranus) | 冰火前置uranus-2.4.1-bugfix-1.21.1-neoforge. | 1包 | — | [卡片](./_卡片/IAFEnvoy__Uranus.md) |
| [gizmo-ds/smsn-mod](https://github.com/gizmo-ds/smsn-mod) | 救救网络smsn-neoforge-1.4.3-1.21.1.jar | 1包 | — | [卡片](./_卡片/gizmo-ds__smsn-mod.md) |
| [Mrbysco/StructureCompass](https://github.com/Mrbysco/StructureCompass) | 结构指南针StructureCompass-1.21.1-4.2.1.jar | 1包 | — | [卡片](./_卡片/Mrbysco__StructureCompass.md) |
| [Mrbysco/AgeingSpawners](https://github.com/Mrbysco/AgeingSpawners) | AgeingSpawners-1.20.1-2.0.0.jar | 1包 | — | [卡片](./_卡片/Mrbysco__AgeingSpawners.md) |
| [CraftTweaker/CraftTweaker](https://github.com/CraftTweaker/CraftTweaker) | CraftTweaker-forge-1.20.1-14.0.60.jar | 1包 | — | [卡片](./_卡片/CraftTweaker__CraftTweaker.md) |
| [someaddons/cupboard](https://github.com/someaddons/cupboard) | cupboard-1.20.1-4.1.jar | 2包 | — | [卡片](./_卡片/someaddons__cupboard.md) |
| [FTBTeam/FTB-Essentials](https://github.com/FTBTeam/FTB-Essentials) | ftb-essentials-forge-2001.2.4.jar | 1包 | — | [卡片](./_卡片/FTBTeam__FTB-Essentials.md) |
| [FTBTeam/FTB-Ranks](https://github.com/FTBTeam/FTB-Ranks) | ftb-ranks-forge-2001.1.7.jar | 1包 | — | [卡片](./_卡片/FTBTeam__FTB-Ranks.md) |
| [hammertater/treechop](https://github.com/hammertater/treechop) | TreeChop-1.20.1-forge-0.19.0-fixed.jar | 1包 | — | [卡片](./_卡片/hammertater__treechop.md) |
| [FTBTeam/FTB-Mods-Issues](https://github.com/FTBTeam/FTB-Mods-Issues) | a/[FTB任务] ftb-quests-neoforge-2101.1.24. | 2包 | — | [卡片](./_卡片/FTBTeam__FTB-Mods-Issues.md) |
| [stfwi/engineers-decor](https://github.com/stfwi/engineers-decor) | [工程师的装饰]engineersdecor-1.3.31.jar | 1包 | — | [卡片](./_卡片/stfwi__engineers-decor.md) |
| [LatvianModder/Item-Filters](https://github.com/LatvianModder/Item-Filters) | [物品过滤器] item-filters-forge-2001.1.0-buil | 1包 | — | [卡片](./_卡片/LatvianModder__Item-Filters.md) |
| [PaintNinja/Presence-Footsteps-Forge](https://github.com/PaintNinja/Presence-Footsteps-Forge) | [脚步声Forge版] PresenceFootsteps-1.20.1-1.9 | 1包 | — | [卡片](./_卡片/PaintNinja__Presence-Footsteps-Forge.md) |
| [someaddons/structureessentials](https://github.com/someaddons/structureessentials) | structureessentials-1.21.1-5.0.jar | 1包 | — | [卡片](./_卡片/someaddons__structureessentials.md) |
| [FTBTeam/FTB-Ultimine](https://github.com/FTBTeam/FTB-Ultimine) | a/[连锁破坏] ftb-ultimine-neoforge-2101.1.13 | 1包 | — | [卡片](./_卡片/FTBTeam__FTB-Ultimine.md) |
| [shedaniel/LightOverlay](https://github.com/shedaniel/LightOverlay) | [亮度覆盖] light-overlay-12.0.0-neoforge.jar | 1包 | — | [卡片](./_卡片/shedaniel__LightOverlay.md) |
| [TwelveIterations/TrashSlot](https://github.com/TwelveIterations/TrashSlot) | a/[垃圾槽] trashslot-neoforge-1.21.1-21.1.9 | 2包 | — | [卡片](./_卡片/TwelveIterations__TrashSlot.md) |
| [TwelveIterations/CookingForBlockheads](https://github.com/TwelveIterations/CookingForBlockheads) | a/[傻瓜烹饪／懒人厨房] cookingforblockheads-neofo | 2包 | — | [卡片](./_卡片/TwelveIterations__CookingForBlockheads.md) |
| [TwelveIterations/CraftingTweaks](https://github.com/TwelveIterations/CraftingTweaks) | a/[合成辅助] craftingtweaks-neoforge-1.21.1- | 2包 | — | [卡片](./_卡片/TwelveIterations__CraftingTweaks.md) |
| [rikka0w0/LanServerProperties](https://github.com/rikka0w0/LanServerProperties) | [自定义局域网联机] lanserverproperties-1.13.2-ne | 1包 | — | [卡片](./_卡片/rikka0w0__LanServerProperties.md) |
| [JTK222/common-networking](https://github.com/JTK222/common-networking) | common-networking-neoforge-1.0.21-1.21.1 | 1包 | — | [卡片](./_卡片/JTK222__common-networking.md) |
| [P3pp3rF1y/Reliquary](https://github.com/P3pp3rF1y/Reliquary) | [圣遗物] reliquary-1.21.1-2.0.78.1552.jar | 2包 | — | [卡片](./_卡片/P3pp3rF1y__Reliquary.md) |
| [FTBTeam/FTB-Chunks](https://github.com/FTBTeam/FTB-Chunks) | a/[FTB 区块] ftb-chunks-neoforge-2101.1.14 | 1包 | — | [卡片](./_卡片/FTBTeam__FTB-Chunks.md) |
| [CyclopsMC/EvilCraft](https://github.com/CyclopsMC/EvilCraft) | EvilCraft | 1包 | — | [卡片](./_卡片/CyclopsMC__EvilCraft.md) |
| [CyclopsMC/CyclopsCore](https://github.com/CyclopsMC/CyclopsCore) | Cyclops Core | 1包 | — | [卡片](./_卡片/CyclopsMC__CyclopsCore.md) |
| [CyclopsMC/CommonCapabilities](https://github.com/CyclopsMC/CommonCapabilities) | Common Capabilities | 1包 | — | [卡片](./_卡片/CyclopsMC__CommonCapabilities.md) |
| [desht/ModularRouters](https://github.com/desht/ModularRouters) | Modular Routers | 1包 | — | [卡片](./_卡片/desht__ModularRouters.md) |
| [vadis365/Mob-Grinding-Utils](https://github.com/vadis365/Mob-Grinding-Utils) | Mob Grinding Utils | 1包 | — | [卡片](./_卡片/vadis365__Mob-Grinding-Utils.md) |
| [Buuz135/Industrial-Foregoing](https://github.com/Buuz135/Industrial-Foregoing) | More Industrial Foregoing Addons (MIFA) | 1包 | — | [卡片](./_卡片/Buuz135__Industrial-Foregoing.md) |
| [BlakeBr0/IronJetpacks](https://github.com/BlakeBr0/IronJetpacks) | Iron Jetpacks | 1包 | — | [卡片](./_卡片/BlakeBr0__IronJetpacks.md) |
| [MysticMods/Roots](https://github.com/MysticMods/Roots) | Roots Classic | 1包 | [报告](./MysticMods__Roots.md) | [卡片](./_卡片/MysticMods__Roots.md) |
| [SilentChaos512/Silent-Gear](https://github.com/SilentChaos512/Silent-Gear) | Silent Gear Metalworks | 1包 | [报告](./SilentChaos512__Silent-Gear.md) | [卡片](./_卡片/SilentChaos512__Silent-Gear.md) |
| [Commoble/MoreRed](https://github.com/Commoble/MoreRed) | More Red x CC:Tweaked Compat | 1包 | — | [卡片](./_卡片/Commoble__MoreRed.md) |
| [XFactHD/FramedBlocks](https://github.com/XFactHD/FramedBlocks) | FramedBlocks | 1包 | [报告](./XFactHD__FramedBlocks.md) | [卡片](./_卡片/XFactHD__FramedBlocks.md) |
| [Buuz135/Functional-Storage](https://github.com/Buuz135/Functional-Storage) | Functional Storage | 1包 | — | — |
| [Direwolf20-MC/LaserIO](https://github.com/Direwolf20-MC/LaserIO) | LaserIO | 1包 | — | [卡片](./_卡片/Direwolf20-MC__LaserIO.md) |
| [Draconic-Inc/Draconic-Evolution](https://github.com/Draconic-Inc/Draconic-Evolution) | Draconic Evolution | 1包 | — | [卡片](./_卡片/Draconic-Inc__Draconic-Evolution.md) |
| [AlphaMode/CompactMachines](https://github.com/AlphaMode/CompactMachines) | Compact Machines | 1包 | — | [卡片](./_卡片/AlphaMode__CompactMachines.md) |
| [Draconic-Inc/BrandonsCore](https://github.com/Draconic-Inc/BrandonsCore) | Brandon's Core | 1包 | — | [卡片](./_卡片/Draconic-Inc__BrandonsCore.md) |
| [SilentChaos512/SilentGems](https://github.com/SilentChaos512/SilentGems) | Silent's Gems | 1包 | — | [卡片](./_卡片/SilentChaos512__SilentGems.md) |
| [Ellpeck/ActuallyAdditions](https://github.com/Ellpeck/ActuallyAdditions) | Actually Additions | 1包 | — | [卡片](./_卡片/Ellpeck__ActuallyAdditions.md) |
| [BuiltBrokenModding/AI-Improvements](https://github.com/BuiltBrokenModding/AI-Improvements) | AI Improvements: Performance Tuning | 1包 | — | [卡片](./_卡片/BuiltBrokenModding__AI-Improvements.md) |
| [Geforce132/SecurityCraft](https://github.com/Geforce132/SecurityCraft) | Security Craft | 1包 | — | [卡片](./_卡片/Geforce132__SecurityCraft.md) |
| [McJty/McJtyLib](https://github.com/McJty/McJtyLib) | McJtyLib | 1包 | — | [卡片](./_卡片/McJty__McJtyLib.md) |
| [refinedmods/refinedstorage2](https://github.com/refinedmods/refinedstorage2) | Refined Storage | 1包 | — | [卡片](./_卡片/refinedmods__refinedstorage2.md) |
| [SilentChaos512/SilentLib](https://github.com/SilentChaos512/SilentLib) | Silent Lib (silentlib) | 1包 | — | [卡片](./_卡片/SilentChaos512__SilentLib.md) |
| [refinedmods/rangedpumps](https://github.com/refinedmods/rangedpumps) | Ranged Pumps | 1包 | — | [卡片](./_卡片/refinedmods__rangedpumps.md) |
| [VazkiiMods/AkashicTome](https://github.com/VazkiiMods/AkashicTome) | Akashic Tome | 1包 | — | [卡片](./_卡片/VazkiiMods__AkashicTome.md) |
| [ARxyt/ColonyPathingEdition](https://github.com/ARxyt/ColonyPathingEdition) | MineColonies | 1包 | — | [卡片](./_卡片/ARxyt__ColonyPathingEdition.md) |
| [Shadows-of-Fire/Wither-Skeleton-Tweaks](https://github.com/Shadows-of-Fire/Wither-Skeleton-Tweaks) | Wither Skeleton Tweaks | 1包 | — | [卡片](./_卡片/Shadows-of-Fire__Wither-Skeleton-Tweaks.md) |
| [ImFalling/OpenBlocks_Elevator_Fabric](https://github.com/ImFalling/OpenBlocks_Elevator_Fabric) | OpenBlocks Elevator | 1包 | — | [卡片](./_卡片/ImFalling__OpenBlocks_Elevator_Fabric.md) |


## 补充分析（非整合包来源 / 手动追加）

| 对象 | 类型 | 报告 | 一句话 |
|---|---|---|---|
| BleedZone7 / dumbcatmod 0.0.3（Forge 1.20.1） | **反编译分析**（jar，无公开源码） | [报告](./BleedZone7__dumbcatmod-0.0.3-forge-1.20.1.md) | MCreator 打底 + 手写子系统：修仙境界(Capability)、武器品阶/技能/诅咒、守潮尸潮事件、抽卡、拆解/车床/矿机、自研玩家动画引擎 dcanim、自研 VFX 引擎 dcvfx、内置性能剖析 DcPerf + LOD |
| westernat/ParticleStorm（1.21.1 NeoForge，v1.4.2.1） | 源码分析（本地克隆） | [报告](./westernat__ParticleStorm.md) | 把基岩版粒子格式搬进 Java：组件 dispatchedMap + DFU Codec 数据驱动、自研 Molang 编译器（11.5k 行）、11 种程序化网格/材质映射、与 GeckoLib 的 locator+粒子关键帧集成、最小同步（只同步 emitter 存在与绑定） |
| DBE（dbe + dbe_npc，1.21.1 NeoForge，1.1.0-SNAPSHOT） | **反编译分析**（jar，Kotlin，无公开源码） | [报告](./DBE__dbe-1.1.0-neoforge-1.21.1.md) | 引擎级库：动画图(1448 class)+游戏内编辑器+IK/根运动/第一人称+GAS 能力系统+状态树+Bullet 刚体物理(60Hz 独立线程)+NPC 模块+蓝图/Lua 脚本；含 6 个子系统详解 |
| Tinkers' Construct / Tetra / Silent Gear（材质拼接专题） | 源码分析（三仓库对比） | [专题报告](./专题__材质拼接与复合效果__Tinkers_Tetra_SilentGear.md) | 三条技术路线对比：Tinkers=灰阶母版+调色板+datagen 生成 545 贴图；Tetra=选贴图名+顶点色+层叠+Synergy；Silent Gear 4.x=两档模板+顶点色+MIXBOX 颜料混色（复合材质）；含复合效果合成语义/美术特效/HUD 对比与选型建议 |
| 元素反应模拟器 v0.21（Unity / C#） | **反编译分析**（出货包，无源码） | [报告](./元素反应模拟器v0.21__元素反应实现.md) | 原神式元素反应引擎：11 元素（含燃/冻/激三种藏元素）、ElementalInfo 衰减公式、BehaviorXxx 优先级表（四条规律）、蒸发/融化倍率、感电跳伤、燃烧燃料机制、绽放/激化、8 折叠加规则；含未实现清单与 4 条疑似 bug |
| FallingColors/HexMod（Hex Casting 0.11.4，1.20.1） | 源码分析（Kotlin，多加载器） | [报告](./HexCasting__FallingColors-HexMod.md) | "把编程语言做进 MC"：栈式 VM（CastingVM/CastingImage/CastingEnvironment 三分离）+ 链表调用栈的 3 种帧（Hermes/Charon/Thoth 三种控制流）+ 29 类 Mishap 错误值 + 113 条指令按域分包 + 服务端权威施法 + hexdoc 注册表自动生成图鉴 |
| TeaCon 2026 整合包（164 mod，MC 26.1.2 / NeoForge） | 仓库定位 + **全量反编译** | [定位表](../对照表/TeaCon2026整合包Mod-GitHub定位.md) | 143 个定位到公开仓库（87 来源声明级 + 6 中 + 50 默认采信）；**164 个全部反编译**（3,938,805 行）并生成结构卡片，见  |
| TeaCon 2026 重点 Mod（7 个） | 深度分析（反编译实读） | [报告](./TeaCon2026__重点Mod深度分析.md) | Minecraft Mod MCP(游戏内 MCP 服务器/截图+输入注入)、车万女仆 2.0(LLM agent + 内置棋类引擎)、傀儡装配(部件×材质数据驱动)、AnvilCraft(行为树+配方族+流体网络)、NeoMTR(内嵌 Rhino/Jetty/批渲染)、VoteMe(Redis+Reactor 现场投票)、听B站(流媒体分层集成) |
| 四包未定位 mod（223 个） | 本地 jar **反编译补漏** | [补漏报告](./四包未定位Mod本地反编译补漏.md) | 从 PCL2 已装整合包取出 214 个 jar 用 CFR 反编译（**278 万行**）+ 速览卡片；顺带回收 **44 个仓库地址**（含克隆失败的 MFFS_Classic/EnderStorage/ExtremeReactors2）；剩 18 个无源（星轨包未安装占 13） |
| 其余 15 个整合包（**4478 个 jar**） | **Mod 清单提取**（PCL2 已装包全量） | [对照表](../../对照表/) | 逐包清单 15 份 → `对照表/Mod清单__<包>.md`；元数据带仓库 2323 个（52%）；不在已有映射里的**新仓库 152 个**（标注 12 个误匹配 + **24 个深挖候选**）→ `对照表/剩余包_新仓库清单.md`；只有非 GitHub 地址的 **524 个** → `对照表/剩余包_非GitHub地址mod工作单.md`。顺带修好 1.12.2 老包缺 `mcmod.info` 解析的缺陷（NovaEngineering-World 带仓库 3 → 37） |
| 星轨重铸缺失 13 个 jar | **多镜像下载 + 反编译** | [补漏报告](./四包未定位Mod本地反编译补漏.md) | 用自建下载器（Modrinth CDN 主备 + BMCLAPI + forgecdn 主备，**SHA512 校验**）从整合包索引直链补齐 13/13，反编译约 12.7 万行入 `_pack_decompiled/星轨重铸/`；因元数据无仓库地址，不新增仓库 |
| **Domum Ornamentum**（方块版材质拼接，1.21.1 NeoForge，反编译实读） | **深挖报告 #1** | [深挖报告](./深挖__Domum-Ornamentum__方块版材质拼接.md) | 材质 = **源方块引用**（`record MaterialTextureData(Map<部件id,Block>)` DataComponent，Codec+StreamCodec 三用）；**部件 id 写成占位贴图的资源位置**（`minecraft:block/oak_planks`）→ 重贴图靠 sprite 名零映射命中；UV 归一化重映射 + **tint 打包 `blockStateId<<8｜tintIndex`** 让生物群系/染料染色原生生效；渲染类型取源方块**并集**、不支持则擦除；硬度/音效/抗爆/工具**委托主部件**；一条"部件化配方"覆盖全部材质组合（139 条配方）；动态木框 48 部件由**连通位图派生**（擦除 = 指向 AIR）|
| **DSH 插件能否移植到 ZCode** ／ **能否造出"真看画面 + 不干扰玩家"** | **设计答复**（两问） | [设计答复](./设计__DSH插件移植ZCode_与_不干扰玩家的AI游玩.md) | ① 移植：**工具层可近乎照搬**（ZCode 插件用 `mcpServers` 暴露 MCP 工具，官方 `node-repl-host` 即范式），`src/` 那 60-70%（bot/看门狗/记忆/地图）与宿主无关可原样复用；但**三样无对应物**——按 preset 收窄工具（ZCode 无 preset/composition）、插件前端 UI（无此扩展面）、凭据服务；**主动唤醒**受限（hooks 仅 7 事件且 `async` 无效），给了 Stop-hook 阻塞等待 / 定时心跳 / 常驻进程三种替代。② 不干扰：干涉的唯一根源是**输入注入**（那个 mod 的控制模式会强制释放鼠标=人机交权，且 `ALWAYS_ALLOWED` 里 6 个方法仍有副作用，**真只读只有 7 个**）；三种架构——只读组合（零代码，看玩家视角）／**二号客户端**（零代码、agent 有自己的眼睛和手，推荐）／**自研 mod**（离屏 `RenderTarget` 给眼睛 + 服务端 NPC 当身体；库里 `Geforce132/SecurityCraft` 的 `CameraFeed` 是现成工业级参考）|
| **whale-craft vs Minecraft Mod MCP**（两种"让 AI 进 MC"的路线） | **对照报告** | [对照报告](./对照__whale-craft_vs_MinecraftModMCP.md) | MCP mod = **游戏内 mod**（Java，走标准 MCP：HTTP/SSE，端口 9876）把**本客户端的画面与 GUI**交出去（真实截图 / 反射点控件 / 注入键鼠，**零鉴权**）；whale-craft（`yzi1b/whale-craft`，MIT，JS/Node，DSH 插件）= **宿主侧 mineflayer 协议机器人**以**玩家身份**连服，工具**原生注册**（开篇即写明"不装 MCP 子进程"），有会话级身体 + 工作区记忆 + **单通道看门狗**（空闲唤醒 / 生成中插话），但**看不到画面**（`mc_map` 是字符地形图与方块名合成图）。结论：测自己的 mod 用 MCP mod，让 AI 去服务器玩用 whale-craft；两者可并存。**§5 追加"能否同会话共用"**：能，但有三道关口——① 那个 mod **不是 MCP 协议**（0 处 `tools/list`/`tools/call`/`initialize`，是自定义方言，标准 MCP 客户端连不上）、② whale-craft 的 MC 模式是**无条件白名单**（要 `mcMode.allowOtherTools` 开口子）、③ 两具身体（你的角色 vs bot）要同世界并交代清楚；给了三种配法，**最省事的一种只需开 `pwsh`**：curl 打 `screenshot_to_file` 落地 PNG → 用已在白名单里的 `read_image` 看。源码已归档 `源码库/_参考仓库/yzi1b__whale-craft`（v0.1.7，1.49 万行） |
| DBE / Spark 两个发布版本差异（1.0.1004 → 1.0.1009） | **版本差异报告**（类级 CRC32 比对） | [差异报告](./DBE__版本差异_1.0.1004到1.0.1009.md) | 起因是"mod 更新了"——核实后**公开渠道最新仍是 9/5 那份、与本库已反编译的 sha256 逐字节相同**（CF 项目 `dbes-spark-engine` 仅 2 个文件）。于是改测两版差异：**命名空间统一**（`cn/solarmoon/spark_core/**` 3238 类整体并入 `cn/dbe`，故公开 GitHub 仓库对不上现版 jar）+ 新增游戏内编辑器/动画图节点库/蓝图工具/粒子/IK/根运动，删除 `npc/client` 与旧粒子层；工具与复现命令见报告 |
| **BOSS 引擎调研（六样本共性模式）** | **深挖报告**（五路并行，服务于 Forge 1.20.1 Colossus 框架设计） | [深挖报告](./深挖__BOSS引擎调研__六样本共性模式.md) | 样本=首领崛起(BR)/Cataclysm/Twilight Forest 移植/Eternal Starlight/Iron's Spells + 5 个周边系统；十条共性（阶段=同步 int + 一次性血量闸门、调度内核三代演进到状态栈、判定帧全是动画 tick 魔数、死亡先播动画后结算、BossBar 只补一条样式旁路、参战者收敛为 hurt 收集名单、多人缩放无一样本认真做、战斗状态零自定义包）+ 五处分歧裁决表 + 不该进框架清单。关键缺口：**全库没有一个样本做 JSON 数据驱动招式表**，这是框架最大的差异化空间 |
| **下一步开挖清单** | 待办（非报告） | [深挖待办清单.md](../../深挖待办清单.md) | 18 条：第一梯队 6（Domum Ornamentum / TLM2 LLM / Mod MCP 改造 / Mahou Tsukai / AnvilCraft / synaxis）+ 第二梯队 5 + 第三梯队 2 + 本轮新候选 5（Chisel+CTM、语言进方块三方对照、Cardinal Components、结构 datapack 族、ETF/Player Animator） |
