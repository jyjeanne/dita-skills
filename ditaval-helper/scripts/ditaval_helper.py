#!/usr/bin/env python3
"""
ditaval_helper.py — DITAVAL validator and generator

Usage (validate):
    python ditaval_helper.py validate path/to/filter.ditaval
    cat filter.ditaval | python ditaval_helper.py validate -

Usage (generate):
    python ditaval_helper.py generate \\
        --exclude audience=internal \\
        --include platform=linux \\
        --flag product=enterprise:color=#0055CC:style=italic \\
        --revflag rev=2.1:style=underline

Output (validate): JSON  →  { "is_valid": bool, "errors": [...], "warnings": [...] }
Output (generate): DITAVAL XML to stdout
Exit code: 0 = success, 1 = invalid
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_VALID_ACTIONS = {"include", "exclude", "flag", "passthrough"}
_VALID_STYLES = {"underline", "double-underline", "italics", "overline", "line-through"}
_VALID_REVPROP_ACTIONS = {"include", "exclude", "flag", "passthrough"}
_VISUAL_ATTRS = {"color", "backcolor", "style"}


def _err(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


def _warn(element: str, rule: str, message: str) -> dict:
    return {"element": element, "rule": rule, "message": message, "line": 0}


# ===========================================================================
# VALIDATE
# ===========================================================================

def validate_ditaval(xml_content: str, base_path: Path | None = None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {"is_valid": False,
                "errors": [_err("root", "well-formed", str(exc))],
                "warnings": []}

    if root.tag != "val":
        errors.append(_err(root.tag, "root-element",
                           f"Root element must be <val>, found <{root.tag}>"))
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    seen_props: set[tuple[str, str]] = set()
    style_conflict_count = 0

    for child in root:
        tag = child.tag

        if tag == "prop":
            _validate_prop(child, seen_props, errors, warnings, base_path)

        elif tag == "revprop":
            _validate_revprop(child, errors, warnings, base_path)

        elif tag == "style-conflict":
            style_conflict_count += 1
            if style_conflict_count > 1:
                errors.append(_err("style-conflict", "style-conflict-singleton",
                                   "<style-conflict> must appear at most once in <val>"))

        else:
            warnings.append(_warn(tag, "unknown-element",
                                   f"Unknown element <{tag}> in <val>"))

    return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _validate_prop(prop: ET.Element, seen: set, errors: list,
                   warnings: list, base_path: Path | None) -> None:
    att = prop.get("att")
    val = prop.get("val", "")       # val is optional
    action = prop.get("action")

    if not att:
        errors.append(_err("prop", "att-required",
                           "<prop> must have an @att attribute"))
        return

    if not action:
        errors.append(_err("prop", "action-required",
                           f"<prop att='{att}'> must have an @action attribute"))
        return

    if action not in _VALID_ACTIONS:
        errors.append(_err("prop", "action-invalid",
                           f"<prop att='{att}' action='{action}'> — "
                           f"@action must be one of: {', '.join(sorted(_VALID_ACTIONS))}"))

    # Duplicate att+val
    key = (att, val)
    if key in seen:
        errors.append(_err("prop", "duplicate-prop",
                           f"Duplicate <prop att='{att}' val='{val}'>; "
                           "each att+val combination must be unique"))
    seen.add(key)

    # flag without visual feedback
    if action == "flag":
        has_start = prop.find("startflag") is not None
        has_end = prop.find("endflag") is not None
        has_visual = any(prop.get(a) for a in _VISUAL_ATTRS)
        if not has_start and not has_end and not has_visual:
            warnings.append(_warn("prop", "flag-no-feedback",
                                   f"<prop att='{att}' val='{val}' action='flag'> "
                                   "has no visual attributes or startflag/endflag"))

    # style attribute value
    style = prop.get("style")
    if style and style not in _VALID_STYLES:
        errors.append(_err("prop", "style-invalid",
                           f"@style='{style}' is invalid; "
                           f"must be one of: {', '.join(sorted(_VALID_STYLES))}"))

    # imageref existence
    for flag_el in (prop.find("startflag"), prop.find("endflag")):
        if flag_el is not None:
            _check_imageref(flag_el, errors, warnings, base_path)


def _validate_revprop(revprop: ET.Element, errors: list,
                      warnings: list, base_path: Path | None) -> None:
    action = revprop.get("action")
    val = revprop.get("val", "(any)")

    if not action:
        errors.append(_err("revprop", "action-required",
                           f"<revprop val='{val}'> must have an @action attribute"))
        return

    if action not in _VALID_REVPROP_ACTIONS:
        errors.append(_err("revprop", "action-invalid",
                           f"<revprop val='{val}' action='{action}'> — "
                           f"@action must be one of: {', '.join(sorted(_VALID_REVPROP_ACTIONS))}"))

    if action == "flag":
        has_visual = any(revprop.get(a) for a in _VISUAL_ATTRS)
        has_start = revprop.find("startflag") is not None
        if not has_visual and not has_start:
            warnings.append(_warn("revprop", "flag-no-feedback",
                                   f"<revprop val='{val}' action='flag'> "
                                   "has no visual attributes or startflag"))

    for flag_el in (revprop.find("startflag"), revprop.find("endflag")):
        if flag_el is not None:
            _check_imageref(flag_el, errors, warnings, base_path)


def _check_imageref(flag_el: ET.Element, errors: list,
                    warnings: list, base_path: Path | None) -> None:
    imageref = flag_el.get("imageref")
    if imageref and base_path:
        target = (base_path / imageref).resolve()
        if not target.exists():
            warnings.append(_warn(flag_el.tag, "imageref-missing",
                                   f"imageref='{imageref}' does not exist "
                                   f"relative to the DITAVAL file"))


# ===========================================================================
# GENERATE
# ===========================================================================

def generate_ditaval(conditions: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<val>", ""]

    # Group by category for readability
    excludes = [c for c in conditions if c["action"] == "exclude"]
    includes = [c for c in conditions if c["action"] == "include"]
    flags = [c for c in conditions if c["action"] == "flag"]
    revflags = [c for c in conditions if c["action"] == "revflag"]

    if excludes:
        lines.append("  <!-- Exclude rules -->")
        for c in excludes:
            val_attr = f' val="{c["value"]}"' if c.get("value") else ""
            lines.append(f'  <prop action="exclude" att="{c["attribute"]}"{val_attr}/>')
        lines.append("")

    if includes:
        lines.append("  <!-- Include rules -->")
        for c in includes:
            val_attr = f' val="{c["value"]}"' if c.get("value") else ""
            lines.append(f'  <prop action="include" att="{c["attribute"]}"{val_attr}/>')
        lines.append("")

    if flags:
        lines.append("  <!-- Flag rules -->")
        for c in flags:
            val_attr = f' val="{c["value"]}"' if c.get("value") else ""
            extra = _format_visual_attrs(c)
            lines.append(f'  <prop action="flag" att="{c["attribute"]}"{val_attr}{extra}>')
            lines.append(f'    <startflag><alt-text>{{{{FILL}}}}</alt-text></startflag>')
            lines.append(f'  </prop>')
        lines.append("")

    if revflags:
        lines.append("  <!-- Revision flags -->")
        for c in revflags:
            val_attr = f' val="{c["value"]}"' if c.get("value") else ""
            extra = _format_visual_attrs(c)
            lines.append(f'  <revprop action="flag"{val_attr}{extra}>')
            lines.append(f'    <startflag><alt-text>{{{{FILL}}}}</alt-text></startflag>')
            lines.append(f'  </revprop>')
        lines.append("")

    if flags or revflags:
        lines += [
            '  <!-- Style conflict resolution -->',
            '  <style-conflict foreground-conflict-color="#CC0000"'
            ' background-conflict-color="#FFEEEE"/>',
            "",
        ]

    lines.append("</val>")
    return "\n".join(lines)


def _format_visual_attrs(condition: dict) -> str:
    parts = []
    for attr in ("color", "backcolor", "style"):
        if condition.get(attr):
            parts.append(f'{attr}="{condition[attr]}"')
    return (" " + " ".join(parts)) if parts else ""


# ===========================================================================
# CLI
# ===========================================================================

def _parse_condition(spec: str, action: str) -> dict:
    """Parse 'att=val' or 'att=val:color=#RGB:style=underline' into a dict."""
    parts = spec.split(":")
    att_val = parts[0].split("=", 1)
    cond: dict = {
        "attribute": att_val[0],
        "value": att_val[1] if len(att_val) > 1 else "",
        "action": action,
    }
    for extra in parts[1:]:
        if "=" in extra:
            k, v = extra.split("=", 1)
            cond[k] = v
    return cond


def main() -> None:
    parser = argparse.ArgumentParser(description="DITAVAL validator and generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate sub-command
    val_parser = subparsers.add_parser("validate", help="Validate a DITAVAL file")
    val_parser.add_argument("file", help="Path to DITAVAL file or '-' for stdin")

    # generate sub-command
    gen_parser = subparsers.add_parser("generate", help="Generate a DITAVAL template")
    gen_parser.add_argument("--exclude", nargs="+", metavar="att=val",
                            help="Conditions to exclude (e.g. audience=internal)")
    gen_parser.add_argument("--include", nargs="+", metavar="att=val",
                            help="Conditions to include (e.g. platform=linux)")
    gen_parser.add_argument("--flag", nargs="+", metavar="att=val[:color=#RGB]",
                            help="Conditions to flag with optional visual attrs")
    gen_parser.add_argument("--revflag", nargs="+", metavar="rev=val[:style=underline]",
                            help="Revision values to flag")

    args = parser.parse_args()

    if args.command == "validate":
        xml_content = (sys.stdin.read() if args.file == "-"
                       else Path(args.file).read_text(encoding="utf-8"))
        base_path = None if args.file == "-" else Path(args.file).parent
        result = validate_ditaval(xml_content, base_path)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["is_valid"] else 1)

    else:  # generate
        conditions: list[dict] = []
        for spec in (args.exclude or []):
            conditions.append(_parse_condition(spec, "exclude"))
        for spec in (args.include or []):
            conditions.append(_parse_condition(spec, "include"))
        for spec in (args.flag or []):
            conditions.append(_parse_condition(spec, "flag"))
        for spec in (args.revflag or []):
            conditions.append(_parse_condition(spec, "revflag"))
        if not conditions:
            parser.error("generate requires at least one condition flag")
        print(generate_ditaval(conditions))


if __name__ == "__main__":
    main()
