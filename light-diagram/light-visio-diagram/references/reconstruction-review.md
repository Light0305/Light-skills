# 实现与复查笔记

本 skill 学习了用户在 `Reference  Repositories/工具` 提供的 Visio 参考实现，没有把这些仓库作为运行依赖，也未调用其模型或付费接口。

## 已采纳的实用模式

| 本地参考 | 采用的思路 | 本 skill 的处理 |
| --- | --- | --- |
| `Visio/Visiomaster-main` | 图片拆成场景，保留来源，原生形状渲染及导出复查 | 手工测量场景；不将本案例包装成自动识图 |
| `Visio/Visio-Illustrator/plugins/visio-scientific-illustrator` | 原生组件、文字与粘附连线，保存后重开 | 实际检查每条边的 BeginX/EndX 连接对象 |
| `Visio/codex-visio-paper-figure-skill-main` | 以像素作为中间坐标，明确页面尺寸 | 统一在渲染边界转换坐标及文字尺度 |
| `Visio/visio-skill-main` | JSON 描述和确定性绘制 | 场景校验与 Visio 渲染分开，离线也能检查关系端点 |
| `Visio/VisPainter` | 设计、渲染、查看结果再修改 | 从实际导出的图片判断完成度 |
| `Visio/Office-Visio-MCP-Server` | 桌面 Visio 自动化能力 | 精确路径使用本机 COM；不接管用户现有实例 |

路径按参考工具根目录解释；这些是研究来源，复制 skill 到其他机器时无需携带它们。

## 本机执行得到的约束

- `DrawPolyline` 的 pywin32 调用使用普通浮点列表；本环境的手工包装 SAFEARRAY 调用失败。
- `DrawPolyline` 初始产生二维形状。语义线需先设 `OneD = 1` 再 `GlueToPos`；不能只看见箭头就认定是连接线。
- 形状使用 `NameU`，连接对象返回的 `Cell` 用 `Name`；`Cell.NameU` 在本机 Visio 16.0 类型库不存在。
- 通过 `DispatchEx` 创建本次专属 Visio 实例。失败时只清理该实例，避免影响已打开的用户文档。
- PNG 尺寸通过 `Application.Settings.SetRasterExportSize(3, width, height, 0)` 设置；参见 [Microsoft 官方 API 文档](https://learn.microsoft.com/en-us/office/vba/api/visio.applicationsettings.setrasterexportsize)。实际导出尺寸仍需检查。

这些是经过本机测试的实现选择，并非所有工具或版本的通用限制。

## 复现与科学修正的区别

首次测试使用之前实际生图得到的 Transformer 架构图，来源可追溯到 `light-diagram-prompt` 的测试目录。它不是论文原图。对照 [Attention Is All You Need 第 3.1、3.2.3 节](https://arxiv.org/html/1706.03762v7)，encoder memory 的 K,V 进入 cross-attention，其后的 Add & Norm 接收该子层输出和 decoder 残差。原生成图额外把 K,V 线分支接入该 Add & Norm；这是本次科学修正版删除的一条边。

复现页保留原图可见关系，修正版删除该边，其余布局一致。两页的区别必须记录在场景和交付说明中。删除一条错误边不等于已证明整个模型图覆盖所有实现细节；本案例仍是简化架构示意。
