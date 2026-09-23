# 内存泄漏alltheleaks-1.1.12+1.21.1-neoforge.jar — 速览卡片

- 仓库: https://github.com/pietro-lopes/AllTheLeaks
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\pietro-lopes__AllTheLeaks`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: ${mod_id}, minecraft, neoforge
- 许可证: MIT License Copyright (c) 2023 AllTheLeaks This license appl
- 源码规模: 286 个 .java，10,396 行
- 主类候选: `src/main/java/dev/uncandango/alltheleaks/diag/common/mods/minecraft/ModernFixProfilerByMod.java` (8 行)
- 目录特征: API, Client, Config, Mixin
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `dev/uncandango/alltheleaks` | 282 |
| `dev/uncandango/atl_agent` | 4 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/dev/uncandango/alltheleaks/commands/ATLCommands.java` | 350 |
| `src/main/java/dev/uncandango/alltheleaks/feature/common/mods/minecraft/MemoryMonitor.java` | 301 |
| `src/main/java/dev/uncandango/alltheleaks/feature/common/mods/minecraft/SaveWithLoadedChunks.java` | 238 |
| `atl-agent/src/main/java/dev/uncandango/atl_agent/transformer/JarInJarDependencyLocatorTransformer.java` | 235 |
| `src/main/java/dev/uncandango/alltheleaks/events/CommonEvents.java` | 229 |
| `src/main/java/dev/uncandango/alltheleaks/api/windows/ProcessMemoryCounter.java` | 198 |
| `src/main/java/dev/uncandango/alltheleaks/feature/common/mods/minecraft/IngredientDedupe.java` | 181 |
| `src/main/java/dev/uncandango/alltheleaks/leaks/IssueManager.java` | 181 |
| `src/main/java/dev/uncandango/alltheleaks/utils/MethodNodeHasher.java` | 150 |
| `src/main/java/dev/uncandango/alltheleaks/diag/server/mods/minecraft/DebugThreadsHooks.java` | 142 |
| `src/main/java/dev/uncandango/alltheleaks/utils/MethodNodeDebug.java` | 126 |
| `src/main/java/dev/uncandango/alltheleaks/events/ClientEvents.java` | 125 |
| `src/main/java/dev/uncandango/alltheleaks/mixin/core/debug/ChunkMapMixin.java` | 125 |
| `src/main/java/dev/uncandango/alltheleaks/mixinsq/ATLMixinAdjuster.java` | 124 |
| `src/main/java/dev/uncandango/alltheleaks/utils/ReflectionHelper.java` | 115 |