# 文件契约与本地工具

Python 3.10+ 标准库；本轮在 Windows、Python 3.11 验证。本工具处理**单机、顺序、前台命令**，不执行隐式 shell，不装包、联网、提交远端任务或恢复训练。宿主仍需实现真正的实验代码、审查参数、资源、任务依赖完成情况与科学内容。

## 执行工作区

```text
campaign.json                 # ID、设计/idea 身份、执行范围、硬限额；本批次固定
upstream.json                 # 上游原件索引及本地冻结文件的指纹
inputs/design/                # context.json / design.json / plan.md / 可选 protocols
events/<event-id>.json         # 每个事件独立排他创建；不覆盖旧事件
runs/<run-id>/
  spec.json                   # 本次实际参数数组、cwd、单位、参数、预期输出
  input-manifest.json         # 输入路径/角色、大小、SHA-256、可选快照位置
  snapshots/                  # 选定的小型代码、配置、锁文件等原样快照
  environment.json            # 指定的数值环境变量、Git HEAD/状态、环境声明
  prepared.json               # 准备时各文件与 campaign 的指纹
  started.json                # 已消耗一次尝试；实际命令和生效时限
  process.json                # 只有成功启动 Popen 后才有本地子进程 PID
  stdout.log / stderr.log     # 原始字节日志
  outputs/                    # 新建目录；{output} 或 LIGHT_EXPERIMENT_OUT 指向这里
  result.json                 # 实际进程状态、退出码、耗时、产物检查、输入漂移
  manifest.json               # 封存后的文件清单；不包含它自己及后续 assessments
  assessments/<id>.json       # 宿主的 QC/科学判定；后续更正追加、连接 supersedes
derived/                      # 分析/图表等派生物，按项目需要建立
execution-report.md           # 人类可读交接
```

只在实际发生对应步骤时创建文件。所有相对记录路径必须在指定根目录中，拒绝路径穿越、绝对输出和输出链接逃逸；输出的符号链接/junction/特殊文件不会被沿着复制，清单会报告未归档项。原始输出不自动删除，不隐式压缩或上传。

`init` 拒绝覆盖已有工作区、与设计重叠的路径、技能目录内的研究输出。协议目录有链接时拒绝隐式跟随。冻结副本用于本批次，原件后来变化只警告；副本或 campaign 自身变化会报错。未来版本创建新批次，旧批次保持。

## 创建与准备：不启动实验

```powershell
python "<skill-root>/scripts/experiment.py" init --design "<project>/Design/PROT-0001_方案短名/v01" --out "<project>/Experiment/EXP-0001_执行批次" --max-runs 6 --max-wall-seconds 1800 --budget-basis "本轮批准的六次本地尝试和半小时进程墙钟"
```

示例数字仅演示语法，真实限额必须来自任务。可重复 `--experiment-id X01` 取上游就绪范围的非空子集。草稿可导入，不会被升级；准备运行时检查状态、范围、任务关系/环、资源、门槛和样本论证状态，并要求冻结 plan.md 非空。此处不是上游完整校验器，也不核算科学功效。先由宿主核对 `plan.md` 与 JSON 以及真实可用性；Design 的直接来源检查不会因 init 而自动执行，外部论文/数据也不会自动复制。

填好 [run-spec.example.json](../templates/run-spec.example.json)，再运行：

```powershell
python "<skill-root>/scripts/experiment.py" prepare --workspace "<execution-workspace>" --spec "<filled-run-spec.json>"
```

重要字段：

- `run_id / experiment_id / task_id`：安全 ID（1–64 字符，字母/数字开头，其余为字母数字、`_`、`-`）；后两者必须匹配冻结范围。
- `kind`：`smoke / baseline / pilot / experiment / confirmation / diagnostic`。`unit` 保存科学单位及 seed/fold/instance/resolution 等实际轴；`parameters` 保存实际解析参数。
- `parent_run_id`：可选的已有尝试，说明修复/续跑关系；原因和科学影响另记事件。`depends_on_runs`：可选前置运行，启动前要求其成功、产物合格、输入无运行中漂移、终止已确认且最新 assessment 的 QC 通过，递归核对间接前置。科学结果为 falsify 不阻断技术有效的前置。started.json.dependencies 保存实际采用的 result 与 assessment 文件指纹；上游开发任务的人工验收由宿主检查，工具不推断其完成。
- `argv`：真实可执行文件和逐项参数；不把整串命令塞进一个元素。首项必须可找到，`.bat/.cmd` 需显式解释器。`cwd` 是实际项目目录。参数中的 `{output}` 展开成该次新目录，也可从环境读 `LIGHT_EXPERIMENT_OUT`；没有其他模板替换。
- `timeout_seconds`：正有限数。`environment` 只支持实现列出的非敏感数值变量，如线程、可见设备和确定性选项；其有效值在准备/执行间不得变化。认证配置留在已有运行环境，不能写进命令、配置或日志。工具不全量导出环境。
- `provenance.environment / hardware / determinism`：宿主实际核对的记录；不清楚时如实写未知及影响。`runner_python` 只是记录器的解释器，不能当作 R/Julia/C++ 或另一个 Python 环境的版本。
- `inputs[]`：存在的单个文件，包含 `path / role / snapshot`。至少有代码/二进制；自行包括真正影响计算的源码、评价器、解析配置、依赖锁、数据/划分等。小文件 `snapshot=true`，大文件可只做流式 SHA-256（仍有 I/O 成本），或哈希能定位不可变版本的 manifest。工具不递归发现 import、动态数据或完整环境依赖。目录先做明确清单，不把目录名当数据版本。
- `expected_outputs[]`：相对 outputs 的明确文件，带 `role / required / min_bytes`。至少一个原始产物必须 required=true 且 min_bytes>0（缺省为 1）；可同时有可选诊断文件或空标记文件。不能仅凭空目录或可选输出通过运行。不存在或过小的必需文件会使产物检查失败；文件非空仍不自动表示数据有效。

准备后修改输入会在启动前被拒绝；修改 code/config 需要新 run ID。已封存的前置输出可作为新运行输入，按同样方式记录指纹。不要边跑边改共享源码；正式运行宜用明确的代码版本/隔离副本。记录器在开始和结束哈希列出的输入；运行中改了又还原、未列出的依赖变化仍可能漏检。

## 运行与预算

```powershell
python "<skill-root>/scripts/experiment.py" run --workspace "<execution-workspace>" --run-id R001
```

同一个 ID 只能启动一次；stdout/stderr 原样保存。尝试从创建 `started.json` 起计数，启动失败、崩溃和超时都消耗次数。生效时限为单次 timeout 和批次剩余进程墙钟的较小值；达到限额不再启动。不自动重试，修复后准备新 ID。计时采用 monotonic；结束与强制终止有少量额外开销，不能承诺精确到时刻的成本硬隔离。数据哈希、实现、排队和分析耗时须由宿主另外记入项目总投入；这个限额只覆盖记录器测得的子进程墙钟。

预算与 run_started 事件对账。已记录尝试的目录或 started.json 丢失时拒绝继续启动，不能因移走失败记录而恢复额度；从真实备份恢复或由宿主明确核实历史与剩余授权。事件不是防篡改账本，同时改写所有本地依据不在该检查能力内。

正常完成只证明受监督的前台进程退出。不要用这个工具包装 `sbatch`、远端提交、分离子服务或后台 shell，然后将提交成功当成实验完成。对于受监督进程超时/中断，Windows 用指定 PID 的 `taskkill /T`，POSIX 用进程组终止；无法确认终止时保留不确定性并阻断后续启动。它不是容器/作业调度器，不能限制任意程序的所有系统副作用或保证捕获脱离进程组的后台进程。

工作区使用排他锁，默认顺序执行。断电/强杀后不要直接再跑同一 ID。先检查锁和 PID、真实日志以及残留任务，按 execution.md 处理，再：

```powershell
python "<skill-root>/scripts/experiment.py" recover --workspace "<execution-workspace>" --run-id R001 --reason "实际核实的进程停止依据与中断原因"
```

有 `result.json` 的尝试保持原记录，用 `note` 追加纠正；`recover` 只为缺失结果的尝试建立明确中断记录。检查记录 PID 不存活仍需操作者确认残留后代/远端任务。恢复时真实终止时间未知，`ended_at=null`，从开始到恢复的时间按保守上界计入预算，不能当成测得的真实计算时长。

## 质检、解释与事件

填好 [assessment.example.json](../templates/assessment.example.json)：

```powershell
python "<skill-root>/scripts/experiment.py" assess --workspace "<execution-workspace>" --run-id R001 --file "<filled-assessment.json>"
python "<skill-root>/scripts/experiment.py" note --workspace "<execution-workspace>" --file "<event.json>"
```

QC 状态 `pending / passed / failed / unknown`；科学 outcome `support / falsify / inconclusive / not_evaluated`。进程失败、缺失产物或输入漂移不能通过 QC；当前前置失效时也不能通过。支持/反驳需通过 QC、关联主张和有原始依据的指标。`metrics[]` 每项 `name / value / unit / artifact / locator`；值为有限数或 null，artifact 必须是封存清单内的 outputs 文件、stdout.log 或 stderr.log，不能引用 spec、输入快照、封存元数据或事后 assessment 附件。locator 指出 JSON 键、行或索引，须由宿主实际读取核对。程序失败时正式指标保留 null，部分诊断值仍在原始日志中。脚本核对文件归属与完整性，不解析 locator、不计算指标，也不认证主张。

事件输入示例（按实际填写）：

```json
{"event_type":"deviation","run_id":"R001","occurred_at":null,"actor":"实际操作者","observation":"实际发生的变化；发生时间无法恢复","interpretation":"推测及影响，和事实分开","evidence_refs":["runs/R001/stderr.log:实际行号"],"next_action":"有依据的动作","retrospective":true}
```

发生时间有来源时用带时区的 ISO 时间；`recorded_at` 由工具写入本机 UTC 时间（非可信第三方时间）。同类记录追加新文件；assessment 更正连接 `supersedes`，事件更正用 `corrects_event_id`。追加或使用评估前检查完整更正链及历史内容，并与已记录 run_assessed 对账；删除最新失败判定不能回退采用旧的通过判定。哈希不是数字签名，本地文件也不是防篡改 ELN。

## 检查与退出码

```powershell
python "<skill-root>/scripts/experiment.py" verify --workspace "<execution-workspace>"
```

检查冻结交接、准备文件、运行 ID、封存产物指纹、遗漏/新增文件、评估内容和事件身份。`ok=true` 可以同时包含未运行、失败运行和 QC 待评估警告，表示记录结构/完整性通过，**不是实验成功**。设计草稿/上游原件变化只警告；本地快照漂移或封存产物被改报错。未列出的外部输入、统计有效性、指标语义、任务实际完成、真实硬件和完整代码依赖不在工具认证范围。

未启动运行的列明输入漂移会报错，完成后正常修改活跃代码不改写旧运行。前置被撤销或其完整性失效时，下游核查报错并保留原始文件；前置仍通过但采用的评估指纹改变、或旧运行未记录该绑定时，提示人工复核。QC 的 pending/failed/unknown 继续显示警告。分析交接与更正处理见 [evidence-and-handoff.md](evidence-and-handoff.md)。

退出码：0 为该工具动作完成或结构无错误；1 为本次运行失败/不完整或校验失败；2 为参数、读取或前置条件错误。运行失败返回真实 `returncode` 字段，CLI 退出码本身不透传实验进程所有退出值。JSON 拒绝重复键和非标准 NaN/Inf。

## 已有结果和外部任务的适配

已有追踪/调度记录是原始依据，不要求迁入此工具或补跑。手动建立等价的执行索引：设计身份、真实 run/job ID、原始命令配置和输入、状态查询记录与时间、实际退出码、原始存储 locator/版本/指纹、QC 和科学判定。未知字段 null 或写明未知，`recorded_by=external_scheduler / user_report / retrospective_import` 与本地实际记录分开。

外部导入文件独立保存（如 `external-runs/<original-id>/`），不要伪造 local `started/process/result` 或让 `verify` 误认证。`note` 可引用这些外部证据，完整手动索引由宿主检查；它们不自动计入 local runner 的预算，因此必须在项目总预算表中核算，不能借此绕过限额。
