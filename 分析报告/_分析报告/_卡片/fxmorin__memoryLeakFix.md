# Memory Leak Fix — 速览卡片

- 仓库: https://github.com/fxmorin/memoryLeakFix
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 37185178
- 本地源码: `源码库\_参考仓库\_bulk\fxmorin__memoryLeakFix`
- 目标版本: MC 1.20.4 / NeoForge - / Forge 1.20.4-49.0.14 / Fabric 0.15.3；mod 版本 1.1.5
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 源码规模: 28 个 .java，1,193 行
- 目录特征: Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `ca/fxco/memoryleakfix` | 28 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/ca/fxco/memoryleakfix/config/MemoryLeakFixMixinConfigPlugin.java` | 393 |
| `common/src/main/java/ca/fxco/memoryleakfix/utils/MixinInternals.java` | 84 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/readResourcesLeak/TextureUtil_freeBufferMixin.java` | 69 |
| `forge/src/main/java/ca/fxco/memoryleakfix/forge/MemoryLeakFixExpectPlatformImpl.java` | 63 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/hugeScreenshotLeak/Minecraft_screenshotMixin.java` | 50 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/drownedNavigationLeak/Drowned_navigationMixin.java` | 47 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/biomeTemperatureLeak/Biome_threadLocalMixin.java` | 43 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/targetEntityLeak/Minecraft_targetClearMixin.java` | 41 |
| `fabric/src/main/java/ca/fxco/memoryleakfix/fabric/MemoryLeakFixExpectPlatformImpl.java` | 40 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/drownedNavigationLeak/ServerLevel_navigationMixin.java` | 38 |
| `common/src/main/java/ca/fxco/memoryleakfix/config/mixinExtension/UnMixinExtension.java` | 34 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/tagKeyLeak/TagKey_internerMixin.java` | 32 |
| `common/src/main/java/ca/fxco/memoryleakfix/MemoryLeakFixExpectPlatform.java` | 28 |
| `common/src/main/java/ca/fxco/memoryleakfix/mixin/entityMemoriesLeak/Brain_clearMemoriesMixin.java` | 28 |
| `common/src/main/java/ca/fxco/memoryleakfix/config/Remap.java` | 27 |