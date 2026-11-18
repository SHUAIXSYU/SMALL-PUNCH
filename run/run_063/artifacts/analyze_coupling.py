"""Finite-secant local diagnostics and deterministic response scenarios, no new fitting."""
from common63 import *
import numpy as np,math
sys.path.insert(0,str(R/'run/run_055/artifacts'))
from feature_core import extract,NAMES,FIXED2,FIXED5
FREF=1428.9;H=.025;CENTER=np.array([.24,.16]);SIGMA=236.49902622197678;N0=.0968
LNR=math.log(1000/150);D=np.array([SIGMA*LNR,.48])
def decomposition(J):
 J=np.asarray(J,dtype=float)
 if J.ndim!=2 or J.shape[1]!=2 or J.shape[0]<2 or not np.isfinite(J).all():return {'status':'NOT_EVALUABLE','reason':'two finite columns and >=2 observations required'}
 U,s,V=np.linalg.svd(J,full_matrices=False);tol=max(J.shape)*np.finfo(float).eps*s[0];rank=int(np.sum(s>tol));norm=np.linalg.norm(J,axis=0)
 for i,positive in [(0,True),(1,False)]:
  if (V[i,0]<0 if positive else V[i,0]>0):V[i]*=-1;U[:,i]*=-1
 assert np.allclose(U@np.diag(s)@V,J,rtol=1e-12,atol=1e-14)
 eig=np.linalg.eigvalsh(J.T@J);np.testing.assert_allclose(np.sqrt(np.maximum(eig,0))[::-1],s,rtol=1e-10,atol=1e-12)
 cos=float(J[:,0]@J[:,1]/np.prod(norm)) if min(norm)>0 else None
 return {'status':'EXPLORATORY_LOCAL_LINEAR_ANALYSIS' if rank==2 else 'NOT_EVALUABLE','rank':rank,'rank_tolerance':tol,'singular_values':s.tolist(),'condition_number':float(s[0]/s[-1]) if rank==2 else None,'column_norms':norm.tolist(),'cosine':cos,'angle_deg':float(np.degrees(np.arccos(np.clip(cos,-1,1)))) if cos is not None else None,'strong_direction_xy':V[0].tolist(),'weak_direction_xy':V[1].tolist(),'J':J.tolist(),'U':U.tolist(),'no_noise_weighted_information_interpretation':True}
def scale_features():return np.array([FREF]*8+[FREF/1.2]*4+[FREF*.0003]*4+[FREF*.0012])
def physical_offset(q):
 q=np.asarray(q);return {'normalized_dx_dy':q.tolist(),'tangent_delta_sigma_MPa_delta_n':(D*q).tolist(),'scope':'local sensitivity offset, not a newly inverted or calibrated material parameter'}

def main():
 d=read(P/'verified_local_data.json');old=read(R/'run/run_059/artifacts/private/study_A_local_secants.json');grid=np.array(d['grid_m']);curves={k:np.array(v) for k,v in d['curves_N'].items()};feat={k:np.array(v) for k,v in d['features'].items()};Aforce=np.column_stack([(curves['P02']-curves['P01'])/(2*H),(curves['P04']-curves['P03'])/(2*H)]);Af=np.column_stack([(feat['P02']-feat['P01'])/(2*H),(feat['P04']-feat['P03'])/(2*H)]);scales=scale_features();full=decomposition(Aforce/FREF/np.sqrt(len(grid)));vw=np.array(full['weak_direction_xy']);vs=np.array(full['strong_direction_xy']);observed=np.array(d['observed_center_refinement_delta_N_on_run059_grid']);amp=d['refinement_RMSE_reference_N']
 assert abs(H*FREF*full['singular_values'][-1]-3.092632613282926)<1e-12
 views={};verify=[]
 definitions={'two_loads':list(FIXED2),'five_features':list(FIXED5),'full241':None,'early2_secondary':[0,1],'independent3_secondary':[0,1,10],'early_mid3_exploratory':[0,1,5]}
 for name,cols in definitions.items():
  AA=Aforce if cols is None else Af[cols];rr=np.full(len(grid),FREF) if cols is None else scales[cols];J=AA/rr[:,None]/np.sqrt(len(AA));s=decomposition(J)
  if name in old['views']:
   np.testing.assert_allclose(J,old['views'][name]['J'],rtol=1e-12,atol=1e-13);np.testing.assert_allclose(s['singular_values'],old['views'][name]['singular_values'],rtol=1e-12,atol=1e-13);assert abs(s['condition_number']-old['views'][name]['condition_number'])<1e-10;verify.append(name)
  s.update(feature_columns=cols,feature_names=None if cols is None else [NAMES[c] for c in cols],row_scales=rr.tolist(),row_scaling='declared physical scale and sqrt(row count), NOT measured covariance',half_step_weak_physical_equivalent_RMS_N=H*FREF*s['singular_values'][-1],half_step_strong_physical_equivalent_RMS_N=H*FREF*s['singular_values'][0],global_full_weak_equivalent_RMS_N=float(np.linalg.norm(J@(H*vw))*FREF),global_full_strong_equivalent_RMS_N=float(np.linalg.norm(J@(H*vs))*FREF),role='frozen_primary' if name in ['two_loads','five_features','full241'] else 'secondary_or_exploratory_no_new_prediction_validation',numerical_convergence='NUMERICAL_RESOLUTION_LIMITED')
  views[name]=s
 bands=[];globalweak=Aforce@(H*vw);globalstrong=Aforce@(H*vs)
 for lo,hi in [(0,.3),(.3,.6),(.6,.9),(.9,1.2),(0,1.2)]:
  mask=(grid*1000>=lo-1e-10)&((grid*1000<hi-1e-10) if hi<1.2 else (grid*1000<=hi+1e-10));aa=Aforce[mask];Jn=aa/FREF/np.sqrt(mask.sum());info=decomposition(Jn);locweak=H*FREF*info['singular_values'][-1];gweak=float(np.sqrt(np.mean(globalweak[mask]**2)));e=float(np.sqrt(np.mean(observed[mask]**2)))
  info.update(lower_mm=lo,upper_mm=hi,points=int(mask.sum()),interval_own_weak_halfstep_RMS_N=locweak,interval_own_strong_halfstep_RMS_N=H*FREF*info['singular_values'][0],same_global_weak_halfstep_RMS_N=gweak,same_global_strong_halfstep_RMS_N=float(np.sqrt(np.mean(globalstrong[mask]**2))),global_weak_squared_response_fraction=float(np.sum(globalweak[mask]**2)/np.sum(globalweak**2)),observed_center_change_RMS_N=e,center_change_over_own_weak=float(e/locweak) if locweak>0 else None,center_change_over_same_global_weak=float(e/gweak) if gweak>0 else None,sigma_full_pair_response_RMS_N=float(np.sqrt(np.mean((curves['P02'][mask]-curves['P01'][mask])**2))),n_full_pair_response_RMS_N=float(np.sqrt(np.mean((curves['P04'][mask]-curves['P03'][mask])**2))),numerical_quality='NUMERICAL_RESOLUTION_LIMITED; center ratio is a diagnostic, NOT arm-error bound',independent_data_support='VERIFIED_FE_RESPONSE for axes; mixed-direction response is EXPLORATORY_LOCAL_LINEAR_ANALYSIS')
  bands.append(info)
 direction={'center_sigma_MPa':SIGMA,'center_n':N0,'center_xy':CENTER.tolist(),'parameter_normalization':d['normalization'],'h':H,'strong_xy':vs.tolist(),'weak_xy':vw.tolist(),'weak_tangent_per_unit_length':physical_offset(vw),'weak_halfstep_tangent':physical_offset(H*vw),'strong_halfstep_tangent':physical_offset(H*vs),'slope_dn_per_dln_sigma':float(.48*vw[1]/(LNR*vw[0])),'slope_dn_per_dsigma_MPa_at_I06':float(.48*vw[1]/(SIGMA*LNR*vw[0])),'weak_radial_h_to_axis_sample_L1_h_ratio':float(sum(abs(vw))),'max_weak_radial_step_within_axis_cross_convex_hull':float(H/sum(abs(vw))),'mixed_halfstep_in_axis_coordinate_box':True,'mixed_halfstep_outside_axis_cross_convex_hull':bool(sum(abs(H*vw))>H),'not_global_compensation_curve':True,'mixed_FE_response_not_measured':True,'physical_coordinate_mapped_halfstep_locations':[]}
 for sign in [-1,1]:
  q=CENTER+sign*H*vw;direction['physical_coordinate_mapped_halfstep_locations'].append({'sign':sign,'x':float(q[0]),'y':float(q[1]),'sigma_y_MPa':float(150*np.exp(q[0]*LNR)),'n':float(.02+.48*q[1]),'role':'conceptual future weak-direction test only, no INP/Job prepared or authorization'})
 feature_rows=[];g=Af/scales[:,None];norm=np.linalg.norm(g,axis=1);redundancy=(g@g.T)/np.outer(norm,norm)
 ref_native=read(R/'run/run_062/artifacts/private/verified_plot_arrays.json');fnew,_,_=extract(ref_native['refined_native_u_m'],ref_native['refined_native_force_N']);fold,_,_=extract(ref_native['original_native_u_m'],ref_native['original_native_force_N']);dfactual=fnew-fold
 for i,name in enumerate(NAMES):
  strong=H*float(Af[i]@vs);weak=H*float(Af[i]@vw)
  feature_rows.append({'index':i,'name':name,'unit':'N' if i<8 else 'N/mm' if i<12 else 'N*m','baseline_value':float(feat['I06'][i]),'dphi_dx':float(Af[i,0]),'dphi_dy':float(Af[i,1]),'row_scale':float(scales[i]),'local_gradient_angle_deg':float(np.degrees(np.arctan2(g[i,1],g[i,0]))),'global_weak_halfstep_delta_phi':weak,'global_strong_halfstep_delta_phi':strong,'normalized_global_weak_halfstep_equiv_N':FREF*weak/scales[i],'observed_center_change_delta_phi':float(dfactual[i]),'center_change_over_abs_weak_response':float(abs(dfactual[i]/weak)) if abs(weak)>1e-14 else None,'primary_two':i in FIXED2,'primary_five':i in FIXED5,'scope':'local response gradient/observed center difference only, not empirical parameter formula'})
 csvsave(P/'feature_direction_responses.csv',feature_rows);save(P/'feature_redundancy.json',{'names':list(NAMES),'signed_local_gradient_cosines':redundancy.tolist(),'interpretation':'two-component local gradient redundancy, not across25sample feature Pearson correlation, not noise covariance','no_new_selection_or_retraining':True})
 # Deterministic shapes of response change. These are NOT experiment noise draws.
 U=np.array(full['U']);ramp=grid/grid[-1];bump=np.exp(-.5*((grid-.00098)/.00001)**2)
 shapes={'aligned_weak_mode':U[:,-1],'aligned_strong_mode':U[:,0],'coherent_ramp':ramp,'localized_contact_bump':bump};scenarios=[];profiles={}
 for name,shape in shapes.items():
  shape=shape/np.sqrt(np.mean(shape**2))
  for mult in [.25,.5,1.,2.]:
   for sign in [-1.,1.]:
    label=f'{name}_RMSx{mult:g}_sign{sign:+g}';e=shape*(amp*mult*sign);profiles[label]=e.tolist();scenarios.append((label,name,mult,sign,e,None))
 for sign in [-1.,1.]:scenarios.append((f'observed_center_pattern_sign{sign:+g}','observed_center_pattern',1.,sign,observed*sign,dfactual*sign))
 scenario_rows=[]
 for label,name,mult,sign,e,actual_feature_delta in scenarios:
  efeatures=extract(grid,e)[0] if actual_feature_delta is None else actual_feature_delta
  for view in ['two_loads','five_features','full241']:
   v=views[view];cols=v['feature_columns'];changes=e if cols is None else efeatures[cols];sc=np.array(v['row_scales']);z=changes/sc/np.sqrt(len(changes));J=np.array(v['J']);dq=np.linalg.lstsq(J,z,rcond=None)[0];projected=J@dq
   scenario_rows.append({'scenario':label,'shape':name,'input_RMS_factor':mult,'sign':sign,'view':view,'response_RMS_N':float(np.sqrt(np.mean(e**2))),'response_max_abs_N':float(max(abs(e))),'delta_x':float(dq[0]),'delta_y':float(dq[1]),'delta_sigma_tangent_MPa':float(D[0]*dq[0]),'delta_n_tangent':float(D[1]*dq[1]),'normalized_offset_norm_over_h':float(np.linalg.norm(dq)/H),'unexplained_scaled_response_fraction':float(np.linalg.norm(z-projected)/np.linalg.norm(z)) if np.linalg.norm(z)>0 else None,'evidence':'SCENARIO_ANALYSIS; deterministic coherent shape; not material parameter estimate/CI or actual arm error'})
 save(P/'direction_analysis.json',direction);save(P/'view_SVD_comparison.json',{'views':views,'historical_views_independently_reconstructed':verify,'equal_information_loss_percentage':'NOT_EVALUABLE without observational covariance and common error model','strict_converged_Jacobian':'NOT_EVALUABLE','formal_Fisher_CI':'NOT_EVALUABLE'})
 save(P/'band_SVD_analysis.json',{'bands':bands,'partition':'left-closed right-open, last includes1.2; full separate','scaling':'Fref*sqrt(N_band) for declared RMS metric, not statistical whitening','same_global_direction_xy':vw.tolist()});csvsave(P/'band_summary.csv',[{k:v for k,v in b.items() if not isinstance(v,(dict,list))} for b in bands]);csvsave(P/'scenario_parameter_sensitivity.csv',scenario_rows)
 save(P/'analysis_arrays.json',{'grid_m':grid.tolist(),'A_force_N_per_normalized':Aforce.tolist(),'A_all_features':Af.tolist(),'global_weak_halfstep_N':globalweak.tolist(),'global_strong_halfstep_N':globalstrong.tolist(),'observed_center_difference_N':observed.tolist(),'scenario_force_profiles':profiles,'reference_amplitude_N':amp})
 save(P/'scenario_assumptions.json',{'evidence':'SCENARIO_ANALYSIS','amplitudes_N':[amp*k for k in [.25,.5,1,2]],'shapes':list(shapes)+['observed_center_pattern'],'correlation':'fully coherent deterministic shape per scenario; no independence/Gaussian covariance model','localized_shape_sigma_u_m':.00001,'localized_shape_center_u_m':.00098,'Gaussian_shape_is_not_Gaussian_random_noise':True,'actual_center_pattern_does_not_bound_arms':True,'actual_pattern_feature_delta':'native feature difference, not area from resampled base curve','mapping':'delta_q=pinv(frozen local J)*scaled response perturbation; tangent response sensitivity, NOT new SPT material inversion','no_material_estimates_or_refit':True,'Fisher_CI':'NOT_EVALUABLE','parameter_error_bound':'NOT_EVALUABLE','all_4_arms_time_step_convergence':'NOT_EVALUABLE'})
 print(json.dumps({'weak_xy':vw.tolist(),'halfstep_physical_tangent':direction['weak_halfstep_tangent'],'conceptual_halfstep_locations':direction['physical_coordinate_mapped_halfstep_locations'],'bands':[{'window':[b['lower_mm'],b['upper_mm']],'cos':b['cosine'],'s':b['singular_values'],'condition':b['condition_number'],'weak_N':b['interval_own_weak_halfstep_RMS_N'],'globalweak_N':b['same_global_weak_halfstep_RMS_N'],'center_over_ownweak':b['center_change_over_own_weak']} for b in bands],'scenario_records':len(scenario_rows)}))
if __name__=='__main__':main()
