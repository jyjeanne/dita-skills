#!/usr/bin/env python3
"""
review_dita_guide.py — Full hierarchical review of a DITA guide

Traverses the entire DITA publication hierarchy:
  bookmap / ditamap  →  child ditamaps  →  dita topics

For every file reachable from the root map the script:
  1. Validates structure against DITA 1.3 DTD rules
     (reuses validate_bookmap / validate_ditamap / validate_dita_topic)
  2. Checks best practices when --best-practices is supplied
     (reuses best_practices.analyze)
  3. Detects cross-guide issues invisible to single-file validators:
     · missing href targets
     · circular map references
     · duplicate topic @id values across the entire guide

Usage:
    python review_dita_guide.py path/to/root.ditamap
    python review_dita_guide.py path/to/guide.bookmap --best-practices
    python review_dita_guide.py path/to/root.ditamap --format summary

Output (JSON):
  {
    "root":    "<path>",
    "summary": { "maps", "topics", "missing", "errors", "warnings", ... },
    "files":   [ { "path", "type", "depth", "is_valid", "errors", "warnings" }, ... ],
    "cross_guide": [ { "rule", "message", "paths": [...] }, ... ]
  }

Exit codes:  0 = all valid,  1 = errors found,  2 = usage / IO error
"""

import argparse
import importlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate sibling skill scripts and import validators at runtime
# ---------------------------------------------------------------------------

# review-dita-guide/scripts/  →  ../../  =  dita-skills/
_SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent

_SKILL_SCRIPT_DIRS: dict[str, Path] = {
    "validate_dita_topic": _SKILLS_ROOT / "validate-dita-topic" / "scripts",
    "validate_ditamap":    _SKILLS_ROOT / "validate-ditamap"    / "scripts",
    "validate_bookmap":    _SKILLS_ROOT / "validate-bookmap"    / "scripts",
    "best_practices":      _SKILLS_ROOT / "dita-best-practices" / "scripts",
}

_VALIDATORS: dict | None = None  # lazy-loaded


def _load_validators() -> dict:
    modules: dict = {}
    for name, path in _SKILL_SCRIPT_DIRS.items():
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
        try:
            modules[name] = importlib.import_module(name)
        except ImportError:
            modules[name] = None
    return modules


def _get_validators() -> dict:
    global _VALIDATORS
    if _VALIDATORS is None:
        _VALIDATORS = _load_validators()
    return _VALIDATORS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Map elements whose @href can point to another file
_MAP_REF_TAGS = frozenset({
    "topicref", "mapref",
    # bookmap structural elements
    "chapter", "part", "appendix",
    "frontmatter", "backmatter", "notices", "preface",
    "glossarylist", "indexlist", "tablelist", "figurelist", "toc",
    "keydef", "booklist",
})

_TOPIC_EXTENSIONS = frozenset({".dita", ".xml"})
_MAP_EXTENSIONS   = frozenset({".ditamap", ".bookmap"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rel(abs_path: Path, root_dir: Path) -> str:
    """Return *abs_path* relative to *root_dir*, falling back to str."""
    try:
        return str(abs_path.relative_to(root_dir)).replace("\\", "/")
    except ValueError:
        return str(abs_path).replace("\\", "/")


def _cross_issue(rule: str, message: str, paths: list | None = None) -> dict:
    entry: dict = {"rule": rule, "message": message}
    if paths:
        entry["paths"] = [p.replace("\\", "/") for p in paths]
    return entry


def _classify(path: Path) -> str:
    """Return 'bookmap', 'map', 'topic', 'unknown', or 'missing'."""
    if not path.exists():
        return "missing"
    ext = path.suffix.lower()
    if ext == ".bookmap":
        return "bookmap"
    if ext == ".ditamap":
        return "map"
    if ext in _TOPIC_EXTENSIONS:
        try:
            tag = ET.parse(str(path)).getroot().tag
            if tag == "bookmap":
                return "bookmap"
            if tag == "map":
                return "map"
            return "topic"
        except ET.ParseError:
            return "topic"
    return "unknown"


def _get_hrefs(map_path: Path) -> list[tuple[str, str]]:
    """
    Return (href_clean, element_tag) pairs for all local file references
    inside *map_path*. External URLs and pure keyrefs are silently skipped.
    """
    try:
        tree = ET.parse(str(map_path))
    except ET.ParseError:
        return []

    refs: list[tuple[str, str]] = []
    for el in tree.iter():
        if el.tag not in _MAP_REF_TAGS:
            continue
        href = el.get("href", "").strip()
        if not href or href.startswith(("http://", "https://", "ftp://")):
            continue
        href_clean = href.split("#")[0]
        if href_clean:
            refs.append((href_clean, el.tag))
    return refs


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def _traverse(
    map_path: Path,
    root_dir: Path,
    depth: int,
    # path_stack: maps in the current recursion branch — popped on backtrack
    # Detects true cycles (A→B→A) without flagging shared maps (diamond A→C, B→C).
    path_stack: set,
    # all_visited_maps: every map ever processed — never removed.
    # Prevents re-validating a shared map that appears in multiple branches.
    all_visited_maps: set,
    visited_topics: set,
    file_results: list,
    cross_issues: list,
    validators: dict,
    include_bp: bool,
) -> None:
    """
    Recursively walk the map hierarchy rooted at *map_path*.

    Uses two sets for map tracking:
    - *path_stack*   — current DFS path; enables true circular-reference detection
                       via backtracking (add on entry, discard on return).
    - *all_visited_maps* — global dedup set; prevents re-validating shared child
                           maps that appear in multiple branches (diamond structure).
    """
    abs_path = map_path.resolve()

    # --- True circular reference: same map in current recursion path ---
    if abs_path in path_stack:
        cross_issues.append(_cross_issue(
            "circular-reference",
            f"Circular map reference: '{_rel(abs_path, root_dir)}' "
            "is included more than once in the same traversal path",
            [_rel(abs_path, root_dir)],
        ))
        return

    # --- Diamond dedup: map already validated in another branch — skip silently ---
    if abs_path in all_visited_maps:
        return

    # Add to both tracking sets; will be removed from path_stack on return
    path_stack.add(abs_path)
    all_visited_maps.add(abs_path)

    # --- Validate the map itself ---
    file_type = _classify(abs_path)
    result = _validate_file(abs_path, file_type, root_dir, validators, include_bp)
    result["depth"] = depth
    file_results.append(result)

    if file_type == "missing":
        path_stack.discard(abs_path)
        return

    # --- Recurse into children ---
    for href, tag in _get_hrefs(abs_path):
        child_path = (abs_path.parent / href).resolve()
        child_ext  = child_path.suffix.lower()

        if child_ext in _MAP_EXTENSIONS or tag == "mapref":
            _traverse(
                child_path, root_dir, depth + 1,
                path_stack, all_visited_maps,
                visited_topics, file_results, cross_issues, validators, include_bp,
            )
        elif child_ext in _TOPIC_EXTENSIONS or child_ext == "":
            # Leaf topic — validate once even if referenced from multiple maps
            if child_path in visited_topics:
                continue
            visited_topics.add(child_path)
            topic_type = _classify(child_path)
            t_result = _validate_file(
                child_path, topic_type, root_dir, validators, include_bp,
            )
            t_result["depth"] = depth + 1
            file_results.append(t_result)
        # unknown extension — skip silently

    # Backtrack: remove from current path so sibling branches can revisit via
    # a different route without triggering a false circular-reference.
    path_stack.discard(abs_path)


def _validate_file(
    abs_path: Path,
    file_type: str,
    root_dir: Path,
    validators: dict,
    include_bp: bool,
) -> dict:
    """Run the appropriate validator on *abs_path* and return a result dict."""
    rel = _rel(abs_path, root_dir)
    base: dict = {
        "path":     rel,
        "type":     file_type,
        "depth":    0,          # filled by caller
        "is_valid": False,
        "errors":   [],
        "warnings": [],
    }

    if file_type == "missing":
        base["errors"].append({
            "element": "topicref",
            "rule":    "href-target-missing",
            "message": f"Referenced file not found: '{rel}'",
            "line":    0,
        })
        return base

    try:
        content = abs_path.read_text(encoding="utf-8")
    except OSError as exc:
        base["errors"].append({
            "element": "file",
            "rule":    "io-error",
            "message": str(exc),
            "line":    0,
        })
        return base

    # --- Structural validation ---
    v = validators
    if file_type == "bookmap" and v.get("validate_bookmap"):
        outcome = v["validate_bookmap"].validate(content, base_path=abs_path.parent)
    elif file_type == "map" and v.get("validate_ditamap"):
        outcome = v["validate_ditamap"].validate(content, base_path=abs_path.parent)
    elif file_type == "topic" and v.get("validate_dita_topic"):
        outcome = v["validate_dita_topic"].validate(content)
    else:
        # Fallback: well-formedness only
        try:
            ET.fromstring(content)
            outcome = {"is_valid": True, "errors": [], "warnings": []}
        except ET.ParseError as exc:
            outcome = {
                "is_valid": False,
                "errors":   [{"element": "root", "rule": "well-formed",
                               "message": str(exc), "line": 0}],
                "warnings": [],
            }

    base["is_valid"]  = outcome["is_valid"]
    base["errors"]    = outcome["errors"]
    base["warnings"]  = outcome["warnings"]

    # --- Best practices (topics only, opt-in) ---
    if include_bp and file_type == "topic" and v.get("best_practices"):
        bp = v["best_practices"].analyze(content)
        base["best_practices"] = bp.get("findings", [])

    return base


# ---------------------------------------------------------------------------
# Cross-guide analysis
# ---------------------------------------------------------------------------

def _cross_guide_checks(
    file_results: list,
    root_dir: Path,
    cross_issues: list,
) -> None:
    """Detect issues that span multiple files — runs after full traversal."""

    id_locations: dict[str, list[str]] = {}

    for fr in file_results:
        if fr["type"] != "topic":
            continue
        abs_path = (root_dir / fr["path"]).resolve()
        if not abs_path.exists():
            continue
        try:
            root_el = ET.parse(str(abs_path)).getroot()
        except ET.ParseError:
            continue
        topic_id = root_el.get("id", "")
        if topic_id:
            id_locations.setdefault(topic_id, []).append(fr["path"])

    for tid, paths in id_locations.items():
        if len(paths) > 1:
            cross_issues.append(_cross_issue(
                "duplicate-guide-id",
                f"Topic @id='{tid}' appears in {len(paths)} files; "
                "IDs must be unique across the guide for reliable linking",
                paths,
            ))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(file_results: list, cross_issues: list) -> dict:
    maps     = sum(1 for f in file_results if f["type"] in ("map", "bookmap"))
    topics   = sum(1 for f in file_results if f["type"] == "topic")
    missing  = sum(1 for f in file_results if f["type"] == "missing")
    unknown  = sum(1 for f in file_results if f["type"] == "unknown")
    errors   = sum(len(f["errors"])   for f in file_results) + sum(
        1 for ci in cross_issues
        if ci.get("rule") not in ("duplicate-guide-id",)   # errors only
    )
    warnings = sum(len(f["warnings"]) for f in file_results) + sum(
        1 for ci in cross_issues
        if ci.get("rule") == "duplicate-guide-id"           # warnings
    )
    valid    = sum(1 for f in file_results if f["is_valid"])
    return {
        "total_files":        len(file_results),
        "maps":               maps,
        "topics":             topics,
        "missing":            missing,
        "unknown":            unknown,
        "valid_files":        valid,
        "invalid_files":      len(file_results) - valid,
        "errors":             errors,
        "warnings":           warnings,
        "cross_guide_issues": len(cross_issues),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def review_guide(
    root_path: "str | Path",
    include_best_practices: bool = False,
) -> dict:
    """
    Review the DITA guide rooted at *root_path*.

    Returns the full review report as a dict:
      { "root", "summary", "files", "cross_guide" }
    """
    root_path = Path(root_path).resolve()
    root_dir  = root_path.parent

    if not root_path.exists():
        return {
            "root":        str(root_path).replace("\\", "/"),
            "summary":     {},
            "files":       [],
            "cross_guide": [_cross_issue(
                "io-error",
                f"Root file not found: '{root_path}'",
            )],
        }

    validators: dict   = _get_validators()
    file_results: list = []
    cross_issues: list = []
    path_stack: set        = set()
    all_visited_maps: set  = set()
    visited_topics: set    = set()

    _traverse(
        root_path, root_dir, depth=0,
        path_stack=path_stack,
        all_visited_maps=all_visited_maps,
        visited_topics=visited_topics,
        file_results=file_results,
        cross_issues=cross_issues,
        validators=validators,
        include_bp=include_best_practices,
    )

    _cross_guide_checks(file_results, root_dir, cross_issues)

    return {
        "root":        str(root_path).replace("\\", "/"),
        "summary":     _build_summary(file_results, cross_issues),
        "files":       file_results,
        "cross_guide": cross_issues,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review an entire DITA guide from its root bookmap or ditamap",
    )
    parser.add_argument("root", help="Path to the root .ditamap or .bookmap file")
    parser.add_argument(
        "--best-practices", action="store_true",
        help="Include best-practice findings for each topic",
    )
    parser.add_argument(
        "--format", choices=["full", "summary"], default="full",
        help="Output format: 'full' (default) or 'summary' statistics only",
    )
    args = parser.parse_args()

    try:
        report = review_guide(args.root, include_best_practices=args.best_practices)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(2)

    if args.format == "summary":
        output = {
            "root":        report["root"],
            "summary":     report["summary"],
            "cross_guide": report["cross_guide"],
        }
    else:
        output = report

    print(json.dumps(output, indent=2))
    sys.exit(1 if report["summary"].get("errors", 0) > 0 else 0)


if __name__ == "__main__":
    main()
