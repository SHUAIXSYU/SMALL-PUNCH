"""Public API preview-only verification; no solver start or actual enqueue path."""
import sys,json,hashlib,importlib.util
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_023/artifacts';P=A/'private'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
spec=importlib.util.spec_from_file_location('settings_verified',ROOT/'run/run_017/artifacts/preview_batch.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
from abqjobpilot.api import JobRequest
from abqjobpilot.runtime_coordination import runner_ownership_state
api,settings=mod.inspect_settings();save(A/'settings_verification.json',settings)
project=mod.PROJECT
protected=[project/'project.json',project/'project.db',project/'runtime/settings.json',project/'runtime/queue.json',project/'runtime/live_status.json',Path.home()/'.abqjobpilot/recent_projects.json',Path.home()/'.abqjobpilot/app_settings.json']
before={str(p):sha(p) for p in protected};queue=api.list_jobs();owner=runner_ownership_state(project/'runtime')
save(P/'preview_initial_state.json',dict(observed_at=datetime.now().astimezone().isoformat(),protected=before,queue=queue,owner=owner))
assert queue['status']=='OK' and owner['state']=='ABSENT'
terminal={'COMPLETED','COMPLETED_WITH_WARNINGS','DATACHECK_FAILED','FULL_FAILED','FAILED','CANCELLED'}
assert all(j['status'] in terminal for j in queue['jobs']), 'Nonterminal existing queue record'
manifest=read(A/'cae_candidate_manifest.json');assert len(manifest['points'])==2
results=[];(A/'previews').mkdir(exist_ok=False)
for point in manifest['points']:
    src=ROOT/point['source_inp'];inp=ROOT/point['inp_path'];work=ROOT/point['working_dir']
    assert sha(src)==point['source_sha256'] and sha(inp)==point['sha256']
    old=b'0.01, 1., 1e-12, 0.1\n';new=b'0.001, 1., 1e-12, 0.005\n'
    assert src.read_bytes().count(old)==1 and inp.read_bytes()==src.read_bytes().replace(old,new,1)
    assert b'*include' not in inp.read_bytes().lower()
    assert work.is_dir() and not any(work.iterdir())
    assert inp.stem==point['job_name'] and all(j.get('job_name')!=point['job_name'] for j in queue['jobs'])
    req=JobRequest(inp_path=str(inp),job_name=point['job_name'],working_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='preview_only',allow_solver_submit=False,batch='SPIO_run023_numerical_PREVIEW',strategy='two_anchor_increment_refinement',metadata={'run':'run_023','point_id':point['point_id'],'project_id':mod.PID,'inp_sha256':point['sha256'],'authorized_jobs':0,'automatic_retries':0})
    pre=api.preflight(req).to_dict();dry=api.enqueue(req,dry_run=True).to_dict()
    save(A/'previews'/f"{point['point_id']}.json",dict(request=req.to_dict(),preflight=pre,dry_run=dry))
    assert pre['status']=='PREVIEW_READY' and not pre['errors']
    assert dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
    assert not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'))
    assert Path(pre['expected_odb_path']).resolve()==(ROOT/point['expected_outputs']['odb']).resolve()
    assert sha(inp)==point['sha256'] and not any(work.iterdir())
    results.append(dict(**point,inp_absolute_path=str(inp),working_dir_absolute=str(work),project_id=mod.PID,cpus=14,gpus=0,run_datacheck=True,run_full=True,automatic_retries=0,preflight=pre['status'],dry_run=dry['status'],queue_id=None))
after={str(p):sha(p) for p in protected};qafter=api.list_jobs();ownerafter=runner_ownership_state(project/'runtime')
assert before==after and queue==qafter and ownerafter['state']=='ABSENT'
save(P/'preview_integrity.json',dict(before=before,after=after,queue_before=queue,queue_after=qafter,owner_before=owner,owner_after=ownerafter,unchanged=True))
save(A/'prepared_batch.json',dict(version='run023-increment-prepared-v1',created_at=datetime.now().astimezone().isoformat(),status='PASS_PREPARATION_ONLY',project_id=mod.PID,project_path=str(project),settings='PERSISTED',comparison_contract=read(A/'comparison_contract_identity.json'),points=results,queue_unchanged=True,solver_started=False,datacheck_started=False,authorized_solver_jobs=0,authorized_enqueue_jobs=0,limitations=['No Abaqus syntax/license/convergence verification; preview only','Future enqueue must recheck state and receive new user authorization','AUTO_STOP_UNAVAILABLE: manual one-job gating recommended']))
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',points=[dict(point_id=p['point_id'],sha256=p['sha256'],preflight=p['preflight'],dry_run=p['dry_run']) for p in results],queue_unchanged=True)))
