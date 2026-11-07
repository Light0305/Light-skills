# 深层资源与任务路由

先读 [workflow.md](workflow.md) 和 [source-adaptation.md](source-adaptation.md)。按任务阶段选择完整资料；每套来源均可贡献选图、设计、实现、修订和检查，不分成四个固定职责。不要同时加载所有文档。

## 按实际任务选择来源与自有指南

- nature-figure：问题与证据、领域图型、视觉设计、Python/R 实现、图像与定量组合、统计图注、导出与实际成图检查。
- SciPilot：[剖析](library/scipilot/references/data_profiling.md)、[图型](library/scipilot/references/chart_selection.md)、[十类绘制配方](library/scipilot/references/plot_recipes.md)、[语义问题](library/scipilot/references/viz_pitfalls.md)、[实际读图](library/scipilot/references/visual_review.md)、[交付检查](library/scipilot/references/publication_checklist.md)及本包适配的样式/布局/导出/检查工具；不限于诊断选图。
- Light-Science 自有视觉审阅：[输入整理](visual-review/comparison.md)、[绘制与构造](visual-review/repair-and-preservation.md)、[设计细节](visual-review/layout-and-type.md)、[保留项与判断](visual-review/reviewer-contract.md)、[三维体系](visual-review/three-d/route.md)和反馈工具；无用户参考时也能支持布局、实现和检查。
- figures4papers：[设计论述](library/figures4papers/references/design-theory.md)、[API 与验证](library/figures4papers/references/api.md)、[组合模式](library/figures4papers/references/common-patterns.md)、[完整教程](library/figures4papers/references/tutorials.md)、[案例入口](library/figures4papers/references/demos.md)和下方完整论文脚本；不限于代码素材。

## 选图、证据与多模态

- 数据与表达意图：[SciPilot 选图](library/scipilot/references/chart_selection.md)、[剖析解读](library/scipilot/references/data_profiling.md)、[18 类常见问题](library/scipilot/references/viz_pitfalls.md)。按适配规则修正绝对阈值和自动统计建议。
- 开始一张科研图：[figure contract](library/nature/references/figure-contract.md)、[证据架构](library/nature/references/multipanel-evidence-architecture.md)。写科学问题、最关键比较、可推翻解释和面板必要性；不为填满版面凑面板。
- 全文多图：[Results–Discussion](library/shared/core/nature-results-discussion.md)、[术语记录](library/shared/core/terminology-ledger.md)、[一致性](library/shared/core/consistency-sweep.md)。检查一套图是否只是重复排名，是否真正增加一般性、机制或边界证据。
- 图型和领域：[chart-types](library/nature/references/chart-types.md)、[完整设计论述](library/nature/references/design-theory.md)、[16 类组合模式](library/nature/references/common-patterns.md)。支持示意引导、图像板+定量、临床三联、非对称主面板，不强迫等大的网格。
- 图像板：读取 [common-patterns 的图像板组合](library/nature/references/common-patterns.md)、[图像/医学/材料实例](library/nature/assets/gallery/fig2-spatial-imaging-rich.png)，实际像素接口是 `research_panels.image_panel`。有物理标定才画物理比例尺；未知时可明确使用 px。跨条件处理一致、标注裁剪/通道，不以截图替换原数据。

## Python 与 R 的具体做法

- Python：[API 与调色板](library/nature/references/api.md)、[完整教程](library/nature/references/tutorials.md)、[SciPilot 十类配方](library/scipilot/references/plot_recipes.md)。代码块中演示值/模拟数据不能原样带入真实结果。
- R：[完整 R 路线](library/nature/references/r-workflow.md)、[领域模板路由](library/nature/references/r-template-index.md)。包括 ggplot2、patchwork、ComplexHeatmap/grid、survival、circlize/ggtree 等，按实际任务核对依赖与输入。
- 新增可运行的 R 入口：`scripts/domain_plots.R` 的 `annotated_heatmap_r()` 和 `survival_panel_r()`，见 [domain-workflows.md](domain-workflows.md)。前者是真正 ComplexHeatmap/grid 导出，后者是事件/删失数据与风险表，不能用普通折线冒充。
- 图表数据表：`scripts/table_tools.py::to_latex()` 默认交原生 booktabs 表格，保留数值/显示字符串分离、逐列方向、并列最优、分组表头和 NA。见 [tables.md](tables.md)，不把论文表格转成图片。
- 连续场与三维：`scripts/field_tools.py` 读取不规则坐标间距、缺失域和显式色标；不能把矩阵索引当真实坐标。见 [fields-and-3d.md](fields-and-3d.md)。

## 完整论文脚本和成图

`assets/library/implementations.json` 索引实际函数与输入边界，`catalog.json` 索引完整源脚本、可用数据状态与原图候选。先用 `python scripts/library.py route --query "消融"` 定位可调用函数及相关来源；找完整原实现可用 `search --query "surface" --kind source-pattern`。路由不执行源代码，也不把概念指导算成已验证模板。

| 结构 | 首选来源案例 | 借用重点 |
| --- | --- | --- |
| 跨数据集 × 多指标 | Cflows / CellSpliceNet | 分组槽位、共享图例、真实单位和科学计数法 |
| 跨类别/子类别对照 | BrainTeaser | 层级分组、密集小倍图、不同填充语义 |
| 组件消融 | ImmunoStruct / CellSpliceNet | 组件组合、主模型与消融的关系、与变异数据对应 |
| 混合指标尺度热图 | RNAGenScape | 行组与任务组、数值标注、指标方向、尺度分离 |
| 时间累计构成 | ophthal_review | 真实日期间距、累计底边、事件标注与留位 |
| 参数扫掠与训练过程 | VIGIL / RNAGenScape | 实际 x 网格、多指标、事件/基线与图例 |
| 非对称频谱比较 | FPGM | 2×2 局部 + 跨列主图 + 汇总/对照；原 NPZ 缺失时仅作结构参考 |
| 真三维流形或概念几何 | RNAGenScape / Dispersion | 曲面拓扑、缺失域、视角、占据率；区分概念示意与实测场 |

完整脚本中的 `raw_data.py` 随对应目录保留；只有源数据数组不等于有独立样本或统计检验。原图候选可能由同目录其他脚本生成，需核对文件名、轴和数据，不能任取一个作精确对照。

## 参考图、局部修订与三维

- 领域完整图：`python scripts/library.py search --kind visual-reference --query "materials impedance frequency origin zoom"` 返回实际图、来源、布局分析和限制；按本任务领域、证据角色与构造替换查询。`absolute_preview_path` 为空的 link-only 条目应打开 `figure_url`，不能当作随包图片；反例另标且不计可调用实现。
- [排版与文字指南](visual-review/layout-and-type.md)：字体家族、发丝线、紧凑度、图级/面板级比例、图例内部密度。按视觉类别而非脆弱的像素小数选参数。
- [绘制细则](visual-review/repair-and-preservation.md)与[审图细则](visual-review/reviewer-contract.md)：先列构造、标志元素和局部坐标侧，再对照最终渲染；将已经正确的地方列入保留项，一次优先修少数实质问题。
- [三维入口](visual-review/three-d/route.md)：区分用户数据的风格适配与明确要求的复刻；按子类读取曲面、轨迹、体域、照明、候选比较。几何和数据的科学含义优先。

## 最终图与图注

[完整 QA 合约](library/nature/references/qa-contract.md)、[图注](library/nature/references/figure-legend-conventions.md)、[SciPilot 实际审图](library/scipilot/references/visual_review.md)。对每个面板逐一查样本单位、估计量、变异、样本数、标签、图例和独立证据作用。`scripts/preflight.py` 只是绘制前的提示，`publication.py/.R` 检查实际导出，两者不能取代读图。

本包 atlas 与 rich gallery 是源库的结构练习/示例，未独立确认为发表论文图，也不应称为“顶刊质量标准”。以实际数据、适合的参考和成图判断。
