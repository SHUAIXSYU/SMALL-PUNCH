"""MAIN's independent read-only review of real CAE AgentHub handoff and previews."""
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
CAE=PRIVATE/"cae"
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


def split_nonmaterial(raw:bytes):
    lines=raw.splitlines(keepends=True)
    candidates=[i for i,line in enumerate(lines) if line.startswith(b"** CANDIDATE ONLY:")]
    runs=[i for i,line in enumerate(lines) if line.startswith(b"** RUN_040 CANDIDATE ")]
    plastics=[i for i,line in enumerate(lines) if line.strip().lower()==b"*plastic"]
    assert len(candidates)==len(plastics)==1 and len(runs)<=1
    start=runs[0] if runs else candidates[0]
    end=next(i for i in range(plastics[0]+1,len(lines)) if lines[i].lstrip().startswith(b"*"))
    return b"".join(lines[:start]+lines[end:])


def main():
    assert not (PRIVATE/"main_cae_review.json").exists()
    ids=read(ART/"task_ids.json")
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    task=hub.task(ids["cae_task_id"])
    assert task["execution_state"]=="COMPLETED" and task["evidence_state"]=="RECORDED"
    identity=hub.register("MAIN","codex-main-run040-cae-review")
    received=hub.poll_messages(identity)
    assert any(m["task_id"]==ids["cae_task_id"] for m in received),"Real CAE message not received"
    assert hub.verify_chain()
    frozen=read(PRIVATE/"candidate_manifest.json")
    assert sha(PRIVATE/"candidate_manifest.json")==read(RUN/"checkpoints/start.json")["candidate_manifest_sha256"]
    result=read(CAE/"structured_result.json")
    manifest=read(CAE/"generated_candidate_manifest.json")
    static=read(CAE/"static_verification.json")
    preview=read(CAE/"preview_result.json")
    integrity=read(CAE/"preview_integrity.json")
    assert result["task_id"]==ids["cae_task_id"] and result["candidate_count"]==8
    assert result["frozen_candidate_manifest_sha256"]==sha(PRIVATE/"candidate_manifest.json")
    assert len(result["artifacts"])>=16
    for item in result["artifacts"]:
        assert sha(ROOT/item["path"])==item["sha256"]
    assert len(frozen["points"])==len(manifest["points"])==len(static["points"])==len(preview["points"])==8
    source=ROOT/"run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp"
    assert sha(source)==result["source_sha256"]
    nonmaterial=split_nonmaterial(source.read_bytes())
    assert hashlib.sha256(nonmaterial).hexdigest()==result["nonmaterial_sha256"]
    assert preview["project_id"]==json.loads(task["payload"])["project_id"]=="b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
    assert preview["settings"]=="PERSISTED" and preview["abqjobpilot_version"]=="0.2.2"
    assert preview["preflight_passed"]==preview["dry_run_passed"]==8
    assert preview["queue_unchanged"] and preview["settings_unchanged"]
    assert preview["new_queue_records"]==0 and not preview["solver_started"] and not preview["datacheck_started"]
    assert integrity["protected_unchanged"] and integrity["queue_unchanged"]
    assert static["nonmaterial_bytes_identical"] and static["unique_ids_jobs_paths_hashes_parameters"]
    rows=[]
    for p,produced,verified,prev in zip(frozen["points"],manifest["points"],static["points"],preview["points"]):
        cid=p["candidate_id"]
        assert cid==produced["candidate_id"]==verified["candidate_id"]==prev["candidate_id"]
        assert p["job_name"]==produced["job_name"]==prev["job_name"]
        assert p["sigma_y_mpa"]==verified["sigma_y_mpa"]
        assert p["n"]==verified["n"]
        path=ROOT/p["inp_path"]
        assert sha(path)==produced["inp_sha256"]==verified["inp_sha256"]==prev["inp_sha256"]
        assert split_nonmaterial(path.read_bytes())==nonmaterial
        param=read(ROOT/p["parameters_path"])
        assert param["sigma_y_mpa"]==p["sigma_y_mpa"] and param["n"]==p["n"]
        assert sha(ROOT/p["parameters_path"])==produced["parameters_sha256"]
        assert (ROOT/p["working_dir"]).is_dir() and not any((ROOT/p["working_dir"]).iterdir())
        assert prev["request"]["cpus"]==14 and prev["request"]["gpus"]==0
        assert prev["request"]["run_datacheck"] and prev["request"]["run_full"]
        assert prev["request"]["submission_mode"]=="preview_only" and not prev["request"]["allow_solver_submit"]
        assert prev["preflight"]["status"]=="PREVIEW_READY" and prev["dry_run"]["status"]=="DRY_RUN_READY"
        assert prev["preflight"]["job_name"]==p["job_name"]
        assert prev["dry_run"]["queue_file_mutated"] is False
        assert verified["plastic_strain_range"]==[0.0,0.9]
        rows.append({"candidate_id":cid,"algorithm":p["algorithm"],"job_name":p["job_name"],
                     "sigma_y_mpa":p["sigma_y_mpa"],"n":p["n"],"inp_path":p["inp_path"],
                     "inp_sha256":produced["inp_sha256"],"working_dir":p["working_dir"],
                     "material_rows":verified["material_rows"],"preflight":"PREVIEW_READY",
                     "dry_run":"DRY_RUN_READY","numeric_risk":"HIGH_LOW_N" if p["n"]<.05 else
                         "BOUNDARY_SIGMA" if p["sigma_y_mpa"]<155 else "GENERAL_UNVALIDATED_PARAMETER_POINT"})
    assert len(set(r["inp_sha256"] for r in rows))==8
    data={"version":"run040-main-cae-review-v1","observed_at":datetime.now().astimezone().isoformat(),
          "status":"PASS_PREPARATION_ONLY_WITH_NUMERICAL_WARNING",
          "cae_task_id":ids["cae_task_id"],"cae_execution_state":task["execution_state"],
          "cae_agent_id":task["lease_agent"],"actual_message_received":True,
          "artifact_hashes_verified":len(result["artifacts"]),"source_sha256":result["source_sha256"],
          "nonmaterial_sha256":result["nonmaterial_sha256"],"frozen_candidate_manifest_sha256":result["frozen_candidate_manifest_sha256"],
          "project_id":preview["project_id"],"abqjobpilot_version":preview["abqjobpilot_version"],
          "settings":"PERSISTED","preflight_passed":8,"dry_run_passed":8,
          "queue_unchanged":True,"new_enqueues":0,"solver_starts":0,"datacheck_starts":0,
          "higher_risk_ids":[r["candidate_id"] for r in rows if r["numeric_risk"]!="GENERAL_UNVALIDATED_PARAMETER_POINT"],
          "rows":rows,"future_provenance_limit":"Preflight/dry-run do not prove syntax, convergence, PEEQ, local contact quality or physical validity"}
    save_new(PRIVATE/"main_cae_review.json",data)
    print(json.dumps({"status":data["status"],"preflight_passed":8,"dry_run_passed":8,
                      "higher_risk_ids":data["higher_risk_ids"],"artifact_hashes_verified":len(result["artifacts"]),
                      "hub_chain":hub.verify_chain()},ensure_ascii=False))


if __name__=="__main__":
    main()
