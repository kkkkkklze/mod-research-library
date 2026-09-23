# Serilum/Collective 源码分析报告

> 分析对象：`源码库\_参考仓库\_bulk\Serilum__Collective`（MC 26.2 版源码，v8.39）。
> 定位：Serilum 200+ 个小 mod 的公共前置库（"mods 的共享代码 + 配置系统 + 网络 + 翻译"）。

## 1. 基本信息

| 项 | 值（来源） |
|---|---|
| Mod 名 / mod_id | Collective / `collective`（`gradle.properties`） |
| 作者 | Serilum（Rick South，`Common/src/main/resources/META-INF/mods.toml`） |
| 版本 / 目标 | 8.39；MC 26.2（`minecraft_version=26.2`、`minecraft_display_version=26.2.0`），Java 25 |
| 加载器 | Fabric loader 0.19.3 + fabric-api 0.152.1+26.2；Forge 65.0.0；NeoForge 26.2.0.1-beta |
| Gradle | MultiLoader 模板：`settings.gradle` include `Common/Fabric/Forge/NeoForge`；约定插件在 `buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`；外层插件 fabric-loom 1.15-SNAPSHOT、neoforged.moddev 2.0.141（`build.gradle`）；Forge 模块用 forge gradle `[7.0.29,8.0)` + accesstransformers 5.0.3 + jarjar 0.2.3（`Forge/build.gradle:1-6`） |
| 许可证 | All Rights Reserved（`license.md`） |
| 编译依赖 | Common 仅 `compileOnly` mixin 0.8.5 + mixinextras-common 0.3.5（`Common/build.gradle`）；Fabric 模块额外 `api com.terraformersmc:modmenu:20.0.0-beta.2`。`mods.toml` 只声明对 `minecraft` 的 required 依赖 → 它是纯"被依赖方"，不依赖任何内容 mod |

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **271**，总行数 **14907**；分模块 Common 111 / Fabric 95 / Forge 32 / NeoForge 33。

Common（`Common/src/main/java/com/natamus/collective/`）按包文件数：
- `functions` 39（`BlockPosFunctions`/`GearFunctions`/`PlayerFunctions`/`EntityFunctions`/`MessageFunctions`/`StringFunctions`/`JsonFunctions`/`FABFunctions`…，全部是无状态静态工具类）
- `services/helpers` 10、`data` 7、`translations` 6、`implementations/event` 6、`schematic` 5、`globalcallbacks` 5、`config` 4、`implementations/networking` 4、`networking/packets` 3、`implementations/networking/api` 3

Fabric：`fabric/mixin` 47、`fabric/mixin/crop` 10、`fabric/callbacks` 20、`fabric/services` 10、`fabric/bundle` 2。NeoForge/Forge 结构对称：`services` 10、`mixin` 13/14、`events`、`config`、`networking`、`translations`、`bundle`。

最大文件：`config/DuskConfig.java` 719、`functions/GearFunctions.java` 486、`functions/BlockPosFunctions.java` 428、`schematic/Schematic.java` 384、`functions/PlayerFunctions.java` 373、`functions/FABFunctions.java` 265。

## 3. 入口与注册

Common 无入口，只有一个静态 init：`Common/src/main/java/com/natamus/collective/CollectiveCommon.java:12-21`

```java
public static void init() {
    Constants.LOG.info("Loading Collective version " + CollectiveReference.VERSION + ".");
    CollectiveConfigHandler.initConfig();      // 反射式配置系统
    GlobalVariables.generateHashMaps();        // 共享查表
    LoadJSONFiles.startListening();            // JSON 回调
    registerPackets();
    loadEvents();                              // Services.ENTITYDATA.init()
}
```

- 三平台各自实现加载：`Fabric/src/main/java/com/natamus/collective/CollectiveFabric.java:23`（`ModInitializer`）、`CollectiveFabricClient.java:11`（`ClientModInitializer`，注意包名是 `com.natamus.collective` 而非 `.fabric`）、`NeoForge/.../CollectiveNeoForge.java:24`（`@Mod`）、`Forge/.../CollectiveForge.java:26`（`@Mod`）。平台类只做三件事：调 `CollectiveCommon.init()`、把加载器事件转发到 Common 的 `CollectiveEvents`、注册平台独有监听（如 NeoForge 的 `NeoForgeRegisterItemHelper::addItemsToCreativeInventory`）。
- **没有统一 DeferredRegister 框架**：注册被抽象成 `services/helpers/RegisterBlockHelper`、`RegisterItemHelper`，接口方法一律用 `Object modEventBusObject` 传事件总线，避免 Common 泄漏加载器类型。NeoForge 实现 `NeoForge/.../services/NeoForgeRegisterBlockHelper.java:70-91` 内部按 namespace 缓存 `DeferredRegister.Blocks`，注册完成后用反射把对象写回调用方静态字段（`setRegisteredBlockWithItemPair`，同文件 54-68）。
- 每个平台入口最后都调 `check/RegisterMod.register(NAME, MOD_ID, VERSION, ACCEPTED_VERSIONS)`（异步更新检查），版本常量集中在 `util/CollectiveReference.java`。

## 4. 核心系统

1. **ServiceLoader 平台抽象**：`services/Services.java:8-21` 用静态字段 `ServiceLoader.load(X.class).findFirst().orElseThrow(...)` 持有 10 个 helper（`ModLoaderHelper`、`RegisterBlockHelper/ItemHelper`、`RegisterKeyMappingHelper`、`EventTriggerHelper`、`TeleportHelper`、`BlockTagsHelper`、`EntityDataHelper`、`ClientUtilsHelper`、`ToolFunctionsHelper`）；三平台各出 10 个实现类。Common 侧调用 `Services.MODLOADER.isClientSide()/isModLoaded()`（示例：`config/DuskConfig.java:116`）。**注意：`META-INF/services/*` 声明文件未包含在公开源码里（未确认，疑由构建生成），Fabric 的 `fabric.mod.json` 同样缺失。**
2. **自带事件总线 + globalcallbacks**：`implementations/event/EventFactory.java:10` 注释写明取自 Fabric API，配 `Event.java`/`ArrayBackedEvent.java`/`PhaseSorting.java`，为 Common 提供带优先级的事件；对外扩展点是 `globalcallbacks/`（`JSONCallback`、`GlobalCropCallback`、`CachedBlockEntityCallback`、`CollectiveGuiCallback`、`MainMenuLoadedCallback`）。Fabric 侧直接复用原生 `net.fabricmc.fabric.api.event.EventFactory`（`fabric/callbacks/` 20 个类），NeoForge/Forge 侧用 `@EventBusSubscriber` 把平台事件转成同一个 `CollectiveEvents` 方法（`NeoForge/.../events/RegisterCollectiveNeoForgeEvents.java:21-47`）。
3. **配置系统 DuskConfig（最大价值点）**：`config/DuskConfig.java` 注明基于 MidnightLib v2.2.0；注解 `@Entry(min,max,isColor)`/`@Comment`/`@Client`/`@Server`/`@Hidden`（633-645 行），反射遍历 `config.getFields()` 建 UI（`DuskConfigScreen`/`DuskConfigListWidget`/`ButtonEntry`），Gson 写 `config/<modid>.json5`（`DuskConfig.java:87,93`）。依赖 mod 只要写一个 `extends DuskConfig` 的类 + 静态 `@Entry` 字段（范例 `config/CollectiveConfigHandler.java:9-24`），就自动获得 JSON5 配置与游戏内配置界面。
4. **跨平台网络层**：`implementations/networking/`（注释标明基于 MIT 的 mysticdrew/common-networking），`api/Network.java:29` 提供 `registerPacket(Identifier, Class, encoder, decoder, handler)`，`api/NetworkHandler.java:17-153` 定义 `sendToClient/sendToClients/sendToClientsInLevel/sendToClientsLoadingChunk/sendToClientsInRange` 等 default 方法，`api/Dispatcher.java` 是静态门面；平台实现 `FabricNetworkHandler`/`NeoForgeNetworkHandler`/`ForgeNetworkHandler` 负责实际 payload 注册。自带 `packets/CollectiveInstalledPacket` 用于探测"对端是否装了 Collective"，`isRegisteredOnClient` 让服务端只在对方装库时发自定义包，天然兼容原版客户端。
5. **翻译与资源包下发**：`translations/TranslationDownloader.java:24-54` 从 `translations.serilum.com` 拉取语言 JSON 到 `data/serilum/translations`（用 `manifest.min.json` 时间戳做增量，`applied.json` 记状态）；`translations/ServerTranslationPack.java:41-90` 在服务端给没装 Collective 的玩家推送/要求资源包，并按 `itemNameTranslationMode`（auto/server/client）决定物品名走翻译键还是服务端语言。这是"一套文案服务全部子 mod 用户"的方案。
6. **实体替换（SAM）与 JSON 数据驱动**：`data/GlobalVariables.java` 存放共享表（`globalSAMs`、`activeSAMEntityTypes`、`moddedvillagers`、`blocksWithTileEntity`），`events/CollectiveEvents.java:73-207` 在实体加入世界时按 `SAMObject`（原/目标实体、changeChance、onlyOnSurface、onlyBelowSpecificY、itemToHold、rideNotReplace）概率替换并转移装备/年龄/坐骑，用 `entity.addTag("collective.checked")` 防重入；`config/GenerateJSONFiles.java:20-45` + `LoadJSONFiles.java` 让子 mod 声明需要哪些 JSON（`area_names.json`、`entity_names.json`、`linger_messages.json`），由库统一生成/读取。
7. **杂项**：`functions/` 39 个工具类覆盖方块坐标、齿轮/装备、玩家、消息（含 `sendTranslatableMessage` 系列 20+ 重载）、作物、爆炸、RayTrace；`schematic/Schematic.java` 提供结构化蓝图解析；`fakeplayer/FakePlayer.java`；`check/RegisterMod.java:74-88` 用守护线程池 + `HttpClient` 做非阻塞更新检查（失败静默）；`check/ShouldLoadCheck.java:6-11` 判断是否被 jar-in-jar 打包并按 bundle 配置决定是否生效。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.4，注册在 `networking/PacketRegistration.java:12-15`（`CollectiveInstalledPacket`、`EntityDataSyncPacket`），由平台入口在 Common init 与客户端初始化时分别调用。
- 数据驱动：`JSONCallback.ALL_JSON_FILES_AVAILABLE`（`globalcallbacks/JSONCallback.java:18`）+ `GenerateJSONFiles.requestJSONFile(modid, fileName)` 是给子 mod 用的双侧 JSON 管线；`data/BlockEntityData.java` + `EntityDataSyncPacket` 做实体附加数据同步。
- 配置：DuskConfig（见 4.3），配置项本体在 `CollectiveConfigHandler`，注释元数据用 `configMetaData` HashMap 描述。
- datagen：**无**（全仓库无 `GatherDataEvent`/`DataProvider`）；仅 `NeoForge/build.gradle` 与 `Forge/build.gradle` 保留了 `runData` 运行配置和 `src/generated/resources` 源集，实际未使用。

## 6. Mixin

配置：`Fabric/src/main/resources/collective_fabric.mixins.json`（mixins 33 + client 14）、`collective_fabric.crop.mixins.json`（10，作物生长专用，避免与其它 mod 的作物 mixin 冲突）、`collective_neoforge.mixins.json`（7+7）、`collective_forge.mixins.json`（6+7）；共 84 个 mixin 类（Fabric 57 / NeoForge 14 / Forge 13），Forge/NeoForge 各自维护独立 mixin 集合而非共用 Common。

- 每个配置都挂 plugin：`FabricMixinConfigPlugin.shouldApplyMixin`（`Fabric/src/main/java/com/natamus/collective/fabric/mixin/plugin/FabricMixinConfigPlugin.java:24-42`）按类名中的 `.fabric./.forge./.neoforge.` 过滤加载器，并用 `Class.forName` 探测运行环境（同文件 66-79，注释自嘲 "hack-ish"）；同时按 `FabricBundleJarJarCheck` + `FabricBundleConfigCheck` 决定 bundle 内子 mod 的 mixin 是否生效。
- 代表性 hook：`Fabric/.../mixin/PlayerMixin.java:24-53`（`@Mixin(Player.class, priority=999)`，`@ModifyVariable` 注入 `actuallyHurt` 的 `Math.max` 返回值做伤害计算回调、`@Inject` 到 `getDestroySpeed` RETURN 做挖掘速度回调、`@Inject` 到 `drop` HEAD 做物品抛出回调，全部转发给 `fabric/callbacks/*` 的事件）；`Fabric/.../mixin/crop/CropBlockMixin.java:14-21`（`@Inject` 到 `randomTick` 中 `ServerLevel.setBlock` 的 INVOKE，可取消 → `PRE_CROP_GROW`）。
- 可访问性统一放在库内：`Common/src/main/resources/META-INF/accesstransformer.cfg`（约 35 条，Forge/NeoForge 的 build.gradle 直接引用 Common 的该文件）与 `Common/src/main/resources/collective.accesswidener`（Fabric loom `accessWidenerPath` 指向它），子 mod 无需自己写 AT/AW。

## 7. 值得学的 5 条做法

1. **平台抽象用 ServiceLoader + `Object` 参数**：Common 接口不出现任何加载器类型，注册总线以 `Object modEventBusObject` 传递（`services/helpers/RegisterBlockHelper.java:14-27`），平台实现内再强转（`NeoForgeRegisterBlockHelper.java:70-91`）。适用：自己也写 Multiloader 库时。
2. **公共源集并入各加载器 jar**：`buildSrc/src/main/groovy/multiloader-loader.gradle:5-36` 用 `commonJava`/`commonResources` configuration 把 Common 的源码与资源直接编进 Fabric/Forge/NeoForge jar，避免运行期额外依赖。
3. **元数据模板化**：`buildSrc/src/main/groovy/multiloader-common.gradle:84-111` 把 `mod_id/version/各加载器版本` expand 进 `mods.toml`、`neoforge.mods.toml`、`fabric.mod.json`、`*.mixins.json`，实现一份版本号全平台一致。
4. **Mixin 用 config plugin 做加载器 + 开关过滤**：`FabricMixinConfigPlugin.java:24-42,66-79`；当库要"同时兼容三加载器且部分子 mod 可被禁用"时，这是最低成本的做法。
5. **AT/AW 集中在库里**：`Common/src/main/resources/META-INF/accesstransformer.cfg` + `collective.accesswidener`，子 mod 依赖库即可反射/直接访问私有成员，无需各自维护配置（`Forge/build.gradle:39-44`、`Fabric/build.gradle:23-26` 都引用 Common 的这份文件）。

## 8. 公开 API 与外部 mod 接入方式

- **依赖方式**：把 Collective 作为必选前置（`mods.toml` 只有 `minecraft` 依赖，自身可独立加载）；子 mod 通过 Gradle `compileOnly project(':Common')` 风格的 capability（`$group:$mod_id`）引用（见 `multiloader-loader.gradle:15-23`）。
- **准备 API**：`com.natamus.collective.functions.*`（39 个工具类）、`com.natamus.collective.schematic.*`、`com.natamus.collective.objects.RandomCollection/SAMObject`、`com.natamus.collective.data.GlobalVariables`。
- **扩展点**：
  - 配置：`extends com.natamus.collective.config.DuskConfig` + `@Entry` 静态字段 + `configMetaData` 注释（范例 `config/CollectiveConfigHandler.java`）
  - 事件：`globalcallbacks/*`（Common 事件，`Event<T>.register`）+ 平台 `fabric/callbacks/*`（Fabric 原生 Event）、`events/CollectiveEvents`（服务端 tick/实体加入）
  - 网络：`implementations/networking/api/Network.registerPacket(...)`、`Dispatcher.sendToServer/sendToClient/...`、`packets/EntityDataSyncPacket`（实体数据同步）
  - 数据：`config/GenerateJSONFiles.requestJSONFile(modid, fileName)` 请求库生成/读取 JSON
  - 生效开关：`check/ShouldLoadCheck.shouldLoad(modId)`、`translations/ServerTranslationPack.requireClientTranslations(modName)`（服务端翻译支持）、`features/PlayerHeadCacheFeature.enableHeadCaching()`（玩家头颅缓存）、`services/helpers/*` 接口（新增平台能力的扩展位）
  - 版本约束常量：`util/CollectiveReference.ACCEPTED_VERSIONS`（`"[26.2.0]"`），子 mod 用它给出兼容版本号给 `RegisterMod.register` 做更新检查
