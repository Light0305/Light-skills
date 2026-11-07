# 多面板与证据组织

确定组合图服务的阅读问题和 panel 作用。Results 图可用“主证据 → 对照 → 正交验证 → 机制/边界”组织；探索、报告和方法比较不必强套该叙事。

同一结果的多种指标有时有价值，但不能用换指标代替互补证据。按阅读需要分配主面板、解释面板与补充图，不将每张输入表机械变为一张 Figure。

## 互补证据角色

选择能改变本图推断的角色：问题/设置、主要定量证据、可信对照、分解、分层、正交测量、扰动、失败边界或机制约束。不必凑齐；遮住某面板若不损失独特信息，考虑合并或转到补充材料。

可用证据链：定义能力→建立效果→攻击不同失败模式→边界；总体分布→定量→内部结构→代表性例外；主要表现→跨条件→代价→更困难情景。按科学问题选择，不能照抄面板字母和数量。

决定性证据占主位置/面积。同一色、分母、统计量和类别顺序贯穿可比面板。对照安静但清楚，不能淡到难以审查；负结果和失败边界不为排版隐去。

完整示例见 [visual-library.md](visual-library.md)。架构来自给定 nature-figure/nature-shared 指导，不是官方 Nature 投稿规则。

- 同变量保持颜色、符号、量纲和分类顺序；共享尺度按科学可比性决定。
- 等跨度可比面板用等绘图区，不仅是纸面外框相等。
- 支持网格、跨行和不等跨度。刻意不等宽记录原因，不放宽全局容差隐藏错位。
- 图例、colorbar、inset、twin axis 明确处理；复杂图显式传比较 `axes`。
- 标签按实际坐标统一放置，最终尺寸核对并检查边距裁切。

`require_matplotlib_panel_alignment` / `require_patchwork_panel_alignment` 默认物理容差 1.5 pt，属于技术默认值，不是期刊普适规定。可靠错位修复后重导出；不可审查说明原因。几何一致不证明科学可比，仍看各 panel 的误差、n、尺度和含义。

R 的 `null` 布局单位必须在实际设备的 viewport 中解析；不能直接累计未解析的 gtable 宽高。嵌套 patchwork 需声明设计矩阵或比较组，见 [R 路线](r.md)。固定比例、facet、inset 等复杂布局必须核对所测矩形是否覆盖真正的数据区，不能把外层框的通过当作全部子图通过。

## 执行证据契约与布局

`evidence_tools.plan_evidence(tables, spec)` 的 `tables` 是命名 DataFrame/CSV；`spec` 包含 question、claims 与 panels。每个 claim 可声明 required_roles 和 boundary；每个 panel 声明 id/source/claim/role/question/chart，chart 使用选图接口的字段语义。select 是字段到允许值列表，完整保存源行位置；depends_on 决定阅读依赖并拒绝循环。程序返回真实数据的选图阻断、来源哈希、覆盖与警报，不从列名猜科学结论。

`independence={"from":"另一面板ID","key":"受试者ID"}` 检查实际 ID 交集，重叠不能冒充独立验证；ID 不重叠仍不能证明独立研究或正交测量。同表同记录的第二视图会提示重复证据。`audit_evidence_layout(plan, composition.fit())` 检查必需面板和 min_area_mm2，不拿均匀网格代替证据判断。

经 `study_data` 汇总或合并的表还检查原始记录交集；不同表名、不同汇总行标签不能绕过。只检查派生来源时可用 `independence={"from":"另一面板ID"}`，不会据此认定不同患者。复杂任务实际比较适用的构造：同一比例矩阵有利于总览，点区间有利于判断精度；保留会改变主结论的边界，辅助分布与全字段诊断可移至补充图。完整可运行任务见 `assets/examples/multicentre.py`（来源下载需显式 --download）。

`composition.compose()` 支持跨行/列、逐面板 min_plot_mm、plot_aspect、3d projection。色标等辅助轴可用 panel_label=false；不把色标计为新的证据面板。image_layout 的 image_plate 按原图/ROI 比例创建布局；equal_pixel_group 表示采集图按相同物理 mm/源像素显示，局部放大则保留各自标尺。空间不足抛出 LayoutError 后改画布/布局，不缩字掩盖。

完整证据推理和必要性审计见 [multipanel evidence architecture](library/nature/references/multipanel-evidence-architecture.md)；复杂任务应读取原文，不能仅按图型数量排网格。
