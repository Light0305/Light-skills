# Workflow 文件与命令契约 1.0

## 适用范围和文件

多步任务的可选台账；局部任务不必使用。宿主负责研究推理、工具调用、授权判断、成本控制与专业验收。此工具只维护确定性的文件/依赖关系，不执行命令，不调模型或联网，也不会定时恢复任务。

```text
项目/
└── Workflow/
    ├── workflow.json           目标、事件和捕获的文件引用；唯一事实源
    └── 00-Workflow总览.md       带生成标记的可重建视图
```

workflow.json 包含 schema_version、WF_uuid、可选 project_id、created_at、initial_objective、revision 和 events。每个事件保留 request_id、原请求哈希、recorded_at、顺序 revision、规范化 operations 与 event_hash。重放生成当前目标和任务，不直接修改 JSON；不会覆盖专业产物。历史无限增长时可按新目标/项目备份维护，当前版不自动压缩。

每次写入持有 `.write.lock`，整份 JSON 通过同目录临时文件、flush/fsync 和原子替换提交。锁异常遗留时先确认无写入者，再恢复，脚本不自动抢锁。视图更新在提交之后，失败返回 `view_warning`，不谎报业务提交失败；修复视图后 render。视图已有手写内容时拒绝覆盖。没有跨 Memory、project.json 或原生专业文件的联合事务。

## 初始化与目标

`init --project <真实项目> --spec <json>` 读取 `objective`：goal、scope、success（非空字符串列表）、stop_rule、authorization_basis（当前真实会话请求的摘要）。示例见 assets/objective.example.json。授权摘要便于恢复上下文，不是可执行权限票据；脚本不能验证它是否真实。

一个目标表示当前约定交付，不等同整个项目或一篇论文全生命周期。目标状态 active / complete / hold / stopped；初始 OBJ-0001，换目标递增。闭合后继续实质工作用有理由的新 objective。脚本不自动初始化 Memory/project.json 或专业目录。已存在 workflow.json 时恢复而非重建。

已绑定 project_id 的台账要求当前登记仍然存在且身份一致；登记丢失不能静默退回无绑定项目。独立初始化、未绑定登记的旧台账仍可独立使用。

## apply 的批量变更

`apply --project <项目> --spec <json>`，格式为 `request_id` 非空唯一字符串、`expected_revision` 当前整数修订号、`operations` 1～100 项。先整体验证，全部成功才提交；任一步失败不写台账。调用方重读后使用新 request_id 和修订号修改计划。

相同 request_id + 完全相同请求内容可幂等重试，返回当前 revision 和原 applied_revision；相同 ID 换内容会拒绝。已成功重试不再检查旧 expected_revision。它只防止重复记账，不防止外部任务重复执行；工具超时必须先核实项目与 native run/job。

支持下列 action：

| action | 字段与含义 |
|---|---|
| `add` | 新 id，例如 T0001；skill 使用 routes.json 中实际技能 ID；title/question/workspace/inputs/depends_on/expected_outputs/acceptance/stop_rule/budget，required 默认 true；可 supersedes 旧任务并附 reason |
| `transition` | id、目标 status、reason；running 另需 execution_ref；completed 另需 evidence 和具体 verification；从 blocked 继续/取消或取消 running 另需 reconciliation |
| `objective` | 新 objective 同初始化结构，另需 reason；旧目标和任务保留，当前不再调度旧任务；存在 running 时先处理该运行再切换 |
| `close` | status 为 complete / hold / stopped，另需 reason；complete 要求至少一个当前、未被替代的 required 任务，全部完成且其来源和依赖当前可用，并且没有 running 任务 |

任务 workspace 是实际或计划中的项目内目录引用，台账不会创建它。expected_outputs 是计划交付文件的项目内路径，不接受仅目录名充当完成证据。用户只要求草稿时，交付标准如实写草稿；工具不判断其科学成熟度。

depends_on 仅引用此前已登记任务，可同批先 add 父任务再 add 子任务。因此不允许自引用、前向引用或环；研究循环通过新任务表达。任务可引用上一目标的实际完成结果，仍检查其来源与依赖。supersedes 是后继关系，会阻止旧任务再次运行，并使仍引用旧任务的依赖需复核；不会自动重绑到新版本。替代 required 任务仍必须 required。多个后继可表达真正拆分的工作，但由宿主说明责任和依赖。

budget 必填：`status=not_applicable` 用于没有收费/额外计算执行的具体任务，仍需 basis；`bounded` 需真实依据 basis 和实际 limits 文本；`unknown` 需具体缺口 basis，不能开始该任务，可先做不依赖它的诊断。文本上限不由台账计费或强制执行，实验等原生工具按实际契约约束。不能把未知预算填成 0、假装不适用，或统一套固定循环次数。

## 文件引用与变更检测

inputs 和完成 evidence 为 `[{"path":"项目内/文件","locator":"真实段落、字段、科学 ID 或范围"}]`。提交时捕获 sha256/bytes，读取时按当前文件比较；相对路径支持项目整体搬移。文件可较大，分块计算哈希。不存在的文件不能作为输入或完成证据；计划的 expected_outputs 可尚不存在。Memory 的原生事件可引用；研究事实优先引用各专业源。

inputs 表示此任务依赖的固定版本，不是所有读过文件的流水账。任务本身需要修改的活文件，先用专业原生快照、已有版本文件或受控版本清单保存前态，再将这个固定入口作为 inputs；实际修改结果作为新的 evidence。不能把将被本任务修改的唯一活文件同时当作必须不变的输入，也不能为了过检查而省略关键前提。冻结设计仍遵守新版本规则。

拒绝绝对路径、越界、链接/Windows junction、.env 类私密配置、.git 和 Workflow 自证。外部大数据、集群文件、网页或用户口述，先在专业目录保存真实来源清单/有定位的记录，再引用该文件；不能为了绕过规则复制大数据或伪造原生文件。哈希只确认该清单本身，宿主仍要检查实际外部数据身份。

来源漂移/丢失或旧任务被 supersedes 时，相关任务及其依赖会报告 needs_review。pending 的未完成依赖也报告 dependency_unusable，是等待条件，不一定是科学错误。`next` 不给出有这些问题的候选；完成时也重新检查输入/依赖，不能静默重新捕获旧绑定。改源后用新任务及实际版本，旧历史仍可读。

`usable`/候选只表示台账层面的文件和依赖条件符合，不能认证论文、工具实际可用、数据无误或授权充足。完成 evidence 至少一项，且覆盖所有 expected_outputs；verification 由宿主如实填写做过的核对及限制，不自动检查科学内容。

## 状态机与恢复

```text
pending → running → completed / failed / blocked / cancelled
pending → blocked / cancelled
blocked → pending / cancelled
```

completed / failed / cancelled 是不可逆历史；重做或重试 add 新 id，可 supersedes 并说明理由。failed 的原因应包含实际失败与已确认的进程终止状态；未确认终止则 blocked。running 再次 start 会被拒绝；但这只防止本台账中的重复状态变更，不是操作系统运行锁。

execution_ref 必须指实际准备使用的 native run/job/工作区入口，不是一个“自动执行命令”。恢复前先读这个入口。blocked 回 pending 必须填写查明实际情况的 reconciliation；若输入版本变化仍需新任务。取消 running 也需 reconciliation，不能只修改台账假装进程停止。

0.2.0 将曾启动后 blocked 的任务单列为 `recovery_required`（含实际 execution_ref），即便它没有依赖其他任务也需恢复。替换它时 add 另需 reconciliation；确认真实停止/未启动且确需重试后，后继才能承接。未知执行尚未处理时拒绝 objective 切换及 complete，防止换目标掩盖仍可能运行的作业。因缺材料而尚未开始的 blocked 不被视为未知执行。既有 1.0 历史仍按原记录重放，不伪造旧 reconciliation。

hold/stopped 不自动终止正在运行的任务。允许继续记录这些 running 的真实完成/失败/受阻或有依据取消，以及取消 blocked；不允许在关闭目标下启动或增加工作。新目标需先处理 running。complete 只表示本轮约定交付，不等于“投稿就绪”或“研究成功”。

## 读取命令与返回

- `catalog [--skills-root <根目录>]` 可重复根目录；只检查 routes.json 的候选 SKILL 文件路径，不递归扫描参考仓库，不安装、不验证运行环境。插件路径不匹配时用宿主发现并直接读技能，不能据空列表判定不可用。
- `status` 返回当前目标、全部任务、修订号、需复核和 running 提示。
- `resume [--memory-skill <light-memory目录>] [--query <当前问题>] [--max-chars 6000]` 是只读联合恢复：返回 Workflow（未建立则 null）、台账候选和 Memory 读取状态。默认从 catalog 的当前安装入口定位读取器，不从研究项目加载代码。Memory 可能为 not_initialized / reader_unavailable / read_failed / read；read 才含实际 context packet，仍需回原生证据。读取失败保留另一侧工作信息；top-level ok 仅表示恢复命令完成，各侧状态必须分别检查。字符预算沿用 Memory 契约，诊断在预算外。
- `next` 返回当前目标尚未启动、未被替代、依赖/来源符合且预算非 unknown 的任务。顺序是登记顺序，不是科学优先级；宿主选择。
- `show --id T0001` 返回任务、所有状态更新和当前来源条件。
- `history` 返回原始事件；`verify` 检查结构/历史和当前目标未被替代任务的来源与依赖；历史问题可 show 查阅。
- `render` 重建总览，不改业务历史。其余读取命令不写项目。
- `init/apply --dry-run` 完整验证但不创建目录、锁、文件或专业工作区，不能代替实际提交。

退出码：成功 0；verify 有待复核/未满足依赖时 1 且 integrity_ok=true；参数、结构或读写错误 2。running 是独立恢复提示，不等于完整性失败，也不会自动成为可重跑候选。

event_hash 可发现普通事件误改，修订与事件数也有一致性检查；这不是签名、可信日志、完整防篡改或密码学来源证明。恶意重算、尾部一致截断、外部操作的恰好一次执行、断电后的存储设备保证、跨主机共享锁，以及科研判断不在本工具保障范围内。
