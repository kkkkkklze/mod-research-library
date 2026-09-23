# illusivesoulworks/elytraslot 源码分析报告

> 本地检出为 `1.21.4` 分支，commit `e13f8ae`，版本 `10.0.1+1.21.4`（非 1.21.1；1.21.1 对应 9.x，代码结构差异主要在渲染状态 API）

## 1. 基本信息

- Mod 名：Elytra Slot；mod_id：`elytraslot`；作者：Illusive Soulworks；描述：给鞘翅单独加一个饰品槽，飞行与胸甲共存
- 目标：MC 1.21.4，Java 21；加载器 = Fabric 0.113.0 + NeoForge 21.4.136。**本分支无 forge 模块**，目录为 `common` / `fabric` / `neoforge`（`fabric` 用 `fabric-loom`，`neoforge` 用 neoforge 插件，均复用 `common` 源码）
- 许可证：LGPL-3.0-or-later
- 编译依赖（关键）：NeoForge 侧 `top.theillusivec4.curios:curios-neoforge:10.0.1`（`implementation`，toml 中 `curios` 为 **required**）、`com.illusivesoulworks.caelus:caelus-neoforge:8.0.1:api`（`compileOnly` + required，`neoforge/build.gradle:45-48`）；Fabric 侧 `io.wispforest:accessories-fabric:1.2.19-beta`（modImplementation，required）、fabric-api、loader；两侧都 `compileOnly` 了 MinecraftCapes（`curse.maven:mccapes-359836`）；common 侧 `mixin:0.8.5`、`asm-tree:9.3`、jsr305

## 2. 规模与包结构

- 23 个 `.java`，926 行。包：`common/.../elytraslot`(常量)、`client`(1)、`common`(Fabric 的 AccessoryElytra / NeoForge 的 CurioElytra 各 1)、`integration/minecraftcapes`(1)、`mixin`(IntegrationMixinPlugin)、`mixin/integration/waveycapes`(1)、`platform`(+`platform/services` 共 6 接口/实现)；fabric 6 文件、neoforge 6 文件
- 最大文件：`ElytraSlotNeoForgeClientMod.java`(121)、`client/ElytraSlotLayer.java`(107)、`ElytraSlotNeoForgeMod.java`(94)、`ElytraSlotFabricMod.java`(90)、`ElytraSlotFabricClientMod.java`(74)、`common/CurioElytra.java`(63)
- **无任何方块/物品注册**：全部内容来自外部饰品库的槽位 + 行为桥接

## 3. 入口与注册

Fabric：`ElytraSlotFabricMod implements ModInitializer`（`onInitialize`）、`ElytraSlotFabricClientMod implements ClientModInitializer`。NeoForge：`@Mod(MOD_ID) ElytraSlotNeoForgeMod`、`@Mod(value = MOD_ID, dist = Dist.CLIENT) ElytraSlotNeoForgeClientMod`。没有任何 DeferredRegister，注册动作只有三类：饰品库注册（Curios 能力 / Accessories 注册）、槽位谓词注册、渲染层注册（用加载器事件而非注册表）。

```java
// ElytraSlotFabricMod.java:76-88 —— 处理"后注册"物品 + 已注册物品
RegistryEntryAddedCallback.event(BuiltInRegistries.ITEM)
    .register((i, resourceLocation, item) -> {
      if (item.getDefaultInstance().has(DataComponents.GLIDER)) {
        AccessoryRegistry.register(item, new AccessoryElytra());
      }
    });
for (Item item : BuiltInRegistries.ITEM) { if (item.getDefaultInstance().has(DataComponents.GLIDER)) { ... } }
```

NeoForge 侧对称：`RegisterCapabilitiesEvent` 里遍历 `BuiltInRegistries.ITEM`，凡默认实例带 `GLIDER` 组件就 `evt.registerItem(CuriosCapability.ITEM, (stack, ctx) -> new CurioElytra(stack), item)`（`ElytraSlotNeoForgeMod.java:86-94`）。

## 4. 核心系统

**① "以数据组件为判据"的通用适配**：全程用 `DataComponents.GLIDER` 代替物品白名单，任何带该组件的物品（原版鞘翅、模组滑翔物）自动可入槽，配合 `CuriosSlotTypes.registerPredicate(id, (ctx, stack) -> stack.has(GLIDER))`（NeoForge）/`SlotPredicateRegistry.register(..., TriState.TRUE/DEFAULT)`（Fabric）声明槽位合法性。同一思路贯穿注册、渲染、耐久全链路。

**② 属性桥接 Caelus**：NeoForge 在 `PlayerTickEvent.Post` 中每 tick 先 `removeModifier(ELYTRA_CURIO_MODIFIER.id())`，再在 `curios.isEquipped(stack -> stack.has(GLIDER))` 时 `addTransientModifier`（`ElytraSlotNeoForgeMod.java:69-84`），修饰符定义在 `common/CurioElytra.java:32`（+1.0 ADD_VALUE → `elytraslot:elytra`）。**Fabric 完全不同**：不碰属性，直接注册 `EntityElytraEvents.CUSTOM` 返回 `true` 让 Fabric API 接管飞行（`ElytraSlotFabricMod.java:43-66`）。这是"平台能力优先、属性方案兜底"的典型选择。

**③ 耐久与破坏分离到平台事件**：Fabric 用 `EntityElytraEvents.CUSTOM` 的 `tickElytra` 参数 `stack.hurtAndBreak(1, serverLevel, serverPlayer, item -> ref.reference().breakStack())`；NeoForge 监听 Caelus 的 `GlidingDamageEvent`，把找到的滑翔物 `evt.addGlider(curio.stack(), item -> CuriosApi.broadcastCurioBreakEvent(...))`（`ElytraSlotNeoForgeMod.java:57-67`）——用第三方事件把"谁该掉耐久"变成可扩展集合。

**④ 渲染状态（1.21.4 新架构）**：NeoForge 侧 `RegisterRenderStateModifiersEvent` 在实体渲染状态构建时扫描 Curios 槽，把第一个 `GLIDER` 物品 `renderState.setRenderData(ELYTRA_RENDER, stack.copy())`（`ELYTRA_RENDER` 是自定义 `ContextKey<ItemStack>`）；`NeoForgeClientPlatform.getRenderingElytra` 只读渲染状态，渲染层不接触实体数据。Fabric 无此机制，`FabricClientPlatform` 反查 `Minecraft.getInstance().level.getEntity(state.id)` 再取 AccessoriesCapability。

**⑤ 渲染层与披风互斥**：`client/ElytraSlotLayer.java:62-80` 仅在"槽内有滑翔物且胸甲不是原版鞘翅"时用 `EquipmentLayerRenderer.renderLayers(LayerType.WINGS, ...)` 画翅膀；贴图解析顺序 `getPlayerElytraTexture:84-105` = 皮肤 elytraTexture → MinecraftCapes → 披风贴图。披风遮蔽三平台三法：NeoForge 监听 Caelus `RenderCapeEvent` 后 `evt.setCanceled(true)`；Fabric 用 `LivingEntityFeatureRenderEvents.ALLOW_CAPE_RENDER`；对 WaveyCapes 用 mixin 取消其渲染。

**⑥ 条件 mixin**：`mixin/IntegrationMixinPlugin.java:24-34` 的 `shouldApplyMixin` 用 `Services.LOADING.isModLoaded("waveycapes")` 决定是否施加，配合 `@Pseudo @Mixin(targets = "dev.tr7zw.waveycapes...CustomCapeRenderLayer", remap = false)` 实现零硬依赖。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（`grep CustomPacketPayload|PacketDistributor` 无命中），纯客户端/服务端各自本地判定
- 配置：**无**（无 `ModConfigSpec`/config 类）
- datagen：**无**
- 数据驱动：仅"槽位谓词"注册（运行时谓词，非 JSON）；`fabric.mod.json` 未入库、由 loom/`build.gradle` 生成

## 6. Mixin

配置：`common/src/main/resources/elytraslot_integrations.mixins.json`（`required: false`、`compatibilityLevel: JAVA_16`、`plugin: ...IntegrationMixinPlugin`、`refmap: elytraslot.refmap.json`），toml 里以 `[[mixins]] config` 挂载。唯一条目：`mixin/integration/waveycapes/CustomCapeRenderLayerMixin` → `@Inject(at = @At("HEAD"), method = "render", cancellable = true)` 注入第三方 `CustomCapeRenderLayer.render`，槽内有滑翔物时 `ci.cancel()`。

## 7. 值得学的 5 条具体做法

1. **用数据组件而非物品白名单做判据**：`stack.has(DataComponents.GLIDER)` 贯穿注册/槽位谓词/渲染/耐久（`ElytraSlotNeoForgeMod.java:54,62,79,90`）——场景：你的功能要"适配所有同类物品"时，找原版已有的组件语义。
2. **同时处理"已注册"与"后注册"物品**：先 `for (Item item : BuiltInRegistries.ITEM)` 扫一遍，再 `RegistryEntryAddedCallback`（Fabric）/在能力注册事件的遍历中（NeoForge）兜底——场景：给别的 mod 的物品挂能力，且对方可能后加载。
3. **平台能力优于自造协议**：Fabric 直接用 `EntityElytraEvents.CUSTOM`，NeoForge 才退回 Caelus 属性——场景：多加载器项目里每个平台优先用其官方 API，common 只保留纯逻辑。
4. **渲染状态与渲染层解耦**：`ContextKey<ItemStack> ELYTRA_RENDER` + `RegisterRenderStateModifiersEvent`（`ElytraSlotNeoForgeClientMod.java:49,86-111`）——场景：1.21.4+ 渲染层拿不到实体时，先写入 renderState 再读。
5. **条件 mixin 插件按包名+modId 过滤**：`IntegrationMixinPlugin.shouldApplyMixin` 前缀匹配包名后 `isModLoaded`——场景：兼容补丁 mixin 目标可能不存在，必须能整体跳过且不污染日志。

## 8. 公开 API

非 API/前置类 mod：不对外暴露扩展点（对外提供的是"槽位可放 GLIDER 物品"这一行为）。它的对外契约是依赖 `curios` / `accessories` / `caelus` 三个前置的公开 API，实现路径见上。
