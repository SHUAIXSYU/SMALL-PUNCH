"""Read existing verified curves and evaluate fixed-grid directions; no optimizer."""
from pathlib import Path
import sys,json,csv,hashlib,os
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_054';P=RUN/'artifacts/private';os.environ['MPLCONFIGDIR']=str(P/'mplconfig');sys.path.insert(0,str(R))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inverse.fd_loss import Curve,interpolate
from direction_math import rms,cosine,angle,alpha_vectors,span_comparison,loss_decomposition,band_masks
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvread(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def loadcurve(path):
 r=csvread(path);uk='displacement_m' if 'displacement_m' in r[0] else 'displacement_model_length';fk='force_n' if 'force_n' in r[0] else 'force_model_force'
 return Curve(tuple(float(x[uk]) for x in r),tuple(float(x[fk]) for x in r),'m','N')
def main():
 aud=read(P/'input_compatibility_audit.json');bind=aud['loss_binding'];exp=csvread(R/bind['target_path']);exp=[r for r in exp if 0<=float(r['displacement_m'])<=.0012];assert len(exp)==241
 u=np.array([float(x['displacement_m']) for x in exp]);fexp=np.array([float(x['force_n']) for x in exp]);assert u[0]==0 and u[-1]==.0012
 fy={r['id']:np.array(interpolate(loadcurve(R/r['fd']),u)) for r in aud['records']}
 oldc=np.array(interpolate(loadcurve(R/aud['old_center_fd']),u));fy['C014']=oldc
 oldaligned=csvread(R/'run/run_022/artifacts/private/analysis/aligned_curves.csv');newaligned=csvread(R/'run/run_053/artifacts/private/main/aligned_241_three_models.csv')
 for i,x in enumerate(u):
  assert abs(float(oldaligned[i]['displacement_m'])-x)<1e-16 and float(newaligned[i]['displacement_m'])==x
  assert float(oldaligned[i]['experimental_force_n'])==float(newaligned[i]['experimental_force_N'])==fexp[i]
 for pid in ['L01','L02','L03','L04']:assert np.allclose(fy[pid],[float(r[pid+'_force_n']) for r in oldaligned],rtol=0,atol=1e-10)
 for pid in ['D01','H01','H02']:assert np.allclose(fy[pid],[float(r[pid+'_force_N']) for r in newaligned],rtol=0,atol=1e-10)
 sx=(fy['L02']-fy['L01'])/.1;sy=(fy['L04']-fy['L03'])/.1;av=alpha_vectors(fy['H01'],fy['D01'],fy['H02']);sa=av['secant'];directions={'sigma_x_old':sx,'n_y_old':sy,'alpha_D01':sa}
 orig=read(R/'run/run_022/artifacts/private/analysis/sensitivity.json');assert np.allclose(sx,orig['Sx_n'],rtol=0,atol=1e-9) and np.allclose(sy,orig['Sy_n'],rtol=0,atol=1e-9)
 oldJ=np.column_stack([sx,sy]);sv=np.linalg.svd(oldJ,compute_uv=False);assert np.allclose(sv,orig['matrix']['singular_values_raw'],rtol=1e-9)
 needed=fexp-fy['D01'];base_residual=-needed;oldloss=read(R/'run/run_053/artifacts/private/main/response_metrics.json');lm={r['candidate_id']:r['loss'] for r in oldloss['records']}
 assert abs(float(np.mean((base_residual/1428.9)**2))-lm['D01'])<1e-15
 decom={}
 for label,key in [('H01','minus'),('H02','plus')]:
  d=loss_decomposition(av[key],needed);assert abs(d['delta_loss']-(lm[label]-lm['D01']))<1e-15;decom[label]=d
 masks=band_masks(u);pairs={};unit={k:v/np.linalg.norm(v) for k,v in directions.items()}
 for a,b in [('sigma_x_old','n_y_old'),('sigma_x_old','alpha_D01'),('n_y_old','alpha_D01')]:pairs[a+'__'+b]={'cosine':cosine(directions[a],directions[b]),'angle_degrees':angle(directions[a],directions[b]),'scope':'historical within-study exploratory' if b=='n_y_old' else 'EXPLORATORY_CROSS_BASEPOINT_NUMERICAL_CONTRACT'}
 bands=[]
 for j,mask in enumerate(masks):
  a,b=[(0,.3),(.3,.6),(.6,.9),(.9,1.2)][j];row={'lower_mm':a,'upper_mm':b,'points':int(sum(mask)),'D01_residual_RMSE_N':rms(base_residual[mask]),'D01_loss_contribution_fraction':float(np.sum(base_residual[mask]**2)/np.sum(base_residual**2)),'alpha_sensitivity_RMS_N_per_alpha':rms(sa[mask]),'alpha_squared_response_fraction':float(np.sum(sa[mask]**2)/np.sum(sa**2)),'H01_response_RMSE_N':rms(av['minus'][mask]),'H02_response_RMSE_N':rms(av['plus'][mask]),'H01_deltaLoss_contribution':float(np.sum((fy['H01'][mask]-fexp[mask])**2-base_residual[mask]**2)/(241*1428.9**2)),'H02_deltaLoss_contribution':float(np.sum((fy['H02'][mask]-fexp[mask])**2-base_residual[mask]**2)/(241*1428.9**2)),'alpha_cosine_to_needed_correction':cosine(sa[mask],needed[mask]),'cos_sigma_alpha':cosine(sx[mask],sa[mask]),'cos_n_alpha':cosine(sy[mask],sa[mask]),'cos_sigma_n':cosine(sx[mask],sy[mask]),'sigma_squared_response_fraction':float(np.sum(sx[mask]**2)/np.sum(sx**2)),'n_squared_response_fraction':float(np.sum(sy[mask]**2)/np.sum(sy**2)),'sigma_RMS_N_per_x':rms(sx[mask]),'n_RMS_N_per_y':rms(sy[mask])}
  bands.append(row)
 normalization={'sigma':'x=ln(sigma_y/150)/ln(1000/150), derivative denominator delta_x=.1, endpoints x_center+/- .05 at200MPa,n=.1','n':'y=(n-.02)/.48, denominator delta_y=.1, endpoints n=.076/.124 atsigma200MPa','alpha':'alpha=.5/1/1.5 at D01; denominator1; N per unit alpha. No physical equivalence to x/y full-range changes','shape_comparison':'each full-window response divided by its own Euclidean norm; cosines and projection only, no magnitude-based parameter importance ranking','force_scaling':'optional common F_ref1428.9N does not alter cosines','formal_joint_metrics':'NOT_EVALUABLE: basepoints and step controls differ; no three-column Jacobian/FIM computed'}
 result={'version':'run054-offline-direction-v1','grid_points':241,'loss_contract':bind['version'],'scope':'EXPLORATORY_CROSS_STUDY_RESPONSE_SHAPES','normalization':normalization,'alpha':{'halfstep':.5,'fullstep':1.,'secant_RMS_N_per_alpha':rms(sa),'secant_norm_N_per_alpha':float(np.linalg.norm(sa)),'secant_positive_points':int(sum(sa>0)),'secant_negative_points':int(sum(sa<0)),'side_response_RMSE_N':{'H01':rms(av['minus']),'H02':rms(av['plus'])},'side_cosine_after_sign_alignment':cosine(-av['minus'],av['plus']),'even_RMS_N':rms(av['even']),'odd_RMS_N':rms(av['odd']),'even_over_odd_RMS':rms(av['even'])/rms(av['odd']),'max_abs_even_N':float(np.max(abs(av['even']))),'forward_backward_slope_difference_RMS_N_per_alpha':rms(av['forward']-av['backward']),'alpha_RMS_over_D01_adjacent_increment_RMS':rms(sa)/.3383060028573848,'sides_RMSE_over_observed_increment':{k:rms(av[v])/.3383060028573848 for k,v in [('H01','minus'),('H02','plus')]},'not_infinitesimal_derivative':True},'cosines':pairs,'alpha_projection_onto_old_parameter_shape_span':span_comparison([sx,sy],sa),'residual':{'sign':'needed correction = F_exp - F_D01; positive alignment may reduce linear term but full finite response can overshoot','norm_N':float(np.linalg.norm(needed)),'RMS_N':rms(needed),'alpha_cosine_to_needed_correction':cosine(sa,needed),'alpha_angle_to_needed_correction_degrees':angle(sa,needed),'finite_loss_decomposition':decom},'bands':bands,'historical_old_two_parameter_matrix_only':{'singular_values_N_per_normalized_coordinate':sv.tolist(),'condition_number':float(sv[0]/sv[-1]),'scope':'recomputed old run020/022 two-column study only, historical numerical warnings retained; not transferred to D01 or alpha'},'formal_joint_Jacobian':None,'formal_joint_Fisher_information':None,'formal_joint_condition_number':None,'formal_joint_identifiability':'NOT_EVALUABLE','joint_rank_claim':False,'alpha_optimization_or_recommendation_from_quadratic':False}
 save(P/'direction_results.json',result);csvsave(P/'band_results.csv',bands)
 csvsave(P/'aligned_response_vectors.csv',[{'displacement_m':float(x),'exp_force_N':float(fexp[i]),**{k+'_force_N':float(v[i]) for k,v in fy.items()},'sigma_old_N_per_x':float(sx[i]),'n_old_N_per_y':float(sy[i]),'alpha_N_per_alpha':float(sa[i]),'H01_minus_D01_N':float(av['minus'][i]),'H02_minus_D01_N':float(av['plus'][i]),'alpha_even_N':float(av['even'][i]),'needed_correction_N':float(needed[i])} for i,x in enumerate(u)])
 fig,ax=plt.subplots(figsize=(8,4.7))
 for k in directions:ax.plot(u*1000,unit[k],label=k)
 ax.set(xlabel='Punch displacement (mm)',ylabel='Unit Euclidean-norm response shape',title='Exploratory shapes: different basepoints / time controls');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(P/'unit_direction_shapes.png',dpi=180);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(8,7),sharex=True)
 for k,v in [('H01-D01',av['minus']),('H02-D01',av['plus'])]:axes[0].plot(u*1000,v,label=k)
 axes[1].plot(u*1000,sa,label='Centered alpha secant (N/unit alpha)');axes[1].plot(u*1000,av['even'],label='Even response (N)')
 for ax in axes:ax.axhline(0,color='grey',lw=.7);ax.legend();ax.grid(alpha=.2)
 axes[0].set_ylabel('Force contrast (N)');axes[1].set(xlabel='Punch displacement (mm)',ylabel='Finite contrast / secant (labeled units)');fig.suptitle('D01-based hardening contrasts; no fitted optimum');fig.tight_layout();fig.savefig(P/'alpha_contrasts_and_asymmetry.png',dpi=180);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.4));axes[0].plot(u*1000,needed,label='Experiment - D01')
 for k in ['H01','H02']:axes[0].plot(u*1000,fy[k]-fy['D01'],label=k+' - D01')
 axes[0].set(xlabel='Displacement (mm)',ylabel='Force (N)');axes[0].legend();axes[0].grid(alpha=.2)
 x=np.arange(4);axes[1].bar(x-.18,[r['D01_loss_contribution_fraction'] for r in bands],.36,label='D01 residual squared fraction');axes[1].bar(x+.18,[r['alpha_squared_response_fraction'] for r in bands],.36,label='Alpha response squared fraction');axes[1].set_xticks(x,['0-.3','.3-.6','.6-.9','.9-1.2']);axes[1].set(xlabel='Displacement band (mm)',ylabel='Fraction (not energy or information)');axes[1].legend(fontsize=8);fig.tight_layout();fig.savefig(P/'residual_vs_alpha_regions.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4.5));lab=['sigma / n (old)','sigma / alpha*','n / alpha*'];coskeys=list(pairs)
 for k,label in [('cos_sigma_n',lab[0]),('cos_sigma_alpha',lab[1]),('cos_n_alpha',lab[2])]:ax.plot(np.arange(4),[r[k] for r in bands],marker='o',label=label)
 ax.set_xticks(np.arange(4),['0-.3','.3-.6','.6-.9','.9-1.2']);ax.set(xlabel='Displacement band (mm)',ylabel='Cosine',title='* Cross-study exploratory comparison, not common Jacobian');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(P/'band_direction_cosines.png',dpi=180);plt.close(fig)
 print(json.dumps({'cosines':pairs,'alpha':result['alpha'],'projection':result['alpha_projection_onto_old_parameter_shape_span'],'residual':result['residual'],'bands':bands,'old_condition':result['historical_old_two_parameter_matrix_only']['condition_number']}))
if __name__=='__main__':main()
