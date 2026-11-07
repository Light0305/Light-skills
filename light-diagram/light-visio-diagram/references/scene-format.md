# 场景格式与执行方式

`scripts/render_scene.py` 读取 UTF-8 JSON。无网络调用，不解析图片。先由使用 skill 的模型查看参考图、盘点对象并填写坐标；脚本负责确定性绘制。

## 坐标和对象

```json
{
  "schema_version": "1.0",
  "font": "Arial Narrow",
  "canvas": {"width_px": 800, "height_px": 400, "pixels_per_inch": 100},
  "pages": [{
    "name": "Replica", "slug": "replica", "mode": "faithful",
    "nodes": [
      {"id": "a", "type": "roundrect", "bbox": [100, 150, 200, 70],
       "text": "Input", "style": {"fill": "#bce6d5", "font_px": 24}},
      {"id": "b", "type": "roundrect", "bbox": [500, 150, 200, 70],
       "text": "Output", "style": {"fill": "#b9def8", "font_px": 24}}
    ],
    "paths": [],
    "edges": [{
      "id": "a_to_b", "source": {"node": "a", "anchor": [1, 0.5]},
      "target": {"node": "b", "anchor": [0, 0.5]},
      "points": [[300, 185], [500, 185]], "arrow": 13,
      "style": {"stroke": "#0b1532", "stroke_px": 3}
    }]
  }]
}
```

- `canvas` 全页通用。`pixels_per_inch` 是像素到 Visio 英寸的坐标换算尺度，不是原图已有的印刷 DPI。字体、线宽也按此尺度换算。
- `bbox` 是左上角 x、y、宽、高，均用像素；`anchor` 是节点内部从左上角起的归一化坐标。左中 `[0,.5]`，右中 `[1,.5]`，上中 `[.5,0]`，下中 `[.5,1]`。端点必须与对应节点锚点一致（容差 0.2 像素）。
- 支持 `rect`、`roundrect`、`ellipse`、`text`、`junction`、`bezier`、`polygon`。文字与 junction 默认仍按普通形状处理；设 `stroke: "none"` 和 `fill: "none"` 才会透明。小型 junction 不是可见圆点。`roundrect` 可设 `radius_px`。`polygon` 使用至少三个顶点加重复首点的闭合 `points` 和显式 `bbox`，适合斜视特征平面、侧面和示意图标。
- `text` 用 `\n` 换行。`font` 必须为本机可用字体；不默默回退。样式支持 `fill`、可选 `fill_secondary`（Visio 渐变样式 25）、`stroke`、`stroke_px`、`font_px`、`text_color`、`bold`、`align`（0 左、1 中、2 右）、`dash_pattern`（Visio 线型编号）、`line_cap`。默认粗体、居中、无填充、深色轮廓。
- 对象 ID 在每页内唯一，由字母开头，之后仅字母数字下划线；`slug` 是每页唯一的安全小写文件名片段，仅字母数字和连字符。
- `paths` 和 `edges` 共有 `points`、`style`、`arrow`、`arrow_size`、可选 `radius_px`。`arrow: 0` 无箭头，默认 13 为 Visio 箭头样式编号；`begin_arrow` 默认 0，只有确需双端箭头时才设为对应编号。`paths` 是独立几何，适合实体骨架与装饰，不能代替需粘附的关系箭头；`edges` 会转为一维形状并使用 `GlueToPos` 粘附两端。
- 路径默认 `curve: "polyline"`；设 `curve: "bezier"` 时用三次贝塞尔控制点，数量必须为 `3k+1`：首点 P0，之后每段 C1、C2、终点。相邻段共用端点。闭合 `bezier` 节点同样用 `points`，首尾相同，可填充；渲染器把其轮廓适配到显式 `bbox`，消除 Visio 曲线包围框近似对锚点的影响。节点适合蛋白轮廓，开放路径适合 RNA/DNA 骨架。
- `nodes`、`paths`、`edges` 默认按此顺序绘制，各数组内部顺序即叠放次序。可在页面设置 `draw_order`，列出每个对象的 ID 恰好一次。关系箭头必须排在其两个端点节点之后。标注圆点可排在骨架路径之后，防止被遮盖。
- 需要局部图片或文本混排时应扩展实现，而非塞入未支持字段。
- 可在顶层保存 `provenance`，在页面保存 `mode` 等元数据；渲染器不会据此自动修正图，也不验证这些文字的科学含义。

为保证 PNG 与参考图同画布，可在 nodes 第一项放置全页白色矩形、无边线。这是原生形状，并非参考图截图。

## 保存与核查

输出为 `output.vsdx`、`output-<slug>.png`、`output-<slug>.svg`、`output.pdf`、`output.audit.json`。保存后在本次独立 Visio 实例中重开再导出。审计核对节点文字、语义线的一维属性和起终点粘附，并列出压缩包内媒体对象。当前渲染器只支持全原生场景，因此媒体对象为空是通过条件之一；以后增加局部图片时须改为与声明的组件清单比对。

每页还会临时移动一个有语义连线的普通节点，检查其相邻端点是否按相同位移跟随，然后恢复原坐标。`movement_probes` 记录实际覆盖的节点与端点数量；它不表示所有节点均经过拖动测试。无可用节点时明确记为跳过。

审计不评判视觉与科学正确性。形状文字匹配不能排除被截断、字号不合适或字体替换；必须查看导出图。若变更场景或渲染器，重新生成并检查对应输出，不复用旧审计。

需要图像定位诊断时，可运行 `scripts/compare_reference.py source.png output-replica.png comparison.json`，依赖 Pillow。脚本要求尺寸一致，报告白底以外区域的 RGB 误差及容差 3 像素的深色像素匹配；不将其包装成“还原百分比”。对修正版与原图的有意差异应单独解释。

多折点路径保持测量的布局。粘附后移动节点会带动端点，但中间折点可能随线的几何变换而偏移。要求拖动后仍自动正交避障时，应改用 Visio 动态连接线并重新评估复现效果。

输入先检查容器类型、有限数值、样式、闭合轮廓和端点约束，布尔值不作为坐标或 pixels_per_inch。原生 audit 在实际保存后同时记录 scene_sha256 与最终 VSDX 的 sha256；代表节点移动检查不能扩大为所有节点与全局避障保证。
