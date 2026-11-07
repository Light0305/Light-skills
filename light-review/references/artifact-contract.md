# 文件交付与离线工具契约

普通局部评审直接在对话交付即可。完整或多轮任务建议在论文项目内建立独立目录，例如 `Review/REV-0001_稿件版本与轮次/`，放报告和结构化记录。不要把研究文件存到技能安装目录。

## 推荐产物

- `review.md`：依据 [模板](../assets/report-template.md) 形成可读报告，包括结论、优点、承重主张、问题、最小修复、覆盖与局限。模板可按请求压缩。
- `review.json`：需要跨轮追踪时保存的问题与检查记录，起点见 [review-record.template.json](../assets/review-record.template.json)。人读报告和 JSON 内容应一致；不要生成两个互相矛盾的结论。
- `packet/packet.json` 和 `packet/materials/`：可选的材料版本副本。冻结仅复制显式指定的文件，不递归收集项目，不读取凭据、不联网。

冻结不会阅读或评审内容，不会证明材料是最终版，也不是加密或只读存储。工具通过 SHA-256 检测冻结副本变化；原稿后续变化不改变旧包。它不包含完整环境或运行产物，不能被称为计算复现。

## 工具用法

Python 3.10+，标准库，无模型/API 依赖。下列 `<skill>` 与 `<paper>` 是实际目录的占位路径，执行前替换；Windows 用引号保护空格。

```text
python "<skill>/scripts/review_packet.py" freeze --out "<project>/Review/REV-0001_稿件版本与轮次/packet" --file "manuscript=<paper>/paper.pdf" --file "figure=<paper>/figures/fig1.png" --file "supplement=<paper>/supplement.pdf"
python "<skill>/scripts/review_packet.py" verify --packet "<project>/Review/REV-0001_稿件版本与轮次/packet"
python "<skill>/scripts/review_packet.py" validate --packet "<project>/Review/REV-0001_稿件版本与轮次/packet" --record "<project>/Review/REV-0001_稿件版本与轮次/review.json"
python "<skill>/scripts/review_packet.py" validate --packet "<project>/Review/REV-0002_修订复核/packet" --record "<project>/Review/REV-0002_修订复核/review.json" --previous-packet "<project>/Review/REV-0001_稿件版本与轮次/packet" --previous-record "<project>/Review/REV-0001_稿件版本与轮次/review.json"
```

`freeze` 要求输出目录不存在，输入均为显式普通文件。失败后保留 `.incomplete` 标记及已复制部分，不将其当作可用 packet；换新输出目录重试即可。它生成 `review.stub.json`，将其复制到评审目录作为 `review.json` 后填写；stub 的所有阅读/检查状态均未完成，空问题列表不代表没有问题。

role 可为 `manuscript`、`figure`、`supplement`、`data`、`code`、`context`、`reference`、`render`、`venue`。图在 PDF 内时不必另外导出才能列为材料，但必须真正检查相应页面。文件无需全齐，材料不齐在报告中声明。

`verify` 核对 packet ID、材料路径、字节数和哈希。`validate` 先 verify，再执行下面的记录约束。退出码 0 为结构/版本检查通过，2 为参数、读取、版本或记录不一致。成功输出明确说明不是科学内容验证。工具不验证自然语言锚点是否准确、文献是否支持主张、检查是否真的发生，不能替代宿主的事实核验。

## JSON 记录（1.1；兼容 1.0）

这是一份具体记录格式，校验器实现下列约束，不宣称是通用 JSON Schema 引擎。

| 字段 | 含义与约束 |
|---|---|
| `schema_version` | 新记录为 `1.1`；历史 `1.0` 仍可核对，packet 自身格式保持 `1.0` |
| `packet_id` | 对应冻结版本 |
| `previous_review` | 首轮为 null；1.1 的 recheck 必须绑定直接前轮的 `packet_id` 和报告实际字节的 `record_sha256` |
| `review_status` | `draft` / `final`；stub 永远初始为 draft |
| `scope` | `full` / `focused` / `recheck` |
| `assessment_complete` | 是否具备完整科学评估范围；focused 不可 true；与实际阅读覆盖一致 |
| `summary`, `strengths`, `limitations` | 非空摘要字符串；后两项为字符串数组，没有优点/局限可以是空数组但不得捏造 |
| `coverage` | packet 每个 material_id 恰好一条，含 `status` 与 `notes` |
| `checks` | 每个 check 恰好一条，说明实际结果及 evidence |
| `claims` | 承重主张及评估；ID 唯一，定位并链接材料证据 |
| `issues` | 稳定 ID、证据和修复/关闭任务 |
| `sources` | 外部来源；区分全文、仅元数据与不可访问 |
| `readiness` | scientific / submission 及 rationale，不能由空问题列表自动赋 ready |

coverage status：`inspected`、`partial`、`unreadable`、`not_read`、`not_applicable`。notes 说明查看范围、局限或不适用原因。assessment_complete=true 时不得有核心 manuscript/figure/supplement/render 材料未 inspected；这仍依赖宿主的真实声明。未被作者提供的图表/附录须在 limitations 和对应 checks 中记录，脚本不能从文件列表猜出遗漏。

checks 的 check 固定为 `claims`、`methods`、`statistics`、`figures`、`numerical`、`literature`、`reproducibility`、`ethics`、`venue`。每条 status 为 `passed`、`issue`、`not_assessable`、`not_applicable`；passed/issue 需要材料 evidence。若不需要某项则说明原因，不为满足结构虚构检查。理论稿 statistics 可以 not_applicable；未检查图时 figures 不可 passed。

材料指针统一为 `{"material_id":"M001","anchor":"PDF p.3, Results, paragraph 2"}`；anchor 必须真实可定位，不伪造行号。来源 source_id 与主张 claim_id 单独引用，不以网页伪装材料指针。

检查、主张、问题、改判及关闭的 evidence 必须引用 coverage 为 inspected 或 partial 的材料，不能拿 not_read/unreadable/not_applicable 的内容宣称发现或核实。partial 只支持真正查过的锚点，范围由评审者说明；完整评估仍要求核心材料 inspected。主张作出可评估判断时也须实际读过其 location；无法读出原图内容时，可以在 coverage/limitations 报告读取失败，以实际读过的错误记录等支持有关问题，不猜图中具体缺陷。location 是定位线索，不能单独替代证据。

claim 至少含 id、text、central（布尔）、location、evidence、assessment。assessment 为 `supported`、`limited`、`unsupported`、`contradicted`、`not_assessable`。supported/limited/contradicted 必须有 evidence；无法支持可列空 evidence 并通过问题/局限说明。

issue 必需字段：id、severity、category、basis、evidence_status、confidence、blocking、required、status、claim_ids、location、evidence、source_ids、observation、impact、suggested_fix、closure_test、owner、resolution_evidence。枚举见模板和脚本。

- critical 必须 required 和 blocking；major 必须 required；minor 不可 blocking。blocking 必须 required。required=true 的 deferred 仍算待解决。
- `confirmed`/`reporting_gap`/`unresolved` 与 `high`/`medium`/`low` 独立记录；不要用低 confidence 掩盖无事实依据的批评。
- `basis` 为 review/audit/venue。`category` 为 claim/methods/statistics/figure/numerical/novelty/citation/reproducibility/ethics/submission/presentation。
- evidence 至少一处。reporting_gap 的证据指向实际查过的相关段落/范围；unresolved 定位疑点，不是凭空猜测。
- verified/dismissed 必须有新核验的 resolution_evidence；dismissed 另有非空 `dismissal_reason`。
- 新版 1.1 的关闭问题还需 `closure_check`：本轮 `packet_id`、`method`（rechecked / unchanged_evidence）和非空 notes，描述关闭检验实际结果。旧版 1.0 没有该字段，不回填虚构历史核验。
- owner 支持 light-write / light-chart / light-diagram / light-anaysis / light-design / light-experiment / light-journal-select / author / specialist；旧 figure-workflow 兼容。详见 [实际交接](handoff-and-recheck.md)。

以下是**合成示例**，展示 issues 数组内一条记录的形状，不是已检查任何真实论文的声明。使用时替换为本轮真实材料指针和事实；不要把示例粘贴进真实报告充当发现。

```json
{
  "id": "LR-001",
  "severity": "major",
  "category": "claim",
  "basis": "audit",
  "evidence_status": "confirmed",
  "confidence": "high",
  "blocking": true,
  "required": true,
  "status": "open",
  "claim_ids": ["C1"],
  "location": {"material_id": "M001", "anchor": "Abstract, second sentence"},
  "evidence": [{"material_id": "M001", "anchor": "Table 1, site Z"}],
  "source_ids": [],
  "observation": "摘要称每站点均更好，表中Z站点的A=0.53低于B=0.55，且越高越好。",
  "impact": "全站点优越性主张与表中结果直接矛盾。",
  "suggested_fix": "确认结果来源；若表值正确，改为有边界的平均表现陈述并同步关联位置。",
  "closure_test": "复读新摘要、结果、结论和表，确认不再出现不成立的全站点主张。",
  "owner": "light-write",
  "resolution_evidence": []
}
```

ready 的机械条件：该维度不存在未关闭的 required 问题（open/addressed/deferred 均未关闭），适用 checks 全为 passed/not_applicable。scientific ready 还要求 assessment_complete=true、核心材料完整检查；submission ready 要求 venue passed、final 记录。critical 阻塞所属维度；category=submission 仅影响 submission，其他类别影响 scientific。所有阻塞都会同时阻止 submission ready，但科学缺陷不自动证明投稿文件/venue规则有错：未选venue时可为 scientific=hold、submission=not_assessable。科学 hold 时不得称 submission ready，即使技术文件齐全，可在 rationale 描述其技术准备情况。

局部评审已发现阻塞问题时，也可对**当前范围**给 hold，并说明全文未评估；不要把已知阻塞隐藏在笼统的 not_assessable 中。可选 minor 建议不必把已经完成的检查记成 issue：明确其不是必需修订，保留 passed 及建议说明即可。

submission not_requested 不要求 venue 核查；not_assessable 可以报告已做部分检查。ready 只允许在 final 中。上述检查防止自相矛盾，**不证明就绪判断正确**。

## 直接前轮绑定与关闭留存

需要跨轮机械核对时使用 1.1，将实际直接前轮写进 `previous_review`，同时向 validate 提供成对的 `--previous-packet`、`--previous-record`。有绑定而未提供前轮文件会失败；只有一个参数也失败。前轮 packet 先核对冻结文件，报告检查其结构/版本和实际字节 SHA-256，再检查本轮转换；前轮报告可以是 1.0 或 1.1。工具只比较这个直接前轮，不自动遍历或认证更早的链，也无法发现没有声明的其他报告。

以下片段仅说明字段形状；占位摘要必须换成真实值：

```json
{
  "schema_version": "1.1",
  "previous_review": {
    "packet_id": "sha256:<直接前轮真实packet摘要>",
    "record_sha256": "<直接前轮review.json真实64位小写SHA-256>"
  }
}
```

新旧 packet 可以内容相同：packet_id 表示已列材料的内容身份，不是轮次编号。报告、判断或检查范围可以在同样材料上发展；轮次目录和前轮报告字节用于区分记录，不为了让 ID 不同人为改文件。

连续性约束：

1. **旧问题全部留存。** 包括已关闭、可选和延期问题；不以新目录重置编号，也不靠删旧必需问题获得 ready。合并时保留旧 ID、映射和有依据的关闭状态。新问题的数字编号高于直接前轮已分配的最大值。
2. **改判有据可查。** severity/category/basis/blocking/required/observation/impact/closure_test 任一改变，需要 issue 内 `reassessment={"reason":"实际原因","evidence":[本轮材料指针]}`。这允许纠正旧判断，不把降级一律视为错误；脚本不证明所给理由充分或问题语义确实未偷换。
3. **关闭绑定本轮。** rechecked 表示实际检验了修改和关联位置；复制旧 packet_id 的 closure_check 无效。结论与证据仍由评审者核实，脚本不会分析论文来判断检验是否满足。
4. **继承仅限未变证据。** unchanged_evidence 只能继承前轮同状态的 verified/dismissed；问题定义不能同时改判。工具比较问题 location、evidence 和 resolution_evidence 的角色、字节哈希、大小与锚点，不靠同名文件或相同 M001 编号判断。notes 还要说明研究适用性/依赖未变；未列依赖及科学适用性由人复核。改变内容、关闭方式、排除理由或有关范围时使用 rechecked；不能继承未关闭问题。
5. **可以重新打开。** 新证据挑战已关闭问题时保留 ID，恢复 open/addressed/deferred 并说明来源，重新决定当前风险；不是锁死一次关闭结论。

关闭片段（合成形状，不是已完成检查）：

```json
{
  "status": "verified",
  "resolution_evidence": [{"material_id": "M001", "anchor": "当前摘要、结果和结论"}],
  "closure_check": {
    "packet_id": "sha256:<本轮真实packet摘要>",
    "method": "rechecked",
    "notes": "实际重读的范围、关闭检验结果与仍保留的限制。"
  }
}
```

CLI 成功输出 `lineage=immediate_parent_checked` 表示上述直接前轮机械比较通过；单轮为 not_checked。历史 1.0 未绑定 recheck 可正常读，但额外 warning 明确未核对问题连续性和关闭继承；不能据此声称跨轮验证成功。历史记录不静默升级，JSON 重复键会报错而不是让后一个值覆盖前一个。

工具始终不能验证锚点真实含义、视觉检查、领域判断、独立性或科学就绪。直接调用 Python 的 validate_record 只检查单记录；跨轮需另调用 validate_transition，CLI 已组合这两步。原稿修改不会破坏旧冻结副本；要审当前采用版必须另确认它，不能用旧包 verify 成功来证明新稿未变。
