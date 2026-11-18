"""Read-only D09 retry gate assessment after the Windows reboot."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_037"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
OLD = "q_0bebaa417158409fba973efcbae921fd"
RETRY = "q_ed246bd7469b4701a8570326dfb73eb3"
INP = ROOT / "run/run_033/artifacts/candidates/SPIO_R033_D09_L/SPIO_R033_D09_L.inp"
EXPECTED_SHA = "5d754294edca19e8eef85661f5a99f18cfe189f484b86ddb5e3ee52acc354d4b"
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]

from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_workflow import build_recovery_plan
from agenthub_sp_invopt.hub import Hub


def now() -> str:
    return datetime.now().astimezone().isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    assert sys.version_info[:3] == (3, 11, 13)
    assert sha(INP) == EXPECTED_SHA
    assert not (RUN / "run.json").exists()
    started = now()
    git_state = {"branch": git("branch", "--show-current"),
                 "head": git("rev-parse", "HEAD"),
                 "remote": git("remote", "-v"),
                 "working_tree": git("status", "--short")}
    save(RUN / "checkpoints/start.json", {"at": started, "git": git_state,
        "python_interpreter": sys.executable, "python_version": sys.version.split()[0]})

    api = AbqJobPilotClient()
    version = api.capabilities()["application_version"]
    project = api.show_project(project_id=PID).to_dict()
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert version == "0.2.2"
    assert project["status"] == "OK" and project["project"]["project_id"] == PID
    assert Path(project["project"]["path"]).resolve() == PROJECT.resolve()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    scoped = api.for_project(project_id=PID)
    queue = scoped.list_jobs()
    assert queue["status"] == "OK"
    old = [x for x in queue["jobs"] if x["queue_id"] == OLD]
    retry = [x for x in queue["jobs"] if x["queue_id"] == RETRY]
    assert len(old) == len(retry) == 1
    plan = build_recovery_plan(PROJECT / "runtime", project_db=PROJECT / "project.db").to_dict()
    status = scoped.status(job_id=RETRY).to_dict()
    active = [x for x in queue["jobs"] if x["raw_status"] in
              {"QUEUED", "RUNNING", "DATACHECK_RUNNING", "DATACHECK_OK", "FULL_RUNNING"}]
    evidence = {"at": now(), "project_id": PID, "api_version": version,
                "settings_status": settings["status"], "inp_sha256": sha(INP),
                "old_queue_record": old[0], "retry_queue_record": retry[0],
                "retry_public_status": status, "active_queue_ids": [x["queue_id"] for x in active],
                "recovery_plan": plan, "new_enqueue_called": False,
                "solver_or_datacheck_started_by_codex": False,
                "recovery_or_runtime_metadata_modified_by_codex": False}
    save(RUN / "artifacts/private/read_only_reassessment.json", evidence)
    summary = {"at": evidence["at"], "status": "BLOCKED_RECOVERY_REQUIRED",
               "project_id": PID, "retry_queue_id": RETRY,
               "retry_raw_status": retry[0]["raw_status"],
               "retry_started_at": retry[0]["started_at"],
               "retry_ended_at": retry[0]["ended_at"],
               "old_d09_raw_status": old[0]["raw_status"],
               "active_queue_ids": evidence["active_queue_ids"],
               "owner_state": plan["assessment"]["owner"]["state"],
               "solver_process_state": plan["assessment"]["solver_process"]["state"],
               "process_identity_state": plan["assessment"]["process_evidence"]["state"],
               "reboot_verified_by_recovery": plan["assessment"]["reboot_verified"],
               "recovery_can_apply": plan["can_apply"],
               "unresolved": plan["unresolved"], "third_job_enqueued": False}
    save(RUN / "artifacts/status_summary.json", summary)

    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    actor = hub.register("MAIN", "codex-main-run037-d09-reassessment")
    prior = json.loads((ROOT / "run/run_036/checkpoints/completed.json").read_text(encoding="utf-8"))
    task = hub.create_task(actor["agent_id"], "MAIN", "assess_d09_recovery_after_reboot",
        {"run": "run_037", "project_id": PID, "prior_task_id": prior["task_id"],
         "requested_action": "new D09 retry queue-only if safe", "result": summary["status"]},
        "run037-d09-recovery-after-reboot-v1", depends=(prior["task_id"],))
    lease = hub.claim(task["task_id"], actor, "run037-main-review-claim-v1")
    save(RUN / "artifacts/private/main_session.json",
         {"identity": actor, "task_id": task["task_id"], "lease": lease})
    for path in (RUN / "artifacts/private/read_only_reassessment.json",
                 RUN / "artifacts/status_summary.json"):
        hub.artifact(task["task_id"], actor["agent_id"], path,
                     {"run": "run_037", "purpose": "read-only recovery gate reassessment"},
                     version="run037-recovery-gate-v1")
    hub.message(task["task_id"], actor["agent_id"], "MAIN", summary,
                "run037-d09-reassessment-result-v1")
    hub.finish(lease, summary, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()

    report = ("# run_037 — D09 重启后恢复准入复核\n\n"
        f"**BLOCKED / RECOVERY_REQUIRED。** 原D09 `{OLD}` 仍为 `{old[0]['raw_status']}`；"
        f"第一次重试 `{RETRY}` 仍为 `{retry[0]['raw_status']}`，"
        f"开始时间 `{retry[0]['started_at']}`，结束时间未知。尚无可信 Full Analysis 完成记录。\n\n"
        f"AbqJobPilot {version} 官方只读恢复计划：owner=`{summary['owner_state']}`，"
        f"solver=`{summary['solver_process_state']}`，进程身份=`{summary['process_identity_state']}`，"
        f"reboot_verified=`{summary['reboot_verified_by_recovery']}`，can_apply=`{plan['can_apply']}`。"
        f"阻塞原因：{'; '.join(plan['unresolved'])}。本机重启不等于官方恢复准入；"
        "不能绕过公开入队守卫或直接修改队列、数据库、锁文件。\n\n"
        "本次仅只读审计并登记 AgentHub；未创建第三次尝试，未入队、启动 Solver/Datacheck、"
        "应用恢复或修改原有产物。请在正确 Project 的稳定版 GUI 运行 Tools → Runtime Recovery 并保存报告；"
        "当前计划不可应用时，需由 AbqJobPilot 维护者核查进程身份与历史锁文件的安全恢复方式。"
        "待公开状态明确空闲后，重新审核独立新工作目录和冻结 INP 才能提交新一次尝试。\n\n"
        f"AgentHub task `{task['task_id']}`；完整只读证据在 `artifacts/private/read_only_reassessment.json`。\n")
    (RUN / "summary.md").write_text(report, encoding="utf-8")
    run_json = {"schema_version": "1.0", "run_id": "run_037",
                "stage": "D09 recovery gate reassessment after reboot",
                "objective": "Queue another D09 attempt only if official recovery gate is clear",
                "status": "BLOCKED", "start_time": started, "end_time": now(),
                "git_branch": git_state["branch"], "git_head": git_state["head"],
                "git": git_state, "python_interpreter": sys.executable,
                "inputs": [{"path": "run/run_033/artifacts/candidates/SPIO_R033_D09_L/SPIO_R033_D09_L.inp",
                            "role": "frozen input", "sha256": sha(INP)},
                           {"path": "run/run_036/checkpoints/completed.json", "role": "prior diagnosis"}],
                "outputs": [{"path": "run/run_037/artifacts/status_summary.json", "role": "read-only status"},
                            {"path": "run/run_037/artifacts/private/read_only_reassessment.json",
                             "role": "private recovery plan"},
                            {"path": "run/run_037/summary.md", "role": "report"}],
                "validation": [{"check": "project_and_frozen_input", "status": "PASS",
                                "evidence": "Project ID, PERSISTED Settings and input SHA-256 match"},
                               {"check": "official_recovery_plan", "status": "BLOCKED",
                                "evidence": "can_apply=false and prior retry remains DATACHECK_RUNNING"},
                               {"check": "third_enqueue", "status": "NOT_RUN",
                                "evidence": "public recovery guard not cleared"}],
                "errors": [{"code": "RECOVERY_REQUIRED", "severity": "BLOCKED",
                            "message": "; ".join(plan["unresolved"])}]}
    save(RUN / "run.json", run_json)
    save(RUN / "checkpoints/completed.json",
         {"at": run_json["end_time"], "status": "BLOCKED", "task_id": task["task_id"],
          "summary_sha256": sha(RUN / "summary.md")})
    index = ROOT / "run/README.md"
    text = index.read_text(encoding="utf-8")
    assert "## run_037 — D09 重启后恢复准入复核" not in text
    index.write_text(text.rstrip() + "\n\n## run_037 — D09 重启后恢复准入复核\n\n"
                     "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                     "| run_037 | 重启后只读复核 D09 第三次尝试准入 | BLOCKED / RECOVERY_REQUIRED | "
                     "[summary](run_037/summary.md) |\n\n未新增入队或求解。\n", encoding="utf-8")
    status_path = ROOT / "status/PROJECT_STATUS.md"
    status_text = status_path.read_text(encoding="utf-8")
    assert status_text.startswith("# SMALL-PUNCH 项目状态\n\n")
    status_path.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n\n",
        "# SMALL-PUNCH 项目状态\n\n## 当前状态 — run_037（2026-10-25，Asia/Shanghai）\n\n"
        f"**BLOCKED / RECOVERY_REQUIRED。** 重启后官方只读恢复计划仍 `can_apply=false`；"
        f"第二次 D09 尝试 `{RETRY}` 为 `DATACHECK_RUNNING`，进程身份不匹配，旧锁文件仍在。"
        "第三次尝试未入队；不得点击 Start Queue。详见[run_037报告](../run/run_037/summary.md)。\n\n", 1),
        encoding="utf-8")
    print(json.dumps({"status": summary["status"], "task_id": task["task_id"],
                      "queue_id": RETRY, "recovery_can_apply": plan["can_apply"],
                      "third_job_enqueued": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
