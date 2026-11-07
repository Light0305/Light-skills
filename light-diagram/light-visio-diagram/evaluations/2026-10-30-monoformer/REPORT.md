# MonoFormer：复杂架构全流程实测

2026-10-30。用户要求参照上传的复杂 CV 架构图，先用 `light-diagram-prompt` 写提示词，实际生成同类图，再测试 Visio 复现。本轮确实完成了提示词、两次内置生图调用、原生重建、保存重开及导出查看；没有仅以文档检查代替运行。

主交付：[monoformer-final.vsdx](monoformer-final.vsdx)，含按图复现和科学关系修正两页；用于后续编辑优先查看第 2 页。另有 [PDF](monoformer-final.pdf)、[复现 PNG](monoformer-final-replica.png)、[修正版 PNG](monoformer-final-corrected.png) 及同名 SVG。[交互对照页](../index.html) 展示生成图与 Visio 导出。

## 提示词与依据

- [prompt-v1.txt](prompt-v1.txt)：从本地 `light-diagram-prompt` 的流程、结构说明、领域语言和检查清单形成的完整生图提示词。
- [prompt-v2-edit.txt](prompt-v2-edit.txt)：实际查看第一版后写的完整编辑提示词。
- [image-v1.png](image-v1.png)、[image-v2-edit.png](image-v2-edit.png)：两次内置 imagegen 的原始输出，均未人工修改。
- [style-reference.jpg](style-reference.jpg)：用户上传的视觉参考；提炼了斜视特征平面、四级跨层融合和模块放大等表达方式。新图第一次调用仅传完整提示词，第二次编辑以 image-v1 为目标。
- [BRIEF.md](BRIEF.md)：图意、范围和主要连接；[source-manifest.json](source-manifest.json)：来源与执行信息；[verification.json](verification.json)：文件哈希及实际检查。

科学依据是 Bae、Moon、Im 的 [Deep Digging into the Generalization of Self-Supervised Monocular Depth Estimation](https://arxiv.org/html/2205.11083v3)，读取了第 3.1–3.3 节及 Figure 1；门控顺序还核对了作者 [blocks.py 中 GCT 实现](https://github.com/sjg02122/MonoFormer/blob/main/monoformer/networks/depth/blocks.py)。图中输入街景和深度输出块均为示意，不是真实照片或论文预测结果。未生成性能数据、训练损失或真实张量值。

## 生图检查：有改善，仍未全部通过

| 版本 | 实际观察 | 判定 |
| --- | --- | --- |
| v1 | 四级主体和放大模块齐全；Transformer inset 漏掉 MSA 前 Norm，Output 箭头反向；主图 X 状态在装饰平面附近重复 | 科学关系验收未通过 |
| v2 edit | 补回 Norm，Output 和门控主链方向改善，重复 X 标注移除；仍保留从 Attention Reweighting 到最终加法的错误旁路、两处残差源的反向箭头头部，以及部分 ACM 输出悬空/跳连竖线重叠歧义 | 科学关系验收仍未通过 |

本轮到两次调用后转入可编辑重建，没有用无限生图掩盖问题。底层模型版本、种子与调用费用未返回，不作推断。科学错误没有被漂亮版式抵消，也没有因为后续能修正就改记成生图通过。

## Visio 重建及分开的修正版

| 项目 | 第 1 页：按生成图复现 | 第 2 页：科学关系修正 |
| --- | ---: | ---: |
| 原生形状 | 417 | 411 |
| 关系线 | 81 | 80 |
| 保存后重开的粘附端点 | 162 / 162 | 160 / 160 |
| 文字值、箭头样式检查差异 | 0 | 0 |
| 临时移动及恢复 | image_frame 的相邻端点通过 | image_frame 的相邻端点通过 |
| 栅格素材 | 0 | 0 |

特征平面、网格、前/侧面、示意街景、模块、符号和文字均为原生对象。SVG 无 image 元素，PDF 为两页且可提取文字。记录见 [monoformer-final.audit.json](monoformer-final.audit.json)。移位测试只覆盖每页一个代表节点；全部关系线均核对保存后的粘附与箭头样式。

第 1 页保留源图问题，其中可见悬空箭头用透明代理端点表示：结构审计可以通过，但这不意味着科学关系正确。第 2 页明确作出以下修改，未暗中替换复现页：

1. 删除从 Conv 和 X 合流之前的 Attention Reweighting 到最终加法的额外旁路。
2. 去掉 Transformer 第二残差和 FFD 残差起点的不应存在的反向箭头，保留正确终点。
3. 将四条悬空 ACM 下支输出接回同级第二注意力平面，保持各级独立。
4. 删除具有跨级混接歧义的连续竖直总线，保留四条独立的 Zi→ACM 路径。

修正版通过本例预设的四级模块、五个状态、残差初始化、同级跳连和门控来源检查，不等于证明完整网络实现等价。重复块有稳定内部 ID；相邻特征平面与 Transformer 侧端口表示同一个 Zi。

## 原生预览引导的改进

首次原生导出暴露了包围框端口落在斜面轮廓外、连线斜偏及 A_p 自动换行。按可见轮廓反算端口、调整文字框后再次生成最终文件并打开两页 PNG 检查。渲染器补充了多边形、起点箭头样式和保存后箭头校验；经验写入 skill 的张量架构参考说明。提示词检查也补充了状态绑定、独立层级与精确旁路来源。

复现页 [图像诊断](comparison-final.json)：整图 RGB 平均绝对误差 15.03 / 255，前景并集误差 31.29 / 255；深色像素在 3 像素容差内的召回 0.9460、精确率 0.9639。它们是定位诊断，不是“还原百分比”，也不评价科学正确性。

仍有明确差异：示意街景是原生几何近似，网格色彩、细小透视、字体、下标/斜体及渐变不与生成图逐像素相同。复合特征组件尚未自动分组，折线不保证自动正交避障。本例不能称为“1:1 完美还原”，也不能外推成全学科或多随机种子的成功率。

本轮由同一助手撰写、运行和目视复查，无独立盲评。`build_scene.py` 是人工测量该图的场景，不是自动识图系统。非 final 文件仅为迭代留档，不对应当前最终场景。
