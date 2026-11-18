"""Independent MAIN cross-check from already hashed raw reaction and energy histories."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_050/artifacts/private'
def load(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=[]
for pid in ['D01','I08']:
 folder=R/f'run/run_045/artifacts/private/odb/{pid}';res=json.loads((folder/'result.json').read_text());ep=folder/'energy_history.csv';fp=folder/'force_displacement.csv'
 for p in [ep,fp]:assert sha(p)==res['artifact_hashes'][p.relative_to(R).as_posix()]
 e=load(ep);f=load(fp);assert len(e)==len(f)
 u=np.array([float(q['displacement_m']) for q in f]);force=np.array([float(q['force_n']) for q in f]);assert np.all(np.diff(u)>0)
 work=np.r_[0,np.cumsum((force[:-1]+force[1:])/2*np.diff(u))]
 stages=[]
 for target in [.3,.6,.9,1.2]:
  i=int(np.argmin(abs(u*1000-target)));q=e[i];pd=float(q['ALLPD']);wk=float(q['ALLWK']);ie=float(q['ALLIE']);fd=float(q['ALLFD']);se=float(q['ALLSE']);tot=float(q['ETOTAL'])
  stages.append({'requested_displacement_mm':target,'actual_displacement_mm':float(u[i]*1000),'saved_index':i,'time':float(q['step_time']),'ALLPD_J':pd,'ALLWK_J':wk,'ALLIE_J':ie,'ALLFD_J':fd,'ALLSE_J':se,'ALLSD_J':float(q['ALLSD']),'ALLAE_J':float(q['ALLAE']),'ETOTAL_J':tot,'force_displacement_work_J':float(work[i]),'work_quadrature_difference_over_ALLWK':float((work[i]-wk)/wk) if wk else None,'ALLPD_over_ALLWK':pd/wk if wk else None,'ALLIE_plus_ALLFD_minus_ALLWK_J':ie+fd-wk,'energy_balance_over_ALLWK':tot/wk if wk else None})
 out.append({'candidate_id':pid,'sources':{'energy_csv':ep.relative_to(R).as_posix(),'energy_sha256':sha(ep),'fd_csv':fp.relative_to(R).as_posix(),'fd_sha256':sha(fp)},'stages':stages,'scope':'direct whole-model saved energy and independent RP work quadrature; no local RF2 attribution'})
with (P/'main_global_energy_check.json').open('x',encoding='utf-8') as f:json.dump({'records':out,'no_new_ODB_or_solver_call':True},f,indent=2,allow_nan=False)
print(json.dumps({'finals':[{r['candidate_id']:r['stages'][-1]} for r in out]}))
