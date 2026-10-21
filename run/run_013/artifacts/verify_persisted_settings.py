"""Strict ID-scoped persisted Settings evidence and non-submitting preview refresh."""
import datetime,hashlib,json,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_013'
OUT=RUN/'artifacts'
ABQ=Path(r'D:\Projects\abqjobpilot')
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project'
INP=ROOT/'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp'
INP_HASH='fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a'
sys.path[:0]=[str(ABQ),str(ROOT/'agenthub_sp_invopt')]
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot import config
from hub import Hub
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    if not p.is_file(): return None
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def tree(p): return {x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def write(p,data):
    if p.exists(): raise FileExistsError('Evidence exists; do not overwrite '+str(p))
    tmp=p.with_suffix('.tmp.json')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    read(tmp);tmp.replace(p)
def git(root,*args): return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
def main():
    started=now()
    historical_before=tree(ROOT/'run/run_012')
    protected=[PROJECT/'project.json',PROJECT/'project.db',PROJECT/'runtime/settings.json',PROJECT/'runtime/queue.json',PROJECT/'runtime/live_status.json',INP,ROOT/'inverse/hollomon.py',Path.home()/'.abqjobpilot/recent_projects.json',Path.home()/'.abqjobpilot/app_settings.json']
    hashes_before={str(p):sha(p) for p in protected}
    candidate_before=tree(INP.parent)
    initial={'observed_at':started,'git':{'branch':git(ROOT,'branch','--show-current'),'head':git(ROOT,'rev-parse','HEAD'),'remote':git(ROOT,'remote','-v'),'working_tree':git(ROOT,'status','--short')},'external_source':{'root':str(ABQ),'head':git(ABQ,'rev-parse','HEAD'),'branch':git(ABQ,'branch','--show-current'),'working_tree':git(ABQ,'status','--short')},'python':sys.executable,'python_version':sys.version,'protected_hashes':hashes_before,'run012_tree_hashes':historical_before,'candidate_directory':candidate_before}
    write(RUN/'checkpoints/initial_state.json',initial)
    api=AbqJobPilotClient()
    caps=api.capabilities()
    write(OUT/'capabilities.json',caps)
    assert caps['application_version']=='0.2.2' and caps['capabilities']['project_settings_read']
    # Resolve by the exact registered ID, not a path alias or fallback recent Project.
    settings_response=api.get_project_settings(project_id=PID).to_dict()
    write(OUT/'settings_api_response.json',settings_response)
    assert settings_response['status']=='PERSISTED' and settings_response['persisted'] is True and settings_response['exists'] is True
    assert settings_response['project_id']==PID and not settings_response['errors']
    assert Path(settings_response['project_path']).resolve()==PROJECT.resolve()
    assert Path(settings_response['runtime_dir']).resolve()==(PROJECT/'runtime').resolve()
    settings_path=Path(settings_response['settings_file'])
    assert settings_path.resolve()==(PROJECT/'runtime/settings.json').resolve() and settings_path.is_file()
    assert not settings_response['defaulted_fields'], 'Do not accept code-default substitution'
    saved=settings_response['settings']
    assert saved==read(settings_path)==settings_response['effective_settings']
    expected={'abaqus_cmd':r'D:\ABAQUS2024\Commands\abq2024.bat','default_cpus':14,'use_gpu':False,'default_gpus':0,'run_datacheck':True,'run_full':True,'auto_shutdown_enabled':False}
    assert all(type(saved[k]) is type(v) and saved[k]==v for k,v in expected.items())
    command=Path(saved['abaqus_cmd'])
    assert command.is_file() and config.ABAQUS_CMD==str(command)
    project_info=api.show_project(project_id=PID).to_dict()
    assert project_info['status']=='OK' and project_info['project']['project_id']==PID
    assert read(PROJECT/'project.json')['project_id']==PID
    assert sha(INP)==INP_HASH and INP.stem=='SPIO_R008_Q200_N010_Candidate'
    scoped=api.for_project(project_id=PID)
    assert Path(scoped.runtime_dir).resolve()==(PROJECT/'runtime').resolve()
    q_before=scoped.list_jobs()
    assert q_before['status']=='OK' and q_before['jobs']==[]
    old_request=read(ROOT/'run/run_012/artifacts/request.json')
    request=JobRequest(inp_path=str(INP),job_name=INP.stem,cpus=saved['default_cpus'],gpus=saved['default_gpus'] if saved['use_gpu'] else 0,working_dir=str(INP.parent),run_datacheck=saved['run_datacheck'],run_full=saved['run_full'],submission_mode='preview_only',allow_solver_submit=False,metadata={'run_id':'run_013','configuration_source':'PERSISTED_PROJECT_SETTINGS','settings_sha256':sha(settings_path),'project_id':PID,'inp_sha256':INP_HASH})
    request_dict=request.to_dict()
    comparable_fields=['inp_path','job_name','cpus','gpus','working_dir','run_datacheck','run_full','submission_mode','allow_solver_submit']
    assert all(request_dict[k]==old_request[k] for k in comparable_fields)
    write(OUT/'request.json',request_dict)
    preflight=scoped.preflight(request).to_dict()
    write(OUT/'preflight.json',preflight)
    assert preflight['status']=='PREVIEW_READY' and not preflight['errors']
    dry=scoped.enqueue(request,dry_run=True).to_dict()
    write(OUT/'dry_run.json',dry)
    assert dry['status']=='DRY_RUN_READY' and not dry['errors']
    assert not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
    old_preflight=read(ROOT/'run/run_012/artifacts/preflight.json')
    assert preflight['command_preview']==old_preflight['command_preview']
    q_after=scoped.list_jobs()
    hashes_after={str(p):sha(p) for p in protected}
    historical_after=tree(ROOT/'run/run_012')
    assert q_after['status']=='OK' and q_after['jobs']==[]
    assert hashes_before==hashes_after and candidate_before==tree(INP.parent)
    assert historical_before==historical_after
    result={'observed_at':now(),'status':'PASS','scope':'Strict persisted Project Settings and engineering preflight/dry-run only','project_id':PID,'project_name':project_info['project']['name'],'settings_status':'PERSISTED','settings_path':settings_path.relative_to(ROOT).as_posix(),'settings_sha256':sha(settings_path),'verified_settings':saved,'defaulted_fields':[],'abaqus_command_exists':True,'abaqus_command_sha256':sha(command),'source_version':caps['application_version'],'source_head':initial['external_source']['head'],'source_working_tree':initial['external_source']['working_tree'],'candidate_inp':INP.relative_to(ROOT).as_posix(),'candidate_sha256':INP_HASH,'preflight':'PREVIEW_READY','dry_run':'DRY_RUN_READY','run012_request_fields_unchanged':comparable_fields,'run012_command_preview_matches':True,'run012_history_unchanged':True,'queue_empty_before_after':True,'queue_sha256':sha(PROJECT/'runtime/queue.json'),'protected_files_unchanged':True,'candidate_directory_unchanged':True,'solver_started':False,'datacheck_started':False,'queue_written':False,'settings_written':False,'first_hollomon_forward_solve_authorization_request_ready':True,'execution_authorization_granted':False,'science_state':'NOT_EVALUATED','limitations':['Abaqus execution, license checkout, solver convergence and model physics are not verified by this preview.','Candidate material retains the true-total-strain interpretation and is not experimentally validated.','Historical source INP equivalence to the edited CAE database remains UNKNOWN.']}
    write(OUT/'verification_result.json',result)
    resolution={'observed_at':now(),'status':'RESOLVED_BY_NEW_EVIDENCE','prior_run':'run_012','prior_task_id':'7d56b96f-bae2-473e-b9f6-89afb6dbcd14','blocker_code':'PROJECT_RUNTIME_SETTINGS_NOT_SAVED','resolving_run':'run_013','evidence':['run/run_013/artifacts/settings_api_response.json','run/run_013/artifacts/verification_result.json'],'prior_history_unchanged':True,'scope':'Settings persistence blocker only; not scientific validation or execution authorization'}
    write(OUT/'run012_blocker_resolution.json',resolution)
    write(RUN/'checkpoints/after_checks.json',{'observed_at':now(),'protected_hashes':hashes_after,'run012_tree_hashes':historical_after,'queue':q_after,'git_head':git(ROOT,'rev-parse','HEAD'),'abq_source_head':git(ABQ,'rev-parse','HEAD'),'abq_source_status':git(ABQ,'status','--short')})
    db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3';assert db.is_file()
    hub=Hub(db,lease_seconds=300)
    identity=hub.register('MAIN','codex-main-run013-persisted-settings')
    task=hub.create_task(identity['agent_id'],'MAIN','verify_persisted_settings',{'run_id':'run_013','project_id':PID,'prior_run':'run_012','allowed':'strict settings read and API preview only'},'run013-main-persisted-settings-v1',depends=['7d56b96f-bae2-473e-b9f6-89afb6dbcd14'])
    lease=hub.claim(task['task_id'],identity,'run013-main-evidence-record-v1')
    write(OUT/'private/lease.json',lease)
    artifacts=[]
    for name in ['settings_api_response.json','request.json','preflight.json','dry_run.json','verification_result.json','run012_blocker_resolution.json']:
        artifacts.append(hub.artifact(task['task_id'],identity['agent_id'],OUT/name,{'run_id':'run_013','method':'strict public get_project_settings(project_id), preflight and enqueue(dry_run=True)','source_head':initial['external_source']['head'],'project_id':PID,'science':'NOT_EVALUATED'},version='run013-v1'))
    hub.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED')
    message=hub.message(task['task_id'],identity['agent_id'],'MAIN',{'type':'BLOCKER_RESOLVED_BY_NEW_EVIDENCE','task_id':task['task_id'],'resolution':resolution,'status':'PASS','settings_status':'PERSISTED','first_hollomon_forward_solve_authorization_request_ready':True,'solver_execution_authorized':False},'run013-settings-resolution-v1')
    receipts=[m for m in hub.poll_messages(identity) if m['task_id']==task['task_id']]
    assert receipts and hub.verify_chain()
    assert all(sha(Path(a['path']))==a['sha256'] for a in artifacts)
    write(OUT/'agenthub_receipt.json',{'identity':identity,'task_id':task['task_id'],'execution':'COMPLETED','evidence':'RECORDED','science':'NOT_EVALUATED','artifacts':[{k:a[k] for k in ['artifact_id','sha256','version']} for a in artifacts],'outbox_id':message['message_id'],'inbox_receipts':receipts,'audit_hash_chain_valid':True,'registered_artifact_hashes_verified':True})
    write(RUN/'run.json',{'schema_version':'1.0','run_id':'run_013','stage':'Persisted Settings verification and blocker resolution','objective':'Resolve run_012 Settings prerequisite using strict public API evidence','status':'PASS','start_time':started,'end_time':now(),'python_interpreter':sys.executable,'git_head':initial['git']['head'],'git_branch':initial['git']['branch'],'inputs':[{'path':'agenthub_sp_invopt/abqjobpilot_project/project.json','role':'Project identity'},{'path':settings_path.relative_to(ROOT).as_posix(),'sha256':sha(settings_path),'role':'persisted configuration'},{'path':INP.relative_to(ROOT).as_posix(),'sha256':INP_HASH,'role':'candidate input'},{'path':'run/run_012/run.json','role':'immutable prior blocked record'}],'outputs':[{'path':'run/run_013/artifacts/'+name,'role':name.removesuffix('.json')} for name in ['settings_api_response.json','preflight.json','dry_run.json','verification_result.json','run012_blocker_resolution.json','agenthub_receipt.json']],'validation':[{'check':name,'status':'PASS','evidence':'run/run_013/artifacts/'+file,'scope':scope} for name,file,scope in [('Strict persisted settings','settings_api_response.json','Exact Project ID; no defaulted fields'),('Preflight and dry-run refresh','verification_result.json','No Abaqus execution'),('Run012 preserved and blocker resolved','run012_blocker_resolution.json','New evidence only'),('AgentHub evidence','agenthub_receipt.json','Six hashes, durable resolution message and valid audit chain')]],'errors':[],'task_id':task['task_id'],'run012_settings_blocker_resolved':True,'first_hollomon_forward_solve_authorization_request_ready':True,'science_state':'NOT_EVALUATED','solver_started':False,'datacheck_started':False,'queue_written':False,'settings_written':False,'commit_performed':False,'push_performed':False})
    print(json.dumps({'status':'PASS','settings':'PERSISTED','preflight':preflight['status'],'dry_run':dry['status'],'task_id':task['task_id'],'ready_to_request_first_forward_solve':True},indent=2))
if __name__=='__main__':
    try: main()
    except Exception:
        (OUT/'private/failed_attempt01.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
