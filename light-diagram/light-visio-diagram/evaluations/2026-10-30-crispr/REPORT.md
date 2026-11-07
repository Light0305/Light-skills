# CRISPR–Cas9：自由轮廓与分子曲线进阶实测

2026-10-30；Windows、Python 3.11.13、桌面 Visio 16.0。此例是在用户要求增加难度后追加的真实重建测试，覆盖不规则蛋白轮廓、多段曲线、链连续性、配对线、剪切缺口、标注与遮挡。

交付：[crispr-final.vsdx](crispr-final.vsdx)、[PNG](crispr-final-replica.png)、[SVG](crispr-final-replica.svg)、[PDF](crispr-final.pdf)。[交互对照页](../index.html) 展示原图和实际导出，也可调透明度叠加。

## 来源与科研范围

参考是前一轮 `light-diagram-prompt` 实际生成的 `02-crispr/image-v3.png`，不是 Jinek 论文原图。已原样保存为 `source.png`，路径和哈希见 [source-manifest.json](source-manifest.json)。

科学关系按 Jinek et al., 2012, DOI [10.1126/science.1225829](https://doi.org/10.1126/science.1225829) 的体外切割范围核查；实际读取了[论文 PDF](https://computingbiology.github.io/docs/jinek2012.pdf) 的摘要及核酸酶段落。保留双 RNA 与嵌合 RNA 两种替代输入，HNH 指向互补 DNA 链切口，RuvC-like 指向非互补链切口。不新增细胞修复结果、PAM、序列方向或原子结构信息。

## 实际结果

| 项目 | 结果 |
| --- | --- |
| 原生对象 | 136：21 个节点、108 个几何路径、7 条关系连线 |
| 文件内原生 NURBS 曲线行 | 33；来自三次贝塞尔轮廓与路径 |
| 嵌入栅格文件 / SVG image 元素 | 0 / 0 |
| 保存、关闭、重新打开 | 已完成 |
| 关系线端点粘附 | 14 / 14 通过 |
| 节点文字值差异 | 0；PDF 可提取 9 条标签 |
| 实际移动及还原 | dual_card 的 1 个曲线箭头端点随动并恢复 |
| PNG / PDF | 1536 × 1024；PDF 一页 |

记录：[crispr-final.audit.json](crispr-final.audit.json)、[verification.json](verification.json)。蛋白外轮廓、HNH/RuvC-like 区域、RNA/DNA 骨架、配对线、切口符号与文字均为 Visio 原生对象。没有调用新的生图服务，也没有把参考图或局部截图嵌入页面。

几何检查确认：上方两条 RNA 的自由端独立；下方嵌合 RNA 两色段端点重合；中央 guide 与 scaffold 端点重合；两条 DNA 在切割位置均有实际几何缺口。此检查不表示核酸序列或蛋白构象真实。

## 从实际预览发现并修复的问题

1. 第一版 DNA 标注圆点被后画的骨架遮住。渲染器增加显式 `draw_order`，把圆点放在骨架上方，再重导出检查。
2. Noncomplementary strand 第一版自动换成两行。扩大文字框并降低字号，最终预览恢复单行。
3. 新增原生三次贝塞尔与闭合轮廓支持，使用真实 `DrawBezier(..., 3, ...)`；不把曲线悄悄替换成细折线。

这些经验已写回 skill 与自由曲线参考说明。最终 PNG 已实际打开检查。

## 忠实度与可编辑范围

整体构图、蛋白轮廓、RNA 卡片、DNA 路径、切口与标签接近参考图；光滑渐变和双色描边只能近似原图的蛋白表面纹理及圆管高光，DNA 左侧交叉也存在控制点近似。字体、细小配对线位置与若干箭头外观仍有差异，因此该例通过原生结构和关键概念检查，**没有通过逐像素 1:1 复现验收**。

图像诊断见 [comparison-final.json](comparison-final.json)：整图 RGB 平均绝对误差 8.20 / 255，前景并集误差 40.51 / 255；深色像素的 3 像素容差召回 0.9546、精确率 0.9378。原图白底较多，整图误差小不能掩盖局部质感差异；这些指标不是还原百分比。

当前各轮廓与骨架可分别编辑，复合生物组件尚未自动分组。拖动一个组件的边框不保证其全部内部曲线一起移动。关系箭头做了粘附检查，核酸骨架作为实体几何保留。复杂纹理、真实三维结构、多区室反馈通路和高密度跨面板关系尚未由本例验证。

此例为人工测量与控制点描绘，非自动图像识别。`build_scene.py` 只用于重建此例场景；非 final 文件为本次保留的迭代输出。
