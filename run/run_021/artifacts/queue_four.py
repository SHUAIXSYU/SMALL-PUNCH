"""Frozen four-job public enqueue-only. No Solver, Runner start, or retries."""
import sys,json,hashlib,subprocess,re,importlib.util,traceback
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'run/run_021';OUT=RUN/'artifacts'
ABQ=Path(r'D:\Projects\abqjobpilot');PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RUNTIME=PROJECT/'runtime'
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';BATCH=ROOT/'run/run_020/artifacts/prepared_batch.json'
sys.path[:0]=[str(ROOT),str(ABQ)]
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state,queue_transaction
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def now():return datetime.now().astimezone().isoformat()
def save(p,v):
    assert not p.exists(),str(p)
    t=p.with_name(p.name+'.tmp')
    with t.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
    read(t);t.replace(p)
def replace_json(p,v):
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(p)
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
preview=load(ROOT/'run/run_017/artifacts/preview_batch.py','settings_reader')
def git(*a,root=ROOT):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def frozen():
    assert sha(BATCH)=='e538bc574a4c26be95ef36f89fc4c2aea12e70d09e9da0f8040bed394fa1e278'
    batch=read(BATCH);assert batch['project_id']==PID and (ROOT/batch['project_path']).resolve()==PROJECT
    names=['SPIO_R020_L01_SYM','SPIO_R020_L02_SYP','SPIO_R020_L03_NM','SPIO_R020_L04_NP']
    assert [p['job_name'] for p in batch['points']]==names
    for p in batch['points']:
        for k in ['inp_path','working_dir','parameters_path','expected_odb']:
            assert not Path(p[k]).is_absolute() and (ROOT/p[k]).resolve().is_relative_to(ROOT/'run/run_020')
        inp=ROOT/p['inp_path'];values=read(ROOT/p['parameters_path'])
        assert sha(inp)==p['inp_sha256'] and sha(ROOT/p['parameters_path'])==p['parameters_sha256']
        assert values['sigma_y_mpa']==p['sigma_y_mpa'] and values['n']==p['n'] and values['E_pa']==210e9 and values['nu']==.3
        assert values['inp_sha256']==p['inp_sha256'] and p['maximum_attempts']==1 and p['automatic_retries']==0
        assert (ROOT/p['working_dir']).is_dir() and not any((ROOT/p['working_dir']).iterdir())
        keywords=[s for s in inp.read_text().splitlines() if s.startswith('*') and not s.startswith('**')]
        assert not any(re.search(r'(?i)^\*(include|import)\b|\b(input|file|library|oldjob)\s*=|^\*restart\s*,\s*read',s) for s in keywords)
    return batch
def protected():
    batch=read(BATCH)
    paths=[BATCH,PROJECT/'project.json',PROJECT/'project.db',RUNTIME/'settings.json',RUNTIME/'live_status.json',ROOT/'inverse/hollomon.py']
    paths += [ROOT/p[k] for p in batch['points'] for k in ['inp_path','parameters_path']]
    paths += [ABQ/p for p in read(OUT/'runner_fake_tests.json')['source_hashes']]
    return {str(p):sha(p) for p in paths}
def processes():
    cmd='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    rows=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],text=True,encoding='utf8',errors='replace'))
    conflict=[];gui=[]
    for p in rows:
        name=p['Name'].lower();line=(p.get('CommandLine') or '').lower()
        if re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',name) or (name in {'python.exe','pythonw.exe','cmd.exe'} and 'spio_r020_' in line):conflict.append(p)
        if name in {'python.exe','pythonw.exe'} and ('run_gui.py' in line or 'abqjobpilot' in line):gui.append(p)
    return dict(observed_at=now(),conflicts=conflict,gui_processes=gui,gui_binding='NO_GUI_PROCESS_OBSERVED' if not gui else 'REVIEW_COMMAND_LINES')
def inspect(api,batch):
    listing=api.list_jobs();assert listing['status']=='OK' and not listing['errors']
    found=[];old=[]
    terminal={'COMPLETED_OK','COMPLETED_WITH_WARNINGS','FAILED_FATAL','FAILED_NUMERICAL','FAILED_INPUT','FAILED_LICENSE','DATACHECK_FAILED','DATACHECK_FAILED_INVALID_GPU_OPTION','SKIPPED','CANCELLED'}
    for job in listing['jobs']:
        matches=[p for p in batch['points'] if job['job_name']==p['job_name'] or Path(job.get('work_dir','')).resolve()==ROOT/p['working_dir'] or Path(job.get('inp_path','')).resolve()==ROOT/p['inp_path']]
        if not matches:
            assert job.get('raw_status') in terminal,'Other executable/unresolved job';old.append(job);continue
        assert len(matches)==1
        p=matches[0];expected=dict(job_name=p['job_name'],inp_path=str(ROOT/p['inp_path']),work_dir=str(ROOT/p['working_dir']),cpus=14,gpus=0,run_datacheck=True,run_full=True)
        assert all(job.get(k)==v for k,v in expected.items()),'Identity conflict'
        assert job['status']=='QUEUED' and job.get('raw_status')=='QUEUED','Existing job already executed/unresolved; do not resubmit'
        assert p['inp_sha256'] in job.get('notes',''),'Existing hash evidence absent'
        assert not job['started_at'] and not job['ended_at']
        found.append(job)
    assert len({j['job_name'] for j in found})==len(found),'Duplicate queued identity'
    assert [j['job_name'] for j in found]==[p['job_name'] for p in batch['points'][:len(found)]],'Existing batch not ordered prefix'
    return listing,found,old
def idle():
    owner=runner_ownership_state(RUNTIME);live=read(RUNTIME/'live_status.json');proc=processes()
    assert owner['state']=='ABSENT' and live.get('phase')=='IDLE' and not live.get('process_identity'),'Runner ownership/recovery conflict'
    assert not proc['conflicts'],'Solver/target process conflict'
    return dict(owner=owner,live=live,process_observation=proc)
def req(p,tid=None):
    return JobRequest(inp_path=str(ROOT/p['inp_path']),job_name=p['job_name'],working_dir=str(ROOT/p['working_dir']),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run020_four_authorized_run021',strategy=p['point_id'],metadata={'project_id':PID,'task_id':tid,'inp_sha256':p['inp_sha256'],'max_attempts':1,'auto_retries':0,'notes':f"run021; project_id={PID}; task_id={tid}; inp_sha256={p['inp_sha256']}; max_attempts=1; retries=0; USER GUI START ONLY; AUTO_STOP_UNAVAILABLE"})
def prepare():
    batch=frozen();before=protected();qhash=sha(RUNTIME/'queue.json');api,settings=preview.inspect_settings()
    queue,found,old=inspect(api,batch);state=idle()
    previews=[]
    for p in batch['points']:
        r=req(p);pre=api.preflight(r).to_dict();dry=api.enqueue(r,dry_run=True).to_dict()
        assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors']
        assert not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
        assert Path(pre['expected_odb_path']).resolve()==ROOT/p['expected_odb']
        previews.append(dict(point=p,request=r.to_dict(),preflight=pre,dry_run=dry))
    assert before==protected() and qhash==sha(RUNTIME/'queue.json')
    assert all(sha(ABQ/p)==h for p,h in read(OUT/'runner_fake_tests.json')['source_hashes'].items())
    save(OUT/'admission.json',dict(observed_at=now(),status='PASS',settings=settings,queue=queue,existing=found,state=state,previews=previews,auto_stop='AUTO_STOP_UNAVAILABLE'))
    save(RUN/'checkpoints/protected_before.json',before)
    run=dict(schema_version='1.0',run_id='run_021',stage='Four-job queue-only submission',objective='Authorize frozen four jobs and audit installed failure stop behavior; no Codex Solver start',status='RUNNING',start_time=now(),end_time=None,python_interpreter=sys.executable,git_head=git('rev-parse','HEAD'),git_branch=git('branch','--show-current'),inputs=[dict(path='run/run_020/artifacts/prepared_batch.json',sha256=sha(BATCH),role='Frozen four inputs')],outputs=[],validation=[],errors=[])
    save(RUN/'run.json',run);save(RUN/'checkpoints/run_initial.json',run)
    (RUN/'summary.md').write_text('# run_021 — RUNNING\n\nFrozen four-job Queue-only authorization; no Solver start.\n',encoding='utf8')
    print(json.dumps(dict(status='PASS',previews=4,existing=len(found),settings='PERSISTED',owner=state['owner']['state'],gui=state['process_observation']['gui_binding'],auto_stop='AUTO_STOP_UNAVAILABLE')))
def enqueue():
    batch=frozen();ad=read(OUT/'admission.json');assert ad['status']=='PASS' and protected()==read(RUN/'checkpoints/protected_before.json')
    assert not (OUT/'authorization.json').exists(),'Prior attempt exists; reconcile read-only, never rerun mutation'
    api,settings=preview.inspect_settings();assert settings['settings_response']==ad['settings']['settings_response']
    assert settings['source_head']==ad['settings']['source_head'] and settings['source_working_tree']==ad['settings']['source_working_tree']
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=1800);identity=hub.register('MAIN','codex-main-run021-four-queue')
    scope=dict(run_id='run_021',authorization_source='Explicit user four-job Queue-only authorization; sections 1-5 only',project_id=PID,project_path=str(PROJECT),frozen_batch_sha256=sha(BATCH),points=[dict(**p,inp_absolute=str(ROOT/p['inp_path']),working_dir_absolute=str(ROOT/p['working_dir'])) for p in batch['points']],max_jobs=4,maximum_attempts_per_job=1,automatic_retries=0,cpus=14,gpus=0,run_datacheck=True,run_full=True,codex_enqueue_allowed=True,codex_solver_start_allowed=False,user_manual_gui_start_authorized=True,auto_stop='AUTO_STOP_UNAVAILABLE',center_recompute_allowed=False)
    task=hub.create_task(identity['agent_id'],'MAIN','enqueue_frozen_four_once',scope,'run021-frozen-four-enqueue-v1',depends=['88b9dcde-b2b8-4576-85d5-4efaf2397082']);tid=task['task_id']
    hub.approve(tid,identity['agent_id'],'enqueue');lease=hub.claim(tid,identity,'run021-main-queue-v1')
    save(OUT/'private/lease.json',lease);save(OUT/'authorization.json',dict(observed_at=now(),task_id=tid,identity=identity,scope=scope,hub_approvals=['enqueue']))
    accepted=[]
    try:
        # The official reentrant runtime transaction also prevents GUI acquisition
        # between sequential API enqueues; no queue/DB data are directly written.
        with queue_transaction(RUNTIME):
            idle();listing,found,old=inspect(api,batch)
            for p in batch['points']:
                frozen();assert protected()==read(RUN/'checkpoints/protected_before.json');idle();hub.require_approval(tid,'enqueue')
                _,found,_=inspect(api,batch);existing=[j for j in found if j['job_name']==p['job_name']]
                r=req(p,tid);save(OUT/(p['point_id']+'_request.json'),r.to_dict())
                if existing:response=dict(status='EXISTING_VERIFIED',job_id=existing[0]['queue_id'])
                else:
                    save(RUN/'checkpoints'/(p['point_id']+'_enqueue_attempt.json'),dict(at=now(),attempt=1,retry_forbidden=True,request_sha256=sha(OUT/(p['point_id']+'_request.json'))))
                    response=api.enqueue(r,dry_run=False).to_dict()
                    save(OUT/(p['point_id']+'_enqueue_response.json'),response)
                    assert response['status']=='ENQUEUED' and response['job_id'],'Rejected/uncertain mutation; STOP'
                    assert not any(response[k] for k in ['solver_started','runner_started','forbidden_mutations_detected'])
                after,found,history=inspect(api,batch);assert history==old
                assert any(j['queue_id']==response['job_id'] and j['job_name']==p['job_name'] for j in found)
                accepted.append(dict(job_name=p['job_name'],queue_id=response['job_id'],inp_path=str(ROOT/p['inp_path']),inp_sha256=p['inp_sha256'],working_dir=str(ROOT/p['working_dir']),status='QUEUED',cpus=14,gpus=0,run_datacheck=True,run_full=True))
                save(OUT/(p['point_id']+'_queue_verified.json'),after)
            assert len(found)==4
            save(OUT/'queue_after.json',after)
        state=idle();frozen();assert protected()==read(RUN/'checkpoints/protected_before.json')
        statuses=[]
        for item in accepted:
            status=api.status(job_id=item['queue_id']).to_dict();outputs=api.locate_outputs(job_id=item['queue_id']).to_dict()
            assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists']
            statuses.append(dict(queue_id=item['queue_id'],status=status,outputs=outputs))
        save(OUT/'postcheck.json',dict(at=now(),state=state,jobs=statuses,protected_unchanged=True))
        result=dict(observed_at=now(),status='FOUR_JOBS_QUEUED_AWAITING_MANUAL_START',run_status='WARNING',task_id=tid,project_id=PID,jobs=accepted,auto_stop='AUTO_STOP_UNAVAILABLE',solver_started=False,datacheck_started=False,automatic_retries=0,scientific_analysis='NOT_STARTED',gui_process_binding=state['process_observation']['gui_binding'])
        save(OUT/'enqueue_result.json',result)
        artifacts=[]
        for name in ['audit_runner.py','runner_fake_tests.json','runner_audit.md','queue_four.py','admission.json','authorization.json','queue_after.json','postcheck.json','enqueue_result.json']+[p['point_id']+suffix for p in batch['points'] for suffix in ['_request.json','_enqueue_response.json','_queue_verified.json']]:
            file=OUT/name
            if file.exists():artifacts.append(hub.artifact(tid,identity['agent_id'],file,{'run':'run_021','scope':'Four queue-only jobs; automatic abnormal stop unavailable'},version='run021-v1'))
        hub.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED');message=hub.message(tid,identity['agent_id'],'MAIN',result,'run021-four-queued-v1')
        save(OUT/'agenthub_receipt.json',dict(task_id=tid,artifacts=artifacts,message_id=message['message_id'],cross_session_auto_notification_claimed=False))
        print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        failure=dict(at=now(),status='BLOCKED',accepted=accepted,error=str(e),traceback=traceback.format_exc(),retry_forbidden=True)
        save(OUT/'private/enqueue_failure.json',failure);hub.fail(lease,'BATCH_ENQUEUE_STOPPED',str(e),retryable=False);raise
if __name__=='__main__':
    assert sys.argv[1] in {'prepare','enqueue'}
    (prepare if sys.argv[1]=='prepare' else enqueue)()
