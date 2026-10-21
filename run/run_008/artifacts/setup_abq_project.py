"""Create one isolated formal AbqJobPilot Project using its public Python API."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ABQ=Path(r'D:\Projects\abqjobpilot')
sys.path.insert(0,str(ABQ))
from abqjobpilot.api import AbqJobPilotClient
NAME='SP-InvOpt run_008 candidate preview'
PROJECT=ROOT/'agenthub_sp_invopt'/'abqjobpilot_project'
RECENT=ROOT/'agenthub_sp_invopt'/'abqjobpilot_recent_projects.json'
if PROJECT.exists(): raise SystemExit('REFUSE_EXISTING_PROJECT_PATH')
client=AbqJobPilotClient(recent_file=str(RECENT))
caps=client.capabilities()
created=client.create_project(NAME,path=str(PROJECT),description='Independent SP-InvOpt Project for run_008 preview and evidence. No Solver or Queue execution authorized.')
if created.errors: raise SystemExit(json.dumps(created.to_dict(),indent=2))
project=client.for_project(project=str(PROJECT))
listing=client.list_jobs(project=str(PROJECT))
payload={'source_root':str(ABQ),'source_version':caps['application_version'],'capabilities':caps['capabilities'],'project':created.to_dict(),'project_path':str(PROJECT.relative_to(ROOT)).replace('\\','/'),'project_id':created.data.get('project',{}).get('project_id'),'queue_status':listing.to_dict() if hasattr(listing,'to_dict') else listing,'settings':{'global_settings_file_exists':False,'project_settings_file_exists':(PROJECT/'runtime'/'settings.json').is_file(),'effective_resource_and_run_settings':'UNKNOWN; v0.2.2 would fall back to code defaults, which are not used'}}
out=ROOT/'run'/'run_008'/'artifacts'/'abqjobpilot_project.json'
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(payload,ensure_ascii=False,indent=2))
