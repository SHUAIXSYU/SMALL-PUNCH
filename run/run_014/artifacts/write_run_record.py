"""Write initial pending Run report; never mutates external runtime or Hub."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from coordinate_once import ROOT, RUN, OUT, INP, HASH, PID, JOB, WORK, read, write, sha, now

result = read(OUT / 'enqueue_result.json')
initial = read(RUN / 'checkpoints/initial_git.json')
data = {
    'schema_version': '1.0', 'run_id': 'run_014',
    'stage': 'First authorised Hollomon forward validation',
    'objective': 'One exact candidate, one queue job, user GUI Runner start, then real ODB handoff',
    'status': 'WARNING', 'execution_state': 'QUEUED / AWAITING_GUI_START',
    'start_time': initial['observed_at'], 'end_time': None,
    'time_notes': 'Run pending human GUI Start Queue; no computation duration observed.',
    'python_interpreter': sys.executable, 'git_head': initial['head'], 'git_branch': initial['branch'],
    'inputs': [{'path': INP.relative_to(ROOT).as_posix(), 'sha256': HASH, 'role': 'unchanged authorised candidate'},
               {'path': 'agenthub_sp_invopt/abqjobpilot_project/project.json', 'role': 'exact Project identity'},
               {'path': 'agenthub_sp_invopt/abqjobpilot_project/runtime/settings.json', 'role': 'PERSISTED settings'},
               {'path': 'run/run_013/artifacts/verification_result.json', 'role': 'prior input identity and settings evidence'}],
    'outputs': [{'path': p.relative_to(ROOT).as_posix(), 'role': p.stem} for p in sorted(OUT.glob('*.json'))],
    'validation': [{'check': label, 'status': 'PASS', 'evidence': 'run/run_014/artifacts/' + name,
                    'scope': scope} for label, name, scope in [
                        ('Hard admission', 'admission_before_enqueue.json', 'Project, persisted settings, input hash/dependencies, empty queue, owner/process/output absence, preflight/dry-run'),
                        ('Single enqueue', 'queue_after_enqueue.json', 'One queue record, explicit resource/phase/output fields, no start'),
                        ('AgentHub evidence', 'agenthub_receipt.json', 'Exact task-scoped approvals, nine artifact records, MAIN message receipt and hash chain')]],
    'errors': [], 'project_id': PID, 'task_id': result['task_id'], 'queue_id': result['queue_id'],
    'job_name': JOB, 'working_dir': WORK.relative_to(ROOT).as_posix(),
    'max_jobs': 1, 'max_attempts': 1, 'auto_retries': 0, 'cpus': 14, 'gpus': 0,
    'run_datacheck': True, 'run_full': True, 'datacheck_status': 'NOT_STARTED', 'full_analysis_status': 'NOT_STARTED',
    'duration_sec': None, 'odb_exists': False, 'odb_valid': 'NOT_EVALUATED', 'odb_agent_status': 'NOT_DISPATCHED_PENDING_FULL_ANALYSIS',
    'sanity_comparison': 'UNKNOWN_PENDING_NEW_RESULTS', 'numerical_warnings': None,
    'science_state': 'NOT_EVALUATED', 'queue_written': True, 'solver_started': False, 'datacheck_started': False,
    'settings_written': False, 'commit_performed': False, 'push_performed': False,
    'further_authorization_required_for_current_job': False,
    'further_authorization_required_for_retry_or_additional_job': True}
write(RUN / 'run.json', data)
manifest = {'observed_at': now(), 'entries': [
    {'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'role': p.stem,
     'visibility': 'private' if 'private' in p.parts else 'repository evidence'}
    for p in sorted(RUN.rglob('*')) if p.is_file() and p.name != 'run.json' and 'solver' not in p.parts
]}
write(OUT / 'manifest.json', manifest)
print(json.dumps({'run_id': 'run_014', 'status': data['status'], 'task_id': data['task_id'], 'queue_id': data['queue_id']}))
