# 案例 B：作者演练输出

本文件由技能作者在同一构建会话编写，不是独立评测。来源为 [合成命题 B](../fixtures/case-b.md)，请求仅涉及命题与证明。

在给定范围内，这个命题为假。科学就绪（本次命题范围）为 **hold**；完整论文未提供，不能评估其整体就绪状态。投稿文件检查为 **not_requested**。

## LR-001 · critical · confirmed · blocking=true

位置：Proposition 的“C independent of epsilon”与 Proof 的“Set C=1/epsilon”。所选 C 随 epsilon 改变，不能证明原命题要求的统一上界。

反例检验：取 x=1、y=0，原不等式要求 1/epsilon <= C 对所有 epsilon∈(0,1] 成立。任给有限 C，若 C≤0 则 epsilon=1 已违反；若 C>0，可选 epsilon<min(1,1/C)，使1/epsilon>C。因此在原假设内不存在这种统一有限 C。

最小修复：交回 `light-write` 或作者确认实际意图。可改为“每个固定 epsilon 的 Lipschitz 常数为1/epsilon”，此时允许 C 依赖 epsilon；也可将 epsilon 限制在[epsilon_0,1]，epsilon_0>0，得到统一 C=1/epsilon_0。两种修改都改变原命题范围，应检查后续定理是否仍成立，不能悄悄改量词。

关闭检验：在选定的新命题及实际参数范围内重查量词、常数依赖与所有使用它的推导。当前状态 open。

优点：差分恒等式本身正确，它足以证明固定 epsilon 的结论。此问题是确定的理论反例，不需要统计显著性、随机种子或经验实验来解决。未评估其他定理、整体论文或新颖性。
