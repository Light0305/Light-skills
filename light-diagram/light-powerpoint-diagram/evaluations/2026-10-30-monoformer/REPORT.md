# MonoFormer：PowerPoint 复杂图复现实测

2026-10-30。采用前一轮 `light-diagram-prompt` 实际生成的 MonoFormer 图作为相同参考，便于与 Visio 路径比较。本轮没有新增生图调用。

交付：[可编辑 PPTX](output/monoformer-final.pptx)、[复现 PNG](output/monoformer-replica.png)、[修正版 PNG](output/monoformer-corrected.png)、[PDF](output/monoformer.pdf)、[交互对照](../index.html)。PowerPoint 窗口已显示最终文件；后续精修和验证采用可见窗口。

## 来源和范围

`source.png` 与前轮 `light-visio-diagram/evaluations/2026-10-30-monoformer/image-v2-edit.png` 同字节，SHA256 为 `8008113dacc2fdc830ba0eabdfdc54a580b5fe1b245f17d6d6584b7c79a085c2`。场景复用前轮人工测量坐标，补充原生下标和希腊字母排版，不把它称为自动识图。

科学依据沿用已读取的 Bae、Moon、Im 论文 [Deep Digging into the Generalization of Self-Supervised Monocular Depth Estimation](https://arxiv.org/html/2205.11083v3) 第 3.1–3.3 节与 Figure 1，以及作者 [GCT 实现](https://github.com/sjg02122/MonoFormer/blob/main/monoformer/networks/depth/blocks.py)。源图仍有已知科学关系错误，不能因为 PPTX 可编辑而改记成生图科学验收通过。

## 实际结果

| 检查 | 按图复现 | 科学关系修正 |
| --- | ---: | ---: |
| 原生对象，含透明辅助拐点 | 465 | 471 |
| 场景语义关系 | 81 | 80 |
| 原生连接符段数 | 105 | 110 |
| 保存重开后已连接的线段端点 | 210 / 210 | 220 / 220 |
| 实际临时移动并恢复的场景节点 | 76 | 72 |
| 随这些节点移动的场景端点 | 162 | 160 |
| 原生文字对象 | 63 | 63 |
| 嵌入图片 | 0 | 0 |

各节点移动 10×5 px，测量连接符实际端点的同量位移并恢复，误差阈值 0.1 pt。所有原生连接符另核对两端节点及方向。原场景部分透明代理点用于忠实保留源图的悬空箭头；它们不代表真实科学组件。新增透明拐点用于保留走线路径，修正版连接更长，因此原生对象数略多。

两页均实际在桌面 PowerPoint 16.0 保存、关闭、重新打开并导出。字面文字、字体、文本容纳、箭头及连接均通过脚本检查；PNG 两页均为 1774×887，PDF 两页各可提取 67 行文字。最终文件再次在可见窗口验证，见 [原生审计](output/monoformer.audit.json) 与 [结果检查](verification.json)。

第 2 页删除错误的 pre-Conv attention→最终加法旁路；去掉两处残差源的反向箭头；四级 ACM 下支接回同级注意力平面；移除混接竖直总线。对这些已声明概念关系及四级状态逐项检查通过，不等于证明完整网络实现等价。

## 从实测得到的改进

初稿由宿主 Artifact Tool 创建原生路径和文字。把任意自定义路径直接包装成原生连接符的候选被桌面 PowerPoint 拒绝打开；改成标准连接符分段，并在拐点处使用透明原生连接点，成功保存重开。还修复了字体字段、XML 序列化兼容、过小箭头与下标排版。具体写入 [工具研究](../../references/tools-and-runtime.md) 和脚本，没有安装参考仓库中的服务。

宿主文件检查通过，保留 8 条包围框相交提示：两页中 X4 标签框与初始化残差路线，以及右侧残差竖线与三个较宽希腊字母标签框相交。逐页查看原生导出后，实际线段没有穿过可见字形；这些提示作为已复查诊断保留，没有声称零告警。

[图像诊断](comparison-final.json)：整图 RGB 平均绝对误差 15.55/255，前景并集误差 32.59/255；深色像素在 3 px 容差内召回 0.9524、精确率 0.9683。这些不是还原百分比，不能评价科学正确性，也不能单独决定 PowerPoint 与 Visio 谁更好。

尚有限制：街景为原生几何示意，细小配色、纹理、字体、梯度和排版有近似；折线路径由多段连接符组成，透明拐点不自动避障；未测试复合组件整体分组、任意缩放旋转或 Keynote/Google Slides 导入。该例由同一助手制作、运行和目视复查，没有独立盲评，不能外推全学科成功率或称为 1:1 完美还原。

制作场景和脚本随包保留；`.build/` 为迭代与文件校验记录，`output/` 为当前交付。
