"""Reproduce the published B4 comparison from actual FE-only CSV; no fitting."""
from pathlib import Path
import csv,json
import numpy as np
from frozen_comparator import evaluate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
def rows(p):
 with p.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def main():
 fd=rows(ROOT/'fd_and_predictions_241.csv');q=rows(ROOT/'target_Q_981.csv');u=np.array([float(v['u_mm']) for v in fd]);center=np.array([float(v['I06_REFINED_N']) for v in fd]);zero={k:np.array([float(v[k+'_N']) for v in fd]) for k in ['B2_S2_P','B2_S2_M']};actual={k:np.array([float(v[k+'_N']) for v in fd]) for k in ['B4_01','B4_02','B4_03','B4_04']};pred={k:np.array([float(v[k+'_linear_prediction_N']) for v in fd]) for k in actual};targets={k:np.array([float(v[k+'_MPa']) for v in q]) for k in ['I06_REFINED',*zero,*actual]}
 result=evaluate(center,zero,actual,pred,targets,u);expected=json.loads((ROOT/'metrics.json').read_text(encoding='utf8'))['frozen_evaluation']['primary'];checks=0
 for k,v in result['candidates'].items():
  for metric in ['relative_reference','primary_prediction_error']:
   assert abs(v[metric]['RMS_N']-expected['candidates'][k][metric]['RMS_N'])<1e-11;checks+=1
  assert v['actual_tau_membership']==expected['candidates'][k]['actual_tau_membership'];checks+=1
 for v,e in zip(result['compatibility'],expected['compatibility']):
  for family in ['fixed','free']:
   assert v[family]['members']==e[family]['members'];checks+=1
   if v[family]['d_Q_diameter_MPa'] is not None:assert abs(v[family]['d_Q_diameter_MPa']-e[family]['d_Q_diameter_MPa'])<1e-11;checks+=1
 out=ROOT/'reproduced';out.mkdir(exist_ok=True);(out/'metrics.json').write_bytes(json.dumps(result,indent=2).encode('utf8'));fig,ax=plt.subplots(figsize=(7,4));ix=np.arange(4);ks=list(actual);ax.bar(ix-.2,[np.sqrt(np.mean((zero['B2_S2_P' if k in ['B4_01','B4_03'] else 'B2_S2_M']-center)**2)) for k in ks],.4,label='S2 only FE');ax.bar(ix+.2,[result['candidates'][k]['relative_reference']['RMS_N'] for k in ks],.4,label='B4 joint actual FE');ax.set(xticks=ix,xticklabels=ks,ylabel='RMS difference from I06 (N)');ax.legend();fig.tight_layout();fig.savefig(out/'compensation.png',dpi=300);plt.close(fig);print(f'{checks} RMS/membership/target-diameter checks reproduced from public FE CSV')
if __name__=='__main__':main()
