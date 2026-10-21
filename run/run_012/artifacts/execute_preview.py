"""Official non-submitting previews with honest persisted-vs-user configuration provenance."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_012'
OUT=RUN/'artifacts'
ABQ=Path(r'D:\Projects\abqjobpilot')
sys.path[:0]=[str(ABQ),str(ROOT/'agenthub_sp_invopt')]
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot import config
from hub import Hub
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def sha(p):
    if not p.is_file(): return None
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists(): raise FileExistsError('Preserve prior evidence: '+str(p))
    tmp=p.with_suffix('.tmp.json')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    json.loads(tmp.read_text(encoding='utf-8'))
    tmp.replace(p)
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
project=ROOT/'agenthub_sp_invopt/abqjobpilot_project'
runtime=project/'runtime'
settings_path=runtime/'settings.json'
inp=ROOT/'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp'
expected_hash='fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a'
pid='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
user_settings={'abaqus_cmd':r'D:\ABAQUS2024\Commands\abq2024.bat','default_cpus':14,'use_gpu':False,'default_gpus':0,'run_datacheck':True,'run_full':True,'auto_shutdown_enabled':False}
started=now()
protected=[project/'project.json',runtime/'queue.json',runtime/'live_status.json',settings_path,project/'project.db',inp,Path.home()/'.abqjobpilot/recent_projects.json',Path.home()/'.abqjobpilot/app_settings.json']
before={str(p):sha(p) for p in protected}
outputs_before={p.name:sha(p) for p in inp.parent.iterdir() if p.is_file()}
initial={'observed_at':started,'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short'),'python':sys.executable,'python_version':sys.version,'protected_hashes':before,'candidate_directory_files':outputs_before}
write(RUN/'checkpoints/initial_state.json',initial)
api=AbqJobPilotClient()
caps=api.capabilities()
assert caps['application_version']=='0.2.2'
info=api.show_project(project=str(project)).to_dict()
assert info['status']=='OK' and info['project']['project_id']==pid
assert Path(info['project']['runtime_dir']).resolve()==runtime.resolve()
assert inp.is_file() and sha(inp)==expected_hash
assert Path(user_settings['abaqus_cmd']).is_file()
assert config.ABAQUS_CMD==user_settings['abaqus_cmd'],'Public API command does not match explicit user command'
scoped=api.for_project(project=str(project))
queue_before=scoped.list_jobs()
assert queue_before['status']=='OK' and queue_before['jobs']==[]
saved=json.loads(settings_path.read_text(encoding='utf-8-sig')) if settings_path.is_file() else None
missing=[k for k in user_settings if not isinstance(saved,dict) or k not in saved]
differences={k:{'user':v,'saved':saved[k]} for k,v in user_settings.items() if isinstance(saved,dict) and k in saved and saved[k]!=v}
settings_ok=not missing and not differences
if saved is not None and not settings_ok:
    raise RuntimeError('Saved Settings differ from explicit user parameters; preserve diagnostics and stop')
settings_record={'observed_at':now(),'path':settings_path.relative_to(ROOT).as_posix(),'exists':settings_path.is_file(),'sha256':sha(settings_path),'persisted_values':saved,'user_stated_values':user_settings,'missing_fields':missing,'differences':differences,'status':'PASS' if settings_ok else 'BLOCKED','preview_parameter_source':'PERSISTED_PROJECT_SETTINGS' if settings_ok else 'EXPLICIT_USER_MESSAGE_ONLY','abaqus_command_exists':True,'abaqus_command_sha256':sha(Path(user_settings['abaqus_cmd'])),'note':'No source-code default values were substituted for missing user configuration.'}
write(OUT/'settings_verification.json',settings_record)
write(OUT/'private/nearby_settings_inventory.json',{'selected_global_settings':str(config.SETTINGS_FILE),'selected_global_exists':Path(config.SETTINGS_FILE).is_file(),'legacy_exists':(ABQ/'runtime/settings.json').is_file(),'user_home_settings_paths':[str(p) for p in (Path.home()/'.abqjobpilot').rglob('settings.json')]})
request=JobRequest(inp_path=str(inp),job_name=inp.stem,cpus=14,gpus=0,working_dir=str(inp.parent),submission_mode='preview_only',allow_solver_submit=False,run_datacheck=True,run_full=True,metadata={'run_id':'run_012','configuration_source':settings_record['preview_parameter_source'],'project_id':pid,'inp_sha256':expected_hash})
write(OUT/'request.json',request.to_dict())
preflight=scoped.preflight(request).to_dict()
write(OUT/'preflight.json',preflight)
assert preflight['status']=='PREVIEW_READY',preflight
dry=scoped.enqueue(request,dry_run=True).to_dict()
write(OUT/'dry_run.json',dry)
assert dry['status']=='DRY_RUN_READY' and not dry['queue_file_mutated'] and not dry['solver_started'] and not dry['runner_started'],dry
queue_after=scoped.list_jobs()
after={str(p):sha(p) for p in protected}
outputs_after={p.name:sha(p) for p in inp.parent.iterdir() if p.is_file()}
assert queue_after['status']=='OK' and queue_after['jobs']==[] and before==after and outputs_before==outputs_after
result={'observed_at':now(),'status':'PASS' if settings_ok else 'BLOCKED','scope':'Engineering API preview; no solver, datacheck, license or physical validation','project_id':pid,'project_name':info['project']['name'],'project_root':project.relative_to(ROOT).as_posix(),'stable_version':caps['application_version'],'inp':inp.relative_to(ROOT).as_posix(),'inp_sha256':expected_hash,'project_and_inp_identity':'PASS','settings_status':settings_record['status'],'configuration_source':settings_record['preview_parameter_source'],'preflight_status':preflight['status'],'dry_run_status':dry['status'],'queue_empty_before_after':True,'protected_files_unchanged':True,'candidate_directory_unchanged':True,'queue_sha256_before':before[str(runtime/'queue.json')],'queue_sha256_after':after[str(runtime/'queue.json')],'solver_started':False,'datacheck_started':False,'queue_written':False,'settings_written':False,'auto_shutdown_invoked':False,'scientific_state':'NOT_EVALUATED','single_solver_authorization_request_ready':settings_ok,'blockers':[] if settings_ok else ['PROJECT_RUNTIME_SETTINGS_NOT_SAVED'],'limitations':['This public API preview does not execute Abaqus or verify license/solver capability.','Candidate true-total-strain interpretation remains without experimental validation.']}
write(OUT/'preview_result.json',result)
write(RUN/'checkpoints/after_preview.json',{'observed_at':now(),'protected_hashes':after,'candidate_directory_files':outputs_after,'queue':queue_after})
# This is MAIN recording its own audit, not a simulated CAE session.
db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
assert db.is_file()
hub=Hub(db,lease_seconds=300)
identity=hub.register('MAIN','codex-main-run012-preflight')
task=hub.create_task(identity['agent_id'],'MAIN','audit_preflight_dry_run',{'run_id':'run_012','project_id':pid,'inp_sha256':expected_hash,'allowed':'official public preflight and dry-run only','forbidden':['enqueue','solver','datacheck','settings mutation']},'run012-main-preflight-dryrun-v1',depends=['a4b4805f-4989-4168-a54a-3bbf435b52a6'])
lease=hub.claim(task['task_id'],identity,'run012-main-audit-record-v1')
write(OUT/'private/main_lease.json',lease)
artifacts=[]
for name in ['settings_verification.json','request.json','preflight.json','dry_run.json','preview_result.json']:
    artifacts.append(hub.artifact(task['task_id'],identity['agent_id'],OUT/name,{'run_id':'run_012','method':'official AbqJobPilot 0.2.2 API; dry_run=True','configuration_source':settings_record['preview_parameter_source'],'science':'NOT_EVALUATED'},version='run012-v1'))
hub.finish(lease,result,evidence_state='RECORDED',science_state='NOT_EVALUATED')
message=hub.message(task['task_id'],identity['agent_id'],'MAIN',{'run_id':'run_012','task_id':task['task_id'],'execution_status':'COMPLETED','check_status':result['status'],'preflight':preflight['status'],'dry_run':dry['status'],'settings':settings_record['status'],'single_solver_authorization_request_ready':settings_ok},'run012-preview-result-v1')
receipts=[m for m in hub.poll_messages(identity) if m['task_id']==task['task_id']]
assert receipts and hub.verify_chain()
write(OUT/'agenthub_receipt.json',{'identity':identity,'task_id':task['task_id'],'task_status':'COMPLETED','artifact_ids':[a['artifact_id'] for a in artifacts],'artifact_hashes':{Path(a['path']).name:a['sha256'] for a in artifacts},'outbox_message_id':message['message_id'],'inbox_receipts':receipts,'audit_hash_chain_valid':True,'check_status':result['status']})
run={'schema_version':'1.0','run_id':'run_012','stage':'Saved Settings and execution-chain preview','objective':'Resolve run_010 preflight/dry-run prerequisites without enqueue or solver','status':result['status'],'start_time':started,'end_time':now(),'python_interpreter':sys.executable,'git_head':initial['head'],'git_branch':initial['branch'],'inputs':[{'path':'agenthub_sp_invopt/abqjobpilot_project/project.json','role':'Project identity'},{'path':inp.relative_to(ROOT).as_posix(),'sha256':expected_hash,'role':'candidate input'}],'outputs':[{'path':'run/run_012/artifacts/'+n,'role':n.removesuffix('.json')} for n in ['settings_verification.json','preflight.json','dry_run.json','preview_result.json','agenthub_receipt.json']],'validation':[{'check':k,'status':v,'evidence':'run/run_012/artifacts/preview_result.json','scope':'API preview only'} for k,v in [('settings',result['settings_status']),('preflight','PASS'),('dry-run','PASS'),('empty unchanged queue','PASS'),('AgentHub evidence and message','PASS')]],'errors':[] if settings_ok else [{'code':'PROJECT_RUNTIME_SETTINGS_NOT_SAVED','severity':'BLOCKED','message':'Target Project runtime/settings.json does not exist. Explicit user parameters enabled API preview but cannot prove persisted configuration.','evidence':'run/run_012/artifacts/settings_verification.json','resolution':'UNRESOLVED'}],'task_id':task['task_id'],'solver_started':False,'datacheck_started':False,'queue_written':False,'settings_written':False,'commit_performed':False,'push_performed':False,'single_solver_authorization_request_ready':settings_ok}
write(RUN/'run.json',run)
print(json.dumps({'status':result['status'],'settings':result['settings_status'],'preflight':preflight['status'],'dry_run':dry['status'],'task_id':task['task_id'],'single_solver_authorization_request_ready':settings_ok},indent=2))
