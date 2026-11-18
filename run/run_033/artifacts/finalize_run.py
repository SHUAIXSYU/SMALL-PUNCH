"""Final public readback and Run protocol closure for queue-only batch DOE."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_033"
A = RUN / "artifacts"
P = A / "private"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.runtime_coordination import runner_ownership_state
from agenthub_sp_invopt.hub import Hub

TERMINAL = {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL",
            "FAILED_NUMERICAL", "FAILED_INPUT", "FAILED_LICENSE",
            "DATACHECK_FAILED", "DATACHECK_FAILED_INVALID_GPU_OPTION",
            "SKIPPED", "CANCELLED"}


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


def save_once(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    assert not (RUN / "checkpoints/completion.json").exists()
    batch = read(A / "prepared_batch.json")
    manifest = read(A / "queue_manifest.json")
    ids = read(A / "queue_task_ids.json")
    auth = read(A / "authorization_scope.json")
    assert manifest["status"] == "TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START"
    assert batch["project_id"] == manifest["project_id"] == auth["project_id"] == PID
    assert manifest["prepared_batch_sha256"] == sha(A / "prepared_batch.json")
    assert manifest["authorization_scope_sha256"] == sha(A / "authorization_scope.json")
    assert len(batch["points"]) == len(manifest["ordered_points"]) == len(manifest["queue_ids"]) == 20
    assert len(set(manifest["queue_ids"])) == 20
    assert [x["point_id"] for x in manifest["ordered_points"]] == batch["batch_order"]
    assert auth["queue_order"] == batch["batch_order"]
    assert manifest["solver_started"] is False and manifest["datacheck_started"] is False
    assert manifest["all_20_workdirs_empty"]
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    session = read(P / "main_session.json")
    for task in (session["budget_task_id"], session["cae_task_id"],
                 session["review_task_id"], ids["batch_confirm_task_id"]):
        assert hub.task(task)["execution_state"] == "COMPLETED"
    for point_id, task_id in ids["point_tasks"].items():
        task = hub.task(task_id)
        assert task["execution_state"] == "COMPLETED" and task["evidence_state"] == "RECORDED"
        assert json.loads(task["result"])["point_id"] == point_id
    assert hub.verify_chain()
    api = AbqJobPilotClient()
    scoped = api.for_project(project_id=PID)
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert settings["status"] == "PERSISTED" and settings["project_id"] == PID
    q = scoped.list_jobs()
    assert q["status"] == "OK" and not q["errors"]
    executable = [j for j in q["jobs"] if j.get("raw_status") not in TERMINAL]
    assert [j["job_name"] for j in executable] == [p["job_name"] for p in batch["points"]]
    assert [j["queue_id"] for j in executable] == manifest["queue_ids"]
    for j, p in zip(executable, batch["points"]):
        assert j["status"] == j["raw_status"] == "QUEUED"
        assert j["cpus"] == 14 and j["gpus"] == 0
        assert j["run_datacheck"] and j["run_full"]
        assert Path(j["inp_path"]).resolve() == (ROOT / p["inp_path"]).resolve()
        assert Path(j["work_dir"]).resolve() == (ROOT / p["working_dir"]).resolve()
        assert p["inp_sha256"] in (j.get("notes") or "")
        assert not j.get("started_at") and not j.get("ended_at")
        assert sha(ROOT / p["inp_path"]) == p["inp_sha256"]
        assert not any((ROOT / p["working_dir"]).iterdir())
    recovery = assess_runtime(ROOT / "agenthub_sp_invopt/abqjobpilot_project/runtime",
                              project_db=ROOT / "agenthub_sp_invopt/abqjobpilot_project/project.db")
    owner = runner_ownership_state(ROOT / "agenthub_sp_invopt/abqjobpilot_project/runtime")
    assert recovery["status"] == "CLEAN" and recovery["live_phase"] == "IDLE"
    assert not recovery["running_queue_ids"] and not recovery["lock_files"]
    assert owner["state"] == "ABSENT"
    save_once(P / "final_public_readback.json", {"at": now(), "settings": settings,
                                                  "queue": q, "runner": recovery,
                                                  "owner": owner,
                                                  "executable_queue_ids": manifest["queue_ids"],
                                                  "all_queued_not_started": True})
    rows = []
    for p, record in zip(batch["points"], manifest["ordered_points"]):
        rows.append(f"| {p['point_id']} | `{p['job_name']}` | `{record['queue_id']}` | {p['sigma_y_mpa']:.6f} | {p['n']:.6f} |")
    summary = """# run_033 — 20 Job DOE batch queue-only

**WARNING / TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户明确授权20个新增Job和GUI中一次Start Queue；Codex只通过AbqJobPilot 0.2.2公开API逐条queue-only入队，未启动Datacheck或Solver。正式Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`，PERSISTED Settings为Abaqus 2024、14 CPU/0 GPU、Datacheck+Full。最终公开接口回读恰好20项可执行记录，顺序、路径、SHA-256和资源与冻结清单一致，全部为QUEUED且独立工作目录为空；Runner空闲，无待恢复状态。I01/I02已完成，不在本批，未重复运行。

I02在入队前核查：唯一真实Queue/History执行尝试，Datacheck和Full日志返回0，Queue为`COMPLETED_WITH_WARNINGS`，STA完成，ODB/STA/MSG/DAT/LOG身份及哈希稳定，当前无锁或目标进程；数值警告保留待整批ODB分析，不把Solver完成当作科学有效。无阻塞性执行身份或文件冲突。

DOE设计在新INP生成前冻结：14新点中7个全域Latin hypercube、7个既有SPT低Loss邻域及宽裕边界的Sobol贪心最远点；固定种子、间距及归一化参数公式见`artifacts/doe_design.json`。低Loss依据是历史run_022的SPT-only PROVISIONAL证据，并非封存拉伸结果或真实材料答案。真实CAE会话通过AgentHub任务完成14份输入，MAIN独立核对20份材料表、非材料模型字节、数值设置、SHA-256与空输出目录。20/20公开Preflight、20/20 Dry-run通过，预览阶段Queue不变；冻结清单见`artifacts/prepared_batch.json`。

## 队列顺序

| 点 | Job | queue_id | sigma_y (MPa) | n |
| --- | --- | --- | ---: | ---: |
""" + "\n".join(rows) + """

本批授权身份见`artifacts/authorization_scope.json`，20份完整INP路径、参数精度、完整SHA-256和工作目录见`artifacts/prepared_batch.json`，逐项公开API回执见`artifacts/queue_receipts/`，最终Queue证据见`artifacts/queue_manifest.json`。AgentHub记录20个独立队列任务、批准动作、queue_id和证据；审计链核验通过。20个Job尚未开始，预算已入队20/20、实际新增求解尝试0/20。运行后失败尝试同样消耗对应额度，零自动重试，不补点。

**AUTO_STOP_UNAVAILABLE。** GUI Start Queue可能串行运行全部20项，单个Job失败或严重警告不会可靠地自动停整个队列；用户已明确接受这一批量模式。请在正确Project确认队列只有上述20项后，亲自点击一次Start Queue。此动作尚未发生，Codex不会代点。整批实际终态由后续公开Queue/History核验，再交真实ODB会话只读批量提取；失败或不可信Job的Loss=null。当前未执行BO、DE或RL，未访问封存拉伸验证数据，保留历史信息暴露和旧Run结论，未commit/push。
"""
    (RUN / "summary.md").write_text(summary, encoding="utf-8")
    run = read(RUN / "run.json")
    assert run["status"] == "RUNNING"
    run["status"] = "WARNING"
    run["end_time"] = now()
    run["outputs"] = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
                      for path in (P / "i02_execution_audit.json", A / "doe_design.json",
                                   A / "cae_candidate_manifest.json", A / "cae_result.json",
                                   P / "main_preflight.json", A / "prepared_batch.json",
                                   A / "authorization_scope.json", A / "queue_manifest.json",
                                   P / "final_public_readback.json", RUN / "summary.md")]
    run["validation"] = [
        {"check": "I02_actual_execution_identity", "status": "WARNING_PASS", "scope": "One completed attempt; numerical warnings deferred"},
        {"check": "DOE_pre_generation_freeze", "status": "PASS", "scope": "7 global + 7 local, fixed seeds, no parameter repeat"},
        {"check": "real_CAE_AgentHub_delivery", "status": "PASS", "scope": "14 new INPs"},
        {"check": "twenty_static_input_identity", "status": "PASS", "scope": "Material, nonmaterial, hashes and empty independent workdirs"},
        {"check": "twenty_public_preflight_dry_run", "status": "PASS", "scope": "20/20 each, no queue mutation during preview"},
        {"check": "twenty_queue_only_public_API", "status": "PASS", "scope": "20 unique queue IDs in frozen order"},
        {"check": "no_solver_or_datacheck_start_by_Codex", "status": "PASS", "scope": "Queue remains QUEUED; workdirs empty"},
        {"check": "automatic_batch_failure_stop", "status": "WARNING", "scope": "Unavailable; user explicitly accepted possible continuation"}]
    run["errors"] = []
    (RUN / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    completion = {"at": now(), "run_id": "run_033", "status": "WARNING",
                  "stop_state": manifest["status"],
                  "project_id": PID, "prepared_batch_sha256": sha(A / "prepared_batch.json"),
                  "queue_manifest_sha256": sha(A / "queue_manifest.json"),
                  "queue_count": 20, "solver_started": False,
                  "agenthub_chain_valid": True,
                  "summary_sha256": sha(RUN / "summary.md"),
                  "run_json_sha256": sha(RUN / "run.json"),
                  "sealed_tensile_accessed": False}
    save_once(RUN / "checkpoints/completion.json", completion)
    with (ROOT / "run/README.md").open("a", encoding="utf-8") as f:
        f.write("\n## run_033 — 20 Job DOE batch queue-only\n\n")
        f.write("| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n")
        f.write("| run_033 | I02终态、14新DOE、真实CAE、20/20预览与批量入队 | WARNING / TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_033/summary.md) |\n\n")
        f.write("20项QUEUED，等待用户在正确Project手动点击一次Start Queue；AUTO_STOP_UNAVAILABLE风险已确认。\n")
    status_path = ROOT / "status/PROJECT_STATUS.md"
    old = status_path.read_text(encoding="utf-8")
    assert old.startswith("# SMALL-PUNCH 项目状态\n")
    lead = """# SMALL-PUNCH 项目状态

## 当前状态 — run_033（2026-10-24，Asia/Shanghai）

**WARNING / TWENTY_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户新授权20项批量DOE：6份run_030冻结I03–I08及14份run_033新CAE输入；20/20 Preflight和Dry-run通过，20项按冻结顺序经公开API入队，所有Job仍为QUEUED，Runner空闲、工作目录为空。I01/I02已完成且未重复；I02身份与文件证据无阻塞冲突，数值警告待后续只读分析。AgentHub记录20项queue_id和授权，详见[run_033报告](../run/run_033/summary.md)。**AUTO_STOP_UNAVAILABLE：单Job失败后GUI Runner仍可能继续后续Job；用户已接受批量模式。** 现在等待用户在正确Project确认仅本批20项可执行，然后本人点击一次Start Queue。Codex未启动Solver/Datacheck，不执行BO/DE/RL；封存资料禁读及历史暴露事实继续保留。

"""
    status_path.write_text(lead + old[len("# SMALL-PUNCH 项目状态\n"):], encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "queue_count": 20,
                      "project_id": PID, "run_id": "run_033"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
