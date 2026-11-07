# 科研项目目录工具

为研究项目建立能持续使用的目录与导航。这是 Light-Skills 包级规范和可选辅助工具，不是新的总控 skill，不承担 light-leader 的职责。一个项目对应一篇论文或一项软著，也可以包含同一论文延伸的软著和专利。只讨论一个问题、改一段文字或临时看一张图时，直接完成任务，不强制建项目。

`Memory/` 由 light-memory 管理项目记忆，`Workflow/` 由 light-leader 按需管理跨阶段工作交接；目录工具只登记入口并把总览留给各自原生工具。完整规范含工作网络、产物树与新旧项目接入方式。

## 定位与选择

先读用户指定项目的 README、已有目录与 `project.json`（如有）。用户路径和已有项目约定优先；当前目录是 skill 包源码时，不能把它当作研究项目。无法确定具体项目时，可先交付目录方案，只询问真实研究产物要保存到哪里。

需要完整布局、命名、版本和各阶段产物时读 [项目目录规范](references/project-layout.md)。核心规则：

- 新项目使用单数阶段名：`Literature / Idea / Design / Experiment / Analysis / Figure / Write / Review`；按需增加 `Journal / Patent / SoftwareCopyright / Acquisition`。
- 只创建当前任务需要的阶段。项目根 `README.md` 给问题、阶段、结论、下一步和导航；`project.json` 只登记路径与归档关系，不复制科学证据或专业状态。
- 各任务拥有自己的工作目录。保留专用 skill 已实现的 JSON、文件名与内部目录；不为统一外观改名 `paper.pdf`、`design.json`、`campaign.json` 或 `runs/`。
- 目录编号只是归档 ID。`IDEA-0001` 可是一轮含多个候选的选题工作区，不替换 `ideas.json` 内的 I01；PROT、EXP 等也不替换原 design/campaign/run ID。
- 旧目录原地登记，默认不移动、不改写、不合并。修订设计新建版本；新实验批次、新分析与新评审使用新目录并引用旧记录。
- 安装目录里的文档、模板和测试不是研究成果。独立安装的专业 skill 通过其本地 `references/project-layout.md` 即可遵守约定，不依赖本管理工具。

## 可选本地工具

Python 3.10+，标准库。以下 `<layout-root>` 是本 README 所在绝对目录；`<project>` 是真实研究项目。所有命令都支持 `--dry-run`（只读的 check 不需要）。

```text
python "<layout-root>/scripts/project.py" init --root "<project>" --name "项目名称"
python "<layout-root>/scripts/project.py" add --root "<project>" --kind literature --title "项目文献库"
python "<layout-root>/scripts/project.py" add --root "<project>" --kind search --title "第一轮检索"
python "<layout-root>/scripts/project.py" add --root "<project>" --kind idea --title "选题探索"
python "<layout-root>/scripts/project.py" add --root "<project>" --kind design --title "最小验证" --upstream IDEA-0001
python "<layout-root>/scripts/project.py" revise --root "<project>" --key PROT-0001@v01
python "<layout-root>/scripts/project.py" register --root "<project>" --kind analysis --title "既有分析" --path "Analyses/旧课题/AN01"
python "<layout-root>/scripts/project.py" check --root "<project>"
```

`init/add/revise/register/update/refresh` 支持 `--dry-run`。`add/revise` 只创建空任务目录和导航，随后将该目录传给专业 skill 的原生初始化器；不预填其要求为空的输出目录。`register` 仅登记已经存在的项目内目录。`update --key ... --status ...` 只更新归档状态；`complete` 不等于科学结论成立。工具不启动实验、不联网、不调用模型、不迁移文件。检查只覆盖登记结构、路径与引用，专业校验仍由相应 skill 完成。

根 README 和阶段总览仅更新 `light-project:navigation` 标记内的导航，标记外文字保留。`project.json` 为登记事实源，导航可以 `refresh` 重建。不要用 refresh 掩盖科研文件缺失或上游漂移。并发写入会被锁阻止；若异常遗留 `.light-project.lock`，确认没有写入者后再手动处理，不自动抢锁。

若先建立检索轮次或已有文献库，使用 `register --kind literature --path Literature` 登记已有 Library，不再 add 接管同名目录。图的三种 kind 为 `figure-methods / figure-mechanisms / figure-data`；其余 kind 与阶段对应，软著用 `copyright`，采集用 `acquisition`。`add --kind memory` 或 `add --kind workflow` 仅创建空入口，再交原生工具初始化；已初始化时用 register 登记，refresh 不覆盖它们的总览。

新增/接入任务后，把实际输入 key 逐一传给 `--upstream`。保留用户内容的前提下，可用 `update --key AN-0001 --status active` 更新归档状态，再用 `check` 核对目录与导航。设计新版本由 revise 创建空目录，仍需实际修订并维护 design.json 的 version；工具不会替你复制或冻结科学内容。

维护公共约定后，执行 `python "<layout-root>/scripts/sync_layout.py"` 分发本地参考，再加 `--check` 核对一致性。验证结果见 [验证记录](verification.md)。
