"""Close run_039 after real ODB handoff and independent MAIN evidence review."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_039"
MAIN = RUN / "artifacts/private/main"
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def now():
    return datetime.now().astimezone().isoformat()


def main():
    j=read(MAIN/"main_review.json")
    assert j["independent_loss_recalculated"]==19
    ids=read(RUN/"artifacts/task_ids.json")
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    assert hub.task(ids["odb_task_id"])["execution_state"]=="COMPLETED"
    identity=ids["main_identity"]
    received=hub.poll_messages(identity)
    assert any(m["task_id"]==ids["odb_task_id"] for m in received),"Real ODB handoff not received by MAIN session"
    assert hub.verify_chain()
    top=j["top_five"]
    top_table="\n".join(
        f"| {r['point_id']} | {r['sigma_y_mpa']:.9f} | {r['n']:.9f} | {r['loss']:.9g} | {r['rmse_n']:.3f} | {r['cutback']} | {r['numerical_quality']} |"
        for r in top)
    rows=j["rows"]
    full_table="\n".join(
        f"| {r['point_id']} | {r['sigma_y_mpa']:.9f} | {r['n']:.9f} | "
        f"{('null' if r['loss'] is None else format(r['loss'],'.9g'))} | "
        f"{('—' if r['rmse_n'] is None else format(r['rmse_n'],'.3f'))} | "
        f"{r['runtime_s']} | {r['cutback']} | {r['max_saved_peeq']:.6f} | {r['numerical_quality']} |"
        for r in rows)
    report=f"""# run_039 — 20 Job DOE 实际审计与探索性优化准入

## 执行身份与审计

- 正式 Project ID 为 `{j['project_id']}`。AbqJobPilot 公开 API 回读 run_033 原20项：19项 Datacheck 与 Full Analysis 软件完成（均为 `COMPLETED_WITH_WARNINGS`），没有确认的求解失败；原 D09 为 `UNKNOWN_INTERRUPTED`，不能记作成功，也没有可信原始 Loss。它的旧 ODB 未打开、未哈希、未评分。
- D09 的 run_035 第一次独立重试仍为 UNKNOWN。run_038 的第二次独立重试是另一个 Job/queue_id，软件完成，但 ODB 数值证据有2次接受态大应变警告及接受帧反力回落，因此冻结数值准入下 Loss=null。原批次19/20软件完成的历史结论不改写。22个不同参数点中有22个软件完成的某次结果，其中19个可按冻结协议做**探索性 PROVISIONAL**评分，3个因数值问题不评分。
- 真实 ODB Codex 会话通过 AgentHub 领取任务 `{ids['odb_task_id']}`，复核既有19项及I01来源与哈希，以 Abaqus 2024 Python只读提取I02和独立D09替代项，回传22点表及45项新证据的SHA-256清单。MAIN会话实际领取了持久化消息，逐项核验清单并独立重算19个固定Loss，差异均小于1e-12。
- I01/I02与本批共享 `run030-standard-m0025-hollomon-v1` 数值契约及 `run017-exploratory-fd-v1` Loss。I01/I02没有重复求解。旧run_014/run_022采用不同增量控制，未混入这22点同精度表。原20项公开执行状态与22点参数表分别保存，D09替代来源有明确标识。

## 冻结目标与数值质量

SPT原实验目标只用0–1.2 mm的241个既定点，位移m、载荷N，`F_ref=1428.9 N`。Loss=241点上等权 `mean(((F_FE-F_exp)/F_ref)^2)`；线性插值，无零点移动、平滑、外推、裁窗或候选专属权重。`RMSE=F_ref*sqrt(Loss)`，因此Loss不直接是百分比误差。标记PROVISIONAL，因为实验校正细节和夹具等效性尚未独立验证；保留拉伸验证集既往信息暴露声明，此Run没有读取封存文件。

三项数值阻塞：D07末帧极小已接受反力回落（幅度约0.000305 N，成因未确认）；D10接受态大应变增量警告；D09替代项接受态大应变警告及接受反力回落。它们的ODB存在且软件终态不能替代数值资格。其余评分点也只记为数值审查后**WARNING/PROVISIONAL**，常见零力矩/接触跟踪提示保留，不能推导物理正确。22项已完成尝试的cutback范围{j['totals']['cutback_range'][0]}–{j['totals']['cutback_range'][1]}，最大保存帧PEEQ范围{j['totals']['saved_peeq_range'][0]:.6f}–{j['totals']['saved_peeq_range'][1]:.6f}，低于材料表末端0.9；不代表被拒绝试算的峰值。累计可归属的完成计算时长{j['totals']['runtime_sum_22_completed_s']}s，单次中位{j['totals']['runtime_median_s']}s；14 CPU配额折算{j['totals']['allocated_cpu_hours_14']:.3f}核时，不是实测利用率。

### 已评分最佳五点

| ID | σy MPa | n | Loss | RMSE N | cutback | 数值质量 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{top_table}

### 22点全表

| ID | σy MPa | n | Loss | RMSE N | 耗时 s | cutback | PEEQ | 数值质量 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{full_table}

## 参数空间、补偿与可识别性

- 最低**已计算且通过当前数值评分门槛**的是D01：σy={top[0]['sigma_y_mpa']:.12g} MPa、n={top[0]['n']:.12g}、Loss={top[0]['loss']:.12g}、RMSE={top[0]['rmse_n']:.4f} N。D01接近探索边界150 MPa，不证明边界外更优，也不支持未经授权拓展范围。
- 描述性 `Loss≤0.01` 五点是{', '.join(j['low_loss_point_ids'])}，归一化参数x与y相关系数{j['low_loss_normalized_xy_pearson']:.6f}。这些经过Loss选择的稀疏点沿负斜率方向分布，提示σy与n补偿。D01和I08的参数位置不同且Loss接近；五点FE曲线之间仍可有数十牛顿差，故“相近Loss”不等于“完全相同曲线”或唯一低Loss连续谷地。run_022先前中心敏感性余弦约0.990176、条件数约15.1276，使用较粗增量控制，仅作为不同数值契约的佐证，不与本批Jacobian等同。
- 0–0.4、0.4–0.8、0.8–1.2 mm三个窗口中，五条低Loss曲线的描述性均方根离散分别约{j['displacement_interval_diagnostics'][0]['low_loss_curve_spread_rms_n']:.1f}、{j['displacement_interval_diagnostics'][1]['low_loss_curve_spread_rms_n']:.1f}、{j['displacement_interval_diagnostics'][2]['low_loss_curve_spread_rms_n']:.1f} N。后段绝对载荷差较大，但也伴随接触演化；不能单凭此改动冻结Loss窗口。
- GLOBAL有效评分{j['region_summary']['GLOBAL']['scored']}个，中位Loss={j['region_summary']['GLOBAL']['median_loss']:.6g}；LOCAL有效评分{j['region_summary']['LOCAL']['scored']}个，中位Loss={j['region_summary']['LOCAL']['median_loss']:.6g}。抽样设计不同，不能把中位数差当成算法优越性。

## BO/DE 准入与下一批方案

**WARNING：可申请受限的探索性优化，不可称正式材料参数反演。** 19个可比较高保真样本足以构造初步surrogate、已有低误差位置；但D07/D09/D10数值拦截、近150 MPa边界的最佳点、参数补偿、实验校正与理想夹持模型误差限制结论。取得新授权前不提出任何新的FE计算，不把有null Loss的点作零值或任意惩罚拟合。

建议新增上限16次FE，分两个4+4关口：第一关BO 4次、DE 4次，完成数值审核后再决定是否使用第二关BO 4次、DE 4次。两算法起点共享相同的19个有效、同契约的DOE评价；3个无效点作为数值不可用位置记录，不作目标训练。各分支只看共同初始集及自己随后新增的结果；先固定随机种子、去重距离、候选规则和成本口径。BO以归一化参数、log1p(Loss)、带ARD的Matérn-5/2 GP和预设的Expected Improvement序贯提议，每次只用已验收结果更新；保留边界与空间覆盖探索，避免代理模型过度自信。DE以共享数据中按预先规则选出的8个不同初始个体组建种群，其余共享点保留为可见历史档案；预设种群8、固定变异/交叉参数和种子，最多8个新增试验向量（约一代），不因失败静默补点。两分支每新增一个FE均消耗预算，失败/不可信结果保留null并触发审核；同一FE点不得两次计入比较预算。比较只报告相同新增FE次数下的已评估最佳Loss与耗时，16次先导不足以断言算法优劣。

关口停止：Datacheck/Full失败、身份不明、窗口不覆盖、PEEQ表外、重复严重接受态警告、局部接触/载荷异常影响评分，或可评分比例明显下降时暂停后续入队；不得自动重试或改变数值/实验契约。下一批所有新计算需另行明确授权、独立INP和输出目录。

## 私有证据

公开执行审计：`run/run_039/artifacts/private/execution_audit.json`；真实ODB回传及45项SHA-256清单：`run/run_039/artifacts/private/odb/`；MAIN独立审计、22点数据表与五幅图：`run/run_039/artifacts/private/main/`。图中散点均为实际FE点，没有将插值曲面冒充真实Loss。所有可恢复实验曲线留在Git忽略目录。未启动新Solver、Datacheck、入队、重试、BO/DE/RL，也未提交Git。
"""
    (MAIN/"REPORT.md").write_text(report,encoding="utf-8")
    summary=f"""# run_039 — 20项 DOE 批量审计与优化准入

**WARNING / 19_OF_22_NUMERICALLY_SCOREABLE。** 原run_033的20项尝试中19项软件完成，D09原尝试中断、终态不明；未确认普通求解失败。D09独立run_038替代Job软件完成但有阻塞数值警告，其Loss为null。合并未重复执行的I01/I02，22个独立参数点中19个有冻结协议的探索性PROVISIONAL Loss，D07/D09/D10保持null。真实ODB Agent通过AgentHub完成提取，MAIN实际收取消息并独立重算19项。

最低已评估点D01：σy={top[0]['sigma_y_mpa']:.9g} MPa，n={top[0]['n']:.9g}，Loss={top[0]['loss']:.9g}，RMSE={top[0]['rmse_n']:.3f} N；I08次之。五个Loss≤0.01的稀疏点在归一化参数上呈负相关（r={j['low_loss_normalized_xy_pearson']:.3f}），提示补偿，不能证明连续谷地或唯一材料参数。BO/DE准入为**WARNING：仅适合另行授权的受限探索**，建议最多16个新增FE，先4 BO+4 DE审核，再决定余下4+4；本Run没有新增计算。

完整[MAIN报告](artifacts/private/main/REPORT.md)、[22点表](artifacts/private/main/evaluated_22_points.csv)、[原20项执行审计](artifacts/private/main/original_20_execution_audit.csv)、[参数Loss散点](artifacts/private/main/parameter_loss_scatter.png)、[低Loss区域](artifacts/private/main/low_loss_zoom.png)、[最佳F–D对照](artifacts/private/main/top_five_fd.png)、[全域与局部对比](artifacts/private/main/global_local_loss.png)及[Loss与数值成本](artifacts/private/main/loss_vs_runtime_cutback.png)均在Git忽略的私有证据区。历史run_025 BLOCKED、D09中断及封存拉伸数据禁读和既往暴露声明保留。完成后停止。
"""
    (RUN/"summary.md").write_text(summary,encoding="utf-8")
    evidence=[RUN/"artifacts/private/execution_audit.json",RUN/"artifacts/private/odb/manifest.json",
              RUN/"artifacts/private/odb/dataset_22.json",RUN/"artifacts/private/odb/REPORT.md",
              MAIN/"main_review.json",MAIN/"evaluated_22_points.csv",MAIN/"original_20_execution_audit.csv",
              MAIN/"REPORT.md",MAIN/"parameter_loss_scatter.png",MAIN/"low_loss_zoom.png",
              MAIN/"top_five_fd.png",MAIN/"global_local_loss.png",MAIN/"loss_vs_runtime_cutback.png",
              RUN/"summary.md"]
    manifest={"version":"run039-main-evidence-v1","created_at":now(),
              "files":[{"path":rel(p),"sha256":digest(p),"bytes":p.stat().st_size} for p in evidence]}
    save(MAIN/"evidence_manifest.json",manifest)
    task=hub.task(ids["main_task_id"])
    if task["execution_state"]=="PENDING":
        lease=hub.claim(ids["main_task_id"],identity,"run039-main-review-claim-v1")
        save(MAIN/"lease.json",lease)
        for path in (MAIN/"main_review.json",MAIN/"REPORT.md",MAIN/"evidence_manifest.json",
                     MAIN/"parameter_loss_scatter.png",MAIN/"top_five_fd.png"):
            hub.artifact(ids["main_task_id"],identity["agent_id"],path,
                         {"run":"run_039","source":"MAIN independent review","odb_task_id":ids["odb_task_id"]},
                         version="run039-main-review-v1")
        hub.finish(lease,{"status":j["status"],"scored":19,"blocked":["D07","D09","D10"],
                          "best_point":"D01","best_loss":top[0]["loss"],"bo_de_admission":j["bo_de_admission"],
                          "report_path":rel(MAIN/"REPORT.md"),"report_sha256":digest(MAIN/"REPORT.md"),
                          "new_solver_datacheck_enqueue_retry":False},evidence_state="RECORDED",science_state="WARNING")
    else:
        assert task["execution_state"]=="COMPLETED"
    assert hub.verify_chain()
    run=read(RUN/"run.json")
    run["status"]="WARNING";run["end_time"]=now()
    run["outputs"]=[{"path":v["path"],"sha256":v["sha256"]} for v in manifest["files"]]
    run["outputs"].append({"path":rel(MAIN/"evidence_manifest.json"),"sha256":digest(MAIN/"evidence_manifest.json")})
    run["validation"]=[
        {"check":"public_execution_audit","status":"WARNING","evidence":"19/20 original software completed; original D09 UNKNOWN_INTERRUPTED"},
        {"check":"real_ODB_AgentHub_handoff","status":"PASS","evidence":"ODB task completed; MAIN session received persistent message; 45 new artifacts rehashed"},
        {"check":"frozen_loss_independent_recalculation","status":"PASS","evidence":"19/19 accepted curves, 241 fixed points, absolute difference <1e-12"},
        {"check":"numerical_quality","status":"WARNING","evidence":"D07/D09/D10 null; accepted large-strain/force-drop concerns"},
        {"check":"AgentHub_audit_chain","status":"PASS","evidence":"verified after both tasks finished"},
        {"check":"sealed_tensile_isolation","status":"PASS","evidence":"no access in run_039; prior information exposure retained"}]
    save(RUN/"run.json",run)
    save(RUN/"checkpoints/completed.json",{"at":run["end_time"],"status":run["status"],
                                                "odb_task_id":ids["odb_task_id"],"main_task_id":ids["main_task_id"],
                                                "evidence_manifest_sha256":digest(MAIN/"evidence_manifest.json")})
    index=ROOT/"run/README.md"
    text=index.read_text(encoding="utf-8")
    if "## run_039 — 20项 DOE 批量结果分析" not in text:
        index.write_text(text.rstrip()+"\n\n## run_039 — 20项 DOE 批量结果分析\n\n"
                         "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                         "| run_039 | 原20项与I01/I02及独立D09补算审计、冻结Loss、补偿与BO/DE准入 | WARNING / 19 scored, 3 null | [summary](run_039/summary.md) |\n\n"
                         "原20项19项软件完成、D09原始中断；22参数点19项探索性评分。无新求解或优化。\n",encoding="utf-8")
    status=ROOT/"status/PROJECT_STATUS.md"
    text=status.read_text(encoding="utf-8")
    if "## 当前状态 — run_039" not in text:
        insertion=("## 当前状态 — run_039（2026-10-25，Asia/Shanghai）\n\n"
                   "**WARNING / 19_OF_22_NUMERICALLY_SCOREABLE。** 原run_033批次20项中19项软件完成，原D09仍为UNKNOWN_INTERRUPTED；独立run_038 D09补算软件完成但因接受态数值警告与反力回落而不评分。真实ODB Agent通过AgentHub完成回传，MAIN独立复算合并I01/I02后的19个探索性Loss。最低已评估点D01（σy≈152.309 MPa，n≈0.23066，Loss≈0.00050616）。D07/D09/D10 Loss=null；低Loss五点提示参数补偿但不证明唯一性。BO/DE仅WARNING条件下可申请另行授权的受限探索，建议最多16个新增FE、首关4+4。详见[run_039报告](../run/run_039/summary.md)。没有新增求解、Datacheck、入队、重试或优化；封存拉伸禁读及历史暴露声明保留。\n\n")
        status.write_text(text.replace("# SMALL-PUNCH 项目状态\n\n","# SMALL-PUNCH 项目状态\n\n"+insertion,1),encoding="utf-8")
    print(json.dumps({"status":"WARNING","odb_task_id":ids["odb_task_id"],"main_task_id":ids["main_task_id"],
                      "best":"D01","loss":top[0]["loss"],"scored":19,"null":["D07","D09","D10"],
                      "hub_chain":hub.verify_chain()},ensure_ascii=False))


if __name__=="__main__":
    main()
