"""Audit the 20-job GUI batch and dispatch only safe ODBs to real ODB chat."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_034"
A = RUN / "artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def save_once(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def processes():
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    procs = raw if isinstance(raw, list) else [raw]
    return [p for p in procs if re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", p.get("Name") or "", re.I)
            or ((p.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                and ("spio_r030_i0" in (p.get("CommandLine") or "").lower()
                     or "spio_r033_d" in (p.get("CommandLine") or "").lower()))]


def main():
    assert not (RUN / "run.json").exists()
    prepared_file = ROOT / "run/run_033/artifacts/prepared_batch.json"
    queue_file = ROOT / "run/run_033/artifacts/queue_manifest.json"
    prepared = read(prepared_file)
    submitted = read(queue_file)
    assert sha(prepared_file) == submitted["prepared_batch_sha256"]
    assert sha(queue_file) == read(ROOT / "run/run_033/checkpoints/completion.json")["queue_manifest_sha256"]
    assert len(prepared["points"]) == len(submitted["queue_ids"]) == 20
    assert prepared["project_id"] == submitted["project_id"] == PID
    api = AbqJobPilotClient()
    scoped = api.for_project(project_id=PID)
    settings = api.get_project_settings(project_id=PID).to_dict()
    project = api.show_project(project_id=PID).to_dict()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(settings["project_path"]).resolve() == PROJECT.resolve()
    q = scoped.list_jobs()
    history = api.list_project_jobs(project_id=PID).to_dict()
    assert q["status"] == history["status"] == "OK" and not q["errors"] and not history["errors"]
    queue_by_id = {j["queue_id"]: j for j in q["jobs"]}
    selected = [queue_by_id[qid] for qid in submitted["queue_ids"]]
    assert [j["job_name"] for j in selected] == [p["job_name"] for p in prepared["points"]]
    runtime = assess_runtime(RT, project_db=PROJECT / "project.db")
    assert runtime["status"] == "CLEAN" and runtime["owner"]["state"] == "ABSENT"
    assert runtime["live_phase"] == "IDLE" and not runtime["running_queue_ids"]
    assert not runtime["errors"] and not runtime["history_disagreements"]
    first_processes = processes()
    time.sleep(1)
    second_processes = processes()
    assert not first_processes and not second_processes, "Abaqus process status unclear"

    records = []
    for index, (point, job) in enumerate(zip(prepared["points"], selected), 1):
        work = ROOT / point["working_dir"]
        inp = ROOT / point["inp_path"]
        assert point["inp_sha256"] == sha(inp)
        assert job["job_name"] == point["job_name"]
        assert job["queue_id"] == submitted["queue_ids"][index-1]
        assert Path(job["inp_path"]).resolve() == inp.resolve()
        assert Path(job["work_dir"]).resolve() == work.resolve()
        assert job["cpus"] == 14 and job["gpus"] == 0
        assert job["run_datacheck"] and job["run_full"]
        assert point["inp_sha256"] in (job.get("notes") or "")
        hmatch = [h for h in history["jobs"] if h["job_name"] == point["job_name"]]
        assert len(hmatch) == 1 and hmatch[0]["run_count"] == 1
        detail = api.show_job(hmatch[0]["job_id"], project_id=PID).to_dict()
        status = scoped.status(job_id=job["queue_id"]).to_dict()
        outputs = scoped.locate_outputs(job_id=job["queue_id"]).to_dict()
        files = {}
        for ext in ("odb", "sta", "msg", "dat", "log"):
            path = work / f"{point['job_name']}.{ext}"
            if path.is_file():
                files[ext] = {"path": rel(path), "sha256": sha(path),
                              "size": path.stat().st_size,
                              "mtime_ns": path.stat().st_mtime_ns}
            else:
                files[ext] = None
        lock = work / f"{point['job_name']}.lck"
        safe = (job["status"] == "COMPLETED"
                and job["raw_status"] in ("COMPLETED_OK", "COMPLETED_WITH_WARNINGS")
                and job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
                and bool(job["started_at"]) and bool(job["ended_at"])
                and isinstance(job["duration_sec"], (int, float)) and job["duration_sec"] > 0
                and all(files.values()) and not lock.exists())
        phases = {}
        if files["log"]:
            log = (ROOT / files["log"]["path"]).read_text(errors="replace")
            for phase in ("DATACHECK_RUNNING", "FULL_RUNNING"):
                starts = re.findall(r"\[([^]]+)\] START " + phase, log)
                ends = re.findall(r"\[([^]]+)\] END " + phase + r" return_code=(-?\d+)", log)
                phases[phase] = {"starts": starts, "ends": ends}
            safe = safe and all(len(phases[phase]["starts"]) == len(phases[phase]["ends"]) == 1
                                and int(phases[phase]["ends"][0][1]) == 0
                                for phase in phases)
        if files["sta"]:
            sta = (ROOT / files["sta"]["path"]).read_text(errors="replace")
            safe = safe and "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta
        safe = safe and status["status"] == "COMPLETED" and bool(outputs["odb_exists"])
        if point["point_id"] == "D09":
            assert job["raw_status"] == "UNKNOWN_INTERRUPTED"
            assert lock.exists(), "D09 lock disappeared; re-evaluate safety before ODB read"
            assert not safe
        record = {"position": index, "point_id": point["point_id"],
                  "job_name": point["job_name"], "queue_id": job["queue_id"],
                  "project_id": PID, "inp_path": point["inp_path"],
                  "inp_sha256": point["inp_sha256"],
                  "working_dir": point["working_dir"],
                  "queue_record": job, "api_status": status, "api_outputs": outputs,
                  "history_detail": detail, "files": files,
                  "lock_exists": lock.exists(), "lock_path": rel(lock),
                  "phases": phases,
                  "safe_for_readonly_odb": bool(safe),
                  "numerical_and_scientific_status": "PENDING_ODB" if safe else "UNSCORED_INCOMPLETE_OR_UNSAFE"}
        records.append(record)
    safe_records = [r for r in records if r["safe_for_readonly_odb"]]
    excluded = [r for r in records if not r["safe_for_readonly_odb"]]
    assert len(safe_records) == 19 and len(excluded) == 1
    assert excluded[0]["point_id"] == "D09"
    for r in safe_records:
        for entry in r["files"].values():
            path = ROOT / entry["path"]
            assert sha(path) == entry["sha256"] and path.stat().st_mtime_ns == entry["mtime_ns"]
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save_once(RUN / "checkpoints/start.json", {"at": now(), "git": git_state,
                                               "python": sys.executable,
                                               "python_version": sys.version.split()[0]})
    save_once(RUN / "run.json", {"schema_version": "1.0", "run_id": "run_034",
                                 "stage": "twenty-job actual result audit and batch ODB analysis",
                                 "objective": "Audit all 20; read-only extract safe ODBs; frozen SPT Loss and DOE landscape",
                                 "status": "RUNNING", "start_time": now(), "end_time": None,
                                 "git": git_state, "python_interpreter": sys.executable,
                                 "python_version": sys.version.split()[0],
                                 "inputs": [{"path": rel(prepared_file), "sha256": sha(prepared_file)},
                                            {"path": rel(queue_file), "sha256": sha(queue_file)}],
                                 "outputs": [], "validation": [], "errors": []})
    (RUN / "summary.md").write_text("# run_034 — 20 Job DOE 实际结果分析\n\nRUNNING；D09 UNKNOWN_INTERRUPTED 暂不读取或评分。\n", encoding="utf-8")
    audit = {"at": now(), "status": "NINETEEN_SAFE_ONE_UNKNOWN_INTERRUPTED",
             "project_id": PID, "prepared_batch_sha256": sha(prepared_file),
             "queue_manifest_sha256": sha(queue_file),
             "settings": settings, "project": project,
             "runtime": runtime,
             "process_snapshots": [first_processes, second_processes],
             "records": records, "safe_count": 19, "excluded_count": 1,
             "excluded_reason": {"D09": "UNKNOWN_INTERRUPTED, DATACHECK_PASS only, live/leftover .lck; no safe ODB read or Loss; no cleanup/retry"},
             "no_solver_datacheck_enqueue_retry": True}
    save_once(P / "execution_audit.json", audit)
    public = {"at": now(), "status": audit["status"],
              "project_id": PID,
              "safe_for_odb_point_ids": [r["point_id"] for r in safe_records],
              "excluded": [{"point_id": r["point_id"], "queue_id": r["queue_id"],
                            "status": r["queue_record"]["raw_status"],
                            "lock_exists": r["lock_exists"]} for r in excluded],
              "batch_attempts_started": 20, "completed_software_success": 19,
              "numerical_qualification_pending": 19,
              "not_scored": 1,
              "no_solver_datacheck_enqueue_retry": True}
    save_once(A / "execution_summary.json", public)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run034-batch-results")
    scope = {"run": "run_034", "project_id": PID,
             "user_report": "GUI batch has finished, verify actual terminal evidence",
             "actual_execution_audit": rel(P / "execution_audit.json"),
             "actual_execution_audit_sha256": sha(P / "execution_audit.json"),
             "safe_odb_job_count": 19,
             "excluded_D09": {"queue_id": excluded[0]["queue_id"],
                              "status": "UNKNOWN_INTERRUPTED", "lck_exists": True,
                              "read_odb": False, "loss": None},
             "frozen_batch": rel(prepared_file), "frozen_batch_sha256": sha(prepared_file),
             "loss_binding": "run/run_030/artifacts/loss_contract_binding.json",
             "loss_version": "run017-exploratory-fd-v1",
             "allowed_operations": "Read-only Abaqus Python ODB extraction for 19 safe jobs; SPT-only offline score; no solver/datacheck/enqueue/retry",
             "requirements": [
                 "Real ODB Codex session claims and heartbeats this AgentHub task; do not use simulated worker",
                 "For each listed safe job recheck source input/ODB hash, lock/process/read-only safety, Punch RP identity, U2/RF2/Step Time and ODB completion",
                 "Generate raw RP CSV and positive F-D CSV; frozen 241-point Loss, RMSE, NRMSE; no per-job shift/smooth/extrapolate",
                 "Extract maximum saved-frame PEEQ, material table pmax, accepted/rejected attempts, cutbacks, accepted vs rejected warning classes, contact/energy diagnostics, runtime, file provenance",
                 "Record each Job's status separately. Mark invalid/incomplete with loss=null and reason; do not infer success from ODB existence",
                 "Do not open D09 ODB or clear its .lck; D09 is UNKNOWN_INTERRUPTED and excluded",
                 "Register per-job result artifacts and summary in AgentHub; send structured result to MAIN",
                 "No sealed tensile data, no solver/datacheck/retry/enqueue, no historical file modification or git commit/push"],
             "jobs": [{"point_id": r["point_id"], "job_name": r["job_name"],
                       "queue_id": r["queue_id"], "inp_absolute": str(ROOT / r["inp_path"]),
                       "inp_sha256": r["inp_sha256"],
                       "working_dir_absolute": str(ROOT / r["working_dir"]),
                       "odb_absolute": str(ROOT / r["files"]["odb"]["path"]),
                       "odb_sha256": r["files"]["odb"]["sha256"],
                       "source_file_hashes": {k: v["sha256"] for k, v in r["files"].items()},
                       "duration_sec": r["queue_record"]["duration_sec"]}
                      for r in safe_records]}
    save_once(A / "odb_task_payload.json", scope)
    odb_task = hub.create_task(main["agent_id"], "ODB", "batch_extract_score_nineteen_odb",
                               scope, "run034-odb-nineteen-safe-batch-v1")["task_id"]
    hub.message(odb_task, main["agent_id"], "ODB", scope,
                "run034-odb-dispatch-nineteen-v1")
    review = hub.create_task(main["agent_id"], "MAIN", "review_twenty_doe_landscape",
                             {"run": "run_034", "odb_task_id": odb_task,
                              "execution_audit_sha256": sha(P / "execution_audit.json"),
                              "loss_version": "run017-exploratory-fd-v1"},
                             "run034-main-doe-review-v1", depends=(odb_task,))["task_id"]
    save_once(P / "main_session.json", {"identity": main, "odb_task_id": odb_task,
                                          "review_task_id": review})
    save_once(A / "task_ids.json", {"odb_task_id": odb_task,
                                     "review_task_id": review})
    assert hub.verify_chain()
    print(json.dumps({"status": audit["status"], "safe_count": 19,
                      "excluded": "D09", "odb_task_id": odb_task,
                      "review_task_id": review}, ensure_ascii=False))


if __name__ == "__main__":
    main()
