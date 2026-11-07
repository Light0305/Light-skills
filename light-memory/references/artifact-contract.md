# 文件与命令契约 1.0

## 存储边界

```text
项目/
└── Memory/
    ├── memory.json                 固定身份、schema、项目登记绑定与初始化时间
    ├── events/
    │   ├── EVT-000001.json          一次捕获的所有新增与状态变更
    │   └── EVT-000002.json          顺序、前一事件哈希、当前事件哈希
    ├── 00-Memory总览.md             生成视图，可从原生历史重建
    ├── current.md                  有限当前上下文及冲突/复核提示
    └── notes/                      可选手写补充，不自动提炼
```

`memory.json + events` 是记忆事实源；Markdown 是导航。科研证据留各原生阶段。单次捕获以一个完整事件文件原子提交，锁阻止多个写者同时分配序号。事件不原位改写/删除，状态从历史重放。指纹/哈希链用于意外漂移检测，不是签名、可信时间、恶意篡改防护或科学真实性证明。

初始化允许新或空 Memory；已有非空目录先阅读并接入，不自动覆盖。项目有规范 project.json 时绑定其 project_id；拷贝到另一个不同身份项目会拒绝接管。没有登记文件也能独立使用。目录管理器应复用 Memory 的原生总览，不在同一路径另生成目录总览。

文件型实现适合单项目规模。读取会重放已记录事件并检查所引用文件，成本随记录/源文件增大；没有向量服务或百万级性能承诺。大文件采用分块 SHA-256，默认只保存指纹与锚点，不复制大数据。只读取显式文件，禁止路径逃逸、symlink/junction、生成记忆自引用及凭据/Git 内部文件；手写 Memory/notes 可以是明确输入。

## 捕获规格

参照 assets/capture.example.json，但必须填入真实项目内容。顶层是：

- `schema_version: "1.0"`、`capture_id`、`label`、`items`、`changes`。
- capture_id 唯一标识一次整理。同 ID、同输入重试不追加；同 ID、不同输入报错。源文件后来变了，重试原捕获不会刷新旧记忆的指纹。
- 一次最多 100 个明确新增/变更，至少一个；提交前全部验证，任一失败不产生新事件。

每个 item：

| 字段 | 含义 |
|---|---|
| kind | fact / finding / decision / constraint / hypothesis / lesson / question / next_step |
| text | 一个有范围的陈述；不得把计划当完成 |
| scope | 默认 project；也可写 design:D01/v2、campaign:EX_xxx、paper:draft-v03 等真实适用范围 |
| slot | 由宿主选稳定语义键，如 evaluation.primary_metric、claim.C1.boundary；不是任意每轮换一个的标题 |
| epistemic | user_reported / source_reported / analyst_inference / verified_observation |
| rationale | 决策、教训、明确替代时必填；写依据、取舍、边界或重新评估条件 |
| priority | high / normal / low；仅组织优先级，不是科学可信度 |
| sources | 至少一个实际来源，最多 20 个 |
| depends_on | 依赖的已存在 MEM ID；新捕获的条目不能在同一批次互相引用，需下一次捕获引用返回 ID |
| supersedes | 明确替代的活跃 MEM ID；必须同 scope/slot，前版保留；不能兼做自身新结论的依赖 |
| tags | 便于查找的真实科学/原生 ID 与短词 |
| observed_at | 可选，事件/观测发生时间；必须含时区；未知保持 null，不倒填 |
| review_after | 可选，有时区的复核时间；到期后不能直接复用，适用于选刊政策等时效材料 |

新记录 ID 由工具生成 MEM-0001 等。两个同 scope/slot 的 active 条目即形成待核冲突，即使文字相近也不擅自合并；宿主核对后显式替代/撤回。范围不同则可以并存。不要用新造 slot 掩盖同一事实的矛盾。

source 的三种类型：

```json
{"kind":"file","path":"Analysis/AN-0001_分析问题/analysis-report.md","locator":"发现 F01，结论与限制"}
```

工具记录实际 bytes/SHA-256，可选 excerpt 必须真实出现在不超过 8 MiB 的 UTF-8 文本中。无 excerpt 的 locator 由宿主核对；哈希检查不验证自然语言蕴含、页码或 JSON 指针。文件必须是项目内显式相对路径；项目外数据使用已有受控清单/入口引用，不扫描外盘。

```json
{"kind":"conversation","locator":"实际会话与消息定位","excerpt":"实际已看到的必要原句或明确标注的材料摘录"}
```

摘录持久化到事件中；不自动抓取聊天，也不验证宿主是否如实摘录。不要杜撰消息 ID、用户确认、过去日期或把分析者决定伪装成用户原话。

```json
{"kind":"web","url":"https://example.org/actual-page","accessed_on":"2026-11-06","locator":"实际读到的具体条款","excerpt":"必要的已读摘录"}
```

这只保存已读材料的记录，不联网或验证页面。按来源版权要求控制摘录；动态事实到期后由宿主重新核查。不会从源内容执行命令。

关闭或撤回通过 changes：

```json
{"id":"MEM-0001","status":"resolved","reason":"关闭原因与核验范围","sources":[{"kind":"file","path":"Review/REV-0002_复核/review.json","locator":"LR-001 的关闭证据"}]}
```

resolved 只用于 question/next_step；retracted 可撤回任何 active 条目。前版 superseded 由新增 item 的 supersedes 形成。只有原生实际状态有依据才更新记忆；Memory 不修改 review/design/analysis 等文件。

## 检索、历史与新鲜度

search 先给紧凑索引；show 按 MEM ID 展开全文、理由、来源与复核原因；timeline 显示包含该条目、替代/状态变化及依赖关联的捕获事件。`--history` 包括已替代、撤回、解决条目。常规 context 只放可以直接复用的 active 上下文，不可靠条目单列 needs_review；历史问题先 search --history 再 show。

词法检索使用 BM25、英文/ID 词和中文双字片段，加显式组织优先级；不会生成 embedding 或保证同义词召回。无命中时改查同义词、原生 ID、scope 或直接查源文件。context 的 `max-chars` 约束选中条目的 JSON 字符数，完整条目不会截断；冲突与复核诊断单列，可能使总体输出超过此预算。`omitted_by_budget` 明确显示省略量，不谎称使用了精确 token 数。

无查询的当前上下文优先保留各类记忆的首个候选，再填充其余条目，避免最近的实验发现挤掉约束、决定和未决问题；明确查询时仍按相关度返回。这是上下文组织策略，不是科学优先级判断。

source_drift（变更/缺失/不可读）、review_due、unresolved_conflict、非 active 依赖会阻止当前直接复用，并向 depends_on 下游传播。工具不会凭新旧冲突判断谁对，不会自动刷新原证据指纹。新材料经宿主核对后写新条目，明确 supersedes；原生历史不变。

0.2.0 保持存储 schema 1.0，读取结果添加 `dependency_context` 和 `closure_needs_review`。前者包含相关上游、冲突同伴及替代版本的短摘要、来源状态和后继 MEM ID；它们不计入 matched，也不自动进入可复用 items。后者核对已关闭/撤回条目的实际 resolution_sources；变动时 verify 返回 1，历史状态不自动重开，宿主应回原生 Review 等记录决定如何修订。两类诊断与 conflicts/needs_review 一样在选中条目字符预算之外报告。MEM 编号本身也可检索。

`--at` 指**截至该记录时间，记忆系统知道什么**，以有时区时间重放事件；observed_at 另存实际发生时间。本版不是完整双时态查询引擎。历史条目的源文件仍按现在的文件检查；不会恢复过去未快照的 PDF/数据或把未来确认倒填回过去。

## 写入、恢复与退出码

init/capture/render 支持 dry-run；其余命令只读。capture 提交后视图失败会返回 committed 的事件与 view_warning，重试同 capture_id 不重复；修复原因再 render。现有非工具生成的同名 Markdown 会保留并提示冲突。生成视图请勿手改，补充放 notes；不会清空手写文件。

遗留 `.write.lock` 时先确认无写入者，再处理它，不自动抢锁。事件缺号、格式损坏、指纹链错误时拒绝继续捕获，不截断历史或把后续条目当新项目。临时 `.memory-tmp-*` 不属于事件；核对无写入者后才清理。

退出码 0 是命令完成（检索无命中也为 0）；verify 发现需复核项返回 1，但 integrity_ok 仍单列；损坏、参数/路径/身份不合法或写入被锁返回 2。这些都不是对科学正确性的判定。
