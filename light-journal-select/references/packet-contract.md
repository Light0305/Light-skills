# 可选本地证据包 1.1

仅用于反复比较、更新或需要审计的交接；单刊咨询直接回答。空白起点是 [selection-packet.json](../templates/selection-packet.json)，合成示例是 [selection-packet.example.json](../templates/selection-packet.example.json)。示例不是研究材料或推荐结果，不能只改刊名就当真实核查。

## 最小字段

- `schema_version: 1.1`；`as_of` 为本轮实际结论日期（YYYY-MM-DD），不能在未来。来源访问日期不能晚于它；历史轮次保留历史日期，不能把旧访问日刷成今天。
- `research: {basis, inputs}`：basis 说明实际读到的研究材料、科学身份/版本、消息位置、未读范围；inputs 是本轮决定实际采用的本地文件快照列表 `[{path, sha256}]`。相对路径以证据包所在目录为基准，也接受明确的绝对路径；SHA-256 是小写64位十六进制。只对所列普通文件流式读取，不扫描项目或复制大数据。
- 只有消息/片段时 inputs 可空，basis 仍须具体；输出 `not_bound` 警告，不能声称做过文件版本验证。文件型研究应绑定实际分析/稿件、决定性本地政策或已读取的来源记录，不只登记一份记忆摘要。哈希由宿主对实际读取文件计算，不手填猜测值。
- `decision: {status, target_id, basis}`：status 为 `proposed / author_selected / delegated / unselected`。basis 引作者原话/消息或暂定理由。前三种 target_id 必须指已登记候选；unselected 必须为 null。作者选了不符合条件的刊，也保留其选择、列明冲突，不能伪造推荐已过关。delegated 只表示会话已授权代选，不授权投稿。
- `constraints[]`：`id, requirement, hard, origin, kind`。origin 为 `user / institution / funder / assumption`；assumption 只能软偏好。kind 为 `indexing / metric / fees / open_access / deadline / other`，按决定性事实分类；不能用 other 隐去已知收录或费用约束。
- `sources[]`：`id, kind, locator, accessed_on, applies_to`。kind 沿用 `official_journal / official_index / official_policy / primary_article / metadata / author_input / secondary`。locator 是精确 URL 或材料位置。可另记数据年、版本、有效时段、定位和简短释义，脚本不解释这些内容。
- `candidates[]`：`id, name, recommended, target, checks, identity, scope, article_type, fit, comparables`。recommended 是“可作为满足条件的推荐”，不是作者决定。待核或排除项为 false；同刊不同路线可用不同候选 ID，报告中归并展示，不能当两本刊。
- `target`：`publisher, homepage, issns, article_type, publication_route, submission_stage`。issns 是已核的 ISSN 列表，暂无可为空并说明缺口；脚本仅检查格式，不校验身份或校验位。article_type 用该刊正式类型，route 明确如 subscription / gold_oa / hybrid_oa；stage 为 `planning / initial / revision / transfer / production`。未知仍可建探索草案，不能把自拟标签当作已核官方路线。

## 来源必须覆盖所声明对象

applies_to 是实际检查后的适用声明，不是从 URL 自动推断，例：

```json
[{"candidate_id": "J1", "article_type": "Research Article", "publication_route": "hybrid_oa"}]
```

- 每项至少 candidate_id，其他字段可省略；省略只表示该来源未声明对类型/路线的限制，不能满足需要这些精确字段的门槛。共享政策可显式列多个候选，不能填虚构的“全部期刊”。
- 每个被引用的来源都要有一条匹配本候选的适用声明；如声明了文章类型/路线，也必须匹配 target。这里的文章类型是来源适用于本候选的类型，不要求可比论文本身与稿件类型完全相同。
- 身份/范围至少有适用的官方期刊/索引/政策来源，按脚本 FACET_KINDS 分工；文章类型另须显式匹配 article_type。费用和 OA 检查的 pass/fail 还必须精确匹配文章类型及出版路线。类型/路线标签匹配不证明页面内容真实支持结论。
- 收录检查的 pass/fail 至少指向 official_index；metric 至少 official_index / official_policy；费用、OA、时限至少 official_journal / official_policy / author_input。作者提供的已批减免/发票可作证，普通“我应该能免费”不能当已确认资格，必须披露外核状态。其余引用可提供背景，不能靠一种来源名称替代实质核查。
- 政策/指标版本、类别、费用资格和有效日期仍由宿主读原文判断。历史版本可能正是单位要求，不能机械以访问日期新旧或30天阈值作废；已知失效、撤回或发生冲突的证据要重核。

## 三态与先例

- `checks[]`：`constraint_id, status, basis, source_ids`；status 仅 `pass / fail / unknown`。漏硬条件按 unknown；非 unknown 必须有适用来源。
- `identity / scope / article_type` 同为 `{status, basis, source_ids}`，1.1 的 status 也用 pass/fail/unknown。fail 表示已证实身份/范围/类型不符，直接排除；unknown 条件性保留。这里不再用“核查过”代替“符合”。
- `fit`：`band, rationale, counterevidence`，band 为 `strong / plausible / weak / unknown / mismatch`。只有 strong/plausible 可进入已满足门槛的推荐；counterevidence 必填但仍要实际查反证。
- `comparables[]`：`title, year, locator, status, source_ids, shared_axes, important_difference`；status 为 verified/unverified，verified 至少有 primary_article / metadata。来源绑定期刊，不证明真的发表在该刊或实质可比，这两项由人核对。未来刊期年只有另记 `published_on`，且在线已发表日期不晚于 as_of 才可作先例；future/in-press 且尚未发表不能算。
- 没有已核先例可用 `precedent_exception: {reason, source_ids}`，需适用官方范围/类型证据并在报告披露不确定性；不豁免身份、类型或硬条件。

## 执行与解读

```text
python <skill-root>/scripts/audit_selection.py <round-dir>/selection-packet.json
python -m unittest discover -s <skill-root>/tests -p test_*.py
```

CLI 从证据包位置解析输入，工作目录可不同；只读本地文件，不联网、不执行其内容、不改输入。文件缺失/变动会使审计不通过，所有依赖这份研究画像的推荐均不就绪；保留旧轮次与旧哈希，重新读材料、判断贡献及受影响目标，再建新轮次。不要只刷新指纹消掉提示。内存调用 `audit(packet, packet_dir=...)` 才能核对文件；缺基准目录会明确 not_checked 并不通过。

输出包括 `audit_level`、`input_integrity`、`eligible / conditional / excluded`、推荐所缺项和 `handoff`。eligible 只表示输入声称的门槛通过，不等于最优目标。handoff 中 `target_authorized` 与 `evidence_ready` 分别表示声称的作者决定权限和本地门槛，不互相推导；暂定目标仍可交共用提纲，不强迫作者先确认。未选目标、没有推荐、诚实记录待核/排除的包可返回0；**0不是“存在合适首投”**。1 表示错误推荐或文件版本问题，2 表示输入损坏/结构不合法。

旧1.0原样兼容：facet仍用 verified/unverified；输出 legacy_1.0 及未检查对象/路线/研究版本/决定权限的警告。不自动升级旧档或声称已完成1.1核验。完整交接还要人工核对实际内容、版本、科学依据、作者决定和官方政策；本程序不能认证网页、真实性、科学匹配、录用率或最优排序。
