"""Audit existing pilot execution using public APIs and hand safe ODBs to real ODB."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_042"
ART=RUN/"artifacts"
PRIVATE=ART/"private"
PROJECT=ROOT/"agenthub_sp_invopt/abqjobpilot_project"
PID="b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.path[:0]=[str(ROOT),r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import probe_solver_processes
from agenthub_sp_invopt.hub import Hub


def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()
def save(p,v):
    with Path(p).open("x",encoding="utf-8") as stream:
        json.dump(v,stream,ensure_ascii=False,indent=2);stream.write("\n")
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def phases(path):
    data=path.read_text(encoding="utf-8",errors="replace")
    result={}
    for phase in ("DATACHECK_RUNNING","FULL_RUNNING"):
        starts=re.findall(r"\[([^]]+)\] START "+phase,data)
        ends=re.findall(r"\[([^]]+)\] END "+phase+r" return_code=(-?\d+)",data)
        result[phase]={"starts":starts,"ends":ends,
                       "one_successful_phase":len(starts)==len(ends)==1 and ends[0][1]=="0"}
    return result


def main():
    assert not (RUN/"run.json").exists()
    assert sys.executable.lower()==r"d:\xianlab\envs\torch-gpu\python.exe"
    start={"at":now(),"git":{"branch":git("branch","--show-current"),"head":git("rev-parse","HEAD"),
                                  "remote":git("remote","-v"),"working_tree":git("status","--short")},"python":sys.executable}
    save(RUN/"checkpoints/start.json",start)
    frozen_path=ROOT/"run/run_040/artifacts/private/candidate_manifest.json"
    generated_path=ROOT/"run/run_040/artifacts/private/cae/generated_candidate_manifest.json"
    queue_path=ROOT/"run/run_041/artifacts/private/queue_manifest.json"
    frozen=read(frozen_path);generated=read(generated_path);queued=read(queue_path)
    assert sha(frozen_path)==generated["frozen_candidate_manifest_sha256"]=="692c3215c974b35ea1c816b86520f2c183241504c8bd2e0b111cda44bb2d502b"
    assert len(frozen["points"])==len(generated["points"])==len(queued["points"])==8
    before={"queue":sha(PROJECT/"runtime/queue.json"),"settings":sha(PROJECT/"runtime/settings.json"),"db":sha(PROJECT/"project.db")}
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
    project=api.show_project(project_id=PID).to_dict();settings=api.get_project_settings(project_id=PID).to_dict()
    assert project["status"]=="OK" and project["project"]["project_id"]==PID
    assert settings["status"]=="PERSISTED"
    queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
    assert queue["status"]==history["status"]=="OK"
    rt=assess_runtime(PROJECT/"runtime",project_db=PROJECT/"project.db")
    process=probe_solver_processes()
    assert rt["status"]=="CLEAN" and rt["owner"]["state"]=="ABSENT" and process["state"]=="CLEAR"
    assert not rt["running_queue_ids"]
    records=[]
    for p,g,receipt in zip(frozen["points"],generated["points"],queued["points"]):
        cid=p["candidate_id"]; name=p["job_name"]
        assert cid==g["candidate_id"]==receipt["candidate_id"]
        inp=ROOT/p["inp_path"]; work=ROOT/p["working_dir"]
        assert sha(inp)==g["inp_sha256"]==receipt["inp_sha256"]
        matches=[j for j in queue["jobs"] if j["queue_id"]==receipt["queue_id"]]
        assert len(matches)==1;job=matches[0]
        assert job["job_name"]==name and Path(job["inp_path"]).resolve()==inp.resolve()
        assert Path(job["work_dir"]).resolve()==work.resolve()
        assert (job["cpus"],job["gpus"],job["run_datacheck"],job["run_full"])==(14,0,True,True)
        hh=[h for h in history["jobs"] if h["job_name"]==name]
        assert len(hh)==1
        detail=api.show_job(hh[0]["job_id"],project_id=PID).to_dict()
        assert detail["status"]=="OK" and len(detail["runs"])==hh[0]["run_count"]==1
        assert detail["runs"][0]["queue_id"]==job["queue_id"] and detail["runs"][0]["attempt_no"]==1
        phase=phases(work/f"{name}.log") if (work/f"{name}.log").exists() else {}
        successful=job["raw_status"] in {"COMPLETED_OK","COMPLETED_WITH_WARNINGS"} and job["return_code"]==0 and job["final_verdict"]=="SUCCESS"
        safe=bool(successful and phase and all(v["one_successful_phase"] for v in phase.values()) and not (work/f"{name}.lck").exists())
        files={}
        for ext in ("odb","sta","msg","dat","log"):
            path=work/f"{name}.{ext}"
            files[ext]={"path":rel(path),"exists":path.is_file(),"bytes":path.stat().st_size if path.is_file() else None,
                        "sha256":sha(path) if safe and path.is_file() else None}
        if safe:
            assert all(v["exists"] and v["bytes"]>0 for v in files.values())
            assert "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in (work/f"{name}.sta").read_text(errors="replace")
            assert Path(job["odb_path"]).resolve()==(ROOT/p["expected_odb"]).resolve()
            assert (work/f"{name}.odb").stat().st_size==job["odb_size_bytes"]
        records.append({**p,"inp_sha256":g["inp_sha256"],"queue_id":job["queue_id"],
                        "queue_status":job["raw_status"],"queue_record":job,"history_detail":detail,
                        "started_attempts":int(bool(job.get("started_at"))),"started_at":job.get("started_at"),
                        "completed_at":job.get("ended_at"),"actual_runtime_s":job.get("duration_sec"),
                        "phase_evidence":phase,"files":files,"software_completed":successful,
                        "safe_for_readonly_odb":safe,"scientific_score_state":"PENDING_ODB_NUMERICAL_REVIEW"})
    after={"queue":sha(PROJECT/"runtime/queue.json"),"settings":sha(PROJECT/"runtime/settings.json"),"db":sha(PROJECT/"project.db")}
    assert before==after
    audit={"version":"run042-pilot-execution-audit-v1","at":now(),"project_id":PID,"project":project,"settings":settings,
           "runtime":rt,"process_probe":process,"source_frozen_manifest_sha256":sha(frozen_path),
           "queue_manifest_sha256":sha(queue_path),"records":records,"software_completed":sum(r["software_completed"] for r in records),
           "read_safe":sum(r["safe_for_readonly_odb"] for r in records),"started_attempts":sum(r["started_attempts"] for r in records),
           "protected_before":before,"protected_after":after,"readonly":True}
    save(PRIVATE/"execution_audit.json",audit)
    old_ids=read(ROOT/"run/run_041/artifacts/private/task_ids.json")
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    actor=hub.register("MAIN","codex-main-run042-batch-analysis")
    audit_task=old_ids["execution_audit_task_id"]
    assert hub.task(audit_task)["execution_state"]=="PENDING"
    lease=hub.claim(audit_task,actor,"run042-execution-audit-claim-v1")
    save(PRIVATE/"audit_lease.json",lease)
    hub.artifact(audit_task,actor["agent_id"],PRIVATE/"execution_audit.json",{"output_run":"run_042","scope":"real existing eight Job audit, no new execution"},version="run042-v1")
    hub.finish(lease,{"output_run":"run_042","software_completed":audit["software_completed"],"read_safe":audit["read_safe"],
                      "started_attempts":audit["started_attempts"],"consumed_authorization":audit["started_attempts"],"retry_allowance":0},evidence_state="RECORDED",science_state="NOT_EVALUATED")
    dispatch={"output_run":"run_042","task_id":old_ids["odb_task_id"],"project_id":PID,
              "audit_path":rel(PRIVATE/"execution_audit.json"),"audit_sha256":sha(PRIVATE/"execution_audit.json"),
              "output_directory":"run/run_042/artifacts/private/odb",
              "numeric_version":"run030-standard-m0025-hollomon-v1","loss_version":"run017-exploratory-fd-v1",
              "baseline_dataset":"run/run_040/artifacts/private/initial_dataset.json",
              "jobs":[{"candidate_id":r["candidate_id"],"job_name":r["job_name"],"queue_id":r["queue_id"],"inp_path":r["inp_path"],
                       "inp_sha256":r["inp_sha256"],"working_dir":r["working_dir"],"odb_path":r["files"]["odb"]["path"],
                       "odb_sha256":r["files"]["odb"]["sha256"],"read_safe":r["safe_for_readonly_odb"]} for r in records],
              "rules":{"read_only":True,"no_solver_datacheck_enqueue_retry":True,"holdout_access":False,
                       "no_smoothing_zero_shift_crop_extrapolate":True,"null_for_unscoreable":True,
                       "accepted_vs_rejected_warnings_separate":True,"main_independent_review":True}}
    save(ART/"odb_task_payload.json",dispatch)
    hub.message(old_ids["odb_task_id"],old_ids["identity"]["agent_id"],"ODB",dispatch,"run042-actual-eight-pilot-odb-handoff-v1")
    save(ART/"task_ids.json",{"identity":actor,"execution_audit_task_id":audit_task,"odb_task_id":old_ids["odb_task_id"],"main_review_task_id":old_ids["science_task_id"]})
    assert hub.verify_chain()
    save(RUN/"run.json",{"schema_version":"1.0","run_id":"run_042","stage":"Pilot batch actual results analysis",
          "objective":"Audit eight real Jobs, real ODB extraction, frozen Loss and BO/DE comparison",
          "status":"RUNNING","start_time":start["at"],"end_time":None,"git_branch":start["git"]["branch"],"git_head":start["git"]["head"],
          "git":start["git"],"python_interpreter":sys.executable,
          "inputs":[{"path":rel(frozen_path),"sha256":sha(frozen_path),"role":"frozen candidates"},{"path":rel(queue_path),"sha256":sha(queue_path),"role":"queue identities"}],
          "outputs":[{"path":rel(PRIVATE/"execution_audit.json"),"role":"actual execution evidence"}],
          "validation":[{"check":"public_execution_audit","status":"PASS","evidence":f"{audit['software_completed']} software completed; numerical review pending"}],"errors":[]})
    (RUN/"summary.md").write_text("# run_042 — BO/DE 实际结果分析\n\nRUNNING：实际执行审计完成；等待真实ODB会话提取及MAIN复核。\n",encoding="utf-8")
    print(json.dumps({"software_completed":audit["software_completed"],"read_safe":audit["read_safe"],"started_attempts":audit["started_attempts"],"odb_task_id":old_ids["odb_task_id"]}))


if __name__=="__main__":main()
