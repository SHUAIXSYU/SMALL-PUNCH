"""Read-only final verification, persistent manual-start handoff, then stop."""
from pathlib import Path
import sys,json,os
import queue_hardening as v
R=v.R;RUN=v.RUN;A=v.A;P=v.P;read=v.read;save=v.save;sha=v.sha;rel=v.rel;now=v.now
from abqjobpilot.api import AbqJobPilotClient
from agenthub_sp_invopt.hub import Hub

def main():
    assert not (RUN/'checkpoints/phase1_completed.json').exists()
    manifest=read(P/'queue_manifest.json');pts=v.points();ids=read(P/'task_ids.json');pre=read(P/'precheck.json')
    api=AbqJobPilotClient();scoped=api.for_project(project_id=v.PID);env=v.q.environment(api);runtime=v.q.runtime_guard(deep=True);final=v.queue_guard(scoped,api,pts,2)
    assert final['queue_ids']==manifest['queue_ids'] and len(set(final['queue_ids']))==2 and final['executable_count']==2
    details=[]
    for p,r in zip(pts,manifest['points']):
        assert sha(R/p['inp_path'])==p['inp_sha256']==r['inp_sha256'] and not any((R/p['working_dir']).iterdir())
        st=scoped.status(job_id=r['queue_id']).to_dict();out=scoped.locate_outputs(job_id=r['queue_id']).to_dict()
        assert st['status']=='QUEUED' and not st['odb_exists'] and not st['lock_exists']
        details.append({'candidate_id':p['candidate_id'],'queue_id':r['queue_id'],'status':st,'outputs':out})
    assert sha(v.RT/'settings.json')==pre['protected_after'][str(v.RT/'settings.json')]
    frozen={'run/run_051/artifacts/prepared_batch.json':sha(v.FROZEN),'run/run_051/artifacts/material_contract.json':sha(R/'run/run_051/artifacts/material_contract.json'),'run/run_051/artifacts/comparison_contract.json':sha(R/'run/run_051/artifacts/comparison_contract.json')}
    protected={'run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip':'d439ef3ae696d9711aa3a3d4fa989f61710adf3cd9a73c9935b9432131dddc3a','run/run_047/artifacts/private/independent_validation_report.md':'e9c118714ba39d12662a31304c57140e95144cb7d0b4b5dddd9bd20d3d7bdf52','run/run_048/artifacts/private/independent_reassessment_report.md':'f666424ef9a65143ab341c101e0357391b462f356e554f947e7497a96da1c483'}
    assert all(sha(R/p)==s for p,s in protected.items())
    save(P/'final_readback.json',{'at':now(),'environment':env,'runtime':runtime,'queue':final,'job_status_and_outputs':details,'frozen_evidence':frozen,'historical_validation_evidence_unchanged':protected,'settings_unchanged':True,'project_db_hash_before_preview':pre['protected_before'][str(v.PROJECT/'project.db')],'project_db_hash_at_final':sha(v.PROJECT/'project.db'),'project_db_note':'No direct DB writes. Public Queue/History details above distinguish any GUI-synced unstarted placeholders from attempts','actual_solver_started':False,'actual_datacheck_started':False,'all_workdirs_empty':True})
    ledger={'at':now(),'authorized_inputs':2,'prepared':2,'queued':2,'started_attempts':0,'software_completed':0,'numerically_reviewed':0,'scientifically_evaluated':0,'failed':0,'unknown':0,'consumed_FE_budget':0,'reserved_for_named_inputs':2,'automatic_retries':0,'third_job_allowed':False,'authorization_source_sha256':sha(P/'authorization_scope.json'),'queue_ids':final['queue_ids'],'phase2':'PENDING_USER_NOTIFICATION_AND_MAIN_EXECUTION_AUDIT'}
    save(P/'budget_ledger.json',ledger)
    table='\n'.join(f"| {i+1} | {p['job_name']} | `{p['queue_id']}` | QUEUED |" for i,p in enumerate(manifest['points']))
    with (RUN/'summary.md').open('x',encoding='utf-8') as f:f.write(f'''# run_052 — H01/H02授权入队

**WARNING / TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START。** 第一阶段完成：恰好两项本批获授权Job可执行，均QUEUED；无Solver/Datacheck启动，实际FE尝试消耗0。请用户在正确Project核对两项后手动点击一次Start Queue。

Project：`E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`；ID `{v.PID}`。

| 顺序 | Job | queue_id | 当前状态 |
|---|---|---|---|
{table}

14 CPU、0 GPU，每Job最多一次Datacheck成功后一次Full Analysis，零自动重试，单Runner串行，仅用户GUI启动。AUTO_STOP_UNAVAILABLE已按当前本机Runner源码重新核实，用户接受第一项失败/警告后仍可能继续第二项。

严格PERSISTED Settings、Abaqus命令路径、两份冻结完整哈希、82行材料表、低段和块外字节、最大增量.00125及Punch U2/RF2不变均通过核验。当前Runner CLEAN/IDLE、无活动所有权或待恢复状态，输出目录为空；2/2新Preflight与2/2新Dry-run通过后才顺序入队。只使用公开API，没有直接编辑Queue/Project DB/Hub SQLite、清理锁或修改历史输入。

授权/queue_id/输入与工作目录证据登记AgentHub。[授权](artifacts/private/authorization_scope.json)、[预检查](artifacts/private/precheck.json)、[队列清单](artifacts/private/queue_manifest.json)、[最终回读](artifacts/private/final_readback.json)、[预算台账](artifacts/private/budget_ledger.json)。未来两项ODB只读任务已登记，依赖尚未完成的MAIN执行审核任务，不会因为登记自动唤醒或执行。

未读取拉伸实验，run046冻结预测及run047/048历史保持；没有新输入、拟合、BO/DE/RL或Git提交。第二阶段尚未执行，不存在新F–D/Loss/PEEQ或科学结论。当前停止，等待用户手动计算完成后通知。
''')
    idx=R/'run/README.md';txt=idx.read_text(encoding='utf-8-sig');assert '## run_052' not in txt
    with idx.open('a',encoding='utf-8') as f:f.write('\n\n## run_052 — H01/H02授权Queue-only入队\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_052 | 两项冻结高应变包络授权、现行预检及公开API入队 | WARNING / TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_052/summary.md) |\n\n两项QUEUED、0启动/消耗，等待用户GUI手动Start Queue；尚未开展结果分析。\n')
    sp=R/'status/PROJECT_STATUS.md';old=sp.read_text(encoding='utf-8-sig');save(P/'status_before_run052.json',{'sha256':sha(sp),'text':old});header='# SMALL-PUNCH 项目状态\n';assert old.startswith(header)
    new=header+'\n## 当前状态 — run_052（2026-10-26，Asia/Shanghai）\n\n**WARNING / TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户已批准run051两项冻结高应变包络一次尝试/Job、14CPU0GPU、零重试、GUI手动启动，并接受AUTO_STOP_UNAVAILABLE。新2/2预检与Dry-run通过，已公开API按H01→H02仅入队两项、唯一queue_id，恰好两项QUEUED、实际启动/预算消耗0；真实输出尚未生成。见[run_052](../run/run_052/summary.md)。原输入/冻结及独立验证历史保留，无Solver/Datacheck/参数变更/额外Job。未来ODB任务依赖MAIN实际执行审核，当前停止等待用户手动启动。\n\n'+old[len(header):]
    tmp=sp.with_suffix('.md.run052.tmp');tmp.write_text(new,encoding='utf-8');os.replace(tmp,sp)
    save(P/'git_final.json',{'at':now(),'branch':v.q.git('branch','--show-current'),'head':v.q.git('rev-parse','HEAD'),'working_tree':v.q.git('status','--short'),'preexisting_changes_preserved':True})
    files=[{'path':rel(p),'sha256':sha(p),'visibility':'PRIVATE_GIT_IGNORED' if P in p.parents else 'PUBLIC_SCOPE_OR_CODE'} for p in sorted(RUN.rglob('*')) if p.is_file() and p.name!='run.json' and p!=A/'manifest.json']
    save(A/'manifest.json',{'version':'run052-phase1-evidence-index-v1','at':now(),'files':files,'excludes':'self/run.json/later Hub receipt and completion checkpoint to avoid cyclic hashes'})
    h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity']
    handoff={'status':manifest['status'],'run':'run_052','project_id':v.PID,'order':v.ORDER,'queue_ids':final['queue_ids'],'queue_manifest_path':rel(P/'queue_manifest.json'),'queue_manifest_sha256':sha(P/'queue_manifest.json'),'authorization_sha256':sha(P/'authorization_scope.json'),'phase1_report':rel(RUN/'summary.md'),'queued':2,'started':0,'consumed':0,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','auto_stop':'AUTO_STOP_UNAVAILABLE','future_execution_audit_task_id':ids['execution_audit_task_id'],'future_odb_task_ids':ids['odb_task_ids'],'science_state':'NOT_EVALUATED'}
    task=h.create_task(actor['agent_id'],'MAIN','phase1_hardening_queue_manual_start_handoff',{'run':'run_052','queue_ids':final['queue_ids'],'final_readback_sha256':sha(P/'final_readback.json')},'run052-phase1-handoff-v1',depends=(ids['confirm_task_id'],));lease=h.claim(task['task_id'],actor,'run052-handoff-claim-v1');save(P/'handoff_lease.json',lease)
    for p in [RUN/'summary.md',P/'precheck.json',P/'final_readback.json',P/'budget_ledger.json',P/'queue_manifest.json',A/'manifest.json']:h.artifact(task['task_id'],actor['agent_id'],p,{'run':'run_052','scope':'queue-only handoff, no FE result'},version='run052-v1')
    message=h.message(task['task_id'],actor['agent_id'],'MAIN',handoff,'run052-queued-handoff-v1');h.finish(lease,handoff,evidence_state='RECORDED',science_state='NOT_EVALUATED')
    assert all(h.task(t)['execution_state']=='PENDING' for t in [ids['execution_audit_task_id'],*ids['odb_task_ids'].values(),ids['science_task_id']])
    save(P/'hub_phase1_receipt.json',{'at':now(),'handoff_task_id':task['task_id'],'message_id':message['message_id'],'budget_task_id':ids['budget_task_id'],'point_tasks':ids['point_tasks'],'future_tasks_pending':True,'execution_state':'COMPLETED','science_state':'NOT_EVALUATED','no_cross_session_wakeup_claimed':True})
    run=read(RUN/'run.json');save(RUN/'checkpoints/before_phase1_final.json',run)
    run.update(status='WARNING',end_time=now(),outputs=[{'path':rel(RUN/'summary.md'),'role':'manual-start report'},{'path':rel(P/'queue_manifest.json'),'role':'actual queue identities','sha256':sha(P/'queue_manifest.json')},{'path':rel(P/'budget_ledger.json'),'role':'authorized vs started budget','sha256':sha(P/'budget_ledger.json')},{'path':rel(P/'hub_phase1_receipt.json'),'role':'formal Hub evidence receipt','sha256':sha(P/'hub_phase1_receipt.json')},{'path':rel(A/'manifest.json'),'role':'evidence index','sha256':sha(A/'manifest.json')}],validation=[{'check':'frozen identity and changed material scope','status':'PASS','evidence':rel(P/'authorization_scope.json'),'scope':'two original INP hashes, D01 plastic-only differences and controls'},{'check':'current public preflight/dry-run','status':'PASS','evidence':rel(P/'precheck.json'),'scope':'2/2;PERSISTED14CPU0GPU;not Abaqus syntax/convergence validation'},{'check':'unstarted authorized Queue and Runner','status':'PASS','evidence':rel(P/'final_readback.json'),'scope':'exactly two in order;QUEUED;no outputs/locks/started attempts'},{'check':'science results','status':'WARNING','evidence':rel(P/'budget_ledger.json'),'scope':'awaiting human GUI start; no results or scientific qualification'}],errors=[])
    temp=RUN/'run.json.new';save(temp,run);read(temp);os.replace(temp,RUN/'run.json')
    save(RUN/'checkpoints/phase1_completed.json',{'at':now(),'run_json_sha256':sha(RUN/'run.json'),'queue_ids':final['queue_ids'],'queue_manifest_sha256':sha(P/'queue_manifest.json'),'started':0,'consumed_FE_budget':0,'phase2_executed':False,'stopped_for_user_GUI_start':True})
    print(json.dumps({'status':manifest['status'],'queue_ids':final['queue_ids'],'queued':2,'started':0,'phase2_executed':False}))

if __name__=='__main__':main()
