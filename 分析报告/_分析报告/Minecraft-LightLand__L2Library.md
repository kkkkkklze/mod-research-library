# L2Library（lcy0x1 / Minecraft-LightLand）源码分析报告

## 1. 基本信息

- Mod 名：L2Library；mod_id：`l2library`；作者：`lcy0x1`（`mod_group_id=dev.xkmc`）；版本 3.0.8。
- 目标：Minecraft **1.21.1** + **NeoForge**（`neo_version=21.1.64`，`neo_version_range=[21.1.4,)`，Java 21）。
- Gradle：`net.neoforged.gradle.userdev 7.0.165`、`java-library`、`maven-publish`、`curseforgegradle`、`modrinth.minotaur`、`gradle-secrets-plugin`（`build.gradle:1-12`）。
- 许可证：LGPL-2.1（`gradle.properties`）。
- 依赖（关键）：用 **jarJar**（`lljij=true`）内嵌 `l2serial`、`l2modularblocks`、`l2core`、`l2tabs`、`l2menustacker`、`l2itemselector`、以及 `com.tterrag.registrate`（`MC1.21-1.3.0+55`）。编译期 optional：`curios 9.0.5+1.21`、`jei 19.21.0.247`、`patchouli 1.21-87`。`libs/` 里存放 15 个自有子模块的 jar 与 `-sources.jar`，通过 `flatDir` 仓库接入。
- 它自身即是"前置库"：l2mods 全家桶（l2magic / l2backpack / l2weaponry / modulargolems 等）都依赖它。

## 2. 源码规模与包结构

- 主仓库极薄：`src/main/java` 仅 **32 个 .java、991 行**（`find . -name '*.java' | wc -l`）。真正实现被拆到 15 个 jarJar 子模块，解压 `libs/*-sources.jar` 后共 **1883 个 java 文件**：l2core 198、l2magic 285、modulargolems 289、glimmeringtales 248、l2backpack 205、l2complements 176、l2weaponry 108、l2damagetracker 81、l2menustacker 75、danmaku_api 74、l2tabs 66、l2serial 63、l2modularblocks 53、l2itemselector 32、fast_projectile_api 30。
- 主仓库包：`dev.xkmc.l2library.content.explosion`（BaseExplosion / ExplosionHandler）、`content.raytrace`（RayTraceUtil 154 行）、`events`、`init`（L2Library / L2LibraryConfig / FlagMarker）、`mixin`、`util`（Frac 152 行）。
- l2core 包（198 文件 / 9672 行）：`base.menu`（base/data/scroller/stacked）、`base.effects`、`base.entity`、`base.tile`、`capability`（attachment/conditionals/player/level）、`init.reg`（registrate/simple/ench/datapack/varitem）、`serial`（config/configval/recipe/loot/advancements/ingredients）、`mixin`、`util`。
- 最大文件：`base/menu/base/BaseContainerMenu.java` 313 行、`init/reg/registrate/L2Registrate.java` 287 行、`base/menu/base/MenuLayoutConfig.java` 237 行、`init/reg/ench/EnchVal.java` 221 行、`base/tile/BaseTank.java` 214 行。

## 3. 入口与注册

主类 `src/main/java/dev/xkmc/l2library/init/L2Library.java:12-25`：仅建 `L2Registrate` 与 `PacketHandler`（1 个包 `TargetSetPacket`），构造器只调 `L2LibraryConfig.init()`。子模块各自有 `@Mod`：`dev/xkmc/l2core/init/L2Core.java:19-39` 是主库入口，形如：

```java
public static final L2Registrate REGISTRATE = new L2Registrate(MODID);
public static final PacketHandler PACKET_HANDLER = new PacketHandler(MODID, 1,
        e -> e.create(EffectToClient.class, PLAY_TO_CLIENT), ...);
public L2Core(IEventBus bus) { L2LibReg.register(); L2CoreConfig.init(); Handlers.register(); }
```

注册框架是 **Registrate 的二次封装**（`L2Registrate extends AbstractRegistrate`，`init/reg/registrate/L2Registrate.java`），并自研一层极简注册器 `init/reg/simple`（`Reg` / `Val` / `SR.of(REG, BuiltInRegistries.X)` / `IngReg` / `CdcReg` / `AttReg`），`L2LibReg.java:34-81` 用它们集中登记 ingredient、condition、NeoForge attachment、GlobalLootModifier、PlacementModifierType、自定义 registry（`legacy_enchantment`，`sync(true)`）。`newRegistry(id, cls)` 同时注册 `CodecHandler` 与 `Handlers.registerReg`，使自建 registry 可直接被序列化（`L2Registrate.java:142-157`）。

## 4. 核心系统

1. **跨格式序列化（l2serial）**：`serialization/unified_processor/UnifiedCodec.java` 是核心——按 `@SerialClass`/`@SerialField` 反射遍历字段（含父类链），通过 5 个上下文 `JsonContext / TagContext / PacketContext / RealCodecContext / SingletonContext` 把同一份 POJO 同时编解码为 JSON、NBT、网络包、DFU Codec。字段按 `TreeMap` 排序保证确定性（`UnifiedCodec.java:105`）；`GenericCodec` 处理 List/Map/Set/Record/Enum/Holder；`NullDefer` 解决"字段缺失 → 补默认值"；`serialization/codec/CodecAdaptor.java` 把任意 `@SerialClass` 直接变成 `StreamCodec`。**一次声明，四处复用**，是其网络/配置/数据包全部同构的根因。
2. **网络**：`l2serial/network/PacketHandler.java`——构造器接收 `Function<PacketHandler, PacketConfiguration<?>>...` 数组；包 id 由**类名小写化**自动推导（`of(Class)`，行 67-79）；`register(RegisterPayloadHandlersEvent)` 里 `event.registrar(modid).versioned(verStr).optional()` 注册，支持 optional 兼容；`BasePayload<T>` 统一包装 `CustomPacketPayload`，提供 `toServer / toTrackingPlayers / toTrackingOnly / toClientPlayer / toAllClient / toTrackingChunk / sendToNear` 七种投递方法。
3. **数据驱动 GUI 布局**：`MenuLayoutConfig`（`base/menu/base/MenuLayoutConfig.java`）是 `record(int height, HashMap<String,Rect> side, HashMap<String,Rect> comp)`，作为**数据包 registry** 注册（`L2LibReg.java:70` `REG.dataReg("menu_layout", ...)`），即界面槽位/贴图切片的坐标写在数据包里；`getSlot(key, fac, con)` 按 Rect 的 `rx/ry/w/h` 批量生成槽位，`ScreenRenderer.draw/drawBottomUp/drawLeftRight/drawLiquid` 负责渲染与进度条。
4. **配置**：`l2core/util/ConfigInit.java`——`L2Registrate.registerClient/registerUnsynced/registerSynced` 三分流到 `CLIENT/COMMON/SERVER`；文件固定落在 `l2configs/<modid>-<type>.toml`（`markL2()`）；`Builder.define` 被覆写，为每个配置项**自动生成 lang key 与 tooltip**（`ConfigInit.java:119-126`），并在客户端注册 NeoForge `ConfigurationScreen`。
5. **UI 扩展框架**：`l2tabs`（`tabs/core/TabManager`、`TabBase`、`TabGroup`、`TabType`，compat 层同时支持 curios 与 accessories，含 `Init/data/OpenCuriosPacket`）、`l2menustacker`（`screen/base/ScreenTracker`、`screen/track/*Trace`、`screen/packets/*ToClient`：把容器菜单做成分层"菜单栈"，支持 QuickAccess 快捷键、把物品/末影箱/背包作为可打开的追踪源）。
6. **效果 / 能力同步**：`capability/conditionals`（ConditionalData、PlayerFlagData，含 `NetworkSensitiveToken`）、`base/effects/api`、`PlayerCapabilityNetworkHandler` 与四个 ToClient 包构成统一的"服务端数据 → 客户端渲染"通道（`L2Core.java:27-32`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见上，l2serial `PacketHandler` + `SimplePacketBase` / `SerialPacketBase`；同步策略是"按需定向"（entity tracking / chunk / near / single player），非全量广播。
- 数据驱动：`init/reg/datapack/DatapackReg.java`（`DataPackRegistryEvent`，`dataReg(...)`）与 `DataMapReg`；已用于 `menu_layout`、`legacy_enchantment`；`serial/configval` 提供 `ConfigVal` 系列（`BooleanValueCondition` 等）让**数据包/战利品/配方读取 mod 配置值**；`serial/recipe`、`serial/loot`、`serial/advancements` 提供 codec 化的配方/掉落/进度构建。
- datagen：`Registrate.addDataGenerator`（如 `L2TagGen.EFF_TAGS`）、`init/data`、`MapCodeGen`；`build.gradle` 配置 `runs.data` 输出到 `src/generated/resources`。
- AT：`src/main/resources/META-INF/accesstransformer.cfg` 用量很大（配方 Builder 私有字段、`MobEffectInstance` 的 duration/amplifier、`LivingEntity.onEffectAdded`、`Level.getDestroyType`、`AbstractContainerMenu.addDataSlot` 等）。

## 6. Mixin

- `src/main/resources/l2library.mixins.json`（package `dev.xkmc.l2library.mixin`，priority 1000）：`AbstractArrowMixin`（`@Inject` 到 `AbstractArrow.tickDespawn` HEAD，按 persistentData 的 `ARROW_DESPAWN` 加速销毁）、`EntityMixin`、`LightningBoltMixin`、`SmithingTransformRecipeMixin`、client `ClientLocalPlayerMixin`。
- 子模块：`l2core.mixins.json` 仅 `CreativeModeTabMixin`；l2tabs / l2menustacker 各有 `AbstractContainerScreenMixin`，l2menustacker 另有 `MinecraftMixin`、`ServerPlayerMixin`。

## 7. 值得学的 5 条具体做法

1. **一份 `@SerialClass` POJO 全场景复用**：JSON/NBT/包/Codec 共用 `UnifiedCodec`，新增数据类型无需写 4 套序列化（`l2serial/.../UnifiedCodec.java`）——适合自建附件/能力/配方。
2. **包 id 由类名自动生成 + `optional()` 注册**：`PacketHandler.of(Class)` 小写化类名当路径，配合 `versioned().optional()`，缺包端不会崩（`l2serial/network/PacketHandler.java:67-79,126`）——适合附属 Mod 兼容。
3. **GUI 布局外置成数据包**：`MenuLayoutConfig` 用 `record + HashMap<String,Rect>`，槽位与贴图切片坐标写 JSON，多 Mod 复用同一容器界面（`l2core/base/menu/base/MenuLayoutConfig.java:72-81`）——适合成套机器/背包 UI。
4. **配置项自动补 lang 与 tooltip**：覆写 `ModConfigSpec.Builder.define`，用 `text()` 说明自动生成 `configuration.*` 语言键（`l2core/util/ConfigInit.java:119-126`）——适合配置多的 Mod。
5. **jarJar 多模块 + `libs/` 源包**：主仓库只留 32 个文件，功能拆分到子模块 jar，`jar { archiveClassifier='slim' }` + `tasks.jarJar` 直接产出发布包（`build.gradle:118-131`）——适合库型 Mod 的分层维护。

## 8. 公开 API 与接入方式（库/前置类）

- 公开 API 包：`dev.xkmc.l2core.*`（首选入口 `init/reg/registrate/L2Registrate`、`init/reg/simple/*`、`base/menu/base/*`、`base/tile/*`、`capability/*`）、`dev.xkmc.l2serial.*`（`@SerialClass`/`@SerialField`、`PacketHandler`、`CodecAdaptor`）、`dev.xkmc.l2tabs.*`、`dev.xkmc.l2menustacker.*`、`dev.xkmc.l2modularblocks.*`。
- 外部接入方式：`new L2Registrate("yourmodid")` 后调用 `registerSynced/registerClient`（配置）、`effect(name, sup, desc)` / `potion(...)` / `particle(...)`（带自动 lang 的注册）、`buildL2CreativeTab(name, def, cfg)`（连排序进 L2 创造栏）、`newRegistry(id, cls)`（自建 registry + 序列化 + 同步）；网络只需向 `new PacketHandler(modid, ver, ...)` 传包类数组。
- 扩展点/接口：`ConfigInit`（配置模板）、`DatapackReg`/`DataMapReg`（注册自己的数据包注册表）、`TabBase`/`TabType`（自定义创造栏标签页）、`SlotClickHandler` 与 `MenuSourceRegistry`/`MenuTraceRegistry`（自定义菜单追踪源与点击处理）、`ParticleSupplier`、`LootHelper`/`AddItemModifier`。

（说明：子模块数据来自 `libs/*-sources.jar` 解压结果，非仓库内源码；`l2serial` 等 jar 同时作为 `libs/` 内嵌依赖存在。）
