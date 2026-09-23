# illusivesoulworks/charmofundying 源码分析报告

## 1. 基本信息

- Mod 名：Charm of Undying；mod_id：`charmofundying`；作者：Illusive Soulworks；描述：让不死图腾可放在饰品槽生效，不必手持
- 目标：MC 1.21.1，Java 21；加载器 **三个模块全支持**：`fabric`（loom，loader 0.15.11）、`forge`（50.0.31）、`neoforge`（21.1.1），共享 `common`
- 分支/版本：分支 `1.21.x`，commit `79909f5`，版本 `9.1.0+1.21.1`
- 许可证：LGPL-3.0-or-later
- 编译依赖（重点）：`dev.emi:trinkets:3.10.0`（Fabric，modImplementation）、`curios-forge/curios-neoforge:9.0.4`（compileOnly `:api`，toml 里 `curios` 为 required）、**SpectreLib 0.17.2（`spectrelib-common/fabric/forge/neoforge`，跨加载器配置库，common 用 `[0.3.0,)`）**、`mod_menu`(Fabric)、jsr305、mixin 0.8.5

## 2. 规模与包结构

- 31 个 `.java`，1603 行。common：`charmofundying`(CommonMod / Config / Constants)、`common`(ITotemEffectProvider、TotemProviders、VanillaTotemEffectProvider)、`common/integration`(BMEnchantedTotemEffectProvider)、`common/network`、`client`(TotemRenderer / ClientPacketHandler)、`mixin`、`platform`(+`services`)；fabric 8 文件（含 `common/integration/FWaystonesVoidTotemEffectProvider`）、forge 6、neoforge 6
- 最大文件：`CharmOfUndyingNeoForgeMod.java`(96)、`FWaystonesVoidTotemEffectProvider.java`(94)、`CharmOfUndyingFabricMod.java`(94)、`CharmOfUndyingForgeMod.java`(91)、`CharmOfUndyingCommonMod.java`(74)、`FabricPlatform.java`(70)
- **无物品/方块注册、无 assets**（资源仅 3 个文件：mixins.json + 两个 toml）

## 3. 入口与注册

三个加载器入口都只做编排：`CharmOfUndyingCommonMod.init()`（→ `TotemProviders.init()`）、`CharmOfUndyingConfig.setup()`、注册能力/网络/渲染器。Common 侧是纯静态工具类（`CharmOfUndyingCommonMod.java:35-37`），不依赖任何加载器类型；平台差异全部由 `Services.PLATFORM`（`IPlatform`：`findTotem/getRegistryName/isModLoaded/broadcastTotemEvent`）与 `IClientPlatform` 两个 ServiceLoader 接口承担。

“注册”只有两件事：
```java
// CharmOfUndyingNeoForgeMod.java:85-95（Forge 同构，用 CuriosApi.registerCurio）
for (Item item : BuiltInRegistries.ITEM) {
  if (TotemProviders.IS_TOTEM.test(item)) {
    evt.registerItem(CuriosCapability.ITEM, (stack, ctx) -> new ICurio() { ... }, item);
  }
}
```
以及客户端 `CuriosRendererRegistry.register(item, CurioTotemRenderer::new)`；Fabric 侧不注册能力，改在 `TrinketRendererRegistry.registerRenderer(...)` + `TrinketRenderer.translateToChest`。

## 4. 核心系统

**① 图腾效果提供者注册表（本仓库最有借鉴价值的设计）**：`common/TotemProviders.java:40-61` 用 `ConcurrentHashMap<String, ITotemEffectProvider>` 以**物品注册名字符串**为键（`Services.PLATFORM.getRegistryName(item)`），并暴露 `IS_TOTEM` 谓词给槽位查找复用；`putEffectProvider(key, provider)` 是公开扩展点。SPI `ITotemEffectProvider` 三方法：`applyEffects(entity, source, stack)`、`modifyStack(lookup, stack)`（默认 `shrink(1)`）、`bypassInvul()`（默认 false）。

**② mixin 分两处注入 death protection**：`mixin/MixinLivingEntity.java:37-61` 在 `LivingEntity.checkTotemDeathProtection` 上挂两个 `@Inject(cancellable=true)`：`HEAD` 处用于 `bypassInvul()==true` 的图腾（如 Fabric Waystones 的虚空图腾，需要在原版无敌判定之前生效）；另一处注入到 `INVOKE InteractionHand.values()` 调用点，用于普通图腾（此时原版已完成 bypass 伤害检查）。两次注入共享一个 `@Unique Pair<ITotemEffectProvider, ItemStack> charmofundying$totem` 字段——HEAD 里先解析出"用哪个 provider + 哪个栈"，第二处直接复用它 `useTotem`，避免重复查找。

**③ 槽位查找下沉到平台**：`IPlatform.findTotem` = Curios 的 `curios.findFirstCurio(stack -> IS_TOTEM.test(stack.getItem()))`（`NeoForgePlatform.java:37-41`）或 Trinkets 的 `component.getEquipped(...)`（`FabricPlatform.findTotem`）。common 完全不认识饰品库。

**④ 使用流程统一在 common**：`CharmOfUndyingCommonMod.useTotem:54-74` 先 `stack.copy()`，再 `effectProvider.modifyStack(...)` 消耗原栈，然后给 ServerPlayer `awardStat(Stats.ITEM_USED)` + `CriteriaTriggers.USED_TOTEM.trigger`，最后 `applyEffects` 成功才 `broadcastTotemEvent` —— 保证"消耗/成就/广播"与效果实现解耦。

**⑤ 客户端表现由网络包补齐**：`SPacketUseTotem`（record，`StreamCodec.composite(INT entityId, ItemStack.STREAM_CODEC)`）→ `ClientPacketHandler.handle:20-44` 重新生成 `TOTEM_OF_UNDYING` 粒子发射器、播放 `TOTEM_USE` 本地音效，若是自己再 `gameRenderer.displayItemActivation(stack)`；服务端用 `PacketDistributor.sendToPlayersTrackingEntityAndSelf` / `PlayerLookup.tracking` + self / Forge `SimpleChannel` 三套发送。

**⑥ 集成项的"静态注册"入口**：`FWaystonesVoidTotemEffectProvider.init()` 在 Fabric 入口按 `FabricLoader.isLoaded("fwaystones")` 调用；`VanillaTotemEffectProvider.modifyStack` 内按 `isModLoaded("mr_infinite_totem")` 查无限附魔决定是否消耗；Fabric 入口还给 `netheriteextras:totem_of_neverdying` 现场匿名子类覆写 `modifyStack` 改成按耐久消耗。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：1 个 S2C 包 `charmofundying:use_totem`。NeoForge `playToClient(TYPE, STREAM_CODEC, handler)`；Forge `ChannelBuilder.named(...).simpleChannel()` + `messageBuilder(...).consumerNetworkThread(→ DistExecutor.unsafeRunWhenOn(CLIENT))`（`forge/.../CharmOfUndyingForgeNetwork.java:29-52`）；Fabric `PayloadTypeRegistry.playS2C().register` + `ClientPlayNetworking.registerGlobalReceiver`。无 C2S。
- 配置：**SpectreLib**（`CharmOfUndyingConfig.java`，SERVER 类型），4 项：`xOffset/yOffset/zOffset`(defineInRange ±100)、`renderTotem`(boolean)，客户端渲染时直接读 `CharmOfUndyingConfig.SERVER.renderTotem.get()`；Fabric 侧靠 `CharmOfUndyingConfigInitializer implements SpectreConfigInitializer` 触发。
- datagen：无。数据驱动：无（**仓库内无槽位 JSON**，槽位沿用 Trinkets/Curios 自带槽位；具体槽位名未在仓库内定义，未确认）。

## 6. Mixin

配置：`common/src/main/resources/charmofundying.mixins.json`（required、`compatibilityLevel: JAVA_17`、`refmap: charmofundying.refmap.json`、client 组为空）。唯一条目：`MixinLivingEntity` → 目标 `LivingEntity.checkTotemDeathProtection`，注入点 = `@At("HEAD")` 与 `@At(value="INVOKE", target="...InteractionHand.values()[...")`，均 `cancellable=true`，命中后 `cir.setReturnValue(true)`。

## 7. 值得学的 5 条具体做法

1. **以"注册名字符串"为键的效果提供者表**：`TotemProviders` 用 `ConcurrentHashMap<String, ITotemEffectProvider>` + `getRegistryName(item)`（`TotemProviders.java:36,56`）——场景：要按物品挂不同行为、又不想持有 Item 引用（加载顺序安全），字符串键天然可跨 mod 扩展。
2. **两段式 mixin + `@Unique` 字段缓存中间结果**：`MixinLivingEntity.java:37-61`——场景：同一个目标方法需要"方法前"和"方法中某调用点"两处插入且共享数据，用字段传递比重复计算/让 common 缓存更安全。
3. **SPI 默认方法承载"绝大多数情况"**：`ITotemEffectProvider.modifyStack` 默认 `stack.shrink(1)`，特殊物品才覆写（匿名子类按耐久扣）——场景：扩展点接口要把 90% 行为设为默认实现，接入者只写差异部分。
4. **跨加载器用第三方配置库而非自己造**：SpectreLib 让 `CharmOfUndyingConfig` 在三个加载器共用一份 `SpectreConfigSpec` 代码（`CharmOfUndyingConfig.java:13-48`）——场景：多加载器项目不想维护三套 Config 类。
5. **消耗/统计/成就/广播与效果实现分离**：`CharmOfUndyingCommonMod.useTotem:54-74` 在 common 中统一处理 `awardStat`+`CriteriaTriggers.USED_TOTEM`+`copy()` 后置传递——场景：任何"物品被使用"的自定义逻辑，都应保持原版统计与成就链路完整。

## 8. 公开 API

非 API 前置类，但存在事实上的扩展点（未做 API 模块拆分）：`ITotemEffectProvider`（`common/.../common/ITotemEffectProvider.java`）+ `TotemProviders.putEffectProvider(String key, ITotemEffectProvider)`（`TotemProviders.java:59`）——外部 mod 只要在自己的入口里 put 一个 `"namespace:item"` → provider 即可让任意物品成为图腾，无需依赖本 mod 的平台类。
