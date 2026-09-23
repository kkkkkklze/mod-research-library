# MaidsoulKitchen（Wall-ev）源码分析报告

## 1. 基本信息

- Mod 名：Maidsoul Kitchen；mod_id：`maidsoulkitchen`；作者：`wallev`（group `com.github.wallev`）；版本 `0.3.0.9`（alpha）。
- 目标：Minecraft **1.20.1 + Forge 47.3.0**，Java 17，Parchment `2023.08.20-1.20.1`；许可证 `MIT / CC BY-NC-SA 4.0`（`gradle.properties`）。
- Gradle：`net.minecraftforge.gradle [6.0.16,6.2)`、`org.spongepowered.mixin 0.7.+`、`org.parchmentmc.librarian.forgegradle`、`mod-publish-plugin`、`curseforgegradle`、`gradle-secrets-plugin`（`build.gradle:3-19`）。
- 依赖：**强制** `touhou_little_maid >= 1.3.6`（东方小女仆，提供 `IMaidTask` / `EntityMaid` / `BehaviorControl` 体系）。`gradle.properties` 里逐条固定了约 40 个**可选**联动版本号：`farmersdelight / minersdelight / mynethersdelight / cuisinedelight / youkaishomecoming / brewinandchewin / farm_and_charm / kaleidoscopecookery / kitchenkarrot / vinery / bakery / meadow / tea_aroma / vintagedelight / simplefarming …`，另有 jei / emi / rei / jade / top / patchouli / cloth_config / KubeJS 等。功能定位是"Maid 学会做更多菜 + 兼容各料理 mod 的机器"。

## 2. 源码规模与包结构

- 规模：**657 个 .java、52619 行**。最大包：`util` 25、`client/gui/widget/button` 13、`task/cook/common/rule/cook` 12、`network/packet/c2s` 12、`modclazzchecker/manager` 11、`modclazzchecker/core/classana/clazz` 10、`compat/msm` 共 **175 个文件**。
- 最大文件：`compat/msm/common/util/CraftGuideOperator2.java` 989、`client/gui/entity/maid/cook/CookConfigGuiV1.java` 875、`modclazzchecker/manager/TaskInfo.java` 757、`util/fakeplayer/WrappedMaidFakePlayer.java` 746、`compat/msm/common/util/action/ItemUseStepUtil.java` 744、`task/cook/common/manager/MaidCookManager.java` 655。

## 3. 入口与注册

`src/main/java/com/github/wallev/maidsoulkitchen/MaidsoulKitchen.java:15-39`：

```java
@Mod(MaidsoulKitchen.MOD_ID)
public final class MaidsoulKitchen implements IModInfo {
    public MaidsoulKitchen() { initRegister(); initConfigureRegister(); initDebug(); }
    // ModItems / ModEffects / ModContainers / ModRecipes / ModEntities.MEMORY_MODULE_TYPES
    // + ModLoadingContext.registerConfig(COMMON, GeneralConfig.init())
}
```

全部注册走 `init/*` 的 DeferredRegister；女仆任务注册在 `init/touhoulittlemaid/{TaskRegister,DataRegister}.java`；`CompatRegistry.java` 汇总可选联动；配置分 `GeneralConfig` + `config/subconfig/{RegisterConfig,TaskConfig}`（每个任务一个 enable 开关）。

## 4. 核心系统

1. **任务系统**：`api/task/IMaidsoulKitchenTask.java` 扩展 TLM 的 `IMaidTask`，核心是把任务拆成 AI 行为列表 `List<Pair<Integer, VBehaviorControl>> vCreateBrainTasks(EntityMaid)`；任务用静态表注册 `TaskInfoMap.putTask(uid, canAdd:Supplier<Boolean>, task:Supplier<...>)`（行 20-26）。实际任务在 `task/cook/<mod>/`（furnace / farmersdelight pot / youkaishomecoming kettle …）与 `task/farm/`（berry、fruit、serene seasons）。
2. **注解驱动的兼容求解 + 生成式 mixin 白名单（本项目最有价值的工程点）**：任务枚举 `modclazzchecker/manager/TaskInfo.java` 每一项挂 `@KitchenModule/@FarmModule/@BerryModule/@IgnoreSolver` 与 `@TaskErrorLang(en_us, zh_cn)`；开发期由 `modclazzchecker/manager/gen/TaskCompatExtractor.java` 反射枚举并按模块类型生成 `mod_task_clazz.json`（写入 jar 根，内容为 `taskId → [{taskUid, compatMod, mixinList}]`，同时输出人读的 `src/main/resources/task_compat.txt`）。运行时 `modclazzchecker/manager/TaskMixinManager.java:20-32` 用 `LoadingModList.get().getModFileById(...).getFile().findResource("mod_task_clazz.json")` 读回，`mixinmanager/MixinPlugin.java:29-31` 的 `shouldApplyMixin` 交给 `TaskModClazzMixinManager.canMixin(类名)` 决定是否应用——**兼容 mixin 是否生效由生成数据决定，而不是硬编码 modid 判断**。
3. **类存在性校验（modclazzchecker）**：`core/classana/clazz/{ClassAnalyzerTool,McMethodOrFieldVerify,SignatureConverter,ClassAnalyzerManager}.java` 做目标 mod 的类/方法签名核验，失败时通过 `ReportErrorEvent` + `TaskErrorLang`（中英双语）在游戏内报错并禁用该任务，避免兼容 mod 版本变动导致崩游戏。
4. **msm 自动料理框架（`compat/msm`，175 文件）**：`compat/msm/common/autocraftguide/base/` 定义 `IRecipeGuideGenerator / ICookingGuideGenerator / ICookingRecipeGuideGenerator` 与 `AutoCraftGuideGeneratorRegister`，各机器只需实现"配方→操作步骤"的生成器：`cookingpot/IFdCookingPotGuideGenerator`、`click/ICutterGuideGenerator`、`plate/IPlateGuideGenerator`、`tea/ITeaGuideGenerator`、`water/GeneratorSingleWaterGuide`、`fluidinsert/IFluidInsertRecipeGuideGenerator`、`nbtcustom/INbtCookingGuideGenerator`。执行侧是步骤化工具 `common/util/action/{ItemUseStepUtil,ToolUseStepUtil}.java` 与总控 `CraftGuideOperator2.java`，库存抽象为 `common/inv/{InvHandlerRegister,WorldlyContainerInvHandlerFactory}.java`、`common/storage/`。
5. **女仆数据与 GUI**：`entity/data/inner/task/cook/v1/KitchenData`、`.../berryfruit/v1/BerryFruitData` 存放每个女仆的料理/农场配置；`client/gui/entity/maid/cook/CookConfigGui(V1).java` + `client/gui/widget/button/` 提供配置界面，改动通过 `network/packet/c2s/*` 回传服务端。
6. **假玩家执行**：`util/fakeplayer/WrappedMaidFakePlayer.java`（746 行）把女仆包装成 FakePlayer，用原版交互路径完成"使用物品/操作机器"，绕开逐 mod 手写交互。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkHandler.java:21-60` Forge `SimpleChannel`，版本 `"1.0.0"`，**12 个 PLAY_TO_SERVER + 1 个 PLAY_TO_CLIENT**，包体多为 `(entityId, ResourceLocation dataKey, String mode/rec)` 三元组；对外暴露 `C2S.*` / `S2C.*` 静态方法做类型化门面（`toggleCookBagGuiSideTab`、`syncKitchenData2`、`renderMaidHubZone` 等）。
- 配置：`config/GeneralConfig`（COMMON）+ `subconfig/TaskConfig`、`RegisterConfig`（每个任务/模块一个 enabled 开关，也是任务注册时的 `canAdd` 条件）。
- datagen：`datagen/DataGenerators.java` 输出 blockstate/item model/lang（`ModLanguageProvider` 487 行）/tags/entities；自定义配方 `datagen/recipe/itemuse/ItemUseRecipeBuilder`、`datagen/recipe/water/ConsumeWaterRecipeBuilder` 对应运行时的 `recipe/itemuse`、`recipe/water`（`itemuse/*` 与 `water/*` 配方序列化器注册在 `init/ModRecipes`）。
- 数据驱动：无 datapack registry；"数据"主要是 jar 内生成的 `mod_task_clazz.json` 与 `task_compat.txt`。

## 6. Mixin

- `src/main/resources/maidsoulkitchen.mixins.json`（`required: true`，package `mixin.core`）：`forge.IItemHandlerMixin`、`minecraft.ContainerMixin`、`minecraft.ver.BehaviorControlAccessor`，client 端 `minecraft.AbstractContainerScreenMixin`。
- `maidsoulkitchen-compat.mixins.json`（`required: false`，package `mixin.compat`，`"plugin": "...mixinmanager.MixinPlugin"`）：**18 个条件 mixin**，覆盖 `brewinandchewin.KegBlockEntityMixin`、`cuisinedelight.CookingDataAccessor`、`farmersdelight.CookingPotBlockEntityMixin`、`farmersrespite.KettleBlockEntityMixin`、`kitchkarrot.BrewingBarrelBlockEntityMixin`、`minecraft.AbstractFurnaceBlockEntityMixin`、`minersdelight.CopperPotBlockEntityMixin`、`touhoulittlemaid.EntityMaidMixin`、`youkaishomecoming.BasePotBlockEntityMixin` 等（多为 `@Accessor`）。
- `mixinmanager/legacy/` 是从早期版本沿用的 JSON 配置化 mixin 开发工具（`MixinManagerDev`、`TaskRegisterConfig`、`TaskMixinRegister`）。

## 7. 值得学的 5 条具体做法

1. **用 "modid + 版本区间" 枚举统一管理兼容目标**：`modclazzchecker/manager/Mods.java:9-60` 把 `youkaishomecoming` 的 LEGACY/NEW 写成两条带 range 的枚举项（`YHCD_LEGACY("[2.2.3,2.3.13)")`、`YHCD_NEW("[2.3.13,)")`）——兼容多版本可选依赖时比 `isLoaded` + 版本号硬判断清晰得多。
2. **条件 mixin 白名单数据驱动**：`MixinPlugin.shouldApplyMixin` → `TaskModClazzMixinManager.canMixin`（`mixinmanager/MixinPlugin.java:29-31`）+ `TaskMixinManager` 读 jar 内 `mod_task_clazz.json`——适合"兼容 20+ mod 且每个 mixin 只对特定版本有效"的场景。
3. **开发期注解 → 生成校验数据 → 运行期消费**：`@KitchenModule/@FarmModule` + `@TaskErrorLang` + `gen/TaskCompatExtractor.solver()`，同一份元数据既产出人读 `task_compat.txt` 也产出机器读 JSON，避免重复维护——适合大型兼容矩阵。
4. **配方 → 操作步骤的生成器接口族**：`compat/msm/common/autocraftguide/base/ICookingGuideGenerator` 系列，让每台新机器只实现一个 generator + 一个 InvHandler 注册即可被女仆自动操作（`AutoCraftGuideGeneratorRegister`），AI 执行逻辑完全复用 `ItemUseStepUtil/ToolUseStepUtil`——适合"给 NPC/机械自动执行容器交互"的设计。
5. **FakePlayer 包装实体以复用原版交互**：`util/fakeplayer/WrappedMaidFakePlayer.java`——需要让非玩家实体"使用物品/点方块"时，比逐 mod 手写交互逻辑省事。

## 8. 公开 API 与接入方式

- `com.github.wallev.maidsoulkitchen.api.task`：`IMaidsoulKitchenTask`（含 `TaskInfoMap.putTask` 静态注册与 `TaskMixinMap.putList` 的 mixin 需求声明）、`ICookTask`、`IDataTask`、`farm/ICompatFarmHandler` / `ICompatFarmTask` / `ICompatHandler`（农场兼容 handler 扩展）。
- `api.event/MaidMkTaskEnableEvent.java`：任务启用事件（对外挂钩点）。
- `api/bauble/IMaidsoulKitchenBauble.java`：饰品接入接口。
- 数据接入：`entity/data/inner/task/**` 是女仆数据的序列化层；新增料理机器兼容的推荐路径是"实现 `ICookingGuideGenerator` + `InvHandlerRegister` + 在本 mod 的 `Mods`/`TaskInfo` 里登记"。

（说明：仓库为根目录单工程（`settings.gradle` 无子模块 include），`build.gradle` 中仍有 `if (!project.name.equals("Main"))` 的多模块遗留判断；`libs/` 下为 compileOnly/implementation 分类的本地兼容库。）
