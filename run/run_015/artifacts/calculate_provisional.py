"""Evaluate an already frozen private configuration; never execute FE."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from inverse.fd_loss import Curve, Target, ScientificEvidence, evaluate, interpolate


def main(config_path, output_dir):
    config_bytes = config_path.read_bytes()
    cfg = json.loads(config_bytes)
    if cfg['mode'] != 'PROVISIONAL' or cfg['formal_approval'] is not False:
        raise ValueError('This script only supports explicit provisional evaluation')
    if (cfg['weights'] != 'one per selected experimental point'
            or cfg['experimental_zero_shift_m'] != 0 or cfg['fe_zero_shift_m'] != 0
            or cfg['compliance_correction'] != 'NONE'
            or cfg['experiment_sign_change'] != 'NONE'):
        raise ValueError('Unsupported processing configuration; refusing silent changes')
    data = {}
    for name in ('target', 'fe'):
        path = ROOT / cfg[name]
        if hashlib.sha256(path.read_bytes()).hexdigest() != cfg[name + '_sha256']:
            raise ValueError('Frozen source hash mismatch: ' + name)
        data[name] = list(csv.DictReader(path.open(encoding='utf8')))
    all_exp = Curve(tuple(float(r['displacement_m']) for r in data['target']),
                    tuple(float(r['force_n']) for r in data['target']), 'm', 'N')
    lo, hi = cfg['window_m']
    points = [(u, f) for u, f in zip(all_exp.displacement, all_exp.force) if lo <= u <= hi]
    target = Target(Curve(tuple(p[0] for p in points), tuple(p[1] for p in points), 'm', 'N'),
                    tuple(1 for p in points), cfg['force_reference_n'], cfg['version'])
    fe = Curve(tuple(float(r['displacement_model_length']) for r in data['fe']),
               tuple(float(r['force_model_force']) for r in data['fe']), 'm', 'N')
    result = evaluate(target, fe, fe_status=cfg['fe_status'], evidence=ScientificEvidence(), mode='PROVISIONAL')
    result.update(observed_at=datetime.now().astimezone().isoformat(),
                  config_sha256=hashlib.sha256(config_bytes).hexdigest(),
                  formal_loss=None, normalized_rmse=result['loss']**.5,
                  force_reference_n=cfg['force_reference_n'], window_m=cfg['window_m'],
                  warning=cfg['warning'], source_identities={k:cfg[k] for k in ('target_sha256','fe_sha256')})
    output_dir.mkdir(exist_ok=False)
    with (output_dir/'result.json').open('x', encoding='utf8') as f:
        json.dump(result, f, indent=2)
    predictions = interpolate(fe, target.curve.displacement)
    with (output_dir/'residuals.csv').open('x', encoding='utf8', newline='') as f:
        w = csv.writer(f);w.writerow(['displacement_m','experiment_force_n_assumed','fe_force_n','residual_n','weight'])
        w.writerows((u, e, p, p-e, 1) for u,e,p in zip(target.curve.displacement,target.curve.force,predictions))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8,5))
    ax.plot([1000*u for u in target.curve.displacement], target.curve.force, label='Supplied curve (XLSX N label assumed)')
    ax.plot([1000*u for u in target.curve.displacement], predictions, label='run_014 FE on frozen experimental grid')
    ax.set(xlabel='Displacement (mm); zeros unchanged', ylabel='Force (N, provisional assumption)',
           title='PROVISIONAL: common numerical range only\nSensor, compliance, geometry match and force units unverified')
    ax.grid(alpha=.3);ax.legend();fig.tight_layout();fig.savefig(output_dir/'provisional_overlay.png', dpi=170);plt.close(fig)
    return result


if __name__ == '__main__':
    config, out = map(Path, sys.argv[1:])
    if 'private' not in config.parts or 'private' not in out.parts:
        raise ValueError('Private config and output required')
    r = main(config, out)
    print(json.dumps({k:r[k] for k in ('mode','loss','point_count','normalized_rmse','formal_loss')}))
