# light-memory 0.1.0 验证记录

本文保留初版历史。0.2.0修订、35项最终回归及实际Memory/Leader闭环见[2026-11-07升级](2026-11-07-upgrade.md)。

日期：2026-11-06。范围：当前源码包内的独立文件型项目记忆、目录接入与专业产物兼容。测试均使用临时隔离项目和明确的合成科研材料；没有把示例生成到真实研究项目，也没有联网验证科学结论、自动启动真实科研任务或安装后台监听。

## 已运行

- **31 项 light-memory 行为测试全部通过。** 覆盖采集原子性、重复重试、只读检索、中文查询、来源变更/丢失、同范围冲突与不同范围并存、明确替代/撤回/问题关闭、下游依赖失效、政策复核到期、记录时间回放、项目身份与隔离、来源路径限制、事件损坏、并发锁、视图修复与用户内容保留。
- **15 项目录工具回归：14 通过，1 因当前 Windows 无符号链接创建权限而跳过。** 已有 Windows junction 拒绝测试仍通过。新增 Memory 接入的行为由 light-memory 测试另覆盖。
- 技能结构检查通过；18 个技能入口/本地参考同步采用同一项目规则。单独复制 scripts/references/assets/agents 到独立安装目录后，初始化与读取成功，不依赖研究快照或相邻技能。

合计本轮 46 个测试：45 通过、1 跳过。此前其他专业工具的历史验证不计入本轮数量。

## 与当前科研包的实际结合

测试实际调用现有 design_bridge.py 生成方案草稿、analysis_bridge.py 生成原生分析工作区、review_packet.py 冻结材料。记忆引用它们的原生文件，未改写专业内容，也未把“初始化完成”记成研究/审查已完成；原生分析文件变化后，对应记忆转为需复核，其他无关记忆仍可用。

目录工具先建立空 Memory，原生记忆初始化器可直接接入；project refresh 保留 light-memory 生成的 00-Memory总览，避免两个工具争用同一文件。

评价器问题、下游决定失效和评审问题关闭等场景检验了存储/检索行为。这些是由主执行者运行的确定性测试，不是独立专家评审，也未证明宿主在真实长会话中能完整提炼所有重要记忆。

## 复跑

```powershell
python -X utf8 -m unittest discover -s light-memory/tests -v
python -X utf8 -m unittest discover -s project-layout/tests -v
python -X utf8 project-layout/scripts/sync_layout.py --check
python -X utf8 "<skill-creator>/scripts/quick_validate.py" light-memory
```

从源码包根目录执行；技能结构检查器使用实际安装的 skill-creator 路径。进一步评估应使用真实项目的中断续作、关键决策回忆、相似版本混淆和有效阴性保留，记录遗漏/错记/过期复用，而不只看生成文件和自动 PASS。
