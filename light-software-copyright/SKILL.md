---
name: light-software-copyright
description: >-
  Prepare, revise, and check Chinese software copyright registration materials
  from real software: function descriptions, traceable source-code deposits,
  software manuals, optional application worksheets and correction responses.
  Use for 软著、软件著作权申请材料、源程序鉴别材料、软著说明书、申请表填报辅助、
  材料补正 and version updates. Supports research scripts, CLI tools, libraries,
  services, desktop and web applications; ordinary code documentation and
  patent drafting do not need this skill.
metadata:
  version: "0.2.0"
---

# Light · 软件著作权材料

## 项目目录与续作

需要落盘或继续已有项目时，先读 [项目目录约定](references/project-layout.md)，按其中的本阶段位置、版本与关联规则保存；用户指定路径和旧项目优先。包内资源相对本 skill，研究产物相对真实项目，二者不要混用。只做局部讨论时无需初始化目录。

把真实软件整理成内容可信、口径一致、能够追溯到项目的软著材料。默认中国大陆登记；
其他司法辖区先核对当地制度，不套用本技能的交存规则。主要负责本地材料和填报辅助，
不默认登录、上传或提交登记申请。

整套默认只交付 **功能说明.docx、软件代码.docx、软件说明书.docx**，各带软件名称和版本。
功能说明讲已实现能力、使用场景与可观察结果，软件说明书解释实际设计或操作过程，
两者互相引用而不重复拼装。填报底稿、事实表、源行映射和检查记录留内部，按需另供。
三份是本包的交付约定，不等于法定申请的全部文件；真实提交另核申请表、身份证明及当次要求。
持续项目从有关 Memory / Workflow 恢复，再回真实源码、运行证据和采用版本，
按 [项目接入与回传](references/project-integration.md) 衔接；局部请求只处理所需一份。

## 先判断这次要做什么

| 用户需要 | 执行范围 | 按需阅读 |
|---|---|---|
| 从项目做一套材料 | 读项目、梳理事实、写三份、导出、检查 | [项目证据](references/project-evidence.md)、[文档写作](references/manual-writing.md)、[参考排版](references/reference-layout.md) |
| 只有软件构想或论文 | 做材料准备清单；明确尚缺的实现 | [项目证据](references/project-evidence.md) |
| 只写/改说明书 | 按真实软件形态选择操作手册或设计说明书 | [文档写作](references/manual-writing.md) |
| 整理源码、计算源程序量 | 明确登记范围，冻结快照，连续分页 | [源码交存](references/source-deposit.md) |
| 检查材料、处理补正 | 先读现有材料/通知；定位冲突，再做局部修改 | [检查与补正](references/review-and-correction.md) |
| 更新版本或继续上次工作 | 读取已有 case 和报告，仅重建受影响材料 | [检查与补正](references/review-and-correction.md) |
| 查规则、准备正式导出 | 核对官方来源、规则适用范围和当前表单 | [规则与来源](references/rules-and-sources.md) |

不要求用户使用这些模式名。用户只要一份材料，就完成这一份，不自动扩成整包。
参考仓库的取舍见 [调研记录](references/repository-research.md)，正常执行无需读取。

## 材料必须成立的事实

- **从项目出发。** 读入口、核心实现、说明、配置、测试和实际界面/命令，再提炼功能。
  文件名、README 宣传和行业常识只是线索。尚未实现的功能不写成已具备。
- **登记软件的完整范围与交存节选分开。** 先界定本次版本的自有程序，确定完整有序底稿，
  再选前后连续页。不能从仓库任挑 3,000 行就称为前后 30 页，也不能用节选行数填总量。
- **源码不造假。** 不凑满 60 页、不复制重复代码、不临时生成业务实现充当既有程序，
  不删除原作者署名、版权头或改名掩饰来源。正常应用开发需求另行处理，完成后再冻结真实版本。
- **区分来源。** 标明用户已确认事实、项目观察、建议值、未核实项；姓名、权属、完成日、
  首次发表、真实部署配置等不能靠 Git 作者、文件时间、机器配置或模型推断冒充确认。
- **遵循当前表单。** 稳定的规章要求与门户动态要求分别记录。AI 使用事实如实保留；
  如果实际签章承诺与事实冲突，指出具体冲突并请申请人核实办理口径，不生成虚假承诺、
  伪造人工研发记录，也不以“降 AIGC”规避声明。未联网不妨碍有清楚标记的本地草稿。
- **资料可续作。** 单一事实源和追溯清单随材料保留，不把唯一证据放入临时目录后删除。
  不把内部 JSON、审计记录、占位截图混入拟上传文件。

## 默认执行方式

解析本文件所在绝对目录为 `SKILL_DIR`。使用可用 Python 3.10+；命令中的变量/尖括号应
替换成真实绝对路径。不要把项目根目录、skill 安装目录和材料输出目录混用。
下面命令为单行形式，Windows、macOS、Linux 均可调用；按当前 shell 正确引用路径。

### 1. 先读已有材料，再定位项目

优先复用会话、已有申请表、说明书、源代码和补正通知。多个可独立登记的项目才询问范围，
只有一个明确项目就直接继续。新材料默认放研究项目的 `SoftwareCopyright/SWC-0001_软件版本/`，已有 `软件著作权申请资料/` 原地续作，用户指定路径优先。
只读分析源码；不启动训练、生产服务、收费 API 或迁移数据库来证明功能。

```text
python "<SKILL_DIR>/scripts/copyright_case.py" init --project "<项目绝对路径>" --case "<材料绝对路径>"
python "<SKILL_DIR>/scripts/copyright_case.py" scan --case "<材料绝对路径>"
```

脚本收集文件、哈希、编码和风险线索，不替模型判断功能或著作权。
读取 `inventory.json` 指向的实际文件，填写 `case.json` 的功能证据、适用人群、环境建议等，
并审核 `selection.json` 中每个候选的范围与来源。未知扩展名、Notebook、Git 忽略文件和
未读取文件都要有处理记录，不静默当成“没有源码”。

### 2. 先做可审阅草稿，集中补充缺失事实

给用户简短的软件理解和建议口径，尽可能同时完成申请字段、说明书结构、源码范围清单。
只集中询问仍缺少或互相冲突的登记事实；已有明确授权或已确认信息直接沿用。
可继续不依赖答案的分析、写作和检查。生成可编辑 DOCX/PDF 本身不另设审批门禁。

`case.json` 是唯一事实底稿，结构见 [assets/case.example.json](assets/case.example.json)。
`null` 表示未知，不能用示例公司、默认日期、V1.0 或开发机配置自动填满。
`reviews.facts_confirmed` 仅在对话或既有材料确有依据时设为 true，并记录依据。
`scope_reviewed` 是 Agent 审核程序范围的记录，不是假装用户逐文件确认。

### 3. 写与软件形态匹配的文档

按 [文档写作](references/manual-writing.md) 写作，使用
[assets/functions.example.json](assets/functions.example.json) 和
[assets/manual.example.json](assets/manual.example.json) 作为两份正文的渲染输入结构；
版式依 [参考排版](references/reference-layout.md)，不复用样例软件的代码、名称、单位或事实：

- 有界面应用：按真实任务写“进入—输入—操作—反馈”，以真实截图支撑关键过程。
- CLI/科研工具：写实际命令、参数、输入格式、输出解释、错误与复现条件。
- 库、API、后端、嵌入式：可选设计说明书，解释模块、接口、数据、算法和运行逻辑。
- Notebook：保留代码单元来源，运行输出/数据与程序代码分开；不把论文改写成虚构软件。

截图复用用户提供的原图或真实运行取证；记录来源、版本、角色、页面/命令及哈希。
浏览器/桌面工具按所在环境选择，不限定某个产品。缺图时交付草稿并列补图任务；
无界面的设计说明书不强制截图。AI 设计图和架构示意不能充当运行截图。

### 4. 冻结源码与导出

先读 [源码交存](references/source-deposit.md)。在 `selection.json` 中审核所有候选，
排好完整底稿顺序并填写理由，再运行：

```text
python "<SKILL_DIR>/scripts/copyright_case.py" extract --case "<材料绝对路径>"
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料绝对路径>"
```

初次导出统一进 `草稿/`。`--release` 只在检查完成后复制到 `正式资料/`，会保留已有版本，
不自动上传。详见 [导出与工具](references/export-and-tools.md)。
核心扫描/抽取只用 Python 标准库；DOCX 用 python-docx，代码宽度量测/PDF 用 ReportLab + 可用中文字体，
图片用 Pillow，有 PDF 时核验另需 pypdf。填报 TXT 或 PDF 仅在请求/实际需要时生成。
用已安装的库或文档工具即可；缺依赖先完成正文和中间底稿，不把安装/重启当作开始写作的前提。
内置工具不支持的版式可用环境内可用文档工具，仍须记录真实文件并检查。

### 5. 检查到能诚实交付

```text
python "<SKILL_DIR>/scripts/copyright_case.py" audit --case "<材料绝对路径>"
```

机器核验覆盖事实缺失、范围遗漏、快照变动、哈希、节选连续性、名称版本、旧材料和占位符；
只处理单份材料时，用 `audit --case "<材料绝对路径>" --only manual`（或 `functions`、`code`、`application`），
不要求用户为一份说明书补齐整套申请字段或生成无关材料。
内容是否准确、权属是否有依据、截图是否真实和实际排版仍需阅读。
PDF 至少检查实际页数、首页/中间连接处/末页、最长代码行与复杂图表页；文档长时按风险扩展。
发现截断、乱码、空白页或计行不足应修复再验，不能靠声明成功。

交付区分：**草稿可继续编辑 / 本地材料已核验待申请人复核 / 当前表单与签章待核实**。
本地检查通过不等于受理、登记成功或所有门户条件满足。提供材料绝对路径、实际文件用途、
尚缺事实和下一步即可；无须向普通用户倾倒内部参数和检查流水账。

## 输出与续作

```text
SoftwareCopyright/SWC-0001_软件版本/
  case.json                  名称版本、登记事实、功能证据、核验依据
  inventory.json             文件发现和风险线索
  selection.json             完整登记范围、排除理由和底稿顺序
  source-pages.json           原始行/Notebook 单元 → 底稿页 → 提交页
  functions.json             已实现功能、使用场景与结果
  manual.json                经项目证据校核的正文
  layout-profile.json        本案件采用的干净排版参数
  screenshots/               真实截图及旁置来源记录（有需要时）
  草稿/                      可编辑材料；未核实项可见
  正式资料/软件名称 版本/    默认仅三份 DOCX；已有版本不覆盖
  deliverables.json          生成输入/文件哈希与实际检查结果
  audit.json                 可复核的问题及下一步
```

这不是强制用户接受的文件夹布局；已有规范可沿用，并相应调整脚本路径。
续作先核对事实、源码及文档输入的指纹；改名/换版本重建页眉和关联文件，补图只重建文档，
代码变动重扫并重新审核变化项。保留用户手改稿和历史材料，不自动覆盖。
