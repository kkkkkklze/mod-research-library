# Darkhax-Minecraft/AttributeFix 源码分析报告

## 1. 基本信息

- Mod 名：AttributeFix；mod_id `attributefix`；作者 Darkhax
- 目标版本：`gradle.properties` version=24.0，`minecraft_version=1.20.4`
- 加载器：**三平台** Forge `49.0.19` + NeoForge `20.4.91-beta`（`neoforge_version_range=20.4,`）+ Fabric（loader `0.15.3`，fabric-api `0.93.1+1.20.4`）
- Gradle 插件：**没有 moddev/loom**。`common/build.gradle:1-3` 用 `org.spongepowered.gradle.vanilla 0.2.1-SNAPSHOT`（只拿到反混淆 MC，不含加载器）；`forge/build.gradle:1-6` 用 `net.minecraftforge.gradle '[6.0,6.2)'` + `org.spongepowered.mixin 0.7-SNAPSHOT`；`fabric/build.gradle:1-4` 用 `fabric-loom 1.2-SNAPSHOT`
- 许可证：LGPL V2.1
- 编译依赖：common 仅 `compileOnly org.spongepowered:mixin:0.8.5`；各平台 `implementation project(':common')`（forge/neoforge 为 `compileOnly project(':common')`）。**零第三方 mod 依赖**，`mods.toml` 只声明 minecraft + neoforge
- 构建脚本抽到 `gradle/` 目录：`property_loader / java / build_number / git_changelog / minify_jsons / signing / version_checker / patreon.gradle`，多项目复用

## 2. 源码规模与包结构

实测：**7 个 `.java`，331 行**（几乎是"教科书级最小 mod"）。

- `common/.../attributefix/config/AttributeConfig.java` 194 行（占 59%，全部业务逻辑）
- `common/.../attributefix/Constants.java` 46
- `common/.../attributefix/mixin/AccessorRangedAttribute.java` 23
- `neoforge/.../net/darkhax/neoforge/AttributeFixNeoForge.java` 18
- `fabric/.../AttributeFixFabricServer.java` 18、`...FabricClient.java` 15
- `forge/.../attributefix/AttributeFixForge.java` 17

包结构只有 `attributefix`、`attributefix.config`、`attributefix.mixin` 三个；`neoforge` 子项目甚至不复用主包名（`net.darkhax.neoforge`）。

## 3. 入口与注册

**没有任何注册内容**——不注册方块/物品/属性/事件，唯一改动是反射式修改已有 `RangedAttribute` 的字段。三个平台入口都只做同一件事：

```java
// neoforge/.../AttributeFixNeoForge.java:14-18
@SubscribeEvent
public static void onLoadComplete(FMLLoadCompleteEvent event) {
    AttributeConfig.load(FMLPaths.CONFIGDIR.get().resolve(Constants.MOD_ID + ".json").toFile()).applyChanges();
}
```

- NeoForge/Forge：`@Mod` + `@Mod.EventBusSubscriber(bus = Bus.MOD)`，监听 `FMLLoadCompleteEvent`
- Fabric：拆成两个入口类，`AttributeFixFabricServer` 用 `ServerLifecycleEvents.SERVER_STARTED` 且额外判 `server.isDedicatedServer()`；`AttributeFixFabricClient` 用 `ClientLifecycleEvents.CLIENT_STARTED`（`fabric.mod.json` 不在本快照中，entrypoint 声明方式**未确认**）

**时序设计点是关键**：故意等到加载完成（注册表已冻结）之后才改属性上界，因此不需要 registry 事件，也就不会被其他 mod 的注册顺序影响。

## 4. 核心系统

1. **属性上界改写（唯一功能）**：`AttributeConfig.applyChanges()`（`AttributeConfig.java:26-64`）遍历 `BuiltInRegistries.ATTRIBUTE`，只处理 `instanceof RangedAttribute` 的项，先校验 `minValue > maxValue` 则报错 `continue`，再只在值真的变化时调用 accessor 写入。核心技巧是通过 mixin 生成的接口强制转型：
   ```java
   final AccessorRangedAttribute accessor = (AccessorRangedAttribute) (Object) attribute;
   if (minValue != ranged.getMinValue()) accessor.attributefix$setMinValue(minValue);
   ```
   （`AttributeConfig.java:48-59`；accessor 定义见 `AccessorRangedAttribute.java:17-23`，`@Accessor("minValue") @Mutable` + `attributefix$` 前缀避免冲突）
2. **"默认值表"与配置合并**：`NEW_DEFAULT_VALUES`（`AttributeConfig.java:148-154`）把 `MAX_HEALTH / ARMOR / ARMOR_TOUGHNESS / ATTACK_DAMAGE / ATTACK_KNOCKBACK` 提升到 `1_000_000D`；`Entry` 构造（167-172 行）把 `min` 固定为原版值、`max` 取新默认值，且 `enabled = "minecraft".equals(id.getNamespace())` 只默认放行原版属性，第三方属性需手动开启——避免影响其它 mod 的数值平衡。
3. **配置文件自生成 + 不丢用户数据**：`load(File)`（66-142 行）先遍历注册表生成全部默认条目，若文件已存在则反序列化后**逐条校验**（ID 非法 / 属性不存在 / min > max 都仅打 error 日志），然后 `config.attributes.put(...)` 覆盖但不丢弃非法项（108-109 行注释明写 "Prevent data loss"），最后无条件回写完整文件——所以这个文件同时充当"已安装属性清单"。
4. **数字序列化细节**：`Constants.java:21-46` 用 `excludeFieldsWithoutExposeAnnotation()` + 自定义 `DoubleJsonSerializer`（`BigDecimal.toBigIntegerExact()` 失败就退回原值），避免 1000000.0 被写成科学计数法 / 出现多余小数位；另处理 `isInfinite()/isNaN()`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**
- 数据驱动：**无**（无 datapack、无 tag、无 `src/main/resources/data`）
- 配置：**手写 Gson JSON**（`config/attributefix.json`），不用任何配置库。`Entry` / `DoubleValue` 都用 `@Expose`，`DoubleValue` 用 `@SerializedName("default")` 输出 `{"default":8.0,"value":1000000.0}` 结构
- datagen：**无**

## 6. Mixin

配置：三份完全相同的 `attributefix.mixins.json`（`fabric/`、`forge/`、`neoforge/` 各自 resources），均 `required:true`、`compatibilityLevel: "JAVA_17"`、`defaultRequire:1`；仅 Forge 版多 `"refmap": "${mod_id}.refmap.json"`。
- `AccessorRangedAttribute` → target `RangedAttribute`，`@Accessor minValue / maxValue` + `@Mutable`（无 @Inject；文件里 import 了 `Inject/At/CallbackInfo` 但未使用，属残留）

## 7. 值得学的 5 条具体做法

1. **改原版对象优先用 `@Mutable` accessor，而不是重注册**：不碰注册表、不需要 registry 事件，兼容性最好（`mixin/AccessorRangedAttribute.java:17-23`）。
2. **在 `FMLLoadCompleteEvent`（加载完成后）才改数据**：绕开加载器注册顺序问题；Fabric 对应 `CLIENT_STARTED` / `SERVER_STARTED`（三个入口类）。
3. **默认值白名单化**：只对 `minecraft` 命名空间的属性默认 `enabled`，第三方属性要显式开（`AttributeConfig.java:169`）。
4. **配置回写时保留非法条目**：校验失败只打日志不动数据，防止用户手改配置后丢内容（`AttributeConfig.java:108-109`）。
5. **自定义 Gson `Double` 序列化器**：避免 `BigDecimal`/科学计数法污染配置文件，适合所有需要写"人类可读浮点数"的配置（`Constants.java:24-46`）。

## 8. 库 / API 说明

非库模组，无公开 API 与扩展点。**已知缺陷（供参考）**：`AttributeConfig.Entry.isEnabled()`（`AttributeConfig.java:174-177`）方法体为 `return this.isEnabled();`，是无终止条件的自递归，一旦被调用必然 `StackOverflowError`；当前代码路径未调用它，且 `applyChanges()` 也没读 `enabled` 字段（该开关实际未生效）。
