"""Register run_039 ODB artifacts and report the 22-point result to MAIN."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
OUT=ROOT/"run/run_039/artifacts/private/odb"
TASK="4bb49a70-f8d1-4a08-93b2-8953e3e58cb4"
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

def main():
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    lease=read(OUT/"lease.json")
    assert lease["task_id"]==TASK
    task=hub.task(TASK)
    assert task["execution_state"]=="CLAIMED" and task["assigned_role"]=="ODB"
    assert task["lease_agent"]==lease["agent_id"] and task["lease_session"]==lease["session_id"]
    hub.heartbeat(lease)
    manifest=read(OUT/"manifest.json")
    dataset=read(OUT/"dataset_22.json")
    prior19=read(OUT/"existing_19_revalidation.json")
    i01=read(OUT/"i01_revalidation.json")
    assert prior19["reusable_count"]==19 and i01["reusable"]
    assert dataset["point_count"]==22 and dataset["provisional_score_count"]==19 and dataset["loss_null_count"]==3
    assert {r["point_id"] for r in dataset["rows"] if r["loss_or_null"] is None}=={"D07","D09","D10"}
    assert manifest["file_count"]==len(manifest["files"])
    assert all(sha(ROOT/item["path"])==item["sha256"] for item in manifest["files"])
    for pid in ("I02","D09"):
        result=read(OUT/pid/"result.json")
        assert result["task_id"]==TASK and result["run_id"]=="run_039"
        assert all(sha(ROOT/path)==digest for path,digest in result["artifact_hashes"].items())
    d09=read(OUT/"D09/result.json")
    i02=read(OUT/"I02/result.json")
    assert d09["loss_or_null"] is None and d09["rejected_attempts"]==44
    assert i02["loss_or_null"] is not None
    registered=0
    for item in manifest["files"]:
        path=ROOT/item["path"]
        hub.artifact(TASK,lease["agent_id"],path,
                     {"run_id":"run_039","scope":"ODB_22_POINT_HANDOFF","sha256":item["sha256"],
                      "original_D09_odb_opened":False,"no_solver_datacheck_enqueue_retry":True},
                     version="run039-odb-22point-v1")
        registered+=1
    hub.artifact(TASK,lease["agent_id"],OUT/"manifest.json",
                 {"run_id":"run_039","scope":"manifest","file_count":manifest["file_count"],
                  "original_D09_odb_opened":False},version="run039-odb-22point-v1")
    registered+=1
    rows=[{"point_id":r["point_id"],"job_name":r["job_name"],"queue_id":r["queue_id"],
           "loss_or_null":r["loss_or_null"],"numeric_status":r["numeric_status"],
           "result_path":r["result_path"]} for r in dataset["rows"]]
    body={"kind":"run039_odb_22_point_result","task_id":TASK,"run_id":"run_039",
          "dataset_path":"run/run_039/artifacts/private/odb/dataset_22.json",
          "dataset_csv_path":"run/run_039/artifacts/private/odb/dataset_22.csv",
          "report_path":"run/run_039/artifacts/private/odb/REPORT.md",
          "manifest_path":"run/run_039/artifacts/private/odb/manifest.json",
          "manifest_sha256":sha(OUT/"manifest.json"),
          "point_count":22,"provisional_score_count":19,"loss_null_points":["D07","D09","D10"],
          "original_19_revalidated":19,"I01_revalidated":True,
          "I02":{"job_name":i02["job_name"],"queue_id":i02["queue_id"],"loss_or_null":i02["loss_or_null"],
                 "rmse_n_or_null":i02["rmse_n_or_null"],"max_saved_peeq":i02["max_saved_peeq"],
                 "accepted_increments":i02["accepted_increments"],"rejected_attempts":i02["rejected_attempts"],
                 "cutback_increments":i02["cutback_increments"],"result_path":"run/run_039/artifacts/private/odb/I02/result.json"},
          "D09_replacement":{"job_name":d09["job_name"],"queue_id":d09["queue_id"],
                 "software_status":d09["full_status"]["phase"],"loss_or_null":None,
                 "numeric_blocking_issues":d09["numerical_blocking_issues"],
                 "max_saved_peeq":d09["max_saved_peeq"],"accepted_increments":d09["accepted_increments"],
                 "rejected_attempts":d09["rejected_attempts"],"cutback_increments":d09["cutback_increments"],
                 "accepted_large_strain_warning_count":sum(w["class"]=="LARGE_STRAIN_INCREMENT" for w in d09["warning_events_by_accepted_or_rejected"]["accepted"]),
                 "negative_accepted_force_step_count":d09["contact_transition_review"]["negative_force_step_count"],
                 "result_path":"run/run_039/artifacts/private/odb/D09/result.json"},
          "original_D09_status":"UNKNOWN_INTERRUPTED_NOT_OPENED_OR_HASHED",
          "first_D09_retry_status":"UNKNOWN_NOT_OPENED",
          "d09_attempt_lineage_path":"run/run_039/artifacts/private/odb/d09_attempt_lineage.json",
          "rows":rows,"loss_version":"run017-exploratory-fd-v1","loss_mode":"PROVISIONAL",
          "science_state":"NOT_EVALUATED","main_review_required":True,
          "sealed_holdout_accessed":False,"historical_holdout_exposure_declaration":"Previously exposed",
          "no_solver_datacheck_enqueue_retry":True}
    hub.message(TASK,lease["agent_id"],"MAIN",body,"run039-odb-22point-results-v1")
    hub.finish(lease,{"status":dataset["status"],"registered_artifacts":registered,
                      "manifest_sha256":body["manifest_sha256"],"point_count":22,
                      "provisional_score_count":19,"loss_null_count":3,
                      "D09_replacement_loss":None,"main_review_required":True},
               evidence_state="RECORDED",science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    final=hub.task(TASK)
    print(json.dumps({"task_id":TASK,"hub_state":final["execution_state"],
                      "evidence_state":final["evidence_state"],"science_state":final["science_state"],
                      "registered_artifacts":registered,"message_key":"run039-odb-22point-results-v1"}))

if __name__=="__main__":
    main()
