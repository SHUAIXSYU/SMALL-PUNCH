"""Actual FE / sealed forecasts / finite-pool outcomes. Not experimental DIC."""
from analyze_holdout import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
C=['#0072B2','#D55E00','#009E73','#CC79A7'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'white','axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15})

def figures(data,out,figdir):
 D=Path(data);O=Path(out);Z=Path(figdir);Z.mkdir(exist_ok=True,parents=True);F=rows(D/'fd_actual_241.csv');P=rows(D/'frozen_FD_241.csv');u=np.array([float(x['u_mm']) for x in F]);ids=[r['candidate_id'] for r in rows(D/'jobs.csv')];labels=[i.replace('H4_HO_','') for i in ids];results=rows(O/'results.csv');sc=rows(O/'compatibility_scenarios.csv');q=rows(D/'target_Q_981.csv');eps=np.array([float(x['true_total_strain']) for x in q]);Q={i:np.array([float(x[i+'_MPa']) for x in q]) for i in ['I06_L2']+ids};fc=np.array([float(x['I06_L2_N']) for x in F])
 def save(f,name):f.savefig(Z/name,dpi=300,bbox_inches='tight');plt.close(f)
 f,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
 ax[0].plot(u,fc,color='k',lw=1.5,label='I06 actual FE')
 for i,l,c in zip(ids,labels,C):
  a=np.array([float(x[i+'_N']) for x in F]);p=np.array([float(x[i+'_predicted_N']) for x in P]);ax[0].plot(u,a,color=c,lw=1.7,label=l);ax[0].plot(u,p,color=c,ls='--',lw=1);ax[1].plot(u,a-p,color=c,lw=1.3,label=l)
 ax[0].set(ylabel='Punch force (N)',title='Solid: actual held-out FE; dashed: sealed forecast');ax[0].legend(ncol=3,fontsize=8);ax[1].set(ylabel='Actual minus forecast (N)',xlabel='Punch displacement (mm)',xlim=(0,1.2));ax[1].axhline(0,color='k',lw=.6);f.tight_layout();save(f,'01_actual_FD_and_frozen_forecasts.png')
 f,ax=plt.subplots(1,2,figsize=(10,4));x=np.arange(4)
 av=[float(r['actual_g_minus_I06_um']) for r in results];pv=[float(r['predicted_g_minus_I06_um']) for r in results];ax[0].bar(x-.18,av,width=.36,color=C,label='Actual FE');ax[0].bar(x+.18,pv,width=.36,color='white',edgecolor=C,hatch='//',label='Sealed forecast');ax[0].axhline(1,color='gray',ls=':');ax[0].axhline(-1,color='gray',ls=':');ax[0].set(xticks=x,xticklabels=labels,ylabel='g minus I06 (um)',title='Frozen reference radii .5/1 mm, punch1.2 mm');ax[0].legend(fontsize=8);ax[1].bar(x,[float(r['g_prediction_error_um']) for r in results],color=C);ax[1].set(xticks=x,xticklabels=labels,ylabel='Actual minus predicted g (um)',title='Forecast error, not measurement noise')
 for a in ax:a.tick_params(axis='x',rotation=20)
 f.tight_layout();save(f,'02_primary_shape_actual_vs_forecast.png')
 f,ax=plt.subplots(1,2,figsize=(10,4.3),sharey=True);allids=['I06_L2']+ids;from matplotlib.colors import ListedColormap,BoundaryNorm
 cmap=ListedColormap(['#dddddd','#ffffff','#E69F00','#009E73']);norm=BoundaryNorm([-1.5,-.5,.5,1.5,2.5],cmap.N)
 for a,fam in zip(ax,['fixed','free']):
  arr=np.zeros((5,4))
  for j,tf in enumerate([2,4.5,5,10]):
   z=next(r for r in sc if r['family']==fam and float(r['tau_F_N'])==tf and float(r['tau_g_um'])==1);fdids=z['FD_ids'].split(';');joint=z['joint_ids'].split(';')
   for k,i in enumerate(allids):arr[k,j]=-1 if fam=='fixed' and i.endswith('_FREE') else (2 if i in joint else (1 if i in fdids else 0))
  a.imshow(arr,cmap=cmap,norm=norm,aspect='auto');a.grid(False);a.set(xticks=range(4),xticklabels=[2,4.5,5,10],yticks=range(5),yticklabels=['I06']+labels,xlabel='FD tolerance (N)',title=f'{fam.capitalize()}-high pool, shape tolerance1 um')
  for (i,j),v in np.ndenumerate(arr):a.text(j,i,{-1:'n/a',0:'out',1:'FD only',2:'joint'}[int(v)],ha='center',va='center',fontsize=8)
 f.suptitle('Actual memberships: green joint; orange excluded by shape; gray outside family');f.tight_layout();save(f,'03_fixed_free_compatibility_membership.png')
 f,ax=plt.subplots(2,2,figsize=(10,7))
 for j,tf in enumerate([5.,10.]):
  z=next(r for r in sc if r['family']=='free' and float(r['tau_F_N'])==tf and float(r['tau_g_um'])==1);before=float(z['FD_D_Q_MPa']);ax[0,j].bar([0,1],[before,0],color=[C[0],C[1]]);ax[0,j].text(1,.15,'1Q*',ha='center');ax[0,j].set(xticks=[0,1],xticklabels=['FD only','FD + shape'],ylabel='Finite target diameter (MPa)',title=f'Free-high pool: FD bound{tf:g} N');qq=np.array([Q[i] for i in z['FD_ids'].split(';')]);ax[1,j].fill_between(eps,qq.min(axis=0),qq.max(axis=0),color=C[0],alpha=.25,label='FD finite envelope');ax[1,j].plot(eps,Q['I06_L2'],color=C[1],lw=1.7,label='Joint pool: I06 only');ax[1,j].set(xlabel='True total strain',ylabel='True stress (MPa)',xlim=(.002,.1));ax[1,j].legend(fontsize=8)
 f.suptitle('*One sampled target has geometric diameter0; not proof of unique material');f.tight_layout();save(f,'04_target_diameter_and_envelopes.png')
 robust=rows(O/'robustness_pool_scenarios.csv');f,ax=plt.subplots(1,2,figsize=(12,4.4));signal=np.abs(av);ax[0].bar(x,signal,color=C);ax[0].axhline(1,color='k',ls='--',label='Primary feature tolerance1 um');ax[0].axhline(.10498610224004779,color='gray',ls=':',label='Historical observed dt drift*');ax[0].set(xticks=x,xticklabels=labels,ylabel='Absolute g residual (um)',title='*Not a new-endpoint error bound');ax[0].tick_params(axis='x',rotation=20);ax[0].legend(fontsize=8)
 settings=[('shared_uniform_radius_shift',.01,'Shared radius10um'),('independent_specimen_point_position',.001,'Independent radius1um'),('shared_backward_phase',.005,'Shared phase5um'),('independent_specimen_backward_phase',.005,'Independent phase5um')]
 for j,tf in enumerate([5.,10.]):
  vals=[]
  for mode,bound,l in settings:
   z=next(r for r in robust if r['family']=='free' and float(r['tau_F_N'])==tf and float(r['tau_g_um'])==1 and r['error_scenario']==mode and float(r['error_bound_mm'])==bound);vals.append(float(z['max_simultaneous_geom_MPa']))
  ax[1].bar(np.arange(4)+(j-.5)*.35,vals,width=.35,color=C[j],label=f'FD {tf:g}N')
 ax[1].set(xticks=range(4),xticklabels=[s[2] for s in settings],ylabel='Max simultaneous finite D_Q (MPa)',title='Hypothetical operator-error scenarios, not device accuracy');ax[1].tick_params(axis='x',rotation=25);ax[1].legend(fontsize=8);f.tight_layout();save(f,'05_signal_numerical_and_measurement_limits.png')
 f,ax=plt.subplots(1,2,figsize=(12,4.4));labels2=['Development5N','Development10N','Holdout5N','Holdout10N'];before=[8.739697717005779,11.030806192776833,4.047861317839262,9.155854316911022];after=[3.9891223749867173,3.9891223749867173,0,0];xx=np.arange(4);ax[0].bar(xx-.18,before,.36,color=C[0],label='FD only');ax[0].bar(xx+.18,after,.36,color=C[1],label='FD + shape,1um');ax[0].set(xticks=xx,xticklabels=labels2,ylabel='Finite geometric D_Q (MPa)',title='Compare within each pool; datasets differ');ax[0].tick_params(axis='x',rotation=20);ax[0].legend(fontsize=8)
 for j in [2,3]:ax[0].text(j+.18,.2,'1Q*',ha='center',fontsize=8)
 ix=ids.index('H4_HO_M_FIXED');jx=ids.index('H4_HO_P_FREE');ax[1].bar([0,1],[av[ix],av[jx]],color=[C[0],C[3]]);ax[1].axhline(1,color='gray',ls=':');ax[1].set(xticks=[0,1],xticklabels=['M_FIXED','P_FREE'],ylabel='Actual g minus I06 (um)',title='Counterexample: pair dQ9.156MPa, shape gap0.004um');ax[1].text(.5,.45,'Both excluded by I06 shape constraint;\nnot globally pairwise distinguishable',ha='center',transform=ax[1].transAxes,fontsize=9);f.suptitle('Independent same-model support; one reference / finite pool, not external validation');f.tight_layout();save(f,'06_development_holdout_scope_and_counterexample.png')
 print('6 scientific figures generated')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--figures',required=True);a=p.parse_args();figures(a.data,a.out,a.figures)
