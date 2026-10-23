"""Freeze prepared input identities and verify current-task evidence only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'run/run_017/artifacts'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub,HubError

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)

def main():
    stamp=datetime.now().astimezone().isoformat()
    tasks=read(OUT/'hub_tasks.json');tid=tasks['tasks']['CAE'];db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        task=dict(conn.execute('SELECT * FROM tasks WHERE task_id=?',(tid,)).fetchone())
        assert task['execution_state']=='COMPLETED'
        artifacts=[dict(r) for r in conn.execute('SELECT * FROM artifacts WHERE task_id=?',(tid,))]
        messages=[dict(r) for r in conn.execute("SELECT * FROM messages WHERE task_id=? AND recipient_role='MAIN' AND direction='INBOX'",(tid,))]
        approvals=[dict(r) for r in conn.execute('SELECT * FROM approvals WHERE task_id IN (?,?)',(tid,tasks['tasks']['MAIN']))]
        events=[dict(r) for r in conn.execute('SELECT seq,actor,event,at_iso FROM events WHERE task_id=? ORDER BY seq',(tid,))]
    assert messages and artifacts
    for a in artifacts:
        p=Path(a['path']).resolve();assert p.is_relative_to(OUT)
        assert sha(p)==a['sha256']
    assert {a['action'] for a in approvals}=={'generate_inp','verify_inp'}
    save(OUT/'private/cae_handoff_verified.json',dict(observed_at=stamp,task=task,
         artifact_count=len(artifacts),artifacts=artifacts,messages=messages,events=events,
         approvals=approvals,scope='Only current CAE task; no sealed historical payloads'))
    baseline=read(OUT/'private/source_inventory.json')
    integrity=[]
    for s in baseline['files']:
        actual=sha(ROOT/s['path']);assert actual==s['sha256']
        integrity.append(dict(path=s['path'],before=s['sha256'],after=actual,unchanged=True))
    save(OUT/'private/integrity_check.json',dict(observed_at=stamp,files=integrity,
                                              protected_count=len(integrity),heldout_read_or_hash=False))

    design=read(OUT/'parameter_design.json');manifest=read(OUT/'cae_candidate_manifest.json')
    preview=read(OUT/'batch_preview_result.json')
    assert len(design['points'])==len(manifest['points'])==len(preview['candidates'])==5
    points=[]
    for d,m,p in zip(design['points'],manifest['points'],preview['candidates']):
        assert d['point_id']==m['point_id']==p['point_id']
        assert d['job_name']==m['job_name']==p['job_name']
        assert d['working_dir']==m['working_dir']==p['working_dir']
        assert d['inp_path']==m['inp_path']==p['inp_path']
        assert sha(ROOT/d['inp_path'])==m['sha256']==p['sha256']
        params=read(ROOT/d['parameters_path'])
        assert params['sigma_y_mpa']==d['sigma_y_mpa'] and params['n']==d['n']
        assert not any((ROOT/d['working_dir']).iterdir())
        assert p['preflight']=='PREVIEW_READY' and p['dry_run']=='DRY_RUN_READY' and p['queue_id'] is None
        points.append(dict(**d,inp_sha256=m['sha256'],parameters_sha256=sha(ROOT/d['parameters_path']),
                           expected_outputs=m['expected_outputs'],maximum_attempts=1,automatic_retries=0))
    refs=['parameter_design.json','cae_candidate_manifest.json','loss_contract_identity.json',
          'odb_analysis_protocol.md','sensitivity_analysis.py','abq_settings_verification.json','batch_preview_result.json']
    bundle=dict(version='run017-five-point-prepared-batch-v1',frozen_at=stamp,
        status='PREPARED_AWAITING_USER_AUTHORIZATION',
        scientific_scope='First local sensitivity study on user-accepted idealised clamping baseline',
        project_id=preview['project_id'],project_path='agenthub_sp_invopt/abqjobpilot_project',
        cpus=14,gpus=0,run_datacheck=True,run_full=True,auto_shutdown=False,
        points=points,contracts=[dict(path='run/run_017/artifacts/'+r,sha256=sha(OUT/r)) for r in refs],
        maximum_future_jobs=5,authorized_jobs=0,executed_jobs=0,queue_ids=[],
        execution_order=[p['point_id'] for p in points],
        proposed_dispatch='One candidate queued at a time after explicit authorization; GUI Start Queue required; review each result before next',
        future_runtime_gate='Recheck persisted settings, hashes, empty outputs, queue, Runner ownership/recovery immediately before any authorized enqueue',
        estimated_baseline_seconds=825,estimated_baseline_allocated_cpu_hours=825*14/3600,
        estimate_uncertainty='One prior 165 s run only; not a prediction or guarantee',
        suggested_wall_clock_review_budget_seconds=3600,
        stop_conditions=['Datacheck failure: no Full','Any failed/cancelled/incomplete Job stops batch',
                         'Input, settings or target identity changed','Output collision or Runner ownership/recovery conflict',
                         'Material coverage exceeded or endpoint approached','Unreviewed negative eigenvalue/distortion/contact warnings',
                         'Cumulative review time budget reached: do not dispatch another Job'],
        no_automatic_retry=True,no_parameter_replacement=True,
        full_inversion_or_global_uniqueness_qualified=False,
        blind_status='Independent retained validation with historical information exposure; no new access')
    save(OUT/'prepared_batch.json',bundle)
    resolution=dict(observed_at=stamp,prior_run='run_016',prior_history_preserved=True,
        force_units='RESOLVED_BY_SOURCE_CONFIRMATION_N',punch_size='SOURCE_CONFIRMED_2_5_MM_AND_MODEL_MATCH',
        fixture_scope='EXPLORATORY_BASELINE_ACCEPTED_BY_USER_NOT_FULL_EQUIVALENCE_PROVEN',
        displacement_correction='UNCERTAINTY_RETAINED_NO_SECONDARY_CORRECTION',
        loss_window='FROZEN_FOR_LOCAL_EXPLORATORY_COMPARISON_ONLY',
        full_formal_inversion='NOT_QUALIFIED_BY_THIS_PREPARATION',
        evidence=['run/run_017/artifacts/private/experimental_metadata.json',
                  'run/run_017/artifacts/private/cae/qualification_report.md',
                  'run/run_017/artifacts/private/loss_contract.json'])
    save(OUT/'run016_resolution_by_new_evidence.json',resolution)
    hub=Hub(db,lease_seconds=1800)
    hub.message(tid,tasks['identity']['agent_id'],'CAE',dict(status='MAIN_ACCEPTED_PREPARATION',
           artifact_hashes_verified=len(artifacts),preflight_and_dry_run_all_pass=True,
           no_additional_generation_or_computation_authorized=True),'run017-main-cae-ack-v1')
    lease=hub.claim(tasks['tasks']['MAIN'],tasks['identity'],'run017-main-final-review-v1')
    save(OUT/'private/main_lease.json',lease)
    denied=[]
    for task_id in tasks['tasks'].values():
        for action in ('enqueue','start_solver','recover_retry'):
            try:hub.require_approval(task_id,action)
            except HubError as exc:denied.append(dict(task_id=task_id,action=action,result=str(exc)))
            else:raise ValueError('Unexpected execution approval')
    save(OUT/'execution_permission_check.json',dict(observed_at=stamp,denied=denied,actual_external_action=False))
    print(json.dumps(dict(cae_artifacts_verified=len(artifacts),baseline_files_unchanged=len(integrity),
                         batch_version=bundle['version'],ready_to_request=True,authorized_jobs=0),indent=2))

if __name__=='__main__':main()
