#!/usr/bin/env python3
"""
pipeline.py — Main PDF → DITA conversion pipeline orchestrator.

Runs all 5 stages in sequence:
  Stage 1  extract    PDF text + structure       → extracted.json
  Stage 2  chunk      Structure → DITA XML       → topics/ + root.ditamap
  Stage 3  validate   DITA 1.3 validity check    → validation_report.json
  Stage 4  optimize   Best-practices + auto-fix  → optimization_report.json
  Stage 5  review     Full guide cross-check     → review_report.json

Usage:
    python pipeline.py <input.pdf> <output_dir>
    python pipeline.py <input.pdf> <output_dir> --map-title "My Guide" --format summary
    python pipeline.py <input.pdf> <output_dir> --skip-review   # faster; skips stage 5
    python pipeline.py --from-json <extracted.json> <output_dir>  # skip PDF extraction

Output: JSON pipeline report (stdout) + individual stage reports in <output_dir>
Exit code: 0 = success, 1 = validation errors, 2 = pipeline failure
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import time

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_SKILLS_ROOT = _SCRIPT_DIR.parent.parent


# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------

def _run_stage(label: str, cmd: list[str], output_file: Path | None = None) -> dict:
    """Run a stage script and return its result dict."""
    start = time.monotonic()
    print(f"\n[PIPELINE] Stage: {label} ...", file=sys.stderr)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        elapsed = time.monotonic() - start

        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {"raw_output": proc.stdout[:2000]}

        if proc.returncode not in (0, 1):
            result["_stage_error"] = proc.stderr[:500] if proc.stderr else "non-zero exit"

        if output_file and proc.stdout.strip():
            output_file.write_text(proc.stdout, encoding="utf-8")

        status = "ok" if proc.returncode == 0 else "warnings" if proc.returncode == 1 else "error"
        print(f"[PIPELINE] {label}: {status} ({elapsed:.1f}s)", file=sys.stderr)

        return {
            "stage":      label,
            "status":     status,
            "exit_code":  proc.returncode,
            "elapsed_s":  round(elapsed, 2),
            "result":     result,
        }

    except subprocess.TimeoutExpired:
        return {
            "stage":     label,
            "status":    "timeout",
            "exit_code": -1,
            "elapsed_s": 300,
            "result":    {"error": "Stage timed out after 300s"},
        }
    except Exception as e:
        return {
            "stage":     label,
            "status":    "error",
            "exit_code": -1,
            "elapsed_s": 0,
            "result":    {"error": str(e)},
        }


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

def _summary_report(stages: list[dict], output_dir: Path) -> dict:
    """Return a condensed summary report."""
    overall = "ok"
    for s in stages:
        if s["status"] == "error":
            overall = "error"
            break
        if s["status"] in ("warnings", "timeout"):
            overall = "warnings"

    val_summary   = {}
    optim_summary = {}
    review_summary = {}

    for s in stages:
        r = s.get("result", {})
        if s["stage"] == "validate":
            val_summary = r.get("summary", {})
        elif s["stage"] == "optimize":
            optim_summary = r.get("summary", {})
        elif s["stage"] == "review":
            review_summary = r.get("summary", {})

    return {
        "overall":    overall,
        "output_dir": str(output_dir),
        "stages": [{
            "stage":     s["stage"],
            "status":    s["status"],
            "elapsed_s": s["elapsed_s"],
        } for s in stages],
        "validation": val_summary,
        "optimization": optim_summary,
        "review": review_summary,
    }


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    pdf_path: Path | None,
    extracted_json: Path | None,
    output_dir: Path,
    skills_root: Path,
    map_title: str | None,
    skip_review: bool,
    fmt: str,
) -> tuple[dict, int]:
    """Execute all pipeline stages. Returns (report_dict, exit_code)."""

    output_dir.mkdir(parents=True, exist_ok=True)
    stages: list[dict] = []

    # ------------------------------------------------------------------
    # Stage 1 – Extract (skip if --from-json)
    # ------------------------------------------------------------------
    if pdf_path is not None:
        extracted_path = output_dir / "extracted.json"
        stage = _run_stage(
            "extract",
            [sys.executable,
             str(_SCRIPT_DIR / "extract_pdf.py"),
             str(pdf_path)],
            output_file=extracted_path,
        )
        stages.append(stage)
        if stage["status"] == "error" or stage["exit_code"] not in (0, 1):
            return (_build_report(stages, output_dir, fmt), 2)
        extracted_json = extracted_path
    else:
        stages.append({
            "stage": "extract", "status": "skipped",
            "exit_code": 0, "elapsed_s": 0, "result": {},
        })

    # ------------------------------------------------------------------
    # Stage 2 – Chunk
    # ------------------------------------------------------------------
    chunk_cmd = [
        sys.executable,
        str(_SCRIPT_DIR / "chunk_to_dita.py"),
        str(extracted_json),
        str(output_dir),
    ]
    if map_title:
        chunk_cmd += ["--map-title", map_title]

    stage = _run_stage("chunk", chunk_cmd)
    stages.append(stage)
    # Any non-zero exit from chunk_to_dita is a fatal error
    # (exit 1 = file-not-found / JSON parse error, exit 2 = unexpected crash).
    if stage["exit_code"] != 0:
        return (_build_report(stages, output_dir, fmt), 2)

    # ------------------------------------------------------------------
    # Stage 3 – Validate
    # ------------------------------------------------------------------
    val_report_path = output_dir / "validation_report.json"
    stage = _run_stage(
        "validate",
        [sys.executable,
         str(_SCRIPT_DIR / "validate_output.py"),
         str(output_dir),
         "--skills-root", str(skills_root)],
        output_file=val_report_path,
    )
    stages.append(stage)

    # ------------------------------------------------------------------
    # Stage 4 – Optimize
    # ------------------------------------------------------------------
    optim_report_path = output_dir / "optimization_report.json"
    stage = _run_stage(
        "optimize",
        [sys.executable,
         str(_SCRIPT_DIR / "optimize_dita.py"),
         str(output_dir),
         "--skills-root", str(skills_root)],
        output_file=optim_report_path,
    )
    stages.append(stage)

    # ------------------------------------------------------------------
    # Stage 5 – Review (full guide cross-check)
    # ------------------------------------------------------------------
    if not skip_review:
        review_script = skills_root / "review-dita-guide" / "scripts" / "review_dita_guide.py"
        map_path = output_dir / "root.ditamap"
        review_report_path = output_dir / "review_report.json"

        if review_script.exists() and map_path.exists():
            stage = _run_stage(
                "review",
                [sys.executable, str(review_script),
                 str(map_path), "--best-practices"],
                output_file=review_report_path,
            )
        else:
            stage = {
                "stage": "review", "status": "skipped",
                "exit_code": 0, "elapsed_s": 0,
                "result": {"reason": "review script or map not found"},
            }
        stages.append(stage)
    else:
        stages.append({
            "stage": "review", "status": "skipped",
            "exit_code": 0, "elapsed_s": 0, "result": {},
        })

    report = _build_report(stages, output_dir, fmt)

    # Determine exit code: 1 if any validation errors, else 0
    val = next((s for s in stages if s["stage"] == "validate"), {})
    val_errors = val.get("result", {}).get("summary", {}).get("total_errors", 0)
    return (report, 1 if val_errors > 0 else 0)


def _build_report(stages: list[dict], output_dir: Path, fmt: str) -> dict:
    if fmt == "summary":
        return _summary_report(stages, output_dir)
    return {
        "output_dir": str(output_dir),
        "stages":     stages,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PDF → DITA conversion pipeline (5 stages)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("pdf", nargs="?", default=None, help="Input PDF file path")
    group.add_argument("--from-json", metavar="EXTRACTED_JSON",
                       help="Skip PDF extraction; start from an existing extracted.json")

    parser.add_argument("output_dir", help="Output directory for DITA files and reports")
    parser.add_argument("--map-title", default=None, help="Override root ditamap title")
    parser.add_argument("--skills-root", default=str(_DEFAULT_SKILLS_ROOT),
                        help="Path to the dita-skills repository root")
    parser.add_argument("--skip-review", action="store_true",
                        help="Skip Stage 5 (review_dita_guide.py) for faster runs")
    parser.add_argument("--format", choices=["full", "summary"], default="summary",
                        dest="fmt", help="Report verbosity (default: summary)")
    args = parser.parse_args()

    pdf_path       = Path(args.pdf)        if args.pdf        else None
    extracted_json = Path(args.from_json)  if args.from_json  else None
    output_dir     = Path(args.output_dir)
    skills_root    = Path(args.skills_root)

    report, exit_code = run_pipeline(
        pdf_path=pdf_path,
        extracted_json=extracted_json,
        output_dir=output_dir,
        skills_root=skills_root,
        map_title=args.map_title,
        skip_review=args.skip_review,
        fmt=args.fmt,
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
