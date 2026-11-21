"""Reproducible H4 scientific figures from FE-only CSV. Not new FE or DIC."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_h4 import rows,load,fid
C=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white','axes.grid':True,'grid.alpha':.15,'savefig.dpi':300,'font.family':'DejaVu Sans'})
def figures(data,analysis,out):
 data=Path(data);analysis=Path(analysis);out=Path(out);out.mkdir(exist_ok=True,parents=True)
 def save(f,name):f.savefig(out/name,dpi=300,bbox_inches='tight');plt.close(f)
 profiles=rows(data/'bottom_profiles.csv');shape=rows(data/'shape_features.csv');metric=load(analysis/'metrics.json');sc=rows(analysis/'compatibility_scenarios.csv');pairs=rows(analysis/'priority_pair_signals.csv');best=metric['exploratory_best']['feature'];base=metric['baseline_feature']
 def prof(case,u):
  rr=sorted([r for r in profiles if r['case']==case and float(r['target_u_mm'])==u],key=lambda r:float(r['r_ref_mm']));return np.array([float(r['r_ref_mm']) for r in rr]),np.array([float(r['w_mm']) for r in rr])
 f,axs=plt.subplots(2,2,figsize=(10,7),sharex=True)
 for ax,u in zip(axs.flat,[.3,.6,.9,1.2]):
  x,w0=prof('I06_L2',u)
  for i,col in zip(['R18_02','R18_14','R18_05','R18_15','R18_17'],C):
   xx,w=prof(i,u);ax.plot(xx,1000*(w-w0),label=i,color=col,lw=1.5)
  ax.set(xlim=(0,2),title=f'Punch u = {u:g} mm',ylabel='Bottom w - I06 (um)');ax.axhline(0,color='k',lw=.5)
 axs[1,0].set_xlabel('Reference bottom radius (mm)');axs[1,1].set_xlabel('Reference bottom radius (mm)');axs[0,0].legend(ncol=2,fontsize=8);f.suptitle('Actual existing FE: bottom shapes at exactly bracketed punch stages');f.tight_layout();save(f,'01_bottom_profile_differences.png')
 f,axs=plt.subplots(1,3,figsize=(12,3.7),sharey=True)
 for ax,(i,j) in zip(axs,[('R18_02','R18_14'),('R18_05','R18_15'),('R18_02','R18_17')]):
  for k,(r1,r2) in enumerate([(.5,1.5),(.5,1),(1,1.5)]):
   rr=[r for r in pairs if r['case_a']==i and r['case_b']==j and r['feature'].startswith(f'r{r1:g}_r{r2:g}_')];rr=sorted(rr,key=lambda r:float(r['feature'].split('_u')[1]));ax.plot([float(r['feature'].split('_u')[1]) for r in rr],[float(r['pair_shape_difference_um']) for r in rr],marker='o',color=C[k],label=f'w({r1:g})-w({r2:g})')
  ax.set(title=f'{i} / {j}',xlabel='Punch displacement (mm)',xticks=[.3,.6,.9,1.2]);ax.axhline(1,color='gray',ls=':',lw=1)
 axs[0].set_ylabel('Direct pair feature difference (um)');axs[0].legend(fontsize=8);f.suptitle('Pair shape differences are distinct from each-candidate-to-I06 residuals');f.tight_layout();save(f,'02_priority_pair_shape_signals.png')
 keys=[x['feature'] for x in metric['ranked_features']];tws=[.1,.25,.5,1.];f,axs=plt.subplots(1,2,figsize=(10,6),sharey=True)
 for ax,tf in zip(axs,[5.,10.]):
  imdata=np.zeros((12,4));count=np.zeros((12,4),int)
  for a,k in enumerate(keys):
   for b,tw in enumerate(tws):
    x=next(r for r in sc if r['observation']=='single_'+k and r['family']=='free' and float(r['tau_F_N'])==tf and float(r['tau_w_feature_um'])==tw);imdata[a,b]=float(x['reduction_percent']);count[a,b]=int(x['after_Q_count'])
  im=ax.imshow(imdata,vmin=0,vmax=100,cmap='cividis',aspect='auto')
  for a in range(12):
   for b in range(4):ax.text(b,a,'1Q*' if count[a,b]==1 else f'{imdata[a,b]:.0f}%',ha='center',va='center',fontsize=8,color='white' if imdata[a,b]<40 else 'black')
  ax.set(title=f'FD tolerance = {tf:g} N',xticks=range(4),xticklabels=tws,yticks=range(12),yticklabels=keys,xlabel='Hypothetical derived-feature tolerance (um)');ax.grid(False)
 f.colorbar(im,ax=list(axs),label='Finite-pool geometric diameter reduction (%)',shrink=.7,pad=.03);f.suptitle('12 bounded development screens; *1Q is one sampled target, not uniqueness');save(f,'03_finite_target_contraction_screen.png')
 q=rows(data/'target_Q_981.csv');eps=np.array([float(x['true_total_strain']) for x in q]);ids=['I06_L2']+[x['candidate_id'] for x in rows(data/'jobs.csv')];Q={i:np.array([float(x[i+'_MPa']) for x in q]) for i in ids}
 f,axs=plt.subplots(1,2,figsize=(10,4),sharey=True)
 for ax,tf in zip(axs,[5.,10.]):
  raw=next(r for r in sc if r['observation']=='FD_only' and r['family']=='free' and float(r['tau_F_N'])==tf);joint=next(r for r in sc if r['observation']=='single_'+best and r['family']=='free' and float(r['tau_F_N'])==tf and float(r['tau_w_feature_um'])==1.)
  for rec,col,label in [(raw,C[0],'Full FD only'),(joint,C[1],'+ selected shape, tolerance 1 um')]:
   qq=np.array([Q[i] for i in rec['retained_ids'].split(';')]);ax.fill_between(eps,qq.min(axis=0),qq.max(axis=0),color=col,alpha=.25,label=label);ax.plot(eps,qq.max(axis=0),color=col,lw=1);ax.plot(eps,qq.min(axis=0),color=col,lw=1)
  ax.plot(eps,Q['I06_L2'],color='k',lw=1,label='I06 target');ax.set(title=f'FD tolerance = {tf:g} N',xlabel='True total strain',xlim=(.002,.1));ax.legend(fontsize=8)
 axs[0].set_ylabel('Target true stress (MPa)');f.suptitle('Actual deployed material targets: finite-pool envelopes, not confidence bounds');f.tight_layout();save(f,'04_target_envelope_contraction.png')
 f,axs=plt.subplots(1,2,figsize=(10,4),sharey=True)
 for ax,tf in zip(axs,[5.,10.]):
  for lab,col,label,style in [('baseline_single',C[2],'Old .5/1.5mm at1.2','-'),('single_'+best,C[0],'Selected .5/1mm at1.2','-'),('selected_pair_two_stage',C[1],'Selected at .6 and1.2','--')]:
   rr=sorted([r for r in sc if r['observation']==lab and r['family']=='free' and float(r['tau_F_N'])==tf],key=lambda x:float(x['tau_w_feature_um']));y=[float(r['after_D_Q_MPa']) if r['after_D_Q_MPa'] else 0 for r in rr];ax.plot(tws,y,label=label,color=col,ls=style,marker='o')
   if lab=='single_'+best:
    for xx,yy,r in zip(tws,y,rr):
     if r['after_status']=='SINGLE_TARGET_NOT_UNIQUENESS':ax.annotate('1Q*',(xx,yy),xytext=(0,6),textcoords='offset points',fontsize=8,ha='center')
  ax.set(title=f'FD tolerance = {tf:g} N',xlabel='Hypothetical feature bound (um)',xticks=tws);ax.legend(fontsize=8)
 axs[0].set_ylabel('Finite-pool target diameter (MPa)');f.suptitle('One vs two features; *single sampled target shown at geometric diameter zero');f.tight_layout();save(f,'05_one_vs_two_shape_features.png')
 num=rows(analysis/'numerical_shape_changes.csv');rad=rows(analysis/'radial_location_scenarios.csv');tim=rows(analysis/'synchronization_scenarios.csv');primary_num=[r for r in num if r['feature']==best];ps=[r for r in pairs if r['feature']==best]
 f,axs=plt.subplots(1,2,figsize=(11,4))
 values=[float(r['abs_change_um']) for r in primary_num]+[float(r['pair_shape_difference_um']) for r in ps];labs=['I06 dt','B4_01 dt','B4_02 dt','02/14 pair','05/15 pair','02/17 pair'];axs[0].bar(range(6),values,color=[C[2]]*3+[C[0]]*3);axs[0].set(xticks=range(6),xticklabels=labs,ylabel='Shape-feature difference (um)',title='Observed FE changes: not endpoint error bounds');axs[0].tick_params(axis='x',rotation=30)
 rval=next(float(r['sum_endpoint_linear_interpolation_deviation_um']) for r in rad if r['case']=='I06_L2' and r['feature']==best and float(r['hypothetical_radius_error_mm'])==.01);tval=next(float(r['linearized_feature_error_um']) for r in tim if r['case']=='I06_L2' and r['feature']==best);vals=[max(float(r['abs_change_um']) for r in primary_num),tval,rval];axs[1].bar(range(3),vals,color=C[:3]);axs[1].set(xticks=range(3),xticklabels=['Observed dt change','1 um punch timing*','10 um radius*'],ylabel='Feature change (um, log scale)',yscale='log',title='*Hypothetical metrology scenarios, not device accuracy');axs[1].tick_params(axis='x',rotation=20);f.tight_layout();save(f,'06_numerical_and_metrology_scales.png')
 stress=rows(analysis/'boundary_sensitivity.csv');f,axs=plt.subplots(1,2,figsize=(10,4),sharey=True)
 for ax,tf in zip(axs,[5.,10.]):
  rr=sorted([r for r in stress if float(r['tau_F_N'])==tf and float(r['nominal_feature_tolerance_um'])==1],key=lambda r:int(r['direction']));ax.plot([float(r['diagnostic_effective_tolerance_um']) for r in rr],[float(r['diameter_geometric_MPa']) for r in rr],marker='o',color=C[0]);ax.axvline(1,color=C[1],ls='--',label='Nominal 1 um');ax.set(xlabel='Diagnostic effective feature bound (um)',title=f'FD tolerance = {tf:g} N');ax.legend(fontsize=8)
 axs[0].set_ylabel('Finite target diameter (MPa)');f.suptitle('Boundary stress-test: nominal bound +/- observed 0.105 um; not a guaranteed error model');f.tight_layout();save(f,'07_boundary_sensitivity.png')
 print('7 scientific figures written')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--analysis',required=True);p.add_argument('--out',required=True);a=p.parse_args();figures(a.data,a.analysis,a.out)
