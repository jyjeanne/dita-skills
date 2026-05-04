#!/usr/bin/env python3
"""
generate_bookmap.py — DITA 1.3 bookmap template generator

Usage:
    python generate_bookmap.py <title> [id]
    python generate_bookmap.py <title> [id] \
        --chapters ch1.dita ch2.dita \
        --appendix appendixA.dita

Output: well-formed DITA 1.3 bookmap XML with correct DOCTYPE
"""

import argparse
import re
import sys


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return ("id-" + slug) if slug and slug[0].isdigit() else (slug or "generated-id")


def generate(title: str, book_id: str | None = None,
             chapters: list[str] | None = None,
             appendix: list[str] | None = None) -> str:
    bid = book_id or slugify(title)
    ch_list = chapters or ["{{FILL}}-chapter1.dita", "{{FILL}}-chapter2.dita"]
    app_list = appendix or ["{{FILL}}-appendixA.dita"]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE bookmap PUBLIC "-//OASIS//DTD DITA 1.3 BookMap//EN" "bookmap.dtd">',
        f'<bookmap id="{bid}">',
        "",
        "  <booktitle>",
        f"    <mainbooktitle>{title}</mainbooktitle>",
        "    <booktitlealt>{{FILL}}</booktitlealt>",
        "  </booktitle>",
        "",
        "  <bookmeta>",
        "    <publisherinformation>",
        "      <organization><name>{{FILL}}</name></organization>",
        "    </publisherinformation>",
        "    <bookid>",
        "      <isbn>{{FILL}}</isbn>",
        "      <edition>{{FILL}}</edition>",
        "    </bookid>",
        "    <bookchangehistory>",
        "      <reviewed><revisionid>1.0</revisionid></reviewed>",
        "    </bookchangehistory>",
        "  </bookmeta>",
        "",
        "  <frontmatter>",
        "    <toc/>",
        "    <figurelist/>",
        "    <tablelist/>",
        "  </frontmatter>",
        "",
    ]

    for href in ch_list:
        lines.append(f'  <chapter href="{href}"/>')

    lines.append("")
    for href in app_list:
        lines.append(f'  <appendix href="{href}"/>')

    lines += [
        "",
        "  <backmatter>",
        "    <amendments/>",
        "    <indexlist/>",
        "  </backmatter>",
        "",
        "</bookmap>",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a DITA 1.3 bookmap template")
    parser.add_argument("title", help="Book title")
    parser.add_argument("id", nargs="?", help="Bookmap @id (defaults to slugified title)")
    parser.add_argument("--chapters", nargs="+", metavar="FILE",
                        help="Chapter href values")
    parser.add_argument("--appendix", nargs="+", metavar="FILE",
                        help="Appendix href values")
    args = parser.parse_args()

    print(generate(args.title, args.id, args.chapters, args.appendix))


if __name__ == "__main__":
    main()
