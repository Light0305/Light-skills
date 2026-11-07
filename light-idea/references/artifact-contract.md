# 项目产物与可检查的关系

只有需要完整、可追溯项目时使用这些文件；快速讨论可在聊天中表达相同的关键判断。模板和示例中的文字是待填写内容，不是实验结果。

## 只读输入索引

`context.json` 由 `idea_bridge.py ingest` 写入，`schema_version="1.0"`。

- `papers[]`：保留原 `paper_id`、题名、作者、年份、DOI/URL、摘要、预印本/撤稿标记和原 `screening`；`assets` 是已有文件的绝对路径。
- `input_files[]`：实际输入文件的绝对路径、字节数和 SHA-256；供后续检测漂移。
- `upstream`：保留问题计划、检索覆盖及初步 gaps/ideas，不代表接受了原分析。
- `warnings[]`：记录元数据冲突、未人工筛选、来源缺失等。`reading_status="not_assessed"` 不能被脚本自动升级。
- `context_history[]`：可选；刷新前的完整 context 快照路径与 SHA-256，位于本工作区 `context-history/`。只保存索引，不备份原文；校验归档本身没有变化，不要求历史输入仍与当前文件相同。

不要手改 input fingerprints 让漂移检查消失；应重新导入并复核受影响的证据。输入材料可以混题，索引本身不能识别主题。

## 新检索到的论文

`external_papers.jsonl` 可选，每行一篇：

```json
{"paper_id":"ext_example","title":"Example only; replace with verified metadata","url":"https://example.org/paper","retrieved_at":"2026-11-02","is_preprint":null}
```

ID 是本地引用键，不是虚构的学术标识。保留真实 DOI、作者、年份和版本（能核对时填写）。与已有 DOI 重复时沿用原 ID，避免一个工作被当作多个独立支持来源。日期写实际检索日期。`example.org` 仅用于说明结构，不能进入真实交付的引用。

## 证据账本

`evidence.jsonl` 每行一条已实际查看的证据：

```json
{"evidence_id":"E01","paper_id":"p_actual_id","kind":"limitation","statement":"原文实际支持的有限主张","access_level":"full_text","source_file":"/absolute/path/paper.md","source_sha256":"<实际核对文件的小写SHA-256>","locator":"Methods §2.1 / Table 2","verified":true}
```

`source_file` 和 `source_url` 至少一个；本地文件用绝对路径。`locator` 必须有具体锚点，不能只写“论文中”。`access_level` 为 `metadata / abstract / full_text`。`kind` 为 `author_claim / observation / limitation / method / counterevidence`。

`verified=true` 的含义只是宿主已核对该位置及表述，不是事实获得独立验证；不能只为让验证通过而填写。原文结论和自己推测的机制不要写成同一条证据。页码不能由 Markdown 行号或 PDF 页文件名臆造。

本地证据记录实际核对时的 `source_sha256`；用作推荐的支持/最近工作证据时必需，刷新 context 也不能消除该来源的变动。旧非推荐记录缺哈希会提示，仍可继续梳理。URL-only 证据保留真实访问日期、版本和锚点，脚本不会联网核验远程内容。迁移与复读规则见 [修订与交接](revisions-and-handoffs.md)。

## 查重日志

`novelty_log.jsonl` 每行一次检索：

```json
{"search_id":"N01","idea_ids":["I01"],"idea_versions":{"I01":1},"idea_fingerprints":{"I01":"<当时科学内容的SHA-256>"},"date":"2026-11-06","source":"Crossref","query":"actual query","intent":"duplicate","status":"ok","result_paper_ids":[],"screened_summary":"实际检查的结果范围与判断","limitations":"语言、年份、访问或排序限制"}
```

意图见 [novelty.md](novelty.md)。`status` 为 `ok / failed / blocked / not_run`；后面三种记录保留原因，不算成功查重。`result_paper_ids` 都必须在本轮论文表中。零结果只能用于限定覆盖，不能单独支撑创新认证。

`idea_versions` 和 `idea_fingerprints` 共同对应当时的问题/机制/范围/判别方案。`fingerprint --workspace` 只读给出当前内容键，不进行搜索。对 `recommended`，当前版本、当前内容需要 `duplicate` 和至少一种其它意图的成功日志，而且两次 query 不能完全相同；这是最低记录要求，不表示两条日志已经足够。旧日志不改原日期或绑定；相关内容变动后真实重新检查并追加记录。

## Idea 记录

`ideas.json` 顶层：`schema_version`、`topic`、`constraints` 和 `ideas[]`。最小候选包含 `idea_id / version / title / status / question / rationale / basis_evidence_ids / novelty`。详见 [ideas.example.json](../templates/ideas.example.json)。

展开的候选另有：

- `claim_type`：`empirical / causal / theoretical / methodological / qualitative / resource`。
- `hypothesis`：待检验的解释、构造或命题，不写成已观察结果。
- `prior_art[]`：`paper_id / overlap / delta / evidence_ids`；对方已解决的内容必须有其自身的证据引用。
- `novelty`：`status / search_ids / conclusion / limitations`。
- `design`：`prediction / rival_explanation / test / baseline / metric / success / falsifier / negative_result_value / first_step / budget / failure_modes`。字段按领域解释，理论的 baseline 可以是最近定理或最强已知界。
- `assessment`：可选，逐维写 `score / reason / uncertainty`；不生成无依据的总分。
- `gates`：`data_access / resource_fit`；值是 `confirmed / plausible / unknown / blocked`，指当前推荐的最小验证所需条件。推荐时同时填写 `data_access_basis / resource_fit_basis`，说明条件如何确认。
- `review`：`strongest_objection / response / residual_risk`。
- `decision_reason`：为什么是当前状态，什么新信息会改变决定。
- `history[]`：修改版本、触发论文、改变理由与原版可定位副本；实质修订保留旧候选，不能只覆写原字段。

`recommended` 需要：具体差异、有 `verified=true` 的支持证据、至少一个正文深度的最近工作证据、当前版本的成功多路径查重、完整的最小验证、两个 `confirmed` 资源条件和反方审查。高风险完整研究的审批状态另列，不假设 pilot 的推荐等于研究授权。

`hold / rejected / archived` 可以不填完整 design，但要有原因。已知重合的候选不应仍标 `differentiated_within_scope`。`shortlisted` 表示准备展开，并不自动要求所有推荐条件已满足。

## 验证命令及能力边界

```powershell
python "<skill-root>/scripts/idea_bridge.py" verify --workspace "<project>/Idea/IDEA-0001_选题主题"
```

返回 JSON：`ok / errors / warnings / counts`。无错误退出 0；结构、引用关系、当前版本查重或指纹错误退出 1；无法读取输入/命令参数错误退出 2。未知证据/论文/检索 ID、重复 ID、明显的字段类型错误均应修复。缺少证据/查重文件时，空文件适用于纯候选或明确暂缓；有推荐方向就会触发相应条件错误。

结构化输出、`decision.md` 和 `cards/*.md` 中的 `[[paper_id]]` 也检查是否存在。本地证据哈希、已知论文的文件归属和旧 context 快照也被检查。脚本不联网，不验证 DOI 是否真实，不判断证据是否真的蕴含主张，也不能识别填了一大段却没有科学内容的字段。通过检查只能说明基本结构与记录一致。最后由宿主检查：推荐是否有正文依据、搜索是否覆盖决定性最近工作、阴性结果是否可解释、试验条件是否真的满足。

不要把方法来源 [sources.md](sources.md) 中的 ideation 论文自动塞进用户具体领域的 evidence ledger；方法学参考与选题的学科证据是两套来源。
