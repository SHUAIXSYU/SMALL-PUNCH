"""Register the exact 20-job authorization and deliver 14 INPs to real CAE."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_033"
A = RUN / "artifacts"
P = A / "private"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def save_once(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    assert not (A / "task_ids.json").exists()
    doe_file = A / "doe_design.json"
    doe = read(doe_file)
    assert doe["version"] == "run033-twenty-doe-design-v1"
    assert len(doe["new_points"]) == 14 and len(doe["existing_frozen"]) == 6
    assert len(doe["batch_order"]) == 20
    batch_file = ROOT / "run/run_030/artifacts/prepared_batch.json"
    batch = read(batch_file)
    assert doe["run030_batch_sha256"] == sha(batch_file)
    assert [p["point_id"] for p in batch["points"][2:]] == [p["point_id"] for p in doe["existing_frozen"]]
    assert read(P / "i02_execution_audit.json")["status"] == "I02_EXECUTION_IDENTITY_PASS_WITH_WARNINGS"
    scope = {"run": "run_033", "authorization_source": "Explicit user 20-job batch DOE authorization in current conversation",
             "project_id": batch["project_id"], "numeric_version": batch["numeric_version"],
             "loss_version": batch["loss_version"], "doe_design_sha256": sha(doe_file),
             "run030_batch_sha256": sha(batch_file),
             "exact_new_job_count": 20,
             "six_reused_frozen_point_ids": [p["point_id"] for p in doe["existing_frozen"]],
             "fourteen_new_point_ids": [p["point_id"] for p in doe["new_points"]],
             "queue_order": doe["batch_order"], "maximum_attempts_per_job": 1,
             "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
             "automatic_retries": 0, "solver_start": "USER_GUI_ONLY_ONCE_AFTER_FULL_QUEUE",
             "runner_mode": "SINGLE_RUNNER_SERIAL_BATCH",
             "auto_stop": "UNAVAILABLE_USER_ACCEPTS_POSSIBLE_CONTINUATION_AFTER_JOB_FAILURE",
             "failure_loss": None, "no_replacement_jobs": True,
             "I01_I02_excluded_from_new_jobs": True,
             "sealed_tensile_data_use": "FORBIDDEN",
             "BO_DE_RL_execution": "FORBIDDEN"}
    save_once(A / "authorization_scope.json", scope)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=7200)
    main = hub.register("MAIN", "codex-main-run033-batch-doe")
    budget = hub.create_task(main["agent_id"], "MAIN", "authorize_20_job_batch_doe",
                             scope, "run033-authorize-twenty-batch-v1")["task_id"]
    budget_lease = hub.claim(budget, main, "run033-budget-claim-v1")
    hub.artifact(budget, main["agent_id"], A / "authorization_scope.json",
                 {"run": "run_033", "source": "explicit current user authorization"}, version="run033-v1")
    hub.artifact(budget, main["agent_id"], doe_file,
                 {"run": "run_033", "source": "pre-generation DOE frozen"}, version="run033-v1")
    hub.finish(budget_lease, scope, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    cae_payload = {"run": "run_033", "project_root": str(ROOT),
                   "doe_design": "run/run_033/artifacts/doe_design.json",
                   "doe_design_sha256": sha(doe_file),
                   "numeric_contract": "run/run_030/artifacts/model_contract.json",
                   "numeric_contract_sha256": sha(ROOT / "run/run_030/artifacts/model_contract.json"),
                   "source_inp": "run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp",
                   "source_sha256": batch["source_inp_sha256"],
                   "hollomon_generator": "inverse/hollomon.py",
                   "hollomon_generator_sha256": batch["generator_sha256"],
                   "reuse_protocol": "run/run_030/artifacts/cae_candidate_manifest.json",
                   "new_points": doe["new_points"],
                   "required": [
                       "Real CAE Codex session claims this AgentHub task and heartbeats; do not impersonate CAE with MAIN worker",
                       "Generate exactly 14 independent INPs at frozen paths, one parameters.json and empty independent workdir per point; never overwrite existing files",
                       "Use source run027 model and run007 Hollomon generator as in run030; exact numeric contract run030-standard-m0025-hollomon-v1; E=210GPa nu=.3 pmax=.9",
                       "Prove only candidate material table and candidate-only comments differ from source; preserve geometry mesh BC contact load and output requests including Punch RP U2/RF2",
                       "Validate plastic table format monotonicity coverage, parameter identity, unique Job names, complete SHA256 and provenance",
                       "Write candidate manifest and structured result in run033/artifacts; register artifacts and message MAIN through AgentHub",
                       "Do not preflight or enqueue unless it helps as read-only preview; MAIN will conduct all 20 previews and queue only after review",
                       "No Solver/Datacheck, no historical file modification, no sealed tensile access, no Git commit/push"],
                   "out_of_scope": "I03-I08 already frozen; do not regenerate or modify"}
    save_once(A / "cae_task_payload.json", cae_payload)
    cae = hub.create_task(main["agent_id"], "CAE", "generate_fourteen_doe_inp",
                          cae_payload, "run033-cae-fourteen-doe-inp-v1", depends=(budget,))["task_id"]
    hub.approve(cae, main["agent_id"], "generate_inp")
    hub.message(cae, main["agent_id"], "CAE", cae_payload, "run033-cae-dispatch-v1")
    review = hub.create_task(main["agent_id"], "MAIN", "review_fourteen_cae_and_twenty_previews",
                             {"run": "run_033", "doe_design_sha256": sha(doe_file),
                              "cae_task_id": cae, "batch_count": 20},
                             "run033-main-review-cae-twenty-v1", depends=(cae,))["task_id"]
    save_once(P / "main_session.json", {"identity": main, "budget_task_id": budget,
                                          "cae_task_id": cae, "review_task_id": review})
    save_once(A / "task_ids.json", {"budget_task_id": budget, "cae_task_id": cae,
                                     "review_task_id": review})
    assert hub.verify_chain()
    print(json.dumps({"status": "CAE_DISPATCHED", "budget_task_id": budget,
                      "cae_task_id": cae, "review_task_id": review,
                      "doe_sha256": sha(doe_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
