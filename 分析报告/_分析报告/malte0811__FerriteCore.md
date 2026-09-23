# malte0811/FerriteCore 源码分析报告

## 1. 基本信息

- Mod 名 FerriteCore，`mod_id = ferritecore`，作者 malte0811，版本 7.0.3（`gradle.properties`）；许可证 MIT（`Fabric/src/main/templates/fabric.mod.json`、`NeoForge/src/main/templates/META-INF/neoforge.mods.toml`）。
- 目标版本：`minecraft_version=1.21.1`（`next_major_mc=1.22`）、`neo_version=21.1.218`、`fabric_loader_version=0.18.4`、Parchment `2024.11.17`、NeoForm `1.21.1-20240808.144430`。
- Gradle：根 `build.gradle` 只声明 `net.neoforged.moddev`(ModDevGradle) 2.0.139、`fabric-loom` 1.5-SNAPSHOT、`me.modmuss50.mod-publish-plugin` 0.7.4；`buildSrc/src/main/groovy/ferritecore.subproject-conventions.gradle` 统一 Java 21 toolchain，`ferritecore.loader-conventions.gradle` 负责 jar manifest、签名、模板展开（`src/main/templates` → mods.toml/fabric.mod.json）与 CurseForge/Modrinth 发布。
- 编译依赖：Common `compileOnly org.spongepowered:mixin:0.8.5`、`asm-tree 9.3`、JUnit5；Fabric 仅 `fabric-loader`。**不依赖 Cloth Config 等任何配置 UI 库**，配置自研（见第 5 节）。
- 3 个模块：`Common`（全部逻辑+Mixin）、`Fabric`、`NeoForge`；`Fabric` 的 `build.gradle:23` 用 `compileJava.doFirst { System.clearProperty("mixin.target.mapid") }` 处理多子项目 Mixin AP 冲突。

## 2. 源码规模与包结构

69 个 `.java`、3789 行（`find -name '*.java' | wc -l` / `cat | wc -l`，含 4 个测试类，总量极小但全是"针尖"级优化）。包分布（Common 为主）：`mixin/accessors` 7、`impl` 6、`hash` 5、`fastmap` 5、`mixin/predicates` 4、`fastmap/table` 3、`ducks` 3、`mixin/{blockstatecache,dedupmultipart,config}` 各 3、`util` 3、`mixin/{fastmap,mrl,modelsides,threaddetec,dedupbakedquad,datacomponents}` 各 2、`/test` 4。
最大文件：`fastmap/table/FastmapNeighborTable.java` 217、`fastmap/PropertyIndexer.java` 208、`mixin/config/FerriteConfig.java` 176、`impl/BlockStateCacheImpl.java` 169、`util/SmallThreadingDetector.java` 168、`fastmap/FastMap.java` 166。

## 3. 入口与注册

无任何注册内容（无 DeferredRegister、无物品/方块）。`NeoForge/src/main/java/malte0811/ferritecore/ModMainForge.java` 的 `@Mod(Constants.MODID)` 类体为空；客户端初始化在 `ModClientForge.java`：`@EventBusSubscriber(value = Dist.CLIENT, modid = ...)` + `RenderLevelStageEvent.RegisterStageEvent` → `Deduplicator.registerReloadListener()`。Fabric 侧用 `Fabric/.../mixin/fabric/MinecraftMixin.java:13-21` 注入 `Minecraft.<init>` 中 `ItemRenderer` 构造调用点来注册重载监听。
平台差异不用 Architectury，而是**反射加载同名类**：`Common/.../util/Constants.java:11-17` 中 `Class.forName("malte0811.ferritecore.PlatformHooks")`，`mixin/config/IPlatformConfigHooks.java:8-15` 同理加载 `malte0811.ferritecore.mixin.platform.ConfigFileHandler`。

## 4. 核心系统

1. **FastMap 邻居表（最大收益项）**：`fastmap/FastMap.java` 用一维 `List<Value> valueMatrix` + `List<FastMapKey<?>> keys` 模拟多维数组，`with(oldIndex, prop, value)`（:72-85）以整数下标运算取代 vanilla 的 Guava `Table` 查表（每个 state 一张表 → 每方块一张表，600MB→7MB）。`fastmap/PropertyIndexer.java` 为 `BooleanProperty/IntegerProperty/EnumProperty` 及 `Direction` 提供特化实现（`IntIndexer.toIndex = i - min`），其余走 `GenericIndexer`，并用 `isValid()` 逐值自检后回退。
2. **StateHolder 改造**：`mixin/fastmap/FastMapStateHolderMixin.java` 以 `@Redirect` 替换 `setValue/trySetValue` 里的 `Table.get`（:29-43），`@Overwrite populateNeighbours`（:50-53）转交 `impl/StateHolderImpl.populateNeighbors`；后者用 `ThreadLocal LAST_STATE_MAP/LAST_FAST_STATE_MAP` 让同一 `StateDefinition` 的所有 state 共享一个 FastMap（:34-44），并在关闭邻居表时挂 `CrashNeighborTable.getInstance()`（会主动抛异常并说明原因，用于暴露第三方直接访问）。
3. **去重器**：`impl/Deduplicator.java` 维护 5 张静态缓存（`VARIANT_IDENTITIES`、`KNOWN_MULTIPART_MODELS`、`OR/AND_PREDICATE_CACHE`、`BAKED_QUAD_CACHE`），注册 `SimplePreparableReloadListener<Unit>` 在资源重载时清空；quad 顶点用 `ObjectOpenCustomHashSet` + 自定义 `LambdaBasedHash`（`hash/LambdaBasedHash.java`），注释说明 `Arrays.hashCode` 碰撞导致过性能回退（:83-94）。
4. **BlockState 缓存去重**：`impl/BlockStateCacheImpl.java` 用 `MethodHandle`+反射读 vanilla 私有 `cache` 字段（:37-49，理由："Mixin 处理私有内部类不好"），`deduplicateCachePost` 先用 `ThreadLocal LAST_CACHE` 比旧缓存，再查全局 `CACHE_COLLIDE/CACHE_PROJECT/CACHE_FACE_STURDY`，最后 `replaceInternals` 把第三方已持有的 shape 内部数组替换为规范实例。
5. **Mixin 工程化（本仓库最值得学）**：每个功能子包 = 一个 `ferritecore.<feature>.mixin.json` + 包内 `Config extends FerriteMixinConfig`，json 里以 `"plugin": "malte0811.ferritecore.mixin.<feature>.Config"` 挂载；`mixin/config/FerriteMixinConfig.java:45-61` 的 `shouldApplyMixin` 先读 `FerriteConfig.Option` 开关，再按 `LithiumSupportState` 自动退让（`HAS_LITHIUM` 用 `MixinService.getService().getBytecodeProvider().getClassNode(name)` 探测、不加载类，:132-140）；`postApply` 中直接用 ASM 改字节码（:87-115，把 `values` 字段类型 `Reference2ObjectArrayMap` 改成 `Reference2ObjectMap` 并同步 FieldInsn/INVOKEVIRTUAL/CHECKCAST）。子配置类极短，例如 `mixin/fastmap/Config.java` 只有 `super(FerriteConfig.NEIGHBOR_LOOKUP)`。
6. **配置系统**：`mixin/config/FerriteConfig.java` 用 `Option` 表达依赖（`PREDICATES` 依赖 `NEIGHBOR_LOOKUP`，启用依赖未启用时 `throw new IllegalStateException`，:145-158）；平台实现读文件：Fabric 手写 `config/ferritecore.mixin.properties`（保留每条注释，`Fabric/.../ConfigFileHandler.java:44-56`），NeoForge 用 nightconfig `ConfigSpec.correct()` 写 `config/ferritecore-mixin.toml`（`NeoForge/.../ConfigFileHandler.java:22-38`）；两者都实现 `collectDisabledOverrides`，允许**其他 mod 通过元数据 `ferritecore:disabled_options` 关闭指定选项**。

## 5. 网络 / 数据驱动 / 配置 / datagen

无网络代码（无 payload/网络注册），无 datagen，无数据包内容（`Common/src/main/resources` 只有 10 个 mixin json + `logo.png`）。配置原因见第 4 节 6：FerriteCore 需要在 Mixin 加载期（早于普通 mod 加载、早于任何配置界面可用）就读到开关，所以刻意不用内存型配置库，只用 `Properties`/TOML。NeoForge 侧另有 `NeoForge/src/main/resources/roadrunner.overrides.properties`（内容 `mixin.alloc.blockstate = false`，供 RoadRunner 兼容开关）。测试资源不打包。

## 6. Mixin

- 配置文件：10 个 `Common/src/main/resources/ferritecore.*.mixin.json`（accessors / blockstatecache / datacomponents / dedupbakedquad / dedupmultipart / fastmap / modelsides / mrl / predicates / threaddetec）+ `Fabric/src/main/resources/ferritecore.fabric.mixin.json`，分别登记在 `fabric.mod.json` 的 `mixins` 数组与 `neoforge.mods.toml` 的 `[[mixins]] config=`；`refmap` 用 `${refmap_target}` 占位符由构建期 `expand` 填充。
- 代表性 hook：`FastMapStateHolderMixin` → `@Redirect Table.get`（`setValue`/`trySetValue`）、`@Overwrite populateNeighbours`；`KeyValueConditionMixin`/`AndConditionMixin`/`OrConditionMixin` → `priority = 2000` + `@Overwrite getPredicate`；`ModelResourceLocationMixin` → `@Inject(method="<init>(Lnet/minecraft/resources/ResourceLocation;Ljava/lang/String;)V", at=@At("TAIL"))`；`BlockStateBaseMixin` → `@Inject(method="initCache", HEAD/TAIL)`；`BlockStateCacheMixin` → `@Mixin(targets="net.minecraft.world.level.block.state.BlockBehaviour$BlockStateBase$Cache")`；`MixinMultipartBuilder` → `@Redirect NEW MultiPartBakedModel`；`MixinMultipartModel` → `priority=1100` + `@Redirect Map.get/put`；`PalettedContainerMixin` → 三个构造 `@Inject TAIL` 置空 `threadingDetector` + `@Overwrite acquire/release`；`PatchedDataComponentMapMixin` → `@Inject(method={"set","remove"}, at=@At("RETURN"))` 空 map 换单例；`mixin/accessors/*` 7 个 `@Accessor/@Invoker` 接口（`VoxelShapeAccess`、`BakedQuadAccess` 等）。

## 7. 值得学的 5 条具体做法

1. **配置开关 + Mixin 插件按需加载**：mixin json 声明 `plugin`，插件 `shouldApplyMixin` 读配置返回 false，实现"功能可关、冲突可让" —— `Common/.../mixin/config/FerriteMixinConfig.java:45-61`；适用：任何想给用户/其他 mod 留后门的高风险 Mixin。
2. **用 `MixinService.getBytecodeProvider().getClassNode` 无加载探测其他 mod**：静态块里判 `HAS_LITHIUM` 自动禁用冲突 Mixin —— 同文件 :21-25, :132-140；适用：与已知优化 mod 的兼容处理。
3. **一个功能一个 mixin json + 包内 `Config` 类**：`ferritecore.fastmap.mixin.json` ↔ `mixin/fastmap/Config.java`，IDE 中功能边界清晰 —— `Common/src/main/resources/*.mixin.json`；适用：Mixin 数量 >5 的工程化组织。
4. **`@Overwrite` 时必须在 javadoc 写 `@reason`/`@author`**：作者每个 Overwrite 都写了理由（如 `FastMapStateHolderMixin.java:45-49`、`KeyValueConditionMixin.java:26-31`），便于冲突定位；适用：与大型模组共存时排查注入冲突。
5. **无加载期依赖的平台抽象**：`Class.forName("malte0811.ferritecore.PlatformHooks")` + 接口 `IPlatformHooks`，Common 不 import 任何 loader 类 —— `util/Constants.java:11-17`、`mixin/config/IPlatformConfigHooks.java:8-15`；适用：不引入 Architectury 的多平台小 mod（不依赖 @ExpectPlatform 的构建插件）。

## 8. （非库类 mod，仅供参考）

无对外 API；对外契约只有两项：配置项名（`config/ferritecore.mixin.properties` 的键名，如 `replaceNeighborLookup`）与其他 mod 可写入的元数据 `ferritecore:disabled_options`（字符串数组，元素为选项名）——`Common/.../util/Constants.java:8` + 两个平台的 `ConfigFileHandler.collectDisabledOverrides`。
