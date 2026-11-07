# light-review

接在 `light-write` 和作图之后的**投稿前内部评审技能**。检查完成稿、最终图表和补充材料，把重要问题变成能定位、能修复、能复核关闭的任务。

入口是 [SKILL.md](SKILL.md)。原有 `light-analysis` 继续负责实验结果分析，本包不会覆盖它，也不修改 `light-write`。

## 如何使用

把**整个目录**作为技能包使用，保留 `references/`、`assets/` 和 `scripts/`；也可以直接让助手读取本目录的 `SKILL.md`，按其指南处理材料。需要宿主自动发现时，将完整包放入该宿主的技能目录。本次交付是当前工作区中的技能源包，未修改用户全局技能目录。

例如：

> 使用 light-review 对这篇完成稿、最终图表和补充材料做投稿前内部评审。优先检查承重主张、方法与统计、图文数值一致性，给出问题位置、证据、最小修复及关闭条件。目标期刊暂未确定。

修改后可以说：

> 复核上一轮 LR-001、LR-003 和 LR-004，检查实际修改及所有关联位置。沿用原编号，说明哪些可以关闭、哪些仍有必要工作。

提供现有材料即可，不必先填统一表格。最好说明哪个是当前主稿、哪些图表与补充材料属于同一版、文章类型和目标 venue（如有）。资料不全时做有边界的局部评审。

## 工作方式

1. 理解研究问题、贡献、结果和真实优点。
2. 把承重主张对应到方法、图表、推导和引用证据。
3. 按真实证据类型审方法与推理，不把所有论文当作ML实验或临床试验。
4. 单独检查实际图表、数字、公式与跨节一致性。
5. 必要时核查近邻工作、承重引用和当前精确 venue 要求。
6. 将问题交回正文、作图、分析、实验或作者环节，并在新版本中复核。

不凑缺点数量，不以总分平均掉阻塞问题；不把“没报告”写成“没做”，不把图片异常写成造假定论。可选增强与必要修改分开，新增实验须说明为何是保留承重主张所需。

科学就绪与投稿材料就绪分别记录为 hold、revise、ready 或 not_assessable；未要求投稿文件核查时后者可为 not_requested。它们是内部准备状态，不是期刊决定或录用概率。

默认交付评审与修复任务；不会自行改稿、改图、开展新实验、上传外部评审网站或投稿。用户要求修订时可在既有授权范围内继续。普通任务不强制三位模拟审稿人；共享上下文不能称为独立互盲评审。

## 与上游怎样衔接

直接接收 light-write 正文及有关来源/主张/数值账本；有可选稿件 packet 1.0 时使用其原生 auditor 核对采用文件与文字锚点。图表可以来自任意流程，Chart/Diagram 已有 QA 和原生文件按各自真实接口检查。上游工具通过只是核查线索，不自动继承 verified 状态。

持续项目先恢复有关 Memory，再回读实际科学原件；Workflow 仅记录工作状态。详见 [项目接入](references/project-integration.md) 和 [交接与复核](references/handoff-and-recheck.md)。不依赖历史本机路径或其他技能必须相邻安装。

## 资料基础

2026-11-02 定向检索并整理 **9个仓库、8篇核心论文、3篇博客和5份官方指南**。包括科研综合技能包中的 peer-review 子技能，未局限于仓库名称。

- 推荐先看 K-Dense、EvoSkills、neuromechanist/research-skills 和 Academic-Paper-Skills 的具体子技能。
- 方法依据包括 NEJM AI 2024 的反馈研究、Nature Machine Intelligence 2026 的随机干预、PLOS 2025 的评审质量评价、PRISMM-Bench、ReviewGrounder 及 ActReview。
- 每项均记录采用的思想、未采用的做法和证据边界；区分正式出版、作者公开稿、预印本、博客与官方规范。

完整链接与对照见 [sources.md](references/sources.md)，固定 commit 和获取文件 SHA-256 见 [source-audit.json](references/source-audit.json)。未运行上游研究系统，也未把其论文性能当成本技能效果证明。

## 文件与工具

| 文件 | 用途 |
|---|---|
| [SKILL.md](SKILL.md) | 可发现的入口、流程、证据/严重度/就绪规则 |
| [评审方法](references/review-method.md) | 理解、定向深查、反查评审与综合 |
| [领域指南](references/domain-gates.md) | 实证统计、计算、生命临床、物理工程、理论、社科人文、综述 |
| [图文数值审计](references/figures-and-numbers.md) | 真实图表、聚合定义、数字复算与修图任务 |
| [文献与venue](references/literature-and-venue.md) | 可比性、引用核验、报告规范与投稿要求 |
| [文件契约](references/artifact-contract.md) | 可选的版本冻结、结构化记录和复核用法 |
| [项目接入](references/project-integration.md) | Memory 恢复、稿图/分析采用版本、更正与真实回流 |
| [报告模板](assets/report-template.md) | 完整评审的起点，可按范围压缩 |
| [review_packet.py](scripts/review_packet.py) | 标准库离线工具，只做显式文件快照与记录一致性检查 |
| [本轮验证](evaluations/2026-11-06-upgrade.md) / [历史记录](evaluations/REPORT.md) | 本轮升级与原有合成演练、未完成的独立试跑 |

技能本身是 Markdown 指令，不要求运行脚本。需要可追踪文件时才使用 Python 3.10+ 工具。`freeze`、`verify`、`validate` 不联网、不调用模型；它们无法证明稿件内容正确或评审已真实完成。

## 当前质量状态

**0.2.0 源码/流程升级，尚无真实稿件专家质量验证。** 当前验证范围及准确数量见 [本轮记录](evaluations/2026-11-06-upgrade.md)。新增可选记录 1.1 的直接前轮绑定、问题留存/改判与关闭证据检查，兼容旧记录 1.0；未绑定的旧版 recheck 明确提示连续性未检查。检查证据必须指向声明已读或部分已读的材料，但脚本不能认证真实阅读或修复充分性。

历史三份合成案例为同会话作者演练。原独立模型前向测试因工作区额度耗尽未完成，仍不计通过；本轮没有重新发起付费模型或真实领域专家评审。

运行工具测试：

```text
python -X utf8 -m unittest discover -s tests -v
```

来源与许可边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。未替维护者指定整体开源许可证。
