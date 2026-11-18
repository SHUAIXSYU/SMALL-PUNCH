"""Finalize the offline run and register MAIN evidence through the public Hub API."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_027"
ART = RUN / "artifacts"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now().astimezone().isoformat()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    main_id = load(ART / "private/main_identity.json")["identity"]
    cae_id = load(ART / "cae_task.json")["task_id"]
    cae = hub.task(cae_id)
    assert cae and cae["execution_state"] == "COMPLETED" and cae["evidence_state"] == "RECORDED"
    assert cae["science_state"] == "NOT_EVALUATED"
    messages = hub.poll_messages(main_id)
    actual_cae = [m for m in messages if m["task_id"] == cae_id and m["sender"].startswith("CAE:")]
    assert actual_cae, "Real CAE completion message not delivered to MAIN session"
    assert hub.verify_chain()

    preview = load(ART / "preview_result.json")
    byte = load(ART / "private/independent_byte_audit.json")
    tests = load(ART / "comparison_test_result.json")
    contract = load(ART / "comparison_contract.json")
    cae_manifest = load(ART / "cae_candidate_manifest.json")
    assert preview["status"] == "PASS_PREVIEW_ONLY" and tests["status"] == "PASS_OFFLINE_TESTS_ONLY"
    assert preview["candidate_sha256"] == byte["candidate_sha256"] == cae_manifest["sha256"]
    assert preview["comparison_contract_sha256"] == sha(ART / "comparison_contract.json")
    assert preview["queue_unchanged"] and not preview["solver_started"] and not preview["datacheck_started"]
    assert preview["runner_owner"] == "ABSENT" and preview["recovery_status"] == "CLEAN"
    assert contract["new_solver_authorization"] is False and contract["enqueue_authorization"] is False
    inp = Path(preview["candidate_inp"])
    assert inp.is_file() and sha(inp) == preview["candidate_sha256"]
    workdir = Path(preview["working_dir"])
    assert workdir.is_dir() and not any(workdir.iterdir())
    settings = load(ART / "private/abq_preview_evidence.json")["settings"]["settings_response"]
    assert settings["status"] == "PERSISTED"
    assert settings["project_id"] == preview["project_id"]
    settings_values = settings["effective_settings"]
    assert settings_values["default_cpus"] == 14 and settings_values["default_gpus"] == 0
    assert settings_values["run_datacheck"] and settings_values["run_full"]

    prepared = {
        "schema": "sp_invopt.single_center_refinement_prepared.v1",
        "run_id": "run_027",
        "cae_task_id": cae_id,
        "job_name": preview["job_name"],
        "source_inp_absolute": byte["source_inp"],
        "source_sha256": byte["source_sha256"],
        "candidate_inp_absolute": preview["candidate_inp"],
        "candidate_sha256": preview["candidate_sha256"],
        "working_dir_absolute": preview["working_dir"],
        "parameters": {"sigma_y_mpa": 200, "n": 0.1, "E_pa": 210000000000, "nu": 0.3},
        "only_input_change": {"keyword": "*Static", "line_one_based": 1468,
                              "before": byte["old_static_line"], "after": byte["new_static_line"]},
        "project_id": preview["project_id"],
        "settings_status": settings["status"],
        "preflight": preview["preflight"],
        "dry_run": preview["dry_run"],
        "comparison_contract": rel(ART / "comparison_contract.json"),
        "comparison_contract_sha256": preview["comparison_contract_sha256"],
        "queue_id": None, "enqueue_authorized": False, "solver_authorized": False,
        "solver_state": "NOT_STARTED", "scientific_qualification": "NOT_EVALUATED"
    }
    dump(ART / "prepared_candidate.json", prepared)

    summary = f"""# run_027 — 单一中心点进一步增量细化准备

**状态：WARNING（离线准备完成，数值资格待求解）。** run_025 的 `BLOCKED_V01_NUMERICAL_QUALIFICATION` 原结论不变。无入队、Datacheck 或 Solver；V02 仍不可执行。

## 唯一输入与真实 CAE 交接

MAIN 通过 AgentHub 将任务 `{cae_id}` 交给真实独立 CAE Codex 会话。CAE 领取、生成、核对、登记证据并回传完成消息；MAIN 会话已实际领取该消息。源 V01 INP：`{rel(Path(byte['source_inp']))}`，SHA-256 `{byte['source_sha256']}`。候选 Job `SPIO_R027_CTR_M0025`：`{rel(inp)}`，完整 SHA-256 `{sha(inp)}`；工作目录 `{rel(workdir)}` 当前为空。独立逐字节复核证明仅第 1468 行 `*Static` 的最大增量 `0.005 → 0.0025`，其余字节完全一致，无 INCLUDE 或外部模型引用。材料参数仍为 σy=200 MPa、n=0.1、E=210 GPa、ν=0.3；初始增量0.001，总时间1，最小增量1e-12，最大增量次数999999。

## 求解前冻结比较协议

`run027-adjacent-refinement-v1`，SHA-256 `{sha(ART / 'comparison_contract.json')}`。主要比较新候选与 V01；run_014 仅辅助观察趋势。固定 `run017-exploratory-fd-v1`、0–1.2 mm、241 个实验位移点、`u=-U2`、`F=-RF2`、线性插值、不外推、不平滑、不删点、不平移零点或再次柔度校正。预设工程门槛：RMSE≤2 N，最大绝对差≤7.1445 N，最大正则相对差≤5%（分母下限71.445 N），绝对 Loss 差≤0.00065，最大保存帧 PEEQ 差≤0.02。先核查 Job/ODB 身份、完整窗口、材料表覆盖及已接受帧警告。局部 1.10–1.16 mm 原始接受帧、节点23及拓扑相邻接触区域 CPRESS/COPEN、cutback/接触事件只作诊断，不替代全窗口门槛。COPEN 哨兵或缺失值不当作实际开口。

直接复用已测试比较实现 `run/run_023/artifacts/compare_validation.py`（SHA-256 `{contract['comparison_implementation_sha256']}`）和 Loss 实现 `inverse/fd_loss.py`（SHA-256 `{contract['loss_implementation_sha256']}`）。12 项单元测试通过；V01 自比较为零差；原 run_014 对 V01 的 RMSE 3.998775 N、最大差19.558201 N 得以复现。这些测试均未评价新候选的数值结果。

## AbqJobPilot 只读预览

本机稳定版 0.2.2，正式 Project `{preview['project_id']}`。严格 Settings=`PERSISTED`，Abaqus 2024 命令文件存在，14 CPU、0 GPU、Datacheck 和 Full Analysis 开启。公开 API `preflight`=`{preview['preflight']}`，`enqueue(dry_run=True)`=`{preview['dry_run']}`；Project/Queue/Settings/历史记录在调用前后不变。Runner owner=`ABSENT`、recovery=`CLEAN`，新工作目录无冲突。预览不等于 Abaqus 语法、许可证或收敛检查；无 queue_id、无新 ODB。

## 停止与后续授权

本 Run 到候选准备即止。申请仅此一个新 Job 时，须明确绑定候选完整 SHA、Job 名、Project ID、工作目录、14 CPU/0 GPU、单次 Datacheck+Full Analysis、零自动重试，并重新检查 Queue/Runner/输出冲突；用户负责 GUI 手动 Start Queue。未取得新授权前不得入队或求解。V02 的未使用额度不得转给本候选。未来若该相邻细化通过，仅可判定本中心点增量细化；使用新设置优化须单独冻结数值契约，历史粗设置结果须标识精度来源。

证据入口：`artifacts/prepared_candidate.json`、`artifacts/cae_candidate_manifest.json`、`artifacts/comparison_contract.json`、`artifacts/comparison_test_result.json`、`artifacts/preview_result.json`；字节、Settings、Queue 和 CAE 会话证据在 Git 忽略的 `artifacts/private/`。
"""
    (RUN / "summary.md").write_text(summary, encoding="utf-8")
    run = load(RUN / "run.json")
    run["status"] = "WARNING"
    run["end_time"] = now()
    run["outputs"] = [{"path": rel(p), "sha256": sha(p)} for p in (
        inp, ART / "prepared_candidate.json", ART / "comparison_contract.json",
        ART / "comparison_test_result.json", ART / "preview_result.json", RUN / "summary.md")]
    run["validation"] = [
        {"check": "real_cae_handoff", "status": "PASS", "scope": "separate CAE chat claimed, completed, sent Hub evidence; MAIN received completion"},
        {"check": "single_byte_change", "status": "PASS", "scope": "only *Static maximum increment 0.005 to 0.0025"},
        {"check": "comparison_offline_tests", "status": "PASS", "scope": "12 unit tests and historical metric reproduction"},
        {"check": "abqjobpilot_preview", "status": "PASS", "scope": "PERSISTED settings, preflight, dry-run, no mutations"},
        {"check": "numerical_accuracy", "status": "NOT_EVALUATED", "scope": "new candidate not solved; run025 BLOCKED remains"},
    ]
    dump(RUN / "run.json", run)

    index = ROOT / "run/README.md"
    index_text = index.read_text(encoding="utf-8")
    assert "## run_027" not in index_text
    index.write_text(index_text.rstrip() + "\n\n## run_027 — 单一中心点增量细化准备\n\n"
                     "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                     "| run_027 | 真实CAE单候选、冻结相邻细化比较、公开API预览 | WARNING（离线准备完成） | [summary](run_027/summary.md) |\n\n"
                     "未入队或求解；run_025数值资格仍BLOCKED，V02不可执行，停止等待新授权。\n", encoding="utf-8")
    status_path = ROOT / "status/PROJECT_STATUS.md"
    status_text = status_path.read_text(encoding="utf-8")
    assert "## 当前状态 — run_027" not in status_text
    status_path.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n", "# SMALL-PUNCH 项目状态\n\n"
        "## 当前状态 — run_027（2026-10-24，Asia/Shanghai）\n\n"
        "**WARNING：唯一中心点增量细化候选已准备，尚未获准入队或求解。** 真实CAE会话完成候选与字节核验；最大增量仅由0.005改为0.0025。冻结的相邻比较协议、12项离线测试及AbqJobPilot公开Preflight/Dry-run通过，Queue保持不变。run_025数值资格BLOCKED保留；V02不可执行。见[run_027报告](../run/run_027/summary.md)。停止等待唯一新Job授权。\n\n", 1), encoding="utf-8")

    task = hub.create_task(main_id["agent_id"], "MAIN", "single_center_refinement_review",
                           {"run": "run_027", "cae_task_id": cae_id, "job_name": preview["job_name"],
                            "candidate_sha256": preview["candidate_sha256"], "decision": "OFFLINE_PREPARED_ONLY",
                            "enqueue_authorized": False, "solver_authorized": False},
                           "run027-main-offline-review-v1", depends=(cae_id,))
    lease = hub.claim(task["task_id"], main_id, "run027-main-review-claim-v1")
    (ART / "private/main_review_lease.json").write_text(json.dumps(lease, indent=2) + "\n", encoding="utf-8")
    artifacts = [ART / "prepared_candidate.json", ART / "comparison_contract.json",
                 ART / "comparison_test_result.json", ART / "preview_result.json",
                 ART / "private/independent_byte_audit.json", ART / "private/abq_preview_evidence.json",
                 RUN / "summary.md", RUN / "run.json"]
    receipts = []
    for p in artifacts:
        item = hub.artifact(task["task_id"], main_id["agent_id"], p,
                            {"run": "run_027", "method": "MAIN offline independent verification",
                             "source_cae_task_id": cae_id, "no_solver": True}, version="run027-preparation-v1")
        receipts.append({"path": rel(p), "sha256": item["sha256"], "artifact_id": item["artifact_id"]})
    hub.finish(lease, {"decision": "WARNING_OFFLINE_PREPARED_ONLY", "candidate_sha256": sha(inp),
                       "preflight": preview["preflight"], "dry_run": preview["dry_run"],
                       "queue_id": None, "solver_started": False, "run025_blocked_preserved": True},
               evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    receipt = {"at": now(), "cae_task_id": cae_id, "main_task_id": task["task_id"],
               "received_cae_message_ids": [m["message_id"] for m in actual_cae],
               "registered_artifacts": receipts, "audit_chain_valid": True,
               "candidate_sha256": sha(inp)}
    dump(ART / "private/main_agenthub_receipt.json", receipt)
    dump(RUN / "checkpoints/completion.json", {"at": now(), "status": "WARNING_OFFLINE_PREPARED_ONLY",
                                              "cae_task_id": cae_id, "main_task_id": task["task_id"],
                                              "candidate_sha256": sha(inp), "queue_id": None})
    print(json.dumps({"status": "WARNING_OFFLINE_PREPARED_ONLY", "main_task_id": task["task_id"],
                      "candidate_sha256": sha(inp), "hub_chain": True}))


if __name__ == "__main__":
    main()
