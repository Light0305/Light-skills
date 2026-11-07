# 安装与调用

本文面向 Light-Science v2.0。公开仓库为 `Light0305/Light-Science`。本地源码可从根目录执行 `npx skills@latest add .`，再补充 `npx skills@latest add ./light-chart/skills/light-chart`。安装到哪个宿主、项目或用户范围，由安装时的选择决定。

## skills CLI

Windows 使用 `npx.cmd`；macOS / Linux 使用 `npx`。CLI 需要 Node.js 22.20+、Git。安装动作不会代替各技能的依赖安装。

```bash
# 查看远程入口
npx skills@latest add Light0305/Light-Science --list

# 交互选择技能、Agent 与安装范围
npx skills@latest add Light0305/Light-Science

# 补充嵌套目录中的 Chart，选择相同安装范围
npx skills@latest add https://github.com/Light0305/Light-Science/tree/master/light-chart/skills/light-chart

# 只安装论文写作
npx skills@latest add Light0305/Light-Science --skill light-write

# 只安装项目总控与记忆
npx skills@latest add Light0305/Light-Science --skill light-leader light-memory
```

选择 Project 时先进入研究项目。Global 安装可跨项目使用。本地实测：根目录 `--list` 只发现 14 个顶层技能，Chart 需通过上面的完整路径安装；Diagram 总入口含四个子目录。完整源目录中的上游学习快照不是正式入口，以 [README 技能表](../README.md#skills-一览) 为准。

独立安装 Diagram 子技能时指定其目录，例如：

```bash
npx skills@latest add https://github.com/Light0305/Light-Science/tree/master/light-diagram/light-powerpoint-diagram
```

把末尾目录替换为 `light-diagram-prompt`、`light-illustrator-diagram` 或 `light-visio-diagram` 即可安装其他子技能。上述分支路径沿用当前仓库的 `master`；未来改变默认分支时应同步更新。

CLI 的参数与宿主清单以 [官方文档](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) 为准。

## 手动安装

把**完整技能目录**放入所用 Agent 支持的位置，保留相对路径、脚本、模板、资源和许可证。不要只复制 `SKILL.md`。

Codex 支持项目级 `.agents/skills/` 和用户级 `~/.agents/skills/` 等本地技能位置；详见 [官方技能文档](https://developers.openai.com/codex/skills/#where-to-save-skills)。安装后检查宿主的技能列表；没有出现时重新启动宿主。

| 安装调用名 | 本源码中的完整目录 |
| --- | --- |
| `literature-search` | `light-literature/` |
| `light-chart` | `light-chart/skills/light-chart/` |
| `light-diagram` | `light-diagram/`，包含它使用的四个子目录 |
| `light-diagram-prompt` | `light-diagram/light-diagram-prompt/` |
| `light-illustrator-diagram` | `light-diagram/light-illustrator-diagram/` |
| `light-powerpoint-diagram` | `light-diagram/light-powerpoint-diagram/` |
| `light-visio-diagram` | `light-diagram/light-visio-diagram/` |
| 其余 `light-*` | 源码根目录中同名的完整技能目录 |

只需要某个 Diagram 子技能时可独立安装。安装总入口时保留相应子目录，避免破坏相对导航。`project-layout/` 是可选目录工具与规范，不是第 20 个技能；各技能已自带目录约定。

## 环境与调用检查

先确定任务，再准备依赖。文献和采集分别有自己的 Python 项目与清单；Chart 的 Python / R 依赖按所选路线准备；PowerPoint、Visio 和 Illustrator 桌面路线需要对应应用。论文默认 LaTeX＋PDF，用户模板优先，编译器与页面检查见 [light-write](../light-write/README.md)。

安装提供技能指引和本地工具，实际推理、联网、生图、桌面权限与计算资源由宿主和环境提供。首次使用应确认入口可发现、相关文件可读，以及当前任务需要的工具可用。

更新源码不会自动更新另一个安装副本。继续既有项目时确认实际调用目录与版本，避免多个同名副本造成混淆。
