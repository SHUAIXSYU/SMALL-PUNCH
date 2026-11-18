"""Read-only AbqJobPilot API audit; create analysis tasks through AgentHub."""
import sys,json,hashlib,subprocess,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_019/artifacts';PRIV=OUT/'private'
PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project';RT=PROJECT/'runtime';PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.runtime_coordination import runner_ownership_state
from abqjobpilot.process_identity import verify_launch_evidence
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def save(p,v):
    assert not p.exists(),p
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(p)
api=AbqJobPilotClient(); scoped=api.for_project(project_id=PID)
info=api.show_project(project_id=PID).to_dict();assert info['status']=='OK' and info['project']['project_id']==PID==read(PROJECT/'project.json')['project_id']
assert Path(scoped.runtime_dir).resolve()==RT
protected=[PROJECT/'project.json',PROJECT/'project.db',RT/'queue.json',RT/'settings.json',RT/'live_status.json',ROOT/'run/run_017/artifacts/prepared_batch.json',ROOT/'inverse/fd_loss.py']
before={str(p):sha(p) for p in protected}
queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
assert queue['status']==history['status']=='OK'
owner=runner_ownership_state(RT);live=read(RT/'live_status.json')
assert owner['state']=='ABSENT' and live['phase']=='IDLE'
batch=read(ROOT/'run/run_017/artifacts/prepared_batch.json')
records=[]
for point in batch['points']:
    inp=ROOT/point['inp_path'];work=ROOT/point['working_dir'];assert sha(inp)==point['inp_sha256']
    q=[j for j in queue['jobs'] if j['job_name']==point['job_name']]
    h=[j for j in history['jobs'] if j['job_name']==point['job_name']]
    rec=dict(point=point,input_sha256=sha(inp),queue_matches=q,history_matches=h,files={},execution='NOT_FOUND',safe_for_odb_read=False)
    for ext in ('odb','sta','msg','dat','log'):
        p=work/(point['job_name']+'.'+ext)
        rec['files'][ext]=dict(path=p.relative_to(ROOT).as_posix(),exists=p.is_file(),sha256=sha(p),size=p.stat().st_size if p.is_file() else None,mtime_ns=p.stat().st_mtime_ns if p.is_file() else None)
    if q:
        assert len(q)==len(h)==1
        j=q[0];assert Path(j['inp_path']).resolve()==inp and Path(j['work_dir']).resolve()==work
        rec['api_status']=scoped.status(job_id=j['queue_id']).to_dict();rec['api_outputs']=scoped.locate_outputs(job_id=j['queue_id']).to_dict()
        rec['history_detail']=api.show_job(h[0]['job_id'],project_id=PID).to_dict()
        evidence=read(RT/j['process_evidence_path']);rec['process_evidence']=evidence
        rec['current_phase_process_observations']={k:verify_launch_evidence(v['process_identity']) for k,v in evidence['phases'].items()}
        rec['execution']=j['raw_status'];rec['queue_id']=j['queue_id'];rec['duration_sec']=j['duration_sec']
        sta=(work/(point['job_name']+'.sta')).read_text(errors='replace')
        rec['sta_completed']='THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in sta
        rec['lock_exists']=(work/(point['job_name']+'.lck')).exists()
        rec['safe_for_odb_read']=(j['status']=='COMPLETED' and j['return_code']==0 and j['final_verdict']=='SUCCESS' and rec['sta_completed'] and not rec['lock_exists'] and all(v['state']=='CONFIRMED_EXITED' for v in rec['current_phase_process_observations'].values()))
    records.append(rec)
time.sleep(1)
for r in records:
    r['output_stable']=all(not f['exists'] or ((ROOT/f['path']).stat().st_size==f['size'] and (ROOT/f['path']).stat().st_mtime_ns==f['mtime_ns']) for f in r['files'].values())
    r['safe_for_odb_read'] &= r['output_stable']
audit=dict(observed_at=now(),project=info,capabilities=api.capabilities(),queue=queue,history=history,runner_ownership=owner,live_status=live,records=records,protected_before=before)
assert before=={str(p):sha(p) for p in protected}
save(PRIV/'execution_audit.json',audit)
hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
identity=hub.register('MAIN','codex-main-run019-results')
main=hub.create_task(identity['agent_id'],'MAIN','audit_existing_results',dict(run_id='run_019',scope='Existing outputs only; no Solver/datacheck/queue/retry',frozen_batch='run/run_017/artifacts/prepared_batch.json'),'run019-main-existing-analysis-v1')
lease=hub.claim(main['task_id'],identity,'run019-main-analysis-v1');save(PRIV/'main_lease.json',lease)
payload=dict(run_id='run_019',main_task_id=main['task_id'],audit_path='run/run_019/artifacts/private/execution_audit.json',
    output_directory='run/run_019/artifacts/private/odb',valid_point_ids=[r['point']['point_id'] for r in records if r['safe_for_odb_read']],
    protocol='run/run_017/artifacts/odb_analysis_protocol.md',loss_identity='run/run_017/artifacts/loss_contract_identity.json',
    scope='Read-only Abaqus Python ODB extraction, log/energy/PEEQ diagnostics and frozen exploratory loss; no solver, queue, retries or hidden tensile access',
    acceptance=['Verify exact input/material/ODB identity and safe readonly open','RP U2 RF2 paired time; u=-U2 F=-RF2 SI','Raw CSV and FD CSV/plot, saved-frame PEEQ including material coverage','Explain cutbacks, negative eigenvalues, distortion and energy evidence','Fixed 241 grid, 0-1.2 mm; full coverage required; PROVISIONAL loss only under frozen gate','Preserve source hashes; register files and structured completion message via Hub','Missing P02-P05 are NOT_FOUND, not zero loss; no complete sensitivity fabricated'])
odb=hub.create_task(identity['agent_id'],'ODB','extract_existing_sensitivity_odb',payload,'run019-odb-existing-results-v1')
message=hub.message(odb['task_id'],identity['agent_id'],'ODB',payload,'run019-odb-handoff-v1')
save(OUT/'task_ids.json',dict(main_task_id=main['task_id'],odb_task_id=odb['task_id'],identity=identity,message_id=message['message_id']))
hub.artifact(main['task_id'],identity['agent_id'],PRIV/'execution_audit.json',dict(run_id='run_019',method='Readonly public API and exact frozen output paths'),version='run019-v1')
print(json.dumps(dict(task_ids=read(OUT/'task_ids.json'),points=[dict(point=r['point']['point_id'],execution=r['execution'],safe=r['safe_for_odb_read']) for r in records]),ensure_ascii=False))
