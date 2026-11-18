"""MAIN independent byte/material review and public preview-only API checks."""
from pathlib import Path
from datetime import datetime
import sys,json,hashlib,csv,math
import numpy as np
from highp_envelope import plastic_block,Envelope
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_051';A=RUN/'artifacts';P=A/'private';sys.path[:0]=[str(R),r'D:\Projects\abqjobpilot']
from agenthub_sp_invopt.hub import Hub
from abqjobpilot.api import AbqJobPilotClient,JobRequest
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def rel(p):return p.relative_to(R).as_posix()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def main():
 contract=read(A/'material_contract.json');dispatch=read(P/'cae_task_identity.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3');task=hub.task(dispatch['task_id'])
 assert task['execution_state']=='COMPLETED' and task['lease_agent'].startswith('CAE:')
 save(P/'real_cae_result_received.json',{'received_at':datetime.now().astimezone().isoformat(),'task':task,'via':'formal Hub.task result; real SP-InvOpt CAE Codex session separately activated and completed'})
 source=R/contract['source_inp'];assert sha(source)==contract['source_inp_sha256'];base_raw=source.read_bytes();prefix,suffix,base,texts=plastic_block(base_raw)
 api=AbqJobPilotClient();cap=api.capabilities();pid='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';project=R/'agenthub_sp_invopt/abqjobpilot_project';scoped=api.for_project(project_id=pid)
 settings=api.get_project_settings(project_id=pid).to_dict();assert settings['status']=='PERSISTED' and settings['persisted'] and not settings['defaulted_fields'] and not settings['errors']
 assert settings['project_id']==pid and Path(settings['project_path']).resolve()==project.resolve() and read(project/'project.json')['project_id']==pid
 s=settings['settings'];assert s==settings['effective_settings']==read(project/'runtime/settings.json')
 expected={'abaqus_cmd':r'D:\ABAQUS2024\Commands\abq2024.bat','default_cpus':14,'default_gpus':0,'use_gpu':False,'run_datacheck':True,'run_full':True,'auto_shutdown_enabled':False}
 assert all(type(s[k]) is type(v) and s[k]==v for k,v in expected.items()) and Path(s['abaqus_cmd']).is_file()
 guard=[project/'project.json',project/'project.db',project/'runtime/settings.json',project/'runtime/queue.json',A/'material_contract.json',A/'comparison_contract.json',source]
 before={rel(p):sha(p) for p in guard};queue_before=scoped.list_jobs();assert queue_before['status']=='OK'
 results=[]
 for point in contract['points']:
  inp=R/point['intended_inp_path'];work=R/point['working_dir'];raw=inp.read_bytes();a,b,rows,lowtext=plastic_block(raw)
  assert a==prefix and b==suffix and raw==prefix+(R/point['plastic_rows_path']).read_bytes()+suffix
  for _,p in base:
   if p<=contract['p_switch']:assert lowtext[p]==texts[p]
  with (R/point['table_path']).open(encoding='utf-8-sig',newline='') as f:table=list(csv.DictReader(f))
  assert rows==[(float(v['yield_stress_pa']),float(v['equivalent_plastic_strain'])) for v in table]
  assert work.is_dir() and not any(work.iterdir()) and inp.stem==point['job_name']
  assert b'0.001, 1., 1e-12, 0.00125' in raw and b'\n*Include' not in raw and b'\n*INCLUDE' not in raw
  assert not any(j.get('job_name')==point['job_name'] for j in queue_before['jobs'])
  assert all(sha(R/point[k])==point[k.replace('_path','_sha256')] for k in ['table_path','plastic_rows_path'])
  request=JobRequest(inp_path=str(inp),job_name=point['job_name'],working_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='preview_only',allow_solver_submit=False,batch='SPIO_run051_highp_PREVIEW_ONLY',strategy='frozen_D01_high_strain_tangent_envelope',metadata={'run':'run_051','candidate_id':point['candidate_id'],'material_contract_sha256':sha(A/'material_contract.json'),'inp_sha256':sha(inp),'authorized_solver_jobs':0})
  pre=scoped.preflight(request).to_dict();dry=scoped.enqueue(request,dry_run=True).to_dict()
  assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
  assert all(not dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
  assert Path(pre['expected_odb_path']).resolve()==(R/point['expected_odb']).resolve()
  assert 'cpus=14' in pre['command_preview'] and 'gpus=' not in pre['command_preview']
  assert not any(work.iterdir())
  results.append({**point,'inp_path':rel(inp),'inp_absolute_path':str(inp.resolve()),'inp_sha256':sha(inp),'working_dir_absolute':str(work.resolve()),'all_nonplastic_bytes_identical':True,'original_low_rows_identical':True,'material_rows_equal_frozen_fragment':True,'request':request.to_dict(),'preflight':pre,'dry_run':dry,'solver_attempts':0,'queue_id':None})
 after={rel(p):sha(p) for p in guard};queue_after=scoped.list_jobs();assert before==after and queue_before==queue_after
 save(P/'main_preflight_dry_run.json',{'version':'run051-main-independent-preview-v1','at':datetime.now().astimezone().isoformat(),'capabilities':cap,'settings_response':settings,'source_runtime':'D:/Projects/abqjobpilot','points':results,'preflight_passed':2,'dry_run_passed':2,'guard_before':before,'guard_after':after,'queue_unchanged':True,'queue_before':queue_before,'queue_after':queue_after,'no_solver_datacheck_enqueued':True,'scope_limit':'public preview is not an Abaqus syntax/license/convergence or physical validation'})
 save(A/'prepared_batch.json',{'version':'run051-two-highp-envelopes-prepared-v1','frozen_at':datetime.now().astimezone().isoformat(),'status':'PREPARED_NO_SOLVER_OR_ENQUEUE_AUTHORIZATION','project_id':pid,'project_path':rel(project),'material_contract_path':rel(A/'material_contract.json'),'material_contract_sha256':sha(A/'material_contract.json'),'comparison_contract_path':rel(A/'comparison_contract.json'),'comparison_contract_sha256':sha(A/'comparison_contract.json'),'cae_task_id':dispatch['task_id'],'cae_agent_id':task['lease_agent'],'cae_session_id':task['lease_session'],'numeric_controls_unchanged_from_D01':True,'resources':{'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0},'order':[v['job_name'] for v in results],'points':[{k:v[k] for k in ['candidate_id','job_name','inp_path','inp_absolute_path','inp_sha256','working_dir','working_dir_absolute','expected_odb','post_transition_hardening_multiplier','table_rows','queue_id','solver_attempts']} for v in results]})
 print(json.dumps({'real_CAE_task':dispatch['task_id'],'agent':task['lease_agent'],'preflight':2,'dry_run':2,'queue_unchanged':True,'jobs':[{'job':v['job_name'],'sha256':v['inp_sha256']} for v in results]}))
if __name__=='__main__':main()
