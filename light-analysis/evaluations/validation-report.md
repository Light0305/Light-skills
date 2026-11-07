# 本轮验证

验证日期：2026-11-02。环境：Windows、Python 3.11，标准库。所有运行材料都是隔离临时目录中的合成已知答案，不是用户科研实验数据。

## 已实际执行

- skill-creator 的 `quick_validate.py`：通过。Windows 主机默认编码不能读取中文，使用 `PYTHONUTF8=1` 后完成原验证器；未改动验证器源码。
- 35 项程序测试：全部通过，无跳过。包括 26 项输入/计划/证据/派生物/配对计算等测试、8 项原生记录测试、1 项真实相邻技能联调。
- 与本机 `light-design` 和 `light-experiment` 实际接口联调：先经真实设计校验与 runner 运行两个小型确定性进程，再读取原始 ODE 产物、执行实际收敛阶分析代码、登记派生物并导出停止反馈。机器可读结果见 [integration-results.json](integration-results.json)。
- 检查 upstream idea/设计/批次/运行身份保留，分析前后上游文件字节/哈希不变；在成功反馈后故意改变选中的原始文件，验证器检测到漂移。
- 配对统计工具验证了常数改善的退化警告、方向、行序不变、两单位已知经验 bootstrap 分布、真实零、缺失/重复/非有限输入与不覆盖规则。
- 静态交付检查：本地 Markdown 链接与 JSON 可解析；12 个选中仓库均有固定 commit 和实际读取文件记录，审阅缓存路径未带入交付。
- 本机 `light-experiment/SKILL.md` 的交接段补上可用的 `light-anaysis` 入口，原执行工具未改动；两个技能的格式检查均通过。新技能入口以 junction 安装到 `C:/Users/Light/.codex/skills/light-anaysis`，指向本源码。
- 一个独立、全新上下文的合成场景试用已完成：实际计算、完整报告、证据登记与设计阶段反馈均交付，并经根代理复核。保留了一个已解决的模板查找问题；详见 [forward-test.md](forward-test.md)。不将一个案例称为完整模型基准。

ODE 测试是 `y'=-y, y(0)=1` 的 Euler/RK4 在 20/40/80 步的解析验证。实际分析得到预期近一阶/四阶；两次执行相同问题不增加独立 N，三个网格也不成为三次独立实验。测试数据来源在分析和 feedback 中保持 `synthetic_validation`。

## 复跑

```powershell
$env:PYTHONUTF8 = '1'
$env:LIGHT_EXPERIMENT_ROOT = '<local light-experiment source>'
$env:LIGHT_DESIGN_ROOT = '<local light-design source>'
python -m unittest discover -s tests -v
python '<skill-creator-root>/scripts/quick_validate.py' '<light-anaysis-root>'
```

从该技能目录执行测试。未设置 LIGHT_EXPERIMENT_ROOT 时普通测试不依赖相邻仓库，实际联调项会明确 skip，不能宣称这时仍是 35 项全部执行。LIGHT_DESIGN_ROOT 选填；提供时才进行真实设计校验。测试可通过 LIGHT_ANALYSIS_VALIDATION_REPORT 指定输出摘要，否则仅在临时目录运行。

## 验证边界

没有执行系统性独立模型基准、真实领域项目评测、大型集群/云存储、R/Julia 或复杂层级/Bayesian 分析。一个合成场景的独立试用不证明其他研究场景也会通过。程序检查的是明确输入的完整性、身份关系、若干无效状态和有限统计实现；它无法判定实质证据蕴含、统计模型是否合理、原始实验真实性或 loop route 是否正确。场景规格见 [scenarios.md](scenarios.md)，其中未经实测的预期行为不等于本轮已观测到该模型行为。

后续应在真实项目中记录：分析是否数值正确、区间是否对应目标量、是否保留阴性/反例、是否准确区分执行/设计/idea 问题，以及下一轮是否产生真正改变决定的信息。按实际失败改进，避免为场景数量添加空泛规则。
