# 方法来源、推荐阅读与取舍依据

2026-11-06 复查说明：本轮重新核对 [SciMON 的 ACL 原始记录/摘要](https://aclanthology.org/2024.acl-long.18/) 和 [LitPivot v3 的 arXiv 记录/摘要](https://arxiv.org/abs/2604.02600v3)。前者支持生成后与已有论文比较并迭代，后者明确想法变化会改变相关文献集合。将查重绑定当前科学内容、将证据绑定来源字节是本包据此作出的工程设计，并非论文验证过的本技能效果。本轮没有重新阅读全文或复核以下所有仓库；原有阅读范围和日期保留。

检索与核查日期：**2026-11-02（Asia/Tokyo）**。重点覆盖 2024–2026；保留一篇 2023 年的选题经验文章。以下“优先”指对本技能的具体用途，不是期刊、star 数或商业宣传的质量排名。论文页面、选定正文段落、作者/机构博客和仓库文档已阅读；**没有安装或复现这些外部系统**。

检索通过学术页面、出版物原页、作者/机构网站及 GitHub 完成。当前环境没有专用 academic-search MCP，故使用网页检索与原始页面核对，GitHub API 补查提交与许可元数据。不是穷尽检索。

访问限制：OpenReview 论坛和 PDF 直接访问遇到浏览器验证；P01/P02 的会议归属改由 ICLR 官方公开记录交叉核对，实质结论以可读取的 arXiv 文本为依据。没有将验证页面当作论文已读。

## 选择标准

优先选择能直接改变工作流的材料：有公开方法或实现、把构思连到真实文献、明确最近工作比较、有人类/执行评估或清楚讨论局限。优秀来源也只支持其实际检查的场景；小型 HCI 研究、模型评分、公开代码和真正实验结果不是同一种证据。

实际检索式示例：

```text
github scientific skills research ideation scientific brainstorming problem selection K-Dense
github Orchestra-Research AI-research-SKILLs research ideation brainstorming creative thinking
Can LLMs Generate Novel Research Ideas large scale human study 2025 code
ResearchAgent SciMON Chain of Ideas research idea generation 2024 2025
"The Ideation-Execution Gap" execution outcomes LLM human research ideas
"Scideator" github allenai
"IdeaSynth" "Iterative" "2025"
"Large Language Models Extend Known Research" "2610.17439"
```

再沿论文给出的官方代码链接、引用和作者页面核对。SciMON 的旧地址 `eaglew/clbd` 已重定向，不能把同名第三方实现误认成论文官方仓库；K-Dense 的当前仓库名也已变更为 scientific-agent-skills。提交快照见 [repository-audit.json](repository-audit.json)。

## 值得直接学习的仓库

| ID / 仓库 | 具体阅读位置与价值 | 本技能采用的部分 | 不直接照搬的部分 |
|---|---|---|---|
| R01 · [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `skills/scientific-brainstorming/SKILL.md`、`skills/hypothesis-generation/SKILL.md`；覆盖假设、竞争解释、证据与取舍 | 区分假设/观察/判断，保留反方与资源条件 | 不继承商业推荐、全部工具依赖或脱离当前任务的固定审批流程；skill 文本本身不是效果验证 |
| R02 · [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | `21-research-ideation/brainstorming-research-ideas` 和 `creative-thinking-for-research` 两个子 skill；适合选题操作设计 | 问题/解法起点、边界、简单比较、结构迁移等可选启发式 | 不把每个创造力框架的广泛有效性当作已有证据，不把全部技巧变成固定步骤 |
| R03 · [NoviScl/AI-Researcher](https://github.com/NoviScl/AI-Researcher) | `README.md` 的 grounded generation、deduplication、novelty filtering；包含 P01/P02 的构思与执行研究材料 | 先生成、结构去重、再展开并与最近工作比较；把执行研究当校准材料 | 不复制大规模批量生成和模型排名当作成功保障；示例价格不是当前预算 |
| R04 · [JinheonBaek/ResearchAgent](https://github.com/JinheonBaek/ResearchAgent) | `README.md` 的问题→方法→实验与多维 review；P04 官方实现 | 以核心论文为起点，用相关文献与结构化批评迭代 | 多个模型审查不等于独立专家认可；API 未识别出许可证，不复制其代码 |
| R05 · [EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty](https://github.com/EagleW/Scientific-Inspiration-Machines-Optimized-for-Novelty) | 作者从 ACL 论文链接的官方 SciMON 仓库；README 与 NLP/生物医学目录 | 候选与已发表工作比较后再修订，而不是一次生成就交付 | 相似度和新颖性优化不能取代科学差异判断 |
| R06 · [DAMO-NLP-SG/CoI-Agent](https://github.com/DAMO-NLP-SG/CoI-Agent) | `README.md`、prompts 目录入口；组织研究进展链与 Idea Arena 材料 | 恢复问题怎样演进、哪个假设仍未解决 | 不默认引入 Java/GROBID、嵌入服务和多个 API；旧报告成本不作为当前报价 |
| R07 · [cheerss/SciPIP](https://github.com/cheerss/SciPIP) | `README.md` 与 P08；强调正文、语义/引用检索与双路径生成 | 利用正文与跨文献概念，避免只靠论文元数据脑暴 | 不把 Neo4j、完整数据库或重型安装当作使用 light-idea 的前提 |
| R08 · [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | `README.md` 的 Generate Research Ideas 与 progressive search 说明 | 将构思与可执行检验相连，保留失败分支与停止条件 | 不自动运行它、执行外部生成代码或扩展成无人值守投稿；一个 workshop 实验不证明普遍成功 |
| R09 · [Research-Equality/RE-idea-generation](https://github.com/Research-Equality/RE-idea-generation) | `README.md` 的 primary/branch/operating skills 和最小路线 | 明确生成、展开、novelty assessment 的边界 | 属整合导航，可能复用 R01/R02 等内容，不能当作独立科学证据重复计数 |

R01/R02 最适合学习 skill 的表达与操作；R03/P01/P02 最适合校准“好提案”的判断；R04–R08 最适合学习有文献输入的迭代结构。R09 适合继续发现子 skill。Scideator、IdeaSynth、LitPivot 在本轮主要作为论文/作者材料使用，没有把未核实的 GitHub 链接冒称为官方代码。

本项目重新编写流程和辅助脚本，没有复制第三方代码或成段提示词。仓库许可证快照只是便于追溯，未来如要移植代码应检查具体文件及当时条款；`null`/`NOASSERTION` 不是已获授权。

## 优先读的论文

### P01 · 对“看起来新颖”的人类评估

[Si, Yang & Hashimoto. *Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers*. ICLR 2025；预印本 2024。](https://arxiv.org/abs/2409.04109) [会议记录](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ea94957d81b1c1caf87ef5319fa6b467-Abstract-Conference.html)

核对：摘要、会议版本记录和官方仓库。研究中 AI ideas 被评为更新颖，但可行性略弱，并发现自评与多样性问题。**采用**：先保留不同机制，查重与自评分开。**边界**：NLP 设定下的专家提案评分不是实验成果或跨学科成功率。

### P02 · 必须校准执行落差

[Si, Hashimoto & Yang. *The Ideation-Execution Gap: Execution Outcomes of LLM-Generated versus Human Research Ideas*. 2025 预印本；ICLR 2026。](https://arxiv.org/abs/2506.20803) [核对的正文 v1](https://arxiv.org/html/2506.20803v1) [会议公开列表](https://iclr.cc/Downloads/2026)

核对：§2、§4.1–4.2、§5、§7.2。43 位研究者执行随机分配的构思；AI ideas 从提案到执行后的评分下降更大。**不能改写成“人类执行结果显著优于 AI”**：按 idea 为单位的最终组间差异未显著。范围主要是受资源约束的 NLP prompting。采用最小验证、隐藏依赖和可解释阴性结果，属于基于该研究的设计推论，尚非对本技能的效果验证。

### P03 · 生成后回到最近工作

[Wang, Downey, Ji & Hope. *SciMON: Scientific Inspiration Machines Optimized for Novelty*. ACL 2024；预印本始于 2023。](https://aclanthology.org/2024.acl-long.18/)

核对：出版方摘要、元数据与作者官方代码链接。检索已有研究作为启发，比较后迭代新建议。**采用**：最近工作核查是生成循环的一部分。**边界**：距离或评分变好不能认证科学创新性，更不能证明新假设成立。

### P04 · 从核心论文到问题、方法和实验

[Baek, Jauhar, Cucerzan & Hwang. *ResearchAgent: Iterative Research Idea Generation over Scientific Literature with Large Language Models*. NAACL 2025；预印本 2024。](https://aclanthology.org/2025.naacl-long.342/)

核对：出版方摘要/记录与官方仓库说明。连接论文和实体知识，并让审查反馈修改提案。**采用**：问题、方法、验证一起检查；批评需要导致实质修改。**边界**：人类/模型提案评估不是候选已经过实证检验；本技能不要求部署多代理系统。

### P05 · 用共同要素表达文献和构思

[Radensky et al. *Human-LLM Compound System for Scientific Ideation through Facet Recombination and Novelty Evaluation*（Scideator，早期版本标题不同）. 2024–2026。](https://arxiv.org/abs/2409.14634) [核对的 v7 正文](https://arxiv.org/html/2409.14634v7)

核对：v7（2026-05-16）§2、§4 与附录 H。用途、机制、评价用于检索、组合和创新比较。**采用**：同一套结构贯穿证据与候选，检索近邻和结构相邻方向。**边界**：用户研究/模块消融不证明最终科研产出；不要混引旧版样本数字或标题。

### P06 · 少量方向反复展开，比只堆候选更有用

[Pu et al. *IdeaSynth: Iterative Research Idea Development Through Evolving and Composing Idea Facets with Literature-Grounded Feedback*. CHI 2025。](https://arxiv.org/abs/2410.04025) [出版 DOI](https://doi.org/10.1145/3706598.3714057)

核对：v2 摘要与 DOI 记录。以问题、解法、评价、贡献的可编辑要素支持迭代；研究考察探索与细化。**采用**：只对入围方向深入，允许用户修改某一要素。**边界**：交互体验和提案细节增加不等于方向更正确或更容易发表。

### P07 · 恢复研究演进链

[Li et al. *Chain of Ideas: Revolutionizing Research Via Novel Idea Development with LLM Agents*. 2024，arXiv v5。](https://arxiv.org/abs/2410.13185)

核对：摘要、版本历史、官方实现文档。把文献组织成发展链，再生成想法和实验设计。**采用**：解释旧问题怎样被逐步推进，剩下哪一个真实瓶颈。**边界**：作者的 Idea Arena 和费用报告不直接迁移成当前环境的可靠性或成本保证。

### P08 · 正文知识与多粒度检索

[Wang et al. *SciPIP: An LLM-based Scientific Paper Idea Proposer*. 2024；v2 更新于 2025-02-17。](https://arxiv.org/abs/2410.23166)

核对：v2 摘要与官方项目说明。区分仅关键词/元数据和正文/语义/引用带来的信息。**采用**：利用上游精读材料，补查概念近邻。**边界**：本文的生成质量评估不能外推到所有领域；检索模块不能自动证明覆盖完整。

### P09 · 生成、批评与检验相连

[Gottweis et al. *Accelerating scientific discovery with Co-Scientist*；v1 原名 *Towards an AI co-scientist*. 2025–2026。](https://arxiv.org/abs/2502.18864)

核对：当前 v2（2026-06-29）摘要、2025/2026 作者机构博客；本轮未把 v2 全文当作已读。**采用**：有研究目标约束的候选、竞争审查、后续实验验证。**边界**：所报告的具体生物医学验证不等于所有生成假设已验证，不复用临床有效性措辞。

### P10 · 接到执行，也保留失败和预算

[Yamada et al. *The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search*. 2025。](https://arxiv.org/abs/2504.08066)

核对：摘要、官方仓库和作者博客。以树搜索管理实验分支，报告三篇提交中的 workshop 级评审实验。**采用**：构思需要能转成检验，保存失败分支。**边界**：workshop 接受不是 ICLR 主会接受，有限实例不证明通用的自动科研成功率。

### P11 · 最适合衔接本项目的更新：idea 与相关文献共同变化

[Kambhamettu et al. *LitPivot: Developing Well-Situated Research Ideas Through Dynamic Contextualization and Critique within the Literature Landscape*. 2026。](https://arxiv.org/abs/2604.02600) [核对的 v3 正文](https://arxiv.org/html/2604.02600v3)

核对：§3、§4.3、§5 和 §7.1；v3 为 2026-09-22，机构博客称 UIST 2026。**采用**：文献触发 pivot 后，重建相关文献集合，检查问题/方法/评价一致性。**边界**：研究聚焦 HCI/NLP 的限时任务与文献定位，没有评估完整可行性或实际科研成功；本技能另设资源和 pilot 审查。

### P12 · 更新观察：陌生度与研究方向差异分开

[Liu et al. *Large Language Models Extend Known Research But Do Not Create New Research Directions*. 2026-10-12，预印本 v1。](https://arxiv.org/abs/2610.17439)

核对：摘要与版本记录；**新预印本，作为观察项而非定论**。作者在嵌入空间区分距离与方向新颖性。**采用**：提醒检查问题/机制差异，而不以语义陌生度代替创新。**边界**：指标与表示选择限制其解释，标题结论不能扩展为所有 LLM 或所有科学创造力的普遍规律。

## 博客与实践文章

| ID / 来源 | 时间与读取位置 | 对 skill 的用途与局限 |
|---|---|---|
| B01 · Paul Graham, [How to Do Great Work](https://www.paulgraham.com/greatwork.html) | 2023-07；选题、学习到前沿、发现异常与试做部分 | 结合兴趣、已有优势与问题价值；属于作者经验，不是经验证的选题算法 |
| B02 · Google Research, [Accelerating scientific breakthroughs with an AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) | 2025-02-19；架构与验证说明 | 了解生成/反思/比较/演化/接实验的整体思路；作者机构介绍不能替代独立评估 |
| B03 · Sakana AI, [The AI Scientist Generates its First Peer-Reviewed Scientific Publication](https://sakana.ai/ai-scientist-first-publication/) | 2025-03-12；2025-04-07 更新；Evaluation Process | 核实 workshop 与三篇提交的有限语境，避免从醒目标题推断通用能力 |
| B04 · Google DeepMind, [Co-Scientist: A multi-agent AI partner to accelerate research](https://deepmind.google/blog/co-scientist-a-multi-agent-ai-partner-to-accelerate-research/) | 2026-05-19；研究协作与假设生成部分 | 更新到当前研究工具背景；不据此要求购买/注册，也不默认相关工具已连接 |
| B05 · Ai2, [LitPivot: Developing research ideas through dynamic contextualization within the literature landscape](https://huggingface.co/blog/allenai/litpivot) | 2026-10-23；Why pivoting is hard / How LitPivot works / Our findings | 很直接地解释文献驱动的对齐与区分；样本和体验结论以论文为准，不夸大为发表效果 |

## 来源如何进入本 skill

以下是本项目的综合设计判断，不是来源逐字规定的统一流程。

| 本技能设计 | 主要依据 | 本地实现 |
|---|---|---|
| 区分事实、解释、假设、决定 | R01、P01/P02 的评估局限 | evidence ledger、证据深度与原文锚点 |
| 问题/机制/评价共同表示 | P05、P06 | ideation 矩阵、卡片、最近工作对照 |
| 先多样化再收敛 | R02、R03、P01 | 按问题/机制/预测去重，保留不同风险候选 |
| 生成后比较已有工作 | P03、P04、R03 | 查重日志、明确 delta、反方审查 |
| 改了方向就更新相关文献 | P11、B05 | 当前版本日志、pivot history |
| 可行性不被 novelty 分数遮住 | P01、P02 | 先看阻断条件，再作透明比较 |
| pilot、反证和可解释阴性结果 | P02、P09、P10，加上研究设计判断 | 区分预测、竞争解释、停止条件 |
| 本地轻量衔接 | 已检查的 light-literature 文件契约 | 标准库导入器、指纹和 ID 检查，无模型/API 依赖 |

未来更新应优先检查论文修订、官方仓库路径、执行型评估与真实使用失败。不要因为发现更多框架就持续膨胀入口文件；只有能改变决定的内容才进入工作流。
