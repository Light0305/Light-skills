# light-diagram-prompt

2026-10-27 已完成四篇真实论文、十张生图的首轮实测，包含问题修订与失败版本留档。打开本目录 evaluations/2026-10-27/index.html 浏览图片和完整提示词；报告位于 evaluations/2026-10-27/REPORT.md。三个案例在限定概念范围内通过本轮目视检查，Transformer详细连线仍需校正。此结果不代表多模型通过率。

A prompt-first skill for turning research content into strong image-generation prompts for **non-data scientific diagrams**: method and system figures, architectures, mechanisms, workflows, experimental setups, conceptual diagrams, taxonomies, comparisons, and graphical abstracts. It can also generate with host tools or an optional user-configured service.

## Boundary

This skill delivers the design brief and complete prompt before any generation. Unless prompt-only is requested, it prefers a native host image tool, otherwise a configured image service; without either, prompt delivery is sufficient. Editable reconstruction in Illustrator, PowerPoint or Visio remains downstream. See [generation configuration](references/image-generation.md) and the [configuration example](assets/imagegen.example.json).

Quantitative plots are out of scope. For mixed figures, keep real plots, microscopy, photographs, and measured evidence as user-supplied assets; never ask an image model to fabricate them.

## Files

- `SKILL.md` — scope, workflow, response format, and routing rules.
- `references/diagram-archetypes.md` — select the right information structure.
- `references/domain-visual-language.md` — domain objects, relationship semantics, and failure modes.
- `references/prompt-structure.md` — Figure Brief and prompt assembly guide.
- `references/prompt-quality-check.md` — final scientific and visual audit.
- `references/worked-examples.md` — complete cross-domain teaching examples and boundary cases.
- `references/reference-corpus.md` — optional local corpus inventory, retrieval protocol, and provenance.
- `references/reference-observations.md` — observations from images actually opened during skill design.
- `references/acceptance-cases.md` — offline behavior and quality-boundary scenarios.
- `scripts/search_reference_figures.py` — optional offline filename/metadata search and Pillow contact-sheet helper.
- `scripts/image_service.py` — offline generation-route planning and a user-configured OpenAI-compatible Image API client.

## Optional local corpus helper

The helper searches filenames and available JSON metadata (not visual similarity). If Pillow is installed, it can save a contact sheet for human inspection. Run from PowerShell, Bash, or another shell with Python 3:

```bash
python -I "D:/Light-Science/light-diagram/light-diagram-prompt/scripts/search_reference_figures.py" "D:/Light-Science/light-diagram/light-diagram-prompt/Some papers' diagram/topconf-paper-figure-gallery-main这个仓库提供的" --query "multimodal alignment" --pattern framework --metadata "D:/Light-Science/light-diagram/Reference  Repositories/skill/topconf-paper-figure-gallery-main/data/figures.json" --limit 12 --contact-sheet "D:/Light-Science/light-diagram/light-diagram-prompt/reference-candidates/alignment-contact-sheet.png"
```

The helper does not modify source figures and refuses to overwrite an existing contact sheet. Candidate ranking is text-only; inspect selected images before describing visual traits. Without a corpus, metadata, or Pillow, the core skill remains usable.

## Local checks

```bash
python -I -m unittest discover -s "D:/Light-Science/light-diagram/light-diagram-prompt/tests" -v
```

These tests check the offline search helper and document structure; they do not run the skill through an LLM or test image-generation quality. See `VERIFICATION.md` for the checked scope and limitations.

## 中文快速使用

当前文件夹是独立 skill 源码包，尚未自动安装到宿主的技能目录。可以让助手先读取本目录的 `SKILL.md` 并按照它处理请求；需要斜杠调用时，把整个技能包放到宿主支持的 skills 目录中（图库可选），重新加载后使用 `light-diagram-prompt`。不需要安装参考仓库；生图 API 配置是可选项。

示例请求：

> 按 light-diagram-prompt 的流程，根据下面的方法段生成英文论文方法图提示词。重点突出两个分支如何融合，图中文字用英文，参考本地图库的相近架构图。只输出最终 prompt。

> 根据这段材料界面机制描述生成生图提示词，保留层序和离子迁移方向，不添加原文没有的反应中间体。

完整流程默认返回简短图意与结构、实际查看的参考图观察、完整可复制提示词，以及生成后核查点。未知生图模型采用通用写法；没有图库也可运行。`Some papers' diagram` 是可选的大型本地素材库，分发技能时无需一并打包。

需要图片时，先展示提示词或实际提示词文件链接，再优先调用宿主生图；宿主没有生图工具时使用可选的 URL/Key/模型配置。两者都没有，或明确只要提示词时，交付提示词即可。配置方法与调用命令见上方链接。

## Use

Give the skill a paper, methods section, caption, research plan, protocol, concept, existing figure, and/or visual references. It will identify the figure's claim and structure, use available references when appropriate, and return a self-contained prompt with exact allowed labels and scientific boundaries.

For the best method diagrams, provide the methods text and the figure's intended message. An abstract alone supports a high-level concept, not a detailed reconstruction of method internals.
