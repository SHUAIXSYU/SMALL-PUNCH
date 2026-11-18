"""Freeze actual pilot findings, numerical caveats and a no-new-FE research decision."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_042"
ART=RUN/"artifacts"
PRIVATE=ART/"private"
MAIN=PRIVATE/"main"
ODB=PRIVATE/"odb"
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub


def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def now():return datetime.now().astimezone().isoformat()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()
def save(p,v):
    with Path(p).open("x",encoding="utf-8") as stream:json.dump(v,stream,ensure_ascii=False,indent=2);stream.write("\n")
def atomic(p,v):
    tmp=p.with_suffix(p.suffix+".tmp");save(tmp,v);os.replace(tmp,p)


def main():
    assert not (RUN/"checkpoints/completed.json").exists()
    j=read(MAIN/"main_analysis.json");audit=read(PRIVATE/"execution_audit.json");ids=read(ART/"task_ids.json")
    assert j["software_completed"]==8 and j["new_scoreable"]==5 and j["started_attempts"]==8
    assert {r["candidate_id"] for r in j["rows"] if r["loss"] is None}=={"BO01","BO02","DE02"}
    assert j["branches"]["BO"]["best_so_far_loss"]==j["branches"]["DE"]["best_so_far_loss"]==j["initial_best"]["loss"]
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    assert hub.task(ids["odb_task_id"])["execution_state"]=="COMPLETED"
    messages=hub.poll_messages(ids["identity"])
    odb_messages=[m for m in messages if m["task_id"]==ids["odb_task_id"]]
    assert odb_messages,"Real ODB result not received by MAIN session"
    save(PRIVATE/"odb_receipt.json",{"at":now(),"task_id":ids["odb_task_id"],"messages":[
        {"message_id":m["message_id"],"sender":m["sender"],"body_sha256":hashlib.sha256(m["body"].encode()).hexdigest()} for m in odb_messages]})
    decision={"version":"run042-pilot-scientific-decision-v1","at":now(),
              "execution":"8 software completed, 5 provisionally scoreable, 3 null; no solver failure",
              "optimization":"Neither branch improves D01; BO best-new lower than DE in this single pilot only",
              "next_action":"PAUSE_UNCHANGED_BO4_DE4; prioritize numerical gate diagnosis and parameter uncertainty",
              "unique_material_identification":"NOT_ESTABLISHED",
              "current_best_nominee":{"point_id":"D01","sigma_y_mpa":j["initial_best"]["sigma_y_mpa"],"n":j["initial_best"]["n"],"loss":j["initial_best"]["loss"],"status":"best evaluated exploratory candidate only"},
              "proposed_future_budget":{"maximum":6,"authorization":"NONE",
                   "gate1":"up to 2 separately authorized point-specific increment comparisons at D01/I08 if offline diagnostics leave accuracy unresolved",
                   "gate2":"up to 4 interior/boundary-near low-Loss-ridge and transverse points, after gate1 and a newly frozen uncertainty design",
                   "no_transfer_of_unused_budget":True},
              "boundaries":"keep sigma_y 150–1000 MPa and n 0.02–0.50; no extension without independent basis and authorization",
              "holdout":"still sealed; historic information exposure retained; no independent tensile validation in this Run"}
    save(MAIN/"research_decision.json",decision)
    table=[]
    for r in j["rows"]:
        loss="null" if r["loss"] is None else f"{r['loss']:.10g}"
        rmse="—" if r["rmse_n"] is None else f"{r['rmse_n']:.3f}"
        table.append(f"| {r['candidate_id']} | {r['algorithm']} | {r['sigma_y_mpa']:.9f} | {r['n']:.9f} | {loss} | {rmse} | {r['max_saved_peeq']:.6f} | {r['cutback']} | {r['actual_runtime_s']} | {r['quality']} |")
    bo=j["branches"]["BO"];de=j["branches"]["DE"]
    report=f"""# run_042 — Batch BO / DE 半代真实高保真结果

## 核验结论与身份

8项真实Job均各启动一次Datacheck与一次Full Analysis，两个阶段返回码均0；公开Queue和History均为完成，有警告。没有Solver失败、未启动或本批中断。8个ODB全部通过只读准入并由真实ODB会话提取；数值门槛下5项可评分、BO01/BO02/DE02三项Loss=null。输入完整SHA、queue_id、完整参数、材料表、INP/ODB和STA/MSG/DAT/LOG来源及单次历史均匹配run_040冻结证据与run_041入队记录。源ODB读取前后哈希保持不变。当前运行评估CLEAN、Runner所有权ABSENT、Abaqus进程探测CLEAR，旧D09中断ODB未访问。

真实ODB任务 `{ids['odb_task_id']}` 由独立会话领取、完成并通过AgentHub消息回传；MAIN实际轮询接收。MAIN复核ODB manifest共{j['manifest_verified_files']}项文件哈希，独立从正向F–D原始CSV线性插值到固定241点，重算5项Loss/RMSE，差异小于1e-12及1e-8 N。共同初始19点来源与曲线哈希同样复核，沿用相同单位、符号与实验目标。

数值契约 `run030-standard-m0025-hollomon-v1`，Loss `run017-exploratory-fd-v1`：0–1.2 mm、241点、F_ref=1428.9 N、等权MSE、线性插值，未平移零点、平滑、删点、裁窗或外推。原始实验与模型未改。Loss仍为探索性PROVISIONAL，不代表物理验证。

## 八项结果

| Job缩写 | Algorithm | σy MPa | n | Loss | RMSE N | 最大保存帧PEEQ | cutback增量数 | 时间 s | 数值质量 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(table)}

完整Job名称为 `SPIO_R040_` 加上表缩写。cutback指发生拒绝尝试的增量数，BO02为29个、拒绝尝试总数36次，不能混为同一计数。

## BO/DE 共同起点比较

两分支同从run_039的19个有效点及D07/D09/D10三个已知null开始；初始最佳D01：σy={j['initial_best']['sigma_y_mpa']:.12g} MPa、n={j['initial_best']['n']:.12g}、Loss={j['initial_best']['loss']:.12g}。8次新尝试全部消耗授权，包括三项数值不评分；没有重试或补点。

| 分支 | 启动尝试 | 可评分 | Solver失败 | 数值不评分 | 新增最佳 | 新增最佳Loss | 含D01的best-so-far | 对D01改善 | FE墙钟 s |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| BO | 4 | 2 | 0 | 2 | BO04 | {bo['best_new']['loss']:.10g} | {bo['best_so_far_loss']:.10g} | 0 | {bo['actual_wall_s']} |
| DE | 4 | 3 | 0 | 1 | DE03 | {de['best_new']['loss']:.10g} | {de['best_so_far_loss']:.10g} | 0 | {de['actual_wall_s']} |

BO04最佳新参数σy={bo['best_new']['sigma_y_mpa']:.12g} MPa、n={bo['best_new']['n']:.12g}，RMSE={bo['best_new']['rmse_n']:.4f} N；DE03为σy={de['best_new']['sigma_y_mpa']:.12g} MPa、n={de['best_new']['n']:.12g}，RMSE={de['best_new']['rmse_n']:.4f} N。新增最佳分别约为D01 Loss的3.735倍、154.360倍，因此两分支在预算0、1、2、3、4处的共同best-so-far均保持D01，绝对/相对改善都为0。本次BO新候选的最低Loss较DE低，但可评分率50%低于DE的75%；这不足以给出算法总体优越性。

BO四点是已冻结的batch Kriging-believer提议，批内没有实际新观测更新；图中逐点曲线仅按预定执行顺序统计。DE四点属于8个体的半代；DE03和DE04若按冻结选择规则分别可替换I07和D02，DE01未胜过D01、DE02因null不替换D05。这只是亲本比较，没有生成下一批或宣称完整进化代。

BO总FE墙钟818s（约13分38秒），DE738s（12分18秒），合计1556s；14 CPU配额折算6.051核时，非实测CPU利用率。共同历史完成计算5203s只作共享成本，不分别重复计入两支新增成本。当前共30个不同参数点有24项可评分；含原D09两次不确定历史尝试，累计已观察32次尝试。本Run本身新Solver/Datacheck/入队次数均0。

## 数值证据与接触演化

- PEEQ最大保存帧为0.5791538–0.8067979，均小于各自材料表0.9覆盖末端；这不是被拒绝试算峰值证明。
- BO01有9个接受帧反力回落，发生于1.1738–1.2000 mm，最大单步约−0.05066 N、合计−0.28381 N。当前保守门槛将其暂不评分。该幅度很小，尚不能单凭回落判断数值失稳或物理失效；不能追溯放宽门槛给本批补评分。
- BO02在约0.0027375–0.0042563 mm的接受增量中有1个大应变增量警告，且末段10个反力回落合计约−0.10269 N；DE02有2个接受态大应变警告（约0.0042–0.0099 mm），末端单步回落约−0.00671 N。两项保持null；实际Solver完成记录保留。
- 负特征值、单元畸变/塑性积分未尝试标题位于被拒试算：BO01负特征值3、畸变2；BO02负特征值6、畸变4；DE02负特征值4、畸变3。没有将这些警告当作已接受状态的物理结果。可评分5项接受态警告只有既有零力矩提示，另有DAT接触跟踪提示。
- 1.10–1.16 mm内BO04约在1.11812–1.12112 mm出现+18.951 N接受帧载荷变化，同时node23首次出现正CPRESS，没有相应拒绝尝试或严重警告。DE03约1.12187–1.12487 mm有+20.886 N变化，DE04约1.15290–1.15590 mm有+19.591 N变化；这些是局部接触/载荷相关证据，未被直接判成数值失败或唯一成因。详细CPRESS/COPEN与COPEN哨兵/缺失值处理保留在ODB诊断中。
- 能量诊断给出F–D积分与ALLWK对照，完整接触能量平衡仍NOT_VERIFIED。软件结束、ODB可读、暂可评分与物理可信分开记录。

## 参数补偿、边界和预测本构

最低已评估点仍是D01，其σy只比下界150 MPa高2.309 MPa。新BO03更贴近下界（150.411 MPa），但Loss约0.00511，并未改善；贴边本身不意味着更优。保持原150–1000 MPa与n 0.02–0.50范围，不擅自扩大下界。

D01和I08仍是最接近的两项低Loss候选，其参数相差约112.702 MPa和0.07626 n。BO04（385.087 MPa,0.08100）提供另一个高σy/低n的低绝对残差位置，但其Loss较D01高3.735倍，不能称同等最优。D01–BO04与I08–BO04的同网格F–D互比RMSE分别约82.53 N、40.35 N。这些真实有限点及不同预测单轴曲线支持参数补偿方向，不能证明连续谷地、严格非唯一或唯一性。

预测本构曲线仅由冻结 `inverse/hollomon.py` 的真总应变候选公式生成，绘制七个Loss≤0.01位置的0–0.2真总应变/真应力。低SPT残差可以对应不同的屈服和硬化曲线；没有读取真实单轴拉伸数据，没有把颈缩后转换当作材料真值。

每个参数点的数值误差仍未独立量化，D01与I08 Loss差仅约5.57e-5，不足以断言其排序显著。中心点run_029的相邻细化通过只适用于该中心，不能移作整个参数域或本批候选的统一误差上界。

## GP与下一阶段科研决定

采用原代码、原超参数边界对“初始19点+本分支新有效点”做**诊断性**重拟合，没有重写本批提议或产生新候选：BO 21点GP仍为 `{j['branch_gp_diagnostics']['BO']['kernel']}`，x方向长度尺度触及上界2、噪声触及下界1e-8。DE分支数据的辅助GP诊断也触界且有L-BFGS异常退出提示；DE实际算法不使用该GP。原核/变换没有因结果而改写。代理边界解和未知可评分域均限制直接继续原BO提议策略。

**明确建议：不直接执行原计划的BO4+DE4，优先参数不确定性与数值资格诊断。** 最短路径先做已有文件的离线复查：微小末段回落是否为接触/几何路径、保守门槛是否适合未来使用、低Loss方向与横向的可区分性。当前null和历史结论保持；若要改资格规则，应另立前瞻版本，而非为本批降低门槛。

若离线证据仍不足，可另行申请一个最多6次的**新研究协议**：先最多2次D01/I08各自的增量精度比较，确认最优候选的数值可比性；通过后再最多4个处于既定范围内、沿补偿方向和横向布置的识别点，优先估计解集宽度而非追求极小Loss下降。该方案不能自动挪用剩余8次预算，必须冻结目的、参数/数值设置、准入阈值及新授权；当前没有生成或执行它们。遇身份不明、失败、窗口不完整、表外PEEQ或严重未解释接受态问题则暂停，不自动重试。

DE若仅为演示算法，可以在新协议中完成半代；但本项目的反演信息收益更应优先，且若失败处理/候选策略改变，BO/DE公平性协议要先重设。可以保留D01为“当前最佳已评估探索性候选”，尚不宜冻结唯一材料答案或直接宣称独立验证就绪。保留多解集合与排序不确定性后，才由用户另行决定正式结果冻结及封存验证集解盲；本Run没有解盲。

## 交付和停止

私有目录包含8项执行审计、145项ODB提取证据清单、8项结果表、共同基线预算表、24点有效数据、Loss–Budget/成本图、参数Loss散点、最佳F–D对照和预测本构CSV/图及provenance。AgentHub记录实际消耗8次授权和NOT_EVALUATED/WARNING科学状态。run_025等历史BLOCKED和既往拉伸数据暴露声明保留。无新求解、Datacheck、入队、重试、FE搜索、RL或Git提交。完成后停止。
"""
    (MAIN/"REPORT.md").write_text(report,encoding="utf-8")
    budget={"at":now(),"scope":"run041 eight frozen first-gate Jobs only","authorized":8,"started":8,"consumed":8,
            "software_completed":8,"solver_failed":0,"unconfirmed":0,"scoreable":5,"unscoreable":3,
            "retry_allowance":0,"first_gate_remaining":0,"planned_second_gate_authorized":False,
            "branches":{b:{k:j['branches'][b][k] for k in ("attempted","valid_count","unscoreable_count","actual_wall_s")} for b in ("BO","DE")}}
    save(MAIN/"budget_actual.json",budget)
    summary=f"""# run_042 — BO/DE 先导批次真实结果

**WARNING / PILOT_COMPLETE_NO_BASELINE_IMPROVEMENT。** 8/8单次Datacheck+Full软件完成，真实ODB会话完成只读提取；5/8可按冻结Loss探索性评分。BO01、BO02、DE02因接受态反力回落或大应变警告保留null，无自动重试。MAIN独立复算5项结果，固定241点目标和原Loss未变。

BO新4次中2项可评分，最佳BO04：Loss={bo['best_new']['loss']:.10g}，σy={bo['best_new']['sigma_y_mpa']:.9g} MPa、n={bo['best_new']['n']:.9g}。DE新4次中3项可评分，最佳DE03：Loss={de['best_new']['loss']:.10g}，σy={de['best_new']['sigma_y_mpa']:.9g} MPa、n=0.08。两支含共同起点的best-so-far均保持D01 Loss={j['initial_best']['loss']:.10g}，改善0。BO/DE是一次batch及半代单种子先导，不能推导总体算法优越性。

建议暂停原BO4+DE4追加，先处理数值资格与参数补偿/不确定性；若需要新FE，另行冻结最多2个点级数值验证加4个识别设计的协议及授权。D01仅保留当前最佳探索性候选，尚不支持唯一材料识别或自动解盲。

完整[私有报告](artifacts/private/main/REPORT.md)、[8项数据](artifacts/private/main/eight_results.csv)、[预算曲线](artifacts/private/main/loss_budget_and_cost.png)、[参数散点](artifacts/private/main/parameter_loss_scatter.png)、[F–D对照](artifacts/private/main/best_fd_comparison.png)及[预测本构](artifacts/private/main/predicted_constitutive_curves.png)。8次已启动授权全部消耗；第二阶段额外8次未授权。本Run无新增求解、入队、重试或RL，历史BLOCKED与封存拉伸隔离声明保留，完成后停止。
"""
    (RUN/"summary.md").write_text(summary,encoding="utf-8")
    files=[PRIVATE/"execution_audit.json",PRIVATE/"odb_receipt.json",ODB/"manifest.json",ODB/"batch_summary.json",
           ODB/"batch_results.csv",ODB/"REPORT.md",ART/"main_analysis.py",ART/"audit_dispatch.py",ART/"finalize_run.py",RUN/"summary.md"]
    files.extend(p for p in sorted(MAIN.iterdir()) if p.is_file())
    manifest={"version":"run042-main-evidence-v1","at":now(),"files":[{"path":rel(p),"sha256":sha(p),"bytes":p.stat().st_size} for p in files]}
    save(MAIN/"evidence_manifest.json",manifest)
    task_id=ids["main_review_task_id"]
    assert hub.task(task_id)["execution_state"]=="PENDING"
    lease=hub.claim(task_id,ids["identity"],"run042-main-scientific-review-v1")
    save(PRIVATE/"main_review_lease.json",lease)
    for path in (MAIN/"REPORT.md",MAIN/"main_analysis.json",MAIN/"research_decision.json",MAIN/"budget_actual.json",MAIN/"evidence_manifest.json",RUN/"summary.md"):
        hub.artifact(task_id,ids["identity"]["agent_id"],path,{"output_run":"run_042","scope":"MAIN independent pilot analysis"},version="run042-v1")
    result={"output_run":"run_042","status":"PILOT_COMPLETE_NO_BASELINE_IMPROVEMENT","software_completed":8,"scoreable":5,
            "unscoreable":["BO01","BO02","DE02"],"consumed_attempts":8,"BO_best_new_loss":bo["best_new"]["loss"],
            "DE_best_new_loss":de["best_new"]["loss"],"best_so_far_D01":j["initial_best"]["loss"],"improvement":0,
            "decision":decision["next_action"],"report":rel(MAIN/"REPORT.md"),"report_sha256":sha(MAIN/"REPORT.md"),
            "new_solver_datacheck_enqueue_retry":False}
    hub.message(task_id,ids["identity"]["agent_id"],"MAIN",result,"run042-science-results-v1")
    hub.finish(lease,result,evidence_state="RECORDED",science_state="WARNING")
    assert hub.verify_chain()
    run=read(RUN/"run.json");run["status"]="WARNING";run["end_time"]=now()
    run["outputs"]=[{"path":v["path"],"sha256":v["sha256"]} for v in manifest["files"]]
    run["outputs"].append({"path":rel(MAIN/"evidence_manifest.json"),"sha256":sha(MAIN/"evidence_manifest.json")})
    run["validation"]=[
        {"check":"actual_public_execution_identity","status":"PASS","evidence":"8 single attempts, successful Datacheck/Full logs and History; full hashes"},
        {"check":"real_ODB_AgentHub_handoff","status":"PASS","evidence":"separate ODB session completed; MAIN message received; 145 file hashes verified"},
        {"check":"frozen_Loss_independent_recalculation","status":"PASS","evidence":"5 new and 19 initial valid curves independently interpolated, fixed 241 points"},
        {"check":"numerical_scoreability","status":"WARNING","evidence":"BO01/BO02/DE02 null; accepted-state warning/force-drop evidence retained"},
        {"check":"algorithm_comparison_scope","status":"WARNING","evidence":"single batch BO and DE half-generation, neither improves D01"},
        {"check":"GP_diagnostics","status":"WARNING","evidence":"BO length/noise bounds persist; branch-only future diagnostic, original model unchanged"},
        {"check":"AgentHub_budget_and_chain","status":"PASS","evidence":"8 started attempts consumed, no retry; chain verified"},
        {"check":"execution_boundary_and_holdout","status":"PASS","evidence":"no new Solver/Datacheck/enqueue; sealed tensile not accessed"}]
    atomic(RUN/"run.json",run)
    save(RUN/"checkpoints/completed.json",{"at":run["end_time"],"status":"WARNING","odb_task_id":ids["odb_task_id"],
          "main_review_task_id":task_id,"evidence_manifest_sha256":sha(MAIN/"evidence_manifest.json")})
    save(ART/"manifest.json",{"version":"run042-public-evidence-index-v1","private_manifest_path":rel(MAIN/"evidence_manifest.json"),"private_manifest_sha256":sha(MAIN/"evidence_manifest.json"),"file_count":len(files)})
    index=ROOT/"run/README.md";text=index.read_text(encoding="utf-8")
    assert "## run_042 — BO/DE 先导真实结果" not in text
    index.write_text(text.rstrip()+"\n\n## run_042 — BO/DE 先导真实结果\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_042 | 8项实际审计、真实ODB提取、冻结Loss与BO/DE科学比较 | WARNING / 5 scored, no D01 improvement | [summary](run_042/summary.md) |\n\n8项软件完成、5项可评分，三项null；建议先数值资格与不确定性研究，无新求解。\n",encoding="utf-8")
    status=ROOT/"status/PROJECT_STATUS.md";text=status.read_text(encoding="utf-8")
    assert "## 当前状态 — run_042" not in text
    block=("## 当前状态 — run_042（2026-10-25，Asia/Shanghai）\n\n"
           "**WARNING / PILOT_COMPLETE_NO_BASELINE_IMPROVEMENT。** run_041八项均单次Datacheck+Full软件完成，真实ODB Agent只读提取，MAIN独立复算；BO01/BO02/DE02按数值门槛Loss=null，另5项探索性可评分。BO最佳新增BO04 Loss≈0.00189029，DE最佳新增DE03≈0.0781313；两支共同best-so-far仍D01≈0.000506164，改善0。8次授权全部消耗，无重试。参数补偿、候选数值误差和GP触界仍限制唯一识别，建议暂停原BO4+DE4，优先数值资格/参数不确定性；任何新评估须新协议和授权。详见[run_042报告](../run/run_042/summary.md)。本Run无新Solver/Datacheck/入队/FE搜索/RL，封存拉伸未访问，旧BLOCKED及历史信息暴露声明保留。\n\n")
    status.write_text(text.replace("# SMALL-PUNCH 项目状态\n\n","# SMALL-PUNCH 项目状态\n\n"+block,1),encoding="utf-8")
    print(json.dumps({"status":"WARNING","software_completed":8,"scoreable":5,"consumed":8,
                      "BO_best_new":bo["best_new"]["loss"],"DE_best_new":de["best_new"]["loss"],
                      "D01_improvement":0,"decision":decision["next_action"],"hub_chain":hub.verify_chain()},ensure_ascii=False))


if __name__=="__main__":main()
