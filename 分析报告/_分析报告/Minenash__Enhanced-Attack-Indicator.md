# Minenash/Enhanced-Attack-Indicator 源码分析报告

## 1. 基本信息

- Mod 名：Enhanced Attack Indicator；mod_id：`enhanced_attack_indicator`；作者：Minenash
- 目标版本：Fabric，Minecraft `1.21.8`，Yarn `1.21.8+build.1`，Fabric Loader `0.16.14`，Java 17（`gradle.properties`）
- Gradle 插件：`fabric-loom 1.10-SNAPSHOT` + `maven-publish`（`build.gradle:1-4`）
- 许可证：MIT（`fabric.mod.json`；本地 checkout 未含 LICENSE 文件，取自 git HEAD）
- 依赖：fabric-api `0.131.0+1.21.8`（硬依赖）、ModMenu `15.0.0-beta.3`（可选，仅在 `gradle.properties` 声明并通过 entrypoint 注册）。环境标记 `"environment": "client"`
- 注意：工作区 checkout 缺少 `fabric.mod.json`/`LICENSE`/`lang` 等文件，需 `git show HEAD:src/main/resources/fabric.mod.json` 读取

## 2. 源码规模与包结构

- `.java` 文件 **5 个，共 599 行**（`find . -name '*.java' -exec wc -l {} +`）
- 包结构（`com.minenash.enhanced_attack_indicator` 下仅 2 个子包）：
  - `config/` 3 文件：`Config.java`(777B)、`MidnightConfig.java`(19.7KB，内嵌配置库)、`ModMenuEntryPoint.java`
  - `mixin/` 1 文件：`InGameHudMixin.java`(2.5KB)
  - 根：`EnhancedAttackIndicator.java`(4.7KB，128 行)
- 最大文件：`config/MidnightConfig.java`（约 500 行，第三方内嵌库，非本 mod 逻辑）

## 3. 入口与注册

主类 `src/main/java/com/minenash/enhanced_attack_indicator/EnhancedAttackIndicator.java:13`，实现 `ClientModInitializer`，`onInitializeClient()` 仅做配置初始化，无 DeferredRegister/注册框架（Fabric 客户端 mod，无内容注册）：

```java
public class EnhancedAttackIndicator implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        Config.init("enhanced_attack_indicator", Config.class);
    }
}
```

`fabric.mod.json` 两个 entrypoint：`client` → 主类；`modmenu` → `config.ModMenuEntryPoint`（`ModMenuApi.getModConfigScreenFactory()` 返回 `Config.getScreen(parent, "enhanced_attack_indicator")`）。

## 4. 核心系统

**a) 准星进度优先级链（核心逻辑，单方法）** `EnhancedAttackIndicator.java:22-117`
- `getProgress(float weaponProgress)` 接收原版武器冷却进度，按配置顺序尝试各来源并返回 `[0,1]` 的进度，或返回哨兵值 `2.0F` 表示"满进度"（由 mixin 画 `CROSSHAIR_ATTACK_INDICATOR_FULL_TEXTURE` 图标）。
- `Config.weaponCoolDownImportance`（`FIRST/MIDDLE/LAST` 枚举）决定武器冷却在链中的位置（`:29`、`:95`、`:112`）。
- 覆盖来源：睡觉计时（`player.getSleepTimer()` 0-100，`:32-36`）、方块破坏（`interactionManager.getBlockBreakingProgress()/10`，`:38-43`）、弓/弩/三叉戟蓄力（`BowItem.getPullProgress`、`CrossbowItem.getPullTime`，`:45-61`）、食物与药水（`DataComponentTypes.FOOD`/`Items.POTION`，`:63-70`）、容器与收纳袋填充度（`DataComponentTypes.CONTAINER`/`BUNDLE_CONTENTS`，`:72-93`）、物品冷却（`player.getItemCooldownManager().getCooldownProgress`，`:98-106`）、已装填弩 `:108-110`。
- `weaponCooldown()` `:119-126` 用 `item.getTranslationKey().contains("pickaxe"/"shovel"/"axe")` 判定工具类型来开关显示。

**b) HUD 注入（mixin 层）** `mixin/InGameHudMixin.java`
- 用 `@Redirect` 拦截 `InGameHud.renderCrosshair` 内对 `ClientPlayerEntity.getAttackCooldownProgress(F)` 的调用，替换为自定义进度（`:24-34`）；`progress == 2.0F` 时翻转 `@Unique boolean renderFullness`。
- 另一个 `@Redirect` 强制 `Entity.isAlive()` 返回 `false`，用于屏蔽原版"+"号满进度图标（`:36-39`）；再在 `@At("TAIL")` 用 `@Inject` 自己画 16x16 满进度贴图（`:42-50`）。
- `renderHotbar` 同样被 `@Redirect`，把 `2.0F` 映射为 `0.99F` 以免热键栏满条（`:52-56`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（纯客户端）。
- 配置：内嵌 **MidnightConfig**（`config/MidnightConfig.java`，反射 + `@Entry` 字段注解，直接声明在 `config/Config.java:7-16`），Gson 序列化到 `config/<modid>.json`，`excludeFieldsWithModifiers(TRANSIENT/PRIVATE)` + 自定义 `HiddenAnnotationExclusionStrategy`（`MidnightConfig.java:72`）。附带 `@Client`/`@Server`/`@Comment` 注解与 `MidnightConfigScreen`（:184-313）。
- datagen：无。

## 6. Mixin

- 配置：`src/main/resources/enhanced_attack_indicator.mixins.json`（`"required": true`，`package: ...mixin`，`compatibilityLevel: JAVA_17`，`client: ["InGameHudMixin"]`，`defaultRequire: 1`）
- 唯一 mixin 类 `InGameHudMixin`，hook 目标均为 `InGameHud.renderCrosshair` / `renderHotbar`，注入手段为 `@Redirect`（INVOKE 级）+ `@Inject(at = TAIL)`。

## 7. 值得学的 5 条具体做法

1. **哨兵值编码"需额外贴图"状态**：进度方法返回 `2.0F` 而非布尔标志，让 mixin 端把 `2.0F` 折叠成 `1.0F`/`0.99F` 再单独画满进度图标（`EnhancedAttackIndicator.java:31,124`），适合需要"同一数值接口表达多态显示"的 HUD 类 mod。
2. **单点 `@Redirect` 替换原版 HUD 数值来源**：拦截 `getAttackCooldownProgress` 一处调用即可驱动准星与热键栏，改动面最小（`InGameHudMixin.java:24,52`）。
3. **可排序的"显示优先级"配置**：把新手关心的冲突（武器冷却 vs 其他进度）抽象成 `FIRST/MIDDLE/LAST` 枚举而不是多个布尔开关（`Config.java:5-7`）。
4. **内嵌轻量配置库 + ModMenu 适配**：`MidnightConfig` 单文件反射配置 + 单独 `ModMenuEntryPoint`，避免为一两个开关引入 ClothConfig 依赖（`config/MidnightConfig.java`、`config/ModMenuEntryPoint.java`）。
5. **`getTranslationKey().contains(...)` 做物品分类兜底**：在不引入标签系统的客户端 mod 里按物品名识别镐/锹/斧（`EnhancedAttackIndicator.java:120-123`）；注意这是脆弱的英文名匹配，正式项目应改用物品标签。

## 8. 公开 API

非库 mod，无对外 API 包。仅 `EnhancedAttackIndicator.getProgress(float)` 为 `public static`，理论上可被其他客户端 mod 调用，但无稳定性承诺。
