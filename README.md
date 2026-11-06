<div align="center">

<img src="assets/logo.png" alt="Light Skills logo" width="170">

# Light Skills

**面向科研、竞赛与创新项目的 AI 全流程技能包**

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/skills-23-5B6FE0.svg" alt="23 skills">
  <img src="https://img.shields.io/badge/Claude%20Code-ready-8AA0FF.svg" alt="Claude Code ready">
  <img src="https://img.shields.io/badge/Codex-ready-FFA63D.svg" alt="Codex ready">
  <img src="https://img.shields.io/badge/OpenCode-ready-22C55E.svg" alt="OpenCode ready"><br/>
  <img src="https://img.shields.io/badge/LaTeX-typesetting-008080.svg" alt="LaTeX typesetting">
  <img src="https://img.shields.io/badge/Python%20%2B%20R-figures-7C3AED.svg" alt="Python and R figures">
</p>

<p><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

</div>

---

## 这个项目能帮你做什么？

Light Skills 是一套公开、通用、领域无关的 AI skill 包，用来把一个研究或创新项目从“模糊想法”推进到“可检查的交付物”。

它适合这些场景：

| 你现在的需求 | Light Skills 会怎么帮 |
|---|---|
| 我只有一个研究方向 | 追问目标、约束、数据来源和评价标准，再拆成阶段计划 |
| 我有一个 idea，但不知道新不新 | 检索相似工作、拆 target/background、找最强反例和审稿人攻击点 |
| 我要做实验/数据分析 | 设计数据流、实验矩阵、脚本、自测、结果解释和鲁棒性检查 |
| 我要写英文论文 | 组织故事线、图表、引用核查、LaTeX 排版、投稿前检查 |
| 我要画科研图 | 用 Python/R 程序化出图，检查尺寸、字号、色盲安全、视觉诚实 |
| 我要做竞赛/项目展示界面 | 设计 frontend demo、系统结构、交互页面和展示材料 |
| 我要准备专利/软著材料 | 生成交底书草案、技术方案、实施例、软著文档清单 |
| 我要跨对话继续项目 | 用项目台账记录目标、决策、产物、未验证声明和下一步 |

## 为什么适合科研项目？

- **先读再写**：先读文件、数据、日志和论文源，再判断下一步。
- **查不到就标 unknown**：事实、DOI、链接、期刊规则和软件版本不靠猜。
- **图表必须可复现**：论文图、数据图、实验图走 Python/R 程序化生成。
- **关键节点问用户**：选题、创新性、证据强度、投稿目标和继续投入都应有人确认。
- **不依赖私有知识库**：公开版不要求 MCP 或本地数据库；最新信息在任务现场核查。

## 先安装

先进入仓库目录：

```powershell
git clone https://github.com/Light0305/Light-skills.git
cd Light-skills
$env:PYTHONUTF8="1"
```

### Codex

```powershell
# 项目级：$REPO\.agents\skills
$env:PYTHONUTF8="1"
python scripts\bootstrap_agent_skills.py --targets agents --mode auto --force

# 全局级：$HOME\.agents\skills
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.agents\skills\"
```

### Claude Code

```powershell
# 项目级：$REPO\.claude\skills\<skill>\SKILL.md
$env:PYTHONUTF8="1"
python scripts\bootstrap_agent_skills.py --targets claude --mode auto --force

# 全局级：$HOME\.claude\skills
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.claude\skills\"
```

### OpenCode

```powershell
# 项目级：$REPO\.opencode\skills\<skill>\SKILL.md
$env:PYTHONUTF8="1"
python scripts\bootstrap_agent_skills.py --targets opencode --mode auto --force

# 全局级：$HOME\.config\opencode\skills
New-Item -ItemType Directory -Force "$HOME\.config\opencode\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$HOME\.config\opencode\skills\"
```

安装后检查：

```powershell
$env:PYTHONUTF8="1"
python scripts\bootstrap_agent_skills.py --check-only
```

## 环境要求

### 基础环境

- Git
- Python 3.10+
- Windows 上运行 Python 前建议设置：`$env:PYTHONUTF8="1"`

### LaTeX 环境

```powershell
winget install --id MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements
latexmk -v
pdflatex --version
xelatex --version
biber --version
```

用于论文排版、PDF 编译、模板检查。`light-typesetting` 支持 `latexmk`、pdfLaTeX、XeLaTeX、LuaLaTeX、BibTeX、Biber；如果本机缺工具，会标记 `UNAVAILABLE`，不会假装已经排版成功。

### R 环境

```powershell
winget install --id RProject.R --accept-package-agreements --accept-source-agreements
Rscript -e "install.packages(c('ggplot2','scales'), repos='https://cloud.r-project.org')"
$env:PYTHONUTF8="1"
python skills\light-figure\scripts\r_ggplot.py --detect
```

用于 ggplot2 科研图。没有 R 时，图表技能应先问你：继续用 Python 诚实降级，还是安装/配置 R。

## 从哪里开始？

你可以按当前状态直接复制下面的 prompt：

| 当前状态 | 建议入口 |
|---|---|
| 只有方向 | `/light-orchestrator 我想把这个方向做成可投稿英文论文。请先问必要问题，再拆阶段、产物、风险和用户确认点。` |
| 已有 idea | `$light-idea-critique 批判这个 idea：创新性、可证伪性、相似工作、最强反例、审稿人风险和验证路线。` |
| 已有项目文件 | `$light-file-reading 先读取这个项目目录，列出关键文件、已完成内容、未验证声明、风险和下一步。` |
| 要查文献 | `$light-literature-search 围绕这个问题做检索策略、关键词扩展、证据地图和相关工作边界。` |
| 要做实验 | `$light-research-plan 给出实验矩阵、数据需求、评价指标、失败条件和最小可行验证。` |
| 要画图 | `$light-figure 基于这些数据规划论文图，要求程序化生成、可复现、色盲安全、标注清楚。` |
| 要写论文 | `$light-paper-writing 根据已有证据组织英文论文结构、贡献、局限性和自审清单。` |
| 要排版投稿 | `$light-typesetting 基于当前 LaTeX 源、图、BibTeX 和期刊模板做可复现编译与投稿前检查。` |
| 要做界面 | `$light-frontend-design 为这个科研/竞赛项目设计 demo 页面、组件结构、交互和展示重点。` |

## 技能地图

| 模块 | 技能 |
|---|---|
| 总控与连续性 | `light-orchestrator`、`light-memory-pm`、`light-file-reading`、`light-project-structure` |
| 想法与文献 | `light-literature-search`、`light-idea-generation`、`light-idea-critique`、`light-research-plan` |
| 数据与实验 | `light-data-engineering`、`light-experiment-coding`、`light-result-analysis` |
| 论文交付 | `light-paper-writing`、`light-citation`、`light-consistency`、`light-typesetting`、`light-venue-matching`、`light-review-rebuttal` |
| 图表与展示 | `light-figure`、`light-frontend-design`、`light-system-design` |
| 诚信与成果转化 | `light-research-ethics`、`light-patent-disclosure`、`light-software-copyright` |

## 完整技能一览

| 技能 | 主要用途 | 典型产出 |
|---|---|---|
| [`light-orchestrator`](skills/light-orchestrator) | 总控入口：理解任务、追问必要信息、选择技能链路、设置用户确认点 | 阶段计划、技能路由、决策检查点、工作流台账 |
| [`light-memory-pm`](skills/light-memory-pm) | 项目台账与跨对话续接，不把私人记忆写进公开仓库 | 项目卡、交接卡、决策日志、续接提示 |
| [`light-file-reading`](skills/light-file-reading) | 读取论文、PDF、Word、PPT、表格、图片和项目文件 | 文件清单、理解笔记、抽取质量报告、未核查声明列表 |
| [`light-project-structure`](skills/light-project-structure) | 搭建和治理科研/软件项目目录，让产物可维护、可复现 | 项目骨架、目录规范、治理策略、结构检查 |
| [`light-literature-search`](skills/light-literature-search) | 制定检索策略、扩展关键词、追踪证据边界和相关工作 | 检索式、证据地图、文献表、PRISMA 式流程记录 |
| [`light-idea-generation`](skills/light-idea-generation) | 从文献缺口、交叉领域和约束条件中生成候选研究 idea | idea 卡、缺口证据、谱系分析、候选排序 |
| [`light-idea-critique`](skills/light-idea-critique) | 批判 idea 的创新性、可证伪性、可行性和致命缺陷 | go/no-go 判定、反例清单、修订路线、创新性证据门 |
| [`light-research-plan`](skills/light-research-plan) | 把问题转成可执行研究计划，包括假设、变量、对照和失败树 | 实验矩阵、预注册草案、样本量/功效检查、复现计划 |
| [`light-research-ethics`](skills/light-research-ethics) | 检查伦理、授权、同意、数据边界和研究诚信风险 | 伦理风险表、授权生命周期检查、撤稿/重叠/异常文本提示 |
| [`light-data-engineering`](skills/light-data-engineering) | 评估数据身份、访问权限、质量、划分、泄漏和漂移风险 | 数据卡、质量门、泄漏检查、可用性/可行性报告 |
| [`light-experiment-coding`](skills/light-experiment-coding) | 构建可复现实验代码、配置、测试和运行记录 | 实验脚手架、配置 schema、seed 审计、run manifest |
| [`light-result-analysis`](skills/light-result-analysis) | 做统计分析、方法适配、过拟合/泄漏检查和结果解释 | 分析报告、统计检验、方法兼容性检查、结果卡 |
| [`light-figure`](skills/light-figure) | 规划并程序化生成论文图和数据图，支持 Python 与 R | 图表计划卡、Python/R 图、导出包、视觉诚实检查 |
| [`light-paper-writing`](skills/light-paper-writing) | 基于已有证据写作论文结构、论证链、贡献、局限和自审 | IMRaD/会议稿草案、claim-evidence 绑定、自审清单、润色稿 |
| [`light-citation`](skills/light-citation) | 核查引用真实性、DOI、链接、定位信息和声明-引用绑定 | 引用注册表、四门核查、可疑引用清单、修复建议 |
| [`light-consistency`](skills/light-consistency) | 检查论文、图表、PPT、代码和补充材料之间的一致性 | 术语表、事实绑定、指标/方法锁、跨材料一致性报告 |
| [`light-typesetting`](skills/light-typesetting) | LaTeX 模板排版、编译、日志预检和投稿前格式检查 | 可编译 LaTeX/PDF、模板适配、编译日志、投稿 readiness |
| [`light-venue-matching`](skills/light-venue-matching) | 根据主题、证据、风险和隐私约束匹配期刊/会议 | venue 候选表、fit 排名、风险提示、用户选择记录 |
| [`light-review-rebuttal`](skills/light-review-rebuttal) | 分解审稿意见、规划补实验、管理承诺并撰写回复 | 回复矩阵、承诺台账、实验请求门、response letter |
| [`light-frontend-design`](skills/light-frontend-design) | 为科研项目、竞赛或软件成果设计界面、组件和展示体验 | 页面结构、组件方案、动效建议、可访问性/浏览器 QA |
| [`light-system-design`](skills/light-system-design) | 设计软件系统架构、接口、数据模型、迁移和上线准备度 | 架构包、OpenAPI/schema、迁移策略、设计 readiness |
| [`light-patent-disclosure`](skills/light-patent-disclosure) | 整理发明点、现有技术差异和专利交底材料，不替代律师判断 | 专利访谈表、检索线索、交底书证据包 |
| [`light-software-copyright`](skills/light-software-copyright) | 整理软著申请所需的软件说明、材料清单和源码留存计划 | 软著材料包、源码留存计划、材料完整性检查 |

## 科研主线

Light Skills 不是让 AI 闷头从头跑到尾，而是把科研拆成可审计、可回退、可交给用户决策的阶段。

<p align="center">
  <img src="assets/research-workflow.zh.svg" alt="Light Skills 科研主线：从问题到交付的七阶段可审计流程" width="960">
</p>

| 阶段 | Light 主要做什么 | 常用技能 |
|---|---|---|
| 接收与理解 | 读论文、表格、图片、项目文件，建立任务边界与项目台账 | `file-reading`、`memory-pm`、`project-structure` |
| 查新与 idea | 检索文献、生成候选 idea、做创新性/可行性/致命缺陷批判 | `literature-search`、`idea-generation`、`idea-critique` |
| 研究设计 | 明确假设、变量、对照、样本量、失败树和复现实验计划 | `research-plan`、`research-ethics` |
| 数据与实验 | 整理数据、检查泄漏和质量、写实验代码、做结果分析 | `data-engineering`、`experiment-coding`、`result-analysis` |
| 论文交付 | 生成可复现图表、写论文、核查引用、检查全文一致性、LaTeX 排版 | `figure`、`paper-writing`、`citation`、`consistency`、`typesetting` |
| 投稿与转化 | 匹配期刊/会议、准备回复审稿、整理专利交底或软著材料 | `venue-matching`、`review-rebuttal`、`patent-disclosure`、`software-copyright` |
| 展示与软件 | 需要项目展示、竞赛 demo 或软件系统时，补前端和系统设计 | `frontend-design`、`system-design` |

## 论文 Demo 展示

一个论文Demo示例，方向是环境化学 / 光催化动力学，它展示了从合成数据、分析、程序化图表到 LaTeX PDF 的完整交付形态。

<p align="center">
  <a href="projects/photocatalytic-dye-kinetics-study/paper/main.pdf">
    <img src="projects/photocatalytic-dye-kinetics-study/paper/main-preview.png" alt="English science paper preview" width="540">
  </a><br>
  <sub><a href="projects/photocatalytic-dye-kinetics-study/paper/main.pdf">阅读 PDF</a> </sub>
</p>

## 图表展示

下面的九宫格科研图由 Python 与 R 生成。

<p align="center">
  <img src="examples/e2e-research-demo/figures/research_figure_gallery.png" alt="Light Skills research figure gallery" width="920">
</p>


## 反馈与支持

- 邮箱：1833058953@qq.com
- GitHub：[@Light0305](https://github.com/Light0305)
- 欢迎 issue / PR / 使用反馈。

<table align="center">
  <tr>
    <th align="center">微信赞赏</th>
    <th align="center">微信交流</th>
    <th align="center">微信公众号</th>
  </tr>
  <tr>
    <td align="center" width="33%"><img src="assets/wechat-donation.jpg" alt="微信赞赏码" width="200"></td>
    <td align="center" width="33%"><img src="assets/wechat-contact.png" alt="作者个人微信二维码" width="200"></td>
    <td align="center" width="33%"><img src="assets/wechat-official-account.jpg" alt="微信公众号二维码" width="200"></td>
  </tr>
</table>

## 许可证

本项目使用 [MIT License](LICENSE)。
