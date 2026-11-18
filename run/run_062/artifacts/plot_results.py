"""Static scientific plots of native curves and frozen-grid comparisons."""
from common62 import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22,'savefig.dpi':180})
def finish(fig,name):
 fig.tight_layout();fig.savefig(P/name);plt.close(fig)
def main():
 d=read(P/'verified_plot_arrays.json');m=read(P/'refinement_metrics.json');u=np.array(d['grid_m'])*1000;a=np.array(d['original_N']);b=np.array(d['refined_N']);e=np.array(d['experiment_N']);delta=b-a
 no=np.array(d['original_native_u_m'])*1000;nn=np.array(d['refined_native_u_m'])*1000;fo=np.array(d['original_native_force_N']);fn=np.array(d['refined_native_force_N'])
 fig,ax=plt.subplots(2,1,figsize=(8,7),sharex=True)
 ax[0].plot(no,fo,label='I06 original, max dt=0.0025');ax[0].plot(nn,fn,'--',label='I06 refined, max dt=0.00125');ax[0].plot(u,e,color='.35',lw=1,label='SPT experiment (frozen target)');ax[0].set_ylabel('Punch force (N)');ax[0].legend();ax[0].set_title('Same material / geometry / BC; adjacent increment refinement only')
 ax[1].plot(u,delta,color='tab:red');ax[1].axhline(0,color='k',lw=.6);ax[1].set(xlabel='Punch displacement (mm)',ylabel='Refined - original (N)',xlim=(0,1.2));ax[1].set_title(f"Frozen 241-point RMSE={m['force_difference_RMSE_N']:.6f} N; R={m['R_RMSE']:.6f}")
 finish(fig,'I06_FD_overlay_and_difference.png')
 fig,ax=plt.subplots(2,1,figsize=(8,6),sharex=True)
 ax[0].plot(no,fo,'.-',ms=3,label='Original native accepted history');ax[0].plot(nn,fn,'.--',ms=2,label='Refined native accepted history');ax[0].set_ylabel('Force (N)');ax[0].legend()
 ax[1].plot(u,delta,'o-',ms=3);ax[1].set(xlabel='Punch displacement (mm)',ylabel='Frozen-grid difference (N)',xlim=(1.10,1.16));ax[0].set_title('Native sampling and local contact diagnostic window')
 finish(fig,'local_1p10_1p16_native.png')
 fig,ax=plt.subplots(2,1,figsize=(8,6),sharex=True)
 ax[0].plot(u,a-e,label='Original - experiment');ax[0].plot(u,b-e,'--',label='Refined - experiment');ax[0].set_ylabel('Residual (N)');ax[0].legend()
 ax[1].plot(u,100*abs(delta)/np.maximum(abs(a),71.445));ax[1].set(xlabel='Punch displacement (mm)',ylabel='Regularized difference (%)',xlim=(0,1.2));ax[1].set_title('Denominator=max(|original force|,71.445 N); no zero shift / smoothing')
 finish(fig,'residuals_and_regularized_difference.png')
 fig,ax=plt.subplots(1,2,figsize=(10,4));segs=m['segments'];labels=[f"{v['lower_mm']:.1f}-{v['upper_mm']:.1f}" for v in segs]
 ax[0].bar(labels,[v['RMSE_N'] for v in segs]);ax[0].set(xlabel='Displacement interval (mm)',ylabel='F-D difference RMSE (N)');ax[0].tick_params(axis='x',rotation=25)
 ax[1].plot(no,d['old_max_PEEQ'],label='Original');ax[1].plot(nn,d['new_max_PEEQ'],'--',label='Refined');ax[1].set(xlabel='Actual native displacement (mm)',ylabel='Maximum PEEQ over IPs');ax[1].legend();ax[1].set_title('Scalar maxima; not the same material point')
 finish(fig,'segment_errors_and_PEEQ.png')
 context=read(P/'contact_and_peak_context.json')['context'];fig,ax=plt.subplots(2,1,figsize=(8,6),sharex=True)
 for name,c in context.items():
  fr=c['all_1p10_to_1p16_native_accepted_frames'];xx=[];p=[];op=[]
  for f in fr:
   n=next((v for v in f['contact'].get('topology_node_values',[]) if v['node_label']==23),None)
   if n:
    xx.append(f['u_mm']);p.append(np.nan if n['cpress'] is None else n['cpress']/1e6);op.append(np.nan if n.get('copen_valid') is None else n['copen_valid']*1e6)
  ax[0].plot(xx,p,'.-',label=name);ax[1].plot(xx,op,'.-',label=name)
 ax[0].set_ylabel('Node23 CPRESS (MPa)');ax[0].legend();ax[1].set(xlabel='Actual displacement (mm)',ylabel='Node23 valid COPEN (um)');ax[0].set_title('Saved contact evidence; missing/sentinel gaps are not physical openings')
 finish(fig,'node23_contact_1p10_1p16.png')
 print(json.dumps({'figures':5,'no_smoothing_extrapolation_or_fit':True}))
if __name__=='__main__':main()
