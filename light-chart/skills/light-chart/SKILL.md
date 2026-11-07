---
name: light-chart
description: >-
  Create, refine, and audit scientific data figures in Python or R from real data,
  existing plotting code, or a reference image. Use for 科研绘图、选图、多面板排版、
  组学注释热图、随访与效应图、实测信号和时频、生态排序、真实三维场、
  图像板伴随定量、参考图适配、LaTeX 科研表格与可编辑论文图交付。
  Pure manuscript prose and AI-generated mechanism illustrations use other workflows.
metadata:
  version: "0.11.0"
---

# Light Chart

## 项目目录与续作

需要落盘或继续已有项目时，先读 [项目目录约定](references/project-layout.md)，按其中的本阶段位置、版本与关联规则保存；用户指定路径和旧项目优先。包内资源相对本 skill，研究产物相对真实项目，二者不要混用。只做局部讨论时无需初始化目录。

持续项目、评审修图或稿图交接再读 [项目证据与版本衔接](references/project-integration.md)：先恢复有关 Memory，再回科学原件与采用的 FIG/分析/稿件版本核对；实质修订保留前版，将实际结果和未决项接回 Write、Review、Memory 与已有 Workflow。

以 nature-figure 的研究问题—证据—实现—成图核查为执行主干。SciPilot 与 figures4papers 的获许可资源按任务接入；Light-Science 自行实现审图修订工具，并编写[视觉与三维指南](references/visual-review/overview.md)。FigMirror 的概念启发保留来源说明，公开包不包含它的原始代码、提示词或示例图。文件数量和自动 PASS 不证明科研表达或视觉质量。

## 从实际输入开始

先理解研究问题、统计单位、配对/重复/层级结构、分母、单位、原始或汇总数据、已有代码和最终用途。关键科学含义无法推断时才提问；尊重已确定的 Python/R 选择，普通后端选择不增加确认或写全局偏好。

- 数据新画或实质重做：先读 [workflow.md](references/workflow.md)，采用 Nature 的简短任务契约和证据组织，再选图与实现。不要要求用户填写大型任务表。
- 已有图改进：先运行/实际看图，保留正确数据、映射和构造，定位影响理解的问题后修改。
- 参考图适配：实际查看原图，读 [reference-style.md](references/reference-style.md)。拆解构造、必要标志、面板比例、图例/色标和文字层级；新数据不适配时说明改造，不能照搬数值或像素坐标。
- 多表/多实验：一张图围绕一个研究问题组织互补证据，给每个面板明确的问题、角色与独有信息。矩阵旁再列同序原值不自动增加证据；重复视图可有必要，但应有明确阅读用途。
- 论文表格：默认输出 LaTeX 与结构化数值，读 [tables.md](references/tables.md)；表格不算一张新图，不默认转成图片。

图中保留数据、坐标和单位、必要图例/色标、面板字母与短条件标签。介绍性标题、长方法、来源、误差说明和审查文字放图外独立图注；删去横幅后重新布局，不能留下大块空带。

## 准备任务并找到真实实现

`figure_job.prepare_job(sources, spec)` 或 `python scripts/figure_job.py --data NAME=data.csv --spec task.json --out decision.json` 将实际数据剖析、科学字段映射、选图/证据检查和实现检索连起来。模型据上下文写简短 spec；单图包含 question 与 chart，多面板沿用 evidence_tools 的 question/claims/panels。它准备决策，**不自动完成分析、出图或审阅**。本地 CF NetCDF 用显式 `intent=scalar_field`、变量/坐标、维选择与归约声明接入同一入口；先归约成二维场再剖析，详见 [fields-and-3d.md](references/fields-and-3d.md)。

`library.py route --query "配对变化"` / `--backend r` 定位可调用入口、输入边界和完整来源；`search` 查完整代码与资料。有取舍时用 `library.py plan --data data.csv --spec chart.json --out choice.json`。`unimplemented_concepts` 和 `adaptation_required` 必须处理；正文提到某图型、图库样例能运行，都不等于已有任意数据适配器。检索显示数量不应隐藏混合任务的缺口。

需要领域布局参照时，用 `library.py search --kind visual-reference --query "clinical forest risk evidence"` 按研究问题和构造查完整论文图；打开返回的图和卡片，核对证据角色、布局与适用边界，不能把参照命中算成可调用能力。

实现前打开实际要采用的函数/完整案例及其图，不能只读合并指南。第一轮使用来源时读 [source-adaptation.md](references/source-adaptation.md)，完整定位见 [library-guide.md](references/library-guide.md)。不要机械要求每次调用四套，也不要把检索到的资料记为已经执行的代码。

## 领域与构造按实际能力进入

| 当前任务 | 按需打开 |
| --- | --- |
| 比较、配对、分布、趋势、矩阵与估计 | [chart-selection.md](references/chart-selection.md)、[python.md](references/python.md) |
| 多面板证据、主次与实测留位 | [multipanel.md](references/multipanel.md)、nature 完整证据架构 |
| 字体、语义颜色、实际印刷阅读 | [design.md](references/design.md)、[editorial-review.md](references/editorial-review.md) |
| 原生 R、注释热图、KM+风险表 | [r.md](references/r.md)、[domain-workflows.md](references/domain-workflows.md) |
| 实测波形、全程极值、PSD与时频 | `scripts/signal_plots.py`、`scripts/domain_decisions.py`；采样率和实际秒坐标一致才进 Hz 域 |
| 群落 Hellinger-PCA 排序 | `scripts/ordination.R`、`scripts/domain_decisions.py`；明确覆盖等级/丰度含义与完全匹配的样本ID |
| bulk gene-count 描述结构 | `intent=count_structure` 与 `scripts/omics_plots.py`；明确 CPM、pseudocount 与 CPM/count 筛选规则。`pca_scores()` 保等单位并返回逐 ID artist、独立颜色/形状映射；`metadata_source`、`sample_id` 严格匹配，不能从样本名猜注释或生成差异显著性。用法见 [domain-workflows.md](references/domain-workflows.md) |
| 观测 2×2 相对与绝对风险 | `intent=two_arm_risk_evidence` 与 `scripts/effect_plots.py`；映射四个真实计数，明确独立二项工作模型、置信水平与尺度；零事件 RR 保留为 unavailable，不自动校正或汇总 |
| 实测预算扫描与预测计数 | `intent=computational-sweep/confusion-counts` 与 `scripts/computational_plots.py`；重复/划分语义、完整键与记录ID；不自动拟合模型或推断独立性 |
| 实测材料复阻抗 | `intent=impedance` 与 `scripts/impedance_plots.py`；显式映射谱ID、Hz、Re Z 和物理符号 Im Z（Ω），保留所有象限；Nyquist/Bode 不自动拟合电路或归一化面积 |
| 汇总分类计数、真实mosaic/静态alluvial与重复行为轨迹 | [domain-workflows.md](references/domain-workflows.md)、`count_tables.py`、`repeated_measures.R`；保留分母、零单元和重复单位，不将汇总表展开个体 |
| 图像、连续场和真实三维 | [fields-and-3d.md](references/fields-and-3d.md)、`image_layout.py`；按需读[三维指南](references/visual-review/three-d/route.md) |
| 完整论文组合与参数扫描 | [paper-patterns.md](references/paper-patterns.md)、figures4papers 完整代码/实际成图 |
| 实际审图反馈、修订与选稿 | [review-cycle.md](references/review-cycle.md)、`scripts/review_cycle.py` |
| 目标期刊与输出约束 | [journal-output.md](references/journal-output.md)；明确投稿要求时核验当前官方规范 |

以上是入口，不是完整学科分析能力声明。PCA 不代表 UMAP；排序得分图不代表带载荷箭头的 biplot；真实高度场不代表体数据。`assets/library/implementations.json` 中的输入和边界决定实际覆盖。论文图片库与旧模板只作经过实际看图/核对的辅助参考，不作为核心执行依赖。

## 设计、绘制和修订

先定最终物理尺寸、证据主次和必要构造，再留坐标/标签/图例/色标空间。`composition.compose(...).figure` 与 `fit()` 负责跨行列和实测留位；`min_plot_mm` 核对固定 aspect 后的真实数据区，报告同时保留实际与分配矩形。空间不足时改变组织或尺寸，不缩字或拉伸等单位坐标掩盖。图像保比例，连续场保真实坐标，比较面板保需要共用的尺度。

颜色按类别、顺序、真实中心的偏差或周期选，不能给所有领域统一套淡色。用本任务的 `project-style.json` 固定身份、符号/线型、字体和色标；Python/R 共享语义。检查实际透明度、小点、细线和深色文字，不用色板名称代替可读性；灰度下需要保留的正负方向应有额外编码。参照是具体结构与语义，不只是吸取色号。

绘制用用户选择的原生后端：Python `publication.save_figure()`；R `publication.R` 与 `r_runtime.py run`。固定页面导出，核对最终 PDF 字体、几何与数据；后端无关检查可检查 R 文件，不能用 Python 近似图冒充原生 R。需要 helper 时随任务交付，不能依赖原始参考仓库绝对路径。

文件型 `source_data` 自动记录来源路径与字节；其余实际输入可用 `source_files` 绑定数据、绘图代码、配置、helper 和图注，R 沿用同名参数。采用图前可运行 `python scripts/source_binding.py figure.qa.json` 只读复核已记录来源及导出；具体范围见 [项目衔接](references/project-integration.md)。它不证明代码实际使用了这些输入，也不把内存表摘要当作源文件核验。

实际看当前 PNG 和最终 PDF 渲染，再看整图、局部和最终尺寸。技术核对与视觉判断分开：前者查数值/ID/区间/单位/导出；后者查互补证据、主次、拥挤、无意义留白、颜色与查找成本。

复杂任务使用 [审图修订流程](references/review-cycle.md)：定位问题、保留正确部分、修改代码、重渲复核与选稿。`review_engine.py` 记录真实返回的意见、检查文件绑定并管理轮次；宿主负责安排真实审阅上下文。不能把自检称为独立审阅。`raster_diagnostics.py` 只报告像素诊断，不输出综合质量分。

`review_tools.compare_revisions()` 检查修订是否丢数据、必要面板/构造、单位或身份映射。`record_review()` 绑定实际当前文件的执行者自检，不能证明独立审查。无问题不强凑轮次，最新版不自动最好；到预算上限仍有重要问题要记录并退回相应设计步骤。

## 科学边界与交付

保留原始观测与字段，清洗/汇总/排除/抽样有明确理由与记录。行数、细胞数或技术重复不自动是独立 n；不能从汇总重建分布，不能补造检验、区间、p/q值、标尺或图像定量。复杂分析没有输入或合适方法时，交代缺口后完成可支持的部分。

交付实际可运行代码、必要输入/映射与 helper、PDF/SVG 和 PNG 预览、独立图注及关键核对结果。表格交 `.tex` 与数值。代码用相对路径，并说明实际使用的来源与修改，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [sources.json](sources.json)。已验证范围和仍需适配的能力分清，不能以自动 PASS 或一次样例宣称达到各领域顶刊水平。
