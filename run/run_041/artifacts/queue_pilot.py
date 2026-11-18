"""Eight frozen run_040 inputs, official queue-only API, no Solver launcher.

init -> preflight -> enqueue. A mutation marker forbids a second submission
attempt after any partial/uncertain outcome. Historical inputs are read-only.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_041"
ART=RUN/"artifacts"
PRIVATE=ART/"private"
RECEIPTS=PRIVATE/"queue_receipts"
PROJECT=ROOT/"agenthub_sp_invopt/abqjobpilot_project"
RT=PROJECT/"runtime"
PID="b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
ABQ=Path(r"D:\Projects\abqjobpilot")
FROZEN=ROOT/"run/run_040/artifacts/private/candidate_manifest.json"
GENERATED=ROOT/"run/run_040/artifacts/private/cae/generated_candidate_manifest.json"
MAIN_REVIEW=ROOT/"run/run_040/artifacts/private/main_cae_review.json"
ORDER=["BO01","BO02","BO03","BO04","DE01","DE02","DE03","DE04"]
EXECUTABLE={"QUEUED","DATACHECK_OK"}
ACTIVE={"RUNNING","DATACHECK_RUNNING","FULL_RUNNING"}
HISTORICAL={"COMPLETED_OK","COMPLETED_WITH_WARNINGS","FAILED_FATAL","FAILED_NUMERICAL",
            "FAILED_INPUT","FAILED_LICENSE","DATACHECK_FAILED","DATACHECK_FAILED_INVALID_GPU_OPTION",
            "SKIPPED","CANCELLED","UNKNOWN_INTERRUPTED"}
OLD_LOCK=ROOT/"run/run_033/artifacts/solver/SPIO_R033_D09_L/SPIO_R033_D09_L.lck"
sys.path[:0]=[str(ROOT),str(ABQ)]
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import build_recovery_plan
from abqjobpilot.runtime_coordination import queue_transaction, runner_ownership_state
from agenthub_sp_invopt.hub import Hub


def now(): return datetime.now().astimezone().isoformat()
def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def rel(path): return Path(path).relative_to(ROOT).as_posix()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""): h.update(chunk)
    return h.hexdigest()
def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open("x",encoding="utf-8") as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write("\n")
def git(*args): return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def split_nonmaterial(raw):
    lines=raw.splitlines(keepends=True)
    c=[i for i,l in enumerate(lines) if l.startswith(b"** CANDIDATE ONLY:")]
    r=[i for i,l in enumerate(lines) if l.startswith(b"** RUN_040 CANDIDATE ")]
    p=[i for i,l in enumerate(lines) if l.strip().lower()==b"*plastic"]
    assert len(c)==len(p)==1 and len(r)<=1
    start=r[0] if r else c[0]
    end=next(i for i in range(p[0]+1,len(lines)) if lines[i].lstrip().startswith(b"*"))
    return b"".join(lines[:start]+lines[end:])


def load_batch():
    run40=read(ROOT/"run/run_040/run.json")
    expected={i["path"]:i["sha256"] for i in run40["outputs"]}
    assert sha(FROZEN)==expected[rel(FROZEN)]=="692c3215c974b35ea1c816b86520f2c183241504c8bd2e0b111cda44bb2d502b"
    assert sha(GENERATED)==expected[rel(GENERATED)]
    assert sha(MAIN_REVIEW)==expected[rel(MAIN_REVIEW)]
    frozen=read(FROZEN); generated=read(GENERATED); reviewed=read(MAIN_REVIEW)
    assert generated["frozen_candidate_manifest_sha256"]==sha(FROZEN)
    assert frozen["contract_sha256"]==sha(ROOT/frozen["contract_path"])
    assert frozen["algorithm_implementation_sha256"]==sha(ROOT/frozen["algorithm_implementation_path"])
    assert generated["generator_sha256"]==sha(ROOT/generated["generator"])
    assert generated["numeric_contract_sha256"]==sha(ROOT/generated["numeric_contract_path"])
    assert reviewed["preflight_passed"]==reviewed["dry_run_passed"]==8
    assert [p["candidate_id"] for p in frozen["points"]]==ORDER
    assert len(generated["points"])==len(reviewed["rows"])==8
    source=ROOT/generated["source_inp"]
    assert sha(source)==generated["source_sha256"]
    nonmaterial=split_nonmaterial(source.read_bytes())
    points=[]
    for p,g,m in zip(frozen["points"],generated["points"],reviewed["rows"]):
        assert p["candidate_id"]==g["candidate_id"]==m["candidate_id"]
        for key in ("job_name","inp_path","working_dir","sigma_y_mpa","n"):
            assert p[key]==g[key]==m[key]
        assert p["parameters_path"]==g["parameters_path"]
        assert p["expected_odb"]==g["expected_odb"]
        assert sha(ROOT/p["inp_path"])==g["inp_sha256"]==m["inp_sha256"]
        assert sha(ROOT/p["parameters_path"])==g["parameters_sha256"]
        params=read(ROOT/p["parameters_path"])
        assert params["sigma_y_mpa"]==p["sigma_y_mpa"] and params["n"]==p["n"]
        assert params["E_pa"]==210000000000 and params["nu"]==.3
        assert params["generator_sha256"]==generated["generator_sha256"]
        assert params["numeric_contract_sha256"]==generated["numeric_contract_sha256"]
        assert params["max_plastic_strain"]==.9
        assert p["numeric_version"]=="run030-standard-m0025-hollomon-v1"
        assert p["loss_version"]=="run017-exploratory-fd-v1"
        raw=(ROOT/p["inp_path"]).read_bytes()
        assert split_nonmaterial(raw)==nonmaterial
        text=raw.decode("utf-8")
        assert "0.001, 1., 1e-12, 0.0025" in text
        assert not re.search(r"(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b",text)
        work=ROOT/p["working_dir"]
        assert work.is_dir() and not any(work.iterdir()),f"Output conflict: {p['candidate_id']}"
        assert not (ROOT/p["expected_odb"]).exists()
        points.append({**p,"inp_sha256":g["inp_sha256"],"parameters_sha256":g["parameters_sha256"]})
    assert len({p["inp_sha256"] for p in points})==8
    assert len({p["working_dir"] for p in points})==8
    binding=read(ROOT/"run/run_030/artifacts/loss_contract_binding.json")
    assert sha(ROOT/binding["target_path"])==binding["target_sha256"]
    assert sha(ROOT/binding["implementation_path"])==binding["implementation_sha256"]
    return points


def environment(api):
    caps=api.capabilities()
    assert caps["application_version"]=="0.2.2"
    project=api.show_project(project_id=PID).to_dict()
    settings=api.get_project_settings(project_id=PID).to_dict()
    assert project["status"]=="OK" and project["project"]["project_id"]==PID
    assert Path(project["project"]["path"]).resolve()==PROJECT.resolve()
    assert read(PROJECT/"project.json")["project_id"]==PID
    assert settings["status"]=="PERSISTED" and settings["persisted"] and settings["project_id"]==PID
    assert not settings["defaulted_fields"] and not settings["errors"]
    assert Path(settings["project_path"]).resolve()==PROJECT.resolve()
    v=settings["effective_settings"]
    assert v==settings["settings"]==read(RT/"settings.json")
    assert Path(v["abaqus_cmd"]).resolve()==Path(r"D:\ABAQUS2024\Commands\abq2024.bat").resolve()
    assert Path(v["abaqus_cmd"]).is_file()
    assert (v["default_cpus"],v["default_gpus"],v["use_gpu"])==(14,0,False)
    assert v["run_datacheck"] is True and v["run_full"] is True
    return {"project":project,"settings":settings,"capabilities":caps,
            "api_source":str(ABQ/"abqjobpilot/api/client.py"),"api_source_sha256":sha(ABQ/"abqjobpilot/api/client.py")}


def runtime_guard(deep=False):
    owner=runner_ownership_state(RT)
    a=assess_runtime(RT,project_db=PROJECT/"project.db")
    assert owner["state"]=="ABSENT" and a["status"]=="CLEAN" and a["live_phase"]=="IDLE"
    assert not a["running_queue_ids"] and not a["errors"] and not a["history_disagreements"]
    assert set(Path(p).resolve() for p in a["lock_files"])<={OLD_LOCK.resolve()}
    result={"at":now(),"owner":owner,"assessment":a,
            "retained_historical_lock":"Original D09 inactive, separate output identity; not removed or reused"}
    if deep:
        plan=build_recovery_plan(RT,project_db=PROJECT/"project.db").to_dict()
        assert plan["assessment"]["solver_process"]["state"]=="CLEAR"
        assert all(".lck file exists" in s for s in plan["unresolved"])
        result["recovery_plan"]=plan
    return result


def queue_prefix(scoped,api,points,prefix):
    queue=scoped.list_jobs()
    history=api.list_project_jobs(project_id=PID).to_dict()
    assert queue["status"]==history["status"]=="OK" and not queue["errors"] and not history["errors"]
    assert all(j["raw_status"] in EXECUTABLE|ACTIVE|HISTORICAL for j in queue["jobs"])
    assert not [j for j in queue["jobs"] if j["raw_status"] in ACTIVE]
    active=[j for j in queue["jobs"] if j["raw_status"] in EXECUTABLE]
    assert [j["job_name"] for j in active]==[p["job_name"] for p in points[:prefix]],"Unexpected executable Queue jobs/order"
    for p,j in zip(points,active):
        assert j["raw_status"]==j["status"]=="QUEUED"
        assert Path(j["inp_path"]).resolve()==(ROOT/p["inp_path"]).resolve()
        assert Path(j["work_dir"]).resolve()==(ROOT/p["working_dir"]).resolve()
        assert (j["cpus"],j["gpus"],j["run_datacheck"],j["run_full"])==(14,0,True,True)
        assert p["inp_sha256"] in (j.get("notes") or "")
        assert not j.get("started_at") and not j.get("ended_at")
    for p in points:
        same=[j for j in queue["jobs"] if j["job_name"].casefold()==p["job_name"].casefold()
              or Path(j["work_dir"]).resolve()==(ROOT/p["working_dir"]).resolve()
              or Path(j["inp_path"]).resolve()==(ROOT/p["inp_path"]).resolve()]
        expected=1 if points.index(p)<prefix else 0
        assert len(same)==expected,"Candidate already queued/executed or identity collision"
        assert not [j for j in history["jobs"] if j["job_name"].casefold()==p["job_name"].casefold()
                    or Path(j["inp_path"]).resolve()==(ROOT/p["inp_path"]).resolve()],"Candidate has execution history"
    return {"queue":queue,"history":history,"executable_count":len(active),"queue_ids":[j["queue_id"] for j in active]}


def request(p,task):
    return JobRequest(inp_path=str((ROOT/p["inp_path"]).resolve()),job_name=p["job_name"],
                      working_dir=str((ROOT/p["working_dir"]).resolve()),cpus=14,gpus=0,
                      run_datacheck=True,run_full=True,submission_mode="enqueue_only",allow_solver_submit=False,
                      batch="run041_authorized_eight_bo_de_pilot",strategy="frozen_batch_single_runner_user_gui_start",
                      metadata={"project_id":PID,"task_id":task,"inp_sha256":p["inp_sha256"],
                                "maximum_attempts":1,"automatic_retries":0,
                                "notes":f"run041 {p['candidate_id']} {p['algorithm']}; project_id={PID}; inp_sha256={p['inp_sha256']}; task_id={task}; one manual-GUI Datacheck+Full; 14CPU 0GPU; zero retries; AUTO_STOP_UNAVAILABLE"})


def init():
    assert not (RUN/"run.json").exists()
    assert sys.executable.lower()==r"d:\xianlab\envs\torch-gpu\python.exe" and sys.version_info[:3]==(3,11,13)
    points=load_batch()
    git_state={"branch":git("branch","--show-current"),"head":git("rev-parse","HEAD"),"remote":git("remote","-v"),"working_tree":git("status","--short")}
    start={"at":now(),"git":git_state,"python":sys.executable,"python_version":sys.version.split()[0]}
    save(RUN/"checkpoints/start.json",start)
    identity={"frozen_candidate_manifest_path":rel(FROZEN),"frozen_candidate_manifest_sha256":sha(FROZEN),
              "generated_manifest_path":rel(GENERATED),"generated_manifest_sha256":sha(GENERATED),
              "note":"Full INP hashes bound by preexisting CAE generated manifest and run040 MAIN review; candidate parameter manifest is immutable",
              "order":ORDER,"points":points}
    save(PRIVATE/"frozen_batch_identity.json",identity)
    auth={"run":"run_041","authorization_source":{"type":"current_user_chat_message","title":"SP-InvOpt｜BO/DE Pilot Batch — Eight-Job Authorised Execution","message_id":None,
         "scope":"User explicitly authorizes all eight frozen inputs in one queue-only batch; user alone clicks GUI Start Queue; failure may continue following jobs"},
          "project_id":PID,"project_path":str(PROJECT),"batch_identity_sha256":sha(PRIVATE/"frozen_batch_identity.json"),
          "candidate_manifest_sha256":sha(FROZEN),"generated_manifest_sha256":sha(GENERATED),"order":ORDER,
          "max_total_started_attempts":8,"each_max_datacheck":1,"each_max_full_after_datacheck_success":1,
          "automatic_retries":0,"cpus":14,"gpus":0,"run_datacheck":True,"run_full":True,
          "solver_start":"USER_GUI_ONLY","AUTO_STOP_UNAVAILABLE_accepted":True,
          "queued_is_not_started":True,"second_stage_eight_authorized":False,
          "numeric_version":"run030-standard-m0025-hollomon-v1","loss_version":"run017-exploratory-fd-v1",
          "points":[{k:p[k] for k in ("candidate_id","algorithm","job_name","sigma_y_mpa","n","inp_path","inp_sha256","working_dir","expected_odb")} for p in points]}
    save(PRIVATE/"authorization_scope.json",auth)
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    main=hub.register("MAIN","codex-main-run041-eight-pilot")
    budget=hub.create_task(main["agent_id"],"MAIN","record_eight_pilot_user_authorization",auth,"run041-eight-budget-v1")
    lease=hub.claim(budget["task_id"],main,"run041-budget-claim-v1")
    save(PRIVATE/"budget_lease.json",lease)
    hub.artifact(budget["task_id"],main["agent_id"],PRIVATE/"authorization_scope.json",{"source":"explicit current human authorization","run":"run_041"},version="run041-v1")
    hub.finish(lease,{"authorized":8,"prepared":8,"queued":0,"started":0,"consumed_attempts":0,"retry_allowance":0,"solver_start":"USER_GUI_ONLY"},evidence_state="RECORDED",science_state="NOT_EVALUATED")
    tasks={}
    for p in points:
        payload={"scope":auth,"candidate":p,"max_started_attempts":1,"automatic_retries":0,"manual_gui_only":True}
        task=hub.create_task(main["agent_id"],"MAIN","queue_only_pilot_candidate",payload,f"run041-queue-{p['candidate_id']}-v1",depends=(budget["task_id"],))
        hub.approve(task["task_id"],main["agent_id"],"enqueue")
        hub.approve(task["task_id"],main["agent_id"],"start_solver")
        tasks[p["candidate_id"]]=task["task_id"]
    confirm=hub.create_task(main["agent_id"],"MAIN","verify_eight_pilot_queue_only_batch",{"run":"run_041","batch_sha256":sha(PRIVATE/"frozen_batch_identity.json")},"run041-confirm-batch-v1",depends=tuple(tasks.values()))
    audit=hub.create_task(main["agent_id"],"MAIN","audit_pilot_actual_terminal_after_user_completion",{"run":"run_041","scope_sha256":sha(PRIVATE/"authorization_scope.json"),"trigger":"only after user reports completion; do not start solver"},"run041-future-execution-audit-v1",depends=(confirm["task_id"],))
    odb=hub.create_task(main["agent_id"],"ODB","extract_eight_pilot_safe_odb_after_audit",{"run":"run_041","audit_task_id":audit["task_id"],"loss_version":auth["loss_version"],"read_only":True,"sealed_tensile_access":False},"run041-future-odb-v1",depends=(audit["task_id"],))
    science=hub.create_task(main["agent_id"],"MAIN","compare_batch_bo_partial_de_actual_results",{"run":"run_041","bo_batch":True,"de_partial_generation":True,"initial_valid":19,"future_remaining_budget_authorized":False},"run041-future-science-review-v1",depends=(odb["task_id"],))
    save(PRIVATE/"task_ids.json",{"identity":main,"budget_task_id":budget["task_id"],"point_tasks":tasks,
                                   "confirm_task_id":confirm["task_id"],"execution_audit_task_id":audit["task_id"],
                                   "odb_task_id":odb["task_id"],"science_task_id":science["task_id"]})
    assert hub.verify_chain()
    save(RUN/"run.json",{"schema_version":"1.0","run_id":"run_041","stage":"Authorized BO/DE eight-job queue-only batch",
         "objective":"Register eight attempts, verify frozen inputs and current public API previews, queue only and await user GUI start",
         "status":"RUNNING","start_time":start["at"],"end_time":None,"git_branch":git_state["branch"],"git_head":git_state["head"],
         "git":git_state,"python_interpreter":sys.executable,"inputs":[{"path":rel(FROZEN),"sha256":sha(FROZEN),"role":"frozen parameters"},{"path":rel(GENERATED),"sha256":sha(GENERATED),"role":"preexisting frozen INP hashes"}],
         "outputs":[{"path":rel(PRIVATE/"authorization_scope.json"),"role":"explicit scoped authorization"}],"validation":[],"errors":[]})
    (RUN/"summary.md").write_text("# run_041 — BO/DE 八项授权批量入队\n\nRUNNING：授权已登记，未执行入队或求解；等待本轮8项预检查。\n",encoding="utf-8")
    print(json.dumps({"status":"EIGHT_AUTHORIZATIONS_REGISTERED","started_attempts":0,"budget_task_id":budget["task_id"]}))


def preflight():
    assert not (PRIVATE/"preflight.json").exists()
    points=load_batch(); ids=read(PRIVATE/"task_ids.json")
    api=AbqJobPilotClient(); scoped=api.for_project(project_id=PID)
    env=environment(api); rt=runtime_guard(deep=True); q=queue_prefix(scoped,api,points,0)
    runner=ABQ/"abqjobpilot/runner_core.py"
    code=runner.read_text(encoding="utf-8")
    loop=code[code.index("    def _run_loop(self)"):]
    assert "                run_next_job(job)" in loop
    assert "if self._stop_after_current:" in loop
    assert "final_verdict" not in loop and "FAILED" not in loop
    runner_evidence={"status":"AUTO_STOP_UNAVAILABLE","source":str(runner),"sha256":sha(runner),
                     "evidence":"_run_loop calls run_next_job(job) then continues without outcome check; manual stop flag only; output admission errors can stop independently"}
    before={"queue":sha(RT/"queue.json"),"settings":sha(RT/"settings.json"),"project_db":sha(PROJECT/"project.db")}
    previews=[]
    for p in points:
        req=request(p,ids["point_tasks"][p["candidate_id"]])
        pre=scoped.preflight(req).to_dict(); dry=scoped.enqueue(req,dry_run=True).to_dict()
        previews.append({"candidate_id":p["candidate_id"],"request":req.to_dict(),"preflight":pre,"dry_run":dry})
        assert pre["status"]=="PREVIEW_READY" and not pre["errors"]
        assert dry["status"]=="DRY_RUN_READY" and not dry["errors"] and not dry["queue_file_mutated"]
        assert not dry["solver_started"] and not dry["runner_started"]
        assert Path(pre["expected_odb_path"]).resolve()==(ROOT/p["expected_odb"]).resolve()
    after={"queue":sha(RT/"queue.json"),"settings":sha(RT/"settings.json"),"project_db":sha(PROJECT/"project.db")}
    assert before==after
    queue_prefix(scoped,api,points,0); runtime_guard()
    save(PRIVATE/"preflight.json",{"at":now(),"status":"PASS_ALL_EIGHT_CURRENT_PREVIEWS","environment":env,"runtime":rt,
                                   "queue_before":q,"runner_stop":runner_evidence,"protected_before":before,"protected_after":after,
                                   "previews":previews,"queue_unchanged":True,"settings_unchanged":True,"solver_started":False})
    print(json.dumps({"status":"PASS_ALL_EIGHT_CURRENT_PREVIEWS","preflight":8,"dry_run":8,"auto_stop":"AUTO_STOP_UNAVAILABLE"}))


def enqueue():
    if (PRIVATE/"queue_manifest.json").exists():
        m=read(PRIVATE/"queue_manifest.json")
        print(json.dumps({"status":"ALREADY_QUEUED_NO_SUBMISSION","queue_ids":m["queue_ids"]}));return
    assert not (RUN/"checkpoints/enqueue_started.json").exists(),"Partial/uncertain submission: read-only reconciliation required, no retry"
    admission=read(PRIVATE/"preflight.json")
    assert admission["status"]=="PASS_ALL_EIGHT_CURRENT_PREVIEWS" and len(admission["previews"])==8
    points=load_batch(); ids=read(PRIVATE/"task_ids.json")
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400); main=ids["identity"]
    api=AbqJobPilotClient(); scoped=api.for_project(project_id=PID)
    environment(api); runtime_guard(deep=True); queue_prefix(scoped,api,points,0)
    assert sha(RT/"settings.json")==admission["protected_after"]["settings"]
    save(RUN/"checkpoints/enqueue_started.json",{"at":now(),"queue_only_submission_attempt":1,"FE_attempts_started":0,"no_automatic_resubmit":True})
    queued=[]
    for i,p in enumerate(points):
        tid=ids["point_tasks"][p["candidate_id"]]
        assert hub.task(tid)["execution_state"]=="PENDING"
        hub.require_approval(tid,"enqueue")
        lease=hub.claim(tid,main,f"run041-{p['candidate_id']}-queue-claim-v1")
        save(PRIVATE/f"lease_{p['candidate_id']}.json",lease)
        req=request(p,tid)
        with queue_transaction(RT):
            runtime_guard(); queue_prefix(scoped,api,points,i)
            assert sha(ROOT/p["inp_path"])==p["inp_sha256"] and not any((ROOT/p["working_dir"]).iterdir())
            save(RECEIPTS/f"{i+1:02d}_{p['candidate_id']}_request.json",req.to_dict())
            save(RUN/f"checkpoints/submission_{i+1:02d}_{p['candidate_id']}.json",{"at":now(),"submission_attempt":1,"FE_attempts":0,"candidate_id":p["candidate_id"]})
            response=scoped.enqueue(req,dry_run=False).to_dict()
            save(RECEIPTS/f"{i+1:02d}_{p['candidate_id']}_response.json",response)
            assert response["status"]=="ENQUEUED" and response["job_id"]
            assert response["queue_only"] and response["queue_file_mutated"] and not response["solver_started"] and not response["runner_started"]
            assert not response["forbidden_mutations_detected"]
            after=queue_prefix(scoped,api,points,i+1)
            assert after["queue_ids"][-1]==response["job_id"]
        status=scoped.status(job_id=response["job_id"]).to_dict()
        outputs=scoped.locate_outputs(job_id=response["job_id"]).to_dict()
        assert status["status"]=="QUEUED" and not status["odb_exists"] and not status["lock_exists"]
        assert not any((ROOT/p["working_dir"]).iterdir())
        receipt={"at":now(),"position":i+1,"candidate_id":p["candidate_id"],"algorithm":p["algorithm"],"job_name":p["job_name"],
                 "queue_id":response["job_id"],"task_id":tid,"project_id":PID,"inp_path":str(ROOT/p["inp_path"]),"inp_sha256":p["inp_sha256"],
                 "working_dir":str(ROOT/p["working_dir"]),"expected_odb":str(ROOT/p["expected_odb"]),"sigma_y_mpa":p["sigma_y_mpa"],"n":p["n"],
                 "cpus":14,"gpus":0,"run_datacheck":True,"run_full":True,"automatic_retries":0,
                 "execution_state":"QUEUED","actual_FE_attempts":0,"scientific_score_state":"NOT_EVALUATED",
                 "status":status,"outputs":outputs,"solver_started":False,"datacheck_started":False}
        path=RECEIPTS/f"{i+1:02d}_{p['candidate_id']}_receipt.json";save(path,receipt)
        hub.artifact(tid,main["agent_id"],path,{"run":"run_041","scope":"queue-only, not a started FE attempt"},version="run041-v1")
        hub.message(tid,main["agent_id"],"MAIN",receipt,f"run041-{p['candidate_id']}-queued-v1")
        hub.finish(lease,receipt,evidence_state="RECORDED",science_state="NOT_EVALUATED")
        queued.append(receipt)
        print(json.dumps({"queued":i+1,"of":8,"candidate_id":p["candidate_id"],"queue_id":response["job_id"]}),flush=True)
    final=queue_prefix(scoped,api,points,8); runtime=runtime_guard(deep=True)
    assert len(set(final["queue_ids"]))==8
    assert sha(RT/"settings.json")==admission["protected_after"]["settings"]
    assert sha(PROJECT/"project.db")==admission["protected_after"]["project_db"]
    for p in points:
        assert sha(ROOT/p["inp_path"])==p["inp_sha256"] and not any((ROOT/p["working_dir"]).iterdir())
    manifest={"at":now(),"status":"EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START","project_id":PID,
              "order":ORDER,"queue_ids":final["queue_ids"],"points":queued,
              "authorized_max_attempts":8,"queued_count":8,"started_attempts":0,"consumed_FE_budget":0,
              "remaining_start_allowance":8,"automatic_retries":0,"other_executable_jobs":0,
              "cpus":14,"gpus":0,"run_datacheck":True,"run_full":True,"solver_start":"USER_GUI_ONLY",
              "solver_started":False,"datacheck_started":False,"auto_stop":"AUTO_STOP_UNAVAILABLE",
              "runtime":runtime,"queue_after":final,
              "authorization_scope_sha256":sha(PRIVATE/"authorization_scope.json"),
              "frozen_batch_identity_sha256":sha(PRIVATE/"frozen_batch_identity.json")}
    save(PRIVATE/"queue_manifest.json",manifest)
    lease=hub.claim(ids["confirm_task_id"],main,"run041-final-queue-confirm-v1")
    save(PRIVATE/"confirm_lease.json",lease)
    hub.artifact(ids["confirm_task_id"],main["agent_id"],PRIVATE/"queue_manifest.json",{"run":"run_041","scope":"all eight exact queued; no solver starts"},version="run041-v1")
    hub.message(ids["confirm_task_id"],main["agent_id"],"MAIN",{"status":manifest["status"],"queue_ids":manifest["queue_ids"],"started_attempts":0},"run041-eight-queued-v1")
    hub.finish(lease,{"status":manifest["status"],"queue_ids":manifest["queue_ids"],"queued":8,"started_attempts":0,"consumed_FE_budget":0},evidence_state="RECORDED",science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    print(json.dumps({"status":manifest["status"],"queue_ids":manifest["queue_ids"],"started_attempts":0}))


if __name__=="__main__":
    assert len(sys.argv)==2 and sys.argv[1] in {"init","preflight","enqueue"}
    try:
        {"init":init,"preflight":preflight,"enqueue":enqueue}[sys.argv[1]]()
    except Exception:
        path=PRIVATE/f"{sys.argv[1]}_failure.json"
        if not path.exists():
            confirmed=[read(p) for p in sorted(RECEIPTS.glob("*_receipt.json"))] if RECEIPTS.exists() else []
            save(path,{"at":now(),"phase":sys.argv[1],"status":"BLOCKED","traceback":traceback.format_exc(),
                       "confirmed_queue_ids":[r["queue_id"] for r in confirmed],"no_automatic_retry":True})
        raise
