#!/usr/bin/env python3
"""
generate_ditamap.py — DITA 1.3 map template generator

Usage:
    python generate_ditamap.py <title> [id]
    python generate_ditamap.py <title> [id] --topics file1.dita file2.dita ...

Output: well-formed DITA 1.3 map XML with correct DOCTYPE
"""

import argparse
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\-_]", "-", text.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return ("id-" + slug) if slug and slug[0].isdigit() else (slug or "generated-id")


def key_from_href(href: str) -> str:
    """Derive a key name from a file path (e.g. 'intro.dita' → 'key-intro')."""
    stem = Path(href).stem
    key = re.sub(r"[^a-zA-Z0-9\-]", "-", stem).strip("-")
    return f"key-{key}" if key else "key-topic"


def generate(title: str, map_id: str | None = None,
             topics: list[str] | None = None) -> str:
    mid = map_id or slugify(title)
    topic_list = topics or ["{{FILL}}.dita", "{{FILL}}.dita"]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA 1.3 Map//EN" "map.dtd">',
        f'<map id="{mid}">',
        f'  <title>{title}</title>',
        "",
        "  <!-- Key definitions -->",
    ]

    for href in topic_list:
        key = key_from_href(href)
        lines.append(f'  <keydef href="{href}" keys="{key}"/>')

    lines += ["", "  <!-- Topic references -->"]
    for href in topic_list:
        key = key_from_href(href)
        lines.append(f'  <topicref href="{href}" keys="{key}"/>')

    lines += [
        "",
        "  <!-- Relationship table (remove if not needed) -->",
        "  <reltable>",
        "    <relcolspec/>",
        "    <relcolspec/>",
    ]    # One relrow per pair of topics, or a single placeholder
    pairs = list(zip(topic_list[::2], topic_list[1::2]))
    if not pairs:
        pairs = [("{{FILL}}.dita", "{{FILL}}.dita")]
    for a, b in pairs:
        lines += [
            "    <relrow>",
            f'      <relcell><topicref href="{a}"/></relcell>',
            f'      <relcell><topicref href="{b}"/></relcell>',
            "    </relrow>",
        ]
    lines += ["  </reltable>", "</map>"]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a DITA 1.3 map template")
    parser.add_argument("title", help="Map title")
    parser.add_argument("id", nargs="?", help="Map @id (defaults to slugified title)")
    parser.add_argument("--topics", nargs="+", metavar="FILE",
                        help="Topic href values to include")
    args = parser.parse_args()

    print(generate(args.title, args.id, args.topics))


if __name__ == "__main__":
    main()
