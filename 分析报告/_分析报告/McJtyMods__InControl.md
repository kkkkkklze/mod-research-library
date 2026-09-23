# McJtyMods/InControl 源码分析

## 1. 基本信息

- Mod 名 / mod_id：InControl / `incontrol`（`src/main/resources/META-INF/mods.toml`）
- 作者：McJty；目标版本：**Minecraft 1.16.5 + Forge 36.1.13**（旧版 API：`MobEntity`/`IWorld`/`ForgeRegistries.ENTITIES`）
- 版本号：`1.16-5.2.12`，许可证 MIT（`gradle.properties`、mods.toml）
- Gradle：ForgeGradle 3.+、CurseGradle 1.4.0、sourceCompatibility 1.8，Mapping `official`（`build.gradle`）
- 编译依赖：JEI（compileOnly api）、TheOneProbe、**Bookshelf / GameStages（net.darkhax）**、LostCities（`mcjty:lostcities`）；全部为可选软依赖（仅 `mods.toml` 中声明 forge 为 mandatory）
- 纯服务端逻辑 mod，无 mixin（`grep -rn mixin` 无结果）

## 2. 源码规模与包结构

- 68 个 `.java`，合计 9001 行（`find -name '*.java' | wc -l`）
- 包（第 3 层，文件数）：`incontrol.commands` 12、`incontrol.rules` 9、`incontrol.compat` 6、`incontrol.tools.varia` 5、`incontrol.tools.typed` 5、`incontrol.tools.rules` 5、`incontrol.spawner` 4、`incontrol.data` 3、根 3、`incontrol.tools.cache` 2、`incontrol.rules.support` 2、`incontrol.setup` 1
- 最大文件：`tools/rules/CommonRuleEvaluator.java`(1074)、`tools/rules/RuleBase.java`(807)、`rules/support/GenericRuleEvaluator.java`(614)、`spawner/SpawnerConditions.java`(390)、`spawner/SpawnerSystem.java`(383)、`rules/SpawnRule.java`(350)、`rules/SummonAidRule.java`(347)

## 3. 入口与注册

主类 `src/main/java/mcjty/incontrol/InControl.java:12`，仅 25 行：

```java
@Mod(InControl.MODID)
public class InControl {
    public static final String MODID = "incontrol";
    public static ModSetup setup = new ModSetup();
    public InControl() {
        FMLJavaModLoadingContext.get().getModEventBus().addListener((FMLCommonSetupEvent e) -> setup.init());
        MinecraftForge.EVENT_BUS.addListener((FMLServerStoppedEvent e) -> StructureCache.CACHE.clean());
    }
}
```

`setup/ModSetup.java:28` 的 `init()` 是真正的装配点：`setupModCompat()`（用 `ModList.get().isLoaded()` 探测 lostcities/gamestages/sereneseasons/baubles/enigma）→ `MinecraftForge.EVENT_BUS.register(new ForgeEventHandlers())` → `RulesManager.setRulePath(FMLPaths.CONFIGDIR.get())` + `readRules()` → `SpawnerParser.readRules("spawner.json")`。**没有任何 DeferredRegister/Registrate**：本 mod 不注册方块物品实体，注册内容只有事件监听器与命令（`commands/ModCommands.java:12` 用 Brigadier 注册 `/incontrol` 与别名 `/ctrl`）。

## 4. 核心系统

**(a) 规则引擎（typed 属性系统）**：`tools/typed/{Key,Type,Attribute,AttributeMap,GenericAttributeMapFactory}.java`。`Key.create(Type.INTEGER, "minlight")` 声明一个命名键，`AttributeMap.consume(key, consumer)` 只在 JSON 出现该键时回调，且消费后键从 map 移除；规则构造末尾 `map.isEmpty()` 不为空即报 "Invalid keywords"（`rules/SpawnRule.java:231-242`）——**未知字段立刻报错的严格 DSL 校验**。

**(b) 规则解析与热重载**：`rules/RulesManager.java`。`readAllRules()` 读 `config/incontrol/` 下 6 个文件（spawn / summonaid / potentialspawn / loot / experience / phases.json），用 `Function<JsonElement,T> parser` 泛型复用同一段读法（`:160`），每条规则解析失败只跳过并计数（`:171`）。`safeCall()` 把单个文件异常隔离，避免一个坏 JSON 崩掉全部规则。

**(c) 条件求值**：`tools/rules/CommonRuleEvaluator.java` 持有 `List<BiFunction<Object,IEventQuery,Boolean>> checks`，`match()` 对所有 check 做 AND（`rules/support/GenericRuleEvaluator.java:604`）。通用条件（光照/高度/生物群系/结构/装备）在父类，spawn 专属条件（canspawnhere/maxcount/hostile）在子类覆盖 `addChecks`。

**(d) 事件适配层 `IEventQuery<T>`**：把不同事件（`LivingSpawnEvent.CheckSpawn`、`EntityJoinWorldEvent`、`LivingDropsEvent`…）统一投影成 `getWorld/getEntity/getPlayer/getSource`（`rules/SpawnRule.java:35-126`），规则代码完全不感知事件类型——**同一套 DSL 复用于生成、掉落、经验、召唤援军**。

**(e) 统计缓存**：`rules/RuleCache.java` 每维度一个 `CachePerWorld`，一次遍历 `sw.getEntities()` 同时算出 总数/被动/敌对/中立 与 per-mod、per-EntityType 计数（`:189-223`），并用 `-1` 哨兵 + `countDone` 标志保证"每 tick 只算一次"；`registerSpawn/registerDespawn` 增量修正。这是 maxcount/mincount 条件能廉价运行的前提。

**(f) 自建刷怪器**：`spawner/SpawnerSystem.java` 用 `TickEvent.WorldTickEvent`（counter=20，每秒 1 次）驱动，按维度分组规则（`worldData: Map<RegistryKey<World>, WorldSpawnerData>`）；核心是 `busySpawning` 静态标记（`:38`）：**在调用 `ForgeHooks.canEntitySpawn` 前置位、调用后清空，让 spawn.json 的 `incontrol` 条件能区分"这次生成是 InControl 自己发起的"**（`GenericRuleEvaluator.java:120`），实现两个子系统互不递归过滤。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **无网络**：无 SimpleChannel/PacketHandler，纯服务端。
- **数据驱动**：全部规则来自 `config/incontrol/*.json`（Gson），不是 datapack `data/` 目录；`/incontrol reload` 触发 `RulesManager.reloadRules()` 与新规则过滤器失效（`onPhaseChange()` 把 `filteredRules` 置 null 实现惰性重建）。
- **配置**：无 ForgeConfigSpec，配置即 JSON 文件。
- **持久化**：`data/DataStorage.java extends WorldSavedData`，存 daycounter、day、phases（阶段集合）、`data/Statistics.java` 存刷怪统计。
- **datagen**：`build.gradle` 有 `data` run 配置，但工程内无 `src/generated`，实际未使用。

## 6. Mixin

无。

## 7. 值得学的 5 条具体做法

1. **Key+AttributeMap 严格 DSL 校验**：声明式键表 + 消费即移除 + 剩余键报错；路径 `tools/typed/AttributeMap.java`；适用于任何 JSON/配置文件驱动的内容包。
2. **`IEventQuery<T>` 事件投影**：用接口把事件抽成统一取值视图，规则代码零事件类型依赖；路径 `tools/rules/IEventQuery.java`；适用于需要同时处理多个 Forge 事件的库。
3. **规则表达式编译成 `List<Consumer<EventGetter>>`**（`RuleBase.java:117-161`）：解析期完成取值/校验，运行期只执行闭包，避免每 tick 重解析 JSON。
4. **sentinel 缓存的"每 tick 一次"计数**：`RuleCache.CachePerWorld` 用 `-1`/`countDone` 惰性整表扫描 + spawn/despawn 增量维护；适用于高频查询实体统计的 AI/刷怪逻辑。
5. **静态 `busySpawning` 递归护栏**：自建子系统调用原版/事件入口前打标记，让规则能识别"自产事件"；`spawner/SpawnerSystem.java:162`；适用于自定义生成器 + 事件驱动规则的组合。

## 8. 公开 API

非 API 类 mod。`src/api/java` 下只有内嵌的 Baubles 与 `mcjty/enigma/api` 兼容层（EnigmaScript 的 `setState/setPlayerState`，经 `compat/ModRuleCompatibilityLayer.java` 调用），不对第三方暴露扩展点；外部 mod 只能通过事件优先级或 LostCities/GameStages 这类被探测的软依赖间接协作。
