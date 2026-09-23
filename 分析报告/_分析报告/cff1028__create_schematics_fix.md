# cff1028/create_schematics_fix 源码分析报告

## 1. 基本信息

- Mod 名：Create Bugfix: Schematic Patch；mod_id `schematicsfix`；作者 CFF1028
- 目标：MC 1.21.1 / NeoForge（`gradle.properties:neo_version=21.1.193`，`minecraft_version_range=[1.21.1]`，`loader_version_range=[1,)`）
- Gradle 插件：`net.neoforged.moddev` 2.0.103（NeoForge MDK 模板），另有 `java-library`、`maven-publish`、`idea`（`build.gradle:1-6`）
- 许可证：`src/main/templates/META-INF/neoforge.mods.toml` 写 MIT；`gradle.properties:mod_license` 仍为模板默认 `All Rights Reserved`（未同步）
- 编译依赖：无。`build.gradle:114-134` 的 `dependencies` 块全是 MDK 注释样例，未加 Create
- 运行时依赖声明：`neoforge [21.1.170,)`、`create [6.0.0,)`（neoforge.mods.toml 末尾）。注意其 `[[dependencies.clipboard_patch]]` 段名与 `modId="schematicsfix"` 不一致，疑为从 "clipboard_patch" 改名后残留（实际是否生效未确认）
- 模板残留：`mod_id=examplemod`、`mod_group_id=com.example.examplemod`；Java 包仍为 `com.example.schematicsfix`

## 2. 源码规模与包结构

- 5 个 `.java`，共 597 行（`find . -name '*.java' -exec wc -l {} +`）
- 包结构（仅一层业务包）：
  - `com.example.schematicsfix`：`SchematicFixMod`、`Config`、`SchematicProcessor`(268 行)、`SchematicWatcher`(182 行)
  - `com.example.schematicsfix.commands`：`ScanAllCommand`
- 最大文件：SchematicProcessor 268、SchematicWatcher 182、ScanAllCommand 70、Config 30、SchematicFixMod 49
- `src/main/resources` 不存在：无 lang、无贴图、无 datagen 输出

## 3. 入口与注册

主类 `SchematicFixMod`（`src/main/java/com/example/schematicsfix/SchematicFixMod.java`），构造签名为 NeoForge 1.21 的 `(IEventBus, ModContainer)`：

```java
@Mod("schematicsfix")
public class SchematicFixMod {
    public static final Path SCHEMATICS_DIR = FMLPaths.GAMEDIR.get().resolve("schematics");
    public static final Path UPLOADED_DIR = SCHEMATICS_DIR.resolve("uploaded");
    public static final Path ANOMALY_DIR = SCHEMATICS_DIR.resolve("anomaly");
    public SchematicFixMod(IEventBus bus, ModContainer container) {
        container.registerConfig(ModConfig.Type.COMMON, Config.SPEC);
        NeoForge.EVENT_BUS.register(this);
    }
```

事件：`ServerStartingEvent` 起 watcher、`RegisterCommandsEvent` 注册 `/schematic-all`、`ServerStoppingEvent` 停 watcher。无 DeferredRegister、无物品/方块内容注册——纯事件型 mod。

## 4. 核心系统

1. **目录监听 `SchematicWatcher`**：`WatchService` 递归注册(`registerDirectory` 161-176)，只收 `ENTRY_CREATE/ENTRY_MODIFY`；文件名以 `.nbt` 结尾才处理；用 `fileWriteTimes`(ConcurrentHashMap 存 path→时间戳) + 1000ms `FILE_STABILIZATION_DELAY` + `delayedExecutor.schedule` 做二次防抖，稳定后 `server.execute(...)` 切回服务器主线程处理（152-158）。玩家名 = 所在父目录名（106）。
2. **NBT 清洗与拦截 `SchematicProcessor`**：白名单 `ALLOWED_TAGS = {create:clipboard_pages, create:clipboard_type}`，`cleanComponents`(211-235) 删除 `components` 复合标签下所有非白名单键（防 NBT 注入伪造组件）；`containsBannedKeywordsRecursive`(246) 递归扫 StringTag 匹配配置里的关键词。
3. **异常样本处置 `handleAnomalousSchematic`(126-154)**：先复制到 `schematics/anomaly/<玩家名>/` 存档，再广播系统消息；命中违禁词则把原文件截断为 0 字节，仅"被修改"则原位回写。
4. **命令 `ScanAllCommand`**：`/schematic-all`，`hasPermission(2)`，`Files.walk` 遍历 uploaded 目录批量跑同一处理器，用 AtomicInteger 统计条数。
5. **配置 `Config`**：`ModConfigSpec`，COMMON 类型，`bannedKeywords`(默认 bedrock/command_block) 与 `enableKeywordCheck`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（无 payload/channel 注册）
- 数据驱动：无（无 json 资源）
- 配置：NeoForge `ModConfigSpec`，`BUILDER.push("Schematic Patch Config")`，见 `Config.java:14-29`
- datagen：无，`src/main/resources` 目录缺失

## 6. Mixin

无 mixin（无 `*.mixins.json`、无 mixin 包、无 mixin 配置项）。全部通过 Forge/NeoForge 事件总线与文件系统副作用实现，属于"零侵入"实现。

## 7. 值得学的 5 条具体做法

1. **文件监听防抖**：Create 蓝图上传是异步写盘，用 `fileWriteTimes` 时间戳 + 延时任务二次确认写入稳定再处理，避免读到半截文件（`SchematicWatcher.java:108-149`）；适用场景：任何"监听外部目录导入资源"的 mod。
2. **跨线程边界显式切主线程**：watcher 线程只做 IO 判定，NBT 解析与广播统一 `server.execute`（`SchematicWatcher.java:152`、`SchematicProcessor.java:139`）；适用：异步线程碰世界/玩家数据。
3. **只读打开 + FileChannel FileLock**：`channel.tryLock(0L, Long.MAX_VALUE, true)` 共享锁 + `isValidNbtFile` 检查 gzip 魔数 `0x1F 0x8B`（`SchematicProcessor.java:83-102, 156-168`）。
4. **可重试异常白名单 + 指数退避**：`isRetryableException` 只对 EOF/Zip/ZLIB/"being used by another process" 重试，最多 3 次、每次 300ms×n（`SchematicProcessor.java:30-71`）。
5. **原地改写用 tmp + ATOMIC_MOVE**：`NbtIo.writeCompressed(root, tmp)` 后 `Files.move(tmp, file, REPLACE_EXISTING, ATOMIC_MOVE)`，失败清理 tmp（`SchematicProcessor.java:170-183`）；适用：任何改写存档/配置文件的场景。
6. **清洗前先备份原件**：所有改动前先 `Files.copy` 到 `anomaly/<player>/` 留证（`SchematicProcessor.java:129-133`）。

## 8. 公开 API

非库模组，无对外 API 包与扩展点。对外可复用的仅是包内 `public static boolean SchematicProcessor.processSchematicFile(MinecraftServer, Path, String)`。
