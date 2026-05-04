#!/usr/bin/env python3
"""
chunk_to_dita.py — Stage 2: Convert extracted PDF structure into DITA 1.3 topics + map.

Usage:
    python chunk_to_dita.py <extracted.json> <output_dir>
    python chunk_to_dita.py <extracted.json> <output_dir> --map-title "My Guide"

Output:
    <output_dir>/
        root.ditamap
        topics/
            <slug>.dita   (one per section)

Exit code: 0 = success, 1 = error
"""

import json
import sys
import re
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Topic-type heuristics
# ---------------------------------------------------------------------------

_TASK_TITLE_RE = re.compile(
    r"\b(how\s+to|configure|install|create|set\s+up|enable|disable|deploy|"
    r"add|remove|update|upgrade|migrate|run|start|stop|build|use|connect|"
    r"register|log\s*in|sign\s*in|reset|change|modify)\b",
    re.IGNORECASE,
)
_REFERENCE_TITLE_RE = re.compile(
    r"\b(reference|parameters|settings|options|properties|attributes|"
    r"commands|api|syntax|specifications?|values?|defaults?|glossary)\b",
    re.IGNORECASE,
)


def _detect_topic_type(section: dict) -> str:
    """Return 'task', 'reference', or 'concept' based on content heuristics."""
    title = section.get("title", "")
    content = section.get("content", [])

    if _REFERENCE_TITLE_RE.search(title):
        return "reference"

    if _TASK_TITLE_RE.search(title):
        return "task"

    # Count ordered-list items across all content blocks
    ordered_items = sum(
        len(b["items"]) for b in content
        if b.get("type") == "list" and b.get("ordered")
    )
    if ordered_items >= 3:
        return "task"

    # Table with Name/Value/Description pattern → reference
    for block in content:
        if block.get("type") == "table":
            headers_lower = [h.lower() for h in block.get("headers", [])]
            if any(h in headers_lower for h in ("name", "parameter", "property", "attribute", "command")):
                return "reference"

    return "concept"


# ---------------------------------------------------------------------------
# Slug / ID generation
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert a title to a lowercase-hyphen slug suitable for filenames and IDs."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:60] or "topic"


def _unique_id(base: str, used: set) -> str:
    """Return a unique slug, appending a counter if necessary."""
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# DITA XML generation
# ---------------------------------------------------------------------------

_DOCTYPE_MAP = {
    "concept":   '<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">',
    "task":      '<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">',
    "reference": '<!DOCTYPE reference PUBLIC "-//OASIS//DTD DITA Reference//EN" "reference.dtd">',
}

_BODY_TAG = {
    "concept":   "conbody",
    "task":      "taskbody",
    "reference": "refbody",
}


def _text_to_shortdesc(content: list[dict]) -> str:
    """Extract first-sentence summary from first paragraph."""
    for block in content:
        if block.get("type") == "paragraph":
            text = block["text"]
            # Take up to first sentence ending or 148 words
            sentences = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
            first = sentences[0].strip()
            words = first.split()
            if len(words) > 50:
                first = " ".join(words[:50]) + "…"
            return first
    return ""


def _add_paragraph(parent: ET.Element, text: str) -> None:
    p = ET.SubElement(parent, "p")
    p.text = text


def _add_list(parent: ET.Element, block: dict) -> None:
    tag = "ol" if block.get("ordered") else "ul"
    lst = ET.SubElement(parent, tag)
    for item in block.get("items", []):
        li = ET.SubElement(lst, "li")
        li.text = item


def _add_table(parent: ET.Element, block: dict) -> None:
    headers = block.get("headers", [])
    rows = block.get("rows", [])
    if not headers and not rows:
        return
    table = ET.SubElement(parent, "simpletable")
    if headers:
        sthead = ET.SubElement(table, "sthead")
        for h in headers:
            stentry = ET.SubElement(sthead, "stentry")
            stentry.text = h
    for row in rows:
        strow = ET.SubElement(table, "strow")
        for cell in row:
            stentry = ET.SubElement(strow, "stentry")
            stentry.text = cell


def _fill_body(body: ET.Element, topic_type: str, content: list[dict]) -> None:
    """Populate a topic body element with content blocks."""
    if topic_type == "task":
        steps = ET.SubElement(body, "steps")
        pre_steps_buffer: list[dict] = []
        post_steps_buffer: list[dict] = []
        steps_written = False

        def _flush_buffer_into(parent: ET.Element, buf: list[dict]) -> None:
            for b in buf:
                if b["type"] == "paragraph":
                    _add_paragraph(parent, b["text"])
                elif b["type"] == "list":
                    _add_list(parent, b)
                elif b["type"] == "table":
                    _add_table(parent, b)
            buf.clear()

        for block in content:
            if block.get("type") == "list" and block.get("ordered"):
                steps_written = True
                for item in block.get("items", []):
                    step = ET.SubElement(steps, "step")
                    cmd = ET.SubElement(step, "cmd")
                    cmd.text = item
            else:
                if steps_written:
                    post_steps_buffer.append(block)
                else:
                    pre_steps_buffer.append(block)

        # Flush pre-step content into <context> (valid taskbody child)
        if pre_steps_buffer:
            context_el = ET.Element("context")
            _flush_buffer_into(context_el, pre_steps_buffer)
            # Insert <context> before <steps>
            steps_idx = list(body).index(steps)
            body.insert(steps_idx, context_el)

        # Flush post-step content into <result> (valid taskbody child)
        if post_steps_buffer:
            result_el = ET.SubElement(body, "result")
            _flush_buffer_into(result_el, post_steps_buffer)

        # Remove empty <steps>
        if not list(steps):
            body.remove(steps)
    else:
        for block in content:
            if block.get("type") == "paragraph":
                _add_paragraph(body, block["text"])
            elif block.get("type") == "list":
                _add_list(body, block)
            elif block.get("type") == "table":
                _add_table(body, block)


def _generate_topic(section: dict, topic_id: str, topic_type: str) -> str:
    """Generate a complete DITA 1.3 topic as an XML string."""
    root = ET.Element(topic_type)
    root.set("id", topic_id)
    root.set("xml:lang", "en-US")

    title_el = ET.SubElement(root, "title")
    title_el.text = section["title"]

    shortdesc_text = _text_to_shortdesc(section["content"])
    if shortdesc_text:
        shortdesc_el = ET.SubElement(root, "shortdesc")
        shortdesc_el.text = shortdesc_text

    body_tag = _BODY_TAG[topic_type]
    body = ET.SubElement(root, body_tag)
    _fill_body(body, topic_type, section["content"])

    # Recurse: subsections become nested <section> or child topics
    # For simplicity: add subsections as <section> blocks inside the body
    for sub in section.get("subsections", []):
        sec_el = ET.SubElement(body, "section")
        sec_title = ET.SubElement(sec_el, "title")
        sec_title.text = sub["title"]
        for block in sub.get("content", []):
            if block.get("type") == "paragraph":
                _add_paragraph(sec_el, block["text"])
            elif block.get("type") == "list":
                _add_list(sec_el, block)
            elif block.get("type") == "table":
                _add_table(sec_el, block)

    # Pretty print
    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)

    doctype = _DOCTYPE_MAP[topic_type]
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{doctype}\n{xml_str}\n'


# ---------------------------------------------------------------------------
# DITA map generation
# ---------------------------------------------------------------------------

def _generate_map(title: str, topic_entries: list[dict]) -> str:
    """Generate a DITA 1.3 map as an XML string.

    topic_entries: list of {"href": "...", "title": "...", "navtitle": "..."}
    """
    root = ET.Element("map")
    root.set("xml:lang", "en-US")

    title_el = ET.SubElement(root, "title")
    title_el.text = title

    for entry in topic_entries:
        topicref = ET.SubElement(root, "topicref")
        topicref.set("href", entry["href"])
        topicref.set("navtitle", entry["navtitle"])

    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
        f'{xml_str}\n'
    )


# ---------------------------------------------------------------------------
# Main chunking logic
# ---------------------------------------------------------------------------

def chunk(extracted: dict, output_dir: Path, map_title: str | None = None) -> dict:
    """Convert extracted document structure into DITA files.

    Returns a summary dict with generated file paths.
    """
    topics_dir = output_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)

    used_ids: set = set()
    topic_entries: list[dict] = []
    generated: list[dict] = []

    def _process_section(section: dict) -> None:
        title = section.get("title", "Untitled")
        slug = _slugify(title)
        topic_id = _unique_id(slug, used_ids)
        topic_type = _detect_topic_type(section)
        filename = f"{topic_id}.dita"
        rel_path = f"topics/{filename}"
        abs_path = topics_dir / filename

        xml_content = _generate_topic(section, topic_id, topic_type)
        abs_path.write_text(xml_content, encoding="utf-8")

        topic_entries.append({
            "href":     rel_path,
            "navtitle": title,
        })
        generated.append({
            "file":       str(abs_path),
            "id":         topic_id,
            "title":      title,
            "topic_type": topic_type,
        })
        # Subsections are already inlined as <section> blocks inside the topic
        # by _generate_topic; do NOT recurse here or they would be duplicated.

    for section in extracted.get("sections", []):
        _process_section(section)

    # Generate root ditamap
    title = map_title or extracted.get("title", "Untitled Guide")
    map_xml = _generate_map(title, topic_entries)
    map_path = output_dir / "root.ditamap"
    map_path.write_text(map_xml, encoding="utf-8")

    return {
        "map":    str(map_path),
        "topics": generated,
        "total":  len(generated),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Chunk extracted PDF structure into DITA topics.")
    parser.add_argument("extracted_json", help="Path to extracted.json from extract_pdf.py")
    parser.add_argument("output_dir", help="Directory to write DITA files")
    parser.add_argument("--map-title", default=None, help="Override the root map title")
    args = parser.parse_args()

    json_path = Path(args.extracted_json)
    if not json_path.exists():
        print(json.dumps({"error": f"File not found: {json_path}"}))
        sys.exit(1)

    extracted = json.loads(json_path.read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = chunk(extracted, output_dir, map_title=args.map_title)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
