# TheIllusiveC4/Caelus 源码分析报告

## 1. 基本信息

- Mod 名：Caelus API；mod_id：`caelus`；作者：Illusive Soulworks（原 TheIllusiveC4/C4）；仓库 group `com.illusivesoulworks.caelus`
- 目标版本：MC 1.21.1，Java 21，支持加载器 = Forge 52.0.1 + NeoForge 21.1.1（多加载器分模块 `common` / `forge` / `neoforge`，**无 fabric 模块**）
- Gradle：自研 `buildSrc` 脚本 `multiloader-common.gradle`、`multiloader-loader.gradle`（loader 模块 `commonJava` / `commonResources` 复用 common 源码与资源，`build.gradle` 内 `expandProps` 做 toml 占位符替换）；发布用 modrinth + publishCurseForge 插件
- 许可证：LGPL-3.0-or-later（选 LGPL 是为了让附属 mod 可静态链接而不被迫开源）
- 编译依赖：`net.neoforged:neoforge:21.1.1`（neoforge/build.gradle:41）、`org.spongepowered:mixin:0.8.5`（common，compileOnly）、`org.jetbrains:annotations:24.1.0`；**不依赖任何第三方 mod**，它本身就是被依赖的前置 API

## 2. 源码规模与包结构

- 26 个 `.java`，总计 1382 行（`find ... -exec wc -l`）——极小体量，适合精读
- 包结构（第 3 层）：`common/api`(1)、`common/common`(2)、`common/common/network`(1)、`common/common/registry`(2)、`common/mixin/core`(4)、`common/mixin/util`(2)、`common/platform`(1)、`common/platform/services`(2)、`forge/...`(5 文件，含 api/RenderCapeEvent、network/CaelusNetwork、platform/services)、`neoforge/...`(6 文件，结构对称)
- 最大文件：`CaelusNeoForgeRegistry.java`(111)、`CaelusForgeRegistry.java`(110)、`CaelusApiImpl.java`(96)、`CaelusApi.java`(90)、`CaelusNeoForgeMod.java`(65)、`CPacketFlight.java`(65)

## 3. 入口与注册

入口：`neoforge/.../CaelusNeoForgeMod.java:36`、`forge/.../CaelusForgeMod.java`（均在构造器里只做三件事：调用 `CaelusApiImpl.setup()`、挂载 mod 事件总线监听、挂载 `NeoForge.EVENT_BUS` / `MinecraftForge.EVENT_BUS`）。

注册不用 DeferredRegister/Registrate，而是自研平台抽象：`common/.../common/registry/RegistryProvider.java:29` 由 `Services.REGISTRY_FACTORY.create(...)` 返回平台实现，业务侧只写接口；加载器实现在 `CaelusNeoForgeRegistry` / `CaelusForgeRegistry`。

```java
// CaelusApiImpl.java:40-47
public static final RegistryProvider<Attribute> ATTRIBUTES =
    RegistryProvider.get(Registries.ATTRIBUTE, CaelusConstants.MOD_ID);
private static final RegistryObject<Attribute> FALL_FLYING = ATTRIBUTES.register("fall_flying",
    () -> new RangedAttribute("caelus.fallFlying", 0.1d, 0.0d, 1.0d).setSyncable(true));
private static final AttributeModifier ELYTRA_MODIFIER =
    new AttributeModifier(ResourceLocation.fromNamespaceAndPath(MOD_ID, "elytra"), 1.0f,
        AttributeModifier.Operation.ADD_VALUE);
```

注意 `0.1` 默认值 = 中性（DEFAULT），`setSyncable(true)` 保证客户端能同步到属性。

## 4. 核心系统

**① 属性三态飞行许可（核心设计）**：`CaelusApiImpl.canFallFly:69-89` 用 `TriState{ALLOW,DEFAULT,DENY}` 把连续的属性值分档——`val>=1.0` ALLOW、`0<val<1` DEFAULT、`val<=0` DENY；属性实例不存在时回退查胸甲槽物品 `Services.CAELUS.canFly(stack, entity)`。等价于"属性值作优先级闸门"，让附属 mod 既能强制允许也能强制禁止，而不必覆盖原版逻辑。

**② 修改原版判定而不替换**：`mixin/core/MixinLivingEntity.java:38-46` 用 `@ModifyArg` 改 `LivingEntity.updateFallFlying` 内 `setSharedFlag(IZ)V` 的布尔参数，判定收拢到 `mixin/util/MixinHooks.canFly(entity, oldFlag, newFlag)`；DEFAULT 分支返回 `newFlag` = 完整保留原版行为。

**③ 客户端预测 + 服务端确认**：`mixin/util/ClientMixinHooks.checkFlight()` 在本地满足条件时立即 `startFallFlying()` 并发包；服务端 `CPacketFlight.handle:47-58` 先 `stopFallFlying()` 再按同样条件（地面/水中/漂浮效果）重新校验后 `startFallFlying()`。载荷为空单例（`StreamCodec.unit(INSTANCE)`），只用包的存在性表达意图。

**④ 修饰符每 tick 重建**：`common/CaelusEvents.livingTick` 每 tick 先 `removeModifier(elytraModifier.id())` 再按当前胸甲物品决定是否 `addTransientModifier`，从而把"物品 → 属性"映射做成无状态、无需缓存失效的推导。

**⑤ 自实现 API 单例注入**：`mixin/core/MixinCaelusApi.java` 以 `@Mixin(value = CaelusApi.class, remap = false)` + `@Inject(at=HEAD, method="getInstance", cancellable=true)` 让抽象类静态工厂返回 `CaelusApiImpl.INSTANCE`，避免暴露实现类给附属 mod。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：仅 1 个包。NeoForge 用 `evt.registrar(MOD_ID).playToServer(CPacketFlight.TYPE, StreamCodec.unit(CPacketFlight.INSTANCE), handler)`（`CaelusNeoForgeMod.java:53-57`）；Forge 端 `forge/.../network/CaelusNetwork.java`（49 行）手写旧式通道注册。`CPacketFlight` 实现 `CustomPacketPayload`，`TYPE` 为 `caelus:flight`。
- 配置：无。datagen：无。数据驱动：无（纯代码逻辑）。

## 6. Mixin

配置：`common/src/main/resources/caelus.mixins.json`（`required: true`、`compatibilityLevel: JAVA_17`、`injectors.defaultRequire: 1`）。mixins 组：`MixinCaelusApi`（hook `CaelusApi.getInstance` 静态方法）、`MixinLivingEntity`（hook `updateFallFlying`）；client 组：`MixinLocalPlayer`（`@Inject` + `@ModifyVariable` 双注入 `aiStep` 中 `getItemBySlot` 调用点，用 `@Unique caelus$flag` 暂存判定结果，不满足时把槽位物品替换为 `ItemStack.EMPTY`）、`MixinCapeLayer`（hook `CapeLayer.render`，`canRenderCape` 为假时 `cb.cancel()` 阻止原版披风在飞时渲染）。

## 7. 值得学的 5 条具体做法

1. **用属性 + 三态枚举做兼容开关**：`CaelusApiImpl.canFallFly` + `CaelusApi.TriState`——场景：任何"你想让别的 mod 能覆盖你的默认行为"的功能点，用数值带宽（<0 / 0~1 / >=1）表达 DENY/DEFAULT/ALLOW，比布尔注入点多一档"不表态"。
2. **ServiceLoader 做多加载器平台层**：`platform/Services.java:26-39` 用 `ServiceLoader.load(...).findFirst().orElseThrow()` + `platform/services/ICaelusPlatform`、`IRegistryFactory` 接口——场景：common 代码不 import 任何加载器类，只依赖服务接口，新平台只需加一个实现模块。
3. **自研 RegistryProvider 取代 DeferredRegister**：`common/.../registry/RegistryProvider.java:29,37` 只有 6 个方法（register/getEntries/getModId + 2 静态工厂），换平台零改动——场景：前置库 mod 想同时支持 Forge/NeoForge 而不复制注册代码。
4. **空载荷包表达动作**：`CPacketFlight.INSTANCE` + `StreamCodec.unit(...)`——场景：客户端只请求"执行一次服务端动作"（跳跃、开始飞行、打开 GUI），无需任何字段，服务端自行重新校验，天然防作弊。
5. **判定逻辑写在 `mixin/util/*Hooks` 而非 mixin 类内**：`MixinHooks.canFly`、`ClientMixinHooks.checkFlight/canRenderCape`——场景：mixin 类只做转发，纯逻辑可单元测试、可被多条注入点复用，也便于阅读注入意图。

## 8. 公开 API（本 mod 属 API/前置类）

- 公开包：`com.illusivesoulworks.caelus.api`（`CaelusApi`，及平台专属事件 `forge|neoforge/.../api/RenderCapeEvent.java`）
- 扩展点：`CaelusApi.getInstance()` 单例入口（未安装实现会抛 `RuntimeException("Missing Caelus API implementation!")`，可作软依赖探测）；`getFallFlyingAttribute()` 返回 `Holder<Attribute>`；`getElytraModifier()` 供原版鞘翅使用；`canFallFly(entity)` / `canFallFly(entity, checkDefaults)`；`TriState` 枚举
- 附属 mod 接入方式：①把自己的胸甲物品注册属性修饰符（+1.0 ADD_VALUE 到 `caelus:fall_flying`）即可获得飞行；②用负值/大于 1 的值覆盖他人；③客户端披风遮蔽可监听 `RenderCapeEvent`（`CaelusApi` 本身不含事件，事件类在各加载器模块的 `api` 包内，属平台差异点）
