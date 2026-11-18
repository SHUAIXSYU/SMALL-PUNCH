"""One authorized, queue-only D09 retry with a fresh output identity."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_038"
ART = RUN / "artifacts"
PRIVATE = ART / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
SOURCE = ROOT / "run/run_033/artifacts/candidates/SPIO_R033_D09_L/SPIO_R033_D09_L.inp"
SOURCE_SHA = "5d754294edca19e8eef85661f5a99f18cfe189f484b86ddb5e3ee52acc354d4b"
NAME = "SPIO_R038_D09_RETRY2"
WORK = ART / "solver" / NAME
ORIGINAL_ID = "q_0bebaa417158409fba973efcbae921fd"
PRIOR_RETRY_ID = "q_ed246bd7469b4701a8570326dfb73eb3"
RECOVERY_ID = "17c1916bf0644eac8e36daf6c3c15ab1"
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]

from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import build_recovery_plan
from agenthub_sp_invopt.hub import Hub


def now() -> str:
    return datetime.now().astimezone().isoformat()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sys.version_info[:3] == (3, 11, 13)
    assert not (RUN / "run.json").exists(), "Existing run_038 must not be overwritten"
    assert SOURCE.is_file() and sha(SOURCE) == SOURCE_SHA
    prepared = load(ROOT / "run/run_033/artifacts/prepared_batch.json")
    point = next(item for item in prepared["points"] if item["point_id"] == "D09")
    assert point["inp_sha256"] == SOURCE_SHA
    assert point["sigma_y_mpa"] == 157.3882604690048
    assert point["n"] == 0.029673713406920432
    assert prepared["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert prepared["loss_version"] == "run017-exploratory-fd-v1"
    forbidden = re.findall(r"(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b.*$",
                           SOURCE.read_text(encoding="utf-8", errors="replace"))
    assert not forbidden, f"External input dependency: {forbidden}"
    assert WORK.is_dir() and not any(WORK.iterdir()), "New output directory must be empty"
    assert not (WORK / f"{NAME}.odb").exists()
    assert not (WORK / f"{NAME}.lck").exists()

    api = AbqJobPilotClient()
    assert api.capabilities()["application_version"] == "0.2.2"
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert load(PROJECT / "project.json")["project_id"] == PID
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    assert settings["persisted"] is True and not settings["defaulted_fields"]
    config = settings["settings"]
    assert Path(config["abaqus_cmd"]).is_file()
    assert config["abaqus_cmd"].lower().endswith("abq2024.bat")
    assert (config["default_cpus"], config["default_gpus"], config["use_gpu"]) == (14, 0, False)
    assert config["run_datacheck"] is True and config["run_full"] is True

    recovery = load(PROJECT / "runtime/recovery_audit" / f"{RECOVERY_ID}.json")
    assert recovery["outcome"] == "APPLIED" and recovery["approval_source"] == "local_gui_confirmation"
    assert recovery["affected_queue_ids"] == [PRIOR_RETRY_ID]
    live = load(PROJECT / "runtime/live_status.json")
    assert live["phase"] == "IDLE" and live["recovery_operation_id"] == RECOVERY_ID
    runtime = assess_runtime(PROJECT / "runtime", project_db=PROJECT / "project.db")
    plan = build_recovery_plan(PROJECT / "runtime", project_db=PROJECT / "project.db").to_dict()
    assert runtime["status"] == "CLEAN" and runtime["owner"]["state"] in {"ABSENT", "STALE"}
    assert plan["assessment"]["solver_process"]["state"] == "CLEAR"
    assert not runtime["running_queue_ids"]
    scoped = api.for_project(project_id=PID)
    before = scoped.list_jobs()
    assert before["status"] == "OK"
    active_states = {"QUEUED", "RUNNING", "DATACHECK_RUNNING", "DATACHECK_OK", "FULL_RUNNING"}
    assert not [item for item in before["jobs"] if item["raw_status"] in active_states]
    original = [item for item in before["jobs"] if item["queue_id"] == ORIGINAL_ID]
    assert len(original) == 1 and original[0]["raw_status"] == "UNKNOWN_INTERRUPTED"
    assert not [item for item in before["jobs"] if item["queue_id"] == PRIOR_RETRY_ID]
    assert not [item for item in before["jobs"] if
                item["job_name"].casefold() == NAME.casefold()
                or Path(item["work_dir"]).resolve() == WORK.resolve()]
    history = api.list_project_jobs(project_id=PID).to_dict()
    assert history["status"] == "OK"
    prior_history = [item for item in history["jobs"] if item["job_name"] == "SPIO_R035_D09_RETRY1"]
    assert len(prior_history) == 1 and prior_history[0]["latest_status"] == "UNKNOWN"

    request = JobRequest(inp_path=str(SOURCE.resolve()), job_name=NAME,
                         working_dir=str(WORK.resolve()), cpus=14, gpus=0,
                         run_datacheck=True, run_full=True,
                         batch="run038_user_authorized_d09_retry2",
                         strategy="one_new_attempt_after_gui_recovery",
                         submission_mode="enqueue_only", allow_solver_submit=False,
                         metadata={"notes": "User-authorized D09 retry after official GUI recovery and queue removal; prior attempts preserved"})
    preflight = scoped.preflight(request).to_dict()
    dry_run = scoped.enqueue(request, dry_run=True).to_dict()
    assert preflight["status"] == "PREVIEW_READY" and not preflight["errors"]
    assert dry_run["status"] == "DRY_RUN_READY" and dry_run["queue_file_mutated"] is False
    assert not dry_run["solver_started"] and not dry_run["runner_started"]
    assert Path(preflight["expected_odb_path"]).resolve() == (WORK / f"{NAME}.odb").resolve()

    git_state = {"branch": git("branch", "--show-current"),
                 "head": git("rev-parse", "HEAD"), "remote": git("remote", "-v"),
                 "working_tree": git("status", "--short")}
    start = now()
    save(RUN / "checkpoints/start.json", {"at": start, "git": git_state,
                                          "python_interpreter": sys.executable,
                                          "python_version": sys.version.split()[0]})
    authorization = {"run": "run_038", "authorization_source": "Current user request to requeue D09 after removing bad Queue item",
                     "scope": "one queue-only D09 attempt; user manually starts GUI Runner",
                     "project_id": PID, "source_inp": str(SOURCE.resolve()),
                     "source_inp_sha256": SOURCE_SHA, "job_name": NAME,
                     "working_dir": str(WORK.resolve()),
                     "parameters": {"sigma_y_mpa": point["sigma_y_mpa"], "n": point["n"],
                                    "E_pa": 210000000000, "nu": 0.3},
                     "numeric_contract": prepared["numeric_version"],
                     "loss_contract": prepared["loss_version"],
                     "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
                     "max_new_attempts": 1, "automatic_retries": 0,
                     "old_queue_ids": [ORIGINAL_ID, PRIOR_RETRY_ID],
                     "solver_start": "USER_GUI_ONLY"}
    save(ART / "authorization_scope.json", authorization)
    precheck = {"at": now(), "project": project, "settings": settings,
                "recovery_audit": recovery, "runtime_assessment": runtime,
                "recovery_plan_after_gui": {"can_apply": plan["can_apply"],
                                             "unresolved": plan["unresolved"]},
                "queue_before_count": len(before["jobs"]), "active_queue_before": [],
                "prior_retry_history": prior_history[0],
                "source_inp_sha256": sha(SOURCE), "external_references": forbidden,
                "work_dir_empty": True, "preflight": preflight, "dry_run": dry_run,
                "note": "A stale lock in original D09 workdir remains; new output identity does not reuse it"}
    save(PRIVATE / "precheck.json", precheck)

    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run038-d09-retry2")
    previous_task = load(ROOT / "run/run_037/checkpoints/completed.json")["task_id"]
    task = hub.create_task(main["agent_id"], "MAIN", "queue_only_d09_retry_after_recovery",
                           authorization, "run038-one-d09-retry-queue-v1", depends=(previous_task,))
    hub.approve(task["task_id"], main["agent_id"], "enqueue")
    hub.approve(task["task_id"], main["agent_id"], "start_solver")
    save(PRIVATE / "main_session.json", {"identity": main, "task_id": task["task_id"]})
    lease = hub.claim(task["task_id"], main, "run038-main-queue-claim-v1")
    save(PRIVATE / "main_lease.json", lease)
    hub.require_approval(task["task_id"], "enqueue")
    hub.artifact(task["task_id"], main["agent_id"], SOURCE,
                 {"run": "run_038", "purpose": "frozen source INP"}, version="run038-d09-retry-v1")
    for path in (ART / "authorization_scope.json", PRIVATE / "precheck.json"):
        hub.artifact(task["task_id"], main["agent_id"], path,
                     {"run": "run_038", "purpose": "authorization and precheck"},
                     version="run038-d09-retry-v1")

    # Recheck the control state immediately before the one public queue mutation.
    latest = scoped.list_jobs()
    latest_runtime = assess_runtime(PROJECT / "runtime", project_db=PROJECT / "project.db")
    assert latest["status"] == "OK" and latest_runtime["status"] == "CLEAN"
    assert not [item for item in latest["jobs"] if item["raw_status"] in active_states]
    assert sha(SOURCE) == SOURCE_SHA and not any(WORK.iterdir())
    result = scoped.enqueue(request, dry_run=False).to_dict()
    save(PRIVATE / "enqueue_api_result.json", result)
    if result["status"] != "ENQUEUED" or not result["job_id"]:
        hub.fail(lease, "ABQJOBPILOT_ENQUEUE_REJECTED", json.dumps(result["errors"], ensure_ascii=False))
        raise RuntimeError(f"Public API rejected enqueue: {result['status']} {result['errors']}")
    queue_id = result["job_id"]
    after = scoped.list_jobs()
    assert after["status"] == "OK"
    active_after = [item for item in after["jobs"] if item["raw_status"] in active_states]
    assert len(active_after) == 1 and active_after[0]["queue_id"] == queue_id
    item = active_after[0]
    assert item["raw_status"] == "QUEUED" and item["job_name"] == NAME
    assert Path(item["inp_path"]).resolve() == SOURCE.resolve()
    assert Path(item["work_dir"]).resolve() == WORK.resolve()
    assert (item["cpus"], item["gpus"], item["run_datacheck"], item["run_full"]) == (14, 0, True, True)
    assert Path(item["odb_path"]).resolve() == (WORK / f"{NAME}.odb").resolve()
    assert not any(WORK.iterdir())
    public_status = scoped.status(job_id=queue_id).to_dict()
    outputs = scoped.locate_outputs(job_id=queue_id).to_dict()
    assert public_status["status"] == "QUEUED" and not public_status["odb_exists"]
    assert not public_status["lock_exists"] and not outputs["odb_exists"]
    assert not result["solver_started"] and not result["runner_started"]
    receipt = {"at": now(), "status": "D09_RETRY2_QUEUED_AWAITING_MANUAL_START",
               "task_id": task["task_id"], "project_id": PID,
               "queue_id": queue_id, "job_name": NAME,
               "source_inp": str(SOURCE.resolve()), "source_inp_sha256": SOURCE_SHA,
               "working_dir": str(WORK.resolve()), "queue_active_count": 1,
               "queue_record": item, "public_status": public_status,
               "output_status": outputs, "cpus": 14, "gpus": 0,
               "run_datacheck": True, "run_full": True,
               "automatic_retries": 0, "solver_started_by_codex": False,
               "datacheck_started_by_codex": False, "preflight": preflight["status"],
               "dry_run": dry_run["status"], "gui_manual_start_required": True}
    save(ART / "queue_receipt.json", receipt)
    for path in (PRIVATE / "enqueue_api_result.json", ART / "queue_receipt.json"):
        hub.artifact(task["task_id"], main["agent_id"], path,
                     {"run": "run_038", "project_id": PID, "queue_id": queue_id},
                     version="run038-d09-retry-v1")
    hub.message(task["task_id"], main["agent_id"], "MAIN", receipt,
                "run038-d09-retry2-queued-v1")
    hub.finish(lease, receipt, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()

    report = ("# run_038 — D09 第二次独立重试入队\n\n"
        f"**WARNING / D09_RETRY2_QUEUED_AWAITING_MANUAL_START。** 用户通过 GUI 的官方恢复"
        f"将上次重试 `{PRIOR_RETRY_ID}` 标为 UNKNOWN_INTERRUPTED，并从 Queue 移除其记录；"
        "Project History 中该尝试仍保留 UNKNOWN。Live 已为 IDLE，无正在运行的 Solver，当前 Queue"
        "在提交前没有可执行任务。原始 D09 的旧锁文件保留于原输出目录。\n\n"
        f"唯一新 Job `{NAME}` / `{queue_id}` 使用原冻结 INP `{SOURCE}`，SHA-256 `{SOURCE_SHA}`；"
        f"独立空工作目录 `{WORK}`。数值与 Loss 契约不变，14 CPU、0 GPU、Datacheck+Full，"
        "零自动重试。公开 API Preflight=PREVIEW_READY，Dry-run=DRY_RUN_READY，"
        "queue-only 入队后仅此 Job 为 QUEUED；Codex 未启动 Datacheck 或 Solver。\n\n"
        f"请在 Project ID `{PID}` 对应的 GUI 中确认只显示该待执行 Job，再由您点击一次 Start Queue。"
        "求解成功、数值有效和实验拟合均尚未评估。旧 run_034、run_036/037 历史结论不改写。\n\n"
        f"AgentHub task `{task['task_id']}`；预检与授权见 `artifacts/private/precheck.json`、"
        "`artifacts/authorization_scope.json`，真实 Queue 收据见 `artifacts/queue_receipt.json`。\n")
    (RUN / "summary.md").write_text(report, encoding="utf-8")
    finish = now()
    run_json = {"schema_version": "1.0", "run_id": "run_038",
                "stage": "one authorized D09 queue-only retry after official GUI recovery",
                "objective": "Reuse frozen D09 INP with a new output identity and enqueue once",
                "status": "WARNING", "start_time": start, "end_time": finish,
                "git_branch": git_state["branch"], "git_head": git_state["head"],
                "git": git_state, "python_interpreter": sys.executable,
                "python_version": sys.version.split()[0],
                "inputs": [{"path": relative(SOURCE), "role": "frozen INP", "sha256": SOURCE_SHA},
                           {"path": "run/run_033/artifacts/prepared_batch.json", "role": "frozen DOE"},
                           {"path": "run/run_037/summary.md", "role": "prior blocked assessment"}],
                "outputs": [{"path": relative(path), "role": "run_038 evidence", "sha256": sha(path)}
                            for path in (ART / "authorization_scope.json", PRIVATE / "precheck.json",
                                         PRIVATE / "enqueue_api_result.json", ART / "queue_receipt.json",
                                         RUN / "summary.md")],
                "validation": [{"check": "frozen_input_hash", "status": "PASS", "evidence": SOURCE_SHA},
                               {"check": "official_gui_recovery", "status": "PASS",
                                "evidence": f"Audit {RECOVERY_ID} APPLIED; history UNKNOWN; live IDLE"},
                               {"check": "project_settings", "status": "PASS",
                                "evidence": "PERSISTED, Abaqus 2024, 14 CPU, 0 GPU, datacheck/full"},
                               {"check": "preflight_and_dry_run", "status": "PASS",
                                "evidence": "PREVIEW_READY / DRY_RUN_READY"},
                               {"check": "queue_only", "status": "PASS",
                                "evidence": f"Only {queue_id} QUEUED; no solver start"},
                               {"check": "numerical_or_scientific_result", "status": "NOT_EVALUATED",
                                "evidence": "User has not manually started this Job"}],
                "errors": []}
    save(RUN / "run.json", run_json)
    save(RUN / "checkpoints/completed.json",
         {"at": finish, "status": "WARNING", "task_id": task["task_id"],
          "queue_id": queue_id, "receipt_sha256": sha(ART / "queue_receipt.json")})
    index = ROOT / "run/README.md"
    index_text = index.read_text(encoding="utf-8")
    assert "## run_038 — D09 第二次独立重试" not in index_text
    index.write_text(index_text.rstrip() + "\n\n## run_038 — D09 第二次独立重试\n\n"
                     "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                     "| run_038 | 官方恢复后原冻结 D09 输入单项 queue-only 入队 | WARNING / AWAITING_MANUAL_START | "
                     "[summary](run_038/summary.md) |\n\n等待用户在 GUI 手动 Start Queue。\n", encoding="utf-8")
    status_path = ROOT / "status/PROJECT_STATUS.md"
    status_text = status_path.read_text(encoding="utf-8")
    assert status_text.startswith("# SMALL-PUNCH 项目状态\n\n")
    status_path.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n\n",
        "# SMALL-PUNCH 项目状态\n\n## 当前状态 — run_038（2026-10-25，Asia/Shanghai）\n\n"
        f"**WARNING / D09_RETRY2_QUEUED_AWAITING_MANUAL_START。** GUI 官方恢复审计 `{RECOVERY_ID}`"
        f" 已 APPLIED；旧重试历史 UNKNOWN、Queue 记录已由用户移除。新 Job `{NAME}` / `{queue_id}`"
        " 已经公开 API 单项入队，当前仅它可执行；原冻结 INP 哈希一致，独立工作目录，"
        "14 CPU/0 GPU、Datacheck+Full，零自动重试。Codex 未启动求解；等待用户 GUI 手动 Start Queue。"
        "旧 run_034、run_036/037 结论保留。详见[run_038报告](../run/run_038/summary.md)。\n\n", 1),
        encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "task_id": task["task_id"],
                      "queue_id": queue_id, "job_name": NAME,
                      "active_count": 1, "solver_started": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
