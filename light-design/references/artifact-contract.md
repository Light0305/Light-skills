# 结构化计划与检查边界

只有完整项目交付才需要这些文件；短讨论可以直接表达同样的判断。JSON 模板是空白结构，不是已完成研究。

## context.json：不可静默改写的输入

`schema_version="1.0"`，`mode="light-idea"`；保存所选 `idea` 原对象、`constraints`、它明确引用的 `evidence / papers`、相关 `novelty_log`、决定/card 的文本索引及 `input_files[]`。

每个输入指纹包含绝对 `path / bytes / sha256`。0.2.0 导入还跟随所选证据的 source_file/source_sha256 及选中论文已声明的 PDF 身份；verify 持续核对这些直接来源。不会递归扫描整个文献库。保留 warnings；上游推荐和证据标记不代表本轮重新核实。

没有上游目录时可由宿主建立：

```json
{"schema_version":"1.0","mode":"standalone","idea":{"idea_id":"I_local","version":1,"question":"用户实际提出的问题"},"evidence":[],"papers":[],"input_files":[],"warnings":["独立 brief，未经过 light-idea 查重"]}
```

这是身份与来源容器，不自动认证选题。用户提供的真实输入如需冻结，可同样在 `input_files` 记录指纹。

## design.json：字段

顶层 `schema_version / design_id / version / selection / status / objective / constraints / claims / sources / evidence / resources / gates / experiments / tasks / execution_scope / budget / review / history`。ID 使用 1–64 个字母、数字、下划线或连字符，以字母或数字开头。`version / idea_version` 是正整数。`selection` 的 idea ID/版本必须与冻结输入一致。

状态是 `draft / needs_input / hold / ready_for_pilot / ready_for_execution`。脚本不自动推进状态。

### 主张和证据

```json
{"claim_id":"C01","statement":"有边界的目标结论","prediction":"核心假设的可区分预测","rival":"最强替代解释及其预测","scope":"适用对象、条件与范围","evidence_ids":["E01"]}
```

`evidence_ids` 可引用 `context.evidence` 或本轮 `design.evidence`；两处 ID 不能冲突。新假说不要求已有证据证明其成立。已有事实、方法选择与设计者假设应在文字中区分，不能为了填引用而制造证据。

本轮来源：`source_id / title / url 或 path`，建议附真实 DOI、版本/日期。本地 path 配 sha256 保存核对过的字节；相对路径在设计工作区内，外部来源用绝对路径。新证据：`evidence_id / source_id / statement / locator / access_level / verified`。`access_level` 为 `metadata / abstract / full_text`，`verified` 为布尔值，表示实际核对了表述与锚点，不表示独立复现实验。当前就绪范围使用的 verified 本地证据要求非空、匹配的来源与哈希，未来未使用来源可保留待补提示。

### 资源与门槛

资源：`resource_id / name / status`，状态 `available / unknown / unavailable`；执行范围内还要有 `specification / locator / basis`。分别表示具体版本/量程/规格、可定位的来源或位置、可用性核实依据。官方链接存在不等于数据权限已开通。

门槛：`gate_id / description / status / basis`，状态 `confirmed / unknown / blocked / not_applicable`。已确认或不适用都需说明理由。实验用 `gate_ids` 引用其真实前置条件；只列适用条件，不给所有课题增加审批清单。

### 实验

基本字段：`experiment_id / name / stage / claim_ids / resource_ids / gate_ids / sample_size`；非空字符串数组使用真实的 ID。

`stage` 是 `pilot / exploratory / confirmatory`。计划就绪的实验还需：

```json
{
  "purpose":"这项实验会改变哪一个决定",
  "design":"设计类型、比较与识别限制",
  "units":{"allocation":"分配层级；不适用时写理由","independent":"独立重复","observation":"观测及嵌套结构"},
  "conditions":["具体条件/对照，理论或定性研究使用相应设置"],
  "allocation":"实际随机化、配对、平衡或案例选择；不适用要解释",
  "procedure":"具体步骤或真实协议位置；未实现的入口须列为任务",
  "measurement":{"primary":"主要终点/证据","operationalization":"定义、单位、聚合","timepoint":"采集或验收时点","qc":"质量门槛与技术失败"},
  "sample_size":{"n":null,"n_definition":"总独立单位数、每组数或其他明确含义","method":"论证方法","basis":"真实依据、计算位置及不确定性","status":"pending"},
  "analysis":"估计量/主要比较、模型或证明/解释步骤及不确定性",
  "decisions":{"support":"支持哪条有限结论以及下一步","falsify":"反驳/排除什么以及下一步","inconclusive":"何种不可判定及补充信息","stop":"继续/修订/停止与最大投入"}
}
```

数量型 `sample_size.n` 为正整数或暂未确定的 `null`。`status=justified` 时必须有正整数 N 和解释；`pending` 阻断对应实验就绪。理论/某些定性研究可用 `not_applicable`、`n=null`，同时解释信息充分性或验收依据；它不是绕过定量样本论证的按钮。多组、层级和不平衡设计在 `n_definition / basis` 与协议中保存完整分配，不能用一个总 N 代替设计。

### 任务、预算和审查

任务：`task_id / experiment_id / depends_on[]`。就绪范围内需要 `inputs[] / action / outputs[] / acceptance / owner / effort`。`action` 可是实际入口或需要实现的具体规格；`effort` 写资源、时长/范围、依据与限额。空依赖用 `[]`，有依赖必须是已存在任务且无环。

预算：`summary / basis / limit`，允许有依据的范围，不强制未知费用变成精确金额。脚本不核算预算和设备容量，宿主应检查总量、单位、复测和日历依赖。

反方审查：`strongest_objection / response / residual_risk`。`history[]` 用对象记录日期、前一版本、变化、理由及是否已接触相关结果；结构检查不认证其中的时间声明。

## 就绪状态的有限含义

`execution_scope` 是本版允许宣布可开始的实验 ID 数组。

- `ready_for_pilot`：非空且全部是 pilot；检查仅对该范围加完整性门槛。其依赖任务所属实验也必须在范围内，后续实验可以仍待确认。
- `ready_for_execution`：覆盖全部计划实验；每条主张都有实验对应。
- 两种就绪状态均检查范围内的实验字段、样本论证状态、资源可用性、门槛、执行任务、预算和反方记录。

新增实验尚未纳入全部就绪范围时，需重新选择状态，不能仍称整个计划可执行。未列出的现实资源、遗漏的门槛、无科学内容的长文本、失真的功效计算或错误的因果识别无法被脚本发现。

## 运行与退出码

```powershell
python "<skill-root>/scripts/design_bridge.py" ingest --ideas "<idea-workspace>" --idea-id I01 --out "<new-design-workspace>"
python "<skill-root>/scripts/design_bridge.py" verify --workspace "<design-workspace>"
```

仅依赖 Python 3.10+ 标准库；本次以 3.11 测试。`ingest` 拒绝覆盖已有三个交付文件，以及与上游重叠的目录；重复上游证据/论文 ID 或已失效的直接来源在写出前处理。就绪交接要求 plan.md 非空，且仍需核对协议、正文和 JSON 的内容一致性。版本修订及执行边界见 [修订与执行交接](revision-and-handoff.md)。

`verify` 返回 `ok / errors / warnings / counts`；无结构错误退出 0，关系/字段/就绪范围/指纹错误退出 1，读取、解析或命令错误退出 2。草稿可通过并附未就绪警告。警告不是“可忽略”：宿主需解释其科学影响。

**此工具不执行实验、不验证 URL/DOI 真实性、不读取被引用正文、不证明证据蕴含、不计算真实功效、不核算成本，也不授予实验权限。** 文件存在或结构通过不能当作科学验收。
