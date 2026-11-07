# 视觉库：原图与可运行的重设计

这些是供选择和批判的范例，不是统一“顶刊模板”。论文原图来自用户提供的 figures4papers；方法比较、消融与矩阵保留其数值。原生 R 例子使用公开内置数据，解析场和模拟组合图明确作演示。预览已更新为稿件图面，长说明单独输出。来源条款见 notices。

常用图型的完整可运行图册入口为 `assets/examples/gallery.py` 和 `gallery.R`。先运行 `python assets/examples/gallery.py --out output/atlas --native-r --rscript PATH` 导出 R 内置数据与三类原生 R 图，再运行 `python assets/examples/gallery.py --out output/atlas`，生成分类阅览页、缩略总览和 PDF/SVG/PNG。基础图用于检查构造，不能当独立科研任务验证；Iris、faithful、配对/纵向数据与真实留出预测都有字段和计算输出。`--only 14,21` 可修订指定图型；`--task-root` 是可选的开发案例汇入，缺少历史任务目录时不影响基础图和原生 R 图。表格不计入图数。尚未适配的来源配方不算已运行覆盖。

| 任务 | 实际查看 | 完整运行入口 | 可迁移设计 |
| --- | --- | --- | --- |
| 多方法、多指标、已有误差 | [原复合图](../assets/visual-library/source_immunostruct.png) 和 [估计值比较](../assets/visual-library/01_method_comparison.png) | `assets/examples/benchmark.py` 的 `method_comparison` | 共享方法顺序、直接行名、等宽指标、克制区分重点与对照 |
| 消融、组件开关、敏感性 | [组件与结果](../assets/visual-library/02_component_ablation.png) | 同入口 `ablation` | 组件/结果共享行；所有变体可见；保留超参数坐标含义 |
| 多任务数字矩阵 | [原图](../assets/visual-library/source_rnagenscape.png) 和 [重设计](../assets/visual-library/03_structured_heatmap.png) | 同入口 `rna_matrix` | 两级表头、方法族分隔、共享科学尺度、方向说明 |
| 注释、分块、聚类 | [原生 R 注释热图](../assets/visual-library/05_native_R_annotated_heatmap.png) | `assets/examples/domains.R` | 树/矩阵/注释同步、仅保留新增信息的轨道、色标与分类图例各司其职 |
| 事件与删失 | [生存曲线与风险表](../assets/visual-library/06_native_R_survival_risk.png) | 同入口 | 原生阶梯区间、删失标记、共享时间坐标与在险人数；不加重复编号与解释横幅 |
| 连续场、三维形状 | [同一解析场](../assets/visual-library/08_quantitative_field.png) | `assets/examples/fields_and_tables.py` | 真实坐标间距、同色标、缺失域保留；二维辅助读三维遮挡 |
| 趋势、原始点、效应、矩阵共存 | [模拟实验组合图](../assets/visual-library/04_experimental_evidence.png) | `assets/examples/experimental.py` | 主要证据跨列、跨面板同色、个体/群体分层、保留零效应边界 |

没有组件设计就不要发明组件；没有原始观测就不能套原始点；一个问题不硬凑六面板。完整示例应按数据结构改造。

## 原图哪些值得保留

**ImmunoStruct**：复合图将方法验证、消融、代表性结构和实验比较组织在一页，视觉语言统一。可迁移的是证据角色和紧凑对齐。源比较柱采用非零基线，本包用点/区间呈现同样的汇总值；不能盲抄截断柱轴。蛋白结构、实验图像属于源研究，不能当新项目的证据或装饰。

**RNAGenScape**：保留所有方法、多任务矩阵、同族排序与重点行。+/− 是目标方向，不是显著性；两矩阵量纲不同。本包保留 13 个方法、六任务、全部源数值，采用共享的零中心/0–100% 尺度，不推断误差。

**nature-figure 图库**：图像板、空间校准、混合模态、非对称版式和定量层次可参考；完整图型、Python/R、配色、统计表达、图注和检查也参与任务。部分本地演示有标注重叠、粗糙示意素材和过大标题，应具体纠正，不能因名称中有 Nature 就全库照搬。

**获许可来源与自有审图资源**：SciPilot、figures4papers 和 nature 的资源按 [workflow.md](workflow.md) 使用；[自写指南](visual-review/overview.md)与十组合成示例支持排版、三维与修订练习。FigMirror 的概念启发保留署名，原文件不在公开包中。参考仍需筛选，例如带大幅全局标题的展示图不能照搬为稿件图面。

## 复现与数据边界

从技能根目录运行：

```text
python assets/examples/benchmark.py --out output/reported_benchmarks
python assets/examples/experimental.py --out output/simulated_design
Rscript assets/examples/domains.R output/native_R
python assets/examples/fields_and_tables.py --output output/field_and_native_table
```

JSON 输入随包提供，附来源文件哈希与条款；不依赖开发机参考仓库。输出 PDF、可编辑 SVG、450 dpi PNG、灰度、技术 QA 与图注。示例画布、布局和原语参数可改。

方法/消融的完整输入 JSON 随输出导出，矩阵另交精确值 CSV。数字不必每格都印在图内，仍能复核。表格入口仅输出 `.tex`、CSV 和独立表注，不提供表格图片。R 依赖与执行状态需在实际环境检查；仅生成文件不等于进程干净退出。

`immunostruct.json` 的均值和误差来自源仓库；`std` 不可统称置信区间，Mean PPVn 的源误差已除以 √5。Cancer AUROC 有并列，不得称全部指标独胜。

`rnagenscape.json` 提取原脚本顶层字面量数组，不运行原绘图副作用。`experimental.py` 输出 SIMULATED_DATA、生成种子、所有受试单位及统计定义；生物学名称仅用于设计演示。

真实项目替换全部输入和统计定义，更新图注、单位，再看图修订。不能把模拟趋势或源论文结果遗留在用户图内。
