# R 路线

使用 ggplot2 / patchwork；导出依赖 svglite、ragg、jsonlite、systemfonts。以实际技能路径 `source(..., encoding="UTF-8")` 加载 `scripts/publication.R`，它通过自身位置定位审计脚本。中文源文件用 UTF-8；运行环境也应支持 UTF-8，不能为了英文日志强制 `LC_ALL=C` 后仍假定中文正确。导出后核对中文与 PDF 文字提取。

保存 `.R` 后通过 `python scripts/r_runtime.py run task.R --log output/r-runtime.json --script-args ...` 执行；不熟悉环境时先运行 `python scripts/r_runtime.py doctor`。启动器只补齐 Windows 子进程中缺失的真实 `PROCESSOR_ARCHITECTURE`，并移除不被 Windows R 识别的 `C.UTF-8` locale 拼写。正常完成必须退出 0；绘图错误、非零退出与超时仍按失败记录。不要接受“有 PDF、但进程崩溃”为通过，也不用强制终止或重装所有包掩盖问题。

`source(publication.R)` 后调用 `use_project_style("project-style.json")`。`lc_colors(c("Control","Treatment"))` 按组名读取固定色，`lc_fonts()` 返回配置与可用字体。ggplot/patchwork 的中文混排导出另需 gridtext；导出器将汉字与 Latin 拆成原生文字片段，避免 PNG 正常但 Cairo PDF 只有方框。独立 grid 标签用 `mixed_text_grob()`；自定义 draw 回调不会被偷偷替换，特殊 grid/ComplexHeatmap 中文标签需明确设置支持字体并检查实际 PDF。

加载后的接口例子，数值仅为演示：

```r
library(ggplot2)
example_data <- data.frame(time = c(0, 1, 4, 10), value = c(1.2, 1.5, 1.9, 2.0))
p <- ggplot(example_data, aes(time, value)) +
  geom_line(linewidth = 0.6, colour = "#0072B2") +
  geom_point(size = 1.8, colour = "#0072B2") +
  labs(x = "Time (h)", y = "Response (a.u.)") + theme_light_chart()
save_figure_r(p, "output/illustrative_series", width_mm = 127, height_mm = 89)
```

- `theme_light_chart(lang="zh")` 使用项目字号和 Latin 主字体；导出阶段为汉字采用配置的 CJK 字体。图面数字保留 Latin 字体。
- `save_figure_r` 在 R 输出 PDF/SVG/PNG，可选择 TIFF；宽高用 mm，DPI 只影响栅格。
- patchwork 先测最终面板几何；`alignment_options` 可传审计参数与有理由的例外。
- 优先扁平组合：四面板用 `p1+p2+p3+p4+plot_layout(ncol=2)`；跨行用 `p1+p2+p3+plot_layout(design="AC\nBC")`。嵌套组合可能不对齐，不能以嵌套结构本身证明面板相等。
- 嵌套图需通过 `alignment_options=list(design=matrix(c("a","b","c","d"),2,byrow=TRUE))` 声明布局，或显式给比较组。ID 按绘制顺序对应实际数据面板，跨行例子的设计矩阵为 `matrix(c("a","c","b","c"),2,byrow=TRUE)`。测量来自实际 viewport，设计矩阵只说明哪些边应对齐。
- Cairo 有不足 1 pt 的页面取整时，共享检查工具只校正页面框并保持内容相对于左上角的位置，不缩放数据或字体；校正前后尺寸写入 QA。差异超过 1 pt 时拒绝自动校正。
- 图例、inset、固定比例轴或特殊跨行布局需检查所测面板是否对应绘图区。
- Python 负责上述页面框校正、PDF 和 R 布局 JSON 检查，不重画数据或替代 R 图件。缺审计环境记录 `NOT_AUDITABLE`。
- R 或包缺失时可准备 R 代码并报告缺项，不用 Python 近似图冒充。

旧模板保留有用处理/图层，分离无关路径和项目数据，统一最终尺寸、输出与相关检查。

## 深层资料

## 原生修订比较

保存时传 `review_plots=list(response=p, endpoint=q)` 与 `source_files=c(raw="data.csv")`；必须是实际导出的组件 ggplot，不能传整张 patchwork 冒充单面板。review_tools.R 从 ggplot_build 提取每个 facet 的真实绘图层、位置、分组、统计字段、尺度和颜色/符号/线型映射，原文件绑定 SHA-256。Python compare_revisions() 检查层删除、坐标/区间变化、身份变化与显示范围变化；audit_marks_r() 检查坐标裁切。改色等有意修改逐项说明，不能用理由豁免缺失数据或文件变更。

`source_files` 也可列实际绘图代码、配置和图注，名称须唯一。清单在绘制前记录绝对路径/字节/哈希，导出后检查变更；数据在出图中被改动或删除会失败。SVG 和可选 TIFF 也进入导出绑定。采用前用 `python scripts/source_binding.py figure.qa.json` 只读复核，旧的无路径清单不补造来源；边界见 [项目衔接](project-integration.md)。

当 `source_files` 同时包含数据和代码等材料时，传 `data_sources=c("raw")` 明确数据条目名称；数据签名只比较这些原文件，代码仍绑定各自修订。未指定时沿用保守的全来源签名；不自动从扩展名猜数据角色，也不为通过比较而删掉不利的数据源。

lc_native_text() 现在按实际 glyph index 检查非 ASCII 文字，科学上下标/负号缺字时选择已安装且包含该字形的回退字体，而不是假定 Arial 全部支持。它适用于 ggplot/grid 文字 grob；自定义绘制回调需要自行接入并查看 PNG 和 PDF。数学 plotmath 的缩小字号和轮廓另检；可用原生 Unicode 保留正常文字大小。

完整运行例为 assets/examples/advanced_tasks.py 与同名 .R：使用原生 R CO2 的 84 条记录/12 株植物，保留正常修订、删层和错误裁切三个比较结果。grid/ComplexHeatmap 等自定义回调暂不提供通用的原生绘图层比较，不以成功导出代替此能力。

完整领域路线见 [R workflow](library/nature/references/r-workflow.md) 和 [domain workflows](domain-workflows.md)。ComplexHeatmap/grid 使用 publication.R 的 draw 回调，不能只 print 后假定导出成功。
