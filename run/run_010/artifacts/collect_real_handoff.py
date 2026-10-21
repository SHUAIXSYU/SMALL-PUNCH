"""MAIN receives persistent messages and verifies the real CAE task's evidence."""
import datetime,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'run/run_010/artifacts'
sys.path.insert(0,str(ROOT/'agenthub_sp_invopt'))
from hub import Hub
db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
hub=Hub(db)
identity=json.loads((OUT/'main_identity.json').read_text(encoding='utf-8'))
task_id=json.loads((ROOT/'run/run_010/run.json').read_text(encoding='utf-8'))['task_id']
received=hub.poll_messages(identity)
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
(OUT/'private').mkdir(exist_ok=True)
(OUT/'private'/('main_poll_'+stamp.replace(':','_')+'.json')).write_text(json.dumps(received,ensure_ascii=False,indent=2),encoding='utf-8')
task=hub.task(task_id)
task.pop('lease_token',None)
with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
    c.row_factory=sqlite3.Row
    artifacts=[dict(r) for r in c.execute('SELECT * FROM artifacts WHERE task_id=?',(task_id,))]
    messages=[dict(r) for r in c.execute("SELECT m.*,r.received AS receipt_time FROM messages m JOIN message_receipts r ON r.message_id=m.message_id WHERE m.task_id=? AND m.recipient_role='MAIN' AND r.session_id=?",(task_id,identity['session_id']))]
    events=[dict(r) for r in c.execute('SELECT * FROM events WHERE task_id=? ORDER BY seq',(task_id,))]
for artifact in artifacts:
    p=Path(artifact['path'])
    artifact['exists']=p.is_file()
    artifact['hash_verified']=p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==artifact['sha256']
    artifact['path']=str(p.relative_to(ROOT)).replace('\\','/')
completion_messages=[]
for message in messages:
    body=json.loads(message['body'])
    if (message['sender']==task['lease_agent'] and body.get('execution_status')=='COMPLETED'
        and body.get('session_id')==task['lease_session'] and body.get('generation')==task['generation']):
        completion_messages.append(message['message_id'])
result={'observed_at':stamp,'task_id':task_id,'main_identity':identity,'expected_cae_codex_thread_id':'01a15d5e-a3ad-75f1-b53c-ac6a12c21c48','task':task,'artifacts':artifacts,'received_cae_messages':messages,'task_events':events,'audit_hash_chain_valid':hub.verify_chain(),'execution_complete':task['execution_state']=='COMPLETED','artifact_hashes_valid':bool(artifacts) and all(a['hash_verified'] for a in artifacts),'main_received_task_message':bool(messages),'scientific_validation':'NOT_EVALUATED'}
result['main_received_completion_message']=bool(completion_messages)
result['completion_inbox_message_ids']=completion_messages
result['artifact_producer_matches_claimed_cae']=bool(artifacts) and all(a['producer']==task['lease_agent'] for a in artifacts)
target=OUT/'real_handoff.json'
if target.exists():
    (ROOT/'run/run_010/checkpoints'/('handoff_'+stamp.replace(':','_')+'.json')).write_bytes(target.read_bytes())
temp=OUT/'real_handoff.tmp.json'
temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
json.loads(temp.read_text(encoding='utf-8'))
temp.replace(target)
print(json.dumps({k:result[k] for k in ['task_id','execution_complete','artifact_hashes_valid','main_received_task_message','audit_hash_chain_valid']},indent=2))
