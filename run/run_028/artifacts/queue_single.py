"""Authorized one-job queue-only submission; never launches the Runner or Abaqus."""
import hashlib, importlib.util, json, re, subprocess, sys, traceback
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_028'
A = RUN / 'artifacts'
P = A / 'private'
ABQ = Path(r'D:\Projects\abqjobpilot')
PROJECT = ROOT / 'agenthub_sp_invopt/abqjobpilot_project'
RT = PROJECT / 'runtime'
PID = 'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
FROZEN = ROOT / 'run/run_027/artifacts/prepared_candidate.json'
EXPECTED = 'dae9345bc60973c27edec498dfbd27f269e1f5bbe151316918862954faac40c9'
sys.path[:0] = [str(ROOT), str(ABQ)]
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state, queue_transaction
from abqjobpilot.recovery_assessment import assess_runtime
from agenthub_sp_invopt.hub import Hub

spec = importlib.util.spec_from_file_location('settings_reader', ROOT / 'run/run_017/artifacts/preview_batch.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

def now(): return datetime.now().astimezone().isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    if not p.is_file(): return None
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def save(p,obj):
    assert not p.exists(), f'Existing record: {p}'
    t=p.with_name(p.name+'.tmp')
    with t.open('x',encoding='utf8') as f: json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
    read(t);t.replace(p)
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def frozen():
    f=read(FROZEN)
    assert f['job_name']=='SPIO_R027_CTR_M0025' and f['project_id']==PID
    assert f['candidate_sha256']==EXPECTED and f['queue_id'] is None
    inp=Path(f['candidate_inp_absolute']);work=Path(f['working_dir_absolute'])
    assert inp.resolve()==(ROOT/'run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp').resolve()
    assert work.resolve()==(ROOT/'run/run_027/artifacts/solver/SPIO_R027_CTR_M0025').resolve()
    assert sha(inp)==EXPECTED and work.is_dir() and not any(work.iterdir()), 'INP changed or output conflict'
    source=Path(f['source_inp_absolute'])
    assert sha(source)==f['source_sha256']
    old=b'0.001, 1., 1e-12, 0.005\n';new=b'0.001, 1., 1e-12, 0.0025\n'
    assert source.read_bytes().count(old)==1 and inp.read_bytes()==source.read_bytes().replace(old,new,1)
    assert f['only_input_change']['before']==old.decode().strip() and f['only_input_change']['after']==new.decode().strip()
    assert sha(ROOT/f['comparison_contract'])==f['comparison_contract_sha256']
    contract=read(ROOT/f['comparison_contract'])
    assert contract['version']=='run027-adjacent-refinement-v1'
    assert sha(ROOT/contract['comparison_implementation_path'])==contract['comparison_implementation_sha256']
    return f,inp,work

def runtime_state():
    own=runner_ownership_state(RT); recovery=assess_runtime(RT,project_db=PROJECT/'project.db')
    cmd='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    raw=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],encoding='utf8',errors='replace'))
    procs=raw if isinstance(raw,list) else [raw]
    conflicts=[p for p in procs if re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',p.get('Name') or '',re.I)
               or ((p.get('Name') or '').lower() in ('python.exe','pythonw.exe','cmd.exe') and 'spio_r027_ctr_m0025' in (p.get('CommandLine') or '').lower())]
    assert own['state']=='ABSENT' and recovery['status']=='CLEAN' and recovery['live_phase']=='IDLE'
    assert not recovery['lock_files'] and not recovery['errors'] and not recovery['running_queue_ids'] and not conflicts
    return {'at':now(),'owner':own,'recovery':recovery,'process_conflicts':conflicts}

TERMINAL={'COMPLETED_OK','COMPLETED_WITH_WARNINGS','FAILED_FATAL','FAILED_NUMERICAL','FAILED_INPUT','FAILED_LICENSE','DATACHECK_FAILED','DATACHECK_FAILED_INVALID_GPU_OPTION','SKIPPED','CANCELLED'}
def queue_state(api,f,inp,work):
    q=api.list_jobs();h=api.list_project_jobs(project_id=PID).to_dict()
    assert q['status']=='OK' and h['status']=='OK' and not q['errors'] and not h['errors']
    existing=[];history=[]
    for j in q['jobs']:
        same=(j.get('job_name')==f['job_name'] or Path(j.get('inp_path') or '').resolve()==inp.resolve() or Path(j.get('work_dir') or '').resolve()==work.resolve())
        if same:
            assert j.get('job_name')==f['job_name'] and Path(j.get('inp_path') or '').resolve()==inp.resolve() and Path(j.get('work_dir') or '').resolve()==work.resolve(), 'Candidate identity collision'
            assert j.get('cpus')==14 and j.get('gpus')==0 and j.get('run_datacheck') is True and j.get('run_full') is True
            assert EXPECTED in (j.get('notes') or ''), 'Existing queue lacks frozen hash'
            assert j.get('status')=='QUEUED' and not j.get('started_at') and not j.get('ended_at'), 'Existing attempted/unknown candidate'
            existing.append(j)
        else:
            assert j.get('raw_status') in TERMINAL, 'Other executable/unresolved queue job'
    assert len(existing)<=1
    for j in h['jobs']:
        if j.get('job_name')==f['job_name'] or Path(j.get('inp_path') or '').resolve()==inp.resolve(): history.append(j)
    assert not history, 'Candidate already appears in execution history'
    return {'queue':q,'history':h,'existing':existing}

def protected(f):
    c=read(ROOT/f['comparison_contract'])
    paths=[FROZEN,Path(f['candidate_inp_absolute']),Path(f['source_inp_absolute']),ROOT/f['comparison_contract'],ROOT/c['comparison_implementation_path'],PROJECT/'project.json',RT/'settings.json']
    return {str(p):sha(p) for p in paths}

def request(f,task_id=None):
    return JobRequest(inp_path=f['candidate_inp_absolute'],job_name=f['job_name'],working_dir=f['working_dir_absolute'],cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='enqueue_only',allow_solver_submit=False,batch='run028_one_center_refinement',strategy='ONE_AUTHORIZED_JOB',metadata={'run':'run_028','project_id':PID,'task_id':task_id,'inp_sha256':EXPECTED,'maximum_attempts':1,'automatic_retries':0,'notes':f'run028; project_id={PID}; inp_sha256={EXPECTED}; task_id={task_id}; 14CPU 0GPU; one Datacheck then Full; zero retries; manual GUI Start Queue only; V02 forbidden'})

def prepare():
    assert not RUN.joinpath('run.json').exists()
    P.mkdir(parents=True,exist_ok=True)
    (RUN/'checkpoints').mkdir(exist_ok=True)
    git_state={'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short')}
    save(RUN/'checkpoints/start.json',{'at':now(),'git':git_state,'python':sys.executable,'version':sys.version.split()[0]})
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_028','stage':'single authorized queue-only submission','status':'RUNNING','start_time':now(),'end_time':None,'git':git_state,'python_interpreter':sys.executable,'inputs':[{'path':'run/run_027/artifacts/prepared_candidate.json','sha256':sha(FROZEN)}],'outputs':[],'validation':[],'errors':[]})
    (RUN/'summary.md').write_text('# run_028 — 单项授权 Queue-only\n\nRUNNING；禁止 Codex 启动 Solver。\n',encoding='utf8')
    f,inp,work=frozen(); before=protected(f);qsha=sha(RT/'queue.json')
    api,settings=reader.inspect_settings()
    s=settings['settings_response'];v=s['effective_settings']
    assert s['status']=='PERSISTED' and s['project_id']==PID and Path(s['project_path']).resolve()==PROJECT.resolve()
    assert v['default_cpus']==14 and v['default_gpus']==0 and not v['use_gpu'] and v['run_datacheck'] and v['run_full']
    assert Path(v['abaqus_cmd']).is_file() and 'abq2024' in Path(v['abaqus_cmd']).name.lower()
    assert settings['source_version']=='0.2.2' and settings['source_working_tree']==''
    state=runtime_state();qs=queue_state(api,f,inp,work)
    req=request(f)
    pre=api.preflight(req).to_dict();dry=api.enqueue(req,dry_run=True).to_dict()
    assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors']
    assert dry['job_id'] is None and not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'))
    assert Path(pre['expected_odb_path']).resolve()==(work/(f['job_name']+'.odb')).resolve()
    assert protected(f)==before and sha(RT/'queue.json')==qsha and not any(work.iterdir())
    save(A/'admission.json',{'at':now(),'status':'PASS','frozen':f,'protected':before,'queue_sha256':qsha,'settings':settings,'runtime_state':state,'queue_state':qs,'preflight':pre,'dry_run':dry})
    print(json.dumps({'status':'PASS_ADMISSION','preflight':pre['status'],'dry_run':dry['status'],'existing_candidate':len(qs['existing'])}))

def enqueue():
    assert not (A/'enqueue_result.json').exists() and not (RUN/'checkpoints/enqueue_attempt.json').exists(), 'Prior attempt; reconcile read-only'
    ad=read(A/'admission.json'); assert ad['status']=='PASS'
    f,inp,work=frozen(); assert protected(f)==ad['protected']
    api,settings=reader.inspect_settings(); assert settings['settings_response']==ad['settings']['settings_response'] and settings['source_head']==ad['settings']['source_head'] and settings['source_working_tree']==ad['settings']['source_working_tree']
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=1800)
    identity=hub.register('MAIN','codex-main-run028-single-queue')
    scope={'run':'run_028','authorization_source':'Explicit user single-job authorization in current conversation','job_name':f['job_name'],'inp_sha256':EXPECTED,'project_id':PID,'working_dir':str(work),'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'maximum_attempts':1,'automatic_retries':0,'only_queue_submit_by_codex':True,'solver_start_by_user_gui_only':True,'V02_authorized_by_this_task':False,'comparison_contract_sha256':f['comparison_contract_sha256']}
    task=hub.create_task(identity['agent_id'],'MAIN','enqueue_one_center_refinement',scope,'run028-one-authorized-queue-v1',depends=('4c055b2b-1abb-4669-9394-677617cd0cee',))['task_id']
    hub.approve(task,identity['agent_id'],'enqueue')
    lease=hub.claim(task,identity,'run028-main-queue-claim-v1')
    save(P/'hub_session.json',{'identity':identity,'task_id':task,'lease':lease})
    save(A/'authorization.json',{'at':now(),'task_id':task,'scope':scope})
    with queue_transaction(RT):
        runtime_state();qs=queue_state(api,f,inp,work)
        assert qs['queue']==ad['queue_state']['queue'] and protected(f)==ad['protected'] and not any(work.iterdir())
        hub.require_approval(task,'enqueue')
        req=request(f,task);save(A/'request.json',req.to_dict())
        if qs['existing']:
            response={'status':'EXISTING_VERIFIED','job_id':qs['existing'][0]['queue_id'],'solver_started':False,'runner_started':False}
        else:
            save(RUN/'checkpoints/enqueue_attempt.json',{'at':now(),'attempt_number':1,'request_sha256':sha(A/'request.json'),'retry_forbidden':True,'unknown_outcome_requires_readonly_reconciliation':True})
            response=api.enqueue(req,dry_run=False).to_dict()
        save(A/'enqueue_response.json',response)
        assert response['status'] in ('ENQUEUED','EXISTING_VERIFIED') and response['job_id'] and not response['solver_started'] and not response['runner_started']
        after=queue_state(api,f,inp,work)
        assert len(after['existing'])==1 and after['existing'][0]['queue_id']==response['job_id']
        assert len(after['queue']['jobs'])==len(qs['queue']['jobs'])+(0 if qs['existing'] else 1)
        save(A/'queue_after.json',after)
    post=runtime_state(); assert protected(f)==ad['protected'] and sha(inp)==EXPECTED
    status=api.status(job_id=response['job_id']).to_dict();outputs=api.locate_outputs(job_id=response['job_id']).to_dict()
    assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists'] and not any(work.iterdir())
    save(A/'postcheck.json',{'at':now(),'runtime':post,'status':status,'outputs':outputs,'no_solver_or_datacheck_start':True})
    result={'at':now(),'status':'SPIO_R027_CTR_M0025_QUEUED_AWAITING_MANUAL_START','task_id':task,'queue_id':response['job_id'],'job_name':f['job_name'],'inp_path':str(inp),'inp_sha256':EXPECTED,'working_dir':str(work),'project_id':PID,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0,'datacheck_started':False,'solver_started':False,'V02_queued':False,'numerical_qualification':'NOT_EVALUATED'}
    save(A/'enqueue_result.json',result)
    for path in (A/'authorization.json',A/'admission.json',A/'request.json',A/'enqueue_response.json',A/'queue_after.json',A/'postcheck.json',A/'enqueue_result.json'):
        hub.artifact(task,identity['agent_id'],path,{'run':'run_028','scope':'single queue-only; no Solver','input_sha256':EXPECTED},version='run028-v1')
    hub.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED')
    assert hub.verify_chain()
    save(A/'agenthub_receipt.json',{'at':now(),'task_id':task,'queue_id':response['job_id'],'audit_chain_valid':True,'odb_task_created':False,'reason':'Only after real job completion; cross-session messages do not auto-wake'})
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try:
        assert sys.argv[1] in ('prepare','enqueue')
        (prepare if sys.argv[1]=='prepare' else enqueue)()
    except Exception:
        P.mkdir(parents=True,exist_ok=True)
        save(P/('failure_'+datetime.now().strftime('%H%M%S%f')+'.json'),{'at':now(),'status':'BLOCKED','traceback':traceback.format_exc(),'no_automatic_retry':True})
        raise
