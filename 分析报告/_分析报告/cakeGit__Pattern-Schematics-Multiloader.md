# cakeGit / Pattern-Schematics-Multiloader 源码分析（Architectury 多加载器范例）

## 1. 基本信息
- Mod 名：Create: Pattern Schematics；mod_id `create_pattern_schematics`；作者 Cake；许可证 **MIT**（`forge/src/main/resources/META-INF/mods.toml`）
- 目标：MC **1.20.1**，**同时发布 Fabric + Forge**（`gradle.properties: enabled_platforms = fabric,forge`；fabric_loader 0.15.7 / fabric-api 0.92.0+1.20.1 / forge 47.1.43），Java 17
- Gradle：`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.5-SNAPSHOT` + `machete`（jar 压缩，仅 CI）+ `me.modmuss50.mod-publish-plugin 0.6.3`（`build.gradle`）
- 映射：**loom 分层映射** = quilt-mappings 23 → parchment 2023.09.03 → officialMojangMappings（`nameSyntheticMembers=false`），`build.gradle:29-36`
- 依赖（`gradle.properties`）：Create Fabric `0.5.1-f-build.1417+mc1.20.1`（common 里 `modCompileOnly`）、Create Forge `0.5.1.f-26` + **Registrate `MC1.20-1.3.3`** + Flywheel `0.6.10-7`；Fabric 侧网络走 Create Fabric 自带的 `me.pepperbell.simplenetworking`
- 版本号格式：`${mod_version}+${project.name}-${minecraft_version}[-${GITHUB_RUN_NUMBER}]`

## 2. 源码规模与包结构
实测 **67 个 .java / 3971 行**：`common` 43 文件 2957 行、`fabric` 13 文件 515 行、`forge` 11 文件 499 行（逻辑几乎全在 common）。
- `com.cak.pattern_schematics`（根，含 MOD_ID/REGISTRATE）：`PatternSchematics`、`PlatformGetter`、`PatternSchematicsClient(Events)`
- `.registry`（+`.registry.fabric` / `.registry.forge`）：注册、`PlatformPackets(+Impl)`、lang、创造栏插入
- `.foundation` / `.foundation.mirror` / `.foundation.mixin_accessors` / `.foundation.util`（+平台子包 `mirror.fabric|forge`、`fabric|forge`）：核心工具与客户端工具逻辑
- `.content.item`、`.content.ponder`、`.mixin`（15 个）、`.packet.fabric|forge`、`.fabric`、`.forge`
- 最大文件：`foundation/mirror/PatternSchematicHandler.java` 500 > `content/ponder/PatternSchematicPonderScenes.java` 273 > `foundation/mirror/StaticRenderers.java` 200

## 3. 入口与注册
common 无 `@Mod`：`PatternSchematics.java` 持有 `MOD_ID` 与 `CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)`，静态块设 `REGISTRATE.setTooltipModifierFactory(...)`；`init()` 统一调 `PatternSchematicsRegistry.register()`、`PlatformPackets.registerPackets()`、`PlatformPackets.getChannel().initServerListener()`。
平台入口：`PatternSchematicsFabric implements ModInitializer` → `init() + REGISTRATE.register()`；`forge/PatternSchematicsForge` 的 `@Mod` 构造器 → `REGISTRATE.registerEventListeners(eventBus)` → `init()` → `DistExecutor.unsafeRunWhenOn(CLIENT, ...)`。
注册框架为 **Create 的 CreateRegistrate**（非 DeferredRegister）：`registry/PatternSchematicsRegistry.java` 仅两个 `ItemEntry`（`EMPTY_PATTERN_SCHEMATIC`、`PATTERN_SCHEMATIC`，`.defaultModel().properties(p -> p.stacksTo(1))`）。

## 4. 核心系统
1. **跨平台注入（@ExpectPlatform）**：`PlatformPackets`（`getChannel / registerPackets / sendPatternSchematicSyncPacket`）、`PlatformGetter.platformName`、`PatternSchematicHandlerPlatformProvider.getPlatformPatternSchematicHandler` 三处声明，实现类必须位于平台子包且类名后缀 `Impl`（`registry.fabric.PlatformPacketsImpl`、`registry.forge.PlatformPacketsImpl`）。
2. **网络抽象层**：自有接口 `foundation/GenericNetworker.java`（`initServerListener/initClientListener/sendToServer(SimplePacketBase)`），Fabric 实现包装 `me.pepperbell.simplenetworking.SimpleChannel`（空实现的 listener 方法），Forge 实现包装 `net.minecraftforge.network.simple.SimpleChannel`——common 只依赖 Create 的 `SimplePacketBase`。
3. **包注册（平台各一份枚举）**：`registry/forge/PatternSchematicPackets.java` 用 `NetworkRegistry.ChannelBuilder` + `NETWORK_VERSION=3` + 内嵌 `PacketType`（encoder=`T::write`、decoder、`consumerNetworkThread`）按序注册；fabric 版用 `new SimpleChannel(CHANNEL_NAME)` + `registerS2CPacket/registerC2SPacket`。
4. **同步包与校验**：`packet/{forge,fabric}/PatternSchematicSyncPacket.java` 继承 `SimplePacketBase`，字段 `slot/deployed/anchor/rotation/mirror/cloneScaleMin|Max/Offset`，`Vec3iUtils.packVec3i` 压缩；`handle` 里 `context.enqueueWork` 后按 slot 取玩家物品栈、用 `PatternSchematicsRegistry.PATTERN_SCHEMATIC.isIn(stack)` 校验，再写 NBT（`Deployed/Anchor/Rotation/Mirror/CloneScale*`）并 `SchematicInstances.clearHash(stack)`。
5. **客户端工具（绕过 mixin 的策略）**：`foundation/mirror/PatternSchematicHandler.java` **整类复制** Create 的 `SchematicHandler` 后继承扩展（文件注释："Gave up with the copious amounts of mixins needed so i just copied the class file"），平台客户端各自 `PatternSchematicHandlerForge/Fabric` 继承它，并在客户端入口赋值给 `PatternSchematicsClient.PATTERN_SCHEMATIC_HANDLER`。
6. **Ponder 与本地化**：`content/ponder/PatternSchematicsPonderIndex.java` 用 `PonderRegistrationHelper(MOD_ID).forComponents(...).addStoryBoard("pattern_schematic/...", scene, tag)`；`registry/PatternSchematicsLang.java` 用 `REGISTRATE::addRawLang` 累积 lang。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：见上（按平台各实现一套 channel，common 只留 `sendPatternSchematicSyncPacket` 门面）。无配置系统（无 Config）。
- datagen：**仅 Fabric 侧** `fabric/PatternSchematicsFabricData implements DataGeneratorEntrypoint`，注册 `REGISTRATE.setupDatagen(createPack(), ExistingFileHelper.withResourcesFromArg())`、`PatternSchematicsLang.register()`、ponder tags/index、`SharedText.gatherText()`、`PonderLocalization.generateSceneLang/provideLang`；loom `datagen` run 通过 `-Dfabric-api.datagen.output-dir=${project(":common").file("src/generated/resources")}` 把产物输出到 common，`common/build.gradle` 再把 `src/generated/resources` 加入资源目录。
- 资源：`common/src/main/resources/pattern_schematics.accesswidener` 为空壳（仅 `accessWidener v2 named` 头）；仓库内**未见 `fabric.mod.json`**（但 `fabric/build.gradle:processResources` 有 `filesMatching("fabric.mod.json")`，疑似未提交，未确认）。

## 6. Mixin
三份配置：`pattern_schematics.common.mixins.json`（`mixins` 15 条，`client` 为空，`injectors.defaultRequire=1`）、`fabric/.../pattern_schematics.mixins.json`（3 条，多出 `AntiCreativeCrateCrashMixin`）、`forge/.../pattern_schematics.mixins.json`（2 条）。
代表性目标（全部打在 Create 上）：`AbstractContraptionEntityMixin`（144 行）、`SchematicPrinterMixin`、`DeployerMovementBehaviorMixin`、`SchematicannonBlockEntityMixin`、`StructureTemplateMixin`、`SchematicInstancesMixin`、`ServerSchematicLoaderMixin`、`CreateCreativeModeTabMixin`。Forge 侧用 `loom.forge.mixinConfig("pattern_schematics.common.mixins.json", "pattern_schematics.mixins.json")` 把两份配置都挂进 mods.toml；common 的访问器接口集中在 `foundation/mixin_accessors/`（`MovementContextAccessor`、`SchematicTableBlockEntityMixinAccessor`、`SchematicTableMenuMixinAccessor`）。

## 7. 值得学的 5 条做法
1. **三模块骨架 + 逻辑全在 common**（`common/ fabric/ forge/`）：平台差异只用 `@ExpectPlatform` 抽象类暴露，实现类强制放在 `<pkg>.<platform>` 且以 `Impl` 结尾——本项目最值得抄的工程结构。
2. **网络层再包一层接口**：`foundation/GenericNetworker.java` 让 common 不出现任何加载器代码，新增包体只需改平台枚举。
3. **依赖 mod 大改造先用"继承复制"再加深**：`PatternSchematicHandler` 直接复制 Create 的 `SchematicHandler`（MIT）来避免数十个 mixin，风险低、可控性强。
4. **datagen 在 Fabric 侧跑、产物写回 common**：`fabric/build.gradle` 的 `datagen` run + `-Dfabric-api.datagen.output-dir=:common/src/generated/resources`，配合 `common/build.gradle:sourceSets.main.resources.srcDir("src/generated/resources")`。
5. **AW 的平台传递写法**：fabric `remapJar { injectAccessWidener = true }`，forge `forge { convertAccessWideners = true; extraAccessWideners.add(...) }`。

## 8. 公开 API
无对外 API 包（内容型附属 mod）；`PlatformPackets`、`GenericNetworker` 是内部跨平台门面，非第三方接入点。
