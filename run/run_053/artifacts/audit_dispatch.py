"""Read-only execution audit; reuse the two existing Hub ODB tasks with a new-Run output overlay."""
import sys,json,csv,re,hashlib,subprocess
from pathlib import Path
from datetime import datetime
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_053';A=RUN/'artifacts';P=A/'private';sys.path[:0]=[str(R),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import probe_solver_processes
from agenthub_sp_invopt.hub import Hub
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';PROJECT=R/'agenthub_sp_invopt/abqjobpilot_project'
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rel(p):return p.relative_to(R).as_posix()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
def phase_facts(path):
 text=path.read_text(encoding='utf-8',errors='replace');out={}
 for phase in ['DATACHECK_RUNNING','FULL_RUNNING']:
  starts=re.findall(r'\[([^]]+)\] START '+phase,text);ends=re.findall(r'\[([^]]+)\] END '+phase+r' return_code=(-?\d+)',text)
  duration=(datetime.fromisoformat(ends[0][0])-datetime.fromisoformat(starts[0])).total_seconds() if len(starts)==len(ends)==1 else None
  out[phase]={'start_records':starts,'end_records':ends,'one_successful_phase':len(starts)==len(ends)==1 and ends[0][1]=='0','duration_s_from_local_log':duration}
 return out
def main():
 assert not (RUN/'run.json').exists()
 start={'at':now(),'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short')},'python':sys.executable}
 save(RUN/'checkpoints/start.json',start)
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_053','stage':'Post-solve hardening envelope sensitivity analysis','objective':'actual audit, real ODB extraction, independent frozen Loss and response/spatial/energy comparison; no new FE','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
 frozen_path=R/'run/run_051/artifacts/prepared_batch.json';frozen=read(frozen_path);queue_manifest=read(R/'run/run_052/artifacts/private/queue_manifest.json');oldids=read(R/'run/run_052/artifacts/private/task_ids.json')
 assert sha(frozen_path)==queue_manifest['prepared_batch_sha256'];assert frozen['project_id']==PID and frozen['order']==['SPIO_R051_H01_LOW','SPIO_R051_H02_HIGH']
 cc=read(R/frozen['comparison_contract_path']);assert sha(R/frozen['comparison_contract_path'])==frozen['comparison_contract_sha256']
 for k in ['target','config','implementation']:assert sha(R/cc['loss_binding'][k+'_path'])==cc['loss_binding'][k+'_sha256']
 assert sha(R/cc['comparison_implementation_path'])==cc['comparison_implementation_sha256']
 baseline_result=read(R/cc['baseline_result_path']);assert sha(R/cc['baseline_job'])==cc['baseline_odb_sha256']==baseline_result['odb_sha256'] and sha(R/cc['baseline_fd_path'])==cc['baseline_fd_sha256']
 ref_params=read(R/'run/run_046/artifacts/private/freeze/D01_parameters.json');assert cc['baseline_SPT_loss']==ref_params['SPT_loss']==.0005020002745645833
 guards={p:sha(R/p) for p in ['run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip','run/run_047/artifacts/private/independent_validation_report.md','run/run_048/artifacts/private/independent_reassessment_report.md','run/run_050/artifacts/private/scientific_report.md','run/run_051/artifacts/prepared_batch.json','run/run_051/artifacts/material_contract.json','run/run_051/artifacts/comparison_contract.json']};save(P/'protected_before.json',guards)
 api=AbqJobPilotClient();scoped=api.for_project(project_id=PID);project=api.show_project(project_id=PID).to_dict();settings=api.get_project_settings(project_id=PID).to_dict();assert project['status']=='OK' and project['project']['project_id']==PID
 queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict();assert queue['status']==history['status']=='OK'
 runtime=assess_runtime(PROJECT/'runtime',project_db=PROJECT/'project.db');process=probe_solver_processes();assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT' and not runtime['running_queue_ids'] and process['state']=='CLEAR'
 before={p:sha(PROJECT/p) for p in ['runtime/queue.json','runtime/settings.json','project.db']}
 records=[]
 for p,receipt in zip(frozen['points'],queue_manifest['points']):
  cid=p['candidate_id'];name=p['job_name'];qid=receipt['queue_id'];matches=[j for j in queue['jobs'] if j['queue_id']==qid];assert len(matches)==1;j=matches[0]
  assert qid=={'H01':'q_02e7827a5c2d41aba1781ec0f36e78a4','H02':'q_5a027a0d764148c08f4d7be36049439f'}[cid]
  inp=R/p['inp_path'];work=R/p['working_dir'];assert sha(inp)==p['inp_sha256']==receipt['inp_sha256'] and j['job_name']==name and Path(j['inp_path']).resolve()==inp.resolve() and Path(j['work_dir']).resolve()==work.resolve()
  assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True)
  hh=[v for v in history['jobs'] if v['job_name']==name];detail=api.show_job(hh[0]['job_id'],project_id=PID).to_dict() if len(hh)==1 else None
  attempts=detail['runs'] if detail else [];single=len(attempts)==1 and attempts[0]['queue_id']==qid and attempts[0]['attempt_no']==1
  phase=phase_facts(work/f'{name}.log') if (work/f'{name}.log').is_file() else {}
  successful=j['raw_status'] in ['COMPLETED_OK','COMPLETED_WITH_WARNINGS'] and j['return_code']==0 and j['final_verdict']=='SUCCESS'
  files={ext:{'path':rel(work/f'{name}.{ext}'),'exists':(work/f'{name}.{ext}').is_file(),'bytes':(work/f'{name}.{ext}').stat().st_size if (work/f'{name}.{ext}').is_file() else None,'sha256':sha(work/f'{name}.{ext}') if (work/f'{name}.{ext}').is_file() else None} for ext in ['odb','sta','msg','dat','log']}
  sta_complete=files['sta']['exists'] and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in (work/f'{name}.sta').read_text(encoding='utf-8',errors='replace')
  safe=bool(successful and single and phase and all(v['one_successful_phase'] for v in phase.values()) and sta_complete and all(v['exists'] and v['bytes']>0 for v in files.values()) and not (work/f'{name}.lck').exists())
  pe=j.get('process_evidence_path');process_candidates=[PROJECT/pe,PROJECT/'runtime'/pe] if pe else [];pepaths=[x for x in process_candidates if x.is_file()]
  evidence={'path':rel(pepaths[0]),'sha256':sha(pepaths[0]),'data':read(pepaths[0])} if len(pepaths)==1 else {'status':'PATH_UNRESOLVED','raw_path':pe}
  records.append({**p,'queue_id':qid,'queue_record':j,'history_detail':detail,'public_status':scoped.status(job_id=qid).to_dict(),'public_outputs':scoped.locate_outputs(job_id=qid).to_dict(),'software_completed':successful,'software_phase':j['raw_status'],'started_attempt_count':len([r for r in attempts if r.get('started_at')]),'single_attempt_confirmed':single,'actual_runtime_s':j.get('duration_sec'),'phase_evidence':phase,'sta_successful_completion':sta_complete,'files':files,'process_evidence':evidence,'safe_for_readonly_odb':safe,'numerical_state':'PENDING_ODB_REVIEW','scientific_score_state':'PENDING_MAIN_REVIEW','output_run':'run_053'})
 after={p:sha(PROJECT/p) for p in before};assert before==after
 batch=[j for j in queue['jobs'] if j.get('batch_name')=='run052_two_authorized_hardening_scenarios'];assert sorted(j['queue_id'] for j in batch)==sorted(r['queue_id'] for r in records),'Unexpected job in authorized batch'
 audit={'version':'run053-real-two-job-execution-audit-v1','at':now(),'project_id':PID,'project':project,'settings':settings,'queue':queue,'history':history,'runtime':runtime,'process_probe':process,'frozen_manifest_sha256':sha(frozen_path),'baseline_D01_identity_verified':True,'records':records,'software_completed_count':sum(v['software_completed'] for v in records),'safe_read_count':sum(v['safe_for_readonly_odb'] for v in records),'consumed_started_attempts':sum(v['started_attempt_count'] for v in records),'batch_actual_job_count':len(batch),'extra_batch_jobs':0,'protected_before':before,'protected_after':after,'no_new_execution_or_enqueue':True}
 save(P/'execution_audit.json',audit)
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run052-hardening-queue')
 audit_task=oldids['execution_audit_task_id'];assert hub.task(audit_task)['execution_state']=='PENDING';lease=hub.claim(audit_task,actor,'run053-actual-audit-claim-v1');save(P/'audit_lease.json',lease)
 hub.artifact(audit_task,actor['agent_id'],P/'execution_audit.json',{'output_run':'run_053','scope':'actual two existing attempts; not a new solve'},version='run053-v1');hub.finish(lease,{'output_run':'run_053','audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'software_completed':audit['software_completed_count'],'safe_read':audit['safe_read_count'],'consumed':audit['consumed_started_attempts'],'no_new_attempts':True},evidence_state='RECORDED',science_state='NOT_EVALUATED')
 dispatch={'version':'run053-existing-ODB-tasks-output-overlay-v1','output_run':'run_053','project_id':PID,'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'task_ids':oldids['odb_task_ids'],'points':records,'baseline_result_path':cc['baseline_result_path'],'comparison_contract_path':frozen['comparison_contract_path'],'comparison_contract_sha256':frozen['comparison_contract_sha256'],'material_contract_path':frozen['material_contract_path'],'material_contract_sha256':frozen['material_contract_sha256'],'actual_output_root':'run/run_053/artifacts/private/odb','history_rule':'supersedes only the preplanned run052 output_root with current legal run053; no old run files/payloads are modified','requirements':['claim both existing task IDs using real ODB session; no new fake worker','read-only Abaqus2024 Python, verify source hashes and safe lock/process status','reuse proven run045 extraction/diagnostic logic and run050 CAX4 spatial/energy methods, output in run053 only','RP ASM_SPT node1 must be verified; u=-U2,F=-RF2; full history/field validation','diagnose accepted/rejected attempts separately, PEEQ/table.9, force recoil/contact jumps; no smoothing/delete/fit','four stages .3/.6/.9/1.2mm nearest accepted frame,2376 CAX4 IP,reference/current 2pi*r*detJ volumes','both plastic-work definitions exactly asrun050: final-PEEQ-region cumulative and interval-after-threshold split fromS.Mises/PEEQ atall savedframes, directALLPD crosscheck, noRF2-share claim','score status preliminary only; if failed/incomplete markLossnull, do not score partial history','provide structured result.json perH01/H02 plus spatial_energy_result.json and actual source/provenance hashes','do not edit original/old runs, globalindex/MAIN reports,inputs or infrastructure; no Solver/datacheck/enqueue/retry/tensile reading']}
 save(A/'odb_dispatch.json',dispatch);save(P/'task_ids.json',{'identity':actor,'prior_run052_task_ids':oldids,'execution_audit_task_id':audit_task,'odb_task_ids':oldids['odb_task_ids'],'science_task_id':oldids['science_task_id']})
 for cid,tid in oldids['odb_task_ids'].items():
  hub.message(tid,actor['agent_id'],'ODB',{'output_run':'run_053','dispatch_path':rel(A/'odb_dispatch.json'),'dispatch_sha256':sha(A/'odb_dispatch.json'),'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'candidate_id':cid,'output_root':dispatch['actual_output_root']+'/'+cid,'old_run052_output_location_superseded_only':True,'current_user_completion_authorization':True},f'run053-real-odb-dispatch-{cid}-v1')
 print(json.dumps({'run':'run_053','software_completed':audit['software_completed_count'],'safe_odb':audit['safe_read_count'],'attempts_consumed':audit['consumed_started_attempts'],'runtimes_s':{r['candidate_id']:r['actual_runtime_s'] for r in records},'ODB_tasks':oldids['odb_task_ids']}))
if __name__=='__main__':main()
