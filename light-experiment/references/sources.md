# 方法依据：仓库、子技能、论文与实践文章

核对日期：**2026-11-02（Asia/Tokyo）**。范围按用户澄清限定为计算机与理工科的计算实验，优先 2024–2026 的方法与执行实践。选择依据是能否改进真实实现、执行和证据保留，不按 star、期刊名或“自主科学家”宣传排名。这不是系统综述，也没有证明本技能能提高真实科研成功率。

本轮使用 `nature-academic-search` 的多源检索思路。专用 academic-search MCP 未挂载，改用网页发现、出版社/会议/arXiv 原页、Europe PMC 原文 XML、GitHub API 和提交固定的原始文件。仓库没有被安装或运行；**参考其公开方法后独立编写本技能和辅助代码，未复制外部提示词、代码或整包模板**。

## 建议先读的仓库与子技能

精确提交、文件指纹、许可识别与访问错误在 [repository-audit.json](repository-audit.json)。表内文件路径是实际检查的内容；链接使用默认分支便于阅读，复核使用 audit 中的 commit-pinned 链接。仓库许可与单文件许可可能不同；`null / NOASSERTION` 不代表获得复制许可。

| ID / 仓库 | 实际检查与价值 | 本技能的取舍 |
|---|---|---|
| R01 · [Research-Equality/RE-experiment](https://github.com/Research-Equality/RE-experiment) | 精读 `skills/execution-preflight`、`bounded-experiment-loop`、`experiment-output-contract`、`backward-traceability`、`experiment-repair-loop` 的 `SKILL.md` | 最直接的执行子技能集合：预检、限额迭代、日志/摘要分层、错误分类与追溯。采用原则，不强制统一 CLI、不把一个“最佳摘要”替代全部尝试，不沿用其通用 LaTeX `\num{formula}` 设想（是否求值取决于具体宏定义，不能当作标准能力） |
| R02 · [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `skills/pytorch-lightning/SKILL.md` 和 `references/logging.md` | 提醒模型、数据、训练、日志与 checkpoint 是不同职责；本地 CSV 可作为轻依赖记录。保留项目原框架，不强制 Lightning，不复制绑定特定当前版本的安装命令或云服务选择 |
| R03 · [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | `13-mlops/mlflow/SKILL.md`；`22-agent-native-research-artifact/research-manager/SKILL.md` 及 `references/event-taxonomy.md` | 借鉴 run/参数/指标/产物和观察/决定/死路的关联。事件在发生时记录，不限定为事后 epilogue；不自动创建整套 ARA，不用固定观察次数把猜想升级成知识。旧 MLflow 示例的 API 应以项目所装版本核对 |
| R04 · [EvoScientist/EvoScientist](https://github.com/EvoScientist/EvoScientist) | `EvoScientist/prompts.py` 中执行预检、阶段反思、证据充分性和记忆相关段落；P07 | 采用记录真实失败、针对日志修复和提炼可迁移教训。拒绝把固定“≥3 seeds”当普遍充分性，也不把所有 success signals 满足或作者报告的代码运行率视为科学结论成立；不默认多代理 |
| R05 · [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | README；`ai_scientist/treesearch/agent_manager.py` 的 stage configuration、goals、max_iterations；P08 | 借鉴阶段、分支、可测目标和停止限额；不用模型评分代替原始产物与科学验收，不要求树搜索或自动论文写作 |
| R06 · [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | `program.md` 的 baseline、固定评价、逐次记录与实验循环 | 借鉴稳定评价器、实际预算和每次尝试记录。明确舍弃 `LOOP FOREVER`、崩溃指标写 0、只按最佳验证值保留修改，以及自动 reset 的工作方式；搜索赢家仍需独立确认。固定五分钟适用于该项目，不成为本技能通则 |
| R07 · [mlflow/mlflow](https://github.com/mlflow/mlflow) | README 和 [Tracking 官方文档](https://mlflow.org/docs/latest/ml/tracking/) 的 Runs/Artifacts/Code Versions | 使用现有工具的原始 run ID；本地索引可与之对应。MLflow 的记录功能不自动保证数据划分、指标语义或完整依赖溯源，不要求上云/部署/模型注册 |
| R08 · [iterative/dvc](https://github.com/iterative/dvc) | 仓库 README.rst；[Experiment Management 官方文档](https://doc.dvc.org/user-guide/experiment-management)；B01 | 代码/数据版本与运行记录互补。适合大数据和缓存的可取回版本；`.dvc` 引用存在不是对象已可访问，单纯把所有数据复制进 run 也不是更强的复现方案 |
| R09 · [drivendataorg/cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science) | `docs/docs/using-the-template.md` 的环境、任务入口和 raw data 段落 | 采用原始与派生分层、可重跑入口。保留现有项目布局，不强制重建目录、安装 Make、建远端仓库或自动同步云端 |
| R10 · [snakemake/snakemake](https://github.com/snakemake/snakemake) | README；[Rules 官方文档](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html) 的 input/output/shell 规则 | 依赖图和产物驱动执行，适合已有多阶段计算流程。现有 DAG 应直接复用，不在外面再造调度层；缓存命中需有正确依赖与配置，不等于新计算发生 |
| R11 · [ResearchObject/workflow-run-crate](https://github.com/ResearchObject/workflow-run-crate) | README；[Process Run Crate 官方 profile](https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/) 的 Overview 与软件/action/input/output 关系；P02 | 将计划、执行、操作者、输入和产物分开，支持从简单命令逐步扩展。附带 JSON 只借鉴关系，不宣称 RO-Crate 合规或第三方可信时间 |

优先顺序：**执行操作先 R01/R06，持久证据先 R07/R08/R11，阶段反思先 R04/R05**。R02/R03 是综合科研技能包中可定位的小技能，符合“包里包含执行能力”的检索范围。框架参考与软件能力说明不是独立实验证据。

初检中的 eLabFTW/Bluesky 因偏向实体实验而在用户澄清后排除；不进入实施指南。最初猜测的 `WorkflowHub-EU/workflow-run-crate` 返回 404，沿 P02 参考文献 121 确认正确组织是 `ResearchObject`，错误保留在 audit 中，不当作有效仓库计数。

## 近年论文：采用什么，证据到哪里为止

### P01 · 项目结构与持续记录（2024，正式期刊）

van Kampen et al. [*ENCORE: a practical implementation to improve reproducibility and transparency of computational research*](https://www.nature.com/articles/s41467-024-52446-8)，Nature Communications 15:8117，2024-09-16；[DOI](https://doi.org/10.1038/s41467-024-52446-8)。

读取出版摘要，并通过 [Europe PMC 原文 XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11405857/fullTextXML) 核对 Results、Component 1（结构、概念信息、代码/数据/中间结果）、Component 5 与可用性段落。采用持续记录研究上下文及计算—数据的联系。作者组内应用经验不构成本技能的因果效果评测；不照搬其模板和额外导航器。

### P02 · 把执行与计划分开建模（2024，正式期刊）

Leo et al. [*Recording provenance of workflow runs with RO-Crate*](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0309210)，PLOS ONE 19:e0309210，2024-09-10；DOI `10.1371/journal.pone.0309210`。

核对摘要、§2.1–2.3 与 Fig.1–5 的关系和分层。采用 software/action/input/output/agent/time、prospective 与 retrospective provenance 的区分，以及不强迫小命令使用完整工作流语言的思路。规范兼容性与科学有效性是不同问题；本工具没有完成正式 RO-Crate 导出。

### P03 · ML 科学比较的质量条件（2024，正式期刊）

Kapoor et al. [*REFORMS: Consensus-based Recommendations for Machine-learning-based Science*](https://pmc.ncbi.nlm.nih.gov/articles/PMC11092361/)，Science Advances 10:eadk3452，2024-05-01；DOI `10.1126/sciadv.adk3452`。

核对摘要、Module 5 的基线比较、Module 6 的泄漏和 Module 7 的指标/不确定性。落实为固定划分、预处理边界、对等选择预算、逐单位数据与质量审查。共识清单不是保证，不能把填写完毕当作外部验证通过。

### P04 · 代码存在与实验完成有差距（2025，ICML 正式论文）

Starace et al. [*PaperBench: Evaluating AI’s Ability to Replicate AI Research*](https://proceedings.mlr.press/v267/starace25a.html)，PMLR 267:56843–56873，2025。

核对会议摘要与元数据：任务包含理解、代码和成功执行，用分层 rubric 评估复现。**本技能的工程推论**：把实现检查、进程成功、产物和科学验收分层，并设计可核验场景；该论文没有评测本技能，也不能把 rubric 分数当任意领域的科学正确概率。

### P05 · 重复、比较与研究者偏差（2024，JMLR 正式论文）

Patterson, Neumann, White & White. [*Empirical Design in Reinforcement Learning*](https://www.jmlr.org/papers/v25/23-0183.html)，JMLR 25(318):1–63，2024。

核对摘要及其覆盖的性能变化、基线、超参数和研究者偏差主题；没有逐页精读整篇。采用保留重复分布、基线与超参数选择过程、区分运行噪声和其他变异。RL 的评价细节不能原封不动套到确定性求解器或硬件计时上。

### P06 · 超出 ML 的数值性能执行（2025 出版的会议文集）

Baumgarten & Corallo. [*Continuous Benchmarking of Numerical Algorithms Implemented in M++ via Gitlab CI/CD and Google Benchmark*](https://majournals.bib.uni-mannheim.de/maconf/article/view/1025)，Mannheim Conference Series，2025-10-02；DOI `10.25521/maconf.2025.1025`。

核对元数据/摘要：PDE 数值算法、持续 benchmark、HPC 与性能记录。采用保持计算正确性与性能条件、保存逐实例配置和计时来源的执行思路；不声称读完 PDF 或独立验证其性能。文集对应第九届 bwHPC Symposium 2023，不能把会议举行年与出版年混写。

### P07 · 从失败中形成执行记忆（2026，预印本）

Lyu et al. [*EvoScientist: Towards Multi-Agent Evolving AI Scientists for End-to-End Scientific Discovery*](https://arxiv.org/abs/2603.08127)，读取 [v2 正文](https://arxiv.org/html/2603.08127v2)，v1 2026-03-09，v2 2026-10-05。

核对版本、摘要与 §3.4–3.5，借鉴工程执行轨迹、日志诊断、阶段结果和可迁移经验。作者报告的改进限定于其评测和系统；代码成功率不等于研究质量，多代理也不是采用这些原则的前提。

### P08 · 阶段管理和负结果（2025，预印本）

Yamada et al. [*The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search*](https://arxiv.org/abs/2504.08066)，[v1 正文](https://arxiv.org/html/2504.08066v1)，2025-04-10。

核对摘要、§3.2 的 experiment progress manager、目录中的附录案例与仓库阶段配置。采用明确阶段、迭代限额和保留失败分支。未复现整个系统；workshop 评审案例不等于主会录用或广泛可靠的自主科学能力。B03 对同一系统的博客不是另一项独立验证。

### P09 · 从结果文件转向执行过程评测（2026，预印本/共享任务报告）

Hong et al. [*Overview of the NLPCC 2026 Shared Task 11: Agent-Based Experiment Reproduction from Scientific Papers*](https://arxiv.org/abs/2609.11117)，v1 2026-09-10。

核对原始摘要、元数据；作者提出 AgentActionBench，记录 ML 与 AI4Science 复现过程的行为轨迹和任务 rubric。采用对实际动作与证据的测试，而非只审终稿目录。没有核对全部 rubric 或复现其人机相关性分析；不据此宣传自动评审等同专家验收。

### P10 · 标准化可读的 provenance（2025，预印本）

Padovani, Anantharaj & Fiore. [*yProv4ML: Effortless Provenance Tracking for Machine Learning Systems*](https://arxiv.org/abs/2507.01078)，v1 2025-07-01。

核对摘要/元数据，采用低侵入收集和可移植 provenance 格式的方向。没有测量其开销、覆盖率或完整实现；作者对工具限制的概括不作为“MLflow 无法记录 lineage”的绝对断言。轻量本地 JSON 与标准化导出应分开声明。

另见 Kassis et al. [*Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*](https://arxiv.org/abs/2609.00065)（2026，预印本；本轮仅检索摘要/元数据）：该工作明确不报告 task-level evaluation。收录多个 skill 本身不能证明任务效果，故本技能另做实际执行/故障测试并保留真实项目验证限制。

## 博客和机构实践

| ID / 文章 | 实际读取与采用 | 边界 |
|---|---|---|
| B01 · Rob de Wit / DVC，[Transforming a Jupyter Notebook into a Reproducible Pipeline for Experiments with DVC](https://dvc.org/blog/jupyter-notebook-to-dvc-pipeline/)（发布 2025-10-30，更新 11-17） | 从 notebook 原型到分阶段 pipeline、参数和数据/实验版本；读取主要流程 | 改编自 2023 演讲，不能把更新时间当方法首次提出时间；不要求迁出所有 notebook，正式结果需有可重跑的执行顺序 |
| B02 · MLflow maintainers，[Announcing MLflow 3](https://mlflow.org/blog/mlflow-3-launch/)（2025-06-09） | 原文的 tracing、评估、版本和应用行为关联，补充官方 Tracking 文档 | 发布文章有产品定位；LLM judge 分数、生产可观测性与科学主张验证不等价，不自动部署服务 |
| B03 · Sakana AI，[The AI Scientist Generates its First Peer-Reviewed Scientific Publication](https://sakana.ai/ai-scientist-first-publication/)（2025-03-12，4 月更新） | 原文的工作流、投稿实验与边界说明；结合 P08 | 三篇投稿中一篇超过 workshop 门槛，按事先安排撤回；不是已发表的 ICLR 主会论文。作者博客不能独立验证作者系统 |
| B04 · IBM/Meta PyTorch teams，[Maximizing Training Throughput Using PyTorch FSDP and Torch.compile](https://pytorch.org/blog/maximizing-training-throughput/)（2024-05-21，页面显示 11 月更新） | 正文将 numerical parity 与 throughput 分开；采用优化后仍需验证数值/任务质量 | 其模型、设备、MFU 和加速比是特定案例，不写成本技能预期收益 |

## 实施时直接可查的官方说明

- M01 · [Harvard Kempner Computing Handbook: Reproducible Research](https://handbook.eng.kempnerinstitute.harvard.edu/s2_swe_for_research/reproducible_research.html)：项目、环境、数据/配置和结果的联系。机构手册，未用网页抓取时间当发表年。
- M02 · [PyTorch Reproducibility](https://docs.pytorch.org/docs/2.15/notes/randomness.html)：运行/平台/版本与确定性设置。`stable` 页面本轮出现重定向，使用实际目标版本路径核对；实施时按项目安装版本查对应文档。
- M03 · [PyTorch Benchmark recipe](https://docs.pytorch.org/tutorials/recipes/recipes/benchmark)：线程、预热、CUDA 同步；页面标明创建于 2020，更新于 2025。不是 2025 首创的方法。
- M04 · [Benchmarking JAX code](https://docs.jax.dev/en/latest/benchmarking.html)：核对异步 dispatch、`block_until_ready()`、编译与稳态计时段落。借鉴计时边界，不强制安装 JAX。
- M05 · [Process Run Crate profile](https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/)：本轮版本 0.6。2024 论文中的 profile 版本与当前版本有差异，实际导出须明确版本，不混写。

## 来源如何变成技能规则

| 本技能决策 | 主要依据 | 验证方式 |
|---|---|---|
| 冻结设计/配置/输入并保留原件 | P01/P02、R08/R11 | 本地交接集成、字节指纹与漂移测试 |
| 限额运行、独立尝试和错误日志 | R01/R05/R06、P07/P08 | 真正启动短命令、崩溃/超时/中断/预算测试 |
| 进程状态、QC、科学判定分层 | P03/P04/P09；本技能的工程综合 | 退出 0 但缺输出、失败不能通过 QC 的反例 |
| 逐单位记录与公平比较 | P03/P05、M02 | 行为场景与原始值/来源约束，真实领域仍需研究者审查 |
| 数值正确性和性能分开 | P06、B04、M03/M04 | 解析 ODE 的实际收敛测试；未测试真实 GPU/HPC |
| 事件时间/事后补记、原始与派生分层 | P01/P02、R03/R09 | 追加事件、更正保留、封存产物漂移测试 |

这些是来源支持的方法选择与本技能的工程推论，不是外部论文对本技能的效果认证。

## 检索与访问限制

使用过的查询包括 `github scientific skills experiment execution tracking reproducibility`、`RE-experiment skills`、`EvoScientist experiment agent`、`2024 2025 reproducible computational research provenance`、`2024 2025 benchmarking numerical scientific computing`、`PaperBench experiment reproduction`、`2026 AgentActionBench` 和官方站点定向检索。

Nature 的 ENCORE 原页遭遇登录重定向，PMC 网页出现验证码，已用 Europe PMC 原文 XML 阅读特定章节。部分搜索混入第三方聚合、营销和社交页面，只用于发现；技术判断优先回到原始仓库/出版页。没有声称获取每篇全文，没有导入 star/引用量来排名，也没有执行这些外部代理平台。后续应以真实使用中发现的遗漏迭代技能，并重新核对变化的工具接口。
