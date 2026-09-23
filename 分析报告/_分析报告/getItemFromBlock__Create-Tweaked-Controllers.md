# getItemFromBlock/Create-Tweaked-Controllers 源码分析报告

## 1. 基本信息

- Mod 名：Create: Tweaked Controllers；modId `create_tweaked_controllers`；作者 getItemFromBlock（credits 提及 McArctic 的 1.21.1 移植版）
- 目标：MC 1.20.1 / **Forge 47.4.0**（`gradle.properties:minecraft_range=[1.20.1,1.21)`、`forge_range=[47.4.0,)`、`loader_range=[47,)`）；版本 1.20.1-1.2.7；许可证 MIT（`src/main/resources/META-INF/mods.toml`）
- Gradle 插件：`net.minecraftforge.gradle` + `org.spongepowered.mixin`(MixinGradle 0.7-SNAPSHOT) + `jarJar.enable()`（`build.gradle:12,22-30`）；Mixin 0.8.5（annotationProcessor `org.spongepowered:mixin:${mixin_version}:processor`，`build.gradle:234`）
- 依赖（`build.gradle:205-234`）：`implementation` create-1.20.1:6.0.0-4（`transitive = false`）、Ponder-Forge 1.0.36、Framework(curse.maven)、CC:Tweaked forge 运行期；`compileOnly` Registrate MC1.20-1.3.3、flywheel-forge-api 1.0.0-215、Controllable(curse.maven)、JEI common/forge-api 15.20.0.106、cc-tweaked core/forge-api 1.105.0；`runtimeOnly` flywheel-forge、JEI forge、CC:Tweaked forge
- 说明：本地副本 src 下共 72 个文件，资源仅 `create_tweaked_controllers.mixins.json` 与 `META-INF/mods.toml`（README 引用的 `logo.png`、界面贴图/lang 均不在包内，疑为克隆不完整，**未确认**）

## 2. 源码规模与包结构

- 70 个 `.java`，7545 行
- 顶层 `com.getitemfromblock.create_tweaked_controllers`：主类、`ModBlockEntityTypes`、`ModTab`、`ModClientEvents`、`ModClientStuff`、`ModCommonEvents`
- 子包（文件数）：`gui` 12 + `gui/InputConfig` 7（逐类输入绑定屏）、`input` 11（输入抽象与各实现）、`controller` 8（状态机/序列化/红石输出/渲染）、`packet` 5、`compat/ComputerCraft` 4、`compat/Controllable` 1、`block` 3、`item` 3、`config` 3、`mixin` 1
- 最大文件：`controller/ControlProfile.java` 494、`gui/ModControllerConfigScreen.java` 378、`item/TweakedLinkedControllerItemRenderer.java` 364、`block/TweakedLecternControllerBlockEntity.java` 336、`controller/TweakedLinkedControllerClientHandler.java` 331、`gui/TweakedLinkedControllerScreen.java` 258

## 3. 入口与注册

主类 `CreateTweakedControllers`（`src/main/java/.../CreateTweakedControllers.java:26-51`），用 Create 的 Registrate 包装：

```java
@Mod(CreateTweakedControllers.ID) @Mod.EventBusSubscriber
public class CreateTweakedControllers {
    private static final CreateRegistrate REGISTRATE = CreateRegistrate.create(ID);
    public CreateTweakedControllers() {
        IEventBus eventBus = FMLJavaModLoadingContext.get().getModEventBus();
        REGISTRATE.registerEventListeners(eventBus);
        ModTab.register(eventBus); ModItems.register(); ModBlocks.register();
        ModBlockEntityTypes.register(); ModMenuTypes.register(); ModConfigs.register(ModLoadingContext.get());
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ModClientStuff.onConstructor(eventBus, forgeEventBus));
        ModComputerCraftProxy.register();
    }
    public static void init(final FMLCommonSetupEvent e) { ModPackets.registerPackets(); }
```

内容注册走 Registrate（`item/ModItems.java:17-21`：`registrate().item("tweaked_linked_controller", X::new).properties(p->p.stacksTo(1)).model(AssetLookup.itemModelWithPartials()).register()` → `ItemEntry<T>`）；同时提供 `translateDirect/builder()`（转 Create 的 `LangBuilder`，`LangBuilder.resolveBuilders(args)`）。

## 4. 核心系统

1. **输入抽象 `input/GenericInput`**：接口统一 `GetButtonValue()/GetAxisValue()/GetDisplayName()/IsInputValid()/IsDataCoherent()/Serialize(DataOutputStream)/Deserialize(DataInputStream)/OpenConfigScreen(Screen,Component)/GetType()`；`InputType` 枚举 7 种（NONE/JOYSTICK_BUTTON/JOYSTICK_AXIS/MOUSE_BUTTON/MOUSE_AXIS/MOUSE_WHEEL/KEYBOARD_KEY），每种对应一个实现类（`JoystickButtonInput` 等）。`input/JoystickInputs.java`(204 行) 基于 GLFW 枚举 joystick/gamepad 并读取轴/按钮。
2. **控制器配置 `controller/ControlProfile`（494 行）**：`public GenericInput[] layout = new GenericInput[25]` 固定 25 槽 + `hasJoystickInput/hasMouseScroll/duplicatedKeys`；自带二进制格式版本号 `CURRENT_VERSION_MAJOR=0x01/MINOR=0x00`；文件路径硬编码 `config/gamepad_profiles/gamepad_profile_<id>`，`CheckProfileUpgrade()` 把旧 `gamepad_profile_0` 升级为 `ControlType.CUSTOM_0` 并删旧文件；`ControlType` 枚举（KEYBOARD_MOUSE/JOYSTICK/CUSTOM_n）；手写 `DataInputStream/DataOutputStream` 序列化，而非走 ForgeConfigSpec。
3. **客户端状态机 `controller/TweakedLinkedControllerClientHandler`**：`MODE`（IDLE/BIND…）、`buttonStates`(short 位掩码)、`axisStates`(int)、`PACKET_RATE = 5`(tick)、`buttonPacketCooldown/axisPacketCooldown` 做发送节流，`selectedLocation` 记录待绑定 LinkBehaviour 位置；提供 `IGuiOverlay OVERLAY`。
4. **服务端执行 `TweakedLinkedControllerServerHandler.tick(Level)`**：由 `ModCommonEvents.onServerWorldTick`（`LevelTickEvent`，仅 `Phase.START` 且 `LogicalSide.SERVER`）驱动，把输入解码为红石输出 `ControllerRedstoneOutput.DecodeAxis(float)/DecodeButtons(short)`（6 轴 + 按钮位）。
5. **手持/讲台双通道包**：`packet/TweakedLinkedControllerPacketBase` 定义 `handleItem(ServerPlayer,ItemStack)` 与 `handleLectern(ServerPlayer,TweakedLecternControllerBlockEntity)` 两条处理路径，子类只覆写需要的那条（`TweakedLinkedControllerBindPacket.handleItem` 用 Create 的 `BlockEntityBehaviour.get(level,pos,LinkBehaviour.TYPE)` 取频率并写回物品 NBT `"Items"`；`TweakedLinkedControllerStopLecternPacket.handleLectern` 调 `lectern.tryStopUsing(player)`）。
6. **讲台控制器 `block/TweakedLecternControllerBlockEntity extends SmartBlockEntity`**：字段 `controller`(ItemStack)、`user/prevUser`(UUID，客户端用 prevUser)、`useFullPrecision`、`axis[6]`、`ControllerRedstoneOutput output`、`TweakedLecternPeripheral peripheral`、`AbstractComputerBehaviour computerBehaviour`；`addBehaviours` 里挂 `ModComputerCraftProxy.behaviour(this)`；`ModCommonEvents.onEntityJoinWorld` 清 `player.getPersistentData()["IsUsingLecternController"]` 作为崩溃后自愈。
7. **第三方兼容**：`ModClientStuff.clientInit` 用 `ModList.get().isLoaded("controllable")` 决定是否 `ControllerHandler.Register()`；ComputerCraft 侧 `compat/ComputerCraft/ModSyncedPeripheral` + `TweakedLecternPeripheral` 提供外设 API。
8. **GUI 体系**：`ModControllerConfigScreen`(378) 总入口，`gui/InputConfig/*Screen`（Keyboard/MouseButton/MouseAxis/MouseWheel/JoystickButton/JoystickAxis）+ `InputList` 做逐槽绑定；配套自绘渲染器 `ControllerButtonRenderer/DigitIconRenderer/JoystickIcon/ModIcons/PlainRectRenderer`，物品用 Create 的 `CustomRenderedItemModelRenderer`（`TweakedLinkedControllerItemRenderer` 364 行）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`packet/ModPackets` 枚举 + 4 个 payload，全部 `PLAY_TO_SERVER`；`NetworkRegistry.ChannelBuilder.named(asResource("main"))`，`NETWORK_VERSION = 2`，协议版本字符串双向 `::equals` 校验，`serverAcceptedVersions/clientAcceptedVersions` 设 2 表示**不兼容旧版本**；用 Create 的 `SimplePacketBase`（自定义 `write(FriendlyByteBuf)`/`handle(Context)`），`PacketType` 静态 `index++` 自动分配 id；提供 `sendToNear(level,pos,range,msg)`（`PacketDistributor.NEAR` + `TargetPoint`）。
- 配置：`config/ModConfigs.register` → `ModConfig.Type.CLIENT`，文件名 `ID.replaceAll("_","") + "-client.toml"`；`ModClientConfig` 含 `use_custom_mappings`、`toggle_mouse_focus`、`auto_reset_mouse_focus`、主菜单/暂停菜单按钮行列、`controller_layout_type`(XBOX/NINTENDO/PLAYSTATION)。另外按键走 `config/ModKeyMappings`（`RegisterKeyMappingsEvent` 注册 mouse_focus=LALT、mouse_reset=R、controller_exit=TAB）。
- datagen：无（无 data 源集/无 `runData` 产物）。
- 数据驱动：无 JSON 数据包；控制配置为自定义二进制 profile 文件。

## 6. Mixin

配置 `src/main/resources/create_tweaked_controllers.mixins.json`：`required=true`、`compatibilityLevel="JAVA_17"`、`refmap`、`injectors.defaultRequire=1`，仅 1 个 mixin：`mixin/KineticBlockEntityMixin` → 目标 `com.simibubi.create.content.kinetics.base.KineticBlockEntity#getFlickerScore`，`@Inject(at = @At("HEAD"), cancellable = true, remap = false)`，直接 `callback.setReturnValue(0)`（关掉动力方块闪烁评分）。

## 7. 值得学的 5 条具体做法

1. **输入即对象**：把"键鼠/手柄/滚轮/光标"统一为 `GenericInput` 接口，序列化、显示名、打开配置屏都挂在实例上（`input/GenericInput.java`）；适用：需要支持多输入设备且允许玩家自定义映射。
2. **包基类承载双路径分发**：`TweakedLinkedControllerPacketBase` 同时定义 item 与 lectern 处理入口，子类空实现不需要的那条，服务端根据上下文二选一（`packet/`）；适用：同一操作在"手持物品/世界方块"两种载体上语义相同。
3. **协议版本硬隔离**：`NETWORK_VERSION=2` + 双向 `::equals` 校验，宁可拒绝连接也不做兼容（`packet/ModPackets.java:34-52`）；适用：频繁改包体的迭代期。
4. **发送节流常量集中**：客户端 `PACKET_RATE=5`、`buttonPacketCooldown/axisPacketCooldown` 在状态机里统一控制发包频率（`controller/TweakedLinkedControllerClientHandler.java:45-52`）；适用：输入/位置类高频同步。
5. **崩溃自愈标记**：用 `player.getPersistentData()` 写"正在使用讲台控制器"，登录时无条件清除，避免上次崩溃后玩家被锁在 lectern 状态（`ModCommonEvents.java:30-41`）；适用：任何"进入临时状态后可能崩服"的交互。

## 8. 公开 API

非库模组，无 `api` 包、无对外扩展点；跨 mod 接入是反向的——它依赖 Controllable/ComputerCraft 并提供 CC:Tweaked 外设（`compat/ComputerCraft/TweakedLecternPeripheral`）。
