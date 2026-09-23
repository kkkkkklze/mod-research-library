# tr7zw/3d-skin-layers 源码分析

仓库路径：`源码库\_参考仓库\_bulk\tr7zw__3d-skin-layers`

## 1. 基本信息

- Mod 名 / mod_id：3d-Skin-Layers / `skinlayers3d`（`gradle-compose.yml`）
- 作者：tr7zw；版本：1.11.2（`gradle-compose.yml`）
- 目标版本：MC 1.16.5 → 1.21.11，Fabric + Forge + NeoForge 全平台（`versions/` 下 28 个版本目录，如 `versions/1.21.1-fabric`、`versions/1.21.10-neoforge`）
- Gradle 插件：仓库**根目录没有 build.gradle**。本项目用 tr7zw 自研的 `gradle-compose` 生成构建，模板来源 `https://github.com/tr7zw/ProcessedModTemplate/tree/master`（`gradle-compose.yml`），子项目 `3dSkinLayers-Versionless`，启用 flags：`mixinextras`、`includeLibs`、`addTRenderLib`、`addTRansitionLib`、publishFabric/Forge/Neo
- 编译依赖：`dev.tr7zw.transition`（`ModLoaderUtil` / `ModLoaderEventUtil` / `PlayerUtil`，见 `src/main/java/dev/tr7zw/skinlayers/SkinLayersModBase.java`）、TRenderLib、MixinExtras（`@WrapOperation`）、`maven.modrinth:entity-model-features` 仅编译期（`versions/1.21.1-fabric/dependencies.gradle`、`versions/1.21.1-neoforge/dependencies.gradle` 均为 `modCompileOnlyApi`）
- 许可证：仓库根目录无 LICENSE 文件，**未确认**

## 2. 源码规模与包结构

- `find . -name '*.java'` = **57 个文件，4711 行**（排除 .git）
  - `src/main/java` 46 文件（`CustomizableModelPart` 266 行、`PlayerRendererMixin` 234、`SkullBlockEntityRendererMixin` 217、`SkinUtil` 192、`ConfigScreenProvider` 177、`PlayerModelMixin` 140）
  - `3dSkinLayers-Versionless/src/main` 10 文件 / 1445 行（`Mth` 679、`CustomizableCube` 200、`SolidPixelWrapper` 198）
  - `src/test` 1 文件（`dev/tr7zw/tests/MixinTests.java`）
- 包：`dev.tr7zw.skinlayers`（根 4）、`.mixin` 14、`.api` 11、`.accessor` 7、`.render` 2、`.renderlayers` 1、`.config` 2、`.util` 2；`dev.tr7zw.skinlayers.versionless.{render,config,util,util.wrapper}`

## 3. 入口与注册

无 DeferredRegister（纯客户端渲染 mod）。Fabric 入口 `dev.tr7zw.skinlayers.SkinLayersMod`（`ClientModInitializer`），Forge/Neo 入口 `SkinLayersBootstrap`（`@Mod("skinlayers3d")` + `DistExecutor.unsafeRunWhenOn` / `ModLoaderEventUtil.registerClientSetupListener`，`SkinLayersBootstrap.java:11-47`）。类层次：

```java
public class SkinLayersMod extends SkinLayersModBase implements ClientModInitializer {
    public void onInitializeClient() { this.onInitialize(); }
}
public abstract class SkinLayersModBase extends ModBase {   // ModBase 在 versionless 模块
    protected SkinLayersModBase() {
        instance = this;
        ModLoaderUtil.disableDisplayTest();
        ModLoaderUtil.registerConfigScreen(ConfigScreenProvider::createConfigScreen);
    }
}
```

配置不是注册式：`ModBase.onInitialize()` 用 Gson 手写读写 `config/skinlayers.json`（`3dSkinLayers-Versionless/.../ModBase.java:20-54`），字段见 `versionless/config/Config.java`（renderDistanceLOD=14、fastRender、compatibilityMode、各部件开关）。

## 4. 核心系统

1. **版本无关核心（versionless 模块）**：`versionless/ModBase` + `versionless/render/CustomizableCube`、`CustomModelPart` + `versionless/util/wrapper/{SolidPixelWrapper,TextureData,ModelBuilder}`。该模块不 import 任何 MC 类（自有 `Mth`、`Vector3`、`Direction`），由 `util/NMSWrapper.WrappedNativeImage` 适配 `NativeImage`，靠 `getLuminanceOrAlpha()!=0/-1` 判断像素"存在/实心"。
2. **皮肤 → 3D 网格**：`SkinUtil.setup3dLayers(AbstractClientPlayer, PlayerSettings, thinArms)` 按固定 UV 偏移生成 6 个部件网格（`SkinUtil.java:146-156`：腿 4×12×4@(0,48)/(0,32)、臂 4|3×12×4@(48,48)/(40,32)、躯干 8×12×4@(16,32)、头 8×8×8@(32,0)，头 rotationOffset 0.6f）。核心算法 `SolidPixelWrapper.wrapBox/ getSizeUV / getOnTextureUV / UVtoXYZ / XYZtoUV / addPixel`：逐像素遍历六个面，用邻居像素（含斜向 farNeighbour、backside 重叠）计算 `hide` 面集合与 `corners` 待剔除角，只输出可见面；非 64×64（HD 皮肤）直接放弃（`SkinUtil.java:139`）。
3. **紧凑化渲染**：`CustomModelPart.compactCubes` 把多边形展平进 `float[] polygonData`，步长 `polyDataSize = 23`（3 法线 + 4 顶点×5），`CustomizableModelPart.compile` 直接写 `VertexConsumer`（addVertex/setColor/setUv/setOverlay/setLight/setNormal），并复用 `Vector4f[4]` 减少分配；异常时抛出带 `polygonAmount`/`polygonData.length` 的诊断（指向 issue #280）。
4. **注入式渲染（duck interface + 高优先级 mixin）**：`accessor/ModelPartInjector` 声明 `setInjectedMesh(Mesh, OffsetProvider)`；`@Mixin(value = ModelPart.class, priority = 300)` 在 `render(...,IIIII)V` 的 HEAD 处 cancel 并用 `injectedMesh.render(...)` 替代，先 `translateAndRotate` 再 `offsetProvider.applyOffset`。`PlayerRendererMixin` 负责在 `renderHand` / `setModelProperties` 中按 config 与 `OffsetProvider.*` 注入或隐藏 hat/jacket/sleeve/pants。
5. **纹理获取降级链**：`SkinUtil.getTexture` 依次尝试 资源包 `Resource` → `TextureManager` → `HttpTextureAccessor#getImage` / `DynamicTexture#getPixels`，用 `NativeImageAccessor#skinlayers$isAllocated()` 判断底层图片是否已被释放，再用 Guava `Cache`（`expireAfterAccess 60s` + `removalListener` 调 `close()`）兜底；注释明确"从 GPU 下载纹理会因 HD 皮肤导致 JVM 崩溃"故弃用。
6. **头颅/头戴物品**：`accessor/SkullSettings`、`SkullRendererCache` + mixin `SkullBlockEntityRendererMixin`、`SkullModelMixin`、`SkullModelStateMixin`、`BlockEntityWithoutLevelRendererMixin`（1.21.9+ 分支打 `PlayerHeadSpecialRenderer` / `SkullSpecialRenderer`）、`CustomHeadLayerMixin`、`Deadmau5EarsLayerMixin`。
7. **兼容层**：`util/SodiumWorkaround`、`EMFModelPartMixin`（`targets = "traben.entity_model_features.models.parts.EMFModelPart"`，`@Inject` 特定 JVM 描述符的 render 并 cancel）、`irisCompatibilityMode` / `applySodiumWorkaround` 配置项、`Class.forName("dev.tr7zw.disguiseheads.DisguiseHeadsShared")` 反射探测兼容 mod（`ModBase.java:38`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端 mod）。
- 数据驱动：仅 mixin json 与旧版本的 `skinlayers3d.accesswidener`（`versions/1.16.5-fabric/src/main/resources/`）；**无 datagen**。

## 6. Mixin

配置：`src/main/resources/skinlayers3d.mixins.json`（`refmap: skinlayers3d.refmap.mixins.json`，`defaultRequire: 1`，`mixins: []`，14 个全部在 `client`）。代表：

- `PlayerRendererMixin` → `AvatarRenderer`（≥1.21.9）/ `PlayerRenderer`；`@Inject(method="renderHand", at=@At("HEAD"))`、`@WrapOperation(method="method_72996", at=@At(value="NEW", target="...PlayerModel;"))` 把 armor 用的 PlayerModel 标记 ignored
- `ModelPartMixin` → `ModelPart`，`priority = 300`，HEAD cancel
- `PlayerMixin` / `PlayerModelMixin` → 在 MC 类上实现 `PlayerSettings` / `PlayerEntityModelAccessor`
- `HttpTextureMixin` / `NativeImageMixin` → 暴露 `getImage`、`skinlayers$isAllocated`
- `SkullBlockEntityRendererMixin` → `SkullBlockRenderer`；`SkullBlockEntityMixin` → `SkullBlockEntity`
- 旧版 `PlayerRendererMixin` 里保留 `setModelProperties` + `CustomLayerFeatureRenderer`（RenderLayer 版实现），≤1.21.1 使用

## 7. 值得学的 5 条做法

1. **单文件多版本预处理注释**：用 `//? if >= 1.21.0 { ... } else { /* ... */ }` 注释块在同一源码树里按 MC 版本切换代码，配合 `versions/<mc>-<loader>/dependencies.gradle` 提供每版本依赖，一个仓库覆盖 1.16.5→1.21.11（`src/main/java/dev/tr7zw/skinlayers/SkinLayersMod.java:3-21`、`PlayerRendererMixin.java:18-81`）。适用：想少维护分支的多版本 mod。
2. **duck interface 挂状态 + 高 priority mixin 拦截渲染**：把自定义 mesh 挂在 vanilla `ModelPart` 上，不新建渲染管线即可替换渲染（`mixin/ModelPartMixin.java:20-45`、`accessor/ModelPartInjector.java`）。适用：给原版模型附加自定义几何体。
3. **紧凑 float 缓冲区 + 复用临时向量**：`polygonData` 展平、`polyDataSize=23`、`Vector4f[4]` 复用（`versionless/render/CustomModelPart.java:26-46`、`CustomizableModelPart.java:165`）。适用：每帧大量顶点/小对象的热路径。
4. **纹理像素级读取的降级链 + 自动释放的缓存**：多来源 try 顺序 + `allocation` 校验 + Guava `removalListener` 关闭 `NativeImage`（`SkinUtil.java:27-114`）。适用：需要读取玩家皮肤/动态纹理像素的客户端功能。
5. **API 用 EMPTY 常量实现空对象模式**：`Mesh.EMPTY`、`MeshTransformer.EMPTY_TRANSFORMER`、`MeshTransformerProvider.EMPTY_PROVIDER`、`BoxBuilder.DEFAULT` 免去 null 判断（`api/Mesh.java:14-55`、`api/MeshTransformerProvider.java:17`）。适用：对外暴露扩展点的库 mod。
6. 附：`src/test/java/dev/tr7zw/tests/MixinTests.java` 用测试断言 mixin 是否真的打上（防止 mixin 静默失效）。

## 8. 公开 API（库/接入面）

- 包：`dev.tr7zw.skinlayers.api`
- 入口：`SkinLayersAPI`（`setupBoxBuilder(BoxBuilder)`、`setupMeshTransformerProvider(MeshTransformerProvider)`，其余为只读 `@Getter`：meshHelper / meshProvider / boxBuilder）
- 扩展点接口：`MeshHelper`（`create3DMesh(NativeImage, w,h,d, u,v, topPivot, rotationOffset, mirror)`）、`MeshProvider#getPlayerMesh`、`MeshTransformer`、`MeshTransformerProvider#prepareTransformer(@Nullable ModelPart)`（供 bendy-lib 之类做弯曲）、`OffsetProvider#applyOffset`、`BoxBuilder#build`、`LayerFeatureTransformerAPI`
- 数据 interface（由 mixin 实现在 MC 类上，外部可直接 cast）：`accessor/PlayerSettings extends api.PlayerData`（setHeadMesh/setTorsoMesh/.../getCurrentSkin/hasThinArms/clearMeshes）、`accessor/PlayerEntityModelAccessor`、`accessor/ModelPartInjector`、`api/SkullData`
