"""Create the one authorized Run 010 task in the existing ledger."""
import datetime, hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_010'
sys.path.insert(0, str(ROOT / 'agenthub_sp_invopt'))
from hub import Hub
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
db = ROOT / 'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
assert db.is_file(), 'Existing ledger required'
write(RUN / 'checkpoints/initial_state.json', {'observed_at':now, 'branch':git('branch','--show-current'), 'head':git('rev-parse','HEAD'), 'remote':git('remote','-v'), 'working_tree':git('status','--short'), 'db_existed':True, 'python':sys.executable, 'python_version':sys.version})
hub = Hub(db)
identity = hub.register('MAIN', 'codex-01a15d5d-c7b5-7f92-8211-56647eb48cbb-run010')
write(RUN / 'artifacts/main_identity.json', identity)
inp = 'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp'
payload = {'run_id':'run_010','objective':'Verify existing candidate Hollomon INP in the real CAE Codex session', 'expected_codex_thread_id':'01a15d5e-a3ad-75f1-b53c-ac6a12c21c48', 'inp':inp,'expected_sha256':'fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a', 'parameters':{'sigma_y_MPa':200,'n':0.1,'E_GPa':210,'nu':0.3,'max_plastic_strain':0.9}, 'science_status':'candidate true-total-strain interpretation; not experimentally validated', 'allowed':['read existing INP and generator','validate materials, path, hash and structural consistency','write CAE evidence under run/run_010/artifacts/cae','register artifacts and finish task in existing Hub'], 'forbidden':['solver','datacheck','enqueue','modify original models','simulate CAE worker','commit','push'], 'coordination':'MAIN audits AbqJobPilot actual Settings and runs public preflight/dry-run only if fully verified. CAE independently verifies INP and reports evidence; no guessing resource settings.'}
write(RUN / 'artifacts/cae_task_request.json', payload)
task = hub.create_task(identity['agent_id'], 'CAE', 'verify_inp', payload, 'run010-real-cae-verify-r008-v1')
hub.approve(task['task_id'], identity['agent_id'], 'verify_inp')
message = hub.message(task['task_id'], identity['agent_id'], 'CAE', {'type':'TASK_ASSIGNED','task_id':task['task_id'],'request':'Read task payload, claim from your real CAE Codex session, maintain heartbeat, register evidence and finish. Main awaits persistent result.'}, 'run010-main-cae-assignment-v1')
write(RUN / 'artifacts/dispatch.json', {'created_at':now,'identity':identity,'task':task,'message':message,'audit_hash_chain_valid':hub.verify_chain()})
write(RUN / 'run.json', {'schema_version':'1.0','run_id':'run_010','stage':'Real Agent Integration & Preflight','objective':payload['objective'],'status':'RUNNING','start_time':now,'end_time':None,'python_interpreter':sys.executable,'git_head':git('rev-parse','HEAD'),'git_branch':git('branch','--show-current'),'task_id':task['task_id']})
print(json.dumps({'identity':identity,'task_id':task['task_id'],'audit':hub.verify_chain()},ensure_ascii=False))
