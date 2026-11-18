"""One authorized frozen input, queue-only; no Solver launcher or post-run work."""
from pathlib import Path
import sys,json,re,traceback,hashlib
sys.dont_write_bytecode=True
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_061';A=RUN/'artifacts';P=A/'private'
sys.path[:0]=[str(R),r'D:\Projects\abqjobpilot',str(R/'run/run_041/artifacts'),str(R/'run/run_058/artifacts')]
import queue_pilot as q
from queue_prospective import guard
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.runtime_coordination import queue_transaction
from agenthub_sp_invopt.hub import Hub
read=q.read;save=q.save;sha=q.sha;git=q.git;now=q.now;PID=q.PID;RT=q.RT;PROJECT=q.PROJECT
FROZEN=R/'run/run_060/artifacts/prepared_batch.json'
EXPECTED='f944338d77fa7798d3546dd51075f149f886a4fd015b37fba28c58878311b906'
STATUS='ONE_I06_REFINEMENT_JOB_QUEUED_AWAITING_MANUAL_START'
def rel(p):return Path(p).resolve().relative_to(R.resolve()).as_posix()
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)

def freeze():
    j=read(R/'run/run_060/run.json')
    for f in j['outputs']:assert sha(R/f['path'])==f['sha256'],f['path']
    assert sha(FROZEN)=='599734dbcfc0a809188fd0f58453cf33a3d4923caa7efc4b0bf89d2b7850b3a9'
    evidence=read(R/'run/run_060/artifacts/private/evidence_manifest.json')['files']
    sources=read(R/'run/run_060/artifacts/private/source_manifest.json')['sources']
    for f in evidence+sources:assert sha(R/f['path'])==f['sha256'],f['path']
    batch=read(FROZEN);assert batch['project_id']==PID and len(batch['points'])==1
    assert batch['baseline_status']=='QUALIFIED_WITH_LIMITATIONS'
    p=batch['points'][0];assert p['job_name']=='SPIO_R060_I06_M00125' and p['inp_sha256']==EXPECTED
    assert batch['order']==[p['job_name']]
    inp=R/p['inp_path'];work=R/p['working_dir'];src=R/p['source_inp'];raw=inp.read_bytes();original=src.read_bytes()
    assert inp.resolve()==Path(p['inp_absolute_path']).resolve() and work.resolve()==Path(p['working_dir_absolute']).resolve()
    assert sha(inp)==EXPECTED and sha(src)==p['source_inp_sha256'] and sha(R/p['source_odb'])==p['source_odb_sha256']
    assert sha(R/p['parameters_path'])==p['parameters_sha256']
    assert (p['sigma_y_mpa'],p['n'],p['E_pa'],p['nu'])==(236.49902622197678,.0968,210e9,.3)
    assert sha(R/p['material_generator'])==p['material_generator_sha256']
    audit=read(R/'run/run_060/artifacts/private/input_byte_audit.json');recovered=raw
    assert raw.count(audit['new_static_data'].encode())==1
    recovered=recovered.replace(audit['new_static_data'].encode(),audit['old_static_data'].encode(),1)
    for x in audit['comment_replacements']:
        assert recovered.count(x['new'].encode())==1
        recovered=recovered.replace(x['new'].encode(),x['old'].encode(),1)
    assert recovered==original,'Non-allowlisted model change'
    lines=raw.splitlines(keepends=True);i=next(i for i,l in enumerate(lines) if l.strip().upper()==b'*PLASTIC')+1
    k=next(k for k in range(i,len(lines)) if lines[k].lstrip().startswith(b'*'))
    table=b''.join(lines[i:k]);rows=[tuple(map(float,l.strip().split(b','))) for l in lines[i:k] if l.strip()]
    assert hashlib.sha256(table).hexdigest()==p['material_table_bytes_sha256']
    assert len(rows)==34 and rows[0][1]==0 and rows[-1][1]==.9
    assert all(b[0]>a[0] and b[1]>a[1] for a,b in zip(rows,rows[1:]))
    assert b'inc=999999' in raw and b'RF2, U2' in raw
    assert not re.search(rb'(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b',raw)
    assert p['numerics']=={'solver':'Abaqus/Standard2024','initial_increment':.001,'maximum_increment':.00125,'minimum_increment':1e-12,'total_time':1.,'maximum_increments':999999}
    assert work.is_dir() and not any(work.iterdir()) and not (R/p['expected_odb']).exists(),'Output conflict'
    assert sha(R/batch['comparison_contract_path'])==batch['comparison_contract_sha256']
    return batch,p,{'status':'PASS','at':now(),'source_records_verified':len(sources),'static_records_verified':len(evidence),'inp_sha256':sha(inp),'material_table_byte_identical':True,'reverse_allowlisted_three_changes_recovers_source':True,'baseline_status':batch['baseline_status'],'comparison_contract_sha256':batch['comparison_contract_sha256']}

def req(p,tid):
    return JobRequest(inp_path=p['inp_absolute_path'],job_name=p['job_name'],working_dir=p['working_dir_absolute'],cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run061_one_I06_resolution',strategy='frozen_run060_adjacent_increment_comparison',metadata={'project_id':PID,'task_id':tid,'inp_sha256':EXPECTED,'max_started_attempts':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','notes':f'run061 unique I06; INP_SHA256={EXPECTED}; task={tid};14CPU0GPU;singleDCthenFull;zeroRetries;USER_GUI_ONLY;no_other_job'})

def init():
    assert not (RUN/'run.json').exists()
    assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
    start={'at':now(),'python':sys.executable,'python_version':sys.version,'git':{'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')},'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':read(R/'run/run_058/checkpoints/start.json')['local_CAE']}
    assert start['git']['staged']==read(R/'run/run_060/checkpoints/start.json')['git']['staged']
    for f in start['local_CAE']:assert sha(R/f['path'])==f['sha256']
    save(RUN/'checkpoints/start.json',start)
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_061','stage':'I06 single refinement authorized queue-only execution record','objective':'verify run060 freeze; register one exact user-authorized attempt; enqueue only; stop for manual GUI start','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_head':start['git']['head'],'git_branch':start['git']['branch'],'inputs':[{'path':rel(FROZEN),'sha256':sha(FROZEN),'role':'immutable preparation manifest'}],'outputs':[],'validation':[],'errors':[]})
    batch,p,identity=freeze();save(P/'freeze_integrity.json',identity)
    api=AbqJobPilotClient();scope=api.for_project(project_id=PID);env=q.environment(api);runtime=q.runtime_guard(deep=True)
    same=[j for j in scope.list_jobs()['jobs'] if j['job_name']==p['job_name']]
    assert len(same)<=1 and all(j['raw_status']=='QUEUED' for j in same),'Existing executed/uncertain identity'
    current=guard(scope,api,[p],1 if same else 0)
    runner=q.ABQ/'abqjobpilot/runner_core.py';loop=runner.read_text(encoding='utf-8').split('    def _run_loop(self)',1)[1]
    assert '                run_next_job(job)' in loop and 'final_verdict' not in loop and 'FAILED' not in loop
    auth={'version':'run061-one-frozen-I06-user-authorization-v1','source':{'type':'current explicit human message','title':'SP-InvOpt｜I06 Numerical Resolution — Authorised Queue & Post-Run Qualification','message_id':None},'prepared_manifest':rel(FROZEN),'prepared_manifest_sha256':sha(FROZEN),'point':p,'project_id':PID,'project_path':rel(PROJECT),'authorized_total':1,'max_datacheck':1,'max_full_after_successful_datacheck':1,'max_started_attempts':1,'automatic_retries':0,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'solver_start':'USER_GUI_ONLY','no_other_job_or_transfer':True,'comparison_contract_path':batch['comparison_contract_path'],'comparison_contract_sha256':batch['comparison_contract_sha256'],'weak_direction_RMS_N':3.092632613282926,'baseline_status':'QUALIFIED_WITH_LIMITATIONS','phase2_trigger':'EXPLICIT_USER_COMPLETION_NOTIFICATION; not run during Phase1'}
    save(P/'authorization_scope.json',auth)
    hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run061-I06-queue')
    budget=hub.create_task(actor['agent_id'],'MAIN','record_one_I06_refinement_authorization',auth,'run061-I06-budget-v1');lease=hub.claim(budget['task_id'],actor,'run061-budget-claim-v1')
    hub.artifact(budget['task_id'],actor['agent_id'],P/'authorization_scope.json',{'run':'run_061','scope':'one exact frozen input; enqueue is not started FE'},version='run061-v1')
    hub.finish(lease,{'authorized_total':1,'queued':len(same),'started':0,'consumed':0,'automatic_retries':0},science_state='NOT_EVALUATED')
    enqueue=hub.create_task(actor['agent_id'],'MAIN','enqueue_one_exact_frozen_I06',{'run':'run_061','point':p,'authorization_sha256':sha(P/'authorization_scope.json'),'manual_start_only':True},'run061-I06-enqueue-v1',depends=(budget['task_id'],));hub.approve(enqueue['task_id'],actor['agent_id'],'enqueue')
    confirm=hub.create_task(actor['agent_id'],'MAIN','confirm_unique_unstarted_I06_queue',{'run':'run_061','job_name':p['job_name'],'inp_sha256':EXPECTED},'run061-I06-confirm-v1',depends=(enqueue['task_id'],))
    audit=hub.create_task(actor['agent_id'],'MAIN','audit_after_user_completion_notification',{'run':'run_061','trigger':'EXPLICIT_USER_COMPLETION_NOTIFICATION_REQUIRED','queue_manifest':'run/run_061/artifacts/private/queue_manifest.json','candidate':p,'max_started_attempts':1,'no_solver_or_recovery':True},'run061-future-audit-v1',depends=(confirm['task_id'],))
    odb=hub.create_task(actor['agent_id'],'ODB','readonly_I06_refined_after_MAIN_audit',{'run':'run_061','candidate':p,'audit_task_id':audit['task_id'],'comparison_contract_path':batch['comparison_contract_path'],'comparison_contract_sha256':batch['comparison_contract_sha256'],'scope':'real safe ODB only; actual RP U2/RF2,time,FD,PEEQ saved frames,ALLPD,contact,cutback and accepted/rejected warnings,hashes/cost; no Solver/retry','output_root':'run/run_061/artifacts/private/odb/I06_REFINED','tensile_access':False},'run061-future-ODB-v1',depends=(audit['task_id'],))
    science=hub.create_task(actor['agent_id'],'MAIN','independent_I06_resolution_qualification',{'run':'run_061','comparison_contract_path':batch['comparison_contract_path'],'comparison_contract_sha256':batch['comparison_contract_sha256'],'scope':'independent identity,FD,loss,PEEQ,warning review; R against frozen3.092632613282926N; preserve run059 and I06 limits; no retraining/no Fisher CI/no new FE'},'run061-future-science-v1',depends=(odb['task_id'],))
    ids={'identity':actor,'budget_task_id':budget['task_id'],'queue_task_id':enqueue['task_id'],'confirm_task_id':confirm['task_id'],'execution_audit_task_id':audit['task_id'],'odb_task_id':odb['task_id'],'science_task_id':science['task_id']};save(P/'task_ids.json',ids)
    protected=[PROJECT/'project.json',PROJECT/'project.db',RT/'settings.json',RT/'queue.json',FROZEN,R/batch['comparison_contract_path'],R/p['inp_path']]
    before={rel(x):sha(x) for x in protected};request=req(p,enqueue['task_id']);pre=scope.preflight(request).to_dict();dry=scope.enqueue(request,dry_run=True).to_dict()
    save(P/'current_preview.json',{'at':now(),'request':request.to_dict(),'preflight':pre,'dry_run':dry})
    assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
    assert not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
    assert Path(pre['expected_odb_path']).resolve()==(R/p['expected_odb']).resolve()
    after={rel(x):sha(x) for x in protected};assert before==after
    save(P/'precheck.json',{'at':now(),'status':'PASS_ONE_CURRENT_PREVIEW','environment':env,'runtime':runtime,'queue_before':current,'existing_unstarted_queue':bool(same),'protected_before':before,'protected_after':after,'AUTO_STOP_UNAVAILABLE':True,'runner_source_sha256':sha(runner),'runner_source_path':str(runner),'no_auto_retry':'terminal failures not selected for automatic requeue; policy bound in metadata/notes, no retry setting fabricated','preflight':1,'dry_run':1,'solver_datacheck_started':False});assert hub.verify_chain()
    print(json.dumps({'status':'PREFLIGHT_DRY_RUN_PASS','settings':'PERSISTED','runtime':'CLEAN_IDLE','existing_queue':bool(same),'authorized':1,'started':0}))

def enqueue():
    batch,p,_=freeze();ids=read(P/'task_ids.json');actor=ids['identity'];hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    api=AbqJobPilotClient();scope=api.for_project(project_id=PID);pre=read(P/'precheck.json');prior=pre['existing_unstarted_queue']
    assert pre['status']=='PASS_ONE_CURRENT_PREVIEW' and not (RUN/'checkpoints/enqueue_started.json').exists(),'No automatic replay'
    q.environment(api);q.runtime_guard(deep=True);guard(scope,api,[p],1 if prior else 0)
    save(RUN/'checkpoints/enqueue_started.json',{'at':now(),'queue_submission_attempt':0 if prior else 1,'FE_attempts_started':0,'do_not_replay':True})
    tid=ids['queue_task_id'];hub.require_approval(tid,'enqueue');lease=hub.claim(tid,actor,'run061-enqueue-claim-v1');save(P/'lease_enqueue.json',lease);request=req(p,tid)
    if prior:
        current=guard(scope,api,[p],1);qid=current['queue_ids'][0];response={'status':'EXISTING_VERIFIED_UNSTARTED_QUEUE','job_id':qid,'solver_started':False,'runner_started':False}
    else:
        with queue_transaction(RT):
            q.runtime_guard();guard(scope,api,[p],0)
            assert sha(R/p['inp_path'])==EXPECTED and not any((R/p['working_dir']).iterdir())
            save(P/'enqueue_request.json',request.to_dict())
            response=scope.enqueue(request,dry_run=False).to_dict();save(P/'enqueue_response.json',response)
            assert response['status']=='ENQUEUED' and response['job_id'] and response['queue_only'] and response['queue_file_mutated']
            assert not any(response[k] for k in ['solver_started','runner_started','forbidden_mutations_detected'])
            current=guard(scope,api,[p],1);qid=response['job_id'];assert current['queue_ids']==[qid]
    status=scope.status(job_id=qid).to_dict();outputs=scope.locate_outputs(job_id=qid).to_dict()
    assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists'] and not any((R/p['working_dir']).iterdir())
    receipt={'at':now(),'queue_id':qid,'job_name':p['job_name'],'inp_path':p['inp_absolute_path'],'inp_sha256':EXPECTED,'working_dir':p['working_dir_absolute'],'project_id':PID,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0,'max_started_attempts':1,'stage_state':'QUEUED','software_state':'NOT_STARTED','numerical_state':'NOT_EVALUATED','science_state':'NOT_EVALUATED','api_response':response,'api_status':status,'api_outputs':outputs,'reused_existing':prior}
    save(P/'queue_receipt.json',receipt);hub.artifact(tid,actor['agent_id'],P/'queue_receipt.json',{'run':'run_061','scope':'queue operation only; no FE started'},version='run061-v1');hub.finish(lease,receipt,science_state='NOT_EVALUATED')
    final=guard(scope,api,[p],1);runtime=q.runtime_guard(deep=True);freeze()
    manifest={'at':now(),'status':STATUS,'project_id':PID,'project_path':rel(PROJECT),'order':[p['job_name']],'queue_ids':[qid],'point':receipt,'queue_after':final,'runtime':runtime,'authorized_total':1,'queued':1,'started':0,'consumed_FE_attempts':0,'remaining_unstarted_authorized_attempts':1,'automatic_retries':0,'other_executable_jobs':0,'solver_start':'USER_GUI_ONLY','AUTO_STOP_UNAVAILABLE':True,'prepared_batch_sha256':sha(FROZEN),'comparison_contract_sha256':batch['comparison_contract_sha256'],'phase2':'NOT_STARTED_AWAIT_EXPLICIT_USER_COMPLETION_NOTIFICATION'}
    save(P/'queue_manifest.json',manifest)
    lease=hub.claim(ids['confirm_task_id'],actor,'run061-confirm-claim-v1');hub.artifact(ids['confirm_task_id'],actor['agent_id'],P/'queue_manifest.json',{'run':'run_061','scope':'one unique QUEUED/unstarted identity'},version='run061-v1');hub.finish(lease,{'status':STATUS,'queue_id':qid,'queued':1,'started':0,'consumed':0},science_state='NOT_EVALUATED');assert hub.verify_chain()
    print(json.dumps({'status':STATUS,'queue_id':qid,'started':0,'consumed':0}))

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['init','enqueue']
    try:{'init':init,'enqueue':enqueue}[sys.argv[1]]()
    except Exception:
        target=P/(sys.argv[1]+'_failure.json')
        if not target.exists():save(target,{'at':now(),'status':'BLOCKED_OR_UNCERTAIN_QUEUE','phase':sys.argv[1],'traceback':traceback.format_exc(),'no_automatic_replay':True})
        raise
