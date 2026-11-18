"""Current official API and source-log audit; releases existing ODB task only."""
from common62 import *
import re,numpy,scipy,matplotlib
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.recovery_workflow import probe_solver_processes
from agenthub_sp_invopt.hub import Hub
sys.path.insert(0,str(R/'run/run_041/artifacts'));import queue_pilot as q
sys.path.insert(0,str(R/'run/run_056/artifacts'));from review_science import parse_trials
PID=q.PID;PROJECT=q.PROJECT;QID='q_392e020abc59422c9cb6a93f35b235d2'
EXPECTED='f944338d77fa7798d3546dd51075f149f886a4fd015b37fba28c58878311b906'
def phases(path):
 text=path.read_text(encoding='utf-8',errors='replace');out={}
 for phase in ['DATACHECK_RUNNING','FULL_RUNNING']:
  starts=re.findall(r'\[([^]]+)\] START '+phase,text);ends=re.findall(r'\[([^]]+)\] END '+phase+r' return_code=(-?\d+)',text)
  out[phase]={'start_records':starts,'end_records':ends,'one_successful_phase':len(starts)==len(ends)==1 and ends[0][1]=='0','duration_s':(datetime.fromisoformat(ends[0][0])-datetime.fromisoformat(starts[0])).total_seconds() if len(starts)==len(ends)==1 else None}
 return out
def main():
 assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
 start={'at':now(),'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')},'python':sys.executable,'versions':{'numpy':numpy.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__}}
 save(RUN/'checkpoints/start.json',start)
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_062','stage':'run061 Phase2 I06 numerical resolution qualification','objective':'true execution audit, real ODB Agent extraction, MAIN review and frozen adjacent-refinement/R comparison; no new FE','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'parent_execution_run':'run_061','inputs':[],'outputs':[],'validation':[],'errors':[]})
 frozen=read(R/'run/run_060/artifacts/prepared_batch.json');point=frozen['points'][0];contract=read(R/frozen['comparison_contract_path']);ids=read(R/'run/run_061/artifacts/private/task_ids.json');receipt=read(R/'run/run_061/artifacts/private/queue_receipt.json')
 protected={}
 for num in ['055','056','057','058','059','060','061']:
  for x in [R/f'run/run_{num}/run.json',R/f'run/run_{num}/summary.md']:protected[rel(x)]=sha(x)
 for num in ['060','061']:
  for x in read(R/f'run/run_{num}/run.json')['outputs']:
   assert sha(R/x['path'])==x['sha256'];protected[x['path']]=x['sha256']
  for x in read(R/f'run/run_{num}/artifacts/private/evidence_manifest.json')['files']:
   assert sha(R/x['path'])==x['sha256'];protected[x['path']]=x['sha256']
 for x in read(R/'run/run_060/artifacts/private/source_manifest.json')['sources']:
  assert sha(R/x['path'])==x['sha256'];protected[x['path']]=x['sha256']
 assert receipt['queue_id']==QID and receipt['inp_sha256']==point['inp_sha256']==EXPECTED
 assert sha(R/point['inp_path'])==EXPECTED
 raw=(R/point['inp_path']).read_bytes();src=(R/point['source_inp']).read_bytes();audit=read(R/'run/run_060/artifacts/private/input_byte_audit.json')
 recovered=raw.replace(audit['new_static_data'].encode(),audit['old_static_data'].encode(),1)
 for v in audit['comment_replacements']:recovered=recovered.replace(v['new'].encode(),v['old'].encode(),1)
 assert recovered==src and sha(R/point['source_inp'])==point['source_inp_sha256']
 gitbase=read(R/'run/run_061/checkpoints/start.json');assert gitbase['git']['staged']==start['git']['staged'] and sha(R/'.gitignore')==gitbase['gitignore_sha256']
 for f in gitbase['local_CAE']:assert sha(R/f['path'])==f['sha256'];protected[f['path']]=f['sha256']
 save(P/'protected_sources_before.json',protected)
 api=AbqJobPilotClient();scope=api.for_project(project_id=PID);env=q.environment(api);queue=scope.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
 runtime=q.runtime_guard(deep=True);process=probe_solver_processes();assert process['state']=='CLEAR'
 before={rel(x):sha(x) for x in [PROJECT/'runtime/queue.json',PROJECT/'runtime/settings.json',PROJECT/'project.db']}
 matches=[j for j in queue['jobs'] if j['queue_id']==QID];assert len(matches)==1;j=matches[0];job=point['job_name'];work=R/point['working_dir']
 assert j['job_name']==job and Path(j['inp_path']).resolve()==(R/point['inp_path']).resolve() and Path(j['work_dir']).resolve()==work.resolve()
 assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True)
 same=[v for v in queue['jobs'] if v['job_name']==job];assert len(same)==1
 hm=[v for v in history['jobs'] if v['job_name']==job];assert len(hm)==1
 detail=api.show_job(hm[0]['job_id'],project_id=PID).to_dict();attempts=detail['runs'];single=len(attempts)==1 and attempts[0]['queue_id']==QID and attempts[0]['attempt_no']==1
 phase=phases(work/f'{job}.log') if (work/f'{job}.log').exists() else {}
 files={ext:{'path':rel(work/f'{job}.{ext}'),'exists':(work/f'{job}.{ext}').is_file(),'bytes':(work/f'{job}.{ext}').stat().st_size if (work/f'{job}.{ext}').is_file() else None,'sha256':sha(work/f'{job}.{ext}') if (work/f'{job}.{ext}').is_file() else None} for ext in ['odb','sta','msg','dat','log']}
 completed=j['raw_status'] in ['COMPLETED_OK','COMPLETED_WITH_WARNINGS'] and j.get('return_code')==0 and j.get('final_verdict')=='SUCCESS'
 staok=files['sta']['exists'] and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in (work/f'{job}.sta').read_text(errors='replace')
 safe=bool(completed and single and phase and all(v['one_successful_phase'] for v in phase.values()) and staok and all(v['exists'] and v['bytes']>0 for v in files.values()) and not (work/f'{job}.lck').exists())
 ev=parse_trials(files) if staok else None
 record={**point,'queue_id':QID,'queue_record':j,'history_detail':detail,'public_status':scope.status(job_id=QID).to_dict(),'public_outputs':scope.locate_outputs(job_id=QID).to_dict(),'software_completed':completed,'software_status':j['raw_status'],'single_attempt_confirmed':single,'started_attempt_count':len([r for r in attempts if r.get('started_at')]),'phase_evidence':phase,'actual_runtime_s':j.get('duration_sec'),'sta_completion_verified':staok,'files':files,'safe_for_readonly_odb':safe,'numerical_quality':'PENDING','scientific_scoreability':'PENDING','output_run':'run_062'}
 batch=[v for v in queue['jobs'] if v.get('batch_name')=='run061_one_I06_resolution'];assert [v['queue_id'] for v in batch]==[QID]
 after={p:sha(R/p) for p in before};assert before==after
 actual={'version':'run062-I06-execution-audit-v1','at':now(),'project_id':PID,'environment':env,'queue':queue,'history':history,'runtime':runtime,'solver_process':process,'record':record,'no_extra_batch_jobs':True,'protected_before':before,'protected_after':after,'no_queue_or_solver_operation':True}
 save(P/'execution_audit.json',actual)
 if ev:save(P/'main_raw_numeric_events.json',ev)
 assert safe,'Existing solve unsafe/incomplete: preserve audit and stop, no retry'
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run061-I06-queue');tid=ids['execution_audit_task_id'];assert hub.task(tid)['execution_state']=='PENDING'
 lease=hub.claim(tid,actor,'run062-real-execution-audit-v1');save(P/'audit_lease.json',lease)
 hub.artifact(tid,actor['agent_id'],P/'execution_audit.json',{'run':'run_062','parent':'run_061','scope':'read-only real execution audit'},version='run062-v1')
 hub.finish(lease,{'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'software_completed':True,'safe_read_count':1,'consumed_attempts':record['started_attempt_count'],'output_run':'run_062'},science_state='NOT_EVALUATED')
 dispatch={'version':'run062-existing-ODB-task-output-overlay-v1','output_run':'run_062','parent_execution_run':'run_061','project_id':PID,'task_id':ids['odb_task_id'],'audit_path':rel(P/'execution_audit.json'),'audit_sha256':sha(P/'execution_audit.json'),'point':record,'baseline':frozen['baseline'],'comparison_contract_path':frozen['comparison_contract_path'],'comparison_contract_sha256':frozen['comparison_contract_sha256'],'actual_output_root':'run/run_062/artifacts/private/odb/I06_REFINED','requirements':['Real ODB Codex session claims existing task; source readOnly=True with Abaqus2024 Python, no Solver/datacheck/retry','Verify actual Punch RP and Step; u=-U2,F=-RF2,units m/N,no2pi; native raw U2/RF2/time,FD,241 alignment,Field/History consistency','max PEEQ across all saved frames/IP, per-frame maxima and actual displacement/frame/inc/time; ALLPD/available energies','STA/MSG warnings mapped accepted/rejected attempts, cutback, native force steps, final equilibrium markers','contact node23 and topological neighbours CPRESS/COPEN with all accepted saved frames1.10-1.16mm; sentinel COPEN>=1e30 missing','Also audit global/local native force jump peaks, and .68-.70,.85-.88,.97-.99mm; relation to contact is association not unique cause','Need corresponding old I06 contact and common-stage PEEQ: read baseline ODB safely if needed, output new baseline supplementary extraction in run062 only; never edit old outputs','same-stage comparisons .3/.6/.9/1.2mm: save scalar-max interpolation brackets and nearest actual frames per frozen protocol; no comparing equal frame numbers across jobs','structured result.json,diagnostics.json,raw_history.csv,force_displacement.csv,peeq_saved_frames.csv,ODB extraction/provenance/hash; material pmax.9','Preserve frozen comparison implementation, no smoothing/zero shift/extrapolation; MAIN computes scientific comparison independently','write only new run062 artifacts plus formalHub; no historical/index/status edit/no tensile/no predictors/no retrain'],'history_rule':'existing run061 task payload immutable; dispatch supplies permitted output_run overlay'}
 save(A/'odb_dispatch.json',dispatch);save(P/'task_ids.json',{'identity':actor,'parent_run061_task_ids':ids,'execution_audit_task_id':tid,'odb_task_id':ids['odb_task_id'],'science_task_id':ids['science_task_id']})
 hub.message(ids['odb_task_id'],actor['agent_id'],'ODB',{'output_run':'run_062','dispatch_path':rel(A/'odb_dispatch.json'),'dispatch_sha256':sha(A/'odb_dispatch.json'),'user_completion_confirmed':True,'output_root':dispatch['actual_output_root']},'run062-ODB-dispatch-v1');assert hub.verify_chain()
 print(json.dumps({'software_status':j['raw_status'],'safe_read':safe,'single_attempt':single,'phases':phase,'runtime_s':record['actual_runtime_s'],'cutbacks':ev['cutback_count'],'rejected_attempts':ev['rejected_attempts'],'warnings':ev['warning_counts'],'odb_task_id':ids['odb_task_id'],'audit_sha256':sha(P/'execution_audit.json')}))
if __name__=='__main__':main()
