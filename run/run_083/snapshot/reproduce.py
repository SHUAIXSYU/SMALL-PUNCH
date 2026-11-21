"""Reconstruct R18 FE-only scientific metrics and figures from reviewed CSV.
No raw ODB, experimental data, fit, optimization, or solver invocation.
"""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from frozen_comparator import evaluate
ROOT=Path(__file__).resolve().parent
COL={0.:'#333333',-1.:'#0072B2',-1.2:'#D55E00'}
NAME={0.:'No added S3',-1.:'Opposed equal',-1.2:'Opposed 1.2'}
def rows(p):
 with p.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def main():
 j=rows(ROOT/'jobs.csv');fd=rows(ROOT/'fd_predictions_241.csv');qt=rows(ROOT/'target_Q_981.csv');u=np.array([float(r['u_mm']) for r in fd]);eps=np.array([float(r['true_total_strain']) for r in qt]);center=np.array([float(r['I06_L2_N']) for r in fd]);actual={r['candidate_id']:np.array([float(x[r['candidate_id']+'_actual_N']) for x in fd]) for r in j};primary={r['candidate_id']:np.array([float(x[r['candidate_id']+'_primary_prediction_N']) for x in fd]) for r in j};Q={k:np.array([float(x[k+'_MPa']) for x in qt]) for k in ['I06_L2',*actual]};pars={r['candidate_id']:{'m2':float(r['m2']),'variant':r['variant']} for r in j};result=evaluate(actual,center,Q,pars,primary,u);expected=json.loads((ROOT/'metrics.json').read_text(encoding='utf8'))['frozen_evaluation'];checks=0
 for k in actual:
  for metric in ['response','primary_prediction_error']:
   for key in ['RMS_N','max_abs_N','max_at_mm']:
    assert abs(result['candidates'][k][metric][key]-expected['candidates'][k][metric][key])<1e-10;checks+=1
 for a,b in zip(result['scenarios'],expected['scenarios']):
  for fam in ['fixed','free']:
   assert a[fam]['members']==b[fam]['members'];checks+=1
   if a[fam]['D_Q_MPa'] is not None:assert abs(a[fam]['D_Q_MPa']-b[fam]['D_Q_MPa'])<1e-10;checks+=1
  assert abs(a['D_Q_gain_MPa']-b['D_Q_gain_MPa'])<1e-10;checks+=1
 for a,b in zip(result['parity'],expected['parity']):assert abs(a['even_over_odd']-b['even_over_odd'])<1e-10;checks+=1
 out=ROOT/'reproduced';out.mkdir(exist_ok=True);(out/'metrics.json').write_bytes(json.dumps(result,indent=2).encode('utf8'))
 plt.rcParams.update({'font.size':9,'figure.facecolor':'white','savefig.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
 def end(fig,name):fig.tight_layout();fig.savefig(out/name,dpi=300);plt.close(fig)
 fig,axs=plt.subplots(2,3,figsize=(13,7),sharex=True,sharey=True)
 for ax,m in zip(axs.flat,[-3,-2,-1.5,1.5,2,3]):
  ax.plot(u,center,color='.6',lw=2,label='I06 reference FE')
  for r in j:
   if float(r['m2'])!=m:continue
   k=r['candidate_id'];ratio=float(r['ratio']);ax.plot(u,actual[k],color=COL[ratio],label=NAME[ratio])
  ax.set(title=f'c2/a = {m:+g}',xlabel='Punch displacement (mm)',ylabel='Punch force (N)',xlim=(0,1.2))
 axs[0,0].legend(fontsize=7);end(fig,'01_actual_FE_curves.png')
 fig,axs=plt.subplots(2,3,figsize=(13,7),sharex=True)
 for ax,m in zip(axs.flat,[-3,-2,-1.5,1.5,2,3]):
  for r in j:
   if float(r['m2'])!=m:continue
   k=r['candidate_id'];ratio=float(r['ratio']);ax.plot(u,actual[k]-center,color=COL[ratio],label=NAME[ratio]+' actual FE');ax.plot(u,primary[k]-center,color=COL[ratio],ls='--',lw=.9,label=NAME[ratio]+' frozen prediction')
  ax.axhline(0,color='.7',lw=.6);ax.set(title=f'c2/a = {m:+g}',xlabel='Displacement (mm)',ylabel='Force difference from I06 (N)',xlim=(0,1.2))
 axs[0,0].legend(fontsize=6,ncol=2);end(fig,'02_actual_vs_frozen_predictions.png')
 fig,axs=plt.subplots(1,2,figsize=(10,4))
 for ax,sign in zip(axs,[-1,1]):
  for ratio in [0.,-1.,-1.2]:
   rr=sorted([r for r in j if float(r['ratio'])==ratio and np.sign(float(r['m2']))==sign],key=lambda r:abs(float(r['m2'])));ax.plot([abs(float(r['m2'])) for r in rr],[float(r['actual_RMS_N']) for r in rr],'o-',color=COL[ratio],label=NAME[ratio]);ax.plot([abs(float(r['m2'])) for r in rr],[float(r['primary_predicted_RMS_N']) for r in rr],'--',color=COL[ratio],lw=.8)
  ax.set(title='Negative low perturbation' if sign<0 else 'Positive low perturbation',xlabel='Absolute c2 / a',ylabel='Full-window RMS from I06 (N)',xticks=[1.5,2,3]);ax.legend(fontsize=7)
 fig.suptitle('Solid: actual FE; dashed: frozen primary prediction');end(fig,'03_compensation_by_amplitude.png')
 fig,axs=plt.subplots(1,2,figsize=(10,4));cm=plt.get_cmap('tab10')
 for n,m in enumerate([-3,-2,-1.5,1.5,2,3]):
  k=next(r['candidate_id'] for r in j if float(r['m2'])==m and float(r['ratio'])==0);axs[0].plot(eps,Q[k],color=cm(n),label=f'c2/a={m:+g}, all 3 c3');axs[1].plot(eps,Q[k]-Q['I06_L2'],color=cm(n))
 axs[0].plot(eps,Q['I06_L2'],'k--',label='I06');axs[0].set(xlabel='True total strain',ylabel='Actual input true stress (MPa)',xlim=(.002,.1));axs[0].legend(fontsize=6);axs[1].set(xlabel='True total strain',ylabel='Target stress difference from I06 (MPa)',xlim=(.002,.1));end(fig,'04_material_targets.png')
 fig,ax=plt.subplots(figsize=(8,7));mat=np.array([[float(r['actual_RMS_N'])<=t for t in [2,5,10]] for r in j]);ax.imshow(mat,cmap=matplotlib.colors.ListedColormap(['#E8E8E8','#56B4E9']),aspect='auto',vmin=0,vmax=1)
 for i,r in enumerate(j):
  for c,t in enumerate([2,5,10]):ax.text(c,i,('IN' if mat[i,c] else 'OUT')+f" ({t-float(r['actual_RMS_N']):+.2f} N)",ha='center',va='center',fontsize=7)
 ax.set(xticks=range(3),xticklabels=['tau = 2 N','tau = 5 N','tau = 10 N'],yticks=range(18),yticklabels=[r['candidate_id'] for r in j],title='Actual reference-relative compatibility; signed margins shown');end(fig,'05_compatibility_membership.png')
 fig,axs=plt.subplots(1,3,figsize=(13,4))
 for ax,t in zip(axs,[2,5,10]):
  s=next(z for z in result['scenarios'] if z['tau_N']==t and z['buffer_N']==0)
  for fam,c,lab in [('free','#56B4E9','Free high family'),('fixed','#666666','No added S3 family')]:
   ax.fill_between(eps,s[fam]['envelope_min_MPa'],s[fam]['envelope_max_MPa'],color=c,alpha=.4,label=lab);ax.plot(eps,s[fam]['envelope_min_MPa'],color=c,lw=.7);ax.plot(eps,s[fam]['envelope_max_MPa'],color=c,lw=.7)
  ax.set(title=f'tau = {t} N; fixed n={len(s["fixed"]["members"])} / free n={len(s["free"]["members"])}',xlabel='True total strain',ylabel='Target true stress (MPa)',xlim=(.002,.1));ax.legend(fontsize=7)
 end(fig,'06_finite_target_envelopes.png')
 fig,axs=plt.subplots(1,3,figsize=(13,4))
 for var,c in [('fixed_high',COL[0.]),('opposed_equal',COL[-1.]),('opposed_1p2',COL[-1.2])]:
  rr=[x for x in result['parity'] if x['variant']==var];axs[0].plot([r['abs_m2'] for r in rr],[r['even_over_odd'] for r in rr],'o-',color=c,label=var)
 axs[0].axhline(.25,color='black',ls='--',lw=.7);axs[0].set(xlabel='Absolute c2 / a',ylabel='Even / odd RMS ratio');axs[0].legend(fontsize=6)
 for t,c in [(5,'#0072B2'),(10,'#D55E00')]:
  rr=[z for z in result['scenarios'] if z['tau_N']==t];axs[1].plot([r['buffer_N'] for r in rr],[r['D_Q_gain_MPa'] for r in rr],'o-',color=c,label=f'tau={t} N')
 axs[1].set(xlabel='Exploratory inward buffer (N)',ylabel='Free minus fixed target diameter (MPa)');axs[1].legend(fontsize=7)
 for r in j:axs[2].scatter(abs(float(r['m2'])),float(r['primary_error_ratio']),color=COL[float(r['ratio'])],marker='o' if float(r['m2'])>0 else 'x')
 for th in [.25,.5,1]:axs[2].axhline(th,color='.5',ls=':',lw=.6)
 axs[2].set(xlabel='Absolute c2 / a',ylabel='Primary curve error / predicted response RMS');end(fig,'07_nonlinearity_and_numerical_margin.png')
 fig,axs=plt.subplots(1,3,figsize=(13,4));ix=np.arange(18)
 axs[0].bar(ix,[float(r['max_saved_PEEQ']) for r in j],color='#0072B2');axs[0].axhline(.9,color='red',ls='--',lw=.8);axs[0].set(xlabel='R18 candidate index',ylabel='Maximum saved PEEQ',xticks=[0,5,11,17],xticklabels=[1,6,12,18],ylim=(0,1))
 axs[1].bar(ix,[float(r['actual_max_abs_N']) for r in j],color='#D55E00');axs[1].set(xlabel='R18 candidate index',ylabel='Max absolute force difference from I06 (N)',xticks=[0,5,11,17],xticklabels=[1,6,12,18])
 contacts=rows(ROOT/'contact_events.csv')
 for i,r in enumerate(j):axs[2].scatter([float(z['u_mm']) for z in contacts if z['candidate_id']==r['candidate_id']],[i]*sum(z['candidate_id']==r['candidate_id'] for z in contacts),s=2,color=COL[float(r['ratio'])])
 axs[2].set(xlabel='Actual saved displacement (mm)',ylabel='R18 candidate index',yticks=[0,5,11,17],yticklabels=[1,6,12,18],title='Positive-CPRESS topology changes');end(fig,'08_peeq_peaks_and_contact.png')
 print(f'{checks} metric/membership/target/parity checks reproduced; 8 figures generated, no new FE')
if __name__=='__main__':main()
