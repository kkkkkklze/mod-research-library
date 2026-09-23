# MoePus/CreateBetterFPS 源码分析

## 1. 基本信息

- Mod 名：CreateBetterFps；mod_id：`createbetterfps`；作者：MoePus
- 目标：Minecraft 1.20.1 + Forge 47.3.39（`gradle.properties`：`mapping_channel=official`，无 Parchment）；Gradle 插件 `net.minecraftforge.gradle [6.0.16,6.2)` + `org.spongepowered.mixin`（mixingradle 0.7-SNAPSHOT）；MIT；版本 1.1.2
- 关键依赖（`build.gradle:157-164`）：`Ponder-Forge` compileOnly、`flywheel-forge-api` compileOnly、Create（`curse.maven:create-328085:6641603` = 6.0.6-150）runtimeOnly、**Embenddium `0.3.31-beta.53` implementation**、**Oculus `1.8.0` implementation**；注解处理器 `org.spongepowered:mixin:0.8.5:processor`
- `mods.toml` 依赖：create optional(CLIENT)、oculus `[1.8.0,)` mandatory(CLIENT)、embeddium `[0.3.31-beta.53,)` mandatory —— 即**强制要求 Embeddium（Sodium）+ Oculus(Iris) 环境**
- AT 文件 `src/main/resources/META-INF/accesstransformer.cfg`：仅一行 `public com.mojang.blaze3d.vertex.BufferBuilder f_85658_ # format`（读取 BufferBuilder 的 format 字段）

## 2. 源码规模与包结构

**9 个 .java，1033 行**（微型 mod）：

- `com.moepus.createbetterfps`（1）：`CreateBetterFps.java` 11 行，主类空实现
- `.mixin`（3）：`SuperByteBufferBuilderMixin` 30、`ShadedBlockSbbBuilderMixin` 33、`SuperBufferFactoryMixin` 19
- `.renderer`（5）：`SodiumByteBuffer` **815 行**（唯一大文件）、`BlockVertex` 26、`EntityVertex` 27、`IrisTerrainVertex` 36、`IrisEntityVertex` 36
- 资源仅 `createbetterfps.mixins.json`、`META-INF/mods.toml`、`accesstransformer.cfg`（无 assets/lang/数据）

## 3. 入口与注册

`src/main/java/com/moepus/createbetterfps/CreateBetterFps.java:5-11` 只有一个 `@Mod(CreateBetterFps.MODID)` 空构造器 —— 无注册表、无事件、无网络。功能全部通过 **3 个 mixin 替换 CreatePonder/Catnip 的 `SuperByteBuffer` 实现**达成。

## 4. 核心系统

**1) 三处注入点把 Create 的 CPU 渲染换成 Sodium 顶点写入**（`createbetterfps.mixins.json`：`required:true`、`refmap: createbetterfps.refmap.json`、`compatibilityLevel: JAVA_8`、`defaultRequire: 1`，三类都在 `mixins` 数组、全部 `remap = false`，注入点用 `require = 0` 放宽）：

- `mixin/SuperByteBufferBuilderMixin.java:26-29`：`build()` HEAD → `cir.setReturnValue(new SodiumByteBuffer(mesh.toImmutable(), shadeSwapVertices.toIntArray()))`，`@Shadow @Final` 直接拿私有字段 `mesh`、`shadeSwapVertices`。
- `mixin/ShadedBlockSbbBuilderMixin.java:27-32`：`end()` HEAD → `bufferBuilder.end()` → `new MutableTemplateMesh(data)` → `SodiumByteBuffer(mesh.toImmutable(), shadeSwapVertices.toIntArray())`。
- `mixin/SuperBufferFactoryMixin.java:15-18`：`create(BufferBuilder.RenderedBuffer)` HEAD → `new SodiumByteBuffer(new MutableTemplateMesh(builder).toImmutable())`。

**2) `SodiumByteBuffer implements net.createmod.catnip.render.SuperByteBuffer`**（`renderer/SodiumByteBuffer.java:43`）——整类重写 Create 的变换/颜色/UV 平移/光照 API，关键设计：

- **静态本地暂存缓冲**：`BUFFER_VERTEX_COUNT = 48`、`SCRATCH_BUFFER = MemoryUtil.nmemAlignedAlloc(64, BUFFER_SIZE)`、静态指针 `BUFFER_PTR/BUFFED_VERTEX`（:90-95），满则 `flush()`（:285-300），避免每次渲染分配。
- **按顶点格式分派**：`renderIntoSodium()`（:787-806）用 `VertexBufferWriter.tryOf(builder)`，再比较 `VertexFormatRegistry.instance().get(bb.format)` 与四个预置 `VertexFormatDescription`：`BlockVertex`(STRIDE 32)/`EntityVertex`(36)/`IrisTerrainVertex`(52)/`IrisEntityVertex`(56)。
- **Iris 分支**：判断 `ShadowRenderer.ACTIVE` 决定走 `IrisRenderShadowInto` 还是 `IrisRenderInto`（:328/:407）；Iris 格式额外写 `CapturedRenderingState` 的 entity/blockEntity/item id、mid_u/mid_v 与 `NormalHelper.computeTangent` 计算的切线（`IrisTerrainVertex.java`、`IrisEntityVertex.java`）。
- **光影与着色**：`ShadersModHelper.isShaderPackInUse()` 时关闭 diffuse（:700+）；`shadeSwapVertices` 数组逐顶点翻转 `shaded` 标记以还原 Create 的"面片免光照"效果，并预先按"法线朝上"算出 `unshadedDiffuse`；颜色混合用整数 `(a*b+0xFF)>>>8` 运算而非浮点。
- **回退路径**：`renderInto()`（:808-815）先试 Sodium 快路径，失败则 `defaultRenderInto(input, builder)` 走原版 `VertexConsumer`，最后 `reset()`。

## 5. 网络 / 数据驱动 / 配置 / datagen

全部为**无**：无 payload、无 `ModConfigSpec`、无 datagen、无 JSON 数据（`src/main/resources` 仅 3 个元数据文件）。

## 6. Mixin

- 配置：`src/main/resources/createbetterfps.mixins.json`（`package: com.moepus.createbetterfps.mixin`，client 数组为空 —— 全部放在通用 `mixins` 数组）
- 目标类与方法：`SuperByteBufferBuilder#build`、`ShadedBlockSbbBuilder#end`、`SuperBufferFactory#create`（均为 HEAD + `CallbackInfoReturnable#setReturnValue`，即"整体替换返回值"而非 @Redirect，可整段跳过原实现）
- remap 一律 `false`（Catnip 类不在混淆映射内）

## 7. 值得学的具体做法

1. "整体替换返回值"式注入（`@Inject(at=HEAD, cancellable=true)` + `setReturnValue`）替换第三方 API 实现类，比逐点 @Redirect 侵入更小：三个 mixin 文件即是范例。
2. 静态对齐分配的原生暂存缓冲 + 满即 flush 的写法：`renderer/SodiumByteBuffer.java:90-95, 285-300`，适合高频小批次顶点提交。
3. 为每种顶点格式预建 `VertexFormatDescription` 常量并按 `BufferBuilder.format` 分派写指针偏移：`renderer/BlockVertex.java`、`IrisEntityVertex.java`，是接 Sodium API 的标准姿势。
4. 用 `@Shadow @Final` 读取目标类私有最终字段（`mesh`、`shadeSwapVertices`），避免 AT/访问器类：`mixin/SuperByteBufferBuilderMixin.java:18-24`。
5. 条件注入用 `require = 0` 保底不崩（三个 mixin 均如此），配合 `mods.toml` 中把 Embeddium/Oculus 设为 mandatory 依赖，保证只在确定环境生效。

## 8. 库/API 扩展点

不适用（非库 mod，无对外 API）。
