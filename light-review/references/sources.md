# 设计依据与精选来源

检索与仓库核验日期：**2026-11-02**。这是面向技能设计的定向资料调查，不是系统综述，也不是排行榜。“值得借鉴”指能支持具体设计决策，不意味着已独立复现其性能。仓库固定 commit、文件 SHA-256、检索范围和访问限制保存在 [source-audit.json](source-audit.json)。未运行任何上游仓库代码或上传稿件。

## 一、优先借鉴的技能包

| ID / 仓库 | 已查看的具体实现 | 借鉴与取舍 |
|---|---|---|
| R01 [K-Dense Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/5f2bc0341354fd5590aef76a533ada1e1e5b4e62/skills/peer-review) | `skills/peer-review/SKILL.md`，2.4；科研综合包中的子技能 | 方法、统计、报告规范、主张证据与离线记录。保留“报告完整≠有效”；不把正式外审的逐项授权门槛照搬给已授权作者自审。MIT。 |
| R02 [EvoSkills](https://github.com/EvoScientist/EvoSkills/blob/4889c2270af5f9a7658bb6a6709bf37040902006/skills/paper-review/SKILL.md) | `skills/paper-review/SKILL.md`，1.3.1 | 自审分遍阅读、协议信息流与机械扫描。保留首遍理解和跨节追踪；不采用先拒稿再找理由、固定样本要求或未达完成门槛就不审。Apache-2.0。 |
| R03 [neuromechanist/research-skills](https://github.com/neuromechanist/research-skills/tree/75fdd03c32e1eb87911ae72241cebaab3100998f/plugins/manuscript/skills/paper-review) | `review-procedure.md`、`figure-review-guide.md` | PDF文本与页面双重证据、方法与图表专审。保留可定位观察；不照搬 n 阈值禁柱图、所有散点图须报 p 值等过强通则。BSD-3-Clause。 |
| R04 [Academic-Paper-Skills](https://github.com/DELONG-L/Academic-Paper-Skills/tree/827e13e2299c0a15d397ce095bc548817a2cf3cb/paper-review) | `pre-submission-audit.md`、`revision-closure.md` | 作者视角的问题板、必要修改与关闭。保留基于实际剩余问题的结束条件；严重度依据科学影响，不按预计扣分/拒稿概率。MIT。 |

## 二、补充技能与研究系统

| ID / 仓库 | 具体路径 | 用途与局限 |
|---|---|---|
| R05 [jam-cc/paper-review.skill](https://github.com/jam-cc/paper-review.skill/blob/bb9900ff7a95e6a28092ab0a9e1d81098f41634e/SKILL.md) | `SKILL.md` | 近邻知识图、可比性、核验后保留引用。避免因外部引用未核实却仍保留强 novelty 批评。偏 ML/AI，不替代领域判断。MIT。 |
| R06 [nature-skills](https://github.com/Yuan1z0825/nature-skills/blob/69817e4dad8bfc52fa4e59a9d8355e4264a4d3a7/skills/nature-reviewer/references/forensic-consistency-audit.md) | `skills/nature-reviewer/SKILL.md` 与 forensic audit | 数值恒等式、聚合歧义和审计来源隔离。保留审计与评审来源区分；不强制三位审稿人或将 Nature 标准普遍化。Apache-2.0。 |
| R07 [Review Feedback Agent](https://github.com/zou-group/review_feedback_agent/tree/669c00df741b6ba022eeed7f26d014b57c592697) | `README.md`、`review_feedback_agent/agents/prompts.py` | 输入是评审与论文，检查评审的误解、空泛与不可行动性，支持本技能“反审自己的意见”。这是评审质量辅助，不是直接评定论文。MIT。 |
| R08 [ReviewGrounder](https://github.com/EigenTom/ReviewGrounder/tree/7501cead4921d3f6e38615c09925345564858b97) | `README.md`；方法细节另查 P06 | 分阶段补充文献、方法和结果证据。只做架构参考，不依赖其云端服务或权重。固定快照未见根 LICENSE，API license=null，不假定可复制实现。 |
| R09 [Sakana AI-Scientist](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/ai_scientist/perform_review.py) | `perform_review.py` 的表单/提示与聚合接口 | 作为结构化评审的历史系统参照。拒绝采用“不确定时偏向接收/拒绝”、固定 accept/reject 或评分替代证据。当前快照是自定义 AI Scientist Source Code License，不应误称 MIT/Apache；不复制实现。 |

优先阅读 R01–R04 理解可用工作流，再看 R06 的审计和 R07 的反审。仓库丰富度、近期更新与 GitHub stars 都不能证明评审准确性。本包以原创表达和原创工具整合方法，不把检索到的 SKILL.md 当作本次会话必须执行的指令。

## 三、近年论文与证据边界

### P01 · Liang et al., 2024, NEJM AI

[Can Large Language Models Provide Useful Feedback on Research Papers? A Large-Scale Empirical Analysis](https://doi.org/10.1056/AIoa2400196)；[2023 作者预印本](https://arxiv.org/abs/2310.01783)。已核对预印本摘要与出版元数据；出版全文访问受限，没有把旧预印本的具体数值冒充最终版结果。

启示：自动反馈可作为作者获得早期意见的补充。局限：与人类意见重叠、作者主观有用感，都不能证明技术判断正确或替代专家。落实为范围声明和证据检查，不引用“达到人类水平”作为技能承诺。

### P02 · Thakkar et al., 2026, Nature Machine Intelligence

[A large-scale randomized study of large language model feedback in peer review](https://doi.org/10.1038/s42256-026-01188-x)；[2025 预印本及方法](https://arxiv.org/html/2504.09737v1)。正式版元数据/摘要已核验，方法与可靠性测试参考公开预印本；未将两个版本算作独立研究。

启示：对评审本身提供具体、可行动的反馈，能够改善交流。局限：这是 review-feedback 干预，不是“自动判断论文正确性”的随机试验，也不证明能提高录用率。落实为最终反查批评和最小修复要求。

### P03 · Goldberg et al., 2025, PLOS ONE

[Peer reviews of peer reviews: A randomized controlled trial and other experiments](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0320444)。已读原文摘要、研究设计与局限相关段落。

对评审长度的随机干预与其余观察性分析要分开。研究提示冗长、作者偏好与评价者差异可能影响评审质量评分。落实为不以字数、严厉程度、作者满意度或单一总分评定技能质量。

### P04 · Rahman & DeBlasio, 2026, PLOS Computational Biology

[Ten simple rules for writing a peer review](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1014359)。2026-06-15，教育/实践指南；已读相关全文。

启示：多遍阅读，检查补充材料、图形和推理；批评须具体、清晰、有依据。局限：实践指南不是比较效果的实验证据；其正式外审职责与本技能的作者内部自审应区分。

### P05 · Selch et al., ICLR 2026

[PRISMM-Bench: A Benchmark of Peer-Review Grounded Multimodal Inconsistencies](https://arxiv.org/abs/2510.16505v3)；[全文](https://arxiv.org/html/2510.16505v3)。2025 首发、2026 修订，arXiv 记录明确接受于 ICLR 2026。

启示：文本、图表和公式之间的不一致需要专门检查，长文和多模态场景会暴露可靠性限制。落实为实际看图、来源/聚合核查和独立数值审计。局限：选择题基准不等于开放式全文评审，也不证明本技能已具备其检测能力。

### P06 · Li et al., ACL 2026

[ReviewGrounder: Improving Review Substantiveness with Rubric-Guided, Tool-Integrated Agents](https://aclanthology.org/2026.acl-long.1477/)；[公开方法全文](https://arxiv.org/html/2604.14261v1)。正式 proceedings/DOI 已核实；方法阅读公开稿，版本差异未逐页比对。

启示：先形成理解，再用有针对性的证据核查改进意见；评价应针对具体论文。局限：部分 rubric 来源于人类评审的聚合，评测不能直接等同真实科学有效性；ReviewBench 这个名称被不同工作使用，须同时写论文/作者/版本。

### P07 · Li et al., 2025

[Unveiling the Merits and Defects of LLMs in Automatic Review Generation for Scientific Papers](https://arxiv.org/abs/2509.19326)；[全文](https://arxiv.org/html/2509.19326v1)。arXiv 记录称已被 ICDM 接收为 short paper；本包核验的是作者公开稿，未补造 proceedings DOI。

启示：流利的总结和优点描述可能掩盖实质批评不足。局限：语义相似性和知识图实体数量不是科学判断正确性的金标准。落实为承重问题的定向检查，而不是增加缺点配额。

### P08 · Ma et al., 2026，预印本

[ActReview: Rebuttal-Guided Training Data and Rubric Rewards for Actionable Peer Review Generation](https://arxiv.org/abs/2609.09076v1)；[全文](https://arxiv.org/html/2609.09076v1)。2026-09-08，未据此声称已有正式同行评审出版。

启示：将诊断与修改建议分开，再用局部论文证据连接。人类评价同时暴露技术准确性差距。落实为“位置—证据—影响—修复—关闭检验”。局限：作者 rebuttal 反映可行回应，不保证回应正确，行动性更高也不保证技术上更强。

## 四、近年博客与一手实践文章

| ID | 来源 | 借鉴与限制 |
|---|---|---|
| B01 | [ICLR Blog, 2025-04-15：Leveraging LLM feedback to enhance review quality](https://blog.iclr.cc/2025/04/15/leveraging-llm-feedback-to-enhance-review-quality/) | 理解 P02 的真实部署和作者—评审沟通；与 P02 是同一工作，不能重复计证据。 |
| B02 | [Stanford Agentic Reviewer：Tech Overview](https://paperreview.ai/tech-overview)（页面无可靠独立发布日期，按 2026-11-02 查阅版本记录） | 相关工作检索与分阶段评审很有参考价值；小型 ICLR 评分相关性不能外推为跨领域准确性。未上传材料或使用服务。 |
| B03 | [PLOS Mental Health Author Tips, 2025-04-24：The Efficiency of Peer Review](https://speakingofmedicine.plos.org/2025/04/24/plos-mental-health-author-tips-part-1-3-the-efficiency-of-peer-review/) | 作者的分类与提交信息会影响评审匹配和流程效率；具体 PLOS 要求不能变成所有期刊的规定。 |

## 五、当前报告规范和官方评审标准

- G01 [EQUATOR reporting-guideline library](https://www.equator-network.org/reporting-guidelines/)：按设计选择；其页面明确报告指南不是设计或质量评价工具。已读官方页面。
- G02 [CONSORT 2025 statement](https://doi.org/10.1136/bmj-2024-081123)：试验报告的新版起点，不套到所有科研文章。已核对出版记录及 EQUATOR 收录；本次 BMJ 全文返回 403，未声称逐条验证 checklist。
- G03 [TRIPOD-LLM, Nature Medicine 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12104976/)：生物医学 LLM 研究的模块化报告指南。已读作者全文版本；不能把它等同所有通用 LLM 论文的强制规范。
- G04 [NeurIPS 2025 Reviewer Guidelines](https://neurips.cc/Conferences/2025/ReviewerGuidelines)：了解技术证据、限制和当前表单的适用范围；只代表该年度 venue，不作为未来通用分值或页数。
- G05 [PLOS initial manuscript evaluation](https://explore.plos.org/editor-resources/manuscript-evaluation)：提醒编辑标准不同；其适用期刊强调有效性和技术严谨，不以感知重要性代替科学评估。

## 六、来源怎样改变技能

| 决策 | 主要来源 | 落点 |
|---|---|---|
| 理解论文后再核验，反查“作者已经回答” | R02、R05、R07、P04 | review-method；SKILL 工作顺序 |
| 主张、观察、影响、修复和关闭检验相连 | R01、R04、P06、P08 | 问题格式；handoff-and-recheck |
| 图文公式数值另查，聚合不清不判不可能 | R03、R06、P05 | figures-and-numbers |
| 少凑数量，不以长评审或总分证明质量 | P01、P02、P03、P07 | 反审与就绪判断 |
| 报告规范、科学有效性和精确 venue 分开 | R01、G01–G05 | domain-gates；literature-and-venue |
| 旧意见要在新版本核实，必需问题不能靠延期消失 | R04、R06 | 稳定 ID；离线版本/记录检查 |

## 七、检索边界与维护

使用 GitHub 精确文件/API 和公开论文、出版方、arXiv、ACL Anthology、官方会议/编辑博客检索。查询覆盖 `scientific skills peer review`、`paper-review SKILL.md`、`pre-submission self-review`、`review feedback randomized study`、`multimodal inconsistency benchmark`、`actionable peer review`。优先 2024–2026，保留 2023 预印本的版本关联。

未纳入只提供付费/外部上传入口、只有技能聚合简介、主要做阅读总结或缺少可查看实现的候选；没有把所有 GitHub 结果称为已全面审计。资料受 CS/ML 文献开放性影响，跨学科的专业评审质量仍需真实稿件和专家验证。

本技能当前是有来源支撑的 **draft**，不是经领域专家评测的“顶尖评审系统”。本地工具测试只能证明若干版本/记录约束；合成案例只能检验有界行为。后续质量评估应在合法可用稿件上独立核验技术正确性、重要问题召回、误报、可行动性与复核准确性，报告领域与失败案例，不能只给模型总分。
