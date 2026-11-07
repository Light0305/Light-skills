# 参考仓库、核对与取舍

核对日期 2026-11-06。学习目标是如何把科研判断、计划状态、外部运行和长期记忆接起来。不是选择一个框架重写现有技能，也没有安装/运行参考仓库。当前实现为原创的指令、集成契约和标准库文件台账，没有复用上游运行时代码。

## 已核对的一手材料

| 仓库及固定版本 | 实际查看的材料 | 采用的思想与本包取舍 |
|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph/tree/5847733bcb186c26b32da5cc822eaf8a89deffeb) · MIT | README；checkpoint/base 的 CheckpointMetadata、CheckpointTuple、pending_writes 等定义；[官方持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence) | 把可恢复工作状态和长期记忆分别维护，保留运行/父记录身份。我们持久化交接台账，不实现 LangGraph 的执行引擎、checkpoint replay 或外部任务恰好一次运行 |
| [Deep Agents](https://github.com/langchain-ai/deepagents/tree/70dfbd597ae3d1ac348f6c46892464868f24b070) · MIT | README；libs/deepagents/deepagents/graph.py 的 skills、planning、subagent/checkpointer 配置与组合方式 | 计划与专业能力按需组合，分层读取指令和产物。保留宿主当前助手，不默认新增代理、后端或框架依赖；任务复杂不自动意味着多代理 |
| [Google ADK Python](https://github.com/google/adk-python/tree/75fc85319f93abc54baf0ebe5b5fb7f71e483225) · Apache-2.0 | README；src/google/adk/agents/loop_agent.py 的恢复位置、escalate 与 max_iterations；[官方循环工作流说明](https://adk.dev/agents/workflow-agents/loop-agents/) | 明确循环状态、退出依据及恢复语义。**该固定版本的 LoopAgent 已标为弃用，建议 Workflow**，不能把旧教程当新推荐。科研循环按问题/预算/信息决定，不能抄默认无限循环或固定示例轮数 |
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework/tree/83c7190658403f1cc653f34b822bb7ada3a3e2e2) · MIT | README；python/samples/03-workflows/checkpoint/checkpoint_with_resume.py 的 executor 状态保存/恢复示例 | 专业执行身份与协调状态分别保存，恢复先核实真实执行。示例使用 InMemoryCheckpointStorage，我们不能把这个示例本身称为跨进程磁盘持久化保证 |

提交、原始文件 URL、字节数、SHA-256 和许可证见 `research/repository-audit.json`；对应 README、许可证和少量源码只作为带许可证的研究快照放 `research/snapshots/`，不作为运行依赖或科研项目输入。`research/audit_repositories.py` 只按这些固定提交下载，不跟随 main 更新。外部主分支继续变化，今后更新设计应重新选定并核对版本。

## 从现有 Light-Skills 得出的具体设计

1. 项目单位服务于一篇论文/一项软著及其关联成果，不能把常见 agent 框架的“任意任务列表”直接当科学项目模型。一个当前 objective 仅表示本轮可验收交付，研究、论文修订可有多个目标与版本。
2. 当前设计、实验和分析已有真实 JSON、冻结输入和原生门槛，总控不统一替换 schema，也不再实现评价器或第二套实验 runner。特别是分析反馈还不能由 idea/design ingest 自动接收，需要宿主实际修订。
3. 当前 write/chart 等接口不完全是机器 API；“读取目标技能 → 按其契约实际做 → 看真实产物再接收”才能覆盖整个包，通用函数名或自动 subprocess 路由会制造假集成。
4. light-memory 已负责来源、冲突、依赖失效与长期恢复。Workflow 只增加它没有覆盖的本轮交付、任务依赖、正在做什么和中断入口，不再复制证据矩阵、文献库或记忆检索。
5. 框架能表示分支/循环并不意味着能判断科研层次。总控由宿主根据竞争解释、上游有效性、已有证据和本轮目标判断，脚本只检查可确定的文件与依赖，避免把固定 if/else 阶段推进伪装成科研推理。

## 后续一起学习的顺序

先用一个真实小项目检验“恢复 → 选择最小动作 → 实际调用 → 接收 → 写回”的完整过程，记录真正失误。再看 LangGraph 中状态、checkpoint 和长期 store 的分工；接着看 Deep Agents 怎样把 planning/skills 接到宿主；最后研究 ADK / Microsoft 的循环、恢复与组合，比较哪些能力值得在实际出现需求时引入。

优先改善有具体失败证据的路由、材料身份、接收标准或恢复接口。多代理协作、后台执行、集群适配、语义检索与信息价值模型都需要真实场景和单独验证；当前测试不能证明其存在或科研效果。没有用过完整真实项目前，不宣称“全自动科研”“最优调度”或相对其他框架的性能优势。
