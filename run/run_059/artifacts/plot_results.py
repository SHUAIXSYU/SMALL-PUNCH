"""Static scientific figures of actual admitted responses and frozen predictions."""
from common import *
import os,numpy as np
os.environ['MPLCONFIGDIR']=str(P/'mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

def main():
 d=read(P/'verified_response_arrays.json');aa=read(P/'study_A_local_secants.json');bb=read(P/'study_B_frozen_parameter_recovery.json');u=np.array(d['grid_m'])*1000;F={k:np.array(v) for k,v in d['curves'].items()}
 out=P/'figures';out.mkdir(exist_ok=False)
 def finish(fig,name):fig.tight_layout();fig.savefig(out/name,dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,5))
 for cid,v in F.items():ax.plot(u,v,label=cid,lw=2 if cid=='I06' else 1.2)
 ax.set(xlabel='Punch displacement (mm)',ylabel='Force (N)',title='Actual FE: I06 and four prospective perturbations');ax.legend();ax.grid(alpha=.25);finish(fig,'FD_five_points.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4.6))
 for ax,cids,label in zip(axes,[['P01','P02'],['P03','P04']],['Yield-stress arms','Hardening-exponent arms']):
  for cid in cids:
   if cid in F:ax.plot(u,F[cid]-F['I06'],label=cid)
  ax.axhline(0,color='grey',lw=.7);ax.set(xlabel='Punch displacement (mm)',ylabel='Force change from I06 (N)',title=label);ax.legend();ax.grid(alpha=.25)
 finish(fig,'axis_response_differences.png')
 if aa['views']:
  vec=rows(P/'finite_difference_force_vectors.csv');fig,axes=plt.subplots(1,2,figsize=(11,4.5))
  sx=np.array([float(x['Sx_N_per_unit_x']) for x in vec]);sy=np.array([float(x['Sy_N_per_unit_y']) for x in vec]);axes[0].plot(u,sx,label='Sx');axes[0].plot(u,sy,label='Sy');axes[0].set(ylabel='N per normalized parameter unit',xlabel='Punch displacement (mm)',title='Actual central finite secants');axes[0].legend()
  axes[1].plot(u,sx/np.linalg.norm(sx),label='Sx / ||Sx||');axes[1].plot(u,sy/np.linalg.norm(sy),label='Sy / ||Sy||');axes[1].set(xlabel='Punch displacement (mm)',ylabel='Unit-vector components',title='Parameter response shape correlation');axes[1].legend()
  for ax in axes:ax.grid(alpha=.25)
  finish(fig,'normalized_parameter_direction_shapes.png')
  names=['two_loads','five_features','full241','early2_secondary','independent3_secondary'];metrics=aa['views'];fig,axes=plt.subplots(1,3,figsize=(14,4.8));xx=np.arange(len(names));sing=np.array([metrics[n]['singular_values'] for n in names])
  axes[0].bar(xx-.17,sing[:,0],.34,label='smax');axes[0].bar(xx+.17,sing[:,1],.34,label='smin');axes[0].set(yscale='log',ylabel='Singular value',title='Frozen physical row / parameter scaling');axes[0].legend()
  axes[1].bar(xx,[metrics[n]['condition_number'] or np.nan for n in names]);axes[1].axhline(20,color='red',ls='--',label='predeclared review flag');axes[1].set(ylabel='Condition number',title='Conditioning is not prediction accuracy');axes[1].legend(fontsize=8)
  axes[2].bar(xx,[metrics[n]['cosine'] for n in names]);axes[2].axhline(.98,color='red',ls='--');axes[2].set(ylim=(0,1.03),ylabel='Column cosine',title='Direction coupling')
  for ax in axes:ax.set_xticks(xx,[n.replace('_','\n') for n in names],rotation=30,fontsize=8);ax.grid(alpha=.2,axis='y')
  finish(fig,'Jacobian_conditioning_and_singular_values.png')
  fig,axes=plt.subplots(1,2,figsize=(10,4.5))
  for i,axis in enumerate(['x','y']):
   eta=[metrics[n]['axes'][axis]['even_odd_ratio'] for n in names];axes[i].bar(xx,eta);axes[i].axhline(.2,color='red',ls='--');axes[i].set_xticks(xx,[n.replace('_','\n') for n in names],rotation=30,fontsize=8);axes[i].set(ylabel='||even|| / ||odd||',title=f'{axis} finite-step asymmetry');axes[i].grid(alpha=.2,axis='y')
  finish(fig,'positive_negative_asymmetry.png')
 metrics=bb['metrics']
 if metrics:
  names=[m['model'] for m in metrics];fig,axes=plt.subplots(2,2,figsize=(12,8));xx=np.arange(len(names))
  for ax,key,index,title,unit in [(axes[0,0],'MAE_MPa_n',0,'Yield stress MAE','MPa'),(axes[0,1],'RMSE_MPa_n',0,'Yield stress RMSE','MPa'),(axes[1,0],'MAE_MPa_n',1,'n MAE','dimensionless'),(axes[1,1],'RMSE_MPa_n',1,'n RMSE','dimensionless')]:
   ax.bar(xx,[m[key][index] for m in metrics]);ax.set_xticks(xx,[n.replace('_','\n') for n in names],fontsize=8);ax.set(title=title,ylabel=unit);ax.grid(alpha=.2,axis='y')
  finish(fig,'prospective_MAE_RMSE_vs_constant.png')
  pred=rows(P/'prospective_parameter_predictions.csv');fig,axes=plt.subplots(2,2,figsize=(11,8))
  for ax,name in zip(axes.ravel(),names):
   rs=[r for r in pred if r['model']==name];truth=np.array([[float(r['x_true']),float(r['y_true'])] for r in rs]);estimated=np.array([[float(r['x_pred']),float(r['y_pred'])] for r in rs]);ax.scatter(truth[:,0],truth[:,1],marker='x',s=65,c='black',label='true inputs');ax.scatter(estimated[:,0],estimated[:,1],marker='o',s=25,label='frozen prediction')
   for r,t,v in zip(rs,truth,estimated):ax.annotate(r['candidate_id'],v,fontsize=8);ax.plot([t[0],v[0]],[t[1],v[1]],color='grey',alpha=.4)
   ax.scatter([.24],[.16],marker='+',s=100,c='red',label='I06');ax.set(xlabel='Normalized log-yield coordinate x',ylabel='Normalized exponent coordinate y',title=name);ax.legend(fontsize=7);ax.grid(alpha=.2)
  finish(fig,'true_vs_frozen_predicted_parameters.png')
  fig,axes=plt.subplots(1,2,figsize=(12,5));cids=['P01','P02','P03','P04'];xx=np.arange(4)
  for i,name in enumerate(names):
   rs=[next(r for r in pred if r['model']==name and r['candidate_id']==cid) for cid in cids]
   for ax,col in zip(axes,['raw_active_amplitude_ratio','incremental_active_amplitude_ratio']):ax.bar(xx+(i-1.5)*.18,[float(r[col]) for r in rs],width=.18,label=name)
  for ax,title in zip(axes,['Raw prediction relative to true I06','Increment diagnostic relative to model(I06)']):ax.axhline(1,color='black',ls='--');ax.axhline(0,color='grey',lw=.8);ax.set_xticks(xx,cids);ax.set(ylabel='Predicted / true active-axis change',title=title);ax.grid(alpha=.2,axis='y')
  axes[0].legend(fontsize=7);finish(fig,'direction_and_amplitude_recovery.png')
  train=read(R/'run/run_057/artifacts/private/frozen_predictor/training_25.json');q=np.array(train['normalized_targets']);h=ConvexHull(q);fig,ax=plt.subplots(figsize=(7,5));ax.scatter(q[:,0],q[:,1],c='grey',s=20,label='25 original FE training points')
  for edge in h.simplices:ax.plot(q[edge,0],q[edge,1],color='grey',lw=.7)
  for r in [r for r in pred if r['model']=='constant_I06_parameters']:ax.scatter(float(r['x_true']),float(r['y_true']),marker='x',c='red');ax.annotate(r['candidate_id']+(' OUTSIDE' if r['candidate_id']=='P03' else ''),(float(r['x_true']),float(r['y_true'])),fontsize=8)
  ax.set(xlim=(.17,.32),ylim=(.09,.25),xlabel='Normalized log-yield x',ylabel='Normalized n coordinate y',title='Prospective local coverage; P03 outside joint training hull');ax.legend(fontsize=8);ax.grid(alpha=.2);finish(fig,'P03_parameter_support.png')
 save(P/'figure_manifest.json',{'files':[{'path':rel(p),'sha256':sha(p)} for p in sorted(out.glob('*.png'))],'all_figures_from_actual_existing_FE':'no surrogate or new FE'})
 print(json.dumps({'figures':len(list(out.glob('*.png')))}))

if __name__=='__main__':main()
