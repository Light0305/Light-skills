# 仓库调研、科研适配与阅读路线

核对日期：2026-11-06。开发记录 `research/repository-audit.json` 固定各仓库提交、所读文件 URL、文件哈希与访问日期，开发快照用于追溯本次判断；这些上游快照不随公开发行包分发。下表保留可直接访问的原始来源。只读 README、有关文档与少量核心源文件，没有运行这些仓库或验证其宣传指标。

## 借鉴什么，实际改成什么

| 来源 | 本次实际观察 | light-memory 的取舍 |
|---|---|---|
| [OpenViking](https://github.com/volcengine/OpenViking) | README 的文件系统上下文与 L0/L1/L2 分层 | 当前总览 → 相关记忆 → 原生证据逐层展开；保留真实项目目录和科学 ID，不安装它的上下文服务 |
| [Graphiti](https://github.com/getzep/graphiti) | README 的来源/历史模型，edges.py 的 created_at、valid_at、invalid_at、expired_at | 保留发生时间与记录时间、明确替代/撤回及可追溯历史；用项目文件事件实现较窄的记录时间回放，不冒称完整双时态图引擎 |
| [Mem0](https://github.com/mem0ai/mem0) | 当前 README 的累积写入和分信号召回；main.py 中 additive extraction 与显式 history 路径 | 采用显式追加事件、精确重试和可见的检索结果；科研陈述仍分用户报告/来源报告/推断/已核对观测，不把模型确认自动等权为实验事实 |
| [Letta 的记忆说明](https://github.com/letta-ai/skills/blob/main/letta/agent-development/references/memory-architecture.md) | 核心上下文、历史和归档需区别；归档不是窗口溢出的天然结果 | 工作上下文保持有限，归档事件按需查；明确本技能需实际整理和写入，不承诺任意会话都会自动存入项目 |
| [Letta 当前入口](https://github.com/letta-ai/letta)、[letta-code](https://github.com/letta-ai/letta-code) | 前者当前 README 指向后者；后者 README 介绍 MemFS 与显式记忆工具 | 参考可追溯文件上下文的方向；不根据旧教程绑定退休服务器接口，不改宿主 harness/系统提示或全局配置 |
| [Claude-Mem](https://github.com/thedotmack/claude-mem) | README 的 search → timeline → get_observations 渐进展开 | search 索引、timeline 变更和 show 全文；本版不安装会话 hooks、常驻 worker 或额外模型调用 |

这里的实现是根据 Light-Skills 现有数据契约独立编写，运行时不导入上述框架，也没有把其核心实现粘贴进本技能。研究快照保留来源，不能把这些仓库的许可证当作本项目的统一许可证；未来若实际复用其实现，应另核对对应组件许可。

## 科研场景特有的设计

下列是本项目的设计决定，不是声称某个上游已验证的能力：

1. **原生研究产物优先。** 文献 meta/note、idea/version、冻结设计、campaign/run、analysis finding、稿件/图/评审问题各有已有事实源。记忆保存决策背景和关联，不另建竞争性的证据库。
2. **不同认识状态分别保存。** 技术执行成功、有限科学支持、主张推断、用户计划不能合并成一个“已确认事实”。同样，valid negative、代码失败与不可判定有不同下一步。
3. **scope 和 slot 共同定位意义。** 不同设计/群体中的结果可并存，同一事实的不同说法要显示冲突；未裁决前不以时间新旧自动选真。
4. **依赖失效需要传播。** 评价器/输入/解释变了，依赖它的比较与建议提示复核；显式 depends_on 只表示必须继续有效的前提，避免所有历史相关性都变成强依赖。
5. **记忆不分配科研权限。** 下一步、旧命令和历史授权是上下文，实际行动结合当前用户任务及会话授权。协调由 light-leader 结合真实材料负责，Memory 不自动派发任务。
6. **先有可测的本地基线。** 分块哈希、事件回放、词法检索、可重建视图在本包可直接测试。语义向量、自动归纳与更复杂图遍历留给有真实失败样例/规模依据的迭代，不用上游 benchmark 替代本项目验证。

## 建议一起学习的顺序

先读 OpenViking README 的分层与检索部分，对应本技能总览/context/show；再读 Graphiti README 的 provenance/temporal 与 edges.py 的时间字段，对照我们的 recorded_at、observed_at、状态事件。然后看 Mem0 当前 main.py 中 add 与 history，区分“抽取策略”和“持久历史”两个问题。最后读 Letta 当前入口与 Claude-Mem 渐进检索，讨论未来何时需要 hooks、服务化和语义检索。

每读一处，回到真实科研场景问：它减少哪种重复劳动？怎样回到证据？什么变更会使记忆不再可用？我们能怎样测出错误？不以 stars、演示流畅度或上游宣传分数决定接入。

## 本次刻意保留的能力边界

词法 BM25/中文片段可能漏掉完全不同措辞的同义概念；宿主需改查 ID/同义词/原生源，当前不声称语义召回。来源哈希只判一致性，不能验证锚点语义、真实用户发言或科学蕴含。历史回放只表示系统截至记录时间知道什么；不恢复过去未保存的原始文件。事件哈希链检测内部变更/缺号，不提供外部可信锚，单独删除完整尾部后不能凭链自身证明历史完整。跨项目迁移、长期研究效果与大规模性能尚需实测。
