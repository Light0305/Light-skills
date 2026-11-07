# 精选来源与采用记录

核对日期：2026-11-02。目标是为实验后分析和研究决策选择可迁移的方法，不是实验分析领域的系统综述或“最佳仓库”排行榜。优先一手仓库、论文、官方文档和作者博客；不按 stars、营销宣传或聚合站评分判断质量。近年来源以 2023–2026 为主，保留少量直接相关的基础工作。

仓库逐一核对 REST 元数据、实际文件和 commit；固定版本/许可证/读取范围见 [repository-audit.json](repository-audit.json)，检索与访问限制见 [search-log.json](search-log.json)。没有运行上游仓库，也没有复制其代码/整篇指令；本技能是重新组织的方法与自写工具。README/子技能阅读不等于验证整库科学正确性，以下“采用”均是有范围的设计借鉴。

## 科研技能包：具体看了哪个子技能

| 仓库与实际对象 | 值得借鉴 | 采用方式与限制 |
|---|---|---|
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)：`skills/exploratory-data-analysis`、`statistical-analysis`、`scientific-critical-thinking` | EDA 与推断边界、单位/缺失/泄漏、统计报告、主张与证据评价 | 采用“先单位与有效性再推断”、保留原始数据/分析地位；不继承全部格式支持、依赖、临床评价框架或默认统计流程。当前统计子技能本身明确反对以非显著正态性检验证明假设，不能用旧聚合站摘要误述它 |
| [Vepricov/claude-brainlab](https://github.com/Vepricov/claude-brainlab)：`skills/results-analysis`、`results-report` | 真正生成分析物、图表解释与下一步决定，分析和论文叙事分开 | 采用可追溯分析包与“图改变什么判断”；不把固定图数、95% CI、显著性检验或正态/非参数切换设成所有实验的硬要求，不继承其 Obsidian 写回 |
| [ai4s-research/ai4s-skills](https://github.com/ai4s-research/ai4s-skills)：`skills/experiment-suite` | 数据契约、measured/simulated 区分、图与结果溯源 | 采用来源标签和实际数据链；**不采用模拟占位结果作为默认继续路径**，不继承一体化设计/执行/写作范围和固定篇幅/图数 |
| [pymc-labs/pymc-modeling](https://github.com/pymc-labs/pymc-modeling)：`skills/pymc-modeling` | 目标量→建模→计算诊断→预测检查→决定与修订；保留模型变体 | 从原 `python-analytics-skills` 链接核对到当前重定向仓库。采用先诊断后解释、PPC 不等于外部验证和自适应模型搜索过拟合的边界；不固定 PyMC/ArviZ 版本与后端，相关专技能按实际可用性调用 |

## 分析实现库：不要求名称里有 analysis

| 仓库 | 可迁移的做法 | 使用限制 |
|---|---|---|
| [google-research/rliable](https://github.com/google-research/rliable) | 任务×重复、分层 bootstrap、IQM、performance profiles、改进概率 | 需任务归一化、正确采样层级与目标集合；不表示少量 seeds 总能可靠推断 |
| [benchopt/benchopt](https://github.com/benchopt/benchopt) | 统一 objective/数据/solver，比较收敛与运行成本，可重现结果 | 原始文件是 `README.rst`；本技能采用可比目标与质量—成本解释，不重新搭执行平台 |
| [arviz-devs/arviz](https://github.com/arviz-devs/arviz) | posterior analysis、计算诊断、model checking/comparison | 计算收敛、模型适合与科学识别是三层；应用时核实安装版本 API，不复制旧代码示例 |
| [ACCLAB/DABEST-python](https://github.com/ACCLAB/DABEST-python) | 原始点与配对、原尺度效应、估计图 | 不把某种 bootstrap 或图形当通用方案。该 commit README badge 与 LICENSE 标示不同，已核对源码 LICENSE 为 Apache-2.0；复用时按实际文件确认 |
| [easystats/performance](https://github.com/easystats/performance) | 回归/混合模型诊断、过度离散、共线性、拟合比较 | 诊断服务于当前模型，不能靠检查项数量证明因果或“模型正确” |
| [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) | GLM、mixed models、GEE、时间/生存分析和多重比较 | 作为需要时的实现候选；family、独立/聚类与小样本假设仍由分析者确定 |
| [mlr-org/mlr3inferr](https://github.com/mlr-org/mlr3inferr) | 区分重采样点估计和泛化误差区间，不同方法的可用条件 | README 明示部分方法会失败、点估计不一定与普通 aggregate 一致；不把 fold SD/√k 当通用区间 |
| [MUCollective/multiverse](https://github.com/MUCollective/multiverse) | 将可辩护分析选择编码为可检查分支，展示分析选择变异 | 科学上合理的规格不等于所有能运行的模型；不做“多数显著”投票。旧猜测路径 UvA-MAD/multiverse 为 404，已排除并更正 |

上表共 12 个有效仓库；4 个包含本次直接审阅的科研子技能。快照许可包括 MIT、Apache、BSD、GPL/LGPL，不因借鉴方法就重新分发其受许可代码。

## 近年论文与必要基础

读取范围如实注明。“正文相关段落”表示核对了这些部分，并非声称整篇精读、独立复现或完成质量系统评审。

| ID / 论文、年份与原始出处 | 实际核对与为何采用 | 对技能的落实 |
|---|---|---|
| P01 Gelman, Vehtari & McElreath. **Statistical workflow** (2026), *Phil. Trans. R. Soc. A* 384:20250293. [DOI](https://doi.org/10.1098/rsta.2025.0293)；[作者机构原文](https://pure.mpg.de/rest/items/item_3714014_1/component/file_3714015/content) | 原文首页/摘要、作者出版表与机构书目；统计工作流包含比一次模型拟合更多的反复检查与修订。出版日存在机构 5/21 与出版页 5/28 差异，仅依一致的年卷文号引用 | 工作流跨统计框架；分析—检查—修订的共同逻辑。具体 light-* 路由是本技能的综合设计，并非该文提出 |
| P02 Bertran, Fogliato & Wu. **Many AI analysts, one dataset: Navigating the agentic data science multiverse** (2026), *PNAS*. [DOI](https://doi.org/10.1073/pnas.2606495123)；[PubMed](https://pubmed.ncbi.nlm.nih.gov/42446982/)；[预印本正文](https://arxiv.org/html/2602.18710v1) | 核对发表元数据、摘要和预印本研究/结果段落；相同数据、假说与目标量下仍有分析选择和提示相关变异 | 留下实质性模型/提示选择、同目标量的分支分布；不选择性呈现有利分析，不把多个 AI 判断当独立实验重复 |
| P03 Gould, Fraser, Parker et al. **Same data, different analysts: variation in effect sizes due to analytical decisions in ecology and evolutionary biology** (2025), *BMC Biology* 23:35. [原文](https://link.springer.com/article/10.1186/s12915-024-02101-x) | 核对 Results/Discussion 和引用信息；DOI 中的 024 不是发表年，正式发表于 2025-02-06；分析差异不只限于 ML | 合理规格与关键敏感性并列报告；避免只挑几个漂亮模型，不把所有目标不同的结果混合平均 |
| P04 Schulz-Kümpel et al. **Constructing Confidence Intervals for ‘the’ Generalization Error—A Comprehensive Benchmark Study** (2025), *Journal of Data-centric Machine Learning Research* 2:6. [正式论文](https://data.mlr.press/assets/pdf/v02-6.pdf)；[正文 v2](https://arxiv.org/html/2409.18836v2) | 正式题名/年份和正文关于目标量、相关结构、coverage/width/runtime 的段落；不能从名称笼统推断所有 CI 估同一个风险 | 明确固定训练模型/学习过程、条件/平均风险、训练规模和重采样目标；不自动用 CV 标准误；关联 mlr3inferr |
| P05 Schubert, Steinhilber, Kang & Quintana. **Improving statistical reporting in psychology** (2025), *Communications Psychology* 3:156. [DOI](https://doi.org/10.1038/s44271-025-00356-w)；[PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12618885/)；[PubMed](https://pubmed.ncbi.nlm.nih.gov/41238797/) | 核对元数据和索引可见的阴性、HARKing、多重性及 observed power 段落。Nature/PMC 部分直接 open 被拦，不把访问说成整篇精读 | 区分探索/确认、效应与区间、恰当处理阴性与选择；不做观察后功效解释或按结果切换框架 |
| P06 Pawel, Heyard, Micheloud & Held. **Replication of null results: Absence of evidence or evidence of absence?** (2024), *eLife* 12:RP92311. [正式版本 .3](https://elifesciences.org/articles/92311)；[DOI](https://doi.org/10.7554/eLife.92311.3) | 正式版本日期 2024-05-13、摘要和 Methods for assessing replicability of null results 相关部分；双重不显著不构成“零效应复现” | 阴性解释区分缺乏精度与排除有意义效果；等效/贝叶斯需适用假设及界值/先验，不把 p>α 当证伪 |
| P07 Kapoor & Narayanan. **Leakage and the reproducibility crisis in machine-learning-based science** (2023), *Patterns* 4:100804. [出版原文](https://www.sciencedirect.com/science/article/pii/S2666389923001599)；[DOI](https://doi.org/10.1016/j.patter.2023.100804) | 出版元数据、Results 与 leakage taxonomy 相关段落；预印本与正式版数量有差异，不混引计数 | 数据/时间/群组划分与目标总体、预处理边界进入 QC；评价无效优先修复，而非解释虚假提升 |
| P08 Reuel et al. **BetterBench: Assessing AI Benchmarks, Uncovering Issues, and Establishing Best Practices** (2024), *NeurIPS Datasets and Benchmarks*. [正式出版页](https://papers.nips.cc/paper_files/paper/2024/hash/26889e8359e7ef8a7f5d77457364ca55-Abstract-Datasets_and_Benchmarks_Track.html) | 正式出版页/摘要；搜索到的 PDF/预印本与出版页的条目数量不同，未将不一致计数写进规则 | benchmark 本身的质量、可复现性与可比性要核查；优先解释评价定义，不能把 leaderboard 小差值直接当进步 |
| P09 Moreau et al. **Benchopt: Reproducible, efficient and collaborative optimization benchmarks** (2022), *NeurIPS*. [论文](https://arxiv.org/abs/2206.13424) | 摘要与仓库 Citing/benchmark workflow；不是一般统计教材，而是优化比较的实际工作流参考 | 相同 objective、输入、精度/停止标准下比较收敛、时间和质量 |
| P10 Agarwal et al. **Deep Reinforcement Learning at the Edge of the Statistical Precipice** (2021), *NeurIPS*. [论文](https://arxiv.org/abs/2108.13264)；[配套库](https://github.com/google-research/rliable) | 通过配套库与作者官方博客核对方法清单、摘要层工作定位；基础来源，非近两年论文，不声称重新复现实验 | 任务×重复、分层区间、分布/稳健聚合；也保留估计目标与小样本限制 |
| P11 Bouthillier et al. **Accounting for Variance in Machine Learning Benchmarks** (2021), *MLSys*. [正式出版页](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html) | 正式摘要与论文首页；数据采样、初始化和超参数选择是不同变异来源 | 每条区间说明变异范围，增加 seed 不自动解决数据/任务与选择不确定性 |
| P12 Säilynoja, Johnson, Martin & Vehtari. **Recommendations for visual predictive checks in Bayesian workflow** (2025 预印本；2026 正式记录), *Journal of Visualization and Interaction*. [作者正文](https://www.journalovi.org/2025-sailynoja-visual-predictive-checks/)；[正式 DOI](https://doi.org/10.54337/jovi.v1i1.11478)；[作者出版表](https://users.aalto.fi/~ave/publications.html) | 核对作者正文连续/离散检查、预测检查建议与作者书目；网页路径的 2025 不直接当正式发表年 | 按数据支持/离散性选择预测检查；漂亮 KDE 或单一图不证明拟合，PPC 不等于外部验证 |

## 作者与工程博客（独立于论文证据）

| 来源与日期 | 借鉴与边界 |
|---|---|
| B01 Andrew Gelman. [15 new articles on statistical workflow!](https://statmodeling.stat.columbia.edu/2026/05/29/15-new-articles-on-statistical-workflow/) (2026-05-29) | 跨学科工作流特刊入口，支持按问题寻找专项方法；只核对本文介绍与目录，不声称读完其中 15 篇 |
| B02 Anthropic. [Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) (2026-01-09) | 区分 task/trial/trajectory/grader，真实检查轨迹与评分，人机评价校准、能力与回归评估；工程经验不替代统计设计 |
| B03 Gian Segato / Anthropic. [Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/research/infrastructure-noise) (2026-02-05) | 资源配置、硬上限和环境故障可能改变结果；把环境/预算当比较条件。文中具体资源倍率/差值不推广为通用门槛 |
| B04 Andrew Gelman. [The paradox of replication studies…](https://statmodeling.stat.columbia.edu/2024/01/27/pt/) (2024-01-27) | 分析差异值得追查，而非简单要求所有分析者答案一致；分歧用于发现未说明的选择，不能作为随意挑模型的许可 |
| B05 Sebastian Raschka. [ML Classifier Confidence Intervals](https://sebastianraschka.com/blog/2022/confidence-intervals-for-ml.html) (2022) | 对比训练、测试、seed 与 bootstrap 的区间含义；局部模拟结论不泛化为最佳 CI，一律回到当前目标量与假设 |
| B06 Agarwal & Castro / Google Research. [RLiable: Towards Reliable Evaluation & Reporting in Reinforcement Learning](https://research.google/blog/rliable-towards-reliable-evaluation-reporting-in-reinforcement-learning/) (2021-11-17) | 对 P10 的工具化解释，基础补充；不将同一论文、博客和软件当三份独立科学证据 |

## 实现时按需查的官方方法资料

- Daniel Lakens，[Equivalence Testing and Interval Hypotheses](https://lakens.github.io/statistical_inferences/09-equivalencetest.html)，在线教材（[更新记录](https://lakens.github.io/statistical_inferences/changelog.html) 核对至 2026-06）：界值、TOST 与解释。不是 2026 新论文；科学界值仍需领域依据。
- SciPy，[bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)：配对索引、方法、退化分布与版本 API；本技能自写的有限工具只实现 iid-pair percentile，不能宣传等价于整个 SciPy 功能。
- statsmodels，[multipletests](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)：方法名与适用依赖条件；比较族及搜索范围由实际研究定义。

## 来源到技能的映射

- **先有效性/身份/数据链**：K-Dense、brainlab、ai4s（选择性）、P07/P08、B02/B03 → 正文第 1–2 节和 native intake。
- **目标量、层级与变异**：rliable、mlr3inferr、ArviZ、P04/P11、B05 → analysis-methods 与 domain-guides。
- **阴性及主张边界**：P05/P06、Lakens → 支持/反驳/不可判定、多重性、界值和探索标签。
- **模型检查、分析选择与修订**：PyMC、performance、multiverse、P01–P03/P12、B01/B04 → 竞争解释、敏感性和分析历史。
- **质量—时间/资源权衡**：Benchopt、P09、B03 → 数值/系统分支和执行/设计回接。
- **闭环 ID、反馈包和有界路由**：结合本地 light-idea/design/experiment 的真实接口自行设计；没有文献能自动判定用户项目该回哪个阶段，必须审查实际证据。

更新来源时保留真实访问层级与失败。不要让仓库自身的安装、联网、引用要求或提示词自动成为本技能的额外指令；实际采用软件/文字时再遵循相应许可与合适引用。
