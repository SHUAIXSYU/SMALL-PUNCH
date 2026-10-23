"""Reproduce the frozen SPT-only diagnostic; no solver or optimizer import."""
import csv
from datetime import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from inverse.fd_loss import Curve, Target, ScientificEvidence, evaluate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / 'run/run_016/artifacts'
    tests = unittest.TestSuite()
    for name, rel in [('previous', 'run/run_015/artifacts/test_fd_loss.py'),
                      ('qualification', 'run/run_016/artifacts/test_loss_qualification.py')]:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tests.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    stamp = datetime.now().astimezone().isoformat()
    tests_result = dict(observed_at=stamp, interpreter=sys.executable,
                        python=sys.version, tests_run=result.testsRun,
                        success=result.wasSuccessful(), failures=len(result.failures),
                        errors=len(result.errors), scope='synthetic-only, no FE/optimizer')
    (out / 'loss_test_log.txt').write_text(stream.getvalue(), encoding='utf8')
    (out / 'loss_test_results.json').write_text(json.dumps(tests_result, indent=2), encoding='utf8')
    cfg_path = ROOT / 'run/run_015/artifacts/private/loss_config_frozen.json'
    cfg = json.loads(cfg_path.read_text(encoding='utf8'))
    data = {}
    for key in ('target', 'fe'):
        source = ROOT / cfg[key]
        if digest(source) != cfg[key + '_sha256']:
            raise ValueError('Frozen source identity mismatch: ' + key)
        with source.open(encoding='utf8', newline='') as f:
            data[key] = list(csv.DictReader(f))
    selected = [(float(r['displacement_m']), float(r['force_n'])) for r in data['target']
                if cfg['window_m'][0] <= float(r['displacement_m']) <= cfg['window_m'][1]]
    target = Target(Curve(tuple(p[0] for p in selected), tuple(p[1] for p in selected), 'm', 'N'),
                    (1.,)*len(selected), cfg['force_reference_n'], cfg['version'])
    fe = Curve(tuple(float(r['displacement_model_length']) for r in data['fe']),
               tuple(float(r['force_model_force']) for r in data['fe']), 'm', 'N')
    # A collaborator declaration narrows uncertainty but is not an independent
    # calibration/fixture/numerical qualification record. Formal gates stay false.
    check = evaluate(target, fe, evidence=ScientificEvidence(),
                     fe_status=cfg['fe_status'], mode='PROVISIONAL')
    check.update(observed_at=stamp, config_sha256=digest(cfg_path),
                 implementation_sha256=digest(ROOT / 'inverse/fd_loss.py'),
                 window_m=cfg['window_m'], force_reference_n_assumed=cfg['force_reference_n'],
                 normalized_rmse=check['loss']**.5,
                 rmse_n_assuming_xlsx_n=cfg['force_reference_n']*check['loss']**.5,
                 formal_loss=None,
                 interpretation='Dimensionless weighted MSE normalized by fixed F_ref squared; not MAPE',
                 changes_to_grid_weights_reference_zero_sign='NONE',
                 new_declaration='Actual punch displacement, corrected by declared standard process; calibration unknown')
    (out / 'private/loss_review.json').write_text(json.dumps(check, indent=2), encoding='utf8')
    print(json.dumps(dict(tests=tests_result, provisional=check), indent=2))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
