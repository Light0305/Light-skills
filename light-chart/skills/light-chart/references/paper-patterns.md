# 论文绘图范例的改造

`assets/paper_patterns.py` 从 figures4papers 的选定实现改造，参数替换论文数据，使用真实坐标与最终尺寸。函数只返回 Figure/Axes，导出/检查交给 `publication.save_figure`。

| 函数 | 来源 | 保留与修正 |
| --- | --- | --- |
| `comparison_bars` | ImmunoStruct `plot_bars.py` | 方法比较、给定误差与独立图例；去固定数据、截断轴和超大字号 |
| `trend_lines` | VIGIL `plot_posttraining.py` | 方法配色、线/点和可选区间；x 使用真实间隔 |
| `annotated_heatmap` | ophthalmology review `plot_composition.py` | 矩阵、色标与格内标注；不修改调用方标签、不依赖 LaTeX、明确缺失 |

`comparison_bars(methods, metrics, values, errors=None)` 的矩阵是“方法 × 指标”，误差定义由输入方提供。`trend_lines(x, values, labels, lower=None, upper=None)` 的矩阵是“曲线 × x”，区间须成对提供。`annotated_heatmap(values, row_labels, column_labels)` 显示原矩阵，不隐式归一化/聚类。

这些不是默认图型。需要分布时不能只画汇总柱，需要配对时保留配对。条款/署名见 `THIRD_PARTY_NOTICES.md`；其余范例按需求逐个迁入，不复制重复副本。
