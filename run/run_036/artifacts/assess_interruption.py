"""Read-only assessment after the user's second D09 GUI interruption."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_036"
PRIVATE = RUN / "artifacts/private"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RETRY_ID = "q_ed246bd7469b4701a8570326dfb73eb3"
OLD_ID = "q_0bebaa417158409fba973efcbae921fd"
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from agenthub_sp_invopt.hub import Hub
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_workflow import build_recovery_plan


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def now():
    return datetime.now().astimezone().isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sys.version_info[:2] == (3, 11)
    assert not (RUN / "run.json").exists()
    prior = load(ROOT / "run/run_035/artifacts/queue_receipt.json")
    assert prior["new_queue_id"] == RETRY_ID and prior["old_queue_id"] == OLD_ID
    inp = Path(prior["inp_path"])
    assert sha(inp) == prior["inp_sha256"]
    api = AbqJobPilotClient()
    assert api.capabilities()["application_version"] == "0.2.2"
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    scoped = api.for_project(project_id=PID)
    queue = scoped.list_jobs()
    assert queue["status"] == "OK"
    old = [j for j in queue["jobs"] if j["queue_id"] == OLD_ID]
    retry = [j for j in queue["jobs"] if j["queue_id"] == RETRY_ID]
    assert len(old) == len(retry) == 1
    assert old[0]["raw_status"] == "UNKNOWN_INTERRUPTED"
    assert retry[0]["job_name"] == prior["new_job_name"] and Path(retry[0]["inp_path"]).resolve() == inp.resolve()
    status = scoped.status(job_id=RETRY_ID).to_dict()
    outputs = scoped.locate_outputs(job_id=RETRY_ID).to_dict()
    plan = build_recovery_plan(PROJECT / "runtime", project_db=PROJECT / "project.db").to_dict()
    assert retry[0]["raw_status"] == "DATACHECK_RUNNING"
    assert plan["can_apply"] is False and plan["assessment"]["status"] in {"STALE_RUNNING", "RECOVERY_REQUIRED", "UNCONFIRMED"}
    evidence = {"at": now(), "user_report": "Clicked the wrong GUI control; requests another restart",
                "project_id": PID, "project": project,
                "settings_status": settings["status"], "stable_api_version": api.capabilities()["application_version"],
                "gui_instance_observed_source": r"D:\Projects\abqjobpilot_dev\run_gui.py",
                "gui_source_version": "0.3.0.dev0 (source inspection; process has since exited)",
                "source_inp_sha256": sha(inp), "old_queue_record": old[0],
                "retry_queue_record": retry[0], "retry_public_status": status,
                "retry_outputs": outputs, "recovery_plan": plan,
                "no_solver_datacheck_enqueue_retry_by_codex": True,
                "no_queue_json_project_db_or_lock_mutation": True}
    save(PRIVATE / "read_only_recovery_assessment.json", evidence)
    live = load(PROJECT / "runtime/live_status.json")
    summary = {"at": evidence["at"], "status": "BLOCKED_RECOVERY_REQUIRED",
               "retry_queue_id": RETRY_ID, "retry_job_name": retry[0]["job_name"],
               "queue_raw_status": retry[0]["raw_status"], "live_phase": live["phase"],
               "started_at": retry[0].get("started_at"), "ended_at": retry[0].get("ended_at"),
               "public_status": status["status"], "owner_state": plan["assessment"]["owner"]["state"],
               "solver_probe": plan["assessment"]["solver_process"]["state"],
               "recovery_can_apply": plan["can_apply"],
               "recovery_unresolved": plan["unresolved"],
               "old_d09_status": old[0]["raw_status"],
               "new_queue_record_created": False, "solver_started_by_codex": False}
    save(RUN / "artifacts/status_summary.json", summary)
    git_state = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"), "working_tree": git("status", "--short")}
    save(RUN / "checkpoints/start.json", {"at": now(), "git": git_state,
                                           "python": sys.executable, "python_version": sys.version.split()[0]})
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    main = hub.register("MAIN", "codex-main-run036-d09-recovery-audit")
    scope = {"run": "run_036", "source_queue_id": RETRY_ID,
             "user_request": "Restart D09 after wrong GUI click", "operation": "read-only recovery assessment",
             "enqueue_authorization_interpreted": "Cannot act while recovery gate blocks", "project_id": PID}
    previous_task = prior["task_id"]
    task = hub.create_task(main["agent_id"], "MAIN", "assess_d09_second_interruption",
                           scope, "run036-d09-second-interruption-audit-v1", depends=(previous_task,))
    lease = hub.claim(task["task_id"], main, "run036-main-recovery-review-claim-v1")
    save(PRIVATE / "main_session.json", {"identity": main, "task_id": task["task_id"], "lease": lease})
    for p in (PRIVATE / "read_only_recovery_assessment.json", RUN / "artifacts/status_summary.json"):
        hub.artifact(task["task_id"], main["agent_id"], p,
                     {"run": "run_036", "purpose": "read-only interrupted-run and recovery assessment"},
                     version="run036-recovery-audit-v1")
    hub.message(task["task_id"], main["agent_id"], "MAIN", summary,
                "run036-d09-recovery-audit-message-v1")
    hub.finish(lease, summary, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    report = f"""# run_036 — D09 第二次尝试的中断诊断

**BLOCKED_RECOVERY_REQUIRED。** 用户要求再次重启 D09，并报告此前 GUI 点错。公开 Queue 记录显示 run_035 的 `SPIO_R035_D09_RETRY1`（`{RETRY_ID}`）已于 `{retry[0].get('started_at')}` 开始 Datacheck；当前仍为 `{retry[0]['raw_status']}`，Live phase=`{live['phase']}`，Full Analysis 未有可信完成证据。原始 D09 `UNKNOWN_INTERRUPTED` 状态和旧锁文件继续保留。

AbqJobPilot 0.2.2 稳定版的**只读**恢复评估：owner=`{plan['assessment']['owner']['state']}`，solver probe=`{plan['assessment']['solver_process']['state']}`，can_apply=`{plan['can_apply']}`。阻塞项：{'; '.join(plan['unresolved'])}。当前状态为 `STALE_RUNNING`，公开 enqueue 会因 `RECOVERY_REQUIRED` 拒绝；本 Run 未调用任何 enqueue、Solver、Datacheck、恢复写入或清理锁文件。ODB 存在不能说明 Full Analysis 成功。

本机当前/此前 GUI 进程来自 `D:\\Projects\\abqjobpilot_dev`（源版本0.3.0.dev0），而已验收的公开 API 来源是 `D:\\Projects\\abqjobpilot` 稳定版0.2.2。稳定版文档明确：恢复修正是**本地 GUI 人工确认**，没有公开 API/CLI/MCP 的 unattended apply。其只读计划目前不可执行，不能由 Codex 绕过或直接修改 Queue JSON、Project DB、Live 状态与锁文件。

下一步需先由用户核实 GUI 操作及 Windows/Runner 状态，并在同一正确 Project 中完成官方恢复评估；当前因缺少命令退出证据且仍有旧 `.lck`，即使打开恢复对话框也可能显示不可应用。若用户选择重新启动 Windows，须确认没有重要未保存工作；之后再用稳定版 GUI 重新评估，不能预先保证准入。只有官方恢复状态明确、Queue 无其他可执行任务、原 INP 哈希和新工作目录检查通过时，才可按新授权创建独立第三次尝试。不能复用 run_035 工作目录，也不能覆盖两次历史产物。

AgentHub task `{task['task_id']}` 已记录诊断。盲测隔离与 run_034/035 的历史证据不变。
"""
    (RUN / "summary.md").write_text(report, encoding="utf-8")
    run_json = {"schema_version": "1.0", "run_id": "run_036",
                "stage": "D09 second interruption and official recovery assessment",
                "objective": "Determine whether one more retry can be safely queued after user's wrong GUI action",
                "status": "BLOCKED", "start_time": evidence["at"], "end_time": now(),
                "git": git_state, "python_interpreter": sys.executable,
                "python_version": sys.version.split()[0],
                "inputs": [{"path": "run/run_035/artifacts/queue_receipt.json",
                            "sha256": sha(ROOT / "run/run_035/artifacts/queue_receipt.json")},
                           {"path": rel(inp), "sha256": sha(inp)}],
                "outputs": [{"path": rel(p), "sha256": sha(p)} for p in
                            (PRIVATE / "read_only_recovery_assessment.json", RUN / "artifacts/status_summary.json", RUN / "summary.md")],
                "validation": [
                    {"check": "public_queue_and_project_identity", "status": "PASS", "scope": "Project PERSISTED; retry record and frozen INP match"},
                    {"check": "official_read_only_recovery_plan", "status": "BLOCKED", "scope": "can_apply=false; unresolved process exit and stale running metadata"},
                    {"check": "new_enqueue", "status": "NOT_RUN", "scope": "Recovery guard blocks further queue writes"},
                    {"check": "AgentHub_evidence", "status": "PASS", "scope": "Main task completed; audit chain verified"}],
                "errors": [{"code": "RECOVERY_REQUIRED", "detail": "; ".join(plan["unresolved"])}]}
    save(RUN / "run.json", run_json)
    save(RUN / "checkpoints/completed.json", {"at": run_json["end_time"], "status": "BLOCKED",
                                                    "task_id": task["task_id"],
                                                    "summary_sha256": sha(RUN / "summary.md")})
    index = ROOT / "run/README.md"
    text = index.read_text(encoding="utf-8")
    if "## run_036 — D09 二次中断与恢复评估" not in text:
        index.write_text(text.rstrip() + "\n\n## run_036 — D09 二次中断与恢复评估\n\n"
                         "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                         "| run_036 | 只读核验第二次尝试与官方恢复准入 | BLOCKED / RECOVERY_REQUIRED | [summary](run_036/summary.md) |\n\n"
                         "旧记录保留；恢复计划不可应用，未新增入队或求解。\n", encoding="utf-8")
    status_file = ROOT / "status/PROJECT_STATUS.md"
    status_text = status_file.read_text(encoding="utf-8")
    if "## 当前状态 — run_036" not in status_text:
        block = f"""## 当前状态 — run_036（2026-10-25，Asia/Shanghai）

**BLOCKED / RECOVERY_REQUIRED。** run_035 的 D09 新尝试 `{RETRY_ID}` 已由用户 GUI 启动并停留在 DATACHECK_RUNNING；Runner owner 为 STALE，Live 仍为 DATACHECK_RUNNING，公开恢复计划 `can_apply=false`。没有 Full Analysis 完成证据。不得再次入队、复用旧输出或清理锁文件；先经同一 Project 的官方 GUI 恢复评估澄清状态。详见[run_036报告](../run/run_036/summary.md)。本轮仅只读诊断，未新增求解、入队或恢复写入；此前结论保留。

"""
        assert status_text.startswith("# SMALL-PUNCH 项目状态\n\n")
        status_file.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n\n", "# SMALL-PUNCH 项目状态\n\n" + block, 1), encoding="utf-8")
    print(json.dumps({"status": "BLOCKED_RECOVERY_REQUIRED", "queue_id": RETRY_ID,
                      "raw_status": retry[0]["raw_status"], "recovery_can_apply": plan["can_apply"],
                      "unresolved": plan["unresolved"], "new_enqueued": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
