# 来源评述与取舍

检索/阅读日期：2026-11-02。优先检查实际 SKILL、流程、模板接口和许可，而非根据名称或星数排名。以下为设计借鉴，并未把上游 skill 作为依赖，也未复制上游脚本进运行包。详细定位和锁定版本在开发仓库 `research/sources-lock.json` 与 `research/repository-review.md`。

| 仓库及具体位置 | 值得借鉴 | 本 skill 的取舍 |
|---|---|---|
| [handsomestWei/patent-disclosure-skill](https://github.com/handsomestWei/patent-disclosure-skill)：`skills/patent-disclosure`、`patent-application`、`patent-oa` | 从交底到申请的分工、必要/优选技术特征、图件与结构登记 | 可直接从有足够依据的技术材料起稿；不把特定前置文件存在等同内容已充分，也不锁死先前的必要性判断 |
| [HuangXinzhe/cn-patent-drafting](https://github.com/HuangXinzhe/cn-patent-drafting)：`references/claims-and-consistency.md` 等；当前入口位于插件子目录 | 中国申请文件衔接、术语与参数一致性、检索和版本记录 | 按请求交付，不把全部内部材料强制包装成法定申请文件 |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-paper-to-patent)：`static/core/workflow.md`、发明类型片段 | 论文、公式、图、代码的稳定来源定位；完整的实施链分析 | 保留事实层和说明书层的双层支持；不要求简单任务跑所有阶段 |
| [OpenGHz/academic-human-in-the-loop](https://github.com/OpenGHz/academic-human-in-the-loop)：`skills/claims-drafting`、`specification-writing`、`patent-review` | 权要主线、从属退路、说明书支持与审查者视角 | 不继承固定模型、多轮外部调用、固定独权数量或将两部式绝对化等约束；审阅不冒充官方审查 |
| [yjmm10/patent-skills](https://github.com/yjmm10/patent-skills)：根 `SKILL.md` | 规范核验、材料转换、交底迭代、按需完整申请 | 自动使用合理默认模板，沿用已授权范围，不为普通撰写反复请求模板/流程确认 |
| [ichen-dev/patent-writing-skill](https://github.com/ichen-dev/patent-writing-skill)：根 `SKILL.md`、Word模板链 | 实际 Word 交付和图件可追溯意识 | 仅作为评估对象；不复制GPL实现/模板，不采用10%关键词重合门槛、强制多站数量或改写真实发明去“过查重”的做法 |
| [aipoch/medical-research-skills](https://github.com/aipoch/medical-research-skills)：`scientific-skills/Academic Writing/patent-assistant` 与 `Evidence Insight/patent-claim-mapper` | 综合科研包中的专利子技能、交底信息收集与特征比较 | 区分可专利性和FTO；示例脚本/API未实际执行，不当作已可用集成 |
| [arcprime-ip/patent-prompts](https://github.com/arcprime-ip/patent-prompts)：`pre-filing/prior-art-analysis`、`claims-drafting` | 单篇新颖性与多文献创造性分开、逐要素与关系核对 | 迁移比较方法而非美国法律结论；从属限定同样需要逐项支持 |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)：`skills/database-lookup/references/uspto.md` | 大型科研包中的专利数据入口、接口版本和数据覆盖意识 | 不依赖旧教程里的固定USPTO/PEDS端点，实际使用前核验官方当前接口；该包不是中国专利撰写规则来源 |
| [patsnap/PatentAgentBench](https://github.com/patsnap/PatentAgentBench/tree/main/patent-drafting-bench) | 从完整交底到权要/说明书/图件的任务设计、通用与个案标准分开 | 用于设计后续行为测试；本次未跑其完整数据集，不宣称基准成绩 |

## 原创实现与官方校验

本 skill 的入口、参考流程、案件结构、模板和3个执行脚本均独立编写。设计上的共同原则与上游出处在表中说明；法律和提交要求以 [官方依据](jurisdictions.md) 中的当前文件复核，而非以仓库提示词作为权威。

尤其纠正了几类容易传播的问题：以词语相似度判新颖性；把缺乏来源的“补充实施例”当作支持；用新材料补已提交申请；固定权要数量；把自评分等同授权概率；把 DOCX 当成已经满足电子申请格式。
