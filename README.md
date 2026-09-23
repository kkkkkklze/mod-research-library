# Mod 源码研究汇总 — 四个整合包 · 591 个开源仓库

> **一句话成果**：把 4 个整合包里所有能找到的 mod 开源仓库（共 **591 个**）全部定位、验证、克隆到本地，并产出 **353 份深度分析报告**（332 份与速览卡片一一对应）+ **580 份结构速览卡片** + **4 份整合包 Mod→GitHub 对照表**，可直接用于学习 mod 工程化开发。缺口盘点见 `对照表/未深挖清单.md`（2026-09-23：580 个仓库中 248 个仍只有卡片）。
>
> **扩展（2026-09-20）**：又覆盖了 **TeaCon 2026**（164 个 mod **全量反编译**，394 万行）与**其余 15 个整合包**（**4478 个 jar** 的 mod 清单已提取，顺带发现 **152 个新仓库**、**24 个深挖候选**）→ 详见下方「八、扩展覆盖」。**下一步开挖清单见 [`深挖待办清单.md`](./深挖待办清单.md)**。

整理时间：2026-09-12（2026-09-16 增补：BleedZone7、ParticleStorm、GeckoLib 4.x、DBE；2026-09-20 增补：TeaCon 2026 仓库定位与 164 个 mod 全量反编译、四包 205 个 mod 反编译补漏、其余 15 包 mod 清单提取、13 个星轨缺失 jar 下载+反编译）

---

## 一、成果清单（本文件夹内容）

| 文件夹 | 内容 | 数量 |
|---|---|---|
| `分析报告/_分析报告/` | **深度分析报告**（子 agent 逐仓库读源码撰写，每条结论带 `文件路径:行号`） | **353 份**（332 份与卡片一一对应；含 BleedZone7 反编译分析、ParticleStorm 源码分析、GeckoLib 4.x↔5.x 对比补充、2026-09-23 批量新增 13 份） |
| `分析报告/_分析报告/_卡片/` | **速览卡片**（脚本自动提取：文件数/行数/包结构/构建方式/主类/许可证） | **580 份** |
| `分析报告/_分析报告/README-索引.md` | 总索引：按 10 个主题分类，链接到每份报告与卡片 | 1 份 |
| `对照表/` | Mod→GitHub 对照表（四包 6 + TeaCon 4 + 其余 15 包清单 15 + 非 GitHub 地址工作单 1 + 总表 4） | **30 个文件** |
| `源码库/_参考仓库/` | **591 个仓库的本地源码**（稀疏检出）+ **`BleedZone7__dumbcatmod-0.0.3/`（493 个 .java）** + **`DBE-1.1.0-neoforge-1.21.1/`（3656 个 .java）** + **`元素反应模拟器v0.21__SkillCooldown/`（C#）** + **`_teacon_decompiled/`（164 个 mod）** + **`_pack_decompiled/`（205 个 mod）**（均为反编译产物，附来源说明） | 约 2.2 GB + 672 万行反编译源码 |
| `学习指南/` | 《Mod 开发学习指南》——基于本批源码提炼的 13 章工程实践指南 | 1 份 |
| `研究脚本/` | 全套可复现脚本（包解析 / jar 元数据提取 / 批量克隆 / 卡片生成 / 表格生成） | 14 个 |
| **`深挖待办清单.md`** | **下一阶段的深挖待办**（第一/二梯队 11 条已列 + 从 15 包筛出的 5 条新候选，每条含理由/起点/目标问题/体量） | 1 份 |

**报告的阅读方式**：每份报告 8 节结构 —— 基本信息 / 源码规模与包结构 / 入口与注册 / 核心系统 / 网络·数据驱动·配置·datagen / Mixin / 值得学的 5 条具体做法 /（库模组）API 与扩展点。所有引用都是 `相对路径:行号`，在 `源码库/_参考仓库/` 里直接打开即可对照。

---

## 二、核心数据

**覆盖链条**：4 个整合包共 1372 条 mod 记录 → 去重后 **591 个唯一 GitHub 仓库** → 全部经 `git ls-remote` 验证、稀疏克隆成功 578 个。

**代码规模**（580 个有源码的仓库统计）：

| 指标 | 数值 |
|---|---|
| Java 文件总数 | **119,563 个** |
| Java 代码总行数 | **12,150,588 行** |
| 最大的仓库 | Create（2016 文件 / 27.7 万行）、Mekanism（2455 文件 / 26 万行）、FancyMenu（27.8 万行） |

**构建方式分布**（能识别出插件的仓库）：

| 构建插件 | 数量 | 说明 |
|---|---|---|
| `net.neoforged.moddev` | **234** | 当前 NeoForge 生态主流 |
| ForgeGradle | 73 | 1.20.1 及更早为主 |
| Architectury（多加载器） | 68 | 跨平台工程 |
| fabric-loom | 36 | Fabric 侧 |
| `net.neoforged.gradle.userdev` | 34 | 上一代官方插件 |
| 多模块工程（Common/Fabric/NeoForge 子项目） | 39 / 581 | 真正的多加载器只占 6.7% |

**工程特性分布**（含对应目录的仓库数）：

| 特性 | 仓库数 | 占比 |
|---|---|---|
| Mixin（字节码注入） | **421** | 72% |
| 客户端专属代码（client/） | 313 | 54% |
| 配置系统（config/） | 276 | 47% |
| 网络通信（network/） | 266 | 46% |
| 公开 API 包（api/） | 185 | 32% |
| 数据驱动内容（data/） | 154 | 27% |
| 实体（entity/） | 151 | 26% |
| 世界生成（worldgen/） | 119 | 20% |
| **Datagen（数据生成）** | 85 | 15% |

---

## 三、四个整合包的对照表

| 整合包 | 版本 | mod 数 | 找到 GitHub | 对照表 |
|---|---|---|---|---|
| 璇穹之歌 | 1.21.1 / NeoForge | 386 | **298** | `对照表/整合包Mod-GitHub对照表.md` |
| [FIDR]暗涌：深岩恐惧 | 1.20.1 / Forge 47.4.16 | 148 | **119** | `对照表/整合包Mod-GitHub对照表-FIDR暗涌1.20.1.md` |
| 星轨重铸：残响（航空学） | 1.21.1 / NeoForge | 347 | **324** | `对照表/整合包Mod-GitHub对照表-星轨重铸1.21.1.md` |
| All the Mods 10 | 1.21.1 / NeoForge | 491 | **408** | `对照表/整合包Mod-GitHub对照表-ATM10.md` |
| **合计（去重）** | — | 1372 条 | **591 个唯一仓库** | `对照表/四个整合包Mod-GitHub总表.csv` |

未找到的以闭源 mod（Xaero 系列、DungeonsArise、Macaw 系列、TaCZ 的部分配套）和中文作者未开源的附属为主。

---

## 四、从 591 个仓库里看到的生态规律

1. **`moddev` 插件已是 1.21 生态标准**（234 个仓库使用），ForgeGradle 基本只出现在 1.20.1 及更早的工程里；`userdev` 属于过渡期产物。新工程直接用 `net.neoforged.moddev`。
2. **Mixin 是标配而不是"黑魔法"**：72% 的仓库带 mixin。大 mod 的成熟做法是"一个功能一个 mixin 配置 + `IMixinConfigPlugin` 开关"（FerriteCore、ModernFix、CreateBigCannons、ElectroEnergetics 都是这个模式）。
3. **"库 + 内容"分离是团队化 mod 的标准架构**：Moonlight→Supplementaries、L2Library→莱特兰全系、PuzzlesLib→Fuzs 系列、SophisticatedCore→三件套、Blueprint→Abnormals 系列、Collective→Serilum 200+ 小 mod。**一个人做多个 mod 时，这个模式能省掉 80% 重复代码。**
4. **Datagen 只有 15% 的仓库在做**——这也是中文 mod 生态与欧美大 mod 差距最明显的一处。做 datagen 的工程（Farmer's Delight、Create、TouhouLittleMaid、Kaleidoscope）内容变更成本显著更低。
5. **多加载器是少数派**（6.7%），真要做时的两种主流方案：buildSrc 约定插件 + 共享源码源集（FerriteCore），或 Stonecutter 预处理多版本（YACL、MidnightLib、TouhouLittleMaid 部分工程）。
6. **对外 API 三件套**：32% 的仓库有 `api/` 包，标配是"注解/接口声明扩展点 + ServiceLoader 跨平台 + 只导出 api 包的 apiJar"（Jade、Curios、GeckoLib、Iceberg、YUNGs-API 都是）。

---

## 五、精选阅读清单（32 份报告，按主题）

> 路径均为相对本文件夹，例如 `分析报告/_分析报告/Creators-of-Create__Create.md`

**架构与注册体系**
- `分析报告/_分析报告/Creators-of-Create__Create.md` — Create：Registrate 注册体系、SmartBlockEntity 行为组合、Ponder 教学系统
- `分析报告/_分析报告/CaffeineMC__sodium.md` — Sodium：ServiceLoader 平台抽象、帧预算调度、数据驱动 Mixin 开关
- `分析报告/_分析报告/architectury__architectury.md` — Architectury：`@ExpectPlatform` 跨加载器抽象、事件桥接
- `分析报告/_分析报告/malte0811__FerriteCore.md` — FerriteCore：Mixin 工程化教科书（目录即开关 / postApply 改字节码）
- `分析报告/_分析报告/embeddedt__ModernFix.md` — ModernFix：注解处理器生成 mixin 配置、编译期客户端校验

**实体与 AI（你的主攻方向）**
- `分析报告/_分析报告/TartaricAcid__TouhouLittleMaid.md` — 东方女仆：Brain 双轨制（原版 Brain + 可插拔任务注册）、GeckoLib 集成、60+ 网络包组织
- `分析报告/_分析报告/AlexModGuy__AlexsMobs.md` / `AlexModGuy__AlexsCaves.md` — Alex 系列：自定义生物群系与生物
- `分析报告/_分析报告/lender544__new1.20.1.md` — 灾变：Boss 战设计（17 万行大工程）
- `分析报告/_分析报告/bonsaistudi0s__Creeper-Overhaul.md`、`Enderman-Overhaul.md` — 重生系列：原版生物变体重制
- `分析报告/_分析报告/Luke100000__ImmersiveAircraft.md` — 载具实体物理

**库 / 前置 / API 设计**
- `分析报告/_分析报告/Snownee__Jade.md` — Jade：插件 API（注解声明 + 归属校验）、请求-应答网络
- `分析报告/_分析报告/TheIllusiveC4__Curios.md`、`TheIllusiveC4__Caelus.md` — 槽位/飞行能力 API
- `分析报告/_分析报告/bernie-g__geckolib.md` — GeckoLib：渲染数据管道（GeoRenderState + DataTicket）、动画状态机
- `分析报告/_分析报告/YUNG-GANG__YUNGs-API.md` — YUNG's API：`@AutoRegister` 注解注册、结构装配器
- `分析报告/_分析报告/MehVahdJukaar__Moonlight.md`、`MehVahdJukaar__Supplementaries.md` — 库与内容的分工范本
- `分析报告/_分析报告/Minecraft-LightLand__L2Library.md` — 莱特兰：jarJar 多模块库（l2core/l2serial/l2tabs）
- `分析报告/_分析报告/SuperMartijn642__CoreLib.md` — 注解注册框架 + GUI Widget 框架 + 自研 datagen

**科技 / 工业（1.20.1→1.21 迁移必读）**
- `分析报告/_分析报告/mekanism__Mekanism.md` — 模块化大工程（26 万行）
- `分析报告/_分析报告/AppliedEnergistics__Applied-Energistics-2.md` — AE2：网格存储、自定义注册表
- `分析报告/_分析报告/BluSunrize__ImmersiveEngineering.md`、`AztechMC__Modern-Industrialization.md`、`Team-EnderIO__EnderIO.md`
- `分析报告/_分析报告/P3pp3rF1y__SophisticatedCore.md` — 升级系统框架（可组合升级 + 存储 API）
- `分析报告/_分析报告/Darkhax-Minecraft__BotanyPots.md` — 数据驱动的作物适配

**战斗 / 属性 / 数据驱动**
- `分析报告/_分析报告/Iron431__irons-spells-n-spellbooks.md` — 法术书：数据驱动法术与属性
- `分析报告/_分析报告/Shadows-of-Fire__Apotheosis.md`、`Apothic-Attributes.md`、`Placebo.md` — 词缀/属性系统的实现与前置库
- `分析报告/_分析报告/MCModderAnchor__TACZ.md` — 枪械：数据包格式、Lua 动画状态机、基座模型定位组

**世界生成 / 结构**
- `分析报告/_分析报告/TelepathicGrunt__RepurposedStructures.md`、`TelepathicGrunt__StructureLayoutOptimizer.md`
- `分析报告/_分析报告/YUNG-GANG__YUNGs-Better-Fortresses.md` — 结构 mod 标准范式（Jigsaw + 结构集注入）
- `分析报告/_分析报告/McJtyMods__LostCities.md` — 程序化城市生成
- `分析报告/_分析报告/DynamicTreesTeam__DynamicTrees.md` — 动态生长系统

**中文作者工程（贴近你的社区）**
- `分析报告/_分析报告/KaleidoscopeMods__KaleidoscopeCookery.md` — 森罗物语：厨房（NeoForge 1.21.1 工程组织）
- `分析报告/_分析报告/0999312__umapyoi.md` — 赛马娘：数据驱动角色
- `分析报告/_分析报告/Minecraft-LightLand__L2Hostility.md` — 怪物词条系统
- `分析报告/_分析报告/Creators-of-Aeronautics__Simulated-Project.md`、`ryanhcode__sable.md` — 航空学物理核心

**Create 附属开发**（星轨重铸包里有 55+ 个开源 Create 附属）
- `分析报告/_分析报告/mrh0__createaddition.md` — Create 附属标准骨架（机器四件套 + Ponder + 通用同步协议）
- `分析报告/_分析报告/DragonsPlusMinecraft__CreateEnchantmentIndustry.md` — 同一作者四个附属的统一风格
- `分析报告/_分析报告/Cannoneers-of-Create__CreateBigCannons.md` — 6 万行大型附属：自建同步注册表、49 个 mixin 按依赖门控
- `分析报告/_分析报告/hlysine__create_connected.md`、`copycats-plus__copycats.md`

---

## 六、使用方法

1. **按主题找仓库** → 打开 `分析报告/_分析报告/README-索引.md`，10 个分类（性能优化 / 库前置 / Create 附属 / 科技工业 / 实体 AI / 战斗魔法 / 世界生成 / 食物生态 / GUI 客户端 / 玩法系统），每行给出报告与卡片链接。
2. **读报告** → 报告里所有 `文件:行号` 引用都指向 `源码库/_参考仓库/<owner>__<repo>/...`，本地直接打开对照。
3. **只看规模/结构** → 打开 `分析报告/_分析报告/_卡片/<owner>__<repo>.md`（580 个仓库全有：文件数、行数、包结构、主类、构建插件、MC 版本、许可证）。
4. **查某个 mod 的仓库** → `对照表/` 下四个包的表格；`四个整合包Mod-GitHub总表.csv` 可排序筛选（含 Modrinth 下载量、是否有报告/卡片）。
5. **复现或换包重跑** → `研究脚本/`：
   - `_pack_research.py <key> <pack.json>` — 从 modrinth.index.json 解析仓库（Modrinth API + jar 元数据 Range 提取 + git ls-remote 校验）
   - `_atm10_resolve.py` / `_atm10_search.py` — CurseForge manifest → 名称 → 仓库
   - `_bulk_clone.py` — 批量稀疏克隆（只拉源码，省磁盘）
   - `_make_cards.py` — 生成速览卡片与索引数据
   - `_gen_final_deliverables.py` — 生成对照表与总索引

---

## 七、已知边界

- **深度报告覆盖 322/591 个仓库**；其余 269 个（多为小型 QoL/优化/补丁类 mod）只有速览卡片。如需把这部分也做成深度报告，可复用 `分析报告/_分析报告/_模板.md` 的模板继续派发。
- 少数仓库的默认分支已跟随作者更新到 MC 26.x（如 `bl4ckscor3/Sit`），卡片与报告中已标注实际检出版本，注意 API 差异。
- `源码库/_参考仓库/` 为**稀疏检出**（只有源码与构建文件），不含贴图/音频/数据资源；需要完整内容时在各仓库目录里执行 `git sparse-checkout disable && git checkout` 即可补全。
- 数据结构原始档：`分析报告/_分析报告/_进度.json`（591 仓库的克隆状态/分层/报告映射）、`_卡片索引.json`（结构化统计源）。

---

## 八、扩展覆盖（2026-09-20）

四包之外，研究范围又扩到 **PCL2 里已安装的全部整合包**（23 个）。已有结论如下。

### 8.1 TeaCon 2026（1 个包，164 个 mod，全量反编译）

| 项目 | 结果 |
|---|---|
| Mod 清单 | 164 个（`unsup.ini` + packwiz `index.toml`/`*.pw.toml` 解析） |
| 仓库定位 | **143 个**（87 来源声明级 + 6 中等 + 50 默认采信）→ `对照表/TeaCon2026整合包Mod-GitHub定位.md` |
| 源码 | **164 个全部反编译**（CFR），**3,938,805 行**，在 `源码库/_参考仓库/_teacon_decompiled/` |
| 卡片 | 164 份 → `_teacon_decompiled/_卡片/` |
| 重点分析 | 7 个 mod 的深度报告 → `分析报告/_分析报告/TeaCon2026__重点Mod深度分析.md`（Minecraft Mod MCP、车万女仆 2.0 的 LLM agent、傀儡装配、AnvilCraft、NeoMTR、VoteMe、听B站） |

### 8.2 四包补漏（205 个无公开源码的 mod，反编译）

| 项目 | 结果 |
|---|---|
| 范围 | 璇穹之歌 91 + ATM10 76 + FIDR 25 + 星轨重铸 13 = **205 个** |
| 规模 | 约 **278 万行**（含星轨重铸后补的 13 个，约 12.7 万行） |
| 附带收获 | 从 jar 元数据里**回收 44 个仓库地址**（含此前克隆失败的 MFFS_Classic、EnderStorage、ExtremeReactors2、RFToolsBase、Modern-Industrialization 等） |
| 报告 | `分析报告/_分析报告/四包未定位Mod本地反编译补漏.md` |

星轨重铸缺的 13 个 jar 用**多镜像下载器**（`研究脚本/_downloader.py`：cdn.modrinth.com → cdn-raw → BMCLAPI；forgecdn 主备切换；**SHA512 校验**）从整合包索引直链补齐，13/13 成功，再反编译入库。

### 8.3 其余 15 个整合包（4478 个 jar 的清单）

| 整合包 | mod 数 | 元数据带仓库 |
|---|---|---|
| Infinity Legacy II | 505 | 307 |
| 乌托邦探险之旅 3.5.2 | 451 | 337 |
| SDBF | 360 | 177 |
| Immersive Fight 4.2.4 | 305 | 144 |
| 涟漪之篇·如涟漪之所见 | 291 | 118 |
| Sky Energy Tech 0.01 | 284 | 168 |
| 你好，新蒸程！V1.7.5 | 279 | 126 |
| ea | 278 | 130 |
| new age sky | 278 | 166 |
| New Age Science and Technology v1.9.9 | 263 | 157 |
| 通天之路 | 259 | 138 |
| NovaEngineering-World（**1.12.2 老包**） | 258 | 37 |
| 星罗棋布 | 241 | 117 |
| 龙之冒险：新征程 v2.3a | 235 | 123 |
| 愚者 | 191 | 112 |
| **合计** | **4478** | **2323（52%）** |

产物：逐包清单 `对照表/Mod清单__<包>.md`（15 份）、**新仓库 152 个** `对照表/剩余包_新仓库清单.md`（标注 12 个误匹配、**24 个深挖候选**）、**只有非 GitHub 地址的 524 个** `对照表/剩余包_非GitHub地址mod工作单.md`（CurseForge 201 / FTB 56 / Modrinth 34，可继续定位）。

**顺带修掉一个索引缺陷**：1.12.2 老包用 `mcmod.info`（而非 `mods.toml`），补上解析后 NovaEngineering-World 的「带仓库」从 3 个涨到 37 个、包内 mod id 覆盖 224/258。

### 8.4 工具已入库（2026-09-21）

`Downloads` 会被不定期清理，因此把当轮工具与数据搬进仓库：`研究脚本/` 新增 **`_downloader.py`**（通用下载器：多源回退 + sha512/sha1/md5/size 校验，支持 `--cf <fileId> <fileName>` / `--list` / `--head`）与 **`_jar_diff.py`**（两版 jar 的类级 CRC32 差异，用来回答"这次更新改了什么"），并把 `_index_packs.py`、`_decompile_jars.py`、`_annotate_repos.py`、`_index_local_jars.py`、`_fill_gaps_{1,2,3}.py` 一并归档；索引数据（4478 jar 索引、四包索引、TeaCon 164 个 packwiz 元文件等）在 `研究脚本/_数据/`，用法见 `研究脚本/README.md`。

> CurseForge 取元数据不用开浏览器：`https://api.cfwidget.com/minecraft/mc-mods/<slug>` 直连可读全部文件；下载走 `mediafilez.forgecdn.net/files/<id前4>/<id后4>/<文件名>`（文件名必须与 CF 一致，否则 403；该 CDN 不支持 Range）。

### 8.5 与 AI agent 生态的两份对照/设计文档（2026-09-22）

`分析报告/_分析报告/` 新增：`对照__whale-craft_vs_MinecraftModMCP.md`（两条"让 AI 进 MC"路线对照，§5 回答"能否同会话共用"，含三种配法）与 `设计__DSH插件移植ZCode_与_不干扰玩家的AI游玩.md`（DSH 插件移植 ZCode 的逐项映射与三处无对应物；"真看画面 + 不干扰玩家"的三种架构）。

> 结论速记：移植**工具层可照搬**（ZCode 插件以 `mcpServers` 提供工具），但 **preset 工具收窄 / 插件前端 UI / 凭据服务**没有对应物，**主动唤醒**要用 Stop-hook 阻塞或定时心跳替代；"不干扰"的正解是**二号客户端**（零代码）或**自研离屏相机 mod**（抄 SecurityCraft 的 `CameraFeed`），而不是在玩家的客户端上做输入注入。

### 8.6 下一步：开挖

[`深挖待办清单.md`](./深挖待办清单.md) 已列 18 条待办（含从本轮筛出的 5 条新候选：Chisel+CTM、语言进方块三方对照、Cardinal Components、结构 datapack 族、ETF/Player Animator）。建议从 **Domum Ornamentum（方块版材质拼接）** 开挖 —— 它与 47 类型调色板管线马上能对接。

---

## 九、给协作者：源码怎么拿（2026-09-24）

**本仓库只收录笔记与脚本，不含上游源码。** `源码库/` 已写进 `.gitignore`——599 个克隆合计 2.9 GB、其中 593 个自带 `.git`（嵌套仓库被 git 记成空指针，推上去队友 clone 下来是一堆空目录），把别人的源码搬运进我们的仓库也不合适。

拉源码（两条路，都需要本机有 `git` 与网络）：

```bash
py 研究脚本/_bulk_clone.py --dry-run   # 只验证清单与落地目录，不联网
py 研究脚本/_bulk_clone.py             # 全量：591 个仓库稀疏克隆（只拉源码，跳过贴图/音频）
bash 研究脚本/_clone_refs.sh           # 只要 10 个代表性仓库（浅克隆 + 自动挑 1.21.1 分支）
```

- 落地目录固定为 `源码库/_参考仓库/`（批量克隆再进 `_bulk/`），命名 `owner__repo`；报告与卡片里所有 `源码库\_参考仓库\...` 引用都指向这里。想换位置：设环境变量 `REF_REPO_DIR=<绝对路径>`。
- 清单是 `分析报告/_分析报告/_union_repos.json`（591 个 `owner/repo` → `{title, packs, dl}`）；克隆状态另有 `分析报告/_分析报告/_进度.json`。
- 脚本按 `dl`（Modrinth 下载量）倒序克隆，已存在的仓库跳过（幂等，可中断重跑）。

**复现不了的部分，提前说明**：`源码库/_参考仓库/_teacon_decompiled/`（164 个 mod，394 万行）与 `_pack_decompiled/`（205 个 mod，约 278 万行）是**闭源 jar 的反编译产物**——它们的来源是整合包里的二进制，不是公开仓库，既不在本仓库内也无法用脚本重新生成。需要对照这部分结论时得找我要原始 jar 与 `_downloader.py` 的下载清单。少数报告的引用指向这些目录，读到时注意手上没有对应文件。

