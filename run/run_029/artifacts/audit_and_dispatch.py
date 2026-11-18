"""Audit terminal AbqJobPilot evidence, then assign one read-only ODB task."""
import hashlib,json,re,subprocess,sys,time,traceback
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_029';A=R/'artifacts';P=A/'private'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot'];sys.dont_write_bytecode=True
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.process_identity import verify_launch_evidence
from agenthub_sp_invopt.hub import Hub
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RT=PROJECT/'runtime'
ENQ=ROOT/'run/run_028/artifacts/enqueue_result.json';PREP=ROOT/'run/run_027/artifacts/prepared_candidate.json';CONTRACT=ROOT/'run/run_027/artifacts/comparison_contract.json'
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 if not p.is_file():return None
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 assert not p.exists(),f'Existing audit record: {p}'
 with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
def rel(p):return p.relative_to(ROOT).as_posix()
def proc():
 cmd='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress'
 raw=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],encoding='utf8',errors='replace'))
 ps=raw if isinstance(raw,list) else [raw]
 conflicts=[p for p in ps if re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',p.get('Name') or '',re.I) or ((p.get('Name') or '').lower() in ('python.exe','pythonw.exe','cmd.exe') and 'spio_r027_ctr_m0025' in (p.get('CommandLine') or '').lower())]
 return {'at':now(),'conflicts':conflicts}
def main():
 assert not (P/'execution_audit.json').exists() and not (A/'task_ids.json').exists()
 enq=read(ENQ);f=read(PREP);c=read(CONTRACT)
 assert enq['queue_id']=='q_6919f51c551844b4bcda1cc22b9a6bc4' and enq['project_id']==f['project_id']==PID
 assert enq['job_name']==f['job_name']=='SPIO_R027_CTR_M0025'
 assert enq['inp_sha256']==f['candidate_sha256']==sha(Path(f['candidate_inp_absolute']))
 assert enq['working_dir']==f['working_dir_absolute'] and sha(CONTRACT)==f['comparison_contract_sha256']
 assert sha(ROOT/c['comparison_implementation_path'])==c['comparison_implementation_sha256']
 api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
 info=api.show_project(project_id=PID).to_dict();settings=api.get_project_settings(project_id=PID).to_dict()
 assert info['status']=='OK' and info['project']['project_id']==PID and Path(scoped.runtime_dir).resolve()==RT
 assert settings['status']=='PERSISTED' and settings['project_id']==PID
 q=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
 assert q['status']==history['status']=='OK'
 matches=[j for j in q['jobs'] if j['queue_id']==enq['queue_id']];assert len(matches)==1;j=matches[0]
 assert j['job_name']==f['job_name'] and Path(j['inp_path']).resolve()==Path(f['candidate_inp_absolute']).resolve()
 assert Path(j['work_dir']).resolve()==Path(f['working_dir_absolute']).resolve()
 assert j['cpus']==14 and j['gpus']==0 and j['run_datacheck'] and j['run_full'] and f['candidate_sha256'] in j['notes']
 assert j['status']=='COMPLETED' and j['raw_status'] in ('COMPLETED_OK','COMPLETED_WITH_WARNINGS') and j['return_code']==0 and j['final_verdict']=='SUCCESS'
 assert j['started_at'] and j['ended_at'] and j['duration_sec'] is not None
 assert not any(x['job_name']=='SPIO_R023_V02_NP' for x in q['jobs'])
 hs=[x for x in history['jobs'] if x['job_name']==f['job_name']];assert len(hs)==1 and hs[0]['run_count']==1
 detail=api.show_job(hs[0]['job_id'],project_id=PID).to_dict();status=scoped.status(job_id=j['queue_id']).to_dict();out=scoped.locate_outputs(job_id=j['queue_id']).to_dict()
 assert status['status']=='COMPLETED' and out['odb_exists']
 runtime=assess_runtime(RT,project_db=PROJECT/'project.db')
 assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT' and runtime['live_phase']=='IDLE' and not runtime['lock_files']
 work=Path(f['working_dir_absolute']);files={}
 for ext in ('odb','sta','msg','dat','log'):
  p=work/(f['job_name']+'.'+ext);assert p.is_file() and p.stat().st_size>0
  files[ext]={'path':rel(p),'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
 log=(ROOT/files['log']['path']).read_text(errors='replace');phases={}
 for phase in ('DATACHECK_RUNNING','FULL_RUNNING'):
  starts=list(re.finditer(r'\[([^]]+)\] START '+phase,log));ends=list(re.finditer(r'\[([^]]+)\] END '+phase+r' return_code=(-?\d+)',log))
  assert len(starts)==len(ends)==1 and int(ends[0][2])==0
  phases[phase]={'start_local':starts[0][1],'end_local':ends[0][1],'return_code':0,'duration_sec':(datetime.fromisoformat(ends[0][1])-datetime.fromisoformat(starts[0][1])).total_seconds(),'time_note':'Raw Runner log strings have no timezone; local clock preserved'}
 sta=(ROOT/files['sta']['path']).read_text(errors='replace')
 assert 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in sta
 assert not (work/(f['job_name']+'.lck')).exists()
 evpath=RT/j['process_evidence_path'];ev=read(evpath);observations={k:verify_launch_evidence(v['process_identity']) for k,v in ev['phases'].items()}
 snap1=proc();time.sleep(1);snap2=proc();assert not snap1['conflicts'] and not snap2['conflicts']
 for x in files.values():assert sha(ROOT/x['path'])==x['sha256'] and (ROOT/x['path']).stat().st_mtime_ns==x['mtime_ns']
 evidence={'at':now(),'run':'run_029','queue_id':j['queue_id'],'job_name':j['job_name'],'inp_sha256':f['candidate_sha256'],'queue_record':j,'api_status':status,'api_outputs':out,'project':info,'settings':settings,'history_detail':detail,'files':files,'phases':phases,'duration_sec':j['duration_sec'],'runtime':runtime,'process_evidence':ev,'current_process_identity':observations,'independent_process_snapshots':[snap1,snap2],'sta_completed_successfully':True,'stable_hashes':True,'safe_for_odb_read':True,'V02_not_queued':True,'scientific_qualification':'PENDING_ODB_AND_FROZEN_COMPARISON'}
 save(P/'execution_audit.json',evidence)
 hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600);identity=hub.register('MAIN','codex-main-run029-refinement-result')
 main_task=hub.create_task(identity['agent_id'],'MAIN','qualify_center_adjacent_increment',{'run':'run_029','queue_id':j['queue_id'],'source_enqueue_task_id':enq['task_id'],'contract_sha256':sha(CONTRACT),'scope':'Read-only result analysis; no new job, V02, retry, hidden tensile'},'run029-main-qualification-v1',depends=(enq['task_id'],))['task_id']
 lease=hub.claim(main_task,identity,'run029-main-claim-v1')
 payload={'run':'run_029','main_task_id':main_task,'queue_id':j['queue_id'],'job_name':f['job_name'],'inp_absolute':f['candidate_inp_absolute'],'inp_sha256':f['candidate_sha256'],'working_dir_absolute':f['working_dir_absolute'],'odb_absolute':str(ROOT/files['odb']['path']),'odb_sha256':files['odb']['sha256'],'audit_path':rel(P/'execution_audit.json'),'output_directory':rel(P/'odb'),'project_id':PID,'requirements':['Use Abaqus 2024 bundled Python, open ODB readOnly=True only after verifying identity and stable source hash','Punch RP U2/RF2 and Step Time raw accepted-frame CSV; positive F-D u=-U2 m, F=-RF2 N; no smoothing or shift','Maximum PEEQ across saved frames and material-table 0.9 coverage; energy outputs if present','Count STA/MSG accepted increments, rejected attempts/cutbacks, negative eigenvalue, distortion, large strain and contact warnings; distinguish rejected trial from accepted states','Extract existing CPRESS/COPEN in 1.10-1.16 mm accepted frames, node23 and topology-derived neighbors, contact-pressure onset, raw force jumps and time/increment mapping; COPEN abs>=1e30 is missing sentinel','Source hashes before/after; JSON/CSV/plot and provenance; register Hub artifacts and send MAIN structured completion','Do not score or alter frozen Loss, do not read sealed tensile, enqueue, start Solver/datacheck, retry, alter source ODB/INP or historical Run files'],'comparison_contract_path':'run/run_027/artifacts/comparison_contract.json','baseline_V01_fd':'run/run_025/artifacts/private/odb/force_displacement.csv','baseline_run014_fd':'run/run_014/artifacts/odb/punch_force_displacement.csv'}
 odb_task=hub.create_task(identity['agent_id'],'ODB','extract_center_adjacent_increment_result',payload,'run029-odb-extract-v1')['task_id']
 hub.message(odb_task,identity['agent_id'],'ODB',payload,'run029-odb-dispatch-v1')
 hub.artifact(main_task,identity['agent_id'],P/'execution_audit.json',{'run':'run_029','method':'AbqJobPilot public API + read-only output provenance'},version='run029-v1')
 save(P/'main_session.json',{'identity':identity,'lease':lease,'main_task_id':main_task,'odb_task_id':odb_task})
 save(A/'task_ids.json',{'main_task_id':main_task,'odb_task_id':odb_task,'queue_id':j['queue_id']})
 assert hub.verify_chain()
 print(json.dumps({'status':'AUDITED_AND_DISPATCHED','main_task_id':main_task,'odb_task_id':odb_task,'queue_id':j['queue_id'],'duration_sec':j['duration_sec'],'phase_durations':phases,'odb_sha256':files['odb']['sha256']}))
if __name__=='__main__':
 try:main()
 except Exception:
  P.mkdir(parents=True,exist_ok=True)
  (P/('audit_failure_'+datetime.now().strftime('%H%M%S%f')+'.txt')).write_text(traceback.format_exc(),encoding='utf8')
  raise
