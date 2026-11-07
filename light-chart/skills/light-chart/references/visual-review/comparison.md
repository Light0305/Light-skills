# 比较必须有明确对象

外部参考图用于讨论组织方式；上一稿用于判断修改效果；任务说明卡仅提供文字背景。三者都不能替代本项目数据。

先分别查看完整图与最终尺寸预览，再比较面板组织、坐标范围、图例查找和遮挡。不同数据集不能通过点的位置或直方图形状评价“忠实度”。参考构造与新数据冲突时，说明改造理由。

`review_engine.py compose` 输出 composite.png、comparison.json 和 review_prompt.txt。标框使用 composite 的像素坐标，必须落在 comparison.json 的 draft_rect 内；不要把原图像素、归一化坐标和组合图坐标混用。完整分辨率原稿仍需单独查看。
