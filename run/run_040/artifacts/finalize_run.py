"""Finalize run_040 offline pilot evidence and MAIN AgentHub scientific gate."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_040"
ART=RUN/"artifacts"
PRIVATE=ART/"private"
CAE=PRIVATE/"cae"
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def save_new(path,data):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write("\n")


def replace_json(path,data):
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("x",encoding="utf-8") as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write("\n")
    os.replace(tmp,path)


def now():
    return datetime.now().astimezone().isoformat()


def main():
    assert not (PRIVATE/"MAIN_REPORT.md").exists()
    run=read(RUN/"run.json")
    assert run["status"]=="RUNNING"
    start=read(RUN/"checkpoints/start.json")
    ids=read(ART/"task_ids.json")
    candidate=read(PRIVATE/"candidate_manifest.json")
    initial=read(PRIVATE/"initial_dataset.json")
    contract=read(ART/"algorithm_contract.json")
    review=read(PRIVATE/"main_cae_review.json")
    surrogate=read(PRIVATE/"surrogate_check.json")
    ident=read(PRIVATE/"identifiability.json")
    runtime=read(PRIVATE/"algorithm_runtime.json")
    assert digest(PRIVATE/"candidate_manifest.json")==start["candidate_manifest_sha256"]
    assert digest(PRIVATE/"initial_dataset.json")==start["initial_dataset_sha256"]
    assert digest(ART/"algorithm_contract.json")==start["algorithm_contract_sha256"]
    assert initial["valid_count"]==19 and initial["invalid_count"]==3
    assert review["preflight_passed"]==review["dry_run_passed"]==8
    assert review["new_enqueues"]==review["solver_starts"]==review["datacheck_starts"]==0
    assert review["actual_message_received"]
    assert len(review["rows"])==8
    from collections import Counter
    assert Counter(p["algorithm"] for p in candidate["points"])=={"BO":4,"DE":4}
    assert all(p["fe_status"]=="NOT_AUTHORIZED_NOT_QUEUED" for p in candidate["points"])
    points="\n".join(
        f"| {r['candidate_id']} | {r['sigma_y_mpa']:.9f} | {r['n']:.9f} | `{r['inp_sha256']}` | {r['numeric_risk']} |"
        for r in review["rows"])
    warnings=", ".join(surrogate["fit_warnings"])
    report=f"""# run_040 — BO/DE 先导优化离线准备

## 身份、来源及数据冻结

新Run `run_040`，Git基线 `{run['git_head']}` / `{run['git_branch']}`；未commit/push。选用登记的 `D:\\XianLab\\envs\\torch-gpu\\python.exe`，实测Python 3.11.13及NumPy/SciPy/scikit-learn/Matplotlib现有依赖，不安装新包。读取run_039 MAIN复核的22个不同参数点，其中19个完整数值资格下的探索性PROVISIONAL Loss，D07/D09/D10三个 `Loss=null`，未填惩罚值。全部19点同属 `{initial['numeric_version']}` 与 `{initial['loss_version']}`；每点保存σy、n、归一化x/y、Loss、正向F–D来源及SHA-256、INP/ODB及结果哈希、数值质量、实际耗时。共同历史成本为24次已观察尝试，22个参数点某次软件完成、19个可评分；可归属完成时长5203s，两个算法共享这一成本。

原始SPT目标及符号、0–1.2 mm的241点、F_ref=1428.9 N、等权归一化MSE、线性插值及固定零点仍由run_017绑定哈希控制。本次没有读取封存拉伸文件或其派生内容；保留历史信息暴露声明，不能称严格无泄漏盲测。σy 150–1000 MPa、n 0.02–0.50是工程探索域，不是独立拉伸确认的可信区间。

## 算法契约

BO代码 `artifacts/pilot.py`：固定种子20261025，输入x/y归一化，`log1p(Loss)` 目标，带有界超参数的ARD Matérn-5/2 GP与白噪声核，EI ξ=0.005；在2^14固定Sobol位置搜索。四个候选采用Kriging believer预测均值作虚拟观测形成**一次性批量BO**；彼此不依赖真实新FE结果，不能称四步顺序BO。离线一次重放耗时{runtime['BO_proposal_wall_s']:.3f}s。GP拟合核 `{surrogate['kernel_fitted_on_all_19']}`；边界提示：{warnings}。19点固定核leave-one-out的log1p Loss平均绝对误差{surrogate['mean_abs_error_log1p']:.6g}、最大{surrogate['max_abs_error_log1p']:.6g}，只作代理诊断，不是校准的不确定性。代理预测可能低于物理零Loss，不可当作FE真值。

DE代码同文件：固定种子20261026、8个体、`rand/1/bin`、F=0.7、CR=0.9、归一化边界反射。最低已评估D01加最远点优先规则由共同19点选8个初始个体；其余共同点保留为可见历史。四个trial针对前四个体，属于**半代**，未做新结果选择或亲本替换。离线一次重放耗时{runtime['DE_proposal_wall_s']:.4f}s。BO候选位置先冻结；DE仅因跨分支去重而读取这四个位置，未读取BO未来结果。该固定顺序对DE位置有影响，已在公平性协议中披露。

两分支共享初始19个有效点和3个已知不可评分点，同一模型/Loss/范围；新FE预算第一关各4次。之后各分支只可见自己的新增结果。比较best-so-far Loss、有效FE数、总尝试数与失败率、wall-clock、数值质量、参数分布与低Loss等效解，并同时报告共享历史成本。单种子、每分支4次不足以统计比较算法优劣。总潜在上限16次的新FE分为4 BO+4 DE首关，审核后方可另行决定第二关4+4；本Run授权新FE=0。

## 八个候选与CAE工程验收

真实CAE Codex会话经AgentHub领取任务 `{ids['cae_task_id']}`，按已冻结完整参数生成8个独立INP及参数JSON。MAIN收到持久消息，独立重算{review['artifact_hashes_verified']}项产物哈希，检查源INP SHA、每项全文件SHA及非材料源字节完全一致，八个工作目录独立且为空。材料表严格递增、覆盖0–0.9塑性应变，E=210 GPa、ν=0.3、真总应变候选Hollomon、初始增量0.001与最大增量0.0025。正式AbqJobPilot 0.2.2 Project `{review['project_id']}` Settings=PERSISTED；8/8 Preflight `PREVIEW_READY`、8/8 Dry-run `DRY_RUN_READY`，14 CPU、0 GPU、Datacheck与Full预览开启。Queue、Settings未变化，实际入队/Datacheck/Solver均为0。

| 候选 | σy (MPa) | n | INP SHA-256 | 先验数值风险 |
| --- | ---: | ---: | --- | --- |
{points}

完整路径、完整参数精度、工作目录、来源、算法候选元数据、输入哈希见冻结清单与CAE结果。INP内保留源模板的注释标题`Job-1`及材料名称`Q200N01`，实际预览明确使用各自的`job_name`与独立目录；标题属于注释，不是新求解身份。Preflight/Dry-run不验证实际Abaqus语法、许可证、收敛或物理有效性。

## 参数补偿、边界与数值风险

D01位于σy下界150 MPa上方仅{ident['D01_vs_I08']['D01_distance_above_lower_bound_mpa']:.3f} MPa；I08的σy高{ident['D01_vs_I08']['sigma_y_difference_mpa']:.3f} MPa、n低{abs(ident['D01_vs_I08']['n_difference']):.5f}而Loss接近，两条FE曲线互比RMSE仍{ident['D01_vs_I08']['same_grid_fe_curve_rmse_n']:.2f} N。五个低Loss点的归一化x/y相关系数{ident['low_loss_normalized_correlation']:.3f}，留一四点子集范围{min(v['correlation'] for v in ident['four_of_five_leave_one_out_correlations']):.3f}至{max(v['correlation'] for v in ident['four_of_five_leave_one_out_correlations']):.3f}；支持有限样本补偿方向，不证明连续谷地、全局唯一或统计置信区间。原边界保持不变，扩大下界需独立物理依据及额外预算。

BO01、BO02与DE02接近n下边界；历史D07/D09/D10也位于低n区域且数值评分受阻。BO03紧邻σy下边界。BO02和DE02在归一化参数距离上距已知失败点仅约0.05，是高风险试探；合法的材料表和预览不能消除此风险。未来每次必须核对Datacheck/Full真实终态、窗口覆盖、PEEQ材料表范围、接触演化与局部力突跳，严重未解释接受态警告则Loss=null；失败与不评分均消耗授权尝试，禁止自动重试。当前AbqJobPilot历史上没有可靠自动异常停队列能力，若未来授权8次，宜逐项受控入队、人工GUI启动、主控审核，出现系统性问题暂停剩余额度。

## 本轮资格结论

**WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK。** 算法、数据、8份输入和8/8工程预览已具备申请首关最多8次新高保真尝试的基础；必须在授权时明确接受三个低n候选与一个边界候选的风险，并保持失败消耗预算、异常暂停及不自动重试。即使八项完成，也只构成单种子探索性先导，不是正式材料反演或BO/DE性能结论。求解前仍要重新核验Project/Settings、Queue、Runner状态和输出目录，当前预览不能替代当时准入。此Run停止于准备阶段，不入队、不启动Solver/Datacheck，不执行RL或Git提交。

证据：`artifacts/private/initial_dataset.json`、`artifacts/private/candidate_manifest.json`、`artifacts/algorithm_contract.json`、`artifacts/pilot_protocol.md`、`artifacts/private/cae/`、`artifacts/private/main_cae_review.json`、`artifacts/private/surrogate_check.json`及单元测试记录。所有含可恢复SPT实验数据或实验驱动参数的证据保存在Git忽略区域。
"""
    (PRIVATE/"MAIN_REPORT.md").write_text(report,encoding="utf-8")
    summary=f"""# run_040 — BO/DE 先导优化离线准备

**WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK。** run_039的19个可评分点及D07/D09/D10三个null记录已按身份与哈希冻结；算法测试5项通过。BO为一次性Kriging believer批量4点，DE为8个体种群的半代4个trial，均未使用新FE观测。真实CAE Agent完成8份独立INP，MAIN收到AgentHub消息并复核；8/8 Preflight、8/8 Dry-run通过。Queue未改变，0次新Datacheck/Solver/入队。

BO01、BO02、DE02靠近历史低n数值阻塞区，BO03紧邻σy下界；GP拟合超参数触及预设边界。可申请最多8次首关新高保真尝试，但须明确数值风险、失败照算预算、逐项审核与暂停条件；第二关4+4只能在首关结果后另行决定。本Run无计算授权，停止等待指令。

完整[私有研究报告](artifacts/private/MAIN_REPORT.md)、[算法及公平性协议](artifacts/pilot_protocol.md)、[工程复核](artifacts/private/main_cae_review.json)与[CAE证据](artifacts/private/cae/REPORT.md)。保留既往拉伸资料暴露声明，不解盲、不改原始模型、不commit/push。
"""
    (RUN/"summary.md").write_text(summary,encoding="utf-8")
    evidence=[PRIVATE/"initial_dataset.json",PRIVATE/"candidate_manifest.json",ART/"algorithm_contract.json",
              ART/"pilot_protocol.md",ART/"pilot.py",ART/"test_pilot.py",ART/"build_pilot.py",
              PRIVATE/"surrogate_check.json",PRIVATE/"identifiability.json",PRIVATE/"algorithm_runtime.json",
              CAE/"structured_result.json",
              CAE/"generated_candidate_manifest.json",CAE/"static_verification.json",CAE/"preview_result.json",
              CAE/"preview_integrity.json",PRIVATE/"main_cae_review.json",PRIVATE/"MAIN_REPORT.md",RUN/"summary.md"]
    evidence.extend(ROOT/r["inp_path"] for r in review["rows"])
    manifest={"version":"run040-main-evidence-v1","created_at":now(),
              "files":[{"path":rel(p),"sha256":digest(p),"bytes":p.stat().st_size} for p in evidence]}
    save_new(PRIVATE/"evidence_manifest.json",manifest)
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    assert hub.task(ids["cae_task_id"])["execution_state"]=="COMPLETED"
    identity=hub.register("MAIN","codex-main-run040-final-review")
    task=hub.task(ids["review_task_id"])
    assert task["execution_state"]=="PENDING"
    lease=hub.claim(ids["review_task_id"],identity,"run040-main-final-review-claim-v1")
    save_new(PRIVATE/"main_review_lease.json",lease)
    for p in (PRIVATE/"MAIN_REPORT.md",PRIVATE/"evidence_manifest.json",PRIVATE/"main_cae_review.json",
              PRIVATE/"candidate_manifest.json",ART/"algorithm_contract.json",ART/"pilot_protocol.md"):
        hub.artifact(ids["review_task_id"],identity["agent_id"],p,
                     {"run":"run_040","source":"MAIN independent scientific and engineering review",
                      "cae_task_id":ids["cae_task_id"]},version="run040-main-v1")
    hub.finish(lease,{"status":"READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK",
                      "valid_initial":19,"null_initial":["D07","D09","D10"],
                      "candidate_count":8,"preflight_passed":8,"dry_run_passed":8,
                      "high_risk_ids":review["higher_risk_ids"],"new_solver_datacheck_enqueue":False,
                      "report_path":rel(PRIVATE/"MAIN_REPORT.md"),"report_sha256":digest(PRIVATE/"MAIN_REPORT.md")},
               evidence_state="RECORDED",science_state="WARNING")
    assert hub.verify_chain()
    run["status"]="WARNING"
    run["start_time"]="2026-10-25T22:20:02.742837+08:00"
    run["end_time"]=now()
    run["outputs"]=[{"path":v["path"],"sha256":v["sha256"]} for v in manifest["files"]]
    run["outputs"].append({"path":rel(PRIVATE/"evidence_manifest.json"),"sha256":digest(PRIVATE/"evidence_manifest.json")})
    run["validation"]=[
        {"check":"initial_19_valid_3_null_shared_identity","status":"PASS","evidence":"run039 source/result/curve hashes and numeric/Loss contracts verified"},
        {"check":"BO_DE_reproducibility_and_bounds","status":"PASS","evidence":"5 offline tests, byte-frozen 8 proposals"},
        {"check":"real_CAE_AgentHub_handoff","status":"PASS","evidence":"separate CAE session claimed/completed; MAIN received message; 26 artifact hashes verified"},
        {"check":"eight_INP_static_and_previews","status":"PASS","evidence":"8 nonmaterial identities, material tables, Preflight and dry-run; no Queue mutation"},
        {"check":"numerical_extrapolation_risk","status":"WARNING","evidence":"BO01/BO02/DE02 low n, BO03 sigma boundary, GP hyperparameters at limits"},
        {"check":"new_solver_datacheck_queue","status":"PASS","evidence":"0 starts and 0 enqueue in this Run"},
        {"check":"AgentHub_chain_and_holdout_isolation","status":"PASS","evidence":"audit chain valid; sealed tensile not read, historic exposure retained"}]
    replace_json(RUN/"run.json",run)
    save_new(RUN/"checkpoints/completed.json",{"at":run["end_time"],"status":run["status"],
                                                "cae_task_id":ids["cae_task_id"],"review_task_id":ids["review_task_id"],
                                                "evidence_manifest_sha256":digest(PRIVATE/"evidence_manifest.json")})
    index=ROOT/"run/README.md"
    text=index.read_text(encoding="utf-8")
    if "## run_040 — BO/DE 先导优化离线准备" not in text:
        index.write_text(text.rstrip()+"\n\n## run_040 — BO/DE 先导优化离线准备\n\n"
                         "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                         "| run_040 | 19点共享数据、批量BO与部分代DE、真实CAE生成8份输入及预览 | WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK | [summary](run_040/summary.md) |\n\n"
                         "8/8 Preflight和dry-run通过；无入队、Datacheck或Solver。\n",encoding="utf-8")
    status=ROOT/"status/PROJECT_STATUS.md"
    text=status.read_text(encoding="utf-8")
    if "## 当前状态 — run_040" not in text:
        block=("## 当前状态 — run_040（2026-10-25，Asia/Shanghai）\n\n"
               "**WARNING / READY_TO_REQUEST_FIRST_GATE_WITH_NUMERICAL_RISK。** 19个同契约有效SPT FE评价及D07/D09/D10三个null已冻结。单种子批量BO 4点与部分代DE 4点经真实CAE Agent生成独立INP，MAIN接收并复核AgentHub证据；8/8官方Preflight、8/8 dry-run通过，Queue无新增、Solver/Datacheck未启动。BO01/BO02/DE02靠近低n数值阻塞区，BO03靠近σy下界，GP超参数触及约束。可申请最多8次首关新高保真尝试，但必须明确风险和逐项异常暂停；本Run不授予执行额度。详见[run_040报告](../run/run_040/summary.md)。封存拉伸禁读及历史信息暴露声明不变，无DE/BO新FE、RL或Git提交。\n\n")
        status.write_text(text.replace("# SMALL-PUNCH 项目状态\n\n","# SMALL-PUNCH 项目状态\n\n"+block,1),encoding="utf-8")
    print(json.dumps({"status":run["status"],"cae_task":ids["cae_task_id"],"review_task":ids["review_task_id"],
                      "candidates":8,"preflight":8,"dry_run":8,"hub_chain":hub.verify_chain()},ensure_ascii=False))


if __name__=="__main__":
    main()
