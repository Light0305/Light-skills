# 期刊与导出契约

`general`、`nature`、`science`、`ieee` 是样式起点，不证明满足某期刊当前要求。需要合规结论时，核验官方来源、文章类型及投稿阶段并记录日期。

确定最终宽高、字号、格式、色彩/分辨率、source data 和初审/生产阶段。未知期刊可采用说明过的通用可编辑输出，无需仅为启动绘图强制问期刊。

- Nature、Nature Communications 和 NMI 分别核验，不能互套图数、图注、Extended Data 或尺寸要求。
- 使用最终物理尺寸，不在 Word/LaTeX 再缩放补救。固定尺寸不使用 tight 裁边。
- PDF/SVG 尽量保留文本；PNG/TIFF 同查像素、DPI 和物理尺寸，DPI 标签不代替足够像素。
- 5 pt 的 PDF 检查默认值是技术起点，不是通用阅读字号或官方要求。按任务设置 `min_font_pt`。
- 图注报告对应 panel、统计单位、n、误差、检验/校正及必要数据来源。作者未给的科学信息不编造。

本包设计参考 SciPilot 预设、nature-figure 的 Nature 资料和 nature-shared 的 NMI 资料；文件/哈希见 `sources.json`。本地快照不代替实时核验。
