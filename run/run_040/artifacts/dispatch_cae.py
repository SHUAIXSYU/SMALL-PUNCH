"""Register frozen offline pilot and hand eight candidate preparations to real CAE."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_040"
ART=RUN/"artifacts"
PRIVATE=ART/"private"
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def save_new(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write("\n")


def main():
    assert sys.executable.lower()==r"d:\xianlab\envs\torch-gpu\python.exe"
    assert not (ART/"task_ids.json").exists()
    frozen=read(PRIVATE/"candidate_manifest.json")
    assert len(frozen["points"])==8
    assert sha(PRIVATE/"candidate_manifest.json")==read(RUN/"checkpoints/start.json")["candidate_manifest_sha256"]
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    main=hub.register("MAIN","codex-main-run040-pilot")
    main_task=hub.create_task(main["agent_id"],"MAIN","freeze_bo_de_initial_and_eight_candidates",
                              {"run":"run_040","initial_dataset_sha256":sha(PRIVATE/"initial_dataset.json"),
                               "algorithm_contract_sha256":sha(ART/"algorithm_contract.json"),
                               "candidate_manifest_sha256":sha(PRIVATE/"candidate_manifest.json"),
                               "solver_permission":"NONE"},"run040-main-algorithm-freeze-v1")
    lease=hub.claim(main_task["task_id"],main,"run040-main-freeze-claim-v1")
    save_new(PRIVATE/"main_freeze_lease.json",lease)
    for path in (PRIVATE/"initial_dataset.json",ART/"algorithm_contract.json",PRIVATE/"candidate_manifest.json",
                 ART/"pilot.py",ART/"test_pilot.py"):
        hub.artifact(main_task["task_id"],main["agent_id"],path,
                     {"run":"run_040","purpose":"frozen SPT-only offline algorithm preparation"},version="run040-pilot-v1")
    hub.finish(lease,{"status":"CANDIDATES_FROZEN","eight_ids":[p["candidate_id"] for p in frozen["points"]],
                      "solver_queue_permission":False},evidence_state="RECORDED",science_state="WARNING")
    cae_payload={"run":"run_040","role":"CAE","kind":"prepare_eight_bo_de_inputs_preview_only",
                 "frozen_candidate_manifest_path":"run/run_040/artifacts/private/candidate_manifest.json",
                 "frozen_candidate_manifest_sha256":sha(PRIVATE/"candidate_manifest.json"),
                 "numeric_contract_path":"run/run_030/artifacts/model_contract.json",
                 "numeric_contract_sha256":sha(ROOT/"run/run_030/artifacts/model_contract.json"),
                 "source_inp_path":"run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp",
                 "source_inp_sha256":read(ROOT/"run/run_030/artifacts/model_contract.json")["source_inp_sha256"],
                 "generator_path":"inverse/hollomon.py",
                 "project_path":"agenthub_sp_invopt/abqjobpilot_project",
                 "project_id":"b87d2cd6-8519-4ac3-bae6-7eb989fb2dae",
                 "outputs_required":["8 independent INPs and parameter JSONs","SHA-256 manifest",
                                     "material table monotonicity/coverage and non-material model diff evidence",
                                     "8 public API preflight and dry-run results","no Queue or Solver action"],
                 "hard_limits":{"enqueue":False,"solver":False,"datacheck":False,"read_sealed_tensile":False,
                                "modify_existing_model":False,"commit_or_push":False}}
    cae=hub.create_task(main["agent_id"],"CAE","prepare_eight_bo_de_inputs_preview_only",cae_payload,
                        "run040-cae-eight-candidates-v1",depends=(main_task["task_id"],))
    hub.approve(cae["task_id"],main["agent_id"],"generate_inp")
    hub.approve(cae["task_id"],main["agent_id"],"verify_inp")
    hub.message(cae["task_id"],main["agent_id"],"CAE",
                {"task_id":cae["task_id"],"payload":cae_payload,
                 "notice":"Real CAE Codex session must claim and report; database message is not automatic receipt"},
                "run040-main-to-cae-v1")
    review=hub.create_task(main["agent_id"],"MAIN","review_eight_cae_previews_and_optimization_readiness",
                           {"run":"run_040","cae_task_id":cae["task_id"],"candidate_manifest_sha256":sha(PRIVATE/"candidate_manifest.json")},
                           "run040-main-cae-review-v1",depends=(cae["task_id"],))
    assert hub.verify_chain()
    info={"main_task_id":main_task["task_id"],"cae_task_id":cae["task_id"],
          "review_task_id":review["task_id"],"main_identity":main,
          "created_at":datetime.now().astimezone().isoformat()}
    save_new(ART/"task_ids.json",info)
    print(json.dumps({"status":"CAE_TASK_REGISTERED","cae_task_id":cae["task_id"],
                      "review_task_id":review["task_id"],"candidate_manifest_sha256":cae_payload["frozen_candidate_manifest_sha256"]},ensure_ascii=False))


if __name__=="__main__":
    main()
