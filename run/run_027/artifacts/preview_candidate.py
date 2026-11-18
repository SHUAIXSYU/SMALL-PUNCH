"""Independent one-candidate byte audit and AbqJobPilot 0.2.2 preview-only API calls."""
import hashlib,importlib.util,json,re,sys,traceback
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_027/artifacts';P=A/'private'
sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state
from abqjobpilot.recovery_assessment import assess_runtime
def now():return datetime.now().astimezone().isoformat()
def sha(p):
 if not p.is_file():return None
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj):
 with p.open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
def main():
 assert not (A/'preview_result.json').exists()
 job='SPIO_R027_CTR_M0025';source=ROOT/'run/run_023/artifacts/candidates/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.inp';candidate=A/'candidates'/job/(job+'.inp');work=A/'solver'/job
 expected_source='14006d69c15e6fd4be021b889964e5add51e724d52fd03ff817b0f80b747c2ff'
 task=read(A/'cae_task.json');contract=read(A/'comparison_contract.json')
 assert task['job_name']==job and Path(task['candidate_inp']).resolve()==candidate.resolve() and Path(task['working_dir']).resolve()==work.resolve()
 assert contract['version']=='run027-adjacent-refinement-v1' and contract['new_solver_authorization'] is False and contract['enqueue_authorization'] is False
 assert sha(source)==expected_source and candidate.is_file() and candidate.stem==job and work.is_dir() and not any(work.iterdir())
 old=b'0.001, 1., 1e-12, 0.005\n';new=b'0.001, 1., 1e-12, 0.0025\n';raw=source.read_bytes();created=candidate.read_bytes()
 assert raw.count(old)==1 and created.count(new)==1 and created==raw.replace(old,new,1)
 assert created.replace(new,old,1)==raw
 lines=created.decode('utf8').splitlines();static=[i for i,line in enumerate(lines) if line.strip().lower()=='*static']
 assert len(static)==1 and lines[static[0]+1].strip()==new.decode().strip()
 assert lines.count('*Step, name=Step_Punch_Displacement, nlgeom=YES, inc=999999')==1
 assert not any(re.search(r'(?i)^\*(include|import|user material)\b|^\*restart\s*,\s*read',line.strip()) for line in lines)
 candidate_hash=sha(candidate);byte_audit={'source_inp':str(source),'source_sha256':sha(source),'candidate_inp':str(candidate),'candidate_sha256':candidate_hash,'old_static_line':old.decode().strip(),'new_static_line':new.decode().strip(),'only_one_static_data_line_changed':True,'source_recovered_from_candidate':True,'nonstatic_bytes_sha256':hashlib.sha256(raw.replace(old,b'',1)).hexdigest(),'source_size_bytes':len(raw),'candidate_size_bytes':len(created),'workdir_empty':True,'relative_include_or_external_model_reference':False}
 save(P/'independent_byte_audit.json',byte_audit)
 spec=importlib.util.spec_from_file_location('abq_settings_reader',ROOT/'run/run_017/artifacts/preview_batch.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 api,settings=mod.inspect_settings();project=mod.PROJECT;runtime=project/'runtime';pid=mod.PID
 assert pid=='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
 protected=[project/'project.json',project/'project.db',runtime/'settings.json',runtime/'queue.json',runtime/'live_status.json',Path.home()/'.abqjobpilot/recent_projects.json',Path.home()/'.abqjobpilot/app_settings.json']
 before={str(p):sha(p) for p in protected}
 queue=api.list_jobs();history=api.list_project_jobs(project_id=pid).to_dict();owner=runner_ownership_state(runtime);recovery=assess_runtime(runtime,project_db=project/'project.db')
 assert queue['status']=='OK' and history['status']=='OK'
 assert not any(j.get('job_name')==job or Path(j.get('inp_path') or '').resolve()==candidate.resolve() for j in queue['jobs']+history['jobs'])
 req=JobRequest(inp_path=str(candidate),job_name=job,working_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='preview_only',allow_solver_submit=False,batch='SPIO_run027_single_center_PREVIEW',strategy='max_increment_adjacent_refinement',metadata={'run':'run_027','cae_task_id':task['task_id'],'project_id':pid,'inp_sha256':candidate_hash,'authorized_enqueue_jobs':0,'authorized_solver_jobs':0,'automatic_retries':0,'no_v02_authorization_transfer':True})
 pre=api.preflight(req).to_dict();dry=api.enqueue(req,dry_run=True).to_dict()
 assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors']
 assert dry['job_id'] is None and not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'))
 assert Path(pre['expected_odb_path']).resolve()==(work/(job+'.odb')).resolve()
 assert sha(candidate)==candidate_hash and work.is_dir() and not any(work.iterdir())
 after={str(p):sha(p) for p in protected};queue_after=api.list_jobs();history_after=api.list_project_jobs(project_id=pid).to_dict()
 assert before==after and queue==queue_after and history==history_after
 save(P/'abq_preview_evidence.json',{'at':now(),'project_id':pid,'settings':settings,'candidate_sha256':candidate_hash,'queue_before':queue,'queue_after':queue_after,'history_before':history,'history_after':history_after,'runner_owner':owner,'recovery_assessment':recovery,'request':req.to_dict(),'preflight':pre,'dry_run':dry,'protected_before':before,'protected_after':after,'protected_unchanged':True,'no_queue_write':True,'no_solver_or_datacheck_start':True})
 result={'at':now(),'status':'PASS_PREVIEW_ONLY','job_name':job,'project_id':pid,'candidate_inp':str(candidate),'candidate_sha256':candidate_hash,'source_sha256':expected_source,'working_dir':str(work),'comparison_contract_sha256':sha(A/'comparison_contract.json'),'settings':'PERSISTED','preflight':pre['status'],'dry_run':dry['status'],'queue_unchanged':True,'queue_id':None,'solver_started':False,'datacheck_started':False,'authorized_enqueue_jobs':0,'authorized_solver_jobs':0,'runner_owner':owner['state'],'recovery_status':recovery['status'],'limitations':['Preview does not run Abaqus syntax/license/convergence checks','Prior run025 frozen BLOCKED status remains','Future queue/solver needs new single-job authorization and fresh state checks']}
 save(A/'preview_result.json',result)
 print(json.dumps({'status':result['status'],'sha256':candidate_hash,'preflight':result['preflight'],'dry_run':result['dry_run'],'queue_unchanged':True}))
if __name__=='__main__':
 try:main()
 except Exception:
  (P/('preview_failure_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.txt')).write_text(traceback.format_exc(),encoding='utf8')
  raise
