"""
light-chart :: layout_tools.py
========================================
排版安全网 + 多面板子图编号对齐。

解决两类高频成图问题：

1. **子图 a/b/c 编号乱放、横竖不对齐** —— `add_panel_labels()`
   把每个标签锚定在各子图的 ``axes fraction (0,1)``（左上角），再统一施加
   **同一个 points 偏移**。由于同一列子图的左边缘 figure-x 相同、同一行子图
   的上边缘 figure-y 相同，统一偏移后所有标签**横看一条线、竖看一条线**，
   不会因为各子图 y 轴刻度宽度不同而错位。

2. **标题/轴标签被裁、图例压数据、子图互相重叠** —— `finalize_figure()`
   出图前兜底启用 constrained_layout（失败回退 tight_layout），统一边距。

两者都是"事后兜底"工具：即使绘制阶段没注意布局，跑一遍也能把版面救回来。

Usage
-----
    from layout_tools import add_panel_labels, finalize_figure
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
    # ... 在 4 个子图上各自作图 ...
    finalize_figure(fig)                 # 先把版面理顺
    add_panel_labels(fig, style="nature")  # a b c d，自动对齐

CLI: ``python layout_tools.py demo --out ./panel_demo`` 画一张 2x2 验证对齐。
"""
from __future__ import annotations

import argparse
import string
import sys

import matplotlib.pyplot as plt


# Windows GBK 终端下直接 print 中文会 UnicodeEncodeError。用 reconfigure 而非替换
# sys.stdout：幂等、不创建新对象，多个脚本一起 import 时也不会关闭底层流。
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# 子图编号的几种期刊惯例
PANEL_STYLES = {
    "nature": lambda s: s,                    # a  b  c   （小写加粗，Nature/Cell 系）
    "science": lambda s: s,                   # a  b  c
    "ieee": lambda s: f"({s})",               # (a)(b)(c) （IEEE/Elsevier 系）
    "paren": lambda s: f"({s})",              # (a)(b)(c)
    "upper": lambda s: s.upper(),             # A  B  C
    "upper_paren": lambda s: f"({s.upper()})",  # (A)(B)(C)
}


def _letter_sequence(n: int) -> list[str]:
    """生成 a, b, ..., z, aa, ab, ... 的标签序列。"""
    letters = string.ascii_lowercase
    out: list[str] = []
    for i in range(n):
        if i < 26:
            out.append(letters[i])
        else:
            # 第 27 个起用 aa, ab... 兜底（超过 26 个 panel 已极罕见）
            out.append(letters[i // 26 - 1] + letters[i % 26])
    return out


def _data_axes(fig) -> list:
    """只取真正的网格子图，排除 colorbar / inset（它们没有 subplotspec）。"""
    return [ax for ax in fig.axes
            if ax.get_visible() and ax.axison
            and not str(ax.get_label()).startswith("<colorbar")
            and getattr(ax, "get_subplotspec", lambda: None)() is not None]


def add_panel_labels(
    fig,
    axes=None,
    labels=None,
    style: str = "nature",
    fontsize=None,
    fontweight: str = "bold",
    x_offset_pt: float = -20.0,
    y_offset_pt: float = 2.0,
    ha: str = "right",
    va: str = "bottom",
    color: str = "black",
):
    """
    给多面板图的每个子图打统一对齐的 a/b/c 编号。

    对齐原理：标签锚点固定为各子图的 ``axes fraction (0, 1)``（左上角），
    再加 **统一的 (x_offset_pt, y_offset_pt) points 偏移**。同列子图左边缘
    figure-x 相同、同行子图上边缘 figure-y 相同 → 偏移一致 → 横竖都对齐。
    用物理 points 偏移而非 axes 比例偏移，保证不同尺寸子图的标签间距一致。

    Args:
        fig: matplotlib Figure。
        axes: 要标注的 axes 列表；默认自动取所有网格子图（按阅读顺序
            上→下、左→右排序），并排除 colorbar / inset。
        labels: 自定义标签列表；默认按 style 生成 a/b/c...。
        style: 'nature'|'science'(a b c) | 'ieee'|'paren'((a)(b)(c)) |
            'upper'(A B C) | 'upper_paren'((A)(B)(C))。
        fontsize: 标签字号；默认取 rcParams['axes.labelsize']。
        fontweight: 默认 'bold'（期刊惯例子图标签加粗）。
        x_offset_pt: 水平偏移(points)，负值=移到子图左侧（默认 -20，
            约让标签落在 y 轴标签外侧上方）。
        y_offset_pt: 垂直偏移(points)，正值=上移（默认 +2）。
        ha, va: 标签对齐方式；默认右下角对齐到偏移点。
        color: 标签颜色。

    Returns:
        放置的 Text/Annotation 对象列表（便于调用方再微调位置）。
    """
    if axes is None:
        axes = _data_axes(fig)
        # 按阅读顺序排序：y1 越大越靠上排在前，同排按 x0 从左到右
        axes = sorted(
            axes,
            key=lambda ax: (-round(ax.get_position().y1, 3),
                            round(ax.get_position().x0, 3)),
        )
    axes = list(axes)
    n = len(axes)
    if n == 0:
        return []

    if labels is None:
        fmt = PANEL_STYLES.get(style)
        if fmt is None:
            raise ValueError(
                f"Unknown panel style: {style!r}. "
                f"Choose from {sorted(PANEL_STYLES)}"
            )
        labels = [fmt(s) for s in _letter_sequence(n)]
    elif len(labels) < n:
        raise ValueError(
            f"提供了 {len(labels)} 个 labels 但有 {n} 个子图需要标注。"
        )

    if fontsize is None:
        fontsize = plt.rcParams.get("axes.labelsize", 9)

    placed = []
    for ax, lab in zip(axes, labels):
        t = ax.annotate(
            lab,
            xy=(0, 1), xycoords="axes fraction",
            xytext=(x_offset_pt, y_offset_pt), textcoords="offset points",
            fontsize=fontsize, fontweight=fontweight, color=color,
            ha=ha, va=va,
            annotation_clip=False,   # 关键：允许标签画在 axes 边界之外不被裁
        )
        placed.append(t)
    return placed


def finalize_figure(fig, prefer: str = "constrained", verbose: bool = False) -> str:
    """
    出图前兜底理顺版面：减少标题/轴标签被裁、图例压数据、子图互相重叠。

    优先用 constrained_layout（matplotlib 自适应排版引擎），失败再回退
    tight_layout，都失败则不动。**建议先调本函数再 add_panel_labels**——
    版面定下来后子图位置才稳定。

    Args:
        fig: matplotlib Figure。
        prefer: 'constrained'（默认）| 'tight'。
        verbose: True 时打印实际采用的策略。

    Returns:
        实际采用的策略：'constrained' | 'tight' | 'none'。
    """
    used = "none"
    if prefer == "constrained":
        try:
            fig.set_layout_engine("constrained")
            fig.canvas.draw()   # 触发一次布局计算，让子图位置落定
            used = "constrained"
        except Exception:
            used = "none"
    if used == "none":
        try:
            with _suppress_tight_warnings():
                fig.tight_layout()
            used = "tight"
        except Exception:
            used = "none"
    if verbose:
        print(f"[layout_tools] finalize_figure -> {used}")
    return used


class _suppress_tight_warnings:
    """tight_layout 在某些组合下会发 UserWarning；静默之，不影响结果。"""

    def __enter__(self):
        import warnings
        self._cm = warnings.catch_warnings()
        self._cm.__enter__()
        warnings.simplefilter("ignore")
        return self

    def __exit__(self, *exc):
        return self._cm.__exit__(*exc)


def _demo(out_basename: str) -> None:
    """画一张 2x2 演示图：刻意让各子图 y 轴量级不同，验证标签仍横竖对齐。"""
    import numpy as np
    rng = np.random.default_rng(0)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
    # 左上：普通量级
    axes[0, 0].plot(np.arange(10), rng.normal(0, 1, 10), marker="o")
    axes[0, 0].set_ylabel("score")
    # 右上：超大量级（y 轴刻度数字很宽，最考验对齐）
    axes[0, 1].plot(np.arange(10), rng.normal(0, 1, 10) * 1e6, marker="s")
    axes[0, 1].set_ylabel("count")
    # 左下：负值 + 长标签
    axes[1, 0].bar(np.arange(5), rng.normal(0, 1, 5))
    axes[1, 0].set_ylabel("Δ expression (a.u.)")
    axes[1, 0].set_xlabel("condition")
    # 右下：小数
    axes[1, 1].scatter(rng.random(20), rng.random(20))
    axes[1, 1].set_ylabel("p")
    axes[1, 1].set_xlabel("x")

    used = finalize_figure(fig, verbose=True)
    labels = add_panel_labels(fig, style="nature")

    png = f"{out_basename}.png"
    fig.savefig(png, dpi=150, bbox_inches="tight")
    print(f"[layout_tools] layout={used}, labels={[t.get_text() for t in labels]}")
    print(f"[layout_tools] wrote {png}")
    print("肉眼/AI 复核：a/b 顶部应等高，a/c 左缘应等宽——即横竖对齐。")


def _cli() -> int:
    p = argparse.ArgumentParser(description="light-chart layout tools")
    p.add_argument("cmd", choices=["demo"],
                   help="`demo`: 画一张 2x2 验证子图标签对齐")
    p.add_argument("--out", default="./panel_demo", help="输出 basename")
    args = p.parse_args()
    if args.cmd == "demo":
        _demo(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
