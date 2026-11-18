"""Submit exactly one D09 retry through AbqJobPilot's queue-only public API."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_035"
OUT = RUN / "artifacts"
PRIVATE = OUT / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.path.insert(0, r"D:\Projects\abqjobpilot")
sys.path.insert(0, str(ROOT))
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state
from agenthub_sp_invopt.hub import Hub


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def now():
    return datetime.now().astimezone().isoformat()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    scope = load(OUT / "authorization_scope.json")
    session = load(PRIVATE / "main_session.json")
    task_id = session["task_id"]
    source = Path(scope["source_inp"])
    work = Path(scope["new_working_dir"])
    name = scope["new_job_name"]
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sha(source) == scope["source_inp_sha256"]
    assert work.is_dir() and not any(work.iterdir())
    api = AbqJobPilotClient()
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert project["status"] == "OK" and Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    s = settings["settings"]
    assert Path(s["abaqus_cmd"]).is_file() and (s["default_cpus"], s["default_gpus"], s["use_gpu"]) == (14, 0, False)
    assert s["run_datacheck"] and s["run_full"]
    owner = runner_ownership_state(PROJECT / "runtime")
    live = load(PROJECT / "runtime/live_status.json")
    assert owner["state"] == "ABSENT" and live["phase"] == "IDLE"
    scoped = api.for_project(project_id=PID)
    before = scoped.list_jobs()
    assert before["status"] == "OK"
    active_statuses = {"QUEUED", "RUNNING", "DATACHECK_RUNNING", "DATACHECK_OK", "FULL_RUNNING"}
    active = [j for j in before["jobs"] if j["raw_status"] in active_statuses]
    existing = [j for j in before["jobs"] if j["job_name"].casefold() == name.casefold() or Path(j["work_dir"]).resolve() == work.resolve()]
    assert not existing, "Retry identity already exists: stop rather than submit again"
    assert not active, "Another executable Job exists; stop"
    old = [j for j in before["jobs"] if j["queue_id"] == scope["old_queue_id"]]
    assert len(old) == 1 and old[0]["raw_status"] == "UNKNOWN_INTERRUPTED"
    assert (Path(old[0]["work_dir"]) / f"{old[0]['job_name']}.lck").is_file()
    request = JobRequest(inp_path=str(source.resolve()), job_name=name, working_dir=str(work.resolve()),
                         cpus=14, gpus=0, run_datacheck=True, run_full=True,
                         batch="run035_user_authorized_d09_retry", strategy="one_retry_after_crash",
                         submission_mode="enqueue_only", allow_solver_submit=False,
                         metadata={"notes": "One user-authorized D09 crash retry; preserve old UNKNOWN_INTERRUPTED job"})
    preflight = scoped.preflight(request).to_dict()
    dry_run = scoped.enqueue(request, dry_run=True).to_dict()
    assert preflight["status"] == "PREVIEW_READY" and not preflight["errors"]
    assert dry_run["status"] == "DRY_RUN_READY" and not dry_run["queue_file_mutated"]
    assert Path(preflight["expected_odb_path"]).resolve() == (work / f"{name}.odb").resolve()
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    assert hub.task(task_id)["execution_state"] == "PENDING"
    hub.require_approval(task_id, "enqueue")
    hub.require_approval(task_id, "start_solver")  # User's GUI action only; API never starts it.
    lease = hub.claim(task_id, session["identity"], "run035-d09-first-retry-queue-claim-v1")
    save(PRIVATE / "main_lease.json", lease)
    for path in (OUT / "authorization_scope.json", PRIVATE / "precheck.json", source):
        hub.artifact(task_id, session["identity"]["agent_id"], path,
                     {"run": "run_035", "purpose": "user-authorized one retry, frozen D09 input"},
                     version="run035-d09-retry-v1")
    result = scoped.enqueue(request, dry_run=False).to_dict()
    save(PRIVATE / "enqueue_api_result.json", result)
    if result["status"] != "ENQUEUED" or not result["job_id"]:
        hub.fail(lease, "ABQJOBPILOT_ENQUEUE_REJECTED", json.dumps(result["errors"], ensure_ascii=False))
        raise RuntimeError(f"Public API rejected enqueue: {result['status']}: {result['errors']}")
    queue_id = result["job_id"]
    after = scoped.list_jobs()
    assert after["status"] == "OK"
    active_after = [j for j in after["jobs"] if j["raw_status"] in active_statuses]
    assert len(active_after) == 1 and active_after[0]["queue_id"] == queue_id
    record = active_after[0]
    assert record["raw_status"] == "QUEUED" and record["job_name"] == name
    assert Path(record["inp_path"]).resolve() == source.resolve()
    assert Path(record["work_dir"]).resolve() == work.resolve()
    assert (record["cpus"], record["gpus"], record["run_datacheck"], record["run_full"]) == (14, 0, True, True)
    assert Path(record["odb_path"]).resolve() == (work / f"{name}.odb").resolve()
    assert not any(work.iterdir())
    status = scoped.status(job_id=queue_id).to_dict()
    outputs = scoped.locate_outputs(job_id=queue_id).to_dict()
    assert status["status"] == "QUEUED" and not status["odb_exists"] and not status["lock_exists"]
    assert outputs["expected_odb_path"] == record["odb_path"] and not outputs["odb_exists"]
    assert not result["solver_started"] and not result["runner_started"]
    assert [j for j in after["jobs"] if j["queue_id"] == scope["old_queue_id"]][0]["raw_status"] == "UNKNOWN_INTERRUPTED"
    assert (Path(old[0]["work_dir"]) / f"{old[0]['job_name']}.lck").is_file()
    receipt = {"at": now(), "status": "D09_RETRY_QUEUED_AWAITING_MANUAL_START",
               "project_id": PID, "task_id": task_id, "old_queue_id": scope["old_queue_id"],
               "old_status": "UNKNOWN_INTERRUPTED", "old_lck_preserved": True,
               "new_queue_id": queue_id, "new_job_name": name,
               "inp_path": str(source.resolve()), "inp_sha256": sha(source),
               "working_dir": str(work.resolve()), "expected_odb": record["odb_path"],
               "parameters": scope["parameters"], "numeric_contract": scope["numeric_contract"],
               "cpus": 14, "gpus": 0, "run_datacheck": True, "run_full": True,
               "queue_active_count": 1, "queue_record": record,
               "api_status": status, "api_outputs": outputs,
               "api_queue_only": result["queue_only"], "solver_started": False,
               "datacheck_started": False, "runner_started": False,
               "automatic_retries": 0, "user_gui_start_required": True,
               "preflight": preflight["status"], "dry_run": dry_run["status"]}
    save(OUT / "queue_receipt.json", receipt)
    for path in (PRIVATE / "enqueue_api_result.json", OUT / "queue_receipt.json"):
        hub.artifact(task_id, session["identity"]["agent_id"], path,
                     {"run": "run_035", "project_id": PID, "queue_id": queue_id},
                     version="run035-d09-retry-v1")
    hub.message(task_id, session["identity"]["agent_id"], "MAIN", receipt,
                "run035-d09-retry-queued-receipt-v1")
    hub.finish(lease, receipt, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    summary = f"""# run_035 — D09 崩溃后的唯一新尝试入队

**WARNING / D09_RETRY_QUEUED_AWAITING_MANUAL_START。** 用户报告电脑死机导致 D09 未完成，并明确批准新增一次同参数重试、由本人在 GUI 点击 Start Queue。原 Job `{old[0]['job_name']}` / `{scope['old_queue_id']}` 仍为 UNKNOWN_INTERRUPTED，原 `.lck`、ODB 和其他产物均未改动。

新 Job `{name}` / `{queue_id}` 已通过 AbqJobPilot 0.2.2 公开 API 单项 queue-only 入队；当前唯一可执行 Queue 记录就是它。直接复用冻结 INP，SHA-256 `{scope['source_inp_sha256']}`；无新 INP 或本构修改。独立工作目录 `{work}`，14 CPU、0 GPU、Datacheck=True、Full=True、零自动重试。Preflight=`{preflight['status']}`，Dry-run=`{dry_run['status']}`。入队后工作目录为空，Solver/Datacheck 未启动。

请在正确的 AbqJobPilot Project（ID `{PID}`，根目录 `{PROJECT}`）中确认 Queue 只显示这个可执行 Job，再由您点击一次 **Start Queue**。当前桌面可见 `D:\\Projects\\abqjobpilot_dev\\run_gui.py` 进程；仅凭进程名不能确认 GUI 已打开本 Project，因此务必核对 Project ID。Codex 未代为启动 GUI Runner。

正式授权和检查证据：`artifacts/authorization_scope.json`、`artifacts/private/precheck.json`、`artifacts/queue_receipt.json`。AgentHub task `{task_id}` 已登记。旧 run_034 中 D09 Loss=null 与历史状态保留，不能将本次入队视为求解完成。
"""
    (RUN / "summary.md").write_text(summary, encoding="utf-8")
    run = load(RUN / "run.json")
    run["status"] = "WARNING"
    run["end_time"] = now()
    run["outputs"] = [{"path": rel(p), "sha256": sha(p)} for p in
                      (OUT / "authorization_scope.json", PRIVATE / "precheck.json",
                       PRIVATE / "enqueue_api_result.json", OUT / "queue_receipt.json",
                       RUN / "summary.md")]
    run["validation"] = [
        {"check": "frozen_input_sha256", "status": "PASS", "scope": "D09 original INP unchanged"},
        {"check": "project_settings", "status": "PASS", "scope": "Project ID/PERSISTED/Abaqus 2024/14 CPU/0 GPU/two stages"},
        {"check": "queue_and_runner_precheck", "status": "PASS", "scope": "No executable jobs; owner ABSENT/live IDLE; old D09 lock preserved"},
        {"check": "preflight_and_dry_run", "status": "PASS", "scope": "Public API only, no queue mutation in dry-run"},
        {"check": "one_queue_only_submission", "status": "PASS", "scope": f"Only {name}, queue_id {queue_id}, no Solver start"},
        {"check": "historical_D09_recovery", "status": "WARNING", "scope": "Old attempt remains UNKNOWN_INTERRUPTED; new separate retry authorized"},
        {"check": "AgentHub_audit", "status": "PASS", "scope": "Task completed and chain verified"}]
    run["errors"] = []
    (RUN / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save(RUN / "checkpoints/completed.json", {"at": run["end_time"], "status": run["status"],
                                                    "task_id": task_id, "queue_id": queue_id,
                                                    "queue_receipt_sha256": sha(OUT / "queue_receipt.json")})
    index = ROOT / "run/README.md"
    index_text = index.read_text(encoding="utf-8")
    if "## run_035 — D09 崩溃重试 Queue-only" not in index_text:
        index.write_text(index_text.rstrip() + "\n\n## run_035 — D09 崩溃重试 Queue-only\n\n"
                         "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                         "| run_035 | 复用冻结 D09 输入，建立独立重试身份并仅入队一次 | WARNING / AWAITING_MANUAL_START | [summary](run_035/summary.md) |\n\n"
                         "旧 D09 UNKNOWN_INTERRUPTED 及锁文件保留；新 Job 等待用户手动 Start Queue。\n", encoding="utf-8")
    project_status = ROOT / "status/PROJECT_STATUS.md"
    status_text = project_status.read_text(encoding="utf-8")
    if "## 当前状态 — run_035" not in status_text:
        block = f"""## 当前状态 — run_035（2026-10-25，Asia/Shanghai）

**WARNING / D09_RETRY_QUEUED_AWAITING_MANUAL_START。** 用户报告崩溃并另行授权 D09 一次新尝试。原 queue_id `{scope['old_queue_id']}` 为 UNKNOWN_INTERRUPTED，旧 `.lck` 与产物保留；新 Job `{name}` / `{queue_id}` 使用原冻结 INP 和独立工作目录，14CPU/0GPU、Datacheck+Full。AbqJobPilot 公开 Preflight/Dry-run 通过，当前仅此新 Job 为 QUEUED；Solver/Datacheck 未启动。请用户核对正确 Project 后 GUI 手动 Start Queue。见[run_035报告](../run/run_035/summary.md)。run_034 历史结论及封存资料禁读规则不变。

"""
        assert status_text.startswith("# SMALL-PUNCH 项目状态\n\n")
        project_status.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n\n", "# SMALL-PUNCH 项目状态\n\n" + block, 1), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "queue_id": queue_id,
                      "job_name": name, "inp_sha256": receipt["inp_sha256"],
                      "active_count": 1, "solver_started": False,
                      "working_dir": receipt["working_dir"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
