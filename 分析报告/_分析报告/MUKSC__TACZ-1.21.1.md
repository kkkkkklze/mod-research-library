# MUKSC/TACZ-1.21.1 源码分析报告

## 1. 基本信息
- Mod 名 Timeless & Classics Guns: Zero / `mod_id=tacz` / 版本 `1.1.8-hotfix-r6` / 作者 Serene Wave Studio | Timeless Squad / 仓库 `MUKSC/TaCZ-1.21.1`（TACZ 的 1.21.1 NeoForge 分支）
- 目标：MC 1.21.1 + **NeoForge**（`neoForge { version = libs.versions.neoforge }` + parchment，`archives_base_name=tacz-neoforge-1.21.1`）；Java 17
- 构建：`net.neoforged.moddev` + `mod-publish-plugin` + `dotenv`（Gradle KTS，版本走 `gradle/libs.versions.toml`）；许可证 `GPL3 / CC BY-NC-ND 4.0`
- 关键依赖（libs.versions.toml / libs 目录）：`simplebedrockmodel` 2.2.1（Bedrock 模型加载，附带 sources jar）、`com.maydaymemory:mae`、`luaj`（FiguraMC fork，Lua 脚本）、`commons-math3`、`bcel`、cloth-config、`player-animation-lib`、JEI、KubeJS/Rhino；兼容：Sodium/Iris/AcceleratedRendering/CarryOn/ShoulderSurfing/Controllable/Framework；`libs/` 内还放了 oculus 的 1.20.1 jar（本地依赖）

## 2. 源码规模与包结构
- 641 个 `.java`，24171 行（`find src -name '*.java' -exec wc -l {} +`）
- 主要包（`com.tacz.guns.*`）：`client/resource/pojo` 53、`api/client/animation` 46（含 gltf 解码）、`resource/pojo/data` 30、`network/message` 23、`util` 18、`resource/modifier/custom` 17、`init` 17、`client/event` 16、`entity/shooter` 13、`client/gui/components` 13、`event` 12、`api/event/common` 12、`client/input` 11、`resource/manager` 9、`mixin/client` 10、`command/sub` 9、`compat/kubejs` 6+
- 最大文件：`item/ModernKineticGunScriptAPI.java`(899)、`client/resource/GunDisplayInstance.java`(768)、`entity/EntityKineticBullet.java`(761)、`client/gui/GunSmithTableScreen.java`(711)、`api/client/animation/gltf/GltfConstants.java`(687)、`client/model/BedrockAttachmentModel.java`(663)、`item/ModernKineticGunItem.java`(593)、`api/item/gun/AbstractGunItem.java`(491)、`api/item/nbt/GunItemDataAccessor.java`(464)

## 3. 入口与注册
`src/main/java/com/tacz/guns/GunMod.java:21` `@Mod(GunMod.MOD_ID)`，构造注入 `(IEventBus bus, ModContainer container)`：
```java
container.registerConfig(ModConfig.Type.STARTUP, PreLoadConfig.spec, "tacz-pre.toml");
container.registerConfig(ModConfig.Type.COMMON, CommonConfig.spec); // 另有 SERVER / CLIENT
Dist side = FMLLoader.getDist();
GunPackLoader.INSTANCE.packType = side.isClient() ? PackType.CLIENT_RESOURCES : PackType.SERVER_DATA;
CapabilityRegistry.ATTACHMENT_TYPES.register(bus); ModItems.ITEMS.register(bus); ...
```
`init/` 包 17 个类全部是 `DeferredRegister` 容器（`ModItems/ModBlocks/ModEntities/ModSounds/ModParticles/ModAttributes/ModRecipe/ModLootModifiers/ModPainting/ModCreativeTabs/ModIngredientTypes/ModContainer/CapabilityRegistry` 等）。另 `registerDefaultExtraGunPack()` 把 jar 内 `/assets/tacz/custom/tacz_default_gun` 导出为默认枪包。

## 4. 核心系统
1. **数据驱动的"枪包"加载**（`resource/GunPackLoader.java`）：`enum GunPackLoader implements RepositorySource`（单例 + `loadPacks(Consumer<Pack>)`），扫描 `gamedir/tacz` 目录并作为资源包/数据包注入游戏，随 `Dist` 切换 CLIENT_RESOURCES/SERVER_DATA；配套 `PackMeta/PackConvertor/VersionChecker/DelegatingPackResources/CommonAssetsManager` 与 `resource/manager/{JsonDataManager,LazyJsonDataManager,CommonDataManager,INetworkCacheReloadListener}`。枪械/配件/弹药 JSON 落到 `resource/pojo`（含 `pojo/data` 30 个文件）。
2. **集中式网络注册**（`network/NetworkHandler.java:28` `@EventBusSubscriber(bus=MOD)`）：一个 `RegisterPayloadHandlersEvent` 里注册约 30 个 payload（`playToServer/playToClient`，每个自带 `TYPE/STREAM_CODEC/handle`），另用 `registrar(VERSION).executesOn(HandlerThread.NETWORK)` 做握手：`configurationToServer(Acknowledge)`、`configurationToClient(ServerMessageSyncedEntityDataMapping)` + `ICustomConfigurationTask`（:69-117）在配置阶段下发同步字段映射表；发送侧封装 `PacketDistributor`（:79-101）。
3. **实体同步框架**（`entity/sync/core/`，`SyncedEntityData/SyncedClassKey/SyncedDataKey/DataHolder/Serializers`，头部注明源自 MrCrayfish Framework，LGPL）：内部 int id 映射（`internalIds`/`syncedIdToKey`）+ 按实体类分组 + 脏实体列表 `dirtyEntities`，配合 1 中的配置阶段映射表实现"只在需要时同步字段"。
4. **动画系统**（`api/client/animation` 46 文件 + `client/animation/statemachine/GunAnimationStateContext.java`(458) + `client/model/BedrockGunModel`(507)/`BedrockAttachmentModel`(663)）：自实现 glTF 解码（`gltf/AccessorDatas`、`AnimationStructure`、`Buffers`）→ 采样成轨道 → 状态机驱动 Bedrock 模型；脚本层有 Lua API（`item/ModernKineticGunScriptAPI.java` 899 行 + `api/vmlib/LuaLibrary`）+ KubeJS 集成（`compat/kubejs`）。
5. **配件属性修饰器系统**（`resource/modifier/custom` 17 个 + `api/modifier/{IAttachmentModifier,ParameterizedCache,CacheValue,JsonProperty}`）：`AttachmentPropertyManager.registerModifier()` 在构造中注册，枪械最终属性由"基础值 + 修饰器链"计算，且支持运行时改值（`api/ValueModifiableAtRuntime`）。
6. **弹道实体**（`entity/EntityKineticBullet.java` 761 行 + `entity/shooter` 13 个）：自定义子弹实体与射手状态（`ReloadState/ShootResult/KnockBackModifier`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：23+ 个 `network/message/*`（`ClientMessagePlayerShoot/ReloadGun/Aim/Zoom/...`、`ServerMessageGunFire/GunReload/SyncGunPack/UpdateEntityData/...`）+ `message/event` 8 个（广播事件）+ `message/handshake` 2 个；接口 `IMessage`、`LoginIndexHolder`。
- 数据驱动：见系统 1（枪包 = 资源包 + data JSON）。
- 配置：4 个 NeoForge `ModConfig`（STARTUP `tacz-pre.toml`、COMMON、SERVER、CLIENT）。
- datagen：有 `data` run config（`data()`），但无 `src/generated` 在仓库中。

## 6. Mixin
- `src/main/resources/tacz.mixins.json`：`common` 5 个（`BindingContextMixin`、`LivingEntityMixin`、`ServerGamePacketListenerImplMixin`、`ServerPlayerMixin`、`ServerPlayNetHandlerMixin`）+ `client` 10 个（`GameRendererMixin`、`HumanoidModelMixin`、`ItemInHandLayerMixin`、`ItemInHandRendererMixin`、`LocalPlayerMixin`、`MouseHandlerMixin`、`PlayerModelMixin`、`SoundManagerPreparationsMixin`、`AbstractButtonMixin`、`LanguageMixin`）。
- 另一独立配置 `tacz.compat.acceleratedrendering.mixins.json`（**按兼容 mod 拆分配置**），两个都在 `neoforge.mods.toml` 的 `[[mixins]] config=` 里声明。
- 代表 hook：`LivingEntityMixin`（`tick` RETURN）、`ServerPlayerMixin`（`restoreFrom` RETURN）、`ServerPlayNetHandlerMixin`（`handlePlayerAction` 内 `stopUsingItem()` 调用点）。

## 7. 值得学的 5 条做法
1. **把 mod 目录当成"内容包仓库"**：`GunPackLoader implements RepositorySource` 扫 `gamedir/tacz`，玩家可自行放置枪包（`resource/GunPackLoader.java`）——任何"内容由玩家提供"的 mod 都适用。
2. **网络全部集中在一个 `RegisterPayloadHandlersEvent` 里注册**（`network/NetworkHandler.java:33-72`），并单独用 `HandlerThread.NETWORK` + 配置阶段包下发映射表——实体字段同步类系统的标准解法。
3. **同步字段用 int id 映射 + 脏列表**（`entity/sync/core/SyncedEntityData.java`）——比每 tick 广播 NBT 省带宽。
4. **兼容 mixin 单独一个 config 文件**（`tacz.compat.acceleratedrendering.mixins.json`），崩溃/冲突时可单独关掉某套兼容 hook。
5. **公开 API 与实现分层**（`api/item/IGun|IAmmo|IAttachment`、`api/entity/IGunOperator`、`api/event/common/*` 11 个事件 + `TimelessAPI`）——第三方 mod 只依赖 `api` 包即可读写枪械数据。

## 8. 公开 API 与接入方式
- API 根：`src/main/java/com/tacz/guns/api/`
  - 查询门面：`api/TimelessAPI.java`（`getCommonGunIndex/getAllCommonGunIndex/getGunDisplay/getClientGunIndex/getCommonAttachmentIndex`、`registerThirdPersonAnimation(ResourceLocation 名称, IThirdPersonAnimation)`）
  - 物品接口：`api/item/{IGun,IAmmo,IAmmoBox,IAttachment,IAnimationItem,IBlock,GunTabType}`；`api/item/gun/AbstractGunItem`、`api/item/nbt/GunItemDataAccessor`、`api/item/builder/*`
  - 实体接口：`api/entity/{IGunOperator,ITargetEntity,ReloadState,ShootResult,KnockBackModifier}`
  - 事件：`api/event/common/{GunFireEvent,GunReloadEvent,GunShootEvent,GunDrawEvent,EntityHurtByGunEvent,...}` + `KubeJSGunEventPoster`（KubeJS 可监听）
  - 附件修饰：`api/modifier/{IAttachmentModifier,CacheValue,ParameterizedCache,JsonProperty}`
  - 资源注入：`api/resource/{ResourceManager,JsonResourceLoader}`、`api/DefaultAssets`
  - 脚本：`api/vmlib/LuaLibrary`、`api/util/{LuaEntityAccessor,LuaNbtAccessor}`
- 接入方式：编译期依赖 TACZ，通过 `IGun`（`getGunId/getGunDisplayId` 等）读写物品、用 `api/item/builder` 构造自己的枪械物品、注册 `IAttachmentModifier` 或监听 `api/event`；KubeJS 走 `compat/kubejs` + `kubejs.plugins.txt`（插件入口声明文件）。
