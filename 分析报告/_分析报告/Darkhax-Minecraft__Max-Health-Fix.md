# Darkhax-Minecraft/Max-Health-Fix 源码分析报告

## 1. 基本信息

- Mod 名：MaxHealthFix；mod_id `maxhealthfix`；作者 Darkhax
- 目标版本：`gradle.properties` version=15.0，`minecraft_version=1.20.4`（注意：**不是 1.21.1**）
- 加载器：**三平台** Forge `49.0.19` + NeoForge `20.4.91-beta` + Fabric（loader `0.15.3`，fabric-api `0.93.1+1.20.4`）
- Gradle 插件：`common/build.gradle:1-3` 用 `org.spongepowered.gradle.vanilla`（只拿反混淆 MC，无加载器）；forge/neoforge 用 `net.minecraftforge.gradle` + `org.spongepowered.mixin`；fabric 用 `fabric-loom`
- 许可证：LGPL V2.1
- 编译依赖：common 仅 `compileOnly org.spongepowered:mixin:0.8.5` + `jsr305`；**零第三方 mod 依赖**，`mods.toml` 只声明 `neoforge` + `minecraft`
- 构建脚本抽到 `gradle/` 供多项目复用：`property_loader / java / build_number / git_changelog / minify_jsons / signing / version_checker.gradle`

## 2. 源码规模与包结构

实测：**7 个 `.java`，154 行**——比 AttributeFix 更小的"最小 mod 范本"。

- `common/.../net/darkhax/maxhealthfix/mixin/MixinLivingEntity.java` 78 行（占 50%，全部逻辑）
- `common/.../mixin/MixinPlayerList.java` 28
- `common/.../IHealthFixable.java` 7、`common/.../Constants.java` 11
- `forge/.../MaxHealthFixForge.java` 11、`neoforge/.../MaxHealthFixNeoForge.java` 11、`fabric/.../MaxHealthFixFabric.java` 8

包只有 `maxhealthfix` 与 `maxhealthfix.mixin` 两个。

## 3. 入口与注册

**完全没有注册内容**，三个平台入口类都只打一行日志（`MaxHealthFixNeoForge.java:8-11`，Fabric 版实现 `ModInitializer.onInitialize()`）。全部功能靠 mixin 完成，入口类存在的意义是让 `@Mod` / `fabric.mod.json` 有落点。

```java
@Mod(Constants.MOD_ID)
public class MaxHealthFixNeoForge {
    public MaxHealthFixNeoForge() { Constants.LOG.info("Loaded {} for Forge.", Constants.MOD_ID); }
}
```

## 4. 核心系统

1. **延迟重放血量（修 MC-17876）**：原版 `LivingEntity.readAdditionalSaveData` 读 `Health` 时属性/装备还没加载，导致 >20 血被钳回默认值。解法是在 HEAD 处**只捕获不修改**：`MixinLivingEntity.java:32-44` 判断 `savedHealth > getMaxHealth() && savedHealth > 0` 时记到 `@Unique private Float actualHealth`，然后在 `tick()` 的 TAIL（`50-62` 行）再 `setHealth(actualHealth)` 后置 null。关键设计：**不在读的时候改，而是等一 tick 让 Curios/饰品把 maxHealth 加回来再重放**。
2. **`@Unique` 字段当临时暂存区**：用 `Float actualHealth`（可空对象而非 float 原语）区分"没有待恢复数据"与"待恢复为 0"，避免用额外 boolean。mixin 类同时 `implements IHealthFixable`，把注入点和跨 mixin 通信的接口分开定义。
3. **跨 mixin 通信走 duck interface**：`IHealthFixable.java:3-7` 只暴露一个 `maxhealthfix$setRestorePoint(float)`，避免 mixin 之间直接 cast 到具体实现类。
4. **复活时重新布置恢复点**：`MixinPlayerList.java:20-26` 注入 `PlayerList.respawn`，`@At(INVOKE, target = "...ServerPlayer;setHealth(F)V")` + `locals = LocalCapture.CAPTURE_FAILSOFT` 拿到局部变量 `newPlayer`，再把旧玩家的 `getMaxHealth()` 塞进新玩家——解决"死亡复活后血量丢失"（git log `bb67df7` 即此修复）。
5. **mixin priority = 9001**（`MixinLivingEntity.java:16`）：明确让自己**最后**应用，保证能读到其它 mod 处理后的血量。

## 5. 网络 / 数据驱动 / 配置 / datagen

全部**无**：无网络包、无 datapack、无配置文件、无 datagen、无 `src/main/resources` 数据目录。

## 6. Mixin

- 配置：`common/src/main/resources/maxhealthfix.common.mixins.json`（`required:true`、`JAVA_17`、`defaultRequire:1`、`refmap:"${mixin_refmap}"`），NeoForge 经 `mods.toml` 的 `[[mixins]] config = "${mod_id}.common.mixins.json"` 挂载；`forge/.../maxhealthfix.forge.mixins.json` 是空的占位文件
- `MixinLivingEntity` → `LivingEntity.readAdditionalSaveData(CompoundTag)V` @At("HEAD")；`LivingEntity.tick()V` @At("TAIL")
- `MixinPlayerList` → `PlayerList.respawn(ServerPlayer,Z)ServerPlayer` @At(INVOKE, `ServerPlayer.setHealth(F)V`)，LocalCapture

## 7. 值得学的 5 条具体做法

1. **"先捕获、后重放"处理加载顺序 bug**：读档阶段拿到的值先缓存，等一 tick（TAIL of tick）再写回，可绕开所有属性/能力加载时序问题（`MixinLivingEntity.java:32-62`）。适用于任何"存档值被过早钳制"的场景。
2. **用 `@At("TAIL")` + 一次性标志做延迟执行**：`actualHealth = null` 保证只执行一 tick，不需要调度器/队列。
3. **可空包装类型当"无数据"哨兵**：`Float` 而非 `float`，省掉一个 boolean 字段。
4. **`@Unique` + 固定前缀命名（`maxhealthfix$`）**：与 AttributeFix 的 `attributefix$` 一致，是 Darkhax 所有库的统一约定，能避免与其它 mixin 字段撞名。
5. **跨 mixin 用自定义接口而非直接类型转换**：`IHealthFixable` 让 `MixinPlayerList` 无需知道 `MixinLivingEntity` 的存在，两处逻辑解耦（`IHealthFixable.java`）。

## 8. 库 / API 说明

非库模组，无对外 API。可作为"100 行内解决一个 MC 官方 bug"的结构模板：common 放 mixin + 接口，三个平台子项目只放 8-11 行的入口壳，`gradle/` 脚本全项目复用。
