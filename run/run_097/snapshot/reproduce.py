"""Reproduce reviewed FE-only paired increment comparisons; no solver dependency."""
from pathlib import Path
import argparse,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=Path(__file__).parent/'data/fd_four_curves.csv');parser.add_argument('--output-dir',type=Path,default=Path(__file__).parent/'figures');args=parser.parse_args()
out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
z=np.genfromtxt(args.data,delimiter=',',names=True);u=z['u_mm'];assert len(u)==241 and np.max(abs(u-np.arange(241)*.005))<1e-12
cols=['I06_coarse','MFREE_coarse','I06_fine','MFREE_fine'];f={k:z[k] for k in cols};colors=['#0072B2','#D55E00','#0072B2','#D55E00'];styles=['--','--','-','-']
rms=lambda v:float(np.sqrt(np.mean(v*v)))
co=f['MFREE_coarse']-f['I06_coarse'];fi=f['MFREE_fine']-f['I06_fine'];change=fi-co
di=f['I06_fine']-f['I06_coarse'];dm=f['MFREE_fine']-f['MFREE_coarse']
centers=[.535,.615,.705,.815,.950,1.140];mask=np.any(np.abs(u[:,None]-np.array(centers))<=.020+1e-12,axis=1)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
def finish(fig,name):fig.tight_layout();fig.savefig(out/name,dpi=300);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.2,4.2))
for k,c,s in zip(cols,colors,styles):ax.plot(u,f[k],color=c,ls=s,lw=1.5,label=k.replace('_',' '))
ax.set(xlabel='Punch displacement (mm)',ylabel='Punch force (N)',xlim=(0,1.2));ax.legend(frameon=False,ncol=2);finish(fig,'01_four_curves.png')
fig,ax=plt.subplots(figsize=(7.2,4.2));ax.plot(u,co,'--',color='#D55E00',label='Coarse pair');ax.plot(u,fi,color='#0072B2',label='Fine pair')
for c in centers:ax.axvspan(c-.02,c+.02,color='gray',alpha=.12)
ax.axhline(0,color='gray',lw=.6);ax.set(xlabel='Punch displacement (mm)',ylabel='M_FREE - I06 force (N)',xlim=(0,1.2));ax.legend(frameon=False);finish(fig,'02_pair_residuals.png')
fig,axs=plt.subplots(2,1,figsize=(7.2,6),sharex=True)
axs[0].plot(u,di,label='I06 fine - coarse',color='#0072B2');axs[0].plot(u,dm,label='M_FREE fine - coarse',color='#D55E00');axs[0].legend(frameon=False)
axs[1].plot(u,change,color='#009E73',label='Fine pair - coarse pair');axs[1].legend(frameon=False)
for ax in axs:ax.axhline(0,color='gray',lw=.6);ax.set(ylabel='Force change (N)',xlim=(0,1.2))
axs[-1].set_xlabel('Punch displacement (mm)');finish(fig,'03_numerical_changes.png')
fig,axs=plt.subplots(2,3,figsize=(10.5,6))
for ax,c in zip(axs.flat,centers):
 sel=abs(u-c)<=.02+1e-12;ax.plot(u[sel],co[sel],'o--',ms=3,color='#D55E00',label='Coarse pair');ax.plot(u[sel],fi[sel],'o-',ms=3,color='#0072B2',label='Fine pair');ax.set_title(f'{c:.3f} mm window');ax.set(xlabel='Displacement (mm)',ylabel='Pair difference (N)');ax.tick_params(axis='x',rotation=25)
axs.flat[0].legend(frameon=False,fontsize=8);finish(fig,'04_fixed_window_zoom.png')
scenarios=[]
for cap in [2.,5.,10.]:
 for rel in [.005,.01,.02]:
  scenarios.append({'absolute_N':cap,'relative':rel,'coarse_compatible':bool(3.945991204283632<=5 and rms(co)<=cap and rms(co)/rms(f['I06_coarse'])<=rel),'fine_compatible':bool(3.945991204283632<=5 and rms(fi)<=cap and rms(fi)/rms(f['I06_fine'])<=rel)})
result={'I06_RMS_N':rms(di),'MFREE_RMS_N':rms(dm),'coarse_pair_RMS_N':rms(co),'fine_pair_RMS_N':rms(fi),'pair_change_RMS_N':rms(change),'pair_change_max_N':float(np.max(abs(change))),'pair_change_max_u_mm':float(u[np.argmax(abs(change))]),'six_window_points':int(sum(mask)),'coarse_window_squared_fraction':float(sum(co[mask]**2)/sum(co**2)),'fine_window_squared_fraction':float(sum(fi[mask]**2)/sum(fi**2)),'scenarios':scenarios,'limitation':'One adjacent increment comparison is not a strict error bound; no smoothing or omission; synthetic two-material FE pair only.'}
(out/'recomputed_metrics.json').write_text(json.dumps(result,indent=2),encoding='utf8',newline='\n');print(json.dumps(result))
