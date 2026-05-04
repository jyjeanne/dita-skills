#!/usr/bin/env python3
"""
validate_ditamap.py — DITA 1.3 map validator

Usage:
    python validate_ditamap.py <file.ditamap>
    cat map.ditamap | python validate_ditamap.py -

Output: JSON  →  { "is_valid": bool, "errors": [...], "warnings": [...] }
Exit code: 0 = valid, 1 = invalid
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Valid @collection-type values (map.mod)
_COLLECTION_TYPES = {"unordered", "sequence", "choice", "family"}

# Elements that do NOT require href/keyref
_HREF_EXEMPT = {"navref", "anchor", "topicmeta", "keydef", "reltable",
                "relcolspec", "relrow", "relcell", "data", "mapref"}

# Maximum recommended topicref nesting depth
_MAX_DEPTH = 5


def validate(xml_content: str, base_path: Path | None = None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {"is_valid": False,
                "errors": [_err("root", "well-formed", str(exc))],
                "warnings": []}

    # Root element
    if root.tag != "map":
        errors.append(_err(root.tag, "root-element",
                           f"Root element must be <map>, found <{root.tag}>"))
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    if not root.get("id"):
        warnings.append(_warn("map", "id-recommended",
                               "<map> should carry an @id attribute"))

    # Title
    if root.find("title") is None and not root.get("title"):
        warnings.append(_warn("map", "title-recommended",
                               "<map> should have a <title> child or @title attribute"))

    # Walk all topicrefs
    seen_keys: dict[str, int] = {}   # key value → count
    _walk_topicrefs(root, depth=0, errors=errors, warnings=warnings,
                    seen_keys=seen_keys, base_path=base_path)

    # Reltable column consistency
    for reltable in root.iter("reltable"):
        _check_reltable(reltable, errors)

    return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _walk_topicrefs(parent: ET.Element, depth: int, errors: list, warnings: list,
                    seen_keys: dict, base_path: Path | None) -> None:
    for child in parent:
        tag = child.tag

        if tag == "topicref" or tag == "chapter" or tag == "appendix":
            _check_topicref(child, depth + 1, errors, warnings,
                            seen_keys, base_path)
            _walk_topicrefs(child, depth + 1, errors, warnings,
                            seen_keys, base_path)

        elif tag == "keydef":
            # keydef defines keys; href optional
            keys = child.get("keys", "")
            for k in keys.split():
                seen_keys[k] = seen_keys.get(k, 0) + 1
                if seen_keys[k] > 1:
                    errors.append(_err("keydef", "duplicate-key",
                                       f"Key '{k}' is defined more than once in this map"))

        elif tag not in _HREF_EXEMPT:
            _walk_topicrefs(child, depth, errors, warnings, seen_keys, base_path)


def _check_topicref(el: ET.Element, depth: int, errors: list, warnings: list,
                    seen_keys: dict, base_path: Path | None) -> None:
    href = el.get("href")
    keyref = el.get("keyref")
    keys = el.get("keys", "")

    # href or keyref required (unless this is a pure key definition)
    if not href and not keyref:
        if not keys:
            errors.append(_err("topicref", "href-or-keyref-required",
                               "<topicref> must have @href or @keyref "
                               "(or @keys if it is a key definition)"))
        else:
            warnings.append(_warn("topicref", "href-or-keyref-recommended",
                                   f"<topicref keys='{keys}'> has no @href; "
                                   "it acts as a key-only definition"))

    # href format check
    if href:
        if href.startswith(("http://", "https://", "ftp://")):
            pass  # external links not validated for existence
        elif "#" in href:
            file_part, _ = href.split("#", 1)
            if file_part and base_path:
                _check_file_exists(file_part, base_path, el.tag, errors, warnings)
        elif base_path:
            _check_file_exists(href, base_path, el.tag, errors, warnings)

    # Duplicate keys from topicref/@keys
    for k in keys.split():
        seen_keys[k] = seen_keys.get(k, 0) + 1
        if seen_keys[k] > 1:
            errors.append(_err("topicref", "duplicate-key",
                               f"Key '{k}' is defined more than once in this map"))

    # @collection-type
    ct = el.get("collection-type")
    if ct and ct not in _COLLECTION_TYPES:
        errors.append(_err("topicref", "collection-type-invalid",
                           f"@collection-type='{ct}' is invalid; "
                           f"must be one of: {', '.join(sorted(_COLLECTION_TYPES))}"))

    # Nesting depth
    if depth > _MAX_DEPTH:
        warnings.append(_warn("topicref", "nesting-depth",
                               f"<topicref> is nested {depth} levels deep; "
                               f"recommended maximum is {_MAX_DEPTH}"))


def _check_file_exists(href: str, base_path: Path,
                       tag: str, errors: list, warnings: list) -> None:
    target = (base_path / href).resolve()
    if not target.exists():
        warnings.append(_warn(tag, "broken-href",
                               f"@href='{href}' does not resolve to an existing file "
                               f"(looked for {target})"))


def _check_reltable(reltable: ET.Element, errors: list) -> None:
    col_count = len(reltable.findall("relcolspec"))
    if col_count == 0:
        return  # no column spec defined — skipped
    for i, row in enumerate(reltable.findall("relrow"), start=1):
        cell_count = len(row.findall("relcell"))
        if cell_count != col_count:
            errors.append(_err("relrow", "reltable-column-mismatch",
                               f"<relrow> #{i} has {cell_count} <relcell> elements "
                               f"but <reltable> declares {col_count} <relcolspec> columns"))


def _err(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


def _warn(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_ditamap.py <file.ditamap | ->", file=sys.stderr)
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
