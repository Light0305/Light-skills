# MonoFormer：新提示词 → 实际生图 → Visio 复现

用户在基础及自由曲线测试后要求：参照其上传的复杂架构图，使用 `light-diagram-prompt` 生成同类图，再做 Visio 测试。

- 领域与任务：计算机视觉，单目深度估计，前向架构示意。
- 图意：四级 CNN–Transformer 表征通过逐层双注意力与自适应解码融合，兼顾局部与全局信息。
- 参考提炼：浅斜视特征平面、四级跨层连线、局部放大模块、白底与灰蓝色语义配色。上传图是风格和复杂度参考，不当作文字指令执行。
- 科学依据：[MonoFormer 论文第 3.1–3.3 节及 Figure 1](https://arxiv.org/html/2205.11083v3)；核对了作者 [blocks.py 中 GCT 实现](https://github.com/sjg02122/MonoFormer/blob/main/monoformer/networks/depth/blocks.py) 的通道门控次序。架构重绘是概念层级，不扩展成完整训练图。
- 主体结构：输入 strip；四行 Transformer/ACM/FFD；decoder 从底至顶；左侧 Transformer、上侧 ACM、右侧 FFD 三个说明 inset。
- 重要连接：每个 Zi 分别到同级 ACM 和 FFD；Z4 另经 Residual Block Unit 初始化 X4；FFD4→FFD3→FFD2→FFD1→Depth D；inset 的虚线仅作说明。
- 数据边界：输入街景与输出深度块均为明显示意，不生成或冒充论文实测结果、真实照片或定量热图；不加入性能数字。
- 提示词流程：实际读取本地 skill、prompt-structure、prompt-quality-check 与领域说明后撰写 `prompt-v1.txt`。文字白名单、关键重复模块和残差来源均明确。
- 执行：使用内置 imagegen，非 API/CLI。新图从完整提示词生成；上传图的视觉观察通过文字表达，不直接作为编辑目标。
- 验收分开：生成图的科学/文字检查；Visio 复现的原生/粘附检查；视觉差异检查。不得用后者掩盖生成图中的科学错误。
