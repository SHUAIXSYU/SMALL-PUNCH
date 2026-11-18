"""Freeze one user-authorized D09 crash retry; no Solver or Queue write."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_035"
OUT = RUN / "artifacts"
PRIVATE = OUT / "private"
PILOT = Path(r"D:\Projects\abqjobpilot")
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
NAME = "SPIO_R035_D09_RETRY1"
OLD_NAME = "SPIO_R033_D09_L"
OLD_ID = "q_0bebaa417158409fba973efcbae921fd"
SOURCE_HASH = "5d754294edca19e8eef85661f5a99f18cfe189f484b86ddb5e3ee52acc354d4b"
sys.path.insert(0, str(PILOT))
sys.path.insert(0, str(ROOT))
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now().astimezone().isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main():
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sys.version_info[:2] == (3, 11)
    assert not (RUN / "run.json").exists()
    prepared_file = ROOT / "run/run_033/artifacts/prepared_batch.json"
    queue_file = ROOT / "run/run_033/artifacts/queue_manifest.json"
    prepared = load(prepared_file)
    prior_queue = load(queue_file)
    point = next(p for p in prepared["points"] if p["point_id"] == "D09")
    old = next(p for p in prior_queue["ordered_points"] if p["point_id"] == "D09")
    inp = ROOT / point["inp_path"]
    work = OUT / "solver" / NAME
    assert point["job_name"] == old["job_name"] == OLD_NAME
    assert old["queue_id"] == OLD_ID
    assert point["inp_sha256"] == old["inp_sha256"] == SOURCE_HASH
    assert point["sigma_y_mpa"] == 157.3882604690048 and point["n"] == 0.029673713406920432
    assert sha(inp) == SOURCE_HASH
    assert work.is_dir() and not any(work.iterdir())
    assert not (work / f"{NAME}.odb").exists() and not (work / f"{NAME}.lck").exists()
    source_text = inp.read_text(encoding="utf-8", errors="replace")
    forbidden = re.findall(r"(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b.*$", source_text)
    assert not forbidden, f"External/restart input dependency: {forbidden}"
    project_file = load(PROJECT / "project.json")
    assert project_file["project_id"] == PID
    api = AbqJobPilotClient()
    assert api.capabilities()["application_version"] == "0.2.2"
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert project["status"] == "OK" and Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert project["project"]["project_id"] == settings["project_id"] == PID
    assert settings["status"] == "PERSISTED" and settings["persisted"] is True and not settings["defaulted_fields"]
    actual = settings["settings"]
    assert Path(actual["abaqus_cmd"]).is_file() and actual["abaqus_cmd"].lower().endswith("abq2024.bat")
    assert (actual["default_cpus"], actual["default_gpus"], actual["use_gpu"]) == (14, 0, False)
    assert actual["run_datacheck"] is True and actual["run_full"] is True
    scoped = api.for_project(project_id=PID)
    queue = scoped.list_jobs()
    assert queue["status"] == "OK"
    active_statuses = {"QUEUED", "RUNNING", "DATACHECK_RUNNING", "DATACHECK_OK", "FULL_RUNNING"}
    active = [j for j in queue["jobs"] if j["raw_status"] in active_statuses]
    assert not active, f"Other executable queue entries: {active}"
    old_entries = [j for j in queue["jobs"] if j["queue_id"] == OLD_ID]
    assert len(old_entries) == 1 and old_entries[0]["raw_status"] == "UNKNOWN_INTERRUPTED"
    assert old_entries[0]["job_name"] == OLD_NAME
    assert Path(old_entries[0]["work_dir"]).resolve() != work.resolve()
    assert (Path(old_entries[0]["work_dir"]) / f"{OLD_NAME}.lck").is_file()
    assert not [j for j in queue["jobs"] if j["job_name"].casefold() == NAME.casefold() or Path(j["work_dir"]).resolve() == work.resolve()]
    owner = runner_ownership_state(PROJECT / "runtime")
    live = load(PROJECT / "runtime/live_status.json")
    assert owner["state"] == "ABSENT" and live["phase"] == "IDLE"
    request = JobRequest(inp_path=str(inp.resolve()), job_name=NAME, working_dir=str(work.resolve()),
                         cpus=14, gpus=0, run_datacheck=True, run_full=True,
                         batch="run035_user_authorized_d09_retry", strategy="one_retry_after_crash",
                         submission_mode="enqueue_only", allow_solver_submit=False,
                         metadata={"notes": "D09 user-authorized one retry after reported PC crash; old q_0bebaa417158409fba973efcbae921fd preserved"})
    preflight = scoped.preflight(request).to_dict()
    dry_run = scoped.enqueue(request, dry_run=True).to_dict()
    assert preflight["status"] == "PREVIEW_READY" and not preflight["errors"]
    assert dry_run["status"] == "DRY_RUN_READY" and dry_run["queue_file_mutated"] is False
    assert dry_run["solver_started"] is False and dry_run["runner_started"] is False
    assert Path(preflight["expected_odb_path"]).resolve() == (work / f"{NAME}.odb").resolve()
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save(RUN / "checkpoints/start.json", {"at": now(), "git": git_state, "python": sys.executable,
                                           "python_version": sys.version.split()[0]})
    scope = {"run": "run_035", "authorization_source": "Current user message: D09 PC crash, requeue D09, user will click GUI Start Queue",
             "authorization_kind": "ONE_NEW_RETRY_ATTEMPT_ONLY", "project_id": PID,
             "old_queue_id": OLD_ID, "old_status": "UNKNOWN_INTERRUPTED", "old_lock_preserved": True,
             "old_working_dir": old["working_dir"], "new_job_name": NAME,
             "new_working_dir": str(work.resolve()), "source_inp": str(inp.resolve()),
             "source_inp_sha256": SOURCE_HASH,
             "parameters": {"sigma_y_mpa": point["sigma_y_mpa"], "n": point["n"], "E_pa": 210000000000, "nu": 0.3},
             "numeric_contract": prepared["numeric_version"], "loss_contract": prepared["loss_version"],
             "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
             "max_new_attempts": 1, "automatic_retries": 0, "solver_start": "USER_GUI_ONLY",
             "no_new_inp_or_material_generation": True, "no_old_output_cleanup_or_overwrite": True}
    save(OUT / "authorization_scope.json", scope)
    audit = {"at": now(), "status": "PRECHECK_PASS", "project": project,
             "settings": settings, "capabilities": api.capabilities(),
             "queue_count": len(queue["jobs"]), "active_queue": [], "old_d09": old_entries[0],
             "runner_owner": owner, "live_phase": live["phase"],
             "source_inp_path": str(inp.resolve()), "source_inp_sha256": sha(inp),
             "external_input_references": forbidden, "new_working_dir": str(work.resolve()),
             "new_working_dir_empty": True, "preflight": preflight, "dry_run": dry_run,
             "solver_started": False, "datacheck_started": False}
    save(PRIVATE / "precheck.json", audit)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run035-d09-retry")
    task = hub.create_task(main["agent_id"], "MAIN", "queue_only_d09_user_authorized_crash_retry",
                           scope, "run035-d09-one-retry-queue-v1", depends=(old["task_id"],))
    task_id = task["task_id"]
    hub.approve(task_id, main["agent_id"], "enqueue")
    hub.approve(task_id, main["agent_id"], "start_solver")
    save(PRIVATE / "main_session.json", {"identity": main, "task_id": task_id})
    assert hub.verify_chain()
    save(RUN / "run.json", {"schema_version": "1.0", "run_id": "run_035",
                            "stage": "one authorized D09 crash retry queue-only",
                            "objective": "Reuse frozen D09 INP with new output identity; enqueue once; user manually starts GUI Runner",
                            "status": "RUNNING", "start_time": now(), "end_time": None,
                            "git": git_state, "python_interpreter": sys.executable,
                            "python_version": sys.version.split()[0],
                            "inputs": [{"path": inp.relative_to(ROOT).as_posix(), "sha256": SOURCE_HASH},
                                       {"path": prepared_file.relative_to(ROOT).as_posix(), "sha256": sha(prepared_file)},
                                       {"path": queue_file.relative_to(ROOT).as_posix(), "sha256": sha(queue_file)}],
                            "outputs": [], "validation": [], "errors": []})
    (RUN / "summary.md").write_text("# run_035 — D09 单次崩溃重试入队\n\nRUNNING，尚未入队。\n", encoding="utf-8")
    print(json.dumps({"status": "PRECHECK_PASS", "task_id": task_id, "new_job_name": NAME,
                      "input_sha256": SOURCE_HASH, "new_working_dir": str(work.resolve()),
                      "preflight": preflight["status"], "dry_run": dry_run["status"],
                      "old_queue_id": OLD_ID, "old_status": old_entries[0]["raw_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
