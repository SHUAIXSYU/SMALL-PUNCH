"""Resume run_039 dispatch after an AgentHub artifact lease guard rejection."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_039"
ART = RUN / "artifacts"
PRIVATE = ART / "private"
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def now():
    return datetime.now().astimezone().isoformat()


def main():
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert not (RUN / "run.json").exists()
    assert (PRIVATE / "execution_audit.json").is_file()
    dispatch = read(ART / "odb_task_payload.json")
    audit = read(PRIVATE / "execution_audit.json")
    assert dispatch["execution_audit_sha256"] == sha(PRIVATE / "execution_audit.json")
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run039-doe-audit")
    odb = hub.create_task(main["agent_id"], "ODB", "revalidate_twenty_doe_and_extract_d09_replacement",
                          dispatch, "run039-odb-twenty-point-handoff-v1")
    review_payload = {"run": "run_039", "odb_task_id": odb["task_id"],
                      "execution_audit": "run/run_039/artifacts/private/execution_audit.json",
                      "loss_version": "run017-exploratory-fd-v1"}
    review = hub.create_task(main["agent_id"], "MAIN", "review_twenty_two_point_doe_and_bo_de_readiness",
                             review_payload, "run039-main-doe-review-v1", depends=(odb["task_id"],))
    audit_task = hub.create_task(main["agent_id"], "MAIN", "register_frozen_execution_audit",
                                 {"run": "run_039", "odb_task_id": odb["task_id"],
                                  "audit_sha256": sha(PRIVATE / "execution_audit.json")},
                                 "run039-main-execution-audit-v1")
    lease = hub.claim(audit_task["task_id"], main, "run039-main-audit-claim-v1")
    save(PRIVATE / "main_audit_lease.json", lease)
    for path in (PRIVATE / "execution_audit.json", ART / "odb_task_payload.json"):
        hub.artifact(audit_task["task_id"], main["agent_id"], path,
                     {"run": "run_039", "purpose": "public execution audit and real ODB handoff"},
                     version="run039-execution-audit-v1")
    hub.finish(lease, {"status": "AUDIT_REGISTERED", "odb_task_id": odb["task_id"]},
               evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    save(ART / "task_ids.json", {"odb_task_id": odb["task_id"],
                                 "main_task_id": review["task_id"],
                                 "audit_task_id": audit_task["task_id"],
                                 "main_identity": main})
    start = read(RUN / "checkpoints/start.json")
    data = {"schema_version": "1.0", "run_id": "run_039",
            "stage": "DOE result audit and optimization readiness",
            "objective": "Audit original 20 attempts and replacement D09; produce 22-point exploratory dataset",
            "status": "RUNNING", "start_time": start["at"], "end_time": None,
            "git_branch": start["git"]["branch"], "git_head": start["git"]["head"],
            "git": start["git"], "python_interpreter": sys.executable,
            "inputs": [{"path": "run/run_033/artifacts/prepared_batch.json", "role": "frozen DOE"},
                       {"path": "run/run_033/artifacts/queue_manifest.json", "role": "original queue manifest"},
                       {"path": "run/run_034/artifacts/private/odb/manifest.json", "role": "prior real ODB extraction"}],
            "outputs": [{"path": "run/run_039/artifacts/private/execution_audit.json", "role": "fresh public execution audit"},
                        {"path": "run/run_039/artifacts/odb_task_payload.json", "role": "ODB task handoff"}],
            "validation": [{"check": "public_execution_audit", "status": "PASS",
                            "evidence": "19 original completed, original D09 interrupted, distinct replacement completed"},
                           {"check": "AgentHub_artifact_registration", "status": "PASS",
                            "evidence": "Recovered from initial ARTIFACT_LEASE_REQUIRED by claiming MAIN audit task"},
                           {"check": "ODB_and_MAIN_review", "status": "PENDING",
                            "evidence": "Formal AgentHub tasks created"}],
            "errors": [{"code": "ARTIFACT_LEASE_REQUIRED", "severity": "RECOVERED",
                        "message": "Initial attempt to attach MAIN evidence to unclaimed ODB task was denied; no artifact was attached; recovered via dedicated MAIN audit task"}]}
    save(RUN / "run.json", data)
    (RUN / "summary.md").write_text("# run_039 — DOE 结果与优化准入\n\nRUNNING：执行审计完成；等待真实 ODB Agent 领取与 MAIN 复核。\n", encoding="utf-8")
    print(json.dumps({"status": "DISPATCH_READY", "odb_task_id": odb["task_id"],
                      "main_task_id": review["task_id"], "audit_task_id": audit_task["task_id"],
                      "original_completed": audit["original_software_completed"],
                      "original_interrupted": audit["original_interrupted"],
                      "replacement_completed": audit["replacement_software_completed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
