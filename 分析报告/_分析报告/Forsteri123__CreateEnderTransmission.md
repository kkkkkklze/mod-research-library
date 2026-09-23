# Forsteri123/CreateEnderTransmission 源码分析

## 1. 基本信息
- Mod 名：Create Ender Transmission；mod_id `createendertransmission`；作者 Forsteri（credits: RayRayRay#7369）；mod 版本 2.0.8-1.19.2
- 目标：MC 1.19.2 + Forge（`mods.toml` loaderVersion `[41,)`）；`gradle.properties` mc_version=1.19.2
- 编译依赖：Create 1.19.2-0.5.1.i（Modrinth，`transitive=false`）、Flywheel 0.6.11-22（`libs/flywheel-forge-1.19.2-0.6.11-22.jar`，注释说明该版本已不在公开 maven，取自 Create 的 jarJar）、Registrate MC1.19-1.1.5；Gradle 用 mixingradle 0.7.+ 与 parchment librarian（`build.gradle:11-12,154-172`）
- 许可证：MIT（`mods.toml`）。依赖声明 create 为 mandatory

## 2. 源码规模与包结构
28 个 `.java`，合计 1528 行（`find … -exec wc -l`）。包分布（第 3 层）：
- 根 `com.forsteri.createendertransmission` 1；`entry` 7；`blocks` 3；`blocks/chunkLoader` 3；`blocks/energyTransmitter` 3；`blocks/fluidTrasmitter`（原文拼写）4；`blocks/itemTransmitter` 3；`transmitUtil` 3；`mixin` 1
- 最大文件：TransmitterScreen 104、EnergyTransmitterBlockEntity 103、FluidTransmitterInventoryHandler 100、TransmissionBlocks 93、CreateEnderTransmission 91、EnergyTransmitterBlock 89、TransmissionPackets 83

## 3. 入口与注册
`src/main/java/com/forsteri/createendertransmission/CreateEnderTransmission.java:29-46`：构造里 `REGISTRATE.registerEventListeners(...)`，随后调用 `TransmissionBlocks.register()` / `TransmissionBlockEntities.register()` / `TransmissionPackets.registerPackets()` / `TransmissionLang.register()`；`CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)`（:82）。注册框架是 Create 的 CreateRegistrate（Registrate 封装），方块全部用 `BlockEntry` 链式注册并附 `BlockStressDefaults.setImpact(...)`（`entry/TransmissionBlocks.java:28-90`）。COMMON 配置注册为 `createendertransmission-server.toml`（:44）。

## 4. 核心系统
1. 通道/密码共享库存（学习价值最高）：`blocks/MatterTransmitterNetwork.java:15-37` 用枚举定义 ITEM/FLUID 两套网络，每套 10 个 channel，channel 内以 password 为键存 `INBTSerializable<CompoundTag>`；`blocks/AbstractMatterTransmitterBlockEntity.java:32-46` 的 `getInv()` 按 (channel,password) 惰性建库存并 `setDirty()`，能力通过 `LazyOptional.of(...)` 暴露（:25）。子类只实现三个方法（`blocks/itemTransmitter/ItemTransmitterBlockEntity.java:22-35`）。
2. 世界级持久化：`blocks/MatterWorldSavedData.java:11-62` 继承 SavedData，10 通道 × 网络枚举全量 NBT 序列化，经 `overworld().getDataStorage().computeIfAbsent(...)` 载入；主类用 `LevelEvent.Load`/`PlayerLoggedInEvent` 刷新静态引用（主类:53-76）。
3. 包装式库存：`ItemTransmitterInventoryHandler` 继承 ItemStackHandler 全量转发到 supplier；`FluidTransmitterInventoryHandler` 继承 Create 的 `CombinedTankWrapper`（:14-32），实现"共享库存可动态换实例"。
4. 动能式跨维能量传输：`blocks/energyTransmitter/EnergyTransmitterBlockEntity.java:42-100` 依 channel/password 聚合同伴 transmitter 清理失效项，`propagateRotationTo` 返回 1f/0f 决定转速传递。
5. 区块加载器：`blocks/chunkLoader/LoaderBlockEntity.java:34-42` 每 tick 对 5×5 chunk 调 `setChunkForced`，阈值随距离 `Math.abs(getSpeed()) >= 16*8*max(|i|,|j|)`；goggle tooltip 输出已加载区块数（:46-63）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`entry/TransmissionPackets.java:20-82`，Forge `SimpleChannel` 单通道 `createendertransmission:main`，协议版本字符串 "1"，枚举 + 自增 index 注册，编解码直接复用 Create `SimplePacketBase.write`；`ConfigureTransmitterPacket` 用 `buffer.writeNbt` 传 channel/password，服务端校验后写入 BE `persistentData`（:25-50）。客户端界面 `transmitUtil/TransmitterScreen.java:22-102`（Create AbstractSimiScreen + IconButton）发包。
- 配置：`entry/TransmissionConfig.java:5-16` 仅一项 `chunkLoader`；被 `entry/ChunkLoaderRecipeCondition.java:17-20` 当作 Forge 配方条件（`ICondition`）使用，实现"配置关掉则相关物品/配方不可见"。
- 数据驱动：无 JSON 数据加载；语言用 `registrate().addRawLang`（`TransmissionLang.java:8-16`）。
- datagen：无（build.gradle 无 runData/Provider 配置）。

## 6. Mixin
`src/main/resources/createendertransmission.mixins.json`（required、JAVA_17）仅一个 mixin：`mixin/FluidTransmitterOnContraptionMixin.java:11-17`，`@Inject(method="canUseAsStorage", at=HEAD, cancellable)` 目标 Create `MountedFluidStorage`，让流体发射器可作为装置（contraption）上的储罐，`remap=false`。

## 7. 值得学的 5 条
1. 用 (channel:int, password:String) 作为共享库存的复合键，把"远程仓库"实现在 SavedData 而非方块上：`blocks/AbstractMatterTransmitterBlockEntity.java:32-46`；适用场景：跨维度/跨区块的物流传输。
2. 能力用 supplier 包装器转发，共享容器实例改变时不必重建 capability：`blocks/itemTransmitter/ItemTransmitterInventoryHandler.java:15-30`。
3. 把 mod 配置项接入 `ICondition`，实现"配置即配方门控"：`entry/ChunkLoaderRecipeCondition.java:17-20`。
4. 直接复用 Create 的基础设施（CombinedTankWrapper、AbstractSimiScreen、Lang/LangBuilder goggle tooltip）省掉自研 UI 与流体合并逻辑：`blocks/fluidTrasmitter/FluidTransmitterInventoryHandler.java:14`、`blocks/chunkLoader/LoaderBlockEntity.java:46-63`。
5. 依赖锁定技巧：Create 走 Modrinth 且 `transitive=false`，Flywheel 以本地 `libs/` jar 提供，规避 0.5.1.i 时代 Flywheel 未公开发布的问题：`build.gradle:154-172`。

## 8. 库/API 扩展点
不适用（非库/前置模组，无对外 API 包）。
