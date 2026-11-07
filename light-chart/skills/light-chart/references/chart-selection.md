# 数据、图型与适配

## 先判断结构

字段类型、行级观测和科学单位分别确认。数字 ID 不参与连续变量相关分析；几个整数不证明是有序量表。`profile_data(source, group_cols, id_cols=..., column_types=..., pair_col=..., condition_col=...)` 可覆盖启发式类型并报告配对缺项。

## 执行选图与检索

先从研究语境确定角色，再用 `library.plan(data, spec)` 或 `library.py plan --data data.csv --spec task.json --out decision.json`。例如配对任务的 spec：

```json
{"intent":"change","unit":"subject","condition":"visit","y":"response","order":["Before","After"],"backend":"python"}
```

`intent` 支持 compare/change/distribution/association/trend/estimates/matrix/survival/proportion/table；用 x/y/group/unit/condition/lower/upper/time/event 指定实际字段，矩阵用 values 列表。`data_level` 为 raw 或 summary，trend 或超过两个条件的连续轨迹需有科学依据的 ordered；数值条件编码不自动证明连续性。survival 的 event 明确为 0/1，只覆盖普通右删失。

结果返回候选及取舍、排除的表达、真实记录诊断和对应来源/函数。重复单位、重复 ID-condition、缺失配对、错误区间等可阻断推荐；默认不排除记录。确已决定完整案例分析才设 `missing:"complete_cases"`，按返回 row_positions 选取并报告 excluded_rows；矩阵缺失可设 `missing:"display"` 保留空单元。`reference.required_elements` 中的 marginals 会参与联合图选择，完整签名还须看原图并在审图中核对。

矩阵混合不同数量/单位时，用 `value_groups:{"change":{"columns":["delta"],"limits":[-3,3]},"fraction":{"columns":["percent"],"limits":[0,100]}}` 明确分组，返回 multi-scale-heatmaps 并检查声明范围是否截断实际值。每个值列恰好出现一次；分组来自科学含义，不从数值大小猜单位。未声明量纲时会提示核对色标可比性，不自动归一化。

候选顺序是有理由的启发式，不是统计置信度。ECDF 等标明 adapt_source 的候选仍需适配原实现；命中相邻函数不等于已实现该候选。整套论文的证据角色和科学主次继续结合完整来源判断。

## 二元比例与多来源汇总

`intent:"proportion"` 要求 event/group/unit，可用 condition 声明交叉分层。实际分子、分母和重复记录参与诊断；缺失结局不能变为阴性。区间图与比例矩阵的取舍取决于精度是否影响阅读；小分层不能只靠颜色浓淡表达确定性。

`study_data.combine_cohorts(tables)` 只合并同结构表，保留每条记录的原始位置；自动 record_id 是追踪标签，不是经过验证的患者身份。`missingness_summary(tables, columns)` 分开报告 NA、记录零值和明确字段集合的完整案例数，不猜零是否为缺失码。

```python
from study_data import combine_cohorts, binomial_estimates, save_study_table
data = combine_cohorts(tables)
estimates, report = binomial_estimates(data, event="positive", unit="record_id",
    groups=["cohort", "condition"], levels={"cohort": ["A", "B"], "condition": ["x", "y"]},
    interval="wilson", confidence=.95, missing="resolve")
save_study_table(estimates, "fractions.csv")
```

完整 levels 保留空单元：n=0 的比例和区间为缺失，不变为 0%。默认遇到缺失结局/分组阻断；明确选择 exclude 才返回排除位置。Wilson 模型假定独立 Bernoulli 记录，科学适用性须先判断；不能用于未处理的重复测量，不自动推断因果或人群患病率。公式参见 [NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)。

派生结果带原始记录来源；`grouped_lineage(source, result, by=[...], operation="...")` 可为调用者计算的组表绑定贡献记录，只验证归属、不验证运算。`save_study_table()` 同时保存 CSV/TSV 与 `.lineage.json`；`chart_plan.read_data()` 和选图 CLI 重读时核对文件字节、解析结果与来源。CSV 需与旁文件一起携带；裸 CSV 不能恢复丢失的来源。未记录的 DataFrame 编辑导致来源失效，需重新从原始数据推导。

| 目的 | 常用表达 | 确认 |
| --- | --- | --- |
| 组间差异 | 原始点、点区间、箱线/小提琴；有依据时用汇总柱 | 独立重复、分布、n、误差 |
| 同一对象前后变化 | 配对连线、差值点、区间 | ID、重复对象、缺失配对 |
| 连续趋势 | 实际坐标上的线、点和给定区间 | 时间间隔、排序、区间来源 |
| 变量关系 | 散点、hexbin、二维密度 | 单位、缺失、过绘；拟合需依据 |
| 构成或计数 | 排序条形、堆叠/百分比堆叠 | 分母、总量、缺失类别 |
| 矩阵 | 热图、注释矩阵 | 值域、标准化、聚类、缺失 |
| 模型性能 | ROC/PR、校准、混淆矩阵、配对比较 | 数据分割、重复、基线和指标 |

## 冲突裁决

- 小样本优先实际观测。箱线和密度是否有意义取决于数据，不用 n=10/30 当普遍许可或禁令。
- 汇总均值 + SD/SEM/CI 可以作图，不能伪造原始点；图注明确误差定义。
- 趋势使用真实 x 间隔；分类连线只在顺序或匹配关系有意义时使用。
- 柱高等长度编码通常从零开始。突出小差异可用点区间、差值或明确说明的坐标设置，不照搬任意截断。
- 双轴、3D、雷达或饼图按数据和阅读任务判断，不机械禁止，也不为装饰引入。
- 配对不能转为独立样本比较。不完整配对先报告；排除需规则和前后计数。
- 大数据优先透明、栅格化、hexbin 或说明规则的汇总，不静默抽样。

模板按科学含义、形状、尺度和变换匹配：精确复用、结构适配或仅继承样式。缺少参考图维度时解释并修改编码，不能伪造或删除观测来满足模板。
