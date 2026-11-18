"""Finalize the I01 queue-only stop point and eight-job authorization ledger."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "run/run_031"
A = R / "artifacts"
P = A / "private"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from agenthub_sp_invopt.hub import Hub
from abqjobpilot.api import AbqJobPilotClient


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    assert not (A / "budget_status.json").exists()
    result = read(A / "enqueue_result.json")
    auth = read(A / "authorization.json")
    batch = read(ROOT / "run/run_030/artifacts/prepared_batch.json")
    session = read(P / "main_session.json")
    admission = read(A / "admission.json")
    after = read(A / "queue_after.json")
    post = read(A / "postcheck.json")
    assert result["status"] == "I01_QUEUED_AWAITING_MANUAL_START"
    assert result["queue_submitted_count"] == 1 and result["started_attempts_confirmed"] == 0
    assert result["remaining_unsubmitted_frozen_jobs"] == 7
    assert result["job_name"] == batch["points"][0]["job_name"]
    assert result["inp_sha256"] == batch["points"][0]["inp_sha256"]
    assert sha(Path(result["inp_path"])) == result["inp_sha256"]
    assert not any(Path(result["working_dir"]).iterdir())
    assert result["queue_id"] == after["existing"][0]["queue_id"]
    assert post["status"]["status"] == "QUEUED" and post["no_solver_or_datacheck_start"]
    executable = {"QUEUED", "DATACHECK_OK", "DATACHECK_RUNNING", "FULL_RUNNING", "UNKNOWN_INTERRUPTED"}
    assert [j["job_name"] for j in after["queue"]["jobs"] if j["status"] in executable] == [result["job_name"]]
    api = AbqJobPilotClient().for_project(project_id=result["project_id"])
    live = api.list_jobs()
    matches = [j for j in live["jobs"] if j["queue_id"] == result["queue_id"]]
    assert len(matches) == 1 and matches[0]["status"] == "QUEUED"
    assert [j["job_name"] for j in live["jobs"] if j["status"] in executable] == [result["job_name"]]
    assert matches[0]["cpus"] == 14 and matches[0]["gpus"] == 0
    assert matches[0]["run_datacheck"] and matches[0]["run_full"]
    assert matches[0]["work_dir"] == result["working_dir"] and matches[0]["inp_path"] == result["inp_path"]
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    assert hub.task(session["budget_task_id"])["execution_state"] == "COMPLETED"
    assert hub.task(session["queue_tasks"]["I01"])["execution_state"] == "COMPLETED"
    assert all(hub.task(session["queue_tasks"][f"I{i:02d}"])["execution_state"] == "PENDING" for i in range(2, 9))
    assert all(hub.task(session["review_tasks"][f"I{i:02d}"])["execution_state"] == "PENDING" for i in range(1, 9))
    assert hub.task(session["phase_gate_task_id"])["execution_state"] == "PENDING"
    ledger = {"at": now(), "status": result["status"], "authorized_frozen_jobs": 8,
              "queue_submitted": 1, "confirmed_started_attempts": 0,
              "remaining_unsubmitted_frozen_jobs": 7, "automatic_retries": 0,
              "point_status": [{"point_id": x["point_id"], "job_name": x["job_name"],
                                "inp_sha256": x["inp_sha256"],
                                "queue_task_id": session["queue_tasks"][x["point_id"]],
                                "result_review_task_id": session["review_tasks"][x["point_id"]],
                                "queue_id": result["queue_id"] if x["point_id"] == "I01" else None,
                                "queue_state": "QUEUED_AWAITING_MANUAL_START" if x["point_id"] == "I01" else "GATE_PENDING",
                                "started_attempts_confirmed": 0}
                               for x in batch["points"]],
              "phase_gate_task_id": session["phase_gate_task_id"],
              "I02_dependency": "I01 real result MAIN review",
              "I05_dependency": "I01-I04 phase gate",
              "no_automatic_cross_session_wakeup": True}
    save(A / "budget_status.json", ledger)
    summary = f"""# run_031 — 八项授权下的 I01 Queue-only 入队

**I01_QUEUED_AWAITING_MANUAL_START。** 用户明确批准 run_030 冻结的 I01–I08 各最多一次 Datacheck+Full Analysis；此 Run 只将 I01 入队。8项授权不意味着同时运行8项；I02–I08 的 AgentHub 任务处于依赖门控等待状态，用户无须为同一冻结范围再次授权。新入队1项，实际启动尝试确认0项，尚未提交7项，零自动重试。

| 身份 | 当前记录 |
| --- | --- |
| Job | `{result['job_name']}` |
| queue_id | `{result['queue_id']}` |
| I01 AgentHub task_id | `{result['task_id']}` |
| 八项预算 task_id | `{result['budget_task_id']}` |
| Project ID | `{result['project_id']}` |
| INP | `run/run_030/artifacts/candidates/{result['job_name']}/{result['job_name']}.inp` |
| INP SHA-256 | `{result['inp_sha256']}` |
| 独立工作目录 | `run/run_030/artifacts/solver/{result['job_name']}` |
| 参数 | σy={result['sigma_y_mpa']:.17g} MPa, n={result['n']:.17g} |
| 资源与阶段 | 14 CPU，0 GPU，Datacheck=True，Full=True；每项最多一次，无自动重试 |

通过本机 AbqJobPilot 0.2.2 公开 API 验证 Project ID、PERSISTED Settings、Abaqus 2024 命令存在、Queue/Runner 无其他可执行或待恢复状态；冻结8份输入和目录哈希/冲突检查通过。I01 Preflight=`PREVIEW_READY`、dry-run=`DRY_RUN_READY`。单次正式 `enqueue_only` 返回上述 queue_id。再次回读 Queue，**只有 I01 可执行且为 QUEUED**，CPU/GPU、两阶段、输入和工作目录与冻结值一致。I02–I08 未入队；I01 工作目录尚无求解输出，Datacheck/Solver 未启动。历史8项 Queue 记录均为终态，未清空或修改。

MAIN通过正式AgentHub身份登记总授权、8个输入完整SHA、8项各自的Queue任务和结果审核任务、I01的任务级入队与手动启动许可，并记录 I01 queue_id。I02 依赖 I01 的真实结果经MAIN审核；I05 另依赖 I01–I04 阶段关口。Hub本身不会自动唤醒其他 Codex 会话，也不启动 Runner。预算状态见[结构化台账](artifacts/budget_status.json)，完整检查见[准入证据](artifacts/admission.json)、[Queue回读](artifacts/queue_after.json)与[提交结果](artifacts/enqueue_result.json)。

**人工停止点：**请在 AbqJobPilot GUI 打开 `E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`，确认只有 `{result['job_name']}` 待执行，然后由您点击一次 **Start Queue**。当前公开接口未替您启动 Solver。完成后需重新激活 MAIN，以公开历史和真实输出核验，交真实 ODB Agent 只读提取并做冻结 Loss/数值审核；通过后方可在本次8项授权内提交 I02。失败或身份不明时暂停，不能重新入队或补跑。run_025 历史 BLOCKED 与保留拉伸禁读规则不变。
"""
    (R / "summary.md").write_text(summary, encoding="utf-8")
    meta = read(R / "run.json")
    assert meta["status"] == "RUNNING"
    meta.update(status="WARNING", end_time=now(),
                outputs=[{"path": rel(path), "role": role} for path, role in [
                    (A / "authorization.json", "Frozen eight-job authorization"),
                    (A / "admission.json", "I01 preflight and runtime admission"),
                    (A / "enqueue_result.json", "Queue-only result"),
                    (A / "budget_status.json", "Budget consumption snapshot"),
                    (R / "summary.md", "Stop-point report")]],
                validation=[
                    {"check": "frozen_identity", "status": "PASS", "scope": "All eight INP and parameter hashes, unique empty workdirs"},
                    {"check": "project_settings", "status": "PASS", "scope": "AbqJobPilot 0.2.2, exact Project, PERSISTED settings, Abaqus command and resources"},
                    {"check": "runner_and_queue_admission", "status": "PASS", "scope": "No active/recovery conflict or other executable Job before enqueue"},
                    {"check": "i01_preview", "status": "PASS", "scope": "Public preflight/dry-run only; no datacheck or Solver"},
                    {"check": "i01_queue_only", "status": "PASS", "scope": "Single QUEUED I01, readback exact queue_id/resources/input/workdir"},
                    {"check": "numerical_result", "status": "NOT_EVALUATED", "scope": "Waiting for manual GUI Start Queue and actual ODB review"}],
                errors=[])
    (R / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    idx = ROOT / "run/README.md"
    text = idx.read_text(encoding="utf-8")
    assert "## run_031" not in text
    idx.write_text(text.rstrip() + "\n\n## run_031 — 八项授权与I01单项入队\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_031 | 登记8项冻结授权、逐项门控、仅I01 queue-only入队 | WARNING / I01_QUEUED_AWAITING_MANUAL_START | [summary](run_031/summary.md) |\n\nI01等待用户GUI手动Start Queue；其余7项未入队，完成与审核后才逐项继续。\n", encoding="utf-8")
    status = ROOT / "status/PROJECT_STATUS.md"
    text = status.read_text(encoding="utf-8")
    heading = "# SMALL-PUNCH 项目状态\n"
    assert text.startswith(heading) and "## 当前状态 — run_031" not in text
    status.write_text(heading + f"\n## 当前状态 — run_031（2026-10-24，Asia/Shanghai）\n\n**WARNING / I01_QUEUED_AWAITING_MANUAL_START。** 用户一次性批准run_030冻结8项，每项一次Datacheck+Full、14CPU/0GPU、零自动重试，由用户GUI手动启动。当前仅I01入队，queue_id=`{result['queue_id']}`；其余7项未提交，需逐项实际结果与MAIN审核后继续。Runner未启动、无新Datacheck/Solver；run_025历史BLOCKED保留。见[run_031报告](../run/run_031/summary.md)。停止等待用户GUI操作。\n\n" + text[len(heading):], encoding="utf-8")
    # Register the final Run evidence while a fresh, scoped MAIN report task is live.
    task = hub.create_task(session["identity"]["agent_id"], "MAIN", "record_i01_queue_stop_point",
                           {"run": "run_031", "queue_id": result["queue_id"],
                            "i01_queue_task_id": result["task_id"], "budget_task_id": result["budget_task_id"],
                            "actual_solver_started": False},
                           "run031-report-stop-point-v1", depends=(result["task_id"],))["task_id"]
    lease = hub.claim(task, session["identity"], "run031-report-claim-v1")
    paths = [A / "authorization.json", A / "admission.json", A / "request.json",
             A / "enqueue_response.json", A / "queue_after.json", A / "postcheck.json",
             A / "enqueue_result.json", A / "agenthub_receipt.json", A / "budget_status.json",
             R / "summary.md", R / "run.json"]
    manifest = {"at": now(), "status": result["status"],
                "files": [{"path": rel(path), "sha256": sha(path)} for path in paths]}
    save(A / "manifest.json", manifest)
    for path in paths + [A / "manifest.json"]:
        hub.artifact(task, session["identity"]["agent_id"], path,
                     {"run": "run_031", "scope": "I01 queue-only; eight frozen jobs authorized"},
                     version="run031-v1")
    hub.finish(lease, {"status": result["status"], "queue_id": result["queue_id"],
                       "submitted": 1, "started_confirmed": 0, "unsubmitted": 7},
               evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    save(R / "checkpoints/completion.json", {"at": now(), "status": result["status"],
         "budget_task_id": result["budget_task_id"], "i01_task_id": result["task_id"],
         "report_task_id": task, "queue_id": result["queue_id"],
         "budget_status_sha256": sha(A / "budget_status.json"),
         "manifest_sha256": sha(A / "manifest.json"), "hub_chain_valid": True,
         "queue_submitted": 1, "started_attempts_confirmed": 0,
         "remaining_unsubmitted": 7})
    print(json.dumps({"status": result["status"], "queue_id": result["queue_id"],
                      "authorized": 8, "submitted": 1, "started_confirmed": 0,
                      "remaining_unsubmitted": 7}))


if __name__ == "__main__":
    main()
