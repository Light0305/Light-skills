# nature-figure 主干下的实际执行流程

默认采用 nature 的任务契约、证据组织、原生后端和实际成图核查。四库的完整实现按当前数据与问题接入；本流程不要求每次调用四套。先看数据和已有图，再决定要执行哪些步骤，小修不扩成整套项目。

## 1 研究问题与实际数据

先读 [Nature figure contract](library/nature/references/figure-contract.md)；多面板另读 [证据架构](library/nature/references/multipanel-evidence-architecture.md)。用短记录确定问题、能支持的结论/边界、统计单位、关键比较、面板各自的必要信息、后端和最终尺寸。没有结论时从待回答的问题开始，不先替数据写因果故事。

运行本包 SciPilot 适配后的 `profile_data`，保留明确的 ID、分组和配对角色。类型、偏态和离群提示是诊断，不自动建立独立 n、删除异常值、指定回归或推断检验。原始/汇总、重复测量、缺失和分母直接影响可选构造。

实际准备入口：

```text
python scripts/figure_job.py --data trace=trace.csv --spec task.json --out decision.json
```

单图 `task.json` 只需模型根据上下文写简短 question、backend 和 chart。比如实测秒信号的 chart 使用 `intent=signal,time=time_s,y=ecg_mV,sampling_hz=360,time_unit=s,signal_unit=mV`；这些是示例字段，必须映射真实输入。

多表多面板使用 `question/claims/panels`；每面板声明 source、chart、role、question，必要时写 `unique_inference`。`prepare_job()` 实际执行剖析、`plan_chart`/`plan_evidence` 与实现检索，保存字段映射和来源用途。`source_use.operation=retrieved_not_executed` 仅表示找到资料，不能写成运行证据。它不画图、不估计未提供统计量、不完成审阅。

`needs_resolution` 先处理科学阻断；`adaptation_required` 表示实现缺口；`prepared` 只表示输入与路由准备完成，不能当作成图合格。

当前新增的开发入口有明确输入边界：`count_structure` 将 `unit` 映射基因ID、`values` 映射样本计数列，并声明 `value_semantics=gene_counts,normalization=library_total_cpm,transform=log2_1plus_cpm,min_cpm,min_samples,heatmap_n`；`metadata_source` 指向同次提供的命名样本表，`sample_id` 与计数列精确一对一匹配，`annotations` 只用真实元数据字段。缺元数据不能 prepared。`two_arm_risk_evidence` 映射 `unit,label,numerator_events,numerator_non_events,comparator_events,comparator_non_events`，明确 `independent_binomial_working_model_explicit=true,confidence,effect=RR,effect_scale=ratio,reference=1,risk_scale,zero_event_policy=unavailable_no_correction`；执行真实 log-Wald RR/Wilson 风险核验，零事件 RR 不可用但绝对风险保留，零下界要求线性风险轴。`computational-sweep/confusion-counts` 委托真实 `plan_computational_chart`；这些是单项开发构造，不认证任意 PCA、浮点热图、调整/合并效应或整个领域。

`impedance` 明确映射 `spectrum,frequency,real,imaginary`，声明 `frequency_unit=Hz,impedance_unit=ohm,imaginary_convention=physical_signed`；`view=nyquist_bode/nyquist/bode` 对应真实可调用构造，保留所有象限和源行，不能自动拟合电路、删除零值或归一化面积。`trend` 的 x 必须是实际数值坐标：原始共享网格轨迹使用 `assets/paper_patterns.py:trend_lines`，供应上下界的可组合轨迹使用 `editorial.interval_trajectory`，不为原始数据补造区间。

## 2 证据与选图先于排版

单图按要回答的关系决定：估计、个体变化、分布、时间、关联、矩阵、信号、空间或其它明确构造。多面板逐项判断覆盖一个面板会失去什么推断；角色和图型名称不同不自动意味着互补。

`evidence_tools.plan_evidence(tables,spec)` 核对实际数据、选择位置、来源、依赖与独立性。它还标记同记录、相同或包含的字段、相同变换/编码，以审查矩阵旁重复原值列等问题；这只是审图线索，不能自动删掉有明确阅读用途的互补视图。`require_complementarity=true` 要求有重叠的视图声明独有信息；完全相同的记录、测量和构造不会仅凭两句不同的说明放行。不同的真实构造（例如 Nyquist 与 Bode）仍可作为互补视图进入实际审阅。

面板选择保留输入源行顺序，选择值列表表示成员而非重排。被选面板以从零连续的行索引计算摘要；`source_positions[i]` 将面板第 i 行映射回原输入的 iloc 位置，`selection_provenance` 保存原输入摘要，`field_mapping.selection` 同时保留原位置和被选数据摘要。原表及其索引不修改。

单独选图可运行 `library.py plan --data data.csv --spec chart.json --out choice.json`，据数据诊断给候选、取舍和阻断。研究目的改变时，选择应随之改变，而不只是按列类型挑模板。

## 3 找完整构造与实际实现

先 `library.py route --query "所需构造" --backend python` 或 `--backend r`。可调用入口与完整来源分开显示；即使设置较小的显示 limit，也保留覆盖混合任务所需的入口。正文里提到某图型、运行样例、UMAP 与 PCA 的名称相近，都不能认证可调用覆盖。`unimplemented_concepts` 必须处理。

然后读取实际函数和最接近的完整来源代码，并实际看其成图：

| 需求 | 可执行起点和完整资料 |
| --- | --- |
| 通用比较/配对/分布/矩阵 | 本包 `plot_templates.py`、`editorial.py`、`research_panels.py`；Nature 完整教程与 SciPilot [绘图配方](library/scipilot/references/plot_recipes.md) |
| 实测波形与时频 | `signal_plots.py`；严格时间、采样率、窗函数/重叠、密度单位与全程覆盖，见函数返回参数 |
| 生态 Hellinger-PCA | 原生 `ordination.R`；明确变换/缩放、严格ID匹配；得分图不冒充 biplot、UMAP 或显著性 |
| 原生 R 热图/随访 | `domain_plots.R` 与 [R 工作流](library/nature/references/r-workflow.md)；沿用真实 ComplexHeatmap 与 survival 结果 |
| 参数扫掠、消融、分组矩阵 | figures4papers [完整案例](library/figures4papers/references/demos.md)及实际论文脚本；如 RNAGenScape 的 plot_sweep 和 ophthal_review 的 plot_composition，按新数据改造完整输入/标度/标注 |
| 参考构造与复杂三维 | 自写[修订指南](visual-review/repair-and-preservation.md)、[排版指南](visual-review/layout-and-type.md)及按需启用的三维资料；联合本包 `field_tools.py` 的真实坐标与体数据实现 |

完整原案例可能需要改造；不要沿用项目固定数值、轴限、强制LaTeX、超大画布字体或未知统计。来源实现只在实际阅读/执行/改造后分别记用途，不能把全部库文件搬入输出。

## 4 布局、语义配色和原生绘制

先安排最终宽高、数据区域、必要短标签、共享轴、图例/色标，再定字线点。用参照学习证据顺序、面积与局部构造，不套统一皮肤：图像板、临床效应、时频与材料谱线需要不同空间安排。复杂取舍可渲染两种布局，按实际阅读比较，不靠面积公式选美。

Python `composition.compose(...).figure`/`fit()` 实测文字留位、跨行列与比例；R 用原生 ggplot/patchwork/grid。空间不足先改布局/组织，不缩字。项目 JSON 固定同组颜色与冗余编码，色标按顺序/发散/周期含义选择，偏浅文字、小点和细线在实际成图中核查。

调用 `publication.save_figure()` 或原生 `publication.R` 固定物理尺寸导出。R 经 `r_runtime.py run` 保留实际退出码；后端无关 PDF 核查可以检查 R 导出，不能以 Python 近似图代替原生 R。

## 5 实际审图、定位修订与选稿

检查当前 PNG、最终 PDF 渲染、局部、灰度和最终尺寸。技术核对查数据/ID/单位/区间/字体/裁切；视觉审阅查证据是否互补、主次、构造、拥挤、空带、颜色和查找成本。自动 PASS 不能代替看图。

复杂完整任务接入 [review-cycle.md](review-cycle.md)：

1. `review_cycle.stage_review(...)` 将当前图、PDF渲染、必要诊断和参照/明确的数据任务简报固定成审阅输入。
2. 独立上下文审阅返回带位置的问题、影响、保留项和修改方向；宿主负责明确角色与实际图片传递，脚本不认证独立性。
3. `accept_review(...)` 调用自有 `review_engine` 记录和核对实际意见；根据结果复审、绘制下一版或停止。无效审阅不算一次，不能凭空开新稿。
4. 修改代码后重新渲染，`compare_revisions()` 检查丢数据/必要构造、单位和身份变化，复核具体意见是否解决。
5. `select_iteration(...)` 保存采用理由和残留问题；不自动选最新一稿，不为凑轮次制造差稿。到预算上限仍有重要问题就记录并退回选图/布局。

数据新画采用 data-first 审阅，不能强制保持某参考图的图型。参考适配才核查约定的构造与标志。`record_review()` 只记录绑定当前文件的执行者自检，不是独立审阅。

## 6 交付与成熟度

图内保留科学标签，介绍、方法、来源与误差定义放独立图注。表格默认 `.tex` 和数值，不转图。交付实际使用的代码、相对路径输入/映射和 helper、可编辑PDF/SVG、PNG预览及必要核对，不依赖原四库位置。

说明已跑通的任务范围和仍需分析/适配之处。实际构造、来源改造、审阅与验证分别留证；一次新样例、图册数量或模型高分都不能认证整个领域或顶刊水平。
