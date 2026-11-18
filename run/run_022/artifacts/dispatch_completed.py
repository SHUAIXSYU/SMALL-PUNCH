"""Dispatch a new extraction task after the actual batch has stopped writing."""
import sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_022/artifacts';P=OUT/'private';sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf8'))
a=read(P/'execution_audit_completed.json');ids=read(OUT/'task_ids.json')
assert a['runner_ownership']['state']=='ABSENT' and a['live_status']['phase']=='IDLE'
assert not (OUT/'extraction_task.json').exists()
eligible=[r['point']['point_id'] for r in a['records'] if r['execution'] in {'COMPLETED_OK','COMPLETED_WITH_WARNINGS'} and r['sta_completed'] and r['output_stable'] and not r['lock_exists']]
hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
hub.heartbeat(read(P/'main_lease.json'))
payload=dict(run_id='run_022',main_task_id=ids['main_task_id'],audit_path='run/run_022/artifacts/private/execution_audit_completed.json',audit_sha256=hashlib.sha256((P/'execution_audit_completed.json').read_bytes()).hexdigest(),output_directory='run/run_022/artifacts/private/extraction',eligible_point_ids=eligible,strict_process_confirmed_points=[r['point']['point_id'] for r in a['records'] if r['safe_for_odb_read']],scope='Completed existing outputs only. Unknown historical process identity must remain disclosed and current read safety independently verified; no Solver/queue/retry',protocol='run/run_020/artifacts/analysis_protocol.md',acceptance=['Separate task after initial pre-execution snapshot; never overwrite private/odb prior result','Abaqus2024 Python openOdb(readOnly=True); verify material table numeric identity with exact frozen INP and ODB job basename; preserve hashes','For each eligible point provide raw RP history CSV, force_displacement.csv with displacement_m and force_n, diagnostics.json plus source provenance, aggregate result.json','Unique ASM_SPT.1 RP; pair U2 RF2 step time; u=-U2 F=-RF2 SI, no abs/2pi/zero shift','Maximum saved-frame PEEQ and actual pmax .9; accepted/rejected warning context, cutbacks, energy and phase durations','If historical process observation UNCONFIRMED, keep historical limitation; only read after current no-target-process/lock/stable/independent read-safety check. Otherwise leave blocked','Register all outputs through existing Hub and return task-scoped message MAIN; do not modify MAIN reports/index/status','No hidden tensile, Solver/datacheck/queue/retry/RL/DE/BO or original source changes'])
t=hub.create_task(ids['identity']['agent_id'],'ODB','extract_completed_four_odb',payload,'run022-odb-completed-v1',depends=[ids['odb_task_id']]);m=hub.message(t['task_id'],ids['identity']['agent_id'],'ODB',payload,'run022-completed-handoff-v1')
with (OUT/'extraction_task.json').open('x',encoding='utf8') as f:json.dump(dict(task_id=t['task_id'],message_id=m['message_id'],payload=payload),f,ensure_ascii=False,indent=2)
print(json.dumps(dict(task_id=t['task_id'],eligible=eligible,strict_confirmed=payload['strict_process_confirmed_points'])))
