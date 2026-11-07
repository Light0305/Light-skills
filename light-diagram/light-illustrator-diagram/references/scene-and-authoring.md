# 场景与原生制作

`scripts/illustrator.py` 是 Windows 桥接与输入验证；`scripts/runtime.jsx` 负责 Illustrator 内实际创建、保存、重开、检查和导出。脚本不做 OCR、位图自动描摹或生图。当前输入是一场景一画板；需要多画板时分别组织场景或扩展原生制作，并验证对应画板。

## 几何单位和对象

顶层包含 `schema_version: "1.1"`、`font`、`font_bold`、`points_per_pixel`、`canvas`、`layers`、`groups`、`pages`。字号及几何以左上原点 px 记录；默认 `points_per_pixel: 0.75`，转换到 Illustrator 时 `[x,y] → [0.75x, Hpt−0.75y]`。因此 1536 × 1024 px 参考对应 1152 × 768 pt，PNG 以 133⅓% 导出恢复参考尺寸。

字体填写实际 PostScript 名，如 `ArialMT`、`Arial-BoldMT`。`layers` 按从底到顶列出 `{id,name}`；`groups` 是 `{id,layer,test_move?}`，存为原生 `LD_GROUP_<id>`。

每页含 `name`、`nodes`、`paths`、`edges`、`draw_order`。所有对象 ID 唯一，格式为字母起始的字母/数字/下划线；每个对象明确 `group`。`draw_order` 必须列出每个对象恰好一次。分组会改变组间堆叠，因此先确定可独立分组的区域，不把相互交错的透明层随意合组。

节点可用 `rect`、`roundrect`、`ellipse`、`junction`、`text`、`polygon`、`bezier`、`compound`。统一 `bbox: [x,y,w,h]`；圆角可加 `radius_px`。多边形点列闭合并重复首点；三次贝塞尔点列为 `P0,C1,C2,P1,...`，共 3k+1 点，实体曲线首尾相同。复合路径含 `contours: [{curve,points},...]`，首轮廓为外壳，其余为实际开口，原生回读检查轮廓几何。

`style` 支持 `fill`、`fill_secondary`、`gradient_type: linear|radial`、`stroke`、`stroke_px`、`font_px`、`bold`、`text_color`、`align: 0|1|2`、`dash_pattern` 和 `opacity`。颜色为六位十六进制或 `none`；当前线性渐变为水平方向。纯文本不需生成背景路径。

文字由 `text` 保存参考语义；当字形需原生排版时，另加 `native_text` 与 `text_runs`，例如：

```json
{"id":"sulfide","type":"text","group":"b","bbox":[100,80,160,40],"text":"Li₂S","native_text":"Li2S","text_runs":[{"start":2,"length":1,"baseline":"subscript"}],"style":{"font_px":24,"bold":true}}
```

`text_runs` 使用零起始字符范围，`baseline` 为 `subscript|superscript`；可加 `font` 为特殊符号指定字体。保存重开后同时检查字面内容与范围属性。旧场景的 `subscript_start` 也可用于单一下标尾段。

路径 `paths` 包含 `id,group,points,curve,style` 及可选 `arrow/begin_arrow`。语义 `edges` 另需 `source/target: {node,anchor:[u,v]}`，折线两端须与节点归一化锚点吻合，容差 0.2 px。箭头为原生三角路径，与线一起成组；元数据记录源/目标。它们不是自动吸附连接符。

## 运行

先查看、编写、验证场景。在案例目录使用新文件名，所有参数传绝对路径；下方变量是示意，按本机路径设置：

```powershell
python -X utf8 "$skill/scripts/illustrator.py" validate "$case/scene.json"
python -X utf8 "$skill/scripts/illustrator.py" render "$case/scene.json" "$case/.build/working-r1.ai" --stem "$case/.build/visible-r1" --delay-ms 45 --redraw-every 2
python -X utf8 "$skill/scripts/illustrator.py" verify "$case/scene.json" "$case/.build/working-r1.ai" --stem "$case/.build/native-r1"
```

`render` 在可见空白新文档创建实际对象；每两个场景对象重绘，逐项日志为 `.drawing.jsonl`，实际回读摘要为 `.render.json`。调速度只影响显示节奏，不改变图。失败保留 `.failure.json` 与部分进度；不要在相同文件名重试。

`verify` 重开指定 AI，核对原生几何、文字、语义路径、组移动，丢弃临时移动后再次重开，导出 `.png/.svg/.pdf/.audit.json`。审计失败仍可生成预览供诊断，Python 退出非零；不能因有输出文件就交付。查看 PNG 后修复。临时描边测字副本全部删除，不是交付文字。

本包脚本仅支持上述原生图元。位图、网格、图案、剪切蒙版和 live effects 不在当前渲染接口内；不接受无声明扁平化。使用其他原生工具扩展时单独记录编辑边界并回读验证。

最终选定已目视检查的候选，复制其字节为新的 `output/*.ai`，在该最终路径再运行 `verify`，核对 AI 哈希未变。保留 PNG、SVG、PDF、场景、源图与报告；临时迭代放 `.build/`。

输入验证不依赖 Python assert，因此优化运行模式也不会跳过几何或参数检查。画布/比例/坐标必须是有限数值，布尔值不作为数字；原生文字范围按 UTF-16 字符单位检查。仅通过场景验证不表示 Illustrator 已经运行。
