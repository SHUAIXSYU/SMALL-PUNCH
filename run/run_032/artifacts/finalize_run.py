"""Finalize the I01 evidence review and I02 queue-only stop point."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_032"
A = RUN / "artifacts"
P = A / "private"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
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


def main():
    assert not (RUN / "checkpoints/completion.json").exists()
    gate = read(A / "main_i01_gate.json")
    i02 = read(A / "i02_enqueue_result.json")
    assert gate["status"] == "PASS_I01_EXPLORATORY_GATE_WITH_WARNINGS"
    assert i02["status"] == "I02_QUEUED_AWAITING_MANUAL_START"
    assert i02["solver_started"] is False and i02["datacheck_started"] is False
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    assert hub.task(gate["odb_task_id"])["execution_state"] == "COMPLETED"
    assert hub.task(gate["review_task_id"])["execution_state"] == "COMPLETED"
    assert hub.task(i02["task_id"])["execution_state"] == "COMPLETED"
    assert hub.verify_chain()
    api = AbqJobPilotClient().for_project(project_id=i02["project_id"])
    q = api.list_jobs()
    assert q["status"] == "OK" and not q["errors"]
    executable = [x for x in q["jobs"] if x["raw_status"] not in {
        "COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL", "FAILED_NUMERICAL",
        "FAILED_INPUT", "FAILED_LICENSE", "DATACHECK_FAILED",
        "DATACHECK_FAILED_INVALID_GPU_OPTION", "SKIPPED", "CANCELLED"}]
    assert len(executable) == 1
    assert executable[0]["queue_id"] == i02["queue_id"]
    assert executable[0]["status"] == "QUEUED" and not executable[0]["started_at"]

    budget = {"at": now(), "project_id": i02["project_id"],
              "authorized_frozen_jobs": 8, "confirmed_started_attempts": 1,
              "completed_attempts": 1, "queued_not_started": 1,
              "unsubmitted_frozen_jobs": 6, "automatic_retries": 0,
              "I01": {"queue_id": gate["queue_id"], "status": "COMPLETED_WITH_WARNINGS",
                      "main_gate": gate["status"], "loss": gate["loss"],
                      "loss_status": gate["loss_status"]},
              "I02": {"queue_id": i02["queue_id"], "status": "QUEUED",
                      "solver_start": "AWAITING_USER_GUI"},
              "I03_I08": "NOT_QUEUED", "next_step": "USER_MANUAL_START_I02_ONLY"}
    budget_path = A / "budget_status.json"
    with budget_path.open("x", encoding="utf-8") as f:
        json.dump(budget, f, indent=2, ensure_ascii=False)
        f.write("\n")

    summary = f"""# run_032 — I01真实结果与I02受控入队

**WARNING / I02_QUEUED_AWAITING_MANUAL_START。** 用户GUI启动的I01经AbqJobPilot公开接口确认Datacheck与Full均返回0，Queue为`COMPLETED_WITH_WARNINGS`，唯一执行尝试、输入哈希与ODB/STA/MSG/DAT/LOG身份吻合；Runner总耗时210秒。真实ODB Codex会话通过AgentHub任务`{gate['odb_task_id']}`领取、只读提取并回传，MAIN任务`{gate['review_task_id']}`独立复核后按求解前冻结的run_030门槛批准仅I02继续。审批只表示探索性数值评价可继续，不代表材料物理验证。

I01 Punch RP正向F–D有403帧，完整覆盖0–1.2 mm；原339点实验曲线中冻结241点、等权、固定1428.9 N、不外推的`run017-exploratory-fd-v1`得探索性PROVISIONAL Loss **{gate['loss']:.12f}**，RMSE **{gate['rmse_n']:.3f} N**、NRMSE **{gate['nrmse']:.6f}**。最大保存帧PEEQ **{gate['max_saved_peeq']:.6f}**，低于0.85人工裕度检查线及0.9材料表终点。STA为402接受增量、0拒绝试算、0 cutback；未见接受态负特征值、过度畸变或大应变警告。接受态首增量零力矩提示和DAT接触跟踪回退提示保留为WARNING；接触/局部F–D未发现未解释的明显突跳。历史Runner进程证据仍为UNCONFIRMED，当前只读安全与真实终态由独立证据核对，不能据此追认历史进程细节。

I02 `{i02['job_name']}` 在既有8次冻结授权内通过哈希、Project/PERSISTED Settings、Runner/Queue、工作目录、Preflight及dry-run复查后，**仅通过公开API入队一次**。queue_id=`{i02['queue_id']}`，INP SHA-256=`{i02['inp_sha256']}`，工作目录=`{i02['working_dir']}`，14 CPU/0 GPU，Datacheck和Full启用、零自动重试。当前唯一可执行Queue记录是I02，未启动Datacheck/Solver；I03–I08未入队。用户应在正确Project中确认只有I02待执行，手动点击一次Start Queue。AbqJobPilot无可靠自动异常停队列；本次单Job方式保持逐项审核。

AgentHub保留授权、I01 ODB真实会话消息与证据、MAIN准入决定、I02入队审批和Queue回读。私有曲线/原始可恢复实验数据位于本Run的Git忽略目录`artifacts/private/odb/`；证据含完整哈希清单。封存拉伸验证资料未读取，历史信息暴露声明和run_025原BLOCKED结论保持。无Codex启动求解、重试、改冻结INP、DE/BO/RL或Git提交。

关键证据：`artifacts/private/execution_audit.json`、`artifacts/private/odb/REPORT.md`、`artifacts/private/odb/result.json`、`artifacts/private/odb/manifest.json`、`artifacts/main_i01_gate.json`、`artifacts/i02_admission.json`、`artifacts/i02_enqueue_result.json`、`artifacts/budget_status.json`。
"""
    (RUN / "summary.md").write_text(summary, encoding="utf-8")

    run = read(RUN / "run.json")
    assert run["status"] == "RUNNING"
    run["status"] = "WARNING"
    run["end_time"] = now()
    run["outputs"] = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)}
                      for p in (P / "execution_audit.json", P / "odb/result.json",
                                P / "odb/manifest.json", A / "main_i01_gate.json",
                                A / "i02_admission.json", A / "i02_enqueue_result.json",
                                budget_path, RUN / "summary.md")]
    run["validation"] = [
        {"check": "I01_public_execution_terminal_and_identity", "status": "PASS"},
        {"check": "real_ODB_AgentHub_delivery_and_MAIN_receipt", "status": "PASS"},
        {"check": "frozen_loss_independent_recalculation", "status": "PASS"},
        {"check": "I01_exploratory_numerical_gate", "status": "WARNING_PASS", "scope": "No predeclared blocker; accepted zero moment and DAT contact warning retained"},
        {"check": "I02_public_preflight_dry_run_enqueue_only", "status": "PASS"},
        {"check": "I02_unique_queue_and_no_solver_start", "status": "PASS"}]
    run["errors"] = []
    (RUN / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    completion = {"at": now(), "run_id": "run_032", "status": "WARNING",
                  "stop_state": i02["status"], "i01_gate": gate["status"],
                  "i01_loss": gate["loss"], "i02_queue_id": i02["queue_id"],
                  "agenthub_chain_valid": True, "queue_unique_executable": True,
                  "summary_sha256": sha(RUN / "summary.md"),
                  "run_json_sha256": sha(RUN / "run.json"),
                  "no_codex_solver_start": True, "sealed_tensile_accessed": False}
    with (RUN / "checkpoints/completion.json").open("x", encoding="utf-8") as f:
        json.dump(completion, f, indent=2, ensure_ascii=False)
        f.write("\n")
    index = ROOT / "run/README.md"
    with index.open("a", encoding="utf-8") as f:
        f.write("\n## run_032 — I01真实ODB审核与I02单项入队\n\n")
        f.write("| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n")
        f.write("| run_032 | I01真实ODB、冻结Loss、MAIN门控和I02 queue-only入队 | WARNING / I02_QUEUED_AWAITING_MANUAL_START | [summary](run_032/summary.md) |\n\n")
        f.write("I01单次尝试已完成；I02为唯一待执行Job，等待用户GUI手动Start Queue；I03–I08未入队。\n")
    status = ROOT / "status/PROJECT_STATUS.md"
    old = status.read_text(encoding="utf-8")
    assert old.startswith("# SMALL-PUNCH 项目状态\n")
    lead = f"""# SMALL-PUNCH 项目状态

## 当前状态 — run_032（2026-10-24，Asia/Shanghai）

**WARNING / I02_QUEUED_AWAITING_MANUAL_START。** 用户GUI完成I01的唯一尝试，真实ODB Agent已通过AgentHub回传；MAIN按run_030冻结门槛审查后准许I02继续。I01探索性PROVISIONAL Loss={gate['loss']:.9f}，PEEQ={gate['max_saved_peeq']:.6f}、0 cutback，零力矩与接触跟踪提示保留WARNING；不宣称物理验证。I02 queue_id=`{i02['queue_id']}`，唯一可执行Job，等待用户在正确AbqJobPilot Project手动Start Queue；Codex未启动求解。8项冻结授权中1次已执行、1项待启动、6项未入队；不自动追加。详见[run_032报告](../run/run_032/summary.md)。run_025历史BLOCKED及封存资料禁读规则保留。

"""
    status.write_text(lead + old[len("# SMALL-PUNCH 项目状态\n"):], encoding="utf-8")
    print(json.dumps({"status": i02["status"], "queue_id": i02["queue_id"],
                      "run": "run_032", "loss": gate["loss"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
