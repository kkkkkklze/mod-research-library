# Packet Fixer — 速览卡片

- 仓库: https://github.com/TonimatasDEV/PacketFixer
- 出现在整合包: 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\TonimatasDEV__PacketFixer`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 源码规模: 32 个 .java，816 行
- 目录特征: Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `dev/tonimatas/packetfixer` | 32 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/dev/tonimatas/packetfixer/util/Config.java` | 129 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/CommonMixinPlugin.java` | 59 |
| `fabric/src/main/java/dev/tonimatas/packetfixer/fabric/mixins/FabricMixinConfig.java` | 52 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/Varint21FrameDecoderMixin.java` | 34 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/NbtAccounterMixin.java` | 28 |
| `fabric/src/main/java/dev/tonimatas/packetfixer/fabric/platform/FabricPlatformHelper.java` | 27 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/FriendlyByteBufMixin.java` | 26 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/VarIntMixin.java` | 26 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/VarLongMixin.java` | 26 |
| `common/src/main/java/dev/tonimatas/packetfixer/platform/services/IPlatformHelper.java` | 26 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/MinecraftServerMixin.java` | 24 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/ServerboundCustomQueryPacketMixin.java` | 24 |
| `neoforge/src/main/java/dev/tonimatas/packetfixer/neoforge/platform/NeoForgePlatformHelper.java` | 23 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/ClientboundCustomQueryPacketMixin.java` | 22 |
| `common/src/main/java/dev/tonimatas/packetfixer/mixins/ClientboundCustomPayloadPacketMixin.java` | 21 |