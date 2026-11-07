# 工具研究和实测取舍

本轮读取的本地材料位于工作区 `Reference  Repositories/工具/PowerPoint/`。这些仓库是参考资料，没有为用户安装插件、改设置或使用其网络服务。下表描述本地快照，不是在线最新版能力声明。

| 材料 | 提炼的信息 | 此包使用方式 |
| --- | --- | --- |
| PptxGenJS/README.md | 文件级生成、原生形状/文字、母版和多端导入 | 参考能力边界；当前宿主要求 Artifact Tool，因此未用它制作本例 |
| Office-PowerPoint-MCP-Server/README.md | 基于 python-pptx 的文件操作、32 个工具、文字/图形检查 | 区分文件级检查与真实桌面行为；未安装/执行 |
| ppt-mcp/README.md、src/ppt_com/connectors.py、freeform.py | 实时 COM、连接点解析、原生 FreeformBuilder、曲线控制点 | 参考连接、曲线和固定目标文件的设计，当前脚本独立实现 |
| mcp-server-powerpoint/README.md | 实时 COM、导出后查看和已打开文档支持 | 采用真实 PowerPoint 导出与复查原则，未安装/执行该服务 |
| python-pptx/src/pptx/oxml/shapes/connector.py | 原生连接符的非可视属性、stCxn/endCxn 与几何顺序 | 核对 OOXML 结构；没有用 python-pptx 编写或修改成品 |
| Instrumenta/README.md | 对齐分布、统一圆角、分组、文字溢出与导出等人工精修工具 | 作为交付可编辑组件和后续精修的参考 |

当前实测链路：宿主自带 `@oai/artifact-tool` 生成原生路径与文本；`lxml` 定点补充 OOXML 连接点；Windows PowerPoint 16.0 用 COM 做可见精修、保存重开、实际连线移动和 PNG/PDF 导出；宿主 finalizer 验证文件包、布局和重新导入。

已发现并解决的兼容问题：

1. 自定义路径包装成 `p:cxnSp` 的候选在本机 PowerPoint 被拒绝打开。最终使用标准 `straightConnector1` 原生连接符，折线由透明原生拐点连接；不用一张 SVG 或普通路径冒充可连接关系。
2. 对该初稿用标准 ElementTree 重序列化 XML 后也出现打开失败。保留原命名空间作用域的 `lxml` 序列化可打开；仍以真实 PowerPoint 检验结果为准，不将命名空间细节推广成所有文件的通则。
3. Artifact Tool 全形状文字的字体字段是 `typeface`；`fontFamily` 在本例未写入预期字体。检查保存后原生字体，不凭传参成功推断生效。
4. PowerPoint 对水平/竖直线可能保存零宽或零高，它们是合法连接符；坐标还要考虑 `HorizontalFlip/VerticalFlip/Rotation`，不能仅由正宽高猜端点方向。
5. 源图与 PowerPoint 坐标统一按画布 px 表示，Office 文字点数为 px×0.75；无需沿用另一个应用的 DPI 字号换算。

`render_scene.mjs` 可用参数或 `ARTIFACT_TOOL_MODULE` 指定宿主模块；默认只探测当前用户已存在的 Codex 运行缓存。Node 包和 Python 扩展不存在时应给出具体缺失项，不自动联网安装。真实 PowerPoint 不可用时仍可提供候选 PPTX 和文件检查，但必须把桌面重开、渲染与随动标为未测试。

批量制作与可见制作不是同一件事。本包默认在桌面验证阶段打开可见窗口，并支持在第一次候选完成后立即显示它；`--hidden` 仅用于用户希望后台运行的情况。保留用户查看窗口，不调用整个应用的 Quit，也不关闭目标文件以外的演示文稿。
