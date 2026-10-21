"""Read-only AbqJobPilot observation. Writes evidence only inside run_014."""
import datetime
import json
from pathlib import Path
from coordinate_once import AbqJobPilotClient, RUN, OUT, RUNTIME, WORK, PID, read, write, now, sha, runner_ownership_state

identity = read(OUT / 'enqueue_result.json')
client = AbqJobPilotClient().for_project(project_id=PID)
qid = identity['queue_id']
public_status = client.status(job_id=qid).to_dict()
outputs = client.locate_outputs(job_id=qid).to_dict()
records = read(RUNTIME / 'queue.json')['jobs']
jobs = [job for job in records if job.get('queue_id') == qid]
if len(jobs) != 1:
    raise RuntimeError('Expected exactly one existing Job identity')
job = jobs[0]
log = Path(job['log_path'])
text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
files = [{ 'path': str(p), 'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns }
         for p in WORK.iterdir() if p.is_file()]
stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
observation = {'observed_at': now(), 'job': job, 'queue_count': len(records), 'public_status': public_status,
               'outputs': outputs, 'runner': runner_ownership_state(RUNTIME), 'live': read(RUNTIME / 'live_status.json'),
               'files': files, 'log_tail': text.splitlines()[-30:],
               'phase_markers': [line for line in text.splitlines() if '] START ' in line or '] END ' in line],
               'source': 'Public status/locate_outputs plus read-only queue/live/log metadata'}
path = RUN / 'checkpoints' / ('observation_' + stamp + '.json')
write(path, observation)
run = read(RUN / 'run.json')
write(RUN / 'checkpoints' / ('run_before_observation_' + stamp + '.json'), run)
active = job['status'] in {'DATACHECK_RUNNING', 'FULL_RUNNING', 'RUNNING'}
run.update({'status': 'RUNNING' if active else 'WARNING', 'execution_state': job['status'],
            'datacheck_started': any('START DATACHECK_RUNNING' in x for x in observation['phase_markers']),
            'solver_started': bool(job.get('started_at')),
            'datacheck_status': 'PASS' if any('END DATACHECK_RUNNING return_code=0' in x for x in observation['phase_markers'])
                                and any('START FULL_RUNNING' in x for x in observation['phase_markers'])
                                else ('RUNNING' if job['status']=='DATACHECK_RUNNING' else 'UNKNOWN'),
            'full_analysis_status': 'RUNNING' if job['status']=='FULL_RUNNING' else
                                    ('NOT_STARTED' if not any('START FULL_RUNNING' in x for x in observation['phase_markers']) else job['status']),
            'duration_sec': job.get('duration_sec'), 'odb_exists': public_status['odb_exists'],
            'latest_observation': path.relative_to(RUN.parents[1]).as_posix()})
tmp = RUN / 'run.observation.tmp'
tmp.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
read(tmp)
tmp.replace(RUN / 'run.json')
print(json.dumps({'observed_at': observation['observed_at'], 'job_status': job['status'],
                  'final_verdict': job.get('final_verdict'), 'return_code': job.get('return_code'),
                  'fatal_reason': job.get('fatal_reason'), 'duration_sec': job.get('duration_sec'),
                  'runner': observation['runner']['state'], 'odb_exists': public_status['odb_exists'],
                  'lck_exists': public_status['lock_exists'], 'phase_markers': observation['phase_markers'],
                  'log_tail': observation['log_tail'][-8:], 'snapshot': str(path)}, ensure_ascii=False, indent=2))
