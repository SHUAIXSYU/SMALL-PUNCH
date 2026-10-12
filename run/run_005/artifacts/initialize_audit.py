"""Inventory and preserve the baseline; no Abaqus or source-file mutation."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_005'
TZ = dt.timezone(dt.timedelta(hours=8))
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()

if __name__ == '__main__':
    baseline = []
    sources = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {'.git', 'references_private', 'Materials', 'materials', 'private', '__pycache__', 'run_005'}]
        for name in files:
            p = Path(folder) / name
            item = dict(path=p.relative_to(ROOT).as_posix(), size=p.stat().st_size,
                        modified_at=dt.datetime.fromtimestamp(p.stat().st_mtime, TZ).isoformat(), sha256=sha(p))
            baseline.append(item)
            if p.suffix.lower() == '.jnl' or p.name.lower() in {'job-1' + ext for ext in ['.odb','.inp','.sta','.msg','.dat','.log','.lck']} or p.suffix.lower() == '.cae':
                item = dict(item, group=p.parent.relative_to(ROOT).as_posix(), source='User-provided local Abaqus model/job artifacts', license='UNKNOWN; no redistribution authorization inferred')
                sources.append(item)
    state = dict(observed_at=dt.datetime.now(TZ).isoformat(), first_clock_observed_at='2026-10-12T18:31:41.656183+08:00',
                 branch=git('branch','--show-current'), head=git('rev-parse','HEAD'), remote=git('remote','-v'),
                 working_tree=git('status','--short'), index=git('ls-files','--stage'), files=baseline,
                 exclusions=['.git/','references_private/','Materials/','materials/','**/private/','__pycache__/','run/run_005/'])
    save(RUN / 'artifacts/private/initial_files.json', state)
    save(RUN / 'checkpoints/initial_state.json', {k:v for k,v in state.items() if k != 'files'})
    save(RUN / 'artifacts/private/file_inventory.json', dict(observed_at=state['observed_at'], files=sources,
        selected_group='CAE/Models/Sanity', rationale='User-identified CAE and matching same-directory Job files; selection subject to ODB/INP/log cross-check, not newest timestamp.',
        excluded_group='CAE/Models/TempTry', method='Project traversal excluding original reference/private audit areas; SHA-256 streaming read, no source copies.'))
    save(RUN / 'artifacts/file_inventory.json', dict(observed_at=state['observed_at'], source_file_count=len(sources), group_count=len(set(f['group'] for f in sources)),
        details='run/run_005/artifacts/private/file_inventory.json', selected_group='Sanity', excluded_group='TempTry', identity_status='PENDING ODB verification', privacy='Source paths and full provenance retained in ignored private audit.'))
    save(RUN / 'run.json', dict(schema_version='1.0', run_id='run_005', stage='Stage 2 entry audit', status='RUNNING',
        objective='Read-only existing ODB extraction and Journal/INP audit; no solver, model changes, optimization or training.',
        start_time=state['first_clock_observed_at'], end_time=None, time_notes='First observed clock after initial reads; exact earlier start unknown.',
        python_interpreter=r'D:\XianLab\envs\conda\torch-gpu\python.exe', git_head=state['head'], git_branch=state['branch'],
        inputs=[dict(path='run/run_005/artifacts/private/file_inventory.json', role='source identities and SHA-256')], outputs=[], validation=[], errors=[]))
    for src, name in [('run/README.md','run_README.md.before'),('status/PROJECT_STATUS.md','PROJECT_STATUS.md.before')]:
        (RUN / 'checkpoints' / name).write_bytes((ROOT / src).read_bytes())
    print(json.dumps(dict(source_file_count=len(sources), baseline_file_count=len(baseline), groups=sorted(set(f['group'] for f in sources))), indent=2))
