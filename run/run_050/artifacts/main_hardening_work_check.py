"""Independent model-implied hardening-work index; not direct local ODB dissipation."""
from pathlib import Path
import csv,json,math
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_050/artifacts/private';F=R/'run/run_046/artifacts/private/freeze'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def integrate(tab,p):
 x,y=tab;assert 0<=p<=x[-1]
 if p==0:return 0.
 idx=int(np.searchsorted(x,p,side='right')-1)
 total=float(np.sum((y[:idx]+y[1:idx+1])*.5*np.diff(x[:idx+1]))) if idx else 0.
 if idx<len(x)-1:
  dx=p-x[idx];yp=y[idx]+(y[idx+1]-y[idx])*dx/(x[idx+1]-x[idx]);total+=float((y[idx]+yp)*dx*.5)
 return total
out=[]
for pid in ['D01','I08']:
 mat=rows(F/f'{pid}_abaqus_yield_stress_plastic_strain.csv');tab=(np.array([float(v['equivalent_plastic_strain']) for v in mat]),np.array([float(v['yield_stress_pa']) for v in mat]));raw=rows(P/f'odb/{pid}/spatial_ips.csv');meta=json.loads((P/f'odb/{pid}/spatial_extraction.json').read_text());ss=[]
 for target in [.3,.6,.9,1.2]:
  d=[v for v in raw if float(v['target_displacement_mm'])==target];bybin=[]
  total=math.fsum(float(v['volume_ref_m3'])*integrate(tab,float(v['PEEQ'])) for v in d)
  for lo,hi in [(0,.1),(.1,.3),(.3,.5),(.5,.9)]:
   w=math.fsum(float(v['volume_ref_m3'])*(integrate(tab,min(float(v['PEEQ']),hi))-integrate(tab,lo)) for v in d if float(v['PEEQ'])>lo)
   bybin.append({'plastic_interval':[lo,hi],'model_implied_reference_work_J':w,'fraction':w/total})
  assert abs(math.fsum(v['model_implied_reference_work_J'] for v in bybin)/total-1)<1e-12
  direct=next(v for v in meta['stages'] if v['target_displacement_mm']==target)['energy_history']['ALLPD']
  ss.append({'target_mm':target,'model_implied_reference_work_J':total,'ALLPD_direct_J':direct,'relative_difference':total/direct-1,'bins':bybin})
 out.append({'candidate_id':pid,'stages':ss})
result={'method':'W_ref_index=sum_IP V0_IP * integral_0^PEEQ frozen_yield_stress(p) dp; exact piecewise-linear table integration','status':'MODEL_IMPLIED_REFERENCE_WORK_INDEX_NOT_DIRECT_LOCAL_ENERGY','assumptions':['existing monotone isotropic J2 hardening','constant reference quadrature measure for an independent consistency index','no assertion of physical large-p validity or exact finite-deformation plastic dissipation','an interval index is not a force contribution and is separate from final-PEEQ-region attribution'],'no_parameter_fit':True,'records':out}
with (P/'main_hardening_work_consistency.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({'finals':[{r['candidate_id']:r['stages'][-1]} for r in out]}))
