"""Read-only pre-batch I02 execution identity audit; no ODB scoring."""
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
RUN = ROOT / "run/run_033"
A = RUN / "artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime


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


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def save_once(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def process_conflicts():
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    items = raw if isinstance(raw, list) else [raw]
    return [x for x in items if re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", x.get("Name") or "", re.I)
            or ((x.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                and "spio_r030_i02_l" in (x.get("CommandLine") or "").lower())]


def main():
    assert not (RUN / "run.json").exists()
    batch_file = ROOT / "run/run_030/artifacts/prepared_batch.json"
    batch = read(batch_file)
    assert sha(batch_file) == read(ROOT / "run/run_030/checkpoints/completion.json")["prepared_batch_sha256"]
    point = batch["points"][1]
    enqueue = read(ROOT / "run/run_032/artifacts/i02_enqueue_result.json")
    assert point["point_id"] == enqueue["point_id"] == "I02"
    assert point["job_name"] == enqueue["job_name"] == "SPIO_R030_I02_L"
    assert point["inp_sha256"] == enqueue["inp_sha256"] == sha(ROOT / point["inp_path"])
    assert enqueue["queue_id"] == "q_a40ddbf45cec472cb3541e28e6184fad"
    assert enqueue["project_id"] == batch["project_id"] == PID
    assert enqueue["working_dir"] == str(ROOT / point["working_dir"])
    assert enqueue["cpus"] == 14 and enqueue["gpus"] == 0
    api = AbqJobPilotClient()
    scoped = api.for_project(project_id=PID)
    settings = api.get_project_settings(project_id=PID).to_dict()
    project = api.show_project(project_id=PID).to_dict()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(settings["project_path"]).resolve() == PROJECT.resolve()
    q = scoped.list_jobs()
    hist = api.list_project_jobs(project_id=PID).to_dict()
    assert q["status"] == hist["status"] == "OK"
    found = [j for j in q["jobs"] if j["queue_id"] == enqueue["queue_id"]]
    assert len(found) == 1
    job = found[0]
    assert job["job_name"] == point["job_name"]
    assert Path(job["inp_path"]).resolve() == (ROOT / point["inp_path"]).resolve()
    assert Path(job["work_dir"]).resolve() == (ROOT / point["working_dir"]).resolve()
    assert job["cpus"] == 14 and job["gpus"] == 0 and job["run_datacheck"] and job["run_full"]
    assert point["inp_sha256"] in (job.get("notes") or "")
    assert job["status"] == "COMPLETED" and job["raw_status"] == "COMPLETED_WITH_WARNINGS"
    assert job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
    assert job["started_at"] and job["ended_at"] and job["duration_sec"] == 209
    matches = [x for x in hist["jobs"] if x["job_name"] == point["job_name"]]
    assert len(matches) == 1 and matches[0]["run_count"] == 1
    detail = api.show_job(matches[0]["job_id"], project_id=PID).to_dict()
    status = scoped.status(job_id=job["queue_id"]).to_dict()
    outputs = scoped.locate_outputs(job_id=job["queue_id"]).to_dict()
    assert status["status"] == "COMPLETED" and outputs["odb_exists"]
    runtime = assess_runtime(RT, project_db=PROJECT / "project.db")
    assert runtime["status"] == "CLEAN" and runtime["owner"]["state"] == "ABSENT"
    assert runtime["live_phase"] == "IDLE" and not runtime["lock_files"]
    assert not runtime["errors"] and not runtime["running_queue_ids"]
    work = ROOT / point["working_dir"]
    files = {}
    for ext in ("odb", "sta", "msg", "dat", "log"):
        path = work / f"{point['job_name']}.{ext}"
        assert path.is_file() and path.stat().st_size > 0
        files[ext] = {"path": rel(path), "sha256": sha(path),
                      "size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
    assert not (work / f"{point['job_name']}.lck").exists()
    sta = (ROOT / files["sta"]["path"]).read_text(errors="replace")
    assert "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta
    log = (ROOT / files["log"]["path"]).read_text(errors="replace")
    phases = {}
    for phase in ("DATACHECK_RUNNING", "FULL_RUNNING"):
        starts = re.findall(r"\[([^]]+)\] START " + phase, log)
        ends = re.findall(r"\[([^]]+)\] END " + phase + r" return_code=(-?\d+)", log)
        assert len(starts) == len(ends) == 1 and int(ends[0][1]) == 0
        phases[phase] = {"start_local": starts[0], "end_local": ends[0][0],
                         "duration_sec": (datetime.fromisoformat(ends[0][0]) - datetime.fromisoformat(starts[0])).total_seconds(),
                         "timezone_note": "Raw Runner LOG timestamps lack timezone; preserved as local strings"}
    first = process_conflicts()
    time.sleep(1)
    second = process_conflicts()
    assert not first and not second
    for entry in files.values():
        path = ROOT / entry["path"]
        assert sha(path) == entry["sha256"] and path.stat().st_mtime_ns == entry["mtime_ns"]
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save_once(RUN / "checkpoints/start.json", {"at": now(), "git": git_state,
                                               "python": sys.executable,
                                               "python_version": sys.version.split()[0]})
    save_once(RUN / "run.json", {"schema_version": "1.0", "run_id": "run_033",
                                 "stage": "twenty-job batch DOE prepare and queue-only",
                                 "objective": "I02 audit; freeze 14 new DOE; true CAE generation; preview and enqueue exactly 20; user GUI starts Runner",
                                 "status": "RUNNING", "start_time": now(), "end_time": None,
                                 "git": git_state, "python_interpreter": sys.executable,
                                 "python_version": sys.version.split()[0],
                                 "inputs": [{"path": rel(batch_file), "sha256": sha(batch_file)},
                                            {"path": "run/run_032/artifacts/i02_enqueue_result.json",
                                             "sha256": sha(ROOT / "run/run_032/artifacts/i02_enqueue_result.json")}],
                                 "outputs": [], "validation": [], "errors": []})
    (RUN / "summary.md").write_text("# run_033 — 20 Job DOE batch\n\nRUNNING；未入队本批，不启动Solver。\n", encoding="utf-8")
    evidence = {"at": now(), "status": "I02_EXECUTION_IDENTITY_PASS_WITH_WARNINGS",
                "queue_id": job["queue_id"], "job_name": job["job_name"],
                "inp_sha256": point["inp_sha256"], "queue_record": job,
                "api_status": status, "api_outputs": outputs, "history_detail": detail,
                "settings": settings, "project": project, "files": files,
                "phases": phases, "duration_sec": job["duration_sec"],
                "runtime": runtime, "process_snapshots": [first, second],
                "sta_completed_successfully": True, "stable_hashes": True,
                "scientific_numerical_review": "DEFERRED_TO_BATCH_ODB",
                "no_automatic_retry": True,
                "no_executable_queue_before_batch": all(j.get("raw_status") in {
                    "COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL", "FAILED_NUMERICAL",
                    "FAILED_INPUT", "FAILED_LICENSE", "DATACHECK_FAILED",
                    "DATACHECK_FAILED_INVALID_GPU_OPTION", "SKIPPED", "CANCELLED"} for j in q["jobs"])}
    assert evidence["no_executable_queue_before_batch"]
    save_once(P / "i02_execution_audit.json", evidence)
    print(json.dumps({"status": evidence["status"], "queue_id": job["queue_id"],
                      "duration_sec": job["duration_sec"], "odb_sha256": files["odb"]["sha256"]}))


if __name__ == "__main__":
    main()
