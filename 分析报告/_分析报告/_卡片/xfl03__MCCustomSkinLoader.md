# CustomSkinLoader — 速览卡片

- 仓库: https://github.com/xfl03/MCCustomSkinLoader
- 出现在整合包: FIDR暗涌, 星轨重铸；Modrinth 下载量(参考): 23061260
- 本地源码: `源码库\_参考仓库\_bulk\xfl03__MCCustomSkinLoader`
- 目标版本: MC 26.2 / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=?，工程结构=single；mod_id: ?
- 源码规模: 113 个 .java，9,019 行
- 主类候选: `Common/src/main/java/customskinloader/mod/forge/ForgeMod.java` (42 行)
- 目录特征: API, Client, Config, Mixin, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `customskinloader/bootstrap/transformer` | 11 |
| `net/minecraft/client` | 11 |
| `customskinloader/utils` | 10 |
| `customskinloader/bootstrap/forge` | 7 |
| `customskinloader/fake/itf` | 7 |
| `customskinloader/loader/jsonapi` | 6 |
| `customskinloader/loader` | 5 |
| `customskinloader/bootstrap/mapping` | 4 |
| `customskinloader/bootstrap/util` | 4 |
| `customskinloader/bootstrap/neoforge` | 4 |
| `customskinloader/fake` | 4 |
| `customskinloader/fake/texture` | 4 |
| `net/minecraftforge/fml` | 4 |
| `customskinloader/bootstrap/installer` | 3 |
| `customskinloader/bootstrap/fabric` | 3 |
| `customskinloader/gradle` | 3 |
| `customskinloader/profile` | 3 |
| `net/minecraft/server` | 3 |
| `customskinloader/bootstrap` | 2 |
| `customskinloader/config` | 2 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `Bootstrap/Core/src/main/java/customskinloader/bootstrap/transformer/patch/SkinManagerPatch.java` | 524 |
| `Bootstrap/Core/src/main/java/customskinloader/bootstrap/installer/BytecodeRemapper.java` | 412 |
| `buildSrc/src/main/java/customskinloader/gradle/ManifestLibrariesExtension.java` | 296 |
| `Common/src/main/java/customskinloader/utils/HttpRequestUtil.java` | 285 |
| `Bootstrap/Core/src/main/java/customskinloader/bootstrap/transformer/patch/PatchSupport.java` | 268 |
| `Bootstrap/Core/src/main/java/customskinloader/bootstrap/mapping/Mappings.java` | 263 |
| `Common/src/main/java/customskinloader/config/Config.java` | 259 |
| `Common/src/main/java/customskinloader/fake/FakeCapeBuffer.java` | 255 |
| `Common/src/main/java/customskinloader/CustomSkinLoader.java` | 237 |
| `Common/src/main/java/customskinloader/loader/LegacyLoader.java` | 235 |
| `Common/src/main/java/customskinloader/fake/FakeSkinBuffer.java` | 224 |
| `Bootstrap/FabricV1/src/main/java/customskinloader/bootstrap/fabric/v1/TransformerBootstrap.java` | 194 |
| `Common/src/main/java/customskinloader/log/Logger.java` | 190 |
| `Common/src/main/java/customskinloader/fake/FakeSkinManager.java` | 184 |
| `Common/src/main/java/customskinloader/loader/MojangAPILoader.java` | 183 |