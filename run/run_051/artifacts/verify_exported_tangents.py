"""Extra MAIN check on actual exported linear-table secants, not target derivatives alone."""
from pathlib import Path
import json,csv
from highp_envelope import Envelope,plastic_block
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_051/artifacts/private'
contract=json.loads((R/'run/run_051/artifacts/material_contract.json').read_text(encoding='utf-8-sig'))
_,_,base,_=plastic_block((R/contract['source_inp']).read_bytes());out=[]
for point in contract['points']:
 with (R/point['table_path']).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 table=[(float(v['yield_stress_pa']),float(v['equivalent_plastic_strain'])) for v in rows]
 model=Envelope(base,contract['p_switch'],sign=point['sign']);intervals=[]
 for (s0,p0),(s1,p1) in zip(table,table[1:]):
  mid=(p0+p1)/2;h=(s1-s0)/(p1-p0);hb=model.slopes[model.index(mid)];ratio=h/hb
  assert not any(p0<p<p1 for _,p in base)
  assert h>0
  lo,hi=(.5,1.) if point['sign']==-1 else (1.,1.5)
  assert lo-1e-9<=ratio<=hi+1e-9
  if p1<=contract['p_switch']:assert abs(ratio-1)<1e-9
  intervals.append({'p0':p0,'p1':p1,'secant_hardening_pa':h,'ratio_to_same_original_segment':ratio})
 first=next(v for v in intervals if v['p0']==contract['p_switch'])
 out.append({'candidate_id':point['candidate_id'],'intervals':intervals,'minimum_table_hardening_pa':min(v['secant_hardening_pa'] for v in intervals),'minimum_ratio':min(v['ratio_to_same_original_segment'] for v in intervals),'maximum_ratio':max(v['ratio_to_same_original_segment'] for v in intervals),'first_after_switch_secant_ratio':first['ratio_to_same_original_segment'],'first_after_switch_relative_tangent_change':first['ratio_to_same_original_segment']-1})
with (P/'exported_tangent_checks.json').open('x',encoding='utf-8') as f:json.dump({'scope':'actual exported PWL table secants; original baseline knot jumps retained, no global C1 claim','records':out,'all_checks_passed':True},f,indent=2,allow_nan=False)
print(json.dumps([{k:v for k,v in r.items() if k!='intervals'} for r in out]))
