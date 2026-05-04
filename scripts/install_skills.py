#!/usr/bin/env python3
"""
install_skills.py — Install DITA AI skills into Claude Code, Mistral Vibe,
                    or GitHub Copilot CLI skill directories.

Usage
-----
  python scripts/install_skills.py --target all --scope personal
  python scripts/install_skills.py --target claude --scope project
  python scripts/install_skills.py --target copilot --scope personal \\
      --skills validate-dita-topic,review-dita-guide
  python scripts/install_skills.py --list

Exit codes
----------
  0  All requested skills installed successfully.
  1  One or more skills failed to install.
  2  Usage error (bad arguments or unknown skill name).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Root of this repository (two levels up from scripts/install_skills.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Files / directories that are NOT skill folders
_NON_SKILL_DIRS = {
    ".github", ".venv", "__pycache__", "dtd", "tests", "scripts",
    "dita_skills.egg-info",
}

# ── Installation path templates ────────────────────────────────────────────
#
# {home}  → user's home directory
# {cwd}   → current working directory (for project-scope installs)
# {skill} → skill directory name (e.g. "validate-dita-topic")
#
# Per-tool, per-scope target directories:
INSTALL_PATHS: dict[str, dict[str, str]] = {
    "claude": {
        # Personal: works for both Claude Code and GitHub Copilot CLI
        "personal": "{home}/.claude/skills/{skill}",
        "project":  "{cwd}/.claude/skills/{skill}",
    },
    "vibe": {
        "personal": "{home}/.vibe/skills/{skill}",
        "project":  "{cwd}/.vibe/skills/{skill}",
    },
    "copilot": {
        # Copilot CLI also accepts ~/.claude/skills but has its own namespace
        "personal": "{home}/.copilot/skills/{skill}",
        "project":  "{cwd}/.github/skills/{skill}",
    },
}

# Friendly display names
_TARGET_LABELS = {
    "claude":  "Claude Code",
    "vibe":    "Mistral Vibe",
    "copilot": "GitHub Copilot CLI",
}


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

def _discover_skills(repo_root: Path) -> dict[str, Path]:
    """
    Return {skill-name: skill-directory-path} for every skill found in the
    repository.  A skill directory is any direct child of *repo_root* that
    contains a ``SKILL.md`` file and is not in ``_NON_SKILL_DIRS``.
    """
    skills: dict[str, Path] = {}
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in _NON_SKILL_DIRS:
            continue
        if (child / "SKILL.md").exists():
            skills[child.name] = child
    return skills


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _resolve_target_path(target: str, scope: str, skill_name: str) -> Path:
    """Return the absolute destination path for a skill install."""
    template = INSTALL_PATHS[target][scope]
    rendered = template.format(
        home=Path.home(),
        cwd=Path.cwd(),
        skill=skill_name,
    )
    return Path(rendered)


# ---------------------------------------------------------------------------
# Install helpers
# ---------------------------------------------------------------------------

def _install_skill(
    skill_name: str,
    skill_src: Path,
    dest: Path,
    overwrite: bool,
    dry_run: bool,
) -> tuple[bool, str, str]:
    """
    Copy *skill_src* to *dest*.

    Returns ``(success, message, status)`` where *status* is one of:
    - ``"ok"``      — installed (or would be, in dry-run mode)
    - ``"skipped"`` — dest already exists and --overwrite was not set
    - ``"error"``   — OS-level failure (permissions, disk full, etc.)
    """
    if dest.exists():
        if not overwrite:
            return False, f"  [SKIP]  {dest}  (already exists; use --overwrite)", "skipped"
        if not dry_run:
            shutil.rmtree(dest)

    if dry_run:
        return True, f"  [DRY-RUN]  {dest}", "ok"

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(skill_src), str(dest))
        return True, f"  [OK]  {dest}", "ok"
    except OSError as exc:
        return False, f"  [ERROR]  {dest}  ({exc})", "error"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install_skills.py",
        description=(
            "Install DITA AI skills into Claude Code, Mistral Vibe, or "
            "GitHub Copilot CLI skill directories."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--target",
        choices=["claude", "vibe", "copilot", "all"],
        default="all",
        help="AI tool to install skills for (default: all).",
    )
    p.add_argument(
        "--scope",
        choices=["personal", "project"],
        default="personal",
        help=(
            "Install for the current user (personal, default) or only for "
            "the current project (project)."
        ),
    )
    p.add_argument(
        "--skills",
        metavar="SKILL[,SKILL…]",
        help=(
            "Comma-separated list of skill names to install.  "
            "Defaults to all available skills."
        ),
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing skill directories.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without making any changes.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List available skills and exit.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output a machine-readable JSON report.",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    available = _discover_skills(_REPO_ROOT)

    # ── --list ─────────────────────────────────────────────────────────────
    if args.list:
        if args.json_output:
            print(json.dumps({"skills": list(available)}, indent=2))
        else:
            print("Available DITA skills:")
            for name in available:
                print(f"  • {name}")
        sys.exit(0)

    # ── Resolve requested skills ────────────────────────────────────────────
    if args.skills is not None:
        requested = [s.strip() for s in args.skills.split(",") if s.strip()]
        if not requested:
            print(
                "error: --skills requires at least one skill name.\n"
                "Run with --list to see available skills.",
                file=sys.stderr,
            )
            sys.exit(2)
        unknown   = [s for s in requested if s not in available]
        if unknown:
            print(
                f"error: unknown skill(s): {', '.join(unknown)}\n"
                f"Run with --list to see available skills.",
                file=sys.stderr,
            )
            sys.exit(2)
        to_install = {name: available[name] for name in requested}
    else:
        to_install = available

    # ── Resolve targets ─────────────────────────────────────────────────────
    targets = list(INSTALL_PATHS) if args.target == "all" else [args.target]

    # ── Install ─────────────────────────────────────────────────────────────
    report: list[dict] = []
    overall_ok = True

    for target in targets:
        label = _TARGET_LABELS[target]
        if not args.json_output:
            print(f"\n{'-' * 60}")
            print(f"Installing for {label}  [{args.scope}]")
            print(f"{'-' * 60}")

        for skill_name, skill_src in to_install.items():
            dest          = _resolve_target_path(target, args.scope, skill_name)
            ok, msg, status = _install_skill(
                skill_name, skill_src, dest,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )
            if not ok:
                overall_ok = False
            if not args.json_output:
                print(msg)
            report.append({
                "target":  target,
                "scope":   args.scope,
                "skill":   skill_name,
                "dest":    str(dest).replace("\\", "/"),
                "status":  status,
                "dry_run": args.dry_run,
            })

    # ── Output ───────────────────────────────────────────────────────────────
    if args.json_output:
        print(json.dumps({"results": report}, indent=2))
    else:
        installed = sum(1 for r in report if r["status"] == "ok")
        skipped   = sum(1 for r in report if r["status"] == "skipped")
        print(f"\n{'-' * 60}")
        prefix = "[DRY-RUN] Would have installed" if args.dry_run else "Installed"
        print(f"{prefix}: {installed}  |  Skipped: {skipped}")
        if not overall_ok and not args.dry_run:
            print(
                "\nTip: use --overwrite to replace existing skill directories.",
                file=sys.stderr,
            )

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
