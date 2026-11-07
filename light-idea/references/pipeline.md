# 与 light-literature 衔接

## 实际上游格式

此接口于 2026-11-06 按本包 light-literature 0.12.0 和实际 Design 导入再次检查，而非假定存在统一的“idea API”。skill 名是 `literature-search`，项目目录名是 `light-literature`。

| 输入 | 使用方式与限制 |
|---|---|
| `<search-run>/papers.jsonl` | 规范记录、`paper_id`、DOI、摘要、来源记录、撤稿/预印本标记；优先作为 run 论文表 |
| `<search-run>/exports/papers.json` | 缺少 JSONL 时的兼容输入；不要同时算两份 |
| `screening.csv` 或 `screening.jsonl` | 读取较新文件，两个文件均记录指纹；同时间而关键决策冲突需解决。保留决定/原因，规则预筛不是人工验收 |
| `query_plan.json` | 问题、概念块、范围、预算和纳排条件 |
| `synthesis.json` | `gaps`、`idea_cards` 是初步假设；保留 `[[p_...]]`，回原文检查 |
| `citation_edges.jsonl`、`citation_analysis.json` | 定位最近工作、桥接文献和前后向扩展；连接不是因果证据 |
| `search_log.json`、`saturation.json` | 判断原检索覆盖；停滞或 provisional 不能证明完整 |
| `Literature/manifest.json` | 全库 `entries[]` 提供 `paper_id` 与相对 `folder`；本批计数不是全库大小，完整性明显缺失时先修复；不能据此声称已阅读全文 |
| `Literature/<folder>/meta.json` | 单篇元数据；与 run 冲突时保留冲突，不能猜哪个正确 |
| `paper.md`、`paper.pdf`、`source_map.json` | 原文、图页与锚点；`source_map` 可缺省，没有时用可核对的章节/图表/行号 |
| `note.md`、`note.en.md`、`paper.zh.md` | 精读笔记/翻译；继承作者与分析者区分，决定性主张回原文 |

文件存在、manifest 中的 note_status、上游 evidence_depth 都不是本轮已读证明。导入器给出的 `reading_status` 始终为 `not_assessed`。只有宿主实际打开相应材料并核对锚点后，才能在 evidence ledger 记录已检查事实。

## 选择输入

1. 用户给了路径就使用该路径；否则先定位真实项目的 `Literature/` 和相关 `Literature/Searches/SEARCH-.../`。已有外部 `runs/<name>/` 原地兼容，不依赖历史本机源码路径。
2. 有多个 run 时，先根据 topic、query plan 与用户上下文选相关的一次。不能把每个 run 的摘要、分数和论文不加区分地拼接。
3. `Literature/` 可混有不相关的文章，必要时先按 `paper_id` 选择。目录名和文件修改时间不是主题相关性证据。
4. 只有笔记或一篇论文时可以直接阅读开展工作，不必为使用此技能重跑完整检索。缺少上游结构文件就手动维护来源和证据。

## 导入命令

```powershell
python "<skill-root>/scripts/idea_bridge.py" ingest --literature "<project>/Literature" --out "<project>/Idea/IDEA-0001_选题主题"
python "<skill-root>/scripts/idea_bridge.py" ingest --run "<project>/Literature/Searches/SEARCH-0001_检索主题" --out "<project>/Idea/IDEA-0001_选题主题"
python "<skill-root>/scripts/idea_bridge.py" ingest --literature "<upstream>/Literature" --run "<project>/Literature/Searches/SEARCH-0001_检索主题" --paper-ids p_a,p_b --out "<project>/Idea/IDEA-0001_选题主题"
```

支持只提供一个 `meta.json` 所在的单篇目录，也支持把上游项目根目录传给 `--literature`，此时定位其 `Literature/`。无 manifest 时从直接子目录的 `meta.json` 构建索引。缺少结构化身份记录时提示错误，改用人工阅读，不从文件名伪造论文身份。

`--paper-ids` 显式选择的论文才进入上下文。默认排除 `decision=exclude`；`--include-excluded` 仅用于明确需要检查反方或背景材料的场景，状态仍原样保留。

导入器读取上游，写 `context.json` 和 `reading_queue.md`，不复制正文、不修改上游、不自动生成科学主张。不覆盖已有文件，需更新时使用新输出目录，或用 `--force` 归档旧 context 后刷新两个索引；不会覆盖已有 idea、证据或决策。所选本地 PDF 若与文献库记录的 pdf_sha256 冲突或缺失，先处理来源版本再导入。

输入索引保留 SHA-256。上游材料变化后，重新读取受影响证据，记录判断是否改变；不能只重算哈希继续沿用旧结论。`verify` 同时检查当前输入和证据独立绑定的来源字节；旧 context 归档仅保存索引而非正文备份。详细迁移见 [修订与交接](revisions-and-handoffs.md)。

同一 run 内重复出现相同 `paper_id`、身份信息相容的记录会合并，保留各次来源并提示；完全相同的重复筛选行保留一次。身份或筛选决定冲突时停止导入。不同 ID 却相同 DOI 会提示人工核对，不能算作多个独立证据。

## 跨阶段闭环

```text
light-literature: 问题 → 检索/筛选 → 阅读 → 文献地图和初步 gap
light-idea:       证据 → 研究问题 → 候选 → 查重/反证 → 取舍 → 最小验证
                                     ↑          ↓
                              问题/机制变化后补查文献
```

补查规模小就用可用的学术检索或浏览工具，记录在本轮目录；确需扩展整个文献地图时，再调用已安装的 literature-search 或上游命令，先阅读其当前说明，不假设命令未变。idea 补查不是重新自动运行全部上游流程。

## 后续交接

选中方向一般用 `design_bridge.py ingest --ideas "<IDEA>" --idea-id "<I01>" --out "<PROT/v01>"` 交给 Design，保留所选版本、竞争解释、最近工作、证据锚点、资源、pilot 和判定规则。原生导入状态是 draft，设计准备度仍需其实际工作；也可将明确未决的候选作为草稿输入，不伪装成推荐。已有研究/分析反馈时按原因循环，不固定走完线性阶段。

重要选择/修订原因、否决路径和重启条件按需交给 Memory；Leader 接实际完成范围、版本、未决项和下一步依据。此阶段产物是研究提案，未开展的验证不能写成结果。
