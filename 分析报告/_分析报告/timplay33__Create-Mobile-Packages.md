# timplay33 / Create-Mobile-Packages 源码分析

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 | Create: Mobile Packages |
| mod_id | `create_mobile_packages` |
| 作者 | Tim Heidler |
| 版本 | 0.7.7（构建号/分支名由 `BUILD_NUMBER`、`BRANCH_NAME` 注入） |
| 目标 MC / 加载器 | Minecraft 1.21.1 / **NeoForge 21.1.219**（`neo_version_range=[21.1.0,)`，`loader_version_range=[4,)`） |
| Gradle 插件 | `net.neoforged.moddev` 2.0.78 + **`com.hypherionmc.modutils.modpublisher` 2.1.7**（自动发 Modrinth/CurseForge/GitHub） |
| Java | toolchain 21 |
| 许可证 | MIT |
| group | `de.theidler.create_mobile_packages` |

依赖（`gradle.properties:22-31`、`build.gradle:214-243`）：Create 6.0.10-280、Ponder 1.0.82、Flywheel 1.0.6、Registrate MC1.21-1.3.0+67；JEI 19.21.0.247（implementation）、EMI 1.1.24（`compileOnly :api` + `localRuntime` 全量，**不污染下游**的写法）、**`ru.zznty:create_factory_abstractions` 用 `jarJar(...)` 内嵌**（提供 `GenericOrder`，支持任意类型订单）、`curse.maven:create-fluidlogistic`（implementation）、Curios 9.5.1（compileOnly api + runtimeOnly）、Jade 15.10.5（implementation）；测试用 `runtimeOnly` 引入 CarryOn、Sable；注解处理器 `org.spongepowered:mixin:0.8.5:processor` 被 `if (!Boolean.getBoolean("idea.sync.active"))` 包裹以规避 IDE 同步问题。

构建亮点：`build.gradle:38-60` 自定义 `readLatestChangelogSection()`，用 `-{10,}` 分隔行从 `CHANGELOG.md` 解析出最新一节（正则 `line ==~ /^-{10,}\s*$/`）作为发布 changelog；`publisher {}` 声明 `modrinthDepends { required "create"; optional "create_factory_logistics" }`、`getJavaVersions([JavaVersion.VERSION_21])`。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` → **112 个 .java / 11224 行**（无内嵌第三方源码）。

包结构（`de/theidler/create_mobile_packages/`）：

| 包 | 文件数 | 说明 |
|---|---|---|
| （根） | 6 | `CreateMobilePackages`(主类)、`CreateMobilePackagesClient`、`CommonEvents`、`InputEvents`、`CMPHelper`、**`IExtendedLogisticsNetwork`**（duck 接口） |
| `index/` | 14 | 注册类 `CMPBlocks / CMPItems / CMPEntities / CMPBlockEntities / CMPMenuTypes / CMPPackets / CMPDataComponents / CMPDisplaySources / CMPShapes / CMPIcons / CMPKeys / CMPToasts / CMPGuiTextures / CMPCommands(238)`；`index/config`(4)、`index/ponder/{scenes}` |
| `blocks/bee_port/` | 12 | 蜂巢港：`BeePortBlock/BlockEntity(688)/Menu/Screen`、`RoboRequest`、`FilterMode`、`BeeCountDisplaySource`、`BeeOnTravelETADisplaySource`、`DronePortTracker`、2 个 toggle 包 |
| `robo/` | 7 | 服务端虚拟无人机：`RoboManager(326)`、`VirtualRobo(390)`、`RoboTarget` + `BeePortBlockEntityTarget/BlockPosTarget/PlayerTarget`、`RoboTrashStore` |
| `entities/` | 5 + `models`/`render` | `RoboEntity(163)`、`RoboBeeState`、`RoboBeeBehaviorController(338)` |
| `items/` | 21 | `portable_stock_ticker`(12)+`trash_menu`(6)、`mobile_packager`(8)、`robo_bee`(1) |
| `network_settings/` | 13 | 物流网络成员/命名/锁定 UI：`NetworkSettingsScreen(481)`、`PlayerNetworksScreen(317)`、`ClientNetworkDataStorage`、`NetworkHelper` + 7 个包 |
| `compat/` | 12 | `Mods`（枚举式模组判定）、`FactoryAbstractions`、`fluidlogistics/CFLBridge`、`sable`、`curios`、`emi`、`jade`、`jei`(3, 最大 419 行) |
| `toast/` | 5 + `types`(2) | 自定义通知框架 |
| `mixin/` | 1 | `LogisticsNetworkMixin` |

最大文件：`items/portable_stock_ticker/PortableStockTickerScreen.java`(1423)、`blocks/bee_port/BeePortBlockEntity.java`(688)、`network_settings/NetworkSettingsScreen.java`(481)、`compat/jei/DroneControllerTransferHandler.java`(419)、`robo/VirtualRobo.java`(390)。注意：仓库内**没有任何 assets/data/生成资源**，`src/generated/resources` 为空，无 datagen。

## 3. 入口与注册

主类 `src/main/java/de/theidler/create_mobile_packages/CreateMobilePackages.java:22-59`：

```java
@Mod(CreateMobilePackages.MODID)
@EventBusSubscriber(modid = CreateMobilePackages.MODID)   // 同一类同时挂 mod 总线与游戏总线
public class CreateMobilePackages {
    public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID)
        .defaultCreativeTab("create_mobile_packages_tab", t -> {
            t.icon(() -> CMPItems.ROBO_BEE.get().getDefaultInstance());
            t.title(Component.translatable("itemGroup.create_mobile_packages"));
        }).build()
        .setTooltipModifierFactory(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item))));
```

**`defaultCreativeTab(...).build()` 直接挂在 Registrate 链上**（比 CDG/Radar 的独立 CreativeTab 类更紧凑）。构造函数顺序注册：`CMPBlocks → CMPItems → CMPBlockEntities → CMPMenuTypes → CMPPackets → CMPConfigs.register(modLoadingContext, modContainer) → CMPEntities → CMPDisplaySources → CMPDataComponents → CMPToasts.registerAll()`（`:48-57`）。命令走 `@EventBusSubscriber` + `RegisterCommandsEvent → CMPCommands.register`（`:65-68`）。`index/CMPEntities.java:12-19` 用 Registrate 的 `entity(...).properties(p -> p.sized(0.6F,0.6F).noSave())` 注册无人机实体。

## 4. 核心系统

**(1) 物流网络扩展：Mixin + Duck 接口（本仓库最有教学价值的一处）**
- 目标：给 Create 的 `LogisticsNetwork` 增加"成员集合 / 网络名 / 所有者是否成员"。
- `CreateMobilePackages.java` 同级定义 `IExtendedLogisticsNetwork.java`（8 个 `create_mobile_packages$xxx` 方法），由 `mixin/LogisticsNetworkMixin.java:29` `@Mixin(value = LogisticsNetwork.class, remap = false) abstract class ... implements IExtendedLogisticsNetwork` 实现——即 **duck-interface 模式：接口给自己用，mixin 给 Create 的类"贴"上实现**，外部调用处只需 `instanceof IExtendedLogisticsNetwork` 转换。
- 细节：`@Unique` 字段全部用 `create_mobile_packages$` 前缀避免与 Create 冲突（`:35-40`）；`@Shadow public UUID owner` 读 Create 私有字段；`@Inject` 到静态 `read` 的 `RETURN` 与实例 `write` 的 `RETURN`（`:42-93`）——在 Create 自己的 NBT 之外追加 `CMP_Players`（用 `NBTHelper.iterateCompoundList/writeCompoundList`）、`CMP_IsOwnerMember`、`name`；构造器 `TAIL` 注入兜底初始化。所有写操作后调 `Create.LOGISTICS.markDirty()` 保证持久化（`:117-147`）。包名以 modid 为前缀的 `CMP_` 键名避免冲突。

**(2) 服务端虚拟无人机 `RoboManager extends SavedData`**
- `robo/RoboManager.java:26-34`：`Map<UUID, VirtualRobo> robos`（`init()` 用 `ConcurrentHashMap`，`:309-311`）+ `List<RoboRequest> beePortRoboRequests` + `List<RoboTrashStore> roboTrashStores`；`get(ServerLevel)`/`load`/`save` 走 SavedData；`tick(ServerLevel)`(:163) 驱动所有无人机与请求状态机，`tryHandlingRequest(RoboRequest, level)`(:200) 做派单。
- 并发安全：垃圾桶相关方法全部 `synchronized`（`getTrashStore/takeTrashItems/setTrashSlots/setTrashTargetAddress`，`:95-160`）。
- 请求对象 `blocks/bee_port/RoboRequest.java`：`enum Status { PENDING, IN_PROGRESS, DONE, CANCELLED }`、`enum Mission { RESTOCK, DELIVER, PICKUP }`，自带 ETA 字段（`getEta()` 在 DONE/CANCELLED 时返回 -1）。
- 目标用**策略接口** `robo/RoboTarget.java`：`getTargetPos()/setETA()/getETA()` + 三个 `default asBeePortBlockEntity()/asPlayer()/asBlockPos()`（默认 null，由子类覆写），实现类 `BeePortBlockEntityTarget / BlockPosTarget / PlayerTarget`——比 `instanceof` 分支干净得多。

**(3) 行为状态机 `RoboBeeBehaviorController` / `RoboBeeState`**
- `entities/robo_entity/RoboBeeState.java` 8 态：`IDLE, TAKEOFF, NAVIGATE_TO_TARGET, ALIGN_FOR_DELIVERY, DELIVER_PACKAGE, PICKUP_PACKAGE, LAND, SHUTDOWN`。
- `RoboBeeBehaviorController.java:26-31` 持有 `state`/`init`/`lastLandedPort`，`tick(VirtualRobo)` 内 `switch (state)` 分派到 `handleIdle/handleTakeoff/handleNavigateToTarget/handleAlignForDelivery/handleLand/handleDeliverPackage/handlePickupPackage/handleShutdown`；移动封装为 `moveTo(robo, target, speed)`、`moveAndScale(robo, target, speed, scaleStart, scaleEnd)`（起飞/降落时的缩放动画）、`isAtTarget(...)`；`openPort(port, open)` 在到达时开关港口。**纯服务端仿真，不依赖实体 AI（无 Goal/PathNavigation）**。

**(4) 虚拟体 + 表现体分离**
- `robo/VirtualRobo.java:25-42`：`id / logisticsNetworkId / itemStack / currentPos / yaw / pitch / entityId / speed / behaviorController / target / targetVelocity / serverLevel / packageHeightScale / homePortPos / returnToHomeAfterDelivery`——真正的"数据体"，随 SavedData 存档。
- `entities/robo_entity/RoboEntity.java:28-34`：`extends Mob`，三个同步数据 `ROT_YAW / DATA_ITEM_STACK / PACKAGE_HEIGHT_SCALE`（`SynchedEntityData.defineId`），`public UUID linkedId` 关联虚拟体；`syncFromVirtual(VirtualRobo)`(:155) 每 tick 把服务端状态刷到客户端表现；`shouldBeSaved()` 与实体注册的 `.noSave()` 保证实体**不入档**，重启后由 `VirtualRobo` 重建。这是"逻辑体持久化 + 实体仅作表现"的完整范例（对无人机/飞船/投射物类实体通用）。

**(5) 蜂巢港方块（复用 Create 包裹港）**
- `blocks/bee_port/BeePortBlockEntity.java:59` `extends PackagePortBlockEntity`；`ROBOBEE_INVENTORY_STACK_SIZE=64`、`ContainerData data = SimpleContainerData(4)`（供菜单同步）、`ItemStackHandler roboBeeInventory(1)`、`boolean beeReturnModeEnabled`、`enum FilterMode`、匿名 `IItemHandler handler`（只允许箱子槽位放无人机，`:70-173`）；`roboSendCooldown` + `lazyTick()` 节流，`tryPushingToAdjacentInventories/tryPullingFromAdjacentInventories/getAdjacentInventories` 做邻接库存交互（`:315-373`）；`requestRoboEntity()` 用 `RoboManager.get(serverLevel).requestRobo(new BeePortBlockEntityTarget(this), getLogisticsNetworkId(), RoboRequest.Mission.RESTOCK)`（`:244-247`）。
- 显示集成：`index/CMPDisplaySources.java:13-14` 用 `REGISTRATE.displaySource("bee_count"/"bee_eta", ...)` 注册两个 Create 显示源；菜单 `index/CMPMenuTypes.java:26-31` 直接复用 Create 的 `PackagePortMenu` 类型（`MenuEntry<PackagePortMenu> BEE_PORT_MENU`）。

**(6) 自定义 Toast 通知框架（可复用度极高）**
- `toast/Toast.java:14-42`：抽象基类，含 `Map<String, BiFunction<RegistryFriendlyByteBuf, UUID, Toast>> REGISTRY` 类型注册表 + `StreamCodec.of(Toast::write, Toast::read)` 手写多态序列化（先写 `typeId` 再交给对应工厂），字段 `id/timeout/height/lastUpdate`。
- 配套：`toast/types/{PackageToast, SimpleToast}` 两个实现、`toast/ToastOverlayRenderer.java:46` 挂 `RenderGuiEvent.Post` 统一渲染、三个包 `ShowToastOnClientPacket / RemoveToastOnClientPacket / RemoveAllToastsOnClientPacket` 做服务端→客户端指令、`index/CMPToasts` 注册、`/cmp toast clear|create` 调试命令（`index/CMPCommands.java:31-45`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：Create 6 的 Catnip 框架。`index/CMPPackets.java` 是**一个 24 项的大枚举**（16 个 C2S + 8 个 S2C，用注释分组，`// Client to Server` / `// Server to Client`），构造时 `new CatnipPacketRegistry.PacketType<>(new CustomPacketPayload.Type<>(asResource(name().toLowerCase())), clazz, codec)`，`register()` 用 `new CatnipPacketRegistry(MODID, 1)` 遍历注册——**包 ID 由枚举序号隐式决定，新增包只需加一行**。
- 包体实现方向由接口决定：如 `items/portable_stock_ticker/SendPackage.java:18` `implements ServerboundPacketPayload`，`STREAM_CODEC = StreamCodec.composite(FactoryAbstractions.GENERIC_ORDER_STREAM_CODEC, p -> p.order, ByteBufCodecs.STRING_UTF8, p -> p.address, SendPackage::new)`，`handle(ServerPlayer player)` 内做权限/旁观/冒险模式检查后复用 Create 的 `AllSoundEvents / AllAdvancements / WiFiEffectPacket`——**UI 与逻辑分离：客户端只发包，服务端查玩家背包里的物品再执行**。
- 客户端状态缓存：`network_settings/ClientNetworkDataStorage.java` 存服务端下发的网络列表，配合 `RequestNetworkDataPacket / NetworkDataPacket / ClearNetworksPacket` 做"请求—下发—清理"三件套。
- **数据驱动**：无自定义数据包注册表、无配方/标签数据（仓库不含 data 目录）。**datagen：无**（全仓库无 `GatherDataEvent`/`DataGenerator` 引用）。
- **配置**：catnip `ConfigBase` 体系。`index/config/CMPConfigs.java:18-64` 与 Create-Radar 同构（`EnumMap<ModConfig.Type, ConfigBase>` + `ModConfigSpec.Builder().configure(builder -> config.registerAll(builder))`），三份：`CMPClient`(46 行)、`CMPCommon`(14)、`CMPServer`(34)，在构造中 `register(ModLoadingContext, ModContainer)` 统一注册。

## 6. Mixin

- 配置：`src/main/resources/create_mobile_packages.mixins.json`——`required:true`、`package de.theidler.create_mobile_packages.mixin`、`refmap create_mobile_packages.refmap.json`、`minVersion "0.8"`、`compatibilityLevel "JAVA_17"`（注意：工具链是 Java 21，此值偏保守但兼容）、`client: []`、**`mixins: ["LogisticsNetworkMixin"]` 仅此一个**。
- 该唯一 mixin 是**纯功能扩展型**（不是 bugfix）：`@Mixin(value = LogisticsNetwork.class, remap = false)` + `implements IExtendedLogisticsNetwork`，注入点三处：静态 `read` 的 `@At("RETURN")`、构造器 `<init>` 的 `@At("TAIL")`、实例 `write` 的 `@At("RETURN")`。`remap = false` 因为目标是 Create（非混淆名）。
- 无 `IMixinConfigPlugin`、无 MixinExtras、无 `@Redirect/@ModifyVariable`——**只在 Create 的数据类上"加字段 + 加 NBT"，是被 Create 附属模组广泛使用的安全模式**。

## 7. 值得学的 5 条做法

1. **Duck 接口 + `create_mobile_packages$` 前缀的 `@Unique` 字段扩展第三方模组数据类**：不改 Create 的字节码逻辑，只增字段与 NBT 读写，调用侧 `instanceof` 转换即可。`mixin/LogisticsNetworkMixin.java:29-93` + `IExtendedLogisticsNetwork.java`。
2. **"虚拟逻辑体 + 非持久化表现实体"分离**：`VirtualRobo` 进 `SavedData` 负责一切逻辑，`RoboEntity`（注册为 `.noSave()`、`shouldBeSaved()=false`）只做渲染与插值，`syncFromVirtual()` 单向刷数据。`robo/VirtualRobo.java:25-42`、`entities/robo_entity/RoboEntity.java:28-34,155`。
3. **自定义 Toast 用"类型 ID + 工厂注册表 + `StreamCodec.of(write, read)`"实现多态网络序列化**，比给每种通知建一个包体省事得多。`toast/Toast.java:14-42`、`toast/ToastOverlayRenderer.java:46`。
4. **目标选择用策略接口 + 三个 `default` 转换方法（返回 null）**，避免到处 `instanceof` 分支。`robo/RoboTarget.java`。
5. **`jarJar(...)` 内嵌强耦合的 API 模组（create_factory_abstractions）并用 `GenericOrder` 抽象订单**，让自己的订单系统同时支持物品/流体/能量类型，而不必硬依赖每个下游模组。`build.gradle:229`、`items/portable_stock_ticker/SendPackage.java:18-24`。

## 8. 公开 API / 扩展点

非库模组。对外接口：`IExtendedLogisticsNetwork`（通过 `instanceof` 从 Create 的 `LogisticsNetwork` 取得，可读写成员/网络名/所有者成员标记）；Create 显示源 `bee_count`、`bee_eta`（可被显示链接直接引用）；`compat/Mods` 枚举式的软依赖判定工具（`Mods.JEI/CURIOS/JADE/EMI/FLUIDLOGISTICS`，注明 "from com/simibubi/create/compat/Mods.java"，可直接抄）；`compat/fluidlogistics/CFLBridge`、`compat/sable/SableCompat` 为可选下游提供集成入口。
