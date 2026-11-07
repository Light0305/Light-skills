# 选刊方法的调研依据与取舍

调研日期：**2026-11-02**。这是为本skill设计所做的定向调研，不是系统综述，也不是仓库性能排行榜。筛选依据是任务贴合度、可读实现、来源透明度、实际评测与已知局限；没有以star数或出版品牌替代判断。

本文件按需阅读。可复查的仓库commit、查看文件、许可证元数据、论文作者与出版日期见 [source-register.json](source-register.json)。以下是独立归纳与本包的设计判断，不是上游原文拼接；未复制上游代码、期刊数据库或整篇文章。未发现明确许可证的项目仅作公开思路参考，不视为获得再分发许可。

## 一、最值得读的选刊相关仓库

### R1. Awesome-Journal-Skills：检索、期刊资料与评测分开

[仓库](https://github.com/brycewang-stanford/Awesome-Journal-Skills) · MIT · [本次版本的选刊方法](https://github.com/brycewang-stanford/Awesome-Journal-Skills/blob/932eb23331721b16e967c59f093781be1928b498/shared-resources/journal-selection/journal-match.md)

- **读了什么**：journal-match、match_venues/match_lib、eval_journal_match及已发布评测结果；包含科研大包内的小模块，不只看仓库名。
- **值得吸收**：召回只是候选阅读列表；期刊实际发表内容与scope有不同信息；工具和评测共用检索代码；分开披露覆盖不足。
- **本包取舍**：不打包其巨大静态目录，不把venue skill当官方政策，也不采用需要猜测单稿录用概率的期望时长计算。其指标是检索到历史发表刊的能力，不能证明真实选刊/录用效果。

### R2. horizon-academic-writing：完整科研技能包中的选刊模块

[仓库](https://github.com/yujie-jason-zhang/horizon-academic-writing) · MIT · [选刊skill](https://github.com/yujie-jason-zhang/horizon-academic-writing/blob/c8d8b38b29a17348d106af408ff8bad99e480a05/skills/horizon-journal-recommender/SKILL.md)

- **读了什么**：horizon-journal-recommender入口；检查配套guide的存在与内容组织。
- **值得吸收**：粗筛后只深核重点候选；单刊/名单核查分流；官方scope与近期内容双重证据；LetPub是辅助来源而非准入条件。
- **本包取舍**：不默认SCIE或订阅优先，不从摘要估计可量化“档次差”；增加无正文时的定位与直接给light-write的交接。仓库提及的分区停更另以原始官方声明核实。

### R3. ChineseResearchLaTeX：大包中的 paper-select-journal

[仓库](https://github.com/huangwb8/ChineseResearchLaTeX) · MIT · [小skill入口](https://github.com/huangwb8/ChineseResearchLaTeX/blob/3022b19f3bcc6b085e1cd636c81aa2f59a6f70e1/skills/paper-select-journal/SKILL.md)

- **读了什么**：入口、质量核查清单，并检查候选/抓取/报告脚本与模板的目录结构；未运行上游脚本。
- **值得吸收**：稿件画像、候选发现、事实抓取与语义判断分开；报告能追溯到中间证据。
- **本包取舍**：不依赖内置2023IF表、不设统一IF≥3、不把近三个月PubMed当所有学科的适配标准，也不沿用该项目专属基础设施。保留分阶段核验，改成跨领域和可调整时间窗口。

### R4. paper-skill：把选刊与写作/转投衔接

[仓库](https://github.com/cLin-c/paper-skill) · MIT · [journal-strategy](https://github.com/cLin-c/paper-skill/blob/366b1da524de3a980e69deb49dd4a28547c6caac/journal-strategy.md)

- **读了什么**：journal-strategy与verification-policy。
- **值得吸收**：投稿顺序、拒稿后区分一般科学问题与期刊特定问题；官方要求与样本论文观察分开。
- **本包取舍**：不要求引用目标刊的固定比例、不把样本文章的规律变成政策；本包只输出写作定位，不扩成全文写作/审稿skill。

## 二、可借鉴但需有选择使用的实现

### R5. journal-recommender：简洁的中国情境工作流

[仓库](https://github.com/zero565656/journal-recommender) · 本次GitHub元数据未给出明确主许可证 · [入口](https://github.com/zero565656/journal-recommender/blob/407aff106677aac090bf2d177155db15e3593126/SKILL.md)

- 看过入口与参考文件结构；scope、费用、收录、风险一起比较的短流程有用。
- 不采用其“先停下来问偏好再检索”的强制等待，也不采用由摘要先估分区再上下分层的做法。作者未给偏好时先探索、明确假设更适合本地工作流。

### R6. journal-fit-finder：语言、地区和证据来源意识

[仓库](https://github.com/hztopcu/journal-fit-finder) · MIT · [入口](https://github.com/hztopcu/journal-fit-finder/blob/2624d0b40a444951157c626c01bda73c65c60b23/journal-fit-finder/SKILL.md)

- 看过入口；全文/摘要输入、地区语言路线、指标体系区别和未发表材料保护值得参考。
- 本包不沿用固定出版商数量/候选配额；语言和地区根据用户与读者需求确定，不据此推断稿件层次。该仓库内容广，不等于各领域已有专家验证。

### R7. journal-recommendation-agent：研究代码中的受限语义匹配

[仓库](https://github.com/LLM-Journal-Rec/journal-recommendation-agent) · MIT · [prompt.py](https://github.com/LLM-Journal-Rec/journal-recommendation-agent/blob/dca2d8a54c0a03e63bb8e037052b97bab962020f/prompt.py)

- 看过README和提示构造代码；强调方法、科学问题与学术读者，并限定候选scope资料。
- 本包不保留固定输出十刊和省略解释的实验输出方式；也不要求外部DeepSeek API。它能研究语义匹配，但现实费用、政策、收录与作者偏好仍要另核。

### R8. lucanard/journal-recommender：多阶段推荐引擎的工程参考

[仓库](https://github.com/lucanard/journal-recommender) · 本次未发现明确主许可证 · [recommender.py](https://github.com/lucanard/journal-recommender/blob/3f8a57f9cff86c761eab48546cf61c5a9430882a/recommender.py)

- 看过引擎的候选检索、约束过滤、重排与fallback相关实现。
- 借鉴分离检索与决策的架构；不采用自动放宽硬条件、用代理指标当JIF或忽略缺失费用的做法。代码里的参考文献功能开关默认关闭，不能因存在函数就称功能已投入使用。本包不运行它，也不搬运其数据库。

另外检查了 [nature-skills](https://github.com/Yuan1z0825/nature-skills) 的相关文件树（Apache-2.0）。其文献检索、写作适配等模块可提供邻接参考，但本次未把它宣称为已有专门选刊实现；本地light-write接口才是本包实际交接依据。

## 三、优先阅读的近年研究

“研究发现”与“本包采用的设计”分开。以下出版者/Crossref书目相互核对；阅读深度不同，未声称所有论文均已全文精读。

### P1. Xu, Xie, Sun & Cheng (2023)：作者投稿行为的系统综述

**Factors affecting authors' manuscript submission behaviour: A systematic review.** *Learned Publishing*, 36(2), 285–298. [DOI](https://doi.org/10.1002/leap.1521)

- **核查**：出版者正文与摘要、Crossref元数据。综述纳入132篇文章，将信息获取、期刊评价、投稿反馈及作者背景组织为相关因素。
- **用途**：说明选刊是多因素、有反馈的决策；支持显式记录作者约束与转投更新。
- **限制**：因素综述不是经过验证的通用权重表，也不能推导单稿概率。本包没有将其改造成任意加权打分。

### P2. Entrup, Ewerth & Hoppe (2023)：实际推荐服务的比较

**A Comparison of Automated Journal Recommender Systems.** TPDL 2023, LNCS 14241, 230–238. [DOI](https://doi.org/10.1007/978-3-031-43849-3_20)

- **核查**：出版者摘要、机构库记录及可见作者稿文本；Crossref书目。
- **用途**：关注输入、功能、隐私、结果重叠与准确性；本包因此采用多路召回并说明推荐器覆盖范围。
- **限制**：2023年的服务快照不能代表今天的工具排名；历史发表刊命中也不等于最优投稿选择。

### P3. Entrup et al. (2024；2023在线)：B!SON开放选刊系统

**Comparing different search methods for the open access journal recommendation tool B!SON.** *International Journal on Digital Libraries*, 25, 505–516. [DOI](https://doi.org/10.1007/s00799-023-00372-3)

- **核查**：出版者正文及Crossref；在线为2023-07-20，卷期为2024，不是年份错误。
- **用途**：标题/摘要与参考文献可提供不同匹配信号，开放数据、解释与OA政策也影响使用。本包采用参考文献邻域与主题路线互补。
- **限制**：OA候选宇宙与元数据覆盖限制外推；不把仅OA工具视为全部期刊，也不把历史工具/政策状态当当前事实。

### P4. de Campos, Fernández-Luna & Huete (2024)：解释要绑定证据

**An explainable content-based approach for recommender systems: a case study in journal recommendation for paper submission.** *User Modeling and User-Adapted Interaction*, 34, 1431–1465. [DOI](https://doi.org/10.1007/s11257-024-09400-6)

- **核查**：出版者正文中方法、用户研究及限制；Crossref书目。
- **用途**：相关论文、主题与匹配词应能解释推荐；本包把解释落实为可比论文及相同维度/关键差异。
- **限制**：用户研究涉及17位生物医学背景参与者、68次推荐评价，关注透明度等感知指标；不证明投稿成功率提高，更不是跨学科万能评分。

### P5. Entrup, Ewerth & Hoppe (2024)：大刊与文本长度偏差

**Can Editorial Decisions Impair Journal Recommendations? Analysing the Impact of Journal Characteristics on Recommendation Systems.** RecSys 2024, 1062–1066. [DOI](https://doi.org/10.1145/3640457.3688194)

- **核查**：作者机构库摘要、会议记录、Crossref；ACM落地页本次403，未声称读到该页全文。
- **用途**：实验显示更长摘要/更多篇数可抬高某些系统中的排序。本包检查出版量偏差、比较代表性研究，不以裸匹配篇数排名。
- **限制**：特定算法上的偏差实验不意味着任何大刊都不适合，也不意味着所有推荐器都有相同偏差。

### P6. Ng et al. (2024)：透明度工具的用户需求

**A mixed-methods survey and focus group study to understand researcher and clinician preferences for a Journal Transparency Tool.** *Scientific Reports*, 14, 26626. [DOI](https://doi.org/10.1038/s41598-024-77790-z) · [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11535019/)

- **核查**：出版者/PMC可见检索文本和Crossref。直接页面请求分别遇到重定向/验证码；这里只依可见摘要与方法片段，不报告未读细节。
- **用途**：将透明度、可获得的费用/范围等信息纳入决策，而非只给一个指标。
- **限制**：生物医学研究者/临床群体的需求研究，不能直接套成全部领域的偏好权重。

### P7. Laine et al. (2025)：识别可疑期刊的编辑观点

**Predatory journals: What can we do to protect their prey?** *PLOS Medicine*, 22(4), e1004542. [DOI](https://doi.org/10.1371/journal.pmed.1004542)

- **核查**：出版者页面、Crossref。
- **用途**：作为编辑界对可疑期刊问题的近期观点补充，实际操作采用TCS/EIFL的可核查信号。
- **限制**：**Editorial**，不是系统综述或干预试验，不把它当检测器性能证据。

### P8. Yan et al. (2026)：LLM与官方范围的语义对齐

**An LLM-Powered Semantic Alignment Framework for Journal Recommendation.** [arXiv:2606.27930v1](https://arxiv.org/abs/2606.27930v1) · [正文](https://arxiv.org/html/2606.27930v1)

- **核查**：arXiv版本、作者、日期、正文中的方法与评测；相关代码见R7。
- **用途**：按方法、科学问题和读者比对scope，并将参考文献作为辅助信号。
- **限制**：本次作为**预印本**使用；主要数据来自统计及相关领域49本刊。Top-k命中历史发表刊不是录用率。正文“Received 5 June 2009”是与arXiv日期不符的模板残留，不能用来确定发表年份。

### P9. Luo (2024)：投稿顺序依赖反馈与成本

**When and Where To Submit A Paper.** [arXiv:2402.01745v1](https://arxiv.org/abs/2402.01745v1) · [DOI](https://doi.org/10.48550/arXiv.2402.01745)

- **核查**：arXiv元数据与摘要；理论经济学**预印本**。
- **用途**：提醒投稿反馈和修改会改变下一步选择，避免机械按指标逐级下降。
- **限制**：理论模型依赖假设；本包只采用定性启示，不使用未经校准的概率计算所谓最佳顺序。

## 四、博客与实用指南

| 来源 | 日期/性质与阅读范围 | 对本包的价值与局限 |
|---|---|---|
| [EIFL：Choosing a journal for your research](https://www.eifl.net/system/files/resources/202409/choosing-a-journal.pdf)，Milica Ševkušić | 2024-08，19页机构指南；查阅可提取正文 | 身份、编辑实践、OA/许可、费用和冒名刊的具体核查；可按本地规则调整。不是工具准确率研究。 |
| [Rebeka Kiss / PolTextLab：Testing Publisher AI Tools for Journal Selection](https://promptrevolution.poltextlab.com/testing-publisher-ai-tools-for-journal-selection-a-guide-for-researchers/) | 2025-06-11，实测博客；可见检索快照，直接抓取502/SSL失败 | 用跨领域案例提醒应用词和方法词可能错配。小规模演示，不据此宣布某工具普遍更优；细节不设为硬规则。 |
| [TIB B!SON：New publication](https://projects.tib.eu/bison/en/news/detail/neue-publikation/) | 2024-10-24，项目研究博客/消息；检索快照可见，直接页面无可提取正文 | 连接2024偏差论文与实际系统改进；证据仍回到P5，而非仅引用宣传性介绍。 |
| [BMJ Author Hub：How to choose a journal](https://authors.bmj.com/before-you-submit/how-to-choose-a-journal/) | 页面未标明确发布日期；2026-11-02检查可见正文 | 范围、读者、编辑服务和顺序投稿；不是只有“近年发表”才有价值，但不能冒称2026新文。 |
| [Taylor & Francis：Choosing a journal](https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/) | 未确认首发年；检查可见正文 | 明确支持写作前考虑读者和文章类型，直接契合light-write前置定位；其推荐器限自有出版生态。 |
| [T&F：Understanding journal metrics](https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-metrics/) | 未确认首发年；可见正文 | 区分指标年份和决定时间口径，提醒desk reject可使首轮统计很短；具体规则回到目标刊。 |
| [Think. Check. Submit. Journals](https://thinkchecksubmit.org/journals/) | 官方页注明2023-03更新、2023-06修订；本次读取当前页面 | 信任核查与身份/费用/评审/保存信号；不把清单简化为“某成员资格=绝对安全”。 |

补充专业阅读：Jody W. Zylke (2024), **Selecting a Journal**, in *Principles of Scientific Writing and Biomedical Publication: A JAMA Editors Guide for Authors*, pp.21–24，[DOI](https://doi.org/10.1093/med/9780197783030.003.0003)。这是书章；核查摘要与书目，未声称读到订阅全文。网页在线日期与Crossref印刷日期不同，登记时保留各自口径。

## 五、证据怎样落实到本skill

| 设计决定 | 主要来源 | 这里额外做的判断 |
|---|---|---|
| 写作前从结果/提纲定位，不强求全文 | T&F指南、R1、现有light-write | 已有/计划证据分开，生成可携带brief |
| 多路召回与最终决策分开 | R1、R2、P2、P3 | 不依赖固定期刊库或外部LLM服务 |
| 官方scope + 可比研究 + 最强反证 | P4、P8、R2 | 增加反证、区别policy/observation，允许有说明的稀疏先例 |
| 不以裸匹配数量或单一推荐器排名 | P2、P5、PolTextLab博客 | 增加覆盖偏差检查，不强制出版商配额 |
| 硬条件三态、未知不算通过 | 官方来源口径、R2/R6的核查思路 | 用本包独立编写的离线脚本检查误放行；不是统计验证的推荐模型 |
| 转投要看反馈与修复成本 | P1、P9、R4 | 不计算伪精确录用概率，不机械降档 |
| 中国情境采用历史版本与单位规则 | [2026-03-27原始声明](https://las.cas.cn/news/tzgg/202603/t20260327_8178738.html) | 不借用第三方“最新中科院分区”说法；后续使用仍需查新变化 |
| 约束保护研究内容和主张边界 | 当前本地light-write接口 | 只改变论证重点，不改变研究事实，不把选刊结论自动写成作者决定 |

研究支撑的是这些设计选择的合理性，**不证明本skill已提升真实录用率**。自动检查和待做的真实使用评测范围见 `../evaluations/validation-2026-11-02.md`。
