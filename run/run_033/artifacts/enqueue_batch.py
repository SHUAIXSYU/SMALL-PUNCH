"""Queue exactly 20 frozen DOE jobs through AbqJobPilot, never starting Solver.

`register` records task-scoped approvals. `enqueue` is a one-shot operation;
on a partial/uncertain outcome it stops and requires read-only reconciliation.
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

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_033"
A = RUN / "artifacts"
P = A / "private"
RECEIPTS = A / "queue_receipts"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
TERMINAL = {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL",
            "FAILED_NUMERICAL", "FAILED_INPUT", "FAILED_LICENSE",
            "DATACHECK_FAILED", "DATACHECK_FAILED_INVALID_GPU_OPTION",
            "SKIPPED", "CANCELLED"}
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.runtime_coordination import queue_transaction, runner_ownership_state
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
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def load_batch():
    batch_path = A / "prepared_batch.json"
    batch = read(batch_path)
    review = read(A / "main_review_result.json")
    assert review["status"] == "PASS_ALL_TWENTY_PREVIEWS"
    assert review["prepared_batch_sha256"] == sha(batch_path)
    assert batch["status"] == "ALL_PREVIEWS_PASS_QUEUE_PENDING"
    assert batch["project_id"] == PID and len(batch["points"]) == 20
    assert batch["batch_order"] == [p["point_id"] for p in batch["points"]]
    assert batch["cpus"] == 14 and batch["gpus"] == 0
    assert batch["run_datacheck"] and batch["run_full"]
    assert batch["automatic_retries"] == 0
    assert batch["solver_start"] == "USER_GUI_ONLY"
    assert batch["new_enqueues"] == batch["new_solver_starts"] == 0
    return batch


def static_identity(batch):
    for p in batch["points"]:
        inp = ROOT / p["inp_path"]
        params = ROOT / p["parameters_path"]
        work = ROOT / p["working_dir"]
        assert inp.is_file() and inp.stem == p["job_name"]
        assert params.is_file() and sha(params) == p["parameters_sha256"]
        assert sha(inp) == p["inp_sha256"]
        assert work.is_dir() and not any(work.iterdir()), f"Output conflict: {work}"


def persisted_settings(api):
    s = api.get_project_settings(project_id=PID).to_dict()
    p = api.show_project(project_id=PID).to_dict()
    caps = api.capabilities()
    assert caps["application_version"] == "0.2.2"
    assert s["status"] == "PERSISTED" and s["project_id"] == PID
    assert s["persisted"] and not s["defaulted_fields"] and not s["errors"]
    assert p["status"] == "OK" and p["project"]["project_id"] == PID
    assert Path(s["project_path"]).resolve() == PROJECT.resolve()
    assert read(PROJECT / "project.json")["project_id"] == PID
    assert s["settings"] == read(RT / "settings.json")
    v = s["effective_settings"]
    assert Path(v["abaqus_cmd"]).is_file()
    assert Path(v["abaqus_cmd"]).name.lower() == "abq2024.bat"
    assert v["default_cpus"] == 14 and v["default_gpus"] == 0
    assert v["use_gpu"] is False and v["run_datacheck"] and v["run_full"]
    return {"settings": s, "project": p, "capabilities": caps}


def runtime_clear():
    owner = runner_ownership_state(RT)
    recovery = assess_runtime(RT, project_db=PROJECT / "project.db")
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    items = raw if isinstance(raw, list) else [raw]
    conflicts = [p for p in items if
                 re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", p.get("Name") or "", re.I)
                 or ((p.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                     and any(x in (p.get("CommandLine") or "").lower()
                             for x in ("spio_r030_i0", "spio_r033_d")))]
    assert owner["state"] == "ABSENT"
    assert recovery["status"] == "CLEAN" and recovery["live_phase"] == "IDLE"
    assert not recovery["errors"] and not recovery["lock_files"]
    assert not recovery["running_queue_ids"] and not conflicts
    return {"at": now(), "owner": owner, "recovery": recovery,
            "process_conflicts": conflicts}


def queue_prefix(api, batch, expected_prefix):
    q = api.list_jobs()
    h = api.list_project_jobs(project_id=PID).to_dict()
    assert q["status"] == h["status"] == "OK" and not q["errors"] and not h["errors"]
    candidate_names = {p["job_name"] for p in batch["points"]}
    executable = [j for j in q["jobs"] if j.get("raw_status") not in TERMINAL]
    assert [j["job_name"] for j in executable] == [p["job_name"] for p in batch["points"][:expected_prefix]], "Unexpected executable Queue content/order"
    for i, job in enumerate(executable):
        p = batch["points"][i]
        assert job["status"] == "QUEUED" and job["raw_status"] == "QUEUED"
        assert job["cpus"] == 14 and job["gpus"] == 0
        assert job["run_datacheck"] and job["run_full"]
        assert Path(job["inp_path"]).resolve() == (ROOT / p["inp_path"]).resolve()
        assert Path(job["work_dir"]).resolve() == (ROOT / p["working_dir"]).resolve()
        assert p["inp_sha256"] in (job.get("notes") or "")
        assert not job.get("started_at") and not job.get("ended_at")
    for job in q["jobs"]:
        if job not in executable:
            assert job.get("raw_status") in TERMINAL
            assert job["job_name"] not in candidate_names
    for p in batch["points"][expected_prefix:]:
        assert not any(j["job_name"] == p["job_name"] for j in q["jobs"])
        assert not any(j["job_name"] == p["job_name"] for j in h["jobs"])
    return {"queue": q, "history": h,
            "executable_count": len(executable),
            "executable_queue_ids": [j["queue_id"] for j in executable]}


def request(p, task_id):
    return JobRequest(
        inp_path=str(ROOT / p["inp_path"]), job_name=p["job_name"],
        working_dir=str(ROOT / p["working_dir"]), cpus=14, gpus=0,
        run_datacheck=True, run_full=True,
        submission_mode="enqueue_only", allow_solver_submit=False,
        batch="run033_authorized_twenty_doe", strategy="single_runner_serial_batch_manual_start",
        metadata={"run": "run_033", "point_id": p["point_id"],
                  "project_id": PID, "task_id": task_id,
                  "inp_sha256": p["inp_sha256"],
                  "maximum_attempts": 1, "automatic_retries": 0,
                  "notes": f"run033 20-Job DOE; point_id={p['point_id']}; project_id={PID}; inp_sha256={p['inp_sha256']}; task_id={task_id}; 14CPU 0GPU; one Datacheck then Full; zero retries; one user GUI Start Queue; AUTO_STOP_UNAVAILABLE"},
    )


def register():
    assert not (A / "queue_task_ids.json").exists(), "Queue tasks already registered"
    batch = load_batch()
    static_identity(batch)
    session = read(P / "main_session.json")
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=7200)
    assert hub.task(session["budget_task_id"])["execution_state"] == "COMPLETED"
    assert hub.task(session["review_task_id"])["execution_state"] == "COMPLETED"
    main = session["identity"]
    ids = {}
    for p in batch["points"]:
        scope = {"run": "run_033", "point_id": p["point_id"],
                 "job_name": p["job_name"], "project_id": PID,
                 "inp_path": str(ROOT / p["inp_path"]),
                 "inp_sha256": p["inp_sha256"],
                 "working_dir": str(ROOT / p["working_dir"]),
                 "sigma_y_mpa": p["sigma_y_mpa"], "n": p["n"],
                 "cpus": 14, "gpus": 0, "run_datacheck": True,
                 "run_full": True, "max_attempts": 1,
                 "automatic_retries": 0,
                 "solver_start": "USER_GUI_ONLY",
                 "batch_budget_task_id": session["budget_task_id"],
                 "prepared_batch_sha256": sha(A / "prepared_batch.json")}
        task = hub.create_task(main["agent_id"], "MAIN", "queue_only_twenty_doe_point",
                               scope, f"run033-queue-{p['point_id']}-v1",
                               depends=(session["review_task_id"],))["task_id"]
        hub.approve(task, main["agent_id"], "enqueue")
        hub.approve(task, main["agent_id"], "start_solver")
        ids[p["point_id"]] = task
    batch_task = hub.create_task(main["agent_id"], "MAIN", "confirm_twenty_queued_manual_start",
                                 {"run": "run_033", "prepared_batch_sha256": sha(A / "prepared_batch.json"),
                                  "order": batch["batch_order"], "solver_start": "USER_GUI_ONLY"},
                                 "run033-batch-queued-confirm-v1", depends=tuple(ids.values()))["task_id"]
    save_once(A / "queue_task_ids.json", {"point_tasks": ids,
                                           "batch_confirm_task_id": batch_task,
                                           "budget_task_id": session["budget_task_id"],
                                           "review_task_id": session["review_task_id"]})
    assert hub.verify_chain()
    print(json.dumps({"status": "TWENTY_QUEUE_TASKS_APPROVED",
                      "count": len(ids), "batch_confirm_task_id": batch_task}))


def enqueue():
    assert not (A / "queue_manifest.json").exists(), "Batch already queued"
    assert not (P / "batch_enqueue_failure.json").exists(), "Prior failure needs manual review"
    batch = load_batch()
    ids = read(A / "queue_task_ids.json")
    assert list(ids["point_tasks"]) == batch["batch_order"]
    static_identity(batch)
    api = AbqJobPilotClient()
    scoped = api.for_project(project_id=PID)
    settings = persisted_settings(api)
    runtime = runtime_clear()
    before = queue_prefix(scoped, batch, 0)
    admission = read(P / "main_preflight.json")
    assert admission["status"] == "PASS_ALL_TWENTY_PREVIEWS"
    assert admission["queue_unchanged"] and len(admission["previews"]) == 20
    assert admission["project_settings_status"] == "PERSISTED"
    save_once(A / "queue_admission.json", {"at": now(), "status": "PASS",
                                             "prepared_batch_sha256": sha(A / "prepared_batch.json"),
                                             "settings": settings, "runtime": runtime,
                                             "queue_before": before,
                                             "all_20_hashes_rechecked": True,
                                             "all_20_workdirs_empty": True,
                                             "other_executable_jobs": 0})
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=7200)
    main = read(P / "main_session.json")["identity"]
    queued = []
    for index, p in enumerate(batch["points"]):
        task_id = ids["point_tasks"][p["point_id"]]
        assert hub.task(task_id)["execution_state"] == "PENDING"
        hub.require_approval(task_id, "enqueue")
        hub.require_approval(task_id, "start_solver")
        lease = hub.claim(task_id, main, f"run033-{p['point_id']}-queue-claim-v1")
        save_once(P / f"lease_{index+1:02d}_{p['point_id']}.json", lease)
        with queue_transaction(RT):
            runtime_clear()
            queue_prefix(scoped, batch, index)
            assert sha(ROOT / p["inp_path"]) == p["inp_sha256"]
            assert not any((ROOT / p["working_dir"]).iterdir())
            req = request(p, task_id)
            req_path = RECEIPTS / f"{index+1:02d}_{p['point_id']}_request.json"
            save_once(req_path, req.to_dict())
            attempt_path = RUN / "checkpoints" / f"enqueue_attempt_{index+1:02d}_{p['point_id']}.json"
            save_once(attempt_path, {"at": now(), "attempt_number": 1,
                                     "point_id": p["point_id"],
                                     "request_sha256": sha(req_path),
                                     "retry_forbidden": True,
                                     "unknown_outcome_requires_readonly_reconciliation": True})
            response = scoped.enqueue(req, dry_run=False).to_dict()
            response_path = RECEIPTS / f"{index+1:02d}_{p['point_id']}_response.json"
            save_once(response_path, response)
            assert response["status"] == "ENQUEUED" and response["job_id"]
            assert response["queue_only"] is True and response["queue_file_mutated"] is True
            assert not response["solver_started"] and not response["runner_started"]
            assert not response["forbidden_mutations_detected"]
            after = queue_prefix(scoped, batch, index + 1)
            assert after["executable_queue_ids"][-1] == response["job_id"]
        assert not any((ROOT / p["working_dir"]).iterdir())
        runtime_clear()
        status = scoped.status(job_id=response["job_id"]).to_dict()
        outputs = scoped.locate_outputs(job_id=response["job_id"]).to_dict()
        assert status["status"] == "QUEUED" and not status["odb_exists"] and not status["lock_exists"]
        assert sha(ROOT / p["inp_path"]) == p["inp_sha256"]
        receipt = {"at": now(), "status": "QUEUED_AWAITING_MANUAL_BATCH_START",
                   "position": index + 1, "point_id": p["point_id"],
                   "job_name": p["job_name"], "queue_id": response["job_id"],
                   "task_id": task_id, "project_id": PID,
                   "inp_path": str(ROOT / p["inp_path"]),
                   "inp_sha256": p["inp_sha256"],
                   "working_dir": str(ROOT / p["working_dir"]),
                   "sigma_y_mpa": p["sigma_y_mpa"], "n": p["n"],
                   "cpus": 14, "gpus": 0, "run_datacheck": True,
                   "run_full": True, "automatic_retries": 0,
                   "solver_started": False, "datacheck_started": False,
                   "api_status": status, "api_outputs": outputs}
        receipt_path = RECEIPTS / f"{index+1:02d}_{p['point_id']}_receipt.json"
        save_once(receipt_path, receipt)
        for path in (req_path, response_path, receipt_path):
            hub.artifact(task_id, main["agent_id"], path,
                         {"run": "run_033", "point": p["point_id"],
                          "inp_sha256": p["inp_sha256"],
                          "scope": "queue-only; user GUI starts serial batch"}, version="run033-v1")
        hub.message(task_id, main["agent_id"], "MAIN", receipt,
                    f"run033-{p['point_id']}-queued-v1")
        hub.finish(lease, receipt, evidence_state="RECORDED", science_state="NOT_EVALUATED")
        queued.append(receipt)
        print(json.dumps({"queued": index + 1, "of": 20,
                          "point": p["point_id"], "queue_id": response["job_id"]}), flush=True)
    final = queue_prefix(scoped, batch, 20)
    assert len(final["executable_queue_ids"]) == 20
    assert len(set(final["executable_queue_ids"])) == 20
    runtime_clear()
    assert all(not any((ROOT / p["working_dir"]).iterdir()) for p in batch["points"])
    manifest = {"at": now(), "status": "TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START",
                "project_id": PID, "prepared_batch_sha256": sha(A / "prepared_batch.json"),
                "numeric_version": batch["numeric_version"],
                "loss_version": batch["loss_version"],
                "authorization_scope_sha256": batch["authorization_scope_sha256"],
                "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
                "automatic_retries": 0, "batch_count": 20,
                "ordered_points": queued,
                "queue_ids": final["executable_queue_ids"],
                "queue_order_exact": True, "other_executable_jobs": 0,
                "all_20_workdirs_empty": True,
                "solver_started": False, "datacheck_started": False,
                "start_queue": "USER_GUI_ONLY",
                "auto_stop_unavailable": True,
                "failure_may_not_pause_following_jobs": True,
                "I01_I02_excluded": True}
    save_once(A / "queue_manifest.json", manifest)
    batch_task = ids["batch_confirm_task_id"]
    lease = hub.claim(batch_task, main, "run033-batch-confirm-claim-v1")
    hub.artifact(batch_task, main["agent_id"], A / "queue_manifest.json",
                 {"run": "run_033", "scope": "all 20 queue-only final order"}, version="run033-v1")
    hub.message(batch_task, main["agent_id"], "MAIN", manifest,
                "run033-twenty-queued-v1")
    hub.finish(lease, manifest, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    print(json.dumps({"status": manifest["status"], "count": 20,
                      "queue_ids": manifest["queue_ids"]}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"register", "enqueue"}:
        raise SystemExit("usage: enqueue_batch.py register|enqueue")
    try:
        (register if sys.argv[1] == "register" else enqueue)()
    except Exception:
        if sys.argv[1] == "enqueue" and not (P / "batch_enqueue_failure.json").exists():
            queued = []
            for receipt in sorted(RECEIPTS.glob("*_receipt.json")) if RECEIPTS.exists() else []:
                value = read(receipt)
                queued.append({"point_id": value["point_id"], "job_name": value["job_name"],
                               "queue_id": value["queue_id"]})
            save_once(P / "batch_enqueue_failure.json",
                      {"at": now(), "status": "BLOCKED_PARTIAL_OR_UNCERTAIN",
                       "already_confirmed_queued": queued,
                       "traceback": traceback.format_exc(),
                       "no_automatic_retry_or_cleanup": True,
                       "manual_readonly_reconciliation_required": True})
        raise
