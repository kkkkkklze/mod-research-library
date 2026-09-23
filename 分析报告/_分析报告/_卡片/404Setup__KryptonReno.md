# Krypton Reno — 速览卡片

- 仓库: https://github.com/404Setup/KryptonReno
- 出现在整合包: 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\404Setup__KryptonReno`
- 目标版本: MC 26.2 / NeoForge 26.2.0.6-beta / Forge 26.2.0.6-beta / Fabric -；mod 版本 ?
- 构建: 插件=?，工程结构=single；mod_id: kreno
- 源码规模: 66 个 .java，4,505 行
- 目录特征: Command, Mixin, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `one/pkg/kreno` | 65 |
| `one/pkg/loader` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/one/pkg/kreno/shared/culling/ServerCullingManager.java` | 449 |
| `common/src/jmh/java/one/pkg/kreno/jmh/compression/Deflate.java` | 257 |
| `common/src/main/java/one/pkg/kreno/mixin/network/pipeline/Varint21FrameDecoderMixin.java` | 200 |
| `common/src/jmh/java/one/pkg/kreno/jmh/compression/Inflate.java` | 195 |
| `common/src/main/java/one/pkg/kreno/shared/network/he/HEConnect.java` | 180 |
| `common/src/main/java/one/pkg/kreno/shared/ModConfig.java` | 171 |
| `common/src/jmh/java/one/pkg/kreno/jmh/compression/DataBase.java` | 170 |
| `common/src/main/java/one/pkg/kreno/shared/ModMixinBootstrap.java` | 161 |
| `common/src/main/java/one/pkg/kreno/mixin/network/chunk/TrackedEntityMixin.java` | 135 |
| `common/src/jmh/java/one/pkg/kreno/jmh/varint/VarIntBase.java` | 126 |
| `common/src/main/java/one/pkg/kreno/shared/network/util/VarLongUtil.java` | 114 |
| `common/src/jmh/java/one/pkg/kreno/jmh/varlong/VarLongBase.java` | 108 |
| `common/src/main/java/one/pkg/kreno/shared/network/util/VarIntUtil.java` | 99 |
| `common/src/jmh/java/one/pkg/kreno/jmh/network/VarIntBenchmark.java` | 94 |
| `common/src/main/java/one/pkg/kreno/shared/network/he/HEConnectHandler.java` | 94 |