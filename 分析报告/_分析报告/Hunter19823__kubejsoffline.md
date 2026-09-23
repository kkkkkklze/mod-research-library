# Hunter19823/kubejsoffline 源码分析

## 1. 基本信息

KubeJS Offline / `kubejsoffline`；作者 ILIKEPIEFOO2（`pie.ilikepiefoo`）；版本 5.2.2；目标 **MC 1.20.1**（`gradle.properties:minecraft_version=1.20.1`）、Java 17；Fabric（`fabric_loader 0.14.22` + `fabric_api 0.91.0`）与 Forge（`47.1.3`）双平台，经 **Architectury**（`architectury 9.1.12`，`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 0.12.0-SNAPSHOT`）统一。许可证 All Rights Reserved。依赖：`kubejs 2001.6.5-build.7`（其运行宿主，required `AFTER` architectury）、`reflections 0.10.2`、`javassist 3.28.0-GA`、`mixinextras 0.2.0-rc.2`；**核心 API 是外部闭源库 `pie.ilikepiefoo:kubejsoffline-core:1.3.0.44`**（`build.gradle` dependencies，来自 GitHub Packages，需 `PACKAGE_ACTOR/PACKAGE_TOKEN`）。

## 2. 规模与包结构

实测 13 个 `.java` / **678 行**（纯胶水层，重逻辑在 core jar 内）。包结构：`pie.ilikepiefoo.kubejsoffline`（9 个：`EventHandler.java` **145 行最大**、`FakeBindingsEvent.java` 115、`DocumentationThread.java` 58、`KubeJSOffline.java` 28、`MinecraftDocumentationBridge.java` 32、`RhinoTypeMapper.java` 32、`OfflinePlugin.java` 8、`KubeJSOffline`/…）、`command/DocumentCommand.java`（63）、`util/ComponentUtils.java`（12）、`fabric/`（2）、`forge/`（2，含 `ReflectionHelperForge.java` 115）。Common/Forge/Fabric 三源集（Architectury 布局）。

## 3. 入口与注册

`KubeJSOffline.init(Path)`（`KubeJSOffline.java:18`）只设 `WORKING_DIR` 并调 `EventHandler.init()`。平台入口：`forge/KubeJSOfflineForge.java` `@Mod` 构造器内 `EventBuses.registerModEventBus(MOD_ID, FMLJavaModLoadingContext.get().getModEventBus())` + `HELPER = new ReflectionHelperForge()` + `init(FMLPaths.GAMEDIR.get())`；`fabric/KubeJSOfflineFabric.java` 的 `onInitialize()` 同理。**无 DeferredRegister**（不注册游戏对象）。KubeJS 插件以服务文件注册：`common/src/main/resources/kubejs.plugins.txt` 内容为 `pie.ilikepiefoo.kubejsoffline.OfflinePlugin`（`OfflinePlugin extends KubeJSPlugin`，当前为空壳，仅占位）。

## 4. 核心系统

- **反射扫描**（`forge/ReflectionHelperForge.java:24-108`）：实现 `core.api.ReflectionHelper`；启动时向 Reflections 的 VFS 注册自定义 `Vfs.UrlType`（处理 mod 文件夹/union URL），并 `Vfs.addDefaultURLTypes(Vfs.DefaultUrlTypes.directory)`；扫描用 `new ConfigurationBuilder().addUrls(...) → new Reflections(cfg).getSubTypesOf(Object.class)`（`:93-108`）得到全量类。Fabric 侧另有 40 行等价实现。
- **文档生成线程**（`DocumentationThread.java:34-57`）：`while (null == KubeJSOffline.HELPER) { this.wait(5000); }` 自旋等待平台入口注入 Helper，随后 `new SimpleDocumentationProvider.Builder().setReflectionHelper(...).setDocumentationBridge(bridge).setTypeNameMapper(new RhinoTypeMapper()).setBindingsProvider(new FakeBindingsEvent()).build().generateDocumentation(...)`，输出到 `<gamedir>/kubejs/documentation/index.html`（`:25-27`）。
- **伪绑定事件**（`FakeBindingsEvent.java`，`extends BindingsEvent implements BindingsProvider`）：继承 KubeJS 的 `BindingsEvent` 并伪造一次"绑定注册"，遍历 `ScriptType.values()` 逐个调用所有 `KubeJSPlugins.getAll()` 的 `plugin.registerBindings(this)` 与 `KubeJSPlugins.addSidedBindings(this)`（:38-42），把各插件的变量/事件组（`EventGroupWrapper` → 每个 handler 生成 `name.handler(EventType)` 唯一名并记录生效 scope）收进 `BINDING_MAP` 供文档使用。异常被吞掉并记日志，保证单个插件出错不影响整体生成。
- **命令与自动模式**（`command/DocumentCommand.java`，`EventRegistrationEvent` via Architectury `CommandRegistrationEvent.EVENT`）：`/kubejsoffline`（`hasPermission(2)`）→ `CompletableFuture.runAsync(new DocumentationThread(bridge))`；`EventHandler.init()`（`EventHandler.java:36-46`）在检测到系统属性/环境变量 `KUBEJS_OFFLINE_AUTO_GEN`（`KubeJSOffline.java:24`）时启用 CI 模式：`ClientGuiEvent.SET_SCREEN` 拦截标题屏 → 打开 `SelectWorldScreen` → `createTestWorld`（`:63`，超平坦单层基岩 + 关闭 mob/掉落/随机刻/天气等 gameRules，`createTestWorldGameRules`），玩家加入时 `player.kjs$runCommand("kubejsoffline")`；生成成功/异常后 `System.exit(0/1)`，并 `future.orTimeout(5, TimeUnit.MINUTES)` 防挂死（`DocumentCommand.java:58`）。
- **反馈桥**（`MinecraftDocumentationBridge.java`）：把生成进度以 `sendSuccess` 聊天消息推送，完成时用 `ClickEvent.Action.OPEN_FILE` 给出可点击的 index.html 链接。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：**无**（无自定义 payload/包）。配置：**无配置文件**，行为开关只有系统属性/环境变量 `KUBEJS_OFFLINE_AUTO_GEN`。datagen：**无**（但其产物是"运行时生成的 HTML 文档 + JSON 索引"，见 `schemabreakdown.md` 中自定义压缩数据结构设计文档）。

## 6. Mixin

三份 mixins 配置（`common/src/main/resources/kubejsoffline-common.mixins.json`、`fabric|forge/src/main/resources/kubejsoffline.mixins.json`）均为**空 mixins/client 数组**；`common/src/main/resources/kubejsoffline.accesswidener` 仅有 `accessWidener v2 named` 头无条目。即**实际无 mixin**（保留骨架以备后用）。

## 7. 值得学的 5 条做法

1. 重逻辑与平台胶水分层：本仓库只有 678 行胶水（入口 + 线程 + 桥），算法核心全部放在独立发布的 `kubejsoffline-core` 工件里（`build.gradle` `implementation group: "pie.ilikepiefoo", name: "kubejsoffline-core"`），多加载器复用同一份 core。
2. 用"伪绑定事件"蹭宿主插件生态：继承 KubeJS `BindingsEvent` 并在自定义 `ScriptType` 上下文中调 `plugin.registerBindings(this)` 从而枚举所有插件绑定（`FakeBindingsEvent.java:33-45`）。
3. 面向 CI 的自动化模式：靠环境变量开关 + 自动建超平坦测试世界 + 加入即执行命令 + 超时 `orTimeout(5, TimeUnit.MINUTES)` + `System.exit`（`EventHandler.java:41-46`、`DocumentCommand.java:35-59`），使文档生成可无人值守跑在构建服务器。
4. 无 mixin 也能拿到全量类信息：用 Reflections + 自定义 `Vfs.UrlType` 处理 mod 目录/union URL（`ReflectionHelperForge.java:26-75`），避免为"扫类"引入 mixin。
5. 扫描线程自旋等待而非硬依赖加载顺序：`while (HELPER == null) wait(5000)`（`DocumentationThread.java:36-44`），平台入口只需赋值即可解耦初始化时序。

## 8. 公开 API / 扩展点

本 mod 自身不对外提供 API，但**其依赖的 core 包即公开扩展面**：`pie.ilikepiefoo.kubejsoffline.core.api.*`（`ReflectionHelper`、`DocumentationBridge`、`DocumentationProvider`、`BindingsProvider`、`TypeNameMapper` 等）+ `core.impl.SimpleDocumentationProvider.Builder`，任何想复用其文档生成能力的外部项目即通过该 API 接入（源码不在本仓库，未确认其完整清单）。
