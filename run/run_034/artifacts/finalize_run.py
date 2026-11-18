"""Finalize run_034 MAIN evidence and AgentHub review without new FE execution."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_034"
MAIN = RUN / "artifacts/private/main"
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    j = read(MAIN / "main_review.json")
    assert j["independent_loss_recalculated_count"] == 17
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=14400)
    ids = read(RUN / "artifacts/task_ids.json")
    identity = read(RUN / "artifacts/private/main_session.json")["identity"]
    odb_task = hub.task(ids["odb_task_id"])
    assert odb_task is not None and odb_task["execution_state"] == "COMPLETED"
    received = hub.poll_messages(identity)
    assert any(m["task_id"] == ids["odb_task_id"] for m in received), "Real ODB handoff message missing"
    assert hub.verify_chain()
    best = j["best_evaluated"]
    rows = j["rows"]
    ordered = sorted((r for r in rows if r["loss"] is not None), key=lambda r:r["loss"])
    table = ["| ID | 来源 | σy MPa | n | Loss | RMSE N | cutback | PEEQ | 状态 |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in rows:
        def fmt(x, digits=6):
            return "—" if x is None else f"{x:.{digits}g}"
        table.append("| {point_id} | {region} | {sy} | {n} | {loss} | {rmse} | {cutback} | {peeq} | {status} |".format(
            point_id=r["point_id"], region=r["region"], sy=fmt(r["sigma_y_mpa"],9),
            n=fmt(r["n"],8), loss=fmt(r["loss"],9), rmse=fmt(r["rmse_n"],7),
            cutback=fmt(r["cutback"],0), peeq=fmt(r["max_saved_peeq"],6),
            status="PROVISIONAL" if r["loss"] is not None else r["score_status"]))
    report = f"""# run_034 MAIN 审核：20 Job DOE 真实结果

## 证据与状态

- 公开 AbqJobPilot API 显示20项均已开始一次；19项 Datacheck 与 Full Analysis 正常结束，D09 为 `UNKNOWN_INTERRUPTED`，仅能确认 Datacheck PASS，Full 终态不明且 `.lck` 存在。不得将 D09 ODB 文件存在当作成功，也不得清锁、恢复或重试。
- 真实 ODB Codex 会话领取 AgentHub task `{ids['odb_task_id']}`，19项通过二次只读准入并提取；MAIN 收到持久化消息，复核 ODB 清单中297项产物 SHA-256，独立复算17项固定 Loss，误差均小于1e-12。
- D10 已完成求解，但 0.0042–0.0069 mm 已接受尝试中有 `LARGE_STRAIN_INCREMENT` 警告，按冻结数值门槛 Loss=null。D07 在最后0.00031886 mm 位移中有 −0.00030518 N 的已接受帧反力回落，ODB 门槛保守置 null；该幅度很小，尚不能确定机制，不追溯改写 ODB 结论。D09 同样 Loss=null。
- 17项为 `run017-exploratory-fd-v1` 的探索性 PROVISIONAL Loss，不等于正式材料拟合或物理验证。全部采用原0–1.2 mm的241点、F_ref=1428.9 N、线性插值、原符号与零点，不平滑、删点、裁窗或外推。

## 逐项结果

{chr(10).join(table)}

## 地形与参数耦合

- 最低已评估点是 {best['point_id']}：σy={best['sigma_y_mpa']:.12g} MPa，n={best['n']:.12g}，Loss={best['loss']:.12g}，RMSE={best['rmse_n']:.6g} N，NRMSE={best['nrmse']:.6g}。第二名 {ordered[1]['point_id']}：Loss={ordered[1]['loss']:.12g}。这是20点设计中的已评分比较，并非连续参数空间全局最优。
- 描述性阈值 Loss≤0.01 下有 {j['low_loss_count']} 点（{', '.join(j['low_loss_points'])}），σy={j['low_loss_sigma_range_mpa'][0]:.3f}–{j['low_loss_sigma_range_mpa'][1]:.3f} MPa，n={j['low_loss_n_range'][0]:.4f}–{j['low_loss_n_range'][1]:.4f}。这五点归一化坐标相关系数为 {j['low_loss_normalized_xy_pearson']:.3f}，显示有限样本中的参数补偿方向。低 Loss 点的挑选本身会造成相关，不能当作置信区间、全局可识别性结论或真实材料范围。
- GLOBAL 的9个有效评分中位数 {j['region_summary']['GLOBAL']['median_loss']:.6g}；LOCAL 的8个为 {j['region_summary']['LOCAL']['median_loss']:.6g}。D01 在全域近 σy 下边界也取得最低 Loss，说明局部高密度设计没有圈定唯一盆地；图中只标真实计算散点，不使用插值地形冒充 FE 真值。
- 19项已完成求解的时长总计 {j['totals']['runtime_s_completed_sum']} s（单项中位 {j['totals']['runtime_s_completed_median']:.0f} s）；14 CPU 配额折算 {j['totals']['allocated_cpu_hours_14cpus']:.3f} 核时，这不是实测 CPU 利用率。cutback 0–25；最大保存帧 PEEQ {j['totals']['max_saved_peeq_min_max'][0]:.4f}–{j['totals']['max_saved_peeq_min_max'][1]:.4f}，均低于本构表末0.9，不能代表未保存试算最大值。
- 成功项普遍保留 Abaqus 零力矩及 DAT 接触跟踪提示；单个返回码0不自动等于数值或物理充分性。D10 的接受态大应变警告必须单独处理，D07 的极小末帧反力回落与局部接触变化应离线审查。

## 科研决定

现有17点可用于**离线**低 Loss 区域、数值风险与代理模型可行性诊断。暂不建议直接申请新的 BO/DE FE 批次：先通过公开 Runner/History 证据澄清 D09 的中断终态、离线审查 D10 警告和 D07 保守拦截；不自动恢复、重试、清锁或追加求解。若这些问题解决，可另行设计受限序贯搜索并申请具体新 FE 授权。参数补偿、理想夹持、仪器校正细节及隐藏拉伸数据隔离仍限制正式本构识别。

私有证据：`run/run_034/artifacts/private/odb/` 与 `run/run_034/artifacts/private/main/`。`fd_overlay.png` 显示实验与17条真实 FE 曲线；`parameter_loss_scatter.png` 为真实已计算散点；`loss_rank.png` 为评分排序。原实验和封存拉伸源未被修改或访问。历史信息暴露声明保留，不称完全盲测。无新增 Solver、Datacheck、入队、重试、BO/DE/RL 或 Git 提交。
"""
    (MAIN / "REPORT.md").write_text(report, encoding="utf-8")
    summary = f"""# run_034 — 20项 DOE 实际结果审计

**WARNING / MAIN_REVIEW_COMPLETE_WITH_THREE_UNSCORED。** AbqJobPilot 公开证据显示20项均已尝试一次；19项求解完成，D09 为 UNKNOWN_INTERRUPTED、Full 终态不明且 `.lck` 存在。真实 ODB Agent 只读提取19项；17项按冻结 Loss 评分，D07/D10/D09 保持 null。

最低已评估点 D01：σy={best['sigma_y_mpa']:.9g} MPa，n={best['n']:.9g}，探索性 Loss={best['loss']:.10g}、RMSE={best['rmse_n']:.4f} N。五个 Loss≤0.01 的点分布在不同参数位置，提示 SPT 曲线参数补偿；不证明唯一材料参数。D10 有已接受尝试中的大应变警告；D07 有极小末帧反力回落，保守不评分。全部原始来源、逐项评分与图表保存在 Git 忽略的[私有报告](artifacts/private/main/REPORT.md)及[逐项表](artifacts/private/main/review_table.csv)。

目前建议先离线澄清 D09 终态及 D10/D07 数值证据，再讨论新的受限 BO/DE FE 授权。既有 run_025 BLOCKED 与盲测历史暴露结论不变；未执行任何新增求解、入队、重试、优化或解盲。
"""
    (RUN / "summary.md").write_text(summary, encoding="utf-8")
    evidence = [RUN / "artifacts/execution_summary.json", RUN / "artifacts/private/execution_audit.json",
                RUN / "artifacts/private/odb/manifest.json", RUN / "artifacts/private/odb/batch_summary.json",
                RUN / "artifacts/private/odb/batch_results.csv", MAIN / "main_review.json",
                MAIN / "review_table.csv", MAIN / "REPORT.md", MAIN / "fd_overlay.png",
                MAIN / "parameter_loss_scatter.png", MAIN / "loss_rank.png", RUN / "summary.md"]
    manifest = {"version": "run034-main-evidence-v1", "created_at": datetime.now().astimezone().isoformat(),
                "files": [{"path": rel(p), "sha256": sha(p), "bytes": p.stat().st_size} for p in evidence]}
    save(MAIN / "evidence_manifest.json", manifest)
    review_id = ids["review_task_id"]
    review_task = hub.task(review_id)
    if review_task["execution_state"] == "PENDING":
        lease = hub.claim(review_id, identity, "run034-main-review-claim-v1")
        save(RUN / "artifacts/private/main_lease.json", lease)
        for path in (MAIN / "main_review.json", MAIN / "REPORT.md", MAIN / "evidence_manifest.json",
                     MAIN / "fd_overlay.png", MAIN / "parameter_loss_scatter.png"):
            hub.artifact(review_id, identity["agent_id"], path,
                         {"run": "run_034", "source": "MAIN independent verification", "odb_task_id": ids["odb_task_id"]},
                         version="run034-main-v1")
        result = {"status": "MAIN_REVIEW_COMPLETE_WITH_THREE_UNSCORED", "scored": 17,
                  "null": ["D09", "D10", "D07"], "best_evaluated": best["point_id"],
                  "best_loss": best["loss"], "report": rel(MAIN / "REPORT.md"),
                  "report_sha256": sha(MAIN / "REPORT.md"),
                  "new_solver_datacheck_enqueue_retry": False,
                  "science": "EXPLORATORY_PROVISIONAL; BO_DE_NEW_FE_NOT_ADMITTED"}
        hub.finish(lease, result, evidence_state="RECORDED", science_state="WARNING")
    else:
        assert review_task["execution_state"] == "COMPLETED"
    assert hub.verify_chain()
    run = read(RUN / "run.json")
    run["status"] = "WARNING"
    run["end_time"] = datetime.now().astimezone().isoformat()
    run["outputs"] = [{"path": item["path"], "sha256": item["sha256"]} for item in manifest["files"]]
    run["outputs"].append({"path": rel(MAIN / "evidence_manifest.json"), "sha256": sha(MAIN / "evidence_manifest.json")})
    run["validation"] = [
        {"check": "public_execution_identity_and_terminal_audit", "status": "WARNING", "scope": "19 completed; D09 UNKNOWN_INTERRUPTED"},
        {"check": "real_ODB_AgentHub_delivery", "status": "PASS", "scope": "19 read-only ODBs; task completed and MAIN message received"},
        {"check": "frozen_loss_independent_recalculation", "status": "PASS", "scope": "17 of 17 scored curves; 241 fixed points; <1e-12 difference"},
        {"check": "numerical_evidence", "status": "WARNING", "scope": "D10 accepted large strain; D07 tiny accepted force decrease; both null"},
        {"check": "agenthub_audit_chain", "status": "PASS", "scope": "Verified after MAIN task completion"},
        {"check": "sealed_tensile_access", "status": "PASS", "scope": "No access in this Run; historic exposure retained"},
    ]
    run["errors"] = [{"code": "UNKNOWN_INTERRUPTED_D09", "detail": "Datacheck PASS only; Full terminal state unknown and .lck exists; no ODB read or retry"}]
    save(RUN / "run.json", run)
    save(RUN / "checkpoints/completed.json", {"at": run["end_time"], "status": run["status"],
                                                    "main_task_id": review_id, "odb_task_id": ids["odb_task_id"],
                                                    "evidence_manifest_sha256": sha(MAIN / "evidence_manifest.json")})
    index = ROOT / "run/README.md"
    index_text = index.read_text(encoding="utf-8")
    if "## run_034 — 20项 DOE 真实结果审计" not in index_text:
        index.write_text(index_text.rstrip() + "\n\n## run_034 — 20项 DOE 真实结果审计\n\n"
                         "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                         "| run_034 | 20项真实执行审计、真实ODB交接、冻结Loss及DOE地形 | WARNING / 17 scored, 3 null | [summary](run_034/summary.md) |\n\n"
                         "19项软件完成，D09中断状态不明；D07/D10数值警告保守不评分。无新求解或优化。\n", encoding="utf-8")
    status = ROOT / "status/PROJECT_STATUS.md"
    status_text = status.read_text(encoding="utf-8")
    block = """## 当前状态 — run_034（2026-10-25，Asia/Shanghai）

**WARNING / MAIN_REVIEW_COMPLETE_WITH_THREE_UNSCORED。** 20项批次均有一次执行尝试，19项软件完成且真实ODB Agent只读提取；17项按冻结SPT Loss得到探索性PROVISIONAL评分。D09为UNKNOWN_INTERRUPTED并有锁文件，D10存在接受态大应变警告，D07存在极小末帧反力回落，三项Loss=null。最低已评估点D01（σy≈152.309 MPa，n≈0.23066，Loss≈0.00050616）。有限点呈参数补偿，不证明全局最优或本构唯一性；暂缓新BO/DE FE，先澄清D09终态并离线审查数值例外。见[run_034报告](../run/run_034/summary.md)。未新增Solver、Datacheck、入队或重试；历史run_025 BLOCKED、封存资料禁读及既有信息暴露声明保留。完成后停止。

"""
    if "## 当前状态 — run_034" not in status_text:
        assert status_text.startswith("# SMALL-PUNCH 项目状态\n")
        status.write_text(status_text.replace("# SMALL-PUNCH 项目状态\n\n", "# SMALL-PUNCH 项目状态\n\n" + block, 1), encoding="utf-8")
    print(json.dumps({"status": run["status"], "review_task_id": review_id,
                      "odb_task_id": ids["odb_task_id"], "scored": 17, "null": 3,
                      "best": best["point_id"], "run": rel(RUN / "summary.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
