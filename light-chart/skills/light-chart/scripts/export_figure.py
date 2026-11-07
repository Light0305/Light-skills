"""
light-chart :: export_figure.py
=========================================
Unified figure export to multiple formats at exact final size.

- Vector preferred: PDF / SVG / EPS for line/bar/scatter (lossless, journal-friendly).
- Raster for photos / micrographs: PNG / TIFF at >= 300 DPI; never JPEG for data figures.
- Embeds TrueType fonts (fonttype 42) to keep text editable where supported.
- Optional grayscale preview to sanity-check colorblind safety.

Usage
-----
    from export_figure import export_figure
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0,1,2],[3,1,4])

    paths = export_figure(
        fig,
        basename="figs/fig1_main",
        formats=["pdf", "svg", "png"],
        size_inches=(3.5, 2.625),   # 示例物理尺寸
        dpi=600,
        grayscale_preview=True,
    )
    # -> ['figs/fig1_main.pdf', 'figs/fig1_main.svg',
    #     'figs/fig1_main.png', 'figs/fig1_main_grayscale.png']

CLI: ``python export_figure.py demo`` 生成一张演示图并多格式导出。
"""
from __future__ import annotations

import argparse
import io
import math
import os
import sys
from typing import Iterable

import matplotlib.pyplot as plt


VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_FORMATS = {"png", "tiff", "tif", "jpg", "jpeg"}
SUPPORTED_FORMATS = VECTOR_FORMATS | RASTER_FORMATS


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def export_figure(
    fig,
    basename: str,
    formats: Iterable[str] | None = None,
    dpi: int = 300,
    size_inches: tuple[float, float] | None = None,
    grayscale_preview: bool = False,
    tight: bool = False,
    pad_inches: float = 0.05,
    transparent: bool = False,
) -> list[str]:
    """
    Export a matplotlib Figure to one or more formats at exact final size.

    Args:
        fig: matplotlib Figure object.
        basename: 输出路径前缀（不含扩展名）；可包含子目录，自动创建。
        formats: list/tuple of extensions, e.g. ['pdf', 'svg', 'png'].
            Default: ['pdf', 'svg', 'png'].
        dpi: raster 格式分辨率；建议 300（普通）/ 600（IEEE 等）。
        size_inches: (width, height) 英寸；指定后会 fig.set_size_inches() 强制
            最终尺寸。强烈建议传入——保证导出后不必在 Word/LaTeX 里二次缩放。
        grayscale_preview: 额外生成一张 _grayscale.png 供色盲安全检查。
        tight: 是否走 bbox_inches='tight'（裁掉留白）。
        pad_inches: tight 模式下保留的边距（英寸）。
        transparent: 透明背景（PPT/海报可能需要）。

    Returns:
        实际写出的文件路径列表。
    """
    if formats is None:
        formats = ("pdf", "svg", "png")
    formats = [f.lower().lstrip(".") for f in formats]
    unknown = [f for f in formats if f not in SUPPORTED_FORMATS]
    if unknown:
        raise ValueError(f"Unsupported formats: {unknown}. "
                         f"Supported: {sorted(SUPPORTED_FORMATS)}")

    if not math.isfinite(dpi) or dpi <= 0:
        raise ValueError("dpi must be positive and finite")
    if size_inches is not None:
        if len(size_inches) != 2 or not all(math.isfinite(v) and v > 0 for v in size_inches):
            raise ValueError("size_inches must contain positive finite width and height")
        fig.set_size_inches(*size_inches)
    if tight and size_inches is not None:
        raise ValueError("tight cropping changes page size; use tight=False with size_inches")

    # Prefer embedded TrueType text; journal-specific requirements are checked separately.
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"  # 文本仍可编辑，期刊通常更欢迎

    fig.canvas.draw()
    # Preserve one measured layout across PDF/SVG/raster renderer font metrics.
    engine = fig.get_layout_engine()
    fig.set_layout_engine("none")
    saved: list[str] = []
    try:
        for fmt in formats:
            if fmt in {"jpg", "jpeg"}:
                print(f"[light-chart] WARNING: skipping {fmt} — "
                      "JPEG is lossy and unsuitable for line/text figures.",
                      file=sys.stderr)
                continue
            path = f"{basename}.{fmt}"
            _ensure_parent(path)
            kwargs: dict = {
                "bbox_inches": "tight" if tight else None,
                "pad_inches": pad_inches,
                "transparent": transparent,
            }
            if fmt in RASTER_FORMATS:
                kwargs["dpi"] = dpi
            with plt.rc_context({"savefig.bbox": None}):
                fig.savefig(path, **kwargs)
            saved.append(path)
            print(f"[light-chart] wrote {path}")

        if grayscale_preview:
            gray_path = _grayscale_from(fig, basename, dpi=dpi, tight=tight, pad_inches=pad_inches)
            if gray_path:
                saved.append(gray_path)
    finally:
        fig.set_layout_engine(engine)
    return saved


def _grayscale_from(fig, basename: str, dpi: int, tight: bool = False,
                    pad_inches: float = 0.05) -> str | None:
    """
    导出灰度预览版用于色盲安全检查。
    用 PIL 转灰度；找不到 PIL 时明确记录跳过。
    """
    try:
        from PIL import Image
    except ImportError:
        print("[light-chart] Pillow not available; "
              "grayscale preview skipped.", file=sys.stderr)
        return None

    gray_path = f"{basename}_grayscale.png"
    _ensure_parent(gray_path)
    # Render into memory: never overwrite the production color PNG.
    with io.BytesIO() as buffer:
        with plt.rc_context({"savefig.bbox": None}):
            fig.savefig(buffer, format="png", dpi=dpi,
                        bbox_inches="tight" if tight else None, pad_inches=pad_inches)
        buffer.seek(0)
        with Image.open(buffer) as source:
            source.convert("L").save(gray_path, dpi=(dpi, dpi))
    print(f"[light-chart] wrote {gray_path} (grayscale preview)")
    return gray_path


def _demo(out_basename: str) -> None:
    """Generate a small demo figure for quick smoke testing."""
    import numpy as np
    rng = np.random.default_rng(7)
    x = np.linspace(0, 10, 50)
    y1 = np.sin(x) + rng.normal(0, 0.1, x.size)
    y2 = np.cos(x) + rng.normal(0, 0.1, x.size)

    fig, ax = plt.subplots(figsize=(3.5, 2.625))
    ax.plot(x, y1, label="sin", marker="o", markersize=3)
    ax.plot(x, y2, label="cos", marker="s", markersize=3, linestyle="--")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(frameon=False)

    paths = export_figure(
        fig, out_basename,
        formats=["pdf", "svg", "png"],
        size_inches=(3.5, 2.625),
        dpi=300,
        grayscale_preview=True,
    )
    print("\nDemo done. Files:")
    for p in paths:
        print(f"  {p}")


def _cli() -> int:
    p = argparse.ArgumentParser(description="light-chart figure exporter")
    p.add_argument("cmd", choices=["demo"], help="`demo`: 跑一张演示图导出 4 种格式")
    p.add_argument("--out", default="./light_chart_demo",
                   help="输出 basename (默认 ./light_chart_demo)")
    args = p.parse_args()
    if args.cmd == "demo":
        _demo(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
