> 来源文档，按需查阅；执行规则以本包 SKILL.md 和 references/source-adaptation.md 为准。旧版期刊数值、强制提问、多代理和自动统计建议不直接生效。

# 期刊图表规范

主流期刊对投稿图表的硬性要求汇总。**画图前先查目标期刊**，把栏宽、字号、DPI、推荐字体、矢量格式偏好记下来再开 matplotlib。

## 目录

- [Nature 系列](#nature-系列)
- [Science](#science)
- [IEEE](#ieee)
- [Elsevier 系列](#elsevier-系列)
- [PNAS](#pnas)
- [中文核心期刊](#中文核心期刊通用要求)
- [跨期刊速查表](#跨期刊速查表)
- [中文字体安装指南](#中文字体安装指南)

---

## Nature 系列

涵盖 *Nature*、*Nature Methods*、*Nature Communications*、*Nature Machine Intelligence* 等。

| 维度 | 要求 |
|---|---|
| 单栏宽 | **89 mm ≈ 3.5 inch** |
| 双栏宽 | **183 mm ≈ 7.2 inch** |
| 最大高 | 247 mm ≈ 9.7 inch（不超过一页） |
| 字号 | 标签 / 刻度 5–7 pt，绝不小于 5 pt |
| 推荐字体 | **Helvetica / Arial**（无衬线） |
| 矢量首选 | **EPS** / PDF / AI |
| 位图 | TIFF / PNG，**>= 300 DPI**；彩色图 RGB；线条图 >= 600 DPI |
| 行宽 | 0.25–1 pt（matplotlib 默认 1 pt 偏粗，建议 0.6） |
| 颜色 | RGB；色盲安全；避免红绿对比 |
| 子图标签 | **a, b, c**（小写、加粗、放左上角） |

**坑**：Nature 极其强调"按最终尺寸出图"——投稿系统会按 mm 计算字号是否合规。

参考：[Nature Figure Guide](https://www.nature.com/nature/for-authors/formatting-guide)

---

## Science

| 维度 | 要求 |
|---|---|
| 单栏宽 | **55 mm ≈ 2.2 inch**（极窄）|
| 1.5 栏宽 | **120 mm ≈ 4.7 inch** |
| 双栏宽 | **183 mm ≈ 7.2 inch** |
| 字号 | 5–7 pt |
| 推荐字体 | **Helvetica / Arial** |
| 矢量首选 | PDF / EPS / AI |
| 位图 | TIFF / PNG **>= 300 DPI**；线/网格图建议 600 |
| 子图标签 | **A, B, C**（大写、加粗、左上） |

**坑**：单栏极窄（2.2 in），如果要把数据全塞进单栏会被压扁，多数情况选 1.5 栏更合理。

---

## IEEE

涵盖 *Trans on PAMI* / *Trans on Image Processing* / 会议（CVPR、ICCV 等）。

| 维度 | 要求 |
|---|---|
| 单栏宽 | **3.5 inch ≈ 88.9 mm** |
| 双栏宽 | **7.16 inch ≈ 181.9 mm** |
| 字号 | 8–10 pt |
| 推荐字体 | **Times New Roman**（衬线）；图内可用 Helvetica/Arial |
| 矢量首选 | PDF / EPS |
| 位图 | **600 DPI**（线条图）/ 300 DPI（照片/灰度图） |
| 黑白可读 | **明确要求**——彩色图要在灰度下仍能区分类别 |
| 子图标签 | (a) (b) (c) 小写带括号 |

**坑**：IEEE 对**黑白可读**抠得很死——会议印刷常黑白印。**线型 + marker + 颜色三重冗余**编码是必须的。

参考：[IEEE Author Tools](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/)

---

## Elsevier 系列

涵盖 *Cell* / *Neuron* / *Cell Reports* / Elsevier 旗下大多数期刊。

| 维度 | 要求 |
|---|---|
| 单栏宽 | **90 mm ≈ 3.54 inch** |
| 1.5 栏宽 | 140 mm ≈ 5.5 inch |
| 双栏宽 | **190 mm ≈ 7.48 inch** |
| 字号 | 7–9 pt |
| 推荐字体 | Helvetica / Arial（无衬线） |
| 矢量首选 | EPS / PDF |
| 位图 | **300 DPI（彩色 + 灰度）**；线条图 1000 DPI |
| 子图标签 | (A) (B) (C) 大写带括号 |
| 颜色 | RGB；color blind safe |

参考：[Elsevier Artwork Guidelines](https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions)

---

## PNAS

| 维度 | 要求 |
|---|---|
| 单栏宽 | **8.7 cm ≈ 3.42 inch** |
| 1.5 栏宽 | **11.4 cm ≈ 4.5 inch** |
| 双栏宽 | **17.8 cm ≈ 7.0 inch** |
| 字号 | 6–8 pt |
| 推荐字体 | Helvetica / Arial / Times（衬线无衬线都接受） |
| 矢量首选 | PDF / EPS |
| 位图 | 300 DPI（彩色） / 600 DPI（黑白） |
| 子图标签 | (A) (B) (C) |

---

## 中文核心期刊通用要求

适用于 *中国科学* 系列、*物理学报*、*中华医学杂志*、各 EI 核心、中文 CCF B/C 类期刊等。**具体期刊以投稿须知为准**——以下是通用约定。

| 维度 | 通用要求 |
|---|---|
| 单栏宽 | **8 cm ≈ 3.15 inch** |
| 双栏宽 | **17 cm ≈ 6.7 inch** |
| 字号 | 中文 6 号（≈8 pt）/ 小 5 号（≈9 pt） |
| 字体 | **中文宋体 + 西文/数字 Times New Roman** 混排 |
| 矢量 | EPS / PDF（部分接受 TIFF） |
| 位图 | **>= 600 DPI**（线条图）/ 300 DPI（照片） |
| 颜色 | 部分期刊只接受黑白图，投稿须知必看 |
| 子图标签 | (a) (b) (c) 或 (甲) (乙) (丙)，与期刊样例一致 |

**坑 1**：中文期刊的 EPS 上传后预览常出方框——出图时务必用 `setup_style(lang='zh', serif_for_zh=True)` 走宋体类字体，且 `savefig` 用 PDF 而非 EPS（EPS 对 TrueType 中文支持差）。

**坑 2**：数字、变量名、单位**必须**走 Times New Roman（西文衬线），不能用中文宋体——这是排版规范。

---

## 跨期刊速查表

| 期刊 | 单栏 (inch) | 双栏 (inch) | 字号 (pt) | 推荐字体 | DPI | 矢量首选 |
|---|---|---|---|---|---|---|
| Nature | 3.5 | 7.2 | 5–7 | Helvetica/Arial | 300+ | EPS/PDF |
| Science | 2.2 | 7.2 | 5–7 | Helvetica/Arial | 300+ | PDF/EPS |
| IEEE | 3.5 | 7.16 | 8–10 | Times | 600 | PDF/EPS |
| Elsevier | 3.54 | 7.48 | 7–9 | Helvetica/Arial | 300+ | EPS/PDF |
| PNAS | 3.42 | 7.0 | 6–8 | Helvetica/Times | 300+ | PDF/EPS |
| 中文核心 | 3.15 | 6.7 | 8–9 | 宋体+TNR | 600 | PDF |

---

## 中文字体安装指南

`setup_style(lang='zh')` 会按优先级查找：

```
Noto Sans CJK SC  >  Source Han Sans SC  >  SimHei  >  Microsoft YaHei
```

宋体混排（`serif_for_zh=True`）时优先：

```
Noto Serif CJK SC  >  Source Han Serif SC  >  SimSun  >  STSong
```

如果一个都没有，会抛出清晰的安装指南而不是默默出方框。手动安装方法：

### Linux

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra

# Fedora / RHEL / CentOS
sudo dnf install google-noto-sans-cjk-fonts google-noto-serif-cjk-fonts

# 安装后刷新 matplotlib 字体缓存
python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"
```

### macOS

```bash
# 推荐：Homebrew Cask
brew install --cask font-noto-sans-cjk-sc font-noto-serif-cjk-sc

# 或手动从 Google Fonts / Adobe 下载
# https://fonts.google.com/noto/specimen/Noto+Sans+SC
```

macOS 本身自带 PingFang SC / Heiti SC / Songti SC，已经够用。

### Windows

1. 去 https://github.com/notofonts/noto-cjk/releases 下载 `Noto_Sans_CJK_SC.zip`
2. 解压，全选 `.otf`/`.ttf` 文件，右键 **"为所有用户安装"**
3. 重启 Python，**或** 删 matplotlib 缓存：
   ```bash
   python -c "import matplotlib; print(matplotlib.get_cachedir())"
   # 把那个目录里的 fontlist*.json 删掉
   ```

Windows 自带 SimHei / SimSun / Microsoft YaHei，最低限度也够用。

### 验证

```bash
python scripts/setup_style.py --list-fonts
```

应该列出可用 CJK 字体。如果列表空，说明缓存没刷新——按上面的方法清缓存重试。

---

## 不同期刊的提交检查工具

- **Nature**：[NPP](https://npp.nature.com/) 投稿系统会自动检 DPI / 尺寸 / 字号
- **IEEE**：[IEEE PDF Express](https://ieee-pdf-express.org/) 检查 PDF 嵌入字体
- **Elsevier**：投稿系统的 PDF Builder 会重新生成 PDF
- **arXiv**：本身宽松，但 EPS/PDF 字体未嵌入会被预览渲染成方块
