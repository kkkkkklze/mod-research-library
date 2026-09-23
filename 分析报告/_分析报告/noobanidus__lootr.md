# Lootr 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Lootr / `lootr`（`gradle.properties:11-12`）
- 作者：Noobanidus；许可证 MIT（`LICENSE:1`）
- 目标 MC / 加载器：Minecraft `1.21`，NeoForge `21.0.114-beta`（`gradle.properties:18-19`）；`neoforge.mods.toml` 中 `modLoader="javafml"`、`loaderVersion="[3,)"`
- Gradle：`com.github.johnrengelman.shadow` 8.1.1，加 SizableShrimp Forge-Class-Remapper（`build.gradle:1-11`）；**所有构建逻辑放在 git submodule** `gradle/` → `noobanidus/gradlehax`（branch 1.21，`.gitmodules`），本地未检出，故 `gradle/*.gradle` 不可读（未确认细节）
- 编译依赖：无强制前置。按 `build.gradle:26-47` 加载的可选集成模块：aequivaleo、blame、carrier_bees、curios、dynamic_trees、geckolib、jade、jei、repurposed_structures、mana_and_artifice、mysticalworld、patchouli、stables、top
- 访问转换器：`src/main/resources/META-INF/accesstransformer.cfg`（在 toml 与 `gradle.properties:26` 声明）

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **102 个**，总计 **8950 行**（`find … -exec wc -l {} +`）。

包结构（`src/main/java/noobanidus/mods/lootr/`）：
- `api/`（8 文件）+ `api/data`（10）、`api/data/{blockentity,entity,inventory}`、`api/registry`（2）、`api/advancement`（4）、`api/client`、`api/network` —— **纯接口 + 静态门面，不含实现**
- `common/`（与加载器无关）：`common/block`（6）、`common/block/entity`（6）、`common/data`（3）、`common/loot/conditions`、`common/mixins`（9）、`common/client`、`common/command`、`common/entity`、`common/advancement`
- `neoforge/`（平台实现）：`neoforge/init`（9 注册类）、`neoforge/impl`（2）、`neoforge/network`（2）+`toClient`（4）+`client`、`neoforge/config`（1）、`neoforge/gen`（5）、`neoforge/event`（5）、`neoforge/block`、`neoforge/client`

最大文件：`neoforge/impl/LootrAPIImpl.java` 624、`neoforge/config/ConfigManager.java` 409、`api/LootrAPI.java` 395、`common/block/entity/LootrShulkerBlockEntity.java` 367、`LootrBarrelBlockEntity.java` 314、`LootrChestBlockEntity.java` 311、`common/command/CommandLootr.java` 305、`common/data/DataStorage.java` 286、`common/entity/LootrChestMinecartEntity.java` 282、`api/ILootrAPI.java` 237。

## 3. 入口与注册

主类 `src/main/java/noobanidus/mods/lootr/neoforge/Lootr.java:28-54`：

```java
@Mod("lootr")
public class Lootr {
  public static Lootr instance;
  private final PacketHandler packetHandler;
  public Lootr(ModContainer modContainer, IEventBus modBus) {
    instance = this;
    LootrAPI.INSTANCE = new LootrAPIImpl();       // API→实现注入
    LootrRegistry.INSTANCE = new LootrRegistryImpl();
    modContainer.registerConfig(ModConfig.Type.COMMON, ConfigManager.COMMON_CONFIG);
    modContainer.registerConfig(ModConfig.Type.CLIENT, ConfigManager.CLIENT_CONFIG);
    NeoForge.EVENT_BUS.addListener(this::onCommands);
    ModTabs.register(modBus); ModBlockEntities.register(modBus); ModBlocks.register(modBus);
    ModEntities.register(modBus); ModItems.register(modBus); ModLoot.register(modBus);
    ModStats.register(modBus); ModAdvancements.register(modBus);
    this.packetHandler = new PacketHandler(modBus);
  }
}
```

注册框架：**NeoForge `DeferredRegister` 手写静态类**，每个 `neoforge/init/ModXxx` 一个 `private static final DeferredRegister<T> REGISTER` + `public static final DeferredHolder<…>` + 统一 `public static void register(IEventBus bus)`（样例 `neoforge/init/ModBlocks.java:16-34`）。`ModLoot` 注册 `LootItemConditionType`，`ModStats`/`ModAdvancements` 注册统计与触发器，`ModTabs` 创造栏。

## 4. 核心系统

**(a) 每玩家独立战利品（per-player loot）**
- `api/data/ILootrInfoProvider.java`：容器情报接口，提供静态工厂 `ILootrInfoProvider.of(BlockPos, Level)`、`.of(RandomizableContainerBlockEntity, UUID, NonNullList<ItemStack>)`（行 24-58），把 vanilla 箱子、矿车、自定义情报统一成一种"提供者"。
- `common/data/LootrSavedData.java:24-28`：`extends SavedData implements ILootrSavedData`，内部 `Map<UUID, LootrInventory> inventories = new HashMap<>()`，每个玩家 UUID 一份独立库存；`save/load(CompoundTag, HolderLookup.Provider)` 用 `ContainerHelper.loadAllItems` 序列化物品。
- `common/data/LootrInventory.java:23`：实现 `ILootrInventory`（即 `Container`），`createMenu` 时挂 `MenuBuilder`，`startOpen/stopOpen` 驱动其他玩家的动画。
- `common/data/DataStorage.java:31-34`：三份独立 `SavedData` 名 —— `lootr/Lootr-AdvancementData`、`lootr/Lootr-DecayData`、`lootr/Lootr-RefreshData`，静态方法全走 `DimensionDataStorage`；配合 `common/mixins/MixinDimensionDataStorage.java`。

**(b) 未加载区块的容器 tick**
- `common/block/entity/BlockEntityTicker.java:20-25`：`ObjectLinkedOpenHashSet` 的 `blockEntityEntries` + `pendingEntries` 双集合、`listLock`/`worldLock` 双锁、`tickingList` 标志，`onServerTick()` 批量交付。设计意图：tick 遍历时把新加入的 Entry 排入 pending，避免 ConcurrentModification；`common/mixins/MixinLevelChunk.java` 在 `updateBlockEntityTicker` HEAD 处补挂自定义 tick。

**(c) 接管原版容器（mixin 驱动）**
mixin 让 Lootr 方块被村民/猫/结构识别为"真箱子"并把原版箱子替换掉（详见第 6 节）。

**(d) 通知 / 命令 / 统计**
`common/command/CommandLootr.java`（305 行）注册 `/lootr` 子命令（转换、清空、统计）；`ModStats`+`api/advancement/{IAdvancementTrigger,IContainerTrigger,ILootedStatTrigger}` 抽象触发器，`LootrRegistryImpl` 提供实现。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`neoforge/network/PacketHandler.java:19-48`。1.21 新式 `RegisterPayloadHandlersEvent` + `PayloadRegistrar`（注释注明抄 Mekanism `BasePacketHandler`）。仅 4 个 S2C 包：`PacketOpenCart/PacketOpenContainer/PacketCloseCart/PacketCloseContainer`，C2S 为空。巧妙点：`record PacketRegistrar(PayloadRegistrar registrar, boolean toServer)` 包装同一个 registrar，`play()` 内部按方向调 `playToClient/playToServer`，handler 直接用方法引用 `ILootrNeoForgePacket::handle`。握手版本号 `LootrAPI.NETWORK_VERSION = "lootr-1.21.0-1"`（`api/LootrAPI.java:33`）。
- **数据驱动**：loot table 驱动核心 —— `ModLoot` 注册自定义 `LootItemConditionType`（loot count 条件，`api/data/LootrBlockType`、`common/loot/conditions/`）；`src/main/resources/data/lootr/loot_tables/blocks/` 与 `data/lootr/tags/block/convert`（可转换方块 tag）；自定义方块实体类型由 `ModBlockEntities` 注册，情报（lootTable/seed/openers）存 SavedData + NBT。
- **配置**：`neoforge/config/ConfigManager.java`（409 行）纯静态字段的 `ModConfigSpec.BooleanValue / IntValue / ConfigValue<List<? extends String>>`（行 36-57），主类手动 `ConfigManager.loadConfig(...)`，字段级缓存；覆盖 dimension/lootTable/modid 白黑名单、decay/refresh 开关、破坏与比较器行为。
- **datagen**：`neoforge/gen/LootrDataGenerators.java:16-30`，`@EventBusSubscriber(bus = MOD)` + `GatherDataEvent` 一次注册 BlockTag / ItemTag / Atlas / LootTable 四个 provider；产物在 `src/generated/resources`。

## 6. Mixin

配置：`src/main/resources/lootr.mixins.json`（`required: true`、package `noobanidus.mods.lootr.common.mixins`、`compatibilityLevel: JAVA_17`、`injectors.defaultRequire: 1`、无 client 段），toml 中 `[[mixins]] config="lootr.mixins.json"`。9 个 mixin 类全在 `common/mixins/`：

| 类 | 目标 | 注入点 |
|---|---|---|
| `MixinPoiType` | `PoiType` | `is` @At RETURN，cancellable（让箱子 POI 命中 Lootr 方块） |
| `MixinPoiTypes` | `PoiTypes` | `forState`、`hasPoi` @At RETURN，cancellable |
| `MixinCatSitOnBlockGoal` | `CatSitOnBlockGoal` | `isValidTarget` @Redirect `BlockState.is(Block)` + @Inject `ChestBlockEntity.getOpenCount` |
| `MixinEndCityPieces$EndCityPiece` | `EndCityPieces.EndCityPiece` | `handleDataMarker` @Inject `ServerLevelAccessor.addFreshEntity`，`require = 0` |
| `MixinStructureTemplate` | `StructureTemplate` | `fillFromWorld`，在 `BlockEntity.saveWithId` 前/后成对注入（拆装箱容器 NBT） |
| `MixinLevelChunk` | `LevelChunk` | `updateBlockEntityTicker` @At HEAD |
| `MixinBaseContainerBlockEntity` / `MixinDimensionDataStorage` / `MixinVehicleEntity` | 同名 vanilla 类 | 类级 `@Mixin`，具体注入点未逐行确认 |

## 7. 值得学的 5 条具体做法

1. **API/实现双包分离**：`api/` 只放静态门面 `LootrAPI`（395 行全是 `return INSTANCE.xxx()`）+ 接口，实现在 `neoforge/impl`，主类构造时赋值 `LootrAPI.INSTANCE`。适用：任何想给其他 mod 提供接入点的库式 mod。见 `api/LootrAPI.java:36`、`neoforge/Lootr.java:37`。
2. **静态门面转接口，平台可换**：`api/ILootrAPI.java`（237 行）把全部行为抽象为接口，换加载器只换 `LootrAPIImpl`。适用：多加载器/多版本共存。
3. **统一"提供者"工厂**：`ILootrInfoProvider.of(...)` 多个重载把方块实体、矿车、自定义数据都归一，调用方不需要类型判断。见 `api/data/ILootrInfoProvider.java:24-58`。
4. **tick 任务用 pending 集合 + 双锁**：避免在遍历中修改集合，`BlockEntityTicker` 是可直接抄的模式。见 `common/block/entity/BlockEntityTicker.java:21-25`。
5. **网络注册用一个 record 包装方向**：`record PacketRegistrar(registrar, toServer)` 让 C2S/S2C 共用一份注册代码，方法引用做 handler。见 `neoforge/network/PacketHandler.java:39-48`。

## 8. 公开 API（Lootr 是"可被其他 mod 侵入"的功能型 mod）

- 入口门面：`api/LootrAPI.java`（`MODID`、`NETWORK_VERSION`、`rl(String)`、`INSTANCE`）
- 接口：`api/ILootrAPI.java`、`api/IClientOpeners.java`、`api/IOpeners.java`、`api/IRedirect.java`、`api/IMarkChanged.java`、`api/network/ILootrPacket.java`
- 数据扩展点：`api/data/ILootrInfo.java`、`ILootrInfoProvider`、`ILootrSavedData`、`CustomLootrInfoProvider.java`、`LootFiller.java`、`DefaultLootFiller.java`、`MenuBuilder.java`、`LootrBlockType.java`、`api/data/inventory/ILootrInventory.java`
- 注册表镜像：`api/registry/LootrRegistry.java` + `ILootrRegistry.java`，静态暴露全部 Lootr 方块/物品/方块实体/触发器/`LootedStat`/创造栏 —— 外部 mod 无需引用 `neoforge` 包即可拿到引用
- 触发器接口：`api/advancement/{IAdvancementTrigger,IContainerTrigger,ILootedStatTrigger}`；标签：`api/LootrTags.java`
- 外部接入方式：依赖 `lootr` 的 `api` 包 → 调 `LootrAPI.*` / `LootrRegistry.*`；让自己的方块实体实现 `ILootrInfoProvider`（或实现 `CustomLootrInfoProvider`）即可被 Lootr 的 opener/decay/refresh 体系接纳；被接管方块需加入 `data/lootr/tags/block/convert`。
