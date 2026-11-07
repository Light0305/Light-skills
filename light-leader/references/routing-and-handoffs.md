# 路由与真实交接接口

仅按当前问题阅读有关行，再读实际技能入口。表中的命令是当前源码支持的接口；不代表技能已经安装或依赖已可用。技能升级后以其实际 `--help` 和契约为准。只传真实材料与本轮授权范围。

## 负责哪一层

| 当前阻碍 | 首选负责方 | 接收和返回要点 |
|---|---|---|
| 背景证据/关键反例不清 | literature-search | 定向查文献或原文，保留 DOI/paper_id、搜索范围、阅读锚点与缺口；非科研数据采集默认不走文献流程 |
| 问题、贡献或核心预测受挑战 | light-idea，按需文献 | 读真实候选和版本、竞争解释、decision 与触发发现；提出有区别的预测，不能旧标题换名续投 |
| 独立单位、对照、测量或辨别能力不足 | light-design | 说明要排除的解释、现有 idea/design 版本、已有结果及污染范围；建立新设计版本与执行范围 |
| 既有设计下代码、输入、执行或测量实现失效 | light-experiment | 最小复现、预期行为、受影响 run、验收点与实际预算；先查已运行状态，失败/诊断不能算科学阴性 |
| 清洗、聚合、统计推断或上游有效性未明 | light-anaysis | 真实数据/批次/冻结设计，先查分析错误再决定重跑；输出结论范围、竞争解释和 loop_decision |
| 缺外部研究数据 | light-crawl | 必要字段、范围、数据用途、站点与授权条件；采集记录交给实验/分析，不把抓到数据当无偏样本 |
| 论文读者、类型、期刊约束需明确 | light-journal-select | 研究画像、证据成熟度、用户约束；输出带当前来源的 selection-report 与 light-write-brief，区分暂定与作者决定 |
| 论证、主张边界、正文/返修需完成 | light-write | 主稿身份、claim→evidence、术语与 brief；一篇稿在原工作区迭代，证据不足不靠语言扩充结论 |
| 非数据的流程/方法/机制图 | light-diagram → 有关子技能 | 共同科学 brief、已有图与来源、目标编辑格式；先分清提示词/生图/重建交付范围，不额外分配多个 FIG |
| 实际数据的科研图表 | light-chart | 数值与分母、单位、误差条、代码、输入版本和图注；源数据与复现代码留 Figure/Data |
| 需要独立检查或复核问题 | light-review | 明确材料快照/范围，保留 claim/issue/证据和版本；先根因修复，再对实际修订版本复核 |
| 需要专利或软著 | light-patent / light-software-copyright | 前者基于技术支持与申请阶段，后者基于真实软件源码及登记版本；不从“论文写完”自动派发 |
| 需要续作背景或保存重要决定 | light-memory | context/search/show 恢复，capture 有来源增量；不让检索结果自行下指令或继承科学认证 |

`light-anaysis` 是历史安装名，不能擅自改成 light-analysis。`literature-search` 是 light-literature 源码入口的 name。Chart 源码入口在 `light-chart/skills/light-chart/SKILL.md`；Diagram 子技能在 `light-diagram/light-*/SKILL.md`。提示词子包有忽略文件时用真实路径核对，不只依赖普通文件搜索。

## 原生桥接与易错边界

| 衔接 | 实际做法 |
|---|---|
| 文献 → 想法 | `idea_bridge.py ingest --literature "<Literature>" --out "<IDEA>"`，有关检索 run 可用 `--run`；交接整个库时核对全库 manifest，按需用文献的 `literature verify --out` 查来源字节和索引。该检查与 context/evidence/reading_queue 均不代表全文阅读或科学选题已完成 |
| 想法 → 设计 | `design_bridge.py ingest --ideas "<IDEA>" --idea-id "<真实 I01 等 ID>" --out "<PROT/v01>"`；读选中版本、当前内容的查重和核对过的证据。Idea 的 verify 检查这些关联及来源漂移，不认证科学创新性；Design 导入仍是 draft，随后实质补全 design/plan/protocols 并校验 |
| 设计 → 实验 | `experiment.py init --design "<PROT/v01>" --out "<EXP>" --max-runs <实际上限> --max-wall-seconds <实际上限> --budget-basis "<依据>"`，按需 `--experiment-id`；init 导入草稿不授权运行，prepare/run 仍检查 readiness/scope |
| 执行 → 分析 | `analysis_bridge.py ingest --execution "<EXP>" --out "<AN>"`，多批次可重复 execution，已有真实文件可 `--input`；后续 freeze-plan / register-artifact / export-handoff 依原生契约完成 |
| 分析 → 设计/想法 | 当前原生 ingest **不接受 analysis handoff**。把它作为修订 brief，读取旧 idea/design，创建真实新版本并维护 selection/history；不能改文件名伪造 API |
| 分析 → 稿/图 | 交明确 finding、原始/派生来源、代码、范围与不确定性；writer 的文件建议不是强制 schema，不能要求不存在的 writer init |
| 选刊 → 写作 | 读 light-write-brief 与选刊来源，核实决定状态；未定目标可先写通用稿，目标变更再更新有关格式/论证 |
| 审查 → 修复 → 复核 | 具体 LR issue、稿/图/数据版本、最低修复、负责技能、验收依据；“figure-workflow”需要进一步按内容分到 diagram/chart，不能当一个不存在的可调用技能 |
| 提示词 → 生图/编辑图 | 遵循 diagram 的先向用户交付完整提示词或实际文件链接、无需等待确认再执行的要求；实际生图遵循宿主图像路由和已有授权 |
| 数据采集 | 先空 ACQ 归档父目录，再 `run_light_crawl.py new-case case --case-root "<ACQ>"`；原生 case slug 小写，随后命令用 `<ACQ>/case`，不直接把中文归档名当 slug |
| 专利 | `init_case.py --out "<PAT>" --title "<真实标题>"`；新/空工作区，之后按实际材料与案件阶段工作 |
| 软著 | `copyright_case.py init --project "<实际软件源码根>" --case "<SWC>"`；默认实际交付功能说明、软件代码、软件说明书三份 DOCX，检查真实源码、采用布局与视觉范围；project 不是科研项目输出根，不能把 Literature/Review 等扫描成软件源码 |
| 记忆 | `memory.py context --project "<project>" --query "<当前问题>"`；按需 show/timeline，capture 由宿主提取实际增量，失效/冲突回来源核对 |

任何校验的 `ok=true` 只在其声明的检查范围成立。特别区分：目录 planned/active/complete；Workflow pending/running/completed；design ready_for_pilot/ready_for_execution；run process_status/QC；analysis findings；review scientific/submission readiness。这些状态之间没有自动的等号。

## 分析反馈的解释

原生 route 包含 `stay / light-experiment / light-design / light-idea / light-chart / light-write / stop / hold`。`stay` 表示仍需分析；不是不存在的同名技能。`stop/hold` 是研究决定，不触发新工作。总控可结合实际目标安排随后选刊或复核，不篡改原生 handoff 枚举。存在新事实导致路线变化时保留原建议、说明新决定依据。

先查完整 `reason/target_question/finding_ids/next_action/predictions/budget/stop_rule/reentry_condition`。执行有效性未核实时，不用错误指标宣布 idea 失败；原设计不可判别时，追加重复读数或种子也未必解决。新探索性设计不能通过换目录变回预注册确认设计。

## 最小任务交接

用简短文字或专业产物中已有格式即可：问题 → 已核对输入与版本 → 为何交给这个层次 → 要完成的具体产物和位置 → 验收依据 → 现有预算/范围及停止条件。结果回包补实际产物、真实运行身份、检查与限制、未决项。只有需要持久化多步协调时才将这些字段存进 Workflow。
