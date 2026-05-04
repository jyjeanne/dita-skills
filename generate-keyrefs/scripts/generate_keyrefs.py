#!/usr/bin/env python3
"""
generate_keyrefs.py — Scan DITA topics and generate keydef / keyref suggestions.

For each set of .dita files:
  1. Finds repeated inline text in <ph>, <term>, <keyword>, <prodname>, <varname>, etc.
  2. Finds repeated external hrefs in <xref>, <link>, <image>, <coderef>
  3. Produces ready-to-paste keydef XML for the map
  4. Suggests which elements to replace with keyref= attributes
  5. Optionally rewrites files in place (--apply)

Usage:
    python generate_keyrefs.py <file_or_dir> [file_or_dir ...]
    python generate_keyrefs.py topics/          --min-occurrences 2
    python generate_keyrefs.py topics/ overview.dita  --apply
    python generate_keyrefs.py topics/ --keydef-output keydefs.xml

Output: JSON → { "keydefs": [...], "changes": [...], "keydef_block": "..." }
Exit code: 0 = success, 1 = error
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Element categories
# ---------------------------------------------------------------------------

# Inline elements whose full text content is a good keyref candidate
_INLINE_TAGS = {
    "ph", "term", "keyword", "cite",
    "prodname", "brand", "varname", "wintitle",
    "cmdname", "option", "parmname", "apiname",
    "filepath", "userinput", "systemoutput",
}

# Elements whose href attribute is a good keyref candidate
_HREF_TAGS = {
    "xref": "external",
    "link": "external",
    "image": "local",
    "coderef": "local",
}

_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Key name generation
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert text or URL into a lowercase-hyphen key name."""
    # Strip protocol from URLs
    text = re.sub(r"^https?://", "", text, flags=re.IGNORECASE)
    # Strip query string and fragment
    text = re.split(r"[?#]", text)[0]
    # Strip file extensions (.png, .html …)
    text = re.sub(r"\.[a-z]{2,5}$", "", text, flags=re.IGNORECASE)
    slug = re.sub(r"[^\w\s-]", " ", text.lower())
    slug = re.sub(r"[\s_/\\]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:48] or "key"


def _unique_key(base: str, used: set[str]) -> str:
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}-{n}"
        n += 1
    used.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def _collect_from_file(path: Path) -> tuple[list[tuple], list[tuple]]:
    """
    Return (text_hits, href_hits).

    text_hits : list of (tag, text, path)
    href_hits : list of (tag, href, path)
    """
    try:
        tree = ET.parse(str(path))
    except ET.ParseError:
        return [], []

    text_hits: list[tuple] = []
    href_hits: list[tuple] = []

    for el in tree.iter():
        tag = el.tag.lower()

        if tag in _INLINE_TAGS:
            text = (el.text or "").strip()
            if len(text) >= 2 and not el.get("keyref"):
                text_hits.append((tag, text, path))

        if tag in _HREF_TAGS:
            href = el.get("href", "")
            if href and not el.get("keyref"):
                href_hits.append((tag, href, path))

    return text_hits, href_hits


def scan_files(paths: list[Path], min_occurrences: int) -> tuple[dict, dict]:
    """
    Aggregate text and href hits across all files.

    Returns:
        text_index : { text_value → list of (tag, path) }
        href_index : { href_value → list of (tag, path) }
    """
    text_index: dict[str, list] = defaultdict(list)
    href_index: dict[str, list] = defaultdict(list)

    for p in paths:
        th, hh = _collect_from_file(p)
        for tag, text, path in th:
            text_index[text].append((tag, path))
        for tag, href, path in hh:
            href_index[href].append((tag, path))

    # Filter to candidates meeting min_occurrences
    text_candidates = {
        k: v for k, v in text_index.items()
        if len(v) >= min_occurrences
    }
    href_candidates = {
        k: v for k, v in href_index.items()
        if len(v) >= min_occurrences
    }
    return text_candidates, href_candidates


# ---------------------------------------------------------------------------
# Keydef building
# ---------------------------------------------------------------------------

def _make_text_keydef(key: str, value: str) -> str:
    """Generate a <keydef> for an inline text value."""
    v = value.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    return (
        f'<keydef key="{key}">\n'
        f'  <topicmeta>\n'
        f'    <keywords>\n'
        f'      <keyword>{v}</keyword>\n'
        f'    </keywords>\n'
        f'  </topicmeta>\n'
        f'</keydef>'
    )


def _make_href_keydef(key: str, href: str, scope_hint: str) -> str:
    """Generate a <keydef> for an href value."""
    h = href.replace("&", "&amp;").replace('"', "&quot;")
    if _HTTP_RE.match(href):
        return f'<keydef key="{key}" href="{h}" scope="external" format="html"/>'
    ext = Path(href).suffix.lstrip(".").lower() or "dita"
    fmt = ext
    return f'<keydef key="{key}" href="{h}" format="{fmt}"/>'


def build_keydefs(
    text_candidates: dict,
    href_candidates: dict,
) -> tuple[list[dict], str]:
    """
    Build keydef list and concatenated XML block.

    Returns:
        keydefs   : list of keydef dicts for JSON output
        xml_block : multi-line XML string ready to paste into a map
    """
    used_keys: set[str] = set()
    keydefs: list[dict] = []
    xml_lines: list[str] = []

    for text, hits in sorted(text_candidates.items(), key=lambda x: -len(x[1])):
        base = _slugify(text)
        key = _unique_key(base, used_keys)
        files = sorted({str(p) for _, p in hits})
        keydefs.append({
            "key":         key,
            "type":        "text",
            "value":       text,
            "occurrences": len(hits),
            "files":       files,
        })
        xml_lines.append(_make_text_keydef(key, text))

    for href, hits in sorted(href_candidates.items(), key=lambda x: -len(x[1])):
        base = "img-" + _slugify(href) if any(
            t in ("image",) for t, _ in hits
        ) else ("ext-" if _HTTP_RE.match(href) else "") + _slugify(href)
        key = _unique_key(base, used_keys)
        files = sorted({str(p) for _, p in hits})
        scope = "external" if _HTTP_RE.match(href) else "local"
        keydefs.append({
            "key":         key,
            "type":        "href",
            "href":        href,
            "scope":       scope,
            "occurrences": len(hits),
            "files":       files,
        })
        xml_lines.append(_make_href_keydef(key, href, scope))

    return keydefs, "\n\n".join(xml_lines)


# ---------------------------------------------------------------------------
# Change list
# ---------------------------------------------------------------------------

def build_changes(
    text_candidates: dict,
    href_candidates: dict,
    keydefs: list[dict],
) -> list[dict]:
    """Return a flat list of suggested element rewrites."""
    key_for_text = {kd["value"]: kd["key"] for kd in keydefs if kd["type"] == "text"}
    key_for_href = {kd["href"]:  kd["key"] for kd in keydefs if kd["type"] == "href"}

    changes: list[dict] = []

    for text, hits in text_candidates.items():
        key = key_for_text.get(text)
        if not key:
            continue
        for tag, path in hits:
            changes.append({
                "file":        str(path),
                "element":     tag,
                "change":      "add_keyref",
                "old_text":    text,
                "new_keyref":  key,
                "description": f'<{tag}>{text}</{tag}> → <{tag} keyref="{key}"/>',
            })

    for href, hits in href_candidates.items():
        key = key_for_href.get(href)
        if not key:
            continue
        for tag, path in hits:
            changes.append({
                "file":        str(path),
                "element":     tag,
                "change":      "add_keyref",
                "old_href":    href,
                "new_keyref":  key,
                "description": f'<{tag} href="{href}"> → <{tag} keyref="{key}">',
            })

    return changes


# ---------------------------------------------------------------------------
# Apply rewrites
# ---------------------------------------------------------------------------

def apply_changes(paths: list[Path], keydefs: list[dict]) -> dict[str, int]:
    """Rewrite .dita files in place, replacing text/href with keyref= attrs.

    Returns a map of {file_path: number_of_changes_applied}.
    """
    key_for_text = {kd["value"]: kd["key"] for kd in keydefs if kd["type"] == "text"}
    key_for_href = {kd["href"]:  kd["key"] for kd in keydefs if kd["type"] == "href"}
    applied: dict[str, int] = {}

    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
            tree = ET.parse(str(path))
        except (ET.ParseError, OSError):
            continue

        root = tree.getroot()
        count = 0

        for el in root.iter():
            tag = el.tag.lower()

            if tag in _INLINE_TAGS:
                text = (el.text or "").strip()
                if text in key_for_text and not el.get("keyref"):
                    el.set("keyref", key_for_text[text])
                    el.text = None
                    count += 1

            if tag in _HREF_TAGS:
                href = el.get("href", "")
                if href in key_for_href and not el.get("keyref"):
                    el.set("keyref", key_for_href[href])
                    del el.attrib["href"]
                    count += 1

        if count == 0:
            continue

        # Preserve original XML declaration / DOCTYPE header
        original_lines = content.splitlines()
        header_lines = []
        for line in original_lines:
            s = line.strip()
            if s.startswith("<") and not s.startswith("<?") and not s.startswith("<!"):
                break
            header_lines.append(line)

        ET.indent(root, space="  ")
        new_xml = ET.tostring(root, encoding="unicode", xml_declaration=False)
        sep = "\r\n" if "\r\n" in content else "\n"
        header = sep.join(header_lines)
        path.write_text(f"{header}{sep}{new_xml}{sep}", encoding="utf-8")
        applied[str(path)] = count

    return applied


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate(
    input_paths: list[Path],
    min_occurrences: int = 2,
) -> dict:
    """Scan DITA files and return analysis dict.

    Returns:
        { "keydefs": [...], "changes": [...], "keydef_block": "...",
          "summary": { "files_scanned", "keydefs_suggested", "changes_suggested" } }
    """
    # Resolve all .dita files
    dita_files: list[Path] = []
    for p in input_paths:
        if p.is_dir():
            dita_files.extend(sorted(p.rglob("*.dita")))
        elif p.suffix.lower() == ".dita":
            dita_files.append(p)

    if not dita_files:
        return {
            "keydefs": [], "changes": [], "keydef_block": "",
            "summary": {"files_scanned": 0, "keydefs_suggested": 0, "changes_suggested": 0},
        }

    text_cands, href_cands = scan_files(dita_files, min_occurrences)
    keydefs, keydef_block = build_keydefs(text_cands, href_cands)
    changes = build_changes(text_cands, href_cands, keydefs)

    return {
        "keydefs":      keydefs,
        "changes":      changes,
        "keydef_block": keydef_block,
        "summary": {
            "files_scanned":      len(dita_files),
            "keydefs_suggested":  len(keydefs),
            "changes_suggested":  len(changes),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate keydef/keyref suggestions from DITA topics."
    )
    parser.add_argument(
        "inputs", nargs="+", metavar="FILE_OR_DIR",
        help="One or more .dita files or directories to scan",
    )
    parser.add_argument(
        "--min-occurrences", type=int, default=2, metavar="N",
        help="Minimum number of occurrences before suggesting a keyref (default: 2)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Rewrite .dita files in place (adds keyref= attributes, removes old text/href)",
    )
    parser.add_argument(
        "--keydef-output", metavar="FILE",
        help="Write keydef XML block to a file (for pasting into your ditamap)",
    )
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        print(json.dumps({"error": f"Path not found: {missing[0]}"}))
        sys.exit(1)

    result = generate(input_paths, min_occurrences=args.min_occurrences)

    if args.apply:
        dita_files: list[Path] = []
        for p in input_paths:
            if p.is_dir():
                dita_files.extend(sorted(p.rglob("*.dita")))
            elif p.suffix.lower() == ".dita":
                dita_files.append(p)
        if result["keydefs"]:
            applied = apply_changes(dita_files, result["keydefs"])
        else:
            applied = {}
        result["applied"] = applied
        result["summary"]["files_rewritten"] = len(applied)

    if args.keydef_output and result["keydef_block"]:
        kd_path = Path(args.keydef_output)
        kd_path.write_text(result["keydef_block"], encoding="utf-8")
        result["keydef_output_file"] = str(kd_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
