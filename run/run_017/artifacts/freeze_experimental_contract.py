"""SPT-only versioned metadata promotion. Values remain unchanged; no FE calls."""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from inverse.fd_loss import Curve, Target, ScientificEvidence, evaluate


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    out = ROOT/'run/run_017/artifacts'
    private = out/'private'
    source = ROOT/'run/run_015/artifacts/private/canonical/candidate_fd_si.csv'
    previous = ROOT/'run/run_015/artifacts/private/loss_config_frozen.json'
    old = json.loads(previous.read_text(encoding='utf8'))
    assert sha(source) == old['target_sha256']
    with source.open(encoding='utf8', newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    assert len(rows) == 339
    original_values = [(r['displacement_m'], r['force_n']) for r in rows]
    for r in rows:
        r['processing_status'] = 'UNIT_CONVERSION_ONLY; N_MM_CONFIRMED_BY_SOURCE_RUN017; ZERO_UNCHANGED; NO_SECONDARY_COMPLIANCE_CORRECTION'
    canonical = private/'canonical_fd_source_confirmed.csv'
    with canonical.open('x', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    with canonical.open(encoding='utf8', newline='') as f:
        output_rows = list(csv.DictReader(f))
    assert original_values == [(r['displacement_m'], r['force_n']) for r in output_rows]
    stamp = datetime.now().astimezone().isoformat()
    selected = [(float(r['displacement_m']), float(r['force_n'])) for r in rows
                if 0 <= float(r['displacement_m']) <= .0012]
    assert len(selected) == 241 and all(b[0]>a[0] and b[1]>a[1] for a,b in zip(selected,selected[1:]))
    # Fixed reference copied from prior definition, independently checked, not tuned.
    ref = old['force_reference_n']
    assert max(float(r['force_n']) for r in rows) == ref
    config = dict(version='run017-exploratory-fd-v1', frozen_at=stamp,
        scope='FROZEN_FOR_IDEALISED_CLAMPING_LOCAL_SENSITIVITY_ONLY',
        formal_inversion_qualified=False, calculation_mode='PROVISIONAL',
        target=canonical.relative_to(ROOT).as_posix(), target_sha256=sha(canonical),
        source_rows_count=339, selected_points=241, window_m=[0.,.0012],
        weights='one per selected experimental point', force_reference_n=ref,
        reference_rule='Full supplied curve maximum; same fixed scalar as prior contract, now source-confirmed N',
        interpolation='linear FE to fixed original experimental grid; no extrapolation or automatic cropping',
        formula='sum(w*(F_FE-F_exp)^2)/(sum(w)*F_ref^2)',
        experimental_sign='unchanged positive loading coordinates',
        fe_sign='displacement_m=-U2; force_n=-RF2; no absolute value or additional 2*pi factor',
        experimental_zero_shift_m=0, fe_zero_shift_m=0, secondary_compliance_correction='NONE',
        metadata='run/run_017/artifacts/private/experimental_metadata.json',
        metadata_sha256=sha(private/'experimental_metadata.json'),
        prior_config=previous.relative_to(ROOT).as_posix(), prior_config_sha256=sha(previous),
        changes=['Source party confirms N and mm; historical Origin label conflict retained as resolved',
                 'New metadata-bearing canonical CSV; numerical strings unchanged',
                 'User accepts idealised clamping for exploratory sensitivity, not full fixture equivalence'],
        window_justification='Fixed existing stroke and pre-peak source window, no observed decline; damage absence unproven; not selected by loss',
        failure_rule='Failed/incomplete/invalid FE: no Loss; no auto retry. Coverage, excessive PEEQ or numerical warnings require review.',
        uncertainties=['Correction algorithm and instrument calibration details unverified',
                       'Full fixture equivalence, friction and damage-free window not established',
                       'Current material law and E are candidate assumptions'],
        implementation='inverse/fd_loss.py', implementation_sha256=sha(ROOT/'inverse/fd_loss.py'))
    cfg_path = private/'loss_contract.json'
    save(cfg_path, config)
    fe_path = ROOT/'run/run_014/artifacts/odb/punch_force_displacement.csv'
    assert sha(fe_path) == old['fe_sha256']
    with fe_path.open(encoding='utf8', newline='') as f:
        fe_rows = list(csv.DictReader(f))
    target = Target(Curve(tuple(u for u,f in selected),tuple(f for u,f in selected),'m','N'),
                    (1.,)*len(selected),ref,config['version'])
    fe = Curve(tuple(float(r['displacement_model_length']) for r in fe_rows),
               tuple(float(r['force_model_force']) for r in fe_rows),'m','N')
    evidence = ScientificEvidence(units_and_sign_verified=True)
    result = evaluate(target,fe,fe_status='COMPLETED_WITH_WARNINGS', evidence=evidence, mode='PROVISIONAL')
    result.update(observed_at=stamp, contract_sha256=sha(cfg_path),
                  fe_source=fe_path.relative_to(ROOT).as_posix(), fe_sha256=sha(fe_path),
                  purpose='Recomputed existing run014 reference only; not one of five new candidates',
                  normalized_rmse=result['loss']**.5, rmse_n=ref*result['loss']**.5,
                  formal_loss=None, numerical_values_unchanged=True,
                  reference_scope='exploratory source-confirmed unit interpretation')
    save(private/'reference_loss.json',result)
    save(private/'canonical_provenance.json',dict(observed_at=stamp, numeric_values_unchanged=True,
        source=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
        canonical=canonical.relative_to(ROOT).as_posix(),canonical_sha256=sha(canonical),
        metadata_sha256=sha(private/'experimental_metadata.json'),
        conversion=dict(displacement='original mm multiplied by 0.001 in run015; not applied twice',force='N unchanged'),
        sample_id_status='curve identifier only, specimen serial not supplied',
        origin_label_conflict='preserved in old records, clarified by source party to N',
        source_instrument_record_independently_verified=False))
    save(out/'loss_contract_identity.json',dict(version=config['version'],
        status='FROZEN_EXPLORATORY_COMPARISON',formal_inversion_qualified=False,
        path=cfg_path.relative_to(ROOT).as_posix(),sha256=sha(cfg_path),
        implementation=config['implementation'],implementation_sha256=config['implementation_sha256'],
        new_fe_authorized=0,source_units='SOURCE_CONFIRMED',fixed_window=True))
    print(json.dumps(dict(version=config['version'],status='FROZEN_EXPLORATORY_COMPARISON',
                         points=len(selected),reference_loss=result['loss'],values_unchanged=True),indent=2))


if __name__ == '__main__':
    main()
