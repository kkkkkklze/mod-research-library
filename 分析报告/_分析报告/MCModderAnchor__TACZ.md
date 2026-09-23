# Timeless and Classics Zero (TaCZ) 源码分析报告

> 分析对象：`_参考仓库/TACZ`（GitHub: MCModderAnchor/TACZ，分支 `1.20.1`）。
> 说明：本地 clone 原先为空仓库（`.git` 无 commit），本报告基于重新拉取的 `1.20.1` 分支源码（版本号 `1.1.8-hotfix`）分析，源码已恢复至 `_参考仓库/TACZ`。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 | Timeless & Classics Guns: Zero（永恒枪械工坊：零） |
| mod_id | `tacz` |
| 作者 | Serene Wave Studio \| Timeless Squad（`src/main/resources/META-INF/mods.toml`） |
| MC / 加载器 | 1.20.1 / Forge `1.20.1-47.3.19`；mods.toml 范围 `minecraft [1.20,1.20.2)`、`forge [46,)` |
| Gradle | ForgeGradle `5.1.+` + `org.parchmentmc.librarian` + MixinGradle `0.7-SNAPSHOT`；parchment `2023.08.20-1.20.1`；Java 17（`build.gradle:33`） |
| 版本/坐标 | `version = 1.1.8-hotfix`、`group = com.tacz`、`archivesBaseName = tacz-1.20.1` |
| 许可证 | `GPL3 / CC BY-NC-ND 4.0`（mods.toml license 字段；LICENSE 为 GPLv3 全文） |
| jarJar 内嵌依赖 | `com.github.mcmodderanchor:simplebedrockmodel:2.2.2-forge+mc1.20.1`（自家基岩版模型库）、`commons-math3:3.6.1`、`luaj-core/jse:3.0.8-figura`、`bcel:6.6.1`、`mixinextras-forge:0.3.6` |
| 编译期依赖 | `com.maydaymemory:mae:1.1.2`（Mayday Animation Engine）、JEI、cloth-config、`player-animation-lib-forge:1.0.2-rc1+1.20`、kubejs/rhino/architectury、controllable、embeddium/oculus（`libs/` 双版本 jar）、accelerated-rendering、carry-on、shoulder-surfing |
| 对外发布 | readme 带 jitpack 徽章（`com.github.MCModderAnchor:TACZ`），即它本身被当 API 依赖 |

注：仓库内 `grep -i gunsmith` 无任何结果，**未确认**存在名为 GunsmithLib 的模块；对第三方开放的是 `com.tacz.guns.api` 包（见第 8 节）。存在第三方非官方 NeoForge 1.21.1 移植（`_bulk/MUKSC__TACZ-1.21.1`，NeoForge moddev + Java 21 + `jarJar` 内嵌 simplebedrockmodel、删除 KubeJS 集成），不属于本仓库。

## 2. 源码规模与包结构

实测（`find src -name '*.java' | wc -l` = **652**，`xargs cat | wc -l` = **58926 行**）。资源：`assets` 3463 文件（textures 866 / sounds 1353 / models 293 / lang 42），`data` 35 文件 —— 说明它是"重资源、代码中等"的结构。

按二级包文件数：`client` 198、`api` 113、`resource` 88、`compat` 57、`network` 36、`util` 25、`entity` 25、`mixin` 17、`init` 16、`config` 16、`event` 14、`block` 11、`command` 10、`item` 9、`crafting` 6、`inventory` 5、`particles` 2、`sound`/`loot`/`debug` 各 1，主类 `com/tacz/guns/GunMod.java`。

最大文件：`item/ModernKineticGunScriptAPI.java` 899、`entity/EntityKineticBullet.java` 767、`client/resource/GunDisplayInstance.java` 766、`client/gui/GunSmithTableScreen.java` 708、`api/client/animation/gltf/GltfConstants.java` 687、`client/model/BedrockAttachmentModel.java` 662、`item/ModernKineticGunItem.java` 589、`api/client/animation/gltf/accessor/AccessorDatas.java` 556、`client/model/BedrockGunModel.java` 508。

另有 `src/main/reserve repository/`（含空格的目录，默认不参与编译）存放未启用枪械模型：`mcx`、`neopup`、`scar_mk20_ssr`、`win1866`、`hcar_model`。

## 3. 入口与注册

主类 `com/tacz/guns/GunMod.java`（`@Mod(GunMod.MOD_ID)`），构造函数做 5 件事（`GunMod.java:32-60`）：

```java
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, CommonConfig.init()); // + SERVER / CLIENT
GunPackLoader.INSTANCE.packType = FMLLoader.getDist().isClient() ? PackType.CLIENT_RESOURCES : PackType.SERVER_DATA;
ModBlocks.BLOCKS.register(bus); ModItems.ITEMS.register(bus); ModEntities.ENTITY_TYPES.register(bus);
ModRecipe.RECIPE_SERIALIZERS.register(bus); ModSounds.SOUNDS.register(bus); /* 共 13 个 DeferredRegister */
registerDefaultExtraGunPack();          // ResourceManager.registerExportResource(...) 导出内置枪包
AttachmentPropertyManager.registerModifier();
```

- 注册框架：全量 Forge `DeferredRegister`+`RegistryObject`（`init/ModItems.java:17`、`init/ModBlocks.java` 等 16 个 `init` 类），无 Registrate。
- MOD 总线侧 `init/CommonRegistry.java`：`FMLCommonSetupEvent` → `NetworkHandler::init` + `ModSyncedEntityData::init`；`AddPackFindersEvent` → `event.addRepositorySource(GunPackLoader.INSTANCE)`。
- 普通总线侧 `resource/CommonAssetsManager.java`（`@Mod.EventBusSubscriber`）：`AddReloadListenerEvent` 重建所有数据管理器、`OnDatapackSyncEvent` 下发枪包数据、`ServerStoppedEvent` 清缓存。
- 客户端 `client/init/ClientSetupEvent.java`（键位、tooltip、overlay、`ClientAssetsManager.INSTANCE.reloadAndRegister`）、`client/init/ModEntitiesRender.java`（子弹/标靶/枪械合成台渲染器）。

## 4. 核心系统

**(1) 枪包（Gun Pack）加载 —— 把外部文件夹/zip 变成真正的资源包**
`resource/GunPackLoader.java`（enum 单例，实现 `RepositorySource`）。扫描 `.minecraft/tacz`（`FMLPaths.GAMEDIR.resolve("tacz")`），每个子目录或 `.zip` 需含 `gunpack.meta.json`（`PackMeta`，支持 `dependencies` 版本区间校验 `modVersionAllMatch`，`GunPackLoader.java:175-269`）；用 `SecureJar.from(path)` + 匿名 `PathPackResources` 包装（:96-118），再经 `DelegatingPackResources` 合成一个名为 `tacz_resources`、位置 `BOTTOM`、来源 `BUILT_IN` 的 pack（:121-134）。`PreLoadConfig.load()` 在此时提前读 `tacz-pre.toml`；首启把内置 `tacz_default_gun` 解压到该目录（除非 `override=true`）。

**(2) 数据驱动资源与索引**
目录约定即 API：`data/guns`、`data/blocks`、`index/guns|ammo|attachments|blocks`、`display/guns|ammo|attachments|blocks`、`geo_models`、`animations`（`.animation.json` 或 `.gltf`）、`scripts`（`.lua`）、`textures`（`resource/CommonAssetsManager.java:88-100`、`client/resource/ClientAssetsManager.java:95-106`）。解析统一 `JsonDataManager extends SimplePreparableReloadListener`（`prepare` 扫描 → `apply` 解析），重资产用 `LazyJsonDataManager` 懒加载。Gson 上挂 12 个自定义 TypeAdapter（`CommonAssetsManager.GSON:55-69`）。索引对象由 POJO 二次构建：`ClientIndexManager.reload()` 把 common index 转成 `ClientGunIndex/ClientAttachmentIndex/...`，再 `warmUpInventoryModels()` 预热主手/副手/快捷栏/背包模型（`ClientIndexManager.java:48-66,152-221`）。

**(3) 网络同步**
`network/NetworkHandler.java`：两条 `SimpleChannel`（`tacz:handshake`、`tacz:network`，版本串 `"1.0.5"`，握手用 `LoginIndexHolder`+`registerHandshakeMessage`）。消息按方向分两类：C→S 玩家意图（shoot/reload/cancelReload/fireSelect/aim/crawl/draw/bolt/melee/zoom/refit/unloadAttachment/laserColor/craft），S→C 事件广播（`ServerMessageGunFire|GunShoot|GunReload|GunDraw|GunHurt|GunKill|GunMelee|GunFireSelect`），与 `api/event/common/GunFireEvent` 等一一对应。数据包同步走 `ServerMessageSyncGunPack`：服务端把每个 reload listener 的 `networkCache`（`Map<DataType, Map<ResourceLocation, String>>`，值是**原始 JSON 文本**）整体下发，客户端 `CommonNetworkCache.fromNetwork()` 用同一套 Gson 反序列化，并"先 data 后 index"延后处理（`resource/network/CommonNetworkCache.java:140-158`）。实体状态另有 `entity/sync/SyncedEntityData`：`ModSyncedEntityData` 声明 9 个 `SyncedDataKey`（`shoot_cool_down`、`reload_state`、`aiming_progress`、`is_aiming`…，`SyncMode.ALL`/`SELF_ONLY`），握手期用 `ServerMessageSyncedEntityDataMapping` 同步 id→字段映射。

**(4) 第一人称渲染与模型**
`client/renderer/item/GunItemRendererWrapper.java`（继承 `AnimateGeoItemRenderer`）：`renderFirstPerson` 中**先跑状态机** `animationStateMachine.update()`（把动画写进模型），再做"逆向 bob"（`Mth.tanh` 抑制手部摇晃写进 `rootNode.additionalQuaternion`）、平移 `(0,1.5,0)`、Z 轴 180° 翻转基岩模型、`FirstPersonRenderGunEvent.applyFirstPersonGunTransform`，最后按 `entityCutout/entityTranslucent` 渲染并 `cacheMuzzlePosition` 记录枪口屏幕坐标（:163-252）。`client/model/BedrockGunModel.java` 用**定位组命名约定**驱动一切显示逻辑：`GunModelConstant.java` 定义 `bullet_in_barrel`/`bullet_in_mag`/`bullet_chain`/`mag_extended_1..3`/`mag_standard`/`mount`/`sight`/`sight_folded`/`carry`/`handguard_default|tactical`/`muzzle_flash`/`shell`(+`shell_N`)/`lefthand_pos`/`righthand_pos`/`magazine`/`additional_magazine`/`attachment_adapter`/`iron_view`/`idle_view`/`refit_view`/`thirdperson_hand`/`fixed`/`ground`/`root`，以及后缀约定 `<配件名>_pos`、`<配件名>_default`、`refit_<配件名>_view`；每个组通过 `setFunctionalRenderer(node, part -> IFunctionalRenderer)` 挂行为（构造函数 `BedrockGunModel.java:70-120`）。瞄具用模板缓冲实现"镜内不渲染枪体"：组合镜 `stencilFunc(GL_GREATER,127)`，长筒镜 `GL_EQUAL,0`（:301-319）；开加速渲染时改走 `ARCompat.setRenderLayer(-943+3)` 并在层前后注入 stencil 任务（:322-389）。LOD 依 `RenderDistance.inRenderHighPolyModelDistance(poseStack)` 切换。

**(5) 动画状态机 + Lua 脚本**
`api/client/animation/statemachine/AnimationStateMachine.java`：多当前状态列表、`trigger(condition)`→`state.transition()` 替换状态并调 `exitAction/entryAction`、`setExitingTime()` 保留收枪动画时长；`LuaAnimationStateMachine` 让 Lua 提供 `initialize/exit` 回调，`LuaStateMachineFactory` 负责工厂化。动画来源双轨：基岩版 `.animation.json`（`BedrockAnimationFile`）与 glTF（`GltfManager`，`api/client/animation/gltf/*` 自解析 accessor/buffer/node），插值器 `interpolator/{Linear,Step,SLerp,Spline,CustomInterpolator}`。逻辑脚本 `resource/manager/ScriptManager.java` 用 luaj 加载 `scripts/*.lua`，`secureStandardGlobals()` 主动剔除 Coroutine/Io/Os/Luajava 库（:107-122），模块名 `namespace_path` 并注册进 `package.preload`；枪械行为脚本通过 `item/ModernKineticGunScriptAPI.java`（`shootOnce`/`adjustReloadTime`/`adjustShootInterval`/`consumeAmmoFromPlayer`/`cacheScriptData` 等 40+ 方法）操作。

**(6) 附件属性 modifier 体系**
`resource/modifier/AttachmentPropertyManager.java`：注册 16 个 `IAttachmentModifier`（Ads/AmmoSpeed/ArmorIgnore/Damage/EffectiveRange/Explosion/HeadShot/Ignite/Inaccuracy/Knockback/Pierce/Recoil/Rpm/Silence/Weight/ExtraMovement，:30-47）。数值计算是可配置的三段式 —— `eval()` 对同一属性的所有 modifier 累加 `addend`、累乘 `percent` 与 `multiplier`，再对每个 modifier 的 `function` 字段做 Lua 表达式求值（`x`=当前值、`r`=默认值、结果取 `y`，:77-125），因此数据包作者能用公式而非改代码调整手感；结果写入 `AttachmentCacheProperty` 与 `ShooterDataHolder`，并经 `AttachmentPropertyEvent` 同时广播给 Forge/KubeJS/脚本。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：见 4.(3)。分发封装 `sendToClientPlayer/sendToTrackingEntity(AndSelf)/sendToAllPlayers/sendToDimension`（`NetworkHandler.java:144-166`）；消息 id 由 `AtomicInteger ID_COUNT` 自增分配，接口仅 `encode/decode/handle`（`network/IMessage.java`）。MixinExtras 的 `@WrapOperation` 用于需要嵌套注入的位置（build.gradle 注释说明 `@Redirect` 不能嵌套）。
- **数据驱动**：POJO 用 Gson + `@SerializedName`。示例：`GunIndexPOJO`（`name/tooltip/display/data/type/item_type/sort`）、`GunDisplay`（`model/texture/iron_zoom/zoom_model_fov/lod/hud/hud_empty/slot/ammo_count_style/damage_style/third_person_animation/animation/state_machine/state_machine_param/use_default_animation/default_animation/player_animator_3rd/sounds`）、`AttachmentData`（`modifier/weight/extended_mag_level/melee`）、`GunData`（`resource/pojo/data/gun/*` 下 20+ 子 POJO：`BulletData/Bolt/ReloadData/Recoil/HeatData/ExplosionData/Ignite/MoveSpeed/MeleeData…`）。内置样例 `assets/tacz/custom/tacz_default_gun/{gunpack.meta.json, assets/tacz/gunpack_info.json}`。
- **配置**：`config/{CommonConfig,ServerConfig,ClientConfig}.java`（Forge 三类配置）+ `config/PreLoadConfig.java`（`tacz-pre.toml`，比 Forge 配置更早，用于 `override` 与 `DefaultPackDebug`）+ `config/sync/SyncConfig.java`；GUI 走 Cloth Config（`compat/cloth/**`，含自定义 widget `CrosshairDropdown`、`OpenGunPackDirEntry`）。
- **datagen**：**实际未使用**。build.gradle 有 `data` run（`--mod tacz --all --output src/generated/resources`）和 `srcDir 'src/generated/resources'`，但仓库中不存在 `src/generated`，`grep -rn "GatherDataEvent\|DataProvider"` 无结果。

## 6. Mixin

配置：`src/main/resources/tacz.mixins.json`（package `com.tacz.guns.mixin`、refmap `tacz.refmap.json`、`compatibilityLevel JAVA_17`、`injectors.defaultRequire 1`）与 `tacz.compat.acceleratedrendering.mixins.json`（带 `plugin: ARCompatMixinPlugin`，只含 `BedrockPartMixin`）；由 MixinGradle 注册两个 config。另有 `META-INF/accesstransformer.cfg` 放宽原版成员（如 `TextureManager.f_118468_`、`I18n.f_118934_`、`LivingEntity.f_20899_`）。

代表性 mixin 与 hook：

| 类 | 目标 / 注入点 |
|---|---|
| `client/ItemInHandRendererMixin` | `ItemInHandRenderer.renderHandsWithItems` HEAD 发 `BeforeRenderHandEvent`；`@Shadow mainHandItem/mainHandHeight` 并实现 `KeepingItemRenderer.keep/getCurrentItem`（切枪时保留旧物品渲染） |
| `client/ItemInHandLayerMixin` | `renderArmWithItem(...)` HEAD + TAIL（第一人称手臂/物品渲染拦截） |
| `client/PlayerModelMixin` / `client/HumanoidModelMixin` | `setupAnim(LivingEntity;FFFFF)` TAIL（第三人称持枪姿态） |
| `client/LocalPlayerMixin` | `@WrapOperation aiStep`、`@WrapOperation turnPlayer`（瞄准/爬行时限制移动） |
| `client/MouseHandlerMixin` | `turnPlayer` 相关 `@WrapOperation` + `@At INVOKE`（开镜灵敏度） |
| `client/GameRendererMixin` | `bobHurt` / `bobView` / `getFov`（镜头晃动与 FOV） |
| `client/SoundManagerPreparationsMixin` | `listResources`（枪包音效预加载） |
| `client/LanguageMixin` | `I18n.getOrDefault(String,String)`/`has(String)` HEAD（枪包内嵌语言） |
| `common/ServerPlayerMixin`、`common/LivingEntityMixin`、`common/ServerGamePacketListenerImplMixin`、`common/ServerPlayNetHandlerMixin` | 服务端玩家状态/`handlePlayerCommand` 等 |
| `client/StairBlockAccessor` | `@Accessor` |

## 7. 值得学的 5 条具体做法

1. **用模型中的"定位组命名"当硬点，代码只按名字挂行为**：`GunModelConstant.java` 定义全部约定名（含 `<配件名>_pos`/`refit_<配件名>_view` 这类后缀规则），`BedrockGunModel` 构造时批量 `setFunctionalRenderer`。适用于任何"资源包提供模型 + 代码控制显示/挂载点"的模组（载具配件、机械臂、Create 类装置）。
2. **用 `SecureJar` + `PathPackResources` + `DelegatingPackResources` 把外部目录/zip 注册成真实资源包**（`resource/GunPackLoader.java:96-134`）——省掉自研文件遍历与"包优先级"，直接复用原版 `SimplePreparableReloadListener`、`FileToIdConverter`、原版语言/音效系统；配 `PreLoadConfig` 在更早阶段读配置，避免"首启覆盖默认内容"。
3. **数据同步不写 per-type 序列化，直接下发原始 JSON 文本**：`CommonDataManager.apply()` 里顺手缓存 `element.toString()`（`resource/manager/CommonDataManager.java:33-48`）→ `ServerMessageSyncGunPack` → 客户端 `CommonNetworkCache` 用同一个 Gson 反序列化；再用 `ICommonResourceProvider` + `CommonAssetsManager.get()`（有服务端实例就用本地、否则用网络缓存）让**同一份业务代码同时服务单机和多人**（`CommonAssetsManager.java:228-236`）。
4. **属性数值修改抽成"addend/percent/multiplier + Lua function"**：`AttachmentPropertyManager.eval()` 三段式叠加，再允许每个 modifier 带一段 Lua 表达式（`x`/`r`→`y`）做任意曲线。数据包作者能写出"伤害=基础值×(1+百分比)×距离衰减函数"这类公式而不需要模组作者改 Java —— 适合所有"数值可扩展"的系统。
5. **重资源懒加载 + 预热**：模型/动画用 `LazyJsonDataManager`（`ClientAssetsManager.java:100-104`）按 id 惰性解析，再在资源重载后对"当前手持 + 快捷栏 + 背包"的物品主动 `warmUpModel/warmUpRuntime`（`ClientIndexManager.java:152-221`），避免第一帧渲染或打开背包时的大卡顿。

## 8. 对外 API 与第三方接入（非纯库模组，但有完整 API 面）

- **API 包**：`com.tacz.guns.api`（113 文件），主入口 `api/TimelessAPI.java`（查询 gun/ammo/attachment/block 的 common 与 client index、取 `GunDisplayInstance`、`registerThirdPersonAnimation`）。
- **主要扩展点**：
  - `api/resource/ResourceManager.registerExportResource(Class, path)`：附属把内置枪包目录导出到 `.minecraft/tacz`（TACZ 自用即此方式，`GunMod.java:62-65`）。
  - `api/item/gun/GunItemManager.registerGunItem(name, RegistryObject<AbstractGunItem>)`：注册自定义枪械物品变种（`AbstractGunItem` 抽象出 `shoot/startReload/tickReload/startBolt/melee/fireSelect/tickHeat` 等，`AbstractGunItem.java:54-97`）。
  - `api/item/{IGun,IAmmo,IAttachment,IBlock,IAnimationItem}` 与 `api/item/nbt/*DataAccessor`（如 `GunItemDataAccessor` 暴露 `GunId`/`GunFireMode`/`Attachment<Type>`/`GunLevelExp`/`HeatAmount` 等 NBT tag 常量），`api/item/builder/*` 提供物品栈构建器。
  - `api/entity/IGunOperator`、`api/client/gameplay/IClientPlayerGunOperator`（服务端/客户端操作抽象，`fromLivingEntity/fromLocalPlayer`）。
  - `api/event/common/*`（9 个枪械事件：Fire/Shoot/Reload/Draw/Melee/FireSelect/FinishReload/EntityHurtByGun/EntityKillByGun）、`api/event/server/AmmoHitBlockEvent`、KubeJS 事件包装。
  - `api/modifier/IAttachmentModifier` + `AttachmentPropertyManager.getModifiers()`（返回可变 Map，可注册新属性 modifier）、`GunProperty`/`GunProperties`/`CacheModifiableByScript`/`ValueModifiableAtRuntime`（脚本可改写数值）。
  - `api/client/animation/**`（ObjectAnimation/AnimationController/状态机/glTF 解析/interpolator）、`api/client/other/{IThirdPersonAnimation,ThirdPersonManager,GunModelTypeManager}`（自定义第三人称动画与模型类型）、`api/vmlib/*`（Lua 常量与库安装，`LuaLibrary.install(Globals)`）。
- **接入方式**：以 jitpack 产物为编译期依赖（readme 徽章）+ mods.toml 声明；第三方附属（如 `_bulk/Txt-Text__TaCZ-Labs`）在 `gradle.properties` 中声明 `tacz_version_range=[1.1.4,)`。KubeJS 侧由 `compat/kubejs/TimelessKubeJSPlugin` 暴露：注册 `tacz_gun` item type、`tacz:gun_smith_table_crafting` 配方 schema、事件组与 `TimelessItem/GunProperties` 绑定，模组未装 KubeJS 时整体跳过（`GunMod.java:54-56`）。
