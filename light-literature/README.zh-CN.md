# litsearch — 文献检索 skill（中文版）

一个独立的、中英双语的“研究方向 → 文献地图”skill。输入一个研究方向，输出：

- 可复现的检索协议（问题、概念块、检索式、数据源、时间/语言限制）；
- 多源检索 + 去重 + 透明打分；
- 标题/摘要筛选表（带 reason code 和证据深度）；
- 多轮前向/后向引用扩展 + 共被引/桥接分析；
- 中英双语报告、证据矩阵、阅读路径、gap 候选和 idea cards；
- Phase 2：`Literature/<文章>/` 文件夹，含 PDF、宿主模型转写、翻译、来源映射和精读笔记。

> **阶段边界**：Phase 1 是检索、筛选、引用分析和双语报告；Phase 2 是
> `literature build` 准备页面资产 + 宿主模型逐页转写、翻译和精读。

完整的逻辑、脚本/agent 边界和取舍见 [ARCHITECTURE.md](ARCHITECTURE.md)。

**默认零注册。** 默认检索用 OpenAlex、Crossref、Europe PMC、OpenAIRE，不需要任何 key；
key 只是重度使用的增强项。Semantic Scholar 没有 key 会被跳过。

---

## 快速开始（离线 demo）

```bash
python run_litsearch.py demo --out runs/demo --lang both
```

打开：

- `runs/demo/report.zh.md`
- `runs/demo/report.en.md`
- `runs/demo/report.bilingual.md`

Demo 使用**合成记录**，只用于验证报告契约，不能当作真实文献引用。

---

## 安装

需要 Python 3.11+、`requests`、`pypdfium2` 和 `Pillow`。

```bash
pip install -e .
litsearch --help
```

**宿主模型解析**默认用 `pypdfium2` 做页面渲染和图片抽取，
它会作为普通依赖自动安装。`pypdfium2` 是 Apache-2.0/BSD-3-Clause 系许可，不会给
MIT 核心引入 AGPL 义务。

可选 PyMuPDF fallback（AGPL-3.0/商业双许可；只在 pypdfium2 对某个 PDF 失败，或你
更想用它的抽取器时需要）：

```bash
pip install -e ".[pdf]"
```

不安装也可以用：

```bash
python run_litsearch.py --help
```

### 作为 Claude Code skill 使用

把仓库放到 `.claude/skills/literature-search/`（项目级）或
`~/.claude/skills/literature-search/`（用户级），Claude Code 会读取其中的
`SKILL.md`。

如果 skill 在另一个项目里运行，建议先安装一次：

```bash
pip install -e /path/to/light-literature
litsearch --help
```

或者用绝对路径调用：

```bash
python /path/to/light-literature/run_litsearch.py --help
```

下文命令用 `python run_litsearch.py` 简写；在别的项目里请换成 `litsearch`
或绝对路径。

---

## 真实检索流程

### 1. 生成并编辑 plan

```bash
python run_litsearch.py plan init \
  --direction "retrieval augmented generation for literature review" \
  --domain cs --lang both \
  --out runs/my-run/query_plan.json
```

编辑 `query_plan.json`：

- 3–5 个可回答的问题，每个都要有 `operationalization`；
- 2–3 个概念块（同义词、缩写、连字符/空格变体）；
- 3 个 lens（基础/前沿、批判/方法、实践/邻近领域）；
- 纳入/排除标准、年份、语言、数据源、预算。

严格校验：

```bash
python run_litsearch.py plan validate --plan runs/my-run/query_plan.json --strict
```

可参考 `references/query-plan.example.json`。

### 2. 检索

```bash
python run_litsearch.py search \
  --plan runs/my-run/query_plan.json \
  --run runs/my-run \
  --sources europepmc,pubmed,arxiv,crossref \
  --max-per-source 80
```

可选 key 数据源：

```bash
python run_litsearch.py search ... --sources openalex,semantic_scholar --enable-optional
```

### 3. 筛选

```bash
python run_litsearch.py screen prescreen --run runs/my-run
```

按 `templates/prompts/screening_instructions.md` 的 rubric 编辑
`runs/my-run/screening.csv` 或 `.jsonl`。

```bash
python run_litsearch.py screen validate --run runs/my-run
```

### 4. 引用扩展

```bash
python run_litsearch.py citations expand \
  --run runs/my-run --seeds 10 \
  --sources europepmc,opencitations \
  --directions forward,backward
```

定向扩展：

```bash
python run_litsearch.py citations expand --run runs/my-run \
  --seed-paper-ids p_ab12cd34ef56,p_7890abcd1234
```

然后对新记录再跑一次：

```bash
python run_litsearch.py screen prescreen --run runs/my-run
```

可选：共被引 / 桥接分析：

```bash
python run_litsearch.py citations analyze --run runs/my-run
```

输出 `citation_analysis.json`：共被引文献、桥接论文、seed 对交集。

### 5. 可选：补 OA PDF 链接

```bash
python run_litsearch.py oa enrich --run runs/my-run --limit 20
```

用 Unpaywall，只需要 `LITSEARCH_MAILTO`（或 `UNPAYWALL_EMAIL`），不需要注册。
会填充 `papers.jsonl` 里的 `pdf_url`、`oa_status`、`license`。

### 6. 可选：下载 OA PDF

```bash
python run_litsearch.py pdf fetch --run runs/my-run --limit 20
```

只下载确认 OA 或位于已知 OA 主机的 PDF（arXiv、ACL Anthology、Europe PMC/PMC、
MDPI、Frontiers、Research Square、Zenodo、HAL、OpenReview、PMLR、CVF、JMLR）。
会校验 `%PDF` magic bytes，输出：

- `runs/my-run/pdfs/<paper_id>.pdf`
- `runs/my-run/pdf_manifest.json`，状态包括 `downloaded` / `already_present` /
  `blocked` / `not_pdf` / `unavailable`。

**不绕过付费墙，也不伪装浏览器绕过出版社反爬。** DOI 只是入口，不保证有可下载 PDF：
MDPI 可能 403，OUP 可能返回 HTML 落地页，闭源论文没有合法的自动副本。
下载不到会记录原因，run 继续。

### 7. 饱和判断与综合

```bash
python run_litsearch.py metrics saturation --run runs/my-run
```

按 `templates/prompts/synthesis_instructions.md` 写
`runs/my-run/synthesis.json`。每个论点必须用 `[[p_id]]` token 引用
`papers.jsonl` 里的真实记录；未知 ID 会直接报错。

### 8. 渲染与校验

```bash
python run_litsearch.py report --run runs/my-run --lang both
python run_litsearch.py verify --run runs/my-run
```

---

## Phase 2 — 宿主模型阅读

导入本地 PDF，或从已筛选的检索结果准备论文：

```bash
python run_litsearch.py literature add --pdf /path/paper.pdf --out /project/Literature
python run_litsearch.py literature build --run runs/my-run --out /project/Literature --status include --include-maybe
```

`add` 可补 `--title`、`--authors`、`--year`、`--doi`。
`--dry-run` 只预览选择和页数，不写输出、不下载 PDF。
`--force-prepare` 刷新页面资产和任务，保留已完成的正文、翻译和笔记。
重复导入、部分构建会复用原文件夹，索引保留其他论文。

脚本负责复制 PDF、渲染页面、抽取图片、生成 `MODEL_PARSE.md` 和
`AGENT_TASKS.md`；**宿主多模态模型**负责实际逐页转写、翻译、精读。
不需要解析服务密钥、额度或路线选择。仅生成任务文件不代表阅读完成。

```text
Literature/
├─ README.md / manifest.json
└─ <year>_<author>_<title>/
   ├─ paper.pdf
   ├─ pages/ / images/ / pdf_assets.json
   ├─ meta.json / MODEL_PARSE.md / AGENT_TASKS.md
   ├─ paper.md / source_map.json / model_parse_notes.md
   ├─ paper.zh.md / translation_notes.md
   ├─ reader.bilingual.md     # 按需生成
   └─ note.md                # 可选英文版 note.en.md
```

宿主模型依次使用 [转写提示词](templates/prompts/parse_pdf_model.md)、
[翻译提示词](templates/prompts/translate_paper.md)、
[精读提示词](templates/prompts/paper_note.md) 和
[中文笔记模板](templates/paper-note-template.zh.md)。
段落、图表、公式保留稳定来源 ID；低置信度公式保留原图，避免猜写。
笔记重建研究路径、承重设计、可计算公式示例和证据边界。

[阅读工作流](references/reading-workflow.md) 对应参考了 nature-reader、
nature-paper-xray、nature-paper-card、nature-ref-verifier、
nature-academic-search 和 nature-downloader。引用字段核查和外部获取是宿主
工作流，不是新增自动核验服务。需要补充合法网页材料时可按
[light-crawl 衔接说明](references/light-crawl.md) 调用本机
`D:\Light-Science\light-crawl`。

宿主工作结束后重跑命令刷新状态。`already_present` 表示已有正文；
`model_parse_required` 表示仍需模型阅读；`pdf_missing` 表示先补 PDF。
页面渲染异常单独记入 `assets_status`。文件存在不代表全文完整或科学判断正确。
旧正文和笔记继续复用，下游分析前核对来源锚点。

### 直接使用 Literature

PDF、原文、翻译、来源映射和笔记统一保存在 `Literature/<论文>/`。
通过 `README.md` 查看论文索引，`manifest.json` 记录最近一次构建。
直接阅读和修改原文件，保持图片相对路径有效；跨论文综合基于这些阅读资产
及 `runs/` 中的规范记录开展，无需维护另一份文献库。

## 数据源

| 数据源 | Key | 作用 |
|---|---|---|
| OpenAlex | 可选；无 key 有每日预算 | 全学科发现 + 引用图 |
| Crossref | 无（建议 `mailto`） | 通用元数据、DOI、参考文献 |
| Europe PMC | 无 | 生物医学 + 引用扩展 |
| OpenAIRE | 无 | 全学科仓库聚合、OA 补充 |
| PubMed | 可选 `NCBI_API_KEY` | 生物医学 recall、MeSH |
| arXiv | 无 | CS/物理/数学预印本 |
| OpenCitations | 无 | 基于 DOI 的前向/后向引用边 |
| DOAJ | 无；**实验性** | ~900–1000 万 OA 文章；上游可能 502 |
| DBLP | 无；**实验性** | CS 会议/期刊；可能触发 Anubis 反爬 |
| Unpaywall | 只需 email，无需注册 | 按 DOI 找 OA PDF |
| Semantic Scholar | 可选 `S2_API_KEY`；无 key 自动跳过 | 引用上下文/intent |

**默认数据源不需要任何 key。** 默认 keyless bundle 是
`openalex, crossref, europepmc, openaire`；CS 加 `arxiv`，生物医学加 `pubmed`。
Semantic Scholar 没有 `S2_API_KEY` 会被跳过。DOAJ/DBLP 是实验性源，失败只记录
degraded，不会让整个 run 失败。

推荐配置：**什么都不用配**。重度使用再加一个免费 `OPENALEX_API_KEY`；需要引用上下文
再加 `S2_API_KEY`。`LITSEARCH_MAILTO` 不是密钥，只是 polite 标识，同时用于 Unpaywall。
未设置时会使用项目占位邮箱 `litsearch@users.noreply.github.com`，维护者可替换成项目专用邮箱。

覆盖范围大致是：OpenAlex 全学科广覆盖（约 3.24 亿 curated works + 大量扩展记录）；
OpenAIRE 聚合各学科仓库；Semantic Scholar 强在 CS/生物医学（约 2.14 亿论文、25 亿引用）；
PubMed/Europe PMC 是生物医学；arXiv 是 STEM 预印本；Crossref 是 DOI 元数据；
OpenCitations 是基于 DOI 的引用边。

**双语输出 ≠ 双语检索。** 报告、筛选表、synthesis 是双语的，但默认数据源是英文索引。
中文方向要在 concept_blocks 里补英文规范词（或用 `plan init --direction-en ...`）；
中文-only 查询会被英文索引当成精确短语，召回的是噪声。CNKI/万方不覆盖。

**不覆盖**：CNKI/万方、Web of Science/Scopus/Embase、IEEE/ACM 全文、
Crossref 之外的图书/专著、标准/专利、大部分灰色文献、临床试验注册库、非英语地区文献。
闭源库不覆盖，也不把“去别的平台手动检索”这种任务交给用户。

两个容易混淆的点：

- **IEEE Xplore 是出版社数据库**：有官方 API，申请后可免费拿元数据/摘要，
  但付费全文需要机构订阅。当前适配器还没接；有 DOI 的 IEEE 论文会通过
  OpenAlex/Crossref/Semantic Scholar 部分覆盖。
- **CCF 不是数据库**，是推荐会议/期刊等级目录（A/B/C）。不能“搜 CCF”；
  正确做法是用 DBLP/OpenAlex/Semantic Scholar 搜论文，再按 CCF 等级过滤/标注。
  DBLP 是最好的免费 CS 会议/期刊索引，但它的 API 目前可能被 Anubis 反爬挡住；
  适配器会记录 `blocked`，不会假装成功。

详见 [references/sources.md](references/sources.md)。

环境变量见 `.env.example`。不要把 key 提交到仓库。

加载顺序：仓库根目录的 `.env`（或 `LITSEARCH_ENV_FILE` 指定的文件）→ 进程环境变量。
`.env` 已被 `.gitignore` 排除。填 `OPENALEX_API_KEY` 和 `LITSEARCH_MAILTO` 即可；
Semantic Scholar 是可选源，不在默认数据源里，不想注册可以完全跳过。

---

## 输出结构

```text
runs/<run>/
├─ query_plan.json
├─ compiled_queries.json
├─ search_log.json          # 源运行 + source health + coverage 曲线
├─ merge_log.json
├─ papers.jsonl
├─ screening.csv / screening.jsonl
├─ citation_edges.jsonl
├─ citation_analysis.json   # 共被引 / 桥接
├─ citation_seeds.json      # 每轮使用的 seeds
├─ saturation.json          # 轮次产出 + coverage/plateau
├─ prisma_s_audit.json      # 16 项 PRISMA-S-informed audit
├─ synthesis.json
├─ oa_enrich.json           # Unpaywall enrichment 摘要
├─ pdf_manifest.json        # OA PDF 下载状态
├─ pdfs/                    # 已下载 PDF
├─ report.en.md / report.zh.md / report.bilingual.md / report.md
└─ exports/
```

---

## 测试

```bash
python -m unittest discover -s tests -t . -v
```

离线测试覆盖归一化、去重、查询编译、打分、筛选、demo 渲染、导出和引用 token 解析。

---

## 已知限制

- PRISMA-informed，不是 PRISMA-compliant。
- 只做标题/摘要筛选，不做全文质量评估。
- 引用扩展受 seed/轮次预算限制，不是穷尽检索。
- 不抓取 CNKI/万方/Web of Science/Scopus；闭源库不覆盖，没有手动检索步骤。
- Phase 2 需要宿主多模态模型实际完成转写、翻译和精读。
- API 元数据可能不完整；每条记录都有 provenance 和 evidence depth。

检索层现在包含：source capability matrix、provider health（EWMA）、coverage/rediscovery 曲线、BM25 + concept rerank、citation/recency strata、PRISMA-S-informed 16 项 audit。

---

## License

MIT。
