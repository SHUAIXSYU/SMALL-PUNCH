"""One authorized V01 queue-only call, never start Runner/Abaqus; V02 gated."""
import sys,json,hashlib,subprocess,re,importlib.util,traceback,shutil
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_024';A=R/'artifacts';P=A/'private'
ABQ=Path(r'D:\Projects\abqjobpilot');PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RT=PROJECT/'runtime'
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';BATCH=ROOT/'run/run_023/artifacts/prepared_batch.json'
sys.path[:0]=[str(ROOT),str(ABQ)]
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state,queue_transaction
from abqjobpilot.recovery_assessment import assess_runtime
from agenthub_sp_invopt.hub import Hub
spec=importlib.util.spec_from_file_location('persisted_settings_reader',ROOT/'run/run_017/artifacts/preview_batch.py');settings_reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(settings_reader)
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def save(p,v):
    assert not p.exists(),f'Existing evidence: {p}'
    t=p.with_name(p.name+'.tmp')
    with t.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
    read(t);t.replace(p)
def git(*args,root=ROOT):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def frozen():
    entry=next(x for x in read(ROOT/'run/run_023/artifacts/manifest.json')['files'] if x['path']=='run/run_023/artifacts/prepared_batch.json')
    assert sha(BATCH)==entry['sha256'];b=read(BATCH);assert b['project_id']==PID and Path(b['project_path']).resolve()==PROJECT
    assert [p['job_name'] for p in b['points']]==['SPIO_R023_V01_CTR','SPIO_R023_V02_NP']
    ident=b['comparison_contract'];assert sha(ROOT/ident['path'])==ident['sha256'] and sha(ROOT/ident['implementation'])==ident['implementation_sha256']
    for p,n in zip(b['points'],[.1,.124]):
        inp=ROOT/p['inp_path'];work=ROOT/p['working_dir'];source=ROOT/p['source_inp']
        assert inp.resolve()==Path(p['inp_absolute_path']).resolve() and work.resolve()==Path(p['working_dir_absolute']).resolve()
        assert inp.resolve().is_relative_to(ROOT/'run/run_023/artifacts/candidates') and work.resolve().is_relative_to(ROOT/'run/run_023/artifacts/solver')
        assert sha(inp)==p['sha256'] and sha(source)==p['source_sha256']
        old=b'0.01, 1., 1e-12, 0.1\n';new=b'0.001, 1., 1e-12, 0.005\n'
        assert source.read_bytes().count(old)==1 and inp.read_bytes()==source.read_bytes().replace(old,new,1)
        assert '*Step, name=Step_Punch_Displacement, nlgeom=YES, inc=999999' in inp.read_text()
        assert p['static_controls']==dict(initial=.001,period=1.,minimum=1e-12,maximum=.005,max_increments=999999)
        v=read(ROOT/p['parameters_path']);assert v['sigma_y_mpa']==200 and v['n']==n and v['E_pa']==210e9 and v['nu']==.3 and v['inp_sha256']==p['sha256']
        assert p['cpus']==14 and p['gpus']==0 and p['run_datacheck'] is True and p['run_full'] is True and p['automatic_retries']==0
        keywords=[s for s in inp.read_text().splitlines() if s.startswith('*') and not s.startswith('**')]
        assert not any(re.search(r'(?i)^\*(include|import)\b|\b(input|file|library|oldjob)\s*=|^\*restart\s*,\s*read',s) for s in keywords)
        assert work.is_dir() and not any(work.iterdir()),'Output conflict; never clean or overwrite'
    return b
def protected(b):
    paths=[BATCH,PROJECT/'project.json',PROJECT/'project.db',RT/'settings.json',RT/'live_status.json',ROOT/'run/run_023/run.json',ROOT/'run/run_023/summary.md',ROOT/b['comparison_contract']['path'],ROOT/b['comparison_contract']['implementation'],ABQ/'abqjobpilot/api/client.py',ABQ/'abqjobpilot/runner.py']
    paths += [ROOT/p[k] for p in b['points'] for k in ['inp_path','source_inp','parameters_path']]
    return {str(p):sha(p) for p in paths}
def state():
    assessment=assess_runtime(RT,project_db=PROJECT/'project.db');owner=runner_ownership_state(RT)
    cmd='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    proc=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],encoding='utf8',errors='replace'))
    conflicts=[p for p in proc if re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',p['Name'],re.I) or (p['Name'].lower() in ('python.exe','pythonw.exe','cmd.exe') and 'spio_r023_' in (p.get('CommandLine') or '').lower())]
    assert assessment['status']=='CLEAN' and not assessment['lock_files'] and not assessment['errors'], 'Recovery/lock state unresolved'
    assert owner['state']=='ABSENT' and assessment['live_phase']=='IDLE' and not conflicts,'Runner/process conflict'
    return dict(at=now(),assessment=assessment,owner=owner,solver_process_conflicts=conflicts)
def queue_state(api,b):
    q=api.list_jobs();hist=api.list_project_jobs(project_id=PID).to_dict()
    assert q['status']=='OK' and hist['status']=='OK' and not q['errors']
    p1,p2=b['points'];found=[];old=[]
    terminal={'COMPLETED_OK','COMPLETED_WITH_WARNINGS','FAILED_FATAL','FAILED_NUMERICAL','FAILED_INPUT','FAILED_LICENSE','DATACHECK_FAILED','DATACHECK_FAILED_INVALID_GPU_OPTION','SKIPPED','CANCELLED'}
    for j in q['jobs']:
        matches=[p for p in b['points'] if j['job_name']==p['job_name'] or Path(j.get('inp_path','')).resolve()==ROOT/p['inp_path'] or Path(j.get('work_dir','')).resolve()==ROOT/p['working_dir']]
        if not matches:
            assert j.get('raw_status') in terminal, 'Other executable/unresolved queue job';old.append(j);continue
        assert len(matches)==1 and matches[0]['point_id']=='V01','V02 or identity conflict'
        expected=dict(job_name=p1['job_name'],inp_path=str(ROOT/p1['inp_path']),work_dir=str(ROOT/p1['working_dir']),cpus=14,gpus=0,run_datacheck=True,run_full=True)
        assert all(j.get(k)==v for k,v in expected.items()) and p1['sha256'] in j.get('notes',''),'Existing V01 identity/hash conflict'
        assert j['status']=='QUEUED' and not j.get('started_at') and not j.get('ended_at'),'V01 already attempted or unresolved; never resubmit'
        found.append(j)
    assert len(found)<=1,'Duplicate V01'
    for j in hist['jobs']:
        assert not any(j['job_name']==p['job_name'] or Path(j.get('inp_path','')).resolve()==ROOT/p['inp_path'] for p in b['points']),'Prior target execution history; stop to reconcile'
    return dict(queue=q,history=hist,existing=found,old=old)
def request(p,task_id=None):
    return JobRequest(inp_path=str(ROOT/p['inp_path']),job_name=p['job_name'],working_dir=str(ROOT/p['working_dir']),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run023_validation_stage1_run024',strategy='V01_ONLY',metadata={'project_id':PID,'task_id':task_id,'inp_sha256':p['sha256'],'maximum_attempts':1,'automatic_retries':0,'notes':f"run024; project_id={PID}; task_id={task_id}; inp_sha256={p['sha256']}; max_attempts=1; retries=0; USER GUI START ONLY; V02 gated by PASS_V01_NUMERICAL_QUALIFICATION; AUTO_STOP_UNAVAILABLE"})
def prepare():
    baseline=dict(at=now(),branch=git('branch','--show-current'),head=git('rev-parse','HEAD'),remote=git('remote','-v'),status=git('status','--short'))
    save(R/'checkpoints/git_initial.json',baseline)
    save(R/'run.json',dict(schema_version='1.0',run_id='run_024',stage='V01 queue-only stage of two-job authorization',objective='Enqueue only frozen V01 and stop for manual GUI start; V02 qualification-gated',status='RUNNING',start_time=now(),end_time=None,python_interpreter=sys.executable,git_head=baseline['head'],git_branch=baseline['branch'],inputs=[dict(path='run/run_023/artifacts/prepared_batch.json',sha256=sha(BATCH),role='Frozen two-input identities')],outputs=[],validation=[],errors=[]))
    (R/'summary.md').write_text('# run_024 — V01 Queue-only\n\nRUNNING：两阶段授权中的V01检查，V02尚不可入队。\n',encoding='utf8')
    b=frozen();before=protected(b);qhash=sha(RT/'queue.json');api,settings=settings_reader.inspect_settings();qs=queue_state(api,b);st=state()
    req=request(b['points'][0]);pre=api.preflight(req).to_dict();dry=api.enqueue(req,dry_run=True).to_dict()
    assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors']
    assert not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'))
    assert Path(pre['expected_odb_path']).resolve()==ROOT/b['points'][0]['expected_outputs']['odb']
    assert before==protected(b) and qhash==sha(RT/'queue.json')
    save(A/'admission.json',dict(at=now(),status='PASS',settings=settings,state=st,queue_state=qs,preflight=pre,dry_run=dry,request=req.to_dict(),queue_sha256=qhash,protected=before))
    print(json.dumps(dict(status='PASS_ADMISSION',settings='PERSISTED',runner=st['owner']['state'],recovery=st['assessment']['status'],preflight=pre['status'],dry_run=dry['status'],existing_v01=len(qs['existing']))))
def enqueue():
    assert not (A/'enqueue_result.json').exists() and not (R/'checkpoints/enqueue_attempt.json').exists(),'Prior attempt: readonly reconciliation only, no rerun'
    b=frozen();p=b['points'][0];ad=read(A/'admission.json');assert ad['status']=='PASS' and protected(b)==ad['protected']
    api,settings=settings_reader.inspect_settings();assert settings['settings_response']==ad['settings']['settings_response'] and settings['source_head']==ad['settings']['source_head'] and settings['source_working_tree']==ad['settings']['source_working_tree']
    h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=1800);i=h.register('MAIN','codex-main-run024-v01-queue')
    scope=dict(run='run_024',authorization_source='Explicit user two-stage authorization in current conversation',project_id=PID,project_path=str(PROJECT),frozen_batch_sha256=sha(BATCH),jobs=b['points'],maximum_unique_jobs=2,maximum_attempts_per_job=1,automatic_retries=0,cpus=14,gpus=0,run_datacheck=True,run_full=True,manual_gui_start_only=True,codex_solver_start_allowed=False,current_enqueue_allowed=['V01'],V02_condition='PASS_V01_NUMERICAL_QUALIFICATION under frozen run023 contract AND no blocking numerical issue; future fresh runtime checks',warning_or_blocked_disallows_V02=True,third_job_allowed=False,comparison_contract=b['comparison_contract'])
    budget=h.create_task(i['agent_id'],'MAIN','record_two_stage_authorization',scope,'run024-two-stage-authorization-v1')['task_id'];bl=h.claim(budget,i,'run024-budget-claim-v1')
    save(A/'authorization.json',dict(at=now(),budget_task_id=budget,identity=i,scope=scope))
    h.artifact(budget,i['agent_id'],A/'authorization.json',{'source':'Explicit current user authorization','two_stage_gate':True},version='run024-v1');h.finish(bl,dict(authorization_recorded=True,attempts_used=0,V02_gate='NOT_EVALUATED'),science_state='NOT_EVALUATED')
    tid=h.create_task(i['agent_id'],'MAIN','enqueue_V01_once',dict(parent_budget_task=budget,point=p,solver_start='USER_GUI_ONLY',stage='V01_ONLY'), 'run024-v01-enqueue-v1',depends=[budget])['task_id'];h.approve(tid,i['agent_id'],'enqueue');lease=h.claim(tid,i,'run024-v01-claim-v1')
    save(P/'session.json',dict(identity=i,lease=lease,task_id=tid,budget_task_id=budget))
    with queue_transaction(RT):
        state();qs=queue_state(api,b);assert qs['queue']==ad['queue_state']['queue'];frozen();assert protected(b)==ad['protected']
        h.require_approval(tid,'enqueue');req=request(p,tid);save(A/'request.json',req.to_dict())
        if qs['existing']:
            response=dict(status='EXISTING_VERIFIED',job_id=qs['existing'][0]['queue_id'],solver_started=False,runner_started=False)
        else:
            save(R/'checkpoints/enqueue_attempt.json',dict(at=now(),attempt=1,request_sha256=sha(A/'request.json'),retry_forbidden=True,unknown_outcome_requires_readonly_reconciliation=True))
            response=api.enqueue(req,dry_run=False).to_dict()
        save(A/'enqueue_response.json',response)
        assert response['status'] in ('ENQUEUED','EXISTING_VERIFIED') and response['job_id'],'Uncertain/rejected enqueue: stop, no retry'
        assert not response['solver_started'] and not response['runner_started']
        after=queue_state(api,b);assert len(after['existing'])==1 and after['existing'][0]['queue_id']==response['job_id'] and after['old']==qs['old']
        save(A/'queue_after.json',after)
    post=state();frozen();assert protected(b)==ad['protected']
    status=api.status(job_id=response['job_id']).to_dict();outputs=api.locate_outputs(job_id=response['job_id']).to_dict()
    assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists']
    save(A/'postcheck.json',dict(at=now(),state=post,status=status,outputs=outputs,protected_unchanged=True,V02_not_queued=True))
    result=dict(at=now(),status='V01_QUEUED_AWAITING_MANUAL_START',task_id=tid,budget_task_id=budget,queue_id=response['job_id'],job_name=p['job_name'],inp_path=p['inp_absolute_path'],inp_sha256=p['sha256'],working_dir=p['working_dir_absolute'],project_id=PID,cpus=14,gpus=0,run_datacheck=True,run_full=True,automatic_retries=0,solver_started=False,datacheck_started=False,V02_queue_id=None,V01_qualification='NOT_EVALUATED',total_authorized_unique_jobs=2,solver_attempts_observed=0,authorization_remaining={'V01':'RESERVED_BY_UNIQUE_QUEUE_ID; one manual attempt only','V02':'CONDITIONAL; cannot enqueue until V01 PASS'},study_complete=False,auto_stop='AUTO_STOP_UNAVAILABLE')
    save(A/'enqueue_result.json',result)
    for name in ['queue_v01.py','authorization.json','admission.json','request.json','enqueue_response.json','queue_after.json','postcheck.json','enqueue_result.json']:
        h.artifact(tid,i['agent_id'],A/name,{'run':'run_024','scope':'V01 queue only; V02 conditional and not queued'},version='run024-v1')
    h.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED');m=h.message(tid,i['agent_id'],'MAIN',result,'run024-v01-awaiting-gui-v1')
    save(A/'agenthub_receipt.json',dict(task_id=tid,budget_task_id=budget,message_id=m['message_id'],worker_tasks_not_yet_created=True,reason='ODB dispatch awaits actual completion',cross_session_auto_wakeup_claimed=False))
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    try:
        assert sys.argv[1] in ('prepare','enqueue');(prepare if sys.argv[1]=='prepare' else enqueue)()
    except Exception as e:
        save(P/('failure_'+datetime.now().strftime('%H%M%S%f')+'.json'),dict(at=now(),status='BLOCKED',error=str(e),traceback=traceback.format_exc(),no_automatic_retry=True));raise
