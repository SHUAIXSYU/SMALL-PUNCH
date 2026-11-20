"""Recompute B2 finite sensitivities from released FE-only files; no experiment."""
import csv,json
from pathlib import Path
import numpy as np
from b2_metrics import pair,target_Q,metrics,rms
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
def main():
 with (ROOT/'fd_241.csv').open(newline='',encoding='utf8') as f:rs=list(csv.DictReader(f))
 u=np.array([float(r['u_mm'])/1000 for r in rs]);base=np.array([float(r['I06_REFINED_N']) for r in rs]);out={};fig,axs=plt.subplots(2,2,figsize=(10,7))
 for j,ax in enumerate(axs.flat,1):
  lo=np.array([float(r[f'B2_S{j}_M_N']) for r in rs]);hi=np.array([float(r[f'B2_S{j}_P_N']) for r in rs]);z=pair(lo,hi,base,u,np.log(1.1));out[f'S{j}']=z['summary'];ax.plot(u*1000,lo-base,'--',label='minus');ax.plot(u*1000,hi-base,label='plus');ax.set(title=f'S{j}',xlabel='Punch displacement (mm)',ylabel='Difference from I06 (N)');ax.legend();ax.grid(alpha=.2)
 expected=json.loads((ROOT/'metrics.json').read_text(encoding='utf8'))['pairs']
 for k,v in out.items():
  for part in ['minus','plus','odd','even','paired_plus_minus']:assert abs(v[part]['RMS_N']-expected[k][part]['RMS_N'])<1e-10
 destination=ROOT/'reproduced';destination.mkdir(exist_ok=True)
 (destination/'recomputed_metrics.json').write_text(json.dumps(out,indent=2),encoding='utf8');fig.tight_layout();fig.savefig(destination/'response_differences.png',dpi=300);plt.close(fig)
 print('All five RMS metrics for four support intervals reproduced to 1e-10 N')
if __name__=='__main__':main()
