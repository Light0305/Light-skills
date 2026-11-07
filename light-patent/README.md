# Light Patent

面向科研与工程材料的专利撰写 skill。默认中国发明专利，支持技术交底、权利要求、说明书、摘要、附图规划与导出、查新分析、稿件迭代和审查意见答复草稿；实用新型按真实产品结构处理。

入口是 [SKILL.md](SKILL.md)。完整工作无需依赖旁边的参考仓库，也不要求指定模型或额外的多智能体服务。

源码版 0.2.0：补齐持续项目接入、背景/本发明披露区分、原申请具体部位与导出后来源/文件变更检查；
本轮验证见 [升级记录](evaluations/2026-11-07-upgrade.md)。

## 使用

将安装包中的 `light-patent` 文件夹放到目标工具的 skill 目录，保留 `SKILL.md`、`references/`、`scripts/`、`assets/` 和 `agents/`。Codex 的用户目录通常为 `~/.codex/skills/light-patent/`；本次是否已安装及具体位置见交付说明。

可直接请求：

```text
使用 $light-patent，阅读这篇论文与补充材料，找出有实际证据的保护主线，写成技术交底书，并列出必须补充的技术事实。

使用 $light-patent，基于这份交底书撰写中国发明专利完整申请草稿，保留核心公式，输出独立的 Word 文件和附图。

使用 $light-patent，只检查这份权利要求的支持、范围和引用关系，给出具体位置及建议修改。

使用 $light-patent，在现稿基础上合并这些修改，保留旧版，说明哪些改动影响保护范围。

使用 $light-patent，对照原始申请、审查意见和D1/D2，形成逐项答复草稿及修改依据表。
```

用户明确指定语言、法域、模板、检索范围和格式时以其要求为准。只润色或局部修改时不会强制跑全案。

## 设计重点

- 每个实质限定都有材料来源与说明书位置，待确认和无支持内容不会混入正式权要。
- 按技术问题组织必要特征、协作关系和从属退路，不用相似度或自评分代替专利性分析。
- 首次申请前的补充披露与已申请后的修改边界分别处理。
- 正式正文、证据表、检索记录、确认问题和交付清单分开保存。
- 按需加载参考文件；法律和数据接口问题使用时核对当前官方来源。

## 可运行工具

核心撰写与标准库工具无需额外安装。Word导出可选依赖：

```text
python -m pip install -r requirements-docx.txt
python scripts/init_case.py --title "一种技术方案" --out ./outputs/案件A
python scripts/audit_case.py ./outputs/案件A/case.json --profile application
python scripts/export_case.py ./outputs/案件A/case.json --kind application --format both --out ./outputs/案件A/交付v1
python scripts/export_case.py ./outputs/案件A/case.json --out ./outputs/案件A/交付v1 --verify
```

案件结构见 [case-format](references/case-format.md)，交付边界见 [delivery](references/delivery.md)。公式导出需要有效OMML，图件需要实际PNG/JPEG；不会把LaTeX字符串或空白图占位当作成品。已有交付目录不会被覆盖。

验证命令：

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

脚本只检查可编码的结构和已记录支持链，不认证法律结论、实质支持或版式。实际交付Word仍需逐页渲染目检；不能把审阅稿视为已通过官方电子申请格式校验。

## 调研与组成

[仓库调研报告](research/repository-review.md) 记录了3个本地参考仓库及7个外部仓库/技能包的具体借鉴与舍弃。运行包内也保留了 [来源评述](references/source-notes.md) 和 [官方依据](references/jurisdictions.md)。参考仓库、第三方研究快照和测试导出文件不进入安装包。

本项目未替用户选择整体开源许可，来源与边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
