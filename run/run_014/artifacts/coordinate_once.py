"""Run014: read-only admission and exactly one public enqueue; NEVER starts Runner.

Modes are intentionally separate. An exclusive attempt marker prevents a second
enqueue call even after an uncertain failure. Do not delete it to retry.
"""
import datetime
import hashlib
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_014'
OUT = RUN / 'artifacts'
ABQ = Path(r'D:\Projects\abqjobpilot')
PROJECT = ROOT / 'agenthub_sp_invopt/abqjobpilot_project'
RUNTIME = PROJECT / 'runtime'
PID = 'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
INP = ROOT / 'run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp'
HASH = 'fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a'
JOB = 'SPIO_R014_Q200_N010'
WORK = OUT / 'solver' / JOB
SOURCE_HEAD = '7012133e7cc0176bb3e56fc24d7154ee3b90bb81'
sys.path[:0] = [str(ABQ), str(ROOT / 'agenthub_sp_invopt')]
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot import config
from abqjobpilot.runtime_coordination import runner_ownership_state, queue_transaction
from hub import Hub

def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(p, data):
    if p.exists():
        raise FileExistsError('Immutable evidence already exists: ' + str(p))
    temp = p.with_name(p.name + '.tmp')
    with temp.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    read(temp)
    temp.replace(p)

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def git(*args):
    return subprocess.check_output(['git', '-C', str(ABQ), *args], text=True).strip()

def processes():
    # OS observation only. This helper NEVER calls any Abaqus executable.
    command = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], text=True, encoding='utf-8', errors='replace')
    entries = json.loads(raw)
    relevant = []
    conflicts = []
    for p in entries:
        name = p['Name'].lower()
        cmd = p.get('CommandLine') or ''
        executable = p.get('ExecutablePath') or ''
        solver = bool(re.search(r'^(standard|explicit|pre|package|abq.*|smap.*)\.exe$', name))
        relevant_abq = 'abaqus' in executable.lower() or 'abqjobpilot' in cmd.lower()
        if solver or relevant_abq:
            relevant.append(p)
        # Any active solver is conservatively a blocker when output identity is unavailable.
        if solver or (name in {'cmd.exe', 'python.exe', 'pythonw.exe'} and
                      (JOB.lower() in cmd.lower() or str(WORK).lower() in cmd.lower())):
            conflicts.append(p)
    return {'observed_at': now(), 'process_count': len(entries), 'relevant': relevant, 'conflicts': conflicts}

def protected():
    files = [PROJECT / 'project.json', PROJECT / 'project.db', RUNTIME / 'settings.json',
             INP, ROOT / 'inverse/hollomon.py', ROOT / 'CAE/Models/Sanity/SP_InvOpt_Sanity_model.cae',
             Path.home() / '.abqjobpilot/recent_projects.json', Path.home() / '.abqjobpilot/app_settings.json']
    files += list((ROOT / 'run/run_013').rglob('*.json'))
    return {str(p): sha(p) for p in files}

def request(task_id=None):
    return JobRequest(inp_path=str(INP), job_name=JOB, working_dir=str(WORK), cpus=14, gpus=0,
                      run_datacheck=True, run_full=True, submission_mode='enqueue_only', allow_solver_submit=False,
                      batch='run_014', strategy='Q200_N010', metadata={
                          'notes': f'run_014; task_id={task_id}; project_id={PID}; inp_sha256={HASH}; max_attempts=1; retries=0; GUI Start Queue only',
                          'project_id': PID, 'inp_sha256': HASH, 'task_id': task_id,
                          'max_attempts': 1, 'auto_retries': 0})

def check():
    api = AbqJobPilotClient()
    caps = api.capabilities()
    require(caps['application_version'] == '0.2.2' and not caps['capabilities']['solver_start'], 'Unexpected API capabilities')
    require(git('rev-parse', 'HEAD') == SOURCE_HEAD and not git('status', '--porcelain'), 'External source identity changed')
    settings = api.get_project_settings(project_id=PID).to_dict()
    require(settings['status'] == 'PERSISTED' and settings['persisted'] and settings['exists'], 'Settings not PERSISTED')
    require(not settings['errors'] and not settings['defaulted_fields'], 'Settings errors/default substitution')
    require(settings['project_id'] == PID and Path(settings['project_path']).resolve() == PROJECT, 'Project mismatch')
    require(Path(settings['runtime_dir']).resolve() == RUNTIME and Path(settings['settings_file']).resolve() == RUNTIME / 'settings.json', 'Runtime mismatch')
    require(read(PROJECT / 'project.json')['project_id'] == PID, 'Manifest ID mismatch')
    saved = settings['settings']
    require(saved == settings['effective_settings'] == read(RUNTIME / 'settings.json'), 'Settings values disagree')
    expected = {'abaqus_cmd': r'D:\ABAQUS2024\Commands\abq2024.bat', 'default_cpus': 14, 'default_gpus': 0,
                'use_gpu': False, 'run_datacheck': True, 'run_full': True, 'auto_shutdown_enabled': False}
    require(all(type(saved[k]) is type(v) and saved[k] == v for k, v in expected.items()), 'Settings outside authorization')
    require(Path(saved['abaqus_cmd']).is_file() and config.ABAQUS_CMD == saved['abaqus_cmd'], 'Command missing or preview command mismatch')
    require(sha(INP) == HASH, 'Authorized input hash mismatch')
    old = read(ROOT / 'run/run_013/artifacts/verification_result.json')
    require(old['candidate_sha256'] == HASH, 'Run013 identity mismatch')
    keywords = [line.strip() for line in INP.read_text(encoding='utf-8-sig').splitlines()
                if line.lstrip().startswith('*') and not line.lstrip().startswith('**')]
    dependencies = [line for line in keywords if re.search(r'(?i)^\*(include|import)\b|\b(input|file|library|oldjob)\s*=|^\*restart\s*,\s*read', line)]
    require(not dependencies, 'External input dependency requires review')
    scoped = api.for_project(project_id=PID)
    require(Path(scoped.runtime_dir) == RUNTIME, 'Scoped runtime mismatch')
    queue = scoped.list_jobs()
    require(queue['status'] == 'OK' and queue['jobs'] == [], 'Queue not empty: do not repeat or append')
    history = api.list_project_jobs(project_id=PID).to_dict()
    require(history['status'] == 'OK', 'History query failed')
    require(JOB not in json.dumps(history), 'Job identity already present in history')
    owner = runner_ownership_state(RUNTIME)
    live = read(RUNTIME / 'live_status.json')
    require(owner['state'] == 'ABSENT' and live.get('phase') == 'IDLE', 'Runner ownership/recovery unresolved')
    require(not live.get('process_identity'), 'Prior process evidence requires explicit review')
    require(not list((RUNTIME / 'reports').rglob('*')), 'Existing reports need interruption/history review')
    proc = processes()
    require(not proc['conflicts'], 'Active solver or target process conflict')
    require(WORK.is_dir() and not list(WORK.iterdir()), 'Output directory not empty')
    preflight = scoped.preflight(request()).to_dict()
    dry = scoped.enqueue(request(), dry_run=True).to_dict()
    require(preflight['status'] == 'PREVIEW_READY' and not preflight['errors'], 'Preflight failed')
    require(dry['status'] == 'DRY_RUN_READY' and not dry['errors'], 'Dry-run failed')
    require(not any(dry[k] for k in ['queue_file_mutated', 'solver_started', 'runner_started', 'forbidden_mutations_detected']), 'Dry-run side effect')
    return scoped, {'observed_at': now(), 'status': 'PASS', 'capabilities': caps, 'settings': settings,
                    'source_head': SOURCE_HEAD, 'input_sha256': HASH, 'input_keywords': sorted(set(keywords)),
                    'external_dependencies': dependencies, 'history': history, 'queue': queue,
                    'runner_ownership': owner, 'live_status': live, 'process_observation': proc,
                    'preflight': preflight, 'dry_run': dry, 'abaqus_command_sha256': sha(Path(saved['abaqus_cmd']))}

def prepare():
    require(not (OUT / 'admission.json').exists(), 'Preparation already recorded')
    WORK.parent.mkdir(exist_ok=False)
    (WORK.parent / '.gitignore').write_text('*\n!.gitignore\n', encoding='utf-8')
    WORK.mkdir(exist_ok=False)
    baseline = protected()
    write(RUN / 'checkpoints/protected_before.json', baseline)
    scoped, checks = check()
    require(baseline == protected(), 'Protected file changed during admission')
    write(OUT / 'admission.json', checks)
    print(json.dumps({'stage': 'ADMISSION', 'status': 'PASS', 'queue_empty': True, 'settings': 'PERSISTED', 'job_name': JOB}))

def enqueue_once():
    # No resume/force/retry option: after a call was attempted, inspect evidence and queue.
    require(not (RUN / 'checkpoints/enqueue_attempt.json').exists(), 'Enqueue already attempted; inspect existing queue_id, NEVER repeat')
    require(read(OUT / 'admission.json')['status'] == 'PASS', 'Admission missing')
    scoped, fresh = check()
    write(OUT / 'admission_before_enqueue.json', fresh)
    require(read(RUN / 'checkpoints/protected_before.json') == protected(), 'Protected files changed')
    db = ROOT / 'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
    require(db.is_file(), 'Existing AgentHub database missing')
    hub = Hub(db, lease_seconds=300)
    identity = hub.register('MAIN', 'codex-main-run014-once')
    scope = {'run_id': 'run_014', 'project_id': PID, 'project_path': str(PROJECT), 'inp_path': str(INP),
             'inp_sha256': HASH, 'job_name': JOB, 'working_dir': str(WORK), 'cpus': 14, 'gpus': 0,
             'run_datacheck': True, 'run_full': True, 'max_jobs': 1, 'max_attempts': 1, 'auto_retries': 0,
             'parameters': {'sigma_y_MPa': 200, 'n': 0.1, 'E_MPa': 210000, 'nu': 0.3, 'max_plastic_strain': 0.9},
             'authorization_source': 'Explicit human run_014 message in MAIN Codex conversation',
             'start_method': 'User clicks GUI Start Queue once; no programmatic Solver start',
             'science_state': 'NOT_EVALUATED', 'model_interpretation': 'candidate true total strain',
             'scope': 'Register exact authorization and enqueue one job; completion of this task is not solver completion'}
    task = hub.create_task(identity['agent_id'], 'MAIN', 'authorize_and_enqueue_once', scope,
                           'run014-main-authorize-enqueue-once-v1', depends=['e7d81ac3-0d08-4677-b4f4-f940fbda8209'])
    tid = task['task_id']
    write(OUT / 'authorization.json', {'observed_at': now(), 'task_id': tid, 'identity': identity, 'scope': scope})
    hub.approve(tid, identity['agent_id'], 'enqueue')
    hub.approve(tid, identity['agent_id'], 'start_solver')
    hub.require_approval(tid, 'enqueue')
    hub.require_approval(tid, 'start_solver')
    lease = hub.claim(tid, identity, 'run014-main-enqueue-evidence-v1')
    write(OUT / 'private/lease.json', lease)
    req = request(tid)
    write(OUT / 'request.json', req.to_dict())
    try:
        # Same native transaction as the official API; reentrant public enqueue
        # retains its own active-owner/recovery/output checks. No direct JSON write.
        with queue_transaction(RUNTIME):
            require(scoped.list_jobs()['jobs'] == [], 'Concurrent queue change: stop')
            require(runner_ownership_state(RUNTIME)['state'] == 'ABSENT', 'Concurrent ownership change')
            require(sha(INP) == HASH and not list(WORK.iterdir()), 'Input/output changed')
            require(protected() == read(RUN / 'checkpoints/protected_before.json'), 'Configuration/model changed')
            write(RUN / 'checkpoints/enqueue_attempt.json', {'observed_at': now(), 'task_id': tid, 'job_name': JOB,
                  'attempt': 1, 'max_attempts': 1, 'retry_forbidden': True, 'request_sha256': sha(OUT / 'request.json')})
            result = scoped.enqueue(req, dry_run=False).to_dict()
            write(OUT / 'enqueue_response.json', result)
            require(result['status'] == 'ENQUEUED' and result['job_id'], 'Enqueue rejected or uncertain: no retry')
            require(not any(result[k] for k in ['solver_started', 'runner_started', 'forbidden_mutations_detected']), 'Unexpected enqueue side effect')
            queue = read(RUNTIME / 'queue.json')['jobs']
            write(OUT / 'queue_after_enqueue.json', queue)
            require(len(queue) == 1, 'Unexpected additional queue record')
            job = queue[0]
            expected = {'queue_id': result['job_id'], 'job_name': JOB, 'inp_path': str(INP), 'work_dir': str(WORK),
                        'cpus': 14, 'gpus': 0, 'run_datacheck': True, 'run_full': True, 'status': 'QUEUED'}
            require(all(job[k] == v for k, v in expected.items()), 'Queued fields mismatch')
        status = scoped.status(job_id=result['job_id']).to_dict()
        outputs = scoped.locate_outputs(job_id=result['job_id']).to_dict()
        write(OUT / 'status_after_enqueue.json', status)
        write(OUT / 'outputs_after_enqueue.json', outputs)
        require(status['status'] == 'QUEUED' and not status['odb_exists'] and not status['lock_exists'], 'Unexpected job state')
        require(protected() == read(RUN / 'checkpoints/protected_before.json'), 'Protected state changed')
        receipt = {'observed_at': now(), 'status': 'WARNING', 'execution_state': 'QUEUED / AWAITING_GUI_START',
                   'task_id': tid, 'queue_id': result['job_id'], 'job_name': JOB, 'inp_sha256': HASH,
                   'datacheck': 'NOT_STARTED', 'full_analysis': 'NOT_STARTED', 'odb_exists': False,
                   'odb_valid': 'NOT_EVALUATED', 'odb_agent': 'NOT_DISPATCHED_PENDING_FULL_ANALYSIS',
                   'duration_sec': None, 'protected_files_unchanged': True, 'max_attempts': 1, 'auto_retries': 0,
                   'science_state': 'NOT_EVALUATED', 'new_authorization_required_for_this_job': False}
        write(OUT / 'enqueue_result.json', receipt)
        artifacts = []
        for name in ['admission.json', 'admission_before_enqueue.json', 'authorization.json', 'request.json',
                     'enqueue_response.json', 'queue_after_enqueue.json', 'status_after_enqueue.json',
                     'outputs_after_enqueue.json', 'enqueue_result.json']:
            artifacts.append(hub.artifact(tid, identity['agent_id'], OUT / name,
                             {'run_id': 'run_014', 'method': 'public enqueue-only API; user GUI start pending',
                              'source_head': SOURCE_HEAD, 'project_id': PID, 'queue_id': result['job_id']}, version='run014-v1'))
        hub.finish(lease, receipt, evidence_state='RECORDED', science_state='NOT_EVALUATED')
        msg = hub.message(tid, identity['agent_id'], 'MAIN', receipt, 'run014-enqueued-awaiting-gui-v1')
        inbox = [m for m in hub.poll_messages(identity) if m['task_id'] == tid]
        require(inbox and hub.verify_chain(), 'Hub receipt/audit failure')
        write(OUT / 'agenthub_receipt.json', {'task_id': tid, 'queue_id': result['job_id'], 'identity': identity,
              'task_execution': 'COMPLETED_ENQUEUE_COORDINATION_ONLY', 'artifacts': artifacts,
              'message_id': msg['message_id'], 'inbox': inbox, 'audit_hash_chain_valid': True})
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    except Exception as exc:
        hub.fail(lease, 'RUN014_ENQUEUE_OR_EVIDENCE_FAILED', str(exc), retryable=False)
        raise

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in {'prepare', 'enqueue-once'}, 'Use prepare or enqueue-once')
        (prepare if sys.argv[1] == 'prepare' else enqueue_once)()
    except Exception:
        path = OUT / 'private' / ('failure_' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.txt')
        path.write_text(traceback.format_exc(), encoding='utf-8')
        raise
