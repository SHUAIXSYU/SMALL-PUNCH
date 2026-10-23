"""Freeze offline qualification artifacts; public Hub calls, scoped read-only verification."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub, HubError

OUT = ROOT / 'run/run_016/artifacts'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(rel, value):
    path = OUT / rel
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def main():
    stamp = datetime.now().astimezone().isoformat()
    identities = json.loads((OUT/'hub_tasks.json').read_text(encoding='utf8'))
    db = ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'
    ids = [identities['tasks'][role] for role in ('CAE', 'ODB')]
    rows = []
    with sqlite3.connect(db.as_uri()+'?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        for tid in ids:
            task = dict(conn.execute('SELECT * FROM tasks WHERE task_id=?', (tid,)).fetchone())
            if task['execution_state'] != 'COMPLETED':
                raise ValueError('Real worker has not completed: '+tid)
            artifacts = [dict(r) for r in conn.execute('SELECT * FROM artifacts WHERE task_id=?', (tid,))]
            if not artifacts:
                raise ValueError('Worker evidence absent')
            for artifact in artifacts:
                path = Path(artifact['path']).resolve()
                if not path.is_relative_to(OUT):
                    raise ValueError('Unexpected worker artifact scope')
                artifact['sha256_verified'] = sha(path) == artifact['sha256']
                if not artifact['sha256_verified']:
                    raise ValueError('Worker artifact hash changed')
            messages = [dict(r) for r in conn.execute(
                "SELECT * FROM messages WHERE task_id=? AND direction='INBOX' AND recipient_role='MAIN'", (tid,))]
            if not messages:
                raise ValueError('No persistent MAIN completion message')
            events = [dict(r) for r in conn.execute(
                'SELECT seq,event,at_iso,actor FROM events WHERE task_id=? ORDER BY seq', (tid,))]
            rows.append(dict(task=task, artifacts=artifacts, messages=messages, events=events))
        approvals = [dict(r) for r in conn.execute(
            'SELECT * FROM approvals WHERE task_id IN (?,?,?)', tuple(identities['tasks'].values()))]
    if approvals:
        raise ValueError('Unexpected run016 action approval')
    save('private/worker_verification.json', dict(observed_at=stamp, verified=rows,
         scope='Only explicit run016 tasks; no historical message/event payload scan',
         receipt_method='Task-scoped read-only SQL plus public Hub acknowledgement; global role poll avoided to protect sealed history',
         approvals=approvals))

    baseline = json.loads((OUT/'private/source_inventory.json').read_text(encoding='utf8'))
    integrity = []
    for row in baseline['files']:
        current = sha(ROOT / row['path'])
        integrity.append(dict(path=row['path'], before=row['sha256'], after=current,
                              unchanged=current == row['sha256']))
    if not all(r['unchanged'] for r in integrity):
        raise ValueError('Protected SPT/model/loss/Abq state changed')
    save('private/integrity_check.json', dict(observed_at=stamp, files=integrity,
                                            heldout_content_access=False, hidden_file_hashed=False))

    protocol_rel = 'run/run_016/artifacts/parameter_and_budget_protocol.md'
    cfg_rel = 'run/run_015/artifacts/private/loss_config_frozen.json'
    xy = [(0.5,0.5),(0.3,0.5),(0.7,0.5),(0.5,0.3),(0.5,0.7),(0,0),(1,0),(1,1)]
    contract = dict(version='run016-offline-qualification-v1', frozen_at=stamp,
        scope='Offline engineering proposal, no execution authorization; formal loss gate remains blocked',
        specification=dict(path=protocol_rel, sha256=sha(ROOT/protocol_rel)),
        bounds=dict(sigma_y_mpa=[150,1000], n=[0.02,0.50],
                    classification='Public-source-informed engineering exploration; not measured bounds'),
        fixed=dict(E_pa=210e9, nu=0.3, interpretation='candidate_true_total'),
        initial_design=[dict(order=i+1, x=x, y=y, sigma_y_mpa=150*(1000/150)**x,
                             n=.02+.48*y, submitted=False) for i,(x,y) in enumerate(xy)],
        loss=dict(configuration_path=cfg_rel, configuration_sha256=sha(ROOT/cfg_rel),
                  implementation_path='inverse/fd_loss.py', implementation_sha256=sha(ROOT/'inverse/fd_loss.py'),
                  status='PROVISIONAL', formal_loss=None, parameter_dependent_crop=False),
        budgets=dict(pilot=5, extension=3, bo=16, de=16, identifiability=4,
                     numerical_quality=2, confirmation=2, total_planning_cap=48,
                     authorized=0, executed=0, automatic_retries=0),
        algorithms=dict(seed=16, de_implemented_in_existing_scipy=True,
                        de_fe_adapter_qualified=False, bo_implementation_qualified=False,
                        actual_search_performed=False),
        prerequisites=['FORCE_UNIT', 'FIXTURE_AND_PUNCH', 'DISPLACEMENT_CORRECTION',
                       'WINDOW_PHYSICS', 'NUMERICAL_QUALITY', 'MODEL_HASH_FREEZE',
                       'UNEXPOSED_REVIEW', 'EXPLICIT_SCOPED_JOB_AUTHORIZATION'],
        blind_validation='Independent retained validation dataset with historical information exposure; no new access')
    assert sum(contract['budgets'][k] for k in ('pilot','extension','bo','de','identifiability','numerical_quality','confirmation')) == 48
    save('inversion_qualification_contract.json', contract)

    hub = Hub(db, lease_seconds=1800)
    identity = identities['identity']
    main_task = identities['tasks']['MAIN']
    lease = hub.claim(main_task, identity, 'run016-main-review-claim-v1')
    save('private/main_lease.json', lease)
    guard = {}
    for action in ('enqueue','start_solver','recover_retry','generate_inp'):
        try:
            hub.require_approval(main_task, action)
        except HubError as exc:
            guard[action] = str(exc)
        else:
            raise ValueError('Unexpected action approval: '+action)
    save('authorization_guard_check.json', dict(observed_at=stamp, expected_denials=guard,
                                              external_api_called=False))
    for row in rows:
        tid = row['task']['task_id']
        hub.message(tid, identity['agent_id'], row['task']['assigned_role'],
                    dict(run='run_016', status='MAIN_REVIEWED', evidence_hashes_verified=True,
                         received_message_ids=[m['message_id'] for m in row['messages']],
                         no_additional_work_authorized=True), 'run016-main-ack-v1')
    print(json.dumps(dict(workers=len(rows), artifact_count=sum(len(r['artifacts']) for r in rows),
                          protected_unchanged=len(integrity), main_task_claimed=main_task,
                          plan_frozen=contract['version'], authorized_jobs=0), indent=2))


if __name__ == '__main__':
    main()
