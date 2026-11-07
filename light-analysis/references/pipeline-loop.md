# 接收结果与研究闭环

## 定位真实研究材料

能力链是 `light-literature → light-idea → light-design → light-experiment → light-analysis`，并允许从分析返回任何真正需要修订的层次。它不是必须安装全部技能的依赖链。

相关源码从当前安装位置定位；研究产物从真实项目的 Experiment、Design、Idea 或明确指定的旧目录读取。不能分析源码目录里的测试/示例并称作用户结果。

light-experiment 的当前原生接口：

| 输入 | 用途与限制 |
|---|---|
| `campaign.json` | 保留 campaign、design/version、selection 的 idea ID/版本、execution_scope 与预算 |
| `upstream.json`、`inputs/design/context.json`、`design.json`、`plan.md` 和适用协议 | 批次实际使用的冻结设计；原计划中的 claims、experiments、tasks、analysis、decisions 仍需阅读 |
| `runs/<id>/spec.json` | experiment/task、kind、unit、parameters、父尝试与依赖；kind=smoke/diagnostic 不能混入主比较 |
| `result.json`、`manifest.json`、原始 logs/outputs | 实际状态、返回码、输出质检、漂移与封存清单；有清单不代表本轮已重新计算哈希 |
| `assessments/*.json` | 当前 receipt 包含 `assessment` 内层对象及 `supersedes`；保留旧判定与修订链，不只抽一个 outcome |
| `events/*.json`、`execution-report.md` | 修复、偏离、事后补记、运行缺口、成本与交接；缺文件保留未知 |

原生 `experiment.py verify` 只能只读检查；若调用，记录真实返回和检查范围，失败后按受影响文件处理。不把它的 `ok=true` 当科学验收。分析 intake 自己只对所列元数据、选中的原始文件和 QC 修订链做有范围的复核，不代替完整 archive 检查。外部 MLflow/DVC/Slurm 或普通 CSV 保留原 ID，用明确输入文件导入；不要伪造原生 result/process 文件。

源文件哈希不符或判定链损坏时，先查清版本/更正，不用当前文件重新登记一个哈希来掩盖原记录差异。QC 是可更正的判断：前置运行 QC 撤销时，递归复核依赖结论，保留原运行/分析/报告；重试不是新增独立单位。仍通过但 receipt 改变要阅读更正理由，不因两个 passed 字样相同就自动采用新版本。

多个 campaign 可能来自同一设计，也可能更换代码/数据/预算。分析工具逐批次保留身份；是否合并由科学可比性决定。相同 seed 数字不自动意味着配对：需确认相同单位、共享外生随机性/数据以及对应关系；不同方法随机调用顺序可破坏 common random numbers 的语义。

## 研究反馈的最小对象

每个实际分析保留一个唯一 `analysis_id`；每轮交接包括：

- `round`、`parent_analysis_id`（首轮为 null）、`history`：本轮改变、已见结果、已否定解释和投入；
- 原 idea、design、campaign、experiment/task/run 身份及版本，不能用新版本覆盖历史；
- `finding_ids`：触发该决定的具体发现与原始/派生证据链；
- `route`、`reason`、`target_question`：去哪里、为何该层次是原因、要消除什么不确定性；
- `next_action`、`predictions`：最小可交付动作，以及不同结果会如何改变判断；
- `budget`、`stop_rule`、`reentry_condition`：本轮上限及依据、停止、重启条件；
- `execution_authorization`：现有授权的实际范围；分析建议本身不增加授权。

预算可以是有依据的运行数/时间/设备/费用上限，也可以 `status=unknown` 并明确必须补什么。不要将未知填成 0，也不要把 `max_iterations=3` 之类示例变成所有课题规则。研究完整性本身需要停止条件；成功不等于必须继续扩大主张。

## 路由的因果层次

1. **分析错**：修正清洗/聚合/推断，保留原结果和变更原因，先不用重跑。
2. **执行错**：已有设计可回答问题但实现、输入或运行失效，返回 light-experiment。提供最小复现、故障定位、验收与受影响运行。修复评价器后所有受影响方法应公平重算/重跑。
3. **设计错或信息不足**：处理与批次完全重合、测量无效、缺必要对照、簇数不足、区间太宽、事后发现需确认，返回 light-design。额外种子未必解决任务分布不确定性，额外读数未必解决簇数不足。
4. **研究前提受挑战**：有效、足够精度的结果排除核心预测，或者证据表明真正贡献已与想象不同，返回 light-idea。重新定义问题/机制、补领域文献差异核查，不能给旧 idea 换个标题就继续投入。
5. **证据足够**：将已验证结论与限制交给绘图/写作；若问题已回答，可直接停止并归档有效阴性。

一轮可以有多个后续动作，但给出一个当前主路由和顺序依赖。例如“先修评价器，再决定设计是否不足”，不能同时把错误指标当成 idea 已证伪的依据。没有关键反事实依据时表述为诊断假说，而非确定原因。

## 三种接回方式

### 返回 light-experiment

交 `handoff.json`、故障/缺口、原设计身份、需修复的实现和现有验收范围。使用新 run ID 记录尝试与父运行；不新增独立 N，不抹去失败成本。修复已超出当前设计的输入/评价/研究目标时，先转 light-design。

### 返回 light-design

当前 `design_bridge.py ingest` 只接受 idea 工作区，**不原生接受本分析的 feedback JSON**。真实衔接方式是把 handoff 作为修订 brief，读取原 `context.json/design.json/plan.md`，在新的版本目录建立修订设计；更新 version/history/受影响实验和执行范围，保留原始 selection，除非 idea 本身已改变。再按该技能执行校验。不能把导出的 handoff 改名 design.json 并宣称已接入。

看过结果再改的阈值或模型是修订/探索性；确认部分用新的独立数据/单位或经论证的有效序贯设计。已污染的保留集留作开发材料，不能因复制到新目录恢复独立性。

### 返回 light-idea

当前 `idea_bridge.py ingest` 接 literature/run，不接受本 handoff。把反馈作为已有 idea 的修订请求，保留原 card、evidence、版本、已排除预测与阴性价值；创建新版本或新候选，说明为什么。改变问题/贡献后按当前范围重新查重；不能沿用旧版本 novelty 认证。

### 交给选刊、绘图与写作

贡献及证据范围已经稳定、需要选刊或重新定位时，用 light-journal-select 接有限贡献、分析版本、主要图表/数据清单、文章类型和作者约束。已有目标或用户直接要起草时可以进 light-write；数值与比较明确后可进 light-chart。handoff 是可阅读的实际材料入口，不宣称这些技能已有通用 ingest API；采用哪个分析、图和稿件版本要写明。选刊与表达优化不能把探索变确认、把未知 QC 变通过。

### 更正与跨会话恢复

重新进入时先对照 Memory 的有关来源与当前原生文件，检查是否已更正、被撤回或换了分析版本。结果/单位/代码/解释发生实质更正时，新建 AN 并引用父分析；列出受影响 finding、图、稿件主张及后续决定。新导出同时绑定报告、计划和派生登记，不能仅改报告而保留旧交接继续用。宿主将实际核对的增量、否定的解释、条件与下一步记回 Memory；有对应 Workflow 任务时更新其真实状态，不新增后台循环。

## 自主推进与终止

已有会话明确授权的范围内，可以直接调用可用相邻技能继续工作；不要每步索要确认。只有分析授权时，完整交接和下一步建议就是本轮完成，不能偷跑昂贵实验。目标技能不可用时，交付其所需具体材料，不编造自动 API。

重复得到相同无区分力的结果时，检查是不是已否定解释在被重新提出、信息来源没有增加或设计从未改变。记录边际信息价值为何足以继续；否则停止/暂缓。报告“本轮分析完成”与“科学问题已解决”是两个不同状态。
