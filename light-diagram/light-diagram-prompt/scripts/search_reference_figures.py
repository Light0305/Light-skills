#!/usr/bin/env python3
"""Search and make a contact sheet for a local scientific-figure corpus.

Search is filename/metadata text matching only, not visual similarity search.
The optional contact sheet requires Pillow and does not alter source images.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def tokens(value: str) -> List[str]:
    return [part for part in re.split(r"[^\w]+", norm(value), flags=re.UNICODE) if part]


def load_metadata(path: Optional[Path]) -> List[Dict[str, Any]]:
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("items", data.get("selected", data.get("figures", [])))
    else:
        rows = []
    if not isinstance(rows, list):
        raise ValueError("metadata records must be a JSON array")
    return [row for row in rows if isinstance(row, dict)]


def metadata_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index image paths and IDs without overwriting duplicate basenames."""
    index: Dict[str, Dict[str, Any]] = {}
    ambiguous = set()
    for row in rows:
        for field in ("id", "image", "path", "filename"):
            value = row.get(field)
            if not value:
                continue
            normalized = norm(str(value).replace("\\", "/"))
            keys = {normalized, norm(Path(normalized).name)}
            if field == "id":
                keys.add(norm(Path(normalized).stem))
            for key in keys:
                if not key or key in ambiguous:
                    continue
                if key in index and index[key] != row:
                    del index[key]
                    ambiguous.add(key)
                else:
                    index[key] = row
    return index


def image_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in IMAGE_SUFFIXES:
            yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def resolve_row(path: Path, root: Path, index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    candidates = [norm(path.relative_to(root).as_posix()), norm(path.as_posix())]
    # Gallery paths often start with images/, while the user's copy starts at
    # venue/final. Match the longest available suffix before basename fallbacks.
    for start in range(max(0, len(path.parts) - 4), len(path.parts)):
        suffix = Path(*path.parts[start:]).as_posix()
        candidates.extend([norm(suffix), norm("images/" + suffix)])
    candidates.extend([norm(path.name), norm(path.stem)])
    for key in candidates:
        if key in index:
            return index[key]
    return None


def row_text(path: Path, row: Optional[Dict[str, Any]]) -> str:
    fields = [path.name, path.as_posix()]
    if row:
        fields.extend(str(row.get(key, "")) for key in ("id", "title", "venue", "year", "pattern", "authors"))
    return norm(" ".join(fields))


def score(path: Path, row: Optional[Dict[str, Any]], query_tokens: Sequence[str], pattern: str) -> Tuple[int, List[str]]:
    text = row_text(path, row)
    reasons: List[str] = []
    value = 0
    title = norm(row.get("title", "")) if row else ""
    for token in query_tokens:
        if token in text:
            value += 2 if token in title else 1
            reasons.append(f"keyword:{token}")
    if pattern:
        actual = norm(row.get("pattern")) if row else ""
        if actual == norm(pattern):
            value += 5
            reasons.append(f"pattern:{actual}")
        elif norm(pattern) in text:
            value += 1
            reasons.append(f"pattern-text:{pattern}")
    return value, reasons


def make_contact_sheet(paths: Sequence[Path], output: Path, columns: int, thumb_width: int) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required for --contact-sheet") from exc
    if columns < 1 or thumb_width < 64:
        raise ValueError("columns must be >= 1 and thumbnail width >= 64")
    cell_height = int(thumb_width * 0.78) + 44
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, path in enumerate(paths):
        x = (index % columns) * thumb_width
        y = (index // columns) * cell_height
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                image.thumbnail((thumb_width - 12, cell_height - 48))
            sheet.paste(image, (x + (thumb_width - image.width) // 2, y + 4))
            label = f"{index + 1}. {path.name}"
        except Exception as exc:  # keep the remaining corpus usable if one file is bad
            label = f"{index + 1}. [unreadable] {path.name}: {exc}"
        draw.text((x + 4, y + cell_height - 38), label[:100], fill="black", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    image_format = Image.registered_extensions().get(output.suffix.lower())
    if image_format is None:
        raise ValueError("contact-sheet output must use a supported image extension, e.g. .png")
    # Exclusive creation protects source images and all pre-existing outputs.
    with output.open("xb") as stream:
        sheet.save(stream, format=image_format)


def main(argv: Optional[Sequence[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="image file or directory to search")
    parser.add_argument("--query", default="", help="keywords matched against filenames and metadata")
    parser.add_argument("--pattern", default="", help="preferred metadata pattern, e.g. framework or pipeline")
    parser.add_argument("--metadata", type=Path, help="optional JSON metadata file")
    parser.add_argument("--limit", type=int, default=10, help="maximum candidates to print")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON instead of readable text")
    parser.add_argument("--contact-sheet", type=Path, help="optionally save a contact sheet of selected candidates")
    parser.add_argument("--columns", type=int, default=4, help="contact-sheet columns")
    parser.add_argument("--thumb-width", type=int, default=320, help="contact-sheet cell width in pixels")
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if not args.root.exists():
        parser.error(f"root does not exist: {args.root}")
    if args.metadata and not args.metadata.is_file():
        parser.error(f"metadata file does not exist: {args.metadata}")

    if args.contact_sheet and args.contact_sheet.exists():
        parser.error(f"refusing to overwrite existing contact sheet: {args.contact_sheet}")
    if args.columns < 1 or args.thumb_width < 64:
        parser.error("columns must be >= 1 and thumbnail width >= 64")
    try:
        rows = load_metadata(args.metadata)
    except (OSError, ValueError) as exc:
        parser.error(f"cannot read metadata: {exc}")
    index = metadata_index(rows)
    query_tokens = tokens(args.query)
    candidates: List[Dict[str, Any]] = []
    root = args.root.resolve()
    for path in image_files(root):
        row = resolve_row(path, root.parent if root.is_file() else root, index)
        value, reasons = score(path, row, query_tokens, args.pattern)
        if (query_tokens or args.pattern) and value == 0:
            continue
        candidates.append({"path": str(path.resolve()), "score": value, "match_reasons": reasons, "metadata": row})

    candidates.sort(key=lambda item: (
        -int(bool(args.pattern and item["metadata"] and norm(item["metadata"].get("pattern")) == norm(args.pattern))),
        -item["score"], item["path"].lower(),
    ))
    selected = candidates[: args.limit]
    contact_sheet = None
    if args.contact_sheet and selected:
        try:
            make_contact_sheet([Path(item["path"]) for item in selected], args.contact_sheet, args.columns, args.thumb_width)
            contact_sheet = str(args.contact_sheet.resolve())
        except RuntimeError as exc:
            print(f"Warning: {exc}; returning text candidates without a sheet.", file=sys.stderr)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))

    if args.as_json:
        print(json.dumps({"text_match_only": True, "results": selected, "contact_sheet": contact_sheet}, ensure_ascii=False, indent=2))
    else:
        print("Text-match candidate search only; inspect images before making visual claims.")
        print(f"Found {len(candidates)} image(s); showing {len(selected)} candidate(s).")
        for number, item in enumerate(selected, 1):
            print(f"{number}. {item['path']} [text-match={item['score']}]")
            if item["match_reasons"]:
                print("   " + ", ".join(item["match_reasons"]))
            row = item.get("metadata") or {}
            if row:
                details = [str(row.get(key)) for key in ("id", "title", "venue", "year", "pattern", "paper") if row.get(key) is not None]
                print("   " + " | ".join(details))
        if contact_sheet:
            print(f"Contact sheet: {contact_sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
