"""
light-chart :: setup_style.py
=======================================
Publication-grade matplotlib / seaborn style configuration.

应用出版级样式预设。支持 nature / ieee / science / general 四种期刊预设，
支持中英文（lang='zh'/'en'），中文模式按优先级自动查找
Noto Sans CJK SC > Source Han Sans SC > SimHei > Microsoft YaHei
并修正负号渲染。SciencePlots 可选——装了就用，没装回退到内置等效预设。

Usage
-----
    from setup_style import setup_style

    # Nature 单栏英文图
    setup_style(journal='nature', lang='en')

    # 中文期刊通用
    setup_style(journal='general', lang='zh')

    # 关闭 SciencePlots 强制用内置预设
    setup_style(journal='ieee', use_sciplots=False)

CLI: ``python setup_style.py --list-fonts`` 列出可用 CJK 字体。
"""
from __future__ import annotations

import argparse
import sys
import warnings

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


# 期刊预设：figsize 单位为英寸，对应该期刊单栏标称宽度
# Nature: 89mm = 3.5 in  双栏: 183mm = 7.2 in
# Science: 与 Nature 接近
# IEEE: 单栏 3.5 in, 双栏 7.16 in
JOURNAL_PRESETS = {
    "nature": {
        "figure.figsize": (3.5, 2.625),  # 4:3 ratio @ 89mm
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "science": {
        "figure.figsize": (3.5, 2.625),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "ieee": {
        "figure.figsize": (3.5, 2.5),
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.7,
        "axes.grid": False,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "general": {
        "figure.figsize": (5.0, 3.5),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "lines.linewidth": 1.2,
        "lines.markersize": 5,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
}

# 中文字体优先级列表（按可用性 + 期刊接受度排序）
CJK_FONT_PRIORITY = [
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "Source Han Sans SC",
    "Source Han Sans CN",
    "SimHei",
    "Microsoft YaHei",
    "PingFang SC",
    "Heiti SC",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
]

CJK_SERIF_PRIORITY = [
    "Noto Serif CJK SC",
    "Noto Serif SC",
    "Source Han Serif SC",
    "Source Han Serif CN",
    "SimSun",
    "STSong",
    "Songti SC",
]

CJK_INSTALL_HINT = """\
找不到任何中文字体。请安装 Noto CJK 字体之一：

  Linux:    sudo apt install fonts-noto-cjk    # Debian/Ubuntu
            sudo dnf install google-noto-sans-cjk-fonts  # Fedora/RHEL
  macOS:    brew install --cask font-noto-sans-cjk-sc
            或下载: https://github.com/notofonts/noto-cjk/releases
  Windows:  下载 https://github.com/notofonts/noto-cjk/releases
            解压后右键 .ttf/.otf 文件 -> "为所有用户安装"

或者列出当前已安装的中文字体：
  python setup_style.py --list-fonts
"""


def _available_fonts() -> set[str]:
    """返回 matplotlib 已索引的全部字体名集合。"""
    return {f.name for f in fm.fontManager.ttflist}


def list_cjk_fonts() -> list[str]:
    """返回系统上可用的 CJK 字体（按优先级排序）。"""
    available = _available_fonts()
    hits = []
    for f in CJK_FONT_PRIORITY + CJK_SERIF_PRIORITY:
        if f in available and f not in hits:
            hits.append(f)
    # 额外做一次包含中文关键词的扫描，捕获非标准命名的中文字体
    for f in available:
        lower = f.lower()
        if any(k in lower for k in ("cjk", "han", "songti", "yahei", "simhei", "simsun")):
            if f not in hits:
                hits.append(f)
    return hits


def configure_chinese_fonts(serif_for_zh: bool = False) -> str:
    """
    自动检测并配置中文字体；同时修正负号渲染。

    Args:
        serif_for_zh: True 时优先选用衬线中文字体（宋体类），用于中文期刊
            "宋体正文 + Times New Roman 数字" 的混排约定。
    Returns:
        实际选用的中文字体名。
    Raises:
        RuntimeError: 系统未安装任何识别到的中文字体。
    """
    available = _available_fonts()
    priority = CJK_SERIF_PRIORITY + CJK_FONT_PRIORITY if serif_for_zh else CJK_FONT_PRIORITY

    chosen = None
    for f in priority:
        regular = any(entry.name == f and 300 <= fm.weight_dict.get(entry.weight, entry.weight) <= 500
                      and entry.style == "normal" for entry in fm.fontManager.ttflist)
        if f in available and regular:
            chosen = f
            break

    if chosen is None:
        # 兜底：扫包含 cjk/han 等关键字的字体
        for f in available:
            lower = f.lower()
            if any(k in lower for k in ("cjk", "han", "song", "hei", "yahei", "kaiti")):
                chosen = f
                break

    if chosen is None:
        raise RuntimeError(CJK_INSTALL_HINT)

    # Latin first: Matplotlib selects the first face containing each glyph.
    # Putting SimSun first also captures Latin/digits, defeating mixed fonts.
    latin_candidates = (["Times New Roman", "DejaVu Serif"] if serif_for_zh
                        else ["Arial", "Helvetica", "DejaVu Sans"])
    latin = next(f for f in latin_candidates if f in available)
    fallback = "DejaVu Serif" if serif_for_zh else "DejaVu Sans"
    plt.rcParams["font.family"] = list(dict.fromkeys([latin, fallback, chosen]))
    if serif_for_zh:
        plt.rcParams["font.serif"] = [latin, chosen]
    else:
        plt.rcParams["font.sans-serif"] = [latin, chosen]
    # 修正负号 unicode minus 在某些中文字体里渲染成方框的问题
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


def _try_sciencplots(journal: str) -> bool:
    """If SciencePlots is installed, apply its style stack; otherwise return False."""
    try:
        import scienceplots  # noqa: F401
    except ImportError:
        return False

    # SciencePlots 风格栈：基础 + 期刊变体
    stack = ["science"]
    if journal == "nature":
        stack.append("nature")
    elif journal == "ieee":
        stack.append("ieee")
    # 关掉 LaTeX 渲染避免环境缺 LaTeX 时崩溃；中文模式必须关
    stack.append("no-latex")
    try:
        plt.style.use(stack)
        return True
    except OSError as e:
        warnings.warn(f"SciencePlots style stack failed: {e}; fallback to builtin.")
        return False


def setup_style(
    journal: str = "general",
    lang: str = "en",
    use_sciplots: bool = False,
    serif_for_zh: bool = False,
    constrained_layout: bool = True,
    project=None,
) -> dict:
    """
    应用出版级样式预设。

    Args:
        journal: 'nature' | 'science' | 'ieee' | 'general'
        lang: 'en' | 'zh' — 中文模式自动配置中文字体并修正负号
        use_sciplots: 优先尝试 SciencePlots；不可用则回退到内置预设
        serif_for_zh: 中文模式下使用宋体类衬线字体（中文期刊常约定）
        constrained_layout: 默认 True——全局开启 constrained_layout 自适应排版，
            从源头减少标题/轴标签被裁、图例压数据、子图互相重叠。需要手动
            subplots_adjust 或某些 colorbar 写法时可传 False 关闭。
    Returns:
        dict 包含 keys: journal / lang / sciplots_used / cjk_font / constrained_layout
    """
    if journal not in JOURNAL_PRESETS:
        raise ValueError(f"Unknown journal preset: {journal}. "
                         f"Choose from {sorted(JOURNAL_PRESETS)}")

    sciplots_used = False
    if use_sciplots:
        sciplots_used = _try_sciencplots(journal)

    # 内置预设始终在 SciencePlots 之上覆盖一遍，确保关键参数（fonttype、字号）落实
    plt.rcParams.update(JOURNAL_PRESETS[journal])
    # Missing candidate fonts cause repeated findfont messages even when fallback works.
    available = _available_fonts()
    for family in ("font.sans-serif", "font.serif"):
        candidates = [name for name in plt.rcParams[family] if name in available]
        if candidates:
            plt.rcParams[family] = candidates

    # 默认开启自适应排版：从源头减少文字遮盖 / 裁切 / 子图重叠
    plt.rcParams["figure.constrained_layout.use"] = constrained_layout

    # 全模式默认修正负号：避免所选字体缺 U+2212 时负号渲染成方框（一种乱码）。
    # 用 ASCII hyphen-minus 代替真减号，几乎所有字体都含，最稳妥。
    plt.rcParams["axes.unicode_minus"] = False

    from project_style import current_project, use_project, rc_params
    project_data = use_project(project) if project is not None else current_project()
    # Shared semantic colors and readable minimum even with a legacy preset.
    from cycler import cycler
    plt.rcParams['axes.prop_cycle'] = cycler(color=project_data['palettes']['categorical'])
    minimum = project_data['typography']['minimum_pt']
    for key in ('font.size','axes.labelsize','axes.titlesize','xtick.labelsize','ytick.labelsize','legend.fontsize'):
        if isinstance(plt.rcParams[key], (int,float)):
            plt.rcParams[key] = max(minimum, plt.rcParams[key])
    cjk_font = None
    if lang == "zh":
        cjk_font = configure_chinese_fonts(serif_for_zh=serif_for_zh)
    elif lang != "en":
        raise ValueError(f"lang must be 'en' or 'zh', got {lang!r}")
    if project is not None:
        plt.rcParams.update(rc_params(project_data, lang=lang))
        if lang == 'zh':
            from project_style import resolved_fonts
            cjk_font = resolved_fonts(project_data)['cjk']

    return {
        "journal": journal,
        "lang": lang,
        "sciplots_used": sciplots_used,
        "cjk_font": cjk_font,
        "constrained_layout": constrained_layout,
    }


def _cli() -> int:
    p = argparse.ArgumentParser(description="light-chart style setup")
    p.add_argument("--list-fonts", action="store_true",
                   help="列出当前系统上可用的 CJK 字体")
    p.add_argument("--test", action="store_true",
                   help="应用预设并打印 rcParams 关键值")
    p.add_argument("--journal", default="general",
                   choices=list(JOURNAL_PRESETS))
    p.add_argument("--lang", default="en", choices=["en", "zh"])
    p.add_argument("--no-sciplots", action="store_true")
    p.add_argument("--serif-zh", action="store_true")
    args = p.parse_args()

    if args.list_fonts:
        fonts = list_cjk_fonts()
        if fonts:
            print("已检测到的 CJK 字体（按优先级排序）：")
            for f in fonts:
                print(f"  - {f}")
        else:
            print("未检测到任何 CJK 字体。")
            print(CJK_INSTALL_HINT)
        return 0

    if args.test:
        info = setup_style(journal=args.journal, lang=args.lang,
                           use_sciplots=not args.no_sciplots,
                           serif_for_zh=args.serif_zh)
        print(f"applied: {info}")
        for k in ("figure.figsize", "font.family", "font.size",
                  "axes.labelsize", "pdf.fonttype", "axes.unicode_minus"):
            print(f"  {k} = {plt.rcParams[k]!r}")
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
