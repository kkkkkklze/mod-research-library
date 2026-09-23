# 设计答复：① DSH 插件能否移植到 ZCode ② 能否做出"真看画面 + 不干扰玩家"的 AI 游玩

> 起因：2026-09-22 用户两问 —— 「dsh 的插件能改成 zcode 用吗」；「用这两个（whale-craft + Minecraft Mod MCP）可以造出一个既能真的玩游戏看画面、又不干扰玩家操作的 mod 吗」。
> 取材：① ZCode 自身的扩展面文档（`zcode-guide 0.2.0` 的 `zcode-configuration-guide` / `diagnosing-hooks`、`plugin-creator 0.1.1` 的 `plugin-json-spec.md`、官方插件 `node-repl-host` 的清单与 README）；② whale-craft 源码实读（`源码库/_参考仓库/yzi1b__whale-craft`）；③ Minecraft Mod MCP 反编译源码（`_teacon_decompiled/minecraft-moddev-mcp-neoforge-26.1.2-0.2.0`）；④ `Geforce132/SecurityCraft` 源码（库内 `_bulk`）。

---

## 一、DSH 插件能改成 ZCode 用吗

**能，但只有"工具层"近乎照搬；另有三层没有等价物，必须重写或降级。**

ZCode 的扩展面就五类 + AGENTS.md（来源：`zcode-configuration-guide`）：**Skills**（目录 + `SKILL.md`）、**Commands**（`.md`）、**MCP**（`~/.zcode/cli/config.json` 的 `mcp.servers`，工作区在 `<repo>/.zcode/config.json`）、**Hooks**（`hooks.json`，需 `hooks.enabled: true`）、**Plugins**（目录 + `.zcode-plugin/plugin.json`，从 marketplace 安装）。
官方插件 `node-repl-host` 就是范式：**插件携带 MCP server**（`dist/mcp/server.js`）—— 它的工具面（`node_repl` 的 `js`）走的就是 MCP。

### 1.1 逐项映射

| whale-craft 用到的 DSH 面 | 用途 | ZCode 对应物 | 结论 |
|---|---|---|---|
| `defineTool()` 注册进 `ctx.tools`（`index.js:22`，`inject = ['webServer','tools']`） | 30 个 `mc_*` 工具 | **插件 manifest 的 `mcpServers`**（`.zcode-plugin/plugin.json` 可内联服务器配置，也可指向 `.mcp.json`）→ 每个工具 = 一个 MCP tool | ✅ 可移植，需重写工具声明为 MCP schema；**bot 逻辑原样复用** |
| `dsh.bundle.patch` → `cordis.patch.yml`；`dsh.profile.bundles` | 插件挂载 | `plugin.json` + 安装到 profile（marketplace） | ✅ 形状不同但语义等价 |
| `agent.cordis.yml` composition：preset 工具组修补（`patchToolGroupsIntoComposition`、`MC_PRESET_TOOL_GROUPS` = tool-fs/tool-jobs/present）、`agentPresets.copy()`、`mcModePresets` 白名单 | **按 preset 收窄工具面**（MC 模式只放行 `mc_*`/`mc_kit_*`+文件工具） | ZCode **没有 preset / composition / 工具组**这套概念（五类资源里没有） | ⚠️ **无法等价**：只能把"收窄"下沉到 MCP server 自己（按会话/开关拒绝），或靠 skill 按需加载 |
| `exports["./client"]` 浏览器 UI（`client.js` 1,791 行：状态条 / 强制停止 / MC设置页） | 人机界面 | ZCode **没有插件前端扩展面**（配置指南未列 UI 资源） | ⚠️ 降级：slash command + 工具返回状态；要图形界面只能自己起本地网页让用户点 |
| `$DSH_HOME/.credentials.yaml`（owner-only，凭据不进模型上下文） | 账密保管 | ZCode **无公开凭据服务 API** | ⚠️ 自己存本地文件（同样可不进上下文），安全性靠自己 |
| 工作区 `.whale-craft/`（`README.md` 索引 + `RULES.md` 准则）+ 会话开始注入（`injectWhaleCraftAgentsMd`） | 长期记忆 + 行事准则 | **`<repo>/AGENTS.md`（原生工作区指令）+ `~/.zcode/skills/`** | ✅ 天然对应，甚至更顺 |
| **看门狗**：后台 job → DSH **followup 唤醒同一会话**，生成中插话注入（`watchdog.mjs` 652 行） | 主动唤醒/插话 | ZCode **hooks 只有 7 个事件**（`SessionStart`/`UserPromptSubmit`/`PreToolUse`/`PermissionRequest`/`PostToolUse`/`PostToolUseFailure`/`Stop`），**`async` 无运行时效果（总是 inline）**；但 `additionalContext` 会注入对话，`Stop` 可请求继续（最多 3 次） | ⚠️ **最难的一块**，见 1.2 |

### 1.2 "主动唤醒"在 ZCode 里怎么落地（三种）

- **A. Stop hook 阻塞等待**（最接近原语义）：回合结束时 Stop hook 跑一个脚本，最多阻塞 N 秒（`timeout` 默认 60s，可配）去问 whalecraft 的 bot 进程"有事件吗"，有事 → 返回 `additionalContext` + 请求继续；没事 → 放行。等效"空闲时被唤醒"，代价是每次停都占一个 hook 进程最长 N 秒。
- **B. 定时心跳**（最稳、零改造）：用 ZCode 的**定时自动化**按固定间隔向会话注入一条固定提示（"检查 bot：有事就处理"），agent 再调 `mc_events` / `mc_watch` 取事件决定。比 DSH 的 job-followup 粗（定时而非事件即时），但完全不依赖未验证的机制。
- **C. 混合**：看门狗仍作为**插件侧常驻进程**跑（事件写文件/队列），由 A 或 B 去读——把"实时性"和"宿主限制"分开。

### 1.3 工作量拆解（按实读的 14,908 行）

- **可原样复用（约 60-70%）**：`src/core.mjs`（2,047 行 bot 核心：连接/移动/背包/动作/字符地形图/合成图像）、`watchdog.mjs`（唤醒判定矩阵）、`memory.mjs`、`accounts.mjs`、`ping.mjs`、`lan.mjs`、`image.mjs`/`png.mjs`、`wait.mjs` —— **都不依赖 DSH**。
- **要重写（约 30-40%）**：`index.js`（3,733 行）里的宿主壳（`defineTool` → MCP tool 声明）、HTTP 面与配置页、preset 修补部分（作废）、版本硬提示词（→ 变成 `SKILL.md` 内容）。
- **验收基线现成**：`selfcheck.mjs`（3,371 行自检）+ `tools/check-core.mjs` + `tools/isolate.mjs` —— 移植时先让自检在 MCP 形态下跑绿，再上真机。

**一句话**：移植 = 写一个 ZCode 插件（`plugin.json` 内联 `mcpServers` + 一个 `SKILL.md` 装 RULES/用法 + 可选 hooks），Minecraft 那半边几乎照搬；**"按 preset 收窄工具""浏览器 UI""凭据服务"三样做不出来，得用别的方式替代**。

---

## 二、能不能造出"真玩游戏看画面 + 不干扰玩家"

**能，但不是把这两个装在一起就行——要选架构。** 先厘清"干扰"的根源：

- 干涉玩家的**唯一根源是输入注入**。Minecraft Mod MCP 的控制模式就是明证：`enterMcpControlMode` 会 **强制把光标设为 NORMAL 并释放鼠标**（`ControlModeHelper.java:81-97`，日志写的是 "MCP took control"），退出时再锁回鼠标、并**压制输入 200ms**（`:74-79`）——即"控制模式 = 人机交权"，用它就必然干扰。
- 另外注意：**不进控制模式也不等于"只读"**。`ALWAYS_ALLOWED`（`:855-872`）里有 15 个方法，其中 `set_gamemode` / `pause_game` / `open_chat` / `close_screen` / `overlay_click` / `release_mouse` 都会**影响玩家的界面或游戏状态**；真正的纯只读只有 7 个：`ping`、`screenshot`、`get_player_info`、`get_world_info`、`debug_fields`、`get_screen_buttons`、`enumerate_widgets`。（`screenshot_to_file` **不在**名单里，要它就得进控制模式。）
- whale-craft 的 bot 是**另一个玩家**，天然不碰你的键鼠；但它**没有画面**（`mc_map` 是字符地形图 + 按方块名合成的彩图，不是渲染）。

### 方案 1：只读组合（零成本，今天就能跑）

玩家的客户端装 MCP mod，agent **只调那 7 个只读方法**看画面；身体交给 whale-craft 的 bot（玩家在游戏里「对局域网开放」→ `mc_lan` 发现 → `mc_connect` 进来）。

- **优点**：不写一行代码、零干扰（不碰输入）。
- **缺点**：看到的是**玩家的视角**（agent 不能"自己走过去看"）；而且那个 mod 监听 `0.0.0.0` 且无鉴权，需要自己改成只绑回环。
- **适合**：让 agent"看着玩家玩，一边当参谋/搭手"。

### 方案 2：二号客户端（零代码，agent 有自己的眼睛和手）⭐ 最实用的"不干扰"解

**再开一个游戏实例**（独立账号 + 同一 mod 包），在它上面装 MCP mod。agent 用它自己的客户端截图、点 GUI、走位——玩家的实例完全不被触碰。

- **优点**：真的看画面 + 真的操作 + 零干扰，**不写任何代码**（现有两个东西各就各位）。
- **成本**：第二份内存/显存（MC 客户端 2-4 GB）、第二个账号（离线/皮肤站即可）、mod 包要与玩家一致（否则内容对不上）。世界共享靠局域网开放或同一服务器。
- **适合**：要 agent 独立探索、自己点 GUI、做端到端测试的场合。

### 方案 3：自研 mod —— 一个 mod 同时给"离屏眼睛"和"服务端身体"

- **眼睛（不干扰的关键）**：把世界**渲染到离屏 RenderTarget**，而不是切换玩家相机。
  **库里有工业级参考**：`Geforce132/SecurityCraft`（`源码库/_参考仓库/_bulk`）的摄像机系统 ——
  `entity/camera/CameraFeed.java`（`TextureTarget` 离屏渲染 + `Frustum` 视锥裁剪 + 复用区块网格 `SectionRenderDispatcher.RenderSection` + `MappableRingBuffer`）、
  `entity/camera/{CameraController,SecurityCamera,CameraClientChunkCacheExtension,CameraViewAreaExtension}`、
  `mixin/camera/{CameraMixin,LevelRendererMixin,GameRendererMixin,FogRendererMixin,CloudRendererMixin}`、
  网络包 `network/{MountCamera,DismountCamera,SetCameraView}`、
  把画面贴到方块上的 `renderers/FrameBlockEntityRenderer.java` + 界面 `screen/CameraMonitorScreen.java`。
  → **"相机 → 离屏纹理 → 显示/编码"这条路它全走通了**，你要做的是"把纹理编码成 PNG 交给 agent"这一步。
  另一条更轻的路是 `MehVahdJukaar/cameramod`（Vista，库内已有仓库：`对照表/剩余包_新仓库清单.md` 第 117 条）。
- **身体**：服务端一个**你自己的 NPC 实体**（你们已有实体/AI 与状态树那条线），服务端权威驱动 —— **不需要假玩家、不需要第二实例、不碰玩家输入**。
- **成本**：客户端二次渲染 + 图像传输（体积/频率/限流）；**收益**：视角跟 NPC 走、可多路、可限帧、完全可控。
- **要借的现成机关**：离屏渲染必须回**渲染线程**（MCP mod 的 `RenderThreadExecutor` / `ModDevMcpMod.executeOnRenderThread` 套路可直接抄）；编码走 `NativeImage` → PNG → 文件/base64。

### 三方案对照

| | 画面 | 身体 | 干扰玩家 | 成本 | 何时选 |
|---|---|---|---|---|---|
| **1 只读组合** | 玩家的真实画面（客户端的） | bot（另一个玩家） | **无** | 零代码 | 让 agent 当"副驾/参谋" |
| **2 二号客户端** | **自己的**真实画面 | 玩家自己（第二个账号） | **无** | 一份实例资源 + 账号 | 要 agent 独立操作 GUI/探索（**推荐**） |
| **3 自研 mod** | **自己的**画面（离屏，可控） | 自己的 NPC 实体 | **无** | 开发（有 SecurityCraft 可抄） | 要长期、可限流、可多路、给玩家做功能 |

- **不要做**：在玩家的客户端上做写操作（输入注入）——那正是"干扰"的定义。
- **风险**：MCP mod 无鉴权 + `0.0.0.0`（先收口再谈组合）；whale-craft 的账号在公共服上就是一个真人行为的玩家。

---

## 三、未确认 / 边界

- 两个方案的结论基于**源码实读**（协议、输入抑制、离屏渲染都有 `文件:行号`），但**均未实测**：没装过 whale-craft、没跑过那个 mod、没编译过 SecurityCraft。
- ZCode 侧的三处"无对应物"结论来自官方文档（配置指南/插件规范/hooks 文档）：文档未提及 ≠ 绝无可能（比如未公开的内部 API），但按公开扩展面判断是这样。
- `screenshot` 返回的是 `data:image/png;base64,…` 字符串（`McpMessageHandler.java:238-250`）——注意它是**内联字符串**，体积会给 token 账单单；这也是"方案 2/3 更值得投入"的一个理由。
