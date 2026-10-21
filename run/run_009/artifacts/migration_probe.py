"""Back up the live Run 008 ledger and verify additive schema migration on its copy."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "agenthub_sp_invopt"))
from hub import Hub

SOURCE = ROOT / "agenthub_sp_invopt" / "runtime" / "sp_invopt.sqlite3"
TARGET = Path(__file__).resolve().parent / "private" / "run008_migration_probe.sqlite3"
if TARGET.exists():
    raise SystemExit("MIGRATION_PROBE_EXISTS_REFUSE_OVERWRITE")
source = sqlite3.connect(f"file:{SOURCE.as_posix()}?mode=ro", uri=True)
target = sqlite3.connect(TARGET)
source.backup(target)
source.close()
target.close()
hub = Hub(TARGET, workspace_root=ROOT)
with hub.connect() as db:
    version_column = "version" in {r["name"] for r in db.execute("PRAGMA table_info(artifacts)")}
    failures_table = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='failures'").fetchone())
    old_artifacts = db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    old_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
result = {"scope": "COPY_ONLY", "source": str(SOURCE), "copy": str(TARGET),
          "version_column": version_column, "failures_table": failures_table,
          "existing_artifacts": old_artifacts, "existing_events": old_events,
          "audit_hash_chain_valid": hub.verify_chain()}
assert version_column and failures_table and result["audit_hash_chain_valid"]
print(json.dumps(result, ensure_ascii=False, indent=2))
