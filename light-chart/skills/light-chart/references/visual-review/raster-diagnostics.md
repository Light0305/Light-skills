# 像素诊断的用途

`scripts/raster_diagnostics.py` 报告尺寸、长宽比、近白背景之外的占比与范围、相邻亮度变化。指定 reference 后，只有相同像素网格才报告通道差异；不自动对齐、裁剪或缩放。

这些量可发现意外空白、导出尺寸改变或大范围渲染变化。它们不会判断数据是否正确、三维结构是否有效、字体是否足够大，也不输出综合质量分或候选排名。

透明背景在计算前合成到白色；white_tolerance 明确记录。颜色主题、背景、抗锯齿与文本都影响结果，不能将占比或差异最小当成优化目标。

示例：`python scripts/raster_diagnostics.py candidate.png --reference control.png --out diagnostics.json`。与实际图片、任务说明和科学核对一起解释结果。
