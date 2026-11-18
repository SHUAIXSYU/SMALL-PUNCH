"""Synthetic mathematical checks only; not FE data or material evidence."""
import sys,json,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('local',ROOT/'run/run_020/artifacts/local_sensitivity.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
u=np.linspace(0,.0012,241);a=u*1e5;b=(u/.0012)**2*80;c=u*2e5;h=.05
data={'C':c,'L01':c-h*a,'L02':c+h*a,'L03':c-h*b,'L04':c+h*b}
r=m.analyze(data,u)
assert np.allclose(r['Sx_n'],a) and np.allclose(r['Sy_n'],b)
assert max(r['curvature_rms_n'].values())<1e-9
assert np.allclose(r['matrix']['singular_values_raw'],np.linalg.svd(np.column_stack([a,b]),compute_uv=False))
partial=m.analyze({'C':c,'L01':data['L01'],'L02':data['L02']},u)
assert partial['Sy_n'] is None and partial['matrix'] is None
zero=m.analyze({k:c for k in data},u)
assert zero['matrix']['condition_number'] is None and zero['matrix']['numerical_rank']==0
quadratic={**data,'L01':data['L01']+h*h*b,'L02':data['L02']+h*h*b}
q=m.analyze(quadratic,u)
assert np.isclose(q['curvature_rms_n']['x'],np.sqrt(np.mean((2*b)**2)))
result=dict(status='PASS',checks=['Known linear sensitivities and SVD','Missing pair stays unavailable','Rank-zero matrix not finite condition number','Known quadratic curvature'],synthetic_only=True,not_fe_evidence=True)
with (ROOT/'run/run_022/artifacts/sensitivity_math_checks.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
