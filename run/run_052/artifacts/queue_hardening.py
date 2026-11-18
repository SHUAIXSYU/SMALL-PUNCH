"""Two frozen run051 hardening inputs: official queue-only API, never Solver.

Reuses verified read-only Project/Runner checks from run041. Only enqueue() can
change the external Queue, with a durable no-replay marker and public API.
"""
from pathlib import Path
import sys,json,hashlib,re,traceback
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_052';A=RUN/'artifacts';P=A/'private';RECEIPTS=P/'queue_receipts'
HELPER=R/'run/run_041/artifacts/queue_pilot.py';sys.path.insert(0,str(HELPER.parent));import queue_pilot as q
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.runtime_coordination import queue_transaction
from agenthub_sp_invopt.hub import Hub
read=q.read;sha=q.sha;save=q.save;now=q.now;rel=q.rel
PROJECT=q.PROJECT;RT=q.RT;PID=q.PID
FROZEN=R/'run/run_051/artifacts/prepared_batch.json';ORDER=['SPIO_R051_H01_LOW','SPIO_R051_H02_HIGH']

def points():
    frozen=read(FROZEN);old=read(R/'run/run_051/run.json');expected={v['path']:v.get('sha256') for v in old['outputs']}
    assert sha(FROZEN)==expected[rel(FROZEN)] and frozen['project_id']==PID and frozen['order']==ORDER
    assert frozen['resources']=={'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0}
    contract=read(R/frozen['material_contract_path']);assert sha(R/frozen['material_contract_path'])==frozen['material_contract_sha256']
    assert sha(R/frozen['comparison_contract_path'])==frozen['comparison_contract_sha256']
    assert contract['p_switch']==.09774053167903649 and contract['amplitude_a']==.5 and contract['transition_width']==.05
    assert contract['E_pa']==210e9 and contract['nu']==.3 and contract['coverage']==[0,.9]
    assert sha(R/contract['implementation'])==contract['implementation_sha256']
    sys.path.insert(0,str((R/contract['implementation']).parent));from highp_envelope import plastic_block
    source=R/contract['source_inp'];assert sha(source)==contract['source_inp_sha256'];prefix,suffix,base,texts=plastic_block(source.read_bytes())
    result=[]
    for p,c in zip(frozen['points'],contract['points']):
        assert p['candidate_id']==c['candidate_id'] and p['job_name']==c['job_name'] and p['table_rows']==82
        inp=R/p['inp_path'];work=R/p['working_dir'];raw=inp.read_bytes();ap,bp,rows,rowtexts=plastic_block(raw)
        assert inp.resolve()==Path(p['inp_absolute_path']).resolve() and work.resolve()==Path(p['working_dir_absolute']).resolve()
        assert sha(inp)==p['inp_sha256'] and inp.stem==p['job_name']
        assert ap==prefix and bp==suffix and raw==prefix+(R/c['plastic_rows_path']).read_bytes()+suffix
        assert sha(R/c['plastic_rows_path'])==c['plastic_rows_sha256'] and sha(R/c['table_path'])==c['table_sha256']
        assert len(rows)==82 and rows[0]==base[0] and rows[-1][1]==.9
        assert all(b[0]>a[0] and b[1]>a[1] for a,b in zip(rows,rows[1:]))
        assert all(rowtexts[v]==texts[v] for _,v in base if v<=contract['p_switch'])
        assert raw.count(b'0.001, 1., 1e-12, 0.00125')==1 and re.search(rb'(?im)^\*step\b[^\r\n]*\binc=999999\b',raw)
        assert b'*Node Output, nset=ASM_SPT.set_punch_rp' in raw and b'RF2, U2' in raw
        assert not re.search(rb'(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b',raw)
        assert work.is_dir() and not any(work.iterdir()) and not (R/p['expected_odb']).exists()
        result.append({**p,'low_branch_sigma_y_mpa':contract['low_branch_sigma_y_mpa'],'low_branch_n':contract['low_branch_n'],'E_pa':contract['E_pa'],'nu':contract['nu'],'p_switch':contract['p_switch'],'transition_width':contract['transition_width'],'material_contract':contract['version'],'all_nonplastic_bytes_identical':True})
    assert len(result)==2 and [p['job_name'] for p in result]==ORDER and len({p['working_dir'] for p in result})==2
    return result

def queue_guard(scoped,api,pts,prefix):
    queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
    assert queue['status']==history['status']=='OK' and not queue['errors'] and not history['errors']
    assert all(j['raw_status'] in q.EXECUTABLE|q.ACTIVE|q.HISTORICAL for j in queue['jobs'])
    assert not [j for j in queue['jobs'] if j['raw_status'] in q.ACTIVE]
    active=[j for j in queue['jobs'] if j['raw_status'] in q.EXECUTABLE]
    assert [j['job_name'] for j in active]==[p['job_name'] for p in pts[:prefix]],'Unauthorized executable Queue/job order'
    details=[]
    for i,p in enumerate(pts):
        same=[j for j in queue['jobs'] if j['job_name'].casefold()==p['job_name'].casefold() or Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve() or Path(j['work_dir']).resolve()==(R/p['working_dir']).resolve()]
        assert len(same)==(1 if i<prefix else 0),'Existing candidate/attempt or identity conflict; no duplicate submission'
        hist=[j for j in history['jobs'] if j['job_name'].casefold()==p['job_name'].casefold() or Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve()]
        if i<prefix:
            j=same[0];assert j['raw_status']==j['status']=='QUEUED' and not j.get('started_at') and not j.get('ended_at')
            assert Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve() and Path(j['work_dir']).resolve()==(R/p['working_dir']).resolve()
            assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True) and p['inp_sha256'] in (j.get('notes') or '')
        assert len(hist)<=1
        for item in hist:
            assert i<prefix,'Candidate history without authorized queued identity'
            detail=api.show_job(item['job_id'],project_id=PID).to_dict();runs=detail['runs'];assert len(runs)==1
            rr=runs[0];assert rr['queue_id']==same[0]['queue_id'] and rr['raw_status']=='QUEUED' and not rr['started_at'] and not rr['completed_at']
            details.append(detail)
    return {'queue':queue,'history':history,'unstarted_GUI_history_placeholders':details,'executable_count':len(active),'queue_ids':[j['queue_id'] for j in active]}

def req(p,task):
    return JobRequest(inp_path=str((R/p['inp_path']).resolve()),job_name=p['job_name'],working_dir=str((R/p['working_dir']).resolve()),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run052_two_authorized_hardening_scenarios',strategy='frozen_H01_H02_batch_user_GUI_start',metadata={'project_id':PID,'task_id':task,'candidate_id':p['candidate_id'],'inp_sha256':p['inp_sha256'],'max_started_attempts':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','notes':f"run052 {p['candidate_id']}; inp_sha256={p['inp_sha256']}; task_id={task}; Project={PID};14CPU0GPU;one Datacheck then Full;zero retries;USER_GUI_ONLY;AUTO_STOP_UNAVAILABLE accepted"})

def init():
    assert not (RUN/'run.json').exists() and sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
    start={'at':now(),'git':{'branch':q.git('branch','--show-current'),'head':q.git('rev-parse','HEAD'),'remote':q.git('remote','-v'),'working_tree':q.git('status','--short')},'python':sys.executable,'python_version':sys.version.split()[0],'readonly_helper_path':rel(HELPER),'readonly_helper_sha256':sha(HELPER)}
    save(RUN/'checkpoints/start.json',start)
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_052','stage':'Authorized hardening-envelope two-job queue-only handoff','objective':'record scoped authorization, verify current frozen identities/runtime/previews, enqueue two only and stop','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[{'path':rel(FROZEN),'role':'immutable run051 frozen inputs','sha256':sha(FROZEN)}],'outputs':[],'validation':[],'errors':[]})
    pts=points()
    auth={'version':'run052-two-frozen-hardening-manual-GUI-authorization-v1','source':{'type':'explicit current user chat instruction','title':'SP-InvOpt｜High-Strain Hardening Envelope — Authorised Execution & Sensitivity Analysis','message_id':None},'project_id':PID,'project_path':rel(PROJECT),'prepared_batch_path':rel(FROZEN),'prepared_batch_sha256':sha(FROZEN),'material_contract_sha256':read(FROZEN)['material_contract_sha256'],'comparison_contract_path':read(FROZEN)['comparison_contract_path'],'comparison_contract_sha256':read(FROZEN)['comparison_contract_sha256'],'points':pts,'max_started_attempts_total':2,'max_per_input_datacheck':1,'max_per_input_full_after_datacheck_success':1,'automatic_retries':0,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'solver_start':'USER_GUI_ONLY','AUTO_STOP_UNAVAILABLE_accepted':True,'batch_continue_after_individual_failure_accepted':True,'third_job_or_budget_transfer_allowed':False,'queued_is_not_started_or_FE_budget_consumed':True,'phase2_trigger':'only after user confirms completion and MAIN audits real execution; no ODB task claimed now'}
    save(P/'authorization_scope.json',auth)
    h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=h.register('MAIN','codex-main-run052-hardening-queue')
    budget=h.create_task(identity['agent_id'],'MAIN','record_two_hardening_user_authorization',auth,'run052-two-budget-v1');lease=h.claim(budget['task_id'],identity,'run052-budget-claim-v1')
    h.artifact(budget['task_id'],identity['agent_id'],P/'authorization_scope.json',{'run':'run_052','scope':'explicit human manual-GUI-only one attempt per frozen input'},version='run052-v1');h.finish(lease,{'authorized':2,'prepared':2,'queued':0,'started':0,'consumed':0,'automatic_retries':0},evidence_state='RECORDED',science_state='NOT_EVALUATED')
    tasks={}
    for p in pts:
        t=h.create_task(identity['agent_id'],'MAIN','queue_only_frozen_hardening_input',{'run':'run_052','candidate':p,'authorization_sha256':sha(P/'authorization_scope.json'),'max_started_attempts':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY'},f"run052-enqueue-{p['candidate_id']}-v1",depends=(budget['task_id'],))
        h.approve(t['task_id'],identity['agent_id'],'enqueue');tasks[p['candidate_id']]=t['task_id']
    confirm=h.create_task(identity['agent_id'],'MAIN','confirm_two_hardening_jobs_unstarted_queue',{'run':'run_052','order':ORDER},'run052-confirm-batch-v1',depends=tuple(tasks.values()))
    audit=h.create_task(identity['agent_id'],'MAIN','audit_hardening_after_user_completion_notification',{'run':'run_052','trigger':'USER_COMPLETION_NOTIFICATION_AND_REAL_TERMINAL_AUDIT_REQUIRED','source_manifest':rel(FROZEN),'queue_evidence_path':'run/run_052/artifacts/private/queue_manifest.json','no_solver_start':True},'run052-future-execution-audit-v1',depends=(confirm['task_id'],))
    odtasks={}
    for p in pts:
        t=h.create_task(identity['agent_id'],'ODB','readonly_hardening_odb_after_MAIN_audit',{'run':'run_052','candidate':p,'authorization_sha256':sha(P/'authorization_scope.json'),'audit_task_id':audit['task_id'],'comparison_contract_path':auth['comparison_contract_path'],'comparison_contract_sha256':auth['comparison_contract_sha256'],'queue_evidence_path':'run/run_052/artifacts/private/queue_manifest.json','scope':'only real safe ODB after audit; FD, PEEQ, warnings,contact,energy,provenance; no solver/retry','output_root':'run/run_052/artifacts/private/odb/'+p['candidate_id'],'tensile_access':False},f"run052-future-odb-{p['candidate_id']}-v1",depends=(audit['task_id'],));odtasks[p['candidate_id']]=t['task_id']
    science=h.create_task(identity['agent_id'],'MAIN','review_actual_D01_H01_H02_hardening_sensitivity',{'run':'run_052','comparison_contract_path':auth['comparison_contract_path'],'no_additional_FE_authorized':True},'run052-future-science-v1',depends=tuple(odtasks.values()))
    save(P/'task_ids.json',{'identity':identity,'budget_task_id':budget['task_id'],'point_tasks':tasks,'confirm_task_id':confirm['task_id'],'execution_audit_task_id':audit['task_id'],'odb_task_ids':odtasks,'science_task_id':science['task_id']})
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID);env=q.environment(api);runtime=q.runtime_guard(deep=True)
    current=scoped.list_jobs();same=[j for j in current['jobs'] if j['job_name'] in ORDER]
    if same:
        assert len(same)==2 and all(j['raw_status']=='QUEUED' for j in same),'Existing partial/running/failed/unknown batch; stop, do not resubmit'
        queue=queue_guard(scoped,api,pts,2);save(P/'existing_queue_detected.json',{'at':now(),'status':'BOTH_ALREADY_QUEUED_DO_NOT_RESUBMIT','queue':queue})
    else:queue=queue_guard(scoped,api,pts,0)
    runner=q.ABQ/'abqjobpilot/runner_core.py';code=runner.read_text(encoding='utf-8');loop=code[code.index('    def _run_loop(self)'):]
    assert '                run_next_job(job)' in loop and 'final_verdict' not in loop and 'FAILED' not in loop
    oldrunner=read(R/'run/run_044/artifacts/private/precheck.json')
    guard=[RT/'queue.json',RT/'settings.json',PROJECT/'project.db',R/read(FROZEN)['material_contract_path'],R/read(FROZEN)['comparison_contract_path']]+[R/p['inp_path'] for p in pts]
    before={str(p):sha(p) for p in guard};previews=[]
    for p in pts:
        request=req(p,tasks[p['candidate_id']]);pre=scoped.preflight(request).to_dict();dry=scoped.enqueue(request,dry_run=True).to_dict()
        previews.append({'candidate_id':p['candidate_id'],'request':request.to_dict(),'preflight':pre,'dry_run':dry})
        assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors']
        assert dry['job_id'] is None and not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
        assert Path(pre['expected_odb_path']).resolve()==(R/p['expected_odb']).resolve()
    after={str(p):sha(p) for p in guard};assert before==after
    save(P/'precheck.json',{'at':now(),'status':'PASS_TWO_CURRENT_PREVIEWS','environment':env,'runtime':runtime,'queue_before':queue,'previews':previews,'protected_before':before,'protected_after':after,'auto_stop':'AUTO_STOP_UNAVAILABLE','runner_source_sha256':sha(runner),'same_runner_as_previous_actual_local_check':sha(runner)==oldrunner['runner_source_sha256'],'runner_source_path':str(runner),'existing_batch':bool(same),'no_solver_or_datacheck_started':True})
    print(json.dumps({'preflight':2,'dry_run':2,'runtime':'CLEAN_IDLE','existing_batch':bool(same),'started':0}))

def enqueue():
    if (P/'queue_manifest.json').exists():
        m=read(P/'queue_manifest.json');pts=points();api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
        q.environment(api);q.runtime_guard(deep=True);current=queue_guard(scoped,api,pts,2)
        assert current['queue_ids']==m['queue_ids'],'Recorded Queue identity changed; no new submission'
        print(json.dumps({'status':'EXISTING_QUEUE_VERIFIED_NO_SUBMISSION','queue_ids':m['queue_ids']}));return
    assert not (RUN/'checkpoints/enqueue_started.json').exists(),'Previous/partial submission outcome needs read-only reconciliation; never replay'
    pre=read(P/'precheck.json');assert pre['status']=='PASS_TWO_CURRENT_PREVIEWS';pts=points();ids=read(P/'task_ids.json');actor=ids['identity'];h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID);q.environment(api);q.runtime_guard(deep=True)
    prior=pre['existing_batch'];queue_guard(scoped,api,pts,2 if prior else 0)
    save(RUN/'checkpoints/enqueue_started.json',{'at':now(),'queue_submission_attempt':0 if prior else 1,'FE_attempts_started':0,'do_not_retry':True,'reusing_already_queued_batch':prior})
    receipts=[]
    for i,p in enumerate(pts):
        tid=ids['point_tasks'][p['candidate_id']];h.require_approval(tid,'enqueue');lease=h.claim(tid,actor,f"run052-{p['candidate_id']}-queue-claim-v1");save(P/f"lease_{p['candidate_id']}.json",lease)
        request=req(p,tid)
        if prior:
            queue=queue_guard(scoped,api,pts,2);qid=queue['queue_ids'][i];response={'status':'EXISTING_VERIFIED_UNSTARTED_QUEUE','job_id':qid,'solver_started':False,'runner_started':False,'queue_file_mutated':False}
        else:
            with queue_transaction(RT):
                q.runtime_guard();queue_guard(scoped,api,pts,i);assert sha(R/p['inp_path'])==p['inp_sha256'] and not any((R/p['working_dir']).iterdir())
                save(RECEIPTS/f"{i+1}_{p['candidate_id']}_request.json",request.to_dict());save(RUN/f"checkpoints/submission_{p['candidate_id']}.json",{'at':now(),'queue_submission_attempt':1,'FE_attempts_started':0})
                response=scoped.enqueue(request,dry_run=False).to_dict();save(RECEIPTS/f"{i+1}_{p['candidate_id']}_response.json",response)
                assert response['status']=='ENQUEUED' and response['job_id'] and response['queue_only'] and response['queue_file_mutated']
                assert not any(response[k] for k in ['solver_started','runner_started','forbidden_mutations_detected'])
                queue=queue_guard(scoped,api,pts,i+1);assert queue['queue_ids'][-1]==response['job_id'];qid=response['job_id']
        status=scoped.status(job_id=qid).to_dict();outputs=scoped.locate_outputs(job_id=qid).to_dict()
        assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists']
        receipt={'at':now(),'candidate_id':p['candidate_id'],'job_name':p['job_name'],'queue_id':qid,'position':i+1,'project_id':PID,'inp_path':str((R/p['inp_path']).resolve()),'inp_sha256':p['inp_sha256'],'working_dir':str((R/p['working_dir']).resolve()),'expected_odb':str((R/p['expected_odb']).resolve()),'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0,'max_attempts':1,'actual_started_FE_attempts':0,'stage_state':'QUEUED','numerical_state':'NOT_EVALUATED','scientific_state':'NOT_EVALUATED','api_status':status,'api_outputs':outputs,'reused_existing_queue':prior}
        path=RECEIPTS/f"{i+1}_{p['candidate_id']}_receipt.json";save(path,receipt);h.artifact(tid,actor['agent_id'],path,{'run':'run_052','scope':'queue-only; not an FE attempt or result'},version='run052-v1');h.finish(lease,receipt,evidence_state='RECORDED',science_state='NOT_EVALUATED');receipts.append(receipt)
        print(json.dumps({'queued':i+1,'of':2,'job_name':p['job_name'],'queue_id':qid}),flush=True)
    final=queue_guard(scoped,api,pts,2);runtime=q.runtime_guard(deep=True);points()
    assert len(set(final['queue_ids']))==2 and all(not any((R/p['working_dir']).iterdir()) for p in pts)
    m={'at':now(),'status':'TWO_HARDENING_JOBS_QUEUED_AWAITING_MANUAL_START','project_id':PID,'order':ORDER,'queue_ids':final['queue_ids'],'points':receipts,'queue_after':final,'runtime':runtime,'queued':2,'started':0,'consumed_FE_attempts':0,'authorized_total_attempts':2,'automatic_retries':0,'other_executable_jobs':0,'solver_start':'USER_GUI_ONLY','auto_stop':'AUTO_STOP_UNAVAILABLE','prepared_batch_sha256':sha(FROZEN),'material_contract_sha256':read(FROZEN)['material_contract_sha256'],'comparison_contract_sha256':read(FROZEN)['comparison_contract_sha256']}
    save(P/'queue_manifest.json',m);lease=h.claim(ids['confirm_task_id'],actor,'run052-confirm-claim-v1');save(P/'confirm_lease.json',lease);h.artifact(ids['confirm_task_id'],actor['agent_id'],P/'queue_manifest.json',{'run':'run_052','scope':'two unstarted authorized queued records'},version='run052-v1');h.finish(lease,{'status':m['status'],'queue_ids':m['queue_ids'],'queued':2,'started':0,'consumed':0},evidence_state='RECORDED',science_state='NOT_EVALUATED')
    print(json.dumps({'status':m['status'],'queue_ids':m['queue_ids'],'started':0}))

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['init','enqueue']
    try:{'init':init,'enqueue':enqueue}[sys.argv[1]]()
    except Exception:
        p=P/f'{sys.argv[1]}_failure.json'
        if not p.exists():save(p,{'at':now(),'status':'BLOCKED','phase':sys.argv[1],'traceback':traceback.format_exc(),'automatic_replay_forbidden':True,'confirmed_receipts':[read(p) for p in sorted(RECEIPTS.glob('*_receipt.json'))]})
        raise
