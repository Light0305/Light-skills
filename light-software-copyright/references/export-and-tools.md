# 导出、依赖与实际文件检查

## 内置工具

| 工具 | 作用 | 依赖 |
|---|---|---|
| `copyright_case.py init` | 建立未知事实底稿；已有 case 保留 | Python 标准库 |
| `scan` | 发现候选、文档/忽略项、编码、统计、哈希和疑似秘密 | 标准库；Git 可用时标记 ignored |
| `extract` | 核对完整范围、逐文件哈希与秘密，生成连续页映射 | 标准库 |
| `audit` | 核对真实项目、事实、输入版本和实际交付文件 | 标准库；有 PDF 时需 pypdf |
| `render_materials.py --kind application` | TXT 填报底稿与完整/提交统计 | 标准库 |
| `--kind code --formats docx,pdf` | 同一源行映射的 DOCX 与固定分页 PDF | python-docx、ReportLab、可用中文字体 |
| `--kind manual --formats docx,pdf` | 将已写好的结构化正文排版；不替 Agent 编造内容 | python-docx、ReportLab；有图需 Pillow |
| `--release --kind …` | 通过本地 audit 后复制相应现有草稿到正式资料 | 不重新生成、不联网、不提交 |

按实际需要安装 `python-docx reportlab pypdf Pillow`，可在独立环境执行
`python -m pip install -r "<SKILL_DIR>/requirements-render.txt"`。优先复用已安装的能力；不改全局
办公配置、不强制安装固定版本 OfficeCLI、不要求用户仅为创建草稿重启编辑器。
脚本已在 Python 3.11 下验证，核心语法最低要求 3.10；依赖范围见文件，具体本次环境见验证报告。

中文 PDF 使用本地可嵌入 TrueType 字体，默认尝试 Windows 宋体等已知路径；也可传
`--font "<本地 TTF/TTC 路径>"`。不附送受限字体、不联网下载字体、不用替换方框假装成功。
内置 DOCX 使用宋体，其他系统如会字体替换，应先安装合法可用字体或使用文档工具调整并复核。

## 操作示例

整套请求默认准备 functions.json（功能说明）和 manual.json（软件说明书），抽取源码后执行：

```text
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料路径>"
python "<SKILL_DIR>/scripts/copyright_case.py" audit --case "<材料路径>"
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料路径>" --release
```

默认 kind=bundle、formats=docx；三份全部构建成功再发布，输入问题不会新发布半套草稿，
磁盘或权限故障仍需读回实际状态。发布在 `正式资料/软件名称 版本/`，只含三份 DOCX，
目录已存在则拒绝覆盖；同版本修订使用新的材料修订目录保留前版。
新 case 默认 three-documents；旧 case 无 profile 沿旧单项命名/版式，显式 bundle 则选三份。
三份是本包交付约定，申请表、身份证明等实际申请文件另按当次任务核对。
以下单项命令按需使用，不是要求默认多交一份 TXT 或 PDF。

从 `SKILL_DIR` 解析脚本路径。先 `init → scan`，Agent 审核事实和 selection 后 `extract`。
把人工/模型根据证据写好的正文保存为 `manual.json`，再导出。
申请字段未齐也可生成草稿；标题必须至少有实际名称和版本。未知项显式显示，`audit` 不会因此
把草稿升级成完成品。缺依赖时不写空 DOCX/PDF，不把 Markdown 改扩展名。

```text
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料路径>" --kind application
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料路径>" --kind code --formats docx,pdf
python "<SKILL_DIR>/scripts/render_materials.py" --case "<材料路径>" --kind manual --formats docx,pdf
python "<SKILL_DIR>/scripts/copyright_case.py" audit --case "<材料路径>"
```

程序退出码 0 表示该操作成功，2 表示需处理的问题。`audit` 的成功只表示 `local_review_ready`，
`portal_ready` 始终为 false；没有机器脚本可以据几项布尔值认定法律事实或登记通过。
仅整理单份材料时，`audit --only manual` / `--only functions` / `--only code` / `--only application` 只检查相应范围；
`--release` 同样只复核本次材料种类，不要求额外生成整套文件。

## 独立排版与文件验证

代码 PDF 直接按冻结页映射绘制，检查每页名称/版本、实际页数和可提取的源文本；DOCX 内容
用 XML 对照原始映射。两种格式独立生成，不能声称 PDF 是 DOCX 的办公软件转换件。
DOCX 中的实际页数、字体替换、目录域与阅读器兼容性仍须在目标软件或真实转换后验证。

手册 DOCX 与 PDF 使用相同正文，但分页可能不同。内置模板适合普通标题、段落、步骤、
参数表、代码块和插图；复杂跨页表、目录域、长图、特殊公式或 60 页以上文档应使用可用文档
工具作专项排版和节选，不能把本工具的简单模板称为覆盖所有提交形态。
如果手册实际超过 60 页，保留完整底稿并另建一般交存的前后连续节选；内置代码分页不能
用于裁切文档。`audit` 会阻止未经处理的超长手册作为正式发布材料。

渲染 PDF 可使用已安装的 `pdftoppm` 或 PyMuPDF；至少看首页、复杂内容页和末页，代码还看
前后页连接处与最长行页。核对清晰度、遮挡、比例、行密度、文字截断、乱码和意外空白。
有图页/末页等情形记录适用依据。`reviews.visual_review` 写实际检查工具、页码和发现，不能
在没有看图时填“通过”。不需要为本地可编辑草稿新增审批流程。

## 保留与续作

渲染器覆盖同名文件前，把不同内容保存到 `历史资料/`；正式文件只通过 `--release` 复制。
清单中的当前版本被替换，旧文件不会被删除。用户手改稿的哈希变化使 audit 报错，应先归档、
理解修改，再更新正文输入重建；不要为了通过检查把用户修改静默覆盖。
输入指纹包含 case、相关源映射/选择及手册图片；补图或改名后应重建受影响的材料。
功能说明/说明书还绑定 features.evidence 实际项目文件，代码只绑定自己的源页及事实等输入；
单改 functions.json 不会使 code/manual 失效。layout-profile.json 记录所用参数，
与当前包参数不同时拒绝静默采用，按 [参考排版](reference-layout.md) 人工处理。
当前材料文件名包含版本，不把历史资料列作待上传文件。
