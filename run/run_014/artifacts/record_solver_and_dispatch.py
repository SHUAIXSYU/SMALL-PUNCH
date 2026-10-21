"""Record terminal GUI Runner evidence, then create one real ODB role task.

Never starts/retries Solver or changes Queue. Cross-chat delivery is a separate
explicit Codex tool operation by MAIN; database messages alone do not deliver it.
"""
import json
import subprocess
import time
from pathlib import Path
from coordinate_once import (ROOT, RUN, OUT, PROJECT, RUNTIME, PID, INP, HASH, JOB, WORK,
                             AbqJobPilotClient, Hub, read, write, sha, now, require, runner_ownership_state)
from abqjobpilot.process_identity import verify_launch_evidence, verify_identity
from abqjobpilot.run_evidence import read_process_evidence

require(not (OUT / 'solver_terminal_result.json').exists(), 'Terminal evidence already recorded; do not create duplicate tasks')
receipt = read(OUT / 'enqueue_result.json')
qid = receipt['queue_id']
client = AbqJobPilotClient().for_project(project_id=PID)
state = client.status(job_id=qid).to_dict()
outputs = client.locate_outputs(job_id=qid).to_dict()
queue = read(RUNTIME / 'queue.json')['jobs']
require(len(queue) == 1 and queue[0]['queue_id'] == qid, 'Unexpected queue identity')
job = queue[0]
require(job['status'] in {'COMPLETED_OK', 'COMPLETED_WITH_WARNINGS'} and job['final_verdict'] == 'SUCCESS', 'Full analysis is not confirmed successful')
require(state['status'] == 'COMPLETED' and not state['errors'] and state['odb_exists'] and not state['lock_exists'], 'Public completed/ODB safety check failed')
require(job['job_name'] == JOB and job['inp_path'] == str(INP) and job['work_dir'] == str(WORK), 'Job location mismatch')
require(job['cpus'] == 14 and job['gpus'] == 0 and job['run_datacheck'] and job['run_full'], 'Execution configuration mismatch')
require(runner_ownership_state(RUNTIME)['state'] == 'ABSENT', 'Runner still owns runtime')
live = read(RUNTIME / 'live_status.json')
require(live['phase'] == 'IDLE', 'Runtime not idle')
native = read_process_evidence(RUNTIME, live.get('process_evidence_path'))
require(native and native['queue_id'] == qid, 'Native phase evidence missing or mismatched')
processes = {phase: verify_launch_evidence(native['phases'][phase]['process_identity'])
             for phase in ['DATACHECK_RUNNING', 'FULL_RUNNING']}
require(all(native['phases'][phase]['command_exit']['return_code'] == 0 for phase in processes), 'Native return codes do not match')
# Preserve the native aggregate UNCONFIRMED: a short-lived process lacked an
# executable identity. Independently establish *present read safety*, not recovery.
pid_output = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
    'Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object -ExpandProperty ProcessId | ConvertTo-Json -Compress'], text=True)
current_pids = set(json.loads(pid_output))
identity_checks = []
missing_identity = []
for phase, entry in native['phases'].items():
    evidence = entry['process_identity']
    for proc in [evidence['launcher']] + evidence['observed_children']:
        if proc.get('identity_status') == 'CONFIRMED':
            check = verify_identity(proc)
            require(check['state'] == 'CONFIRMED_EXITED', 'Known process not confirmed exited')
            identity_checks.append({'phase': phase, 'process': proc, 'current_check': check})
        else:
            require(proc['pid'] not in current_pids, 'Unidentified tracked PID still exists; read blocked')
            missing_identity.append({'phase': phase, 'process': proc, 'current_pid_absent': True})
read_safety = {'observed_at': now(), 'known_identity_checks': identity_checks,
               'incomplete_historical_identities': missing_identity, 'current_pid_snapshot': sorted(current_pids),
               'aggregate_native_status_preserved': processes,
               'scope': 'Present read safety only; no recovery/retry authorization; historical incomplete identity remains WARNING'}
text = Path(job['log_path']).read_text(encoding='utf-8', errors='replace')
markers = [line for line in text.splitlines() if '] START ' in line or '] END ' in line]
require(len(markers) == 4 and sum('START DATACHECK_RUNNING' in x for x in markers) == 1
        and sum('END DATACHECK_RUNNING return_code=0' in x for x in markers) == 1
        and sum('START FULL_RUNNING' in x for x in markers) == 1
        and sum('END FULL_RUNNING return_code=0' in x for x in markers) == 1, 'Not exactly one successful two-phase attempt')
sta = Path(job['sta_path']).read_text(encoding='utf-8', errors='replace')
require('THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in sta.upper(), 'STA success evidence missing')
require(sha(INP) == HASH, 'Original candidate changed')
files = []
for key in ['odb_path', 'sta_path', 'msg_path', 'dat_path', 'log_path']:
    p = Path(job[key])
    require(p.is_file() and p.parent == WORK, 'Missing or unexpected output: ' + key)
    before = (p.stat().st_size, p.stat().st_mtime_ns)
    digest = sha(p)
    require(before == (p.stat().st_size, p.stat().st_mtime_ns), 'Output changed during hashing')
    files.append({'path': p.relative_to(ROOT).as_posix(), 'role': key, 'sha256': digest,
                  'size': before[0], 'mtime_ns': before[1]})
time.sleep(2)
require(not Path(outputs['lck_path']).exists(), 'Output lock reappeared')
for item in files:
    p = ROOT / item['path']
    require((p.stat().st_size, p.stat().st_mtime_ns) == (item['size'], item['mtime_ns']), 'Output changed during stability interval')
read_safety['output_stat_stability_seconds'] = 2
history = AbqJobPilotClient().list_project_jobs(project_id=PID).to_dict()
result = {'observed_at': now(), 'status': 'WARNING' if job['status']=='COMPLETED_WITH_WARNINGS' else 'PASS',
          'queue_id': qid, 'job_name': JOB, 'task_id': receipt['task_id'], 'project_id': PID, 'inp_sha256': HASH,
          'datacheck': 'PASS', 'full_analysis': job['status'], 'final_verdict': job['final_verdict'],
          'return_code': job['return_code'], 'started_at_local': job['started_at'], 'ended_at_local': job['ended_at'],
          'time_zone': 'Asia/Shanghai UTC+08:00', 'duration_sec': job['duration_sec'], 'cpus': 14, 'gpus': 0,
          'phase_markers': markers, 'solver_attempts': 1, 'retries': 0, 'odb_exists': True,
          'odb_safe_to_open': True, 'odb_valid': 'PENDING_READONLY_ODB_AGENT', 'files': files,
          'runner_ownership': 'ABSENT', 'tracked_processes': processes, 'independent_read_safety': read_safety, 'public_status': state,
          'public_outputs': outputs, 'job_record': job, 'history': history,
          'warning_count_abqjobpilot': job.get('warning_count'), 'fatal_reason': job.get('fatal_reason'),
          'scientific_status': 'NOT_EVALUATED', 'user_gui_start_confirmed': True}
write(OUT / 'solver_terminal_result.json', result)

hub = Hub(ROOT / 'agenthub_sp_invopt/runtime/sp_invopt.sqlite3', lease_seconds=300)
identity = hub.register('MAIN', 'codex-main-run014-results')
main_task = hub.create_task(identity['agent_id'], 'MAIN', 'record_forward_solver_terminal_evidence',
                           {'run_id': 'run_014', 'queue_id': qid, 'project_id': PID, 'job_name': JOB,
                            'scope': 'Read-only terminal evidence and safe ODB handoff; no additional computation'},
                           'run014-main-solver-terminal-v1', depends=[receipt['task_id']])
lease = hub.claim(main_task['task_id'], identity, 'run014-main-solver-terminal-claim-v1')
write(OUT / 'private/terminal_lease.json', lease)
artifact = hub.artifact(main_task['task_id'], identity['agent_id'], OUT / 'solver_terminal_result.json',
                        {'method': 'AbqJobPilot public status/outputs/history; read-only logs and process identity verification',
                         'queue_id': qid}, version='run014-terminal-v1')
hub.finish(lease, result, evidence_state='RECORDED', science_state='NOT_EVALUATED')
hub.message(main_task['task_id'], identity['agent_id'], 'MAIN',
            {'type': 'SOLVER_TERMINAL', 'queue_id': qid, 'evidence': artifact['path'], 'sha256': artifact['sha256'],
             'full_analysis': job['status'], 'science_state': 'NOT_EVALUATED'}, 'run014-solver-terminal-message-v1')

odb_task = hub.create_task(identity['agent_id'], 'ODB', 'extract_new_hollomon_forward_results',
    {'run_id': 'run_014', 'project_id': PID, 'queue_id': qid, 'job_name': JOB, 'inp_path': str(INP), 'inp_sha256': HASH,
     'odb_path': job['odb_path'], 'odb_sha256': next(f['sha256'] for f in files if f['role']=='odb_path'),
     'solver_evidence': str(OUT / 'solver_terminal_result.json'), 'output_directory': str(OUT / 'odb'),
     'real_codex_thread_id': '01a15d5e-f6e8-7373-8991-ae275dfd3b40',
     'scope': ['Independently verify Job/ODB identity and safe completed state',
               'Abaqus Python readOnly=True extract actual Punch RP U2/RF2; raw signs; no 2*pi',
               'CSV and F-D plot in model units; no unsupported unit claim or experimental Loss',
               'Convergence, warnings, PEEQ and energy diagnostics; distinguish rejected attempts',
               'Compare to run_005 true Sanity Job-1 F-D data with hash/provenance; interpolation explicit',
               'Register artifacts via Hub API, finish and send structured persistent message to MAIN'],
     'historical_data': str(ROOT / 'run/run_005/artifacts/punch_force_displacement.csv'),
     'historical_odb': str(ROOT / 'CAE/Models/Sanity/Job-1.odb'),
     'max_solver_jobs': 0, 'max_solver_retries': 0, 'science_state': 'NOT_EVALUATED',
     'repository_outputs': 'Only run/run_014/artifacts/odb; do not create new Run or edit MAIN index/run.json/summary'},
    'run014-real-odb-extraction-v1', depends=[main_task['task_id']])
msg = hub.message(odb_task['task_id'], identity['agent_id'], 'ODB',
                  {'type': 'TASK_ASSIGNED', 'task_id': odb_task['task_id'], 'queue_id': qid,
                   'action': 'Real ODB Codex session must poll/claim; database message is not proof of delivery'},
                  'run014-real-odb-handoff-v1')
require(hub.verify_chain(), 'Hub chain invalid')
write(OUT / 'odb_handoff.json', {'observed_at': now(), 'identity': identity,
      'main_solver_evidence_task_id': main_task['task_id'], 'odb_task_id': odb_task['task_id'],
      'queue_id': qid, 'message_id': msg['message_id'], 'terminal_artifact': artifact,
      'delivery_state': 'PERSISTED_AWAITING_CODEX_MESSAGE', 'audit_hash_chain_valid': True})
print(json.dumps({'full_analysis': job['status'], 'duration_sec': job['duration_sec'],
                  'odb_task_id': odb_task['task_id'], 'queue_id': qid}, indent=2))
