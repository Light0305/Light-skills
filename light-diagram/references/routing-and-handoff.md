# 工具选择和共同交接

## 选择依据

先遵从用户指定工具/目标格式，再根据后续编辑需求决定。未指定时，原生矢量轮廓和层次编辑优先 Illustrator；PPT 内演示和团队修改优先 PowerPoint；带连接节点的流程/系统关系编辑优先 Visio。复杂度或领域名称不能独自决定工具。

使用已连接工具前检查其真实能力；没有匹配插件但桌面应用可用时，子 skill 有相应本机路线。不因存在参考仓库就假定已经安装其 MCP。不同后端的原生模型不可互换：

| 方面 | Illustrator | PowerPoint | Visio |
| --- | --- | --- | --- |
| 关系线 | 原生路径及箭头；无动态吸附 | 原生连接符，当前可分段接透明拐点 | 一维线与节点粘附 |
| 整体编辑 | 图层/原生组，跨组关系另调整 | 图形/文本/组，需按实测确认随动范围 | 图形/连接线，需核查粘附与移动 |
| 当前脚本边界 | 路径/复合孔/渐变/文字；不自动识图 | 原生形状与连接补全；不自动识图 | 原生二维形状/曲线/粘附；不自动识图 |

工具冲突用实际约束处理：用户既要高保真矢量轮廓又要求拖动节点自动跟线时，说明哪个行为是主要交付需求；必要时一个主文件加局部素材或用户已要求的第二格式。不能承诺所有软件同时满足全部行为。

## handoff.json

该文件是同一案例的索引与状态记录，不是新的通用绘图格式。不重复复制数千个坐标；具体科学关系可引用 brief/visual schema/后端场景文件，并说明范围。路径相对 handoff 所在目录，或用绝对本地路径；用于追溯的 URL 放在科学来源说明中。

必填顶层字段：

- 新记录 `schema_version: "1.1"`、稳定 `task_id`、正整数 `revision`；旧 1.0 只读兼容并给出绑定范围警告。
- `input_kind: paper|concept|existing_image`。
- `output_mode: prompt_only|image|editable`。
- `stage: planned|prompt_ready|reference_ready|reconstructing|delivered`。
- `brief`：`visual_claim`、`evidence_boundary`、`source_scope`，可加领域和来源。
- `artifacts`：命名文件引用字典，每项 `{path,sha256}`；可加说明。只记录真实存在的文件，不用空文件占位。
- `generation`：`status: not_run|generated|reused|failed`、`calls_this_run`、`executed_prompt`（artifacts 的键或 null）。只计本次调用；旧图原始生成详情写 lineage，不计为本次调用。新任务另记 `selection: builtin|custom|prompt_only`；密钥不进入交接。
- `reference_review`：`status: not_run|passed|issues_recorded`、`issues` 数组。
- `reconstruction`：`mode: faithful|science_corrected`、`corrections` 数组；每条明确对象/关系、改前改后及理由，可指向现有报告。
- `routing`：`requested_tool`、`selected_tool`（`illustrator|powerpoint|visio` 或 null）、`reason`、`visible_process`。用户未指定则 requested 为 null；指定与选定不一致时不能由验证器代替用户批准更换。
- `checks`：`file`、`native`、`visual`、`science` 各自记录 `{status,scope,evidence,subjects}`。status 是 `not_run|passed|failed|not_applicable`，evidence 为报告等 artifacts 键数组；记录 passed/failed 时 subjects 是实际受检文件的 `{artifact_key: sha256}`，防止换了图却沿用旧检查。

科学来源通过 `science_sources: [{artifact,locator,scope}]` 指向 artifacts 中的原件、实际阅读定位及支持范围。仅用户消息/概念输入可以留空，验证器给警告而不阻断；在 brief 中说明范围。生成 reference 不得充当自己的科学来源。修订可加 `parent: {path,sha256}`，指向同 task 的较早 revision；不递归要求历史来源永远可用，也不能用 parent 代替本版检查。

delivered 的检查至少绑定以下 subjects；science 另绑定所声明的科学原件：

| 交付 | file | native | visual | science |
|---|---|---|---|---|
| prompt_only | prompt | 不适用 | 不适用 | prompt |
| image | reference | 不适用 | reference | reference |
| editable | final_native、scene、preview | final_native、scene | final_native、preview、reference | scene、preview、reference |

例如，检查中的 `"subjects": {"prompt": "<该 prompt 的真实 SHA-256>"}` 说明实际检查对象，`evidence: ["report"]` 说明判断依据存放位置。这里是字段示意，不是可直接交付的记录。换文件需重查受影响判断；改掉所有声明并不能让未做的检查成为事实。

常用 artifacts 键为 `prompt`、`reference`、`scene`、`source_record`、`report`、`native_audit`、`final_native`、`preview`；可以添加其他有意义的键。复杂图的 `relation_spec` 可引用包含已核对科学实体/关键边的场景或 brief。只有路径和哈希，不能替代阅读该文件。

生图前必须先向用户交付实际执行提示词或文件链接，记录 `prompt_delivery: {artifact: "prompt", channel: "inline|file_link", before_call: true}`。发生生成时，此 artifact 与 executed_prompt 的哈希必须相同。新增字段可选以兼容历史案例；凡声明 `generation.selection` 的新生图记录都需要这项交付声明。它不证明 UI 消息真的发出，助手仍须实际完成交付。

若缺少生图能力/配置，或调用失败后只能交付提示词，实际 `output_mode` 记 `prompt_only`；`requested_output_mode: image|editable` 保留用户原始目标，1.1 中两者不同时明确 `requested_output_fulfilled: false`。不得把降级交付说成完成了原生文件；之后拿到图片可从参考核查继续。具体配置见 [生图能力与自定义配置](../light-diagram-prompt/references/image-generation.md)。

## 阶段规则

| 阶段 | 实际所需内容 |
| --- | --- |
| planned | brief、目标与已知偏好；尚未执行项写 not_run，不伪造文件 |
| prompt_ready | 完整 prompt；只要提示词的请求可在此后 delivered |
| reference_ready | 实际选定 reference；已查看并通过或登记了待改问题 |
| reconstructing | reference、选定后端与原因、复现/修正模式；关键修正不留在聊天记忆中 |
| delivered / prompt_only | prompt、提示词质量/科学检查证据；native 可 not_applicable |
| delivered / image | reference、图像检查证据，生图或复用记录真实；native 可 not_applicable |
| delivered / editable | final_native、preview、scene、report；四类检查均有通过证据；应用实测缺失则保留 reconstructing 并说明当前可交付的候选 |

存在源错误时允许两种清楚的结果：faithful 保留并标注源图错误，science_corrected 记录并落实修正；科学检查的 scope 必须说明哪种情况，不能把有错误的复现页当作科学正确机制。若源 review 记录 issues，则科学修正版需要 corrections；faithful 需要报告保留问题。

`generation.status: generated` 必须有本次实际调用数 ≥1、reference、实际执行 prompt；`failed` 必须有实际调用数 ≥1、发送提示词与 `failure_record`（artifacts 的键）；失败不能进入 reference_ready 或原生重建。`reused` 必须本次调用数为 0，并有 source_record；`not_run` 必须 0 调用且 executed_prompt 为 null。阶段前进依赖已有证据；修订 prompt 不会自动生成新 reference。换了参考、场景或最终文件，应重查受影响步骤并更新哈希/证据。

验证命令：

```powershell
python -X utf8 "$package/scripts/validate_handoff.py" "$case/handoff.json"
```

它只读验证声明、文件存在、哈希、后端扩展名、检查 subjects 和审计绑定。1.1 的原生审计必须同时带最终文件哈希（AI 为 ai_sha256，其余为 sha256）与 scene_sha256；不能靠外部索引替代。不会检查所有软件审计字段，也不会证明图像好看、科学正确或已由独立专家验收。CLI 对格式错误返回非零与 JSON 错误；重复键/NaN 等不是有效输入。历史 1.0 实例见 [已接入的 Illustrator 案例](../evaluations/2026-10-31-integration/handoff-illustrator.json)。

旧版 Visio 原生审计没有最终文件哈希时，`checks.native.binding_record` 可指向同期 `verification.json` 的 artifacts 键；验证器核对其中 `native_audit_passed` 及 `artifacts_sha256` 的最终文件和场景哈希。必须同时保留并核对原审计，不能只新写一个 passed 的索引。此兼容方式用于追溯已有案例，不代表今天重新打开了原生应用。
