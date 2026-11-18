"""Read-only V01 execution audit, actual ODB handoff. No enqueue or solver API."""
import sys,json,hashlib,subprocess,re,time,importlib.util
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_025';A=R/'artifacts';P=A/'private'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.process_identity import verify_launch_evidence
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    if not p.is_file():return None
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
def now():return datetime.now().astimezone().isoformat()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
baseline={k:git(*v) for k,v in {'head':['rev-parse','HEAD'],'branch':['branch','--show-current'],'remote':['remote','-v'],'status':['status','--short']}.items()}
save(R/'checkpoints/start.json',dict(at=now(),git=baseline))
meta=dict(schema_version='1.0',run_id='run_025',stage='V01 actual result qualification',objective='Audit V01, real ODB extraction, frozen numerical gate; V02 only if qualified',status='RUNNING',start_time=now(),end_time=None,python_interpreter=sys.executable,git_head=baseline['head'],git_branch=baseline['branch'],inputs=[dict(path='run/run_024/artifacts/enqueue_result.json',role='Unique authorized V01 queue identity')],outputs=[],validation=[],errors=[])
save(R/'run.json',meta);(R/'summary.md').write_text('# run_025 — V01 qualification\n\nRUNNING：只读执行审计、真实ODB提取及冻结数值门槛判定。\n',encoding='utf8')
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RT=PROJECT/'runtime'
batchfile=ROOT/'run/run_023/artifacts/prepared_batch.json';assert sha(batchfile)=='626b7afbb37894d6d7ca384d2a3b02e01c3b0083a2878918e492527804dc4435'
b=read(batchfile);point=b['points'][0];ident=b['comparison_contract'];assert sha(ROOT/ident['path'])==ident['sha256'] and sha(ROOT/ident['implementation'])==ident['implementation_sha256']
auth=read(ROOT/'run/run_024/artifacts/enqueue_result.json');assert point['job_name']==auth['job_name'] and sha(ROOT/point['inp_path'])==point['sha256']==auth['inp_sha256']
api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
protected={str(p):sha(p) for p in [PROJECT/'project.json',PROJECT/'project.db',RT/'queue.json',RT/'settings.json',RT/'live_status.json',batchfile,ROOT/ident['path'],ROOT/ident['implementation']]}
info=api.show_project(project_id=PID).to_dict();assert info['project']['project_id']==PID and Path(scoped.runtime_dir).resolve()==RT
settings=api.get_project_settings(project_id=PID).to_dict();assert settings['status']=='PERSISTED'
queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict();assert queue['status']==history['status']=='OK'
js=[j for j in queue['jobs'] if j['queue_id']==auth['queue_id']];assert len(js)==1;j=js[0]
assert j['job_name']==point['job_name'] and Path(j['inp_path']).resolve()==ROOT/point['inp_path'] and Path(j['work_dir']).resolve()==ROOT/point['working_dir']
assert j['cpus']==14 and j['gpus']==0 and j['run_datacheck'] and j['run_full'] and point['sha256'] in j['notes']
assert not [q for q in queue['jobs'] if q['job_name']==b['points'][1]['job_name']],'V02 unexpectedly already submitted'
hs=[x for x in history['jobs'] if x['job_name']==point['job_name']];assert len(hs)==1 and hs[0]['run_count']==1
detail=api.show_job(hs[0]['job_id'],project_id=PID).to_dict();status=scoped.status(job_id=j['queue_id']).to_dict();outputs=scoped.locate_outputs(job_id=j['queue_id']).to_dict()
runtime=assess_runtime(RT,project_db=PROJECT/'project.db');assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT' and runtime['live_phase']=='IDLE' and not runtime['lock_files']
files={}
for ext in ('odb','sta','msg','dat','log'):
    path=ROOT/point['expected_outputs'][ext];assert path.is_file()
    files[ext]=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),size=path.stat().st_size,mtime_ns=path.stat().st_mtime_ns)
log=(ROOT/files['log']['path']).read_text(errors='replace');phases={}
for ph in ('DATACHECK_RUNNING','FULL_RUNNING'):
    starts=list(re.finditer(r'\[([^]]+)\] START '+ph,log));ends=list(re.finditer(r'\[([^]]+)\] END '+ph+r' return_code=(-?\d+)',log))
    assert len(starts)==len(ends)==1 and int(ends[0][2])==0
    phases[ph]=dict(start_local=starts[0][1],end_local=ends[0][1],return_code=0,duration_sec=(datetime.fromisoformat(ends[0][1])-datetime.fromisoformat(starts[0][1])).total_seconds(),time_note='Raw Runner log has no timezone; local clock strings preserved')
sta_complete='THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in (ROOT/files['sta']['path']).read_text(errors='replace')
assert sta_complete and status['status']=='COMPLETED' and j['return_code']==0 and j['final_verdict']=='SUCCESS'
evidence=read(RT/j['process_evidence_path']);observations={k:verify_launch_evidence(v['process_identity']) for k,v in evidence['phases'].items()}
def process_snapshot():
    command='Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    ps=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],encoding='utf8',errors='replace'))
    conflicts=[p for p in ps if re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$',p['Name'],re.I) or (p['Name'].lower() in ('python.exe','pythonw.exe','cmd.exe') and point['job_name'].lower() in (p.get('CommandLine') or '').lower())]
    return dict(at=now(),conflicts=conflicts)
first=process_snapshot();time.sleep(1);second=process_snapshot();assert not first['conflicts'] and not second['conflicts']
for f in files.values():assert sha(ROOT/f['path'])==f['sha256'] and (ROOT/f['path']).stat().st_mtime_ns==f['mtime_ns']
assert not (ROOT/point['working_dir']/(point['job_name']+'.lck')).exists()
assert protected=={p:sha(Path(p)) for p in protected}
audit=dict(at=now(),point=point,queue_id=j['queue_id'],execution=j['raw_status'],queue_record=j,api_status=status,api_outputs=outputs,project=info,settings=settings,queue=queue,history_detail=detail,files=files,phases=phases,duration_sec=j.get('duration_sec'),runtime=runtime,process_evidence=evidence,current_process_identity=observations,independent_process_snapshots=[first,second],stable_hashes=True,safe_for_odb_read=True,safety_scope='Current no active solver/target process, no lock, stable hashes, CLEAN idle Runner; historical transient process identity gaps retained if present',protected=protected)
save(P/'execution_audit.json',audit)
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600);i=h.register('MAIN','codex-main-run025-v01-qualification')
main=h.create_task(i['agent_id'],'MAIN','qualify_V01_numerical_result',dict(run='run_025',queue_id=j['queue_id'],budget_task_id=auth['budget_task_id'],scope='Existing V01 audit and frozen gate; no retry/new Solver; V02 only if PASS'),'run025-main-v1')['task_id'];lease=h.claim(main,i,'run025-main-claim-v1')
payload=dict(run='run_025',main_task_id=main,queue_id=j['queue_id'],point=point,audit='run/run_025/artifacts/private/execution_audit.json',output_directory='run/run_025/artifacts/private/odb',scope='ReadOnly Abaqus 2024 ODB extraction for actual completed V01 only. No solver/datacheck/queue/retry/hidden tensile or mixed historical reports. Only write assigned odb subtree; no main reports/status edits.',requirements=['Verify actual ODB Job/Step/Punch RP and full material elastic/plastic table identity vs frozen INP','Abaqus Python readOnly=True, source hashes before/after, current read safety','Raw Punch RP U2/RF2/Step Time CSV and positive m/N FD u=-U2,F=-RF2; no abs/2pi/smoothing/shift','Max PEEQ all saved frames and table .9 coverage; energy diagnostics as available','STA/MSG/DAT warnings accepted/rejected mapping, cutback intervals, iterations, negative eigenvalues/distortion/large strain, timing','Compare event distribution/local force jumps with run014 center using run023 descriptive methodology if feasible; leave formal frozen Loss/qualification to MAIN','Write structured result.json, diagnostics, source manifest, FD plot, register artifacts through Hub and send MAIN completion message'],comparison_contract='run/run_023/artifacts/private/comparison_contract.json',baseline_audit='run/run_023/artifacts/private/odb_audit/event_audit.json')
odb=h.create_task(i['agent_id'],'ODB','extract_V01_numerical_validation',payload,'run025-odb-v1')['task_id'];h.message(odb,i['agent_id'],'ODB',payload,'run025-odb-dispatch-v1')
h.artifact(main,i['agent_id'],P/'execution_audit.json',{'run':'run_025','method':'Readonly public API + exact outputs/logs'},version='run025-v1')
save(P/'main_session.json',dict(identity=i,lease=lease,main_task=main,odb_task=odb));save(A/'task_ids.json',dict(main_task=main,odb_task=odb,budget_task=auth['budget_task_id']))
print(json.dumps(dict(main_task=main,odb_task=odb,execution=j['raw_status'],phases=phases,duration=j.get('duration_sec'),process_identity_states={k:v['state'] for k,v in observations.items()},safe_for_odb_read=True)))
