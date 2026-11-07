# 运行环境与工具选择

本包 2026-10-30 在 Windows、Python 3.11 + pywin32、Adobe Illustrator 2026 / `30.0.0` / `Illustrator.Application.30` 实测。渲染与原生检查不依赖第三方绘图库。Pillow 用于预览尺寸/像素诊断，PyMuPDF 用于 PDF 文字与图片核对。其他 Illustrator 版本和 macOS 桥接未实测，不应把此 COM 命令作为跨平台接口。

## 本地参考仓库研究

本轮只读 `Reference  Repositories/工具/Illustrator/`，没有安装、运行其服务或修改配置。以下用途区分仓库声明与本轮结果；未将仓库宣传的测试覆盖算成本包覆盖。

| 参考 | 学到的适用点 | 本轮取舍 |
| --- | --- | --- |
| `scientific-illustrator-agent` README、renderer、COM bridge | 结构化场景、Windows COM/JSX、文字与命名对象回读；基础 FigureSpec 主要覆盖简单图元 | 自行实现曲线、复合路径和原生检查，不复制其未授权发布的实现 |
| `illustrator-mcp-server` README | 文档、路径、文字、导出工具及已有文件保护 | 当前会话未提供 Illustrator MCP，采用现有桌面 COM；没有替用户安装服务 |
| `illustrator-mcp` README | 用 ExtendScript 连接桌面 Illustrator 的基本路线 | 只研究桥接模式，未启动其后台服务 |
| `cell-lct` 的 Illustrator runtime reference | 真正逐对象创建、堆叠顺序、曲线控制柄与可见过程的区别 | 没有使用它的隐藏 SVG 导入路线；本包直接从人工场景创建，也不继承其只支持纯色的限制 |
| `illustrator-scripting-guide` PathItem / PathPoint / Gradient / CompoundPathItem / ExportOptionsSVG 等 | 路径、渐变、复合开口与导出 API | 结合本机小样和完整图验证；文档示例不是执行证据 |
| `Types-for-Adobe` README | 类型定义可辅助开发，但版本与字典可能不完全准确 | 不把能编译当作 Illustrator 实测 |
| `creold-illustrator-scripts`、`joshbduncan-illustrator-scripts` README | 丰富的路径、对齐、图层、文字脚本目录 | 作为手工优化参考；未批量执行或整包移植 |

Adobe 的 [开发者入口](https://developer.adobe.com/illustrator/) 说明 JavaScript 等脚本及路径/文字自动化路线；[运行脚本说明](https://helpx.adobe.com/illustrator/desktop/automate-visualize-data/automate-actions/install-and-run-scripts.html) 提供桌面脚本入口。API 细节另查本地手册或 [Illustrator Scripting Guide](https://ai-scripting.docsforadobe.dev/)。

## 本机发现的问题

- Illustrator 30 的 ExtendScript 中 `JSON` 未定义。运行时使用自有 ES3 序列化器；场景 JSON 在 Python 先验证，再由 JSX 读入。本包仅执行本地作者编写和检查的场景，不是任意第三方脚本执行服务。
- 某些 Unicode 下标字符在 Arial-BoldMT 中显示缺字框，即使 `TextFrame.contents` 正确。改用普通数字与 `FontBaselineOption.SUBSCRIPT`；平衡箭头 `⇌` 用声明的 CambriaMath 字体范围，小样和最终图都要目视检查。
- 原生文本框的几何框可能受下标和混合字体的行度量影响，远大于实际字形。运行时临时复制文本并描边测量字形边界，随后删除该副本；交付文字仍是 TextFrame。
- 设置复合路径负绕向后，保存重开可能调整锚点顺序。几何检查允许闭合轮廓循环平移和整体绕向反转，并同步比对左右控制柄；开放语义路径仍保留方向。
- 实测发现未加括号的连续三元条件表达式在该引擎中没有按预期分支，导致左对齐标题被居中。排版改用显式 `if/else`，增加实际字形位置检查；只验宽高容纳会漏掉此问题。
- 复杂图中反复遍历原生对象集合查名字代价高。检查时先缓存实际对象名再回读几何，缓存只用于本次已打开文档，重开后不复用旧引用。
- 不依赖 `GradientColor.angle` 改方向。当前实测渲染器用原点和长度创建水平线性或径向渐变；其他方向需增加矩阵处理并实测。

## 文档与失败处理

脚本只创建新文件。`verify` 按指定 AI 路径查找文档，存在未保存编辑则保留并停止；否则关闭该文件后重开检查。移动探测不保存回 AI。PDF `saveAs` 会改变打开文档身份；实现使用不同路径的 AI 字节副本导出 PDF，不能把再次 open 同一 AI 当成创建独立文档。此修订的实际验证范围见[本轮升级记录](../../evaluations/2026-11-06-upgrade.md)，未经成功运行不称已修复桌面故障。

`.verify-progress.json` 标明实际进入的验证阶段，`.failure.json` 保留原生或桥接失败；COM 断开可能发生在 JSX 日志写入之前。没有成功 audit 就不能用已有 PNG/PDF 推断验证完成。先核对保存文件、哈希、应用状态与已有产物，再决定是否有必要以新 stem 继续；不要自动关闭或重启用户应用。

不会退出 Illustrator，不会关闭无关文档。若出现忙碌、模态窗口、COM 拒绝或原生错误，先检查 UI 与失败日志，保留已创建工作；避免盲目重复绘制。可见绘制依赖当前交互桌面，窗口置前受系统限制时不能宣称已置前成功。
