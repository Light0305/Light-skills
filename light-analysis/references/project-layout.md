<!-- Generated from project-layout/assets; update the source then sync. -->
# 项目目录与续作约定 1.0

只在需要项目文件交付或继续已有项目时使用。局部讨论、改句子和一次性咨询直接按请求完成。用户指定路径、已有布局优先。

## 项目单位与定位

一个研究项目以一篇论文或一项软著为中心，也可包括同一研究延伸的软著、专利；不默认把多篇独立论文合成一个项目。先定位真实研究项目，读 README、已有任务文件和可选的 `project.json`。skill 安装目录、参考仓库、评测样例不作为用户项目；不用历史本机 `D:/Light-Science/...` 路径推定研究材料位置。

新项目按实际任务选用 `Literature / Idea / Design / Experiment / Analysis / Journal / Write / Figure / Review / Patent / SoftwareCopyright / Acquisition`。目录是归档位置，不是强制执行顺序。通常 `Literature → Idea → Design → Experiment → Analysis`，研究部分可循环和补查文献，采集按需支持；通常经选刊进入写作，写作/绘图/评审相互迭代，也可返回研究与选刊。专利、软著依实际需求建立；本约定不实现总控、不授权额外执行。

`Workflow/` 由 `light-leader` 按需维护跨阶段目标、任务依赖、交接与中断恢复状态。存在有关计划时按本轮范围查看，并把真实完成/受阻情况交接回去；专业就绪状态仍以原生记录为准。明确的小任务直接完成，不以缺少总控或台账阻断工作，也不为读取旧计划扩大本轮任务或重复启动运行。

`Memory/` 由 `light-memory` 管理项目背景、决策、失败教训与跨会话上下文。原始证据和专业历史留各阶段，记忆通过版本/路径/ID/锚点引用。README 与 project.json 仅是导航/目录登记，不代替记忆；`light-leader` 结合记忆与专业材料协调，具体工作交接按需保存在 Workflow。

开始持续项目任务时，若已有 Memory，先读其 current.md 并按当前任务核对有关来源/依赖；有 light-memory 时可用其 context/show。阶段交接或实质决定/观测变化后，宿主将实际核对的增量及理由、来源、范围记入 Memory；不要把计划当完成、把旧摘要当新证据或自动扩大授权。无记忆技能时仍可完成专业工作并提供有来源的待记忆增量，不以其缺少阻断任务。生成总览和历史由 light-memory 维护，不在 Memory 内另造一套目录索引或自动监听记录。

## 最小产物与身份

- 当前用到的阶段才建目录；不创建未发生的实验结果、审查或交付文件。原生初始化器需要的草稿保持 draft/pending。
- 完整任务放独立工作区；共同规则统一工作区位置，内部 JSON、文件名、科学状态和校验继续沿用本 skill 的原生契约，不另造同义 YAML/CSV。
- `IDEA-0001 / PROT-0001 / EXP-0001 / AN-0001 / FIG-0001 / PAPER-0001 / REV-0001 / JRN-0001 / PAT-0001 / SWC-0001 / ACQ-0001` 是项目内归档编号。保留原有 paper/idea/design/campaign/run/analysis/issue 等科学身份；归档编号不替换它们。短标题保留中文，避开非法字符和过长路径。
- 同一源材料只维护一个事实源；其他阶段保留路径、ID、版本与锚点引用。大数据、代码仓库和 checkpoints 可留在原存储，登记来源与访问方式，不为布局复制。

## 历史与导航

实质设计修订新建 `v02` 等版本；新执行批次、新分析、新评审使用新目录。论文草稿和图的内部修订沿用其已有版本机制；原始数据、冻结输入、失败/阴性记录不覆盖。反馈可以创建新一轮并引用触发它的旧分析或评审；不把科研调用网络硬塞成单向流水线。

使用已有 `project.json` 时，登记本任务的相对路径、归档 key、实际输入 key 与前版关系；归档状态 `planned / active / complete / hold / archived` 只表示整理进度，不代替专业就绪/有效性判断。没有该文件时，维护最小 README 导航即可，不为专业任务强制安装项目工具。

项目根 README 维护研究问题、当前工作、主要结论及依据和下一步；已使用的阶段可以维护 `00-<阶段名>总览.md`。包级可选工具负责受管导航块，不覆盖标记外正文。`Literature/README.md` 与 manifest 仍由文献工具维护。

已有 `Ideas / Designs / Experiments / Analyses / review / journal-selection / 软件著作权申请资料` 等目录原地续作或登记；不批量改名、搬动、补 symlink，不因目录旧就重跑研究。开始续作时核对实际输入、版本、已完成内容和未决项，不根据文件名或文件存在推断已经阅读/验证。下文是新任务默认位置；旧约定属于兼容输入。

目录管理工具位于源码包的 `project-layout/scripts/project.py`，可选而非执行依赖。它只创建空任务目录并维护根登记/导航；随后把空目录交给原生初始化器。不要提前在要求为空的输出目录塞 README 或公共元数据。专业内容的真实性与完整性继续按本 skill 核验。

## 本技能的归档与交接

默认工作区：`Analysis/AN-0001_分析问题/`

从实际 Experiment/EXP 工作区和冻结设计接入，也允许外部已有数据。保留 context.json、receipt.json、inputs、analysis-plan.json、plan-lock.json、analysis.json、analysis-report.md、code、derived、figures 及实际需要的 handoff.json。原生接入按所列文件复核封存/QC 与原始证据关联，不冒称全运行验收。输入、分析规格或实质结论更正时新建 AN，保留 parent_analysis_id、旧报告/导出和受影响图稿清单；新交接绑定计划、报告及派生登记版本。分析按原因返回 idea/design/experiment，证据足够时通常交给选刊定位、写作或绘图；实质交接由宿主将已核对增量记入 Memory 并更新有关 Workflow，不由目录管理自动触发。light-analysis 为既有安装名，保持历史拼写。
