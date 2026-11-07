> 来源文档，按需查阅；执行规则以本包 SKILL.md 和 references/source-adaptation.md 为准。旧版期刊数值、强制提问、多代理和自动统计建议不直接生效。

# 数据剖析报告解读手册

`scripts/profile_data.py` 跑完输出一份 markdown 报告。本文档讲：**怎么读这份报告 + 怎么把每一条事实翻译成画图决策**。

## 目录

- [一份报告长什么样](#一份报告长什么样)
- [列类型识别规则](#列类型识别规则)
- [样本量的影响](#样本量的影响)
- [分布形态的影响](#分布形态的影响)
- [分组结构的影响](#分组结构的影响)
- [相关性 / 多重共线性的提示](#相关性--多重共线性的提示)
- [缺失值与异常值](#缺失值与异常值)
- [从报告到画图决策的流程](#从报告到画图决策的流程)

---

## 一份报告长什么样

跑：

```bash
python scripts/profile_data.py results.csv --group group --group condition
```

输出有四个核心区块：

1. **Columns** — 每列的类型、样本量、缺失率、关键统计
2. **Group structure** — 分组样本量的最小/中位/最大
3. **Correlations** — 数值列之间的 Pearson r（按 |r| 排序）
4. **Warnings + Chart suggestions** — 自动提示与初步图型建议

下面逐区讲怎么读。

---

## 列类型识别规则

`profile_data.py` 把列分成 6 种类型：

| 类型 | 识别规则 | 画图含义 |
|---|---|---|
| `continuous` | numeric dtype，唯一值 > 7 或包含小数 | y 轴默认走它；做散点、折线、箱线 |
| `ordinal` | numeric dtype，唯一整数值 ≤ 7（如 Likert 1-5）| 横轴可走，但**别连折线**（除非确定有序） |
| `categorical` | object 或 categorical dtype，唯一值 ≤ 30 且类别比 < 0.5 | x 轴 / hue 走它 |
| `boolean` | bool dtype 或全 0/1 | 拆成 2 组对比 |
| `datetime` | datetime dtype，或前 10 个非空值可解析为日期 | 时间轴；折线首选 x |
| `text` | object dtype，唯一值多到不像分类 | 一般是 ID/笔记类，**不画** |

**坑**：列类型自动识别有时会错。常见误判：

- 实验编号是数字（如 1-10），被认成 ordinal，**但你想当分类**。手动 `df['expt_id'] = df['expt_id'].astype(str)`
- 类别标签是数字（0=control, 1=drug A, 2=drug B）会被认成 ordinal。手动转 str
- 时间被存成字符串（"2024-01-01"），自动识别没问题，但**不要**当 categorical 用

跑完报告后**先看类型识别对不对**，错了立刻在数据里改类型再重跑。

---

## 样本量的影响

`Columns` 区显示每列实际可用样本数（去除缺失）。`Group structure` 区显示每组样本数。

### 阈值

| 每组 n | 该用什么图 | **不能**用什么图 |
|---|---|---|
| n < 3 | **直接列每个点**（dot plot） | 均值柱状、箱线、小提琴（统计估计无意义） |
| 3 ≤ n < 10 | stripplot / 蜂巢散点 / dot plot | 均值柱状（掩盖太多）；箱线慎用（四分位不可靠） |
| 10 ≤ n < 30 | **箱线 + 叠加 stripplot** | 仅画均值柱状（**严禁**） |
| n ≥ 30 | 箱线 / 小提琴 / 带误差柱 都可 | — |

### 为什么阈值这么定

- n=3 时，"箱线"的四分位只有 1 个点撑——所谓"中位数"就是中间那一个，所谓"分位"完全没意义
- n=5 的均值标准误 ≈ SD/√5 = SD×0.45，**置信区间几乎和原始分布一样宽**——画误差棒图反而误导
- n<10 不画原始点 = 把数据信息扔掉一半，审稿人直接质疑

### 报告里的小样本警告

```
- **WARN**: at least one group has n<10 — use box/violin + stripplot
  rather than mean-only bar chart.
```

看到这条 → 立刻把图型从"均值柱"切到"箱线 + stripplot"。

---

## 分布形态的影响

`Columns` 区给出每个连续变量的：

```
mean=35.2, sd=129, range=[0.9, 500], skew=3.13 (highly skewed); outliers=3 (IQR); -> log axis
```

### 偏度（skew）

| skew | 含义 | 决策 |
|---|---|---|
| \|skew\| < 0.5 | 大致对称 | 均值 ± SD 可信；箱线、小提琴都合适 |
| 0.5 ≤ \|skew\| < 1 | 中度偏 | 优先**中位数 ± IQR**；柱状图改箱线 |
| \|skew\| ≥ 1 | 高度偏 | 必须箱线 / 小提琴；考虑**对数变换**或对数 y 轴 |

**为什么偏态分布不画均值柱**：均值被极值拉走，"均值±SD"会画出超出数据真实范围的下界（例如 mean=2, SD=5，下界 -3 但数据全正）。审稿人一眼看出问题。

### 跨量级 → 对数轴

报告里的 `-> log axis` 提示：变量最大值 / 最小值 > 100，且全正。

- 剂量响应：剂量 0.1 / 1 / 10 / 100 → log x 轴
- 蛋白丰度：跨 6 个数量级 → log y 轴
- 时间常数：ms ~ 几十秒 → log y 轴

### 异常值

`outliers=3 (IQR)` 表示 IQR 法（Q1-1.5·IQR ~ Q3+1.5·IQR 之外）有 3 个点。

**处理三选一（必须在图注交代选择）**：

1. **展示**：画出来，让读者看到分布全貌（推荐）
2. **标注**：保留但加 annotation 说明（如"sample #17, instrument error"）
3. **剔除**：必须有明确的方法学理由（如"明显的录入错误"），**不能因为不喜欢就剔**

绝对禁止：偷偷删掉异常点不报告。

---

## 分组结构的影响

`Group structure` 区把分组维度映射到样本数：

```
- Grouped by: `group`, `condition`
- Number of groups: 6
- Group size: min=1, median=3, max=3
- **WARN**: at least one group has n<3 ...
```

### 单分组 vs 多分组

| 分组维度 | 映射建议 |
|---|---|
| 单维度（如 group: A/B/C） | x 轴 |
| 双维度（如 group × condition） | x 轴 + hue 颜色 |
| 三维度（如 group × condition × sex） | x 轴 + hue + 子图（facet） |
| 四维度+ | **拆图**或选子集；视觉通道用尽了 |

### 嵌套 vs 交叉

- **交叉**（每个组合都有样本）：用 `groupby(['A','B'])`，所有组合都有
- **嵌套**（B 在 A 内独立）：例如 patient 嵌套在 hospital 内—— hospital 之间的 patient ID 不可比

报告输出 `n_groups` 给的是实际存在的组合数；与"理论笛卡尔积"比较可知是否平衡。

### 平衡 vs 不平衡

- min ≈ max：平衡，统计推断方便
- min ≪ max：不平衡，需要 mixed model 或权重；画图时**不要直接画"组均值"**误导观感

---

## 相关性 / 多重共线性的提示

`Correlations` 区按 |r| 排序列出 top 10：

```
- `response_time` ↔ `score` : r = -0.394 (moderate)
```

### 用法

1. **高度相关的列**（|r| > 0.7）——画散点时这两个互为冗余，不要俩都做 x 轴或都做 hue
2. **多重共线性预警**——做回归/PCA 时，强相关变量会让模型不稳；画 pairplot 看清楚
3. **决定 pairplot 的子集**——20 列全 pairplot 没法看；用 r 排序选 top 5-8 个相关变量

### 警惕的相关性陷阱

- **辛普森悖论**：整体相关 vs 分组内相关方向相反——画散点必须分组着色看
- **非线性相关**：Pearson 只测线性，看到 r=0.1 别下"无关"结论；先画散点

---

## 缺失值与异常值

报告中：

```
| `age` | continuous | 89 | 11 (11%) | ... |
```

`11 (11%)` 表示缺失率 11%。

| 缺失率 | 处理 |
|---|---|
| < 5% | 默认忽略；画图时 dropna 即可 |
| 5-20% | 在图注里交代"n=89 of 100 (11% missing)" |
| > 20% | **不能默默忽略**——考虑是否分组导致系统性缺失；用 missingno 看模式 |

### 缺失模式

- **MCAR**（完全随机）：dropna 即可
- **MAR**（与其它变量相关）：分组分析时要分别处理
- **MNAR**（与未观测变量相关）：缺失本身可能是信号；考虑画"缺失率"专图

---

## 从报告到画图决策的流程

```
profile_data.py 输出报告
        ↓
1. 看 Columns 区：类型对不对？
   - 错的列回去 .astype(...) 修，重跑
        ↓
2. 看 Group structure：样本量够吗？
   - n<10 警告 → 切到箱线+stripplot
   - n<3 警告 → 直接列点，不画统计图
        ↓
3. 看 Columns 区的偏度：
   - skew>1 → 箱线/小提琴 + 考虑 log 轴
   - "-> log axis" 提示 → 加 log 轴
        ↓
4. 看 Group structure 的组数 × Columns 类别数：
   - 维度组合 >12 → 拆图，不要硬塞
        ↓
5. 看 Correlations：
   - 决定散点 hue/style 配置
   - 决定 pairplot 子集
        ↓
6. 看 Warnings：每条都处理掉
        ↓
7. 看 Chart suggestions：作为起点，但**最终决定要结合论证目标**
        ↓
查 chart_selection.md 把"数据形态"和"想表达什么"对上，定最终图型。
```

记住：**`profile_data.py` 给的是数据的事实，`chart_selection.md` 把事实和论点结合起来选图，二者缺一不可**。
