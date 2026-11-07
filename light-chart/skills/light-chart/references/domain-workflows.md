# 领域结构：R 与复杂矩阵

这些是可组合的实现，不要求每张图都经过全部流程。来源的完整 R 指导见 [r-workflow](library/nature/references/r-workflow.md)。

## 注释热图与聚类

使用 `scripts/domain_plots.R::annotated_heatmap_r()`。输入是 `matrix[feature, sample]`，必须有唯一的行名、列名；另给一份包含样本 ID 的 metadata。helper 按 ID 显式对齐，即使 metadata 的顺序被打乱也不改变对应关系。ID 缺失、重复或不匹配直接报错。

调用方明确给出注释列、类别颜色、色标范围、零点、分组和是否聚类。helper 不筛基因、不做 z score、不插补、不填 p 值、不生成星号。聚类含 NA 时停止，要求先决定有依据的距离或缺失处理；不聚类时 NA 保留为独立颜色。默认 Euclidean/complete；任务需要其他距离时在明确说明后改造。

```r
source("scripts/publication.R", encoding = "UTF-8")
source("scripts/domain_plots.R", encoding = "UTF-8")
ht <- annotated_heatmap_r(
  expression_matrix, sample_metadata, "sample_id", c("Cohort", "Batch"),
  annotation_colors, limits = c(-3, 3), center = 0,
  cluster_rows = TRUE, cluster_columns = TRUE,
  name = "Row z score"
)
save_figure_r(ht, "figure", width_mm = 180, height_mm = 140,
  draw = function(object) ComplexHeatmap::draw(object,
    heatmap_legend_side = "right", annotation_legend_side = "right"))
```

这里的变量来自当前任务，示例范围不是允许截断的许可。数据超范围时 helper 报错，需选择合理色标或明确记录饱和方案。真正 ComplexHeatmap 对象必须 `draw()`，不能照 ggplot 直接 `print()` 后宣称成功。`publication.R` 的 `draw` 参数支持这类原生 grid 绘图。

旧模板学习记录（原文件不进入公开包）：043 的行列分块、注释轨道和符号注释的实现；038 的树与热图结构有用，但随机显著性和 44 种模块色不能带入真实任务。058 的分面曲线展示了两种不同区间同时表达，必须分清其各自含义；旧 gtable 修改较脆弱，改用任务中现有包的稳定接口更合适。

## 生存曲线与风险表

`survival_panel_r()` 接受一位独立受试者一行的右删失数据：明确的非负时间、`event=0`（删失）或 `1`（事件）、组别、唯一 ID，以及风险表时间点。不能把原始数据的 1/2 状态直接当 0/1，也不能通过 `as.numeric(factor)` 猜编码。

计算使用 `survival::survfit` 的 Kaplan–Meier 估计与 log-log Greenwood 区间；画阶梯曲线、阶梯区间和删失标记。风险表计数约定为每个时间点**事件和删失发生之前**，即 `observed time >= tick`。风险刻度不截断完整随访。原始记录有 NA 或重复 ID 时要求先处理设计和排除记录，不静默删除。

返回 `plot`、`fit`、`curve`、`risk` 和定义，图和表可一同导出，数值可复核。helper 不附加 log-rank、HR、Cox 回归或因果结论。需要延迟入组、竞争风险、加权曲线或重复/区间删失时改用相应模型；不能套进本右删失接口。

风险表是曲线的读数辅助，仍画在相同横坐标下；这与论文中应由 LaTeX 排版的独立数据表不同。不自动把曲线/风险表各当一个需要字母和介绍标题的实验面板；顶层曲线与下方风险数共享时间轴标签即可。样本数、区间定义、删失约定和数据来源放在独立图注。

## 描述性 bulk-count PCA 与连续环境颜色

Python `analyze_count_structure(..., sample_id=..., min_samples=..., heatmap_n=...)` 保留旧默认：`min_cpm=1`、`pseudocount=1`。任务声明另一规则时可给 `min_count=10, pseudocount=.5`，此时不再给 `min_cpm`；两个阈值同时出现会报错。返回 `parameters` 记录实际变换、筛选基础与阈值，全零行在原 count/CPM 中为零，变换值为 `log2(pseudocount)`，仍不进入 PCA/热图。prepare_job 的 `intent=count_structure` 对应 `transform=log2_cpm, pseudocount=.5, min_count=10`；旧 `transform=log2_1plus_cpm, min_cpm=1` 继续可用。两者均需明确 `min_samples/heatmap_n` 和原 metadata。

`pca_scores(ax, result.scores, metadata, sample_id=..., explained_variance_ratio=result.explained_variance_ratio, color='condition', colors=condition_colors, shape='pair', markers=pair_markers)` 只显示已给分数，保证横纵每个数据单位物理长度相同；颜色和形状可来自独立字段。返回 `artists[sample_id]`、原 `scores`、按 ID 对齐的 `metadata` 及 `color_handles/shape_handles`，由调用者安放图例、标签和有科学依据的配对连线，不能从样本名猜配对。长宽不同的外框不改变该单位尺度；实际数据区可能缩小，需重留物理空间并查看最终尺寸。

R `ordination_plot_r(fit, id, group, shapes=group_shapes, color_by='soil_pH', color_limits=c(4,8), color_colors=c('#A2C8BB','#17654D'), color_label='Soil pH')` 用已对齐 scores 内的连续实数 metadata 着色，shape 仍明确映射 group。例中限值仅是调用形式，必须覆盖本任务全值；常量字段需明确非零范围。连续色标默认使用项目 sequential 色，显式传色时保留任务选择；没有中心值或因果含义。不给 `color_by` 时仍使用原 `palette` 分类颜色。两种路径都保留等单位、真实 ID 和原生标签冻结；`ordination_overlap_enlargement_r()` 克隆原映射及完整色标，只放大同坐标子集，返回 `detail_plot` 供原生审图。原图 ROI 与直线 connector 保留科学坐标，在实测原生文字/marker 边界处留安全缺口，并锁定已测 overview 范围，避免注释重新训练轴后移动点与文字。实际画出的线段记录在 `decision$annotation_geometry`；缺口导致大半框线或过多边不可辨时停止，需重排或放大画布。只测量已支持的 filled marker 15:18；精确重合、多个 unresolved clusters、尺寸变更和不支持的 footprint 不因此变成可自动修复。修改物理尺寸、字体、标签、尺度或图层后须重新测量；仍需查看最终 PDF，颜色/坐标保留不等于视觉合格。

## 可运行的完整例子

`assets/examples/domains.R OUTPUT_DIR` 生成两例：`datasets::mtcars` 的注释聚类热图，及 `survival::lung` 的描述性生存/风险表。输入、变换、事件编码和绘图数值均随图导出。前者是车辆测量的结构验证，不冒充组学实验；后者是非随机、未调整的描述例，不做疗效推断。

依赖：ComplexHeatmap、circlize、survival、ggplot2、patchwork；导出另用 svglite、ragg、jsonlite。本机运行状态与实际图件检查分开记录，不能以文件存在证明 R 进程正常退出。


## 汇总分类计数与重复行为

`intent=count_table` 声明 `dimensions`（2或3个文本类别字段）、`count`、每维完整 `order`、`count_semantics=observed_counts` 与 `view=mosaic/alluvial`。源表必须每个 Cartesian 单元恰好一行，包含实际记录的零；重复、缺格、NA、负数、分数、权重和超过2**53的总数会阻断，不猜零、不汇总、不展开个体。`count_tables.prepare_count_table()` 返回原单元ID/整数边际；`conditional_proportions(..., given=[...])` 返回每格明确分母，零分母的比例为None。

`plot_mosaic(ax, prepared, colors=..., color_dimension=...)` 的二维矩形面积按 count/total，无人为间隙或最小宽；零宽类别仍在返回记录，并列于 `zero_width_categories_for_caption_or_companion`，需在图注/数值伴随表说明，不能挤叠零宽刻度。`plot_alluvial(..., relationship_semantics="joint_categories")` 支持三轴静态联合分类，每个原joint cell保留贯穿三轴的ID，返回实际节点/Bezier带端点、artist及每count高度。节点标签应据返回的原 `level` 放入排版预留处；小单元/多类别宜附数值或改用更简单视图。静态属性链不表示纵向流量、转移或因果，不能自动补CI/p值。颜色需显式给出完整类别映射，计数不是survey权重。

重复行为用 `intent=repeated_trajectory`，映射 `unit/x/y`、完整单位 `order`、科学 `x_unit/y_unit` 和 `view=small_multiples`。准备入口真实核对每条轨迹的ID、全部坐标、重复键、缺失和原行位置；不将天数当独立n，不默认首日baseline，不自动拟合模型/均线/区间。原生R打开 `scripts/repeated_measures.R`，`repeated_trajectory_r(data, unit, x, y, unit_order, x_unit, y_unit, ncol=...)` 返回 `$plot/$data/$manifest`，每unit一格、共用真实尺度，保留所有原始点。超过6条轨迹时可优先采用此构造；根据最终尺寸分批排版，不靠缩字。明确选择Python时不会冒充已实现的nativeR绘图；原两条件配对/一般轨迹接口继续可用。
