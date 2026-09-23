# 对照：whale-craft vs Minecraft Mod MCP —— 两种"让 AI 进 MC"的路线

> 起因：2026-09-22 用户问「`https://github.com/yzi1b/whale-craft` 和 MCP 那个 mod 有什么区别」
> 对照对象：**whale-craft**（`yzi1b/whale-craft`，MIT，JS/Node）与 **Minecraft Mod MCP**（TeaCon 2026 包内 `minecraft-moddev-mcp-neoforge-26.1.2-0.2.0`，modid `mcpmod`，Java/NeoForge）
> 取材：whale-craft 为源码实读（本机克隆，`Downloads/_whalecraft_probe`）；MCP mod 为本库既有报告
> （`分析报告/_分析报告/TeaCon2026__重点Mod深度分析.md` §1，结论基于其反编译源码）。

## 一句话结论

**不是同类，连"住哪"都不同**：MCP mod 是**游戏内的 mod**，把**这个客户端**的眼睛和手（真实画面截图、反射操作 GUI 控件、注入键鼠）**通过一套自称 MCP、实为自定义的 HTTP 方言**交出去（见 §5.1 的订正：它没有实现 MCP 协议）；
whale-craft 是**宿主侧的 agent 插件**，用 **mineflayer** 以**一名玩家**的身份连服务器，把工具**原生注册**进 agent harness——它开篇就写明是**刻意不走 MCP** 的：

> `index.js:1-20`：目标：把"我"接进 MC 做成**一等公民**，而不是外挂一个 MCP 子进程。
> ① 原生工具 `mc_status / mc_say / mc_move / mc_map / mc_dig /…` 直接注册进 `ctx.tools`，**不再依赖 `@deepseek-ai/dsh-mcp-client`**。

## 1. 逐项对照

| 维度 | **Minecraft Mod MCP** | **whale-craft** |
|---|---|---|
| 形态 | **游戏内 mod**（Java / NeoForge，modid `mcpmod`，20 java / 1.07 万行） | **宿主侧插件**（JS / Node ≥22，`index.js` 3,733 行 + `client.js` 1,791 + `src/` 5,434 + 自检 3,371） |
| 住在哪 | **游戏进程内**（客户端里跑一个 HTTP 服务器） | **agent 进程内**（DSH harness 的插件；机器人是 harness 里的一个对象） |
| 身份 | 是这个**客户端本身**（能操作 screen、能截屏） | 是服务器上的**一名玩家**（协议层客户端，无画面） |
| 协议 | **自称 MCP，实为自定义 HTTP 方言**（`{"method":…,"params":{…}}`，params 值全为字符串；另有 `/api/*` 与 SSE；**全仓库 0 处 `tools/list`/`tools/call`/`initialize`** → 标准 MCP 客户端连不上，见 §5.1）；监听 **0.0.0.0:9876**（`McpHttpServer.java:80,86`；`-Dmcp.port` / `MC_MCP_PORT` 可改端口，不改绑定） | **不对外用 MCP**：`defineTool()` 把工具直接注册进 DSH（`ctx.tools`）；对外只有一个自带浏览器 UI 的 HTTP 面 |
| 集成方式 | 任何 MCP 客户端都能接（Claude/Cursor/自研 agent 皆可） | 只服务 **DSH 宿主**（`peerDependencies: @deepseek-ai/dsh-{llm,tools,schemastery}`，可选） |
| 工具数 | **40+**，四大正交面：观测 / GUI 操作 / 输入注入 / 游戏动作 | **30**，三层命名空间：`mc_*` 25 个（游戏内）+ `mc_kit_*`（image/memory/express）+ `mc_admin_*`（配置） |
| 能看什么 | **真实渲染画面**（LWJGL 反射 `glReadPixels` → `BufferedImage`，带缓存）、控件树（`enumerate_widgets`）、世界/玩家字段 | **字符地形图**（默认，`glyphMap`，`core.mjs:1340`，`@` 标自己）+ **由方块名合成的俯视彩色图**（`mapImage`，`core.mjs:1361`，不是截图） |
| 能做什么 | 点按钮 / 选列表 / 切页签 / **反射调用屏幕方法**（`call_screen_method`）/ 注入键鼠与滚轮 / 调视角 / 执行指令 / 放方块 / 接管控制权 | 走路 / 挖 / 建 / 用物品 / 说话 / 玩家聊天 / 背包 / 实体扫描 / 序列动作 / 读服信息 / 连局域网房间（`mc_lan` 只听原版局域网公告 `224.0.2.60:4445`） |
| 状态 | **无状态**：每次请求现场抓取，不记上下文 | **有会话状态**：每会话一个 bot 实例（不同会话可连不同服/账号，同会话单角色，有实例锁文件）+ 工作区长期记忆 `<工作区>/.whale-craft/` |
| 主动性 | **纯被动**：agent 不问就什么都不发生 | **主动唤醒**：`mc_watch` 单通道看门狗（`watchdog.mjs`）——空闲时唤醒、生成中**插话注入提示词**（明确"不模拟用户发言"），可配 `wakeOn` 矩阵（受击/被动位移/拾取/死亡/被传送/近距说话/心跳）、`topicWindowSec`（唤醒后短时内继续算同话题）、`observeWindowMs`（把连珠炮合并成一次唤醒省 token） |
| 安全 | ⚠️ **零鉴权**：全仓库无 token/auth，本机任何进程都能操作你的游戏 | 凭据只写宿主凭据库（`$DSH_HOME/.credentials.yaml`，**不进模型上下文/工具返回/HTTP 响应**）；HTTP 面带**回环 + DNS-rebinding/跨站**信任栅栏（`index.js:52-60`，与 dsh-serve 同款）；`mc_command` 有指令白名单（精确/正则/`*`）；MC 模式工具隔离（`mc_admin_*` 对 MC 会话硬拒） |
| 登录 | 不需要（就在你自己的客户端里） | 离线 / **第三方皮肤站（Yggdrasil）**；**Mojang 微软登录未实现** |
| 适用场景 | **测自己的 mod**：打开自己的 GUI → 点按钮 → 截图断言；也能自动化任何客户端操作（含单人） | **让 AI 真的去玩**：连服务器（含局域网房间）、和真人交互、长期任务、边玩边记事 |

## 2. 五个真正的分水岭

1. **"看"的来源不同 → 能问的问题不同。**
   MCP mod 拿得到**真实画面**（含自定义渲染、粒子、光影、你的 mod GUI），所以它能回答"我的 GUI 画得对不对"；
   whale-craft 拿不到画面（mineflayer 不渲染），它的图是**用方块名重画的示意图**，所以它能回答"周围地形/我的位置/附近实体"，
   但永远看不到界面长什么样、也看不到任何 mod 的视觉效果。
2. **"手"的落点不同。**
   MCP mod 的手落在**客户端本地**（渲染线程 + 反射 + 合成输入），因此能操作**任何屏幕**（原版或 mod 的），甚至能反射调屏幕方法；
   whale-craft 的手落在**服务器协议**上（`mineflayer` 的 dig/place/equip/自定义移动），受服务端规则约束——**它是一名正常玩家**，不是上帝。
3. **集成哲学：对外协议 vs 原生一等公民。**
   MCP mod 走"进程内 HTTP 服务"（本意是给外部 agent 用，但**没做 MCP 协议**，通用性其实要靠自己写适配器）换来**进程隔离**与"游戏内"位置；
   whale-craft 明确反对这条路（"不装 MCP 子进程"）→ 换来**零协议开销、原生工具语义、能主动唤醒/插话**（MCP 的请求-响应模型做不了"生成中插话"），
   代价是**绑死在一个宿主**上（DSH）。
4. **有没有"会话/身体/记忆"的概念。**
   MCP mod 无状态、无身份；whale-craft 有**每会话一具身体**、**工作区记忆树**（`README.md` 索引 + `RULES.md` 准则 + 任意文档，会话开始自动带进上下文）、**版本硬提示词**（随版本发布的固定提示，不可编辑）。
5. **鉴权与信任边界。**
   MCP mod 的 9876 端口**完全开放**（本库报告已标注为风险项）；whale-craft 把"凭据"和"能力"分开管（凭据进宿主凭据库、能力靠白名单/工具隔离），HTTP 面还有回环栅栏。

## 3. 共同点（两条路线都绕不过去的四件事）

两边都把 agent 的能力切成**同四个正交面**，这是"AI 操作 MC"的通用骨架：

| 面 | MCP mod | whale-craft |
|---|---|---|
| 观测 | `screenshot` / `get_world_info` / `enumerate_widgets` | `mc_map` / `mc_scan` / `mc_entities` / `mc_inventory` / `mc_status` |
| 动作 | `click_button_id` / `call_screen_method` / `execute_command` | `mc_move` / `mc_dig` / `mc_build` / `mc_act` / `mc_command` |
| 输入 | `press_key` / `type_text` / `mouse_drag` / `scroll` | `mc_say`（没有键鼠概念——它直接调协议） |
| 时序/控制权 | `enter_control_mode` / `exit_control_mode` / `pause_game` | `mc_watch`（何时该醒）/ `mc_wait` / 实例锁 |

差别在于**"输入面"**：MCP mod 必须模拟键鼠（因为它要驱动一个真实客户端），whale-craft 不需要（它直接发协议包）——这也是"游戏内 mod"与"协议机器人"最本质的分工。

## 4. 给你的选型建议

- **要验证你自己的 mod（GUI/渲染/交互手感）** → 只有 **MCP mod** 这条路（你的四门验证里"无头"那部分解决不了 GUI 与画面）。它正好补上"打开我的 GUI → 点按钮 → 截图断言"。
- **要让 AI 去服务器里玩、陪玩、长期挂机做任务** → **whale-craft**；而且它是 **DSH 插件**（`dsh plugin --profile web add github:yzi1b/whale-craft`），装进你自己的 harness 是一条命令，比接 MCP 少一层。
- **两者可以并存**：MCP mod 管**客户端**（看画面、点 GUI），whale-craft 管**世界**（这具身体干什么）。同机同服时，agent 甚至能"看客户端截图 + 让 bot 动手"。
- **想抄工程**：MCP mod 抄 **HTTP+SSE 骨架 + 渲染线程调度 + 反射缓存**（跨版本客户端自动化）；whale-craft 抄 **单通道看门狗（唤醒/插话的设计动机与参数）、凭据与能力分离、字符图↔图像双通道按模型能力切换**。

## 5. 能否互补？一个会话里能同时用吗？（2026-09-22 追加）

**能，但不是"两个 MCP 工具并排挂上"那么简单**——有三道机制上的关口，逐条说清。

### 5.1 关口一：那个 mod 其实**不是** MCP 协议（本文 §1 的表述已订正）

2026-09-22 对着反编译源码复核：全仓库 grep **0 处** `tools/list` / `tools/call` / `initialize` /
`jsonrpc` / `protocolVersion`。它是**自定义方言**：请求体 `{"method":"click_button_id","params":{...}}`，
params 的值一律被**扁平化成字符串**（`McpMessageHandler.java:35-56`），响应按 `requestId` 回；
另有 `/api/{screenshot,cmd,status,events}`（events 是 SSE）和 `/`、`/index.html`、`/debug` 调试页。

→ **所以不能把它当 MCP 服务器挂进 DSH**（`@deepseek-ai/dsh-mcp-client` 连不上它）。要用它只有两条路：
**让 agent 用 `pwsh` + `curl` 直接打它的 HTTP**，或者**给它写一层薄适配器**（把 37 个方法翻译成 MCP 的
`tools/list` + `tools/call`）。
另有一层"控制模式"闸门：`ALWAYS_ALLOWED`（16 个只读/切换类方法，`McpMessageHandler.java:855-872`）
之外的方法要先 `enter_control_mode`（它挡手滑，不是安全边界）。

### 5.2 关口二：whale-craft 的 MC 模式是**无条件白名单**

`src/config.mjs:64-79` 写明：MC 模式默认**只放行** `mc_*` / `mc_kit_*` + 文件工具
（`read/write/edit/glob/grep/read_image`），宿主的 `pwsh` / `subagent` / `workflow` / `serve_*` **一律看不见**。
想额外开哪个就把名字写进 `mcMode.allowOtherTools`——注意它的两条限制（`:66-74`）：

- ⚠️ **只能"收窄"，不能凭空添加 preset 没挂的工具**（白名单之外本来就看不见）；
- 官方 `minimal`（whale-craft 自动建的「MC模式」就是复制它）**自带一个持久 shell**（`:301`），
  所以 `allowOtherTools: ["pwsh"]` 这条路是通的。

### 5.3 关口三：两具身体 + 一个世界，怎么摆

- **MCP mod 操作的是本机客户端**（单人世界里客户端即服务端）；**bot 要进同一个世界**才能互补：
  在游戏里「对局域网开放」，whale-craft 用 `mc_lan` 自动发现再 `mc_connect` 进来（它 README 明写支持）。
- **两具身体必须交代清楚**：MCP 工具动的是**你自己的角色**，`mc_*` 动的是 **bot**。而 MC 模式注入的
  `RULES.md` 是**bot 视角**的准则，模型很容易以为只有一具身体 → 建议在会话里显式写明，或改 `.whale-craft/RULES.md`。
- **控制权**：你在用键鼠时，MCP mod 的注入会和你抢（它为此准备了 `enter_control_mode` / `exit_control_mode`）；
  对 bot 没影响（它是独立玩家）。

### 5.4 三种可用配法（按省事程度）

**配法 A —— 最省事，先跑通这个（推荐）**

MC 模式会话 + `mcMode.allowOtherTools: ["pwsh"]`，然后让 agent 用 `curl` 打那个 mod：

```
1) curl -X POST http://127.0.0.1:9876/api/cmd -d '{"method":"enter_control_mode"}'
2) curl -X POST http://127.0.0.1:9876/api/cmd -d '{"method":"screenshot_to_file","params":{"path":"<工作区>\\shot.png"}}'
   → {"file":"<绝对路径>","size":N}            # 它自己建目录、写 PNG（McpMessageHandler.java:252-271）
3) read_image "<绝对路径>"                     # ← 看清楚：read_image 已在 MC 白名单里，不用额外开
4) mc_* 让 bot 在世界里做对应的事（挖/建/说话）
```

**为什么这条特别顺**：`screenshot_to_file` 的产物是**磁盘上的 PNG**，而 whale-craft 的 MC 白名单**本来就放行
`read_image`** —— 于是"看客户端画面"这一环零配置就能接上；你只需要为 `curl` 开 `pwsh` 一个口子。
（`screenshot` 另一个方法返回的是 `data:image/png;base64,…` 字符串，走它反而要自己解码。）

**配法 B —— 最像"一套工具"（要写代码）**

给那个 mod 写一层 **MCP 适配器**（HTTP 转发 + 声明 37 个方法的参数表），作为 MCP 服务器挂进 DSH，
再把这个工具组加进 `mcMode.allowOtherTools`。工作量不大（一个转发进程 + 一张参数表），
换来的是"两套工具在同一命名空间里、模型不用学 curl"。

**配法 C —— 不用 MC 模式（最省配置，但丢东西）**

换一个**不在 `mcModePresets` 里**的 preset：whale-craft 的工具仍然**全局可见**
（`index.js:6-7`：注册进 `ctx.tools`，所有会话可见），同时挂 MCP/适配器 → 两套工具齐活；
代价是丢掉 MC 模式的**提示词注入 / `.whale-craft/` 记忆 / 权限收窄 / 看门狗 job 挂载**。

### 5.5 两个必须知道的风险（顺带订正本库另一处报告）

- 那个 mod 监听 **`0.0.0.0`**（`McpHttpServer.java:80,86`）且**零鉴权** → **局域网内任何机器**都能接管你的客户端
  （不是"本机"那么温和）。要长期开着，建议自己包一层 token 并改绑 `127.0.0.1`
  （本库 `TeaCon2026__重点Mod深度分析.md` §1 已按此订正）。
- whale-craft 那边：bot 用的账号在**别人服务器**里是一个真人行为的玩家——别拿正版账号在公共服上跑实验。

---

## 6. 未确认 / 边界

- whale-craft 的运行时行为**未实测**（本报告只读源码与 README；未安装、未连服）。
- MCP mod 的事实引自本库既有报告（基于其**反编译**源码），本次未重读反编译产物。
- whale-craft 的工具清单来自 `index.js` 的字符串常量与 README 表格（README 说 29 个，源码里能抓到 30 个名字，差额 1 属命名空间前缀或别名，未逐一对齐）。
- whale-craft 是否会在将来暴露 MCP（比如给非 DSH 宿主用）：README/源码未见相关计划，仅有"不依赖 dsh-mcp-client"的表述。
- §5 的三种配法与结论基于**源码实读**（协议/白名单/截图接口都带 `文件:行号`），但**未实测**（没有真的同会话跑通两个系统）；配法 A 的 curl 命令是按 `McpMessageHandler` 的解析规则推出来的，首次真跑时请以实际返回为准。
- 依赖与规模：whale-craft 直接依赖只有 `mineflayer` + `vec3`（可选 `sharp`），**没有 pathfinder**——移动是自研的（`core.mjs` 里明确说"刻意不用 `bot.creative.flyTo`，它有两处硬伤"）。
