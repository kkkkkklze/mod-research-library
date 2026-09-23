# YesSteveModel/YSM-Wiki-Issues 源码分析报告

## 结论（仅一句话说明）

该仓库**没有源码**：全仓库只有 `README.md`（mod 介绍/FAQ）、`.github/workflows/{crowdin,deploy}.yml` 与 `docs/` 下的 Wiki 文档（`docs/notes/wiki/**` 中文：MoLang 参考表/变量介绍/自定义函数、Freesia 插件；`docs/en/notes/wiki/**` 英文：Introduction、Installation and Usage、Model Format Description、Configuration File Description、Related Commands、Frequent Questions、`Update Log/` 1.2.0–2.6.5 各版本更新日志），无任何 `.java`、`build.gradle`、mod 元数据文件，属纯 wiki/issue 追踪仓库——无法做源码分析。

## 1. 基本信息

- 仓库定位：Yes Steve Model（YSM）的 **Wiki 内容 + Issue 追踪**仓库（README 顶部链接指向 `https://ysm.cfpa.team/` Wiki 与 Issues），mod 本体**闭源**（README FAQ 明示：为防止美术资源被倒卖，核心部分已用 C++ 重写并加密，故不开放源码）
- 可见的 mod 元信息（来自 README）：Minecraft Java 版玩家模型替换 mod，Modrinth 项目 `yes-steve-model`，CurseForge/Discord 见徽章；作者团队含 `哥斯拉`（策划/美术）、`TartaricAcid`、`TomatoPuddin`（程序，含 Fabric 迁移）
- 许可证 / 目标 MC 版本 / 加载器 / Gradle 插件：仓库内均无文件可考（**未确认**）；README 提到 1.2.0+ 使用 C++ 与 VMP 加壳，最新版本不支持 Mac

## 2. 源码规模与包结构

- `.java` 文件数：**0**；`build.gradle`/`gradle.properties`/`fabric.mod.json`/`neoforge.mods.toml`：**不存在**
- 仓库文件（非 `.git`）约 30 余个，全部为 Markdown 与 2 个 GitHub Actions 配置：`docs/en/notes/wiki/*.md`（6 篇 + `Update Log/` 24 篇）、`docs/notes/wiki/molang/*.md`（简介、变量介绍、常用 molang 集合、molang 参考表、molang 杂项内容、自定义函数）、`docs/notes/wiki/Freesia插件.md`
- 无源码包结构可分析

## 3~8 节

不适用（无入口/注册/核心系统/网络/Mixin/datagen 代码）。**唯一可复用的价值**：这些文档描述了 YSM 模型格式与 MoLang 动画语法（`Model Format Description.md`、`molang/*`），如后续要做"玩家模型/动画"兼容或参考其模型格式规范，应从 Wiki 与 Issues 而非源码入手。
