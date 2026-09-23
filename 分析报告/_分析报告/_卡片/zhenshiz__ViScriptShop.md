# ViScriptShop — 速览卡片

- 仓库: https://github.com/zhenshiz/ViScriptShop
- 出现在整合包: 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\zhenshiz__ViScriptShop`
- 目标版本: MC 1.21.1 / NeoForge 21.1.233 / Forge - / Fabric -；mod 版本 1.2.1
- 构建: 插件=moddev，工程结构=single；mod_id: viscript_shop
- 源码规模: 84 个 .java，13,173 行
- 主类候选: `src/main/java/com/viscriptshop/promotion/condition/PromotionConditionEntry.java` (126 行)
- 目录特征: Command, Data, Mixin, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/viscriptshop/gui` | 39 |
| `com/viscriptshop/promotion` | 15 |
| `com/viscriptshop/event` | 9 |
| `com/viscriptshop/compat` | 8 |
| `com/viscriptshop/util` | 5 |
| `com/viscriptshop/network` | 4 |
| `com/viscriptshop` | 3 |
| `com/viscriptshop/command` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/viscriptshop/gui/ShopUI.java` | 1693 |
| `src/main/java/com/viscriptshop/command/ShopCommand.java` | 550 |
| `src/main/java/com/viscriptshop/gui/data/Shop.java` | 546 |
| `src/main/java/com/viscriptshop/gui/data/AggregatedResources.java` | 530 |
| `src/main/java/com/viscriptshop/gui/view/ShopPreviewView.java` | 494 |
| `src/main/java/com/viscriptshop/gui/data/MerchantInfo.java` | 461 |
| `src/main/java/com/viscriptshop/promotion/PromotionEngine.java` | 457 |
| `src/main/java/com/viscriptshop/promotion/PromotionRule.java` | 420 |
| `src/main/java/com/viscriptshop/util/ViScriptShopServerUtil.java` | 336 |
| `src/main/java/com/viscriptshop/gui/components/MerchantItemAmountDisplay.java` | 327 |
| `src/main/java/com/viscriptshop/util/UIElementUtil.java` | 327 |
| `src/main/java/com/viscriptshop/gui/components/StageRestrictionConfigurator.java` | 292 |
| `src/main/java/com/viscriptshop/gui/layout/GlassDarkShopUiLayout.java` | 283 |
| `src/main/java/com/viscriptshop/gui/data/CategoryInfo.java` | 277 |
| `src/main/java/com/viscriptshop/network/c2s/BuyMerchantPayload.java` | 252 |