# 论文表格：优先 LaTeX

精确查值、多指标单位不兼容或比较文字属性时可用表格。论文任务默认交付 `.tex` 和 CSV/结构化数值，由稿件管理表号、caption、字体与浮动位置；不把表格绘成图来展示“绘图能力”。只有明确用于幻灯片、图片表格等场景时再使用渲染接口。

## 原生输出

`scripts/table_tools.py::to_latex(rows, columns, spanners=..., section_starts=..., rank=...)` 返回 `booktabs` 的 `tabular` 片段，不强加 float、caption、字号、缩放盒或固定宽度。稿件加载 `\usepackage{booktabs}` 后用 `\input{table.tex}` 引入。宽表先调整列组织或由稿件选择跨栏，不默认 `\resizebox` 把整表压小。

- `Column.key` 指向原始数值；`display_key` 可指向调用方提供的“均值 ± 源误差”等显示文本。排名看原值，不能从舍入后的显示文本倒推统计。
- 每列方向明确声明 `better='min'/'max'`，不猜列名。`rank=True` 只强调数值最优，不表示统计显著。默认只将完全相等的原值视为并列；研究约定需要容差时显式给 `tie_atol`。
- `None`/NaN 保持缺失，默认破折号；说明未测、未报告或不适用的实际含义。不以零代替，无穷值报错。
- `spanners=(名称, 起始列, 结束列)` 生成 `\multicolumn` / `\cmidrule`；结束列不包含，分组不得重叠。`section_starts` 控制适量分组间距。
- 文本转义 `% & _ # $ { }` 等 TeX 特殊字符；显示字符串当文字处理，不自动执行任意 LaTeX。示例中的 ±/方向箭头转换成可编译的数学命令。
- 数值的小数位、有效数字、单位、正负号、百分号和缩写逐列一致。`Column.width` 是可选绘制接口的宽度提示，原生 LaTeX 不据此强制列宽。

`assets/examples/fields_and_tables.py` 输出 `07_method_comparison.tex`、CSV、映射及独立表注，不输出表格图片。数据来自 ImmunoStruct 原均值/误差数组；保留两评估集、三个指标、全部方法与缺失。Mean PPVn 的源 `std` 已除以 √5，不能把全表统一标成 SD；Cancer AUROC 的两个 0.771 精确并列。

该宽表示例在 180 mm 稿件宽度、9 pt 正文字体下，可由稿件局部设 `\setlength{\tabcolsep}{4pt}` 安排列间距，编译后检查 overfull 和可读性。该设置不写死在表格片段中；实际稿件较窄时应重新组织表头、分表或跨栏，不能假定任何文档都能直接塞入。

## 只有明确需要图片表格时

`scientific_table()` / `require_table_fit()` 保留为特殊用途接口。后者检查实际渲染的文字是否越界/碰撞；不能把此检查代替 LaTeX 成品检查。默认无竖网格、不为塞一页强行缩字。

辅助参考的用途见 [curated-lessons.md](curated-lessons.md)：借表头层级、分组与数值组织，不复制截图像素，不从截图编造精确数据。
