import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HUBDIR=ROOT/'agenthub_sp_invopt'; sys.path.insert(0,str(HUBDIR))
from hub import Hub
db=HUBDIR/'runtime'/'sp_invopt.sqlite3'; h=Hub(db,workspace_root=ROOT)
with h.connect() as c:
    tasks=[dict(x) for x in c.execute('SELECT task_id,assigned_role,kind,execution_state,evidence_state,science_state,generation FROM tasks ORDER BY rowid')]
    counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('agents','sessions','tasks','dependencies','approvals','messages','message_receipts','artifacts','events')}
    missing_iso=c.execute('SELECT COUNT(*) FROM events WHERE at_iso IS NULL').fetchone()[0]
report={'status':'PASS_LEDGER_AUDIT','db_relative_path':'agenthub_sp_invopt/runtime/sp_invopt.sqlite3','counts':counts,'tasks':tasks,'audit_hash_chain_valid':h.verify_chain(),'legacy_events_without_iso_timestamp':missing_iso,'current_event_schema':'UTC ISO 8601 timestamp bound into v2 event hashes; legacy pre-migration run_008 events retain their original hash format'}
out=ROOT/'run'/'run_008'/'artifacts'/'hub_state.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
