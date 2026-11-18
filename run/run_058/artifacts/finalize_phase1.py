"""Finalize queue-only Run evidence; no polling, solver or post-run evaluation."""
from queue_prospective import *
import shutil

def write(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text)

def main():
    m=read(P/'queue_manifest.json');ids=read(P/'task_ids.json');start=read(RUN/'checkpoints/start.json');pre=read(P/'precheck.json');frozen=read(FROZEN)
    assert m['status']=='FOUR_PROSPECTIVE_JOBS_QUEUED_AWAITING_MANUAL_START'
    assert m['queued']==4 and m['started']==m['consumed_FE_attempts']==0
    assert len(set(m['queue_ids']))==4 and m['order']==frozen['order']
    assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
    assert sha(R/'.gitignore')==start['gitignore_sha256']
    for model in start['local_CAE']:assert sha(R/model['path'])==model['sha256']
    for p in frozen['points']:assert sha(R/p['inp_path'])==p['inp_sha256'] and not any((R/p['working_dir']).iterdir())
    model=read(P/'predictor_identity_verified.json');assert sha(R/frozen['predictor_package_path'])==model['package_sha256']
    for path,h in pre['protected_after'].items():
        if path not in [rel(RT/'queue.json'),rel(PROJECT/'project.db')]:assert sha(R/path)==h,path
    hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    assert hub.task(ids['confirm_task_id'])['execution_state']=='COMPLETED'
    assert hub.task(ids['execution_audit_task_id'])['execution_state']=='PENDING'
    assert all(hub.task(t)['execution_state']=='PENDING' for t in ids['odb_task_ids'].values())
    assert hub.task(ids['science_task_id'])['execution_state']=='PENDING'
    ledger={'version':'run058-authorization-ledger-queued-v1','at':now(),'authorized_total':4,'queued':4,'started':0,'consumed_FE_attempts':0,'remaining_unstarted_authorized_attempts':4,'attempt_limit_per_input':1,'datacheck_limit_per_input':1,'full_limit_after_successful_datacheck':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','AUTO_STOP_UNAVAILABLE':True,'queue_is_not_execution':True,'order':m['order'],'queue_ids':m['queue_ids'],'point_tasks':ids['point_tasks'],'future_execution_audit_task_id':ids['execution_audit_task_id'],'future_ODB_tasks':ids['odb_task_ids'],'future_MAIN_science_task_id':ids['science_task_id'],'future_tasks_state':'PENDING_DEPENDENCY_AND_USER_NOTIFICATION','identity_binding':{'manifest_sha256':sha(FROZEN),'comparison_contract_sha256':frozen['comparison_contract_sha256'],'predictor_package_sha256':model['package_sha256'],'frozen_model_sha256':model['model_sha256'],'training_25_data_sha256':model['training_data_sha256']},'no_fifth_job_or_transfer':True}
    save(P/'authorization_ledger_queued.json',ledger)
    report=['# run058 — 四点前瞻识别批次入队与人工启动交接','',f'记录时间：{now()}。**FOUR_PROSPECTIVE_JOBS_QUEUED_AWAITING_MANUAL_START**。执行前检查及Queue-only阶段通过，整体WARNING保留AUTO_STOP_UNAVAILABLE与I06限制。','',
        '## 本轮实际范围','',
        '用户明确批准run057四份冻结输入各最多一次DC成功后Full、14CPU0GPU、零自动重试、单Runner串行、用户GUI手动启动；接受单项失败后队列可能继续。本Run只执行第一阶段，不启动Solver/datacheck，不进入真实新ODB提取或A/B评价。','',
        '## 冻结完整性、基准与预测器','',
        'run057 prepared_batch及62项静态证据、131项既有来源记录均校验；四个完整INP哈希、材料/参数JSON/生成器/表数据及来源一致。逐字节复核仅原允许的塑性表与三处身份注释变化，其余几何/网格/摩擦/接触/BC/加载/输出不变。材料表严格单调，Pa/无量纲塑性应变，覆盖0–.9，原容差和表行数未变。初始.001、最大.0025、最小1e-12、time1、inc999999保持。工作目录独立且全空，没有INCLUDE依赖。',
        'I06原INP/ODB与完整F–D提取身份一致，保留QUALIFIED_WITH_LIMITATIONS、原cutback/警告和历史进程证明缺口。没有独立时间步收敛认证，不升级NUMERICALLY_CONVERGED，不提交中心Job。',
        f'预测器ZIP完整SHA为{model["package_sha256"]}；原最终模型SHA为{model["model_sha256"]}；训练25点数据SHA为{model["training_data_sha256"]}。ZIP路径安全/内容和文件清单hash全部通过；实际加载两载荷、五特征、完整曲线Ridge及常数I06，在既有I06曲线上验证只推理入口可运行。无新拟合、调参、特征修改或新FE结果访问。冻结训练IDs/标准化/系数/lambda/训练代码与run056/057 A/B协议完整绑定。','',
        '## 当前工程预检','',
        '当前实际安装AbqJobPilot0.2.2公开API，正式Project ID b87d2cd6-8519-4ac3-bae6-7eb989fb2dae、Project根目录与Settings身份一致。Settings严格返回PERSISTED，Abaqus2024 bat存在，14CPU/0GPU、DC=True/Full=True；未修改配置。Runtime CLEAN/IDLE，Runner ownership ABSENT、无活动Solver进程或未解决恢复冲突。旧D09历史锁如存在保留隔离，不清理、不复用。',
        '四项重新Preflight PREVIEW_READY和Dry-run DRY_RUN_READY，4/4通过；预检阶段Queue/Settings等保护哈希未变。所有候选历史/当前身份无重复且工作位置无冲突，正式入队前无其他可执行任务。预览不是Abaqus真实语法、许可证、收敛或物理验证。','',
        '## 实际Queue-only提交','',
        '|顺序|候选|Job|queue_id|状态|完整INP SHA-256|','|---:|---|---|---|---|---|']
    for p in m['points']:report.append(f'|{p["position"]}|{p["candidate_id"]}|{p["job_name"]}|{p["queue_id"]}|QUEUED|{p["inp_sha256"]}|')
    report+=['',
        '每次通过公开enqueue(request,dry_run=False)且submission_mode=enqueue_only、allow_solver_submit=False；使用正式协调锁防止检查/写入竞态，未直接编辑queue.json/project.db。每项单独保存request、response、queue_id与Hub收据，并在下一项前核验Queue前缀顺序。提交checkpoint禁止未知/部分结果自动重放；发现已有完整同身份QUEUED批次时只核验复用，不能重复提交。',
        '提交后公开Queue/History/status/locate_outputs回读：恰好4项本批可执行，顺序P01→P02→P03→P04；四个queue_id唯一，14CPU0GPU、DC/Full开启，路径和INP hash一致。未启动时间、未结束时间，无ODB/LCK，四工作目录仍空；API返回solver_started=False、runner_started=False。没有额外任务、没有I06重算。',
        '自动重试0是本次授权与Runner执行合同：API没有单独retry参数，已在任务/请求metadata与Queue notes绑定single attempt/zero retries；当前Runner从QUEUED/DATACHECK_OK选择下一项，不自动重新入队终态失败项。并非伪称修改了不存在的重试设置。队列写入不是已消费FE尝试，当前4授权/4QUEUED/0启动/0消耗。','',
        '## AUTO_STOP_UNAVAILABLE与停止点','',
        f'实际本机runner_core.py SHA-256 {pre["runner_source_sha256"]}。当前_run_loop调用run_next_job后不根据失败/警告返回值决定停队列；Stop After Current是用户请求标志，不能冒充自动fail-stop。单项失败或警告后其他项仍可能继续，用户已接受。未修改AbqJobPilot代码，未替用户启动。',
        '请用户在正确Project核对四个Job后手动点击一次Start Queue。第一阶段到此停止；不继续主动监控、唤醒或执行第二阶段。用户通知完成后，MAIN先核验真实终态/尝试/输出，再由真实ODB会话经AgentHub领取只读任务。失败/不评分保留null，不补跑，不扩预算。','',
        '## AgentHub与未来研究门控','',
        f'预算任务：{ids["budget_task_id"]}；当前队列确认任务：{ids["confirm_task_id"]}。每候选有独立授权enqueue任务和Queue证据；用户完成后的MAIN执行审计任务 {ids["execution_audit_task_id"]} 仍PENDING，四个ODB任务依赖该审计，MAIN独立复核/科学评价依赖真实ODB完成。没有假称任何ODB Agent已领取、提取或MAIN已获新科研结果。',
        '后续保持run056/057预注册A局部割线与B冻结模型预测规则，无重训/新特征选择。保留半步分辨目标和常数基线、P03凸包外标记、正式Fisher置信区间NOT_EVALUABLE；本轮没有提前计算新响应敏感性/预测误差。真实材料验证仍NOT_EVALUABLE。',
        'Git HEAD/暂存索引与.gitignore不变，2份本地CAE完整；用户既有project.db/工作树改动不清理不覆盖。未读拉伸或封存分析，run046冻结、run047/048历史和run055–057历史保持；保留run015暴露声明。无commit/push/reset/clean、无新INP、无额外Job、无BO/DE/RL。AgentHub正式接口记录全部证据，数据库消息不代表其他Codex会话已自动收到/唤醒。','']
    write(P/'phase1_report.md','\n'.join(report))
    save(P/'git_preservation_final.json',{'at':now(),'head':git('rev-parse','HEAD'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':[{'path':p['path'],'sha256':sha(R/p['path'])} for p in start['local_CAE']],'local_models_intact':True,'Git_index_changed_this_run':False,'status':git('status','--short')})
    files=[p for p in sorted(A.rglob('*')) if p.is_file() and p.name not in ['task_ids.json','evidence_manifest.json','agenthub_completion_receipt.json'] and not p.name.startswith('lease_') and p.name!='confirm_lease.json' and '__pycache__' not in p.parts]
    save(P/'evidence_manifest.json',{'version':'run058-phase1-static-evidence-v1','at':now(),'files':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],'excludes':['self','session/lease tokens','later Hub receipt','live Run/index/status metadata']})
    close=hub.create_task(ids['identity']['agent_id'],'MAIN','record_phase1_queued_budget_and_handoff',{'run':'run_058','queue_ids':m['queue_ids'],'authorization_sha256':sha(P/'authorization_scope.json'),'phase2_must_wait_user_notification':True},'run058-phase1-closeout-v1',depends=(ids['confirm_task_id'],))
    lease=hub.claim(close['task_id'],ids['identity'],'run058-closeout-claim-v1')
    receipts=[]
    for path in files+[P/'evidence_manifest.json']:
        row=hub.artifact(close['task_id'],ids['identity']['agent_id'],path,{'run':'run_058','scope':'phase1 queue-only evidence; future FE unstarted'},version='run058-phase1-v1');receipts.append({'path':rel(path),'sha256':row['sha256']})
    body={'status':m['status'],'queue_ids':m['queue_ids'],'order':m['order'],'queued':4,'started':0,'consumed':0,'report_path':rel(P/'phase1_report.md'),'report_sha256':sha(P/'phase1_report.md'),'manual_GUI_start_required':True,'phase2_waits_user_completion':True}
    message=hub.message(close['task_id'],ids['identity']['agent_id'],'MAIN',body,'run058-phase1-handoff-v1')
    hub.finish(lease,body,evidence_state='RECORDED',science_state='NOT_EVALUATED');assert hub.verify_chain()
    save(P/'agenthub_completion_receipt.json',{'at':now(),'closeout_task_id':close['task_id'],'budget_task_id':ids['budget_task_id'],'point_task_ids':ids['point_tasks'],'confirm_task_id':ids['confirm_task_id'],'future_audit_task_id':ids['execution_audit_task_id'],'future_ODB_task_ids':ids['odb_task_ids'],'future_science_task_id':ids['science_task_id'],'phase1':hub.task(close['task_id']),'registered_artifacts':receipts,'outbox_message_id':message['message_id'],'audit_chain_valid':True,'no_cross_chat_reception_claim':True})
    write(RUN/'summary.md','# run_058 — 四点前瞻识别授权入队\n\n**WARNING / FOUR_PROSPECTIVE_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户授权run057四份冻结INP各一次DC成功后Full、14CPU0GPU、零自动重试、用户GUI启动，接受AUTO_STOP_UNAVAILABLE。当前4/4 Preflight、4/4 Dry-run及预测器冻结复核通过；公开API按P01→P04仅入队四项，queue_id唯一、无其他可执行任务。实际启动/消耗0，四输出目录空。\n\n见[Queue清单](artifacts/private/queue_manifest.json)、[第一阶段报告](artifacts/private/phase1_report.md)、[授权台账](artifacts/private/authorization_ledger_queued.json)、[AgentHub收据](artifacts/private/agenthub_completion_receipt.json)。I06保持QUALIFIED_WITH_LIMITATIONS，未来A/B协议与预测器不改。\n\n第一阶段已结束，等待用户在正确Project GUI手动Start Queue；不自行求解或主动开始第二阶段。真实结果审计、ODB提取和前瞻评价仍待用户通知完成后开展，无额外Job/重试/优化/拉伸读取/Git提交。\n')
    important=[P/'queue_manifest.json',P/'authorization_scope.json',P/'authorization_ledger_queued.json',P/'phase1_report.md',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json']
    save(A/'manifest.json',{'version':'run058-phase1-artifacts-v1','files':[{'path':rel(p),'sha256':sha(p),'private':True} for p in important]})
    j=read(RUN/'run.json');shutil.copyfile(RUN/'run.json',RUN/'checkpoints/run_before_phase1_close.json')
    j.update(status='WARNING',end_time=now(),outcome=m['status'],outputs=[{'path':rel(p),'role':'phase1 queue-only evidence','sha256':sha(p)} for p in important],validation=[{'check':'frozen inputs and predictors','status':'PASS','evidence':rel(P/'predictor_identity_verified.json'),'scope':'4 source INPs, 25 sample model, frozen protocol; no retraining'},{'check':'current public previews','status':'PASS','evidence':rel(P/'precheck.json'),'scope':'4/4 Preflight and 4/4 Dry-run; PERSISTED/14CPU0GPU'},{'check':'queue consistency','status':'PASS','evidence':rel(P/'queue_manifest.json'),'scope':'4 unique QUEUED in frozen order, zero actual starts'},{'check':'I06 precision reference','status':'QUALIFIED_WITH_LIMITATIONS','evidence':'run/run_057/artifacts/private/I06_baseline_audit.json','scope':'no independent time-step convergence claim'}],authorized_attempts=4,queued=4,started=0,consumed_FE_attempts=0,automatic_retries=0,new_INP=0,agenthub_budget_task=ids['budget_task_id'],agenthub_closeout_task=close['task_id'],queue_ids=m['queue_ids'],phase2_status='NOT_STARTED_AWAIT_USER_COMPLETION_NOTIFICATION',new_solver_datacheck_started=False,tensile_access=False)
    temp=RUN/'run.json.tmp';temp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(temp);temp.replace(RUN/'run.json')
    index=R/'run/README.md';content=index.read_bytes();assert b'run_058' not in content
    extra='\n\n## 新授权 Run — run_058\n\n| Run | 阶段 | 目标 | 状态 | 总结 |\n| --- | --- | --- | --- | --- |\n| run_058 | Four-point prospective identification queue-only | 四项冻结身份/预测器核验、授权登记与公开API入队 | WARNING（等待人工启动） | [summary](run_058/summary.md) |\n\n4/4预检和Dry-run通过，按P01→P04仅入队四项、实际启动/FE消耗0。等待用户GUI Start Queue；AUTO_STOP_UNAVAILABLE风险已接受，第二阶段尚未开展。\n'
    index.write_bytes(content+extra.encode())
    status=R/'status/PROJECT_STATUS.md';content=status.read_bytes();header='# SMALL-PUNCH 项目状态\r\n'.encode();assert content.startswith(header)
    note='\r\n## 当前状态 — run_058（2026-10-27，Asia/Shanghai）\r\n\r\n**WARNING / FOUR_PROSPECTIVE_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户已授权run057四个冻结Job一次性queue-only提交，14CPU0GPU、每项一次DC成功后Full、零自动重试、用户GUI启动。4/4当前Preflight/Dry-run及冻结预测器复核通过，真实四queue_id按P01→P04回读均QUEUED、实际启动/消耗0。详见[run_058](../run/run_058/summary.md)。I06限制、AUTO_STOP_UNAVAILABLE和历史边界保留；当前停止等待用户手动启动，不自动执行第二阶段。\r\n'
    status.write_bytes(header+note.encode()+content[len(header):])
    save(RUN/'checkpoints/phase1_completed.json',{'at':now(),'status':m['status'],'queue_ids':m['queue_ids'],'queued':4,'started':0,'consumed':0,'report_sha256':sha(P/'phase1_report.md'),'git_staged_preserved':git('diff','--cached','--name-status')==start['git']['staged'],'future_tasks':'PENDING','no_further_active_work':True})
    print(json.dumps({'status':m['status'],'queue_ids':m['queue_ids'],'report_sha256':sha(P/'phase1_report.md'),'future_ODB_tasks':'PENDING','started':0,'consumed':0,'Git_staged_preserved':True}))

if __name__=='__main__':main()
