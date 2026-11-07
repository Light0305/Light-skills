# 场景和运行

脚本依赖：Node.js 和可用的 `@oai/artifact-tool`；Python 3、`lxml`；桌面验证另需 Windows、PowerPoint 和 `pywin32`。对照诊断需 Pillow。使用宿主提供的运行环境，不在参考仓库安装插件或改其配置。

`render_scene.mjs` 将人工测量的 JSON 导出原生图形初稿。`attach_connectors.py` 补充可随尺寸缩放的自定义连接点，将语义折线转成原生连接符与透明拐点。`verify_powerpoint.py` 用真实 PowerPoint 保存重开、验证和导出。脚本拒绝覆盖已有成品及验证导出；迭代使用新文件名。已打开且有未保存修改的同名文件会被拒绝，先由用户保存或选择独立候选。

顶层 `schema_version: "1.0"`、`font`、`canvas: {width_px,height_px,pixels_per_inch}`、`provenance`、`pages`。scene 的 science-corrected 与 science_corrected 两种历史拼写均可读取，handoff 仍用 science_corrected。当前 PowerPoint 渲染以 CSS px/96 DPI 解释画布和字号；`pixels_per_inch` 保留输入元数据，不影响缩放。不可直接把 Visio 的英寸字号换算规则用于 PowerPoint。

每页含唯一 `slug`、`name`、`mode`、`nodes`、`paths`、`edges`。原点为左上，所有坐标以 px 表示。ID 以字母开头，随后只含字母、数字、下划线。保留 `__bend_N`、`__seg_N` 供连接补全器使用，场景作者不要使用这些后缀。

```json
{
  "schema_version": "1.0",
  "font": "Arial",
  "canvas": {"width_px": 800, "height_px": 400, "pixels_per_inch": 96},
  "provenance": {"source": "source.png", "source_sha256": "实际哈希", "scientific_source": "实际来源"},
  "pages": [{
    "name": "Reference reconstruction", "slug": "replica", "mode": "faithful",
    "nodes": [
      {"id":"input","type":"roundrect","bbox":[80,150,200,70],"text":"Input","radius_px":8,"style":{"fill":"#e0effd","stroke":"#27303b","font_px":24}},
      {"id":"output","type":"rect","bbox":[520,150,200,70],"text":"Output","style":{"fill":"#e0effd","stroke":"#27303b","font_px":24}}
    ],
    "paths": [],
    "edges": [{"id":"main","source":{"node":"input","anchor":[1,0.5]},"target":{"node":"output","anchor":[0,0.5]},"points":[[280,185],[520,185]],"arrow":13,"style":{"stroke":"#101010","stroke_px":2}}]
  }]
}
```

节点支持 `rect`、`roundrect`、`ellipse`、`junction`、`text`、`polygon`、`bezier`。`bbox` 为 `[x,y,w,h]`；多边形和贝塞尔用全画布 `points`。多边形至少三个顶点并重复首点；闭合三次贝塞尔为 3k+1 控制点并重复首点。

`style` 支持 `fill`、可选 `fill_secondary`（线性渐变）、`stroke`、`stroke_px`、`font_px`、`bold`、`text_color`、`align`（0/1/2）、`dash_pattern`（非零为虚线）。`none` 表示无填充或描边。默认加粗，明确需要普通文字时设 `bold:false`。纯文本用 `fill:none`、`stroke:none`。

节点可加 `subscript_start`（从 0 起至文字末尾）。`verify_powerpoint.py --apply-text-format` 为这些节点应用原生下标范围。`native_text_edit:true` 仅用于事先声明的字面修订，如 alpha→α；该选项只在显式格式处理时生效，普通验证不修正文案。

装饰路径有 `id`、`points`、`curve: polyline|bezier`、`style` 和可选 `arrow`、`begin_arrow`。开放贝塞尔为 3k+1 点，不闭合。语义 `edges` 另需 `source/target: {node,anchor:[u,v]}`，端点必须与归一化连接点相符，容差 0.2 px。语义折线按路径保留；语义贝塞尔需要显式声明 `native_curve_approximation: curvedConnector2|curvedConnector3`，用标准原生曲线连接符近似，不保证保持原控制点。未声明时脚本拒绝静默降级。曲线实体轮廓用 paths，可保留三次贝塞尔控制点。箭头 0 表示无，非零表示三角端点，此接口不复刻所有 Visio 箭头枚举。

默认绘制次序是 nodes、paths、edges。`draw_order` 可显式指定每个 ID 恰好一次。补全器为每条多段关系派生不可见拐点，`.connections.json` 中 `edge_parts` 保存逻辑边到连接符的映射。移动可见节点时对应线段随动；拐点不会自动避障或跟随整个模块组合。

在独立案例目录创建 `.build/` 和 `output/` 后运行（路径均替换为实际绝对路径）：

```powershell
& $runtimeNode $skill/scripts/render_scene.mjs $case/scene.json --validate-only
& $runtimeNode $skill/scripts/render_scene.mjs $case/scene.json $case/.build/draft-r1.pptx $artifactModule
python -X utf8 $skill/scripts/attach_connectors.py $case/scene.json $case/.build/draft-r1.pptx $case/.build/connected-r1.pptx
python -X utf8 $skill/scripts/verify_powerpoint.py $case/scene.json $case/.build/connected-r1.pptx $case/.build/connected-r1.pptx.connections.json $case/.build/roundtrip-r1.pptx $case/.build/native-r1 --apply-text-format
```

这些变量为示意，不固定个人安装路径。主机的 `presentations` 要求开始标记时，在首次制作前按其说明运行一次。用它提供的依赖发现工具获取运行路径；工具缺失时可查已安装运行包的 `runtime.json`，不要擅自安装替代依赖。

目视复查后，用主机的 finalizer 检查实际候选。`scripts/finalize_pptx.mjs` 接收 `scene candidate final presentations_skill_dir runtime_python`，需要 `RUNTIME_NODE_MODULES` 指向其依赖。最后用 `verify_powerpoint.py ... final.pptx ... final.pptx output/preview --verify-saved` 检查已保存的最终文件；此模式不重写 PPTX，默认保持可见。

## 用户观看制作

建立与图元库同尺寸的可见空白 PPTX 并保存为工作文件。`draw_visible.py library.pptx working.pptx library.pptx.connections.json scene.json --delay 0.38` 会逐个复制真正的原生对象，显示其选择状态，每 12 个对象保存进度，全部完成后按来源/目标名称接回连接符。目标文件必须是空白页，脚本不会清空已有内容。完成后保持窗口和工作文件，另留 `.drawing-log.json`。该流程使用系统剪贴板，操作期间避免用户同时复制粘贴；不宣称录制了视频。

复杂图可分区域运行。第一批只含已检查的区域和必要框架；后续图元库包含累计场景，以 `--append` 插入尚不存在的名称，保留已画对象并再次接回关系。各批保存场景快照和图元库。`--append` 不更新已存在对象的内容或层级；需要修正已有对象时进行明确编辑或使用新的空白工作文件，不能误以为再次运行会自动同步。避免同时运行两个可见插入进程。

离线 validate-only 在加载 authoring runtime 前执行；它检查输入结构、几何、样式和端点约束，不证明应用可运行。原生 audit 同时记录最终 PPTX、scene 与 connections 的哈希，跨阶段检查绑定当前文件。visible 插入拒绝同一来源/目标与未保存工作文件，并使用系统剪贴板。
