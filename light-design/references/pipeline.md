# 上下游衔接

## 选择实际输入

`light-literature → light-idea → light-design → 实验执行/记录 → 分析/写作` 是能力边界，不是强制安装链。

- `light-idea` 决定什么值得做，以及便宜的第一道检验；本技能决定如何具体实施和解释。
- 有 `Idea/IDEA-0001_选题主题/ideas.json` 时，读取用户选择的 `idea_id` 和当前版本，不自动把其他候选一起展开。未指定且有多个实质方向时先厘清选择；可以先检查共同的资源条件。
- 同时读 `decision.md`、对应 card 和 `context.json / evidence.jsonl / external_papers.jsonl / novelty_log.jsonl` 中相关内容。没有这些文件时可直接用用户的 brief，不以缺少上游技能为由拒绝设计。
- 上游 `design` 是最小验证提纲，应保留其可区分预测、反方意见、阴性价值和预算上限；具体方法允许修订，但要解释原因。
- `recommended`、`confirmed` 和 `verified=true` 都有原来的范围和含义。再次核对本轮所需数据和完整研究资源，尤其注意 pilot 到正式研究的扩展成本。

上游源码从当前安装位置定位，仅用于查看接口；研究材料来自真实项目的 Idea 工作区，不能从源码模板推定用户已经形成想法。

## 冻结与追溯

`design_bridge.py ingest` 只读指定 idea 工作区：

1. 验证 idea ID 唯一并保留版本、状态、约束和原始 design；
2. 读取存在的上下文、证据、补检论文、查重记录及决定/card；
3. 在 `context.json` 保存所选 idea 和结构化来源快照；对实际读取文件记录绝对路径和 SHA-256；
4. 从模板建立 `draft` 计划，`selection` 固定到该 ID/版本；所有科学字段仍待宿主填写。

保留证据原 ID。上游和本轮证据分别为 `context.evidence` 和 `design.evidence`；不能重复命名。新增证据引用 `design.sources` 的真实出处，明确 `access_level / locator / statement / verified`。方法学资料库中的来源不自动进入具体学科研究的证据账本。

输入漂移时先解释改变，再重新导入到新目录或版本并复核，不手改指纹消除警报。0.2.0 跟随所选证据已绑定的本地来源，以及选中论文已声明的 PDF 身份，避免只核对上游索引；更广的文献库核查仍由上游负责。只读摘要、远程内容或旧记录缺绑定的限制保留，导入成功不代表文献已经科学验证。详见 [修订与执行交接](revision-and-handoff.md)。

## 修改与交接

改变问题、机制或目标结论，通常需要回到 idea 的文献差异核查；只改排程或设备配置则在设计版本内记录。不要静默覆写上游 idea、原始文献和已有结果。

交给执行者的最小包是：`selection + design_id/version + execution_scope + plan.md + 适用的 protocols`。同时交代：

- 谁能执行、前置条件和允许的最大资源消耗；
- 输入位置与版本、分配表、数据字典和日志/原始文件存放位置；
- 实验与任务依赖、逐步验收和失败后允许的重试范围；
- 数据锁定、揭盲、主要分析、三类结果的解释及偏离方案的记录办法。

当前 `light-experiment` 已有原生 `experiment.py init --design <本设计版本工作区> --out <独立执行批次>` 接口，冻结 context/design/plan 和适用 protocols。默认输出为 `Experiment/EXP-0001_执行批次/`；使用时先读实际安装版本的说明，不把初始化或设计就绪当作已启动实验。
