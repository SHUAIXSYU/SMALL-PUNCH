"""Current public API execution audit; reuse existing run058 future tasks, no enqueue."""
from common import *
import re,zipfile,numpy as np,scipy,matplotlib
sys.path[:0]=[str(R),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import probe_solver_processes
from agenthub_sp_invopt.hub import Hub
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';PROJECT=R/'agenthub_sp_invopt/abqjobpilot_project'

def phases(path):
 text=path.read_text(encoding='utf-8',errors='replace');out={}
 for phase in ['DATACHECK_RUNNING','FULL_RUNNING']:
  starts=re.findall(r'\[([^]]+)\] START '+phase,text);ends=re.findall(r'\[([^]]+)\] END '+phase+r' return_code=(-?\d+)',text)
  seconds=(datetime.fromisoformat(ends[0][0])-datetime.fromisoformat(starts[0])).total_seconds() if len(starts)==len(ends)==1 else None
  out[phase]={'start_records':starts,'end_records':ends,'one_successful_phase':len(starts)==len(ends)==1 and ends[0][1]=='0','duration_s':seconds}
 return out

def main():
 start={'at':now(),'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')},'python':sys.executable,'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__}}
 assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
 save(RUN/'checkpoints/start.json',start)
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_059','stage':'run058 Phase2 prospective identification evaluation','objective':'actual audit, real ODB session extraction, independent MAIN review and frozen A/B; no new FE','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[],'parent_execution_run':'run_058'})
 fpath=R/'run/run_057/artifacts/prepared_batch.json';frozen=read(fpath);qmanifest=read(R/'run/run_058/artifacts/private/queue_manifest.json');ids=read(R/'run/run_058/artifacts/private/task_ids.json')
 assert sha(fpath)==qmanifest['prepared_batch_sha256']=='9017ada8c03afff78b0e0c89e0ba51c35a9ec0b21c27a4b3a90506c7ac310705'
 assert sha(R/frozen['comparison_contract_path'])==frozen['comparison_contract_sha256']
 assert sha(R/frozen['protocol_path'])==frozen['protocol_sha256']
 protected={}
 for r in ['055','056','057','058']:
  for p in [R/f'run/run_{r}/run.json',R/f'run/run_{r}/summary.md']:
   protected[rel(p)]=sha(p)
 for entry in read(R/'run/run_057/artifacts/private/evidence_manifest.json')['files']:
  assert sha(R/entry['path'])==entry['sha256'];protected[entry['path']]=entry['sha256']
 for entry in read(R/'run/run_058/artifacts/private/evidence_manifest.json')['files']:
  assert sha(R/entry['path'])==entry['sha256'];protected[entry['path']]=entry['sha256']
 bundle=R/'run/run_057/artifacts/private/frozen_predictor';pm=read(bundle/'package_manifest.json')
 package=R/frozen['predictor_package_path'];assert sha(package)==frozen['predictor_package_sha256']
 with zipfile.ZipFile(package) as z:
  assert z.testzip() is None
  for item in pm['files']:assert sha(bundle/item['path'])==item['sha256'] and hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
 model=read(bundle/'frozen_FE_only_inverse_models.json');train=read(bundle/'training_25.json');metadata=read(bundle/'predictor_contract.json')
 assert train['sample_ids']==model['training_ids'] and len(set(train['sample_ids']))==25
 assert sha(bundle/'training_25.json')==metadata['training_data_sha256'] and sha(bundle/'frozen_FE_only_inverse_models.json')==metadata['original_models_sha256']
 save(P/'predictor_integrity_before_new_response.json',{'verified_at':now(),'status':'PASS','phase':'before any new FE response enters prediction','package_sha256':sha(package),'model_sha256':sha(bundle/'frozen_FE_only_inverse_models.json'),'training25_sha256':sha(bundle/'training_25.json'),'training_ids':train['sample_ids'],'metadata_sha256':sha(bundle/'predictor_contract.json'),'protocol_sha256':frozen['comparison_contract_sha256'],'no_retraining':True})
 gitbase=read(R/'run/run_057/checkpoints/start.json');assert start['git']['staged']==gitbase['staged'] and sha(R/'.gitignore')==gitbase['gitignore_sha256']
 for m in gitbase['local_CAE']:assert sha(R/m['path'])==m['sha256'];protected[m['path']]=m['sha256']
 save(P/'protected_sources_before.json',protected)
 api=AbqJobPilotClient();scope=api.for_project(project_id=PID)
 project=api.show_project(project_id=PID).to_dict();settings=api.get_project_settings(project_id=PID).to_dict();queue=scope.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
 assert project['status']=='OK' and project['project']['project_id']==PID and queue['status']==history['status']=='OK'
 runtime=assess_runtime(PROJECT/'runtime',project_db=PROJECT/'project.db');process=probe_solver_processes()
 assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT' and not runtime['running_queue_ids'] and process['state']=='CLEAR'
 before={rel(p):sha(p) for p in [PROJECT/'runtime/queue.json',PROJECT/'runtime/settings.json',PROJECT/'project.db']}
 records=[]
 for point,receipt in zip(frozen['points'],qmanifest['points']):
  qid=receipt['queue_id'];job=point['job_name'];inp=R/point['inp_path'];work=R/point['working_dir']
  matches=[j for j in queue['jobs'] if j['queue_id']==qid];assert len(matches)==1;j=matches[0]
  assert sha(inp)==point['inp_sha256']==receipt['inp_sha256']
  assert j['job_name']==job and Path(j['inp_path']).resolve()==inp.resolve() and Path(j['work_dir']).resolve()==work.resolve()
  assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True)
  hm=[v for v in history['jobs'] if v['job_name']==job];detail=api.show_job(hm[0]['job_id'],project_id=PID).to_dict() if len(hm)==1 else None
  attempts=detail['runs'] if detail else [];single=len(attempts)==1 and attempts[0]['queue_id']==qid and attempts[0]['attempt_no']==1
  phase=phases(work/f'{job}.log') if (work/f'{job}.log').is_file() else {}
  completed=j['raw_status'] in ['COMPLETED_OK','COMPLETED_WITH_WARNINGS'] and j.get('return_code')==0 and j.get('final_verdict')=='SUCCESS'
  files={ext:{'path':rel(work/f'{job}.{ext}'),'exists':(work/f'{job}.{ext}').is_file(),'bytes':(work/f'{job}.{ext}').stat().st_size if (work/f'{job}.{ext}').is_file() else None,'sha256':sha(work/f'{job}.{ext}') if (work/f'{job}.{ext}').is_file() else None} for ext in ['odb','sta','msg','dat','log']}
  sta_success=files['sta']['exists'] and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in (work/f'{job}.sta').read_text(errors='replace')
  safe=bool(completed and single and phase and all(v['one_successful_phase'] for v in phase.values()) and sta_success and all(v['exists'] and v['bytes']>0 for v in files.values()) and not (work/f'{job}.lck').exists())
  records.append({**point,'queue_id':qid,'queue_record':j,'history_detail':detail,'public_status':scope.status(job_id=qid).to_dict(),'public_outputs':scope.locate_outputs(job_id=qid).to_dict(),'software_completed':completed,'software_phase':j['raw_status'],'single_attempt_confirmed':single,'started_attempt_count':len([r for r in attempts if r.get('started_at')]),'phase_evidence':phase,'actual_runtime_s':j.get('duration_sec'),'sta_completion_verified':sta_success,'files':files,'safe_for_readonly_odb':safe,'numerical_quality':'PENDING','scientific_scoreability':'PENDING','output_run':'run_059'})
 after={p:sha(R/p) for p in before};assert before==after
 batchjobs=[j for j in queue['jobs'] if j.get('batch_name')=='run058_four_prospective_identification'];assert sorted(j['queue_id'] for j in batchjobs)==sorted(r['queue_id'] for r in records)
 audit={'version':'run059-real-prospective-execution-audit-v1','at':now(),'project_id':PID,'project':project,'settings':settings,'queue':queue,'history':history,'runtime':runtime,'solver_process':process,'records':records,'software_completed':sum(r['software_completed'] for r in records),'safe_read_count':sum(r['safe_for_readonly_odb'] for r in records),'consumed_started_attempts':sum(r['started_attempt_count'] for r in records),'extra_batch_jobs':0,'protected_before':before,'protected_after':after,'no_new_execution_or_queue_mutation':True}
 save(P/'execution_audit.json',audit)
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run058-prospective-queue');tid=ids['execution_audit_task_id'];assert hub.task(tid)['execution_state']=='PENDING'
 lease=hub.claim(tid,actor,'run059-real-execution-audit-v1');save(P/'audit_lease.json',lease)
 hub.artifact(tid,actor['agent_id'],P/'execution_audit.json',{'run':'run_059','parent_run':'run_058','read_only_existing_results':True},version='run059-v1')
 hub.finish(lease,{'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'software_completed':audit['software_completed'],'safe_read_count':audit['safe_read_count'],'consumed_attempts':audit['consumed_started_attempts'],'output_run':'run_059','no_new_execution':True},science_state='NOT_EVALUATED')
 dispatch={'version':'run059-existing-four-ODB-tasks-output-overlay-v1','output_run':'run_059','project_id':PID,'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'task_ids':ids['odb_task_ids'],'points':records,'comparison_contract_path':frozen['comparison_contract_path'],'comparison_contract_sha256':frozen['comparison_contract_sha256'],'actual_output_root':'run/run_059/artifacts/private/odb','requirements':['real ODB Codex session must claim the four existing Hub tasks, finish and register evidence, no simulated worker','reuse verified Abaqus2024 Python extraction in readOnly=True; source INP/ODB hashes and RP Node ASM_SPT.1/Step must be checked','u=-U2,F=-RF2; no2pi/noabs/nozero shift/no smoothing/noextrapolation; full native history and Field/History comparison','raw_history.csv,force_displacement.csv, aligned241.csv, diagnostics.json, result.json, provenance and numerical warnings perpoint','max saved-frame PEEQ versus actual plastic table pmax.9; accepted/rejected warning mapping, cutback, local force recoil and contact events, available ALLPD energy','terminal/single-attempt/cost facts from MAIN audit; if failed or incomplete report null/UNSCOREABLE and preserve all remaining evidence','MAIN performs frozen inverse predictions later; ODB must not train or modify predictors; do not touch tensile data or sealed analyses','write only run059 artifacts (and formal Hub APIs), do not edit historical Runs/index/status or original models/results','no Solver/datacheck/enqueue/retry or new FE'], 'history_rule':'only output directory overlaid on old task payload; all immutable run058 task payloads/history retained'}
 save(A/'odb_dispatch.json',dispatch);save(P/'task_ids.json',{'identity':actor,'parent_run058_task_ids':ids,'execution_audit_task_id':tid,'odb_task_ids':ids['odb_task_ids'],'science_task_id':ids['science_task_id']})
 for cid,task in ids['odb_task_ids'].items():hub.message(task,actor['agent_id'],'ODB',{'output_run':'run_059','dispatch_path':rel(A/'odb_dispatch.json'),'dispatch_sha256':sha(A/'odb_dispatch.json'),'candidate_id':cid,'output_root':dispatch['actual_output_root']+'/'+cid,'user_completion_notification_received':True},f'run059-real-odb-dispatch-{cid}-v1')
 assert hub.verify_chain()
 print(json.dumps({'run':'run_059','software_completed':audit['software_completed'],'safe_read':audit['safe_read_count'],'consumed':audit['consumed_started_attempts'],'runtime_s':{r['candidate_id']:r['actual_runtime_s'] for r in records},'task_ids':ids['odb_task_ids']}))

if __name__=='__main__':main()
