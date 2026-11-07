> 来源文档，按需查阅；执行规则以本包 SKILL.md 和 references/source-adaptation.md 为准。旧版期刊数值、强制提问、多代理和自动统计建议不直接生效。

# 投稿前合规自检清单

每张图投稿前**逐条勾选**。任何 FAIL 必须重新出图——`scripts/check_figure.py --strict` 是机器版的这份清单。

> 这份清单只查**形式合规**（尺寸、DPI、字号、误差是否写明）。**语义层面**的避坑（均值柱掩盖分布、双 Y 轴误导、饼图等）在 [`viz_pitfalls.md`](viz_pitfalls.md) — 提交前两份清单都要过。

## 目录

- [尺寸 & 分辨率](#尺寸--分辨率)
- [文件格式](#文件格式)
- [字体 & 字号](#字体--字号)
- [配色 & 色盲](#配色--色盲)
- [坐标轴 & 标签](#坐标轴--标签)
- [图例 & 子图标签](#图例--子图标签)
- [误差 & 统计交代](#误差--统计交代)
- [语义合规（viz_pitfalls 交叉检查）](#语义合规viz_pitfalls-交叉检查)
- [中文图额外项](#中文图额外项)
- [终检](#终检)

---

## 尺寸 & 分辨率

- [ ] `figsize` 直接设成目标期刊的最终尺寸（**单栏 ~3.5 in / 双栏 ~7.2 in**）
- [ ] 导出后**没有**在 Word / LaTeX / PPT 里再缩放
- [ ] 位图 DPI ≥ 300（普通彩色）/ ≥ 600（线条图、IEEE）
- [ ] 用 `check_figure.py` 验证文件内嵌的实际尺寸与目标尺寸偏差 < 0.1 in

## 文件格式

- [ ] 数据图（线/柱/散点/热力/箱线）→ **矢量** PDF / SVG / EPS
- [ ] 显微图、照片 → **位图** PNG / TIFF（≥300 DPI）
- [ ] **没有任何 JPEG**（数据图禁用，照片也优先 TIFF）
- [ ] PDF 嵌入 TrueType 字体（**fonttype 42**），不含 Type 3
- [ ] SVG 内**没有 base64 嵌入位图**（破坏矢量优势）

## 字体 & 字号

- [ ] 字体与期刊一致：Nature/Science/Elsevier/PNAS → Helvetica/Arial；IEEE → Times；中文期刊 → 宋体+TNR
- [ ] 最终尺寸下正文标签 7–9 pt，刻度数字 6–8 pt，**最小字 ≥ 6 pt**
- [ ] 所有字符可读，没有方框（中文模式必查）
- [ ] 同一张图字体不超过 2 种

## 配色 & 色盲

- [ ] 默认 Okabe-Ito 或 seaborn `colorblind`，**避免红绿对比**
- [ ] 不同类别**双重编码**：不同颜色 + 不同线型 / marker
- [ ] 导出灰度预览（`export_figure(grayscale_preview=True)`），灰度下仍能区分
- [ ] 热力图用**感知均匀**色图（viridis / magma / inferno / cividis / RdBu_r），**不用** rainbow / jet
- [ ] 双向数据用发散色图 + `center=0`

## 坐标轴 & 标签

- [ ] x / y 轴都有 label，包含**变量名 + 单位**（如 `Time (s)`、`Dose (μM)`）
- [ ] 刻度数字精度合理，不出现 `1.0000` 或 `1.23456789` 这种
- [ ] log 轴明确标 log（如 `Dose (μM, log)`）
- [ ] 不在原点强制 0，除非数据有意义包含 0
- [ ] 不出现 `axes.unicode_minus` 方框（用 `setup_style` 自动修）

## 图例 & 子图标签

- [ ] 图例**清晰可读**，`frameon=False` 去框线让画面干净
- [ ] 图例位置不遮挡数据
- [ ] 类别 > 5 时考虑改用直接标注（在曲线末端写名字）而非图例
- [ ] 子图标签按期刊格式：Nature `a/b/c` 小写加粗；Science/PNAS `A/B/C`；IEEE `(a)/(b)/(c)`
- [ ] 子图标签位置统一（建议左上角，`transform=ax.transAxes`，坐标 `(-0.20, 1.05)`）
- [ ] 多面板的子图字号、配色、坐标尺度**保持一致**

## 误差 & 统计交代

- [ ] 凡有误差棒 / 阴影区间 / 箱线 → **图注**必须写明：
  - [ ] 误差类型（SD / SEM / 95% CI / IQR）
  - [ ] 样本量 n
  - [ ] 显著性检验方法（t-test / Mann-Whitney / ANOVA / 校正）
  - [ ] 显著性符号定义（`* p<0.05, ** p<0.01, *** p<0.001`）
- [ ] 显著性标注的位置不遮挡数据
- [ ] 没有"无误差棒的均值柱"——审稿人会怀疑没做重复

## 语义合规（viz_pitfalls 交叉检查）

形式合规 ≠ 语义合规。下面 8 条是 [`viz_pitfalls.md`](viz_pitfalls.md) 里 15 条避坑清单的**精选 must-pass 项**：

- [ ] **P1**：n<10/组的话**不**用均值柱状图——叠加 stripplot 或换箱线
- [ ] **P2**：没有双 Y 轴（除非两个变量量纲相同）
- [ ] **P3**：没有饼图，没有 3D 柱/3D 饼/3D 表面
- [ ] **P4**：y 轴起点合理（比例/概率从 0 开始；截断有明确断裂标记）
- [ ] **P5**：所有连续色阶配 colorbar，且 colorbar 带 label + 单位
- [ ] **P6**：x 是分类变量的话**没有**用折线连组均值
- [ ] **P12**：一张图只讲一个核心结论（多个论点拆图）
- [ ] **P14**：连续值用 viridis / magma / RdBu_r，**没有** rainbow / jet

完整 15 条详见 [`viz_pitfalls.md`](viz_pitfalls.md)。

## 中文图额外项

- [ ] `setup_style(lang='zh')` 已调用
- [ ] 中文字体可用（`python setup_style.py --list-fonts` 验证）
- [ ] 中文 + 数字 / 西文混排：中文走中文字体，**数字和变量名走 Times New Roman**
- [ ] 负号显示正确，不是方框（`axes.unicode_minus = False`）
- [ ] 中文期刊 PDF 优先于 EPS（EPS 对 TrueType 中文支持差）
- [ ] 图注、坐标轴标签都用中文（除非投英文期刊）

## 终检

- [ ] 跑一遍：
  ```bash
  python scripts/check_figure.py figs/*.pdf figs/*.png \
         --min-dpi 300 --width-in 3.5 --height-in 2.625 --strict
  ```
  exit code 0 才算 PASS。

- [ ] 把生成的 PDF **打印出来**（或缩放到论文实际尺寸）肉眼看一遍——字够大吗？线够清吗？颜色对比够吗？
- [ ] 用色盲模拟工具（Color Oracle / Coblis）查一遍
- [ ] 给非同行（家人朋友）看一眼能不能看懂三条信息：x 是啥、y 是啥、几条线/柱有什么区别——看不懂说明图传达失败

---

## 一行命令总览

把这个清单浓缩为机器可跑的命令：

```bash
# 1. 出图（已经做完）
# 2. 末端审计
python scripts/check_figure.py figs/*.pdf figs/*.png \
       --min-dpi 300 --width-in 3.5 --height-in 2.625 --strict

# 3. 人眼终检
ls figs/ | xargs -I{} echo "open figs/{}"   # 一一打开看
```

任何 FAIL → 回去改 → 再跑 → 直到 PASS。
