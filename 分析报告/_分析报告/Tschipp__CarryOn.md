# Tschipp/CarryOn 源码分析报告

## 1. 基本信息
- Mod 名：Carry On；mod_id `carryon`；作者 Tschipp, PurpliciousCow；version 2.11.1
- 目标版本（`gradle.properties`）：`minecraft_version=26.2`（range `[26.2, 27)`）、Java **25**、NeoForge `26.2.0.41-beta`、Forge `65.1.0`、Fabric `0.156.0+26.2`（loader 0.19.3，loom `1.17-SNAPSHOT`）
- 结构：`settings.gradle` → `include("Common","Fabric","NeoForge","Forge")`，另有 `buildSrc`（Groovy 构建插件）；四端共用 Common
- 许可证：GNU LGPLv3
- 编译依赖（`Common/build.gradle:24-31`）：`org.spongepowered:mixin:0.8.5`（compileOnly）、**mixinextras 0.5.4**（implementation + annotationProcessor，注释说明 Fabric/NeoForge 都已内置）、`cloth-config-neoforge:26.2.155`（compileOnly）；Fabric 端另有 `modmenu_version=18.0.0`

## 2. 源码规模与包结构
`find -name '*.java' | wc -l` → **96 个 / 8897 行**；Common 52、Fabric 15、NeoForge 14、Forge 15。
主要包（Common 侧）：`client/render`、`client/modeloverride`、`client/keybinds`、`common/carry`(+`compat`)、`common/scripting`、`common/config`、`common/pickupcondition`、`common/command`、`config`(+`annotations`，自建配置框架)、`networking/{clientbound,serverbound}`、`platform/services`、`mixin`、`utils`、`compat`。
最大文件：`client/render/CarryRenderHelper.java` 415、`common/config/CarryConfig.java` 392、`common/carry/PlacementHandler.java` 389、`common/scripting/Matchables.java` 354、`common/carry/PickupHandler.java` 322、`common/carry/CarryOnData.java` 281、`Forge/events/CommonEvents.java` 253、`common/config/ListHandler.java` 236、`NeoForge/events/CommonEvents.java` 232、`CarryOnCommon.java` 212、`common/scripting/CarryOnScript.java` 205。

## 3. 入口与注册
Common 侧不写 `@Mod`，只做静态引导（`CarryOnCommon.java:56-104`：`registerServerPackets/registerClientPackets/registerConfig/registerCommands`，网络注册把平台对象当 `Object... args` 透传）。
NeoForge 入口 `NeoForge/src/main/java/tschipp/carryon/CarryOnNeoForge.java:29` `@Mod(Constants.MOD_ID)`，注册表只用**一个 DeferredRegister**：
```java
private static final DeferredRegister<AttachmentType<?>> ATTACHMENT_TYPES =
        DeferredRegister.create(NeoForgeRegistries.ATTACHMENT_TYPES, Constants.MOD_ID);
public static final Supplier<AttachmentType<CarryOnData>> CARRY_ON_DATA_ATTACHMENT = ATTACHMENT_TYPES.register(
        "carry_on_data",
        () -> AttachmentType.builder(() -> new CarryOnData(new CompoundTag()))
                .sync(new CarryOnDataSyncHandler())          // 自动同步包
                .serialize(CarryOnData.CODEC.fieldOf(CarryOnData.SERIALIZATION_KEY))  // 存档
                .build());
```
无 Registrate；物品/声音等原版注册项通过 JSON 或原版机制，Common 层无注册体系。

## 4. 核心系统
**① 平台抽象（platform/services）**：`Services.java:35-42` 用 `java.util.ServiceLoader.load(clazz).findFirst()` 加载 `IPlatformHelper`、`IGamestagePlatformHelper`。网络注册被抽象成 `registerServerboundPacket(type, clazz, codec, handler, Object... args)`，NeoForge 实现里强转 `args[0]` 为 `PayloadRegistrar` 并统一包 `ctx.enqueueWork(() -> handler.accept(packet, ctx.player()))`（`NeoForgePlatformHelper.java:73-98`）。玩家状态的读写也走平台层：`CarryOnDataManager.getCarryData → Services.PLATFORM.getCarryData(player)`（`common/carry/CarryOnDataManager.java:28-38`）。
**② 携带状态 CarryOnData**：`CarryType{BLOCK, ENTITY, PLAYER, INVALID}`；序列化一把梭 —— `CompoundTag.CODEC.flatXmap(...)` 包住整个对象（`CarryOnData.java:67-82`），再用 `ByteBufCodecs.fromCodecWithRegistries(CODEC)` 得到 `StreamCodec`（:84），同一份 CODEC 同时服务存档与网络。方块存 `NbtUtils.writeBlockState` + `tile.saveWithId`，实体存 `entity.save(TagValueOutput)`，被抱的玩家只存 UUID（:128-226）。水logged 状态在搬运时强制置 false（:133-134）。
**③ 数据驱动脚本（common/scripting）**：`CarryOnScript` 是 record，`RecordCodecBuilder` 分 `object/conditions/render/effects` 四段且各段 `optionalFieldOf(..., EMPTY)`（`CarryOnScript.java:61-70`）；`ScriptReloadListener extends SimpleJsonResourceReloadListener`，路径 `FileToIdConverter.json("carryon/scripts")`（`ScriptReloadListener.java:41-44`），reload 后用 `ClientboundSyncScriptsPacket` 推给客户端；`ScriptManager.inspectBlock/inspectEntity` 遍历 `SCRIPTS`，按 name/hardness/resistance/height/width/health/NBT 全匹配（`ScriptManager.java:47-113`），被 `settings.useScripts` 总开关控制。
**④ 渲染**：`client/render`（CarryRenderHelper 415 行 + CarriedObjectRender + CarryingItemRenderLayer + `ICarryOnRenderState` 适配 1.21.8+ render state）+ `client/modeloverride`（替换手臂/手持模型），配合 `MinecraftMixin`/`PlayerRenderStateMixin`/`EntityRendererMixin`。
**⑤ 拾取/放置条件**：`PickupConditionHandler` 把配置字符串解析为 `PickupCondition`（DataResult 失败只记 debug 日志，`PickupConditionHandler.java:42-69`）；`PlacementHandler`（389 行）负责放回世界与把玩家挂成乘客。
**⑥ 自建注解配置框架**：`config/annotations`（`@Config/@Category/@Property`）+ `AnnotationData/BuiltConfig/PropertyData/PropertyType/ConfigLoader`，平台侧只需薄薄一层 `ConfigLoaderImpl`（Fabric 196 行 / NeoForge 140 行），GUI 编辑由 `compat/ClothConfigCompat` 提供。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`networking/PacketBase.java:26-29` 是 `extends CustomPacketPayload` 且只声明 `void handle(Player)` 的接口，所有包实现它，由平台层统一包装成 `IPayloadHandler`；包 ID 常量集中在 `Constants.java:37-41`（key_pressed / start_riding / sync_scripts / start_riding_other / **sync_carry_data**）。共 1 serverbound + 3 clientbound（`CarryOnCommon.java:56-92`）；玩家状态同步主要走 NeoForge attachment 的 `sync` handler，而非手写包。
- 数据驱动：`data/<ns>/carryon/scripts/*.json` 脚本（见 ④③）。
- 配置：自建框架 + Cloth Config（可选）。
- datagen：Common 未发现 DataProvider（未确认 Forge 端是否另有）。

## 6. Mixin
- `Common/src/main/resources/carryon.mixins.json`：package `tschipp.carryon.mixin`，`compatibilityLevel JAVA_21`，**plugin `tschipp.carryon.mixin.CarryOnMixinConfigPlugin`**（NeoForge 侧还有一份 CarryOnMixinConfigPlugin 实现，用于条件禁用）；common: `EntityMixin`、`InventoryMixin`、`PlayerMixin`；client: `AvatarRendererMixin`、`EntityRendererMixin`、`HumanoidModelMixin`、`MinecraftMixin`、`PlayerRenderStateMixin`；另有 `carryon.fabric.mixins.json`、`carryon.forge.mixins.json`，而 `carryon.neoforge.mixins.json` 列表为空。
- 代表 hook：`mixin/PlayerMixin.java:48` `@Inject(method="readAdditionalSaveData(Lnet/minecraft/world/level/storage/ValueInput;)V", at=@At("RETURN"))`，用 `input.read("CarryOnData", CarryOnData.CODEC)` 从旧存档恢复数据（注释注明为跨版本兼容）；`:57` override `stopRiding()` 处理玩家被抱时清除状态与 slowness 效果。

## 7. 值得学的 5 条
1. **四加载器共用一个 Common + 静态 Services + ServiceLoader 的平台抽象**（不引 Architectury）：`platform/Services.java:35`、`platform/services/IPlatformHelper.java`；签名用 `Object... args` 把平台专属对象（PayloadRegistrar）透传，Common 完全不碰平台类。
2. **玩家附加状态用 AttachmentType，一次注册 `sync` + `serialize` 两个 handler 就拿到同步与存档**：`NeoForge/src/main/java/tschipp/carryon/CarryOnNeoForge.java:33-39`，避免自己维护同步包。
3. **状态类用 `CompoundTag.CODEC.flatXmap` 整体包装**，NBT 存档与 `ByteBufCodecs.fromCodecWithRegistries` 网络流共用同一 CODEC：`common/carry/CarryOnData.java:67-84`。
4. **把玩法规则做成数据包 JSON 脚本 + reload 后同步客户端**：`common/scripting/ScriptReloadListener.java:41`、`CarryOnScript.java:61`，让整合包作者自定义"什么能搬"，同时服务端与客户端判定一致。
5. **自建注解驱动配置框架**（`config/annotations` + `BuiltConfig`），平台差异只剩一个 `ConfigLoaderImpl`，并留 Cloth Config 兼容层：`Common/.../config/BuiltConfig.java`、`compat/ClothConfigCompat.java`。

## 8. 公开 API
非库 mod，但可被外部接入的扩展点：`common/scripting` 的 JSON 脚本（数据包）、`config` 的黑/白名单与 `customPickupConditions`、`platform/services/IPlatformHelper`（同架构模组可复制的服务接口）。
