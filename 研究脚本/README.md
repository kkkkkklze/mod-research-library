# 研究脚本（可复现工具集）

这些脚本产出了本目录所有成果（对照表 / 报告 / 卡片 / 反编译源码）。**它们是可复现链路的唯一凭据**，
所以放在仓库内（而不是 `~/Downloads`，那个目录会被不定期清理）。

统一约定：
- 一律用 **`py`** 启动（本机 `python` / `python3` 被拦，静默退出码 49；`node` 可用）。
- 路径常量写在每个脚本顶部（多为 `HERE` / `WS` / `V`）。数据在 `Downloads\_teacon\` 时可原样跑；
  数据被清后把常量改到新位置即可。
- 脚本写中文注释与中文输出，**不要用 bash heredoc 写含反斜杠/反引号的脚本**（会被 bash 吃掉）。

## 下载与补漏

| 脚本 | 作用 | 用法示例 |
|---|---|---|
| **`_downloader.py`** | **通用下载器**：多源回退（Modrinth `cdn → cdn-raw → BMCLAPI`；forgecdn `mediafilez → edge`；raw.githubusercontent → raw.gitmirror）+ 哈希校验（sha512/sha1/md5/size），幂等跳过 | `py _downloader.py "<url>" --sha512 <hex> -o .`<br>`py _downloader.py --cf 8813615 "DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar"`<br>`py _downloader.py --list urls.txt`<br>`py _downloader.py --head "<url>"`（只查体积/时间） |
| `_decompile_jars.py` | 把 `downloaded/*.jar` 批量 CFR 反编译进 `源码库/_参考仓库/_pack_decompiled/<包>/` + 生成速览卡片 + 回填仓库地址 | `py _decompile_jars.py` |
| **`_jar_diff.py`** | **两个 jar 的类级差异**（按 zip 中央目录里的 **CRC32** 比对）：新增/删除/修改 + 按包聚合 + 导出变更的 `.class` 供选择性反编译。比"两边都反编译再 diff"准得多（反编译产物有 CFR 顺序噪声） | `py _jar_diff.py 旧.jar 新.jar`<br>`py _jar_diff.py 旧.jar 新.jar --extract-changed _diff_cls/` |
| `_fill_gaps_1/2/3.py` | 缺口补漏三轮：精确键匹配 → token/双向包含 → 跨包复用（产出 `gap_fill*.json`） | `py _fill_gaps_1.py` |

**CurseForge 元数据不用开浏览器**：CF 网页与 `/download/<fileId>` 有 Cloudflare 挑战（脚本直连 403），但
`https://api.cfwidget.com/minecraft/mc-mods/<slug>` 这个镜像 API 可直连，直接给出**全部文件**（fileId /
文件名 / 发布时间 / 版本 / release 类型）与项目最后更新时间；下载走
`https://mediafilez.forgecdn.net/files/<id前4位>/<id后4位>/<文件名>`（**文件名必须与 CF 上完全一致**，
否则 403；这是踩过的坑）。

**下载踩坑**：CurseForge 的网页与 `/download/<fileId>` 端点有 Cloudflare 挑战（脚本直连 403），
只有 `mediafilez.forgecdn.net/files/<id前4位>/<id后4位>/<文件名>` 能直连；`edge.forgecdn.net` 对部分
老文件 404/403。`archive.teacon.cn` 用 urllib 会 404 而 curl 正常——遇该站先用 curl 落地再入库。

## 清单与索引

| 脚本 | 作用 |
|---|---|
| `_index_packs.py` | 按 PCL2 已安装整合包提取 mod 清单；元数据支持 **5 种格式**：`neoforge.mods.toml` / `mods.toml` / `fabric.mod.json` / **`mcmod.info`（1.12.2 老包）** / `MANIFEST.MF` |
| `_index_local_jars.py` | 索引四个已处理包的本地 jar（分节解析，跳过 `dependencies` 段，避免把依赖 modId 当自己） |
| `_annotate_repos.py` | 给"新仓库清单"加备注列：误匹配（指到 issue 仓/模板仓）+ 值得深挖的候选 |

## 四个包 → 仓库（第一轮）

| 脚本 | 作用 |
|---|---|
| `_pack_research.py` | Modrinth `modrinth.index.json` → 仓库（Modrinth API + jar 元数据 Range 提取 + `git ls-remote` 校验） |
| `_atm10_resolve.py` / `_atm10_search.py` | CurseForge manifest → 名称 → 仓库 |
| `_jar_meta.py` | 用 **HTTP Range** 只读 jar 尾部：EOCD → 中央目录 → 单个条目（拉 `mods.toml`），避免整包下载 |
| `_bulk_clone.py` / `_clone_refs.sh` | 批量稀疏克隆（`--depth 1 --filter=blob:none --sparse`，只留源码，省磁盘） |
| `_make_cards.py` | 生成速览卡片（纯 `os.walk`，不用 `find`——Windows 上会撞 `System32\find.exe`） |
| `_build_final.py` / `_gen_table.py` / `_gen_tables2.py` / `_gen_final_deliverables.py` | 对照表 / 总表 / 总索引生成 |
| `_batch_meta_par.py` | 并发批量取 jar 元数据（线程池版 `_jar_meta.py`） |
| `_apply_mappings.py` / `_verify_candidates.py` | 映射修正（含人工 `CURATED` 覆盖表）与候选校验 |

## 已知的"假绿"陷阱（这些脚本踩过）

1. **`rstrip('.git')` 是字符集不是后缀** → `ImmediatelyFast` 被截成 `ImmediatelyFas`，产生 26 个假死链。用 `re.sub(r'\.git$', '', s)`。
2. **GFM 表格外，`subprocess.find` / `wc` 在 Windows 解析到 `System32`** → 卡片曾统计出"0 个文件"。改纯 Python。
3. **反编译产物不是源码**：CFR 会把合成类并进外层文件，Kotlin 产物还有 `Intrinsics`/`Companion` 噪声；
   引用行号只在**本目录的反编译产物**内有效，与上游仓库行号不同。
4. **核对分母**：任何"带仓库 X/Y"的结论都要用两个独立信号确认（见 `spirepowers` 的"0 条测试假绿"教训）。
