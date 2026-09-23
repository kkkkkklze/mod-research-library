# Async Logger — 速览卡片

- 仓库: https://github.com/decce6/AsyncLogger
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 1427265
- 本地源码: `源码库\_参考仓库\_bulk\decce6__AsyncLogger`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 2.2.2
- 构建: 插件=?，工程结构=single；mod_id: ${modid}, minecraft, neoforge
- 源码规模: 37 个 .java，2,056 行
- 主类候选: `src/mod-src/java/me/decce/asynclogger/AsyncLoggerMod.java` (7 行)
- 目录特征: Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `me/decce/transformingbase` | 30 |
| `me/decce/asynclogger` | 7 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `core/src/main/java/me/decce/transformingbase/core/LoggerConfigurator.java` | 191 |
| `src/service/java/me/decce/transformingbase/service/ConfigLoader.java` | 158 |
| `src/service/java/me/decce/transformingbase/service/forge/ForgeModLocator.java` | 130 |
| `src/service/java/me/decce/transformingbase/service/ClassLoaderHandlerImpl.java` | 126 |
| `core/src/main/java/me/decce/transformingbase/core/AsyncFilter.java` | 103 |
| `core/src/main/java/me/decce/transformingbase/core/sysout/WrappedPrintStream.java` | 100 |
| `core/src/main/java/me/decce/transformingbase/core/FilterImpl.java` | 99 |
| `core/src/main/java/me/decce/transformingbase/core/LoggerTester.java` | 97 |
| `core/src/main/java/me/decce/transformingbase/transform/ClassLoaderHandler.java` | 91 |
| `core/src/main/java/me/decce/transformingbase/core/sysout/RedirectingPrintStream.java` | 72 |
| `core/src/main/java/me/decce/transformingbase/core/AsyncLoggerConfig.java` | 71 |
| `src/service/java/me/decce/transformingbase/service/forge/ForgeImmediateWindowProvider.java` | 66 |
| `src/service/java/me/decce/transformingbase/service/Bootstrapper.java` | 62 |
| `core/src/main/java/me/decce/transformingbase/core/AsyncLogger.java` | 58 |
| `core/src/main/java/me/decce/transformingbase/util/ImplLookupAccessor.java` | 56 |