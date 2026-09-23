# Ixeris — 速览卡片

- 仓库: https://github.com/decce6/Ixeris
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 10184435
- 本地源码: `源码库\_参考仓库\_bulk\decce6__Ixeris`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 4.6.5
- 构建: 插件=?，工程结构=single；mod_id: ${modid}_dummy, minecraft, neoforge
- 源码规模: 168 个 .java，16,633 行
- 主类候选: `src/ixeris/java/me/decce/ixeris/IxerisMod.java` (23 行)
- 目录特征: API, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `me/decce/ixeris` | 168 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/ixeris/java/me/decce/ixeris/forge/transformers/sdl/threading/SDLVideoTransformer.java` | 789 |
| `core/src/main/java/me/decce/ixeris/core/mixins/sdl/threading/SDLVideoMixin.java` | 780 |
| `core/src/main/java/me/decce/ixeris/core/input/win32/RawInputHandlerGlfwWin32.java` | 574 |
| `src/ixeris/java/me/decce/ixeris/forge/transformers/glfw/glfw_threading/GLFWTransformer.java` | 494 |
| `core/src/main/java/me/decce/ixeris/core/mixins/glfw/glfw_threading/GLFWMixin.java` | 485 |
| `src/ixeris/java/me/decce/ixeris/forge/transformers/glfw/callback_dispatcher/GLFWTransformer.java` | 406 |
| `core/src/main/java/me/decce/ixeris/core/mixins/glfw/callback_dispatcher/GLFWMixin.java` | 397 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWMOUSE.java` | 393 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWKEYBOARD.java` | 368 |
| `src/ixeris/java/me/decce/ixeris/forge/transformers/glfw/glfw_state_caching/GLFWTransformer.java` | 358 |
| `core/src/main/java/me/decce/ixeris/core/mixins/glfw/glfw_state_caching/GLFWMixin.java` | 349 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWINPUTDEVICE.java` | 338 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWINPUTHEADER.java` | 338 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWINPUT.java` | 334 |
| `core/src/main/java/me/decce/ixeris/core/natives/win32/RAWHID.java` | 330 |