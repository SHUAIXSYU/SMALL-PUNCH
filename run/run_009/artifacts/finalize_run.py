"""Write Run 009 metadata and a small-file SHA-256 manifest once."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run" / "run_009"
SH = timezone(timedelta(hours=8))


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


paths = [
    "agenthub_sp_invopt/hub.py", "agenthub_sp_invopt/cli.py", "agenthub_sp_invopt/CLI.md",
    "agenthub_sp_invopt/README.md", "run/run_009/summary.md",
    "run/run_009/artifacts/cli_acceptance.py", "run/run_009/artifacts/cli_acceptance.log",
    "run/run_009/artifacts/test_runtime_extensions.py", "run/run_009/artifacts/extensions_before.log",
    "run/run_009/artifacts/extensions_final.log", "run/run_009/artifacts/reuse_regression_final.log",
    "run/run_009/artifacts/migration_probe.py", "run/run_009/artifacts/migration_probe.log",
    "run/run_009/artifacts/activate_upgrade.py", "run/run_009/artifacts/activation_report.json",
    "run/run_009/artifacts/activation.log", "run/run_009/artifacts/finalize_run.py",
    "run/run_009/checkpoints/initial_git.json", "run/README.md", "status/PROJECT_STATUS.md",
]
manifest = {"schema_version": "1.0", "files": [{"path": rel, "sha256": digest(ROOT / rel)} for rel in paths]}
(RUN / "artifacts" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
now = datetime.now(SH).isoformat()
pilot_root = Path("D:/Projects/abqjobpilot")
checkpoint = {
    "observed_at": now,
    "git_branch": git("branch", "--show-current"), "git_head": git("rev-parse", "HEAD"),
    "git_remote": git("remote", "-v"), "working_tree": git("status", "--short"),
    "abqjobpilot_head": git("rev-parse", "HEAD", cwd=pilot_root),
    "abqjobpilot_working_tree": git("status", "--short", cwd=pilot_root),
    "stage5_modified_by_this_run": False, "solver_started": False, "queue_written": False,
    "commit_performed": False, "push_performed": False,
}
(RUN / "checkpoints" / "final_state.json").write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
run = {
    "schema_version": "1.0", "run_id": "run_009", "stage": "AgentHub Runtime completion",
    "objective": "Persisted, auditable SP-InvOpt coordination with CLI and shared SQLite acceptance",
    "status": "WARNING", "start_time": "2026-10-21T15:43:59+08:00", "end_time": now,
    "python_interpreter": sys.executable, "python_version": sys.version.split()[0],
    "git_branch": checkpoint["git_branch"], "git_head": checkpoint["git_head"],
    "inputs": ["agenthub_sp_invopt/hub.py", "run/run_008/run.json", "run/run_008/summary.md",
               "E:/Projects/Stage-5/RL-LAM-AgentHub (read-only)", "D:/Projects/abqjobpilot (read-only)"],
    "outputs": ["agenthub_sp_invopt/cli.py", "agenthub_sp_invopt/CLI.md", "run/run_009/summary.md",
                "run/run_009/artifacts/manifest.json", "run/run_009/checkpoints/final_state.json"],
    "software_checks": {"run008_regression": "8 PASS", "run009_extensions": "8 PASS", "cli_shared_sqlite_handoff": "PASS",
                        "sqlite_migration": "PASS", "scientific_validation": "NOT_EVALUATED"},
    "cross_codex_auto_wakeup": "NOT_IMPLEMENTED", "solver_started": False, "queue_written": False,
    "commit_performed": False, "push_performed": False,
}
(RUN / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"run_id": "run_009", "status": "WARNING", "manifest_files": len(paths), "end_time": now}, ensure_ascii=False))
