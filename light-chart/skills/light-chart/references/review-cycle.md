# 实际审图与修订

`scripts/review_cycle.py` 将实际图件、任务说明和输入记录绑定到一次审阅；`review_engine.py` 是 Light-Science 自行实现的确定性记录工具，不启动模型，也不生成评语。审阅上下文、真实图片传递与独立性由宿主负责安排；session ID 只用于追踪和去重，不能认证独立性。

## 准备实际图件

- `data-first` 按本研究的问题、数据编码和最终尺寸审图。文字说明卡不提供视觉金标准；前稿和外部参照各自声明身份。字段 `reference_inventory` 为兼容既有任务保留，此处记录当前稿构造。
- `reference-fit` 需要真实设计参考，核对约定的构造、布局和新数据适用性；不同数据集不比较数值位置。

```text
python scripts/review_cycle.py stage --workdir task/review --draft task/figure.png --pdf task/figure.pdf --qa task/figure.qa.json --brief task/brief.txt --width-mm 180 --height-mm 120 --min-reviews 2 --max-iters 3
```

换成本任务实际文件。brief 写问题、面板职责、单位、变换、区间定义和保持项。已有图片可不提供 QA，但不能因此宣称数据核对完成。提供 QA 时，它必须绑定本次 PNG/PDF 与来源。

stage 生成不可变的 `img_iter0.png`、`audit_view_0/`、组合图、全分辨率图、96 dpi 尺寸预览、实际 PDF 渲染、诊断、审阅 schema、指南、提示与散列清单。96 dpi 只是统一屏幕代理，不能证明显示器按物理尺寸呈现。未完成的 stage 应保留并另建回路，不覆写旧记录。

## 获取真实意见

宿主给新上下文审阅者当前 audit view，实际打开清单中的图片，读取提示和 schema。审阅者不读源码、原数据、作者自评或旧评语，只返回实际观察。科学计算和源数据由专业核对另行完成。详细约定见 [reviewer-contract](visual-review/reviewer-contract.md)。

```text
python scripts/review_cycle.py accept --workdir task/review --review task/returned-review.json --iter 0 --reviewer-session ACTUAL_HOST_SESSION_ID
```

脚本保留实际载荷字节与完整 session ID。标框使用 comparison.json 的 composite 像素，必须位于 draft_rect；越界和互相矛盾的意见不会计作有效审阅。原始载荷、稿件与事件链会在后续操作前重新核对。

| action | 继续方式 |
| --- | --- |
| retry_reviewer | 意见无效，不计数；查明问题，让新上下文重看同一稿。连续两次无效会记录后停止。 |
| review_same_draft | 当前稿无待修问题，但有效审阅数不足；用新会话确认同一图件。 |
| draw | 已写带框图和修订说明；修改代码、导出真正改变的新稿，再 stage 下一轮。 |
| ship | 视觉意见通过且有效次数满足约定；显式选定当前稿。 |
| stop_at_cap | 停止修订；选择有实际审阅且底线通过的版本，写清剩余问题，不能自动验收。 |

相同请求重放不增加次数。同一 session 改写意见不构成新审阅。`data-first` 使用返回的 repair_instructions 与 annotated.png，禁止模仿文字说明卡；reference-fit 使用带原始观察的 notes.md。保持正确部分，修复后核对数据、单位、身份和必要构造。

```text
python scripts/review_cycle.py select --workdir task/review --iter 1 --reason "实际采用理由"
```

上限选稿需一个或多个 `--unresolved "实际未解决问题"`。底线失败或 verdict=off 的稿件不能被提升。PNG、PDF、理由和未决项写入 selection.json。`ship` 只表示视觉流程状态，不是科学验证、期刊认可或质量认证。

## 严格三维比较

普通新数据三维图不必套用严格复现。用户要求复现或比较/替换 control 时，先读 [三维路由](visual-review/three-d/route.md)，明确 three_d_mode、three_d_subtypes、参考角色、最终 PDF 与 geometry_evidence。

```python
stage_review(workdir, candidate_png, strict_3d=True,
    three_d_mode='candidate-comparison', mode='data-first',
    reference=control_png, reference_role='previous_draft', control=control_png,
    three_d_subtypes=['volumetric-surfaces', 'material-lighting', 'marks-and-panels'],
    geometry_evidence='geometry-audit.json', three_d_views={'other_camera': other_camera_png},
    pdf=candidate_pdf, briefing=actual_scientific_brief, size_mm=(180, 145))
```

变量需替换为真实文件，subtype 按实际表示选择。geometry-audit.json 给出 representation、coordinate_units、实际 checks、limitations 与 assets（role、path、sha256）。散列只证明资源绑定；拓扑、分割、组件数量、体积和标定要有实际科学检查。

stage 加入自写路由、证据、相机、选择、观察表、迭代指南和所选子类；缺资料会报错。源快照留在 geometry_sources_N，视觉审阅只读 audit view 的摘要、control、候选、可选 baseline 和辅助视图。清单锚点防止改开关绕过绑定。

schema 保留 three_d_scorecard 和本次改变、保持项、回归、缺口、下一步及 accept_over_control。存在 control/baseline 时分别观察和评分。候选超过 baseline 不足以替换 control；四项主要维度的下降会阻止接受。分数只是任务内启发式：默认 overall≥85、各项≥75、四项主要维度≥82，详见 [assessment](visual-review/three-d/assessment.md)。不能补分求通过，也不能拿这些阈值认证科研质量。

预检失败保留实际载荷并报错，不改写评语。底层有效性、次数和轮次由自有引擎处理。严格修订使用返回的 strict_3d_repair_instructions.md 与带框图，从已接受 control 出发，保留原观察和科学证据。像素诊断不替代任何上述判断。
