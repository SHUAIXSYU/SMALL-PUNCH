import csv
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'run/run_048/artifacts/private'
m=json.loads((BASE/'reassessment_metrics.json').read_text(encoding='utf-8'))
assert m['formal_main_status']=='NOT_EVALUABLE'
assert m['formal_score']['D01'] is None and m['formal_score']['I08'] is None and m['formal_score']['rank'] is None
assert m['frozen_score_gate_rejection'].startswith('Qualification gates unresolved')
with (BASE/'restricted_pointwise_comparison.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==981
x=[float(r['assumed_log_true_total_strain']) for r in rows]
assert math.isclose(x[0],.002,abs_tol=1e-14) and math.isclose(x[-1],.10,abs_tol=1e-14)
assert all(math.isclose(x[i+1]-x[i],.0001,abs_tol=1e-12) for i in range(980))
for cid in ('D01','I08'):
    r=[float(row[f'{cid}_minus_source_MPa']) for row in rows]
    err=math.sqrt(math.fsum(v*v for v in r)/len(r))
    bias=math.fsum(r)/len(r)
    assert math.isclose(err,m['restricted_primary'][cid]['RMSE_MPa'],rel_tol=0,abs_tol=1e-11)
    assert math.isclose(bias,m['restricted_primary'][cid]['signed_bias_MPa'],rel_tol=0,abs_tol=1e-11)
    assert m['run047_conditional_RMSE_reproduction_abs_difference_MPa'][cid]<1e-9
assert m['restricted_primary']['I08']['RMSE_MPa']<m['restricted_primary']['D01']['RMSE_MPa']
assert m['pre_registered_bands'][-1]['status']=='INCOMPLETE_COORDINATE_COVERAGE'
print('PASS: formal null gates, fixed 981-point grid, independent CSV RMSE/bias, run047 reproduction, ordering and incomplete band')
