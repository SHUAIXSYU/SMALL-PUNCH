"""Assemble the final scoped validation record; performs no solver or queue action."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HUBDIR=ROOT/'agenthub_sp_invopt'; sys.path.insert(0,str(HUBDIR))
from hub import Hub
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
DB=HUBDIR/'runtime'/'sp_invopt.sqlite3'; h=Hub(DB,workspace_root=ROOT); project=HUBDIR/'abqjobpilot_project'; queue=project/'runtime'/'queue.json'
with h.connect() as c:
    tasks=[dict(r) for r in c.execute('SELECT task_id,assigned_role,kind,execution_state,evidence_state,science_state,generation FROM tasks ORDER BY rowid')]
    counts={name:c.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('agents','sessions','tasks','dependencies','approvals','messages','message_receipts','artifacts','events')}
def load(name): return json.loads((ROOT/'run'/'run_008'/'artifacts'/name).read_text(encoding='utf-8'))
mcp=load('mcp_readonly_results.json'); odb=load('historical_odb_interface.json'); cae=load('cae_verification_handoff.json'); queuehash=sha(queue)
result={'run_id':'run_008','status':'WARNING','local_process_handoff':'PASS','task_states':tasks,'agenthub_counts':counts,'agenthub_event_chain_valid':h.verify_chain(),'main_received_cae_verification':bool(cae['main_received_verification']),'odb_interface_status':odb['status'],'odb_is_historical_only':odb['candidate_material_solve']=='NOT_PERFORMED','candidate_inp_parse':load('candidate_inp_parse.json')['status'],'candidate_inp_sha256':sha(ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/'SPIO_R008_Q200_N010_Candidate'/'SPIO_R008_Q200_N010_Candidate.inp'),'abqjobpilot_project_id':json.loads((project/'project.json').read_text(encoding='utf-8'))['project_id'],'abqjobpilot_version':mcp['server_version']['version'],'mcp_tool_names':mcp['tools'],'mcp_readonly_queue_history_status_outputs_connected':True,'abqjobpilot_queue_sha256':queuehash,'abqjobpilot_queue_empty':not json.loads(queue.read_text(encoding='utf-8'))['jobs'],'settings':'UNKNOWN; both global and Project Settings absent','preflight':'NOT_INVOKED_SETTINGS_UNKNOWN','dry_run_enqueue':'NOT_INVOKED_SETTINGS_UNKNOWN','queue_write':'NOT_PERFORMED','solver_or_datacheck':'NOT_PERFORMED','cross_codex_session_delivery':'NOT_VERIFIED; manual Handoff retained','science':'WARNING / NOT_EVALUATED; no experimental or candidate-solve validation'}
if not result['agenthub_event_chain_valid'] or not result['main_received_cae_verification'] or not result['abqjobpilot_queue_empty'] or result['solver_or_datacheck']!='NOT_PERFORMED': raise SystemExit('FINAL_EVIDENCE_CHECK_FAILED')
out=ROOT/'run'/'run_008'/'artifacts'/'final_validation.json'; out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
