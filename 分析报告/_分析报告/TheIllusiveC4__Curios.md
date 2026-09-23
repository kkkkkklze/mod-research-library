# TheIllusiveC4/Curios 源码分析报告

> 分析对象：`_参考仓库/_bulk/TheIllusiveC4__Curios`，本地检出分支 `26.x`（`git log`：`8c2110c Update to Minecraft 26.2`）。
> **重要提示**：所有事实来自该检出（NeoForge 26.2 / Java 25 世代）。仓库另存 Forge 1.20.1 / NeoForge 1.21.1 分支，但本地 clone 只有 `26.x` 一个分支（`git branch -a` 仅 `origin/26.x`），旧版本细节**未确认**。
> **检出完整性**：`git ls-files` 有 259 个文件，磁盘仅 158 个：`META-INF/services/*`、`data/curios/**/*.json`、全部贴图、`pack.mcmeta` 在 git 中存在但未落地到磁盘（下文引用这些内容时以 `git show HEAD:` 为准）。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Curios API / `curios`（`gradle.properties:12`，`src/main/java/top/theillusivec4/curios/CuriosConstants.java:28`） |
| 作者 | C4（TheIllusiveC4，`gradle.properties:11`） |
| 目标版本 | Minecraft `26.2`、NeoForge `26.2.0.26-beta`，范围 `[26.2,)` / `[26.2,27)`（`gradle.properties:8-21`） |
| 加载器 | **仅 NeoForge**：单 source set，无 `fabric.mod.json` / `mods.toml` / accesswidener；jar 名为 `${mod_id}-neoforge`（`build.gradle:35`）；模组元数据由 `src/main/templates/META-INF/neoforge.mods.toml` 经 `expand` 生成（`build.gradle:139-157`） |
| Gradle 插件 | `java-library` + `net.neoforged.moddev 2.0.141` + `maven-publish` + `com.modrinth.minotaur` + `net.darkhax.curseforgegradle`；toolchain Java 25（`build.gradle:8-45`），Gradle 9.6.1 |
| 许可证 | LGPL-3.0-or-later |
| 编译依赖 | 仅 JEI：`compileOnly mezz.jei:jei-26.2-neoforge-api` + `localRuntime`（`build.gradle:117-118`）；REI/EMI 依赖被注释（`build.gradle:120-125`）。**没有对任何 API 前置的依赖**——它自己就是别人的前置 |
| 产物 | 除主 jar 外额外产出 `apiJar`（仅打包 `top/theillusivec4/curios/api/**`，`build.gradle:104-109`）并发布到 maven（`build.gradle:296-317`），这是"库 mod"的标准做法 |

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **141**；总行数 **17813**（main 125 文件 16843 行；test 16 文件 970 行）。

| 包（到 3 层） | 文件/行 | 说明 |
|---|---|---|
| `curios`（根） | 2 / 181 | `CuriosCommonMod`、`CuriosConstants` |
| `api` | 14 / 1907 | Facade：`CuriosApi`、`CuriosSlotTypes`、`CuriosCapability`、`CuriosResources`、`CuriosDataProvider`、`CuriosTags` |
| `api/event` | 7 / 1175 | 供外部监听的事件 |
| `api/type/{capability,data,inventory}` | 3+2+2 | `ICurio`/`ICurioItem`/`ICuriosItemHandler`、`ISlotData`/`IEntitiesData`、`ICurioStacksHandler`/`IDynamicStackHandler` |
| `api/internal/services`(+`client`) | 5+1 | 内部 SPI 接口（`ICuriosSlots`/`ICuriosExtensions`/`ICuriosRegistry`/`ICuriosNetwork`/`ICuriosCodecs`） |
| `api/client`、`api/extensions`、`api/common` | 3+2+2 | `ICurioRenderer`、`RegisterCuriosExtensionsEvent`/`ICurioSlotExtension`、`CuriosCommonHooks`/`DropRule` |
| `impl` | 6 / 632 | SPI 实现（`CuriosSlots`/`CuriosExtensions`/`CuriosRegistry`/`CuriosNetwork`/`CuriosCodecs`/`CuriosClientExtensions`） |
| `common` | 1 / 673 | `CuriosCommonEvents`（事件总线集中地） |
| `common/capability` | 4 / 1176 | `CurioInventory`、`CurioInventoryCapability`、`CombinedCuriosResourceHandler`、`ItemizedCurioCapability` |
| `common/inventory`(+`container`) | 3+2 | `CurioStacksHandler`、`DynamicStackHandler`、`CurioSlot`、`CuriosMenu` |
| `common/data` | 3 / 888 | `CuriosSlotResources`、`SlotData`、`EntitiesData` |
| `common/network`(client/server/sync) | 1+8+5+6 | `NetworkHandler` 与 16 个 payload |
| `mixin`(+`core`) | 1+11 | `CuriosCommonMixinHooks` + 11 个 mixin |
| `client`(+`screen/button`) | 4+2+5 | 客户端入口、GUI、按钮 |
| `config` / `server/command` | 2 / 3 | `CuriosConfig`、`CuriosCommand`、`CurioArgumentType` |

最大文件：`common/capability/CurioInventoryCapability.java`(711)、`common/CuriosCommonEvents.java`(673)、`common/inventory/CurioStacksHandler.java`(662)、`client/screen/CuriosScreen.java`(517)、`api/event/CurioAttributeModifierEvent.java`(507)、`common/inventory/container/CuriosMenu.java`(501)、`api/CuriosApi.java`(494)、`api/client/ICurioRenderer.java`(465)。

## 3. 入口与注册

主类 `src/main/java/top/theillusivec4/curios/CuriosCommonMod.java:59-141`（`@Mod(CuriosConstants.MOD_ID)`），构造器把注册全部委托出去：

```java
public CuriosCommonMod(IEventBus eventBus, ModContainer modContainer) {
  CuriosRegistry.init(eventBus);
  CuriosIntegrations.setup(eventBus);
  eventBus.addListener(this::registerCaps);            // RegisterCapabilitiesEvent
  eventBus.addListener(this::registerPayloadHandler);  // RegisterPayloadHandlersEvent
  NeoForge.EVENT_BUS.addListener(this::reload);        // AddServerReloadListenersEvent
  modContainer.registerConfig(ModConfig.Type.CLIENT, CuriosClientConfig.CLIENT_SPEC);
  modContainer.registerConfig(ModConfig.Type.COMMON, CuriosConfig.COMMON_SPEC);
  modContainer.registerConfig(ModConfig.Type.SERVER, CuriosConfig.SERVER_SPEC);
}
```

- **DeferredRegister 集中在一个 impl 类**：`impl/CuriosRegistry.java:46-88` 注册 5 类对象——`AttachmentType<CurioInventory>`（`inventory`，`serializable(...).copyOnDeath()`）、`CriterionTrigger`（`equip_curio`，`EquipCurioTrigger`）、`ArgumentTypeInfo`（`slot_type`）、`MenuType`（`curios_container`）、`DataComponentType`（`attribute_modifiers`，`persistent + networkSynchronized + cacheEncoding`）。用的是 NeoForge 原生 `DeferredRegister`，没用 Registrate。
- **能力注册遍历全部注册表**（`CuriosCommonMod.java:85-130`）：对 `BuiltInRegistries.ENTITY_TYPE` 中每个实体注册 `CuriosCapability.ITEM_HANDLER`(新 transfer API) 与 `INVENTORY`，但**只有该实体存在默认槽位时才返回实例，否则返回 `null`**（=无能力）；对每个 `Item` 注册 `CuriosCapability.ITEM`，优先取 SPI 注册的 `ICurioItem`，否则取 item 自身 `instanceof ICurioItem`。
- 客户端入口独立：`client/CuriosClientMod.java:39`（`@Mod(value=..., dist=Dist.CLIENT)`），注册按键、`MenuScreen`（`CuriosScreen`）、给**所有** `LivingEntityRenderer` 与 `AvatarRenderer` 添加 `CuriosLayer`、注册 render state modifier。
- 测试模组 `curiostest` 与主模组并列（`build.gradle:76-85` `mods { curios {...} curiostest {...} }`），是官方"外部 mod 接入示例"，位于 `src/test/java/top/theillusivec4/curiostest/`。

## 4. 核心系统

### 4.1 槽位系统（数据驱动 + 代码注册双轨）
- 职责：定义"有哪些槽位类型、每个实体有哪些槽位、槽位大小/排序/图标/掉落规则"。
- 核心类：`common/data/CuriosSlotResources.java`（`SimpleJsonResourceReloadListener<JsonElement>`，`ID = curios:curios_slots`，目录 `curios`，`:69-118`）、`common/slot/SlotType.java`（Builder，`:107-204`）、`api/CuriosSlotTypes.java`、`api/type/ISlotType.java`。
- 设计点：
  1. **三阶段合并**（`CuriosSlotResources.java:168-291`）：先解析 `data/<ns>/curios/slots/*.json`，再合并**配置文件里的槽位**（`fromConfig`，`:354-408`，把 `config` 里的 slot 视为注册命名空间 `"config"`），最后解析 `curios/entities/*.json`（可 `replace` 覆盖、可内联创建槽位 `create=true`）。全部用 `ISlotData.Entry.CODEC` / `IEntitiesData.Entry.CODEC` 解码，失败用 `ifSuccess` 静默跳过。
  2. **校验器谓词表**（`impl/CuriosSlots.java:118-128`）：内置 `curios:all`、`curios:none`、`curios:tag`（= 物品在 `curios:<slotId>` 物品标签里，或 `curios:curio`）；外部 mod 用 `CuriosSlotTypes.registerPredicate(Identifier, BiPredicate<SlotContext,ItemStack>)` 注册自定义校验器，再在 json 的 `validators: ["ns:key"]` 引用。`ISlotType.isItemValid` 默认实现就是 `testPredicates(...)`（`ISlotType.java:197-199`）。
  3. 内置 11 个预设槽位（`Preset`，`CuriosSlotTypes.java:83-132`：back/belt/body/bracelet/charm/curio/feet/hands/head/necklace/ring），各对应 `data/curios/curios/slots/<id>.json` 与同名的 `curios:<id>` 物品标签（`CuriosTags.java:36-134`）。
  4. 排序由 `ISlotType.compareTo` 用 `order` 字段决定（默认 0，同名回退 id 字典序，`ISlotType.java:234-238`）。

### 4.2 能力 / 附件体系（数据存储与对外访问分离）
- 核心类：`common/capability/CurioInventory.java`（`ValueIOSerializable`，挂在 `curios:inventory` attachment 上）、`common/capability/CurioInventoryCapability.java`（`ICuriosItemHandler` 实现，711 行）、`common/capability/CombinedCuriosResourceHandler.java`、`api/CuriosCapability.java`。
- 设计点：
  1. **持久化用 Attachment，访问用 Capability**：真正的数据是 `AttachmentType<CurioInventory>`（`copyOnDeath`），`registerEntity` 里返回的 `new CurioInventoryCapability(livingEntity)` 只是无状态视图；`CurioInventory` 持 `Map<String,ICurioStacksHandler> curios`（`CurioInventory.java:57`）。
  2. **面向外部 mod 的双通道**：`CuriosCapability.ITEM_HANDLER` 直接暴露 NeoForge 新版 `ResourceHandler<ItemResource>`（`CuriosCapability.java:48-49`，注释明确写"external mods 可以不依赖 Curios 类访问"，旧 `IItemHandler` 用 `IItemHandler.of(...)` 包装）；`INVENTORY` 暴露 Curios 自己的 `ICuriosItemHandler`。物品侧用 `ItemCapability<ICurio, Void>`。
  3. **查询接口带缓存**：`CurioInventoryCapability.findFirstCurio/findCurios` 支持 `cacheKey` 重载（`:147-223`），底层是 `Guava Cache`（100 条、1 秒过期，`CurioInventory.java:61-64`），避免每 tick 全量扫描。
  4. 物品能力可被**外部 SPI 覆盖**：`impl/CuriosExtensions.java:18-41` 的 `REGISTERED_ITEMS`（`Item→ICurioItem`）优先于物品自身实现的接口。

### 4.3 动态槽位数量与属性修饰（本版本的重点重构）
- 核心类：`common/inventory/CurioStacksHandler.java`、`CurioInventory.loadInventoryConfiguration()`（`:110-210`）、`api/CurioAttributeModifiers.java`、`api/event/CurioAttributeModifierEvent.java`。
- 设计点：
  1. **数据包重载时保留玩家物品**：槽位尺寸变化时对每个 slot 生成 `SIZE_SHIFT`（`curios:size_shift`）瞬态 `AttributeModifier` 记录差值（`CurioInventory.java:108,125-129`），旧槽位的物品逐个搬移，装不下的进入 `invalidStacks` 待掉落（`:132-164`）。
  2. 槽位修饰符分**瞬态 / 永久**两套：`addTransientSlotModifier`、`addPermanentSlotModifier`（`CurioInventoryCapability.java:549-625`），`clearCachedSlotModifiers` 供重算时清理缓存；槽位属性本身由 `api/SlotAttribute.getOrCreate(id)` **惰性创建并缓存在静态 Map**（`api/SlotAttribute.java:45-52`），不走 DeferredRegister。
  3. 物品属性改用 **DataComponent** `curios:attribute_modifiers`（`api/CuriosDataComponents.java:18`，`CurioAttributeModifiers.CODEC/STREAM_CODEC`）替代旧 NBT；外部通过 `CurioAttributeModifierEvent`（`api/event/CurioAttributeModifierEvent.java:62`，含 `addModifier/removeModifier/replaceModifier/removeIf/clearModifiers/build`）在运行时增删，避免污染物品数据。
  4. `CurioAttributeModifiers` 支持"按槽位归属"的修饰符（`addSlotModifier(...slot)`），因为同一个 curio 在不同槽位可给不同加成。

### 4.4 事件 API（`api/event`，7 个）
`CurioAttributeModifierEvent`、`CurioChangeEvent`（分 `Item`/`State` 两种子类型，`common/CuriosCommonEvents.java:523-533`）、`CurioCanEquipEvent`、`CurioCanUnequipEvent`、`CurioDropsEvent`、`DropRulesEvent`、`SlotModifiersUpdatedEvent`。使用范式见 `common/CuriosCommonEvents.java:264-306`：先 post `DropRulesEvent` 收集 `Pair<Predicate<ItemStack>,DropRule>` 覆盖，再 post `CurioDropsEvent`（可取消）决定掉落。

### 4.5 客户端渲染（把渲染逻辑做成可注册接口）
- `client/CuriosLayer.java`：作为 `RenderLayer` 挂到所有活体渲染器与玩家皮肤渲染器（`client/CuriosClientMod.java:64-87`）。
- `api/client/ICurioRenderer.java`：注册入口 `ICurioRenderer.register(Item, Supplier<ICurioRenderer>)`（`:72`），提供 `HumanoidRender`（`:346`）与 `ModelRender`（`:209`）两套 `default` 实现，降低外部 mod 的样板代码；加载时机是 `EntityRenderersEvent.AddLayers`（内部注释 `:63-70`）。旧类 `CuriosRendererRegistry` 已标 `@Deprecated(forRemoval)`（`:33`）。
- 渲染状态用 **ContextKey** 预计算（`CuriosClientMod.java:89-94`：`custom_render`/`armor_render`/`handheld_render`），在 `RegisterRenderStateModifiersEvent` 里把"该渲染哪些槽位"塞进 render state，避免每帧查询能力。

### 4.6 服务定位（SPI，跨"API 与实现"解耦）
`api/internal/CuriosServices.java:34-45` 用 `ServiceLoader` 加载 5 个服务：`CODECS/SLOTS/REGISTRY/EXTENSIONS/NETWORK`（客户端另有 `CuriosClientServices.EXTENSIONS`，`api/internal/CuriosClientServices.java:9`）。对应 `src/main/resources/META-INF/services/top.theillusivec4.curios.api.internal.services.*` 分别指向 `impl.CuriosCodecs/CuriosSlots/CuriosRegistry/CuriosExtensions/CuriosNetwork`（已用 `git show` 核对内容）。这样 `api/type/ISlotType.java:209-215` 之类接口里的静态 `CODEC` 字段可以直接委托给实现，且 api 包不 `import` impl 包。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`common/network/NetworkHandler.java:45-81`，注册器版本 `"1.0"`（`CuriosCommonMod.java:76`）。客户端→服务端 6 个（`CPacketOpenCurios/OpenVanilla/Page/Destroy/ToggleRender/ToggleCosmetics`），服务端→客户端 10 个（`SPacketSyncCurios`、`SPacketSyncStack`、`SPacketSyncModifiers`、`SPacketSyncData`、`SPacketSyncRender`、`SPacketSyncActiveState`、`SPacketBreak`、`SPacketPage`、`SPacketQuickMove`、`SPacketGrabbedItem`），全部 `record implements CustomPacketPayload` + `StreamCodec`。同步策略：`OnDatapackSyncEvent` 时下发全量（`SPacketSyncData` 携带整个 `CuriosSlotResources`，其 `STREAM_CODEC` 在 `CuriosSlotResources.java:78-101`）+ 逐玩家 `SPacketSyncCurios`；玩家开始追踪实体时补发（`CuriosCommonEvents.java:194-262`）；单槽位变化时仅发 `SPacketSyncStack`，并允许物品自带同步数据（`canSync` / `writeSyncData` → `CompoundTag`，`CuriosCommonEvents.java:656-672`）。
- **数据驱动**：`data/<ns>/curios/slots/*.json`（字段 `order/size/use_native_gui/add_cosmetic/render_toggle/drop_rule/icon/validators/entities/operation/replace/conditions`，序列化器 `impl/CuriosCodecs.java:42-...`、`SlotData.java:43-59`）与 `curios/entities/*.json`（`entities` 支持标签或具体实体、`slots` 支持内联创建）。加载时机：`ServerAboutToStartEvent` 时 `populateData()`（`CuriosCommonEvents.java:188-191`），服务端 reload listener 依赖 `VanillaServerListeners.LAST`（`CuriosCommonMod.java:137-141`）。
- **配置**：`config/CuriosConfig.java`（COMMON `slots` 字符串列表 = 用配置文件声明槽位；SERVER `keepCurios`、`minimumColumns`、`maxSlotsPerPage`）与 `config/CuriosClientConfig.java`（`renderCurios`、GUI 按钮位置与角落）。注意 `CuriosSlotResources` 会**把 config 槽位与 datapack 槽位合并**（`:202-219`），这是 1.21+ 才有的设计。
- **datagen**：`api/CuriosDataProvider.java:52-75` 提供抽象基类（输出路径 `curios/slots`、`curios/entities`，自带 block/item tag provider 与 `tag(...)` 联动），外部 mod 继承后写 `createSlot("x").size(4).dropRule(...).addCondition(...)`、`createEntities(...).addPlayer().addAllPresetSlots()`；示例见 `src/test/java/top/theillusivec4/curiostest/data/CuriosTestProvider.java:15-48`（跑在 `--mod curiostest` 的 clientData run，`build.gradle:62-65`）。
- **其他注册内容**：命令 `/curios list|set|add|remove|clear|drop|reset|replace`（`server/command/CuriosCommand.java:57-160`）、自定义参数类型 `CurioArgumentType`（带槽位 id 补全，`:53-58`）、实体选择器选项（`CuriosSelectorOptions`、mixin `MixinEntitySelectorOptions`）、进度触发器 `curios:equip_curio`（`common/util/EquipCurioTrigger.java:50-99`，`api/CuriosTriggers` 为构建器，并被自己的 mixin `MixinCuriosTriggersEquip` 修正）、JEI 插件（`common/integration/jei/CuriosJeiPlugin`）、EMI 集成被注释掉（`common/integration/CuriosIntegrations.java:7-12`）。

## 6. Mixin

- 配置：`src/main/resources/curios.mixins.json`（`required: true`，`package: top.theillusivec4.curios.mixin.core`，`compatibilityLevel: JAVA_25`，11 个 mixin）。
- `mixin/CuriosCommonMixinHooks.java` 是 mixin 与业务逻辑的隔离层（`attachDataFixer`、`canNeutralizePiglins`、`canWalkOnPowderSnow`、`getFortuneLevel`、`getLootingLevel`、`isFreezeImmune`、`mergeCuriosInventory`、`containsStack/containsTag/contains`）。
- 代表性注入：
  - `MixinLivingEntity`：`@Inject(at=TAIL, method="canFreeze()Z", cancellable=true)` → 冻结免疫（穿戴相关饰品）。
  - `MixinInventory`：`@Mixin(value=Inventory.class, priority=4)`，对 `contains(ItemStack)`、`contains(TagKey)`、`contains(Predicate)`、`hasAnyMatching(Predicate)` 注入，让玩家背包统计包含饰品（`/clear`、进度等逻辑正确）。
  - `MixinNbtPredicate`：改 `getEntityTagToCompare`，使 `nbt=` 选择器能命中饰品数据。
  - `MixinPiglinAi`：`isWearingSafeArmor` RETURN 注入 → 饰品算作"安全护甲"（猪灵中立）。
  - `MixinPowderSnowBlock`：`canEntityWalkOnPowderSnow` RETURN 注入。
  - `MixinApplyBonusCount` / `MixinEnchantedCountIncreaseFunction`：`@ModifyVariable(method="run")` → 时运/抢夺等级叠加饰品加成。
  - `MixinEntitySelectorOptions`：用 lambda 正则匹配注入，注册 `curios` 选择器选项。
  - `MixinV1460`：改 DataFixer `registerTypes`，把饰品 NBT 并入实体数据迁移（配合 `attachDataFixer`）。
  - `AccessorEntity`：`@Accessor`（配合 `accesstransformer.cfg` 中大量 `public`/`public-f` 开放 `MouseHandler.mouseGrabbed`、`AbstractContainerScreen.clickedSlot/draggingItem/findSlot`、`AbstractContainerMenu.lastSlots/remoteSlots`、`InventoryMenu.SLOT_IDS` 等）。
- 注意：**没有任何面向其他 mod 的"开放 mixin"**，mixins.json 不 exports。

## 7. 值得学的 5 条具体做法

1. **api / impl / internal-services 三层，用 `ServiceLoader` 反向解耦**：`api/internal/CuriosServices.java:34` + `META-INF/services/*` + `impl/*` 三件套，使 API 包里的静态字段（如 `ISlotType.CODEC`）能委托实现而 api 不依赖实现。→ 适用：任何要做前置库的 mod，尤其是想同时支持多加载器时（每加载器一套 impl + 各自的 services 文件即可，`CuriosClientServices` 就是客户端侧的同构复制）。
2. **唯一数据源 + 无状态能力视图**：持久数据放 `AttachmentType`（`impl/CuriosRegistry.java:70-74`），对外的 `ICuriosItemHandler` 只是即时构造的包装（`CurioInventoryCapability`），避免能力对象里再存一份状态导致两端不一致。→ 适用：任何"实体/方块持有复杂数据"的系统。
3. **data pack 与 config 合并成同一张运行时表**：`CuriosSlotResources.populateData()` 把 `data/*/curios/slots` 与 config `slots` 合并（`CuriosSlotResources.java:168-219`），config 槽位视作命名空间 `config` 的槽位。→ 适用：想同时允许 datapack 作者和普通玩家自定义内容的系统（Create 附属的配方/产线配置也常用这一模式）。
4. **对"数据包重载改变容量"做平滑迁移**：容量变化用瞬态修饰符记录 `old-default` 差值（`CurioInventory.java:125-129`），物品能塞就塞、塞不下入 `invalidStacks` 再掉落；同时对每条查询提供带 `cacheKey` 的缓存重载（`CurioInventoryCapability.java:147-223`）。→ 适用：任何可被 datapack/属性动态改变尺寸的容器或槽位系统。
5. **渲染与逻辑都做成"注册式 + ContextKey 预计算"**：`ICurioRenderer.register(item, supplier)` + `HumanoidRender/ModelRender` 默认实现，以及 `RegisterRenderStateModifiersEvent` 里把结果写进 render state 的 `ContextKey`（`client/CuriosClientMod.java:89-120`）。→ 适用：给外部 mod 提供外观扩展点（尤其要兼容玩家/非人形实体渲染、且不想在渲染线程里做数据查询时）。

## 8. 公开 API 与外部 mod 接入方式（库/前置视角）

- **公开 API 包**：`top.theillusivec4.curios.api` 及其子包（构建时单独产出 `curios-neoforge-<ver>-api.jar`，只含 `api/**`，`build.gradle:104-109`）。`api/internal/**` 标了 `@ApiStatus.Internal`（`CuriosServices.java:31`），不属于公共契约。
- **Facade 类（推荐入口）**：`CuriosSlotTypes`（查/注册谓词）、`CuriosResources`（MOD_ID、`resource(path)`）、`CuriosCapability`、`CuriosTags`、`CuriosDataProvider`、`CuriosTriggers`、`CuriosTooltip`、`CuriosDataComponents`、`CurioAttributeModifiers`、`SlotContext`/`SlotResult`/`SlotAttribute`/`SlotPredicate`。**注意 `CuriosApi` 整体已标注 `@Deprecated(forRemoval = true)`**（`api/CuriosApi.java:54-61` 起，仅 `registerCurio`/`getCurio`/`getCuriosInventory`/`broadcastCurioBreakEvent` 少数方法留在其中），新代码应直接用上面的具体 Facade。
- **扩展点清单（外部 mod 的 6 种接入姿势）**：
  1. 让物品类 `implements ICurioItem`（`api/type/capability/ICurioItem.java`，30+ 个 `default` 方法，全部带 `ItemStack` 参数，是"无 NBT 时代的接口版"）；或给已有物品注册 `CuriosApi.registerCurio(item, ICurioItem)`（`CuriosApi.java:72`）。
  2. 在 `RegisterCapabilitiesEvent` 里 `evt.registerItem(CuriosCapability.ITEM, (stack, ctx) -> new ICurio(){...}, item)`，并对实体注册 `CuriosCapability.INVENTORY` / `ITEM_HANDLER`（示例：`src/test/java/top/theillusivec4/curiostest/CuriosTest.java:116-136`）。
  3. 数据包：`data/<ns>/curios/slots/<id>.json` 定义槽位类型、`curios/entities/<id>.json` 给实体发槽位；物品归属靠 `curios:<slotId>` 物品标签 + `validators:["curios:tag"]`（或自定义谓词）。用 `CuriosDataProvider` 生成更省事。
  4. 监听 `RegisterCuriosExtensionsEvent` 注册 `ICurioSlotExtension`（自定义空槽图标显示与提示，`RegisterCuriosExtensionsEvent.java:23`、`ICurioSlotExtension.java:42-63`；示例 `CuriosTest.java:98-105`）。
  5. 渲染：`ICurioRenderer.register(item, supplier)`（客户端 setup 期）。
  6. 自定义槽位校验：`CuriosSlotTypes.registerPredicate(id, BiPredicate<SlotContext,ItemStack>)`（示例 `CuriosTest.java:94-95`）。
- **给其他 mod 读数据的推荐路径**：`CuriosApi.getCuriosInventory(living)` → `ICuriosItemHandler`（`findFirstCurio/findCurios/findCurio`，带缓存重载）；不需要 Curios 依赖时可只用 `CuriosCapability.ITEM_HANDLER` 的 `ResourceHandler<ItemResource>`。
- **服务端/管理侧**：`/curios` 命令族与 `curios` 实体选择器选项、`equip_curio` 进度触发器、`CuriosCommonHooks.computeModifiedAttributes(stack, ...)`（`api/common/CuriosCommonHooks.java:21`）。
- **跨加载器现状**：本检出为 NeoForge 单加载器工程；但 api 包的 `internal/services` + `ServiceLoader` 结构、`api` 内 client/common 分离、独立 `apiJar` 发布，正是"同源多加载器"最省改动的组织方式——**多加载器分支的具体差异未确认**（本地无其他分支）。
