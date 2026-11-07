"""Thin adapters around the three execution/analysis backends.

Nothing here imports Scrapling, js-reverse, or REA at module import time. The
adapters only discover commands and describe contracts, which keeps the core
skill usable before the heavy dependencies are installed.
"""

from . import js_reverse, rea, scrapling

__all__ = ["js_reverse", "rea", "scrapling"]
