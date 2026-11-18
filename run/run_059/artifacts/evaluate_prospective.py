"""Independent MAIN review and unchanged frozen A/B evaluation. No fitting or solver calls."""
from common import *
import math,traceback
import numpy as np
sys.path[:0]=[str(R),str(R/'run/run_057/artifacts'),str(R/'run/run_057/artifacts/private/frozen_predictor/code')]
from feature_core import extract,GRID,FIXED2,FIXED5,NAMES,physical_to_normalized
from prospective_metrics import local_secants,recovery_score
from predict_frozen import predict_file
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
from agenthub_sp_invopt.hub import Hub

def table(raw):
 lines=raw.splitlines();i=next(i for i,x in enumerate(lines) if x.strip().upper()==b'*PLASTIC')+1;j=i
 while j<len(lines) and not lines[j].lstrip().startswith(b'*'):j+=1
 return [tuple(map(float,l.split(b','))) for l in lines[i:j] if l.strip()]

def main():
 ids=read(P/'task_ids.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
 for cid,tid in ids['odb_task_ids'].items():assert hub.task(tid)['execution_state']=='COMPLETED',cid+' ODB not complete'
 audit=read(P/'execution_audit.json');numeric=read(P/'main_numerical_audit.json');frozen=read(R/'run/run_057/artifacts/prepared_batch.json');cc=read(R/frozen['comparison_contract_path']);before=read(P/'predictor_integrity_before_new_response.json')
 bundle=R/'run/run_057/artifacts/private/frozen_predictor';assert sha(bundle/'frozen_FE_only_inverse_models.json')==before['model_sha256'] and sha(R/frozen['predictor_package_path'])==before['package_sha256']
 for key in ['metric_implementation','inference_implementation']:assert sha(R/cc[key])==cc[key+'_sha256']
 binding=read(R/'run/run_030/artifacts/loss_contract_binding.json')
 for k in ['target','config','implementation']:assert sha(R/binding[k+'_path'])==binding[k+'_sha256']
 exp_rows=rows(R/binding['target_path'])[:241];u=np.array([float(x['displacement_m']) for x in exp_rows]);exp=np.array([float(x['force_n']) for x in exp_rows]);np.testing.assert_allclose(u,GRID,rtol=0,atol=3e-19)
 target=Target(Curve(tuple(u),tuple(exp),'m','N'),tuple([1.]*241),1428.9,binding['version'])
 base=cc['baseline'];assert sha(R/base['inp_path'])==base['inp_sha256'] and sha(R/base['odb_path'])==base['odb_sha256']
 base_rows=rows(R/base['fd_path']);bu=np.array([float(x['displacement_m']) for x in base_rows]);bf=np.array([float(x['force_n']) for x in base_rows]);feat0,f0,ex0=extract(bu,bf)
 curves={'I06':f0};features={'I06':feat0};native={'I06':{'u':bu.tolist(),'f':bf.tolist()}};checks=[];score=[]
 for p in audit['records']:
  cid=p['candidate_id'];folder=P/'odb'/cid
  try:
   result=read(folder/'result.json');ex=read(folder/'odb_extraction.json');diag=read(folder/'diagnostics.json');fd=rows(folder/'force_displacement.csv');raw=rows(folder/'raw_history.csv');peeq=rows(folder/'peeq_saved_frames.csv');num=next(x for x in numeric['records'] if x['candidate_id']==cid)
   for path,digest in result.get('artifact_hashes',{}).items():assert sha(R/path)==digest,path
   assert result['inp_sha256']==p['inp_sha256'] and result['odb_sha256']==p['files']['odb']['sha256'] and result['queue_id']==p['queue_id'] and result['job_name']==p['job_name']
   assert sha(R/p['inp_path'])==p['inp_sha256'] and sha(R/p['files']['odb']['path'])==p['files']['odb']['sha256']
   assert ex['source_sha256_before']==ex['source_sha256_after']==p['files']['odb']['sha256'] and ex['odb']['isReadOnly']
   assert ex['diagnostic_data']['jobStatus']=='JOB_STATUS_COMPLETED_SUCCESSFULLY' and ex['diagnostic_data']['numberOfAnalysisErrors']==0
   step=ex['steps']['Step_Punch_Displacement'];rp=step['history_regions']['Node ASM_SPT.1'];h=rp['outputs'];frames=step['frame_diagnostics']
   n=len(fd);assert n==len(raw)==len(frames)==len(peeq)==len(h['U2']['data'])==len(h['RF2']['data'])==num['accepted_increments']+1
   assert 'SET_PUNCH_RP' in rp['description'] and result['punch_rp_identity']['node_label']==1 and result['punch_rp_identity']['instance']=='ASM_SPT'
   uu=[];ff=[];field_errors=[];peeqvalues=[];contact_events=[]
   for i,(d,r,hu,hf,frame,pp) in enumerate(zip(fd,raw,h['U2']['data'],h['RF2']['data'],frames,peeq)):
    assert int(d['frame_index'])==int(r['frame_index'])==i and d['step']==r['step']=='Step_Punch_Displacement'
    assert float(r['U2_raw_m'])==hu[1] and float(r['RF2_raw_n'])==hf[1]
    assert float(r['step_time'])==hu[0]==hf[0]==frame['time']
    assert float(d['displacement_m'])==-hu[1] and float(d['force_n'])==-hf[1]
    assert frame['peeq_count_integration_point']==2376 and float(pp['max_peeq'])==frame['peeq_max']
    field_errors.append([abs(frame['rp_field']['U'][1]-hu[1]),abs(frame['rp_field']['RF'][1]-hf[1])]);uu.append(float(d['displacement_m']));ff.append(float(d['force_n']));peeqvalues.append(frame['peeq_max'])
    if i>0 and frame.get('contact',{}).get('available') and frames[i-1].get('contact',{}).get('available'):
     contact=frame['contact'];prev=frames[i-1]['contact'];new=set(contact['positive_cpress_node_labels'])-set(prev['positive_cpress_node_labels']);lost=set(prev['positive_cpress_node_labels'])-set(contact['positive_cpress_node_labels'])
     if new or lost:contact_events.append({'index':i,'increment':frame['increment'],'u_mm':uu[-1]*1000,'delta_force_N':ff[-1]-ff[-2],'new_positive_nodes':sorted(new),'lost_positive_nodes':sorted(lost),'max_cpress_Pa':contact['max_cpress']})
   assert max(x[0] for x in field_errors)==max(x[1] for x in field_errors)==0
   ru=np.array(uu);rf=np.array(ff);curve=Curve(tuple(uu),tuple(ff),'m','N');coverage=ru[0]<=0 and ru[-1]>=.0012 and float(raw[-1]['step_time'])==1
   feat,aligned,brackets=extract(ru,rf)
   maxp=float(max(peeqvalues));assert maxp==result['max_saved_peeq']
   pt=table((R/p['inp_path']).read_bytes());ms=ex['material_summary']['Q200N01'];assert ms['elastic']['first_row']==[210e9,.3] and ms['plastic']['row_count']==len(pt) and ms['plastic']['first_row']==list(pt[0]) and ms['plastic']['last_row']==list(pt[-1])
   assert pt[0]==(p['sigma_y_mpa']*1e6,0.) and pt[-1][1]==.9
   # Independently derive the full material digest from frozen INP data, not only endpoints.
   table_digest=hashlib.sha256(json.dumps([list(v) for v in pt],sort_keys=True).encode('utf-8')).hexdigest()
   assert table_digest==ms['plastic']['table_sha256']
   assert hashlib.sha256(json.dumps([[210e9,.3]],sort_keys=True).encode('utf-8')).hexdigest()==ms['elastic']['table_sha256']
   assert diag['identity_checks']['material_plastic'] and diag['identity_checks']['material_E_nu'] and diag['identity_checks']['material_yield_pmax']
   serious=[v for v in num['events'] if v['outcome']=='ACCEPTED_TRIAL' and v['class']!='ZERO_MOMENT']
   recoil=[{'index':i+1,'u_mm':float(ru[i+1]*1000),'delta_force_N':float(v)} for i,v in enumerate(np.diff(rf)) if v<0]
   blockers=[]
   if not p['software_completed'] or not p['single_attempt_confirmed']:blockers.append('EXECUTION_OR_ATTEMPT_IDENTITY')
   if not coverage:blockers.append('INCOMPLETE_FROZEN_WINDOW')
   if maxp>=.9:blockers.append('MATERIAL_RANGE_EXCEEDED')
   if serious:blockers.append('UNEXPLAINED_ACCEPTED_SERIOUS_WARNING')
   if recoil:blockers.append('NEGATIVE_ACCEPTED_FORCE_STEP_REVIEW')
   blockers+=result.get('numerical_blocking_issues',[])
   eligible=not blockers
   independent=np.array(interpolate(curve,u));np.testing.assert_allclose(independent,aligned,rtol=1e-14,atol=2e-11)
   loss=evaluate(target,curve,fe_status='COMPLETED_WITH_WARNINGS',evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True,numerical_quality_accepted=eligible),mode='PROVISIONAL')['loss'] if eligible else None
   rmse=float(np.sqrt(np.mean((aligned-exp)**2))) if eligible else None
   if eligible:assert abs(loss-np.mean(((aligned-exp)/1428.9)**2))<1e-15
   energy=rows(folder/'energy_history.csv');energy_end={k:float(v) for k,v in energy[-1].items()}
   du=np.diff(ru)*1000;df=np.diff(rf);slope=df/du;ratios=[]
   for i in range(1,len(slope)-1):
    reference=float(np.median(np.r_[slope[max(0,i-4):i],slope[i+1:min(len(slope),i+5)]]))
    if reference>0:ratios.append({'index':i+1,'increment':int(raw[i+1]['increment']),'u_start_mm':float(ru[i]*1000),'u_end_mm':float(ru[i+1]*1000),'force_change_N':float(df[i]),'slope_over_neighbor_median':float(slope[i]/reference)})
   top=sorted(ratios,key=lambda x:x['slope_over_neighbor_median'],reverse=True)[:8]
   for event in top:event['contact_event']=next((v for v in contact_events if v['index']==event['index']),None)
   records={'candidate_id':cid,'job_name':p['job_name'],'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'queue_id':p['queue_id'],'SOFTWARE_STATUS':p['software_phase'],'NUMERICAL_QUALITY':'WARNING' if eligible else 'BLOCKED','SCIENTIFIC_SCOREABILITY':'SCOREABLE_EXPLORATORY' if eligible else 'UNSCOREABLE','blocking_issues':blockers,'points':n,'max_saved_PEEQ':maxp,'material_pmax':.9,'cutbacks':num['cutback_count'],'rejected_attempts':num['rejected_attempts'],'accepted_increments':num['accepted_increments'],'warning_counts':num['warning_counts'],'runtime_s':p['actual_runtime_s'],'loss':loss,'RMSE_to_experiment_N':rmse,'NRMSE':rmse/1428.9 if rmse is not None else None,'RMSE_vs_I06_N':float(np.sqrt(np.mean((aligned-f0)**2))),'max_abs_difference_vs_I06_N':float(np.max(abs(aligned-f0))),'force_recoil':recoil,'contact_events':contact_events,'local_slope_peaks':top,'energy_final':energy_end,'ODB_hash':p['files']['odb']['sha256'],'INP_hash':p['inp_sha256']}
   score.append(records);checks.append({'candidate_id':cid,'status':'PASS_INDEPENDENT_IDENTITY_AND_DATA_REVIEW','RP':'Node ASM_SPT.1','raw_history_FD_sign_every_point_verified':True,'Field_History_max_errors':[0,0],'frame_count':n,'native_monotonic_displacement':True,'window_coverage':coverage,'numerical_event_independence':'MAIN raw STA/MSG parse versus ODB Agent result','artifact_hashes_verified':len(result.get('artifact_hashes',{})),'result_sha256':sha(folder/'result.json'),'scoreable':eligible})
   save(P/(cid+'_feature_interpolation_audit.json'),{'features':dict(zip(NAMES,feat.tolist())),'interpolation':brackets,'native_polyline_areas_not_resampled':True})
   if eligible:curves[cid]=aligned;features[cid]=feat;native[cid]={'u':uu,'f':ff}
  except Exception:
   score.append({'candidate_id':cid,'SCIENTIFIC_SCOREABILITY':'UNSCOREABLE','loss':None,'reason':'MAIN_INDEPENDENT_CHECK_FAILED','traceback':traceback.format_exc()})
 save(P/'main_independent_checks.json',{'checks':checks,'records':score,'I06_status':'QUALIFIED_WITH_LIMITATIONS','source_model_unchanged':True})
 save(P/'verified_response_arrays.json',{'grid_m':GRID.tolist(),'features':{k:v.tolist() for k,v in features.items()},'curves':{k:v.tolist() for k,v in curves.items()},'native':native,'experiment_N':exp.tolist()})
 csvsave(P/'job_scoreability_and_loss.csv',[{k:v for k,v in row.items() if not isinstance(v,(dict,list))} for row in score])
 views={'two_loads':list(FIXED2),'five_features':list(FIXED5),'full241':None,'early2_secondary':[0,1],'independent3_secondary':[0,1,10]}
 analysisA={};bands=[]
 if all(cid in curves for cid in ['P01','P02','P03','P04']):
  for name,columns in views.items():
   names=['I06','P01','P02','P03','P04']
   data=[curves[k] if columns is None else features[k][columns] for k in names]
   scales=np.ones(len(data[0]))*1428.9
   if columns is not None:
    for i,col in enumerate(columns):
     if 8<=col<12:scales[i]=1428.9/1.2
     elif col==16:scales[i]=1428.9*.0012
     elif col>=12:scales[i]=1428.9*.0003
   result=local_secants(*data,scales)
   J=np.array(result['J']);_,_,vt=np.linalg.svd(J,full_matrices=False)
   result['weak_direction_normalized_dx_dy']=vt[-1].tolist();result['columns']=columns;result['parameter_coordinates']=cc['parameter_normalization'];result['row_scales']=scales.tolist()
   result['engineering_flags']={'correlation_flag':abs(result['cosine'])>=.98,'condition_flag':result['condition_number'] is None or result['condition_number']>=20,'asymmetry_flag':any(v['even_odd_ratio'] is None or v['even_odd_ratio']>.2 for v in result['axes'].values())}
   if columns is None:
    result['weak_half_step_force_RMS_N']=float(.025*result['singular_values'][-1]*1428.9);result['engineering_flags']['weak_signal_le2N']=result['weak_half_step_force_RMS_N']<=2
   analysisA[name]=result
  sx=(curves['P02']-curves['P01'])/.05;sy=(curves['P04']-curves['P03'])/.05
  for lo,hi in [(0,.3),(.3,.6),(.6,.9),(.9,1.2)]:
   mask=(GRID*1000>=lo-1e-10)&((GRID*1000<hi-1e-10) if hi<1.2 else (GRID*1000<=hi+1e-10))
   bm=local_secants(*[curves[k][mask] for k in ['I06','P01','P02','P03','P04']],np.full(mask.sum(),1428.9))
   bands.append({'lo_mm':lo,'hi_mm':hi,'points':int(mask.sum()),'Sx_RMS_N_per_normalized_unit':float(np.sqrt(np.mean(sx[mask]**2))),'Sy_RMS_N_per_normalized_unit':float(np.sqrt(np.mean(sy[mask]**2))),'cosine':bm['cosine'],'angle_deg':bm['angle_deg'],'condition_number':bm['condition_number'],'weak_half_step_RMS_N':float(.025*bm['singular_values'][-1]*1428.9),'eta_x':bm['axes']['x']['even_odd_ratio'],'eta_y':bm['axes']['y']['even_odd_ratio']})
  csvsave(P/'finite_difference_force_vectors.csv',[{'u_m':float(v),'Sx_N_per_unit_x':float(sx[i]),'Sy_N_per_unit_y':float(sy[i]),'P01_minus_I06_N':float(curves['P01'][i]-f0[i]),'P02_minus_I06_N':float(curves['P02'][i]-f0[i]),'P03_minus_I06_N':float(curves['P03'][i]-f0[i]),'P04_minus_I06_N':float(curves['P04'][i]-f0[i])} for i,v in enumerate(GRID)])
 save(P/'study_A_local_secants.json',{'status':'COMPLETE_LOCAL_SECANTS_WITH_LIMITATIONS' if analysisA else 'NOT_EVALUABLE_MISSING_ADMISSIBLE_DIRECTIONS','views':analysisA,'bands':bands,'formal_time_step_and_h_convergence':'NOT_EVALUABLE','Fisher_CI':'NOT_EVALUABLE'})
 if bands:csvsave(P/'displacement_band_sensitivity.csv',bands)
 # Inference starts only after frozen integrity checkpoint and independent admission.
 frozen_models=read(bundle/'frozen_FE_only_inverse_models.json');training=read(bundle/'training_25.json')
 before_prediction=sha(bundle/'frozen_FE_only_inverse_models.json');predictions={};predrows=[];modelmetrics=[]
 base_prediction=predict_file(bundle,R/base['fd_path'])['predictions']
 for p in audit['records']:
  cid=p['candidate_id']
  if cid not in curves:continue
  result=predict_file(bundle,P/'odb'/cid/'force_displacement.csv');save(P/(cid+'_frozen_prediction.json'),result);predictions[cid]=result['predictions']
  for name,v in result['predictions'].items():
   trueq=physical_to_normalized(np.array([[p['sigma_y_mpa'],p['n']]]))[0];qpred=np.array([v['x'],v['y']]);qbase=np.array([base_prediction[name]['x'],base_prediction[name]['y']]);axis=0 if cid in ['P01','P02'] else 1
   truechange=trueq-np.array([.24,.16]);increment=qpred-qbase
   predrows.append({'candidate_id':cid,'model':name,'true_sigma_y_mpa':p['sigma_y_mpa'],'true_n':p['n'],'pred_sigma_y_mpa':v['sigma_y_mpa'],'pred_n':v['n'],'sigma_error_MPa':v['sigma_y_mpa']-p['sigma_y_mpa'],'n_error':v['n']-p['n'],'x_true':float(trueq[0]),'y_true':float(trueq[1]),'x_pred':v['x'],'y_pred':v['y'],'active_axis':'x' if axis==0 else 'y','true_active_change':float(truechange[axis]),'raw_prediction_active_change_from_true_I06':float(qpred[axis]-[.24,.16][axis]),'raw_active_amplitude_ratio':float((qpred[axis]-[.24,.16][axis])/truechange[axis]),'incremental_prediction_active_change':float(increment[axis]),'incremental_active_amplitude_ratio':float(increment[axis]/truechange[axis]),'incremental_inactive_leakage_per_step':float(increment[1-axis]/.025),'incremental_direction_correct':bool(np.sign(increment[axis])==np.sign(truechange[axis]) and abs(increment[axis])>1e-12),'input_parameter_hull_status':'OUTSIDE_TRAINING_HULL' if p['outside_observed_parameter_hull'] else 'INSIDE_TRAINING_HULL','prediction_domain':json.dumps(v.get('domain',{}))})
 if len(predictions)==4:
  truth=np.array([[p['sigma_y_mpa'],p['n']] for p in audit['records']])
  for name in ['constant_I06_parameters','two_ridge','five_ridge','full_ridge']:
   predicted=np.array([[predictions[p['candidate_id']][name]['sigma_y_mpa'],predictions[p['candidate_id']][name]['n']] for p in audit['records']]);metric=recovery_score(predicted,truth)
   # Independent scalar formula verification, without fitting anything.
   e=predicted-truth;np.testing.assert_allclose(metric['MAE_MPa_n'],np.mean(abs(e),0),rtol=1e-14,atol=1e-14)
   if name!='constant_I06_parameters':
    m=frozen_models['models'][name];spec=m['model'];DD=np.array([curves[p['candidate_id']] if m['input']=='full' else features[p['candidate_id']] for p in audit['records']]);zz=(DD[:,spec['columns']]-np.array(spec['mean']))/np.array(spec['scale']);qcalc=zz@np.array(spec['coefficients'])+np.array(spec['target_intercept']);np.testing.assert_allclose(qcalc,physical_to_normalized(predicted),rtol=1e-12,atol=1e-12)
   mine=[r for r in predrows if r['model']==name];metric.update(model=name,raw_direction_correct_count=sum(metric['active_axis_sign_correct']),incremental_direction_correct_count=sum(r['incremental_direction_correct'] for r in mine),incremental_active_amplitude_ratios=[r['incremental_active_amplitude_ratio'] for r in mine]);modelmetrics.append(metric)
  baseline_metric=modelmetrics[0]
  for v in modelmetrics:
   v['MAE_ratio_vs_constant']=[a/b if b>0 else None for a,b in zip(v['MAE_MPa_n'],baseline_metric['MAE_MPa_n'])]
   v['RMSE_ratio_vs_constant']=[a/b if b>0 else None for a,b in zip(v['RMSE_MPa_n'],baseline_metric['RMSE_MPa_n'])]
 assert sha(bundle/'frozen_FE_only_inverse_models.json')==before_prediction==before['model_sha256']
 csvsave(P/'prospective_parameter_predictions.csv',predrows)
 save(P/'study_B_frozen_parameter_recovery.json',{'status':'EVALUATED' if len(predictions)==4 else 'PARTIAL_OR_NOT_EVALUABLE','metrics':modelmetrics,'prediction_count':len(predrows),'frozen_model_sha256_before':before_prediction,'frozen_model_sha256_after':sha(bundle/'frozen_FE_only_inverse_models.json'),'no_training_or_tuning':True,'truths_are_FE_inputs_not_measured_material_parameters':True,'P03':'OUTSIDE_TRAINING_HULL','incremental_results_are_diagnostics_not_recentered_predictions':True})
 csvsave(P/'prospective_model_metrics.csv',[{'model':v['model'],'sigma_MAE_MPa':v['MAE_MPa_n'][0],'sigma_RMSE_MPa':v['RMSE_MPa_n'][0],'n_MAE':v['MAE_MPa_n'][1],'n_RMSE':v['RMSE_MPa_n'][1],'max_sigma_error_MPa':v['max_abs_error_MPa_n'][0],'max_n_error':v['max_abs_error_MPa_n'][1],'raw_direction_correct':v['raw_direction_correct_count'],'incremental_direction_correct':v['incremental_direction_correct_count'],'E_local':v['E_local'],'beats_constant':v['beats_constant_I06'],'resolution_goal':v['engineering_resolution_goal_met']} for v in modelmetrics])
 print(json.dumps({'scoreable':len(curves)-1,'conditions':{k:v['condition_number'] for k,v in analysisA.items()},'metrics':[{'model':v['model'],'MAE':v['MAE_MPa_n'],'RMSE':v['RMSE_MPa_n'],'E_local':v['E_local'],'resolution_goal':v['engineering_resolution_goal_met']} for v in modelmetrics]}))

if __name__=='__main__':main()
