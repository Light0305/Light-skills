> 来源文档，按需查阅；执行规则以本包 SKILL.md 和 references/source-adaptation.md 为准。旧版期刊数值、强制提问、多代理和自动统计建议不直接生效。

# 七类图配方

每一节给一份**可直接运行的 Python 代码**——直接复制改数据就能出图。所有代码假设已经调过 `setup_style()`。

## 目录

- [通用前置](#通用前置)
- [1. 折线图（含误差阴影）](#1-折线图含误差阴影)
- [2. 柱状图（分组 + 误差棒）](#2-柱状图分组--误差棒)
- [3. 散点图（多语义映射 + 回归线）](#3-散点图多语义映射--回归线)
- [4. 箱线图 / 小提琴图（叠 stripplot）](#4-箱线图--小提琴图叠-stripplot)
- [5. 热力图（感知均匀色图）](#5-热力图感知均匀色图)
- [6. 误差棒图](#6-误差棒图)
- [7. 分布图（直方图 / KDE）](#7-分布图直方图--kde)
- [8. 相关性矩阵 / 散点矩阵](#8-相关性矩阵--散点矩阵)
- [9. 多面板组合图](#9-多面板组合图)
- [10. Plotly 交互图](#10-plotly-交互图)

---

## 通用前置

```python
import sys, os
sys.path.insert(0, '../scripts')   # 假设从 references/ 调
from setup_style import setup_style
from export_figure import export_figure

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 一次性设好样式
setup_style(journal='nature', lang='en')

# Okabe-Ito 8 色（色盲安全）
OKABE = ['#000000', '#E69F00', '#56B4E9', '#009E73',
         '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
# 也可直接用 seaborn 的 colorblind
PAL = sns.color_palette('colorblind')
```

---

## 1. 折线图（含误差阴影）

**何时用**：时间序列、x 是连续变量、需要展示均值±误差。

```python
def lineplot_with_band(ax, x, y_mean, y_err, label, color, ls='-'):
    """y_err 可以是 SD/SEM/95%CI，图注里务必交代。"""
    ax.plot(x, y_mean, color=color, linewidth=1.0, linestyle=ls, label=label)
    ax.fill_between(x, y_mean - y_err, y_mean + y_err,
                    color=color, alpha=0.2, linewidth=0)

# --- 示例 ---
rng = np.random.default_rng(42)
x = np.linspace(0, 10, 100)
# 假装 n=12 只小鼠，对每个 x 算 mean ± SEM
n = 12
y1_samples = np.sin(x)[:, None] + rng.normal(0, 0.3, (100, n))
y2_samples = np.cos(x)[:, None] + rng.normal(0, 0.3, (100, n))
y1_mean, y1_sem = y1_samples.mean(1), y1_samples.std(1, ddof=1) / np.sqrt(n)
y2_mean, y2_sem = y2_samples.mean(1), y2_samples.std(1, ddof=1) / np.sqrt(n)

fig, ax = plt.subplots(figsize=(3.5, 2.625))
lineplot_with_band(ax, x, y1_mean, y1_sem, 'Condition A',
                   color=OKABE[2], ls='-')
lineplot_with_band(ax, x, y2_mean, y2_sem, 'Condition B',
                   color=OKABE[6], ls='--')   # 第二条用虚线 -> 黑白可读
ax.set_xlabel('Time (s)')
ax.set_ylabel('Response (a.u.)')
ax.legend(frameon=False, loc='lower right')

# 图注必须写: shaded band = SEM, n = 12 mice per group.
export_figure(fig, 'figs/01_line', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300, grayscale_preview=True)
```

**坑**：
- `fill_between` 必须显式 `linewidth=0`，否则 PDF 里阴影边缘会有细线
- 不同曲线**必须**有除颜色之外的区分（线型 / marker），否则灰度下不可读

---

## 2. 柱状图（分组 + 误差棒）

**何时用**：分类变量的均值对比、组间比较。

```python
# 数据：3 组 × 2 条件 × n=10 重复
rng = np.random.default_rng(0)
groups = ['Control', 'Drug A', 'Drug B']
conditions = ['Before', 'After']
data = pd.DataFrame({
    'group': np.repeat(groups, 2 * 10),
    'condition': np.tile(np.repeat(conditions, 10), 3),
    'value': np.concatenate([
        rng.normal(loc, 1.0, 10)
        for loc in [1, 2, 3, 4, 2, 3]   # 6 组合
    ]),
})

# 用 seaborn barplot——默认就是 mean + 95%CI（bootstrap）
# 想要 SD/SEM 改 errorbar 参数
fig, ax = plt.subplots(figsize=(3.5, 2.625))
sns.barplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    errorbar='se',          # 'sd' | 'se' | ('ci', 95) | None
    capsize=0.15,
    err_kws={'linewidth': 0.8},
    ax=ax,
)
# 叠加原始点显示数据分布——审稿人喜欢看分布而非只看均值
sns.stripplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    dodge=True, size=2, alpha=0.6, edgecolor='black', linewidth=0.3,
    ax=ax, legend=False,
)
ax.set_xlabel(''); ax.set_ylabel('Score (a.u.)')
ax.legend(title='', frameon=False, loc='upper left')

# 图注: bars = mean ± SEM; dots = individual replicates; n = 10 per group.
export_figure(fig, 'figs/02_bar', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**坑**：
- 柱状图**不要**用没有误差棒的纯柱——审稿人会怀疑没做重复
- 多组比较时配色保持类别一致（同一个条件在不同图里同色）
- `barplot` 默认 95% CI 是 bootstrap，**速度慢**，明确写 `errorbar='se'` 或 `'sd'` 更快也更明确

---

## 3. 散点图（多语义映射 + 回归线）

**何时用**：相关性、双变量关系；可以同时映射 hue（颜色）+ style（marker）+ size。

```python
# 模拟数据：N 个样本，x 和 y 有相关性，分两组
rng = np.random.default_rng(1)
N = 80
df = pd.DataFrame({
    'x': rng.normal(0, 1, N),
    'group': rng.choice(['A', 'B'], N),
})
df['y'] = 0.6 * df['x'] + np.where(df['group']=='B', 0.5, 0) + rng.normal(0, 0.5, N)

fig, ax = plt.subplots(figsize=(3.5, 3.0))
sns.scatterplot(
    data=df, x='x', y='y',
    hue='group', style='group',     # 颜色 + marker 形状双重编码
    palette=[OKABE[2], OKABE[6]],
    s=25, alpha=0.85, edgecolor='black', linewidth=0.3,
    ax=ax,
)
# 分组回归线 + 95% CI
sns.regplot(data=df[df.group=='A'], x='x', y='y',
            scatter=False, color=OKABE[2], line_kws={'lw': 1.0}, ax=ax)
sns.regplot(data=df[df.group=='B'], x='x', y='y',
            scatter=False, color=OKABE[6], line_kws={'lw': 1.0}, ax=ax)

# 在图里标 Pearson r 和 p
from scipy.stats import pearsonr
for g, c in zip(['A', 'B'], [OKABE[2], OKABE[6]]):
    sub = df[df.group == g]
    r, p = pearsonr(sub.x, sub.y)
    ax.text(0.05 if g=='A' else 0.05, 0.95 if g=='A' else 0.88,
            f'{g}: r={r:.2f}, p={p:.1e}',
            transform=ax.transAxes, fontsize=6, color=c, va='top')

ax.set_xlabel('Predictor x'); ax.set_ylabel('Response y')
ax.legend(title='Group', frameon=False, loc='lower right')

export_figure(fig, 'figs/03_scatter', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 3.0), dpi=300)
```

**坑**：
- 散点图样本量很大（>1000）时，alpha 调到 0.2-0.3 防止 over-plotting，或用 `sns.jointplot` 加边缘密度
- 把 r 和 p 标在图里**很省审稿人时间**，加分项
- regplot 的 `scatter=False` 必须，否则散点会被画两遍

---

## 4. 箱线图 / 小提琴图（叠 stripplot）

**何时用**：组间分布对比；箱线图看四分位，小提琴图看密度。**最佳实践**：箱线图/小提琴图 + stripplot 叠加显示原始点。

```python
# 同任务 2 的数据
fig, ax = plt.subplots(figsize=(3.5, 2.625))
sns.boxplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    showfliers=False,        # 不画异常点，由 stripplot 显示全部点
    width=0.6,
    linewidth=0.8,
    ax=ax,
)
sns.stripplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    dodge=True, size=2.5, alpha=0.6,
    edgecolor='black', linewidth=0.3,
    ax=ax, legend=False,
)
ax.set_xlabel(''); ax.set_ylabel('Score (a.u.)')
ax.legend(title='', frameon=False)

# 想用小提琴图把 boxplot 换 violinplot 即可:
# sns.violinplot(..., inner=None, cut=0)
# inner=None 关掉内部小条；cut=0 让小提琴不超出数据范围

export_figure(fig, 'figs/04_box', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**显著性标注**（如需）：

```python
from matplotlib.lines import Line2D
def sig_bracket(ax, x1, x2, y, h, text, fontsize=6):
    """在 (x1, x2) 之间画一道带文字的桥。"""
    ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y],
            color='black', linewidth=0.6)
    ax.text((x1+x2)/2, y+h, text, ha='center', va='bottom', fontsize=fontsize)

# 例: 在 Control vs Drug A 上方加 '**'
# x1=0-0.15, x2=0-0.15 对应 dodge 后实际位置；调一下偏移
# sig_bracket(ax, -0.2, 0.2, y=5.5, h=0.1, text='**')
```

**坑**：
- 小提琴图比箱线图**更容易误导**——n<10 时密度估计不可靠，建议直接用箱线
- 显著性标注必须在图注里说明：what test，是否校正多重比较（Bonferroni / FDR）
- `* p<0.05, ** p<0.01, *** p<0.001` 这种缩写需在图注或文章中定义

---

## 5. 热力图（感知均匀色图）

**何时用**：矩阵数据、相关性矩阵、混淆矩阵、基因表达矩阵。

```python
# 模拟一个 8×8 相关矩阵
rng = np.random.default_rng(2)
mat = rng.uniform(-1, 1, (8, 8))
mat = (mat + mat.T) / 2     # 对称
np.fill_diagonal(mat, 1.0)
labels = [f'f{i+1}' for i in range(8)]

fig, ax = plt.subplots(figsize=(3.5, 3.0))
hm = sns.heatmap(
    mat, ax=ax,
    cmap='RdBu_r',          # 双向数据用发散色图；单向数据用 'viridis' / 'magma'
    vmin=-1, vmax=1,        # 显式锁定范围 -> 多个图可比较
    center=0,
    annot=True, fmt='.2f',
    annot_kws={'fontsize': 5},
    cbar_kws={'label': "Pearson's r", 'shrink': 0.8},
    linewidths=0.5, linecolor='white',
    xticklabels=labels, yticklabels=labels,
    square=True,
)
ax.tick_params(labelsize=6)
hm.collections[0].colorbar.ax.tick_params(labelsize=6)

export_figure(fig, 'figs/05_heatmap', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 3.0), dpi=300)
```

**坑**：
- **不要用** rainbow / jet / hsv——感知不均匀，会"造峰造谷"。**永远用** viridis / magma / inferno / cividis / RdBu_r
- 双向数据（正负有意义）必须发散色图（`RdBu_r`、`PiYG`）+ `center=0`
- 数值 annot 大量数据时关掉（`annot=False`），不然糊成一片
- `square=True` 让每个格子正方形，更专业

---

## 6. 误差棒图

**何时用**：少量点位的均值 ± 误差对比；典型如不同剂量、不同时间点。

```python
doses = np.array([0, 1, 3, 10, 30, 100])
n = 8
rng = np.random.default_rng(3)
responses = (np.log10(doses + 1) * 2 + rng.normal(0, 0.5, (n, doses.size)))
mean = responses.mean(0)
sem = responses.std(0, ddof=1) / np.sqrt(n)

fig, ax = plt.subplots(figsize=(3.5, 2.625))
ax.errorbar(
    doses, mean, yerr=sem,
    fmt='o',                  # marker
    color=OKABE[2], ecolor=OKABE[2],
    elinewidth=0.8, capsize=2, capthick=0.8,
    markersize=5, markeredgecolor='black', markeredgewidth=0.4,
    label='Compound X',
)
ax.set_xscale('symlog', linthresh=1)   # 0 剂量保留在轴上
ax.set_xlabel('Dose (μM)')
ax.set_ylabel('Response (a.u.)')
ax.legend(frameon=False, loc='lower right')

# 图注: data = mean ± SEM, n = 8 wells per dose.
export_figure(fig, 'figs/06_errbar', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**坑**：
- `capsize=2`（默认 0 时没有 cap），有 cap 更易读
- `symlog` 比 `log` 更适合包含 0 的剂量轴（避免 log(0) 报错）
- 误差棒可以是不对称的（传 `yerr=[lower_err, upper_err]`），表达非高斯分布

---

## 7. 分布图（直方图 / KDE）

**何时用**：看单个连续变量的分布形态——是否对称、是否双峰、是否偏态、是否有 outlier。

```python
rng = np.random.default_rng(7)
# 模拟双峰分布
data1 = np.concatenate([rng.normal(0, 1, 200), rng.normal(4, 1, 200)])
# 模拟偏态分布
data2 = rng.lognormal(0, 0.5, 400)

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), constrained_layout=True)

# === 直方图 + KDE 叠加 ===
ax = axes[0]
ax.hist(data1, bins=30, density=True, alpha=0.55,
        color=OKABE[2], edgecolor='black', linewidth=0.4,
        label='Histogram')
# KDE 用 seaborn 直接画在同一 ax
sns.kdeplot(data1, ax=ax, color=OKABE[6], linewidth=1.2, label='KDE')
# 在底部加 rug 显示每个原始点
sns.rugplot(data1, ax=ax, color='black', height=0.04, alpha=0.4)
ax.set_xlabel('Value'); ax.set_ylabel('Density')
ax.set_title('Bimodal distribution')
ax.legend(frameon=False, fontsize=6)

# === 偏态分布 + 中位数 vs 均值 ===
ax = axes[1]
ax.hist(data2, bins=30, density=True, alpha=0.55,
        color=OKABE[3], edgecolor='black', linewidth=0.4)
sns.kdeplot(data2, ax=ax, color=OKABE[6], linewidth=1.2)
ax.axvline(data2.mean(), color='red', linestyle='--', linewidth=0.8,
           label=f'mean={data2.mean():.2f}')
ax.axvline(np.median(data2), color='black', linestyle=':', linewidth=0.8,
           label=f'median={np.median(data2):.2f}')
ax.set_xlabel('Value (log-normal)'); ax.set_ylabel('Density')
ax.set_title('Right-skewed: mean vs median')
ax.legend(frameon=False, fontsize=6)

export_figure(fig, 'figs/07_distribution', formats=['pdf', 'svg', 'png'],
              size_inches=(7.0, 2.8), dpi=300)
```

**坑**：
- `bins` 太多 → 噪音；太少 → 平滑过度。`bins='auto'` 是不错的起点
- KDE 在数据稀少（n<30）时**不可靠**——直方图更诚实
- 多组叠加分布 → 用 `alpha=0.4` 透明色块；更建议用 small multiples 分面画
- 偏态强烈 → 同时显示均值（红虚）和中位数（黑点）让审稿人看出差异
- 看到双峰立刻警觉：是否分组结构没拆？

---

## 8. 相关性矩阵 / 散点矩阵

**何时用**：多个连续变量（3-20+）想看两两关系。**变量 ≤ 8 用 pairplot，> 8 用 heatmap**。

### 8a. 相关性热力图

```python
# 模拟 6 列数据
rng = np.random.default_rng(8)
n = 200
base = rng.normal(0, 1, n)
df = pd.DataFrame({
    'feature_A': base + rng.normal(0, 0.5, n),
    'feature_B': base + rng.normal(0, 0.3, n),
    'feature_C': -base + rng.normal(0, 0.4, n),
    'feature_D': rng.normal(0, 1, n),
    'feature_E': rng.normal(0, 1, n),
    'feature_F': base * 0.5 + rng.normal(0, 0.6, n),
})
corr = df.corr(method='pearson')

# 半矩阵更易读（对称，画一半就够）
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

fig, ax = plt.subplots(figsize=(4.0, 3.5))
sns.heatmap(
    corr, mask=mask,
    cmap='RdBu_r', vmin=-1, vmax=1, center=0,
    annot=True, fmt='.2f', annot_kws={'fontsize': 6},
    cbar_kws={'label': "Pearson's r", 'shrink': 0.7},
    linewidths=0.5, linecolor='white',
    square=True, ax=ax,
)
ax.tick_params(labelsize=6)
ax.set_title('Feature correlations', fontsize=8)

export_figure(fig, 'figs/08a_corr_heatmap', formats=['pdf', 'svg', 'png'],
              size_inches=(4.0, 3.5), dpi=300)
```

### 8b. 散点矩阵 (pairplot)

```python
# pairplot 适合 ≤ 8 列；超过就糊
import seaborn as sns
df_sub = df[['feature_A', 'feature_B', 'feature_C', 'feature_D']].copy()
df_sub['group'] = rng.choice(['Ctrl', 'Treat'], n)

g = sns.pairplot(
    df_sub, hue='group',
    palette={'Ctrl': OKABE[2], 'Treat': OKABE[6]},
    plot_kws=dict(s=10, alpha=0.6, edgecolor='black', linewidth=0.2),
    diag_kws=dict(linewidth=0.8),
    height=1.4,           # 每个子图英寸数；总尺寸 ≈ height × n_cols
    aspect=1.0,
)
g.fig.set_size_inches(6.0, 6.0)
for ax in g.axes.flat:
    if ax is not None:
        ax.tick_params(labelsize=6)
        ax.set_xlabel(ax.get_xlabel(), fontsize=7)
        ax.set_ylabel(ax.get_ylabel(), fontsize=7)

export_figure(g.fig, 'figs/08b_pairplot', formats=['pdf', 'svg', 'png'],
              size_inches=(6.0, 6.0), dpi=300)
```

**坑**：
- pairplot 变量数 > 8 → 子图小于 1 in，肉眼不可读
- 配 `hue` 区分组要有意义，否则把对角分布看糊
- 上三角和下三角都画相关图 = 信息冗余；用 `mask` 只画一半

---

## 9. 多面板组合图

**何时用**：一篇论文一张 Figure 通常 2-6 个子图；要保证子图字号、配色、坐标尺度一致。

```python
fig, axes = plt.subplots(
    2, 2,
    figsize=(7.2, 5.4),                # Nature 双栏 7.2 in
    constrained_layout=True,           # 比 tight_layout 智能
)

# === 子图 a：折线 ===
ax = axes[0, 0]
x = np.linspace(0, 10, 50)
ax.plot(x, np.sin(x), color=OKABE[2], label='A')
ax.plot(x, np.cos(x), color=OKABE[6], linestyle='--', label='B')
ax.set_xlabel('Time (s)'); ax.set_ylabel('Signal')
ax.legend(frameon=False, fontsize=6)

# === 子图 b：散点 ===
ax = axes[0, 1]
ax.scatter(rng.normal(0,1,50), rng.normal(0,1,50),
           c=OKABE[3], s=12, edgecolor='black', linewidth=0.3)
ax.set_xlabel('PC1'); ax.set_ylabel('PC2')

# === 子图 c：柱状 ===
ax = axes[1, 0]
vals = [3.2, 4.5, 2.8]; errs = [0.3, 0.2, 0.4]
ax.bar(['G1','G2','G3'], vals, yerr=errs, capsize=2,
       color=[OKABE[2], OKABE[6], OKABE[3]], edgecolor='black', linewidth=0.5)
ax.set_ylabel('Score')

# === 子图 d：箱线 ===
ax = axes[1, 1]
data_box = [rng.normal(loc, 1, 30) for loc in [0, 0.7, 1.4]]
ax.boxplot(data_box, tick_labels=['G1','G2','G3'],
           patch_artist=True, widths=0.5,
           boxprops=dict(facecolor=OKABE[2], alpha=0.6, linewidth=0.6),
           medianprops=dict(color='black', linewidth=1.0),
           flierprops=dict(marker='o', markersize=2))
ax.set_ylabel('Value')

# 子图标签：a, b, c, d (Nature 风格)
for ax, label in zip(axes.flat, ['a', 'b', 'c', 'd']):
    ax.text(-0.20, 1.05, label, transform=ax.transAxes,
            fontsize=9, fontweight='bold', va='top', ha='right')

export_figure(fig, 'figs/09_panels', formats=['pdf', 'svg', 'png'],
              size_inches=(7.2, 5.4), dpi=300, grayscale_preview=True)
```

**坑**：
- 子图标签位置 `(-0.20, 1.05)` 视坐标轴标签宽度调整；左对齐居外侧效果最稳
- **统一配色**：同一变量在不同子图里同色（"Condition A 永远蓝色"）
- **统一尺度**：可比的子图共用 ylim/xlim，让对比直观
- `constrained_layout=True` 优先；它会自动协调子图间距和外部 colorbar/legend

---

## 10. Plotly 交互图

**何时用**：补充材料、博客、需要 hover 数据的 web 端展示。**正式投稿 PDF 不用 plotly**——投稿系统不接受 HTML。

```python
import plotly.express as px
import plotly.io as pio

# 中文支持
pio.templates.default = 'plotly_white'
common_layout = dict(
    font=dict(family='Noto Sans CJK SC, Source Han Sans, SimHei, Arial',
              size=12),
    title_font_size=14,
)

df = pd.DataFrame({
    'dose': np.repeat([0, 1, 3, 10, 30, 100], 8),
    'response': np.tile(np.arange(8), 6) + np.random.randn(48),
    'group': np.tile(['A', 'B'] * 4, 6),
})
fig = px.scatter(
    df, x='dose', y='response', color='group', symbol='group',
    log_x=True,
    color_discrete_sequence=['#56B4E9', '#D55E00'],     # Okabe-Ito
    template='plotly_white',
    title='剂量响应曲线（交互版）',
)
fig.update_layout(**common_layout)
fig.write_html('figs/10_interactive.html')
fig.write_image('figs/10_interactive.pdf', width=500, height=350)  # 需 pip install kaleido
```

**坑**：
- 交互图保存 PDF / SVG 需要 `kaleido` 包（`pip install -U kaleido`）
- plotly 默认背景灰，加 `template='plotly_white'`
- 中文字体在 plotly 里通过 `layout.font.family` 配置，与 matplotlib 独立
