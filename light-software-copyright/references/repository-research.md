# 参考仓库调研与设计取舍

核验日期：2026-11-02。方式：先读取用户本地两份参考，再用 Web 搜索发现项目，以 GitHub
公开仓库、原始文件和 `git ls-remote` 核对来源。阅读技能入口、相关规则/示例及部分关键实现；
**未运行上游整套流程，也没有验证任何仓库的“过审率”**。本技能测试只覆盖自己编写的工具。

## 重点比较的八个方案

| 仓库 | 本次读到的价值 | 本技能的取舍 |
|---|---|---|
| [Fokkyp/SoftwareCopyright-Skill](https://github.com/Fokkyp/SoftwareCopyright-Skill) | 用户已提供本地副本。项目业务理解、候选选择、草稿与正式输出分开，并有 demo | 保留先理解再写材料、真实源码与一致性；不沿用前端固定优先、补足 60 页目标、每阶段停等和绑定 OfficeCLI 的限制 |
| [IvanCodesDev/software-certificate-skill](https://github.com/IvanCodesDev/software-certificate-skill) | 用户已提供本地副本。一次收集事实、截图取证、确定性代码 PDF、较完整的质量检查 | 保留集中询问和源码映射；不把唯一审计记录留在临时区后丢弃，不把 40–60 页作为普通手册默认目标，不要求无界面软件取 UI 图 |
| [Light0305/Light-skills](https://github.com/Light0305/Light-skills/tree/master/skills/light-software-copyright) | 从综合科研技能包找到同名子技能。强调真实项目、权利依据、第三方复核、哈希和独立材料任务 | 借鉴研究软件适配与追溯思路；补全可用的文档渲染、Notebook 代码单元和实际产物核验。未把科研 DAG 内部协议搬进独立技能 |
| [suling-fun/software-copyright-materials-skill](https://github.com/suling-fun/software-copyright-materials-skill) | 真实项目分析、申请字段和门户操作参考，强调材料和项目关联 | 借鉴材料拆分与按阶段读参考资料；本技能聚焦本地材料，默认不登录、不上传，不把上游操作经验视为当前官方要求 |
| [Rodert/copyright-forge-skill](https://github.com/Rodert/copyright-forge-skill/tree/main/skills/copyright-forge) | 从创建、诊断、续作、补正、规则检查分流；官方来源登记与证据关系清楚 | 保留任务分流与补正定位；不引入每天自动检查/更新 skill 的旁路，不把“本地核验通过”说成可提交或已登记 |
| [xianxh/software-copyright-filing](https://github.com/xianxh/software-copyright-filing) | 源程序量、旧版本、真实程序结尾等常见错误提示具体 | 只取问题线索；不沿用具体项目路径/解释器、额外省略页、固定字数、Git 最后提交自动确定完成日等特定做法 |
| [shay-Ckm/dsh-skill-softcopyright](https://github.com/shay-Ckm/dsh-skill-softcopyright) | 多处统计交叉核对、统一材料交付的工程思路 | 保留单一统计来源与交叉核对；不把哈希清单/研发日志说成所有申请的法定附件，不提供降检测、虚构证明或研发历史的流程 |
| [raidenfc/my-skills](https://github.com/raidenfc/my-skills/tree/main/software-copyright) | 综合个人技能集中的子技能，采用规划与分步材料生成 | 作为组织结构比较；不沿用固定 60 页产物目标和过多前置确认；未确认许可证，不复制其正文或模板 |

## 也检索过，但不作为主要实现依据

- [CharlieJiang/SourceCodeDocxGenerator](https://github.com/CharlieJiang/SourceCodeDocxGenerator)：
  源码 Word 导出专用工具。README 公开说明完整文件写入可能超过预期页数，提示需要核对真实渲染。
  本次没有执行 JAR/EXE，也未作代码级评价。
- [Skyler-Luo/CCD](https://github.com/Skyler-Luo/CCD)：源码文档工具，README 提供 Word COM 分页方案。
  本次只核对公开介绍，不将依赖 Windows Word 的路线设为通用前提。
- [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills)、
  [aduhappy/aduhappy-skills](https://github.com/aduhappy/aduhappy-skills)：科研技能集合候选；
  宣传或聚合说明不能证明当前有可独立复用的软著子技能，本次未将其列为已完成软著实现精读。
- [caixinyu2017-star/xixi](https://github.com/caixinyu2017-star/xixi)：检索中发现的科研包聚合；
  用于发现上游 Light 子技能，不把同一份上游当作多个独立方案增加参考数量。

## 固定来源

下列 HEAD 经 `git ls-remote` 核对，避免只留下会漂移的分支链接。原始下载文件和本地参考的
SHA-256 记录在工作目录 `Software Copyright Reference  Repositories/research-manifest.json`。
本地副本不假定等于当日 upstream；两者身份和许可应分别核验。

| 仓库 | 2026-11-02 HEAD | 查询到的上游许可 |
|---|---|---|
| Fokkyp/SoftwareCopyright-Skill | `1159f6d280783616e1247f768690eac97c1a3f6e` | 此提交原始 LICENSE 为 GNU AGPL v3；本地副本 LICENSE 却为 MIT，存在差异，不能混同 |
| IvanCodesDev/software-certificate-skill | `ee7d4636f35210767adc0b5689f8678c68e6f7e6` | MIT；本地亦有 MIT 文件 |
| Light0305/Light-skills | `6b44f57d1274eb38a6c79dc29c2d21e5e0a225a9` | MIT |
| suling-fun/software-copyright-materials-skill | `6c9e6e72d8afce7aaccc9831ccd645a6ae2ccb16` | MIT |
| Rodert/copyright-forge-skill | `12ccf65b2a3b653cc08ad54805e33472d2073738` | Apache-2.0 |
| xianxh/software-copyright-filing | `d8b01841f2e98c4648fa4a07c98fbe5f40cae871` | MIT |
| shay-Ckm/dsh-skill-softcopyright | `19986d902ff35043332deeee21328533fbc4c8e4` | MIT |
| raidenfc/my-skills | `10a8ea080f1c9adbda25ca12d0720b5347fe2891` | GitHub 未识别，未确认授权 |

许可列是调研记录，不是第三方授权结论。本次没有把任何上游脚本/模板/图标复制进交付 skill；
入口、参考指南和两份脚本按本任务重新编写，研究快照单独保留在用户参考目录且不进入发布包。

## 实际落地的改进

1. 所有软件形态共用真实项目证据，但写法按 UI、CLI/科研和设计文档区分。
2. 完整源码范围、原始行数、非空行数、完整底稿页、提交节选页分别保存。
3. 程序新增、删除、改动、名称/版本更新和截图替换都会影响指纹，旧材料不能默默通过。
4. 真实秘密定位不回显值；不通过删除版权头、机械改写或假研发记录伪装来源。
5. 简单草稿可持续推进，不把依赖安装、截图和逐阶段确认变成所有工作通用的停点。
6. 机器实际读取项目与产物，能够发现篡改；明确人工语义/权属/视觉检查仍不是布尔值能证明的事实。
7. 法规基线、门户核验、转发线索分层存放，支持断网草稿而不冒充当日官方口径。
