# embeddedt/ModernFix 源码分析报告

> 仓库根：`源码库\_参考仓库\_bulk\embeddedt__ModernFix`（以下文件路径均相对此根）
> 分析对象：ModernFix —— 启动/世界加载/内存优化型性能 mod

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | ModernFix / `modernfix` | `src/main/resources/META-INF/mods.toml:18-19` |
| 作者 | embeddedt | `mods.toml:31` |
| 版本线 | 5.27 | `release_line.txt` |
| MC 版本 / 加载器 | 1.20.1 / `enabled_platforms=forge`，forge `1.20.1-47.4.0` | `gradle.properties` |
| 许可证 | GNU LGPL 3.0（配置系统派生自 Sodium，见 `README.md`） | `mods.toml:12` |
| Gradle 插件 | `net.neoforged.moddev.legacyforge` 2.0.134 + `me.modmuss50.mod-publish-plugin` 2.1.1；Java 17 source/target，toolchain 需 Java 21 | `build.gradle.kts:2-3,68-73`、`CONTRIBUTING.md` |
| 多模块 | root + `annotations`（Java 8，v1.1.0）+ `annotation-processor`（shadow 8.3.9，自动打包 sponge-mixin / fabric-loader / mergetool）+ `buildSrc/GitVersionSource.kt` | `settings.gradle.kts`、`annotation-processor/build.gradle` |
| 编译依赖 | mixinextras-common/forge 0.4.1（`jarJar` 内置）；`modCompileOnly`：JEI、spark、ctm、ldlib、supermartijncore、patchouli、cofh_core、resourcefullib、kubejs、terrablender | `build.gradle.kts:109-137` |

依赖关系要点：ModernFix **没有对外 API 依赖**，它自己就是"寄生式"mod——所有第三方 mod 依赖都只是为了让 compilation 能引用对方类名，从而写针对它们的兼容 mixin。真正的自研基础设施是自己的 `annotations` + `annotation-processor` 两个子模块。本快照只含 Forge 实现（无 `platform/fabric` 目录），Fabric 支持仍在别的分支，运行时靠"classpath 里是否存在 `modernfix-fabric.mixins.json`"判定平台（`src/main/java/org/embeddedt/modernfix/core/config/ModernFixEarlyConfig.java:90`）。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **337**；`find . -name '*.java' -print0 | xargs -0 cat | wc -l` = **20,152 行**。分布：`src/main` 327、`annotations` 6、`annotation-processor` 4、`src/test` 0（无测试）。

按包（第 3 层）文件数：

```
common/mixin     202 (61%!)   util 18   duck 13   core 8   forge/capability 7
dynamicresources 7   world 6   searchtree 6   render 6   resources 4
forge/{recipe,load} 各 4   screen 3   forge/{dynresources,config,classloading} 各 3
platform/, dfu/, blockstate/forge/util/forge/registry/forge/packet/forge/init 各 2
textures/structure/spark/registry/entity/dynamiclanguages/command/chunk/benchmark 各 1
api/{entrypoint,helpers,constants} 各 1
```

mixin 树按功能分五大类（目录名即开关名）：`perf/`（约 60 个子包，最大的是 `dynamic_resources` 11 个）、`bugfix/`（约 20）、`feature/`（约 12）、`core/` 8、`safety/` 4、`devenv/` 2。

最大 10 个文件：
`forge/capability/analysis/CapabilityAnalyzer.java` 712、`core/config/ModernFixEarlyConfig.java` 629、`forge/capability/CapabilityProviderDispatcherGenerator.java` 549、`common/mixin/perf/dynamic_resources/ModelBakeryMixin.java` 412、`resources/ZipPackIndex.java` 393、`core/ModernFixMixinPlugin.java` 328、`forge/dynresources/ModelBakeEventHelper.java` 324、`dynamicresources/DynamicBakedModelProvider.java` 296、`world/gen/ChunkBiomeLookup.java` 266、`screen/OptionList.java` 242。

## 3. 入口与注册

唯一 `@Mod` 类是 `src/main/java/org/embeddedt/modernfix/forge/init/ModernFixForge.java:40-58`（构造器内完成全部注册）：

```java
@Mod(ModernFix.MODID)
public class ModernFixForge {
    public ModernFixForge() {
        commonMod = new ModernFix();
        MinecraftForge.EVENT_BUS.register(this);
        FMLJavaModLoadingContext.get().getModEventBus().addListener(this::commonSetup);
        FMLJavaModLoadingContext.get().getModEventBus().addListener(this::registerItems);
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> MinecraftForge.EVENT_BUS.register(new ModernFixClientForge()));
        ModLoadingContext.get().registerExtensionPoint(IExtensionPoint.DisplayTest.class, () -> new IExtensionPoint.DisplayTest(() -> NetworkConstants.IGNORESERVERONLY, (a, b) -> true));
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, ModernFixConfig.COMMON_CONFIG);
        PacketHandler.register();
        ConfigFixer.replaceConfigHandlers();
        ModFileScanDataCompactor.compact();
    }
```

- **无 DeferredRegister / Registrate**，ModernFix 不注册任何自己的内容。`ModernFixForge.java:72-81` 的 `registerItems` 只在 `-Dmodernfix.largeRegistryTest` 下注册 100 万个物品（注册表压测工具，非功能）。
- 它注册的三样东西：一个 Brigadier 命令（`command/ModernFixCommands.java`，另有 `mfsrc` 调试命令在 `ModernFixForge.java:61-70`）、两个 `SimpleChannel`、一个 `ForgeConfigSpec`。
- 真正的"入口"不是 @Mod 类，而是 **mixin plugin 的构造器**（`core/ModernFixMixinPlugin.java:31-104`）：加载早期配置、拒绝 OptiFine、打 Nashorn/线程数等 JVM 补丁、启动线程 dump。注释原话：`/* We abuse the constructor of a mixin plugin as a safe location to start modifying the classloader */`。

## 4. 核心系统

### 4.1 注解驱动 + 注解处理器生成 mixin 配置（工程化开关，本仓库最大亮点）

职责：**新增一个 mixin 完全不需要手工改 json、不需要注册**。

- 5 个自研注解（`annotations/src/main/java/org/embeddedt/modernfix/annotation/`）：`@ClientOnlyMixin`、`@RequiresMod`（支持 `!modid` 取反，`TYPE`+`PACKAGE` 双目标）、`@RequiresFeatureLevel` + `FeatureLevel{GA,BETA}`、`@IgnoreMixin`（仅供 AP 跳过）、`@IgnoreOutsideDev`。
- `annotation-processor/src/main/java/org/fury_phoenix/mixinAp/annotation/MixinProcessor.java:26-88`：`@SupportedAnnotationTypes({"org.spongepowered.asm.mixin.Mixin","...ClientOnlyMixin"})`，扫描全部 `@Mixin` 类，按"是否带 `@ClientOnlyMixin`"拆成 `mixins` / `client` 两个列表（`filterMixinSets():90-94` 保证互斥），在最后一轮 `processingOver` 时生成 json。
- `annotation-processor/src/main/java/org/fury_phoenix/mixinAp/config/MixinConfig.java:14-64`：把 config 序列化成 record（`required=true`、`minVersion=0.8`、`plugin=ModernFixMixinPlugin`、`compatibilityLevel=JAVA_17`、`defaultRequire=1`、`conformVisibility=true`），用 Gson 写到 `SOURCE_OUTPUT/resources/<rootProject.name>-<project.name>.mixins.json`（`:58-64`）；`build.gradle.kts:54-56` 的 `mixin { config(...) }` 与 `build.gradle.kts:176-180` 的 `sourceSets.main.resources.srcDir("build/generated/sources/annotationProcessor/java/main/resources")` 把它接进产物（AP 所需参数 `-ArootProject.name` / `-Aproject.name` 在 `:164-174` 传入，`checkDanglingMixinPackageInfo` 任务在 `:139-161`）。
  → 因此 **git 里没有 mixins.json**，`src/main/resources` 只有 `META-INF/mods.toml` 和 `accesstransformer.cfg` 两个文件。

### 4.2 编译期客户端混入校验（把运行期崩溃前移）

- `annotation-processor/.../annotation/ClientMixinValidator.java:44-120`：用 AP 的 `Elements`/`Types` 读 `@Mixin` 的 `value`/`targets`，检查目标类是否带 `@OnlyIn(CLIENT)`；同时兼容 **Fabric `@Environment`、Forge `@OnlyIn`、NeoForge `@OnlyIn` 三种 marker**（`markers` 表 + `TypedAccessorMap`）。
- 命中即由 `MixinProcessor.java:107-110` 报 **编译错误** `"Mixin X targets client-side classes: Y"`，提示作者加 `@ClientOnlyMixin`。这是"服务端启动就崩"→"编译不过"的左移手段。

### 4.3 运行时开关体系：目录即选项，父包继承

- 单文件配置 `config/modernfix-mixins.properties`，在 mixin plugin 构造器里最早加载（`ModernFixEarlyConfig.java:499-525`）。
- 选项**不手写**：读生成出来的 mixins.json → 逐个 `ClassReader#accept(SKIP_CODE)` 扫 mixin 类的字节码注解 → 用"去掉类名后的包路径"作为选项名，例如 `mixin.perf.dynamic_resources`（`ModernFixEarlyConfig.java:135-229`）。
- 层级继承：`Option.parent` + `getEffectiveOptionForMixin():470-493` 沿包路径逐段查找，"父包关 → 全部子项关"，子包显式开启可覆盖。
- 4 层覆盖优先级（低→高）：`DEFAULT_SETTING_OVERRIDES`（`:247-276`，默认关闭的项集中列在这里，如 `mixin.perf.dynamic_resources=false`）< mod 兼容声明（`disableIfModPresent("mixin.bugfix.chunk_deadlock","c2me","dimthread")`，`:305-332`）< 全局 `global/modernfix-global-mixins.properties` < 用户 properties。关键规则：**用户不能覆盖已被 mod 关闭的项**，除非 `-Dmodernfix.unsupported.allowOverriding=true`（`:43,451-458`）。
- 另有 `stability_level=GA|BETA` 内置选项：`@RequiresFeatureLevel` 高于当前级别会被记入 `mixinsMissingMods` 并打印原因（`:530-537`）；加载完成时逐条 warn 报告"哪个选项被谁覆盖成什么"（`ModernFixMixinPlugin.java:51-65`）。

### 4.4 shouldApplyMixin 单点总控

`core/ModernFixMixinPlugin.java:130-167`：前缀校验（不属于 `org.embeddedt.modernfix.mixin.` 直接拒绝）→ `ModernFixEarlyConfig.sanitize()` 去掉 `common.|forge.|fabric.` 段（`:72-76`）→ 查配置决定加不加。**一个 mixin 是否生效，取决于配置扫描结果，而不是代码里写没写**；同一处把"未知 mixin"降级为 debug 日志（dev 环境才报 error）。

### 4.5 动态注入 / postApply 二次字节码分析

`core/ModernFixMixinPlugin.java:204-327`（`applyBlockStateCacheScan`）：对 `BlockStateBase` 的目标类做全类扫描——

1. 从方法上的 `@MixinMerged` 注解找出所有"由外部 mixin 注入进来的方法"，并记下来源 mixin 名；
2. 在 `initCache`（多套映射名 `m_60611_`/`func_215692_c`/`method_26200`/`initCache`）里找出它调用了哪些注入方法，并**递归**收集调用链；
3. 收集这些方法里 `PUTFIELD` 写入的字段；
4. 反向给"读取这些字段的其他注入方法"在方法头插入 `this.mfix$generateCache()`（`:317-325`）。

即：**让第三方 mod 注入的代码也自动吃到 ModernFix 的 blockstate 缓存修复**，无需对方配合。
另有更底层的入口 `core/launchplugin/CoreLaunchPluginService.java:19-36`：在 mixin plugin 里用反射把自定义 `ILaunchPluginService` 塞进 ModLauncher 的 `LaunchPluginHandler.plugins`，在类加载期直接改写 `net.minecraftforge.common.capabilities.CapabilityProvider`。

### 4.6 加载器差异抽象 + 平台工具

- `platform/ModernFixPlatformHooks.java`：15 个方法的接口（`isClient`/`isDedicatedServer`/`modPresent`/`isDevEnv`/`isEarlyLoadingNormally`/`getCustomModOptions`/`applyASMTransformers`/`registerCreativeSearchTrees`…），`platform/PlatformHookLoader.java:7-21` 用反射按名尝试 `platform.forge`→`platform.fabric` 的实现类，全部失败则 `Runtime.exit(1)`。平台差异 100% 收敛进 `platform/forge/ModernFixPlatformHooksImpl.java`（194 行）。
- `forge/load/`、`forge/classloading/` 是启动期硬骨头：`ModFileScanDataCompactor`（反射瘦身扫描数据）、`ModResourcePackPathFixer`（Path→IModFile 的 IdentityHashMap 反查）、`ModWorkManagerQueue`（自写队列绕开 Forge WorkManager 的 park 行为）、`ATInjector` + `FastAccessTransformerList extends AccessTransformerList`（自实现 `containsClassTarget`/`FastATMap`）、`ManifestCompactor`。
- 诊断/度量手段：`spark/SparkLaunchProfiler.java:49-58,60-87`（内置 spark 采样器，分阶段 start/stop，可上传 bytebin 或落盘）、CI 跑 `mixin audit`（`.github/workflows/gradle.yml:49` + `ModernFix.java:50-60` 的 `auditAndExit`）、`world/ThreadDumper.java` + `world/IntegratedWatchdog.java`（卡死/死锁诊断）、`benchmark/WorldgenBenchmark.java`（可复现的区块生成基准）、`.claude/skills/rca-issue/SKILL.md`（把 issue 根因排查流程固化成 agent 技能）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`forge/packet/PacketHandler.java:10-35`。两个 `SimpleChannel`：`main` 与 `ingredient_sync`（后者仅当 `perf.smart_ingredient_sync.Channel` 开启时创建，否则为 `null`）；版本号字符串 `"1"`，收发都用 `NetworkRegistry.acceptMissingOr(version)`（允许对端没装）。注册方法 `register()` 是空的（Forge 1.20.1 的 `SimpleChannel` 无需注册消息）。发送侧抽象成 `PlatformHooks.sendPacket(ServerPlayer, Object)`。
- **配置**：两套并存——① `core/config/ModernFixEarlyConfig`（mixin 开关，properties，可被 JVM 属性 `-Dmodernfix.config.<key>=` 覆盖，见 `:396-408`）；② 标准 `ForgeConfigSpec`（`forge/ModernFixConfig.java`，目前只有 `blacklist_async_jei_plugins` 一个键，用于 JEI 插件黑名单）。GUI 侧 `screen/ModernFixConfigScreen` + `OptionList`（242 行）+ `ModernFixOptionInfoScreen`。分类文件 `/modernfix/option_categories.json` 由 `OptionCategories.java:18-38` 读取（**本快照中该资源不存在**，读取失败会回落成单一 `default` 分类，`未确认`是漏提交还是位于其它分支）。
- **数据驱动**：无 datapack 数据、无资源生成，`src/main/resources` 仅 2 个文件。唯一的"数据驱动"是 `mods.toml` 里其它 mod 声明的 `modernfix:integration` 自定义键（见第 8 节）。
- **datagen**：无。

## 6. Mixin

- 配置：构建期生成的 `modernfix-modernfix.mixins.json`（AP 产出，见 4.1），插件 `org.embeddedt.modernfix.core.ModernFixMixinPlugin`，`compatibilityLevel=JAVA_17`、`defaultRequire=1`、`conformVisibility=true`（`MixinConfig.java:27-36`）；refmap 名 `modernfix.refmap.json`（`ModernFixMixinPlugin.java:126`）。
- 规模：**202 个 mixin 类**（占全部 java 的 61%），其中 73 个标 `@ClientOnlyMixin`，约 20 个包/类带 `@RequiresMod`。
- 目标未混淆名靠 `accesstransformer.cfg`（75 行，含 `f_111415_` 等 SRG 字段）开放。
- 代表性 mixin 与注入点：
  - `common/mixin/perf/dynamic_resources/BlockStateBaseMixin.java:16-26` — duck-interface 范式：`@Mixin(BlockBehaviour.BlockStateBase.class) @ClientOnlyMixin class ... implements IModelHoldingBlockState`，用 `mfix$` 前缀字段/方法避免与其它 mod 撞名（`duck/` 包 13 个接口全部是这种被 mixin 实现的注入接口）。
  - `common/mixin/perf/faster_capabilities/CapabilityDispatcherMixin.java:22-44` — `@Inject(method="<init>...", at=@At("RETURN"))` 里生成 dispatcher + `@Overwrite(remap=false) getCapability` 换成 ASM 动态生成的隐藏类（配合 `forge/capability/CapabilityProviderDispatcherGenerator.java` 与 `analysis/CapabilityAnalyzer.java`）。
  - `common/mixin/perf/chunk_meshing/RebuildTaskMixin.java:22-31` — `@Redirect(method="compile", at=@At("INVOKE", target=...BlockPos;betweenClosed...), require = 0)`，用 `require=0` 容忍目标版本漂移。
  - `common/mixin/safety/BlockColorsMixin.java:13-22` — `@Mixin(value=BlockColors.class, priority=700)` 在 `register` 的 `HEAD`/`TAIL` 加锁，防第三方 mod 并发写 Map 导致 CME（`safety/` 4 个类都是这类"给别人的 bug 兜底"）。
  - `common/mixin/perf/optimize_surface_rules/NamespacedSurfaceRuleSourceMixin.java:28` — `@RequiresMod("terrablender")`，仅当 TerraBlender 存在才对它生效。
  - 注入风格偏好 MixinExtras：`@WrapOperation` / `@ModifyExpressionValue` / `@WrapMethod`（`AttachCapabilitiesEventMixin.java:35-38` 记录 cap 注册阶段、`ForgeEventFactoryMixin.java:14` 在事件 post 后重排 cap）而非 `@Redirect`。
- 每个 mixin 包一层 `package-info.java` 承载包级约束（如 `perf/faster_capabilities/bytecode_analysis/package-info.java` 的 `@RequiresFeatureLevel(FeatureLevel.BETA)`，运行时被 4.3 的扫描读取），并由 `build.gradle.kts:139-161` 的 `checkDanglingMixinPackageInfo` 任务禁止出现"没有兄弟类的空 package-info"，防止配置项凭空出现。

## 7. 值得学的 5 条具体做法

1. **用注解处理器生成 mixin 配置**：只写 `@Mixin` 类，json 由 AP 在编译期拼装（`annotation-processor/.../MixinProcessor.java:45-88` + `config/MixinConfig.java:38-64`）。适用：mixin 数量多（本例 202 个）、跨版本分支维护、不想手改 json 的 mod。
2. **编译期校验 mixin 目标的客户端标记**：用 AP 兼容三种 `@OnlyIn`/`@Environment` marker，目标不对就编译报错（`ClientMixinValidator.java:78-120`）。适用：双端 mod、有客户端专用 mixin 的项目。
3. **把"文件目录"变成"功能开关"**：目录名即配置键，运行时扫字节码自动生成选项树，父包关闭继承到子包（`ModernFixEarlyConfig.java:135-229,470-493`）。适用：带几十个可独立关闭补丁的性能/兼容 mod。
4. **覆盖优先级分层 + 明确报告来源**：默认值 < 注解约束 < mod 兼容 < 用户；禁止用户覆盖 mod 覆盖，并在启动时逐条打印"X 被 Y 覆盖为 Z"（`ModernFixEarlyConfig.java:247-276,436-460`；`ModernFixMixinPlugin.java:51-65`）。适用：兼容性矩阵大的 mod，能大幅减少"我明明关了还生效"的issue。
5. **在 `postApply` 里做二次字节码分析，把优化扩散到别人的注入代码**：扫 `@MixinMerged` 找外部注入方法 → 递归找字段写入 → 反向插入自己的缓存钩子（`ModernFixMixinPlugin.java:204-327`）。适用：需要与未知第三方 mixin 共存的性能 mod。

补充（低成本高收益）：CI 里跑 `mixin audit` 并 `-Dmodernfix.auditAndExit=true`（`gradle.yml:49`、`ModernFix.java:50-60`）；内置 spark 采样做分阶段启动 profiling（`spark/SparkLaunchProfiler.java:44-79`）。

## 8. 公开 API（面向其它 mod 的接入点）

- 包：`org.embeddedt.modernfix.api`（`entrypoint` / `helpers` / `constants` 三个子包）。
- 扩展点接口：`api/entrypoint/ModernFixClientIntegration.java` —— `onDynamicResourcesStatusChange(boolean)`、`onUnbakedModelLoad(...)`、`onUnbakedModelPreBake(...)`、`onBakedModelLoad(...)`（全部 `default`，按需重写）。
- 接入方式：在自己 mod 的 metadata 里填入 `modernfix:integration` 键，`api/constants/IntegrationConstants.java` 约定子键名 `entrypoint` / `client_entrypoint`；ModernFix 在 `ModernFixClient.java:61-66` 用 `getCustomModOptions().get("client_entrypoint")` 反射 `Class.forName(...).getDeclaredConstructor().newInstance()` 实例化（Forge 侧读法见 `platform/forge/ModernFixPlatformHooksImpl.java:141-146`）。
- 辅助 API：`api/helpers/ModelHelpers.java` —— `getBlockStateForLocation(...)`、`createFakeTopLevelMap(modelGetter)`（返回 `DynamicMap` 伪装成 map）、`adaptBakery(ModelBakery)`。
- 另一个扩展点：`searchtree/SearchTreeProviderRegistry.Provider`（`getSearchTree`/`canUse`/`getName`），JEI 后端搜索树即通过它注册（`ModernFixClient.java:59`）。
- 命名约定：所有注入到原版类型的成员一律 `mfix$` 前缀（`duck/*.java` 13 个接口可见），是其与其它 mixin mod 共存的关键约定。
