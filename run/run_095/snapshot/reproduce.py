"""Reproduce released FE-only two-thickness arithmetic and figures; no Abaqus call."""
from pathlib import Path
import argparse,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def rms(x):return float(np.sqrt(np.mean(np.square(x))))
def run(root,output):
 x=np.genfromtxt(root/'data/fd_four_curves.csv',delimiter=',',names=True)
 u=x['u_mm'];f10=x['t05_I06_N'];f11=x['t05_MFREE_N'];f20=x['t10_I06_N'];f21=x['t10_MFREE_N']
 assert len(u)==241 and np.allclose(u,np.arange(241)*.005,atol=1e-12,rtol=0)
 s1=rms(f10);s2=rms(f20);v1=f11-f10;v2=f21-f20;z1=v1/s1;z2=v2/s2
 proj=float(np.dot(z1,z2)/np.dot(z1,z1));orth=z2-proj*z1
 d1=rms(v1);d2=rms(v2);cos=float(np.dot(z1,z2)/(np.linalg.norm(z1)*np.linalg.norm(z2)))
 q=np.genfromtxt(root/'data/target_Q_pair.csv',delimiter=',',names=True);dq=rms(q['MFREE_MPa']-q['I06_MPa'])
 scenarios=[{'tau_abs_N':a,'tau_rel':r,'effective_cap_N':min(a,r*s2),'d2_minus_cap_N':d2-min(a,r*s2),'joint_member_MFREE':bool(d1<=5 and d2<=min(a,r*s2)),'robust_verdict':'UNRESOLVED_NO_T2_ERROR_BOUND'} for a in [2.,5.,10.] for r in [.005,.01,.02]]
 output.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
 fig,ax=plt.subplots(figsize=(7.6,4.6),layout='constrained')
 for y,label,color,style in [(f10,'0.5 mm I06','#0072B2','-'),(f11,'0.5 mm M_FREE','#D55E00','--'),(f20,'1.0 mm I06','#009E73','-'),(f21,'1.0 mm M_FREE','#CC79A7','--')]:ax.plot(u,y,label=label,color=color,ls=style,lw=1.7)
 ax.set(xlabel='Punch displacement (mm)',ylabel='Punch force (N)',xlim=(0,1.2),title='Four real FE responses: fixed 241-point grid');ax.legend();ax.grid(alpha=.18);fig.savefig(output/'01_four_fd.png');plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(7.6,6.4),sharex=True,layout='constrained')
 for y,label,col in [(v1,'0.5 mm: M_FREE minus I06','#0072B2'),(v2,'1.0 mm: M_FREE minus I06','#D55E00')]:axes[0].plot(u,y,label=label,color=col,lw=1.4)
 for y,label,col in [(z1,'0.5 mm: delta / own I06 RMS','#0072B2'),(z2,'1.0 mm: delta / own I06 RMS','#D55E00')]:axes[1].plot(u,y,label=label,color=col,lw=1.4)
 for a in axes:a.axhline(0,color='.5',lw=.7);a.legend(fontsize=9);a.grid(alpha=.18)
 axes[0].set(ylabel='Force difference (N)',title='Actual pair differences; native stair-step effects retained');axes[1].set(xlabel='Punch displacement (mm)',ylabel='Normalized difference (-)',xlim=(0,1.2));fig.savefig(output/'02_pair_differences.png');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(9,3.8),layout='constrained')
 axes[0].plot(z1,z2,color='#0072B2',lw=1,label='paired displacement samples');xx=np.array([min(z1),max(z1)]);axes[0].plot(xx,proj*xx,'--',color='#D55E00',label='through-origin projection');axes[0].set(xlabel='0.5 mm normalized difference',ylabel='1.0 mm normalized difference',title=f'Cosine = {cos:.4f}');axes[0].legend(fontsize=8)
 axes[1].plot(u,orth,color='#009E73',lw=1.4);axes[1].axhline(0,color='.5',lw=.7);axes[1].set(xlabel='Punch displacement (mm)',ylabel='Orthogonal normalized residual',title='One-pair direction diagnostic')
 for a in axes:a.grid(alpha=.18)
 fig.savefig(output/'03_scale_and_direction.png');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(9,3.5),layout='constrained')
 margins=np.array([s['d2_minus_cap_N'] for s in scenarios]).reshape(3,3)
 im=axes[0].imshow(margins,aspect='auto',cmap='viridis');axes[0].set_xticks(range(3),['0.5%','1%','2%']);axes[0].set_yticks(range(3),['2','5','10']);axes[0].set(xlabel='Relative cap / own I06 RMS',ylabel='Absolute cap (N)',title='d2 minus effective cap (N)')
 for i in range(3):
  for j in range(3):axes[0].text(j,i,f'{margins[i,j]:.2f}',ha='center',va='center',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
 fig.colorbar(im,ax=axes[0]);axes[1].plot(q['true_total_strain'],q['I06_MPa'],label='I06',color='#0072B2');axes[1].plot(q['true_total_strain'],q['MFREE_MPa'],'--',label='M_FREE',color='#D55E00');axes[1].set(xlabel='True total strain',ylabel='True stress (MPa)',title=f'Deployed target curves: dQ={dq:.3f} MPa');axes[1].legend();axes[1].grid(alpha=.18);fig.savefig(output/'04_scenarios_and_Q.png');plt.close(fig)
 return {'t1_RMS_N':d1,'t2_RMS_N':d2,'S1_N':s1,'S2_N':s2,'normalized_d1':rms(z1),'normalized_d2':rms(z2),'cosine':cos,'projection_ratio':proj,'orthogonal_residual_fraction':float(np.linalg.norm(orth)/np.linalg.norm(z2)),'pair_d_Q_MPa':dq,'scenarios':scenarios}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot-dir',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--output-dir',type=Path);a=p.parse_args();print(json.dumps(run(a.snapshot_dir,a.output_dir or a.snapshot_dir/'reproduced'),allow_nan=False))
