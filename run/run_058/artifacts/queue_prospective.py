"""Frozen four-job authorization and public queue-only submission. No Solver start."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,json,hashlib,zipfile,re,traceback
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_058';A=RUN/'artifacts';P=A/'private';RECEIPTS=P/'queue_receipts'
sys.dont_write_bytecode=True
sys.path[:0]=[str(R),r'D:\Projects\abqjobpilot',str(R/'run/run_041/artifacts')]
import queue_pilot as q
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.runtime_coordination import queue_transaction
from agenthub_sp_invopt.hub import Hub
read=q.read;sha=q.sha;save=q.save;git=q.git
PROJECT=q.PROJECT;RT=q.RT;PID=q.PID
FROZEN=R/'run/run_057/artifacts/prepared_batch.json'

def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def rel(p):return Path(p).resolve().relative_to(R.resolve()).as_posix()

def split(raw):
    lines=raw.splitlines(keepends=True);hits=[i for i,l in enumerate(lines) if l.strip().upper()==b'*PLASTIC'];assert len(hits)==1
    i=hits[0]+1;j=i
    while j<len(lines) and not lines[j].lstrip().startswith(b'*'):j+=1
    return b''.join(lines[:i]),b''.join(lines[j:]),[tuple(map(float,l.strip().split(b','))) for l in lines[i:j] if l.strip()]

def frozen_points():
    oldrun=read(R/'run/run_057/run.json');expected={f['path']:f['sha256'] for f in oldrun['outputs']}
    assert sha(FROZEN)==expected[rel(FROZEN)]=='9017ada8c03afff78b0e0c89e0ba51c35a9ec0b21c27a4b3a90506c7ac310705'
    batch=read(FROZEN);assert batch['project_id']==PID and len(batch['points'])==4
    for f in read(R/'run/run_057/artifacts/private/evidence_manifest.json')['files']:assert sha(R/f['path'])==f['sha256'],f['path']
    for f in read(R/'run/run_057/artifacts/private/source_manifest.json')['sources']:assert sha(R/f['path'])==f['sha256'],f['path']
    contract=read(R/batch['comparison_contract_path']);assert sha(R/batch['comparison_contract_path'])==batch['comparison_contract_sha256']
    assert sha(R/batch['protocol_path'])==batch['protocol_sha256']
    assert sha(R/batch['parent_design'])==batch['parent_design_sha256']
    baseline=contract['baseline'];assert contract['baseline_status']=='QUALIFIED_WITH_LIMITATIONS'
    assert sha(R/baseline['inp_path'])==baseline['inp_sha256'] and sha(R/baseline['odb_path'])==baseline['odb_sha256']
    old=read(R/'run/run_057/artifacts/private/I06_baseline_audit.json');assert old['status']=='QUALIFIED_WITH_LIMITATIONS' and old['complete_window'] and not old['independent_time_step_qualification']
    src=(R/baseline['inp_path']).read_bytes();pre,post,_=split(src)
    expected_params=[(225.54418697302663,.0968),(247.9859496916774,.0968),(236.49902622197678,.0848),(236.49902622197678,.1088)]
    assert batch['resources']=={'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0}
    points=[]
    for i,p in enumerate(batch['points']):
        assert p['candidate_id']==f'P{i+1:02d}' and (p['sigma_y_mpa'],p['n'])==expected_params[i]
        inp=R/p['inp_path'];work=R/p['working_dir'];raw=inp.read_bytes();ap,bp,rows=split(raw)
        assert inp.resolve()==Path(p['inp_absolute_path']).resolve() and work.resolve()==Path(p['working_dir_absolute']).resolve()
        assert sha(inp)==p['inp_sha256'] and inp.stem==p['job_name']
        expected_pre=pre
        for replacement in p['comment_replacements']:
            oldb=replacement['old'].encode();newb=replacement['new'].encode();assert expected_pre.count(oldb)==1;expected_pre=expected_pre.replace(oldb,newb,1)
        assert ap==expected_pre and bp==post
        assert raw==expected_pre+(R/p['plastic_rows_path']).read_bytes()+post
        for field in ['parameters','table','plastic_rows']:assert sha(R/p[field+'_path'])==p[field+'_sha256']
        params=read(R/p['parameters_path']);assert (params['sigma_y_mpa'],params['n'])==expected_params[i]
        assert params['E_pa']==210e9 and params['nu']==.3 and sha(R/params['generator'])==params['generator_sha256']
        assert len(rows)==p['material_rows'] and rows[0]==(p['sigma_y_mpa']*1e6,0) and rows[-1][1]==.9
        assert all(b[0]>a[0] and b[1]>a[1] for a,b in zip(rows,rows[1:]))
        assert raw.count(b'0.001, 1., 1e-12, 0.0025')==1 and b'inc=999999' in raw and b'RF2, U2' in raw
        assert not re.search(rb'(?im)^\s*\*(?:include|import|restart\s*,\s*read)\b',raw)
        assert work.is_dir() and not any(work.iterdir()) and not (R/p['expected_odb']).exists()
        points.append(p)
    assert [p['job_name'] for p in points]==batch['order'] and len({p['working_dir'] for p in points})==4
    return batch,points

def verify_predictors(batch):
    package=R/batch['predictor_package_path'];assert sha(package)==batch['predictor_package_sha256']
    directory=R/'run/run_057/artifacts/private/frozen_predictor';manifest=read(directory/'package_manifest.json')
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        for f in manifest['files']:
            assert sha(directory/f['path'])==f['sha256'] and hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
    model=read(directory/'frozen_FE_only_inverse_models.json');training=read(directory/'training_25.json');metadata=read(directory/'predictor_contract.json')
    assert sha(directory/'frozen_FE_only_inverse_models.json')==metadata['original_models_sha256']=='d146bd7aec84f889eb25611d46f1669e1469e7e741335e293cb82a439ba34364'
    assert training['sample_ids']==model['training_ids'] and len(set(training['sample_ids']))==25
    assert sha(directory/'training_25.json')==metadata['training_data_sha256']
    sys.path.insert(0,str(R/'run/run_057/artifacts'));from predict_frozen import predict_file
    baseline=read(R/batch['comparison_contract_path'])['baseline']
    loaded=predict_file(directory,R/baseline['fd_path'])
    assert set(loaded['predictions'])=={'two_ridge','five_ridge','full_ridge','constant_I06_parameters'} and loaded['no_training_or_tuning']
    return {'status':'PASS','at':now(),'package_sha256':sha(package),'model_sha256':sha(directory/'frozen_FE_only_inverse_models.json'),'training_data_sha256':sha(directory/'training_25.json'),'training_ids':training['sample_ids'],'training_unique_parameters':25,'metadata_sha256':sha(directory/'predictor_contract.json'),'loaded_primary_models':list(loaded['predictions']),'constant_baseline_sha256':sha(directory/'constant_I06.json'),'training_code_snapshot_sha256':sha(directory/'code/run055_training_provenance.py'),'feature_code_sha256':sha(directory/'code/feature_core.py'),'inverse_code_sha256':sha(directory/'code/inverse_baselines.py'),'no_training_or_new_result_access':True,'future_A_B_protocol_sha256':batch['comparison_contract_sha256']}

def guard(scoped,api,points,prefix):
    queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
    assert queue['status']==history['status']=='OK' and not queue['errors'] and not history['errors']
    assert all(j['raw_status'] in q.EXECUTABLE|q.ACTIVE|q.HISTORICAL for j in queue['jobs']), 'UNKNOWN Queue status'
    assert not [j for j in queue['jobs'] if j['raw_status'] in q.ACTIVE]
    executable=[j for j in queue['jobs'] if j['raw_status'] in q.EXECUTABLE]
    assert [j['job_name'] for j in executable]==[p['job_name'] for p in points[:prefix]],'Queue order or out-of-scope executable entry'
    details=[]
    for i,p in enumerate(points):
        same=[j for j in queue['jobs'] if j['job_name'].casefold()==p['job_name'].casefold() or Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve() or Path(j['work_dir']).resolve()==(R/p['working_dir']).resolve()]
        assert len(same)==(1 if i<prefix else 0),'Duplicate/current/history identity conflict'
        hist=[j for j in history['jobs'] if j['job_name'].casefold()==p['job_name'].casefold() or Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve()]
        assert len(hist)<=1
        if i<prefix:
            j=same[0];assert j['raw_status']==j['status']=='QUEUED' and not j.get('started_at') and not j.get('ended_at')
            assert Path(j['inp_path']).resolve()==(R/p['inp_path']).resolve() and Path(j['work_dir']).resolve()==(R/p['working_dir']).resolve()
            assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True)
            assert p['inp_sha256'] in (j.get('notes') or '')
        for item in hist:
            assert i<prefix,'Previous target history exists without current unstarted identity'
            d=api.show_job(item['job_id'],project_id=PID).to_dict();assert len(d['runs'])==1
            run=d['runs'][0];assert run['queue_id']==same[0]['queue_id'] and run['raw_status']=='QUEUED' and not run['started_at'] and not run['completed_at'];details.append(d)
    return {'queue':queue,'history':history,'unstarted_history_placeholders':details,'executable_count':len(executable),'queue_ids':[j['queue_id'] for j in executable]}

def request(p,task):
    return JobRequest(inp_path=p['inp_absolute_path'],job_name=p['job_name'],working_dir=p['working_dir_absolute'],cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run058_four_prospective_identification',strategy='frozen_run056_057_local_identification_no_retraining',metadata={'project_id':PID,'task_id':task,'candidate_id':p['candidate_id'],'inp_sha256':p['inp_sha256'],'max_started_attempts':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY','notes':f"run058 {p['candidate_id']}; INP_SHA256={p['inp_sha256']}; task_id={task}; Project={PID};14CPU0GPU;singleDCthenFull;zeroRetries;USER_GUI_ONLY;AUTO_STOP_UNAVAILABLE accepted"})

def init():
    assert not (RUN/'run.json').exists()
    assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
    start={'at':now(),'git':{'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')},'python':sys.executable,'python_version':sys.version,'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':read(R/'run/run_057/checkpoints/start.json')['local_CAE']}
    for m in start['local_CAE']:assert sha(R/m['path'])==m['sha256']
    assert start['git']['staged']==read(R/'run/run_057/checkpoints/start.json')['staged']
    save(RUN/'checkpoints/start.json',start)
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_058','stage':'Four-point prospective identification authorized queue-only handoff','objective':'verify frozen identities/predictors, register four-attempt authorization, enqueue P01-P04 only, stop before user GUI start','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[{'path':rel(FROZEN),'role':'frozen run057 manifest','sha256':sha(FROZEN)}],'outputs':[],'validation':[],'errors':[]})
    batch,points=frozen_points();models=verify_predictors(batch);save(P/'predictor_identity_verified.json',models)
    auth={'version':'run058-four-prospective-explicit-user-authorization-v1','source':{'type':'current human chat instruction','title':'SP-InvOpt｜Four-Point Prospective Identification — Authorised Queue & Post-Run Evaluation','message_id':None},'project_id':PID,'project_path':rel(PROJECT),'prepared_batch_path':rel(FROZEN),'prepared_batch_sha256':sha(FROZEN),'points':points,'order':batch['order'],'predictor_identity':models,'comparison_contract_path':batch['comparison_contract_path'],'comparison_contract_sha256':batch['comparison_contract_sha256'],'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'max_started_attempts_total':4,'max_per_input_datacheck':1,'max_per_input_full_after_datacheck_success':1,'automatic_retries':0,'single_runner_serial':True,'solver_start':'USER_GUI_ONLY','batch_continue_after_individual_failure_accepted':True,'AUTO_STOP_UNAVAILABLE_accepted':True,'no_fifth_job_or_center_recalculation':True,'queued_is_not_started_or_budget_consumed':True,'baseline_status':'QUALIFIED_WITH_LIMITATIONS','phase2_trigger':'user explicit completion notification then MAIN real execution audit; never claim future ODB tasks now'}
    save(P/'authorization_scope.json',auth)
    hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run058-prospective-queue')
    budget=hub.create_task(actor['agent_id'],'MAIN','record_four_prospective_authorization',auth,'run058-four-prospective-budget-v1');lease=hub.claim(budget['task_id'],actor,'run058-budget-claim-v1')
    hub.artifact(budget['task_id'],actor['agent_id'],P/'authorization_scope.json',{'run':'run_058','scope':'user authorizes four exact frozen inputs, queue-only Agent and user GUI start'},version='run058-v1')
    hub.finish(lease,{'authorized_attempts':4,'queued':0,'started':0,'consumed':0,'automatic_retries':0},science_state='NOT_EVALUATED')
    tasks={}
    for p in points:
        t=hub.create_task(actor['agent_id'],'MAIN','queue_only_exact_prospective_job',{'run':'run_058','candidate':p,'authorization_sha256':sha(P/'authorization_scope.json'),'max_attempts':1,'auto_retries':0,'manual_start_only':True},f"run058-enqueue-{p['candidate_id']}-v1",depends=(budget['task_id'],))
        hub.approve(t['task_id'],actor['agent_id'],'enqueue');tasks[p['candidate_id']]=t['task_id']
    confirm=hub.create_task(actor['agent_id'],'MAIN','confirm_four_unstarted_queue_identities',{'run':'run_058','order':batch['order']},'run058-confirm-four-v1',depends=tuple(tasks.values()))
    audit=hub.create_task(actor['agent_id'],'MAIN','audit_after_user_completion_notification',{'run':'run_058','trigger':'USER_COMPLETION_NOTIFICATION_REQUIRED','queue_manifest_path':'run/run_058/artifacts/private/queue_manifest.json','source_manifest':rel(FROZEN),'max_authorized_attempts':4,'solver_start':'USER_ONLY','no_automatic_claim_or_execution':True},'run058-future-execution-audit-v1',depends=(confirm['task_id'],))
    odb={}
    for p in points:
        t=hub.create_task(actor['agent_id'],'ODB','readonly_prospective_ODB_after_MAIN_audit',{'run':'run_058','candidate':p,'audit_task_id':audit['task_id'],'queue_manifest':'run/run_058/artifacts/private/queue_manifest.json','comparison_contract_path':batch['comparison_contract_path'],'comparison_contract_sha256':batch['comparison_contract_sha256'],'scope':'real safe ODB only: actual RP U2/RF2,time,FD,PEEQ,contact,cutbacks/accepted-rejected warning mapping,energy,cost,hash provenance;no Solver/retry','output_root':'run/run_058/artifacts/private/odb/'+p['candidate_id'],'tensile_access':False},f"run058-future-odb-{p['candidate_id']}-v1",depends=(audit['task_id'],));odb[p['candidate_id']]=t['task_id']
    science=hub.create_task(actor['agent_id'],'MAIN','independent_review_and_frozen_prospective_A_B',{'run':'run_058','comparison_contract_path':batch['comparison_contract_path'],'predictor_identity':models,'tasks':'MAIN must independently verify ODB evidence; A finite secants versus B unchanged predictor; no FIM CI/no new FE/no tensile/no retraining; real material validation NOT_EVALUABLE'},'run058-future-main-science-v1',depends=tuple(odb.values()))
    save(P/'task_ids.json',{'identity':actor,'budget_task_id':budget['task_id'],'point_tasks':tasks,'confirm_task_id':confirm['task_id'],'execution_audit_task_id':audit['task_id'],'odb_task_ids':odb,'science_task_id':science['task_id']})
    api=AbqJobPilotClient();scope=api.for_project(project_id=PID);env=q.environment(api);runtime=q.runtime_guard(deep=True)
    current=scope.list_jobs();same=[j for j in current['jobs'] if j['job_name'] in batch['order']]
    if same:
        assert len(same)==4 and all(j['raw_status']=='QUEUED' for j in same),'Existing partial/running/failed/unknown batch; do not resubmit'
        queue=guard(scope,api,points,4)
    else:queue=guard(scope,api,points,0)
    runner=q.ABQ/'abqjobpilot/runner_core.py';loop=runner.read_text(encoding='utf-8').split('    def _run_loop(self)',1)[1]
    assert '                run_next_job(job)' in loop and 'final_verdict' not in loop and 'FAILED' not in loop
    protected=[PROJECT/'project.json',PROJECT/'project.db',RT/'settings.json',RT/'queue.json',FROZEN,R/batch['comparison_contract_path'],R/batch['predictor_package_path']]+[R/p['inp_path'] for p in points]
    before={rel(p):sha(p) for p in protected};previews=[]
    for p in points:
        req=request(p,tasks[p['candidate_id']]);pre=scope.preflight(req).to_dict();dry=scope.enqueue(req,dry_run=True).to_dict()
        v={'candidate_id':p['candidate_id'],'request':req.to_dict(),'preflight':pre,'dry_run':dry};save(P/(p['candidate_id']+'_preview.json'),v)
        assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
        assert not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
        assert Path(pre['expected_odb_path']).resolve()==(R/p['expected_odb']).resolve();previews.append(v)
    after={rel(p):sha(p) for p in protected};assert before==after
    save(P/'precheck.json',{'at':now(),'status':'PASS_FOUR_CURRENT_PREVIEWS','preflight_passed':4,'dry_run_passed':4,'environment':env,'runtime':runtime,'queue_before':queue,'previews':previews,'protected_before':before,'protected_after':after,'auto_stop':'AUTO_STOP_UNAVAILABLE','runner_source_path':str(runner),'runner_source_sha256':sha(runner),'existing_batch':bool(same),'predictor_freeze_verified':True,'I06_status':'QUALIFIED_WITH_LIMITATIONS','solver_datacheck_started':False})
    assert hub.verify_chain()
    print(json.dumps({'preflight':4,'dry_run':4,'settings':'PERSISTED','runtime':'CLEAN_IDLE','existing_batch':bool(same),'frozen_predictors':'VERIFIED','authorized_attempts':4,'started':0}))

def enqueue():
    batch,points=frozen_points();ids=read(P/'task_ids.json');actor=ids['identity'];hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    api=AbqJobPilotClient();scope=api.for_project(project_id=PID)
    if (P/'queue_manifest.json').exists():
        manifest=read(P/'queue_manifest.json');q.environment(api);q.runtime_guard(deep=True);current=guard(scope,api,points,4);assert current['queue_ids']==manifest['queue_ids']
        print(json.dumps({'status':'EXISTING_QUEUE_VERIFIED_NO_SUBMISSION','queue_ids':manifest['queue_ids']}));return
    assert not (RUN/'checkpoints/enqueue_started.json').exists(),'Previous partial/uncertain submission: no replay'
    pre=read(P/'precheck.json');assert pre['status']=='PASS_FOUR_CURRENT_PREVIEWS'
    q.environment(api);q.runtime_guard(deep=True);prior=pre['existing_batch'];guard(scope,api,points,4 if prior else 0)
    save(RUN/'checkpoints/enqueue_started.json',{'at':now(),'queue_submission_attempt':0 if prior else 1,'FE_attempts_started':0,'do_not_replay':True,'reusing_existing':prior})
    receipts=[]
    for i,p in enumerate(points):
        tid=ids['point_tasks'][p['candidate_id']];hub.require_approval(tid,'enqueue');lease=hub.claim(tid,actor,f"run058-{p['candidate_id']}-queue-claim-v1");save(P/f"lease_{p['candidate_id']}.json",lease)
        req=request(p,tid)
        if prior:
            current=guard(scope,api,points,4);qid=current['queue_ids'][i];response={'status':'EXISTING_VERIFIED_UNSTARTED_QUEUE','job_id':qid,'solver_started':False,'runner_started':False}
        else:
            with queue_transaction(RT):
                q.runtime_guard();guard(scope,api,points,i)
                assert sha(R/p['inp_path'])==p['inp_sha256'] and not any((R/p['working_dir']).iterdir())
                save(RECEIPTS/f"{i+1}_{p['candidate_id']}_request.json",req.to_dict())
                save(RUN/f"checkpoints/submission_{p['candidate_id']}.json",{'at':now(),'queue_submission_attempt':1,'FE_attempts_started':0})
                response=scope.enqueue(req,dry_run=False).to_dict();save(RECEIPTS/f"{i+1}_{p['candidate_id']}_response.json",response)
                assert response['status']=='ENQUEUED' and response['job_id'] and response['queue_only'] and response['queue_file_mutated']
                assert not any(response[k] for k in ['solver_started','runner_started','forbidden_mutations_detected'])
                current=guard(scope,api,points,i+1);assert current['queue_ids'][-1]==response['job_id'];qid=response['job_id']
        status=scope.status(job_id=qid).to_dict();outputs=scope.locate_outputs(job_id=qid).to_dict()
        assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists'] and not any((R/p['working_dir']).iterdir())
        receipt={'at':now(),'candidate_id':p['candidate_id'],'job_name':p['job_name'],'queue_id':qid,'position':i+1,'project_id':PID,'inp_path':p['inp_absolute_path'],'inp_sha256':p['inp_sha256'],'working_dir':p['working_dir_absolute'],'expected_odb':p['expected_odb_absolute'],'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0,'max_attempts':1,'actual_started_FE_attempts':0,'stage_state':'QUEUED','software_state':'NOT_STARTED','numerical_state':'NOT_EVALUATED','scientific_state':'NOT_EVALUATED','api_status':status,'api_outputs':outputs,'api_response':response,'reused_existing_queue':prior}
        path=RECEIPTS/f"{i+1}_{p['candidate_id']}_receipt.json";save(path,receipt)
        hub.artifact(tid,actor['agent_id'],path,{'run':'run_058','scope':'completed enqueue operation only; FE remains QUEUED/unstarted'},version='run058-v1');hub.finish(lease,receipt,science_state='NOT_EVALUATED');receipts.append(receipt)
        print(json.dumps({'queued':i+1,'of':4,'job_name':p['job_name'],'queue_id':qid}),flush=True)
    final=guard(scope,api,points,4);runtime=q.runtime_guard(deep=True);frozen_points()
    assert len(set(final['queue_ids']))==4 and all(not any((R/p['working_dir']).iterdir()) for p in points)
    manifest={'at':now(),'status':'FOUR_PROSPECTIVE_JOBS_QUEUED_AWAITING_MANUAL_START','project_id':PID,'project_path':rel(PROJECT),'order':batch['order'],'queue_ids':final['queue_ids'],'points':receipts,'queue_after':final,'runtime':runtime,'queued':4,'started':0,'consumed_FE_attempts':0,'authorized_total_attempts':4,'remaining_unstarted_authorized_attempts':4,'automatic_retries':0,'other_executable_jobs':0,'solver_start':'USER_GUI_ONLY','auto_stop':'AUTO_STOP_UNAVAILABLE','prepared_batch_sha256':sha(FROZEN),'comparison_contract_sha256':batch['comparison_contract_sha256'],'predictor_package_sha256':batch['predictor_package_sha256'],'phase2':'WAIT_USER_COMPLETION_NOTIFICATION; not executed'}
    save(P/'queue_manifest.json',manifest)
    lease=hub.claim(ids['confirm_task_id'],actor,'run058-confirm-claim-v1');save(P/'confirm_lease.json',lease)
    hub.artifact(ids['confirm_task_id'],actor['agent_id'],P/'queue_manifest.json',{'run':'run_058','scope':'four QUEUED/unstarted, frozen files unchanged'},version='run058-v1')
    hub.finish(lease,{'status':manifest['status'],'queue_ids':manifest['queue_ids'],'queued':4,'started':0,'consumed':0},science_state='NOT_EVALUATED');assert hub.verify_chain()
    print(json.dumps({'status':manifest['status'],'queue_ids':manifest['queue_ids'],'started':0,'consumed':0}))

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['init','enqueue']
    try:{'init':init,'enqueue':enqueue}[sys.argv[1]]()
    except Exception:
        target=P/(sys.argv[1]+'_failure.json')
        if not target.exists():save(target,{'at':now(),'status':'BLOCKED_OR_PARTIAL_QUEUE','phase':sys.argv[1],'traceback':traceback.format_exc(),'no_automatic_replay':True,'confirmed_receipts':[read(p) for p in sorted(RECEIPTS.glob('*_receipt.json'))]})
        raise
