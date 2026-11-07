# 文献身份、来源版本与检查范围

适用于 0.12.0。文章原生目录和既有 paper_id 保持可用；新增指纹、全库索引与只读核查，不把文件存在视作阅读或科学验收完成。

## 一条记录、一份报告、一项研究

- 多个平台返回同一报告的记录：优先依据规范化 DOI、PMID、PMCID、arXiv 或 OpenAlex 标识归并，保留来源及已有别名。发现多个不同非空 DOI 时保守保留，不能通过共同标题、arXiv 标识或一条缺 DOI 记录绕过冲突。
- 没有强标识：标题匹配需同时有可靠的相同年份、足够完整的作者匹配和有辨识度的标题。缺作者、只有英文姓氏、短标题或冲突 DOI 只形成待核对候选。不同保留记录发生旧式 fallback ID 碰撞时分配稳定后缀，避免图和筛选表把它们当同一条。
- 预印本、正式发表稿、更正和同一研究的多个报告：可能有关联，仍保留各自身份、文本和证据。标题/作者相同不能自动认定内容等价；核对出版方或 Crossref 的显式关系和实际差异。
- 跨论文证据综合还需识别研究层次：一个研究的多个报告不能直接当多个独立样本计数。当前 CLI 不自动生成 study_id 或判定重复队列，宿主在证据矩阵中记录关联和计数依据。

`merge_log.json` 记录已合并集群、`possible_duplicates`、候选省略数和 `id_collisions`；候选列表有长度上限，不是全量人工判重报告。保守保留提高核对量，是避免混淆证据的选择，不能承诺完美消歧。

引用扩展按规范化标识补充已有记录，并索引新学到的标识；每个来源返回的别名用于同时重映射引用边的两端。`records_fetched` / identified 是获取的原始记录数，`new_papers` / unique 增量是实际新保留记录数，不能在入口先丢弃记录后仍假定其引用边可直接复用。

## 全库索引和本批结果

`Literature/manifest.json.entries` 与 `README.md` 索引全部实际文章，不因一次增补或只选一篇而丢失旧条目。

| 字段/位置 | 口径 |
|---|---|
| 保存的 `manifest.json.entries` | 全库文章元数据 |
| `manifest.json.library_total` | 全库文章数 |
| `manifest.json.selected_paper_ids` | 本批所选文章 ID |
| `selected`、PDF/解析/翻译/笔记计数 | 本批选择和准备结果 |
| add/build 命令返回的 `entries` | 本批处理条目，保持调用方兼容 |

Idea 原生 ingest 优先读取 manifest 的条目，因而全库索引必须完整。旧版 manifest 若只含末批，核对现存文章元数据后运行正常 add/build 刷新；同一来源可以重复导入，已有原文和笔记保留。不要根据末批的 `selected` 推断全库大小。

## PDF 来源保护

新导入在 `meta.json.pdf_sha256` 保存实际 PDF 字节的 SHA-256。它用于发现记录后的本地变动，不认证论文真伪、合法获取或阅读质量。

同一 paper_id 再次导入时，准备前检查本次选中文献的既有文件、记录指纹和传入文件；不同则停止这次准备，避免新 PDF 配旧翻译/笔记。旧 PDF 已丢失时也不能用与记录不同的文件冒充恢复。`--force-prepare` 只重建页面/任务，不越过来源保护。

确需换版本时，宿主保留旧 PDF、元数据、页面与阅读文件的可定位归档，核实新版本身份，明确建立新的来源基线，并重新核对依赖旧版的段落、图表、笔记与记忆。不同 DOI 可正常作为不同文章导入。同 DOI 的显式版本迁移当前没有自动命令；不要删除指纹后重跑来伪装同版。

旧库没有指纹时只能判定“基线未记录”。先检查当前 PDF、原文和笔记的对应关系，再由正常准备建立基线；新增指纹不能追溯证明旧文件没有变过。PDF 的创建时间属于文件元数据，不作为发表年份；可用 `--year` 提供核对后的年份。

## 两种 verify

```text
python "<skill-root>/run_litsearch.py" verify --run "<SEARCH>" --strict
python "<skill-root>/run_litsearch.py" literature verify --out "<project>/Literature"
```

前者检查检索报告及其引用/筛选等结构。后者只读检查文章 ID/目录、全库索引覆盖、已记录 PDF 的存在与字节一致性，以及元数据声称已有的阅读文件是否缺失/空白。

后者返回 `ok`、`integrity_ok`、`errors`、`needs_review` 和逐篇文件状态：`present_unverified` 仅代表非空文件。退出码 0 表示本检查范围无问题，1 表示需要修复/复核，2 为命令或输入错误。只有 PDF、尚未阅读的正常准备库也可能返回 0；源图对应、转录/译文完整性、引用支持和科学正确性仍需宿主实际验收。

来源变动、索引缺失等问题应带具体文章和受影响范围交回专业工作区，并按需更新 Memory / Workflow；校验脚本不自动重写记录或宣布旧主张失效。

## 设计依据与本轮验证

- Cochrane [Chapter 4](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04) 与 [Chapter 5](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05)：区分检索记录、报告和研究，避免证据重复计数。此处借鉴身份原则，不宣称执行了完整系统综述。
- Crossref [预印本关系](https://www.crossref.org/documentation/schema-library/markup-guide-record-types/posted-content-includes-preprints/) 与 [关系元数据](https://www.crossref.org/documentation/schema-library/markup-guide-metadata-segments/relationships/)：用可核对的显式关系关联版本。
- 本轮离线、实际接口及跨技能验证见 [升级记录](../evaluations/2026-11-06-upgrade.md)。
