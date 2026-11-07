# light-software-copyright

基于真实软件项目，辅助编写中国软件著作权申请材料的独立 skill。

源码版0.2.0，默认交付“软件名称 版本_功能说明.docx”“软件名称 版本_软件代码.docx”
和“软件名称 版本_软件说明书.docx”。参考排版参数与原生文档结构见
[参考排版](references/reference-layout.md)，本轮验证见 [升级记录](evaluations/2026-11-07-upgrade.md)。

支持可选申请表填报底稿、操作/用户手册、无界面软件设计说明书、源程序一般交存材料、材料检查、
补正和换版。适配 Web、桌面、CLI、科研脚本、Notebook、API 和软件库。

## 使用

技能入口是 [SKILL.md](SKILL.md)。将发布包中的 `light-software-copyright` 文件夹放进 Agent
支持的技能目录，例如 Codex 的 `~/.codex/skills/`，即可显式调用：

```text
请使用 $light-software-copyright，为当前真实项目整理一套软著材料。
先自行阅读源码和文档，能确认的信息直接复用，只集中询问缺失的登记事实。
```

也可以说“只写设计说明书”“检查这套材料名称版本是否一致”“按补正通知修改”。
没有项目源码时会整理材料准备清单，不会虚构源码或产品功能。

## 包含什么

- 可按任务读取的项目理解、申请字段、文档写作、源码交存、导出和补正指南。
- 标准库实现的候选扫描、完整范围审核、SHA-256 快照、Notebook 代码抽取和连续页映射。
- 默认三份DOCX；TXT填报底稿、PDF预览与内部检查记录按需，交付副本只含三份DOCX。
  三份交付不等于登记所需全部法定文件。可先完成草稿，再复核和保留历史版本。
- [参考仓库调研](references/repository-research.md)和[规则来源](references/rules-and-sources.md)。

依赖、命令及局限见 [导出与工具](references/export-and-tools.md)。不强制绑定 OfficeCLI、
浏览器产品或云服务。扫描/抽取只需 Python 3.10+；文档导出依赖按需安装。

## 验证与打包

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/package_skill.py
```

发布包使用文件白名单，只包含技能入口和运行所需资源；不包含用户提供的第三方参考仓库、
调研下载快照、测试输出或真实申请资料。本工作目录的参考仓库保持独立。

法规基线和门户动态要求分别记录。本地检查通过只代表材料可供复核；当前表单、签章及权利
事实仍需申请人确认。脚本不登录、上传或提交申请，也不出具登记通过保证。
