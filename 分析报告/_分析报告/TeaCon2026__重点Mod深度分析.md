# TeaCon 2026 重点 Mod 深度分析（7 个）

> 对象：TeaCon 2026 整合包（MC 26.1.2 / NeoForge 26.1.2.87）中**技术上有代表性、或与你的方向（修仙 mod / NPC 与实体 AI / Create 附属 / 美术管线 / AI-agent 工作流）对口**的 7 个 mod。
> 源码：全部为**反编译产物**（CFR），位于 `源码库/_参考仓库/_teacon_decompiled/<mod>/`；每 mod 另有结构速览卡片 `_卡片/`。
> 方法说明：本次**未使用子 agent**（环境要求先选"思考档位"，当前会话被拦），以下分析由我逐个模块实读 + grep 交叉验证得出；行号引用以反编译产物为准，Kotlin 项目会有 `Intrinsics`/`Companion` 噪声，引用类名比行号可靠。
> 挑选理由与"还想看但没做的"见文末第 8 节。

---

## 1. Minecraft Mod MCP —— 把游戏变成 AI agent 可操作的环境 ⭐ 最值得你细看

`xyz.langyo.minecraft.mcp`，modid `mcpmod`，20 个 java / 1.07 万行。**在游戏内跑一个 MCP（Model Context Protocol）服务器**，让 AI agent 直接"看屏幕、点按钮、按键、读世界状态"。

- **传输层**：`common/McpHttpServer.java` —— 自研 HTTP 服务器（`com.sun.net.httpserver`），**POST 收 JSON + SSE（`text/event-stream`）推流**（:374 只允许 POST、:446 SSE 响应头）；端口默认 **9876**。⚠️ **2026-09-22 订正（本文原写"即 MCP 的 Streamable HTTP 传输"，是误判）**：全仓库 grep **0 处** `tools/list` / `tools/call` / `initialize` / `jsonrpc` / `protocolVersion` —— 它**没有实现 MCP 协议**，而是一套**自定义方言**：请求体 `{"method":"click_button_id","params":{...}}`，params 的值一律被**扁平化成字符串**（`McpMessageHandler.java:35-56`），响应按 `requestId` 回（`sendResponse`）；另有 `/api/{screenshot,cmd,status,events}`（events 是 SSE）与 `/`、`/index.html`、`/debug` 的调试前端。**含义：标准 MCP 客户端（含 DSH 的 `@deepseek-ai/dsh-mcp-client`）无法直接连它**，要接得自己写一层适配器或走 HTTP（`McpConfig.java:7`，可用 `-Dmcp.port` 或环境变量 `MC_MCP_PORT` 覆盖）；另自带 `/`、`/index.html`、`/debug` 调试前端（:537）。
- **协议层**：`common/McpMessageHandler.java`（875 行）与 `McpProtocol.java` 定义工具集，从字符串常量可读出**完整工具面**（40+ 个）：
  - 观测：`screenshot` / `screenshot_to_file`、`get_player_info` / `get_world_info` / `debug_fields`、`enumerate_widgets` / `get_screen_buttons`
  - GUI 操作：`click_button_id` / `click_button_index` / `select_list_item` / `switch_tab` / `close_screen` / `call_screen_method`（反射调用屏幕方法！）
  - 输入注入：`press_key` / `type_text` / `paste_text` / `open_chat` / `press_enter` / `hotkey` / `mouse_drag` / `scroll` / `scroll_at` / `overlay_click` / `release_mouse` / `enter_control_mode` + `exit_control_mode`（接管控制权）
  - 游戏动作：`set_view_angle` / `look_delta` / `set_gamemode` / `execute_command` / `place_block` / `pause_game` / `ping`
- **实现手法**：全程**反射**（`ReflectionHelper` / `ReflectionCache` 1041 行）以免编译期依赖；截图走 LWJGL 反射 `GL11.glReadPixels` → `BufferedImage` **带缓存**（`ScreenshotHelper.java:205,254,282`）；所有注入经 `ReflectedInputHandler` + `RenderThreadExecutor` **调度到渲染线程**执行（`ModDevMcpMod.java` 里 `executeOnRenderThread`、5 秒延迟后启动 HTTP 线程）。
- **值得学**：①"游戏即环境"的 agent 接口设计——把截图、控件枚举、输入注入、状态查询做成四个正交工具面；②用反射 + 渲染线程调度实现跨版本客户端自动化；③自带 `/debug` 网页便于人工验证 agent 看到的东西。
- **风险**：**没有任何鉴权**（全仓库 grep 无 token/auth），且监听地址是 **`0.0.0.0`**（`McpHttpServer.java:80,86`：`new InetSocketAddress("0.0.0.0", port)`）——不是"本机任何进程"，而是**局域网内任何机器**都能通过 9876 端口接管你的游戏（可用 `-Dmcp.port`/`MC_MCP_PORT` 换端口，但不改绑定）；另有一层"控制模式"闸门：`ALWAYS_ALLOWED` 之外的 21 个方法要先 `enter_control_mode`（:855-872、:78-80），它挡的是"手滑"，**不是**安全问题。建议只在本地/断网环境用，或自己包一层 token + 改绑 127.0.0.1。
- **对你的用处**：你的 mod 测试目前靠 `runData`/GameTest 这类无头验证（你的记忆里也写着"headless verification is required"）；这套东西正好补上"**有没有 GUI、渲染对不对、交互手感如何**"那一环——让 agent 截图 + 点按钮，就能自动跑"打开我自己的 GUI → 点按钮 → 看结果"。可直接抄的是它的 HTTP/SSE 骨架 + 渲染线程调度。

## 2. 车万女仆 2.0（TouhouLittleMaid 2.0）—— 从"女仆 mod"变成"LLM agent 框架"

`com.github.tartaricacid.touhoulittlemaid`，1854 java / 15 万行。与你已分析过的 1.5.3 相比，2.0 的结构性变化是**新增了一整套 LLM agent 与内置 AI 游戏引擎**：

- **包结构（文件数）**：`client/` 357、`libs/` 329（内嵌 snakeyaml / JLayer(**MP3 解码**) / concentus(**Opus 编解码**)、`geckolib3/` 218（**自带 fork**，全库对 `software.bernie.geckolib` 引用为 0）、`entity/` 207、`ai/` 138、`network/` 85、`api/` 74、`compat/` 61。
- **LLM agent 框架**（`ai/{agent,manager,service}` 共 138 文件）：
  - `ai/service/llm/openai/` —— **OpenAI 兼容客户端**（`request/ChatCompletion`、`response/Message`），用 `LLMSite.LLM_HTTP_CLIENT`（`java.net.http`）异步调用；
  - `ai/agent/context/` —— 上下文提供者体系：`GameContextRegister` 注册、`MaidContexts`/`WorldContexts` + 工具式上下文（`EffectsMaidContexts`、`EquipmentMaidContexts`、`NearbyEntityMaidContexts`、`PositionMaidContexts`、`UserContexts`）——**把游戏状态切成可插拔的 prompt 片段**；
  - `ai/agent/tool/` —— **function-calling 工具**：`QueryGameContextTool`、`QueryMinecraftWikiTool`（真的去查 `minecraft.wiki` / `zh.minecraft.wiki` 的 API！）、`SwitchFollowStateTool`、`SwitchScheduleTool`、`SwitchSitTool`、`SwitchWorkTaskTool`（**让 LLM 直接切女仆的任务/作息/跟随状态**）；
  - `ai/agent/skill/` —— `SkillLoader`/`SkillParser`/`SkillBean`/`SkillInstance`：**技能用 YAML 定义**（这也是要内嵌 snakeyaml 的原因），可加载外部技能包；
  - `ai/manager/setting/papi/` —— 类 PlaceholderAPI 的**提示词模板变量**（`PapiReplacer`/`StringConstant`），以及 `AutoGenSettingCallback`（**用 LLM 自动生成女仆人设**）。
- **内置 AI 游戏引擎**：`api/game/chess/{Position,Search,Evaluate,Util}`、`api/game/gomoku/{AIService,ZhiZhangAIService}`、`api/game/xqwlight/{Position,Search,Util}`（xqwlight = 中国象棋引擎移植）——女仆能跟你下棋/五子棋，**引擎是本地跑的不需要联网**。
- 其余沿用 1.5.x 的骨架：仍是原版 Brain（276 个文件涉及 `MemoryModuleType/SensorType`）、Molang（217 文件）、自研 Bedrock 模型加载；`client/gui/entity/maid/ai/AIChatScreen`（679 行）是聊天界面。
- **值得学**：①**上下文/工具/技能三分**——这套切分让"LLM 驱动游戏实体"变得可维护（上下文=只读观察、工具=可写动作、技能=数据化行为包）；②把 wiki 查询做成工具（LLM 不懂的游戏机制让它自己查）；③技能用 YAML 外置，整合包作者可扩展。
- **坑**：LLM 调用必须在客户端/独立线程且要限流（否则卡 tick）；工具写动作（切任务/作息）要有服务端权威校验，否则等于把实体控制权交给模型。
- **对你的启示**：你的 Player2NPC / 殖民地 AI 若要做"自然语言指挥 NPC"，这套 `context + tool + skill` 是可以直接照搬的形状；另外"内置小游戏引擎"（象棋/五子棋）是给 NPC 加"可玩内容"的廉价方案。

## 3. 傀儡装配（Modular Golems）—— 数据驱动的模块化实体

`dev.xkmc.modulargolems`（L2 莱特兰团队 xkmc 出品），470 java / 2.3 万行。

- **数据驱动组装**：`content/config/GolemMaterial.java`、`GolemMaterialConfig.java`、`GolemPartConfig.java` —— 材质与部件都是**配置驱动**，`GolemMaterialConfig.mayApply(part, material)` 决定"某材质能否做某部件"；实体的部件携带材质（`GolemPart.getMaterial(stack)`），**属性/外观由部件×材质组合决定**。
- **实体骨架**：`content/entity/common/AbstractGolemEntity.java`（**1440 行**，全部傀儡的基类）、`GuardedEntity`（护卫/仇恨）、`ShieldUsingGolemEntity`、`SweepGolemEntity`（横扫攻击 + 专用菜单/屏幕控制 `SweepGolem{Menu,Screen,Overlay}Control`）；具体型：`MetalGolemEntity`、`DogGolemEntity`、`HumanoidGolemEntity`。
- **物品即"存档"**：`content/item/golem/GolemHolder.java`（549 行）——**傀儡被装在一个物品里**（部件、材质、升级全部存物品组件），放下即召唤、收回即保存；`GolemDisintegrateMenu/Screen`（拆解台）负责拆回零件。
- **跨 mod 材质集成**：`compat/materials/`（`CompatManager`/`ClientCompatManager`/`ModDispatch`）把**其他 mod 的材质**（l2complements、composite_material、create、cataclysm、twilightforest、alexscaves 的贴图都在 assets 里）接成傀儡材质 —— 这是"你的东西用别人的材料做"的标准做法。
- 工程细节：用 **Registrate**（与 Create 同一套注册 DSL）注册（`init/registrate/GolemItems`）；Patchouli 手册 232 个文件；111 配方、140 成就。
- **值得学**：①物品当载体存实体状态（省一套实体存档逻辑）；②材质/部件的 **`mayApply` 准入表**比硬编码 if 可扩展；③跨 mod 材质走 compat 适配层。
- **对你的启示**：修仙 mod 的"傀儡/法器"若要做"用不同灵材拼装"，这套 `部件 × 材质 → 属性/外观` 的模型与 `mayApply` 准入表可直接借鉴；"法器存物品、法宝存实体"的双向转换也正好是修仙题材的常见玩法。

## 4. 铁砧工艺（AnvilCraft）—— 大而规整的工业/魔法体系

`dev.dubhe.anvilcraft`，2094 java / 19.8 万行（TeaCon 主力 mod，另有 5 个附属）。

- **结构**：`block/` 421、`client/` 270、**`api/` 269**、`item/` 188、`mixin/` 132、`recipe/` 109、`integration/` 103、`data/` 91、`network/` 84 —— `api/` 的细分很说明它的系统面：`tooltip(37)`、`recipe(25)`、`injection(20)`、`power(16)`、`itemhandler(16)`、`fluid(15)`、`block(15)`、`event(14)`、**`teslatower(11)`**、`heat(11)`、`entity(11)`、**`behavior(8)`**、`hammer(6)`、`amulet`（护符）、`chargecollector`、`portal`、`giantanvil`。
- **`api/behavior/` 有行为树**：`BehaviorTree.java` + `TreeNode`/`ExecutableTreeNode`/`PredicateTreeNode`/`SetTreeNode`/`ExecutionContext` —— 机器/实体的可组合行为（谓词节点 + 执行节点 + 集合节点），比一堆 if-else 高级。
- **能量与流体网络**：`api/energy/{EnergyHelper,IEnergyHandlerHolder,ItemFEStorage}`、`api/fluid/network/{FluidNetworkManager,FluidPipeNetwork,FluidNetworkScanner,ValveState,FluidContainerLookup}` —— 管线网络带扫描器与阀门状态，属于"自建物流/能量网"的完整实现。
- **数据驱动极重**：jar 内 **1566 个成就 + 1498 个配方**，核心玩法是 `anvil_collision/...`（铁砧砸击配方族，文件名里甚至出现 `anvil_tier_0_...128`）——即**"铁砧等级 × 材料碰撞 → 产物"** 全部做成数据，新增内容几乎不用写代码。
- 巨型机器：`SmartBlockPlacerBlockEntity`(3231 行)、`LargeCauldronBlockEntity`(1800，大锅)、`FishTankBlockEntity`(1272)、`CelestialForgingAnvilScreen`(1171，**天锻砧** 的 GUI)。
- **值得学**：①`api/` 的分包粒度就是"扩展点目录"（要看一个 mod 能被怎么扩展，读它的 api 子包名即可）；②把玩法做成配方族（铁砧碰撞表）而非硬编码；③行为树用于机器。
- **对你的启示**：炼丹/炼器若要"炉子等级 × 材料组合 → 产物"，照抄"配方族 + 准入表"的写法；能量/灵力网络可参考它的 pipe network 三件套（Scanner/Manager/Valve）。

## 5. NeoMTR（我的世界铁路 · 纸板箱特色）—— 一个 jar 塞了四个项目

1655 java / 27.7 万行，TeaCon 里代码量最大。实际内容是 **MTR 本体 + 蒸汽机车扩展 + Mozilla Rhino(JS 引擎) + Jetty(Web) + 自研渲染库**：

- **`cn/zbx1425/mtrsteamloco/`**（蒸汽机车，作者 zbx1425——你在几个包里都见过他：WorldComment / minopp / TeasupFlavorRequest）：`render/scripting/{ScriptHolder,ScriptResourceUtil,AbstractScriptContext}` —— 用**内嵌的 Rhino 跑 JS**（`rhinoCtx.evaluateString(...)`，`ScriptHolder.java:102`）让资源包**用脚本驱动列车渲染**（受电弓/门窗/轮组的动态表现）。这是"给资源包一门真语言"的做法。
- **`com/lx862/tprobe3/servlet/`**：`FrontendServlet` + `DepotServletHandler` + `JsonDataSerializer` + `TProbeHelper` —— 用 **Jetty 起一个本地 Web 前端**，把铁路/车辆段数据以 JSON 暴露给浏览器（游戏内的 `mtr/item/ItemDashboard` 是入口）。即"**在 mod 里嵌一个 Web 服务 + 前端**"。
- **`cn/zbx1425/sowcer/`**：自研批渲染库（`batch/{BatchManager,BatchType,ShaderProp,MaterialProp,EnqueueProp}`、`math/{Matrices,Matrix4f}`、`object/`、`shader/`）—— 面向"大量列车/轨道模型"的批量渲染。
- 数据侧：930 模型、562 音效、501 贴图、298 配方（MTR 的列车/轨道配置一贯靠数据包）。
- **值得学**：①**嵌入 JS 引擎让资源包可编程**（比 JSON 表达力强得多，代价是要打包 Rhino ~几千行）；②**嵌入 Web 服务做数据面板**（比在游戏里写 GUI 快得多）；③批渲染库自研（列车数量大时的必要投资）。
- **坑**：三种内嵌（Rhino/Jetty/sqlite）让 jar 体积与攻击面都变大；JS 脚本必须沙箱化（Rhino 的 `ClassShutter` 之类），否则资源包等于任意代码执行。

## 6. VoteMe —— TeaCon 现场投票系统（Redis + Reactor）

`org.teacon.voteme`，1256 java / 17.2 万行——其中**绝大部分是内嵌的 `lettuce`（Redis 客户端）+ `reactor`（响应式流）**，本体只有 `category/command/crafting/item/network/roles/screen/sync/vote` 十来个包。

- **投票靠实体物品**：`item/VoterItem` + `item/CounterItem`，两者都带数据组件 `ArtifactID`（UUID）；`VoterFromCounterRecipe` 把"计数器"合成"投票器"；`ShowVoterPacket` 在客户端展示。
- **服务端是中心化的**：走 **Redis（Lettuce）** 存票，网络栈全异步（Reactor）——这样茶会现场的**网页大屏**可以实时读票数。
- **权限与角色**：`roles/`、`command/VoteMePermissions`、`command/{Alias,Artifact}ArgumentType`（自定义命令参数类型）；`category/VoteCategory(Handler)` 把投票分门别类（最佳美术/最佳玩法…）。
- **值得学**：①**活动类 mod 的正确形态**：游戏端只做"身份 + 物品 + 界面"，计票与展示交给外部服务（Redis/网页），避免把并发与抗刷票硬塞进 MC；②17 万行里 90% 是成熟第三方（Redis/Reactor）——**不自研基础设施**是它的关键决策；③用自定义 `ArgumentType` 提供好用的管理命令。

## 7. 网络音乐机：听听B站 —— 游戏内流媒体播放

`com.zhongbai233.net_music_can_play_bili`，676 java / 10.2 万行（12k 本体 + 内嵌解码/网络库）。

- **B 站集成完整度惊人**（`bili/` 包 20+ 类）：`BiliApiClient`(919) + `BiliApiProperties/ResponseParser`（接口请求与解析）、**`BiliLoginManager` + `BiliCredentialCodec/Store`**（登录与会话凭据的编解码与存储）、`BiliMachineIdentity`（设备标识）、`BiliAudioResolver`（取音轨直链）、`BiliCdnSelector`（多 CDN 选路）、**`BiliLiveStreamResolver` + `BiliLiveAudioStreamHandler` + `BiliLiveRoomInput`（直播间音频流）**、`BiliSubtitleApi`（字幕）、`DolbyAudioHandler`(964)、`BiliPlaybackDiagnostics`、`BiliRequestHeaders`（请求头/签名）、`BiliSongInfoSanitizer`（歌名清洗）。
- **客户端播放**：`client/ClientAudioOutputRegistry`(1025) 统一管理音频输出、`client/MP4HandheldVideoClient`(913)（**手持设备放视频**）、`client/renderer/ControlConsoleRenderer`(1059)（控制台 3D 模型）。
- **服务端治理**：`gui/WhitelistReviewScreen`(1023) + `server/` —— **服务器的点歌白名单审核流程**（管理员审歌）；`blockentity/ModernTurntableBlockEntity`(1019) 是场景里的"现代唱机"。
- **值得学**：①第三方平台集成的工程化：**接口 / 凭据 / 选路 / 诊断 / 清洗**分层，且带 `PlaybackDiagnostics` 便于线上排障；②把"外部内容"变成"服务端可审核"（白名单审核 GUI）；③音频/视频两条链路并存（手持设备播视频）。
- **坑**：凭据要加密存（有 `CredentialCodec`，但客户端存储始终是风险面）；版权与 ToS 风险自担；连续流播放要防主线程阻塞（用独立线程 + 缓冲）。

---

## 8. 横向总结与"还想看"的清单

**这 7 个 mod 给出的可复用做法（按通用性排序）**：
1. **物品当载体**（傀儡装配的 GolemHolder、VoteMe 的 VoterItem）：把复杂状态塞进物品组件，省掉一套实体/方块存档。
2. **数据化 + 准入表**（AnvilCraft 的铁砧配方族、傀儡装配的 `mayApply`）：新增内容尽量落在 JSON/配置，代码只留"准入与合成规则"。
3. **LLM/agent 接口三件套**（TLM2 的 context/tool/skill；Mod MCP 的观测/输入/状态工具面）：可读上下文 + 可写工具 + 数据化技能。
4. **不自研基础设施**（VoteMe 用 Redis+Reactor、TLM2 内嵌 codec、NeoMTR 内嵌 Rhino/Jetty）：把成熟的第三方包进来，把自己的代码留给玩法。
5. **渲染与表现的两条路**：自研批渲染（sowcer）与"脚本驱动渲染"（NeoMTR 的 Rhino）。
6. **审核与治理**（听B站的白名单审核、VoteMe 的权限节点）：面向多人/活动场景必须的服务端治理面。

**对你的 5 条具体启示**：
- 女仆 2.0 的 `context + tool + skill` 可直接作为你 NPC 自然语言指挥的骨架；`QueryMinecraftWikiTool` 这种"让模型自己查 wiki"的做法能省掉大量 prompt 工程。
- Mod MCP 补上了你"无头验证"缺的那一环（GUI/渲染/交互），且它的 HTTP+SSE 骨架与渲染线程调度可单独复用。
- 修仙的"傀儡/法器"设计：`部件 × 材质 → 属性/外观` + `mayApply` 准入 + 物品当载体，这三条一次全都能用上。
- 炼丹/炼器：照 AnvilCraft 的"配方族 + 等级表"写，别硬编码。
- 若你要做"灵气网络/传送网络"：AnvilCraft 的 pipe network（Scanner/Manager/Valve）+ NeoMTR 的 Web 面板是两个可抄的层。

**还想看但本轮没做的**（都已在本地反编译，随时可开工）：`节气 EclipticSeasons`（5.6 万行，季节/天时系统）、`AstralCraft 吉星工艺`（5.8 万行）、`SuperPipeSlide 超级管道速滑`（10.3 万行，为什么这么大值得一查）、`LiveHelper`（6.9 万行，B站直播联动）、`shengpi 圣脾`（TT432 出品）、`Dungeon-Infinity 无限地牢`（1.3 万行）、`GensokyoOntology 幻想存有论`、`TheStreetism 街头主义`（Kotlin）。
