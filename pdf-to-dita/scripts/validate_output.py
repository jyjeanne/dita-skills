#!/usr/bin/env python3
"""
validate_output.py — Stage 3: Validate all generated DITA files.

Calls validate_dita_topic.py and validate_ditamap.py from the dita-skills
repository for every file in the pipeline output directory.

Usage:
    python validate_output.py <output_dir>
    python validate_output.py <output_dir> --scripts-root /path/to/dita-skills

Output: JSON  →  { "summary": {...}, "files": [...] }
Exit code: 0 = all valid, 1 = validation errors found
"""

import json
import sys
import subprocess
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Script discovery
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_SKILLS_ROOT = _SCRIPT_DIR.parent.parent  # dita-skills root


def _find_script(skills_root: Path, skill: str, script: str) -> Path | None:
    """Locate a validator script relative to the dita-skills root."""
    candidate = skills_root / skill / "scripts" / script
    if candidate.exists():
        return candidate
    return None


# ---------------------------------------------------------------------------
# Run a single validator
# ---------------------------------------------------------------------------

def _run_validator(script: Path, target: Path, extra_args: list[str] | None = None) -> dict:
    """Run a validator script and return its parsed JSON output."""
    cmd = [sys.executable, str(script), str(target)] + (extra_args or [])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {
                "is_valid": False,
                "errors": [{"message": f"Validator returned non-JSON: {proc.stdout[:200]}"}],
                "warnings": [],
            }
        return result
    except subprocess.TimeoutExpired:
        return {
            "is_valid": False,
            "errors": [{"message": "Validator timed out"}],
            "warnings": [],
        }
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [{"message": f"Failed to run validator: {e}"}],
            "warnings": [],
        }


# ---------------------------------------------------------------------------
# Main validation pass
# ---------------------------------------------------------------------------

def validate_all(output_dir: Path, skills_root: Path) -> dict:
    """Validate all .dita and .ditamap files in output_dir.

    Returns a consolidated validation report.
    """
    topic_validator = _find_script(skills_root, "validate-dita-topic", "validate_dita_topic.py")
    map_validator   = _find_script(skills_root, "validate-ditamap",    "validate_ditamap.py")

    if not topic_validator:
        return {"error": f"validate_dita_topic.py not found under {skills_root}"}
    if not map_validator:
        return {"error": f"validate_ditamap.py not found under {skills_root}"}

    dita_files   = sorted(output_dir.rglob("*.dita"))
    map_files    = sorted(output_dir.rglob("*.ditamap"))

    file_results: list[dict] = []
    total_errors = 0
    total_warnings = 0

    for dita in dita_files:
        result = _run_validator(topic_validator, dita)
        errors   = result.get("errors", [])
        warnings = result.get("warnings", [])
        total_errors   += len(errors)
        total_warnings += len(warnings)
        file_results.append({
            "file":      str(dita.relative_to(output_dir)),
            "type":      "topic",
            "is_valid":  result.get("is_valid", False),
            "errors":    errors,
            "warnings":  warnings,
        })

    for mapf in map_files:
        result = _run_validator(map_validator, mapf)
        errors   = result.get("errors", [])
        warnings = result.get("warnings", [])
        total_errors   += len(errors)
        total_warnings += len(warnings)
        file_results.append({
            "file":      str(mapf.relative_to(output_dir)),
            "type":      "map",
            "is_valid":  result.get("is_valid", False),
            "errors":    errors,
            "warnings":  warnings,
        })

    invalid_count = sum(1 for f in file_results if not f["is_valid"])

    return {
        "summary": {
            "total_files":    len(file_results),
            "valid":          len(file_results) - invalid_count,
            "invalid":        invalid_count,
            "total_errors":   total_errors,
            "total_warnings": total_warnings,
        },
        "files": file_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate all DITA files in a pipeline output directory.")
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

    report = validate_all(output_dir, skills_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    has_errors = report.get("summary", {}).get("total_errors", 0) > 0
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
