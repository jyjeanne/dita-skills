#!/usr/bin/env python3
"""
extract_pdf.py — Stage 1: Extract structured content from a PDF file.

Requires:  pip install pdfplumber

Usage:
    python extract_pdf.py <file.pdf>
    python extract_pdf.py <file.pdf> --debug

Output: JSON written to stdout
  {
    "source":   "<abs-path>",
    "title":    "<document title>",
    "pages":    <int>,
    "sections": [
      {
        "level":   <int 1-4>,
        "title":   "<heading text>",
        "content": [
          {"type": "paragraph", "text": "..."},
          {"type": "list",      "ordered": bool, "items": ["..."]},
          {"type": "table",     "headers": ["..."], "rows": [["..."]]}
        ],
        "subsections": [...]
      }
    ]
  }

Exit code: 0 = success, 1 = error
"""

import json
import sys
import re
import argparse
from pathlib import Path
from collections import Counter

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


# ---------------------------------------------------------------------------
# Font-size heuristics
# ---------------------------------------------------------------------------

def _most_common_size(words: list) -> float:
    """Return the modal font size — considered the body text size."""
    sizes = [round(w.get("size", 12), 1) for w in words if w.get("size")]
    if not sizes:
        return 12.0
    return Counter(sizes).most_common(1)[0][0]


def _heading_level(size: float, body_size: float, size_map: dict) -> int | None:
    """Return heading level 1-4 or None (body text)."""
    ratio = size / body_size if body_size else 1.0
    if ratio < 1.15:
        return None
    # Map distinct sizes above body to levels in descending order
    if size in size_map:
        return size_map[size]
    return None


def _build_size_map(words: list, body_size: float) -> dict:
    """Map each heading font size → level (1 = largest)."""
    heading_sizes = sorted(
        {round(w.get("size", 0), 1) for w in words
         if round(w.get("size", 0), 1) > body_size * 1.14},
        reverse=True,
    )
    return {sz: (i + 1) for i, sz in enumerate(heading_sizes[:4])}


# ---------------------------------------------------------------------------
# Text grouping helpers
# ---------------------------------------------------------------------------

_ORDERED_LIST_RE = re.compile(r"^\s*(\d+[\.\)])\s+")
_UNORDERED_LIST_RE = re.compile(r"^\s*[•·\-\*]\s+")


def _classify_block(text: str) -> str:
    """Return 'ordered_list', 'unordered_list', or 'paragraph'."""
    if _ORDERED_LIST_RE.match(text):
        return "ordered_list"
    if _UNORDERED_LIST_RE.match(text):
        return "unordered_list"
    return "paragraph"


def _merge_list_items(lines: list[str], ordered: bool) -> dict:
    """Merge consecutive list lines into a single list block."""
    pattern = _ORDERED_LIST_RE if ordered else _UNORDERED_LIST_RE
    items = [pattern.sub("", line).strip() for line in lines]
    return {"type": "list", "ordered": ordered, "items": [i for i in items if i]}


def _group_lines_into_blocks(lines: list[str]) -> list[dict]:
    """Group raw text lines into paragraph / list content blocks."""
    blocks: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        kind = _classify_block(line)
        if kind in ("ordered_list", "unordered_list"):
            ordered = kind == "ordered_list"
            group = [line]
            j = i + 1
            while j < len(lines) and _classify_block(lines[j]) == kind:
                group.append(lines[j].strip())
                j += 1
            blocks.append(_merge_list_items(group, ordered))
            i = j
        else:
            # Accumulate paragraph lines until blank line or heading detected
            para_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() and _classify_block(lines[j]) == "paragraph":
                para_lines.append(lines[j].strip())
                j += 1
            text = " ".join(para_lines)
            if text:
                blocks.append({"type": "paragraph", "text": text})
            i = j
    return blocks


def _table_to_block(table: list[list]) -> dict | None:
    """Convert a pdfplumber table (list of rows) to a structured block."""
    rows = [[cell or "" for cell in row] for row in table if any(row)]
    if not rows:
        return None
    headers = rows[0]
    data_rows = rows[1:]
    return {"type": "table", "headers": headers, "rows": data_rows}


# ---------------------------------------------------------------------------
# Section tree builder
# ---------------------------------------------------------------------------

def _new_section(level: int, title: str) -> dict:
    return {"level": level, "title": title, "content": [], "subsections": []}


def _insert_section(stack: list[dict], section: dict) -> None:
    """Insert section into the tree, maintaining the stack of open parents."""
    target_level = section["level"]
    # Pop until we find an ancestor at a lower level
    while len(stack) > 1 and stack[-1]["level"] >= target_level:
        stack.pop()
    if len(stack) == 1:
        # root virtual node
        stack[0]["subsections"].append(section)
    else:
        stack[-1]["subsections"].append(section)
    stack.append(section)


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract(pdf_path: str, debug: bool = False) -> dict:
    """Extract structured content from a PDF. Returns document dict."""
    if not _HAS_PDFPLUMBER:
        raise ImportError(
            "pdfplumber is required: pip install pdfplumber"
        )

    path = Path(pdf_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    root: dict = {"level": 0, "title": "__root__", "content": [], "subsections": []}
    stack = [root]
    all_words: list = []
    page_count = 0
    doc_title = path.stem  # fallback title

    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)

        # Collect all words for font-size analysis
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size", "fontname"])
            all_words.extend(words)

        body_size = _most_common_size(all_words)
        size_map = _build_size_map(all_words, body_size)
        if debug:
            print(f"[DEBUG] body_size={body_size} size_map={size_map}", file=sys.stderr)

        current_section = root
        pending_lines: list[str] = []

        for page in pdf.pages:
            tables = page.extract_tables()

            words_by_line: dict = {}  # y0 -> list of words
            for word in page.extract_words(extra_attrs=["size", "fontname"]):
                y = round(word["top"], 1)
                words_by_line.setdefault(y, []).append(word)

            for y in sorted(words_by_line):
                line_words = words_by_line[y]
                avg_size = sum(w.get("size", body_size) for w in line_words) / len(line_words)
                text = " ".join(w["text"] for w in line_words).strip()
                if not text:
                    continue

                level = _heading_level(round(avg_size, 1), body_size, size_map)

                if level is not None:
                    # Flush pending lines into current section
                    if pending_lines:
                        current_section["content"].extend(
                            _group_lines_into_blocks(pending_lines)
                        )
                        pending_lines = []

                    section = _new_section(level, text)
                    if level == 1 and stack[0]["subsections"] == []:
                        doc_title = text  # first h1 becomes document title
                    _insert_section(stack, section)
                    current_section = section
                else:
                    pending_lines.append(text)

            # Attach tables to current_section (last section active on this page).
            # pdfplumber's extract_tables() returns 2-D arrays with no y-coordinates,
            # so precise per-section placement requires the Table objects — kept as
            # best-effort assignment for now.
            for raw_table in tables:
                block = _table_to_block(raw_table)
                if block:
                    current_section["content"].append(block)

        # Flush remaining lines
        if pending_lines:
            current_section["content"].extend(
                _group_lines_into_blocks(pending_lines)
            )

    # If no headings found, wrap everything as a single flat section
    sections = root["subsections"]
    if not sections and root["content"]:
        sections = [_new_section(1, doc_title)]
        sections[0]["content"] = root["content"]
    elif sections and root["content"]:
        # Pre-first-heading content (preamble) — prepend to the first section
        sections[0]["content"] = root["content"] + sections[0]["content"]

    return {
        "source": str(path),
        "title":  doc_title,
        "pages":  page_count,
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract structured content from a PDF.")
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    try:
        result = extract(args.pdf, debug=args.debug)
    except ImportError as e:
        print(json.dumps({"error": str(e), "hint": "pip install pdfplumber"}))
        sys.exit(1)
    except (FileNotFoundError, OSError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
