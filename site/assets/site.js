/* Light-Science 官网 · 交互与动效
   GSAP 3.12.5 + ScrollTrigger（本地 vendor/）。没有 GSAP 或开启“减少动态效果”时，所有内容直接可读。 */
(function () {
  'use strict';
  window.__ls = true;

  var REPO = 'https://github.com/Light0305/Light-Science';
  var BLOB = REPO + '/blob/master/';
  var RAW = REPO + '/raw/master/';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');
  var hasGsap = typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined';

  /* ------------------------------------------------------------------ data
     One script serves both pages: <html lang="en" data-base="../"> picks English and the asset base. */
  var EN = (document.documentElement.lang || '').toLowerCase().indexOf('en') === 0;
  var BASE = document.documentElement.getAttribute('data-base') || '';
  function L(zh, en) { return EN ? en : zh; }
  var T = {
    copied: L('已复制', 'Copied'),
    manual: L('请手动复制', 'Copy manually'),
    copyFail: L('没能自动复制。文字已选中，按 Ctrl+C（Mac 为 ⌘+C）复制', 'Couldn’t copy automatically. The text is selected — press Ctrl+C (⌘+C on Mac).'),
    copiedInstall: L('安装指令已复制，粘贴给你的 Agent 即可', 'Install prompt copied — paste it to your agent'),
    copiedPlain: L('已复制到剪贴板', 'Copied to clipboard'),
    stars: function (n) { return L('GitHub，' + n + ' 个 Star', 'GitHub, ' + n + ' stars'); },
    zoom: L('放大查看：', 'View larger: '),
    dataBy: L('数据：', 'Data: '),
    source: L('数据来源 ↗', 'Data source ↗'),
    out: L('产出位置', 'Output'),
    next: L('下一步', 'Next'),
    back: L('可能回到', 'Can go back to'),
    noOrder: L('按项目需要接入，不进入固定顺序', 'Joins when the project needs it, outside the fixed order'),
    refAlt: function (m) { return L(m.title + '的实际生成参考', 'Generated reference: ' + m.title); },
    recAlt: function (m) { return L(m.tool + ' 原生文件的实际导出：' + m.title, 'Actual export of the native ' + m.tool + ' file: ' + m.title); },
    review: L('评审', 'Review'),
    reAnalyze: L('补分析', 'Reanalyze'),
    reRun: L('补实验', 'Rerun')
  };

  var SKILLS = [
    { name: 'light-leader', desc: L('联合记忆与实际材料，协调技能、研究回退、论文修订和中断恢复', 'Combines memory with the actual materials to coordinate skills, backtracking, revisions and recovery'), out: L('Workflow/（按需）', 'Workflow/ (when needed)'), cat: 'coord', path: 'light-leader/SKILL.md' },
    { name: 'light-memory', desc: L('保存有来源的决定、失败教训与约束，恢复上下文，提示来源变化和冲突', 'Keeps sourced decisions, failure lessons and constraints; restores context and flags changed sources'), out: 'Memory/', cat: 'coord', path: 'light-memory/SKILL.md' },
    { name: 'light-literature', alias: '/ literature-search', desc: L('文献检索、筛选、原文获取、精读、翻译、引用核对与证据综合', 'Search, screening, full-text retrieval, close reading, translation, citation checks and evidence synthesis'), out: 'Literature/', cat: 'research', path: 'light-literature/SKILL.md' },
    { name: 'light-idea', desc: L('从证据提出研究问题，比较候选想法、竞争解释与最小判别实验', 'Proposes questions from evidence; compares ideas, competing explanations and minimal discriminating experiments'), out: 'Idea/', cat: 'research', path: 'light-idea/SKILL.md' },
    { name: 'light-design', desc: L('形成可执行、可判别的方案，明确对照、指标、预算与分析计划', 'Builds an executable, discriminating plan with controls, metrics, budget and analysis plan'), out: 'Design/', cat: 'research', path: 'light-design/SKILL.md' },
    { name: 'light-experiment', desc: L('执行计算实验、仿真或基准测试，保存配置、环境、日志与原始结果', 'Runs computational experiments, simulations or benchmarks; keeps configs, environments, logs and raw results'), out: 'Experiment/', cat: 'research', path: 'light-experiment/SKILL.md' },
    { name: 'light-analysis', desc: L('分析结果、误差、不确定性与替代解释，决定补实验、改设计或回到选题', 'Analyzes results, error, uncertainty and alternatives; decides to rerun, redesign or rethink the question'), out: 'Analysis/', cat: 'research', path: 'light-analysis/SKILL.md' },
    { name: 'light-journal-select', desc: L('根据实际贡献与证据选刊，核对官方要求，形成建议和写作 brief', 'Chooses journals from the actual contribution and evidence, checks requirements, writes a brief'), out: 'Journal/', cat: 'paper', path: 'light-journal-select/SKILL.md' },
    { name: 'light-write', desc: L('论文起草、重构、润色、翻译与一致性检查；默认 LaTeX＋编译检查后的 PDF', 'Drafting, restructuring, polishing, translation and consistency checks; LaTeX plus a compile-checked PDF'), out: 'Write/', cat: 'paper', path: 'light-write/SKILL.md' },
    { name: 'light-diagram', desc: L('方法图、机制图的图意、参考、提示词、生图和可编辑重建', 'Method and mechanism figures: intent, references, prompts, generation and editable rebuilds'), out: L('Figure/Methods/、Figure/Mechanisms/', 'Figure/Methods/, Figure/Mechanisms/'), cat: 'paper', path: 'light-diagram/SKILL.md' },
    { name: 'light-chart', desc: L('实际数据的 Python / R 科研图、多面板图和论文表格', 'Python / R scientific charts, multi-panel figures and paper tables from real data'), out: 'Figure/Data/', cat: 'paper', path: 'light-chart/skills/light-chart/SKILL.md' },
    { name: 'light-review', desc: L('投稿前内部评审、图文与证据检查，定位问题并追踪复核', 'Internal pre-submission review of figures, text and evidence, with tracked re-checks'), out: 'Review/', cat: 'paper', path: 'light-review/SKILL.md' },
    { name: 'light-crawl', desc: L('按需采集网站或应用数据，保留获取条件、失败记录和数据来源', 'Collects website or app data on demand, keeping access conditions, failures and provenance'), out: 'Acquisition/', cat: 'ondemand', path: 'light-crawl/SKILL.md' },
    { name: 'light-patent', desc: L('从真实技术材料准备技术交底、权利要求、说明书、摘要与附图', 'Prepares disclosures, claims, specifications, abstracts and drawings from real technical material'), out: 'Patent/', cat: 'ondemand', path: 'light-patent/SKILL.md' },
    { name: 'light-software-copyright', desc: L('根据真实软件准备功能说明、软件代码、软件说明书三份 DOCX', 'Prepares the three DOCX files of a Chinese software copyright filing from real software'), out: 'SoftwareCopyright/', cat: 'ondemand', path: 'light-software-copyright/SKILL.md' },
    { name: 'light-diagram-prompt', desc: L('科学 brief、结构蓝图、生图提示词与检查点', 'Scientific brief, structural blueprint, image prompts and checkpoints'), out: 'Figure/Methods/', cat: 'diagram', path: 'light-diagram/light-diagram-prompt/SKILL.md' },
    { name: 'light-illustrator-diagram', desc: L('Illustrator 原生 .ai 与实际导出', 'Native Illustrator .ai plus real exports'), out: 'Figure/Methods/', cat: 'diagram', path: 'light-diagram/light-illustrator-diagram/SKILL.md' },
    { name: 'light-powerpoint-diagram', desc: L('可编辑 .pptx 与实际导出', 'Editable .pptx plus real exports'), out: 'Figure/Methods/', cat: 'diagram', path: 'light-diagram/light-powerpoint-diagram/SKILL.md' },
    { name: 'light-visio-diagram', desc: L('Visio 原生 .vsdx 与实际导出', 'Native Visio .vsdx plus real exports'), out: 'Figure/Methods/', cat: 'diagram', path: 'light-diagram/light-visio-diagram/SKILL.md' }
  ];
  var CAT = EN
    ? { coord: 'Coordination', research: 'Research loop', paper: 'Paper', ondemand: 'On demand', diagram: 'Diagram entry' }
    : { coord: '协调', research: '研究循环', paper: '论文制作', ondemand: '按需接入', diagram: 'Diagram 入口' };

  var G_RES = L('研究循环', 'Research loop'), G_PAPER = L('论文制作与修订', 'Paper production and revision'), G_ON = L('按需接入', 'On demand'), G_CO = L('协调', 'Coordination');
  var NODES = {
    leader: { name: 'Leader', skill: 'light-leader', group: G_CO, path: 'light-leader/SKILL.md', out: L('Workflow/（需要多步协调时）', 'Workflow/ (when several steps need coordinating)'), desc: L('先恢复，再核对，再行动。读取项目记忆与交接，回到论文、代码、运行结果和采用稿图检查实际状态，再决定下一步交给哪个技能。', 'Restore, verify, then act. It reads project memory and handoffs, checks the actual state against papers, code, run results and adopted figures, then decides which skill takes the next step.'), next: ['memory'], nextLabel: L('读写', 'Reads and writes') },
    memory: { name: 'Memory', skill: 'light-memory', group: G_CO, path: 'light-memory/SKILL.md', out: 'Memory/memory.json · events/ · current.md', desc: L('保存有来源的决定、失败教训与约束，恢复上下文；来源变化或相互冲突时提醒重新核实。具体科学事实仍以各阶段原件为准。', 'Keeps sourced decisions, failure lessons and constraints and restores context; asks for re-verification when sources change or conflict. Scientific facts stay in each stage’s original files.'), next: ['leader'], nextLabel: L('配合', 'Works with') },
    lit: { name: L('文献', 'Literature'), skill: 'light-literature', group: G_RES, path: 'light-literature/SKILL.md', out: L('Literature/年份_作者_原题短名/', 'Literature/Year_Author_ShortTitle/'), desc: L('文献检索、筛选、原文获取、精读、翻译、引用核对与证据综合。想法缺少证据时会回到这里。', 'Search, screening, full-text retrieval, close reading, translation, citation checks and evidence synthesis. Ideas that lack evidence come back here.'), next: ['idea'] },
    idea: { name: L('想法', 'Idea'), skill: 'light-idea', group: G_RES, path: 'light-idea/SKILL.md', out: L('Idea/IDEA-0001_选题主题/', 'Idea/IDEA-0001_Topic/'), desc: L('从证据提出研究问题，比较候选想法、竞争解释与最小判别实验。', 'Proposes research questions from evidence and compares candidate ideas, competing explanations and minimal discriminating experiments.'), next: ['design'], back: ['lit'] },
    design: { name: L('设计', 'Design'), skill: 'light-design', group: G_RES, path: 'light-design/SKILL.md', out: L('Design/PROT-0001_方案/v01/', 'Design/PROT-0001_Plan/v01/'), desc: L('形成可执行、可判别的方案，明确对照、指标、预算与分析计划。', 'Builds an executable, discriminating plan with controls, metrics, budget and an analysis plan.'), next: ['experiment'] },
    experiment: { name: L('实验', 'Experiment'), skill: 'light-experiment', group: G_RES, path: 'light-experiment/SKILL.md', out: L('Experiment/EXP-0001_执行批次/runs/R001/', 'Experiment/EXP-0001_Batch/runs/R001/'), desc: L('执行计算实验、仿真或基准测试，保存配置、环境、日志与原始结果。', 'Runs computational experiments, simulations or benchmarks and keeps configs, environments, logs and raw results.'), next: ['analysis'] },
    analysis: { name: L('分析', 'Analysis'), skill: 'light-analysis', group: G_RES, path: 'light-analysis/SKILL.md', out: L('Analysis/AN-0001_分析问题/', 'Analysis/AN-0001_Question/'), desc: L('分析结果、误差、不确定性与替代解释。可能暴露执行问题、设计不足或选题本身的缺口，于是补实验、改设计或回到选题；证据足够时进入选刊。', 'Analyzes results, error, uncertainty and alternative explanations. It may expose problems in execution, design or the question itself — so you rerun, redesign or rethink — and moves on to journal selection once the evidence holds.'), next: ['journal'], back: ['experiment', 'design', 'idea'] },
    journal: { name: L('选刊', 'Journal'), skill: 'light-journal-select', group: G_PAPER, path: 'light-journal-select/SKILL.md', out: L('Journal/JRN-0001_选刊轮次/', 'Journal/JRN-0001_Round/'), desc: L('根据实际贡献与证据选刊，核对官方要求，形成建议和写作 brief。', 'Chooses journals from the actual contribution and evidence, checks official requirements, and writes a recommendation and a writing brief.'), next: ['write'] },
    write: { name: L('写作', 'Writing'), skill: 'light-write', group: G_PAPER, path: 'light-write/SKILL.md', out: L('Write/PAPER-0001_工作标题/', 'Write/PAPER-0001_WorkingTitle/'), desc: L('论文起草、重构、润色、翻译与一致性检查；完整稿件默认交付 LaTeX 与实际编译检查后的 PDF，用户模板优先。', 'Drafting, restructuring, polishing, translation and consistency checks. Full manuscripts default to LaTeX plus a compile-checked PDF; your own template comes first.'), next: ['diagram', 'chart', 'review'], nextLabel: L('配合', 'Works with') },
    diagram: { name: L('方法图', 'Method fig.'), skill: 'light-diagram', group: G_PAPER, path: 'light-diagram/SKILL.md', out: 'Figure/Methods/ · Figure/Mechanisms/', desc: L('方法图、机制图的图意、参考、提示词和生图；需要继续编辑时，用 Illustrator、PowerPoint 或 Visio 重建为原生文件。', 'Intent, references, prompts and image generation for method and mechanism figures; rebuilt as native Illustrator, PowerPoint or Visio files when they need further editing.'), next: ['write', 'review'], nextLabel: L('配合', 'Works with') },
    chart: { name: L('数据图', 'Data fig.'), skill: 'light-chart', group: G_PAPER, path: 'light-chart/skills/light-chart/SKILL.md', out: L('Figure/Data/FIG-0003_数据图/', 'Figure/Data/FIG-0003_DataFigure/'), desc: L('用实际数据绘制 Python / R 科研图、多面板图和论文表格，保留实验单位、重复测量、缺失值和不确定性。', 'Python / R scientific charts, multi-panel figures and paper tables from real data, keeping experimental units, repeated measures, missing values and uncertainty.'), next: ['write', 'review'], nextLabel: L('配合', 'Works with') },
    review: { name: L('评审', 'Review'), skill: 'light-review', group: G_PAPER, path: 'light-review/SKILL.md', out: L('Review/REV-0001_稿件版本与轮次/', 'Review/REV-0001_ManuscriptVersionRound/'), desc: L('投稿前内部评审、图文与证据检查，定位问题并追踪复核。需要补证据时返回研究，必要时调整期刊定位。', 'Internal pre-submission review of figures, text and evidence that locates problems and tracks re-checks. Sends work back to research when evidence is missing, and repositions the journal when needed.'), next: ['write'], nextLabel: L('交回', 'Returns to'), back: ['analysis', 'experiment', 'journal'] },
    crawl: { name: L('采集', 'Acquisition'), skill: 'light-crawl', group: G_ON, path: 'light-crawl/SKILL.md', out: L('Acquisition/ACQ-0001_采集目标/', 'Acquisition/ACQ-0001_Target/'), desc: L('按需采集网站或应用数据，保留获取条件、失败记录和数据来源。', 'Collects website or app data on demand, keeping access conditions, failure records and data provenance.'), next: ['lit', 'experiment'], nextLabel: L('供给', 'Feeds') },
    patent: { name: L('专利', 'Patent'), skill: 'light-patent', group: G_ON, path: 'light-patent/SKILL.md', out: L('Patent/PAT-0001_技术方案/', 'Patent/PAT-0001_Invention/'), desc: L('从真实技术材料准备技术交底、权利要求、说明书、摘要与附图。涉及公开时间安排时可以提前准备。', 'Prepares disclosures, claims, specifications, abstracts and drawings from real technical material — early, when publication timing matters.'), next: [] },
    swc: { name: L('软著', 'Software ©'), skill: 'light-software-copyright', group: G_ON, path: 'light-software-copyright/SKILL.md', out: L('SoftwareCopyright/SWC-0001_软件版本/', 'SoftwareCopyright/SWC-0001_SoftwareVersion/'), desc: L('根据真实软件准备功能说明、软件代码、软件说明书三份 DOCX。', 'Prepares the three DOCX files of a Chinese software copyright filing — feature description, source code and user manual — from real software.'), next: [] }
  };
  var CYCLE = ['lit', 'idea', 'design', 'experiment', 'analysis'];

  var CHARTS = [
    { id: '03', title: L('实测脑电信号', 'Measured EEG'), cat: L('信号 · 原始时序与频段功率', 'Signals · raw time series and band power'), sum: L('PhysioNet EEG S001/R04：真实采样与固定时窗；时窗不是独立受试者。', 'PhysioNet EEG S001/R04: real sampling and fixed windows; windows are not independent participants.'), src: 'PhysioNet EEGMMIDB', url: 'https://physionet.org/content/eegmmidb/1.0.0/', terms: 'Open Data Commons Attribution License v1.0', w: 960, h: 987 },
    { id: '04', title: L('生态排序与热图', 'Ordination and heatmap'), cat: L('生态 · 群落组成与环境梯度', 'Ecology · community composition and gradient'), sum: L('vegan varespec/varechem：24 个样地、44 个物种；描述群落结构。', 'vegan varespec/varechem: 24 sites, 44 species; describes community structure.'), src: 'vegan · varespec / varechem', url: 'https://cran.r-project.org/package=vegan', terms: 'Väre, Ohtonen & Oksanen (1995)', w: 960, h: 549 },
    { id: '05', title: L('三维场与切片', '3D field and slices'), cat: L('成像 · 体数据、空间标定与对应视图', 'Imaging · volume data, calibration and matching views'), sum: L('Allen Institute / scikit-image cells3d 实测体数据；等值面不是已验证的细胞分割。', 'Allen Institute / scikit-image cells3d measured volume; the isosurface is not a validated cell segmentation.'), src: 'scikit-image · cells3d', url: 'https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.cells3d', terms: 'Allen Institute for Cell Science / scikit-image', w: 960, h: 982 },
    { id: '06', title: L('温度场与时间序列', 'Temperature field and series'), cat: L('气候 · 真实坐标、年度对比与数据支持', 'Climate · real coordinates, yearly comparison, data support'), sum: L('2013/2014 温度场的描述性对比；年度差异不是长期气候趋势。', 'Descriptive comparison of 2013/2014 fields; the yearly difference is not a long-term climate trend.'), src: 'NCEP/NCAR · xarray-data', url: 'https://docs.xarray.dev/en/stable/examples/area_weighted_temperature.html', terms: L('海岸线：Natural Earth（公有领域）', 'Coastlines: Natural Earth (public domain)'), w: 960, h: 757 },
    { id: '08', title: L('植物响应与重复测量', 'Plant response, repeated measures'), cat: L('实验 · 保留个体轨迹与配对关系', 'Experiment · individual trajectories and pairing kept'), sum: L('R datasets::CO2：12 株植物、84 次观测；保留每株轨迹。', 'R datasets::CO2: 12 plants, 84 observations; every plant’s trajectory kept.'), src: 'R datasets::CO2', url: 'https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/zCO2.html', terms: 'Potvin, Lechowicz & Tardif (1990)', w: 960, h: 576 },
    { id: '09', title: L('生长轨迹与随访', 'Growth and follow-up'), cat: L('纵向 · 纵向变化与实际观测数量', 'Longitudinal · change and actual observation counts'), sum: L('R datasets::ChickWeight：真实观测轨迹，明确缺失随访。', 'R datasets::ChickWeight: observed trajectories with missing follow-up made explicit.'), src: 'R datasets::ChickWeight', url: 'https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/ChickWeight.html', terms: L('R datasets 文档', 'R datasets documentation'), w: 960, h: 976 },
    { id: '10', title: L('雨云图与原始点', 'Raincloud with raw points'), cat: L('分布 · 分布形态、四分位与个体观测', 'Distribution · shape, quartiles and individual points'), sum: L('Iris 实测数据；密度、四分位与所有原始点。', 'Measured Iris data: density, quartiles and every raw point.'), src: 'UCI · Iris', url: 'https://archive.ics.uci.edu/dataset/53/iris', terms: 'UCI Machine Learning Repository', w: 960, h: 676 },
    { id: '11', title: L('方法对比与热图', 'Method comparison and heatmap'), cat: L('计算 · 报告值、层级与注释的组织', 'Computation · reported values, hierarchy, annotation'), sum: L('figures4papers 提供的 RNAGenScape 汇总值的重设计；不是本项目的独立实验。', 'Redesign of RNAGenScape summary values from figures4papers; not an independent experiment of this project.'), src: 'figures4papers · CC BY-NC 4.0', url: 'https://github.com/ChenLiu-1996/figures4papers', terms: L('CC BY-NC 4.0，Chen Liu and contributors', 'CC BY-NC 4.0, Chen Liu and contributors'), w: 960, h: 560 },
    { id: '12', title: L('生存曲线与风险人数', 'Survival and number at risk'), cat: L('临床 · 随访支持与不确定性', 'Clinical · follow-up support and uncertainty'), sum: L('R survival::colon：未调整生存曲线、置信带与随访支持。', 'R survival::colon: unadjusted survival curves, confidence bands and follow-up support.'), src: 'R survival::colon', url: 'https://stat.ethz.ch/R-manual/R-devel/library/survival/html/colon.html', terms: L('survival::colon 数据与试验文档', 'survival::colon data and trial documentation'), w: 960, h: 720 }
  ];

  var METHODS = {
    illustrator: { tool: 'Illustrator', title: L('锂硫电池机制', 'Lithium–sulfur battery mechanism'), note: L('锂硫电池机制概念图。原生路径、文字和分组，已修正生成参考中的因果分支与放大来源。', 'Concept figure of a lithium–sulfur battery. Native paths, text and groups; the causal branches and zoom sources from the generated reference were corrected.'), fit: L('自由轮廓、精细矢量、复杂分组与视觉细节', 'Free-form outlines, fine vectors, complex grouping and visual detail'), out: L('.ai，按需 SVG / PDF / PNG', '.ai, plus SVG / PDF / PNG as needed'), file: 'docs/showcase/native/illustrator.ai', fileLabel: L('下载 .ai 原生文件 · 666 KB', 'Download the native .ai · 666 KB'), ratio: '3 / 2', w: 1536, h: 1024 },
    powerpoint: { tool: 'PowerPoint', title: L('CRISPR–Cas9 切割机制', 'CRISPR–Cas9 cleavage mechanism'), note: L('CRISPR–Cas9 概念图，136 个原生对象，保留可编辑轮廓、文字与连接。纹理与曲线细节存在近似。', 'CRISPR–Cas9 concept figure with 136 native objects, keeping editable outlines, text and connectors. Textures and curve details are approximated.'), fit: L('组会与论文协作、模块布局、方便作者继续改图', 'Group meetings and co-authoring, modular layouts, easy to keep editing'), out: L('.pptx，按需 PDF / PNG', '.pptx, plus PDF / PNG as needed'), file: 'docs/showcase/native/powerpoint-crispr.pptx', fileLabel: L('下载 .pptx 原生文件 · 59 KB', 'Download the native .pptx · 59 KB'), ratio: '3 / 2', w: 1536, h: 1024 },
    visio: { tool: 'Visio', title: L('MonoFormer 深度估计架构', 'MonoFormer depth-estimation architecture'), note: L('MonoFormer 四级网络架构。这里展示按图复现页，原生文件第 2 页保留科学关系修正版。', 'Four-stage MonoFormer architecture. Shown here is the page that reproduces the reference; page 2 of the native file keeps a scientifically corrected version.'), fit: L('系统框架、流程、连接关系及节点调整', 'System frameworks, flows, connections and node adjustments'), out: L('.vsdx，按需 SVG / PDF / PNG', '.vsdx, plus SVG / PDF / PNG as needed'), file: 'docs/showcase/native/visio-monoformer.vsdx', fileLabel: L('下载 .vsdx 原生文件 · 152 KB', 'Download the native .vsdx · 152 KB'), ratio: '2 / 1', w: 1600, h: 800 }
  };

  /* --------------------------------------------------------------- helpers */
  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (html != null) n.innerHTML = html;
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  var toastEl = $('[data-toast]');
  var toastTimer;
  function toast(msg, ms) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('is-on'); }, ms || 2400);
  }

  /* ------------------------------------------------------------------ copy */
  function textOf(target) {
    var clone = target.cloneNode(true);
    $$('.ps', clone).forEach(function (p) { p.remove(); });
    return clone.textContent.split('\n').map(function (l) { return l.replace(/^\s+/, ''); }).join('\n').trim();
  }
  function fallbackCopy(text) {
    var ta = el('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }
  $$('[data-copy]').forEach(function (btn) {
    var label = $('[data-copy-text]', btn);
    var original = label ? label.textContent : '';
    btn.addEventListener('click', function () {
      var target = $(btn.getAttribute('data-copy'));
      if (!target) return;
      var text = textOf(target);
      var done = function (ok) {
        if (ok) {
          btn.classList.add('is-done');
          if (label) label.textContent = T.copied;
          var msg = btn.getAttribute('data-copy-toast') || (btn.getAttribute('data-copy-label') ? T.copiedInstall : T.copiedPlain);
          toast(msg, msg.length > 16 ? 3600 : 2400);
          setTimeout(function () { btn.classList.remove('is-done'); if (label) label.textContent = original; }, 2000);
        } else {
          // last resort: leave the text selected so the visitor can press Ctrl/⌘+C
          try {
            var range = document.createRange();
            range.selectNodeContents(target);
            var sel = window.getSelection();
            sel.removeAllRanges(); sel.addRange(range);
          } catch (e) { /* ignore */ }
          toast(T.copyFail, 5000);
          btn.classList.add('is-fail');
          if (label) label.textContent = T.manual;
          setTimeout(function () { btn.classList.remove('is-fail'); if (label) label.textContent = original; }, 5000);
        }
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallbackCopy(text)); });
      } else {
        done(fallbackCopy(text));
      }
    });
  });

  /* ------------------------------------------------------------------- nav */
  var nav = $('.nav');
  var toggle = $('.nav__toggle');
  var links = $('#nav-links');
  function onScroll() { nav.classList.toggle('is-scrolled', window.scrollY > 8); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  function closeMenu() { links.classList.remove('is-open'); toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label', L('打开导航', 'Open menu')); }
  toggle.addEventListener('click', function () {
    var open = !links.classList.contains('is-open');
    links.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? L('关闭导航', 'Close menu') : L('打开导航', 'Open menu'));
  });
  $$('a', links).forEach(function (a) { a.addEventListener('click', closeMenu); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });

  if ('IntersectionObserver' in window) {
    var navMap = {};
    $$('a', links).forEach(function (a) { navMap[a.getAttribute('href').slice(1)] = a; });
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && navMap[en.target.id]) {
          $$('a', links).forEach(function (a) { a.classList.remove('is-active'); });
          navMap[en.target.id].classList.add('is-active');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(navMap).forEach(function (id) { var s = document.getElementById(id); if (s) spy.observe(s); });
  }

  /* ----------------------------------------------------------- GitHub stars */
  (function () {
    var badge = $('[data-stars]');
    if (!badge || !window.fetch) return;
    fetch('https://api.github.com/repos/Light0305/Light-Science', { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || typeof d.stargazers_count !== 'number') return;
        var n = d.stargazers_count;
        badge.textContent = '★ ' + (n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : n);
        badge.hidden = false;
        badge.parentNode.setAttribute('aria-label', T.stars(n));
      })
      .catch(function () { /* 离线或限流时只显示 GitHub */ });
  })();

  /* ---------------------------------------------------------------- ledger */
  var ledger = $('[data-ledger]');
  SKILLS.forEach(function (s, i) {
    var row = el('div', { class: 'lrow', role: 'row', 'data-cat': s.cat });
    row.innerHTML =
      '<span class="lrow__n" role="cell">' + String(i + 1).padStart(2, '0') + '</span>' +
      '<span role="cell"><a class="lrow__name" href="' + BLOB + s.path + '" target="_blank" rel="noopener"><span>' + esc(s.name) + '</span>' + (s.alias ? '<small>' + esc(s.alias) + '</small>' : '') + '</a></span>' +
      '<span class="lrow__desc" role="cell">' + esc(s.desc) + '</span>' +
      '<span class="lrow__out" role="cell">' + esc(s.out) + '</span>' +
      '<span class="cat cat--' + s.cat + '" role="cell">' + CAT[s.cat] + '</span>';
    ledger.appendChild(row);
  });
  $$('.filter').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var f = btn.getAttribute('data-filter');
      $$('.filter').forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); });
      $$('.lrow', ledger).forEach(function (r) {
        var show = f === 'all' || r.getAttribute('data-cat') === f;
        r.hidden = !show;
        if (show && hasGsap && !reduceMQ.matches) gsap.fromTo(r, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: .35, ease: 'power2.out', overwrite: true });
      });
      if (hasGsap) ScrollTrigger.refresh();
    });
  });

  /* --------------------------------------------------------------- gallery */
  var gallery = $('[data-gallery]');
  var figs = [];
  CHARTS.forEach(function (c, i) {
    var fig = el('figure', { class: 'fig' });
    fig.innerHTML =
      '<button class="fig__img" type="button" data-chart="' + i + '" aria-label="' + T.zoom + esc(c.title) + '">' +
      '<img src="' + BASE + 'assets/img/charts/' + c.id + '.webp" alt="' + esc(c.title + L('，', ', ') + c.cat) + '" width="' + c.w + '" height="' + c.h + '" loading="lazy"></button>' +
      '<figcaption class="fig__cap"><div class="fig__top"><span class="fig__n">' + String(i + 1).padStart(2, '0') + '</span><h3 class="fig__title">' + esc(c.title) + '</h3></div>' +
      '<p class="fig__cat">' + esc(c.cat) + '</p><p class="fig__sum">' + esc(c.sum) + '</p>' +
      '<a class="fig__src" href="' + c.url + '" target="_blank" rel="noopener">' + T.dataBy + esc(c.src) + ' ↗</a></figcaption>';
    figs.push(fig);
  });
  // masonry in reading order: each card goes to the currently shortest column
  var colCount = 0;
  function layoutGallery() {
    var w = gallery.clientWidth || window.innerWidth;
    var n = w >= 900 ? 3 : w >= 560 ? 2 : 1;
    if (n === colCount) return;
    colCount = n;
    var cols = [], heights = [];
    for (var k = 0; k < n; k++) { cols.push(el('div', { class: 'gallery__col' })); heights.push(0); }
    figs.forEach(function (fig, i) {
      var c = CHARTS[i], j = heights.indexOf(Math.min.apply(null, heights));
      cols[j].appendChild(fig);
      heights[j] += c.h / c.w + .42;
    });
    while (gallery.firstChild) gallery.removeChild(gallery.firstChild);
    cols.forEach(function (col) { gallery.appendChild(col); });
    if (hasGsap) ScrollTrigger.refresh();
  }
  layoutGallery();
  window.addEventListener('resize', layoutGallery);

  /* -------------------------------------------------------------- lightbox */
  var lb = $('[data-lightbox]');
  var lbImg = $('[data-lb-img]');
  var lbCap = $('[data-lb-cap]');
  var lbCount = $('[data-lb-count]');
  var lbPrev = $('[data-lb-prev]');
  var lbNext = $('[data-lb-next]');
  var lbList = [];
  var lbIndex = 0;
  function lbRender() {
    var it = lbList[lbIndex];
    lbImg.src = it.src; lbImg.alt = it.alt;
    lbCap.innerHTML = it.cap;
    var multi = lbList.length > 1;
    lbPrev.hidden = lbNext.hidden = !multi;
    lbCount.textContent = multi ? (lbIndex + 1) + ' / ' + lbList.length : '';
  }
  function lbOpen(list, index) {
    lbList = list; lbIndex = index || 0; lbRender();
    if (typeof lb.showModal === 'function') lb.showModal(); else lb.setAttribute('open', '');
  }
  function lbStep(d) { lbIndex = (lbIndex + d + lbList.length) % lbList.length; lbRender(); }
  lbPrev.addEventListener('click', function () { lbStep(-1); });
  lbNext.addEventListener('click', function () { lbStep(1); });
  lb.addEventListener('keydown', function (e) {
    if (lbList.length < 2) return;
    if (e.key === 'ArrowLeft') lbStep(-1);
    if (e.key === 'ArrowRight') lbStep(1);
  });
  lb.addEventListener('click', function (e) { if (e.target === lb) lb.close(); });
  var chartItems = CHARTS.map(function (c, i) {
    return {
      src: BASE + 'assets/img/charts/' + c.id + '-full.webp',
      alt: c.title + L('，', ', ') + c.cat,
      cap: '<strong>' + String(i + 1).padStart(2, '0') + ' · ' + esc(c.title) + '</strong>' + esc(c.sum) +
        ' <a href="' + c.url + '" target="_blank" rel="noopener">' + T.source + '</a><small>' + esc(c.terms) + '</small>'
    };
  });
  gallery.addEventListener('click', function (e) {
    var b = e.target.closest('[data-chart]');
    if (b) lbOpen(chartItems, +b.getAttribute('data-chart'));
  });
  $$('[data-lightbox-src]').forEach(function (b) {
    b.addEventListener('click', function () {
      lbOpen([{ src: b.getAttribute('data-lightbox-src'), alt: b.getAttribute('data-lightbox-alt'), cap: esc(b.getAttribute('data-lightbox-caption')) }], 0);
    });
  });

  /* -------------------------------------------------------------- loop map */
  var C = { x: 260, y: 226, R: 140, r: EN ? 42 : 38 };
  var nodesG = $('[data-cycle-nodes]');
  var arcsG = $('[data-cycle-arcs]');
  var backG = $('[data-cycle-back]');
  $('.cycle__track').setAttribute('cy', C.y);
  // hub pills follow the centre
  $$('.node--hub').forEach(function (g, i) {
    var rect = $('rect', g), text = $('text', g);
    var y = C.y - 40 + i * 46;
    rect.setAttribute('y', y); text.setAttribute('y', y + 22);
  });
  var ANG = {};
  CYCLE.forEach(function (id, i) { ANG[id] = (-90 + i * 72) * Math.PI / 180; });
  function pt(a, rad) { return [C.x + rad * Math.cos(a), C.y + rad * Math.sin(a)]; }
  function f(n) { return n.toFixed(1); }

  CYCLE.forEach(function (id, i) {
    var p = pt(ANG[id], C.R);
    var g = svgEl('g', { class: 'node', 'data-node': id, tabindex: '0', role: 'button', 'aria-label': NODES[id].name + L('，', ', ') + NODES[id].skill });
    g.appendChild(svgEl('circle', { cx: f(p[0]), cy: f(p[1]), r: C.r }));
    var n = svgEl('text', { x: f(p[0]), y: f(p[1] - 11), class: 'node__sub' }); n.textContent = '0' + (i + 1);
    var t = svgEl('text', { x: f(p[0]), y: f(p[1] + 7) }); t.textContent = NODES[id].name;
    g.appendChild(n); g.appendChild(t);
    nodesG.appendChild(g);
    if (i < CYCLE.length - 1) {
      var d = Math.asin(C.r / C.R) + .07;
      var a1 = ANG[id] + d, a2 = ANG[CYCLE[i + 1]] - d - .02;
      var s = pt(a1, C.R), e = pt(a2, C.R);
      arcsG.appendChild(svgEl('path', { d: 'M' + f(s[0]) + ' ' + f(s[1]) + ' A' + C.R + ' ' + C.R + ' 0 0 1 ' + f(e[0]) + ' ' + f(e[1]), 'marker-end': 'url(#arr)' }));
    }
  });
  // backward routes: each leaves its node and swings out counter-clockwise by its own amount,
  // so routes from the same stage fan apart instead of running as parallel rings
  var BACK = [
    ['idea', 'lit', 24, L('补文献', 'Read more')],
    ['analysis', 'experiment', 24, L('补实验', 'Rerun')],
    ['analysis', 'design', 50, L('修设计', 'Redesign')],
    ['analysis', 'idea', 76, L('改想法', 'Rethink')]
  ];
  function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }
  function polyD(pts) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + f(p[0]) + ' ' + f(p[1]); }).join(' '); }
  BACK.forEach(function (b) {
    var aS = ANG[b[0]], aT = ANG[b[1]], bulge = b[2];
    while (aT > aS) aT -= Math.PI * 2;
    var S = pt(aS, C.R), T = pt(aT, C.R), pts = [], N = 72;
    for (var k = 0; k <= N; k++) {
      var t = k / N;
      pts.push(pt(aS + (aT - aS) * t, C.R + bulge * Math.sin(Math.PI * t)));
    }
    pts = pts.filter(function (p) { return dist(p, S) >= C.r + 4 && dist(p, T) >= C.r + 8; });
    backG.appendChild(svgEl('path', { 'data-from': b[0], 'data-to': b[1], d: polyD(pts), 'marker-end': 'url(#arr-back)' }));
    // label near the arrival end, where routes from the same stage are already apart
    var lt = bulge < 30 ? .65 : .78; // short routes: label clear of the target node and of the wider routes
    var lp = pt(aS + (aT - aS) * lt, C.R + bulge * Math.sin(Math.PI * lt) + 13);
    var label = svgEl('text', { x: f(lp[0]), y: f(lp[1]), 'data-from': b[0] });
    label.textContent = b[3];
    backG.appendChild(label);
  });
  // 评审 sits outside the ring: a port at the lower left with its own routes back into the research loop
  var port = svgEl('g', { class: 'cycle__port' });
  port.appendChild(svgEl('rect', { x: 18, y: 430, width: 68, height: 30, rx: 15 }));
  var portT = svgEl('text', { x: 52, y: 446 }); portT.textContent = T.review;
  port.appendChild(portT);
  backG.appendChild(port);
  [['analysis', [40, 428], [26, 330], [64, 236], T.reAnalyze], ['experiment', [86, 438], [128, 440], [160, 404], T.reRun]].forEach(function (r) {
    var T = pt(ANG[r[0]], C.R), c2 = r[3];
    var dx = c2[0] - T[0], dy = c2[1] - T[1], L = Math.hypot(dx, dy);
    var end = [T[0] + dx / L * (C.r + 8), T[1] + dy / L * (C.r + 8)];
    var p = svgEl('path', { 'data-from': 'review', 'data-to': r[0], d: 'M' + f(r[1][0]) + ' ' + f(r[1][1]) + ' C' + f(r[2][0]) + ' ' + f(r[2][1]) + ' ' + f(c2[0]) + ' ' + f(c2[1]) + ' ' + f(end[0]) + ' ' + f(end[1]), 'marker-end': 'url(#arr-back)' });
    backG.appendChild(p);
    var mid = p.getPointAtLength ? p.getPointAtLength(p.getTotalLength() * .5) : { x: c2[0], y: c2[1] };
    var lt = svgEl('text', { x: f(mid.x + (r[0] === 'analysis' ? -4 : 10)), y: f(mid.y + (r[0] === 'analysis' ? 0 : 16)), 'data-from': 'review' });
    lt.textContent = r[4];
    backG.appendChild(lt);
  });
  function showRoutes(id) {
    var paths = $$('path', backG), labels = $$('text', backG).filter(function (t) { return t.hasAttribute('data-from'); });
    var animate = hasGsap && !reduceMQ.matches;
    paths.forEach(function (p) {
      var on = p.getAttribute('data-from') === id;
      if (animate) gsap.killTweensOf(p);
      p.classList.toggle('is-on', on);
      p.style.strokeDasharray = ''; p.style.strokeDashoffset = '';
      p.setAttribute('marker-end', 'url(#arr-back)');
    });
    labels.forEach(function (t) { t.classList.toggle('is-on', t.getAttribute('data-from') === id); });
    port.classList.toggle('is-on', id === 'review');
    if (!animate) return;
    var on = paths.filter(function (p) { return p.classList.contains('is-on'); });
    on.forEach(function (p, i) {
      var L = p.getTotalLength();
      p.removeAttribute('marker-end');
      p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
      gsap.to(p, { strokeDashoffset: 0, duration: .55 + L / 1400, delay: i * .12, ease: 'power2.inOut', onComplete: function () { p.style.strokeDasharray = ''; p.setAttribute('marker-end', 'url(#arr-back)'); } });
    });
    gsap.fromTo(labels.filter(function (t) { return t.classList.contains('is-on'); }), { opacity: 0 }, { opacity: 1, duration: .3, delay: .5, stagger: .12, clearProps: 'opacity' });
  }

  var detail = $('.detail');
  var D = function (k) { return $('[data-d="' + k + '"]', detail); };
  function chipList(ids, cls) {
    return ids.map(function (id) { return '<button type="button" class="' + cls + '" data-goto="' + id + '">' + NODES[id].name + '</button>'; }).join('');
  }
  function select(id, focusNode) {
    var n = NODES[id];
    if (!n) return;
    $$('[data-node]').forEach(function (x) {
      x.classList.toggle('is-active', x.getAttribute('data-node') === id);
      x.classList.toggle('is-target', !!(n.back && n.back.indexOf(x.getAttribute('data-node')) > -1));
      if (x.tagName === 'BUTTON') x.setAttribute('aria-pressed', String(x.getAttribute('data-node') === id));
    });
    showRoutes(id);
    D('group').textContent = n.group;
    D('name').textContent = n.name;
    D('skill').textContent = n.skill;
    D('desc').textContent = n.desc;
    D('link').href = BLOB + n.path;
    var dl = $('.detail__dl', detail);
    var html = '<div><dt>' + T.out + '</dt><dd><code>' + esc(n.out) + '</code></dd></div>';
    html += '<div><dt>' + (n.nextLabel || T.next) + '</dt><dd class="detail__chips">' + (n.next.length ? chipList(n.next, 'is-next') : '<span>' + T.noOrder + '</span>') + '</dd></div>';
    if (n.back) html += '<div><dt>' + T.back + '</dt><dd class="detail__chips">' + chipList(n.back, '') + '</dd></div>';
    dl.innerHTML = html;
    if (focusNode) {
      var target = $('[data-node="' + id + '"]');
      if (target) target.focus({ preventScroll: true });
    }
  }
  $$('[data-node]').forEach(function (x) {
    x.addEventListener('click', function () { select(x.getAttribute('data-node')); });
    x.addEventListener('keydown', function (e) {
      if ((e.key === 'Enter' || e.key === ' ') && x.tagName !== 'BUTTON') { e.preventDefault(); select(x.getAttribute('data-node')); }
    });
  });
  detail.addEventListener('click', function (e) {
    var b = e.target.closest('[data-goto]');
    if (b) select(b.getAttribute('data-goto'), true);
  });
  select('analysis');

  /* ------------------------------------------------------------------ tabs */
  function setupTabs(list, onSelect) {
    var tabs = $$('[role="tab"]', list);
    function activate(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
      });
      if (focus) tab.focus();
      onSelect(tab);
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { activate(t); });
      t.addEventListener('keydown', function (e) {
        var k = e.key, j = null;
        if (k === 'ArrowRight') j = (i + 1) % tabs.length;
        if (k === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
        if (k === 'Home') j = 0;
        if (k === 'End') j = tabs.length - 1;
        if (j !== null) { e.preventDefault(); activate(tabs[j], true); }
      });
    });
  }

  // install terminal
  setupTabs($('.terminal__tabs'), function (tab) {
    $$('.terminal__panel').forEach(function (p) { p.hidden = p.id !== tab.getAttribute('aria-controls'); });
  });

  // methods compare
  var cmp = $('[data-compare]');
  var range = $('.compare__range', cmp);
  var panel = $('#compare-panel');
  function setPos(v) { cmp.style.setProperty('--pos', v + '%'); }
  range.addEventListener('input', function () { setPos(range.value); });
  function showMethod(key) {
    var m = METHODS[key];
    var M = function (k) { return $('[data-m="' + k + '"]', panel); };
    var ref = $('[data-m="ref"]', cmp), rec = $('[data-m="rec"]', cmp);
    cmp.style.aspectRatio = m.ratio;
    ref.src = BASE + 'assets/img/methods/' + key + '-ref.webp'; ref.alt = T.refAlt(m);
    rec.src = BASE + 'assets/img/methods/' + key + '-rec.webp'; rec.alt = T.recAlt(m);
    [ref, rec].forEach(function (im) { im.width = m.w; im.height = m.h; });
    M('title').textContent = m.title;
    M('note').textContent = m.note;
    M('fit').textContent = m.fit;
    M('out').textContent = m.out;
    M('file').href = RAW + m.file;
    M('file').textContent = m.fileLabel + ' ↓';
    range.value = 50; setPos(50);
    if (hasGsap && !reduceMQ.matches) gsap.fromTo([cmp, panel], { opacity: .35 }, { opacity: 1, duration: .45, ease: 'power2.out' });
  }
  setupTabs($('.tabs'), function (tab) {
    panel.setAttribute('aria-labelledby', tab.id);
    showMethod(tab.getAttribute('data-method'));
  });
  showMethod('illustrator');

  /* ------------------------------------------------------------------ band
     The Logo's folded band, drawn through the three directories the Leader touches:
     Memory (restore) → Analysis (verify) → Design/v02 (act), then on to the “行动” entry. */
  var bandSvg = $('[data-band]');
  var heroBody = $('.hero__body');
  var band = null;
  function textRight(row, left) {
    var range = document.createRange();
    range.selectNodeContents(row);
    var rects = range.getClientRects(), right = 0;
    for (var i = 0; i < rects.length; i++) if (rects[i].width > 0) right = Math.max(right, rects[i].right);
    return right - left;
  }
  function P(p) { return p[0].toFixed(1) + ' ' + p[1].toFixed(1); }
  function buildBand() {
    if (!bandSvg || !heroBody) return null;
    while (bandSvg.firstChild) bandSvg.removeChild(bandSvg.firstChild);
    var box = heroBody.getBoundingClientRect();
    if (!box.width) return null;
    var W = box.width, H = box.height;
    bandSvg.setAttribute('viewBox', '0 0 ' + W.toFixed(0) + ' ' + H.toFixed(0));
    var tree = $('.tree', heroBody), log = $('.log', heroBody);
    var allRows = $$('.tree__row', tree);
    var rows = [1, 2, 3].map(function (k) { return $('[data-band-row="' + k + '"]', tree); });
    rows.forEach(function (r) { r.classList.add('is-linked'); });
    var mid = function (el) { var r = el.getBoundingClientRect(); return (r.top + r.bottom) / 2 - box.top; };
    var lb = log.getBoundingClientRect(), tb = tree.getBoundingClientRect();
    var stacked = lb.top >= tb.bottom - 4;
    var i1 = allRows.indexOf(rows[0]), i2 = allRows.indexOf(rows[1]);
    var ends = rows.map(function (r) { return textRight(r, box.left); });
    var maxR = 0;
    for (var i = i1; i <= i2; i++) maxR = Math.max(maxR, textRight(allRows[i], box.left));
    var sw = stacked ? 10 : 14;
    var limit = (stacked ? W : lb.left - box.left) - 24;
    var lane = maxR + 30;
    var d = Math.max(8, Math.min(30, (limit - lane) / 2.4));
    if (lane + 2 * d > limit) lane = limit - 2 * d;
    var A = [lane, mid(rows[0])], B = [lane + d, mid(rows[1])], Cc = [lane + 2 * d, mid(rows[2])];
    var h = B[1] - A[1];
    var E, dir;
    if (!stacked) {
      var tag = $('[data-band-log="3"]', log).getBoundingClientRect();
      // stop short of the tag so the amber dot sits between the band end and “行动”
      E = [tag.left - box.left - 14 - sw * 2.2, (tag.top + tag.bottom) / 2 - box.top]; dir = [1, 0];
    } else {
      E = [Math.min(W - 26, Cc[0] + 30), Cc[1] - 34]; dir = [.6, -.8];
    }
    var seg1 = 'M' + P(A) + ' C' + P([A[0] + 8, A[1] + h * .55]) + ' ' + P([B[0] - 26, B[1] - 2]) + ' ' + P(B);
    var seg2 = 'M' + P(B) + ' C' + P([B[0] + 34, B[1] + 8]) + ' ' + P([Cc[0] + 12, Cc[1] + h * .42]) + ' ' + P(Cc);
    var seg3 = 'M' + P(Cc) + ' C' + P([Cc[0] - 4, Cc[1] - Math.max(22, h * .22)]) + ' ' + P([E[0] - dir[0] * 70, E[1] - dir[1] * 40]) + ' ' + P(E);

    var defs = svgEl('defs');
    var lg = svgEl('linearGradient', { id: 'bandFront', gradientUnits: 'userSpaceOnUse', x1: A[0].toFixed(1), y1: A[1].toFixed(1), x2: E[0].toFixed(1), y2: E[1].toFixed(1) });
    lg.appendChild(svgEl('stop', { offset: '0', 'stop-color': '#45d3bd' }));
    lg.appendChild(svgEl('stop', { offset: '1', 'stop-color': '#0c9d8b' }));
    defs.appendChild(lg);
    bandSvg.appendChild(defs);
    var mk = function (dd, cls, color, width) {
      var p = svgEl('path', { d: dd, class: cls, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round' });
      bandSvg.appendChild(p); return p;
    };
    var b = { stacked: stacked };
    b.glow = [mk(seg1, 'band__glow', '#36c7b1', sw * 1.8), mk(seg3, 'band__glow', '#36c7b1', sw * 1.8)];
    b.back = mk(seg2, 'band__back', '#0c5a54', sw);
    b.f1 = mk(seg1, 'band__front', 'url(#bandFront)', sw);
    b.f3 = mk(seg3, 'band__front', 'url(#bandFront)', sw);
    b.ticks = [];
    [A, B, Cc].forEach(function (pnt, k) {
      var x1 = ends[k] + 10, x2 = pnt[0] - sw / 2 - 6;
      if (x2 - x1 > 6) {
        var t = svgEl('line', { x1: x1.toFixed(1), y1: pnt[1].toFixed(1), x2: x2.toFixed(1), y2: pnt[1].toFixed(1), class: 'band__tick' });
        bandSvg.appendChild(t); b.ticks.push(t);
      }
    });
    b.nodes = [A, B, Cc].map(function (pnt) {
      var c = svgEl('circle', { cx: pnt[0].toFixed(1), cy: pnt[1].toFixed(1), r: (sw * .36).toFixed(1), class: 'band__node' });
      bandSvg.appendChild(c); return c;
    });
    var gap = sw * .5 + sw * .6 + 4;
    b.dot = svgEl('circle', { cx: (E[0] + dir[0] * gap).toFixed(1), cy: (E[1] + dir[1] * gap).toFixed(1), r: (sw * .6).toFixed(1), class: 'band__dot' });
    bandSvg.appendChild(b.dot);
    b.outer = buildOuterBand(box, A, sw, stacked);
    return b;
  }
  // the same band flowing out of the headline's full stop, down the gap between copy and buttons, into the window
  var heroBandSvg = $('[data-hero-band]');
  var heroWrap = $('.hero__wrap');
  function buildOuterBand(bodyBox, A, sw, stacked) {
    if (!heroBandSvg || !heroWrap) return null;
    while (heroBandSvg.firstChild) heroBandSvg.removeChild(heroBandSvg.firstChild);
    var wb = heroWrap.getBoundingClientRect();
    heroBandSvg.setAttribute('viewBox', '0 0 ' + wb.width.toFixed(0) + ' ' + wb.height.toFixed(0));
    if (stacked) return null;
    var stop = $('.hero__stop'), lead = $('.hero__lead'), cta = $('.hero__cta .btn'), row = $('.hero__row'), win = $('.hero__window');
    if (!stop || !lead || !cta) return null;
    var sr = stop.getBoundingClientRect(), cr = cta.getBoundingClientRect(), rr = row.getBoundingClientRect(), wr = win.getBoundingClientRect();
    var leadRight = textRight(lead, 0);
    var gapX = (leadRight + cr.left) / 2 - wb.left;
    if (cr.left - leadRight < 3 * sw) return null; // no clean gap to fall through
    // CJK “。” sits low-left in its box; a Latin “.” sits centred just above the baseline
    var S = EN ? [sr.left + sr.width * .5 - wb.left, sr.top + sr.height * .78 - wb.top]
               : [sr.left + sr.width * .26 - wb.left, sr.top + sr.height * .9 - wb.top];
    var E = [A[0] + bodyBox.left - wb.left, A[1] + bodyBox.top - wb.top];
    var rowTop = rr.top - wb.top, winTop = wr.top - wb.top;
    var d = 'M' + P(S) + ' C' + P([S[0], S[1] + 60]) + ' ' + P([gapX, S[1] + 10]) + ' ' + P([gapX, Math.max(S[1] + 70, rowTop + 50)]) +
      ' L' + P([gapX, winTop - 30]) + ' C' + P([gapX, winTop + 40]) + ' ' + P([E[0], E[1] - 110]) + ' ' + P(E);
    var defs = svgEl('defs');
    var lg = svgEl('linearGradient', { id: 'bandOuter', gradientUnits: 'userSpaceOnUse', x1: S[0].toFixed(1), y1: S[1].toFixed(1), x2: E[0].toFixed(1), y2: E[1].toFixed(1) });
    lg.appendChild(svgEl('stop', { offset: '0', 'stop-color': '#008a7b' }));
    lg.appendChild(svgEl('stop', { offset: '1', 'stop-color': '#45d3bd' }));
    defs.appendChild(lg);
    heroBandSvg.appendChild(defs);
    var o = {};
    o.glow = svgEl('path', { d: d, class: 'band__glow', fill: 'none', stroke: '#36c7b1', 'stroke-width': sw * 1.8, 'stroke-linecap': 'round' });
    o.path = svgEl('path', { d: d, fill: 'none', stroke: 'url(#bandOuter)', 'stroke-width': sw, 'stroke-linecap': 'round' });
    o.node = svgEl('circle', { cx: E[0].toFixed(1), cy: E[1].toFixed(1), r: (sw * .36).toFixed(1), class: 'band__node' });
    heroBandSvg.appendChild(o.glow); heroBandSvg.appendChild(o.path); heroBandSvg.appendChild(o.node);
    return o;
  }
  function bandIntro(tl, at) {
    if (!band) return;
    var dash = function (p) { var L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; return p; };
    [band.f1, band.back, band.f3].concat(band.glow).forEach(dash);
    var origin = { transformOrigin: '50% 50%', transformBox: 'fill-box' };
    if (band.outer) {
      dash(band.outer.path); dash(band.outer.glow);
      tl.to([band.outer.path, band.outer.glow], { strokeDashoffset: 0, duration: .75, ease: 'power2.inOut' }, at);
      at += .7;
    }
    tl.to([band.f1, band.glow[0]], { strokeDashoffset: 0, duration: .55, ease: 'power2.in' }, at)
      .to(band.back, { strokeDashoffset: 0, duration: .3, ease: 'none' }, '>')
      .to([band.f3, band.glow[1]], { strokeDashoffset: 0, duration: .55, ease: 'power2.out' }, '>')
      .from(band.nodes[0], Object.assign({ scale: 0, duration: .3, ease: 'back.out(3)' }, origin), at)
      .from(band.nodes[1], Object.assign({ scale: 0, duration: .3, ease: 'back.out(3)' }, origin), at + .5)
      .from(band.nodes[2], Object.assign({ scale: 0, duration: .3, ease: 'back.out(3)' }, origin), at + .82)
      .from(band.ticks, { opacity: 0, duration: .3, stagger: .25 }, at + .1)
      .from(band.dot, Object.assign({ scale: 0, duration: .45, ease: 'back.out(3)' }, origin), at + 1.35)
      .add(function () {
        var all = [band.f1, band.back, band.f3].concat(band.glow);
        if (band.outer) all.push(band.outer.path, band.outer.glow);
        all.forEach(function (p) { p.style.strokeDasharray = ''; p.style.strokeDashoffset = ''; });
      }, at + 1.5);
  }
  band = buildBand();
  var bandW = window.innerWidth, bandTimer;
  window.addEventListener('resize', function () {
    clearTimeout(bandTimer);
    bandTimer = setTimeout(function () { if (window.innerWidth !== bandW) { bandW = window.innerWidth; band = buildBand(); } }, 120);
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { if (!bandIntroRunning) band = buildBand(); });
  var bandIntroRunning = false;

  /* ---------------------------------------------------- how: static fallback */
  var how = $('#how');
  function howStatic() {
    how.classList.add('is-static');
    how.classList.remove('is-pinned');
    $$('.step', how).forEach(function (s) { s.classList.add('is-active'); });
  }

  /* -------------------------------------------------------------- motion */
  if (!hasGsap) {
    document.documentElement.classList.remove('js');
    howStatic();
    return;
  }
  gsap.registerPlugin(ScrollTrigger);
  // keep entrances time-based: a throttled or background tab finishes them instead of freezing mid-way
  gsap.ticker.lagSmoothing(0);

  var mm = gsap.matchMedia();
  mm.add({ desktop: '(min-width: 901px)', mobile: '(max-width: 900px)', reduce: '(prefers-reduced-motion: reduce)' }, function (ctx) {
    var cond = ctx.conditions;
    if (cond.reduce) {
      gsap.set('.reveal', { opacity: 1, y: 0 });
      howStatic();
      return;
    }

    /* hero intro */
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero .pill, .hero .kicker', { opacity: 0, y: 10, duration: .6, stagger: .06 })
      .from('.hero__title .line', { yPercent: 55, opacity: 0, letterSpacing: '.04em', duration: .9, stagger: .1 }, '-=.35')
      .from('.hero__lead, .hero__cta > *', { opacity: 0, y: 14, duration: .6, stagger: .05 }, '-=.55')
      .from('.hero__window', { opacity: 0, y: 40, duration: .9, ease: 'back.out(1.1)' }, '-=.45')
      .from('.hero__body .tree__row', { opacity: 0, x: -8, duration: .35, stagger: .035 }, '-=.4')
      .from('.log__line', { opacity: 0, y: 6, duration: .4, stagger: .2 }, '-=.2');
    if (band) { bandIntroRunning = true; bandIntro(heroTl, 1.8); heroTl.add(function () { bandIntroRunning = false; band = buildBand(); }); }

    /* hero scroll: headline recedes as a graphic layer */

    /* generic reveals (once) */
    ScrollTrigger.batch('.reveal', {
      start: 'top 88%', once: true,
      onEnter: function (els) { gsap.to(els, { opacity: 1, y: 0, duration: .8, ease: 'power3.out', stagger: .07, overwrite: true }); }
    });

    /* ledger rows unfold in reading order */
    ScrollTrigger.batch('.lrow', {
      start: 'top 92%', once: true,
      onEnter: function (els) { gsap.from(els, { opacity: 0, y: 12, duration: .5, ease: 'power2.out', stagger: .045 }); }
    });

    /* figures land with a little weight; the plot is unmasked top-down */
    ScrollTrigger.batch('.fig', {
      start: 'top 90%', once: true,
      onEnter: function (els) {
        gsap.from(els, { opacity: 0, y: 34, duration: .8, ease: 'back.out(1.25)', stagger: .07 });
        gsap.from(els.map(function (e) { return $('.fig__img img', e); }), { scale: 1.08, clipPath: 'inset(0 0 100% 0)', duration: .9, ease: 'power3.out', stagger: .07 });
      }
    });

    /* cycle: arcs draw along the loop, then nodes land */
    var arcs = $$('.cycle__arcs path');
    arcs.forEach(function (p) { var L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
    var cycTl = gsap.timeline({ scrollTrigger: { trigger: '.loop__map', start: 'top 80%', once: true } });
    cycTl
      .from('.cycle .node', { scale: .6, opacity: 0, transformOrigin: '50% 50%', duration: .5, ease: 'back.out(1.8)', stagger: .07 })
      .to(arcs, { strokeDashoffset: 0, duration: .45, ease: 'power2.inOut', stagger: .12 }, '-=.25')
      .from('.lane', { opacity: 0, y: 10, duration: .5, stagger: .08 }, '-=.2');

    /* install terminal clicks into place */
    gsap.from('.terminal', { scale: .97, duration: .5, ease: 'power4.out', scrollTrigger: { trigger: '.terminal', start: 'top 85%', once: true } });

    /* how: pinned, scroll-driven camera over the project tree */
    howPinned(cond.desktop);
  });

  function howPinned(desktop) {
    how.classList.remove('is-static');
    how.classList.add('is-pinned');
    var view = $('.how__view', how);
    var cam = $('.how__cam', how);
    var marker = $('.how__marker', how);
    var rows = $$('.tree__row', cam);
    var steps = $$('.step', how);
    var caption = $('[data-how-caption]', how);
    var rail = $('.steps__rail i', how);
    var v02 = $('[data-key="v02"]', cam);
    var newEvents = $$('[data-how-new2], [data-how-new]', cam);
    var CAPS = ['', 'Memory/current.md', 'Analysis/AN-0001', 'Design/PROT-0001/v02'];
    var FOCUS = { 1: 'current', 2: 'report', 3: 'v02' };
    // rows below v02 sit one row higher until v02 is created, then slide down to make room
    var after = rows.slice(rows.indexOf(v02) + 1);
    var others = rows.filter(function (r) { return r !== v02; });
    function rowH() { return v02.offsetHeight; }

    function inSt(r, st) { return (' ' + (r.getAttribute('data-st') || '') + ' ').indexOf(' ' + st + ' ') > -1; }
    function topOf(r, st) { return r.offsetTop - (st < 3 && after.indexOf(r) > -1 ? rowH() : 0); }
    function camFor(st) {
      var vh = view.clientHeight, vw = view.clientWidth;
      var ch = cam.scrollHeight - (st < 3 ? rowH() : 0);
      var sel = st === 3 ? [$('[data-key="memory"]', cam), v02] : rows.filter(function (r) { return inSt(r, st); });
      var top = Infinity, bot = 0;
      sel.forEach(function (r) { var t = topOf(r, st); top = Math.min(top, t); bot = Math.max(bot, t + r.offsetHeight); });
      var maxS = desktop ? 1.3 : (vw < 420 ? 1.04 : 1.12);
      var s = Math.min(maxS, (vh - 48) / (bot - top));
      var y = vh / 2 - ((top + bot) / 2) * s;
      if (ch * s <= vh) y = (vh - ch * s) / 2;
      else y = Math.max(Math.min(y, 0), vh - ch * s); // never leave an empty band above the root or below the last row
      return { s: s, y: y };
    }
    function markFor(st) {
      var c = camFor(st), row = $('[data-key="' + FOCUS[st] + '"]', cam);
      return { y: c.y + topOf(row, st) * c.s, sy: c.s };
    }
    function rowOpacity(st) {
      return function (i, r) { return inSt(r, st) ? 1 : .26; };
    }
    var stepsEl = $('.steps', how);
    function placeRail() {
      var box = rail.parentNode;
      box.style.top = (stepsEl.offsetTop + 24) + 'px';
      box.style.bottom = 'auto';
      box.style.height = Math.max(0, stepsEl.offsetHeight - 48) + 'px';
    }
    placeRail();
    ScrollTrigger.addEventListener('refreshInit', placeRail);
    var current = 0;
    function setStation(p) {
      var st = p < .3 ? 1 : p < .7 ? 2 : 3;
      if (st === current) return;
      current = st;
      steps.forEach(function (s) { s.classList.toggle('is-active', +s.getAttribute('data-step') === st); });
      caption.textContent = CAPS[st];
    }

    gsap.set(marker, { opacity: 1, transformOrigin: '0 0' });
    var tl = gsap.timeline({
      defaults: { ease: 'power2.inOut' },
      scrollTrigger: {
        trigger: how, pin: '.how__pin', start: 'top top',
        end: function () { return '+=' + Math.round(window.innerHeight * (desktop ? 2.4 : 1.8)); },
        scrub: .6, invalidateOnRefresh: true, anticipatePin: 1,
        onUpdate: function (self) { setStation(self.progress); },
        onRefresh: function (self) { current = 0; setStation(self.progress); }
      }
    });
    tl.fromTo(cam, { y: function () { return camFor(1).y; }, scale: function () { return camFor(1).s; } }, { y: function () { return camFor(1).y; }, scale: function () { return camFor(1).s; }, duration: 1, ease: 'none' }, 0)
      .fromTo(marker, { y: function () { return markFor(1).y; }, scaleY: function () { return markFor(1).sy; } }, { y: function () { return markFor(1).y; }, scaleY: function () { return markFor(1).sy; }, duration: 1, ease: 'none' }, 0)
      .fromTo(others, { opacity: rowOpacity(1) }, { opacity: rowOpacity(1), duration: 1, ease: 'none' }, 0)
      .fromTo(after, { y: function () { return -rowH(); } }, { y: function () { return -rowH(); }, duration: 1, ease: 'none' }, 0)
      .fromTo(v02, { opacity: 0, x: -14 }, { opacity: 0, x: -14, duration: 1, ease: 'none' }, 0)
      .fromTo(newEvents, { opacity: 0, scale: .6 }, { opacity: 0, scale: .6, duration: 1, ease: 'none' }, 0)
      .fromTo(rail, { scaleY: 0 }, { scaleY: 1, duration: 5, ease: 'none' }, 0)
      // to station 2: the camera travels down the tree to Experiment / Analysis
      .to(cam, { y: function () { return camFor(2).y; }, scale: function () { return camFor(2).s; }, duration: 1 }, 1)
      .to(marker, { y: function () { return markFor(2).y; }, scaleY: function () { return markFor(2).sy; }, duration: 1 }, 1)
      .to(others, { opacity: rowOpacity(2), duration: .7 }, 1.15)
      // to station 3: back up to Design/, v02 is inserted and Memory/events gets the write-back
      .to(cam, { y: function () { return camFor(3).y; }, scale: function () { return camFor(3).s; }, duration: 1 }, 3)
      .to(others, { opacity: rowOpacity(3), duration: .7 }, 3.1)
      .to(after, { y: 0, duration: .5, ease: 'power2.out' }, 3.45)
      .to(v02, { opacity: 1, x: 0, duration: .45, ease: 'back.out(2)' }, 3.6)
      .to(marker, { y: function () { return markFor(3).y; }, scaleY: function () { return markFor(3).sy; }, duration: .6 }, 3.45)
      .to(newEvents, { opacity: 1, scale: 1, duration: .45, ease: 'back.out(2.2)', stagger: .12 }, 3.75)
      .to({}, { duration: 1 }, 4.2);
    setStation(0);
  }

  window.addEventListener('load', function () { ScrollTrigger.refresh(); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { ScrollTrigger.refresh(); });
})();
