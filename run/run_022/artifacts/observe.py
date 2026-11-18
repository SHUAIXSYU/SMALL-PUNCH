"""Append-only public status observations; no queue or Solver mutation."""
import sys,json,hashlib,time
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_022/artifacts';P=OUT/'private'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot']
from abqjobpilot.api import AbqJobPilotClient
from abqjobpilot.runtime_coordination import runner_ownership_state
from abqjobpilot.process_identity import verify_launch_evidence
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
api=AbqJobPilotClient();PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';scoped=api.for_project(project_id=PID);RT=Path(scoped.runtime_dir)
queue=scoped.list_jobs();assert queue['status']=='OK';owner=runner_ownership_state(RT);live=read(RT/'live_status.json')
batch=read(ROOT/'run/run_020/artifacts/prepared_batch.json');initial=read(P/'execution_audit.json');records=[]
full=len(sys.argv)>1 and sys.argv[1]=='final'
for p in batch['points']:
    js=[j for j in queue['jobs'] if j['job_name']==p['job_name']];assert len(js)==1;j=js[0]
    assert j['queue_id']==next(r['queue_id'] for r in initial['records'] if r['point']['point_id']==p['point_id'])
    assert sha(ROOT/p['inp_path'])==p['inp_sha256']
    rec=dict(point=p,queue_id=j['queue_id'],execution=j['raw_status'],queue_matches=js,duration_sec=j.get('duration_sec'),safe_for_odb_read=False)
    if full:
        work=ROOT/p['working_dir'];rec['files']={}
        rec['api_status']=scoped.status(job_id=j['queue_id']).to_dict();rec['api_outputs']=scoped.locate_outputs(job_id=j['queue_id']).to_dict()
        for ext in ['odb','sta','msg','dat','log']:
            path=work/(p['job_name']+'.'+ext);rec['files'][ext]=dict(path=path.relative_to(ROOT).as_posix(),exists=path.is_file(),sha256=sha(path),size=path.stat().st_size if path.is_file() else None,mtime_ns=path.stat().st_mtime_ns if path.is_file() else None)
        pe=RT/j['process_evidence_path'] if j.get('process_evidence_path') else None;observations={}
        if pe and pe.is_file():
            evidence=read(pe);rec['process_evidence']=evidence
            observations={k:verify_launch_evidence(v['process_identity']) for k,v in evidence['phases'].items()}
        rec['current_phase_process_observations']=observations
        rec['sta_completed']=rec['files']['sta']['exists'] and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in (ROOT/rec['files']['sta']['path']).read_text(errors='replace')
        rec['lock_exists']=(work/(p['job_name']+'.lck')).exists()
        rec['safe_for_odb_read']=j['status']=='COMPLETED' and j['return_code']==0 and j['final_verdict']=='SUCCESS' and rec['sta_completed'] and not rec['lock_exists'] and owner['state']=='ABSENT' and live['phase']=='IDLE' and len(observations)==2 and all(v['state']=='CONFIRMED_EXITED' for v in observations.values())
    records.append(rec)
if full:
    time.sleep(1)
    for rec in records:
        rec['output_stable']=all(not f['exists'] or ((ROOT/f['path']).stat().st_size==f['size'] and (ROOT/f['path']).stat().st_mtime_ns==f['mtime_ns']) for f in rec['files'].values());rec['safe_for_odb_read'] &= rec['output_stable']
audit=dict(observed_at=datetime.now().astimezone().isoformat(),runner_ownership=owner,live_status=live,queue=queue,records=records)
if full:
    audit['history']=api.list_project_jobs(project_id=PID).to_dict()
    audit['protected_before']={p:sha(Path(p)) for p in initial['protected_before']}
    save(P/'execution_audit_completed.json',audit)
else:
    folder=P/'observations';folder.mkdir(exist_ok=True);save(folder/(datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'),audit)
print(json.dumps(dict(owner=owner['state'],phase=live['phase'],points=[dict(id=r['point']['point_id'],status=r['execution'],duration=r['duration_sec'],safe=r['safe_for_odb_read']) for r in records])))
