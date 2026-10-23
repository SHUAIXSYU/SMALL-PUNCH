"""Register the read-only CAE audit in the existing AgentHub task."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HUB_DIR = ROOT / "agenthub_sp_invopt"
sys.path.insert(0, str(HUB_DIR))
from hub import Hub

TASK_ID = "1d0edf48-a744-4ce5-b8b3-a4e590f54021"
AGENT_ID = "CAE:cae-codex-20261021-632ffd48"
SESSION_ID = "aa78d383-febb-4b7e-99d5-2a9665e9ab6c"
DB = HUB_DIR / "runtime/sp_invopt.sqlite3"
LEASE_PATH = HUB_DIR / "runtime/cae_lease_run015_1d0edf48.json"
CAE_DIR = ROOT / "run/run_015/artifacts/private/cae"
RESULT_PATH = CAE_DIR / "result.json"
RECEIPT_PATH = CAE_DIR / "hub_receipt.json"
EXPECTED_INP_SHA = "fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


def main() -> None:
    require(not RESULT_PATH.exists() and not RECEIPT_PATH.exists(), "Output already exists")
    lease = json.loads(LEASE_PATH.read_text(encoding="utf-8"))
    hub = Hub(DB, lease_seconds=1800)
    identity = hub.session_identity(SESSION_ID)
    require(identity["agent_id"] == AGENT_ID and identity["role"] == "CAE", "Session mismatch")
    task = hub.task(TASK_ID)
    require(task is not None and task["execution_state"] == "CLAIMED", "Task not claimed")
    require(task["lease_session"] == SESSION_ID and lease["generation"] == task["generation"], "Lease mismatch")
    payload = json.loads(task["payload"])
    require(payload["run"] == "run_015" and payload["input"].endswith(".inp"), "Task scope mismatch")
    raw_path = CAE_DIR / "model_geometry_raw.json"
    report_path = CAE_DIR / "model_measurement_audit.md"
    script_path = ROOT / "run/run_015/artifacts/cae_scripts/inspect_existing_model.py"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    sources = raw["sources"]
    for source in sources:
        require(sha256(ROOT / source["path"]) == source["sha256"], "Source changed: " + source["path"])
    require(sources[0]["path"] == payload["input"] and sources[0]["sha256"] == EXPECTED_INP_SHA,
            "Candidate identity mismatch")
    require(raw["specimen"]["node_count"] == 670 and raw["specimen"]["cax4_element_count"] == 594,
            "Unexpected specimen topology")
    require(raw["punch"]["arc_radius_from_end"] == 0.00125, "Unexpected punch radius")
    require(raw["contact"]["mu"] == 0.1, "Unexpected contact friction")
    require(raw["step"]["static_values_initial_period_min_max"] == [0.01, 1.0, 1e-12, 0.1],
            "Unexpected Step data")
    report_text = report_path.read_text(encoding="utf-8")
    for phrase in ("10 mm", "0.5 mm", "1.25 mm", "UNKNOWN", "下模", "−1.2 mm"):
        require(phrase in report_text, "Report content missing: " + phrase)
    hub.heartbeat(lease)

    provenance = {
        "task_id": TASK_ID,
        "role": "CAE",
        "source_files": sources,
        "method": "Read-only INP node/set/segment/keyword parsing with historical JNL cross-check",
        "source_license": "Owner-provided SMALL-PUNCH project model; project-local audit",
        "science_boundary": "Model settings only; actual experimental correspondence and material validity NOT_EVALUATED",
    }
    artifacts = []
    for path, version, role in (
        (raw_path, "run015-cae-model-geometry-v1", "machine-readable extraction"),
        (report_path, "run015-cae-measurement-audit-v1", "facts/inferences/unknowns and minimum experimental questions"),
        (script_path, "run015-cae-readonly-parser-v1", "reproducible extraction script"),
    ):
        row = hub.artifact(TASK_ID, AGENT_ID, path, dict(provenance, artifact_role=role), version=version)
        artifacts.append({"artifact_id": row["artifact_id"],
                          "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": row["sha256"], "version": version})
    result = {
        "task_id": TASK_ID,
        "agent_id": AGENT_ID,
        "session_id": SESSION_ID,
        "generation": lease["generation"],
        "execution_status": "COMPLETED",
        "evidence_status": "RECORDED",
        "science_status": "NOT_EVALUATED",
        "model_audit_status": "MODEL_FACTS_VERIFIED_EXPERIMENT_MATCH_UNKNOWN",
        "candidate_sha256": EXPECTED_INP_SHA,
        "model_facts": {
            "specimen_radius_m": 0.005,
            "specimen_thickness_m": 0.0005,
            "punch_arc_radius_m": 0.00125,
            "clamp_annulus_radius_m": [0.002, 0.005],
            "explicit_die_part": False,
            "friction_coefficient": 0.1,
            "prescribed_punch_u2_end_m": -0.0012,
            "rp_outputs": ["U2", "RF2"],
        },
        "unit_basis": "N-m-Pa stated by user via MAIN; not encoded in INP",
        "open_items": [
            "actual specimen diameter/thickness and punch radius vs model",
            "actual lower die opening/edge fillet/fixture preload vs idealized clamp BC",
            "experimental displacement sensor, zero, compliance, force unit/sign and load history",
            "load XLSX and Origin curve provenance/unit conflict",
            "current edited CAE database equivalence to candidate INP",
        ],
        "artifacts": list(artifacts),
        "limitations": ["No new INP, CAE save, datacheck, Solver, queue action, or experiment assumption"],
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    row = hub.artifact(TASK_ID, AGENT_ID, RESULT_PATH,
                       dict(provenance, artifact_role="structured CAE audit result"),
                       version="run015-cae-result-v1")
    artifacts.append({"artifact_id": row["artifact_id"],
                      "path": str(RESULT_PATH.relative_to(ROOT)).replace("\\", "/"),
                      "sha256": row["sha256"], "version": "run015-cae-result-v1"})
    # The on-disk result remains immutable after registration; the Hub result includes its artifact row.
    hub.finish(lease, result, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    message = hub.message(TASK_ID, AGENT_ID, "MAIN", result, "run015-cae-model-audit-completed-v1")
    terminal = hub.task(TASK_ID)
    require(terminal["execution_state"] == "COMPLETED", "Hub completion not persisted")
    receipt = {
        "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "task_id": TASK_ID,
        "agent_id": AGENT_ID,
        "session_id": SESSION_ID,
        "generation": lease["generation"],
        "execution_state": terminal["execution_state"],
        "evidence_state": terminal["evidence_state"],
        "science_state": terminal["science_state"],
        "artifacts": artifacts,
        "main_message_id": message["message_id"],
        "audit_hash_chain_valid": hub.verify_chain(),
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
