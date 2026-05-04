"""
Tests for scripts/install_skills.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the module without requiring it to be installed as a package
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

def _load_module():
    spec = importlib.util.spec_from_file_location(
        "install_skills",
        _SCRIPTS_DIR / "install_skills.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_mod = _load_module()

discover_skills       = _mod._discover_skills
resolve_target_path   = _mod._resolve_target_path
install_skill         = _mod._install_skill
INSTALL_PATHS         = _mod.INSTALL_PATHS
_REPO_ROOT            = _mod._REPO_ROOT
_TARGET_LABELS        = _mod._TARGET_LABELS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(tmp_path: Path, name: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\nBody.\n")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "run.py").write_text("# script\n")
    return skill_dir


# ===========================================================================
# 1. Skill discovery
# ===========================================================================

class TestDiscoverSkills:
    def test_discovers_skills_with_skill_md(self, tmp_path):
        _make_skill(tmp_path, "skill-a")
        _make_skill(tmp_path, "skill-b")
        result = discover_skills(tmp_path)
        assert "skill-a" in result
        assert "skill-b" in result

    def test_ignores_dirs_without_skill_md(self, tmp_path):
        (tmp_path / "not-a-skill").mkdir()
        (tmp_path / "not-a-skill" / "README.md").write_text("hi")
        result = discover_skills(tmp_path)
        assert "not-a-skill" not in result

    def test_ignores_non_skill_dirs(self, tmp_path):
        for name in ("dtd", "tests", "scripts", ".github", "__pycache__"):
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text("---\n---\n")  # would match otherwise
        result = discover_skills(tmp_path)
        assert result == {}

    def test_ignores_dotfiles(self, tmp_path):
        d = tmp_path / ".hidden-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("---\n---\n")
        result = discover_skills(tmp_path)
        assert ".hidden-skill" not in result

    def test_returns_path_objects(self, tmp_path):
        _make_skill(tmp_path, "my-skill")
        result = discover_skills(tmp_path)
        assert isinstance(result["my-skill"], Path)

    def test_live_repo_has_expected_skills(self):
        """The real repo must contain all known skills."""
        expected = {
            "validate-dita-topic", "validate-ditamap", "validate-bookmap",
            "generate-dita-topic", "generate-ditamap", "generate-bookmap",
            "dita-best-practices", "ditaval-helper", "refactor-dita-content",
            "xslt-dita-helper", "review-dita-guide",
        }
        result = discover_skills(_REPO_ROOT)
        assert expected.issubset(set(result))


# ===========================================================================
# 2. Path resolution
# ===========================================================================

class TestResolveTargetPath:
    def test_claude_personal_contains_home(self):
        p = resolve_target_path("claude", "personal", "my-skill")
        assert str(Path.home()) in str(p) or "~" in str(p).replace("\\", "/")
        assert "my-skill" in str(p)

    def test_claude_project_uses_cwd(self):
        p = resolve_target_path("claude", "project", "my-skill")
        assert str(Path.cwd()) in str(p)
        assert ".claude" in str(p)
        assert "my-skill" in str(p)

    def test_vibe_personal_path(self):
        p = resolve_target_path("vibe", "personal", "test-skill")
        assert ".vibe" in str(p).replace("\\", "/")
        assert "test-skill" in str(p)

    def test_vibe_project_path(self):
        p = resolve_target_path("vibe", "project", "test-skill")
        assert ".vibe" in str(p).replace("\\", "/")
        assert str(Path.cwd()) in str(p)

    def test_copilot_personal_path(self):
        p = resolve_target_path("copilot", "personal", "test-skill")
        assert ".copilot" in str(p).replace("\\", "/")
        assert "test-skill" in str(p)

    def test_copilot_project_path(self):
        p = resolve_target_path("copilot", "project", "test-skill")
        assert ".github" in str(p).replace("\\", "/")
        assert "test-skill" in str(p)

    def test_all_targets_covered(self):
        """Every target in INSTALL_PATHS must resolve without raising."""
        for target in INSTALL_PATHS:
            for scope in ("personal", "project"):
                p = resolve_target_path(target, scope, "x")
                assert isinstance(p, Path)


# ===========================================================================
# 3. Install logic
# ===========================================================================

class TestInstallSkill:
    def test_copies_skill_directory(self, tmp_path):
        src  = _make_skill(tmp_path / "src", "my-skill")
        dest = tmp_path / "dest" / "my-skill"
        ok, msg, status = install_skill("my-skill", src, dest, overwrite=False, dry_run=False)
        assert ok is True
        assert status == "ok"
        assert dest.exists()
        assert (dest / "SKILL.md").exists()
        assert (dest / "scripts" / "run.py").exists()

    def test_copies_nested_files(self, tmp_path):
        src = _make_skill(tmp_path / "src", "sk")
        (src / "references").mkdir()
        (src / "references" / "rules.md").write_text("rules")
        dest = tmp_path / "dest" / "sk"
        ok, _, status = install_skill("sk", src, dest, overwrite=False, dry_run=False)
        assert ok
        assert status == "ok"
        assert (dest / "references" / "rules.md").exists()

    def test_skip_when_dest_exists_no_overwrite(self, tmp_path):
        src  = _make_skill(tmp_path / "src", "sk")
        dest = tmp_path / "dest" / "sk"
        dest.mkdir(parents=True)
        (dest / "old.txt").write_text("old")
        ok, msg, status = install_skill("sk", src, dest, overwrite=False, dry_run=False)
        assert ok is False
        assert status == "skipped"
        assert "SKIP" in msg.upper()
        assert (dest / "old.txt").exists()  # untouched

    def test_overwrite_replaces_existing(self, tmp_path):
        src  = _make_skill(tmp_path / "src", "sk")
        dest = tmp_path / "dest" / "sk"
        dest.mkdir(parents=True)
        (dest / "old.txt").write_text("old")
        ok, msg, status = install_skill("sk", src, dest, overwrite=True, dry_run=False)
        assert ok is True
        assert status == "ok"
        assert not (dest / "old.txt").exists()
        assert (dest / "SKILL.md").exists()

    def test_dry_run_does_not_copy(self, tmp_path):
        src  = _make_skill(tmp_path / "src", "sk")
        dest = tmp_path / "dest" / "sk"
        ok, msg, status = install_skill("sk", src, dest, overwrite=False, dry_run=True)
        assert ok is True
        assert status == "ok"
        assert not dest.exists()
        assert "DRY" in msg.upper()

    def test_dry_run_on_existing_reports_ok(self, tmp_path):
        """Dry-run with --overwrite on existing dest should still say OK."""
        src  = _make_skill(tmp_path / "src", "sk")
        dest = tmp_path / "dest" / "sk"
        dest.mkdir(parents=True)
        ok, msg, status = install_skill("sk", src, dest, overwrite=True, dry_run=True)
        assert ok is True
        assert status == "ok"
        assert "DRY" in msg.upper()

    def test_creates_parent_directories(self, tmp_path):
        src  = _make_skill(tmp_path / "src", "sk")
        dest = tmp_path / "a" / "b" / "c" / "sk"
        ok, _, status = install_skill("sk", src, dest, overwrite=False, dry_run=False)
        assert ok
        assert status == "ok"
        assert dest.exists()

    def test_oserror_returns_error_status(self, tmp_path):
        """A file masquerading as the dest directory triggers OSError → status 'error'."""
        src = _make_skill(tmp_path / "src", "sk")
        # Create a FILE at the parent path so mkdir/copytree fails
        blocker = tmp_path / "dest"
        blocker.write_text("not a directory")
        dest = blocker / "sk"          # invalid: parent is a file, not a dir
        ok, msg, status = install_skill("sk", src, dest, overwrite=False, dry_run=False)
        assert ok is False
        assert status == "error"
        assert "ERROR" in msg.upper()


# ===========================================================================
# 4. CLI integration (via subprocess)
# ===========================================================================

class TestCLI:
    """Run install_skills.py as a subprocess to test the full CLI path."""

    _script = str(_SCRIPTS_DIR / "install_skills.py")

    def _run(self, *args, **kwargs):
        import subprocess
        result = subprocess.run(
            [sys.executable, self._script, *args],
            capture_output=True, text=True, **kwargs
        )
        return result

    def test_list_exits_zero(self):
        r = self._run("--list")
        assert r.returncode == 0

    def test_list_json(self):
        r = self._run("--list", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "skills" in data
        assert len(data["skills"]) >= 11

    def test_dry_run_all_personal_exits_zero(self, tmp_path):
        """Dry-run install to personal dirs must exit 0 and make no FS changes.

        HOME/USERPROFILE are redirected to tmp_path so the test never touches
        the real user profile and is fully isolated from other test runs.
        """
        import os
        isolated_env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
        r = self._run(
            "--target", "all", "--scope", "personal", "--dry-run",
            env=isolated_env,
        )
        assert r.returncode == 0
        assert "DRY-RUN" in r.stdout
        # Nothing should have been created under tmp_path
        assert not list(tmp_path.iterdir())

    def test_dry_run_specific_skill(self):
        r = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic", "--dry-run",
        )
        assert r.returncode == 0
        assert "validate-dita-topic" in r.stdout

    def test_unknown_skill_exits_2(self):
        r = self._run("--skills", "no-such-skill-xyz")
        assert r.returncode == 2
        assert "unknown" in r.stderr.lower()

    def test_empty_skills_arg_exits_2(self):
        """--skills with an empty/whitespace-only value must exit 2, not silently succeed."""
        r = self._run("--skills", "")
        assert r.returncode == 2
        assert "skills" in r.stderr.lower()

    def test_json_output_structure(self):
        r = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic", "--dry-run", "--json",
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "results" in data
        result = data["results"][0]
        assert result["skill"] == "validate-dita-topic"
        assert result["target"] == "claude"
        assert result["scope"] == "project"
        assert result["dry_run"] is True
        assert result["status"] in ("ok", "skipped", "error")  # full set of valid statuses

    def test_json_status_ok_on_fresh_install(self, tmp_path):
        r = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic", "--json",
            cwd=str(tmp_path),
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["results"][0]["status"] == "ok"

    def test_json_status_skipped_on_second_install(self, tmp_path):
        self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic",
            cwd=str(tmp_path),
        )
        r = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic", "--json",
            cwd=str(tmp_path),
        )
        data = json.loads(r.stdout)
        assert data["results"][0]["status"] == "skipped"

    def test_install_project_scope_in_temp_dir(self, tmp_path):
        """Install to a real temp directory (project scope, claude only)."""
        r = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic",
            cwd=str(tmp_path),
        )
        assert r.returncode == 0
        dest = tmp_path / ".claude" / "skills" / "validate-dita-topic"
        assert dest.exists()
        assert (dest / "SKILL.md").exists()

    def test_overwrite_flag(self, tmp_path):
        """Second install with --overwrite must succeed."""
        r1 = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic",
            cwd=str(tmp_path),
        )
        assert r1.returncode == 0
        r2 = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic", "--overwrite",
            cwd=str(tmp_path),
        )
        assert r2.returncode == 0

    def test_no_overwrite_exits_1_when_exists(self, tmp_path):
        """Without --overwrite, re-install exits 1 (skipped → failure)."""
        # First install
        self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic",
            cwd=str(tmp_path),
        )
        # Second install without --overwrite
        r2 = self._run(
            "--target", "claude", "--scope", "project",
            "--skills", "validate-dita-topic",
            cwd=str(tmp_path),
        )
        assert r2.returncode == 1
