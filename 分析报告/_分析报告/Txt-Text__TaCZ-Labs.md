# Txt-Text/TaCZ-Labs 源码分析报告

## 1. 基本信息

- Mod 名 TaCZ:Labs；mod_id `taczlabs`；作者 Txt_Text；GPLv3（`gradle.properties` 声明，仓库无 LICENSE 文件）；版本 1.1.7，group `com.txttext`
- 目标 **Forge 1.20.1 / forge 47.3.33**，Java 17，ForgeGradle `[6.0.16,6.2)` + `org.spongepowered.mixin` 0.7 + parchment librarian；`annotationProcessor 'org.spongepowered:mixin:0.8.5:processor'`
- 定位：**纯客户端附属**（`src/main/resources/META-INF/mods.toml` 中 `side = "CLIENT"`）；依赖 **TaCZ**（`curse.maven:timeless-and-classics-zero-1028108:7745481`，mandatory `[1.0.0,)`）、cloth-config-forge 11.1.136（optional/client）、commons-math3

## 2. 源码规模与包结构

39 个 `.java` / 2898 行。包（`com.txttext.taczlabs`）：`hud/crosshair`(11) + `hud/crosshair/crosshairs`(6)、`config`(3) + `config/clothconfig`(3) + `config/fileconfig`(2)、`util`(6)、`mixin/crosshair`(1) + `mixin/sprintingshoot`(4，整文件注释)、`event/shoot`(2)

最大文件：`config/clothconfig/HudClothConfig.java`(357)、`hud/crosshair/CrosshairRender.java`(331)、`hud/crosshair/DeprecatedCrosshairRenderer.java`(316)、`hud/crosshair/crosshairs/AbstractCrosshair.java`(239)、`config/fileconfig/HudConfig.java`(188)、`util/CrosshairShootManager.java`(145)

## 3. 入口与注册

`TaCZLabs.java:22`：`@Mod(TaCZLabs.MODID)`，构造器仅 `if (FMLEnvironment.dist == Dist.CLIENT) ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ClientConfig.init())`（注释说明沿用旧写法以兼容旧版 Forge）：

```java
@Mod.EventBusSubscriber(modid = MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public static class ClientModEvents {
    @SubscribeEvent public static void onClientSetup(FMLClientSetupEvent event) { ClothConfig.register(); }
}
```

`config/clothconfig/ClothConfig.java:41` 通过 `ModLoadingContext.get().registerExtensionPoint(ConfigScreenHandler.ConfigScreenFactory.class, ...)` 把 Cloth Config 界面挂到 mod 列表（`ConfigBuilder.create().setParentScreen(parent)`）。无 DeferredRegister、无物品/方块。

## 4. 核心系统

**A. 准星接管** `mixin/crosshair/RenderCrosshairEventMixin.java`
- `@Mixin(RenderCrosshairEvent.class)`（TaCZ 自己的类），主注入：`@Inject(method = "renderCrosshair", at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/platform/Window;getGuiScaledWidth()I"), cancellable = true)`——卡在 TaCZ 取窗口尺寸处接管，末尾 `CrosshairRender.renderCrosshair(...); ci.cancel();`
- 按 `gunIndex.getType()`（pistol/smg/rifle/mg/shotgun/sniper/rpg）switch 到配置的 `CrosshairType`；配置为 `TACZ` 时 `return` 交还原版（`:64`）
- 第二处 `@Inject(method="renderHitMarker", at=@At("TAIL"))` 里 `RenderSystem.setShaderColor(1,1,1,1)`，修 TaCZ 命中标记残留着色（`:71`）

**B. 准星绘制管线** `hud/crosshair/CrosshairRender.java` + `crosshairs/*`
- `renderCrosshair` 内按 `CrosshairType` 懒建并缓存实例（`private static AbstractCrosshair crosshair`，`lastCrosshairType` 变化才重建），switch 生成 `Crosshair/RectCrosshair/RightAngleCrosshair/ArcCrosshair/RulerCrosshair`
- `crosshairs/AbstractCrosshair.java` 提供图元：`drawRect`/`drawArc`（`Tesselator` + `VertexFormat.Mode.QUADS` + `DefaultVertexFormat.POSITION_COLOR` + `GameRenderer::getPositionColorShader`），封装 `drawLineWithShadow`/`drawDot`（阴影=同图形偏移 + alpha 128）
- 每种准星只实现 `Render(x, y, spread)`，几何封装为 `Line`，尺寸/颜色全部静态读 `HudConfig`

**C. 扩散三模式** `CrosshairRender.getSpread`（`:88`）
- `REAL`：读 TaCZ `AttachmentCacheProperty.getCache(InaccuracyModifier.ID)` 的实时 inaccuracy map，经 `getGunSpread/getCrosshairSpread` 换算；`VIRTUAL` 用姿态常量（sneak 0.7 / lie 0.5）；`SPEED` 按移动速度
- `lerpAndUpdateSpread(baseSpread, radius)` + `DeltaTime` 做帧率无关平滑，`VISUAL_SCALE = 2.0f` 处理姿态变化的视觉放大

**D. 开火反馈** `util/CrosshairShootManager.java`
- `@Mod.EventBusSubscriber(value = Dist.CLIENT)` 监听 TaCZ `GunShootEvent`，只处理 `event.getShooter() == Minecraft.getInstance().player` 的客户端侧事件；读枪械真实后坐力累加 `currentShootPenalty`（上限 40），按 `DECAY_RATE = 0.70f` 每帧指数衰减

**E. 双套配置 + GUI 桥接** `config/fileconfig/HudConfig.java`、`config/clothconfig/HudClothConfig.java`
- `HudConfig` 为 `ForgeConfigSpec` 静态字段集合（分组 HUD/Global Settings）：7 个 `EnumValue<CrosshairType>` 枪种映射、`customCrosshairs`（按 GunID 覆盖）、RGBA 四通道 + 合成 `color`、`spreadTypes`
- `HudClothConfig` 每个条目 `.setSaveConsumer(HudConfig.X::set)`，ARGB 滑块联动 `updateColorFromARGB()`，`startEnumSelector(...).setEnumNameProvider(...)` 出 i18n 名称；Cloth 缺失时仅无 GUI

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端，无任何自定义包）
- 数据驱动：**无**；只通过 `com.tacz.guns.api`（`TimelessAPI.getClientGunIndex`、`GunData`、`AttachmentCacheProperty`、`RecoilModifier`）读 TaCZ 数据
- 配置：`config/ClientConfig.java` 汇总 `HudConfig.init(builder)` 返回 `ForgeConfigSpec`；`CommonConfig/ServerConfig/FunctionConfig/FunctionClothConfig` 全部整文件注释掉
- datagen：**无**

## 6. Mixin

`src/main/resources/taczlabs.mixins.json`（`required: true`、`refmap: taczlabs.refmap.json`、`compatibilityLevel: JAVA_17`、`defaultRequire: 1`）：
- 实际生效仅 `client: ["crosshair.RenderCrosshairEventMixin"]`；`mixins`/`server` 为空
- `mixin/sprintingshoot/` 4 个类整文件被注释：`LivingEntityShootMixin`（`@Redirect` 读 `ShooterDataHolder.sprintTimeS`，`opcode = Opcodes.GETFIELD`）、`LocalPlayerShootMixin`（`@Redirect` `IGunOperator.getSynSprintTime()`）、`LocalPlayerSprintMixin`（`@Inject getProcessedSprintStatus at RETURN ordinal=1`）、`ShootKeyMixin`——实现"跑射"，含"客户端与服务端无通信、靠双端 sprintTime 一致性保证不假开枪"的注释，属**有价值的死代码**
- 无 AT 文件

## 7. 值得学的 5 条做法

1. **取消式注入整段接管他人 GUI 渲染**：注入点选在目标方法靠前的 `INVOKE`（`Window.getGuiScaledWidth()`），算完坐标即 `ci.cancel()`，不复制上游逻辑；`mixin/crosshair/RenderCrosshairEventMixin.java:27`。
2. **在上游善后点复位渲染状态**：`renderHitMarker` 的 `TAIL` 里重置 `setShaderColor(1,1,1,1)`；同文件 `:71`。
3. **Cloth Config 只做 UI、值仍走 ForgeConfigSpec**：`setSaveConsumer(HudConfig.X::set)` 免维护第二套配置模型；`config/clothconfig/HudClothConfig.java:60`。
4. **enum 策略模式切换数据来源**：`SpreadType.REAL/VIRTUAL/SPEED` 一套渲染三种来源；`hud/crosshair/CrosshairRender.java:88`。
5. **用枚举值表达"交还上游"，而非 boolean**：`CrosshairType.TACZ` 直接 `return`；`mixin/crosshair/RenderCrosshairEventMixin.java:64`。

## 8. 公开 API

无对外 API（无 `api` 包）。可借鉴其**依赖姿态**：只消费 TaCZ 的公开 API（`IGun`、`IGunOperator`、`TimelessAPI`、`GunShootEvent`、`RecoilModifier`）+ 一个 mixin，是"轻量附属 mod 优先用 API、必要时才 mixin"的最小样本。
