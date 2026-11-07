> 来源原文，保留完整上下文；执行规则见本包 SKILL.md 与 references/source-adaptation.md。API 为接口约定，示例值与统计不直接用于真实研究。

# Real-World Demos and Figure Scripts

The design theory, patterns, and guidance in this skill are derived from the figure-making scripts in the [figures4papers](https://github.com/ChenLiu-1996/figures4papers) repository. Those scripts are the canonical demos for this skill.

**Repository:** [https://github.com/ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)

## Project folders (demos)

Each folder contains Python scripts and (in `figures/`) outputs that follow the skill's house style. Use them as references for bar charts, trend and line panels, heatmaps, radar or polar comparisons, and multi-panel layouts.

| Project | Link | Notes |
|--------|------|--------|
| **figure_ImmunoStruct** | [figures4papers/figure_ImmunoStruct](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_ImmunoStruct) | Bar plots for quantitative comparison |
| **figure_CellSpliceNet** | [figures4papers/figure_CellSpliceNet](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_CellSpliceNet) | Bar comparison, ablation |
| **figure_Brainteaser** | [figures4papers/figure_Brainteaser](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Brainteaser) | Bar composition breakdown |
| **figure_VIGIL** | [figures4papers/figure_VIGIL](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_VIGIL) | Radar plots, line plots |
| **figure_ophthal_review** | [figures4papers/figure_ophthal_review](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_ophthal_review) | Trend plots |
| **figure_RNAGenScape** | [figures4papers/figure_RNAGenScape](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_RNAGenScape) | Heat maps |
| **figure_Dispersion** | [figures4papers/figure_Dispersion](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Dispersion) | 3D-style spheres, performance plots |
| **figure_Cflows** | [figures4papers/figure_Cflows](https://github.com/ChenLiu-1996/figures4papers/tree/main/figure_Cflows) | Comparison, ablation, trajectory plots |

本包已保留相应完整实现、可用数据和预览，按 [本地任务路由](../../../library-guide.md) 或 `scripts/library.py search` 查找；无需访问原仓库才能使用。下表上游链接保留为来源标识。

## Related files

- [SKILL.md](../../../../SKILL.md) — When to load this skill
- [api.md](api.md) — Constants, helpers, validation
- [common-patterns.md](common-patterns.md) — Layout and legend patterns
- [design-theory.md](design-theory.md) — Style theory and reproduction rules
- [tutorials.md](tutorials.md) — Step-by-step figure builds
