"""Register a validated existing Project through the official stable public API."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_011'
ABQ=Path(r'D:\Projects\abqjobpilot')
sys.path.insert(0,str(ABQ))
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.project.manager import default_recent_file, default_projects_root
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
creation=json.loads((ROOT/'run/run_008/artifacts/abqjobpilot_project.json').read_text(encoding='utf-8'))
project=Path(creation['project']['project']['path'])
pid='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
manifest=json.loads((project/'project.json').read_text(encoding='utf-8'))
assert manifest['project_id']==pid
recent=default_recent_file()
assert recent==Path(r'C:\Users\wuxia\.abqjobpilot\recent_projects.json'), 'Unverified user registry; refuse registration'
client=AbqJobPilotClient()
assert client.capabilities()['application_version']=='0.2.2'
assert Path(client.projects.manager.recent_file)==recent
protected=[project/'project.json',project/'runtime/queue.json',project/'runtime/settings.json',project/'runtime/live_status.json',project/'project.db',Path.home()/'.abqjobpilot/app_settings.json',ROOT/'agenthub_sp_invopt/abqjobpilot_recent_projects.json']
from abqjobpilot import config
protected.append(Path(config.SETTINGS_FILE))
before={str(p):sha(p) for p in protected}
started=now()
write(RUN/'checkpoints/initial_state.json',{'observed_at':started,'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short'),'python':sys.executable,'python_version':sys.version,'protected_hashes':before})
write(RUN/'artifacts/private/recent_before.json',json.loads(recent.read_text(encoding='utf-8')))
check=client.show_project(project=str(project)).to_dict()
assert check['status']=='OK' and check['project']['project_id']==pid
scoped=client.for_project(project=str(project))
queue=scoped.list_jobs()
assert queue['status']=='OK'
listing_before=client.list_projects().to_dict()
matches=[r for r in listing_before['projects'] if r['project_id']==pid]
if matches:
    assert len(matches)==1 and Path(matches[0]['path']).resolve()==project.resolve()
    registered={'status':'ALREADY_REGISTERED','project':check['project']}
else:
    registered=client.register_project(str(project)).to_dict()
    assert registered['status']=='PROJECT_REGISTERED',registered
listing_after=client.list_projects().to_dict()
matches=[r for r in listing_after['projects'] if r['project_id']==pid]
assert len(matches)==1 and matches[0]['exists'] and Path(matches[0]['path']).resolve()==project.resolve()
after={str(p):sha(p) for p in protected}
assert before==after,'Unexpected protected file change'
old=json.loads((RUN/'artifacts/private/recent_before.json').read_text(encoding='utf-8'))['recent_projects']
new=json.loads(recent.read_text(encoding='utf-8'))['recent_projects']
assert all(entry in new for entry in old),'Unexpected loss/change of existing recent entries'
result={'observed_at':now(),'status':'PASS','scope':'Existing Project registration and public API listing; GUI dropdown not visually refreshed','project_name':manifest['name'],'project_id':pid,'project_root':str(project),'registry':str(recent),'default_projects_root':str(default_projects_root()),'app_settings_exists':(Path.home()/'.abqjobpilot/app_settings.json').exists(),'cause':'run_008 used repository-local recent_file override; GUI uses per-user recent_projects.json','gui_environment':{'owner':'BOLTZMANN\\wuxia','entrypoint':str(ABQ/'run_gui.py'),'window_title':'Agent Command Console','window_process_id':28532,'parent_process_id':19976,'launcher_interpreter':r'D:\Projects\abqjobpilot_archived\0.1.0\.venv\Scripts\pythonw.exe','same_user_and_application_source':True,'note':'Different Python interpreter from Codex, but same application entrypoint and Path.home-based registry; parent/child form one GUI launch.'},'validation_before':check,'queue_valid':True,'queue_count':len(queue['jobs']),'register_result':registered,'matching_recent_entries':matches,'prior_recent_entries_preserved':True,'protected_files_unchanged':before==after,'queue_sha256':sha(project/'runtime/queue.json'),'solver_started':False,'queue_written':False,'settings_written':False}
write(RUN/'artifacts/registration_result.json',result)
write(RUN/'artifacts/private/api_lists.json',{'before':listing_before,'after':listing_after})
write(RUN/'run.json',{'schema_version':'1.0','run_id':'run_011','stage':'Project GUI registration repair','objective':'Register the existing run_008 SP-InvOpt Project in the verified GUI user registry','status':'PASS','start_time':started,'end_time':now(),'python_interpreter':sys.executable,'git_head':git('rev-parse','HEAD'),'git_branch':git('branch','--show-current'),'inputs':[{'path':'run/run_008/artifacts/abqjobpilot_project.json','role':'creation identity'},{'path':'agenthub_sp_invopt/abqjobpilot_project/project.json','role':'validated existing Project'}],'outputs':[{'path':'run/run_011/artifacts/registration_result.json','role':'registration and API listing evidence'},{'path':'run/run_011/summary.md','role':'summary'}],'validation':[{'check':'Project ID, queue validity, official registration and public API re-list','status':'PASS','evidence':'run/run_011/artifacts/registration_result.json','scope':'existing Project registration only; no visual GUI refresh confirmation'}],'errors':[],'solver_started':False,'queue_written':False,'settings_written':False,'duplicate_project_created':False,'commit_performed':False,'push_performed':False})
print(json.dumps({k:result[k] for k in ['status','project_name','project_id','project_root','registry','register_result','protected_files_unchanged']},ensure_ascii=False,indent=2))
