"""Read back eight queued jobs and record the manual-start handoff; no submit."""
from __future__ import annotations

import json
import os
from pathlib import Path

from queue_pilot import (ART, PRIVATE, ROOT, RT, RUN, PID, PROJECT, ORDER, AbqJobPilotClient,
                         Hub, environment, load_batch, now, queue_prefix, read, rel,
                         runtime_guard, save, sha)


def atomic_json(path,data):
    tmp=path.with_suffix(path.suffix+".tmp")
    save(tmp,data)
    os.replace(tmp,path)


def main():
    assert not (RUN/"checkpoints/phase1_completed.json").exists()
    manifest=read(PRIVATE/"queue_manifest.json")
    assert manifest["status"]=="EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START"
    ids=read(PRIVATE/"task_ids.json")
    points=load_batch()
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
    env=environment(api)
    final=queue_prefix(scoped,api,points,8)
    runtime=runtime_guard(deep=True)
    assert final["queue_ids"]==manifest["queue_ids"]
    assert len(final["queue_ids"])==len(set(final["queue_ids"]))==8
    initial=read(PRIVATE/"preflight.json")
    assert sha(RT/"settings.json")==initial["protected_before"]["settings"]
    assert sha(PROJECT/"project.db")==initial["protected_before"]["project_db"]
    audit={"at":now(),"status":"EIGHT_QUEUED_NO_STARTS","environment":env,"runtime":runtime,
           "queue":final,"solver_started":False,"datacheck_started":False,
           "all_inputs_hash_verified_again":True,"all_output_directories_empty":True,
           "auto_stop":"AUTO_STOP_UNAVAILABLE","manual_stop_is_not_automatic_fail_stop":True}
    save(PRIVATE/"final_readback.json",audit)
    budget={"at":now(),"scope":"Only eight immutable run040 inputs; no substitution or retry",
            "maximum_started_attempts":8,"prepared_count":8,"queued_count":8,"started_attempts":0,
            "completed_count":0,"failed_count":0,"uncertain_count":0,"scoreable_count":0,
            "unscoreable_count":0,"pending_scientific_evaluation":8,"consumed_FE_attempts":0,
            "reserved_for_eight_queued_inputs":8,"replacement_budget":0,"second_stage_authorized":False,
            "states":[{"candidate_id":r["candidate_id"],"queue_id":r["queue_id"],"prepared":True,
                       "queue_status":"QUEUED","started":False,"completed":False,"failed":False,
                       "score_state":"NOT_EVALUATED","loss":None,"FE_attempts_consumed":0}
                      for r in manifest["points"]]}
    save(PRIVATE/"budget_ledger.json",budget)
    table="\n".join(f"| {r['position']} | `{r['job_name']}` | `{r['queue_id']}` | QUEUED |" for r in manifest["points"])
    report=f"""# run_041 — BO/DE 八项授权批量入队

**WARNING / EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START。** 本轮第一阶段完成，八项均为QUEUED，Datacheck与Solver未启动。现在停止执行，等待用户本人在正确Project点击一次Start Queue。

## 用户手动启动

AbqJobPilot Project：`E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`。
Project ID：`{PID}`。请在GUI核对以下8个可执行Job及顺序，再点击一次 **Start Queue**。

| 顺序 | Job | queue_id | 回读状态 |
| --- | --- | --- | --- |
{table}

统一配置：14 CPU、0 GPU，Datacheck成功后Full Analysis，每个输入最多一次尝试、零自动重试、单Runner串行；只允许用户GUI启动。`AUTO_STOP_UNAVAILABLE`已经用户明确接受：一个Job失败或带警告后，Runner仍可能继续后续Job；Stop After Current Job是人工请求，不能视为可靠自动异常停机。

## 身份、当前预检及预算

- 实际最大历史Run为run_040，独占创建run_041。读取AGENTS/Run/AgentHub协议、run_039与run_040报告，记录main分支、HEAD及既有工作树，不覆盖历史证据或用户改动。
- 冻结参数清单SHA-256为 `692c3215c974b35ea1c816b86520f2c183241504c8bd2e0b111cda44bb2d502b`。该清单原本冻结算法参数及路径，完整INP哈希来自其绑定的既有CAE生成清单与run_040 MAIN审核；三者在本轮联接核验，未重新生成输入。8份INP、参数JSON、生成器和模型契约哈希全部匹配，非材料源字节一致，工作目录相互独立且为空。
- 数值契约 `run030-standard-m0025-hollomon-v1`，Loss契约 `run017-exploratory-fd-v1` 原版本保持绑定；初始增量0.001、最大0.0025、最小1e-12、总时间1、最大增量数999999、E=210 GPa、ν=0.3。没有根据候选修改几何、网格、接触、摩擦、BC、Punch加载或输出。
- 本机实际导入AbqJobPilot 0.2.2，公开API Project身份和 `PERSISTED` Settings通过，Abaqus命令 `D:\\ABAQUS2024\\Commands\\abq2024.bat` 存在，14 CPU/0 GPU及Datacheck/Full均匹配；本轮重新执行8/8 Preflight和8/8 Dry-run均就绪。预览阶段Queue/Settings/Project DB哈希未变；真实入队只使用公开API，入队后Settings和Project DB仍不变。
- Runner所有权ABSENT、Live为IDLE、运行恢复评估CLEAN、Abaqus进程探测CLEAR，没有其他可执行Job。原run_033 D09历史目录仍有旧锁；该旧Job中断历史及既有官方恢复记录保留，锁不属于八个新目录，未打开旧ODB或清锁。通用恢复计划仍提示该历史锁，未将它误报成新Job活动状态。
- 本机 `runner_core.py` 的 `_run_loop` 在 `run_next_job(job)` 后不检查求解结果而继续选下一个Job，当前代码SHA已登记，异常自动停队列仍不可用。
- MAIN通过正式Hub接口登记8次预算、每项输入完整hash、Project、资源、手动启动方式及独立审批；依次入队并记录8个唯一queue_id。最终回读顺序完全匹配，只有本批8项可执行，均无started_at/ended_at、没有新ODB或锁且工作目录为空。
- 当前预算：授权8、准备8、入队8、实际启动0、消耗FE尝试0。八项额度全部绑定上述输入；未来任何已启动尝试无论成功失败都会消耗对应一次，不能转成替代参数、重试或追加Job。第二阶段额外8次未授权。

## AgentHub及第二阶段停止点

预算登记任务：`{ids['budget_task_id']}`；八项Queue任务及总体验证均COMPLETED/RECORDED，但只代表入队工作完成，科学状态NOT_EVALUATED。后续MAIN执行审计、ODB批量只读提取、MAIN科学比较任务已登记；ODB依赖真实执行审计完成，目前未唤醒ODB会话，也未宣称结果提取。用户通知计算完成后才审计真实终态，逐项区分完成、失败、中断、未启动及科学可评分状态。BO四点仍是固定batch提议，DE四点仍是半代，不得事后改算法或利用对方新增结果重选点。

私有授权范围、逐项API请求/响应、真实queue_id、最终Queue回读和预算账本位于 `artifacts/private/`。封存拉伸文件和派生结果未访问；历史信息泄漏及run_025 BLOCKED等结论保持。未调用Abaqus、Datacheck或GUI启动，无RL、第二阶段优化、commit/push。
"""
    (RUN/"summary.md").write_text(report,encoding="utf-8")
    manifest_files=[PRIVATE/"authorization_scope.json",PRIVATE/"frozen_batch_identity.json",PRIVATE/"preflight.json",
                    PRIVATE/"queue_manifest.json",PRIVATE/"final_readback.json",PRIVATE/"budget_ledger.json",
                    ART/"queue_pilot.py",ART/"finalize_phase1.py",RUN/"summary.md"]
    receipts=PRIVATE/"queue_receipts"
    manifest_files.extend(sorted(receipts.glob("*.json")))
    evidence={"version":"run041-phase1-evidence-v1","at":now(),
              "files":[{"path":rel(p),"sha256":sha(p),"bytes":p.stat().st_size} for p in manifest_files]}
    save(PRIVATE/"evidence_manifest.json",evidence)
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3",lease_seconds=14400)
    actor=ids["identity"]
    task=hub.create_task(actor["agent_id"],"MAIN","record_pilot_phase1_manual_start_handoff",
                         {"run":"run_041","queue_manifest_sha256":sha(PRIVATE/"queue_manifest.json"),
                          "queued":8,"started":0},"run041-phase1-final-handoff-v1",depends=(ids["confirm_task_id"],))
    lease=hub.claim(task["task_id"],actor,"run041-phase1-handoff-claim-v1")
    save(PRIVATE/"handoff_lease.json",lease)
    for path in (RUN/"summary.md",PRIVATE/"budget_ledger.json",PRIVATE/"final_readback.json",PRIVATE/"evidence_manifest.json"):
        hub.artifact(task["task_id"],actor["agent_id"],path,{"run":"run_041","stage":"queue-only handoff; no actual solve"},version="run041-v1")
    hub.finish(lease,{"status":manifest["status"],"queued":8,"started_attempts":0,"consumed_FE_budget":0,
                      "manual_gui_start_required":True,"auto_stop":"AUTO_STOP_UNAVAILABLE"},evidence_state="RECORDED",science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    run=read(RUN/"run.json")
    run["status"]="WARNING";run["end_time"]=now()
    run["phase1_status"]=manifest["status"];run["phase2_status"]="AWAITING_USER_COMPLETION"
    run["outputs"]=[{"path":v["path"],"sha256":v["sha256"]} for v in evidence["files"]]
    run["outputs"].append({"path":rel(PRIVATE/"evidence_manifest.json"),"sha256":sha(PRIVATE/"evidence_manifest.json")})
    run["validation"]=[
        {"check":"eight_frozen_INP_and_contract_identity","status":"PASS","evidence":"full input hashes and exact parameters, source nonmaterial identity, generator/model/Loss bindings"},
        {"check":"current_public_preflight_dry_run","status":"PASS","evidence":"8/8 PREVIEW_READY and 8/8 DRY_RUN_READY, Settings=PERSISTED"},
        {"check":"real_queue_only_enqueue_and_readback","status":"PASS","evidence":"8 unique queue_ids; exact order; only eight executable; all QUEUED; zero starts"},
        {"check":"manual_start_only_and_budget","status":"PASS","evidence":"8 authorized, 8 queued, 0 started, 0 consumed; user GUI only"},
        {"check":"automatic_queue_fail_stop","status":"WARNING","evidence":"AUTO_STOP_UNAVAILABLE; explicit human acceptance; source hash recorded"},
        {"check":"historical_D09_lock","status":"WARNING","evidence":"CLEAN runtime/ABSENT owner/CLEAR processes; isolated old lock retained, not reused"},
        {"check":"AgentHub_audit","status":"PASS","evidence":"formal API tasks/approvals/evidence; chain verified"}]
    atomic_json(RUN/"run.json",run)
    save(RUN/"checkpoints/phase1_completed.json",{"at":run["end_time"],"status":manifest["status"],
          "queue_ids":manifest["queue_ids"],"started_attempts":0,"handoff_task_id":task["task_id"],
          "evidence_manifest_sha256":sha(PRIVATE/"evidence_manifest.json")})
    index=ROOT/"run/README.md";text=index.read_text(encoding="utf-8")
    assert "## run_041 — BO/DE 八项授权批量入队" not in text
    index.write_text(text.rstrip()+"\n\n## run_041 — BO/DE 八项授权批量入队\n\n"
                     "| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n"
                     "| run_041 | 8项冻结输入授权登记、当前预览及公开API批量queue-only入队 | WARNING / EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_041/summary.md) |\n\n"
                     "8项QUEUED，0次实际启动；等待用户GUI一次Start Queue。AUTO_STOP_UNAVAILABLE风险已接受。\n",encoding="utf-8")
    status=ROOT/"status/PROJECT_STATUS.md";text=status.read_text(encoding="utf-8")
    block=("## 当前状态 — run_041（2026-10-25，Asia/Shanghai）\n\n"
           "**WARNING / EIGHT_BO_DE_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户明确授权run_040冻结BO01–BO04、DE01–DE04一次性批量入队，每项一次Datacheck+Full、14CPU/0GPU、零重试、仅用户GUI启动。8项完整身份与当前Preflight/Dry-run通过，已通过公开API按BO01→BO04→DE01→DE04依次入队；8个唯一queue_id、恰好8个可执行任务，均QUEUED，实际启动与预算消耗为0。AgentHub已登记预算/授权/逐项证据及后续只读审计任务。AUTO_STOP_UNAVAILABLE风险用户已接受；当前停止等待GUI人工Start Queue，未启动Solver/Datacheck。旧D09历史锁隔离保留，运行评估CLEAN。详见[run_041报告](../run/run_041/summary.md)。第二阶段额外8次未授权，封存拉伸禁读与历史结论保留。\n\n")
    assert "## 当前状态 — run_041" not in text
    status.write_text(text.replace("# SMALL-PUNCH 项目状态\n\n","# SMALL-PUNCH 项目状态\n\n"+block,1),encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"queued":8,"started":0,"hub_chain":hub.verify_chain(),"queue_ids":manifest["queue_ids"]}))


if __name__=="__main__":main()
