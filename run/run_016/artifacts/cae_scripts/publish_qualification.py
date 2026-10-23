"""Register and return the run_016 read-only CAE qualification through AgentHub."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub

TASK_ID = "5e024e04-4f41-4fd8-a199-15b632ce6e79"
AGENT_ID = "CAE:cae-codex-20261021-632ffd48"
SESSION_ID = "aa78d383-febb-4b7e-99d5-2a9665e9ab6c"
DB = ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3"
LEASE_PATH = ROOT / "agenthub_sp_invopt/runtime/cae_lease_run016_5e024e04.json"
RESULT_PATH = ROOT / "run/run_016/artifacts/private/cae/qualification_result.json"
RECEIPT_PATH = ROOT / "run/run_016/artifacts/private/cae/agenthub_receipt.json"


def main() -> None:
    if RECEIPT_PATH.exists():
        raise SystemExit("Refuse to overwrite prior AgentHub receipt")
    hub = Hub(DB, lease_seconds=1800)
    identity = hub.session_identity(SESSION_ID)
    if identity["agent_id"] != AGENT_ID or identity["role"] != "CAE":
        raise RuntimeError("CAE session identity changed")
    lease = json.loads(LEASE_PATH.read_text(encoding="utf-8"))
    if lease["task_id"] != TASK_ID or lease["agent_id"] != AGENT_ID or lease["session_id"] != SESSION_ID:
        raise RuntimeError("Claim lease identity mismatch")
    task = hub.task(TASK_ID)
    if task is None or task["assigned_role"] != "CAE" or task["execution_state"] != "CLAIMED":
        raise RuntimeError("Expected claimed CAE task")
    if task["lease_agent"] != AGENT_ID or task["lease_session"] != SESSION_ID:
        raise RuntimeError("Task lease no longer belongs to this session")
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result["task_id"] != TASK_ID or result["agent_id"] != AGENT_ID or result["session_id"] != SESSION_ID:
        raise RuntimeError("Result identity mismatch")
    hub.heartbeat(lease)
    registered = []
    for rel in (*result["artifacts"], "run/run_016/artifacts/private/cae/qualification_result.json",
                "run/run_016/artifacts/cae_scripts/publish_qualification.py"):
        item = hub.artifact(
            TASK_ID, AGENT_ID, ROOT / rel,
            {"source": "run_016 CAE read-only geometry qualification",
             "scope": "explicit SPT inputs only; no heldout validation access", "relative_path": rel},
            version="run016-v1",
        )
        registered.append({"path": rel, "sha256": item["sha256"], "artifact_id": item["artifact_id"]})
    hub.finish(lease, result, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    message_body = {
        "task_id": TASK_ID,
        "state": "AUDIT_COMPLETED",
        "qualification": result["qualification"],
        "evidence_state": "RECORDED",
        "science_state": "NOT_EVALUATED",
        "input_sha256": result["input_identity"]["sha256"],
        "report": "run/run_016/artifacts/private/cae/geometry_qualification.md",
        "structured_result": "run/run_016/artifacts/private/cae/qualification_result.json",
        "blockers": [f["code"] for f in result["findings"] if f["state"] == "BLOCKED"],
        "unknowns": [f["code"] for f in result["findings"] if f["state"] == "UNKNOWN"],
        "solver_or_queue_action": False,
    }
    msg = hub.message(TASK_ID, AGENT_ID, "MAIN", message_body,
                      "run016-cae-geometry-qualification-v1")
    receipt = {
        "recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "task_id": TASK_ID,
        "agent_id": AGENT_ID,
        "session_id": SESSION_ID,
        "execution_state": hub.task(TASK_ID)["execution_state"],
        "qualification": result["qualification"],
        "artifacts": registered,
        "message_id": msg["message_id"],
        "message_key": "run016-cae-geometry-qualification-v1",
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task_id": TASK_ID, "execution_state": receipt["execution_state"],
                      "qualification": receipt["qualification"], "artifacts_registered": len(registered),
                      "message_id": receipt["message_id"], "receipt_path": str(RECEIPT_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
