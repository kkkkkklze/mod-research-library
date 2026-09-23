# Chat Heads（dzwdz/chat_heads）源码分析

## 1. 基本信息

- Mod 名 Chat Heads / `mod_id=chat_heads` / 作者 dzwdz、Fourmisain / 许可证 **MPL-2.0**（`neoforge/src/main/resources/META-INF/neoforge.mods.toml:4`）
- 目标（当前 HEAD）：**MC 26.1、Java 25**，`enabled_platforms=fabric,neoforge`，mod_version 1.2.8；Fabric Loader 0.18.5、NeoForge 26.1.0.5-beta、Cloth Config 26.1.154、ModMenu 18.0.0-alpha.8（`gradle.properties`）
- 依赖声明：`neoforge.mods.toml` 中 minecraft 与 neoforge 为 required、`side = "CLIENT"`、`displayTest = "IGNORE_ALL_VERSION"`；`fabric.mod.json` 只 depends fabricloader/minecraft，**suggests cloth-config**
- 构建：Architectury 体系——`dev.architectury.loom-no-remap 1.17-SNAPSHOT` + `architectury-plugin 3.5-SNAPSHOT` + `com.gradleup.shadow 9.4`（发布用 shadowJar：`mainSpec.sourcePaths.clear()` 后 `from(zipTree(jar))` 再打包，`build.gradle:104-119`）+ minotaur / cursegradle 双平台发布；三模块 `common / fabric / neoforge`（`settings.gradle:23-25`）
- 编译依赖：cloth-config 为 `api`（common）；fabric 平台加 `cloth-config-fabric` + `modmenu`，neoforge 平台加 `cloth-config-neoforge`。**不依赖 Fabric API**
- 平台差异用 Architectury `@ExpectPlatform`（`common/.../Compat.java:6-13` → 各平台 `CompatImpl`）

## 2. 源码规模与包结构

47 个 `.java` / 2610 行（`find -name '*.java' -exec wc -l {} +`）。

- `dzwdz.chat_heads`（6）：`ChatHeads`(556)、`ComponentProcessor`(391)、`HeadData`、`Compat`、`PaddedChatGlyph`、`MixinPlugin`
- `dzwdz.chat_heads.config`（9）：`ChatHeadsConfig`(接口)、`ChatHeadsConfigData`(Cloth AutoConfig)、`ChatHeadsConfigDefaults`、`ClothConfigCommonImpl`、3 个 GuiProvider、`RenderPosition`、`SenderDetection`
- `dzwdz.chat_heads.mixin`（18）+ `.mixin.render_targets`（3）
- `dzwdz.chat_heads.mixininterface`（2）：`HeadRenderable`、`Ownable`
- 资源：`chat_heads.mixins.json`、`chat_heads.accesswidener`、15 个语言文件、`fabric.mod.json`、`neoforge.mods.toml`；**无 datagen**

## 3. 入口与注册

无任何内容注册（纯客户端 mod）。

- Fabric：`fabric.mod.json` entrypoints `client → dzwdz.chat_heads.fabric.ChatHeadsFabric`（`ClientModInitializer.onInitializeClient → ChatHeads.init()`），另有 `modmenu → ModMenuImpl`
- NeoForge：`@Mod("chat_heads") ChatHeadsNeoForge(IEventBus)`，构造器里 `FMLEnvironment.getDist() == Dist.CLIENT` 时转 `ChatHeadsNeoForgeClient.init(modBus)`，注册 `FMLCommonSetupEvent` → `event.enqueueWork(ChatHeads::init)`（`neoforge/.../ChatHeadsNeoForgeClient.java:9-17`）
- `ChatHeads.init()` 只做一件事：装了 Cloth Config 才 `ClothConfigCommonImpl.loadConfig()`（`ChatHeads.java:103-107`）

## 4. 核心系统

**(1) 消息→头像解析流水线**：`ChatListenerMixin` 用 3 个 `@ModifyArg` 在 `showMessageToPlayer` / `lambda$handleDisguisedChatMessage$0` / `handleSystemMessage` 处把 Component 交给 `ChatHeads.handleAddedMessage(msg, playerInfo)`（`ChatHeads.java:143-184`）。三级策略（`detectPlayerAndAddChatHead:191-236`）：① 有 `ClickEvent.SuggestCommand("/tell X")` 就认 X（`ComponentProcessor.getTellReceiver:364-374`）；② 在文本里扫在线玩家名；③ 兜底把头像放在消息最前面。

**(2) ComponentProcessor：组件树重写**（`ComponentProcessor.java`）：`split()` 按深度优先把组件树展平成无 sibling 列表、用 `StringDecomposer.iterateFormatted` 预处理 § 格式码（:86-118），`join()` 还原渲染等价组件（:123）；`splitLiteral` 按 code point 二分；`processTranslatableArguments` 只检查 `chat.type.text` 的第 1 个参数（:250-284），文件头 :44-57 列出 A1-A5 全部假设；1.21.9+ 直接插入 `Component.object(new PlayerSprite(ResolvableProfile...), showHat)` 作为"字面头像"（:376-379）。

**(3) 头像数据挂载**：`HeadData(PlayerInfo, codePointIndex)` record（`HeadData.java:6`，`EMPTY` 单例、构造断言保证不变量）；`HeadRenderable`（`chatheads$getHeadData/setHeadData`）与 `Ownable` 两个 duck-interface 由 mixin 实现到 `GuiMessage`/`PlayerChatMessage` 上；`ClientPacketListenerMixin`（`priority = 990`，注释说明是为跑在 EssentialClient 之前，:21）用 mixin-extras `@Share LocalRef` 把发送者 `PlayerInfo` 经 `@ModifyArg` 挂到 `PlayerChatMessage`。

**(4) 两种渲染路径**：`RenderPosition.BEFORE_NAME`（默认）走原版 PlayerSprite 渲染 + `PaddedChatGlyph.getAdvance()` 加 `1 + 2*threeDeeNess` 像素（`PaddedChatGlyph.java:17`）+ `PlayerGlyphProviderInstanceMixin` 用 5 个 `@ModifyArg` 改 `renderQuad` 的左右/上下参数实现"3D 感"；`BEFORE_LINE` 用 `ChatComponentInnerMixin`（`@Mixin(targets = "ChatComponent$1")`）在 `ChatGraphicsAccess.handleMessage` 前直接 `renderChatHead` 并 `updatePose(translate(offset,0))` 平移文本与 tag icon，offset 用 `@Share LocalIntRef` 在两处注入间传递（:27-91）。`customHeadRendering` 标志由 `ChatComponentRenderMixin`、`render_targets/GuiRendererMixin` 一进一出包住 `extractRenderState`/`prepare`，保证只在聊天与配置预览内生效。

**(5) 皮肤贴图**：`SkinTextureDownloaderMixin` 在 `registerTextureInManager` 的 `supplyAsync` 处包一层 Supplier，命中 `skins/` 前缀时用 `ChatHeads.extractBlendedHead` 取 8×8 头 + 帽子层做 alpha 混合（`blendColors:472-497`，支持 HD/legacy 皮肤），注册为 `chat_heads:<原路径>` 的 `DynamicTexture`，并把原路径加入 `blendedHeadTextures` 走单次 blit 快路径（`ChatHeads.renderChatHead:525-530`）。

**(6) 服务端开关**：服务端资源包内若存在 `chat_heads:disable` 资源即整体禁用（`DownloadedPackSourceMixin:19-31` → `serverDisabledChatHeads`）；`ConnectionMixin` 在建立连接时重置 `serverSentUuid`/`serverDisabledChatHeads`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包（客户端 mod，仅读原版包）
- 配置：Cloth Config AutoConfig（`@Config(name = MOD_ID) ChatHeadsConfigData implements ConfigData`）但**不硬依赖**——抽象出 `ChatHeadsConfig` 接口 + `ChatHeadsConfigDefaults` 常量实现，`ChatHeads.CONFIG` 静态字段默认指向 Defaults，装 cloth 时在 init 被替换（`ChatHeads.java:80,103-107`）；`nameAliases` 为 `Map<String,String>`，EssentialsX 的 "`X is Y`" 会被 `autoDetectAlias` 自动加别名并即时存档（`ChatHeads.java:123-140`）；`validatePostLoad` 清理空条目
- datagen：无

## 6. Mixin

- `common/src/main/resources/chat_heads.mixins.json`：client 20 条，`plugin = dzwdz.chat_heads.MixinPlugin`（按 `cloth-config` / `emojiful` 是否加载条件启用对应 mixin），`injectors.defaultRequire = 1`
- Access Widener：`chat_heads.accesswidener` 开放 `SkinManager$TextureCache`、`Font$PreparedTextBuilder`、`ChatComponent$LineConsumer`（平台模块统一用 `loom.accessWidenerPath = project(":common").loom.accessWidenerPath`）
- 代表 hook：`ChatListener.showMessageToPlayer` / `handleSystemMessage`（@ModifyArg）；`ChatComponent.extractRenderState`（@Inject HEAD/RETURN 抓/清 GuiGraphics）+ `lambda$extractRenderState$1` 的 `fill` @ModifyArg 修文字溢出宽度；`ChatComponent.refreshTrimmedMessages`（@ModifyArg 转移 owner，兼容 Compact Chat）；`PlayerGlyphProvider$Instance.renderSprite` 的 5 个 @ModifyArg；`SkinTextureDownloader.registerTextureInManager`；`render_targets/{GuiRenderer,BookViewScreen,ClothConfigScreen}Mixin`
- 只依赖 mixin-extras 的 `@Local`/`@Share`，未用 `@Redirect`/`@WrapOperation`；大量用 `@Mixin(targets = "...$1")` 打内部类/匿名类
- 注：`common/MixinPlugin` 里的 `EmojifulMixin`、`neoforge/MixinPlugin` 里的 `ShowcaseItemFeatureMixin` 分支在本仓库找不到对应类（残留代码）

## 7. 值得学的 5 条做法

1. **`@Mixin(targets = "ChatComponent$1")` 精准注入 lambda/匿名内部类**（`ChatComponentInnerMixin.java:18`），不改原版大方法、不影响其它调用者。
2. **`@Share` + `LocalIntRef` 在同一方法的多处注入间传状态**（同上 :27-91），替代在 mod 里放临时静态字段。
3. **软依赖用"接口 + 常量默认实现 + 运行时替换"**（`ChatHeadsConfig`/`ChatHeadsConfigDefaults`/`ChatHeadsConfigData`），没装 Cloth Config 也能跑。
4. **贴图预混合 + 独立 DynamicTexture 缓存**：把 8×8 头与帽子层离线 blend 成一张图，渲染时单次 blit（`SkinTextureDownloaderMixin` + `blendedHeadTextures` 快路径），而不是每帧混色。
5. **用资源包里的特殊资源名做服务端开关**（`ChatHeads.DISABLE_RESOURCE` + `DownloadedPackSourceMixin`），服务端无需装 mod 也能要求客户端关闭功能。

## 8. 库/扩展点

非库 mod，无公开 API 包；可复用的是两个 duck-interface 模式（`mixininterface/HeadRenderable`、`Ownable`，方法名统一 `chatheads$` 前缀防空冲突）与 `ComponentProcessor` 的组件树 split/join 工具（当前为 public 但无稳定性承诺）。
