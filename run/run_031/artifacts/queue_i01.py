"""Record the authorized eight-job budget, then queue only frozen I01.

Modes are intentionally separate.  No mode starts Abaqus or the GUI Runner.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_031"
A = RUN / "artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
FROZEN = ROOT / "run/run_030/artifacts/prepared_batch.json"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import queue_transaction, runner_ownership_state
from abqjobpilot.recovery_assessment import assess_runtime
from agenthub_sp_invopt.hub import Hub

spec = importlib.util.spec_from_file_location("abq_settings_reader", ROOT / "run/run_017/artifacts/preview_batch.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
TERMINAL = {
    "COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL", "FAILED_NUMERICAL",
    "FAILED_INPUT", "FAILED_LICENSE", "DATACHECK_FAILED", "DATACHECK_FAILED_INVALID_GPU_OPTION",
    "SKIPPED", "CANCELLED",
}


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def save(path, data):
    p = Path(path)
    assert not p.exists(), f"Existing record: {p}"
    tmp = p.with_name(p.name + ".tmp")
    with tmp.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    read(tmp)
    tmp.replace(p)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def frozen():
    batch = read(FROZEN)
    completion = read(ROOT / "run/run_030/checkpoints/completion.json")
    assert sha(FROZEN) == completion["prepared_batch_sha256"]
    assert batch["status"] == "PREPARED_AWAITING_EXPLICIT_SOLVER_AUTHORIZATION"
    assert batch["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert batch["loss_version"] == "run017-exploratory-fd-v1"
    assert batch["project_id"] == PID and batch["cpus"] == 14 and batch["gpus"] == 0
    assert batch["run_datacheck"] is True and batch["run_full"] is True
    assert batch["new_enqueues"] == batch["new_solver_jobs"] == 0
    points = batch["points"]
    assert [p["point_id"] for p in points] == [f"I{i:02d}" for i in range(1, 9)]
    assert len({p["job_name"] for p in points}) == 8
    assert len({p["inp_sha256"] for p in points}) == 8
    assert sha(ROOT / "run/run_030/artifacts/parameter_design.json") == batch["design_sha256"]
    assert sha(ROOT / "run/run_030/artifacts/model_contract.json") == batch["model_contract_sha256"]
    assert sha(ROOT / "run/run_030/artifacts/loss_contract_binding.json") == batch["loss_contract_binding_sha256"]
    for p in points:
        inp = ROOT / p["inp_path"]
        params = ROOT / p["parameters_path"]
        work = ROOT / p["working_dir"]
        assert inp.is_file() and inp.stem == p["job_name"] and sha(inp) == p["inp_sha256"]
        assert params.is_file() and sha(params) == p["parameters_sha256"]
        assert work.is_dir() and not any(work.iterdir()), f"Output conflict: {work}"
        par = read(params)
        assert par["sigma_y_mpa"] == p["sigma_y_mpa"] and par["n"] == p["n"]
        assert par["inp_sha256"] == p["inp_sha256"]
    return batch, points[0]


def protected(batch):
    paths = [FROZEN, PROJECT / "project.json", RT / "settings.json", RT / "queue.json",
             PROJECT / "project.db", RT / "live_status.json"]
    paths += [ROOT / p["inp_path"] for p in batch["points"]]
    paths += [ROOT / p["parameters_path"] for p in batch["points"]]
    return {str(p): sha(p) for p in paths}


def runtime_state(job):
    owner = runner_ownership_state(RT)
    recovery = assess_runtime(RT, project_db=PROJECT / "project.db")
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    procs = raw if isinstance(raw, list) else [raw]
    conflicts = [p for p in procs if
                 re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", p.get("Name") or "", re.I)
                 or ((p.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                     and job.lower() in (p.get("CommandLine") or "").lower())]
    assert owner["state"] == "ABSENT" and recovery["status"] == "CLEAN"
    assert recovery["live_phase"] == "IDLE" and not recovery["lock_files"]
    assert not recovery["errors"] and not recovery["running_queue_ids"] and not conflicts
    return {"at": now(), "owner": owner, "recovery": recovery, "process_conflicts": conflicts}


def queue_state(api, batch, p):
    q = api.list_jobs()
    h = api.list_project_jobs(project_id=PID).to_dict()
    assert q["status"] == h["status"] == "OK" and not q["errors"] and not h["errors"]
    existing = []
    inp = ROOT / p["inp_path"]
    work = ROOT / p["working_dir"]
    frozen_names = {x["job_name"] for x in batch["points"]}
    for j in q["jobs"]:
        same = (j.get("job_name") == p["job_name"] or
                Path(j.get("inp_path") or "").resolve() == inp.resolve() or
                Path(j.get("work_dir") or "").resolve() == work.resolve())
        if same:
            assert j["job_name"] == p["job_name"]
            assert Path(j["inp_path"]).resolve() == inp.resolve()
            assert Path(j["work_dir"]).resolve() == work.resolve()
            assert j["cpus"] == 14 and j["gpus"] == 0
            assert j["run_datacheck"] is True and j["run_full"] is True
            assert p["inp_sha256"] in (j.get("notes") or "")
            assert j["status"] == "QUEUED" and not j.get("started_at") and not j.get("ended_at")
            existing.append(j)
        else:
            assert j.get("raw_status") in TERMINAL, f"Other executable or unresolved queue item: {j.get('job_name')}"
            assert j.get("job_name") not in frozen_names, "Other run030 job already submitted"
    assert len(existing) <= 1
    history_matches = [j for j in h["jobs"] if j.get("job_name") == p["job_name"] or
                       Path(j.get("inp_path") or "").resolve() == inp.resolve()]
    assert not history_matches, "I01 already has a historical execution attempt"
    return {"queue": q, "history": h, "existing": existing}


def request(p, task_id=None, *, preview=False):
    return JobRequest(
        inp_path=str(ROOT / p["inp_path"]), job_name=p["job_name"],
        working_dir=str(ROOT / p["working_dir"]), cpus=14, gpus=0,
        run_datacheck=True, run_full=True,
        submission_mode="preview_only" if preview else "enqueue_only", allow_solver_submit=False,
        batch="run031_authorized_initial_eight", strategy="SEQUENTIAL_ONE_JOB_GATE",
        metadata={"run": "run_031", "point_id": "I01", "project_id": PID,
                  "task_id": task_id, "inp_sha256": p["inp_sha256"],
                  "maximum_attempts": 1, "automatic_retries": 0,
                  "notes": f"run031 I01; project_id={PID}; inp_sha256={p['inp_sha256']}; task_id={task_id}; 14CPU 0GPU; one Datacheck then Full; zero retries; manual GUI Start Queue; I02-I08 not yet eligible"},
    )


def prepare():
    assert not (RUN / "run.json").exists(), "run_031 already initialized; do not repeat"
    batch, p = frozen()
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save(RUN / "checkpoints/start.json", {"at": now(), "git": git_state,
                                           "python": sys.executable, "version": sys.version.split()[0]})
    save(RUN / "run.json", {"schema_version": "1.0", "run_id": "run_031",
                            "stage": "authorized I01 queue-only; eight-job sequential budget",
                            "objective": "Record eight frozen authorizations and queue I01 only, awaiting manual GUI start",
                            "status": "RUNNING", "start_time": now(), "end_time": None,
                            "git": git_state, "python_interpreter": sys.executable,
                            "inputs": [{"path": rel(FROZEN), "sha256": sha(FROZEN)},
                                       {"path": "run/run_030/artifacts/pilot_protocol.md",
                                        "sha256": sha(ROOT / "run/run_030/artifacts/pilot_protocol.md")}],
                            "outputs": [], "validation": [], "errors": []})
    (RUN / "summary.md").write_text("# run_031 — 八项授权下的 I01 Queue-only\n\nRUNNING；Codex 禁止启动 Solver。\n", encoding="utf-8")
    before = protected(batch)
    api, settings = reader.inspect_settings()
    s = settings["settings_response"]
    v = s["effective_settings"]
    assert s["status"] == "PERSISTED" and s["project_id"] == PID
    assert Path(s["project_path"]).resolve() == PROJECT.resolve()
    assert read(PROJECT / "project.json")["project_id"] == PID
    assert v["default_cpus"] == 14 and v["default_gpus"] == 0
    assert not v["use_gpu"] and v["run_datacheck"] and v["run_full"]
    assert Path(v["abaqus_cmd"]).is_file() and "abq2024" in Path(v["abaqus_cmd"]).name.lower()
    assert settings["source_version"] == "0.2.2" and settings["source_working_tree"] == ""
    runtime = runtime_state(p["job_name"])
    queue = queue_state(api, batch, p)
    req = request(p, preview=True)
    pre = api.preflight(req).to_dict()
    dry = api.enqueue(req, dry_run=True).to_dict()
    assert pre["status"] == "PREVIEW_READY" and not pre["errors"]
    assert dry["status"] == "DRY_RUN_READY" and not dry["errors"] and dry["job_id"] is None
    assert not any(dry[k] for k in ("queue_file_mutated", "solver_started", "runner_started", "forbidden_mutations_detected"))
    assert Path(pre["expected_odb_path"]).resolve() == (ROOT / p["expected_odb"]).resolve()
    assert protected(batch) == before and not any((ROOT / p["working_dir"]).iterdir())
    save(A / "admission.json", {"at": now(), "status": "PASS", "project_id": PID,
                                "batch_sha256": sha(FROZEN), "i01": p,
                                "settings": settings, "runtime": runtime, "queue": queue,
                                "preflight": pre, "dry_run": dry,
                                "protected_hashes": before, "no_queue_mutation": True,
                                "existing_i01_queued": len(queue["existing"])})
    # User authorization is one immutable scope; each Job has a separate pending Hub task.
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    identity = hub.register("MAIN", "codex-main-run031-eight-budget")
    scope = {"run": "run_031", "authorization_source": "Explicit user eight-job authorization in current conversation",
             "prepared_batch_sha256": sha(FROZEN), "project_id": PID,
             "jobs": [{"point_id": x["point_id"], "job_name": x["job_name"],
                       "inp_sha256": x["inp_sha256"], "inp_path": str(ROOT / x["inp_path"]),
                       "working_dir": str(ROOT / x["working_dir"]),
                       "sigma_y_mpa": x["sigma_y_mpa"], "n": x["n"],
                       "maximum_attempts": 1} for x in batch["points"]],
             "total_authorized_jobs": 8, "cpus": 14, "gpus": 0,
             "run_datacheck": True, "run_full": True,
             "automatic_retries": 0, "solver_start": "USER_GUI_ONLY",
             "submission": "one eligible Job at a time; next depends on actual result review",
             "budget_not_transferable_to_other_parameters": True,
             "numerical_contract": batch["numeric_version"], "loss_contract": batch["loss_version"]}
    budget_task = hub.create_task(identity["agent_id"], "MAIN", "authorize_eight_frozen_jobs",
                                  scope, "run031-eight-budget-authorization-v1")["task_id"]
    budget_lease = hub.claim(budget_task, identity, "run031-budget-record-claim-v1")
    queue_tasks = {}
    review_tasks = {}
    previous_review = None
    phase_gate_task = None
    for x in batch["points"]:
        ident = x["point_id"]
        if ident == "I01":
            deps = (budget_task,)
        elif ident == "I05":
            assert phase_gate_task is not None
            deps = (phase_gate_task,)
        else:
            deps = (previous_review,)
        payload = {"run": "run_031", "budget_task_id": budget_task,
                   "point_id": ident, "job_name": x["job_name"],
                   "inp_path": str(ROOT / x["inp_path"]), "inp_sha256": x["inp_sha256"],
                   "working_dir": str(ROOT / x["working_dir"]),
                   "sigma_y_mpa": x["sigma_y_mpa"], "n": x["n"],
                   "project_id": PID, "cpus": 14, "gpus": 0,
                   "run_datacheck": True, "run_full": True,
                   "maximum_attempts": 1, "automatic_retries": 0,
                   "solver_start": "USER_GUI_ONLY", "gate": "PREVIOUS_REAL_RESULT_MAIN_REVIEW" if ident != "I01" else "ADMISSION_CHECKS"}
        qid = hub.create_task(identity["agent_id"], "MAIN", "queue_one_frozen_job",
                              payload, f"run031-{ident}-queue-v1", depends=deps)["task_id"]
        queue_tasks[ident] = qid
        review_payload = {"run": "run_031", "point_id": ident, "queue_task_id": qid,
                          "required": "Actual Datacheck/Full status, real ODB Agent read-only extraction, frozen Loss and numerical-warning MAIN review before next queue"}
        rid = hub.create_task(identity["agent_id"], "MAIN", "review_one_frozen_job",
                              review_payload, f"run031-{ident}-result-review-v1", depends=(qid,))["task_id"]
        review_tasks[ident] = rid
        previous_review = rid
        if ident == "I04":
            phase_gate_task = hub.create_task(identity["agent_id"], "MAIN", "initial_four_gate",
                                              {"run": "run_031", "review_task_ids": [review_tasks[f"I{i:02d}"] for i in range(1, 5)],
                                               "condition": "MAIN confirms no blocking numerical issue before I05"},
                                              "run031-I01-I04-gate-v1", depends=(rid,))["task_id"]
    hub.approve(queue_tasks["I01"], identity["agent_id"], "enqueue")
    hub.approve(queue_tasks["I01"], identity["agent_id"], "start_solver")
    save(A / "authorization.json", {"at": now(), "scope": scope,
                                    "budget_task_id": budget_task,
                                    "queue_task_ids": queue_tasks,
                                    "result_review_task_ids": review_tasks,
                                    "phase_gate_task_id": phase_gate_task,
                                    "I01_task_approved_actions": ["enqueue", "start_solver"],
                                    "I02_I08_gate_pending": True,
                                    "approved_new_solver_jobs": 8,
                                    "queue_submitted": 0, "started_attempts_confirmed": 0})
    for path in (A / "authorization.json", A / "admission.json", FROZEN):
        hub.artifact(budget_task, identity["agent_id"], path,
                     {"run": "run_031", "role": "eight-job authorization and preflight"}, version="run031-v1")
    hub.finish(budget_lease, {"status": "EIGHT_FROZEN_JOBS_AUTHORIZED_WITH_SEQUENTIAL_GATE",
                              "authorized": 8, "queued": 0, "started_confirmed": 0,
                              "queue_task_ids": queue_tasks},
               evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    save(P / "main_session.json", {"identity": identity, "budget_task_id": budget_task,
                                   "queue_tasks": queue_tasks, "review_tasks": review_tasks,
                                   "phase_gate_task_id": phase_gate_task})
    print(json.dumps({"status": "PASS_ADMISSION_AUTHORIZATION_RECORDED", "budget_task_id": budget_task,
                      "I01_task_id": queue_tasks["I01"], "preflight": pre["status"],
                      "dry_run": dry["status"], "existing_i01": len(queue["existing"])}))


def enqueue():
    assert not (A / "enqueue_result.json").exists()
    assert not (RUN / "checkpoints/enqueue_attempt.json").exists(), "Prior attempt; read-only reconcile"
    admission = read(A / "admission.json")
    assert admission["status"] == "PASS"
    batch, p = frozen()
    assert protected(batch) == admission["protected_hashes"]
    api, settings = reader.inspect_settings()
    assert settings["settings_response"] == admission["settings"]["settings_response"]
    assert settings["source_head"] == admission["settings"]["source_head"]
    assert settings["source_working_tree"] == admission["settings"]["source_working_tree"]
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    session = read(P / "main_session.json")
    identity = session["identity"]
    task_id = session["queue_tasks"]["I01"]
    assert hub.task(session["budget_task_id"])["execution_state"] == "COMPLETED"
    hub.require_approval(task_id, "enqueue")
    hub.require_approval(task_id, "start_solver")
    lease = hub.claim(task_id, identity, "run031-I01-queue-claim-v1")
    save(P / "i01_lease.json", lease)
    with queue_transaction(RT):
        runtime = runtime_state(p["job_name"])
        q = queue_state(api, batch, p)
        assert q["queue"] == admission["queue"]["queue"]
        assert protected(batch) == admission["protected_hashes"]
        assert not any((ROOT / p["working_dir"]).iterdir())
        req = request(p, task_id)
        save(A / "request.json", req.to_dict())
        if q["existing"]:
            response = {"status": "EXISTING_VERIFIED", "job_id": q["existing"][0]["queue_id"],
                        "solver_started": False, "runner_started": False}
        else:
            save(RUN / "checkpoints/enqueue_attempt.json",
                 {"at": now(), "attempt_number": 1, "request_sha256": sha(A / "request.json"),
                  "retry_forbidden": True, "unknown_outcome_requires_readonly_reconciliation": True})
            response = api.enqueue(req, dry_run=False).to_dict()
        save(A / "enqueue_response.json", response)
        assert response["status"] in ("ENQUEUED", "EXISTING_VERIFIED") and response["job_id"]
        assert not response["solver_started"] and not response["runner_started"]
        after = queue_state(api, batch, p)
        assert len(after["existing"]) == 1 and after["existing"][0]["queue_id"] == response["job_id"]
        assert len(after["queue"]["jobs"]) == len(q["queue"]["jobs"]) + (0 if q["existing"] else 1)
        save(A / "queue_after.json", after)
    post_runtime = runtime_state(p["job_name"])
    assert protected(batch)[str(ROOT / p["inp_path"])] == p["inp_sha256"]
    status = api.status(job_id=response["job_id"]).to_dict()
    outputs = api.locate_outputs(job_id=response["job_id"]).to_dict()
    assert status["status"] == "QUEUED" and not status["odb_exists"] and not status["lock_exists"]
    assert not any((ROOT / p["working_dir"]).iterdir())
    save(A / "postcheck.json", {"at": now(), "runtime": post_runtime,
                                "status": status, "outputs": outputs,
                                "no_solver_or_datacheck_start": True})
    result = {"at": now(), "status": "I01_QUEUED_AWAITING_MANUAL_START",
              "budget_task_id": session["budget_task_id"], "task_id": task_id,
              "queue_id": response["job_id"], "job_name": p["job_name"],
              "point_id": "I01", "project_id": PID,
              "inp_path": str(ROOT / p["inp_path"]), "inp_sha256": p["inp_sha256"],
              "working_dir": str(ROOT / p["working_dir"]),
              "sigma_y_mpa": p["sigma_y_mpa"], "n": p["n"],
              "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
              "automatic_retries": 0, "queue_submitted_count": 1,
              "started_attempts_confirmed": 0, "remaining_unsubmitted_frozen_jobs": 7,
              "datacheck_started": False, "solver_started": False,
              "I02_I08_queued": False, "loss_status": "NOT_EVALUATED"}
    save(A / "enqueue_result.json", result)
    for path in (A / "request.json", A / "enqueue_response.json", A / "queue_after.json",
                 A / "postcheck.json", A / "enqueue_result.json"):
        hub.artifact(task_id, identity["agent_id"], path,
                     {"run": "run_031", "point": "I01", "scope": "one queue-only; manual GUI Solver",
                      "inp_sha256": p["inp_sha256"]}, version="run031-v1")
    hub.message(task_id, identity["agent_id"], "MAIN", result, "run031-I01-queued-message-v1")
    hub.finish(lease, result, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    save(A / "agenthub_receipt.json", {"at": now(), "budget_task_id": session["budget_task_id"],
                                      "i01_task_id": task_id, "queue_id": response["job_id"],
                                      "I01_review_task_id": session["review_tasks"]["I01"],
                                      "audit_chain_valid": True,
                                      "remaining_jobs_gate_pending": 7,
                                      "cross_session_auto_wakeup": False})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ("prepare", "enqueue"):
            raise ValueError("USAGE: queue_i01.py prepare|enqueue")
        (prepare if sys.argv[1] == "prepare" else enqueue)()
    except Exception:
        P.mkdir(parents=True, exist_ok=True)
        save(P / ("failure_" + datetime.now().strftime("%H%M%S%f") + ".json"),
             {"at": now(), "status": "BLOCKED", "traceback": traceback.format_exc(),
              "no_automatic_retry": True})
        raise
