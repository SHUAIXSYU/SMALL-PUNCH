"""Scientific visualizations: observed axes versus explicit local-linear predictions."""
from common63 import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.2,'savefig.dpi':180})
def finish(fig,name):fig.tight_layout();fig.savefig(P/name);plt.close(fig)
def main():
 arrays=read(P/'analysis_arrays.json');direction=read(P/'direction_analysis.json');views=read(P/'view_SVD_comparison.json')['views'];bands=read(P/'band_SVD_analysis.json')['bands'];d=read(P/'verified_local_data.json');f=rows(P/'feature_direction_responses.csv');u=np.array(arrays['grid_m'])*1000;vw=np.array(direction['weak_xy']);vs=np.array(direction['strong_xy']);h=direction['h']
 fig,ax=plt.subplots(1,2,figsize=(11,5.5));colors=['k','tab:blue','tab:blue','tab:orange','tab:orange']
 for rec,color in zip(d['records'],colors):
  q=np.array(rec['coordinate'])-np.array(direction['center_xy']);ax[0].scatter(*q,color=color,zorder=4);ax[0].annotate(rec['sample_id'],q,xytext=(4,4),textcoords='offset points')
 ax[0].plot([h,0,-h,0,h],[0,h,0,-h,0],'k:',label='Convex hull of actual axis samples')
 for v,label,color in [(vw,'Weak predicted direction','tab:red'),(vs,'Strong predicted direction','tab:green')]:
  ax[0].arrow(0,0,*(h*v),color=color,width=.0003,length_includes_head=True,label=label);ax[0].scatter(*(h*v),facecolors='none',edgecolors=color,s=90);ax[0].scatter(*(-h*v),facecolors='none',edgecolors=color,s=90)
 ax[0].set(xlabel='Normalized delta x (log yield stress)',ylabel='Normalized delta y (n)',title='Actual FE points and conceptual mixed directions',aspect='equal');ax[0].legend(fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.20))
 xx,yy=np.meshgrid(np.linspace(-.03,.03,201),np.linspace(-.03,.03,201));J=np.array(views['full241']['J']);G=J.T@J;z=1428.9*np.sqrt(G[0,0]*xx**2+2*G[0,1]*xx*yy+G[1,1]*yy**2)
 cc=ax[1].contour(xx,yy,z,levels=[arrays['reference_amplitude_N'],1.,3.092632613282926,10.,20.]);ax[1].clabel(cc,inline=True,fmt='%.2g N');ax[1].set(xlabel='Normalized delta x',ylabel='Normalized delta y',title='Equal linearized response RMS; NOT confidence contours',aspect='equal');finish(fig,'parameter_compensation_local.png')
 fig,ax=plt.subplots(2,1,figsize=(9,6),sharex=True);ax[0].plot(u,arrays['global_strong_halfstep_N'],label='Strong direction, normalized norm0.025');ax[0].plot(u,arrays['global_weak_halfstep_N'],label='Weak direction, normalized norm0.025');ax[0].set_ylabel('Linearized response (N)');ax[0].legend()
 ax[1].plot(u,arrays['global_weak_halfstep_N'],label='Weak mixed direction (not actual FE)');ax[1].plot(u,arrays['observed_center_difference_N'],label='Observed center refinement difference');ax[1].set(xlabel='Punch displacement (mm)',ylabel='Response difference (N)');ax[1].legend();finish(fig,'strong_weak_and_center_difference.png')
 fig,ax=plt.subplots(1,2,figsize=(11,4.3));x=np.arange(5);labels=['0-.3','.3-.6','.6-.9','.9-1.2','Full']
 ax[0].bar(x-.25,[b['interval_own_weak_halfstep_RMS_N'] for b in bands],width=.25,label='Each band own weak direction');ax[0].bar(x,[b['same_global_weak_halfstep_RMS_N'] for b in bands],width=.25,label='Same full-curve weak direction');ax[0].bar(x+.25,[b['observed_center_change_RMS_N'] for b in bands],width=.25,label='Observed center change');ax[0].set_xticks(x,labels);ax[0].set_ylabel('RMS (N)');ax[0].legend(fontsize=7)
 ax[1].plot(x,[b['condition_number'] for b in bands],'o-');ax[1].set_xticks(x,labels);ax[1].set_ylabel('Condition number (declared RMS metric)');ax[1].set_title('Lower condition alone is insufficient');finish(fig,'band_resolution_comparison.png')
 fig,ax=plt.subplots(1,2,figsize=(12,5));names=[r['name'] for r in f];x=np.arange(17);ax[0].barh(x,[float(r['normalized_global_weak_halfstep_equiv_N']) for r in f]);ax[0].set_yticks(x,names);ax[0].set_xlabel('Weak response / row scale *1428.9 (N-equivalent)');ax[0].set_title('Mixed units use declared physical scales')
 ax[1].plot([float(r['local_gradient_angle_deg']) for r in f],x,'o');ax[1].set_yticks(x,names);ax[1].set_xlabel('Local feature-gradient angle in normalized parameter plane');ax[1].set_title('Nearby angles indicate local redundancy');finish(fig,'feature_weak_response_and_angles.png')
 red=read(P/'feature_redundancy.json');fig,ax=plt.subplots(figsize=(9,8));im=ax.imshow(red['signed_local_gradient_cosines'],vmin=.85,vmax=1,cmap='viridis');ax.set_xticks(x,names,rotation=90);ax.set_yticks(x,names);fig.colorbar(im,ax=ax,label='Cosine of two-component local gradients');ax.set_title('Local directional redundancy, NOT observation covariance');finish(fig,'local_feature_redundancy.png')
 rs=rows(P/'scenario_parameter_sensitivity.csv');selected=[r for r in rs if float(r['input_RMS_factor'])==1 and float(r['sign'])==1];shapes=['aligned_weak_mode','aligned_strong_mode','coherent_ramp','localized_contact_bump','observed_center_pattern'];names=['two_loads','five_features','full241'];fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
 for i,name in enumerate(names):
  current=[next(r for r in selected if r['view']==name and r['shape']==shape) for shape in shapes];xx=np.arange(5)+(i-1)*.25;ax[0].bar(xx,[float(r['delta_sigma_tangent_MPa']) for r in current],width=.25,label=name);ax[1].bar(xx,[float(r['delta_n_tangent']) for r in current],width=.25,label=name)
 ax[0].set_ylabel('Tangent delta yield stress (MPa)');ax[1].set_ylabel('Tangent delta n');ax[1].set_xticks(np.arange(5),['Weak-aligned','Strong-aligned','Ramp','Local bump','Observed pattern']);ax[0].legend();ax[0].set_title('Deterministic response-sensitivity scenarios: RMS0.432678 N; NOT fitted parameters');finish(fig,'deterministic_scenario_offsets.png')
 print(json.dumps({'figures':6,'no_FE_prediction_presented_as_actual':True}))
if __name__=='__main__':main()
