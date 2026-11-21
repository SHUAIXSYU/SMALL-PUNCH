"""Reproduce B3 metrics using reviewed public FE-only CSV; no solver calls."""
from pathlib import Path
import json,csv
import numpy as np
from frozen_comparator import compare,KEYS
ROOT=Path(__file__).resolve().parent
def rows(path):
 with path.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def main():
 fd=rows(ROOT/'fd_levels_241.csv');q=rows(ROOT/'target_Q_981.csv');g=np.array([float(v['u_mm']) for v in fd]);old={k:np.array([float(v[k+'_L1_N']) for v in fd]) for k in KEYS};new={k:np.array([float(v[k+'_L2_N']) for v in fd]) for k in KEYS};target={k:np.array([float(v[k+'_MPa']) for v in q]) for k in KEYS}
 result=compare(old,new,g,target);expected=json.loads((ROOT/'metrics.json').read_text(encoding='utf8'))['frozen_evaluation'];checks=0
 for k in KEYS:
  for name in ['same_point_two_level_difference']+([] if k=='I06_REFINED' else ['L1_relative_same_level_I06','L2_relative_same_level_I06','change_of_relative_response']):
   for metric in ['RMS_N','max_abs_N','max_at_mm']:
    assert abs(result['per_point'][k][name][metric]-expected['per_point'][k][name][metric])<1e-11;checks+=1
  if k!='I06_REFINED':
   for a,b in zip(result['per_point'][k]['thresholds'],expected['per_point'][k]['thresholds']):assert (a['L1_inside'],a['L2_inside'],a['risk_flag'])==(b['L1_inside'],b['L2_inside'],b['risk_flag']);checks+=1
 for a,b in zip(result['available_same_level_candidate_pools'],expected['available_same_level_candidate_pools']):
  assert a['members']==b['members'];checks+=1
  if a['d_Q_diameter_MPa'] is not None:assert abs(a['d_Q_diameter_MPa']-b['d_Q_diameter_MPa'])<1e-11;checks+=1
 assert abs(result['direct_joint_pair']['target_d_Q_MPa']-expected['direct_joint_pair']['target_d_Q_MPa'])<1e-11;checks+=1
 out=ROOT/'reproduced';out.mkdir(exist_ok=True);(out/'metrics.json').write_bytes(json.dumps(result,indent=2).encode('utf8'))
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,4))
 for k,c in [('B4_01','#0072B2'),('B4_02','#D55E00')]:
  ax.plot(g,old[k]-old['I06_REFINED'],'--',color=c,label=k+' L1');ax.plot(g,new[k]-new['I06_REFINED'],color=c,label=k+' L2')
 ax.set(xlabel='Punch displacement (mm)',ylabel='Force difference from same-level I06 (N)',xlim=(0,1.2));ax.legend();fig.tight_layout();fig.savefig(out/'matched_center_residuals.png',dpi=300);plt.close(fig)
 print(f'{checks} independent public-data metric, membership and target checks passed; no new FE')
if __name__=='__main__':main()
