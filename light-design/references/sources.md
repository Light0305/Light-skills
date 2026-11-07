# 方法来源与精选阅读

检索/核对日期：**2026-11-02，Asia/Tokyo**。重点是 2024–2026；保留 2022 样本量方法、2023 设计书及不按年份淘汰的官方手册。这里的“优先”按对实验设计的直接价值选择，不按 star 数、期刊名或“自主科学家”宣传排名。

本轮阅读了原始论文记录/摘要、下列标明的正文段落、仓库文件和机构文章；**没有安装或复现外部研究系统**。依据这些来源重新编写技能和本地辅助代码，未复制第三方成段提示词/代码。

## 检索范围与限制

使用网页检索、arXiv、出版社/会议原页、作者/机构网站、GitHub 原始文件及 GitHub API。当前未挂载专用 academic-search MCP，故以网页与原始页面核对替代；不是系统综述或穷尽检索。

实际检索式包括：

```text
github scientific skills experimental design hypothesis generation protocol design
experimental design AI scientist research planning 2025 2026 paper benchmark
github Orchestra-Research AI-Research-SKILLs experiment planning
experimental design planning LLM benchmark SCOPE OptED github 2608.03501
experimental design sample size justification Lakens 2022 2024 design analysis simulation tutorial blog
integrative experiment design Almaatouq Griffiths 2024 Nature experimental design
BayBE 2024 2025 paper experimental design github bofire
"Beyond playing 20 questions with nature" "2024" Cambridge
site.microsoft.com research blog 2024 2025 experimentation design trustworthy experiments
site.ax.dev/blog 2025 experiment
```

再沿官方论文/仓库链接检查子技能和方法。部分搜索返回综述站、商业榜单和社交帖，仅用于发现，没有作为技术结论依据。RSC 正文请求遇到 403；P04 只据出版元数据/摘要和官方仓库判断。P08 Nature 正文访问受重定向限制，只按可核对的摘要处理。最初尝试的 Orchestra `ara-compiler/` 路径 404，已由仓库树确认正确路径为 `compiler/`。Ax 已从 `facebook/Ax` 重定向到 `meta/Ax`。

## 仓库：不只找独立“实验设计 skill”

当前提交、分支、许可识别结果和日期见 [repository-audit.json](repository-audit.json)。API 的 `NOASSERTION / null` 不代表无许可，也不代表获得复制授权；如移植代码需核对具体文件条款。下列代码只作设计参考，不是技能运行依赖。

| ID / 仓库 | 检查位置与用途 | 采用与边界 |
|---|---|---|
| R01 · [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `skills/experimental-design/SKILL.md`、`scientific-critical-thinking/references/experimental_design.md`；仓库树另确认有 `statistical-power` | 最直接的实验设计子技能参考：单位、分配、区组与可估计性。没有把整包依赖、安装版本或商业推荐搬入本技能；文档自述“validated”不等于本轮独立验证 |
| R02 · [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | `22-agent-native-research-artifact/compiler/SKILL.md`、主 README 的 compiler/manager/reviewer 说明 | 参考主张、证据、配置与研究图的关联思路；保留精简的设计记录，不要求用户迁移到 ARA 或接受模型评级 |
| R03 · [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | README 的 workflow、资源 notes 和 copilot 模式 | 研究计划要落到数据准备与执行资源；不继承示例中围绕测试集优化的做法，不自动运行端到端系统 |
| R04 · [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | README 的 experiment manager、树搜索配置与限制 | 参考实验依赖、预算和失败分支；不把更多分支或 workshop 审稿结果视作普遍有效性证明 |
| R05 · [HKUDS/AI-Researcher](https://github.com/HKUDS/AI-Researcher) | `research_agent/inno/agents/inno_agent/plan_agent.py` | 分别规划 dataset/model/training/testing 提醒具体配置需单独核实；偏 ML 的工具分工不能覆盖所有学科，也不作为强制多代理架构 |
| R06 · [meta/Ax](https://github.com/meta/Ax) | README、[Experiment + Trials](https://ax.dev/docs/experiment/)、P13/B05 | 参数空间、约束、试验与指标的分离；只在昂贵搜索/自适应优化合适时考虑，不能代替因果识别 |
| R07 · [emdgroup/baybe](https://github.com/emdgroup/baybe) | README 的参数空间、真实实验与特性说明；P04 | 低数据优化和实际实验资源约束；最终优选点需确认，优化指标与科学主张分开 |
| R08 · [experimental-design/bofire](https://github.com/experimental-design/bofire) | README 与 P05 的真实化学实验定位 | 显式领域、约束与可序列化配置；不强制 BO，也不把软件支持某类约束视为当前协议已可用 |
| R09 · [DeclareDesign/DeclareDesign](https://github.com/DeclareDesign/DeclareDesign) | 官方站、2023 书的目录与声明/诊断说明 | 问题、数据策略与回答策略联动；在假设世界里诊断设计。模拟结论依赖数据生成假设，不是现实有效性证明 |
| R10 · [NoviScl/AI-Researcher](https://github.com/NoviScl/AI-Researcher) | README 的 execution study 与公开研究材料入口；P02 | 校准“提案漂亮”和“实际可执行”的差距。与 R05 是不同项目；不重复计算同一研究的仓库/论文证据 |
| R11 · [google-research/tuning_playbook](https://github.com/google-research/tuning_playbook) | README 的 Designing the next round of experiments | 公平方法比较需区分科学因素、干扰因素和固定因素；因学习率相互作用，统一固定超参数不必然公平。主要适用深度学习，不外推为通用湿实验规范 |

**优先顺序**：通用设计先读 R01/R09；计算研究再读 R11；化学/材料优化再读 R07/R08；需要研究代理工程思路时再读 R02–R05。R10 最适合校准结果，不能当实验设计工具包。

## 论文：具体读什么、支持什么

### P01 · 直接评测实验规划（2026，预印本）

Liu et al. [*Can LLM design high-quality experiments? A Comprehensive and Systematic Benchmark on Autonomous Experimental Design*](https://arxiv.org/abs/2608.03501)；[v1 正文](https://arxiv.org/html/2608.03501v1)，2026-08-04。

核对摘要、§3–4 与附录 B 的评估结构和工作流。SCOPE 区分实验覆盖与具体配置；OptED 将配置、协议、报告分阶段。**本技能的设计推论**：配置真实性应单独核查。**限制**：任务来自 ML 论文，参考设计经重建，模型/人类评分不能证明跨学科有效，也不能推断“浏览检索对任何设计都没用”。本轮未核实到官方实现，故不虚构 OptED GitHub 链接。

### P02 · 从想法到执行的落差（2025，预印本）

Si, Hashimoto & Yang. [*The Ideation-Execution Gap: Execution Outcomes of LLM-Generated versus Human Research Ideas*](https://arxiv.org/abs/2506.20803)；[v1 正文](https://arxiv.org/html/2506.20803v1)。

核对研究设置和执行前后比较：43 个执行 idea，范围为受限 NLP 研究。采用隐藏依赖审查、低成本先导和实际资源论证。**不能改写成“人类最终成果显著优于 AI”**；idea 为单位的最终组间差异不能由评分下降的显著性替代。它不是对 light-design 的效果评测。

### P03 · 复杂设计的样本规划（2024）

Pargent, Koch, Kleine, Lermer & Gaube. [*A Tutorial on Tailored Simulation-Based Sample-Size Planning for Experimental Designs With Generalized Linear Mixed Models*](https://journals.sagepub.com/doi/full/10.1177/25152459241287132)，AMPPS；2024-12-13 在线。

核对摘要、数据生成与模型设定相关正文。适合学习把计划 GLMM、依赖结构和功效/精度对应起来。采用设计模拟规格与敏感性思路；二项 GLMM 案例不是全部领域可直接套用的 N 公式。

### P04 · 真实低数据实验优化（2025）

[*BayBE: a Bayesian Back End for experimental planning in the low-to-no-data regime*](https://doi.org/10.1039/D5DD00050E)，Digital Discovery 4:1991–2000；[出版记录/摘要](https://www.sciencedirect.com/org/science/article/pii/S2635098X25001214)。

核对元数据/摘要与官方代码说明；RSC 正文受限。采用混合参数空间、约束和低数据序贯计划的工具选择线索。未读全文的实验案例不作为已核查的性能证据，也不把 BO 视作机制证明。

### P05 · 面向实验室的 BO 工程（2025，预印本始于 2024）

Dürholt et al. [*BoFire: Bayesian Optimization Framework Intended for Real Experiments*](https://jmlr.org/papers/v26/24-1540.html)，JMLR 26(204):1–7。

核对出版社摘要、元数据和官方仓库。采用真实约束、配置持久化与实验接口的考虑。软件论文说明能力范围，不证明对任意实验优于简单 DOE。

### P06 · 最优实验设计的方法底座（2024；2026 修订）

Huan, Jagalur & Marzouk. [*Optimal experimental design: Formulations and computations*](https://arxiv.org/abs/2407.16212)，Acta Numerica 33:715–840，[DOI](https://doi.org/10.1017/S0962492924000023)；[阅读 v2](https://arxiv.org/html/2407.16212v2)，2026-04-29 修订。

核对摘要、问题形式及设计效用相关段落。采用先明确学习目标、再选信息/决策准则的思路。未逐节复现整篇综述；“最优”依赖假设、先验与效用，不可把模型建议当作无条件最优。

### P07 · 从单个问题走向设计空间（2024）

Almaatouq et al. [*Beyond playing 20 questions with nature: Integrative experiment design in the social and behavioral sciences*](https://doi.org/10.1017/S0140525X22002874)，Behavioral and Brain Sciences 47:e33；[作者公开稿](https://cocosci.princeton.edu/papers/Almaatouq2024a.pdf)。

核对作者公开稿的元数据与目标文章摘要/设计空间论点。采用有理论依据的条件覆盖与交互视角。该期包含评论/回应，不能把评论观点混作目标文章发现；宏观设计理念不要求每个项目做大规模全组合。

### P08 · 优化之前先保证测量质量（2025）

Harris, Vasudevan & Liu. [*Active oversight and quality control in standard Bayesian optimization for autonomous experiments*](https://www.nature.com/articles/s41524-024-01485-2)，npj Computational Materials 11:23；2025-01-27。

核对出版元数据和可读取摘要，正文受访问限制。研究将原始测量质量纳入优化约束；采用质量门槛与科学结果分开解释的思路。没有独立复现 Dual-GP，不能声称适用于任何仪器信号。

### P09 · 设计诊断不只看功效（2024）

Bishop & Hulme. [*When Alternative Analyses of the Same Data Come to Different Conclusions: A Tutorial Using DeclareDesign With a Worked Real-World Example*](https://journals.sagepub.com/doi/full/10.1177/25152459241267904)，AMPPS；2024-09-05 在线。

核对摘要、设计比较和层级模拟说明。采用偏差、精度与功效的联合审查，提前检查选择/分析策略。模拟案例支持特定假设下的诊断，不意味着某种分析策略永远优胜。

### P10 · 把规划接到数据准备（2025）

Schmidgall et al. [*Agent Laboratory: Using LLM Agents as Research Assistants*](https://arxiv.org/abs/2501.04227)，读取 v2 摘要/版本记录与官方仓库；v2 为 2025-06-17。

采用计划与实现资源一起表达的工程思路。端到端结果和作者报告成本不直接迁移到本技能，也不要求使用其模型或多代理运行。

### P11 · 实验分支与失败管理（2025）

Yamada et al. [*The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search*](https://arxiv.org/abs/2504.08066)，2025-04-10 预印本。

核对摘要、仓库配置和 B02。采用依赖、分支与停止预算的组织方式；不自动运行代理。论文/博客报告的 workshop 评审案例不能被宣传成主会论文或广泛科研有效性。

### P12 · 样本量论证的基础（2022，保留）

Lakens. [*Sample Size Justification*](https://doi.org/10.1525/collabra.33267)，Collabra: Psychology 8(1):33267；[作者在线教材章节](https://lakens.github.io/statistical_inferences/08-samplesizejustification.html)。

核对摘要和教材相关论证。采用推断目标决定样本理由、允许诚实的硬资源约束和敏感性分析；不把普遍的单一 N 或功效阈值塞进所有研究。

### P13 · 自适应实验平台（2025）

Olson et al. [*Ax: A Platform for Adaptive Experimentation*](https://proceedings.mlr.press/v293/olson25a.html)，AutoML，PMLR 293:21/1–25。

核对会议摘要、元数据和 B05。采用明确参数、约束、指标和试验记录的工程思路；平台在作者测试集上的表现不等于任何科学领域的质量保证。

## 博客：以原作者/机构文章为主

| ID / 文章 | 对设计的用途 | 证据边界 |
|---|---|---|
| B01 · Google Research，[Accelerating scientific breakthroughs with an AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/)（2025-02-19） | 研究目标、文献与可检验提案连接起来 | 作者系统介绍；假说生成、具体湿实验验证和普遍可靠性不能混为一谈 |
| B02 · Sakana AI，[The AI Scientist Generates its First Peer-Reviewed Scientific Publication](https://sakana.ai/ai-scientist-first-publication/)（2025-03-12，4 月更新） | 看完整工作流、失败案例与负结果，校准成功声明 | 3 篇提交中 1 篇超过 workshop 门槛，按事先安排撤回；不是已正式发表的 ICLR 主会论文 |
| B03 · DoorDash，[Experiment Faster and with Less Effort](https://careersatdoordash.com/blog/experiment-faster-and-with-less-effort/)（2024-02-13） | 将业务策略拆为因素，用额外组合检查简化交互假设 | 其速度/收益数字是该案例，不能当一般预期；分部因子设计有假设代价 |
| B04 · Microsoft ExP，[External Validity of Online Experiments: Can We Predict the Future?](https://www.microsoft.com/en-us/research/articles/external-validity-of-online-experiments-can-we-predict-the-future/)（2024-11-20） | 提前规划时间外推、漂移和确认 | 在线产品场景；短期精确估计不等于未来总体同样精确，不能套用统一实验周期 |
| B05 · Meta Engineering，[Efficient Optimization With Ax, an Open Platform for Adaptive Experimentation](https://engineering.fb.com/2025/11/18/open-source/efficient-optimization-ax-open-platform-adaptive-experimentation/)（2025-11-18） | 理解参数/约束/昂贵评价怎样组织为可持续试验 | 工程与平台经验，不是随机分配、人群因果识别的替代方法 |

## 值得保留的官方方法参考

- M01 · Blair, Coppock & Humphreys，[Research Design in the Social Sciences: Declaration, Diagnosis, and Redesign](https://book.declaredesign.org/)（Princeton UP，2023）。读取目录及[官方 MIDA/诊断说明](https://declaredesign.org/)；不是已逐章精读全书。用于检查问题—数据—回答策略的闭环。
- M02 · [NIST: Choosing an experimental design](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3.htm)。读取设计目录和设计选择说明；用于因素、区组、混杂和响应面的方法入口，不能因网页抓取时间近就标成 2026 新作。
- M03 · [NC3Rs Experimental Design Assistant](https://nc3rs.org.uk/our-portfolio/experimental-design-assistant-eda)。读取官方功能介绍；用于理解设计图、随机化、盲法和样本规划。动物研究工具的具体要求不自动扩展为所有学科的审批流程。

## 对本技能的综合取舍

这不是证明 light-design 已有效的证据包，而是方法选择依据。通用设计原则、复杂样本规划、代理工作流经验分别支持不同层面的判断。技能选择了：上游身份与证据保留、主张—对照—观测—判定、具体配置核查、独立单位与分析对应、按阶段决策和真实执行交接。

没有采用默认多代理、固定实验数/样本数、强制重型框架、模型自评等于专家验收、自动运行/投稿，以及以引用数量或 star 数代替设计质量的做法。后续升级优先根据真实项目的漏项和错误修订，重新核对变化的来源与接口。
