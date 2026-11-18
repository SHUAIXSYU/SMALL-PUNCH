"""Planned point positions, clearly separated from actual FE observations."""
from pathlib import Path
import json,os
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_056/artifacts/private';os.environ['MPLCONFIGDIR']=str(P/'mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 c=read(P/'prospective_design_contract.json');a=read(R/'run/run_055/artifacts/private/feature_arrays.json');xy=np.array([[np.log(a['targets'][i][0]/150)/np.log(1000/150),(a['targets'][i][1]-.02)/.48] for i in a['primary_ids']]);null=read(R/'run/run_049/artifacts/private/numerically_unscoreable_observations.json');planned=np.array([[p['x'],p['y']] for p in c['points']]);h=ConvexHull(xy)
 fig,axes=plt.subplots(1,2,figsize=(11.5,4.7))
 for ax in axes:
  ax.scatter(xy[:,0],xy[:,1],s=22,label='25 actual scoreable FE')
  for edge in h.simplices:ax.plot(xy[edge,0],xy[edge,1],color='grey',lw=.7)
  ax.scatter([x['x'] for x in null],[x['y'] for x in null],marker='x',s=42,color='grey',label='6 null scores (software completed)')
  ax.scatter(planned[:,0],planned[:,1],marker='+',s=95,color='red',label='4 planned only; NOT run')
  ax.scatter([.24],[.16],marker='*',s=100,color='black',label='Existing I06 center');ax.set(xlabel='Normalized log-yield coordinate x',ylabel='Normalized hardening coordinate y');ax.grid(alpha=.2)
 axes[0].set(xlim=(-.01,1.01),ylim=(-.01,1.01),title='Finite and numerically filtered coverage');axes[0].legend(fontsize=7)
 axes[1].set(xlim=(.14,.31),ylim=(.11,.22),title='Prospective local design; one hull extrapolation')
 for point,label,offset in zip(c['points'],['sigma -','sigma +','n -','n +'],[(-12,-15),(5,-15),(5,-3),(5,3)]):axes[1].annotate(label,(point['x'],point['y']),xytext=offset,textcoords='offset points',fontsize=9)
 fig.tight_layout();fig.savefig(P/'coverage_and_prospective_design.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
