# Theoness1/EatingAnimation 源码分析报告

## 1. 基本信息

- Mod 名：Eating Animation / mod_id：`eatinganimationid` / 作者：theone_ss、spusik_、PinkGoosik、DoctorNight1
- 目标：MC 1.21，**Fabric 专用且纯客户端**（`fabric.mod.json: environment = "client"`）；yarn 1.21+build.2、fabric_loader 0.15.11、fabric-api 0.100.1+1.21，Java 21
- 版本：mod_version 1.9.72，发布版本号 = `minecraft_version + "+" + mod_version`（`build.gradle`）
- 构建：`fabric-loom` 1.6-SNAPSHOT + `io.github.juuxel.loom-quiltflower` 1.8.0；`processResources` 对 fabric.mod.json 做 `${version}` 展开
- 许可证：MIT（LICENSE，Copyright 2024 theone_ss）
- 依赖 = 只有 fabric-loader + fabric-api，无任何其他 mod API
- 快照说明：git 跟踪 2228 文件（绝大部分是贴图与模型），本地工作区只检出 4 个 java + 构建脚本 + 少量资源；`fabric.mod.json` 需用 `git show HEAD:` 读取

## 2. 源码规模与包结构

- **4 个 `.java`，212 行**（实测命令输出）：`ru/tpsd/eatinganimationmod/` 下 `EatingAnimationClientMod`(58)、`DrinkingAnimationClientMod`(34)，`mixin/` 下 `DrawContextMixin`(42)、`DrawContextLegacyMixin`(78)
- 资源侧才是主体：`assets/minecraft/models/item/*.json`（原版物品 override + `*_eating_0..2` 模型）、`assets/eatinganimationid/**`（自身贴图）、`resourcepacks/supporteatinganimation/**`（内置资源包，覆盖 17 个命名空间：additionaladditions、adorn、betterend、betternether、botania、create、duckling、expandeddelight、farmersdelight、foodplusid、hybrid-aquatic、naturalist、snowpig、the_bumblezone、winterly 等）

## 3. 入口与注册

`fabric.mod.json` 的 `entrypoints.client` 同时挂两个 `ClientModInitializer`：`EatingAnimationClientMod`、`DrinkingAnimationClientMod`。没有任何游戏对象注册，初始化只做两件事——**批量注册物品模型谓词**（`EatingAnimationClientMod.java:19-50`）：

```java
private static final ArrayList<Item> FOOD_ITEMS = new ArrayList<>(Registries.ITEM.stream().filter(
        p -> p.getDefaultStack().getComponents().contains(DataComponentTypes.FOOD)).toList());
static { FOOD_ITEMS.add(Items.MILK_BUCKET); }
...
ModelPredicateProviderRegistry.register(item, Identifier.of("eat"), (stack, world, entity, i) -> {...});
ModelPredicateProviderRegistry.register(item, Identifier.of("eating"), (stack, world, entity, i) ->
        entity.isUsingItem() && entity.getActiveItem() == stack ? 1.0F : 0.0F);
```

`onInitializeClient` 末尾用 `ResourceManagerHelper.registerBuiltinResourcePack(locate("supporteatinganimation"), modContainer, ResourcePackActivationType.DEFAULT_ENABLED)` 注册内置资源包；`locate()` 用的是 `Identifier.ofVanilla(path)`（复用 vanilla 命名空间，`EatingAnimationClientMod.java:55-58`）。

## 4. 核心系统

1. **模型谓词求值：本地玩家与远端玩家两套公式**（本 mod 的灵魂，`EatingAnimationClientMod.java:28-41`）：远端（`OtherClientPlayerEntity`，同步只有 useTime/maxUseTime）——`maxUseTime > 16` 时 `(getItemUseTime()/getMaxUseTime()) % 1`，否则 `(getItemUseTime()/32f) % 0.5F`；本地玩家用 `(getMaxUseTime(e) - getItemUseTimeLeft())/30.0F`。`eating` 谓词则为 `isUsingItem() && getActiveItem()==stack ? 1 : 0`，作为 override 的开关条件。
2. **纯 JSON 三帧动画**：`assets/minecraft/models/item/<food>.json` 在原版模型上加 `overrides`，`{"predicate": {"eating": 1, "eat": 0.35/0.70/0.90}, "model": "item/<food>_eating_0..2"}`（实测 apple.json）。零代码扩展新食物，只要给贴图 + 模型 JSON。
3. **内置第三方支持资源包**：`resourcepacks/supporteatinganimation`（含 `pack.mcmeta`/`pack.png`）默认启用，为 create/botania/farmersdelight 等 17 个命名空间提供同构 override 与贴图；第三方 mod 也可以只加自己的 JSON。
4. **GUI/物品栏渲染兼容**：`mixin/DrawContextMixin.java` 用 `@ModifyVariable` + `@At(value="INVOKE_ASSIGN", target="...ItemRenderer;getModel(...)")` 拦截返回值，对「含 `DataComponentTypes.FOOD` 且无 `CUSTOM_MODEL_DATA`」的堆栈改走 `client.getItemRenderer().getModels().getModel(stack)`；`mixin/DrawContextLegacyMixin.java` 是另一套整段重绘方案（`@Inject(HEAD, cancellable)` 自己 push 矩阵 + `renderItem(GUI)` + `draw()`），当前 `eatinganimation.mixins.json` 未启用它。
5. **饮品谓词**：`DrinkingAnimationClientMod.java:12-33` 只对 `Items.POTION` 注册 `drink`/`drinking`，进度同用 `(maxUseTime - getItemUseTimeLeft())/30`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端 + 模型谓词，服务端零改动）
- 数据驱动：**全部玩法由数据构成**——模型 override JSON（predicate 阈值 0.35/0.70/0.90）+ 贴图 + 内置资源包；代码只用 DataComponent 判断物品是否为食物
- 配置：**无**（无 config 入口）；datagen：**无**（无 loom datagen）

## 6. Mixin

- 配置：`src/main/resources/eatinganimation.mixins.json` → `package: ru.tpsd.eatinganimationmod.mixin`，`compatibilityLevel: JAVA_21`，**仅 `client` 段**：`["DrawContextMixin"]`，`injectors.defaultRequire = 1`（`server: []`，`DrawContextLegacyMixin` 已写好但未登记）
- 代表性 hook：`@Mixin(DrawContext.class)`，`@ModifyVariable(method = "drawItem(Lnet/minecraft/entity/LivingEntity;Lnet/minecraft/world/World;Lnet/minecraft/item/ItemStack;IIII)V", at = @At(value = "INVOKE_ASSIGN", target = "Lnet/minecraft/client/render/item/ItemRenderer;getModel(...)Lnet/minecraft/client/render/model/BakedModel;"))`（`DrawContextMixin.java:18-30`）

## 7. 值得学的 5 条具体做法

1. 「零注册表」的功能 mod：用 `Registries.ITEM.stream()` 在客户端 init 时筛出所有带 `DataComponentTypes.FOOD` 的物品批量注册 `ModelPredicateProviderRegistry` 谓词（`EatingAnimationClientMod.java:19-27`），无需维护物品清单，也不碰服务端。
2. 远/近端 GUI 状态可分：远端实体只能拿到 useTime，本地可拿 `getItemUseTimeLeft()`，用条件（`maxUseTime > 16`、`% 1` vs `% 0.5F`）规避不同使用时长物品的动画错位（同上 `:32-40`）。
3. 用 `@ModifyVariable` + `INVOKE_ASSIGN` 替换 `getModel` 返回值，而不是重写整个 `drawItem`（`DrawContextMixin.java:23-30`），兼容面比 `DrawContextLegacyMixin` 的 HEAD/取消式重绘更小。
4. 第三方支持用「内置资源包 + `ResourcePackActivationType.DEFAULT_ENABLED`」分发，而不是硬编码 mixin/注册（`EatingAnimationClientMod.java:51-52`）——玩家可关闭，且能随资源包更新。
5. 所有数值交给 JSON：`predicate.eat` 阈值 + `eating` 开关 + `*_eating_N` 模型，改动画不需要重新编译（`assets/minecraft/models/item/*.json`）。

## 8. 公开扩展点（非库模组，但存在事实接口）

- **模型谓词契约**：`eat`（0..1 进度）、`eating`（0/1 使用中）、`drink`/`drinking`（对 `Items.POTION`）——第三方只要在自己命名空间的物品模型里加同名 `predicate` 的 overrides 即可接入，无需依赖本 mod 代码
- **资源包贡献路径**：`resourcepacks/supporteatinganimation/` 是"为一个 mod 预置资源"的模板；本 mod 不含任何 Java API 或 Fabric API 事件，纯客户端渲染层扩展
