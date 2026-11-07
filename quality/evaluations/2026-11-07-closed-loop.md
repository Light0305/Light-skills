# Light-Skills 整包回归与合成闭环

日期：2026-11-07。范围：D:/Light-Skills源码；15个主技能、4个Diagram子技能及目录工具。未更新全局安装、插件缓存或旧分发包。

## 最终回归

21个测试集共1166个不同测试：1164通过、2跳过、0失败/错误。跳过均因Windows不能创建符号链接，分别属于目录工具和软著；未删除测试或改权限。Memory35项，Leader52项。

首先实际运行整包1164项（1162通过、2跳过）；Leader再补历史兼容和登记丢失回归后，复跑Memory/Leader/目录工具。每集取最新一次实际执行，重复测试不叠加。

- [最终逐集汇总](2026-11-07/final-summary.json)
- [整包初轮及日志](2026-11-07/package-attempt1/summary.json)
- [最终变更集复核](2026-11-07/final-changed-suites/summary.json)
- [入口、语法、JSON与目录同步](2026-11-07/structural-checks.json)

各测试集在独立进程执行，避免同名模块污染。Crawl使用实际本地环境；Analysis/Experiment配置本地上游；Chart执行既有Python/R回归；PowerPoint另有22项Node测试。检索/选刊的离线材料不冒充本轮联网。

## 跨模块覆盖

| 情境 | 实际执行与边界 |
|---|---|
| Literature→Idea→Design | 原生来源、筛选/版本、选中证据及冻结输入的跨模块回归；离线合成或已保存材料，不评价真实召回和创新性 |
| Design→Experiment→Analysis | 两次真实Python运行、完整轨迹、冻结设计、实际收敛阶计算和原生handoff；一个已知解析解ODE，不是科研发现 |
| Analysis→Journal/Write | 绑定实际报告、离线选刊packet及proposed/作者决定区别，核查v02采用记录；没有核实真实期刊现行政策 |
| 数据图 | 原生PNG/PDF/SVG及原始JSON/代码绑定，执行者查看最终PNG；未把单次目检当独立审阅或PDF目检 |
| Write→Review→Write→Review | 发现预设“六次独立实验”错误，修成一个问题/六个组合，针对v02复核LR-001；两轮聚焦检查，不宣称整篇ready |
| Memory/Leader恢复与漂移 | 实际写入问题、修订及关闭依据；重复capture幂等，Leader读回；改变稿件后Memory/Workflow/Write提示复核，未变Analysis与冻结Review保持有效 |
| 失败/未知状态/回退 | 全套中的真实失败进程、依赖/版本失效、分析反馈及本轮未知执行绕过回归；不是独立模型选科学路线评测 |
| Diagram/Crawl/专利/软著 | 当前套件的输出和原生接口回归；软著仍为三份DOCX、黑色标题。没有在ODE例子中捏造专利或软件事实，也未重做全部桌面宿主与门户 |

## 保留的闭环

[结果](2026-11-07/closed-loop-attempt3/result.json)、[实际数值](2026-11-07/closed-loop-attempt3/numerical.json)、[恢复包](2026-11-07/closed-loop-attempt3/resume-before-drift.json)、[故意变动后](2026-11-07/closed-loop-attempt3/resume-with-deliberate-drift.json)、[PNG目检](2026-11-07/closed-loop-attempt3/visual-check.json)。实际项目保留在结果指向的外部临时目录，保持“技能源码不能当项目”的原生保护。

两次重复运行不增加独立样本数。刻意漂移最终恢复为完全相同的原字节，未刷新旧来源指纹；Workflow最终核验通过。原生图QA保持采用时状态，目检单独记录并绑定PNG。

前两次演练为验证脚本接入错误：第一次列出R002却没选择其原始证据，Analysis正确拒绝；第二次把嵌套JSON传给Chart表格输入，改成实际DataFrame并绑定JSON/代码。失败目录、原因及记录保留；确认同步子进程已返回后记为失败/停止。汇总器首次不能解析Node默认输出，改用显式TAP后实际22项通过，旧日志保留。

## 复跑

在源码根目录执行，使用新结果目录避免覆盖证据：

```powershell
python -X utf8 -B quality/run_checks.py --out quality/evaluations/new-run/package
python -X utf8 -B quality/run_closed_loop.py --out quality/evaluations/new-run/closed-loop
python -X utf8 -B project-layout/scripts/sync_layout.py --check
```

局部复核可重复添加--include light-memory / --include light-leader等实际测试集名。沿用各模块依赖，不自动安装。闭环每次建立独立合成项目并记录位置。

## 结论范围

本轮完成源码、确定性回归与上述合成闭环。真实课题研究判断、长会话记忆遗漏、领域适配、独立模型审图/审稿、全部桌面宿主与当前投稿/法律规则仍需真实情境验证；1166个测试不替代这些评价。
