# Python 路线

将本技能的 `scripts` 加入 Python 搜索路径。基础依赖见 `requirements.txt`，不为普通数据图安装整个参考仓库。

```python
from setup_style import setup_style
from publication import save_figure
import matplotlib.pyplot as plt

setup_style(journal="general", lang="en")
fig, ax = plt.subplots(figsize=(5, 3.5), layout="constrained")
ax.plot([0, 1, 4, 10], [1.2, 1.5, 1.9, 2.0], marker="o", label="Illustrative series")
ax.set(xlabel="Time (h)", ylabel="Response (a.u.)")
ax.legend(frameon=False)
report = save_figure(fig, "output/illustrative_series", size_mm=(127, 89))
plt.close(fig)
```

数值仅为接口示例，不能当作用户实验数据。

## 接口

实质性论文图优先查看 [完整成图与例子](visual-library.md)，再选择原语。上方折线仅说明接口，不是视觉质量基准。

- `editorial.figure_style(project="project-style.json",lang="en")`：本地样式上下文；`canvas((180,147))` / `axes_mm(fig,left,top,width,height)`：最终毫米画布/绘图区。构图和导出均放在同一上下文内，确保 QA 记录实际配置。
- `estimate_column` 使用点估计及给定上下界，保留行身份/缺失；`component_matrix` 使用显式 0–1 设计；`scientific_heatmap` 需明确共享尺度，支持零中点、分组、缺失及亮度适配文字。
- `raw_groups` 保留所有点和箱线，不推断 n 的单位；`interval_trajectory` 保留坐标及给定区间，不默认拟合。统计计算由已定义分析负责。
- `research_panels.paired_changes` 按 ID 对齐两个条件，缺配对/重复默认报错；`joint_density` 的 hexbin 与边缘计数来自同一记录。`image_panel` 保留原始像素/显式裁剪及标定，`network_panel` 保留给定坐标和边权；这些接口不推断细胞、网络或统计显著性。
- 毫米布局在 `alignment_options` 指定真正可比的 `row_groups` / `column_groups`；不同证据角色可有意不等宽高并记录理由。

- `profile_data.py data.csv --group condition --id subject_id --json`；配对增加 `--pair subject_id --condition condition`。
- `setup_style(journal="general", lang="zh", use_sciplots=False, project=...)` 检测字体并设置当前执行上下文；需要局部隔离时优先使用 `figure_style` / `project_context`。命名组颜色来自 `project_style.colors_for()`。
- `save_figure(fig, basename, size_mm=(width, height), axes=[...], label_panels=True)` 组合检查。`axes` 只传可比轴；复杂布局用 `alignment_options` 明确分组/例外。
- 文件型 `source_data` 自动绑定实际源文件；`source_files={"code":"plot.py", "task":"task.json", "caption":"caption.md"}` 可补其他实际输入。内存表摘要不等于源文件核验。采用前用 `source_binding.py figure.qa.json` 只读核对已记录来源及全部导出，详见 [项目衔接](project-integration.md)。
- `export_figure(fig, basename, formats=["pdf", "svg", "png"], size_inches=(w,h))` 保留尺寸。固定尺寸不能同时 `tight=True`，灰度预览不覆盖生产 PNG。
- `publication.py figure.pdf --png figure.png --width-mm 180 --height-mm 120 --json-out figure.qa.json` 只读审查已有输出。
- `plot_templates.py paired --input paired.csv --id-col subject --condition-col condition --value-col value --output output/paired`；其他命令为 volcano、roc、dotplot、marginal，列名看各命令 `--help`。

报告区分程序结果和待完成视觉审查。读取最终 PNG 后处理警告。真实任务用真实输入；测试明确标记。

代码需在无本技能安装的机器运行时，携带所需 helper、相对输入和来源说明，不写开发机绝对 skill 路径。

## 深层资料

完整 API/配色、组合模式与教程分别见 [API](library/nature/references/api.md)、[patterns](library/nature/references/common-patterns.md)、[tutorials](library/nature/references/tutorials.md)。不要把本页短说明当作能力上限；源码预检用 scripts/preflight.py。
