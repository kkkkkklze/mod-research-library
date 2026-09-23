# mortuusars/Exposure 源码分析报告

## 1. 基本信息

- Mod 名 Exposure / `mod_id=exposure` / 作者 mortuusars / 版本 1.9.18 / 许可证 MIT（`gradle.properties`）
- 目标 MC 1.21.1，多加载器：common + fabric(loader 0.16.9, API 0.102.1) + neoforge(21.1.200)；构建用 Architectury Loom 1.7-SNAPSHOT + architectury-plugin 3.4-SNAPSHOT（`build.gradle:1-10`）
- 依赖：common 层 `modApi fuzs.forgeconfigapiport`（跨平台配置）；neoforge 层 `modImplementation Create 6.0.8 + Ponder + Flywheel API + Registrate`（Create 是其 API/内容依赖，mods.toml 中 create 为 optional，`[6.0.7,)`）、`modCompileOnlyApi KubeJS/Rhino/JEI`、Jade runtime、mixin-extras 0.4.1（include 打包）；compileOnly Real Camera / Easy Anvils 用于兼容 mixin

## 2. 源码规模与包结构

- 468 个 `.java` / 37,130 行（`find . -name '*.java' -exec cat {} + | wc -l`）；common 419 文件 / 34,833 行、fabric 23 / 1,149、neoforge 26 / 1,148
- 主要包（含文件数）：`client/capture`(13+模板7+任务6)、`client/image`(13) 与 `client/image/modifier/pixel`(14)、`network/packet/clientbound`(19) 与 `serverbound`(10)、`mixin/client`(21) 与 `mixin`(13)、`world/item`(15)、`util/cycles/task`(13)、`world/level/storage`(8)、`world/camera/*`、`client/camera/viewfinder`(7)
- 最大文件：`world/item/camera/CameraItem.java` 1036、`world/entity/CameraStandEntity.java` 821、`world/block/entity/LightroomBlockEntity.java` 728、`Exposure.java` 614、`client/gui/screen/album/AlbumScreen.java` 596、`Config.java` 560

## 3. 入口与注册

主类 `common/src/main/java/io/github/mortuusars/exposure/Exposure.java`：`init()` 只做转发，逐一调用内部静态类的静态 `init()`（Blocks/BlockEntityTypes/EntityTypes/Items/CreativeTabs/DataComponents/CriteriaTriggers/MenuTypes/RecipeSerializers/SoundEvents/ArgumentTypes，第 87-104 行），注册项全部集中在同名内部类里，写法 `Register.item("camera", () -> new CameraItem(...))`。`Register.java` 是 17 个 `@ExpectPlatform` 方法的抽象层（第 40-145 行），`fabric/neoforge` 各一份 `RegisterImpl`；NeoForge 侧在 `ExposureNeoForge.java:35-55` 把 18 个 `DeferredRegister` 统一挂到 mod 事件总线。非注册内容（Tags、LootTables 注入、自定义注册表 key `Exposure.Registries.COLOR_PALETTE/LENS/FILTER`，第 609-613 行）也集中在此。

## 4. 核心系统

1. **相机状态机**：`world/item/camera/CameraItem.java`（1036 行）状态全放 DataComponents（CAMERA_ACTIVE/FILM/LENS/FILTER/SHUTTER_SPEED/SELF_TIMER…），`client/camera/viewfinder/` 下 Viewfinder/ViewfinderShaders/ViewfinderZoom/ViewfinderSelfie 分工。
2. **截图捕获管线**：`client/capture/Capture.java:23-107` = `Task<Result<T>>` + `CaptureAction` + `CaptureTimer`，`completeOnTimeout(12s)`；`template/CaptureTemplate.java:34-50` 用 `ImageEffect.chain(crop, resize, exposure, contrast, levels, hsb, noise, blackAndWhite)` 声明式描述"照片洗出"效果链。
3. **图像与调色**：`client/image/*`（Image/PalettedImage/WrappedNativeImage/CensoredImage/CroppedImage/TrichromeImage）+ `capture/palettizer/{DitheredPalettizer,NearestColorPalettizer}` 把截图量化到 `data/ColorPalette` 注册表。
4. **服务端照片仓库**：`ExposureServer` + `world/level/storage/ExposureRepository.java`（世界目录 `data/exposures/`，`expect(player,id)` 白名单校验客户端上传，`validateUpload` 拒绝非预期 ID/超时上传，第 111-180 行）。
5. **数据驱动注册表**：ColorPalette/Lens/Filter 三个自定义注册表经 `neoforge/event/NeoForgeCommonEvents.java:47` 的 `DataPackRegistryEvent.NewRegistry` 挂接。
6. **异步任务框架**：`util/cycles/task/`（Task/Result/ChainedTask/FallbackTask/TimeoutTask/NestedTask 等 13 类）+ `Cycles` 主循环，由 `mixin/client/GameRendererMixin.java` 在 `getMainRenderTarget()` 调用点前 `ExposureClient.cycles().tick()` 驱动。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：`network/packet/Packet.java` 仅两行接口 `extends CustomPacketPayload { boolean handle(PacketFlow, Player); }`；`Packets` 为 `@ExpectPlatform`，neoforge `PacketsImpl` 包装 `PacketDistributor`（sendToPlayer/sendToAllPlayers/sendToPlayersNear）。共 33 个包（clientbound 19、serverbound 10）。大图不走包体：客户端上传 `ExposureDataC2SP` / 拉取 `ExposureRequestC2SP`↔`ExposureDataResponseS2CP`，配 `client/capture/saving/ExposureUploader`。配置：NeoForge `ModConfig` 三层 SERVER/COMMON/CLIENT（`ExposureNeoForge.java:29-31`），`Config.java` 560 行。datagen：无源码（无 `datagen` 目录），资源另行维护。

## 6. Mixin

配置：`common/src/main/resources/exposure-common.mixins.json`（required，JAVA_17）→ client 22 个 + 通用 14 个；另有 `fabric`/`neoforge` 各自的 mixins.json（全仓 46 个 Mixin 类）。代表：`mixin/client/CameraMixin.java` 注入 `getMaxZoom`(RETURN，用 Viewfinder 自拍距离限制) 与 `setup`(RETURN，按相机 yOffset `move(0, yOffset, 0)` 并叠加自拍旋转)；`mixin/client/GameRendererMixin.java` 在 `GameRenderer#render` 的 `Minecraft.getMainRenderTarget()` 调用点前处理取景器 shader，`ModifyReturnValue` 改 `getFov`；兼容包 `mixin/compat/easy_anvils/*`、neoforge `mixin/create/FillingBySpoutMixin`，由 `ExposureMixinPlugin` 条件启用。

## 7. 值得学的 5 条具体做法

1. 用 Task 组合子表达异步流程（`util/cycles/task/ChainedTask.java`、`TimeoutTask.java`）——任何"异步 + 超时 + 本地化错误"的场景。
2. 效果链声明化：`client/image/modifier/ImageEffect.java` 的 `chain(...)`，新增胶片风格只需拼一个函数。
3. 服务端图片存储 + `expect()` 上传白名单（`world/level/storage/ExposureRepository.java:111-180`）——多人共享玩家生成内容的安全范式。
4. 40+ DataComponent 集中声明且 `persistent(...).networkSynchronized(...)` 成对书写（`Exposure.java:257-390`）——1.21 组件化物品状态的模板。
5. 一个 `@ExpectPlatform` 门面覆盖 17 种注册类型（`Register.java`）+ 每平台一个 Impl，避免 common 里散落平台判断。

## 8. API（对外扩展点）

- NeoForge：`neoforge/api/event/{FrameAddedEvent, ModifyEntityInFrameDataEvent, ModifyFrameExtraDataEvent}`（NeoForge.EVENT_BUS，服务端触发）；KubeJS 插件 `neoforge/integration/kubejs/ExposureKubeJSPlugin` + `event/*EventJS`。
- Fabric：`fabric/api/event/{FrameAddedCallback, ModifyEntityInFrameDataCallback, ModifyEntityInFrameExtraDataCallback, ShutterOpeningCallback}`。
- 另暴露 accesswidener `common/src/main/resources/exposure.accesswidener`。
