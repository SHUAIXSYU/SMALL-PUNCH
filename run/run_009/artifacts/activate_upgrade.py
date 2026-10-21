"""Back up and apply the additive AgentHub schema update to the live ledger."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "agenthub_sp_invopt"))
from hub import Hub

SOURCE = ROOT / "agenthub_sp_invopt" / "runtime" / "sp_invopt.sqlite3"
PRIVATE = Path(__file__).resolve().parent / "private"
BACKUP = PRIVATE / "sp_invopt_pre_run009.sqlite3"
REPORT = Path(__file__).resolve().parent / "activation_report.json"
if BACKUP.exists() or REPORT.exists():
    raise SystemExit("ACTIVATION_OUTPUT_EXISTS_REFUSE_OVERWRITE")
if not SOURCE.is_file():
    raise SystemExit("LIVE_HUB_DB_MISSING")
source = sqlite3.connect(f"file:{SOURCE.as_posix()}?mode=ro", uri=True)
source.row_factory = sqlite3.Row
before = {name: source.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
          for name in ("tasks", "artifacts", "messages", "events")}
backup = sqlite3.connect(BACKUP)
source.backup(backup)
backup.close()
source.close()
backup_hash = hashlib.sha256(BACKUP.read_bytes()).hexdigest()
hub = Hub(SOURCE, workspace_root=ROOT)
with hub.connect() as db:
    after = {name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
             for name in ("tasks", "artifacts", "messages", "events")}
    version = "version" in {r["name"] for r in db.execute("PRAGMA table_info(artifacts)")}
    failures = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='failures'").fetchone())
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
result = {"observed_at": datetime.now(timezone.utc).astimezone().isoformat(),
          "database": str(SOURCE), "backup": str(BACKUP), "backup_sha256": backup_hash,
          "counts_before": before, "counts_after": after, "artifact_version_column": version,
          "failure_diagnostics_table": failures, "sqlite_integrity_check": integrity,
          "audit_hash_chain_valid": hub.verify_chain()}
assert before == after and version and failures and integrity == "ok" and result["audit_hash_chain_valid"]
REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
