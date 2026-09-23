# SonarSonic/Flux-Networks 源码分析报告

## 1. 基本信息

- Mod 名：Flux Networks；mod_id `fluxnetworks`；作者 Sonar Sonic / BloCamLimb；许可证 MIT（`src/main/resources/META-INF/mods.toml:4`）
- 目标版本：MC 1.20.1 + Forge 47.1.33，mod_version 7.2.1.15（`gradle.properties`）；本地副本检出分支为 `1.20`（`git log -1` = 20a3d8b，上游另有 `1.21.1` 分支，本地未包含）
- Gradle 插件：`net.minecraftforge.gradle [6.0,6.2)` + `org.parchmentmc.librarian.forgegradle 1.+`，mappings `parchment 2023.07.16-1.20.1`，Java 17（`build.gradle`）
- 编译依赖：Mekanism API（compileOnly）、The One Probe（implementation）、GregTechCEu compileOnly、JEI、Curios（compileOnly api）、ModernUI-Forge + ModernUI-Core/Markdown（minecraftLibrary + implementation，`build.gradle:150-170`）
- `build.gradle` 声明了独立 `api` 源码集指向 `src/api/java`，但本地副本无该目录，api 类实际位于 `src/main/java/sonar/fluxnetworks/api`（未确认上游是否已拆包）

## 2. 源码规模与包结构

实测：200 个 `.java`，20216 行。包计数（第 3 层）：`sonar/fluxnetworks` 根 4、`api` 22、`client` 58（`gui` 35、`mui` 8、`design` 5、`jei` 3、`render` 3、`widget` 2）、`common` 100（`test` 41、`device` 14、`integration` 12、`connection` 9、`util` 7、`block` 6、`item` 5、`crafting` 4、`capability` 2）、`data` 3、`register` 15。

最大文件：`register/Messages.java` 777、`common/device/TileFluxDevice.java` 673、`common/connection/FluxNetwork.java` 540、`common/test/S2CNetMsg.java` 519、`common/connection/ServerFluxNetwork.java` 386、`common/util/FluxUtils.java` 381、`client/gui/tab/GuiTabConnections.java` 345、`client/mui/CreateTab.java` 337、`register/ClientMessages.java` 336、`common/connection/FluxNetworkData.java` 325。注意 `common/test` 是遗留协议包（大量注释掉的旧实现）。

本地副本为稀疏检出（`.git/info/sparse-checkout` 只保留 java/gradle/toml 等），资源仅剩 `META-INF/mods.toml`。

## 3. 入口与注册

`FluxNetworks.java:11-28` 的 `@Mod` 类极薄：只有 MODID/LOGGER、`ModList.isLoaded("curios"/"modernui")` 探测、`FluxConfig.init()`。

注册走 Forge 原生 `RegisterEvent` + `RegistryObject.create` 的"集中分派"风格（不用 DeferredRegister）：`register/Registration.java:83-91` 一次事件里把 BLOCKS/ITEMS/BLOCK_ENTITY_TYPES/MENU_TYPES/RECIPE_SERIALIZERS/SOUND_EVENTS/CREATIVE_MODE_TAB 分别派给 `RegistryBlocks/RegistryItems/RegistryRecipes/...` 各静态类，类内用 `helper.register(KEY, obj)`（`RegistryItems.java:28-45`）。`FMLCommonSetupEvent` 中建信道、注册 `ForgeChunkManager.setForcedChunkLoadingCallback`（校验每个强加载设备只占 1 区块）、`EnergyUtils.register()`；`GatherDataEvent` 只生成 loot/block tags。

## 4. 核心系统

1) 逻辑网络与持久化：`FluxNetworkData extends SavedData`（`common/connection/FluxNetworkData.java:30-74`），`Int2ObjectMap<FluxNetwork>` + `computeIfAbsent` 挂 overworld 的 DataStorage；`createNetwork` 受 `FluxConfig.maximumPerPlayer` 限制并广播 `Messages.updateNetwork`；`release()` 处理单机切档；每 server tick END 调 `FluxNetwork::onEndServerTick`（`register/EventHandler.java:49-51`）。`FluxNetwork` 内置 `INVALID` 空对象（所有操作静默失败）与逻辑设备常量 ANY/PLUG/POINT/STORAGE/CONTROLLER（`FluxNetwork.java:39-51`）。
2) 能量传输：`TransferHandler`（`common/connection/TransferHandler.java`）是核心，字段 `mBuffer/mChange/mLimit/mSurgeMode`，优先级常量 `PRI_USER(-9999..9999)/PRI_GAIN(10000..100000)/STORAGE_PRI_DIFF=1000000`，抽象 `onCycleStart()/onCycleEnd()` 实现"先模拟后执行"的两阶段吞吐，配合 `TransferIterator`/`ServerFluxNetwork` 排序遍历。
3) 设备体系：`TileFluxDevice`（`common/device/TileFluxDevice.java:41-150`）以位掩码 `mFlags` 打包状态：`SIDES_CONNECTED_MASK=0x3F`、`FLAG_FORCED_LOADING=0x40`、`FLAG_FIRST_TICKED=0x80`、`FLAG_SETTING_CHANGED=0x100`、`FLAG_ENERGY_CHANGED=0x200`；GUI 打开时每 tick 推 `DEVICE_S2C_GUI_SYNC`；`setRemoved/onChunkUnloaded` 转 `PhantomFluxDevice` 保留未加载设备数据；子类 Plug/Point/Controller/Storage/Connector 各配 `Flux*Handler`。
4) 长整型能量 API：`api/energy/IFNEnergyStorage`（`@AutoRegisterCapability`，`receiveEnergyL/extractEnergyL/getEnergyStoredL` 等 long 版）经 `api/FluxCapabilities.java:15` 的 `CapabilityManager.get(new CapabilityToken<>(){})` 暴露；`EnergyType` 枚举 FE/EU 做单位显示；互操作用 `IBlockEnergyConnector/IItemEnergyConnector` + `ForgeEnergyConnector/FNEnergyConnector/GTCEUEnergyConnector`（`common/integration/energy/`），GT/IC2 实现在 `EnergyUtils.register()` 中被注释禁用。
5) 协议与信道：`register/Channel.java` 抽象类定义 `PROTOCOL="707"`、`buffer(index)` 先写 2 字节消息索引，`sendToServer/sendToPlayer/sendToAll/sendToTrackingChunk` 四个语义化发送口；`FMLChannel` 用 `NetworkRegistry.newEventChannel(...).registerObject(this)` 收包后按 short 索引跳到 `Messages.msg` / `ClientMessages.msg`。C2S/S2C 各一套 0 起连续索引常量（`Messages.java:65-93`），并用"容器 token + response code"做请求-响应（`Messages.java:35-54` 注释完整说明协议约定）。
6) 客户端双轨 UI：`client/gui` 传统 Screen（35 文件）与 `client/mui` ModernUI 重写版（8 文件，`icyllis.modernui`），`ClientRegistration.getScreenFactory()` 按 `FluxNetworks.isModernUILoaded()` 二选一。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络见 4.5。数据驱动：`common/crafting/FluxStorageRecipe`（继承 `ShapedRecipe`，`assemble` 时读取输入物品 `FluxConstants.TAG_FLUX_DATA` 子 NBT 汇总能量与 networkID）与 `NBTWipeRecipe`，序列化器以单例注册（`register/RegistryRecipes.java`）。配置为 ForgeConfigSpec 的 CLIENT/COMMON/SERVER 三份 + `FluxConfig.reload(ModConfigEvent)`。datagen 仅 loot 与 block tags（`data/` 3 文件 150 行）。

## 6. Mixin

无。全仓 grep `mixin` 无任何命中，也无 mixins.json；兼容全部通过 capability/事件/能量连接器抽象完成。

## 7. 值得学的 5 条做法

1. 用 `@AutoRegisterCapability` + `CapabilityToken` 提供 long 版能量 capability，绕开 Forge `IEnergyStorage` 的 int 上限（`api/FluxCapabilities.java:15`）——做"超大吞吐"设备时直接抄。
2. SavedData 单例 + `release()` 静态清理，正确应对单机切换存档（`common/connection/FluxNetworkData.java:66-82`）——任何全局缓存都用这套。
3. 自定义信道抽象（`Channel` 抽象类 + 平台实现）配合"2 字节索引 + switch 分派 + PROTOCOL 字符串版本号"，比 `SimpleChannel` 的一包一类更省样板（`register/Channel.java:16-33`）。
4. 位掩码打包 BE 状态并注明 server/client 归属（`TileFluxDevice.java:79-88`），减少 NBT 与同步字段。
5. 传输用"抽象基类定优先级 + onCycleStart/onCycleEnd 两阶段"（`common/connection/TransferHandler.java`），避免同 tick 内重复写入。
6. 用 PhantomFluxDevice 在区块卸载时降级保存设备摘要（`common/connection/PhantomFluxDevice.java`），跨区块电网不断线。

## 8. 对外 API

公开包 `sonar.fluxnetworks.api`（`device`/`energy`/`network`/`misc`/`gui` + `FluxConstants`/`FluxCapabilities`/`FluxTranslate`，共 22 文件 1242 行）。外部 mod 接入方式二选一：给 BE/Item 挂 `FluxCapabilities.FN_ENERGY_STORAGE`；或依赖 Flux 的 `IBlockEnergyConnector/IItemEnergyConnector` 抽象在 `EnergyUtils.register()` 中登记新能量体系。API 与主源码同包混放、未做独立 artifacts（`src/api/java` 在本地副本不存在）。
