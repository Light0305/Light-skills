# 文件契约与辅助工具

Python 3.10+，仅标准库；本轮在 Windows/Python 3.11 验证。工具不联网、不调用模型、不运行实验、不修改上游、不自动作科研决定。它接受本地明确输入，不解析来自数据的命令。

## 输入登记与冻结

从任意目录使用技能绝对路径；示例路径和 ID 要替换为实际值：

```powershell
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" ingest --execution "<project>/Experiment/EXP-0001_执行批次" --input "<project>/Experiment/EXP-0001_执行批次/runs/R001/outputs/raw.csv" --out "<project>/Analysis/AN-0001_分析问题"
```

`--execution` 可重复，逐批次分配 `EX01/EX02/...` 命名空间；**不自动合并科学结果**。`--input` 可重复，登记实际要分析的原始值、日志、外部索引/协议或既有分析文件。无 light-experiment 时只给 `--input` 即可。不要把含大量未读取文件的目录当成“已分析输入”。

原生导入读取 campaign、冻结 design/context/plan/适用协议、events、已建 spec 的 runs、result/manifest 和 assessments；保存本轮读取的小型元数据快照，逐文件上限 16 MiB。超大元数据可作显式原始输入引用，不复制到快照层。运行的完整 outputs、日志、checkpoint **不会自动导入或重哈希**；以 `--input` 明确登记所需文件。上游清单是材料，不是本轮已重新验证所有产物的证明。

本版对存在的原生 manifest，复核所列 run 元数据与显式选择的 outputs/logs 的大小、哈希及封存归属；不遍历重哈希未选择的原始大文件或代码快照。QC receipt 检查内容哈希、run 归属、supersedes 链和已记录事件，拒绝删除最新判定后回退旧通过。旧的无哈希摘录或缺失 seal 仍可接入为诊断材料，保留警告，不能因此获得正式运行验收。需要全运行检查时另用可用的 experiment.py verify，并读实际范围与结果。

每个实际登记文件包含 `input_id / path / role / bytes / sha256 / snapshot`。元数据有原样小快照；显式分析输入默认只做流式 SHA-256，不复制大型数据。哈希有 I/O 成本，云存储/多 TB 数据可先用项目原有不可变 manifest/version 导出需要的派生视图，并记录未全量核对范围；本工具不伪造远端验证。

选中的原生 outputs/logs 另带 `run_ref / sealed`，用于把原始值或登记派生物的 input_ids 接回运行；配置文件不能代替这条数值证据链。runs 索引另保留 claim_refs、depends_on_runs、seal_status、assessment_verified、接入 receipt 指纹和终止状态。`selected_files_only` 仅指所列文件子集，绝不是完整运行已验证。

`context.json` 保存 executions 的身份、主张、实验、run 索引与 selected inputs；`receipt.json` 固定 context 指纹和新 analysis_id。`analysis.json`、`analysis-plan.json` 从模板创建草稿，科学内容由宿主填写。输出必须新建或为空，和输入/执行/技能目录分离。拒绝已发现的符号链接/junction/路径逃逸，不递归复制原始数据。

模板源文件是 [analysis.example.json](../templates/analysis.example.json) 和 [analysis-plan.example.json](../templates/analysis-plan.example.json)；工作区的 `analysis.json`、`analysis-plan.json` 由 `ingest` 创建，不是技能模板目录里的原文件名。

`runs[]` 不是完整计划矩阵。planned-but-no-spec、设计的样本目标、仍运行的 PID/任务真状态需要宿主结合冻结设计/调度器核对；`running_or_interrupted` 明确表示无法从静态记录区分。

## 分析计划

填 `analysis-plan.json`：

- `timing`：`inherited / prospective / retrospective / unknown`；`timing_basis / result_access` 写原计划出处、版本、结果接触事实与未知；
- `question / estimand / independent_unit / comparison / data_scope`：具体问题、目标量、单位、对比和推断范围；
- `analysis_method / uncertainty / missing_and_exclusions / multiplicity / decision_thresholds`：真实方法和假设；不适用可用明确理由，不能空置或编造；
- `sensitivity_branches[]`：会改变决定的合理分支及依据；不需要时空数组。

```powershell
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" freeze-plan --workspace "<analysis-workspace>"
```

生成 `plan-lock.json`，拒绝覆盖。即使是回顾性分析也能冻结当前规格；这不证明首次结果接触时间、不等于预注册、不升级确认地位。冻结后更改规格时在新分析目录登记前轮及偏离，不修改旧 lock 消除漂移。轻量任务不必用工具和完整锁定流程。

## 分析结果与发现

`analysis.json` 顶层：`schema_version="1.0" / analysis_id / round / parent_analysis_id / status / data_kind / findings / exclusions / deviations / history / loop_decision`。

`status=draft / complete` 只表示分析交付状态；不表示研究主张成功。`data_kind` 为 `measured / simulation / synthetic_validation / illustrative / mixed / unknown`。仿真科学问题的真实计算记录用 simulation；测试工具的合成已知答案用 synthetic_validation；混合需逐发现说明来源与适用范围。

发现最小示意（不是实验观测，不要原样作完成结果）：

```json
{
  "finding_id":"F01",
  "claim_refs":["EX01/C01"],
  "run_refs":["EX01/R001"],
  "mode":"exploratory",
  "validity":"unknown",
  "validity_basis":"写实际质检和可比性依据，未知就说明缺什么",
  "outcome":"inconclusive",
  "statement":"写数据支持的有限判断及原因",
  "evidence":[{"input_id":"实际 S 编号","locator":"CSV 行/键/数组索引；统计结论另引实际派生物"}],
  "estimates":[],
  "limitations":["写真实限制"]
}
```

- `finding_id` 和 artifact ID：1–64 字符，字母/数字开头，其后字母数字、`_`、`-`。
- `claim_refs / run_refs` 指实际导入对象，standalone 时可空。外部 job/run ID 在显式导入的材料与 evidence locator 保留，不伪造原生 EX 身份。
- `mode=confirmatory / exploratory / descriptive`；回顾性或未知计划不能把发现标成 confirmatory。继承/前瞻 timing 的真实性由宿主核对，脚本不认证其声明。
- `validity=usable / compromised / unknown`，`outcome=support / falsify / inconclusive / not_evaluated`。支持/反驳需要可用证据及已知数据类型；具体数值/机制是否支持仍需人工科学复核。
- 每个 `evidence` 用一个已知 `input_id` 或 `artifact_id` 加具体 `locator`；程序不核验 locator 指向的数值或语义。
- 两个引用字段不能同时出现；使用原生 run_refs 时，claim_refs 要属于所引实验。支持/反驳需为每个所引 run 明确登记原始 outputs/logs，或经 artifact.input_ids 连回这些文件；只引用 campaign/spec 不够。无原生执行的外部数据照常按真实 input_id 分析。
- 可选的 `estimates[]`：`name / value / unit / n_independent / n_observations / interval`。数值有限或 null；N 正整数或未知 null。`interval` 可为 null，否则包含 `level / lower / upper / type / method / uncertainty_scope`；理论/确定性结论不强填统计区间。
- 正式支持/反驳的成功原生运行需要封存子集一致、可验证的通过 QC、无已知输入漂移或未确认终止；递归核对前置运行。verify 也检查仍可访问的当前 QC：撤销/损坏报错，仍通过但换了 receipt 提醒复核；来源不可访问时明确警告仅保留旧快照，不能声称当前 QC 已复查。
- `failure_outcome_basis` 仅允许已结束的 failed/timed_out，且无输入漂移或已知未终止，按既定任务定义和实际原始证据解释任务结局；不豁免成功运行 QC 失败、仍运行或输入污染。脚本不认证该论证。旧记录缺 termination_confirmed 时仍需宿主核对，不将字段缺失解释为已确认终止。
- 建议补充 `alternatives / next_test / scope / estimate comparison/sample_definition` 等真实科学细节，按需要组织，不强填无意义字段。
- `exclusions / deviations / history` 记录实际对象、理由、结果接触和影响；计数、分母、排除与文章/图表一致性由宿主核对。

## 派生物登记

实际分析代码放 `code/`；输出放 `derived/` 或 `figures/`。宿主先真实执行并检查，再登记：

```powershell
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" register-artifact --workspace "<analysis-workspace>" --artifact-id T01 --file "derived/effect.json" --input-id S0012 --code "code/analyze.py" --command "填写实际已执行的命令" --environment "填写实际环境或锁文件、版本记录"
```

`--input-id`、`--code` 可重复。登记输出和所列代码的大小/哈希、输入 IDs、命令和环境，排他创建 `artifacts/T01.json`。它**不执行或证明命令曾执行**；也不发现隐式 import、未登记输入或所有代码依赖。登记后改代码/输出会被 verify 报告；修订保留旧版并另建分析版本。

配对效应可选工具：

```powershell
python -X utf8 "<skill-root>/scripts/paired_effect.py" --input "<derived-pairs.csv>" --out "<analysis-workspace>/derived/paired-effect.json" --direction higher --unit-definition "填写真正独立且完整配对的单位" --uncertainty-scope "填写该重采样实际覆盖的变异" --data-kind measured --resamples 10000 --seed 0
```

输入 header 必须为 `unit_id,a,b`，每个单位仅一行、两列均为有限值。工具不静默丢缺失对，不接受重复 ID/非有限数，不覆盖已有输出；按单位 ID 排序后重采，行序不影响随机结果。输出均值改善、差值 SD、percentile bootstrap 区间、输入哈希与解释限制。`higher` 时改善为 a−b，`lower` 时为 b−a；真实尺度/量纲在分析中保留。

这不是默认分析器。采样、配对、层级和目标量不满足要求时，用项目现有科学库实现恰当模型。percentile 方法只是透明、无依赖的有限实现，并非所有情况下最优；B=10000 和 seed=0 是可配置计算设置，不是科学门槛。

## 研究决定、验证与反馈

`loop_decision` 包含 `route / finding_ids / reason / target_question / next_action / predictions / budget / stop_rule / reentry_condition / execution_authorization`。route 为 `stay / light-experiment / light-design / light-idea / light-journal-select / light-chart / light-write / stop / hold`。

`predictions[]` 记录 `{result, decision}` 的真实映射；研究动作需要此项，停止/暂缓/选刊/仅绘图写作可为空。`budget.status=bounded / unknown / not_applicable`，都有 basis；bounded 另需真实 limit。未知预算不会阻止完成分析与交接，但不授权新运行。

```powershell
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" verify --workspace "<analysis-workspace>"
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" export-handoff --workspace "<analysis-workspace>"
```

verify 检查：登记输入/快照/派生物/代码一致性，父轮、计划冻结、主张/运行/发现引用、部分数值字段及完成状态的最低交付。草稿可以 ok=true 并带警告。元数据原件变化但快照未变会警告；未复制的原始分析输入变化报错。完成状态需要非空报告和有依据的循环决定；不强制图数或 p 值。

export 仅对结构检查通过且 complete 的分析生成 `handoff.json`，保留原身份、触发发现、循环决定、数据类型、历史、analysis 指纹与警告；不覆盖。之后修改 analysis 会使 handoff 过期。它是相邻技能的修订 brief，**不是已实现的 idea/design ingest API**。下游操作见 [pipeline-loop.md](pipeline-loop.md)。

新 handoff 另以 `sources[]` 绑定 context、receipt、analysis、计划/lock、报告及全部 artifact 登记文件的相对路径、大小与哈希；输出和代码本身由 artifact 记录继续核对。改报告、改命令/来源登记、新增或删去登记也会使交接过期。旧 handoff 缺 sources 时保留兼容警告，不改写旧导出补认证。实质更正保留原包并创建新 AN/parent，由宿主处理下游影响。

新一轮：

```powershell
python -X utf8 "<skill-root>/scripts/analysis_bridge.py" ingest --execution "<new-execution-workspace>" --input "<new-evidence-file>" --parent "<previous-analysis>/analysis.json" --out "<new-analysis-workspace>"
```

保留前轮 analysis 快照、ID、round 与原决定；新轮自动 round+1。历史中的研究假说、版本、成本和已排除解释仍由宿主完整维护。

退出码：0 当前动作成功/结构无错误；verify 的 1 为检测到错误；2 为输入/前置/命令错误。哈希与本地锁均不是防篡改认证或可信时间。脚本不会证明实验真实性、科学有效性、统计覆盖、完整依赖、数值/图表正确或路由合理。
