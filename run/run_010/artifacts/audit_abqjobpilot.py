"""Read-only stable API/config audit; fail closed when persisted settings are absent."""
import datetime, hashlib, inspect, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'run/run_010/artifacts'
ABQ = Path(r'D:\Projects\abqjobpilot')
PROJECT = ROOT / 'agenthub_sp_invopt/abqjobpilot_project'
sys.path.insert(0, str(ABQ))
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot import config, settings_store
def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def record(path):
    return {'path':str(path),'exists':path.is_file(),'sha256':sha(path),'values':json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None}
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
client = AbqJobPilotClient(recent_file=str(ROOT/'agenthub_sp_invopt/abqjobpilot_recent_projects.json'))
tracked = [PROJECT/'project.json',PROJECT/'project.db',PROJECT/'runtime/queue.json', PROJECT/'runtime/live_status.json',Path.home()/'.abqjobpilot/recent_projects.json']
before = {str(p):sha(p) for p in tracked}
project_result = client.show_project(project=str(PROJECT)).to_dict()
caps = client.capabilities()
scoped = client.for_project(project=str(PROJECT))
settings = {'project':record(PROJECT/'runtime/settings.json'), 'selected_global':record(Path(config.SETTINGS_FILE)), 'legacy_installation':record(ABQ/'runtime/settings.json')}
all_home_settings = [record(p) for p in (Path.home()/'.abqjobpilot').rglob('settings.json')]
fields = ['abaqus_cmd','default_cpus','use_gpu','default_gpus','run_datacheck','run_full']
raw = settings['project']['values']
missing = fields if not isinstance(raw,dict) else [f for f in fields if f not in raw]
inp = ROOT/'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp'
expected = 'fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a'
identity_ok = (project_result.get('project',{}).get('project_id') == 'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae' and sha(inp)==expected)
blockers = []
if caps['application_version']!='0.2.2': blockers.append('STABLE_VERSION_MISMATCH')
if not identity_ok: blockers.append('PROJECT_OR_INP_IDENTITY_MISMATCH')
if missing: blockers.append('PERSISTED_PROJECT_SETTINGS_MISSING:'+','.join(missing))
# v0.2.2 preview uses config.ABAQUS_CMD, not persisted Project settings.
if isinstance(raw,dict) and raw.get('abaqus_cmd') != config.ABAQUS_CMD:
    blockers.append('PUBLIC_PREVIEW_COMMAND_DIFFERS_FROM_PROJECT_SETTINGS')
preflight = dry_run = {'status':'BLOCKED','executed':False,'blockers':blockers}
request_record = None
if not blockers:
    if not Path(raw['abaqus_cmd']).is_file():
        raise RuntimeError('Configured Abaqus command does not exist')
    if type(raw['default_cpus']) is not int or raw['default_cpus']<=0 or type(raw['default_gpus']) is not int or raw['default_gpus']<0 or any(type(raw[k]) is not bool for k in ['use_gpu','run_datacheck','run_full']):
        raise RuntimeError('Persisted Settings types/ranges are invalid')
    request=JobRequest(inp_path=str(inp),job_name=inp.stem,working_dir=str(inp.parent),cpus=raw['default_cpus'],gpus=raw['default_gpus'] if raw['use_gpu'] else 0,run_datacheck=raw['run_datacheck'],run_full=raw['run_full'],submission_mode='preview_only',allow_solver_submit=False)
    request_record=request.to_dict()
    preflight={'executed':True,**scoped.preflight(request).to_dict()}
    dry_run={'executed':True,**scoped.enqueue(request,dry_run=True).to_dict()}
private = {'observed_at':now(),'settings_sources':settings,'home_settings_inventory':all_home_settings,'read_only_project_loader_signature':str(inspect.signature(settings_store.load_settings_for_runtime)),'code_fallbacks_observed_only':settings_store.DEFAULT_SETTINGS,'preview_api_source':{'preflight':str(inspect.signature(client.preflight)),'dry_run':str(inspect.signature(client.enqueue)),'note':'Preview _abaqus_cmd_prefix_preview uses config.ABAQUS_CMD; it does not read Project Settings. Command preview always displays DATACHECK and FULL_RUN templates; run flags are not proof of execution.'},'before':before,'after':{str(p):sha(p) for p in tracked}}
write(OUT/'private/abq_settings_sources.json',private)
result={'observed_at':now(),'status':'BLOCKED' if blockers else 'PASS','source_version':caps['application_version'],'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ABQ,text=True).strip(),'source_status':subprocess.check_output(['git','status','--short'],cwd=ABQ,text=True).strip(),'capabilities':caps,'project':project_result,'queue':scoped.list_jobs(),'history':scoped.list_jobs(project=str(PROJECT)).to_dict(),'locate_outputs':scoped.locate_outputs(inp_path=str(inp)).to_dict(),'inp_identity_verified':identity_ok,'inp_sha256':sha(inp),'settings':{'status':'BLOCKED' if missing else 'VERIFIED','project_file_exists':settings['project']['exists'],'global_file_exists':settings['selected_global']['exists'],'legacy_file_exists':settings['legacy_installation']['exists'],'missing_fields':missing,'verified_values':{k:raw[k] for k in fields if isinstance(raw,dict) and k in raw}},'preflight':preflight,'dry_run':dry_run,'request':request_record,'protected_files_unchanged':private['before']==private['after'],'queue_sha256':sha(PROJECT/'runtime/queue.json'),'solver_started':False,'datacheck_started':False,'queue_written':False,'evidence':'run/run_010/artifacts/private/abq_settings_sources.json'}
write(OUT/'abqjobpilot_verification.json',result)
print(json.dumps({k:result[k] for k in ['status','source_version','inp_identity_verified','settings','preflight','dry_run','protected_files_unchanged']},ensure_ascii=False,indent=2))
