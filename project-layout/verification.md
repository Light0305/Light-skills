# 目录规范验证记录

日期：2026-11-06。范围：当前 `D:/Light-Skills` 源码包。所有测试材料来自隔离临时目录或既有合成测试；未迁移真实项目、未启动真实科研任务、未访问采集目标、未修改已安装副本或实现未来总控/记忆技能。

本文保留目录规范首次落地时的验证结果；随后 light-memory 已实现并接入 Memory，新增行为与回归结果见 [记忆技能验证记录](../light-memory/evaluations/verification.md)。下文的 Memory 预留状态仅描述首次验证时点。

随后 light-leader 也已实现并按需接入 Workflow；当前接入、原生总览保留与回归结果见 [总控技能验证记录](../light-leader/evaluations/verification.md)。本文提到“未来总控/记忆”描述首次验证时点，不代表当前实现状态。

## 已完成

- 13 个主技能及 4 个示意图子技能均有入口链接和随技能分发的本地目录参考；生成副本一致性检查通过。
- 默认目录统一，保留现有原生内部文件与数据接口；修正 Idea/Design/Experiment/Analysis、选刊与评审的旧默认路径，并移除活跃接口说明中的历史本机数据位置推定。
- 项目按单篇论文或单项软著组织；可关联同源专利/软著。Memory 只预留位置与职责，目录登记不充当记忆或调度器。

## 验证结果

| 范围 | 测试数 | 结果 |
|---|---:|---|
| 新目录工具 | 15 | 14 通过；1 项符号链接测试因当前 Windows 无创建权限而跳过 |
| light-idea 既有回归 | 37 | 全部通过 |
| light-design 既有回归 | 19 | 全部通过 |
| light-experiment 既有回归 | 35 | 全部通过，含实际合成数值运行 |
| light-analysis 既有回归 | 35 | 全部通过；可选跨技能集成单独配置本地上游后通过 |

合计 141 个不同测试：140 通过、1 跳过。另有 17 个入口/本地参考检查与同步一致性检查通过。Windows junction 的拒绝登记测试实际通过；它不代替被跳过的符号链接测试。

目录工具验证了：按需创建、预览无写入、中文/空格路径、FIG 共享编号、一篇主稿、文献原生索引保留、设计空版本与前版关联、旧目录原地登记、README 标记外内容保留、错误上游与环拒绝、路径越界拒绝、并发锁、损坏导航拒绝、只读检查及导航恢复。

新工具生成的空工作区已交给实际 `design_bridge.py ingest`、`analysis_bridge.py ingest`、`init_case.py` 和 crawl `new-case` 验证兼容。跨设计/执行/分析集成使用真实本地工具与合成数值问题，保存并检验原生输入与运行记录；这不等于真实研究结论通过验证。

## 复跑

```powershell
python -X utf8 -m unittest discover -s project-layout/tests -v
python -X utf8 project-layout/scripts/sync_layout.py --check
python -X utf8 -m unittest discover -s light-idea/tests -v
python -X utf8 -m unittest discover -s light-design/tests -v
python -X utf8 -m unittest discover -s light-experiment/tests -v
python -X utf8 -m unittest discover -s light-analysis/tests -v
$env:LIGHT_EXPERIMENT_ROOT = 'D:\Light-Skills\light-experiment'
$env:LIGHT_DESIGN_ROOT = 'D:\Light-Skills\light-design'
python -X utf8 -m unittest discover -s light-analysis/tests -p test_pipeline_integration.py -v
```

从其他位置执行时替换为实际源码路径。此处设置的两个环境变量仅用于可选本地集成测试，不是运行技能或初始化研究项目的必需配置。
