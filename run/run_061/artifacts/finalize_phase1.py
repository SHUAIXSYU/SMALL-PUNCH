"""Record the completed queue handoff. Does not start or monitor Solver."""
from queue_i06 import *

def main():
    m=read(P/'queue_manifest.json');ids=read(P/'task_ids.json');start=read(RUN/'checkpoints/start.json');pre=read(P/'precheck.json')
    assert m['status']==STATUS and m['queued']==1 and m['started']==m['consumed_FE_attempts']==0
    assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
    assert sha(R/'.gitignore')==start['gitignore_sha256']
    for x in start['local_CAE']:assert sha(R/x['path'])==x['sha256']
    for path,h in pre['protected_after'].items():
        if path not in [rel(RT/'queue.json'),rel(PROJECT/'project.db')]:assert sha(R/path)==h,path
    batch,p,integrity=freeze()
    hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity']
    assert hub.task(ids['confirm_task_id'])['execution_state']=='COMPLETED'
    for key in ['execution_audit_task_id','odb_task_id','science_task_id']:assert hub.task(ids[key])['execution_state']=='PENDING'
    ledger={'version':'run061-one-I06-queued-ledger-v1','at':now(),'authorized_total':1,'queued':1,'started':0,'consumed_FE_attempts':0,'remaining_unstarted_authorized_attempts':1,'max_datacheck':1,'max_full_after_successful_datacheck':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','job_name':p['job_name'],'inp_sha256':EXPECTED,'project_id':PID,'queue_id':m['queue_ids'][0],'queue_task_id':ids['queue_task_id'],'future_execution_audit_task_id':ids['execution_audit_task_id'],'future_ODB_task_id':ids['odb_task_id'],'future_MAIN_science_task_id':ids['science_task_id'],'future_tasks_state':'PENDING; explicit user completion notification required','comparison_contract_sha256':batch['comparison_contract_sha256'],'no_other_job_or_transfer':True,'queue_is_not_execution':True}
    save(P/'authorization_ledger_queued.json',ledger)
    save(P/'preservation_final.json',{'at':now(),'git_head':git('rev-parse','HEAD'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':[{'path':x['path'],'sha256':sha(R/x['path']),'bytes':(R/x['path']).stat().st_size} for x in start['local_CAE']],'source_integrity':integrity,'Git_index_changed_this_run':False,'status':git('status','--short')})
    report=f'''# run_061 — I06数值分辨率验证：单Job授权入队

时间：{now()}。**WARNING / {STATUS}**。本轮只完成Phase1。

## 实际授权和输入

用户当前消息明确批准run060唯一冻结输入，各最多一次Datacheck，成功后最多一次Full，14CPU/0GPU、零自动重试、用户GUI手动启动。未将旧准备清单中的execution_authorized=false改写；新的执行授权单独登记于本Run。

Job：{p['job_name']}。
Queue ID：{m['queue_ids'][0]}。
Project ID：{PID}。
Project：{PROJECT}。
INP：{p['inp_absolute_path']}。
INP完整SHA-256：{EXPECTED}。
Working Directory：{p['working_dir_absolute']}。

run060清单SHA-256 {sha(FROZEN)}。19项冻结静态文件、65项有界来源记录及run060输出逐项复核；原I06 INP/ODB身份匹配。逐字节逆转唯一max increment .0025→.00125和两处批准的身份注释后恢复源输入。34行塑性表字节完全相同，覆盖p0–.9，单调；E210GPa/nu.3、初始.001、min1e-12、time1、inc999999，以及几何/网格/接触/摩擦/BC/加载/输出均保持。无INCLUDE等外部输入依赖，独立工作目录空。

## 当前工程核验

实际AbqJobPilot0.2.2公开API，正式Project与PERSISTED Settings严格匹配；Abaqus2024执行入口存在，14CPU0GPU，DC/Full开启，无配置改写。Runner ownership ABSENT、Runtime CLEAN/IDLE、Solver进程证据CLEAR，无阻塞恢复冲突。旧D09无活动进程的隔离历史锁如存在保留，不清理。目标不存在历史执行/重复提交/输出冲突；入队前可执行项0。

当前Preflight PREVIEW_READY和Dry-run DRY_RUN_READY，1/1通过，无错误；预检前后Queue、Project DB、Settings及冻结文件保护哈希相同。预览不代表实际Abaqus语法、许可证或收敛验证。

通过公开enqueue(request,dry_run=False)仅提交一次，submission_mode=enqueue_only、allow_solver_submit=False，正式协调锁下核验空Queue后提交。没有直接编辑Queue JSON/Project DB。回读Queue/History/status/outputs：恰好1个可执行Job，为本候选QUEUED，queue_id、路径、哈希、14CPU0GPU/DCFull全部对应；无启动/结束时间、无ODB/LCK，工作目录仍空，API solver_started=False、runner_started=False。实际启动/消耗0，授权1次尚未启动，不含其他Job。

自动重试0绑定授权、Hub任务、请求metadata及Queue notes；公开JobRequest没有单独retry字段，未虚构设置。当前Runner仅选择QUEUED/DATACHECK_OK，不自动重新提交终态失败项。实际runner_core.py SHA {pre['runner_source_sha256']}，失败/警告后不提供可靠自动停整个Queue逻辑，保留AUTO_STOP_UNAVAILABLE；本次仅有一个可执行项。未修改Runner源码。

## AgentHub与停止点

MAIN预算任务{ids['budget_task_id']}、唯一enqueue任务{ids['queue_task_id']}、回读确认任务{ids['confirm_task_id']}已完成其登记/入队范围。未来MAIN执行审计{ids['execution_audit_task_id']}、ODB只读任务{ids['odb_task_id']}及MAIN独立复核任务{ids['science_task_id']}仍PENDING，按依赖和用户完成通知门控，不冒称已经提取、审阅或唤醒ODB会话。没有授予Agent start_solver权限，未调用旧Hub外部动作执行器或直接修改SQLite。

用户应在正确Project核对唯一Job后手动点击一次Start Queue。Phase1到此停止，不主动轮询、不执行Phase2，不启动Solver/Datacheck。若求解失败或身份不清，后续保留证据、不重试不补跑。

## 冻结科研边界

比较协议run060 SHA {batch['comparison_contract_sha256']}保持；未来统一原0–1.2mm/241点，run017-exploratory-fd-v1，Fref1428.9N、等权/线性/无平滑移零外推。R分母使用完整3.092632613282926N RMS，0.1/.25/.5仅探索风险提示，不是正式收敛门槛。当前未计算未来FD/PEEQ/Loss/R，未读取新的ODB。

I06仍QUALIFIED_WITH_LIMITATIONS，未证明独立时间步收敛；中心相邻细化不能充当P01–P04误差上界或已收敛Jacobian。run059耦合、LIMITED/PARTIAL结论不改变；不训练预测器、不改变特征或材料，真实材料验证NOT_EVALUABLE。run046冻结、run047/048历史及先前信息暴露声明保持，无拉伸或封存分析访问。Git HEAD、暂存两CAE索引删除、.gitignore及两本地CAE完整保持，无Git清理/commit/push。
'''
    write(P/'phase1_report.md',report)
    files=[x for x in sorted(A.rglob('*')) if x.is_file() and x.name not in ['task_ids.json','evidence_manifest.json','agenthub_completion_receipt.json'] and not x.name.startswith('lease_') and '__pycache__' not in x.parts]
    save(P/'evidence_manifest.json',{'version':'run061-phase1-static-evidence-v1','at':now(),'files':[{'path':rel(x),'sha256':sha(x),'bytes':x.stat().st_size} for x in files],'excluded':'self, private session/lease tokens, later receipt, live Run/index/status'})
    close=hub.create_task(actor['agent_id'],'MAIN','record_I06_phase1_queued_handoff',{'run':'run_061','queue_id':m['queue_ids'][0],'authorization_sha256':sha(P/'authorization_scope.json'),'phase2_requires_user_completion':True},'run061-phase1-closeout-v1',depends=(ids['confirm_task_id'],))
    lease=hub.claim(close['task_id'],actor,'run061-closeout-claim-v1');receipts=[]
    for x in files+[P/'evidence_manifest.json']:
        row=hub.artifact(close['task_id'],actor['agent_id'],x,{'run':'run_061','scope':'actual queue-only handoff; future FE unstarted'},version='run061-phase1-v1');receipts.append({'path':rel(x),'sha256':row['sha256']})
    body={'status':STATUS,'queue_id':m['queue_ids'][0],'job_name':p['job_name'],'inp_sha256':EXPECTED,'report_path':rel(P/'phase1_report.md'),'report_sha256':sha(P/'phase1_report.md'),'queued':1,'started':0,'consumed':0,'manual_GUI_start_required':True,'phase2_waits_user_completion':True}
    message=hub.message(close['task_id'],actor['agent_id'],'MAIN',body,'run061-phase1-handoff-v1');hub.finish(lease,body,evidence_state='RECORDED',science_state='NOT_EVALUATED');assert hub.verify_chain()
    save(P/'agenthub_completion_receipt.json',{'at':now(),'closeout_task_id':close['task_id'],'budget_task_id':ids['budget_task_id'],'queue_task_id':ids['queue_task_id'],'confirm_task_id':ids['confirm_task_id'],'future_audit_task_id':ids['execution_audit_task_id'],'future_ODB_task_id':ids['odb_task_id'],'future_science_task_id':ids['science_task_id'],'phase1':hub.task(close['task_id']),'registered_artifacts':receipts,'message_id':message['message_id'],'audit_chain_valid':True,'no_cross_chat_reception_claim':True})
    write(RUN/'summary.md',f'''# run_061 — I06唯一细化Job授权入队

**WARNING / {STATUS}。** 当前Preflight/Dry-run及冻结完整性通过，唯一Job {p['job_name']} 已通过公开API入队，queue_id `{m['queue_ids'][0]}`。14CPU/0GPU、一次DC成功后Full、零自动重试、用户GUI手动启动。可执行项仅1、启动和FE消耗0，目标目录仍空。

见[第一阶段报告](artifacts/private/phase1_report.md)、[Queue清单](artifacts/private/queue_manifest.json)、[授权台账](artifacts/private/authorization_ledger_queued.json)、[AgentHub收据](artifacts/private/agenthub_completion_receipt.json)。来源为run060冻结候选；没有生成或修改任何INP。

I06保持QUALIFIED_WITH_LIMITATIONS；AUTO_STOP_UNAVAILABLE保留。当前停止，等待用户手动Start Queue。只有用户明确通知结束后才开展MAIN执行审计→真实ODB只读提取→MAIN独立复核和R分析，未来任务均PENDING。本次不执行Phase2，不追加Job、重试或启动Solver/Datacheck。历史科研/Git保护保持。
''')
    important=[P/'queue_manifest.json',P/'authorization_scope.json',P/'authorization_ledger_queued.json',P/'phase1_report.md',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json']
    save(A/'manifest.json',{'version':'run061-phase1-artifacts-v1','files':[{'path':rel(x),'sha256':sha(x),'private':True} for x in important]})
    j=read(RUN/'run.json');save(RUN/'checkpoints/run_before_phase1_close.json',j)
    j.update(status='WARNING',end_time=now(),outcome=STATUS,outputs=[{'path':rel(x),'role':'phase1 execution and queue evidence','sha256':sha(x)} for x in important],validation=[{'check':'frozen identity and exact allowlisted difference','status':'PASS','evidence':rel(P/'freeze_integrity.json'),'scope':'one exact SHA; only max increment and2comments'},{'check':'public current Preflight and Dry-run','status':'PASS','evidence':rel(P/'precheck.json'),'scope':'PERSISTED,14CPU0GPU,1/1 previews'},{'check':'unique unstarted queue readback','status':'PASS','evidence':rel(P/'queue_manifest.json'),'scope':'one QUEUED, no other executable items, no starts'}],authorized_attempts=1,queued=1,started=0,consumed_FE_attempts=0,automatic_retries=0,queue_ids=m['queue_ids'],agenthub_budget_task=ids['budget_task_id'],agenthub_closeout_task=close['task_id'],phase2_status='NOT_STARTED_AWAIT_USER_COMPLETION_NOTIFICATION',new_solver_datacheck_started=False,new_INP=0,tensile_access=False)
    temp=RUN/'run.json.tmp';write(temp,json.dumps(j,ensure_ascii=False,indent=2)+'\n');read(temp);temp.replace(RUN/'run.json')
    index=R/'run/README.md';old=index.read_bytes();assert b'run_061' not in old;write(P/'run_index_before.txt',old.decode('utf-8'))
    index.write_bytes(old+('\n\n## 新授权 Run — run_061\n\n| Run | 阶段 | 目标 | 状态 | 总结 |\n| --- | --- | --- | --- | --- |\n| run_061 | I06 single refinement queue-only | run060唯一冻结输入授权核验、公开API入队 | WARNING（等待人工启动） | [summary](run_061/summary.md) |\n\n1/1预检通过，仅1个QUEUED；实际启动/消耗0。Phase1结束，等待用户GUI Start Queue及完成通知，Phase2未执行。\n').encode())
    status=R/'status/PROJECT_STATUS.md';old=status.read_bytes();first=old.find(b'\n')+1;assert first>0;write(P/'project_status_before.txt',old.decode('utf-8'))
    note=f'\n## 当前状态 — run_061（{now()[:10]}，Asia/Shanghai）\n\n**WARNING / {STATUS}。** run060唯一冻结I06最大增量.00125输入完整核验、PERSISTED Settings和当前Preflight/Dry-run通过；公开API仅入队1项，实际启动/FE消耗0，14CPU0GPU、单次DC成功后Full、零重试。详见[run_061](../run/run_061/summary.md)。用户GUI手动Start Queue；当前停止，Phase2等待明确完成通知。I06限制、run059结论、历史冻结/Git保护均保持。\n'
    status.write_bytes(old[:first]+note.encode()+old[first:])
    save(RUN/'checkpoints/phase1_completed.json',{'at':now(),'status':STATUS,'queue_ids':m['queue_ids'],'queued':1,'started':0,'consumed':0,'report_sha256':sha(P/'phase1_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'Git_staged_preserved':git('diff','--cached','--name-status')==start['git']['staged'],'future_tasks':'PENDING','stop_active_execution':True})
    print(json.dumps({'status':STATUS,'queue_id':m['queue_ids'][0],'report_sha256':sha(P/'phase1_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'AgentHub':'RECORDED_CHAIN_VALID','started':0,'consumed':0}))

if __name__=='__main__':main()
