# Acceptance Cases

These cases define what the skill should do. They are offline review scenarios, not a claim that an image model has been run or that visual quality has been benchmarked.

## Routing and scope

1. **Method section → architecture prompt**
   - Input: modules, tensor/data flow, one contribution, and a caption.
   - Expect: a selected architecture/framework archetype, explicit directional edges, a visible-text whitelist, and no invented internal layers.

2. **Mechanism text → compartment-aware mechanism prompt**
   - Input: named entities, compartments, activation/inhibition, and causal order.
   - Expect: domain-appropriate spatial zones and edge semantics; no unmentioned intermediates.

3. **Protocol → workflow prompt**
   - Input: ordered steps and named equipment.
   - Expect: the stated order and equipment only; no invented timings, parameters, groups, or outputs.

4. **Quantitative chart request**
   - Input: “make a bar chart/heatmap/ROC curve.”
   - Expect: route to a data-figure workflow; do not write an image-generation prompt that fabricates values.

5. **Mixed diagram and results panel**
   - Input: a method schematic plus real plots or microscopy images.
   - Expect: prompt only the schematic and mark factual panels as supplied immutable assets or reserved spaces.

## Input sufficiency and references

6. **Abstract only**
   - Expect: high-level conceptual prompt if the main claim is clear, plus a limitation note; do not infer detailed modules.

7. **Reference image available and readable**
   - Expect: observable style observations separated from target science; no copied labels, data, logos, or exact composition.

8. **Reference image unavailable or unreadable**
   - Expect: no invented visual analysis; proceed from text or ask for a concise description when the reference is essential.

9. **Local corpus available**
   - Expect: candidate retrieval by archetype/pattern then domain, inspection of only a small set, and explicit source paths. Metadata/text search must not be described as visual similarity.

10. **Local corpus absent**
    - Expect: core prompt workflow continues without failure or hard dependency on the corpus.

## Prompt integrity

11. **Final prompt**
    - Expect: no unresolved scaffolding (`[Label]`, `{VISIBLE_TEXT_RULE}`, `<...>`, or internal schema markers); exact visible-text whitelist embedded in the prompt; scientific negative constraints.

12. **Chinese user with English paper**
    - Expect: Chinese explanation but prompt/labels selected from paper and venue language, unless the user requests Chinese labels.

13. **Text-heavy figure**
    - Expect: concise supported labels and a warning about image-model spelling risk; offer minimal-label/blank annotation variant rather than promising exact typography.

14. **User requests prompt only**
    - Expect: only a complete copy-ready prompt, without internal reasoning or a separate tutorial.

15. **User returns a generated image for revision**
    - Expect: inspect before evaluating; list concrete science/topology/text/style defects; return a complete revised prompt and do not claim pixel-perfect restoration.

## Quality boundaries

16. **Reference figure mixes chart and schematic**
    - Expect: transfer layout rhythm only; preserve or exclude charts as real assets; never reproduce numbers from the reference.

17. **Unknown or cross-disciplinary domain**
    - Expect: use the common entity/process/relationship protocol, state assumptions, and ask only the question that affects scientific correctness.

18. **Uncertain causal relation**
    - Expect: retain uncertainty or use a clearly defined tentative relation; never upgrade correlation or temporal order to causality.


## 持续项目情境（待宿主行为验证）

19. **Memory 留有旧版机制，但原始分析已经更正**
    - Expect: 用 Memory 找到旧决定和采用图版，再读新版分析；复核受影响实体/边/图注，保留父版，不仅更新哈希。

20. **用户只要求把现有标签换成稿件采用术语**
    - Expect: 定位参考和稿件版本，完成局部修改与相关复查；无需重新做整篇文献、生图或建立完整 handoff。

21. **宿主内置生图技术失败，但已有授权 fallback**
    - Expect: 复用宿主既有适配器/配置，保留失败链和实际发送提示词；不重复索要 Key，不把安全拒绝转给另一供应商。

22. **Review 把概念连线误当作已证实机制**
    - Expect: 回查科学来源及图注，明确假设边界；无法支持时收缩或移除关系，把具体证据问题交回专业阶段，而非美化箭头后关闭问题。

这些是待运行的行为情境；离线脚本、真实桌面小样均不能替代模型对这些情境的实际处理。
