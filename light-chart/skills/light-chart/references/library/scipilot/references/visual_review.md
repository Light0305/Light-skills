> 来源文档，按需查阅；执行规则以本包 SKILL.md 和 references/source-adaptation.md 为准。旧版期刊数值、强制提问、多代理和自动统计建议不直接生效。

# 视觉自检闭环：让 AI 看着图自己挑错、自己改

这是 `scipilot-figure-skill` v2.1 的核心新增能力。普通画图工具画完就结束了——**没人回看成图**，于是中文方框、文字被裁、图例压住数据、子图编号乱放这些问题全部留到投稿才被审稿人发现。本文件定义一套**出图后的闭环**：

```
绘制 → ① 渲染 PNG 预览 → ② 程序自检(visual_qa) → ③ AI 读图自检
                                                        ↓ 发现问题
        ⑤ 通过 ← ④ 回到对应步骤改图 → 重新渲染 → 再读图 ←┘
```

## 为什么必须「渲染成 PNG 再让 AI 看」

- **矢量 PDF/SVG 没法直接"看"像素层面的重叠和遮挡**——必须先栅格化成 PNG。
- **程序能查的有限**：缺字、越界、刻度相交这类**确定性**问题程序能抓（`visual_qa.py`），但"图例正好压在一簇数据点上""这两条标注文字叠在一起""配色看着发灰分不开"这类**感知性**问题，只有把图当成图像看才发现。
- 本 skill 运行在具备**多模态读图能力**的 AI（Claude 等）之上——可以用 `Read` 工具直接读 PNG。所以这个闭环**真能执行**，不是一句空话。

## 分工：程序自检 vs AI 读图

| 层 | 工具 | 负责抓 |
|---|---|---|
| 程序自检 | `scripts/visual_qa.py :: audit_layout(fig)` | 缺字乱码、文字越界裁切、刻度标签重叠（确定性） |
| AI 读图 | 本文件清单 + `Read` 读 PNG | 图例压数据、标注重叠、子图标签对齐、配色/灰度可分、整体观感（感知性） |

**两层都要过**。程序 PASS 不代表图就好看；AI 读图才是终检。

## 标准操作流程

### 第 1 步：渲染预览

```python
from visual_qa import render_preview, audit_layout, print_report

# fig 是刚画好、还没导出的 matplotlib Figure
preview = render_preview(fig, "figs/_preview.png", dpi=150)
```

> 用 150 dpi：足够看清文字与重叠，又不会让图太大拖慢读图。**导出最终矢量图之前**就做这一步——发现问题还能在源头改。

### 第 2 步：程序自检

```python
issues = audit_layout(fig)
print_report(issues)
```

任何 `FAIL`（几乎只会是缺字乱码）**必须先修**再继续。`WARN`（裁切/重叠）记下来，到第 3 步读图时重点确认。

### 第 3 步：AI 读图自检（关键）

用 `Read` 工具读 `figs/_preview.png`，然后**逐条**对照下面的清单核对。不要扫一眼说"看起来不错"——一项一项看。

#### 读图自检清单

1. **乱码 / 方框**
   - 中文有没有变成 □□□ 方框 / 豆腐块？
   - 负号、`±`、`×`、`μ`、`Δ`、希腊字母、上下标有没有缺字？
   - → 命中：见下方「回改对应表」缺字行。

2. **文字被裁切**
   - 标题、x/y 轴标签、图例、数值标注，有没有被画布四边切掉一截？
   - 旋转后的长刻度标签底部有没有出界？

3. **文字遮盖 / 重叠**
   - **图例有没有压住数据**（点、线、柱）？
   - 显著性标注、数值标签、注释文字之间有没有互相叠？
   - x 轴刻度标签有没有挤成一团、互相穿插？

4. **子图编号对齐**（多面板必查）
   - a/b/c/d 是否**横看一条线、竖看一条线**？同一行的标签等高吗？同一列的标签左缘对齐吗？
   - 字号、加粗、风格是否一致（不能有的 `a` 有的 `(a)`）？
   - → 没对齐：改用 `layout_tools.add_panel_labels(fig)` 统一重打。

5. **子图间距 / 互相侵入**
   - 子图之间有没有重叠？某个子图的 y 轴标签有没有伸进左边邻居？
   - colorbar 有没有和子图挤在一起或压住数据？

6. **配色与灰度**
   - 各类别颜色能区分吗？有没有用到红绿对比（色盲不友好）？
   - 如果生成了 `_grayscale.png`，灰度下还能分开吗？分不开 → 加线型/marker 冗余编码。

7. **数据完整性**
   - 有没有数据点 / 曲线 / 误差棒被坐标轴范围切掉？
   - 误差棒顶端、最高的柱、最外的点是否都在框内可见？

8. **跨子图一致性**
   - 同一个变量在多个子图里是否**同色、同标记、同量纲**？
   - 共享含义的坐标轴范围是否一致（便于横向比较）？

### 第 4 步：回改对应表

发现问题后，回到对应环节改，**不要在预览图上手动 P 图**：

| 读图发现 | 回改动作 |
|---|---|
| 中文/符号缺字方框 | `setup_style(lang='zh')`（中文）；查 `setup_style.py --list-fonts`；负号方框确认 `axes.unicode_minus=False` |
| 文字被裁切 | `layout_tools.finalize_figure(fig)`；导出 `bbox_inches='tight'`；标题过长则换行/缩短 |
| 图例压住数据 | `ax.legend(loc=..., bbox_to_anchor=(1.02,1), frameon=False)` 移到图外；或直接末端标注代替图例 |
| 标注文字互相叠 | 调整 `xytext` 偏移；或用 `adjustText`；减少标注数量（只标关键的） |
| x 轴刻度重叠 | `ax.tick_params(axis='x', rotation=30)`；减少刻度数；缩短标签 |
| 子图标签不对齐 | `add_panel_labels(fig, style='nature')` 统一重打 |
| 子图互相重叠 | `finalize_figure(fig)` 或建图时 `constrained_layout=True` |
| 配色不可区分/灰度糊 | 换 Okabe-Ito / `colorblind` 调色板 + 加线型/marker |
| 数据被切掉 | 放宽 `set_xlim/set_ylim`，或 `ax.margins(0.05)` |

### 第 5 步：重新渲染，再读图

改完**回到第 1 步**重新 `render_preview` 并再读一次。循环直到：

- 程序自检无 `FAIL`，且
- 读图清单 8 项全部通过，**或**
- 剩余问题已明确告知用户并获其接受（如"标签确实密，但这是数据本身决定的"）。

## 循环纪律

- **每改一处就重渲一次**——不要一次改五处然后猜结果，看不到就是没验证。
- **最多 3 轮**：3 轮还过不了，多半是图型选错了（回 `chart_selection.md` 重选）或数据维度太多（拆图，见 `viz_pitfalls.md` P12）。
- **留痕**：把每轮发现的问题和改法简要告诉用户，让 ta 知道图为什么长这样。

## 一个完整示例

```python
import matplotlib.pyplot as plt
from setup_style import setup_style
from layout_tools import finalize_figure, add_panel_labels
from visual_qa import render_preview, audit_layout, print_report
from export_figure import export_figure

setup_style(journal='nature', lang='zh')      # 中文 + 自动 CJK 字体 + constrained_layout

fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
# ... 在 axes 上作图 ...

# —— 自检闭环 ——
finalize_figure(fig)                           # 兜底理顺版面
add_panel_labels(fig, style='nature')          # a b c d 对齐
render_preview(fig, 'figs/_preview.png')       # 渲 PNG
print_report(audit_layout(fig))                # 程序自检
# 然后：用 Read 读 figs/_preview.png，对照上面 8 项清单逐条核对
# 有问题 → 按回改表改 → 重渲 → 再读；全过后再导出最终矢量图：

export_figure(fig, 'figs/fig1', formats=['pdf', 'svg'],
              size_inches=(7.2, 5.4), grayscale_preview=True)
```

**记住**：导出矢量图是**最后一步**，在读图清单全过之后。把问题挡在导出之前，而不是投稿之后。
