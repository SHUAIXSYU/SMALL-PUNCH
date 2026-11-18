"""MAIN approves expired ODB task recovery after prior Codex chat stopped."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_029/artifacts';P=A/'private'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
session=read(P/'main_session.json');odb=session['odb_task_id'];main=session['main_task_id'];identity=session['identity']
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
t=h.task(odb);assert t['execution_state']=='RECOVERY_REQUIRED' and t['generation']==1
assert t['lease_agent'].startswith('ODB:')
files=read(P/'odb/manifest.json')['files'];assert files
for f in files:
 p=ROOT/f['path'];assert p.is_file() and sha(p)==f['sha256']
assert sha(ROOT/'run/run_027/artifacts/solver/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.odb')=='3a58923c7496d91364f4e64fba8e1cdd76c50b8a4f721209ced108fbe6cd4cbd'
# The prior ODB chat's completed turn and idle state were observed via Codex
# wait_threads immediately before this call. This assertion is recorded, not inferred from lease expiry.
h.approve(odb,identity['agent_id'],'recover_retry')
h.recover(odb,identity['agent_id'],worker_stopped_confirmed=True)
assert h.task(odb)['execution_state']=='PENDING' and h.verify_chain()
record={'at':now(),'task_id':odb,'previous_generation':1,'new_execution_state':'PENDING','worker_stopped_confirmation':'Prior ODB Codex turn completed and chat idle; direct wait_threads evidence observed before recovery','source_odb_sha256':'3a58923c7496d91364f4e64fba8e1cdd76c50b8a4f721209ced108fbe6cd4cbd','existing_worker_artifacts_verified':len(files),'action':'task-scoped recover_retry only; no Solver, queue, or ODB re-extraction','audit_chain_valid':True}
with (A/'odb_recovery.json').open('x',encoding='utf8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
h.heartbeat(session['lease'])
h.artifact(main,identity['agent_id'],A/'odb_recovery.json',{'run':'run_029','scope':'task-scoped lease recovery after confirmed worker stop'},version='run029-v1')
print(json.dumps(record,ensure_ascii=False))
