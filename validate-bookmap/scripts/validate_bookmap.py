#!/usr/bin/env python3
"""
validate_bookmap.py — DITA 1.3 bookmap validator

Usage:
    python validate_bookmap.py <file.ditamap>
    cat bookmap.ditamap | python validate_bookmap.py -

Output: JSON  →  { "is_valid": bool, "errors": [...], "warnings": [...] }
Exit code: 0 = valid, 1 = invalid
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Enforced DTD order: (title|booktitle)?, bookmeta?, frontmatter?,
#                      chapter*, part*, (appendices?|appendix*), backmatter?, reltable*
# We express this as ordered "phase" groups; each element maps to a phase index.
# An element appearing in a phase LOWER than the last seen phase is an order violation.
_PHASE: dict[str, int] = {
    "title":        0,
    "booktitle":    0,
    "bookmeta":     1,
    "frontmatter":  2,
    "chapter":      3,
    "part":         4,
    "appendices":   5,
    "appendix":     5,
    "backmatter":   6,
    "reltable":     7,
}

# Elements allowed anywhere (metadata, data, etc.) — don't enforce phase for these
_PHASE_EXEMPT = {"data", "topicmeta", "navref", "anchor"}

# Singleton elements at bookmap root level
_SINGLETONS = {"booktitle", "title", "bookmeta", "frontmatter", "backmatter", "appendices"}


def validate(xml_content: str, base_path: Path | None = None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {"is_valid": False,
                "errors": [_err("root", "well-formed", str(exc))],
                "warnings": []}

    if root.tag != "bookmap":
        errors.append(_err(root.tag, "root-element",
                           f"Root element must be <bookmap>, found <{root.tag}>"))
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    if not root.get("id"):
        warnings.append(_warn("bookmap", "id-recommended",
                               "<bookmap> should carry an @id attribute"))

    # Phase order + singleton enforcement
    last_phase = -1
    singleton_seen: set[str] = set()
    has_chapter_or_part = False
    has_appendices = False
    has_bare_appendix = False

    for child in root:
        tag = child.tag
        if tag in _PHASE_EXEMPT:
            continue

        phase = _PHASE.get(tag)
        if phase is None:
            continue  # unknown element — skip order check

        # Order violation
        if phase < last_phase:
            prev_tag = _phase_name(last_phase)
            errors.append(_err(tag, "element-order",
                               f"<{tag}> (phase {phase}) appears after "
                               f"{prev_tag} (phase {last_phase}); "
                               "bookmap element order is violated"))
        else:
            last_phase = max(last_phase, phase)

        # Singleton check
        if tag in _SINGLETONS:
            if tag in singleton_seen:
                errors.append(_err(tag, f"{tag}-singleton",
                                   f"<{tag}> must appear at most once in <bookmap>"))
            singleton_seen.add(tag)

        if tag in ("chapter", "part"):
            has_chapter_or_part = True
        if tag == "appendices":
            has_appendices = True
        if tag == "appendix":
            has_bare_appendix = True

        # Type-specific checks
        if tag == "booktitle":
            _check_booktitle(child, errors)
        elif tag == "chapter":
            _check_topicref_href(child, "chapter", errors, warnings, base_path)
        elif tag == "appendix":
            _check_topicref_href(child, "appendix", errors, warnings, base_path)
        elif tag == "part":
            _check_topicref_href(child, "part", errors, warnings, base_path)

    # At least one chapter or part
    if not has_chapter_or_part:
        errors.append(_err("bookmap", "chapter-required",
                           "<bookmap> must contain at least one <chapter> or <part>"))

    # appendices and bare appendix must not be mixed
    if has_appendices and has_bare_appendix:
        errors.append(_err("bookmap", "appendices-appendix-mixed",
                           "<appendices> and bare <appendix> elements must not be mixed; "
                           "use either <appendices> (wrapper) or bare <appendix> elements"))

    return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _check_booktitle(booktitle: ET.Element, errors: list) -> None:
    if booktitle.find("mainbooktitle") is not None:
        pass  # present — good
    else:
        errors.append(_err("booktitle", "mainbooktitle-required",
                           "<booktitle> must contain a <mainbooktitle> child"))


def _check_topicref_href(el: ET.Element, tag: str,
                         errors: list, warnings: list,
                         base_path: Path | None) -> None:
    href = el.get("href")
    keyref = el.get("keyref")
    if not href and not keyref:
        errors.append(_err(tag, "href-or-keyref-required",
                           f"<{tag}> must have @href or @keyref"))
        return
    if href and base_path:
        file_part = href.split("#")[0]
        if file_part:
            target = (base_path / file_part).resolve()
            if not target.exists():
                warnings.append(_warn(tag, "broken-href",
                                       f"@href='{href}' does not resolve to an existing file"))


def _phase_name(phase: int) -> str:
    names = {0: "title/booktitle", 1: "bookmeta", 2: "frontmatter",
             3: "chapter", 4: "part", 5: "appendix/appendices",
             6: "backmatter", 7: "reltable"}
    return names.get(phase, f"phase {phase}")


def _err(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


def _warn(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_bookmap.py <file.ditamap | ->", file=sys.stderr)
        sys.exit(2)

    path_arg = sys.argv[1]
    if path_arg == "-":
        xml_content = sys.stdin.read()
        base_path = None
    else:
        p = Path(path_arg)
        xml_content = p.read_text(encoding="utf-8")
        base_path = p.parent

    result = validate(xml_content, base_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["is_valid"] else 1)


if __name__ == "__main__":
    main()
