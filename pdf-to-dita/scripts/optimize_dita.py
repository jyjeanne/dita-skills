#!/usr/bin/env python3
"""
optimize_dita.py — Stage 4: Apply DITA best-practices and auto-fix common issues.

For each generated .dita topic:
  1. Runs best_practices.py to find violations.
  2. Auto-fixes: inserts missing <shortdesc> from first sentence.
  3. Re-runs best_practices.py to confirm fixes.

Usage:
    python optimize_dita.py <output_dir>
    python optimize_dita.py <output_dir> --skills-root /path/to/dita-skills

Output: JSON  →  { "summary": {...}, "files": [...] }
Exit code: 0 = all clean, 1 = remaining issues
"""

import json
import re
import sys
import subprocess
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_SKILLS_ROOT = _SCRIPT_DIR.parent.parent


# ---------------------------------------------------------------------------
# Best-practices runner
# ---------------------------------------------------------------------------

def _run_best_practices(script: Path, dita_path: Path) -> dict:
    """Run best_practices.py and return its JSON output."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(dita_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as e:
        return {"error": str(e), "findings": []}


# ---------------------------------------------------------------------------
# Auto-fix: missing <shortdesc>
# ---------------------------------------------------------------------------

_FIRST_SENTENCE_RE = re.compile(r"([^.!?]{10,}[.!?])\s")
_BODY_TAGS = {"conbody", "taskbody", "refbody", "body"}


def _extract_first_sentence(body: ET.Element) -> str | None:
    """Find the first paragraph inside a body element and extract its first sentence."""
    for p in body.iter("p"):
        text = "".join(p.itertext()).strip()
        if len(text) < 10:
            continue
        match = _FIRST_SENTENCE_RE.match(text)
        sentence = match.group(1) if match else text
        words = sentence.split()
        if len(words) > 50:
            sentence = " ".join(words[:50]) + "…"
        return sentence
    return None


def _fix_missing_shortdesc(dita_path: Path) -> bool:
    """Insert <shortdesc> if absent. Returns True if the file was modified."""
    try:
        content = dita_path.read_text(encoding="utf-8")
        tree = ET.parse(dita_path)
        root = tree.getroot()
    except ET.ParseError:
        return False

    # Already has shortdesc?
    if root.find("shortdesc") is not None:
        return False

    # Find the body element
    body: ET.Element | None = None
    for tag in _BODY_TAGS:
        body = root.find(tag)
        if body is not None:
            break
    if body is None:
        return False

    sentence = _extract_first_sentence(body)
    if not sentence:
        return False

    # Insert <shortdesc> after <title>
    title_idx: int | None = None
    for i, child in enumerate(root):
        if child.tag == "title":
            title_idx = i
            break
    if title_idx is None:
        return False

    shortdesc = ET.Element("shortdesc")
    shortdesc.text = sentence
    root.insert(title_idx + 1, shortdesc)

    # Reserialise preserving the XML declaration and DOCTYPE
    ET.indent(root, space="  ")
    new_xml = ET.tostring(root, encoding="unicode", xml_declaration=False)

    # Keep original header (lines before first element), preserving line endings
    header_lines = []
    newline = "\r\n" if "\r\n" in content else "\n"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("<") and not stripped.startswith("<?") and not stripped.startswith("<!"):
            break
        header_lines.append(line)

    header = newline.join(header_lines)
    dita_path.write_text(f"{header}{newline}{new_xml}{newline}", encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Main optimization pass
# ---------------------------------------------------------------------------

def optimize_all(output_dir: Path, skills_root: Path) -> dict:
    """Run best-practices and auto-fix on all .dita files in output_dir."""
    bp_script = skills_root / "dita-best-practices" / "scripts" / "best_practices.py"
    if not bp_script.exists():
        return {"error": f"best_practices.py not found at {bp_script}"}

    dita_files = sorted(output_dir.rglob("*.dita"))
    file_results: list[dict] = []
    fixes_applied = 0
    remaining_errors = 0
    remaining_warnings = 0

    for dita in dita_files:
        # First pass: find violations
        first_pass = _run_best_practices(bp_script, dita)
        findings_before = first_pass.get("findings", [])

        fixes: list[str] = []
        missing_shortdesc = any(
            f.get("rule") == "missing-shortdesc" for f in findings_before
        )

        if missing_shortdesc:
            modified = _fix_missing_shortdesc(dita)
            if modified:
                fixes.append("inserted-shortdesc")
                fixes_applied += 1

        # Second pass: measure remaining issues
        second_pass = _run_best_practices(bp_script, dita) if fixes else first_pass
        findings_after = second_pass.get("findings", [])

        errors_after   = [f for f in findings_after if f.get("severity") == "error"]
        warnings_after = [f for f in findings_after if f.get("severity") == "warning"]
        remaining_errors   += len(errors_after)
        remaining_warnings += len(warnings_after)

        file_results.append({
            "file":              str(dita.relative_to(output_dir)),
            "fixes_applied":     fixes,
            "findings_before":   len(findings_before),
            "findings_after":    len(findings_after),
            "remaining_errors":  errors_after,
            "remaining_warnings": warnings_after,
        })

    return {
        "summary": {
            "total_topics":     len(dita_files),
            "fixes_applied":    fixes_applied,
            "remaining_errors": remaining_errors,
            "remaining_warnings": remaining_warnings,
        },
        "files": file_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Optimize generated DITA topics using best-practices checks."
    )
    parser.add_argument("output_dir", help="Directory containing generated DITA files")
    parser.add_argument(
        "--skills-root",
        default=str(_DEFAULT_SKILLS_ROOT),
        help="Path to the dita-skills repository root",
    )
    args = parser.parse_args()

    output_dir  = Path(args.output_dir)
    skills_root = Path(args.skills_root)

    if not output_dir.exists():
        print(json.dumps({"error": f"Output directory not found: {output_dir}"}))
        sys.exit(1)

    report = optimize_all(output_dir, skills_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    has_errors = report.get("summary", {}).get("remaining_errors", 0) > 0
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
