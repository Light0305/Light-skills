# Transformer：基础复现实测

2026-10-30；Windows、Python 3.11.13、桌面 Visio 16.0。实际绘制、保存、重开、导出并查看 PNG，非仅文档检查。

交付主文件：[transformer-final.vsdx](transformer-final.vsdx)，含原图复现和科学关系修正两页。另有 [PDF](transformer-final.pdf)、[复现 PNG](transformer-final-replica.png)、[修正版 PNG](transformer-final-corrected.png) 和同名 SVG。[交互对照页](../index.html) 可调透明度比较。

## 参考与范围

参考为前一轮 `light-diagram-prompt` 实际生成的 `image-v4-edit.png`，并非论文原图。本目录的 `source.png` 是该文件的原样副本；原路径、SHA-256 和论文信息在 [source-manifest.json](source-manifest.json)。

科研依据为 Vaswani et al. 的 [Attention Is All You Need，第 3.1、3.2.3 节](https://arxiv.org/html/1706.03762v7)。仅核对架构概览，不扩展成完整实现图。复现页保留参考图从 K,V 路径分支进入 Decoder 中间 Add & Norm 的额外连接；修正版只删除 `extra_memory_to_norm`，保留五条子层残差路径。两页其余场景相同。

## 实测证据

| 项目 | 原图复现 | 科学关系修正 |
| --- | ---: | ---: |
| 原生形状 | 69 | 68 |
| 关系连线 | 30 | 29 |
| 保存后重开的粘附端点 | 60 / 60 | 58 / 58 |
| 文字值差异 | 0 | 0 |
| 临时移动节点及还原 | enc_norm2；3 个相邻端点通过 | enc_norm2；3 个相邻端点通过 |
| PNG 尺寸 | 1536 × 1024 | 1536 × 1024 |

压缩包内无媒体文件，SVG 内无 image 元素。PDF 共两页，文字可提取。原生对象包括文字、圆角矩形、圆、折线和括号，不是整图嵌入。完整记录：[transformer-final.audit.json](transformer-final.audit.json)、[verification.json](verification.json)。

复现页图像诊断：[comparison-final.json](comparison-final.json)。整图 RGB 平均绝对误差为 9.49 / 255；排除大面积白底后的前景并集误差为 28.19 / 255。容差 3 像素的深色像素召回为 0.9858、精确率为 0.9819。这些值不能解释为“还原了 98%”，也不验证科研关系。

## 观察、修订与边界

第一版字体明显偏窄，改为 Arial 并重新调整字号；补回加号上方的箭头，使用可编辑渐变近似参考配色。最终 PNG 已逐页打开检查。

总体布局、标签、模块位置和路径接近参考图；字体笔画、渐变纹理、括号形状与若干箭头细节仍不同，不称为逐像素完美复现。连线粘附有效，但多折点线不提供自动正交避障保证。每页只对一个代表节点做了实际移动；所有关系线均做了保存后粘附核查。

`scene.json` 是人工测量场景，`build_scene.py` 仅重建该案例的输入，不具备自动识图能力。基础例不能代表跨领域复杂图已全部验证。较难的自由曲线测试见 [CRISPR 记录](../2026-10-30-crispr/REPORT.md)。非 final 文件为本次保留的迭代输出。
