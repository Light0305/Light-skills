# 可选案件数据结构 v1

长案用 `scripts/init_case.py` 创建 UTF-8 JSON 再填写。不必为了单句改稿填写 JSON。下面的字段契约由审计脚本检查常见错误，但不是全面 JSON Schema 校验器；未知扩展字段允许保留，核心字段不得用不同含义复用。

## 顶层字段

| 字段 | 内容 |
|---|---|
| `schema_version` | 字符串 `1.0` |
| `title` | 发明名称 |
| `jurisdiction` | 默认 `CN`；内置权要拼接器仅支持中文 CN |
| `patent_type` | `invention` 或 `utility-model` |
| `stage` | `pre-filing` 或 `filed` |
| `sources` | 材料数组，下文说明 |
| `features` | 技术特征及证据数组 |
| `claims` | 按最终顺序排列的权要数组 |
| `documents` | `disclosure`、`specification`、`abstract`，各为块数组 |
| `figures` | 图 ID、标题及图件路径 |
| `abstract_figure_id` | 有图申请选择其中一图 ID，无图为 null |
| `search` | `status`: `pending/completed/limited/skipped-by-user`，另有 `queries`、`limitations` |
| `prior_art` | 已知对比文献记录；不冒充本案原始材料 |
| `questions` | `id/text/severity`；severity 为 `blocking/important/info` |

不将行政信息未知写成伪造值；可在扩展 `administrative` 对象里用 null 记录。`questions` 和检索信息仅进工作记录，不自动进入正文。

## 材料与特征

`sources` 每项：`id`、`label`、`path` 或 `url`、`reviewed` 布尔值；可有 `publication_date`（ISO日期或null）、`role`（默认 `technical`，或 `original-application/context/prior-art`）。本地路径基于案件目录。发明人口述可存为有时间及语境的本地记录；代码来源可加 `revision`，不伪造提交版本。需要冻结材料时记录实际64位十六进制 `sha256`，审计会在文件变化时提示错误；不要手填占位哈希。背景及对比文献不能支持本发明的正式限定。

```json
{
  "id": "F001",
  "text": "超过门限时上传预触发缓冲区及当前采样数据",
  "support": "explicit",
  "source_refs": [{"source_id": "S001", "locator": "第3节第2段"}],
  "rationale": "",
  "original_refs": []
}
```

`support` 四态见材料与证据。`entailed` 需非空 `rationale`。`original_refs` 结构同 `source_refs`，已申请的正式限定需指向 `role=original-application` 的已读材料，不能指后来补充记录。需要对应原权要/说明书/图式定位，不能仅填“原申请”。

原申请来源可加 `document_kind=specification/claims/drawings`；一份合并 PDF 用引用上的
`document_part` 明确部位并优先于来源类型。`abstract/receipt/later-supplement` 不能单独支持新增
技术限定。旧记录未写部位返回 warning，不自动迁移或认证；这些标签仍需对照原件实际核查。

## 正文块

所有文档块的 `id` 全局唯一。块类型：

```json
[
  {"id":"H001","type":"heading","level":1,"text":"具体实施方式"},
  {"id":"B001","type":"paragraph","text":"采集加速度采样数据并写入循环缓冲区。"},
  {"id":"T001","type":"table","headers":["符号","含义"],"rows":[["x","采样值"]]},
  {"id":"E001","type":"equation","latex":"r=x^2","omml":"<m:oMath xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\"><m:r><m:t>r=x²</m:t></m:r></m:oMath>"},
  {"id":"I001","type":"image","figure_id":"G001"}
]
```

OMML 示例仅展示接口；真实上下标、分数、矩阵用对应结构表达，不能用该示例的线性文本冒充复杂公式。权要的 `spec_ids` 指向说明书中有实际内容的段落、表格或公式，不能只指标题或图 ID。段落内部写“参见图1”不会自动检验其语义对应，需人工核对。

`figures` 每项为 `{"id":"G001","title":"图1 方法流程图","path":"figures/flow.png"}`，可扩展图源路径、来源和标记表。路径须指向真实 PNG/JPEG；原始 SVG/Mermaid 可单独记录在 `source_path`。说明书通过 `image` 块引用每幅图；导出时抽出图件形成独立附图文件。

## 权要

```json
{
  "number": 1,
  "kind": "independent",
  "category": "method",
  "subject": "一种振动事件上传方法",
  "depends_on": [],
  "dependency_mode": "any",
  "limitations": [
    {"text":"采集振动采样数据并写入循环缓冲区","feature_ids":["F001"],"spec_ids":["B001"]}
  ]
}
```

`category` 为 `method/product/apparatus/system/device/medium/program-product/use`。实用新型仅接受 `product/apparatus/system/device` 并仍需人工判断结构客体。

`subject` 只写主题名称，不能藏入未映射的技术限定。独权渲染为“主题，其特征在于，包括：限定……。”；从属 `subject` 写“方法”等被引用主题，`depends_on` 填在前编号，多个时仅 `dependency_mode=any`。自动拼接适合常规 CN 草稿；复杂句式可使用文档工具直接成稿并单独审查，不强行更改技术含义来适配脚本。

每个限定有完整文本、非空 `feature_ids` 和 `spec_ids`。逐一检查每个实质限定，包括前序中真实技术限制。同一特征可支持多项权要，但不能以一个粗糙“大特征”掩盖未获支持的子关系。

## 对比文献与检索

`prior_art` 每项含 `id/title/url/publication_date/verified`，可扩展公开号、申请/优先权日、具体教导定位。`verified=true` 表示执行者实际核验，脚本不联网证明该声明。`search.queries` 逐次记录 `date/database/query/notes`。`completed` 不代表穷尽性或具有新颖性。已知文献未核验或检索未完成会产生警告，不能据此输出法律确定结论。

可执行示例和原始材料位于 `tests/fixtures/`，明确为工具测试虚构案例，不是真实发明事实。不要将示例参数移植到用户案件。
