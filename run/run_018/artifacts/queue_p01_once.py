"""One authorized public enqueue. Never starts Runner; never retries a mutation.

Admission can be repeated read-only. The exclusive attempt marker cannot be
overridden. Existing exact P01 is reconciled without another enqueue call.
"""
import hashlib
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_018'
OUT = RUN / 'artifacts'
ABQ = Path(r'D:\Projects\abqjobpilot')
PROJECT = ROOT / 'agenthub_sp_invopt/abqjobpilot_project'
RUNTIME = PROJECT / 'runtime'
PID = 'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
JOB = 'SPIO_R017_P01_CTR'
DIGEST = '3a97ee2a121261515a2c4019fbd0e1fedf1391ff5a988021786673c592892576'
BATCH = ROOT / 'run/run_017/artifacts/prepared_batch.json'
sys.path[:0] = [str(ABQ), str(ROOT)]
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot import config
from abqjobpilot.runtime_coordination import runner_ownership_state, queue_transaction
from agenthub_sp_invopt.hub import Hub


def now(): return datetime.now().astimezone().isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def require(ok, reason):
    if not ok: raise RuntimeError(reason)
def save(p, data):
    require(not p.exists(), 'Evidence already exists: '+str(p))
    temp = p.with_name(p.name+'.tmp')
    with temp.open('x', encoding='utf8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    read(temp)
    temp.replace(p)
def repo_path(rel):
    p = (ROOT / rel).resolve()
    require(p.is_relative_to(ROOT) and not Path(rel).is_absolute(), 'Invalid frozen path')
    return p
def git(*args): return subprocess.check_output(['git','-C',str(ABQ),*args],text=True).strip()


def frozen():
    batch = read(BATCH)
    matches = [p for p in batch['points'] if p['point_id']=='P01']
    require(len(matches)==1, 'Ambiguous P01')
    p = matches[0]
    require(batch['project_id']==PID and repo_path(batch['project_path'])==PROJECT, 'Frozen project mismatch')
    for k,v in dict(cpus=14,gpus=0,run_datacheck=True,run_full=True,auto_shutdown=False).items():
        require(type(batch[k]) is type(v) and batch[k]==v, 'Frozen setting mismatch: '+k)
    require(p['job_name']==JOB and p['inp_sha256']==DIGEST, 'Frozen P01 identity mismatch')
    inp,work,params = map(repo_path,(p['inp_path'],p['working_dir'],p['parameters_path']))
    require(inp.stem==JOB and sha(inp)==DIGEST, 'Full input SHA256 mismatch')
    require(sha(params)==p['parameters_sha256'], 'Parameter hash mismatch')
    values=read(params)
    expected=dict(sigma_y_mpa=387.2983346207417,n=.26,E_pa=210e9,nu=.3,max_plastic_strain=.9)
    require(all(values[k]==v for k,v in expected.items()), 'P01 parameter mismatch')
    require(p['sigma_y_mpa']==values['sigma_y_mpa'] and p['n']==values['n'], 'Frozen parameters disagree')
    require(values['inp_sha256']==DIGEST and values['material_model']=='candidate-true-total-hollomon-v1', 'Constitutive identity mismatch')
    require(p['maximum_attempts']==1 and p['automatic_retries']==0, 'Retry policy mismatch')
    keywords=[s.strip() for s in inp.read_text(encoding='utf-8-sig').splitlines() if s.lstrip().startswith('*') and not s.lstrip().startswith('**')]
    deps=[s for s in keywords if re.search(r'(?i)^\*(include|import)\b|\b(input|file|library|oldjob)\s*=|^\*restart\s*,\s*read',s)]
    require(not deps, 'External input dependencies need review')
    return p, inp, work, values


def protected(inp):
    files=[BATCH,inp,PROJECT/'project.json',PROJECT/'project.db',RUNTIME/'settings.json',RUNTIME/'live_status.json',
           Path.home()/'.abqjobpilot/recent_projects.json',Path.home()/'.abqjobpilot/app_settings.json']
    return {str(p):sha(p) for p in files}


def processes(work):
    cmd='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    entries=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],text=True,encoding='utf8',errors='replace'))
    conflicts=[]
    for p in entries:
        name=p['Name'].lower(); line=p.get('CommandLine') or ''
        solver=bool(re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',name))
        target=name in {'cmd.exe','python.exe','pythonw.exe'} and (JOB.lower() in line.lower() or str(work).lower() in line.lower())
        if solver or target: conflicts.append(p)
    return dict(observed_at=now(),process_count=len(entries),conflicts=conflicts)


def request(inp,work,task_id=None):
    return JobRequest(inp_path=str(inp),job_name=JOB,cpus=14,gpus=0,working_dir=str(work),
        run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,
        batch='run_017_P01_authorized_run018',strategy='P01_CTR',metadata={
            'notes':f'run_018; task_id={task_id}; project_id={PID}; inp_sha256={DIGEST}; max_attempts=1; retries=0; USER GUI Start Queue only',
            'project_id':PID,'inp_sha256':DIGEST,'task_id':task_id,'max_attempts':1,'auto_retries':0})


def inspect_queue(api,inp,work):
    listing=api.list_jobs()
    require(listing['status']=='OK' and not listing['errors'], 'Queue query failed')
    jobs=listing['jobs']
    matching=[j for j in jobs if j.get('job_name')==JOB or Path(j.get('work_dir','')).resolve()==work or Path(j.get('inp_path','')).resolve()==inp]
    require(len(matching)<=1,'Duplicate/conflicting P01 identities')
    terminal={'COMPLETED_OK','COMPLETED_WITH_WARNINGS','FAILED_FATAL','FAILED_NUMERICAL','FAILED_INPUT','FAILED_LICENSE','DATACHECK_FAILED','DATACHECK_FAILED_INVALID_GPU_OPTION','SKIPPED','CANCELLED'}
    require(all(j.get('raw_status',j['status']) in terminal for j in jobs if j not in matching),'Other pending or unresolved Queue record')
    if matching:
        j=matching[0]
        expected=dict(job_name=JOB,inp_path=str(inp),work_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True)
        require(all(j.get(k)==v for k,v in expected.items()), 'Existing P01 identity/configuration conflict')
        require(DIGEST in j.get('notes','') and sha(inp)==DIGEST,'Existing P01 lacks matching hash evidence')
    return listing,matching


def check(task_id=None):
    point,inp,work,params=frozen()
    api=AbqJobPilotClient();caps=api.capabilities()
    require(caps['application_version']=='0.2.2' and not caps['capabilities']['solver_start'],'Unexpected public API')
    settings=api.get_project_settings(project_id=PID).to_dict()
    require(settings['status']=='PERSISTED' and settings['persisted'] is True and settings['exists'] is True,'Settings not persisted')
    require(not settings['errors'] and not settings['defaulted_fields'],'Settings error/default fallback')
    require(settings['project_id']==PID and Path(settings['project_path']).resolve()==PROJECT,'Project mismatch')
    require(Path(settings['runtime_dir']).resolve()==RUNTIME and Path(settings['settings_file']).resolve()==RUNTIME/'settings.json','Runtime mismatch')
    values=settings['settings']
    require(values==settings['effective_settings']==read(RUNTIME/'settings.json'),'Settings disagree')
    expected=dict(abaqus_cmd=r'D:\ABAQUS2024\Commands\abq2024.bat',default_cpus=14,default_gpus=0,use_gpu=False,run_datacheck=True,run_full=True,auto_shutdown_enabled=False)
    require(all(type(values.get(k)) is type(v) and values[k]==v for k,v in expected.items()),'Settings outside authorization')
    require(Path(values['abaqus_cmd']).is_file() and config.ABAQUS_CMD==values['abaqus_cmd'],'Command missing/mismatch')
    info=api.show_project(project_id=PID).to_dict()
    require(info['status']=='OK' and info['project']['project_id']==read(PROJECT/'project.json')['project_id']==PID,'Project ID mismatch')
    scoped=api.for_project(project_id=PID)
    require(Path(scoped.runtime_dir).resolve()==RUNTIME,'Scoped runtime mismatch')
    listing,existing=inspect_queue(scoped,inp,work)
    owner=runner_ownership_state(RUNTIME);live=read(RUNTIME/'live_status.json')
    require(owner['state']=='ABSENT' and live.get('phase')=='IDLE' and not live.get('process_identity'),'Runner active/unresolved ownership or interruption')
    proc=processes(work);require(not proc['conflicts'],'Solver/target process conflict')
    require(work.is_dir() and not any(work.iterdir()),'Output directory not empty')
    req=request(inp,work,task_id)
    pre=scoped.preflight(req).to_dict();dry=scoped.enqueue(req,dry_run=True).to_dict()
    require(pre['status']=='PREVIEW_READY' and not pre['errors'],'Preflight failed')
    require(dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None,'Dry-run failed')
    require(not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected')),'Dry-run side effect')
    require(Path(pre['expected_odb_path']).resolve()==repo_path(point['expected_odb']),'Expected ODB mismatch')
    require('cpus=14' in pre['command_preview'] and 'gpus=' not in pre['command_preview'],'Preview resources mismatch')
    evidence=dict(observed_at=now(),status='PASS',point=point,parameters=params,settings=settings,project=info,capabilities=caps,
        source_head=git('rev-parse','HEAD'),source_working_tree=git('status','--short'),input_sha256=sha(inp),
        command_sha256=sha(Path(values['abaqus_cmd'])),queue=listing,runner_ownership=owner,live_status=live,
        process_observation=proc,preflight=pre,dry_run=dry,external_input_dependencies=[])
    return scoped,req,evidence,existing


def prepare():
    _,inp,_,_=frozen();before=protected(inp)
    qhash=sha(RUNTIME/'queue.json')
    _,_,evidence,_=check()
    require(before==protected(inp) and qhash==sha(RUNTIME/'queue.json'),'Read-only checks changed protected state')
    save(RUN/'checkpoints/protected_before.json',before)
    save(OUT/'admission.json',evidence)
    print(json.dumps(dict(status='PASS',settings='PERSISTED',preflight=evidence['preflight']['status'],dry_run=evidence['dry_run']['status'],owner=evidence['runner_ownership']['state'],input_sha256=evidence['input_sha256'])))


def enqueue_once():
    _,inp,work,params=frozen()
    require(read(OUT/'admission.json')['status']=='PASS','Missing admission')
    require(protected(inp)==read(RUN/'checkpoints/protected_before.json'),'Protected state changed')
    db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3';require(db.is_file(),'Existing Hub absent')
    hub=Hub(db,lease_seconds=1800);identity=hub.register('MAIN','codex-main-run018-p01-queue')
    scope=dict(run_id='run_018',authorization_source='Explicit human P01 Queue-only Submission message',project_id=PID,
        project_path=str(PROJECT),inp_path=str(inp),inp_sha256=DIGEST,job_name=JOB,working_dir=str(work),parameters=params,
        cpus=14,gpus=0,run_datacheck=True,run_full=True,max_jobs=1,max_attempts=1,automatic_retries=0,
        codex_enqueue_allowed=True,codex_solver_start_allowed=False,user_manual_gui_single_start_authorized=True,
        excluded_points=['P02','P03','P04','P05'],science_state='NOT_EVALUATED')
    task=hub.create_task(identity['agent_id'],'MAIN','enqueue_p01_once',scope,'run018-p01-enqueue-'+DIGEST,depends=['a37ef4d7-ed7f-4bb3-803f-3c8726916548'])
    tid=task['task_id'];hub.approve(tid,identity['agent_id'],'enqueue');hub.require_approval(tid,'enqueue')
    lease=hub.claim(tid,identity,'run018-p01-enqueue-evidence-v1')
    save(OUT/'private/lease.json',lease)
    save(OUT/'authorization.json',dict(observed_at=now(),task_id=tid,identity=identity,scope=scope,hub_approvals=['enqueue']))
    try:
        api,req,admission,existing=check(tid)
        save(OUT/'admission_before_enqueue.json',admission);save(OUT/'request.json',req.to_dict())
        with queue_transaction(RUNTIME):
            listing,existing=inspect_queue(api,inp,work)
            require(runner_ownership_state(RUNTIME)['state']=='ABSENT','Concurrent Runner ownership')
            require(protected(inp)==read(RUN/'checkpoints/protected_before.json') and not any(work.iterdir()),'Configuration/input/output changed')
            if existing:
                qid=existing[0]['queue_id'];require(existing[0]['status']=='QUEUED','Existing P01 no longer queued; report actual state without re-enqueue')
                response=dict(status='EXISTING_VERIFIED',job_id=qid,solver_started=False,runner_started=False)
            else:
                require(not (RUN/'checkpoints/enqueue_attempt.json').exists(),'Previous attempt: NEVER retry')
                save(RUN/'checkpoints/enqueue_attempt.json',dict(observed_at=now(),task_id=tid,attempt=1,retry_forbidden=True,request_sha256=sha(OUT/'request.json')))
                response=api.enqueue(req,dry_run=False).to_dict()
                save(OUT/'enqueue_response.json',response)
                require(response['status']=='ENQUEUED' and response['job_id'],'Enqueue rejected/uncertain; no retry')
                require(not any(response[k] for k in ('solver_started','runner_started','forbidden_mutations_detected')),'Unexpected enqueue side effect')
                qid=response['job_id']
            after,match=inspect_queue(api,inp,work)
            require(len(match)==1 and match[0]['queue_id']==qid and match[0]['status']=='QUEUED','Queued identity/state mismatch')
            require(not match[0]['started_at'] and not match[0]['ended_at'],'Execution unexpectedly started')
            prior=[j for j in listing['jobs'] if j.get('queue_id')!=qid]
            require(prior==[j for j in after['jobs'] if j.get('queue_id')!=qid],'Historical queue records changed')
            save(OUT/'queue_after_enqueue.json',after)
        status=api.status(job_id=qid).to_dict();outputs=api.locate_outputs(job_id=qid).to_dict()
        save(OUT/'status_after_enqueue.json',status);save(OUT/'outputs_after_enqueue.json',outputs)
        require(status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists'],'Job unexpectedly started')
        require(not any(work.iterdir()) and runner_ownership_state(RUNTIME)['state']=='ABSENT','Output/Runner activity')
        observation=processes(work);save(OUT/'private/processes_after.json',observation)
        require(not observation['conflicts'],'Solver process observed')
        require(protected(inp)==read(RUN/'checkpoints/protected_before.json'),'Protected state changed')
        require(git('rev-parse','HEAD')==admission['source_head'] and git('status','--short')==admission['source_working_tree'],'External installation changed')
        result=dict(observed_at=now(),status='PASS',scope='QUEUE_ONLY',execution_state='QUEUED / AWAITING_GUI_START',
            task_id=tid,queue_id=qid,job_name=JOB,inp_path=str(inp),inp_sha256=DIGEST,working_dir=str(work),
            cpus=14,gpus=0,run_datacheck=True,run_full=True,pending_jobs=1,other_pending_jobs=0,
            new_enqueues=0 if existing else 1,datacheck='NOT_STARTED',full_analysis='NOT_STARTED',
            solver_started=False,odb_exists=False,protected_files_unchanged=True,automatic_retries=0,science_state='NOT_EVALUATED')
        save(OUT/'enqueue_result.json',result)
        artifacts=[]
        for name in ['queue_p01_once.py','admission.json','admission_before_enqueue.json','authorization.json','request.json','enqueue_response.json','queue_after_enqueue.json','status_after_enqueue.json','outputs_after_enqueue.json','enqueue_result.json']:
            p=OUT/name
            if p.exists(): artifacts.append(hub.artifact(tid,identity['agent_id'],p,dict(run_id='run_018',method='public API enqueue-only; manual GUI start pending',project_id=PID,queue_id=qid),version='run018-v1'))
        hub.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED')
        message=hub.message(tid,identity['agent_id'],'MAIN',result,'run018-p01-queued-result-v1')
        save(OUT/'agenthub_receipt.json',dict(task_id=tid,queue_id=qid,identity=identity,artifacts=artifacts,message_id=message['message_id'],task=hub.task(tid),cross_session_notification_claimed=False))
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        hub.fail(lease,'P01_ENQUEUE_OR_EVIDENCE_FAILED',str(exc),retryable=False)
        raise


if __name__=='__main__':
    try:
        require(len(sys.argv)==2 and sys.argv[1] in {'prepare','enqueue-once'},'Use prepare or enqueue-once')
        (prepare if sys.argv[1]=='prepare' else enqueue_once)()
    except Exception:
        save(OUT/'private'/('failure_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'),dict(observed_at=now(),status='BLOCKED',traceback=traceback.format_exc(),automatic_retry_forbidden=True))
        raise
