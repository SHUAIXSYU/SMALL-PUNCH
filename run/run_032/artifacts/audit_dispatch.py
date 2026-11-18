"""Audit GUI-completed I01 and dispatch a real read-only ODB task."""
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "run/run_032"
A = R / "artifacts"
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


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def save(p, value):
    with Path(p).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def proc():
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    items = raw if isinstance(raw, list) else [raw]
    return [x for x in items if re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", x.get("Name") or "", re.I)
            or ((x.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                and "spio_r030_i01_g" in (x.get("CommandLine") or "").lower())]


def main():
    assert not (R / "run.json").exists() and not (P / "execution_audit.json").exists()
    enqueue = read(ROOT / "run/run_031/artifacts/enqueue_result.json")
    batch_path = ROOT / "run/run_030/artifacts/prepared_batch.json"
    batch = read(batch_path)
    cp = read(ROOT / "run/run_030/checkpoints/completion.json")
    assert sha(batch_path) == cp["prepared_batch_sha256"]
    point = batch["points"][0]
    assert point["point_id"] == "I01" and enqueue["point_id"] == "I01"
    assert enqueue["queue_id"] == "q_c8329bd4fab4455f924d211d62ba0625"
    assert enqueue["job_name"] == point["job_name"] == "SPIO_R030_I01_G"
    assert enqueue["inp_sha256"] == point["inp_sha256"] == sha(ROOT / point["inp_path"])
    assert enqueue["project_id"] == PID and enqueue["working_dir"] == str(ROOT / point["working_dir"])
    assert enqueue["cpus"] == 14 and enqueue["gpus"] == 0
    loss_binding = ROOT / "run/run_030/artifacts/loss_contract_binding.json"
    loss = read(loss_binding)
    assert sha(loss_binding) == batch["loss_contract_binding_sha256"]
    for path_key, hash_key in (("config_path", "config_sha256"), ("target_path", "target_sha256"),
                               ("implementation_path", "implementation_sha256")):
        assert sha(ROOT / loss[path_key]) == loss[hash_key]

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
    assert point["inp_sha256"] in job["notes"]
    assert job["status"] == "COMPLETED" and job["raw_status"] in ("COMPLETED_OK", "COMPLETED_WITH_WARNINGS")
    assert job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
    assert job["started_at"] and job["ended_at"] and job["duration_sec"] > 0
    assert not any(x["job_name"] in {p["job_name"] for p in batch["points"][1:]} for x in q["jobs"])
    hmatches = [x for x in hist["jobs"] if x["job_name"] == point["job_name"]]
    assert len(hmatches) == 1 and hmatches[0]["run_count"] == 1
    detail = api.show_job(hmatches[0]["job_id"], project_id=PID).to_dict()
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
                         "return_code": 0, "duration_sec": (datetime.fromisoformat(ends[0][0]) - datetime.fromisoformat(starts[0])).total_seconds(),
                         "time_note": "Raw Runner LOG timestamps lack timezone; preserved as local strings"}
    first = proc()
    time.sleep(1)
    second = proc()
    assert not first and not second
    for entry in files.values():
        path = ROOT / entry["path"]
        assert sha(path) == entry["sha256"] and path.stat().st_mtime_ns == entry["mtime_ns"]
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save(R / "run.json", {"schema_version": "1.0", "run_id": "run_032",
                           "stage": "I01 actual ODB and sequential gate review", "status": "RUNNING",
                           "objective": "Real ODB extraction, frozen Loss and numerical review; queue I02 only if gate passes",
                           "start_time": now(), "end_time": None, "git": git_state,
                           "python_interpreter": sys.executable, "python_version": sys.version.split()[0],
                           "inputs": [{"path": "run/run_031/artifacts/enqueue_result.json",
                                       "sha256": sha(ROOT / "run/run_031/artifacts/enqueue_result.json")},
                                      {"path": rel(batch_path), "sha256": sha(batch_path)}],
                           "outputs": [], "validation": [], "errors": []})
    (R / "summary.md").write_text("# run_032 — I01 真实结果审核\n\nRUNNING；未作数值准入结论。\n", encoding="utf-8")
    save(R / "checkpoints/start.json", {"at": now(), "git": git_state, "queue_id": job["queue_id"]})
    evidence = {"at": now(), "queue_id": job["queue_id"], "job_name": job["job_name"],
                "inp_sha256": point["inp_sha256"], "queue_record": job,
                "api_status": status, "api_outputs": outputs, "history_detail": detail,
                "settings": settings, "project": project,
                "files": files, "phases": phases, "duration_sec": job["duration_sec"],
                "runtime": runtime, "process_snapshots": [first, second],
                "sta_completed_successfully": True, "stable_hashes": True,
                "safe_for_readonly_odb": True, "I02_I08_not_queued": True,
                "scientific_qualification": "PENDING_REAL_ODB_AND_MAIN_REVIEW"}
    save(P / "execution_audit.json", evidence)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    session = hub.register("MAIN", "codex-main-run032-i01-result")
    tasks = read(ROOT / "run/run_031/artifacts/authorization.json")
    review_task = tasks["result_review_task_ids"]["I01"]
    assert hub.task(review_task)["execution_state"] == "PENDING"
    review_lease = hub.claim(review_task, session, "run032-main-I01-review-claim-v1")
    odb_payload = {"run": "run_032", "point_id": "I01", "main_review_task_id": review_task,
                   "queue_id": job["queue_id"], "job_name": job["job_name"],
                   "project_id": PID, "inp_absolute": str(ROOT / point["inp_path"]),
                   "inp_sha256": point["inp_sha256"], "working_dir_absolute": str(work),
                   "odb_absolute": str(ROOT / files["odb"]["path"]),
                   "odb_sha256": files["odb"]["sha256"],
                   "execution_audit": rel(P / "execution_audit.json"),
                   "output_dir": "run/run_032/artifacts/private/odb",
                   "loss_binding": rel(loss_binding), "loss_binding_sha256": sha(loss_binding),
                   "odb_protocol": "run/run_030/artifacts/odb_result_protocol.json",
                   "pilot_protocol": "run/run_030/artifacts/pilot_protocol.md",
                   "requirements": [
                       "Real ODB Codex session claims this Hub task with lease >=3600 and heartbeats; source ODB readOnly=True with Abaqus 2024 Python; hash before/after",
                       "Validate Punch RP identity, U2/RF2/Step Time raw CSV, F-D sign u=-U2 m and F=-RF2 N; no shift/smoothing/crop/extrapolation",
                       "Compute fixed run017-exploratory-fd-v1 Loss on 0-1.2mm 241 experiment points, F_ref=1428.9 N; RMSE/NRMSE; null score if incomplete",
                       "Record max saved-frame PEEQ vs table pmax=0.9, accepted/rejected increment counts, cutbacks, warnings by accepted/rejected, contact transitions and local F-D jumps",
                       "Record actual phase durations, ODB/STA/MSG/DAT/LOG/input hashes and provenance; separate software success, numerical evidence, scientific validity",
                       "Register artifacts and send structured task message to MAIN; do not enqueue, solve, datacheck, retry, alter source files or access sealed tensile data",
                   ]}
    odb_task = hub.create_task(session["agent_id"], "ODB", "extract_score_i01_result",
                               odb_payload, "run032-odb-I01-extract-score-v1")["task_id"]
    hub.message(odb_task, session["agent_id"], "ODB", odb_payload, "run032-odb-I01-dispatch-v1")
    hub.artifact(review_task, session["agent_id"], P / "execution_audit.json",
                 {"run": "run_032", "source": "AbqJobPilot public API and stable outputs"}, version="run032-v1")
    save(P / "main_session.json", {"identity": session, "review_task_id": review_task,
                                   "review_lease": review_lease, "odb_task_id": odb_task})
    save(A / "task_ids.json", {"review_task_id": review_task, "odb_task_id": odb_task,
                               "queue_id": job["queue_id"]})
    assert hub.verify_chain()
    print(json.dumps({"status": "AUDITED_AND_DISPATCHED", "queue_id": job["queue_id"],
                      "odb_task_id": odb_task, "review_task_id": review_task,
                      "duration_sec": job["duration_sec"], "odb_sha256": files["odb"]["sha256"]}))


if __name__ == "__main__":
    main()
