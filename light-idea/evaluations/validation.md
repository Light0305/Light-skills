# 首版验证记录

日期：2026-11-02（Asia/Tokyo）。环境：Windows / PowerShell / Python 3.11.13。

## 实际完成的检查

| 检查 | 结果 | 能说明什么 |
|---|---|---|
| skill-creator `quick_validate.py` | 源目录和本机技能入口均通过 | frontmatter、名称与入口基础规范合格 |
| `python -X utf8 -m unittest discover -s tests` | **37 项通过** | 本地导入和引用/推荐记录约束的自动检查；使用明确标记的合成夹具 |
| 真实上游试接 | 从 `light-literature/Literature` 与 `runs/final` 导入 **231** 篇选后记录，索引 **20** 个输入文件 | 当前实际文件格式可衔接；保留原筛选状态，不把可用性升级为已读 |
| 上游指纹复查 | 20 个索引输入均无变化 | 本次试接没有更改这些上游材料 |
| 安装路径运行 | 从另一个工作目录调用用户技能目录中的辅助脚本，验证通过 | 调用不依赖当前目录位于 skill 根目录 |
| Markdown 引用、JSON 与 UI 元数据 | 本地相对引用可解析，JSON 可读，默认提示含 `$light-idea` | 支持材料可发现、模板和界面配置可读取 |

关键自动检查覆盖：摘要/全文深度、未人工筛选、排除材料、非 ASCII/BOM、重复身份与来源合并、身份/筛选冲突、输出保护、路径越界、未知论文/证据/检索 ID、正文卡片的虚构引用、证据所属论文、失败查询、当前版本查重、资源阻断与确认依据、反证字段、撤稿支持以及上游变更。

真实上游中发现并兼容了同一 `paper_id` 的重复采集记录（仅时间/来源有差异），以及完全相同的重复筛选行。身份相容时合并并保留来源；冲突时仍停止，避免隐性选择。

## 有限的真实材料行为自审

使用上游现有的一篇医护人员安静离职研究，实际检查 `paper.md` 的 Methods、Discussion 与 Limitations。测试问题是：仅凭这篇材料和未知资源，能否直接推荐因果机制扩展。

本次产物保留两条原文证据，区分横断面关联与因果，提出测量可比性的待展开问题，同时明确这也可能已被既有工作覆盖。候选保持 `hold`，数据/资源为 `unknown`，查重为 `unsearched`；没有制造检索记录、效应量、数据权限或科研推荐。项目关系检查通过：1 篇论文、1 个候选、2 条证据、0 次检索。

另检查了 Literature manifest 中两个互不相同的主题，没有以目录共存为理由将它们拼成一个跨领域创新。

本地试接与自审产物保存在 `validation-local/`，已加入忽略规则；它们是本次环境的检查材料，不是模板文献库。

## 不能由这些检查得出的结论

这是宿主进行的有限自审，没有开展独立代理盲测，也没有完整跑完 scenarios.md 中全部行为场景。没有部署或复现外部研究系统，没有执行科研 pilot，没有测量真实选题质量、发表率或时间节约。

程序检查只能约束结构和记录关系，不能证明填入的证据真实、全文支持相关主张、查重充分或资源真的可用。下一步应在真实选题项目中保留修改/淘汰记录，观察哪些建议在最近工作核查和小规模执行后仍成立，再据此修订技能。

## 复查命令

```powershell
python -X utf8 -m unittest discover -s tests
python -X utf8 "<skill-creator>/scripts/quick_validate.py" "<light-idea-root>"
python "<light-idea-root>/scripts/idea_bridge.py" ingest --literature "<upstream>/Literature" --run "<upstream>/runs/<selected>" --out "<new-output>"
python "<light-idea-root>/scripts/idea_bridge.py" verify --workspace "<idea-workspace>"
```

本机安装使用 `C:/Users/Light/.codex/skills/light-idea` 指向 `D:/Light-Science/light-idea` 的目录联接；它使用同一份源文件。源码目录应保持可用。
