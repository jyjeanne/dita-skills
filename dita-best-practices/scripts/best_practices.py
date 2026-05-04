#!/usr/bin/env python3
"""
best_practices.py — DITA 1.3 best-practices analyzer

Usage:
    python best_practices.py path/to/topic.dita
    cat topic.dita | python best_practices.py -

Output: JSON  →  { "file_type": str, "findings": [...] }
Exit code: 0 = no errors, 1 = errors found (warnings don't affect exit code)
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Thresholds
_MAX_SHORTDESC_WORDS = 50
_MAX_BODY_WORDS = 300
_MAX_BODY_BLOCKS = 50
_MAX_STEPS = 10
_MAX_NESTING_DEPTH = 3
_MIN_REUSE_WORDS = 5        # minimum words in a paragraph to consider for reuse
_SIMILARITY_THRESHOLD = 0.85  # Jaccard similarity above which paragraphs are flagged

# Block-level elements counted for topic-size check
_BLOCK_TAGS = {
    "p", "ul", "ol", "dl", "table", "simpletable", "fig",
    "pre", "codeblock", "note", "section", "example", "msgblock",
}

# Topic type detection
_TOPIC_TYPES = {
    "topic", "concept", "task", "reference",
    "troubleshooting", "glossentry", "map", "bookmap",
}

_BODY_TAGS = {
    "topic": "body", "concept": "conbody", "task": "taskbody",
    "reference": "refbody", "troubleshooting": "troublebody",
}

# Elements that benefit from an @id (for conref targeting)
_REUSABLE_ELEMENTS = {"section", "fig", "table", "simpletable", "note", "example"}


def analyze(xml_content: str) -> dict:
    findings: list[dict] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {"file_type": "unknown",
                "findings": [_finding("error", "parse", "root", str(exc))]}

    file_type = root.tag if root.tag in _TOPIC_TYPES else "unknown"

    # --- shortdesc -----------------------------------------------------------
    _check_shortdesc(root, file_type, findings)

    # --- body size -----------------------------------------------------------
    body_tag = _BODY_TAGS.get(file_type)
    if body_tag:
        body = root.find(body_tag)
        if body is not None:
            _check_body_size(body, findings)
            _check_empty_elements(body, findings)
            _check_reusable_ids(body, findings)

    # --- task-specific -------------------------------------------------------
    if file_type == "task":
        _check_task_steps(root, findings)

    # --- nesting depth -------------------------------------------------------
    _check_nesting_depth(root, findings)

    # --- duplicate paragraph content (reuse candidates) ----------------------
    _check_duplicate_paragraphs(root, findings)

    # --- conref chain detection ----------------------------------------------
    _check_conref_chains(root, findings)

    # --- keyref vs href balance ----------------------------------------------
    _check_href_without_keys(root, file_type, findings)

    error_count = sum(1 for f in findings if f["severity"] == "error")
    return {"file_type": file_type, "findings": findings, "_error_count": error_count}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_shortdesc(root: ET.Element, file_type: str, findings: list) -> None:
    shortdesc = root.find("shortdesc")
    if shortdesc is None:
        if file_type not in ("map", "bookmap", "glossentry"):
            findings.append(_finding("warning", "shortdesc", "shortdesc",
                                      "<shortdesc> is missing; recommended for all topics"))
        return

    for child in shortdesc:
        if child.tag in _BLOCK_TAGS:
            findings.append(_finding("warning", "shortdesc", "shortdesc",
                                      f"<shortdesc> contains block element <{child.tag}>; "
                                      "use inline elements only"))

    text = " ".join(shortdesc.itertext()).strip()
    words = len(text.split())
    if words > _MAX_SHORTDESC_WORDS:
        findings.append(_finding("warning", "shortdesc", "shortdesc",
                                  f"<shortdesc> is {words} words; "
                                  f"recommended maximum is {_MAX_SHORTDESC_WORDS}"))
    elif words == 0:
        findings.append(_finding("warning", "shortdesc", "shortdesc",
                                  "<shortdesc> is present but empty"))


def _check_body_size(body: ET.Element, findings: list) -> None:
    all_text = " ".join(body.itertext()).strip()
    word_count = len(all_text.split())
    block_count = sum(1 for el in body.iter() if el.tag in _BLOCK_TAGS)

    if word_count > _MAX_BODY_WORDS:
        findings.append(_finding("warning", "topic-size", body.tag,
                                  f"Body contains ~{word_count} words; "
                                  f"consider splitting (recommended max: {_MAX_BODY_WORDS})"))
    if block_count > _MAX_BODY_BLOCKS:
        findings.append(_finding("warning", "topic-size", body.tag,
                                  f"Body contains {block_count} block elements; "
                                  f"consider splitting (recommended max: {_MAX_BODY_BLOCKS})"))


def _check_empty_elements(body: ET.Element, findings: list) -> None:
    for el in body.iter():
        if el.tag in ("cmd", "title", "shortdesc", "p"):
            text = "".join(el.itertext()).strip()
            if not text and len(list(el)) == 0:
                findings.append(_finding("warning", "empty", el.tag,
                                          f"Empty <{el.tag}> element found"))


def _check_reusable_ids(body: ET.Element, findings: list) -> None:
    for el in body.iter():
        if el.tag in _REUSABLE_ELEMENTS and not el.get("id"):
            findings.append(_finding("info", "ids", el.tag,
                                      f"<{el.tag}> has no @id; "
                                      "add one to make it reusable as a conref target"))


def _check_task_steps(root: ET.Element, findings: list) -> None:
    taskbody = root.find("taskbody")
    if taskbody is None:
        return
    for steps_tag in ("steps", "steps-unordered"):
        steps_el = taskbody.find(steps_tag)
        if steps_el is not None:
            count = len(steps_el.findall("step"))
            if count > _MAX_STEPS:
                findings.append(_finding("warning", "steps", steps_tag,
                                          f"<{steps_tag}> has {count} steps; "
                                          f"consider splitting the task "
                                          f"(recommended max: {_MAX_STEPS})"))


def _check_nesting_depth(root: ET.Element, findings: list) -> None:
    def _depth(el: ET.Element, tag: str, current: int) -> int:
        return max(
            (_depth(child, tag, current + (1 if child.tag == tag else 0))
             for child in el),
            default=current,
        )

    for tracked_tag in ("section", "topicref", "step"):
        depth = _depth(root, tracked_tag, 0)
        if depth > _MAX_NESTING_DEPTH:
            findings.append(_finding("warning", "nesting", tracked_tag,
                                      f"<{tracked_tag}> is nested {depth} levels deep; "
                                      f"recommended maximum is {_MAX_NESTING_DEPTH}"))


def _check_duplicate_paragraphs(root: ET.Element, findings: list) -> None:
    """Flag paragraph pairs with high textual similarity (reuse candidates)."""
    paragraphs: list[tuple[str, set[str]]] = []
    for p in root.iter("p"):
        text = " ".join(p.itertext()).strip()
        words = text.split()
        if len(words) >= _MIN_REUSE_WORDS:
            paragraphs.append((text, set(words)))

    flagged: set[int] = set()
    for i in range(len(paragraphs)):
        for j in range(i + 1, len(paragraphs)):
            if i in flagged or j in flagged:
                continue
            a_set, b_set = paragraphs[i][1], paragraphs[j][1]
            union = a_set | b_set
            if not union:
                continue
            similarity = len(a_set & b_set) / len(union)
            if similarity >= _SIMILARITY_THRESHOLD:
                snippet = paragraphs[i][0][:60].replace("\n", " ")
                findings.append(_finding("info", "reuse", "p",
                                          f"Near-duplicate paragraph detected "
                                          f"(similarity {similarity:.0%}): \"{snippet}…\" — "
                                          "consider extracting to a conref library"))
                flagged.add(i)
                flagged.add(j)


def _check_conref_chains(root: ET.Element, findings: list) -> None:
    """Detect @conref on elements that are themselves the target of a conref (basic check)."""
    ids_with_conref: set[str] = set()
    for el in root.iter():
        if el.get("conref") and el.get("id"):
            ids_with_conref.add(el.get("id", ""))

    for el in root.iter():
        conref = el.get("conref", "")
        if "#" in conref:
            element_id = conref.split("#")[-1].split("/")[-1]
            if element_id in ids_with_conref:
                findings.append(_finding("error", "conref", el.tag,
                                          f"@conref='{conref}' points to an element "
                                          f"(#{element_id}) that itself uses @conref — "
                                          "chained conrefs are prohibited"))


def _check_href_without_keys(root: ET.Element, file_type: str,
                              findings: list) -> None:
    """Warn when <topicref href="..."> has no @keys (maps only)."""
    if file_type not in ("map", "bookmap"):
        return
    for el in root.iter("topicref"):
        if el.get("href") and not el.get("keys") and not el.get("keyref"):
            href = el.get("href", "")
            findings.append(_finding("info", "reuse", "topicref",
                                      f"<topicref href='{href}'> has no @keys; "
                                      "add a key definition to enable keyref-based linking"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(severity: str, category: str, element: str, message: str) -> dict:
    return {"severity": severity, "category": category,
            "element": element, "message": message}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: best_practices.py <file.dita | ->", file=sys.stderr)
        sys.exit(2)

    path_arg = sys.argv[1]
    xml_content = (sys.stdin.read() if path_arg == "-"
                   else Path(path_arg).read_text(encoding="utf-8"))

    result = analyze(xml_content)
    error_count = result.pop("_error_count", 0)
    print(json.dumps(result, indent=2))
    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
