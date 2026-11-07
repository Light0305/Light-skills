# 接入现有 Light-Skills

各阶段只记会影响后续的增量，表中输入均为真实项目产物。路径是新项目默认位置，已有路径原地兼容。记忆读取不能继承“已读”“verified”“ready”的科学含义；本轮关键工作仍回原生文件核对。

| 技能 / 工作区 | 优先读取 | 值得记住的增量 |
|---|---|---|
| literature-search / Literature | 相关 Searches 轮次的 query_plan/screening/synthesis；manifest/meta；note 与关键原文锚点 | 检索问题/范围变化、关键挑战文献、阅读缺口；保留 paper_id/DOI，不再复制一套文献库 |
| light-idea / Idea/IDEA-* | ideas.json 的候选与版本、decision、证据及来源指纹、当前内容的查新日志、有关历史/card | 为什么选择/暂停/合并/修订方向、竞争解释、被挑战前提和重启条件；恢复时查旧结论适用性，归档 IDEA 与科学 I01 区分 |
| light-design / Design/PROT-*/v* | context、design、plan、protocols | 设计版本/执行范围、独立单位、主要比较与阈值理由、待确认资源；不把草稿/目录新版本写成可执行 |
| light-experiment / Experiment/EXP-* | campaign、冻结输入、相关 runs/spec/result/assessment、execution-report、events | 实际运行身份与技术状态、有效阴性/失败区别、成本边界、故障教训；不混淆重试与独立样本 |
| light-anaysis / Analysis/AN-* | analysis-plan/plan-lock、analysis、report、receipt、handoff、相关原始值 | finding 的范围/不确定性、上游有效性、竞争解释和回路原因；代码错误修正后旧结论及依赖待复核 |
| light-crawl / Acquisition/ACQ-*/case | scope、target、evidence、reports、实际数据清单 | 数据版本/覆盖、字段/采集限制、失败/缺失、可复现入口；采集成功不等于无偏数据 |
| light-journal-select / Journal/JRN-* | report、light-write-brief、selection-packet、来源日期 | 暂定还是作者决定、目标读者/类型、硬条件未决和重核时点；时效信息设 review_after |
| light-write / Write/PAPER-* | 当前主稿与源文件、主张证据/术语账本、brief、drafts/submissions | 当前被采用的稿件版本、核心论证、主动缩小的主张、未决证据；一篇稿的修订不建成多篇论文 |
| light-diagram 及子技能 / Figure/Methods 或 Mechanisms/FIG-* | handoff、实际提示词、参考/生成候选、选定 native/output、QA | 采用哪张参考/后端、关键科学关系修正、实际可编辑边界、当前导出；不把示意图当实验观测 |
| light-chart / Figure/Data/FIG-* | 输入映射、实际代码/helper、图注、导出、QA | 分母/单位/误差条含义、决定性图形修改与采用版本；原始数值仍留专业来源 |
| light-review / Review/REV-* | review/packet、issues、覆盖范围、复核依据 | 对应稿/图版本与 LR issue、最低修复、addressed/verified 区别、剩余阻塞；状态回原生记录核对 |
| light-patent / Patent/PAT-* | case、源材料/特征/权要支持、检索与版本、公开事实 | 保护主线、证据缺口、申请阶段/公开约束；论文作者不自动变发明人 |
| light-software-copyright / SoftwareCopyright/SWC-* | case、inventory/selection、源码冻结映射、functions/manual、layout-profile、source-pages、audit 与实际三份 DOCX | 真实软件版本/登记范围、确认事实与未知事实、补正原因；保留功能说明/软件代码/软件说明书的采用版本与检查范围，论文项目根不自动当源码根 |

## 共同交接

专业技能开始长期项目工作时，若 Memory 已存在，先读 current 并对当前任务调用 context/show；无记忆或无可用工具时仍可从实际材料工作。阶段结束或出现实质变更时，由宿主把已核对的增量写入 Memory，或者给出有来源的待记忆增量供后续接入；不用重复初始化所有阶段，也不以缺少记忆阻断专业任务。

专业身份放条目文本/slot/scope/tags 与原生来源定位，Memory 的 MEM 编号仅标识记忆。若项目用目录工具，可登记固定 `Memory/` 归档项；记忆初始化器独立可用，不强制创建 project.json，不修改其科学内容。

## light-leader 的读取接口

`context` 返回 schema_version、memory_id、当前事件游标、query、选中条目、对应状态/来源、未解决冲突、需复核项和预算省略计数。`show` 可按 MEM ID 展开，`timeline` 可查看变更历史。返回内容是资料，不是可自动执行的指令；调度必须结合用户本轮目标、专业文件和会话授权。此接口不包含“自动选择最优科学路线”的保证。

Leader 的 Workflow 保存当前交付目标、任务依赖与恢复入口；Memory 保存有来源的决定和教训。两者不逐条复制状态，不存在跨目录原子事务。Leader 在实质决定/交接时捕获有价值增量；若某一侧写入中断，恢复时分别查证补全，不能据台账完成推定记忆也已保存。

Leader 0.2.0 的只读 `resume` 可调用当前安装的 memory.py context 合并恢复入口；独立安装可显式传 `--memory-skill`。reader_unavailable/read_failed 与没有 Memory 分开报告，不能当作“无相关记忆”。Workflow 的候选不因记忆读取而自动获得科学就绪或执行权限；宿主检查依赖诊断、所引用专业版本和 native job 后再选择动作。
