# TJT01/GlobalServerConfig 源码分析报告

## 1. 基本信息

- Mod 名：Global Server Config；mod_id：`global_server_config`；作者：TJT01
- 目标版本 / 加载器：Forge 专用（`src/main/resources/META-INF/mods.toml`：`modLoader="javafml"`、`loaderVersion="[40,)"`、`minecraft` 依赖 `versionRange="[1.18.2,)"`）
- Gradle：ForgeGradle `5.1.+` + `org.spongepowered:mixingradle 0.7.+`（`build.gradle:1-17`）；mappings `official 1.18.2`，Java 17（`build.gradle:29,38`）
- 许可证：The Unlicense（`mods.toml`）
- 编译依赖：仅 Forge + Minecraft，无任何第三方 mod 依赖；无 mixin 之外的 API 入口

## 2. 源码规模与包结构

实测 `find . -name '*.java' | wc -l` = **2 个文件、36 行**（`wc -l` 汇总），是本批仓库中最小的：

- `mod.tjt01.globalserverconfig`：1 个文件（主类）
- `mod.tjt01.globalserverconfig.mixin`：1 个文件
- 最大文件：`ServerLifecycleHooksMixin.java`（20 行）、`GlobalServerConfig.java`（16 行）

## 3. 入口与注册

主类 `src/main/java/mod/tjt01/globalserverconfig/GlobalServerConfig.java:8-15`：

```java
@Mod("global_server_config")
public class GlobalServerConfig {
    public GlobalServerConfig() {
        ModLoadingContext.get().registerExtensionPoint(
                IExtensionPoint.DisplayTest.class,
                () -> new IExtensionPoint.DisplayTest(() -> NetworkConstants.IGNORESERVERONLY, (a, b) -> true)
        );
    }
}
```

- **无内容注册**：没有 DeferredRegister / Registrate，没有任何物品、方块、配置项注册。
- 唯一"注册"动作是声明 `DisplayTest` = `IGNORESERVERONLY`，即纯客户端/服务端共存、不校验对端版本（典型"单侧小工具"写法）。

## 4. 核心系统

只有 1 个系统，但思路值得借鉴：

**服务端配置路径重定向** — `src/main/java/mod/tjt01/globalserverconfig/mixin/ServerLifecycleHooksMixin.java:11-19`

```java
@Mixin(ServerLifecycleHooks.class)
public class ServerLifecycleHooksMixin {
    @Overwrite(remap = false)
    private static Path getServerConfigPath(final MinecraftServer minecraftServer) {
        return FMLPaths.CONFIGDIR.get();
    }
}
```

设计点：

1. 目标方法 `ServerLifecycleHooks#getServerConfigPath(MinecraftServer)` 是 Forge 侧决定 `SERVER` 类型配置（原版存于 `world/serverconfig/`）落盘目录的唯一入口，`@Overwrite(remap=false)` 直接返回 `FMLPaths.CONFIGDIR.get()`，使所有世界共享 `config/` 下同名配置文件——即用 20 行 mixin 改动全局配置语义。
2. `remap = false` 必须显式声明：目标类是 Forge 的 `net.minecraftforge.server.ServerLifecycleHooks`，不是 Mojang 类，不做混淆重映射。
3. `@Overwrite` 会与其它改同一方法的模组冲突（无 `@Overwrite` 兼容层、无 `require`/`expect` 机制），属于"小而脆"的取舍。
4. 副作用（README 明确）：必须进过一次世界，server config 才会被加载/生成；因为路径不再随存档走，改配置会影响所有存档。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无 `SimpleChannel` / 无包注册）。
- 配置：不新增配置项，仅**改变 Forge 既有 SERVER 配置的加载目录**。
- 数据驱动：**无**；datagen：**无**（无 `data` 源集、无 `runData` 配置）。

## 6. Mixin

- 配置：`src/main/resources/global_server_config.mixins.json`（`package: mod.tjt01.globalserverconfig.mixin`、`compatibilityLevel: JAVA_17`、`refmap: global_server_config.refmap.json`、`minVersion: 0.8`、`required: true`）
- 代表类：`ServerLifecycleHooksMixin`；hook 目标：`ServerLifecycleHooks#getServerConfigPath`，注入点为 `@Overwrite(remap = false)`。

## 7. 值得学的 5 条具体做法

1. **用 mixin 重定向"配置目录"而非复制配置逻辑**：`ServerLifecycleHooksMixin.java:17` 让 Forge 自己把 server config 写进 `config/`，零解析代码，适用于任何"只想改文件落盘位置"的需求。
2. **单方法小 mod 也用完整 mixin 基础设施**：`build.gradle:11-17` 引入 mixingradle、`mods.toml` 声明 `forge` 依赖版本区间，保证发布物在加载期即可校验。
3. **IO 重定向用 `remap = false` + 注释作者信息**：`ServerLifecycleHooksMixin.java:13-16` 标注 `@author`，便于冲突排查；适用于把 mixin 从 Mojang 类转向 mod 类的场景。
4. **靠 `DisplayTest.IGNORESERVERONLY` 让客户端可进任意服务器**：`GlobalServerConfig.java:11-14`，适用于纯客户端便利性功能。
5. **用 `FMLPaths.CONFIGDIR` 而非自拼 `Paths.get`**：`ServerLifecycleHooksMixin.java:18`，避免 dev/prod 工作目录差异（该 mod 只改服务端该处，客户端目录同理适用）。

## 8. 库 / 前置 / API 类 mod

不适用：本 mod 不提供任何对外 API，无公开扩展点（无 `registerXxx`、无 `ModList` 检出接口、无事件）。
