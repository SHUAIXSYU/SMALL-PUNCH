"""Submit only frozen I02 after the completed I01 MAIN gate.

The two modes are separate. This never starts the GUI Runner or Abaqus.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_032"
A = RUN / "artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
BATCH = ROOT / "run/run_030/artifacts/prepared_batch.json"
TERMINAL = {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL",
            "FAILED_NUMERICAL", "FAILED_INPUT", "FAILED_LICENSE",
            "DATACHECK_FAILED", "DATACHECK_FAILED_INVALID_GPU_OPTION",
            "SKIPPED", "CANCELLED"}
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import queue_transaction, runner_ownership_state
from abqjobpilot.recovery_assessment import assess_runtime
from agenthub_sp_invopt.hub import Hub

spec = importlib.util.spec_from_file_location("settings_reader", ROOT / "run/run_017/artifacts/preview_batch.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


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


def frozen():
    batch = read(BATCH)
    completion = read(ROOT / "run/run_030/checkpoints/completion.json")
    auth = read(ROOT / "run/run_031/artifacts/authorization.json")
    gate = read(A / "main_i01_gate.json")
    assert sha(BATCH) == completion["prepared_batch_sha256"] == auth["scope"]["prepared_batch_sha256"]
    assert auth["scope"]["total_authorized_jobs"] == 8
    assert auth["scope"]["automatic_retries"] == 0
    assert auth["scope"]["solver_start"] == "USER_GUI_ONLY"
    assert batch["project_id"] == auth["scope"]["project_id"] == PID
    assert batch["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert batch["loss_version"] == "run017-exploratory-fd-v1"
    assert gate["status"] == "PASS_I01_EXPLORATORY_GATE_WITH_WARNINGS"
    assert gate["I02_enqueue_gate_open"] is True
    assert gate["review_task_id"] == auth["result_review_task_ids"]["I01"]
    assert gate["odb_task_id"] == read(A / "task_ids.json")["odb_task_id"]
    assert len(batch["points"]) == 8 and [p["point_id"] for p in batch["points"]] == [f"I{i:02d}" for i in range(1, 9)]
    point = batch["points"][1]
    assert point["point_id"] == "I02" and point["job_name"] == "SPIO_R030_I02_L"
    assert point["inp_sha256"] == "c93d77fcbd6e0bab8a12e439a3ab987a37360663296d6e2e62ceaa2610814e47"
    assert sha(ROOT / point["inp_path"]) == point["inp_sha256"]
    assert sha(ROOT / point["parameters_path"]) == point["parameters_sha256"]
    params = read(ROOT / point["parameters_path"])
    assert params["sigma_y_mpa"] == point["sigma_y_mpa"] == 188.34769426063204
    assert params["n"] == point["n"] == 0.116
    assert params["inp_sha256"] == point["inp_sha256"]
    assert (ROOT / point["working_dir"]).is_dir()
    assert not any((ROOT / point["working_dir"]).iterdir()), "I02 output conflict"
    return batch, point, auth, gate


def current_runtime():
    owner = runner_ownership_state(RT)
    recovery = assess_runtime(RT, project_db=PROJECT / "project.db")
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    procs = raw if isinstance(raw, list) else [raw]
    conflicts = [p for p in procs if
                 re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", p.get("Name") or "", re.I)
                 or ((p.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                     and any(x in (p.get("CommandLine") or "").lower()
                             for x in ("spio_r030_i01_g", "spio_r030_i02_l")))]
    assert owner["state"] == "ABSENT"
    assert recovery["status"] == "CLEAN" and recovery["live_phase"] == "IDLE"
    assert not recovery["lock_files"] and not recovery["errors"]
    assert not recovery["running_queue_ids"] and not conflicts
    return {"at": now(), "owner": owner, "recovery": recovery, "process_conflicts": conflicts}


def queue_state(api, batch, point):
    q = api.list_jobs()
    hist = api.list_project_jobs(project_id=PID).to_dict()
    assert q["status"] == hist["status"] == "OK"
    assert not q["errors"] and not hist["errors"]
    inp = (ROOT / point["inp_path"]).resolve()
    work = (ROOT / point["working_dir"]).resolve()
    existing = []
    for job in q["jobs"]:
        same = (job["job_name"] == point["job_name"] or
                Path(job.get("inp_path") or "").resolve() == inp or
                Path(job.get("work_dir") or "").resolve() == work)
        if same:
            assert job["job_name"] == point["job_name"]
            assert Path(job["inp_path"]).resolve() == inp
            assert Path(job["work_dir"]).resolve() == work
            assert job["cpus"] == 14 and job["gpus"] == 0
            assert job["run_datacheck"] and job["run_full"]
            assert point["inp_sha256"] in (job.get("notes") or "")
            assert job["status"] == "QUEUED" and not job.get("started_at") and not job.get("ended_at")
            existing.append(job)
        else:
            assert job.get("raw_status") in TERMINAL, f"Other executable or unresolved: {job['job_name']}"
            if job["job_name"] == batch["points"][0]["job_name"]:
                assert job["queue_id"] == read(ROOT / "run/run_031/artifacts/enqueue_result.json")["queue_id"]
                assert job["raw_status"] == "COMPLETED_WITH_WARNINGS"
            else:
                assert job["job_name"] not in {p["job_name"] for p in batch["points"][2:]}, "Later run030 Job already queued"
    assert len(existing) <= 1
    matches = [h for h in hist["jobs"] if h["job_name"] == point["job_name"] or
               Path(h.get("inp_path") or "").resolve() == inp]
    assert not matches, "I02 historical execution attempt exists"
    return {"queue": q, "history": hist, "existing": existing}


def request(point, task_id, *, preview=False):
    return JobRequest(
        inp_path=str(ROOT / point["inp_path"]), job_name=point["job_name"],
        working_dir=str(ROOT / point["working_dir"]), cpus=14, gpus=0,
        run_datacheck=True, run_full=True,
        submission_mode="preview_only" if preview else "enqueue_only",
        allow_solver_submit=False,
        batch="run031_authorized_initial_eight", strategy="SEQUENTIAL_ONE_JOB_GATE",
        metadata={"run": "run_032", "point_id": "I02", "project_id": PID,
                  "task_id": task_id, "inp_sha256": point["inp_sha256"],
                  "maximum_attempts": 1, "automatic_retries": 0,
                  "notes": f"run032 I02; project_id={PID}; inp_sha256={point['inp_sha256']}; task_id={task_id}; 14CPU 0GPU; one Datacheck then Full; zero retries; manual GUI Start Queue; I01 MAIN gate PASS"},
    )


def protected(point):
    paths = [BATCH, ROOT / point["inp_path"], ROOT / point["parameters_path"],
             PROJECT / "project.json", RT / "settings.json"]
    return {str(p): sha(p) for p in paths}


def admission():
    assert not (A / "i02_admission.json").exists()
    batch, point, auth, gate = frozen()
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    assert hub.task(auth["budget_task_id"])["execution_state"] == "COMPLETED"
    review = hub.task(auth["result_review_task_ids"]["I01"])
    assert review["execution_state"] == "COMPLETED"
    assert json.loads(review["result"]) == gate
    assert hub.task(auth["queue_task_ids"]["I02"])["execution_state"] == "PENDING"
    before = protected(point)
    api, settings = reader.inspect_settings()
    s = settings["settings_response"]
    v = s["effective_settings"]
    assert s["status"] == "PERSISTED" and s["project_id"] == PID
    assert Path(s["project_path"]).resolve() == PROJECT.resolve()
    assert read(PROJECT / "project.json")["project_id"] == PID
    assert v["default_cpus"] == 14 and v["default_gpus"] == 0 and not v["use_gpu"]
    assert v["run_datacheck"] and v["run_full"]
    assert Path(v["abaqus_cmd"]).is_file() and "abq2024" in Path(v["abaqus_cmd"]).name.lower()
    assert settings["source_version"] == "0.2.2" and settings["source_working_tree"] == ""
    runtime = current_runtime()
    q = queue_state(api, batch, point)
    assert not q["existing"], "I02 already queued; use read-only reconciliation"
    pre = api.preflight(request(point, auth["queue_task_ids"]["I02"], preview=True)).to_dict()
    dry = api.enqueue(request(point, auth["queue_task_ids"]["I02"], preview=True), dry_run=True).to_dict()
    assert pre["status"] == "PREVIEW_READY" and not pre["errors"]
    assert dry["status"] == "DRY_RUN_READY" and not dry["errors"] and dry["job_id"] is None
    assert not any(dry[k] for k in ("queue_file_mutated", "solver_started", "runner_started", "forbidden_mutations_detected"))
    assert Path(pre["expected_odb_path"]).resolve() == (ROOT / point["expected_odb"]).resolve()
    assert protected(point) == before and not any((ROOT / point["working_dir"]).iterdir())
    save_once(A / "i02_admission.json", {"at": now(), "status": "PASS", "point": point,
                                           "project_id": PID, "batch_sha256": sha(BATCH),
                                           "settings": settings, "runtime": runtime,
                                           "queue": q, "preflight": pre, "dry_run": dry,
                                           "protected_hashes": before,
                                           "i01_main_gate_sha256": sha(A / "main_i01_gate.json"),
                                           "I02_output_empty": True, "other_executable_jobs": 0})
    print(json.dumps({"status": "I02_ADMISSION_PASS", "preflight": pre["status"],
                      "dry_run": dry["status"]}))


def enqueue():
    assert not (A / "i02_enqueue_result.json").exists()
    admission_record = read(A / "i02_admission.json")
    assert admission_record["status"] == "PASS"
    batch, point, auth, gate = frozen()
    assert sha(A / "main_i01_gate.json") == admission_record["i01_main_gate_sha256"]
    assert protected(point) == admission_record["protected_hashes"]
    api, settings = reader.inspect_settings()
    assert settings["settings_response"] == admission_record["settings"]["settings_response"]
    assert settings["source_head"] == admission_record["settings"]["source_head"]
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    main = read(P / "main_session.json")["identity"]
    task_id = auth["queue_task_ids"]["I02"]
    assert hub.task(auth["result_review_task_ids"]["I01"])["execution_state"] == "COMPLETED"
    assert hub.task(task_id)["execution_state"] == "PENDING"
    # The user already approved I01-I08, but task-scoped actions remain separate.
    hub.approve(task_id, main["agent_id"], "enqueue")
    hub.approve(task_id, main["agent_id"], "start_solver")
    hub.require_approval(task_id, "enqueue")
    hub.require_approval(task_id, "start_solver")
    lease = hub.claim(task_id, main, "run032-I02-queue-claim-v1")
    save_once(P / "i02_lease.json", lease)
    with queue_transaction(RT):
        runtime = current_runtime()
        q = queue_state(api, batch, point)
        assert protected(point) == admission_record["protected_hashes"]
        assert not any((ROOT / point["working_dir"]).iterdir())
        req = request(point, task_id)
        save_once(A / "i02_request.json", req.to_dict())
        if q["existing"]:
            response = {"status": "EXISTING_VERIFIED", "job_id": q["existing"][0]["queue_id"],
                        "solver_started": False, "runner_started": False}
        else:
            save_once(RUN / "checkpoints/i02_enqueue_attempt.json",
                      {"at": now(), "attempt_number": 1,
                       "request_sha256": sha(A / "i02_request.json"),
                       "retry_forbidden": True,
                       "unknown_outcome_requires_readonly_reconciliation": True})
            response = api.enqueue(req, dry_run=False).to_dict()
        save_once(A / "i02_enqueue_response.json", response)
        assert response["status"] in ("ENQUEUED", "EXISTING_VERIFIED") and response["job_id"]
        assert not response["solver_started"] and not response["runner_started"]
        after = queue_state(api, batch, point)
        assert len(after["existing"]) == 1 and after["existing"][0]["queue_id"] == response["job_id"]
        assert len(after["queue"]["jobs"]) == len(q["queue"]["jobs"]) + (0 if q["existing"] else 1)
        save_once(A / "i02_queue_after.json", after)
    post_runtime = current_runtime()
    status = api.status(job_id=response["job_id"]).to_dict()
    outputs = api.locate_outputs(job_id=response["job_id"]).to_dict()
    assert status["status"] == "QUEUED" and not status["odb_exists"] and not status["lock_exists"]
    assert protected(point) == admission_record["protected_hashes"]
    assert not any((ROOT / point["working_dir"]).iterdir())
    save_once(A / "i02_postcheck.json", {"at": now(), "runtime": post_runtime,
                                           "status": status, "outputs": outputs,
                                           "no_solver_or_datacheck_start": True})
    outcome = {"at": now(), "status": "I02_QUEUED_AWAITING_MANUAL_START",
               "point_id": "I02", "job_name": point["job_name"],
               "queue_id": response["job_id"], "task_id": task_id,
               "project_id": PID, "inp_path": str(ROOT / point["inp_path"]),
               "inp_sha256": point["inp_sha256"],
               "working_dir": str(ROOT / point["working_dir"]),
               "sigma_y_mpa": point["sigma_y_mpa"], "n": point["n"],
               "cpus": 14, "gpus": 0, "run_datacheck": True,
               "run_full": True, "automatic_retries": 0,
               "i01_completed_attempts": 1, "i02_started_attempts": 0,
               "remaining_unsubmitted_frozen_jobs": 6,
               "other_executable_jobs": 0,
               "solver_started": False, "datacheck_started": False,
               "manual_start_required": True}
    save_once(A / "i02_enqueue_result.json", outcome)
    for path in (A / "i02_admission.json", A / "i02_request.json",
                 A / "i02_enqueue_response.json", A / "i02_queue_after.json",
                 A / "i02_postcheck.json", A / "i02_enqueue_result.json"):
        hub.artifact(task_id, main["agent_id"], path,
                     {"run": "run_032", "point": "I02", "inp_sha256": point["inp_sha256"],
                      "scope": "one queue-only; user GUI starts Solver"}, version="run032-v1")
    hub.message(task_id, main["agent_id"], "MAIN", outcome, "run032-I02-queued-message-v1")
    hub.finish(lease, outcome, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    print(json.dumps(outcome, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"admission", "enqueue"}:
        raise SystemExit("usage: queue_i02.py admission|enqueue")
    (admission if sys.argv[1] == "admission" else enqueue)()
