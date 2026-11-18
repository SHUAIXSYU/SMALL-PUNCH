"""Freeze the completed offline Run, preserving historical Runs and state."""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_030"
A = RUN / "artifacts"
P = A / "private"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def save(p, data):
    with Path(p).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    assert not (A / "prepared_batch.json").exists()
    assert not (RUN / "summary.md").exists()
    assert not (A / "manifest.json").exists()
    verification = read(P / "main_verification.json")
    acceptance = read(P / "main_cae_acceptance.json")
    design = read(A / "parameter_design.json")
    manifest = read(A / "cae_candidate_manifest.json")
    preview = read(A / "cae_preview_result.json")
    budget = read(A / "budget_protocol.json")
    run = read(RUN / "run.json")
    session = read(P / "main_session.json")
    assert run["status"] == "RUNNING"
    assert verification["status"] == "PASS_OFFLINE_PREPARATION" and verification["queue_unchanged"]
    assert acceptance["status"] == "REAL_CAE_ACCEPTED" and acceptance["verified_artifacts"] == 27
    assert preview["preflight_passed"] == preview["dry_run_passed"] == 8
    assert preview["queue_unchanged"] and preview["settings_unchanged"]
    assert budget["authorized_now"] == design["authorized_solver_jobs"] == design["authorized_enqueues"] == 0
    assert len(design["points"]) == len(manifest["points"]) == len(verification["results"]) == 8
    assert manifest["design_sha256"] == sha(A / "parameter_design.json")
    assert acceptance["cae_task_id"] == session["cae_task_id"]
    points = []
    manifest_by_id = {p["point_id"]: p for p in manifest["points"]}
    verification_by_id = {p["point_id"]: p for p in verification["results"]}
    for d in design["points"]:
        m = manifest_by_id[d["point_id"]]
        v = verification_by_id[d["point_id"]]
        assert m["sha256"] == v["inp_sha256"] == sha(ROOT / d["inp_path"])
        assert not any((ROOT / d["working_dir"]).iterdir())
        points.append({**d, "inp_sha256": m["sha256"],
                       "parameters_sha256": sha(ROOT / d["parameters_path"]),
                       "material_rows": m["material_rows"],
                       "preflight": v["preflight"], "dry_run": v["dry_run"],
                       "queue_id": None, "actual_odb": None, "solver_status": "NOT_STARTED"})
    frozen = {
        "version": "run030-shared-initial-eight-prepared-v1", "frozen_at": now(),
        "status": "PREPARED_AWAITING_EXPLICIT_SOLVER_AUTHORIZATION",
        "project_id": "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae",
        "project_path": "agenthub_sp_invopt/abqjobpilot_project",
        "main_task_id": session["main_task_id"], "cae_task_id": session["cae_task_id"],
        "design_sha256": sha(A / "parameter_design.json"),
        "model_contract_sha256": sha(A / "model_contract.json"),
        "loss_contract_binding_sha256": sha(A / "loss_contract_binding.json"),
        "budget_protocol_sha256": sha(A / "budget_protocol.json"),
        "odb_result_protocol_sha256": sha(A / "odb_result_protocol.json"),
        "source_inp_sha256": manifest["source_sha256"],
        "generator_sha256": manifest["generator_sha256"],
        "numeric_version": "run030-standard-m0025-hollomon-v1",
        "loss_version": "run017-exploratory-fd-v1",
        "points": points, "cpus": 14, "gpus": 0,
        "run_datacheck": True, "run_full": True,
        "new_enqueues": 0, "new_solver_jobs": 0,
        "future_gate": "I01-I04 human review before I05-I08; one authorized Job at a time; no automatic retry",
    }
    save(A / "prepared_batch.json", frozen)
    lines = [
        "# run_030 — 16次探索性反演离线准备",
        "",
        "**WARNING / READY_TO_REQUEST_STAGE_A_WITH_GATES。** 数值契约 `run030-standard-m0025-hollomon-v1` 冻结；run_027 中心相邻细化通过仅支持这个中心的数值设置选择，不推定全参数域稳定。run_025 历史 BLOCKED 保留。没有新入队、Datacheck、Solver 或优化执行。",
        "",
        "## 冻结设计与模型",
        "",
        "8点中4点按归一化参数域分层覆盖全域，4点围绕既有 SPT 低 Loss 区域；序列交错，先评 I01–I04。范围 σy=150–1000 MPa、n=0.02–0.50 是工程探索假设，E=210 GPa、ν=0.3。数值设置：Abaqus/Standard、初始0.001、最大0.0025、最小1e-12、总时间1、最多999999增量；14 CPU、0 GPU、Datacheck+Full。几何、网格、接触、BC、位移加载、输出及候选 Hollomon 解释沿用源模型。",
        "",
        "| 点 | 区域 | Job | σy (MPa) | n |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for p in points:
        lines.append(f"| {p['point_id']} | {p['region']} | `{p['job_name']}` | {p['sigma_y_mpa']:.9f} | {p['n']:.6f} |")
    lines += [
        "",
        "完整精度、8个输入完整 SHA-256、路径与工作目录见[冻结清单](artifacts/prepared_batch.json)。真实 CAE 会话领取、完成任务，并向 MAIN 回传；MAIN 核验27项 AgentHub 产物哈希及完成消息。8份 INP 的非材料字节与 run_027 源完全相同，塑性表覆盖0–0.9且插值误差界≤0.001，8个独立工作目录为空。",
        "",
        "## Loss、预检查与预算",
        "",
        "Loss继续用 `run017-exploratory-fd-v1`：私有 SPT 339点源中的0–1.2 mm、241点，F_ref=1428.9 N，等权归一化均方残差，线性插值且无外推/零点平移/二次校正。目标、配置及实现 SHA 再核验一致；不读取封存拉伸数据。",
        "",
        "正式 AbqJobPilot 0.2.2 Project Settings=`PERSISTED`，Abaqus 2024命令存在，14 CPU/0 GPU、两阶段开启。CAE及MAIN分别通过8/8公开API Preflight、8/8 dry-run；两次预览证据显示 Queue/Project/Settings/History未改变，且无新queue_id或Solver。预览不代表 Abaqus 语法、许可证或收敛已通过。",
        "",
        "总新增 FE 拟定上限16：共享初始8 + BO序贯4 + DE半代先导4。两算法只共享同一8点，后续各只看自身新增结果；单种子小预算不比较算法优劣。首4点完成后人工检查成功样本、Loss、补偿和警告，再决定后4点；8点完成后才审议BO/DE。任何失败、不完整覆盖、材料越表、严重接受态警告或不明运行状态都停止后续提交，Loss=null，不自动重试。详见[完整协议](artifacts/pilot_protocol.md)与[未来ODB回传格式](artifacts/odb_result_protocol.json)。",
        "",
        "中心点实测253秒/Job；规划4–20分钟/Job，仅作为范围估计。首8点32–160分钟，全部16点64–320分钟（不含等待/人工审核，不能视为保证上限）。具备**申请**最多8项首批探索性求解授权的离线工程条件，但建议先授权并逐项审核 I01–I04，再决定后四项；本轮实际授权、入队及新计算均为零。固定夹持理想化、接触/警告、仪器校正细节、参数耦合与数值域外推风险仍在，不能宣称材料本构或全局参数已验证。",
        "",
        "证据：[MAIN独立审核](artifacts/private/main_verification.json)、[真实CAE回传验收](artifacts/private/main_cae_acceptance.json)、[CAE报告](artifacts/private/cae/REPORT.md)、[预算契约](artifacts/budget_protocol.json)。六项离线契约测试通过。完成后停止，不自动进入新Run。",
    ]
    (RUN / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    run.update(status="WARNING", end_time=now(),
               outputs=[{"path": rel(p), "role": role} for p, role in [
                   (A / "prepared_batch.json", "Frozen eight inputs"),
                   (A / "parameter_design.json", "Eight-point design"),
                   (A / "model_contract.json", "Numerical/model contract"),
                   (A / "loss_contract_binding.json", "Frozen SPT Loss identity"),
                   (A / "budget_protocol.json", "16 FE pilot budget"),
                   (A / "odb_result_protocol.json", "Future ODB envelope"),
                   (RUN / "summary.md", "Report"),
                   (P / "main_verification.json", "Independent MAIN audit"),
                   (P / "main_cae_acceptance.json", "Real CAE receipt")]],
               validation=[
                   {"check": "real_cae_handoff", "status": "PASS", "scope": "27 Hub artifact hashes and actual MAIN session completion receipt"},
                   {"check": "eight_inp_static_identity", "status": "PASS", "scope": "Unique hashes, nonmaterial bytes, table and empty workdirs"},
                   {"check": "abq_preview", "status": "PASS", "scope": "8/8 preflight and dry-run; Queue and Settings unchanged"},
                   {"check": "offline_contract_tests", "status": "PASS", "scope": "Six synthetic/identity checks"},
                   {"check": "scientific_validity", "status": "WARNING", "scope": "Center-only numerical check, experiment/model uncertainties and historical information exposure"},
               ],
               errors=[])
    (RUN / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    index = ROOT / "run/README.md"
    text = index.read_text(encoding="utf-8")
    assert "## run_030" not in text
    index.write_text(text.rstrip() + "\n\n## run_030 — 16次探索性反演离线准备\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_030 | 冻结8+4+4预算、八份统一数值控制输入、真实CAE交接与公开预览 | WARNING / READY_TO_REQUEST_STAGE_A_WITH_GATES | [summary](run_030/summary.md) |\n\n未入队或求解；I01–I04 首先需新的具体授权并逐项审核。\n", encoding="utf-8")
    status = ROOT / "status/PROJECT_STATUS.md"
    text = status.read_text(encoding="utf-8")
    heading = "# SMALL-PUNCH 项目状态\n"
    assert text.startswith(heading) and "## 当前状态 — run_030" not in text
    status.write_text(heading + "\n## 当前状态 — run_030（2026-10-24，Asia/Shanghai）\n\n**WARNING / READY_TO_REQUEST_STAGE_A_WITH_GATES。** 16次先导预算与统一最大增量0.0025的数值契约已冻结，真实CAE完成8份输入，8/8 Preflight和dry-run通过；MAIN独立复核及Hub消息接收完成。拟先逐项审核I01–I04，再判断I05–I08；BO/DE剩余8次尚待初批结果。当前入队/新Solver授权均0，历史run_025 BLOCKED保留，中心通过不证明参数域稳定。见[run_030报告](../run/run_030/summary.md)。完成后停止。\n\n" + text[len(heading):], encoding="utf-8")
    paths = [A / "prepared_batch.json", A / "parameter_design.json", A / "model_contract.json",
             A / "loss_contract_binding.json", A / "budget_protocol.json", A / "odb_result_protocol.json",
             A / "pilot_protocol.md", A / "test_offline_contract.py", A / "verify_prepared.py",
             P / "main_verification.json", P / "main_cae_acceptance.json", P / "cae/REPORT.md",
             A / "cae_candidate_manifest.json", A / "cae_preview_result.json", RUN / "summary.md", RUN / "run.json"]
    file_manifest = {"at": now(), "status": "WARNING", "files": [
        {"path": rel(p), "sha256": sha(p), "private": p.is_relative_to(P)} for p in paths]}
    save(A / "manifest.json", file_manifest)
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    assert hub.task(session["cae_task_id"])["execution_state"] == "COMPLETED"
    hub.heartbeat(session["lease"])
    for path in paths + [A / "manifest.json"]:
        hub.artifact(session["main_task_id"], session["identity"]["agent_id"], path,
                     {"run": "run_030", "scope": "offline preparation, no new FE"}, version="run030-v1")
    result = {"status": "READY_TO_REQUEST_STAGE_A_WITH_GATES", "cae_task_id": session["cae_task_id"],
              "prepared_points": 8, "preflight_passed": 8, "dry_run_passed": 8,
              "new_solver_jobs": 0, "new_enqueues": 0,
              "batch_manifest": rel(A / "prepared_batch.json"),
              "historical_run025_blocked_unchanged": True}
    hub.message(session["main_task_id"], session["identity"]["agent_id"], "MAIN", result,
                "run030-main-completion-v1")
    hub.finish(session["lease"], result, evidence_state="RECORDED", science_state="WARNING")
    assert hub.verify_chain()
    save(RUN / "checkpoints/completion.json", {"at": now(), "status": result["status"],
         "main_task_id": session["main_task_id"], "cae_task_id": session["cae_task_id"],
         "prepared_batch_sha256": sha(A / "prepared_batch.json"),
         "manifest_sha256": sha(A / "manifest.json"), "hub_chain_valid": True,
         "new_enqueues": 0, "new_solver_jobs": 0})
    print(json.dumps({"status": result["status"], "points": 8,
                      "cae_task_id": session["cae_task_id"], "manifest_sha256": sha(A / "prepared_batch.json")}))


if __name__ == "__main__":
    main()
