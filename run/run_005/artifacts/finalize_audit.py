"""Verify extraction delivery and preservation, then finalize this Run only."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_005'
ART=RUN/'artifacts'
PRIVATE=ART/'private'
TZ=dt.timezone(dt.timedelta(hours=8))
def now(): return dt.datetime.now(TZ).isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def save(p,value):
    temp=p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    read(temp);temp.replace(p)
def git(*args):
    r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    return dict(command=['git',*args],returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)

def main():
    baseline=read(PRIVATE/'initial_files.json'); inv=read(PRIVATE/'file_inventory.json')
    allowed={'run/README.md','status/PROJECT_STATUS.md'}
    preservation=[]
    for f in baseline['files']:
        p=ROOT/f['path']
        preservation.append(dict(path=f['path'],unchanged=p.exists() and sha(p)==f['sha256'],authorized_edit=f['path'] in allowed))
    save(PRIVATE/'source_integrity_final.json',dict(observed_at=now(),files=preservation))
    checks={
        'baseline_files_preserved_except_two_status_docs':all(f['unchanged'] or f['authorized_edit'] for f in preservation),
        'unchanged_file_count':sum(f['unchanged'] for f in preservation),
        'all_24_model_job_sources_unchanged':all(sha(ROOT/f['path'])==f['sha256'] for f in inv['files']),
        'old_public_runs_unchanged':all(f['unchanged'] for f in preservation if f['path'].startswith('run/run_00')),
        'git_head_unchanged':git('rev-parse','HEAD')['stdout'].strip()==baseline['head'],
        'git_branch_unchanged':git('branch','--show-current')['stdout'].strip()==baseline['branch'],
        'git_index_unchanged':git('ls-files','--stage')['stdout'].strip()==baseline['index'],
        'git_diff_check':git('diff','--check'),
    }
    odb=read(PRIVATE/'odb_extract_attempt03.json'); summary=read(ART/'numerical_sanity.json')
    hist=odb['steps'][summary['selected_step']]['history_regions'][summary['selected_history_region']]['outputs']
    with (ART/'punch_rp_history_raw.csv').open(newline='') as f:raw=list(csv.DictReader(f))
    with (ART/'punch_force_displacement.csv').open(newline='') as f:positive=list(csv.DictReader(f))
    checks['raw_csv_exactly_matches_odb']=len(raw)==181 and all(float(row['step_time'])==hist['U2']['data'][i][0] and float(row['U2_model_length'])==hist['U2']['data'][i][1] and float(row['RF2_model_force'])==hist['RF2']['data'][i][1] for i,row in enumerate(raw))
    checks['positive_csv_exact_signed_transform']=len(positive)==181 and all(float(row['displacement_model_length'])==-float(raw[i]['U2_model_length']) and float(row['force_model_force'])==-float(raw[i]['RF2_model_force']) for i,row in enumerate(positive))
    checks['odb_is_readonly_and_successful']=odb['odb']['isReadOnly'] is True and odb['status']=='PASS'
    checks['same_rp_history_field_consistency']=summary['history_field_U2_max_error']==0 and summary['history_field_RF2_max_error']==0
    checks['inp_odb_mesh_identity']=summary['inp_odb_topology_match']
    checks['png_signatures_valid']=all((ART/f).read_bytes()[:8]==b'\x89PNG\r\n\x1a\n' for f in ['force_displacement.png','punch_u2_time.png','punch_rf2_time.png','energy_diagnostics.png','input_geometry_audit.png'])
    checks['image_visual_review']='All five figures inspected; geometry legend/title overlap corrected and re-inspected.'
    checks['no_new_source_job_files']=all(set(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())==set(f['path'] for f in baseline['files'] if f['path'].startswith(folder+'/')) for folder in ['CAE/Models/Sanity','CAE/Models/TempTry'])
    final=RUN/'checkpoints/final_state.json'
    save(final,dict(status='RUNNING',checks=checks,observed_at=now()))
    link_errors=[]
    for p in [RUN/'summary.md',*ART.glob('*.md'),ROOT/'run/README.md',ROOT/'status/PROJECT_STATUS.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            location=unquote(target.split('#')[0])
            if location and not (p.parent/location).exists():link_errors.append(dict(file=p.relative_to(ROOT).as_posix(),target=target))
    checks['local_document_links_valid']=not link_errors
    checks['link_errors']=link_errors
    checks['public_json_parse']=True
    for p in RUN.rglob('*.json'):
        if 'mplconfig' not in p.parts:read(p)
    failures=[k for k,v in checks.items() if v is False]
    if checks['git_diff_check']['returncode']!=0:failures.append('git_diff_check')
    save(final,dict(status='PASS' if not failures else 'FAILED',observed_at=now(),checks=checks,failures=failures,working_tree=git('status','--short'),
        preservation_scope='97 baseline files outside original references, private prior audits and Git internals; 24 model/job source files hashed before/after. Only two existing status docs edited.'))
    if failures:raise RuntimeError('Verification failed: '+repr(failures))
    old=RUN/'checkpoints/run.running.json'
    if not old.exists():old.write_bytes((RUN/'run.json').read_bytes())
    save(ART/'execution_record.json',dict(observed_at=now(),research_python=sys.executable,
        abaqus_python=odb['executable'],abaqus_launcher=r'D:\ABAQUS2024\commands\abq2024.bat',
        method='Abaqus launcher python (not cae/analysis/datacheck), separate processes, readOnly=True, source hashes before and after.',
        attempts=[
            dict(attempt='Sanity 01',status='FAILED',reason='JSON serialization: float32 not serializable; source ODB read-only, closed in finally',wrapper_returncode=0,evidence='run/run_005/artifacts/private/odb_extract_console.txt'),
            dict(attempt='Sanity 02',status='PASS',reason='Explicit numeric scalar conversion',evidence='run/run_005/artifacts/private/odb_extract_attempt02.json'),
            dict(attempt='Sanity 03',status='PASS',reason='Added requested RP UR3/RM3 and separate valid COPEN diagnostics',evidence='run/run_005/artifacts/private/odb_extract_attempt03.json'),
            dict(attempt='TempTry comparison',status='PASS',reason='Separate historical same-INP comparison; no mixed histories',evidence='run/run_005/artifacts/private/odb_temtry_comparison.json')],
        other_errors=[dict(code='POWERSHELL_JNL_HASH_SHARING',resolution='PowerShell reported sharing violation; Python read-only hash recheck matched baseline, no forced unlock.'),
            dict(code='DOCS_2024_HTTP_403',resolution='Generic conventions cited from vendor-authored university mirror; not claimed as 2024 runtime tests.')],
        forbidden_actions_performed=[],solver_invoked=False,datacheck_invoked=False,journal_replayed=False,model_modified=False,training_or_optimization=False,dependencies_changed=False,commit_or_push=False))
    exclude={RUN/'run.json',final,ART/'manifest.json'}
    files=[p for p in RUN.rglob('*') if p.is_file() and p not in exclude and 'mplconfig' not in p.parts]
    files += [ROOT/'run/README.md',ROOT/'status/PROJECT_STATUS.md']
    manifest=dict(observed_at=now(),exclusions=['run/run_005/run.json','run/run_005/checkpoints/final_state.json','run/run_005/artifacts/manifest.json','run/run_005/artifacts/private/mplconfig/'],
        files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),size=p.stat().st_size,visibility='private' if 'private' in p.parts else 'public',role='audit_evidence_or_report') for p in sorted(files)])
    save(ART/'manifest.json',manifest)
    assert all(sha(ROOT/f['path'])==f['sha256'] for f in manifest['files'])
    result=read(final);result['checks']['static_manifest_hashes_verified']=len(manifest['files']);result['observed_at']=now();save(final,result)
    record=read(RUN/'run.json')
    record.update(status='WARNING',end_time=now(),abaqus_python_interpreter=odb['executable'],
        readiness={'level_1_model_evidence':'WARNING','level_2_odb_extraction':'PASS','level_3_forward_reproducibility':'WARNING','formal_parameterized_solve_ready':False},
        outputs=[dict(path=p.relative_to(ROOT).as_posix(),role='audit_evidence_or_report') for p in sorted(p for p in RUN.rglob('*') if p.is_file() and 'mplconfig' not in p.parts)]+[dict(path=p,role='run_index_or_project_status') for p in sorted(allowed)],
        validation=[dict(check='read_only_odb_extraction',status='PASS',evidence='run/run_005/artifacts/execution_record.json',scope='Sanity and separate TempTry comparison opened readOnly; source bytes preserved'),
            dict(check='rp_history_and_transform',status='PASS',evidence='run/run_005/artifacts/numerical_sanity.json',scope='181 synchronized same-node samples, field agreement, signed conversion, no interpolation or 2pi'),
            dict(check='historical_input_repeat_agreement',status='PASS',evidence='run/run_005/artifacts/numerical_sanity.json',scope='Two existing same-input histories match exactly; no new controlled rerun or model-validity claim'),
            dict(check='model_numerical_readiness',status='WARNING',evidence='run/run_005/artifacts/forward_model_readiness.md',scope='Material/units/axis/mesh/contact concerns unresolved'),
            dict(check='preservation_delivery_and_hashes',status='PASS',evidence='run/run_005/checkpoints/final_state.json',scope='24 sources and older public runs preserved, Git metadata, CSV readback, links, PNG review, '+str(len(manifest['files']))+' static hashes')],
        errors=[dict(code='NUMERICAL_AND_MODEL_PREREQUISITES',severity='WARNING',message='Material semantics and units, axis BC, local curve changes and mesh/increment sensitivity remain unresolved.',evidence='run/run_005/artifacts/forward_model_readiness.md'),
            dict(code='ODB_SERIALIZATION_ATTEMPT01',severity='RESOLVED',message='Abaqus float32 serialization failed despite wrapper return code 0; logs retained; numeric conversion repaired.',evidence='run/run_005/artifacts/execution_record.json'),
            dict(code='JNL_HASH_SHARING',severity='RESOLVED',message='PowerShell read-sharing failure; subsequent non-mutating Python SHA-256 matches baseline.',evidence='run/run_005/artifacts/execution_record.json'),
            dict(code='DOCS_2024_HTTP_403',severity='RESOLVED_WITH_LIMITATION',message='Vendor manual mirror used for general conventions; release-specific runtime claims rely on actual ODB/API.',evidence='run/run_005/artifacts/odb_audit.md')],
        commit_performed=False,push_performed=False,solver_invoked=False,datacheck_invoked=False,journal_replayed=False,model_modified=False)
    save(RUN/'run.json',record)
    assert all((ROOT/f['path']).is_file() for f in record['outputs'])
    assert all(sha(ROOT/f['path'])==f['sha256'] for f in manifest['files'])
    print(json.dumps(dict(status=record['status'],validation_status='PASS',unchanged_files=checks['unchanged_file_count'],source_files=len(inv['files']),manifest_entries=len(manifest['files']),end_time=record['end_time']),indent=2))

if __name__=='__main__':main()
