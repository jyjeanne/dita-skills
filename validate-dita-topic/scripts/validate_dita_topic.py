#!/usr/bin/env python3
"""
validate_dita_topic.py — DITA 1.3 topic validator

Usage:
    python validate_dita_topic.py <file.dita> [topic_type]
    cat topic.dita | python validate_dita_topic.py -

topic_type: topic | concept | task | reference | troubleshooting | glossentry
            (auto-detected from root element if omitted)

Output: JSON  →  { "is_valid": bool, "errors": [...], "warnings": [...] }
Exit code: 0 = valid, 1 = invalid / parse error
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants derived from dtd/technicalContent/dtd/*.mod
# ---------------------------------------------------------------------------

BODY_ELEMENTS: dict[str, str | None] = {
    "topic":           "body",
    "concept":         "conbody",
    "task":            "taskbody",
    "reference":       "refbody",
    "troubleshooting": "troublebody",
    "glossentry":      None,   # uses glossterm + glossdef instead of a body
}

# Elements that are block-level and must not appear inside <shortdesc>
_BLOCK_ELEMENTS = {
    "p", "ul", "ol", "dl", "table", "simpletable",
    "fig", "pre", "codeblock", "note", "section", "example",
}

# taskbody singleton elements (each must appear at most once)
_TASKBODY_SINGLETONS = ("prereq", "context", "result", "tasktroubleshooting", "postreq")

# refbody elements exclusive to reference topics
_REFBODY_EXCLUSIVE = {"refsyn", "properties", "refbodydiv", "prophead", "property"}

# conbody elements exclusive to concept topics
_CONBODY_EXCLUSIVE = {"conbodydiv"}

# troublebody elements exclusive to troubleshooting topics
_TROUBLEBODY_EXCLUSIVE = {"troubleSolution", "condition", "cause", "remedy", "responsibleParty"}

# taskbody elements exclusive to task topics (must not appear in concept/reference)
_TASK_EXCLUSIVE = {
    # taskbody direct children
    "prereq", "context", "result", "tasktroubleshooting", "postreq",
    # steps containers
    "steps", "steps-unordered", "steps-informal",
    # step and its content
    "step", "cmd", "substep", "substeps",
    "info", "tutorialinfo", "stepxmp", "stepresult", "steptroubleshooting",
    # choice table
    "choices", "choice",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def validate(xml_content: str, topic_type: str | None = None) -> dict:
    """Validate *xml_content* as a DITA 1.3 topic.

    Args:
        xml_content: Raw XML string.
        topic_type:  Expected root element tag.  Auto-detected when ``None``.

    Returns:
        ``{"is_valid": bool, "errors": list, "warnings": list}``
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    # --- XML well-formedness -------------------------------------------------
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {
            "is_valid": False,
            "errors": [_err("root", "well-formed", str(exc))],
            "warnings": [],
        }

    detected_type = root.tag if root.tag in BODY_ELEMENTS else None

    # --- Topic type mismatch -------------------------------------------------
    if topic_type and detected_type != topic_type:
        errors.append(_err(
            root.tag, "root-element",
            f"Expected <{topic_type}> but found <{root.tag}>",
        ))

    effective_type: str | None = topic_type or detected_type
    if not effective_type:
        errors.append(_err(root.tag, "unknown-type", f"Unknown DITA topic type: <{root.tag}>"))
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    # --- @id required on root ------------------------------------------------
    if not root.get("id"):
        errors.append(_err(root.tag, "id-required",
                           f"Root element <{root.tag}> must carry a non-empty @id attribute"))

    # --- <title> must be first child -----------------------------------------
    if effective_type != "glossentry":
        children = list(root)
        if not children or children[0].tag != "title":
            errors.append(_err(root.tag, "title-required",
                               "<title> must be the first child of the root element"))

    # --- <shortdesc> quality -------------------------------------------------
    if effective_type != "glossentry":
        _check_shortdesc(root, warnings)

    # --- prolog / related-links order ----------------------------------------
    _check_element_order(root, effective_type, errors)

    # --- Body element and type-specific rules --------------------------------
    if effective_type == "glossentry":
        _validate_glossentry(root, errors, warnings)
    else:
        body_tag = BODY_ELEMENTS[effective_type]
        body = root.find(body_tag)  # type: ignore[arg-type]
        if body is None:
            errors.append(_err(root.tag, "body-required",
                               f"<{body_tag}> is required for topic type '{effective_type}'"))
        else:
            if effective_type == "task":
                _validate_taskbody(body, errors, warnings)
            elif effective_type == "troubleshooting":
                _validate_troublebody(body, errors, warnings)
            elif effective_type == "reference":
                _validate_refbody(body, errors, warnings)
            elif effective_type == "concept":
                _validate_conbody(body, errors, warnings)

    # Disallow exclusive elements from foreign types (applies to all topic types)
    _check_foreign_elements(root, effective_type, errors)

    # --- Duplicate @id values ------------------------------------------------
    _check_duplicate_ids(root, errors)

    # --- @conref format ------------------------------------------------------
    _check_conref_format(root, errors)

    # --- @keyref presence (warn if keys undefined — best effort) -------------
    _check_keyref_presence(root, warnings)

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Type-specific validators
# ---------------------------------------------------------------------------

def _validate_taskbody(taskbody: ET.Element, errors: list, warnings: list) -> None:
    """Validate <taskbody> per strict taskbody constraint (task.dtd)."""

    # Steps: one of steps | steps-unordered | steps-informal
    steps_el = taskbody.find("steps")
    if steps_el is None:
        steps_el = taskbody.find("steps-unordered")
    if steps_el is None:
        steps_el = taskbody.find("steps-informal")
    if steps_el is None:
        warnings.append(_warn("taskbody", "steps-recommended",
                               "No <steps>, <steps-unordered>, or <steps-informal> found in <taskbody>"))
    elif steps_el.tag in ("steps", "steps-unordered"):
        step_list = steps_el.findall("step")
        if not step_list:
            errors.append(_err(steps_el.tag, "step-required",
                               f"<{steps_el.tag}> must contain at least one <step>"))
        if len(step_list) > 10:
            warnings.append(_warn(steps_el.tag, "step-count",
                                   f"<{steps_el.tag}> has {len(step_list)} steps; "
                                   "consider splitting the task (recommended max: 10)"))
        for i, step in enumerate(step_list, start=1):
            if step.find("cmd") is None:
                errors.append(_err("step", "cmd-required",
                                   f"<step> #{i} is missing its required <cmd> child"))

    # Singleton elements must appear at most once
    for tag in _TASKBODY_SINGLETONS:
        if len(taskbody.findall(tag)) > 1:
            errors.append(_err(tag, f"{tag}-singleton",
                               f"<{tag}> must appear at most once inside <taskbody>"))


def _validate_troublebody(troublebody: ET.Element, errors: list, warnings: list) -> None:
    """Validate <troublebody> per troubleshooting.mod."""

    # <condition> at most once
    if len(troublebody.findall("condition")) > 1:
        errors.append(_err("troublebody", "condition-singleton",
                           "<condition> must appear at most once in <troublebody>"))

    # At least one <troubleSolution>
    solutions = troublebody.findall("troubleSolution")
    if not solutions:
        errors.append(_err("troublebody", "troubleSolution-required",
                           "<troublebody> must contain at least one <troubleSolution>"))

    # Each <troubleSolution> may have cause* and remedy*; at least one is recommended
    for i, sol in enumerate(solutions, start=1):
        has_cause = sol.find("cause") is not None
        has_remedy = sol.find("remedy") is not None
        if not has_cause and not has_remedy:
            warnings.append(_warn("troubleSolution", "troubleSolution-empty",
                                   f"<troubleSolution> #{i} has neither <cause> nor <remedy>"))


def _validate_refbody(refbody: ET.Element, errors: list, warnings: list) -> None:
    """Validate <refbody> per reference.mod."""

    for prop_table in refbody.findall(".//properties"):
        rows = prop_table.findall("property")
        for i, row in enumerate(rows, start=1):
            has_cell = any(
                row.find(cell) is not None
                for cell in ("proptype", "propvalue", "propdesc")
            )
            if not has_cell:
                warnings.append(_warn("property", "property-empty",
                                       f"<property> row #{i} has no <proptype>, <propvalue>, or <propdesc>"))


def _validate_conbody(conbody: ET.Element, errors: list, warnings: list) -> None:
    """Validate <conbody> per concept.mod."""

    # <section> children must not be siblings of <conbodydiv> at the same level
    has_section = conbody.find("section") is not None
    has_conbodydiv = conbody.find("conbodydiv") is not None
    if has_section and has_conbodydiv:
        warnings.append(_warn("conbody", "conbodydiv-section-mix",
                               "<conbody> mixes <section> and <conbodydiv> siblings; "
                               "prefer one grouping strategy for clarity"))


def _validate_glossentry(root: ET.Element, errors: list, warnings: list) -> None:
    """Validate <glossentry> per glossentry.mod."""

    if root.find("glossterm") is None:
        errors.append(_err("glossentry", "glossterm-required",
                           "<glossterm> is required in <glossentry>"))
    if root.find("glossdef") is None:
        errors.append(_err("glossentry", "glossdef-required",
                           "<glossdef> is required in <glossentry>"))

    # DTD content model: (glossterm, glossdef, ...) — glossterm must precede glossdef
    children_tags = [c.tag for c in root]
    if "glossterm" in children_tags and "glossdef" in children_tags:
        if children_tags.index("glossterm") > children_tags.index("glossdef"):
            errors.append(_err("glossentry", "glossterm-order",
                               "<glossterm> must precede <glossdef>"))


# ---------------------------------------------------------------------------
# Cross-cutting checks
# ---------------------------------------------------------------------------

def _check_shortdesc(root: ET.Element, warnings: list) -> None:
    shortdesc = root.find("shortdesc")
    if shortdesc is None:
        warnings.append(_warn(root.tag, "shortdesc-recommended",
                               "<shortdesc> is recommended for all topics"))
        return

    for child in shortdesc:
        if child.tag in _BLOCK_ELEMENTS:
            warnings.append(_warn("shortdesc", "shortdesc-no-blocks",
                                   f"<shortdesc> should not contain block element <{child.tag}>"))

    text = "".join(shortdesc.itertext()).strip()
    word_count = len(text.split())
    if word_count > 50:
        warnings.append(_warn("shortdesc", "shortdesc-length",
                               f"<shortdesc> is {word_count} words; recommended maximum is 50"))


def _check_element_order(root: ET.Element, topic_type: str, errors: list) -> None:
    """Check that prolog (if present) precedes the body, and related-links follows it."""

    tags = [child.tag for child in root]
    body_tag = BODY_ELEMENTS.get(topic_type)
    if not body_tag or body_tag not in tags:
        return

    body_idx = tags.index(body_tag)
    if "prolog" in tags and tags.index("prolog") > body_idx:
        errors.append(_err("prolog", "prolog-order",
                           "<prolog> must appear before the body element"))
    if "related-links" in tags and tags.index("related-links") < body_idx:
        errors.append(_err("related-links", "related-links-order",
                           "<related-links> must appear after the body element"))


def _check_foreign_elements(root: ET.Element, effective_type: str, errors: list) -> None:
    """Warn when an element exclusive to another topic type appears in this topic."""

    exclusive_map = {
        "task":            _REFBODY_EXCLUSIVE | _CONBODY_EXCLUSIVE | _TROUBLEBODY_EXCLUSIVE,
        "concept":         _REFBODY_EXCLUSIVE | _TROUBLEBODY_EXCLUSIVE | _TASK_EXCLUSIVE,
        "reference":       _CONBODY_EXCLUSIVE | _TROUBLEBODY_EXCLUSIVE | _TASK_EXCLUSIVE,
        "troubleshooting": _REFBODY_EXCLUSIVE | _CONBODY_EXCLUSIVE,
        "glossentry":      (_REFBODY_EXCLUSIVE | _CONBODY_EXCLUSIVE
                            | _TROUBLEBODY_EXCLUSIVE | _TASK_EXCLUSIVE),
    }
    forbidden = exclusive_map.get(effective_type, set())
    for el in root.iter():
        if el.tag in forbidden:
            errors.append(_err(el.tag, "foreign-element",
                               f"<{el.tag}> is not valid inside a <{effective_type}> topic"))


def _check_duplicate_ids(root: ET.Element, errors: list) -> None:
    seen: set[str] = set()
    for el in root.iter():
        el_id = el.get("id")
        if el_id:
            if el_id in seen:
                errors.append(_err(el.tag, "unique-id",
                                   f"Duplicate @id value '{el_id}' — IDs must be unique within a document"))
            else:
                seen.add(el_id)


def _check_conref_format(root: ET.Element, errors: list) -> None:
    """@conref must use file.dita#topicid/elementid format."""
    for el in root.iter():
        conref = el.get("conref")
        if conref is not None and "#" not in conref:
            errors.append(_err(el.tag, "conref-format",
                               f"@conref='{conref}' must include a '#' fragment "
                               "(e.g. library.dita#topic-id/element-id)"))


def _check_keyref_presence(root: ET.Element, warnings: list) -> None:
    """Warn on @keyref values — they cannot be resolved without map context."""
    for el in root.iter():
        keyref = el.get("keyref")
        if keyref:
            warnings.append(_warn(el.tag, "keyref-unverified",
                                   f"@keyref='{keyref}' cannot be resolved without a map context; "
                                   "verify the key is defined in the applicable ditamap"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(element: str, rule: str, message: str, line: int = 0) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": line}


def _warn(element: str, rule: str, message: str, line: int = 0) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": line}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_dita_topic.py <file.dita | -> [topic_type]", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    topic_type = sys.argv[2] if len(sys.argv) > 2 else None

    if path == "-":
        xml_content = sys.stdin.read()
    else:
        xml_content = Path(path).read_text(encoding="utf-8")

    result = validate(xml_content, topic_type)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["is_valid"] else 1)


if __name__ == "__main__":
    main()
