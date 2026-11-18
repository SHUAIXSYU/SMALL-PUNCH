"""Fresh public execution audit and formal AgentHub handoff to the real ODB chat."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_039"
ART = RUN / "artifacts"
PRIVATE = ART / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
RETRY_ID = "q_434c5f15c837413f8628b5b5188088aa"
PRIOR_IDS = {"q_0bebaa417158409fba973efcbae921fd",
             "q_ed246bd7469b4701a8570326dfb73eb3"}
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]

from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import probe_solver_processes
from agenthub_sp_invopt.hub import Hub


def now() -> str:
    return datetime.now().astimezone().isoformat()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def save(path: Path, data) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def phase_evidence(log_path: Path) -> dict:
    data = log_path.read_text(encoding="utf-8", errors="replace")
    result = {}
    for phase in ("DATACHECK_RUNNING", "FULL_RUNNING"):
        starts = re.findall(r"\[([^]]+)\] START " + phase, data)
        ends = re.findall(r"\[([^]]+)\] END " + phase + r" return_code=(-?\d+)", data)
        result[phase] = {"starts": starts, "ends": ends,
                         "single_zero_exit": len(starts) == len(ends) == 1 and ends[0][1] == "0"}
    return result


def main() -> None:
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sys.version_info[:3] == (3, 11, 13)
    assert not (RUN / "run.json").exists()
    prepared_file = ROOT / "run/run_033/artifacts/prepared_batch.json"
    queue_file = ROOT / "run/run_033/artifacts/queue_manifest.json"
    prepared = read(prepared_file)
    submitted = read(queue_file)
    old_audit = read(ROOT / "run/run_034/artifacts/private/execution_audit.json")
    old_by_point = {x["point_id"]: x for x in old_audit["records"]}
    assert len(prepared["points"]) == len(submitted["ordered_points"]) == len(old_by_point) == 20
    assert sha(prepared_file) == submitted["prepared_batch_sha256"]
    assert prepared["project_id"] == submitted["project_id"] == PID
    assert prepared["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert prepared["loss_version"] == "run017-exploratory-fd-v1"
    binding = read(ROOT / "run/run_030/artifacts/loss_contract_binding.json")
    for key, digest_key in (("loss_identity_path", "loss_identity_sha256"),
                            ("config_path", "config_sha256"),
                            ("target_path", "target_sha256"),
                            ("implementation_path", "implementation_sha256")):
        assert sha(ROOT / binding[key]) == binding[digest_key]
    api = AbqJobPilotClient()
    assert api.capabilities()["application_version"] == "0.2.2"
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    scoped = api.for_project(project_id=PID)
    queue = scoped.list_jobs()
    history = api.list_project_jobs(project_id=PID).to_dict()
    assert queue["status"] == history["status"] == "OK"
    queue_by_id = {j["queue_id"]: j for j in queue["jobs"]}
    runtime = assess_runtime(PROJECT / "runtime", project_db=PROJECT / "project.db")
    process = probe_solver_processes()
    assert runtime["status"] == "CLEAN" and runtime["live_phase"] == "IDLE"
    assert runtime["owner"]["state"] in {"ABSENT", "STALE"}
    assert not runtime["running_queue_ids"] and not runtime["errors"]
    assert process["state"] == "CLEAR"
    active = [j for j in queue["jobs"] if j["raw_status"] in
              {"QUEUED", "RUNNING", "DATACHECK_RUNNING", "DATACHECK_OK", "FULL_RUNNING"}]
    assert not active, f"Unexpected active queue: {active}"

    records = []
    for point, frozen in zip(prepared["points"], submitted["ordered_points"]):
        pid = point["point_id"]
        qid = frozen["queue_id"]
        job = queue_by_id[qid]
        inp = ROOT / point["inp_path"]
        work = ROOT / point["working_dir"]
        assert frozen["point_id"] == pid and frozen["job_name"] == point["job_name"]
        assert frozen["inp_sha256"] == point["inp_sha256"] == sha(inp)
        assert job["job_name"] == point["job_name"]
        assert Path(job["inp_path"]).resolve() == inp.resolve()
        assert Path(job["work_dir"]).resolve() == work.resolve()
        assert (job["cpus"], job["gpus"], job["run_datacheck"], job["run_full"]) == (14, 0, True, True)
        history_rows = [h for h in history["jobs"] if h["job_name"] == point["job_name"]]
        assert len(history_rows) == 1 and history_rows[0]["run_count"] == 1
        files = {}
        for ext in ("odb", "sta", "msg", "dat", "log"):
            file = work / f"{job['job_name']}.{ext}"
            if pid == "D09" and ext == "odb":
                # The original ODB is interrupted and remains ineligible even for hashing.
                files[ext] = {"path": rel(file), "sha256": None,
                              "bytes": file.stat().st_size if file.is_file() else None,
                              "read": False}
            else:
                files[ext] = ({"path": rel(file), "sha256": sha(file),
                               "bytes": file.stat().st_size} if file.is_file() else None)
        old = old_by_point[pid]
        if pid != "D09":
            assert job["raw_status"] in {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS"}
            assert job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
            assert all(files.values()) and not (work / f"{job['job_name']}.lck").exists()
            assert all(files[ext]["sha256"] == old["files"][ext]["sha256"] for ext in files)
            assert old["safe_for_readonly_odb"] is True
            execution = "SOFTWARE_COMPLETED_REUSED_RUN034_ODB"
        else:
            assert job["raw_status"] == "UNKNOWN_INTERRUPTED"
            assert (work / f"{job['job_name']}.lck").exists()
            execution = "ORIGINAL_INTERRUPTED_UNSCORED"
        records.append({"point_id": pid, "region": point["region"],
                        "sigma_y_mpa": point["sigma_y_mpa"], "n": point["n"],
                        "x": point["x"], "y": point["y"],
                        "original_job_name": job["job_name"], "original_queue_id": qid,
                        "original_status": job["raw_status"], "original_started_at": job["started_at"],
                        "original_ended_at": job["ended_at"], "original_duration_s": job["duration_sec"],
                        "frozen_inp_path": point["inp_path"], "frozen_inp_sha256": point["inp_sha256"],
                        "source_files": files, "execution_class": execution})

    # The completed replacement is a separate attempt for the same frozen D09 parameter point.
    retry = queue_by_id[RETRY_ID]
    d09 = next(p for p in prepared["points"] if p["point_id"] == "D09")
    assert retry["job_name"] == "SPIO_R038_D09_RETRY2"
    assert Path(retry["inp_path"]).resolve() == (ROOT / d09["inp_path"]).resolve()
    assert sha(ROOT / d09["inp_path"]) == d09["inp_sha256"]
    assert retry["raw_status"] in {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS"}
    assert retry["return_code"] == 0 and retry["final_verdict"] == "SUCCESS"
    assert retry["started_at"] and retry["ended_at"] and retry["duration_sec"] > 0
    assert (retry["cpus"], retry["gpus"], retry["run_datacheck"], retry["run_full"]) == (14, 0, True, True)
    retry_work = Path(retry["work_dir"])
    assert retry_work.resolve() == (ROOT / "run/run_038/artifacts/solver/SPIO_R038_D09_RETRY2").resolve()
    retry_files = {}
    for ext in ("odb", "sta", "msg", "dat", "log"):
        file = retry_work / f"{retry['job_name']}.{ext}"
        assert file.is_file() and file.stat().st_size > 0
        retry_files[ext] = {"path": rel(file), "sha256": sha(file), "bytes": file.stat().st_size}
    assert not (retry_work / f"{retry['job_name']}.lck").exists()
    retry_phases = phase_evidence(retry_work / f"{retry['job_name']}.log")
    assert all(item["single_zero_exit"] for item in retry_phases.values())
    assert "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in (retry_work / f"{retry['job_name']}.sta").read_text(errors="replace")
    assert scoped.status(job_id=RETRY_ID).to_dict()["status"] == "COMPLETED"
    assert scoped.locate_outputs(job_id=RETRY_ID).to_dict()["odb_exists"] is True
    prior_history = [h for h in history["jobs"] if h["job_name"] == "SPIO_R035_D09_RETRY1"]
    assert len(prior_history) == 1 and prior_history[0]["latest_status"] == "UNKNOWN"
    assert retry["queue_id"] not in PRIOR_IDS
    retry_evidence = {"point_id": "D09", "queue_id": RETRY_ID,
                      "job_name": retry["job_name"], "queue_record": retry,
                      "files": retry_files, "phases": retry_phases,
                      "inp_sha256": d09["inp_sha256"],
                      "original_queue_id": next(x for x in records if x["point_id"] == "D09")["original_queue_id"],
                      "previous_retry_history": prior_history[0],
                      "safe_for_readonly_odb": True,
                      "numerical_quality": "PENDING_ODB_REVIEW"}
    for pid, source_run, manifest_name in (("I01", "run_031", "I01"),
                                            ("I02", "run_032", "I02")):
        candidates = [j for j in queue["jobs"] if f"_{pid}_" in j["job_name"]]
        assert len(candidates) == 1
        job = candidates[0]
        assert job["raw_status"] in {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS"}
        assert job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
        assert job["started_at"] and job["ended_at"]
        assert (job["cpus"], job["gpus"], job["run_datacheck"], job["run_full"]) == (14, 0, True, True)
        assert not (Path(job["work_dir"]) / f"{job['job_name']}.lck").exists()

    started = now()
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save(RUN / "checkpoints/start.json", {"at": started, "git": git_state,
                                          "python_interpreter": sys.executable,
                                          "python_version": sys.version.split()[0]})
    audit = {"at": now(), "project_id": PID, "project": project,
             "settings_status": settings["status"], "runtime": runtime,
             "solver_process_probe": process, "frozen_batch_sha256": sha(prepared_file),
             "frozen_queue_manifest_sha256": sha(queue_file),
             "original_batch": records,
             "original_software_completed": 19, "original_interrupted": 1,
             "original_attempt_count": 20,
             "replacement_d09": retry_evidence,
             "replacement_software_completed": 1,
             "prior_retry_history_status": prior_history[0]["latest_status"],
             "unique_doe_points": 20, "total_d09_attempts": 3,
             "no_solver_datacheck_enqueue_retry_by_codex": True}
    save(PRIVATE / "execution_audit.json", audit)
    dispatch = {"run": "run_039", "project_id": PID,
                "user_request": "20-point DOE analysis with real ODB Agent; no new solve or queue",
                "frozen_batch": rel(prepared_file), "frozen_batch_sha256": sha(prepared_file),
                "execution_audit": rel(PRIVATE / "execution_audit.json"),
                "execution_audit_sha256": sha(PRIVATE / "execution_audit.json"),
                "existing_19_odb_manifest": "run/run_034/artifacts/private/odb/manifest.json",
                "existing_19_odb_manifest_sha256": sha(ROOT / "run/run_034/artifacts/private/odb/manifest.json"),
                "existing_19_main_review": "run/run_034/artifacts/private/main/review_table.csv",
                "existing_19_main_review_sha256": sha(ROOT / "run/run_034/artifacts/private/main/review_table.csv"),
                "loss_contract_binding": "run/run_030/artifacts/loss_contract_binding.json",
                "loss_contract_binding_sha256": sha(ROOT / "run/run_030/artifacts/loss_contract_binding.json"),
                "original_batch_completed": 19,
                "original_D09_status": "UNKNOWN_INTERRUPTED; do not open original ODB",
                "replacement_D09": {"queue_id": RETRY_ID, "job_name": retry["job_name"],
                                    "inp_path": str(ROOT / d09["inp_path"]),
                                    "inp_sha256": d09["inp_sha256"],
                                    "odb_path": str(retry_work / f"{retry['job_name']}.odb"),
                                    "odb_sha256": retry_files["odb"]["sha256"],
                                    "work_dir": str(retry_work),
                                    "duration_sec": retry["duration_sec"]},
                "requirements": [
                    "Real ODB Codex chat must claim task with its own ODB AgentHub session",
                    "Reverify the existing 19 read-only ODB extraction artifacts and source hashes; reuse if unchanged, never overwrite run_034",
                    "Read only the completed run_038 D09 replacement ODB using Abaqus 2024 Python; original run_033 D09 remains interrupted and must not be opened",
                    "Extract Punch RP U2/RF2/Step Time, F-D CSV, saved-frame PEEQ, contact and energy diagnostics, accepted/rejected warnings, cutback and cost",
                    "Use frozen 241-point run017-exploratory-fd-v1 Loss, no shift/smooth/extrapolation; invalid results get loss=null",
                    "Register new D09 evidence and batch handoff via AgentHub; preserve full provenance and warning classifications",
                    "Never read sealed tensile data, run Solver/Datacheck, enqueue/retry, modify existing ODB/INP, or commit/push"]}
    save(ART / "odb_task_payload.json", dispatch)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run039-doe-audit")
    odb_task = hub.create_task(main["agent_id"], "ODB", "revalidate_twenty_doe_and_extract_d09_replacement",
                               dispatch, "run039-odb-twenty-point-handoff-v1")
    main_task = hub.create_task(main["agent_id"], "MAIN", "review_twenty_two_point_doe_and_bo_de_readiness",
                                {"run": "run_039", "odb_task_id": odb_task["task_id"],
                                 "execution_audit": rel(PRIVATE / "execution_audit.json"),
                                 "loss_version": prepared["loss_version"]},
                                "run039-main-doe-review-v1", depends=(odb_task["task_id"],))
    hub.message(odb_task["task_id"], main["agent_id"], "ODB", dispatch,
                "run039-odb-handoff-message-v1")
    for path in (PRIVATE / "execution_audit.json", ART / "odb_task_payload.json"):
        hub.artifact(odb_task["task_id"], main["agent_id"], path,
                     {"run": "run_039", "purpose": "frozen audit and ODB task handoff"},
                     version="run039-execution-audit-v1")
    assert hub.verify_chain()
    save(ART / "task_ids.json", {"odb_task_id": odb_task["task_id"],
                                 "main_task_id": main_task["task_id"],
                                 "main_identity": main})
    save(RUN / "run.json", {"schema_version": "1.0", "run_id": "run_039",
                            "stage": "DOE result audit and optimization readiness",
                            "objective": "Audit original 20 attempts and replacement D09; produce 22-point exploratory dataset",
                            "status": "RUNNING", "start_time": started, "end_time": None,
                            "git_branch": git_state["branch"], "git_head": git_state["head"],
                            "git": git_state, "python_interpreter": sys.executable,
                            "inputs": [{"path": rel(prepared_file), "role": "frozen DOE", "sha256": sha(prepared_file)},
                                       {"path": rel(queue_file), "role": "original queue manifest", "sha256": sha(queue_file)},
                                       {"path": "run/run_034/artifacts/private/odb/manifest.json", "role": "prior real ODB output"}],
                            "outputs": [{"path": rel(PRIVATE / "execution_audit.json"), "role": "fresh public execution audit"},
                                        {"path": rel(ART / "odb_task_payload.json"), "role": "ODB handoff"}],
                            "validation": [{"check": "public_execution_audit", "status": "PASS",
                                            "evidence": "19 original completed, original D09 interrupted, distinct replacement completed"},
                                           {"check": "ODB_and_MAIN_review", "status": "PENDING",
                                            "evidence": "Formal AgentHub tasks created"}],
                            "errors": []})
    (RUN / "summary.md").write_text("# run_039 — DOE 结果与优化准入\n\nRUNNING：执行审计完成，等待真实 ODB Agent 交接与 MAIN 复核。\n", encoding="utf-8")
    print(json.dumps({"status": "ODB_TASK_CREATED", "odb_task_id": odb_task["task_id"],
                      "main_task_id": main_task["task_id"],
                      "original_completed": 19, "original_interrupted": 1,
                      "d09_replacement_completed": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
