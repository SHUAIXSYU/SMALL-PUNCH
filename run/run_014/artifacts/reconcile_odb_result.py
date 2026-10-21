"""MAIN receives the real ODB task, verifies evidence, and closes this Run's work."""
import bisect
import csv
import json
import math
import sqlite3
from pathlib import Path
from coordinate_once import (ROOT, RUN, OUT, PROJECT, RUNTIME, INP, HASH, PID, JOB, WORK,
                             AbqJobPilotClient, Hub, read, write, now, sha, require, git)

handoff = read(OUT / 'odb_handoff.json')
tid = handoff['odb_task_id']
db = ROOT / 'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
hub = Hub(db, lease_seconds=300)
identity = handoff['identity']
task = hub.task(tid)
require(task['execution_state'] == 'COMPLETED' and task['evidence_state'] == 'RECORDED', 'ODB task unfinished')
require(task['science_state'] == 'NOT_EVALUATED' and task['generation'] == 1, 'Unexpected science or claim state')
require(task['lease_agent'] == 'ODB:codex-local-01a15d5e-f6e8-7373-8991-ae275dfd3b40', 'Unexpected ODB producer')
result = read(OUT / 'odb/result.json')
require(json.loads(task['result']) == result, 'Hub result differs from file')
messages = [m for m in hub.poll_messages(identity) if m['task_id'] == tid]
require(messages and any(m['sender'] == task['lease_agent'] for m in messages), 'Real ODB completion message missing')
write(OUT / 'main_received_odb.json', {'observed_at': now(), 'main_identity': identity,
      'odb_task': {k: task[k] for k in ['task_id','execution_state','evidence_state','science_state','lease_agent','lease_session','generation']},
      'messages': messages, 'result': result, 'real_thread_completed': '01a15d5e-f6e8-7373-8991-ae275dfd3b40'})
# Read-only inspection of artifact rows supplements the formal Hub task/message API.
with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
    connection.row_factory = sqlite3.Row
    artifacts = [dict(row) for row in connection.execute('SELECT * FROM artifacts WHERE task_id=?', (tid,))]
require(len(artifacts) == 14 and all(a['producer'] == task['lease_agent'] for a in artifacts), 'ODB artifact producer/count mismatch')
require(all(sha(Path(a['path'])) == a['sha256'] for a in artifacts), 'ODB registered artifact hash mismatch')
manifest = read(OUT / 'odb/manifest.json')
require(all(sha(ROOT / f['path']) == f['sha256'] for f in manifest['files']), 'ODB manifest mismatch')
terminal = read(OUT / 'solver_terminal_result.json')
require(all(sha(ROOT / f['path']) == f['sha256'] for f in terminal['files']), 'Solver output changed after read')
require(sha(INP) == HASH == result['inp_sha256'], 'Input identity changed')
require(sha(ROOT / 'CAE/Models/Sanity/Job-1.odb') == '612bdc14d02642bf66982a4cb00f8c85a08c98b069fb230f5d430cb8709b3d8f', 'Historical ODB changed')

def curve(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return [(float(row['displacement_model_length']),float(row['force_model_force'])) for row in csv.DictReader(f)]
new = curve(OUT / 'odb/punch_force_displacement.csv')
old = curve(ROOT / 'run/run_005/artifacts/punch_force_displacement.csv')
require(len(new) == 170 and len(old) == 181, 'Unexpected F-D sample count')
require(all(new[i][0] < new[i+1][0] for i in range(len(new)-1)), 'Displacement not strictly increasing')
xs = [x for x, y in old]
diffs = []
for x, y in new:
    require(xs[0] <= x <= xs[-1], 'Interpolation outside historical displacement range')
    j = min(max(bisect.bisect_right(xs, x), 1), len(old)-1)
    x0, y0 = old[j-1]; x1, y1 = old[j]
    yhist = y0 + (x-x0)/(x1-x0)*(y1-y0)
    diffs.append(y-yhist)
metrics = {'end_force_difference_model': new[-1][1]-old[-1][1],
           'end_force_difference_percent': 100*(new[-1][1]-old[-1][1])/old[-1][1],
           'max_abs_curve_difference_model': max(abs(x) for x in diffs),
           'rms_curve_difference_model': math.sqrt(sum(x*x for x in diffs)/len(diffs))}
require(abs(metrics['max_abs_curve_difference_model']-result['max_abs_curve_difference_model']) < 1e-9, 'Curve difference verification failed')
require(abs(metrics['rms_curve_difference_model']-result['rms_curve_difference_model']) < 1e-9, 'RMS verification failed')
api = AbqJobPilotClient().for_project(project_id=PID)
queue = read(RUNTIME/'queue.json')['jobs']
require(len(queue)==1 and queue[0]['queue_id']==result['queue_id'] and queue[0]['status']=='COMPLETED_WITH_WARNINGS', 'Queue final state changed')
status = api.status(job_id=result['queue_id']).to_dict()
require(status['status']=='COMPLETED' and not status['lock_exists'] and status['odb_exists'], 'Final public state not completed')
require(not git('status','--porcelain'), 'External source modified')
require(hub.verify_chain(), 'Hub chain invalid')
checks = {'observed_at':now(), 'status':'PASS', 'scope':'MAIN receipt, artifact provenance, independent model-to-model numeric cross-check',
          'odb_task_id':tid, 'real_odb_session':task['lease_session'], 'real_odb_producer':task['lease_agent'],
          'verified_registered_artifact_count':len(artifacts), 'artifacts':artifacts, 'manifest_hashes_valid':True,
          'all_solver_output_hashes_unchanged_after_extraction':True, 'historical_odb_hash_unchanged':True,
          'inp_sha256':HASH, 'independent_metrics':metrics, 'final_public_status':status,
          'queue_count':1, 'audit_hash_chain_valid':True, 'science_state':'NOT_EVALUATED'}
write(OUT/'main_reconciliation.json',checks)
closing = hub.create_task(identity['agent_id'],'MAIN','reconcile_forward_results',
    {'run_id':'run_014','queue_id':result['queue_id'],'odb_task_id':tid,
     'scope':'Receive real ODB result, validate hashes and comparison, report scientific limitations; no further compute'},
    'run014-main-reconcile-v1',depends=[tid])
lease = hub.claim(closing['task_id'],identity,'run014-main-reconcile-claim-v1')
for name in ['main_received_odb.json','main_reconciliation.json','real_odb_claim_observed.json']:
    hub.artifact(closing['task_id'],identity['agent_id'],OUT/name,
                 {'run_id':'run_014','method':'MAIN independent reconciliation','source_task':tid},version='run014-final-v1')
final = {'status':'WARNING','run_id':'run_014','task_id':read(OUT/'enqueue_result.json')['task_id'],
         'main_reconciliation_task_id':closing['task_id'],'odb_task_id':tid,'queue_id':result['queue_id'],
         'job_name':JOB,'datacheck':'PASS','full_analysis':'COMPLETED_WITH_WARNINGS','duration_sec':165,
         'odb_valid_for_readonly_extraction':True,'odb_agent_completed':True,'metrics':metrics,
         'peeq_max_saved_frames':result['peeq_max_saved_frames'],'solver_attempts':1,'auto_retries':0,
         'science_state':'NOT_EVALUATED','current_authorized_job_finished':True,'further_solver_requires_new_authorization':True}
hub.finish(lease,final,evidence_state='RECORDED',science_state='NOT_EVALUATED')
message = hub.message(closing['task_id'],identity['agent_id'],'MAIN',final,'run014-final-main-result-v1')
received = [m for m in hub.poll_messages(identity) if m['task_id']==closing['task_id']]
require(received and hub.verify_chain(),'Final MAIN message/audit failed')
write(OUT/'final_result.json',final)
write(OUT/'final_agenthub_receipt.json',{'observed_at':now(),'task_id':closing['task_id'],
      'outbox_message_id':message['message_id'],'inbox_receipts':received,'audit_hash_chain_valid':True})
print(json.dumps(final,ensure_ascii=False,indent=2))
