# FIDR暗涌 — Mod 源码(GitHub)对照表（含本地反编译）

- mod 总数 **148**：定位到公开仓库 **120**；无公开源码者 **29** 个已用本地安装 jar 反编译（见"本地反编译"列）
- "本地反编译"列 = 从 `PCL2\.minecraft\versions\<包>\mods` 取 jar 用 CFR 反编译，产物在 `源码库/_参考仓库/_pack_decompiled/<包>/`，速览卡片在 `_卡片/`
- 本轮新补充的仓库来源为 jar 内 `mods.toml` 元数据（标注在"来源"列）

| mod 文件 | 项目名 | GitHub | 来源 | 本地反编译 |
|---|---|---|---|---|
| `AgeingSpawners-1.20.1-2.0.0.jar` | AgeingSpawners-1.20.1-2.0.0.jar | https://github.com/Mrbysco/AgeingSpawners | jar-meta |  |
| `Bookshelf-Forge-1.20.1-20.2.15.jar` | Bookshelf | https://github.com/Darkhax-Minecraft/Bookshelf | modrinth-api |  |
| `CraftTweaker-forge-1.20.1-14.0.60.jar` | CraftTweaker-forge-1.20.1-14.0.60.jar | https://github.com/CraftTweaker/CraftTweaker | jar-meta |  |
| `DramaticDoors-QuiFabrge-1.20.1-3.3.3.jar` | Dramatic Doors | https://github.com/Kitteh6660/DramaticDoors | modrinth-api |  |
| `Engineers Delight 1.20.1 B.1.4.jar` | Engineers Delight 1.20.1 B.1.4.jar | — |  | Y（799 行） |
| `EpheroLib-1.20.1-FORGE-1.2.0.jar` | EpheroLib-1.20.1-FORGE-1.2.0.jar | https://github.com/ExcessiveAmountsOfZombies/EpheroLib | manual-verified |  |
| `IBEEditor-1.20-2.2.8-forge.jar` | IBE Editor | https://github.com/skyecodes/IBE-Editor | modrinth-api |  |
| `ItemRarity-1.20.1-forge-1.2.0.jar` | ItemRarity-1.20.1-forge-1.2.0.jar | — |  | Y（2,260 行） |
| `MaxHealthFix-Forge-1.20.1-12.0.4.jar` | Max Health Fix | https://github.com/Darkhax-Minecraft/Max-Health-Fix | modrinth-api |  |
| `Patched-9.0.0+1.20.1-forge.jar` | Patched | https://github.com/EnderTurret/PatchedMod | modrinth-api |  |
| `Quest Kill Task-0.2.0+1.20.1-forge.jar` | Quest Kill Task-0.2.0+1.20.1-forge.jar | — |  | Y（492 行） |
| `Searchables-forge-1.20.1-1.0.3.jar` | Searchables-forge-1.20.1-1.0.3.jar | https://github.com/jaredlll08/searchables | jar-meta |  |
| `Shoppy-1.20.1-FORGE-1.1.1-all.jar` | Shoppy-1.20.1-FORGE-1.1.1-all.jar | — |  | Y（3,181 行） |
| `Stellar.View-1.20.1-0.5.3-Forge.jar` | Stellar View | https://github.com/Povstalec/StellarView | modrinth-api |  |
| `TerraBlender-forge-1.20.1-3.0.1.10.jar` | TerraBlender-forge-1.20.1-3.0.1.10.jar | https://github.com/Glitchfiend/TerraBlender | jar-meta |  |
| `TreeChop-1.20.1-forge-0.19.0-fixed.jar` | TreeChop-1.20.1-forge-0.19.0-fixed.jar | https://github.com/hammertater/treechop | jar-meta |  |
| `WorldEditCUI-1.20+01.jar` | WorldEdit CUI (Unofficial Forge Port) | https://github.com/zbx1425/WorldEditCUI-Arch | modrinth-api |  |
| `YeetusExperimentus-Forge-2.3.0-build.4+mc1.20.1.jar` | Yeetus Experimentus | — |  | Y（107 行） |
| `[Alex 的生物] alexsmobs-1.22.9.jar` | Alex's Mobs | https://github.com/AlexModGuy/AlexsMobs | modrinth-api |  |
| `[CoFH核心] cofh_core-1.20.1-11.0.2.56.jar` | CoFH Core | https://github.com/CoFH/CoFHCore | manual |  |
| `[Csgo 箱子] csgobox-1.0.jar` | [Csgo 箱子] csgobox-1.0.jar | — |  | Y（3,330 行） |
| `[FTB 团队] ftb-teams-forge-2001.3.2.jar` | [FTB 团队] ftb-teams-forge-2001.3.2.jar | https://github.com/FTBTeam/FTB-Teams | manual |  |
| `[FTB任务] ftb-quests-forge-2001.4.22.jar` | [FTB任务] ftb-quests-forge-2001.4.22.jar | https://github.com/FTBTeam/FTB-Mods-Issues | jar-meta |  |
| `[JEI物品管理器] jei-1.20.1-forge-15.49.0.194.jar` | Just Enough Items (JEI) | https://github.com/mezz/JustEnoughItems | modrinth-api |  |
| `[KubeJS 离线文档] kubejsoffline-5.2.0.27.jar` | KubeJS Offline | https://github.com/Hunter19823/kubejsoffline | modrinth-api |  |
| `[MrCrayfish 的家具：重制] refurbished_furniture-forge-1.20.1-1.0.20.jar` | [MrCrayfish 的家具：重制] refurbished_furniture-forge-1.20.1-1.0.20.jar | https://github.com/MrCrayfish/MrCrayfishFurnitureMod-Refurbished | jar-meta |  |
| `[Xaero的世界地图] xaeroworldmap-forge-1.20.1-1.45.0.jar` | Xaero's World Map | — |  | Y（34,696 行） |
| `[Xaero的小地图] xaerominimap-forge-1.20.1-26.4.2.jar` | Xaero's Minimap | — |  | Y（49,026 行） |
| `[一键背包整理Next] InventoryProfilesNext-forge-1.20-1.10.20.jar` | Inventory Profiles Next | https://github.com/blackd/Inventory-Profiles | jar-meta |  |
| `[万用皮肤补丁] CustomSkinLoader_Universal-15.0.1.jar` | CustomSkinLoader | https://github.com/xfl03/MCCustomSkinLoader | modrinth-api |  |
| `[万象] ensorcellation-1.20.1-5.0.2.24.jar` | Ensorcellation | https://github.com/CoFH/Ensorcellation | manual-verified |  |
| `[下界乐事] nethersdelight-1.20.1-4.0.jar` | Nether's Delight | https://github.com/Umpaz/NethersDelight | jar-meta |  |
| `[不同寻常的末地] unusualend-2.3.1d.jar` | [不同寻常的末地] unusualend-2.3.1d.jar | — |  | Y（51,871 行） |
| `[任务拓展] questsadditions-1.4.7.jar` | [任务拓展] questsadditions-1.4.7.jar | — |  | Y（3,472 行） |
| `[传奇领主]block_factorys_bosses-2.1.2-forge-1.20.1.jar` | Bosses'Rise | — |  | Y（52,417 行） |
| `[全局服务器配置] global-server-config-forge-1.18.2+-1.0.jar` | Global Server Config | https://github.com/TJT01/GlobalServerConfig | modrinth-api |  |
| `[内存泄漏修复] memoryleakfix-forge-1.17+-1.1.5.jar` | Memory Leak Fix | https://github.com/fxmorin/memoryLeakFix | modrinth-api |  |
| `[农夫乐事] FarmersDelight-1.20.1-1.3.3.jar` | Farmer's Delight | https://github.com/vectorwing/FarmersDelight | modrinth-api |  |
| `[农夫暇事] farmersrespite-1.20.1-2.1.2.jar` | Farmer's Respite | — |  | Y（6,663 行） |
| `[创世神] worldedit-mod-7.2.15.jar` | WorldEdit | https://github.com/EngineHub/WorldEdit | modrinth-api |  |
| `[加速渲染] acceleratedrendering-1.0.14-1.20.1-alpha.jar` | [加速渲染] acceleratedrendering-1.0.14-1.20.1-alpha.jar | https://github.com/Argon4W/AcceleratedRendering | jar-meta |  |
| `[原版烹饪书] VanillaCookbook-2.2.4.jar` | Vanilla Cookbook | https://github.com/Moralle/VanillaCookbook | modrinth-api |  |
| `[可视化配方编写] visual_recipe_editor1.20.1-1.1.0.jar` | Workstation Recipe Exporter | https://github.com/Xiaoyu-2009/visual_recipe_editor | modrinth-api |  |
| `[唢呐生存指南] Sona-1.20.1-forge-1.5.1.jar` | [唢呐生存指南] Sona-1.20.1-forge-1.5.1.jar | — |  | Y（12,149 行） |
| `[多态合成] polymorph-forge-0.49.10+1.20.1.jar` | Polymorph | https://github.com/illusivesoulworks/polymorph | modrinth-api |  |
| `[失落的城市] lostcities-1.20-7.5.2.jar` | The Lost Cities | https://github.com/McJtyMods/LostCities | modrinth-api |  |
| `[妖怪之山通用库] mysterious_mountain_lib-1.6.34-1.20.1.jar` | Mysterious Mountain Lib | https://github.com/0999312/MMLib | modrinth-api |  |
| `[属性修复] AttributeFix-Forge-1.20.1-21.0.5.jar` | AttributeFix | https://github.com/Darkhax-Minecraft/AttributeFix | modrinth-api |  |
| `[工程师的装饰]engineersdecor-1.3.31.jar` | [工程师的装饰]engineersdecor-1.3.31.jar | https://github.com/stfwi/engineers-decor | jar-meta |  |
| `[帕秋莉手册] Patchouli-1.20.1-85-FORGE.jar` | Patchouli | https://github.com/VazkiiMods/Patchouli | modrinth-api |  |
| `[应用能源2] appliedenergistics2-forge-15.4.10.jar` | Applied Energistics 2 | https://github.com/AppliedEnergistics/Applied-Energistics-2 | modrinth-api |  |
| `[护甲上限突破] overloadedarmorbar-1.20.1-1.jar` | [护甲上限突破] overloadedarmorbar-1.20.1-1.jar | https://github.com/Tfarcenim/OverloadedArmorBar | jar-meta |  |
| `[拾光定影] exposure-forge-1.20.1-1.9.21.jar` | Exposure | https://github.com/mortuusars/Exposure | modrinth-api |  |
| `[掠夺者的枪] Pillagers Gun-1.20.1-forge-3.2.1.jar` | [掠夺者的枪] Pillagers Gun-1.20.1-forge-3.2.1.jar | — |  | Y（4,153 行） |
| `[旅行者背包] travelersbackpack-forge-1.20.1-9.1.56.jar` | Traveler's Backpack | https://github.com/Tiviacz1337/Travelers-Backpack | modrinth-api |  |
| `[时装盔甲重置版] cosmeticarmorreworked-1.20.1-v1a.jar` | [时装盔甲重置版] cosmeticarmorreworked-1.20.1-v1a.jar | https://github.com/zlainsama/CosmeticArmorReworked | manual-verified |  |
| `[时间控制] timecontrol-1.20.1-1.6.0.jar` | Time Control | https://github.com/Unixkitty/timecontrol | modrinth-api |  |
| `[是，史蒂夫模型] ysm-2.6.5-forge+mc1.20.1-release.jar` | Yes Steve Model | https://github.com/YesSteveModel/YSM-Wiki-Issues | jar-meta |  |
| `[更美观的血条] colorfulhearts-forge-1.20.1-4.3.16.jar` | Colorful Hearts | https://github.com/Terrails/colorful-hearts | modrinth-api |  |
| `[望远镜改进] spyglass_improvements-forge-1.5.12b+mc1.20+forge.jar` | Spyglass Improvements | https://github.com/juancarloscp52/spyglass-improvements | modrinth-api |  |
| `[末地乐事] ends_delight-2.6.1+forge.1.20.1.jar` | End's Delight | https://github.com/FoggyHillside/End-s-Delight | modrinth-api |  |
| `[末日生存工具包] Zombie Survival Kit-1.20.1-forge-2.1.8.jar` | [末日生存工具包] Zombie Survival Kit-1.20.1-forge-2.1.8.jar | — |  | Y（48 行） |
| `[永恒枪械工坊：零] tacz-1.20.1-1.1.8-hotfix.jar` | [TaCZ] Timeless and Classics Zero | https://github.com/MCModderAnchor/TACZ | modrinth-api |  |
| `[沉浸原油] ImmersivePetroleum-1.20.1-4.3.1-36b.jar` | Immersive Petroleum | https://github.com/TwistedGate/ImmersivePetroleum | modrinth-api |  |
| `[沉浸工程] ImmersiveEngineering-1.20.1-10.2.0-183.jar` | Immersive Engineering | https://github.com/BluSunrize/ImmersiveEngineering | modrinth-api |  |
| `[沉浸式飞机] immersive_aircraft-1.4.1+1.20.1-forge.jar` | Immersive Aircraft | https://github.com/Luke100000/ImmersiveAircraft | modrinth-api |  |
| `[深暗之地]the_afterdark-1.20.1-forge-1.0.3.1.jar` | The Afterdark | https://github.com/DenisMasterHerobrine/TheAfterdark | modrinth-api |  |
| `[滑翔伞] Paraglider-forge-20.1.3.jar` | Paragliders | https://github.com/Tictim/Paraglider | modrinth-api |  |
| `[物品过滤器] item-filters-forge-2001.1.0-build.59.jar` | [物品过滤器] item-filters-forge-2001.1.0-build.59.jar | https://github.com/LatvianModder/Item-Filters | jar-meta |  |
| `[犀牛] rhino-forge-2001.2.3-build.10.jar` | Rhino | https://github.com/KubeJS-Mods/Rhino | modrinth-api |  |
| `[玉 🔍] Jade-1.20.1-Forge-11.13.3.jar` | Jade 🔍 | https://github.com/Snownee/Jade | modrinth-api |  |
| `[玉米乐事] corn_delight-1.2.11-1.20.1.jar` | Corn Delight | https://github.com/0999312/Corn-Delight | modrinth-api |  |
| `[现代化修复] modernfix-forge-5.27.77+mc1.20.1.jar` | ModernFix | https://github.com/embeddedt/ModernFix | modrinth-api |  |
| `[禁用聊天举报] NoChatReports-FORGE-1.20.1-v2.2.2.jar` | No Chat Reports | https://github.com/Aizistral-Studios/No-Chat-Reports | modrinth-api |  |
| `[网络音乐机] netmusic-1.5.1-forge+mc1.20.1.jar` | Net Music | https://github.com/TartaricAcid/NetMusic | modrinth-api |  |
| `[翻箱倒柜]Rummage-1.20.1-forge-1.1.1.jar` | [翻箱倒柜]Rummage-1.20.1-forge-1.1.1.jar | — |  | Y（3,491 行） |
| `[脚步声Forge版] PresenceFootsteps-1.20.1-1.9.1-beta.1.jar` | [脚步声Forge版] PresenceFootsteps-1.20.1-1.9.1-beta.1.jar | https://github.com/PaintNinja/Presence-Footsteps-Forge | jar-meta |  |
| `[自动汉化更新] I18nUpdateMod-3.7.0-all.jar` | I18nUpdateMod | https://github.com/xfl03/I18nUpdateMod3 | modrinth-api |  |
| `[自定义LAN局域网联机服务器] EasyLAN-forge-1.20.1-v1.6a.jar` | EasyLAN | https://github.com/XiaoXianHW/EasyLAN | modrinth-api |  |
| `[自定义初始装备] CustomStartingGear-1.20-2.0.3.jar` | [自定义初始装备] CustomStartingGear-1.20-2.0.3.jar | — |  | Y（603 行） |
| `[苹果皮] appleskin-forge-mc1.20.1-2.5.1.jar` | AppleSkin | https://github.com/squeek502/AppleSkin | modrinth-api |  |
| `[试验假人] dummmmmmy-1.20-2.0.12-forge.jar` | MmmMmmMmmMmm | https://github.com/MehVahdJukaar/DuMmmMmmy | jar-meta |  |
| `[跑酷！] ParCool-1.20.1-3.4.3.3.jar` | ParCool! | https://github.com/alRex-U/ParCool | modrinth-api |  |
| `[车万女仆] touhoulittlemaid-1.5.3-forge+mc1.20.1.jar` | Touhou Little Maid | https://github.com/TartaricAcid/TouhouLittleMaid | modrinth-api |  |
| `[输入法冲突修复] IMBlocker-5.5.4-forge+1.17-1.20.4.jar` | IMBlocker | https://github.com/reserveword/IMBlocker | modrinth-api |  |
| `[通用拼音搜索] jecharacters-1.20.1-forge-4.6.9.jar` | JustEnoughCharacters | https://github.com/Towdium/JustEnoughCharacters | modrinth-api |  |
| `[通用机械] Mekanism-1.20.1-10.4.16.80.jar` | Mekanism | https://github.com/mekanism/Mekanism | modrinth-api |  |
| `[通用机械发电机] MekanismGenerators-1.20.1-10.4.16.80.jar` | Mekanism Generators | https://github.com/mekanism/Mekanism | modrinth-api |  |
| `[通量网络] FluxNetworks-1.20.1-7.2.1.15.jar` | [通量网络] FluxNetworks-1.20.1-7.2.1.15.jar | https://github.com/SonarSonic/Flux-Networks | jar-meta |  |
| `[配置界面] configured-forge-1.20.1-2.2.3.jar` | [配置界面] configured-forge-1.20.1-2.2.3.jar | https://github.com/MrCrayfish/Configured | jar-meta |  |
| `[铁氧体磁芯] ferritecore-6.0.1-forge.jar` | FerriteCore | https://github.com/malte0811/FerriteCore | modrinth-api |  |
| `[键位冲突显示] Controlling-forge-1.20.1-12.0.2.jar` | [键位冲突显示] Controlling-forge-1.20.1-12.0.2.jar | https://github.com/jaredlll08/Controlling | jar-meta |  |
| `[附魔描述] EnchantmentDescriptions-Forge-1.20.1-17.1.21.jar` | Enchantment Descriptions | https://github.com/Darkhax-Minecraft/Enchantment-Descriptions | modrinth-api |  |
| `[飞车奇匠] automobility-0.4.2+1.20.1-forge.jar` | Automobility | https://github.com/FoundationGames/Automobility | modrinth-api |  |
| `[食物效果显示Forge版] foodeffecttooltips+forge-1.20.1-1.6.0.jar` | Food Effect Tooltips (Forge) | https://github.com/Suel-ki/FoodEffectTooltips-Forge | modrinth-api |  |
| `[饮酒作乐] BrewinAndChewin-1.20.1-3.2.1.jar` | Brewin' And Chewin' | https://github.com/Monad-Modding/BrewinAndChewin | manual |  |
| `[鸡尾酒乐事] Cocktails-Delight-1.20.1-Forge-1.3.9.jar` | [鸡尾酒乐事] Cocktails-Delight-1.20.1-Forge-1.3.9.jar | — |  | Y（1,580 行） |
| `alexsdelight-1.5.jar` | alexsdelight-1.5.jar | — |  | Y（161 行） |
| `architectury-9.2.14-forge.jar` | Architectury API | https://github.com/architectury/architectury | modrinth-api |  |
| `blueprint-1.20.1-7.1.4.jar` | Blueprint | https://github.com/team-abnormals/blueprint | modrinth-api |  |
| `caveore-1.20.1-4.0.jar` | caveore-1.20.1-4.0.jar | — |  | Y（247 行） |
| `celesteconfig-forge-1.20.1-1.1.2.jar` | Sun and Moon Celestial Configuration | https://github.com/infernalstudios/Celestial-Configuration | modrinth-api |  |
| `citadel-2.6.3-1.20.1.jar` | Citadel | https://github.com/Alex-the-666/Citadel | modrinth-api |  |
| `cloth-config-11.1.136-forge.jar` | Cloth Config API | https://github.com/shedaniel/ClothConfig | modrinth-api |  |
| `collective-1.20.1-8.39.jar` | Collective | https://github.com/Serilum/Collective | modrinth-api |  |
| `cupboard-1.20.1-4.1.jar` | cupboard-1.20.1-4.1.jar | https://github.com/someaddons/cupboard | manual |  |
| `damageindicator-2.2.1-1.20.1.jar` | JeremySeq's Damage Indicator | https://github.com/JeremySeq/DamageIndicators | modrinth-api |  |
| `displaydelight-1.7.0.jar` | Display Delight | https://github.com/jkvin114/display-delight-neoforge | modrinth-api |  |
| `embeddium-0.3.31+mc1.20.1.jar` | Embeddium | https://github.com/FiniteReality/embeddium | modrinth-api |  |
| `endertrigon-1.20.1-1.1-all.jar` | Ender Trigon | https://github.com/nonamecrackers2/ender-trigon | modrinth-api |  |
| `enhancedai-3.3.7.3.jar` | Enhanced AI | https://github.com/Insane96/EnhancedAI | modrinth-api |  |
| `exposure_polaroid-forge-1.20.1-1.1.4.jar` | Exposure: Polaroid | https://github.com/mortuusars/ExposurePolaroid | modrinth-api |  |
| `fastboot-1.20.x-1.2.jar` | fastboot-1.20.x-1.2.jar | — |  | Y（55 行） |
| `fdcookbook-1.20.1-forge-1.6.1-rel.jar` | fdcookbook-1.20.1-forge-1.6.1-rel.jar | — |  | Y（1,386 行） |
| `flan-1.20.1-1.11.16-forge.jar` | Flan | https://github.com/Flemmli97/Flan | modrinth-api |  |
| `framework-forge-1.20.1-0.8.0.jar` | framework-forge-1.20.1-0.8.0.jar | https://github.com/MrCrayfish/Framework | manual |  |
| `ftb-essentials-forge-2001.2.4.jar` | ftb-essentials-forge-2001.2.4.jar | https://github.com/FTBTeam/FTB-Essentials | manual |  |
| `ftb-library-forge-2001.2.13.jar` | ftb-library-forge-2001.2.13.jar | https://github.com/FTBTeam/FTB-Library | manual |  |
| `ftb-ranks-forge-2001.1.7.jar` | ftb-ranks-forge-2001.1.7.jar | https://github.com/FTBTeam/FTB-Ranks | manual |  |
| `ftb-xmod-compat-forge-2.1.3.jar` | ftb-xmod-compat-forge-2.1.3.jar | https://github.com/FTBTeam/FTB-XMod-Compat | manual |  |
| `geckolib-forge-1.20.1-4.8.4.jar` | geckolib-forge-1.20.1-4.8.4.jar | https://github.com/bernie-g/geckolib | jar-meta |  |
| `globalpacks-forge-1.20.1-19.3.7.jar` | Global Packs | — |  | Y（728 行） |
| `guideme-20.1.15.jar` | GuideME | https://github.com/AppliedEnergistics/GuideME | modrinth-api |  |
| `incontrol-1.20-9.4.7.jar` | In Control! | https://github.com/McJtyMods/InControl | modrinth-api |  |
| `insanelib-1.23.4.6.jar` | InsaneLib | https://github.com/Insane96/InsaneLib | modrinth-api |  |
| `itemblacklist-1.20.1-1.1.5.jar` | Item Banning | https://github.com/pitbox46/ItemBlacklist | modrinth-api |  |
| `jeimultiblocks-1.20.1-1.0.6.jar` | Just Enough Immersive Multiblocks | https://github.com/sguest/jei-multiblocks | modrinth-api |  |
| `konkrete_forge_1.8.0_MC_1.20-1.20.1.jar` | Konkrete | https://github.com/Keksuccino/Konkrete | modrinth-api |  |
| `kotlinforforge-4.12.0-all.jar` | Kotlin for Forge | https://github.com/thedarkcolour/KotlinForForge | modrinth-api |  |
| `kubejs-forge-2001.6.5-build.26.jar` | KubeJS | https://github.com/KubeJS-Mods/KubeJS | modrinth-api |  |
| `libIPN-forge-1.20-4.0.2.jar` | libIPN | https://github.com/blackd/libIPN | modrinth-api |  |
| `libraryferret-forge-1.20.1-4.0.0.jar` | Library Ferret | — |  | Y（2,269 行） |
| `lightspeed-1.20.1-1.2.3.jar` | LightSpeedRe | https://github.com/kltyton/LightSpeedRe | modrinth-api |  |
| `lookinmyeyes-1.20.1-1.4.6.jar` | lookinmyeyes-1.20.1-1.4.6.jar | — |  | Y（210 行） |
| `lootr-forge-1.20-0.7.35.94.jar` | Lootr | https://github.com/noobanidus/lootr | modrinth-api |  |
| `lostcities-modern-tweaks-v1.0.10.jar` | Lost Cities Modern Tweaks | — |  | Y（0 行） |
| `lunarnether-1.0.3-all.jar` | lunarnether-1.0.3-all.jar | — |  | Y（2,306 行） |
| `mekalus-mc1.20.1-1.8.0.1.jar` | mekalus-mc1.20.1-1.8.0.1.jar | https://github.com/Asek3/Oculus | jar-meta |  |
| `modern_glass_doors-1.1.0-1.20.1.jar` | Modern Glass Doors(Forge) | https://github.com/embeddedt/ModernFix | 本地 jar 元数据 | Y（19,454 行） |
| `moonlight-1.20-2.16.34-forge.jar` | Moonlight Lib | https://github.com/MehVahdJukaar/Moonlight | modrinth-api |  |
| `oculus-mc1.20.1-1.8.0.jar` | Oculus | https://github.com/Asek3/Oculus | modrinth-api |  |
| `panoramica_forge_1.2.1_MC_1.19-1.19.2.jar` | Panoramica | https://github.com/Keksuccino/Panoramica | modrinth-api |  |
| `ping_system-1.01-1.20.1.jar` | Ping System | https://github.com/sam-makes-stuff/ping_system | modrinth-api |  |
| `probejs-7.0.0-forge.jar` | ProbeJS | https://github.com/Prunoideae/ProbeJS | modrinth-api |  |
| `sisser-1.10.jar` | sisser-1.10.jar | — |  | Y（88 行） |
| `taczlabs-1.20.1-1.1.8.jar` | TaCZ-Labs | https://github.com/Txt-Text/TaCZ-Labs | modrinth-api |  |
| `trimmed-forge-1.20.1-2.1.4-all.jar` | Trimmed | https://github.com/dhyces/trimmed | modrinth-api |  |
| `trulytreasures-1.20-3.0.0-forge.jar` | Truly Treasures | https://github.com/Ineffa/Truly-Treasures | modrinth-api |  |