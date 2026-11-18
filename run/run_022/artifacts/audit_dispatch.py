"""Read-only execution audit and formal ODB handoff; no execution functions."""
import sys,json,hashlib,subprocess,time
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'run/run_022';OUT=RUN/'artifacts';PRIV=OUT/'private'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.runtime_coordination import runner_ownership_state
from abqjobpilot.process_identity import verify_launch_evidence
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def now():return datetime.now().astimezone().isoformat()
def save(p,v):
    assert not p.exists(),p
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(p)
PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RT=PROJECT/'runtime';PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
info=api.show_project(project_id=PID).to_dict();assert info['status']=='OK' and info['project']['project_id']==PID==read(PROJECT/'project.json')['project_id']
assert Path(scoped.runtime_dir).resolve()==RT
protected=[PROJECT/'project.json',PROJECT/'project.db',RT/'queue.json',RT/'settings.json',RT/'live_status.json',ROOT/'run/run_020/artifacts/prepared_batch.json',ROOT/'inverse/fd_loss.py']
before={str(p):sha(p) for p in protected}
queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict();assert queue['status']==history['status']=='OK'
owner=runner_ownership_state(RT);live=read(RT/'live_status.json')
batch=read(ROOT/'run/run_020/artifacts/prepared_batch.json');authorized=read(ROOT/'run/run_021/artifacts/enqueue_result.json')
records=[]
for point in batch['points']:
    inp=ROOT/point['inp_path'];work=ROOT/point['working_dir'];assert sha(inp)==point['inp_sha256']
    qs=[j for j in queue['jobs'] if j['job_name']==point['job_name']];hs=[j for j in history['jobs'] if j['job_name']==point['job_name']]
    rec=dict(point=point,input_sha256=sha(inp),queue_matches=qs,history_matches=hs,files={},execution='NOT_FOUND',safe_for_odb_read=False)
    for ext in ('odb','sta','msg','dat','log'):
        p=work/(point['job_name']+'.'+ext)
        rec['files'][ext]=dict(path=p.relative_to(ROOT).as_posix(),exists=p.is_file(),sha256=sha(p),size=p.stat().st_size if p.is_file() else None,mtime_ns=p.stat().st_mtime_ns if p.is_file() else None)
    if qs:
        assert len(qs)==1 and len(hs)<=1
        j=qs[0];assert Path(j['inp_path']).resolve()==inp and Path(j['work_dir']).resolve()==work
        assert j['queue_id']==next(z['queue_id'] for z in authorized['jobs'] if z['job_name']==point['job_name'])
        assert j['cpus']==14 and j['gpus']==0 and j['run_datacheck'] and j['run_full']
        rec['api_status']=scoped.status(job_id=j['queue_id']).to_dict();rec['api_outputs']=scoped.locate_outputs(job_id=j['queue_id']).to_dict()
        if hs:rec['history_detail']=api.show_job(hs[0]['job_id'],project_id=PID).to_dict()
        rec['execution']=j['raw_status'];rec['queue_id']=j['queue_id'];rec['duration_sec']=j.get('duration_sec')
        evidence_path=RT/j['process_evidence_path'] if j.get('process_evidence_path') else None
        observations={}
        if evidence_path and evidence_path.is_file():
            evidence=read(evidence_path);rec['process_evidence']=evidence
            observations={k:verify_launch_evidence(v['process_identity']) for k,v in evidence['phases'].items()}
        rec['current_phase_process_observations']=observations
        sta=(work/(point['job_name']+'.sta')).read_text(errors='replace') if rec['files']['sta']['exists'] else ''
        rec['sta_completed']='THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in sta;rec['lock_exists']=(work/(point['job_name']+'.lck')).exists()
        rec['safe_for_odb_read']=(j['status']=='COMPLETED' and j['return_code']==0 and j['final_verdict']=='SUCCESS' and rec['sta_completed'] and not rec['lock_exists'] and len(observations)==2 and all(v['state']=='CONFIRMED_EXITED' for v in observations.values()) and owner['state']=='ABSENT' and live['phase']=='IDLE')
    records.append(rec)
time.sleep(1)
for r in records:
    r['output_stable']=all(not f['exists'] or ((ROOT/f['path']).stat().st_size==f['size'] and (ROOT/f['path']).stat().st_mtime_ns==f['mtime_ns']) for f in r['files'].values());r['safe_for_odb_read'] &= r['output_stable']
assert before=={str(p):sha(p) for p in protected}
audit=dict(observed_at=now(),project=info,capabilities=api.capabilities(),queue=queue,history=history,runner_ownership=owner,live_status=live,records=records,protected_before=before)
save(PRIV/'execution_audit.json',audit)
run=dict(schema_version='1.0',run_id='run_022',stage='Completed local sensitivity analysis',objective='Audit four existing jobs, real ODB handoff, frozen Loss and local identifiability',status='RUNNING',start_time=now(),end_time=None,python_interpreter=sys.executable,git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),git_branch='main',inputs=[dict(path='run/run_020/artifacts/prepared_batch.json',role='Frozen four-point batch',sha256=sha(ROOT/'run/run_020/artifacts/prepared_batch.json'))],outputs=[],validation=[],errors=[])
save(RUN/'run.json',run);save(RUN/'checkpoints/run_initial.json',run)
(RUN/'summary.md').write_text('# run_022 — RUNNING\n\nExisting results only; no new Solver or queue action.\n',encoding='utf8')
hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600);identity=hub.register('MAIN','codex-main-run022-analysis')
main=hub.create_task(identity['agent_id'],'MAIN','analyze_existing_local_sensitivity',dict(run_id='run_022',scope='Only existing L01-L04 plus run014; frozen Loss; no Solver/queue/heldout access'),'run022-main-v1')
lease=hub.claim(main['task_id'],identity,'run022-main-claim-v1');save(PRIV/'main_lease.json',lease)
payload=dict(run_id='run_022',main_task_id=main['task_id'],audit_path='run/run_022/artifacts/private/execution_audit.json',output_directory='run/run_022/artifacts/private/odb',valid_point_ids=[r['point']['point_id'] for r in records if r['safe_for_odb_read']],protocol='run/run_020/artifacts/analysis_protocol.md',loss_identity='run/run_017/artifacts/loss_contract_identity.json',scope='Read-only Abaqus2024 Python ODB extraction and diagnostics; no solver/datacheck/queue/retry or hidden tensile access',acceptance=['Claim real ODB session through Hub; no simulated worker','Read only valid_point_ids; verify original INP/material vs ODB, stable output and exact Job identity','Punch RP U2/RF2 time-paired raw CSV and positive FD m/N: u=-U2,F=-RF2, no abs or 2pi','For every valid point export saved-frame maximum PEEQ and actual material coverage, convergence/cutbacks/warnings/energy evidence','Assess warning accepted/rejected increments; extract phase timing from logs; record unknowns','Write per-point raw_history.csv, force_displacement.csv, diagnostics.json and provenance plus aggregate result.json','Retain source hashes before/after and no source mutation; register artifacts and send structured result to MAIN','Only write assigned private/odb subtree; MAIN owns analysis/report/index/status; do not open sealed files or old mixed reports'])
odb=hub.create_task(identity['agent_id'],'ODB','extract_four_existing_odb',payload,'run022-odb-v1');msg=hub.message(odb['task_id'],identity['agent_id'],'ODB',payload,'run022-odb-handoff-v1')
save(OUT/'task_ids.json',dict(main_task_id=main['task_id'],odb_task_id=odb['task_id'],identity=identity,message_id=msg['message_id']))
hub.artifact(main['task_id'],identity['agent_id'],PRIV/'execution_audit.json',{'run':'run_022','method':'Readonly public API and exact frozen paths'},version='run022-v1')
print(json.dumps(dict(task_ids=read(OUT/'task_ids.json'),points=[dict(point=r['point']['point_id'],execution=r['execution'],safe=r['safe_for_odb_read'],process_observations=r.get('current_phase_process_observations')) for r in records]),ensure_ascii=False))
