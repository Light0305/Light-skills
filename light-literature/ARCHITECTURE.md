# litsearch — 逻辑与架构

本文说明这个 skill 为什么这样设计、每一步在做什么、哪些部分由脚本完成、哪些部分必须由宿主 agent 完成，以及当前边界。

## 1. 定位

`litsearch` 不是 Zotero 替代品，也不是“输入关键词返回一堆链接”的搜索框。它解决的是：

> 给定一个研究方向，产出一份**可复现、可审计、带证据**的文献地图，并把其中值得读的论文变成可继续用于找 idea 的阅读资产。

它分成两个阶段，阅读结果直接保存在 Literature：

| 阶段 | 输入 | 输出 |
|---|---|---|
| Phase 1 | 研究方向 | 检索协议、候选集、筛选表、引用扩展、饱和记录、双语报告 |
| Phase 2 | 入选论文 / 用户 PDF | `Literature/<year_author_title>/`：PDF、解析 Markdown、中文翻译、综合笔记 |

核心原则：

1. **脚本确定，agent 判断。** 检索、去重、打分、报告渲染由脚本完成；问题定义、筛选判断、综合、翻译、笔记由 agent 完成。脚本不调用 LLM，不需要 LLM API key。
2. **Recall first, precision second.** 先多源广覆盖，再用筛选和分层排序收窄；不假装一次检索就完整。
3. **每条 claim 可追溯。** 报告和综合使用 `[[p_id]]` token；渲染器遇到未知 ID 直接失败。笔记要求章节/页/图/表锚点。
4. **Keyless by default.** 默认源不需要注册；key 只是重度使用或特定能力的增强。
5. **不绕过边界。** 不抓闭源库，不绕付费墙，不伪装浏览器，不把“去别的平台手动搜”甩给用户。
6. **失败要显式记录。** 源失败、PDF 不可得、缺 key、额度耗尽、解析失败都写入 manifest / 状态文件，不静默降级。

## 2. 总体流程

```text
研究方向
  ↓ plan init / validate / compile
query_plan.json + compiled_queries.json
  ↓ search（多源、去重、打分、分层）
papers.jsonl + search_log.json + merge_log.json
  ↓ screen prescreen（规则）→ agent 筛选 → screen validate
screening.csv / screening.jsonl
  ↓ oa enrich / pdf fetch（可选）
pdf_manifest.json + pdfs/
  ↓ citations expand（多轮）→ citations analyze（可选）
citation_edges.jsonl + citation_seeds.json + citation_analysis.json
  ↓ metrics saturation
saturation.json
  ↓ agent 写 synthesis.json
  ↓ report / verify
report.{en,zh,bilingual}.md + exports/
  ↓ literature build / add
Literature/<paper>/paper.pdf + paper.md + paper.zh.md + note.md
  ↓ 直接阅读、修订与跨论文综合
复用 Literature 原文件和 runs 中的规范记录
```

## 3. Phase 1：从方向到文献地图

### 3.1 问题与检索协议

`plan init` 生成 `query_plan.json`，不是直接搜关键词。一个合格 plan 包含：

- 3–5 个可回答的问题，每个有 `operationalization`（人群/任务/方法/结果/数据设定等）；
- 2–3 个概念块，每块含同义词、缩写、连字符/空格变体；
- 3 个 lens：foundations/frontier、skeptic/method、practitioner；
- 纳入/排除标准、年份、语言、数据源、预算。

`plan validate --strict` 会拒绝：

- 问题太少或没有操作化；
- 概念块不足；
- lens 不足；
- 只有泛词（如 “literature search”“systematic review” 这类假朋友）；
- 只有中文、没有英文规范词的检索块。

**为什么：** 双语输出 ≠ 双语检索。默认源是英文索引，中文-only 查询会被当成精确短语，召回噪声。中文方向要补英文规范词，或用 `--direction-en`。

`plan compile` 按源生成语法，并处理源限制（例如 OpenAIRE 的逻辑运算符上限、每源查询条数上限）。

### 3.2 多源检索

默认 keyless bundle：

```text
openalex, crossref, europepmc, openaire
```

领域 bundle：

- CS：加 `arxiv`
- biomed：加 `pubmed`

可选/实验性：

- `semantic_scholar`：没有 `S2_API_KEY` 自动跳过；
- `doaj`、`dblp`：实验性，上游可能 502 或 bot challenge，失败记为 degraded，不拖垮整个 run。

每个源适配器负责：请求、分页、字段归一化、错误记录、速率限制。HTTP 层有缓存、超时、重试、每主机最小间隔。

**为什么多源：** 单一源有覆盖偏差；OpenAlex 全学科广、Crossref 元数据全、Europe PMC/PubMed 生物医学强、OpenAIRE 聚合仓库、arXiv 预印本。多源一致性和排名也进入打分。

### 3.3 去重

去重顺序：

1. 强标识符：DOI、PMID、PMCID、arXiv ID、OpenAlex ID、Semantic Scholar ID；
2. 保守的弱匹配：标题 + 第一作者（归一化后）；
3. 记录 `merge_log.json`，保留来源 provenance。

**为什么保守：** 误合并会永久丢论文；宁可多留一条候选，也不要把两篇不同论文合并。

### 3.4 打分与分层

每篇论文的 `discovery_score` 由六部分组成：

| 组件 | 权重 | 说明 |
|---|---:|---|
| relevance | 35 | 0.6 × 概念覆盖 + 0.4 × BM25 |
| recency | 20 | 领域半衰期：CS 4 年、biomed 6、social/general 8 |
| citation impact | 15 | 年均引用，log 压缩 |
| source agreement | 10 | 多源覆盖 + 最佳排名，按 source health 加权 |
| evidence depth | 10 | full_text_link / abstract / metadata_only |
| metadata | 10 | DOI/作者/venue/年份/类型/摘要/URL 完整度 |

惩罚/奖励：

- retracted：-50
- preprint：-2
- no abstract：-5
- 近 2 年且 relevance ≥ 0.5：+5 frontier bonus

分层：

- `recent`：≤2 年
- `emerging`：≤5 年且引用少
- `high_impact`：年均引用 ≥ p75 且 ≥3 年
- `established`：其余

`select_stratified` / `select_diverse` 避免 top-N 被单一 stratum 或单一源垄断。

**为什么：** 纯引用数会埋没新论文；纯相关性会重复同一类工作；分层让“基础/前沿/批判/实践”都有位置。

### 3.5 筛选

`screen prescreen` 做确定性硬过滤（年份、语言、类型、明显不相关等）。agent 按 `templates/prompts/screening_instructions.md` 填 `screening.csv/jsonl`：

- `include` / `maybe` / `exclude`
- reason code
- evidence depth

`screen validate` 检查枚举、缺失、重复、非法组合。

**为什么：** 筛选是判断，不是脚本能替代的；但格式和硬规则可以脚本化，减少 agent 自由发挥。

### 3.6 引用扩展与饱和

`citations expand` 支持：

- backward（参考文献）
- forward（被引）
- 多轮
- 指定 seed paper IDs
- 每轮记录 `round`、provider、seed、edges
- `citation_seeds.json` 记录用过的 seed，避免重复

`citations analyze` 从已有 edges 做：

- 共被引（co-citation）
- 桥接论文（bridge）
- seed-pair 交集

`metrics saturation` 按轮次算新增/重复/低产出，状态包括：

- `no_citation_round`
- `one_round_only`
- `no_included_screening`
- `two_consecutive_low_yield`
- `max_rounds_or_budget`

**为什么：** 引用扩展很容易“越扩越多”，必须用轮次产出和预算判断何时停；没有 included screening 时不能假装饱和。

### 3.7 报告与审计

`report` 生成：

- `report.en.md`
- `report.zh.md`
- `report.bilingual.md`
- `exports/papers.csv`、`papers.json`、`references.bib`、`screening.csv`

报告包含：

- PRISMA-style counts
- 证据矩阵
- 阅读路径
- gap 候选
- idea cards
- citation graph
- 每轮 saturation
- source health
- coverage curve
- PRISMA-S-informed 16 项 audit

`verify --strict` 检查：

- 报告中的 `[[p_id]]` 是否都在 `papers.jsonl`
- PRISMA 数字是否自洽
- 双语是否齐全
- 引用 token 是否可解析

**为什么：** 报告是给人看的，但必须能被机器校验；未知 ID 直接失败，避免编造引用。

## 4. Phase 2：从论文到阅读资产

### 4.1 入口

两种入口：

```bash
# 从检索 run 构建
litsearch literature build --run runs/my-run --out /project/Literature --status include --include-maybe

# 用户自己给 PDF
litsearch literature add --pdf paper.pdf --out /project/Literature --title "..." --authors "..." --year 2024
```

每篇论文一个文件夹：

```text
Literature/<year>_<author>_<title-slug>/
├─ paper.pdf
├─ paper.md               # 宿主模型转写
├─ paper.zh.md            # 宿主模型全文翻译
├─ note.md                # 中文综合笔记
├─ images/ pages/         # 图表/页面资产
├─ meta.json
├─ AGENT_TASKS.md
├─ source_map.json
└─ MODEL_PARSE.md
```

### 4.2 PDF 获取

`pdf fetch` 只下载：

- 确认 OA 的 PDF；
- 或已知 OA 主机（arXiv、PMC/Europe PMC、MDPI、Frontiers、Zenodo、HAL、OpenReview、PMLR、CVF、JMLR 等）。

校验 `%PDF` magic bytes；有单文件大小、单文件时间、总时间上限；状态包括 `downloaded` / `already_present` / `blocked` / `not_pdf` / `unavailable`。

**不做什么：** 不绕付费墙、不伪装浏览器、不用 Sci-Hub。DOI 是入口，不保证有合法自动副本。

### 4.3 解析：宿主多模态模型

`literature build` / `add` 统一准备阅读材料：

1. 本地 `pypdfium2 + Pillow` 把每页渲染为 150 DPI PNG，并抽取图片；
2. 写 `pdf_assets.json`、`MODEL_PARSE.md` 和 `AGENT_TASKS.md`；
3. 宿主模型按 `parse_pdf_model.md` 逐页读图，写 `paper.md`；
4. 用 `source_map.json` 保存段落/图/表/公式 ID、PDF 页码或结构定位；
5. 补充 `model_parse_notes.md`，核对完整性，不可读公式保留原图。

脚本不调用模型。没有解析服务密钥、额度预算或 A/B 选择。
`--dry-run` 只预览、不写输出也不下载；`--force-prepare` 刷新资产，保留模型产物。
已存在的正文直接复用，旧来源缺锚点时由宿主核对补充，不伪造定位。

状态：`parse_status` 为 `model_parse_required` / `already_present` / `pdf_missing`；
`assets_status` 单独记录 `ok` / `partial` / `unavailable` / `not_prepared`。
渲染不可用时可直接读取 PDF，生成任务不代表解析完成。
渲染器默认 `pypdfium2`，`.[pdf]` 的 PyMuPDF 为可选 fallback。

[reading-workflow.md](references/reading-workflow.md) 说明六个参考技能的落点：
可回溯 reader、研究路径重建、证据卡片、字段核验、检索事实核对、合法全文获取。
[light-crawl.md](references/light-crawl.md) 说明可选本地爬取衔接；通过证据文件交接，
没有硬依赖，也不自动扩展授权或数据源覆盖。

### 4.4 翻译

宿主 agent 按 `templates/prompts/translate_paper.md` 写 `paper.zh.md`：

- 全文翻译，不是摘要；
- 保留来源 ID，按需生成中英对照 reader；
- 保留标题、公式、表格、图注、引用；
- 技术术语首次出现保留英文括号。

### 4.5 综合笔记

宿主 agent 按 `templates/paper-note-template.zh.md` 和 `templates/prompts/paper_note.md` 写 `note.md`：

第 0–16 节：

0. 一句话结论
1. 识别与来源
2. 问题、动机与研究问题
3. 作者声称的贡献
4. 贡献 → 证据矩阵
5. 方法重建
6. 数据与实验设计
7. 关键图表
8. 我相信什么、怀疑什么、什么改变了
9. 批判层（作者局限 / 分析者批评 / 3 条红旗 / 不确定性）
10. 与先行工作的关系
11. 可复用资产
12. 缺口与开放问题
13. 想法卡（3–5 个可检验 idea）
14. 复现清单
15. 关键引文与公式
16. 链接与阅读日志

强制规则：

- `[作者]` 与 `[分析者]` 分开；
- 每个事实性 claim 有锚点；
- 每张主图/表嵌入，并写“想支持什么 / 实际显示什么 / 反读”；
- 最多 3 条红旗，必须威胁承重 claim；
- idea card 必须有 closest prior art、delta、why now、feasibility、discriminating experiment、expected negative result；
- 不能从材料判断时写“材料不足，无法判断”。

**为什么：** 普通摘要无法支持后续找 idea；笔记必须把“论文说了什么”和“我认为什么”分开，否则会把作者 claim 当成事实。

## 5. Literature：统一工作目录

全文、翻译、来源映射、图表和笔记放在同一个论文文件夹里，直接阅读和修改。
`README.md` 是所有已知论文的索引；`manifest.json` 记录最近一次构建结果。
不另外复制一套阅读库，也没有库之间的同步或覆盖规则。

跨论文综合由宿主模型读取已有笔记及原始证据，再结合 `runs/` 中的规范记录完成。
结论保留来源锚点；发现证据不足时定向补检索或补读全文。主题关联和持续监控
不因删除导出层而自动实现，仍按用户任务开展。

## 6. 脚本与 agent 的边界

| 层 | 谁做 | 产出 |
|---|---|---|
| 问题定义、概念块、lens | agent + user | `query_plan.json` |
| 检索式编译 | 脚本 | `compiled_queries.json` |
| HTTP、分页、归一化、缓存 | 脚本 | `search_log.json` |
| 去重、打分、分层 | 脚本 | `papers.jsonl` |
| 硬筛选 | 脚本 | 预筛选结果 |
| 标题/摘要筛选判断 | agent | `screening.csv/jsonl` |
| 引用扩展、饱和计算 | 脚本 | `citation_edges.jsonl`、`saturation.json` |
| 综合、gap、idea cards | agent | `synthesis.json` |
| 报告渲染、校验 | 脚本 | `report.*`、`verify` |
| PDF 下载 | 脚本 | `pdfs/`、`pdf_manifest.json` |
| PDF 页面渲染与资产准备 | 脚本 | `pages/`、`images/`、任务与资产清单 |
| 模型解析、翻译、笔记 | agent | `paper.md`、`paper.zh.md`、`note.md` |

**边界原则：** 任何需要判断、需要写自然语言、需要读图的部分交给 agent；任何需要可复现、可校验、可缓存的部分交给脚本。

## 7. 反造假与失败哲学

- `[[p_id]]` token 只能引用 `papers.jsonl` 的真实记录；未知 ID 渲染失败。
- 笔记必须锚定章节/页/图/表/公式；不能锚定就写“材料不足”。
- 引用扩展记录每轮 seed 和 edge 来源，不把旧边重复计入新一轮。
- 源失败记为 `degraded` / `blocked` / `error`，不假装成功。
- PDF 下载失败记录 `unavailable` / `blocked` / `not_pdf`，不把 HTML 落地页当 PDF。
- 缺 PDF 明确标记；页面渲染失败仍生成宿主任务，记录原因并直接核对 PDF。
- `verify --strict` 检查引用、PRISMA 数字、双语完整性。

## 8. 重要设计取舍

| 取舍 | 选择 | 原因 |
|---|---|---|
| Keyless vs 覆盖 | 默认 keyless，可选 key | 降低使用门槛；重度用户再加 OpenAlex/S2 key |
| 多源 vs 噪声 | 多源 + 去重 + 分层 | 先保 recall，再用筛选和排序收窄 |
| 引用数 vs 新论文 | 六组件打分 + frontier bonus | 避免纯引用数埋没前沿工作 |
| 引用扩展 vs 饱和 | 多轮 + 预算 + 产出判断 | 防止无限扩张，也不假装“已穷尽” |
| PDF 解析 | 宿主多模态模型 | 单一路线，来源锚定，减少外部依赖 |
| PyMuPDF vs pypdfium2 | pypdfium2 默认，PyMuPDF 可选 | pypdfium2 许可宽松、自动安装；PyMuPDF AGPL |
| 文献存储 | Literature 原文件 | 保留完整阅读证据，避免重复副本与同步冲突 |
| 中文输出 vs 英文检索 | 双语输出，英文规范词检索 | 默认源是英文索引；中文-only 召回噪声 |

## 9. 已知边界

- PRISMA-informed，不是 PRISMA-compliant。
- 只做标题/摘要筛选，不做全文质量评估。
- 引用扩展受 seed/轮次/预算限制，不是穷尽检索。
- 不覆盖 CNKI/万方、Web of Science/Scopus/Embase、IEEE/ACM 全文、图书/专著、标准/专利、大部分灰色文献、临床试验注册库、非英语地区文献。
- 闭源库不抓取；没有“去别的平台手动检索”的交接。
- API 元数据可能不完整；每条记录有 provenance 和 evidence depth。
- 转写质量依赖宿主模型、材料清晰度及 PDF 复杂度；状态存在不等于质量验收。
- 没有 Zotero 集成：Zotero 是文献库/PDF 管理，不是 discovery 引擎；本 skill 的 `Literature/` 是可移植的文件结构。

## 10. 当前状态与扩展点

- 版本：0.11.0
- 离线测试：见 tests/
- 默认页面渲染器：pypdfium2 5.9.0
- 可扩展：
  - 新 source adapter（IEEE、CORE、bioRxiv/medRxiv、SSRN 等）
  - 全文筛选/质量评估
  - 可选 Zotero 导入/导出（不作为 discovery）
  - 更多语言的检索规范词与本地化模板

## 11. 命令速查

```bash
# Phase 1
litsearch plan init --direction "..." --domain cs --lang both --out runs/my/query_plan.json
litsearch plan validate --plan runs/my/query_plan.json --strict
litsearch plan compile --plan runs/my/query_plan.json --out runs/my/compiled_queries.json
litsearch search --plan runs/my/query_plan.json --run runs/my
litsearch screen prescreen --run runs/my
litsearch screen validate --run runs/my
litsearch oa enrich --run runs/my --limit 20
litsearch pdf fetch --run runs/my --limit 20
litsearch citations expand --run runs/my --seeds 10
litsearch citations analyze --run runs/my
litsearch metrics saturation --run runs/my
litsearch report --run runs/my --lang both
litsearch verify --run runs/my --strict

# Phase 2
litsearch literature build --run runs/my --out /project/Literature --status include --include-maybe
litsearch literature add --pdf paper.pdf --out /project/Literature
# agent writes paper.zh.md + note.md

# 诊断
litsearch doctor
litsearch sources
litsearch status --run runs/my
```
