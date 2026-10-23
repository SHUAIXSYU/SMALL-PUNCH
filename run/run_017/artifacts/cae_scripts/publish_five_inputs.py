"""Register run_017 CAE evidence and send the bounded result to MAIN."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub

TASK_ID = "64ade6c7-71f6-40ea-9ecc-b70f459773fb"
AGENT_ID = "CAE:cae-codex-20261021-632ffd48"
SESSION_ID = "aa78d383-febb-4b7e-99d5-2a9665e9ab6c"
LEASE = ROOT / "agenthub_sp_invopt/runtime/cae_lease_run017_64ade6c7.json"
MANIFEST = ROOT / "run/run_017/artifacts/cae_candidate_manifest.json"
RESULT = ROOT / "run/run_017/artifacts/private/cae/agenthub_result.json"
VERIFICATION = ROOT / "run/run_017/artifacts/private/cae/verification.json"
RECEIPT = ROOT / "run/run_017/artifacts/private/cae/agenthub_receipt.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if RECEIPT.exists():
        raise SystemExit("Refuse to overwrite prior receipt")
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=1800)
    identity = hub.session_identity(SESSION_ID)
    if identity != {"agent_id": AGENT_ID, "role": "CAE", "session_id": SESSION_ID}:
        raise RuntimeError("Real CAE session identity mismatch")
    lease = json.loads(LEASE.read_text(encoding="utf-8"))
    if any(lease[k] != v for k, v in (("task_id", TASK_ID), ("agent_id", AGENT_ID),
                                      ("session_id", SESSION_ID))):
        raise RuntimeError("Lease identity mismatch")
    task = hub.task(TASK_ID)
    if task is None or task["assigned_role"] != "CAE" or task["execution_state"] != "CLAIMED" or task["lease_agent"] != AGENT_ID or task["lease_session"] != SESSION_ID:
        raise RuntimeError("Expected live claimed CAE task")
    for action in ("generate_inp", "verify_inp"):
        hub.require_approval(TASK_ID, action)
    payload = json.loads(task["payload"])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    if manifest["task_id"] != TASK_ID or result["task_id"] != TASK_ID or verification["task_id"] != TASK_ID:
        raise RuntimeError("Task identity mismatch in outputs")
    if sha(ROOT / payload["design"]) != payload["design_sha256"] or sha(ROOT / payload["baseline_inp"]) != payload["baseline_sha256"]:
        raise RuntimeError("Frozen source changed")
    if len(manifest["points"]) != 5 or verification["status"] != "PASS_STATIC_SCOPE_ONLY":
        raise RuntimeError("Five verified points required")
    for point in manifest["points"]:
        if sha(ROOT / point["inp_path"]) != point["sha256"]:
            raise RuntimeError("INP SHA mismatch")
        if any((ROOT / point["working_dir"]).iterdir()):
            raise RuntimeError("Work directory no longer empty")
    hub.heartbeat(lease)
    common = [
        "run/run_017/artifacts/cae_candidate_manifest.json",
        "run/run_017/artifacts/private/cae/static_checks.json",
        "run/run_017/artifacts/private/cae/verification.json",
        "run/run_017/artifacts/private/cae/qualification_report.md",
        "run/run_017/artifacts/private/cae/operation_log.json",
        "run/run_017/artifacts/private/cae/agenthub_result.json",
        "run/run_017/artifacts/cae_scripts/generate_five_inputs.py",
        "run/run_017/artifacts/cae_scripts/verify_five_inputs.py",
        "run/run_017/artifacts/cae_scripts/publish_five_inputs.py",
    ]
    files = common + [p[key] for p in manifest["points"] for key in ("inp_path", "parameters_path")]
    if len(files) != 19 or len(set(files)) != 19:
        raise RuntimeError("Expected 19 unique evidence files")
    records = []
    for rel in files:
        artifact = hub.artifact(TASK_ID, AGENT_ID, ROOT / rel,
                                {"run_id": "run_017", "relative_path": rel,
                                 "baseline_sha256": payload["baseline_sha256"],
                                 "design_sha256": payload["design_sha256"],
                                 "scope": "five offline material-only INP variants; no solver"},
                                version="run017-five-point-v1")
        records.append({"path": rel, "sha256": artifact["sha256"],
                        "artifact_id": artifact["artifact_id"]})
    hub.finish(lease, result, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    message = {"task_id": TASK_ID, "execution_result": result["execution_result"],
               "candidate_count": 5, "manifest": "run/run_017/artifacts/cae_candidate_manifest.json",
               "manifest_sha256": sha(MANIFEST),
               "verification": "run/run_017/artifacts/private/cae/verification.json",
               "verification_status": verification["status"],
               "input_hashes": [{"point_id": p["point_id"], "job_name": p["job_name"],
                                 "inp_path": p["inp_path"], "sha256": p["sha256"]}
                                for p in manifest["points"]],
               "scope": "idealised clamping baseline only; future PEEQ adequacy UNKNOWN",
               "preflight_dry_run": "MAIN_RESPONSIBILITY_NOT_RUN_BY_CAE",
               "solver_or_queue_action": False,
               "science_state": "NOT_EVALUATED"}
    msg = hub.message(TASK_ID, AGENT_ID, "MAIN", message,
                      "run017-cae-five-inputs-completed-v1")
    receipt = {"recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
               "task_id": TASK_ID, "agent_id": AGENT_ID, "session_id": SESSION_ID,
               "execution_state": hub.task(TASK_ID)["execution_state"],
               "registered_artifacts": records,
               "message_id": msg["message_id"],
               "message_key": "run017-cae-five-inputs-completed-v1"}
    with RECEIPT.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"task_id": TASK_ID, "execution_state": receipt["execution_state"],
                      "artifacts": len(records), "message_id": msg["message_id"],
                      "receipt": str(RECEIPT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
