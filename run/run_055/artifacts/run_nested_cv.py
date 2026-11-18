"""Nested held-out parameter recovery. No experimental curve is read here."""
from pathlib import Path
import sys,json,csv,hashlib,time
from datetime import datetime,timezone,timedelta
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_055/artifacts/private'
from feature_core import physical_to_normalized,normalized_to_physical,NAMES,FIXED2,FIXED5
from inverse_baselines import inner_cache,tune,select_views,fit_model,predict_model,support
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def models_for_training(X,F,Y,physical,light=False):
 specs=select_views(X,Y) if not light else {k:tune(inner_cache(X,Y),[c]) for k,c in [('two_ridge',FIXED2),('five_ridge',FIXED5)]}
 specs['full_ridge']=tune(inner_cache(F,Y),[tuple(range(F.shape[1]))]);models={}
 for name,s in specs.items():
  A=F if name.startswith('full') else X;models[name]={'input':'full' if name.startswith('full') else 'features','selection':s,'model':fit_model(A,Y,'ridge',s['columns'],s['lambda'])}
 if not light:
  for name,cols,A in [('two_nn',FIXED2,X),('five_nn',FIXED5,X),('full_nn',None,F)]:models[name]={'input':'full' if name.startswith('full') else 'features','selection':None,'model':fit_model(A,Y,'nn',cols)}
  for name in ['mean','median']:models[name]={'input':'features','selection':None,'model':fit_model(X,Y,name,[],physical=physical)}
 return models
def metrics(rows):
 out=[]
 for name in sorted(set(r['model'] for r in rows)):
  rs=[r for r in rows if r['model']==name];true=np.array([[r['true_sigma_y_mpa'],r['true_n']] for r in rs]);pred=np.array([[r['pred_sigma_y_mpa'],r['pred_n']] for r in rs]);e=pred-true;rel=abs(e)/true;worst=[int(np.argmax(abs(e[:,i]))) for i in range(2)]
  out.append({'model':name,'test_groups':len(rs),'sigma_MAE_MPa':float(np.mean(abs(e[:,0]))),'sigma_RMSE_MPa':float(np.sqrt(np.mean(e[:,0]**2))),'sigma_MAPE_percent':float(np.mean(rel[:,0])*100),'sigma_max_abs_MPa':float(max(abs(e[:,0]))),'sigma_worst_id':rs[worst[0]]['sample_id'],'n_MAE':float(np.mean(abs(e[:,1]))),'n_RMSE':float(np.sqrt(np.mean(e[:,1]**2))),'n_MAPE_percent':float(np.mean(rel[:,1])*100),'n_max_abs':float(max(abs(e[:,1]))),'n_worst_id':rs[worst[1]]['sample_id'],'parameter_bounds_violations':sum(r['pred_outside_frozen_parameter_bounds'] for r in rs),'distance_domain_flags':sum(r['distance_exceeds_q95'] for r in rs),'heldout_feature_range_flags':sum(r['feature_marginal_outside_count']>0 for r in rs),'normalized_target_MSE':float(np.mean([r['normalized_MSE'] for r in rs]))})
 return out
def run(ids,arrays,light=False,external=False):
 X=np.array([arrays['features'][i] for i in ids]);F=np.array([arrays['curves'][i] for i in ids]);physical=np.array([arrays['targets'][i] for i in ids]);Y=physical_to_normalized(physical);out=[];folds=[];variants=[]
 for i,pid in enumerate(ids):
  ix=np.arange(len(ids))!=i;train=[x for j,x in enumerate(ids) if j!=i];assert pid not in train
  trained=models_for_training(X[ix],F[ix],Y[ix],physical[ix],light);fold={'test_parameter_group':pid,'train_parameter_groups':train,'models':{name:{'input':v['input'],'selection':v['selection']} for name,v in trained.items()}};folds.append(fold)
  for name,v in trained.items():
   A=F if v['input']=='full' else X;q=A[i];m=v['model'];pn=predict_model(m,q)[0];pp=normalized_to_physical([pn])[0];sup=support(m,A[ix],q) if name not in ['mean','median'] else {'distance_exceeds_q95':False,'feature_marginal_outside_count':0,'distance_RMS_standardized':0,'train_nearest_LOO_distance_q95':0,'nearest_train_index':0}
   out.append({'sample_id':pid,'model':name,'true_sigma_y_mpa':float(physical[i,0]),'true_n':float(physical[i,1]),'pred_sigma_y_mpa':float(pp[0]),'pred_n':float(pp[1]),'sigma_error_MPa':float(pp[0]-physical[i,0]),'n_error':float(pp[1]-physical[i,1]),'sigma_relative_abs_error':float(abs(pp[0]-physical[i,0])/physical[i,0]),'n_relative_abs_error':float(abs(pp[1]-physical[i,1])/physical[i,1]),'normalized_MSE':float(np.mean((pn-Y[i])**2)),'pred_outside_frozen_parameter_bounds':bool(not(0<=pn[0]<=1 and 0<=pn[1]<=1)),'selected_columns':json.dumps(m['columns']),'selected_names':json.dumps([NAMES[j] for j in m['columns']]) if v['input']=='features' else 'full241','lambda':m['lambda'],'nearest_training_id':train[sup['nearest_train_index']],**{k:x for k,x in sup.items() if k!='nearest_train_index'}})
   if external and pid in ['D01','I08']:
    vid=pid+'_REFINED';q=np.array(arrays['curves'][vid] if v['input']=='full' else arrays['features'][vid]);vp=normalized_to_physical(predict_model(m,q))[0]
    variants.append({'sample_id':pid,'variant':vid,'model':name,'group_absent_from_training':True,'original_pred_sigma_MPa':float(pp[0]),'refined_pred_sigma_MPa':float(vp[0]),'sigma_prediction_shift_MPa':float(vp[0]-pp[0]),'original_pred_n':float(pp[1]),'refined_pred_n':float(vp[1]),'n_prediction_shift':float(vp[1]-pp[1]),'not_independent_sample':True})
  print(json.dumps({'cohort_N':len(ids),'outer_completed':i+1,'test':pid}),flush=True)
 return out,folds,variants
def main():
 t=time.perf_counter();arrays=read(P/'feature_arrays.json');inventory=read(P/'sample_inventory.json');ids=arrays['primary_ids'];assert len(ids)>=12
 # Protocol/fold identity is frozen before any model fitting.
 save(P/'cv_protocol_identity.json',{'at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat(),'feature_protocol_sha256':sha(P/'feature_protocol.md'),'feature_array_sha256':sha(P/'feature_arrays.json'),'inventory_sha256':sha(P/'sample_inventory.json'),'primary_ids':ids,'outer_folds':[{'test':x,'train':[y for y in ids if y!=x]} for x in ids],'ridge_objective':'sum squared normalized-target error/N + lambda*coefficient squared penalty; intercept unpenalized','lambda_grid':[1e-4,.01,1,100],'experiment_read':False})
 out,folds,variants=run(ids,arrays,external=True);save(P/'outer_fold_details.json',folds);csvsave(P/'inverse_cv_results.csv',out);summary=metrics(out);csvsave(P/'inverse_cv_metrics.csv',summary);csvsave(P/'numerical_duplicate_prediction_checks.csv',variants)
 # Cohort sensitivity: same fixed ridge rules, no different features selected from test errors.
 strict_ids=inventory['historical24_ids'];strict,strictfolds,_=run(strict_ids,arrays,light=True);csvsave(P/'strict24_cv_results.csv',strict);csvsave(P/'strict24_cv_metrics.csv',metrics(strict));save(P/'strict24_fold_details.json',strictfolds)
 X=np.array([arrays['features'][i] for i in ids]);F=np.array([arrays['curves'][i] for i in ids]);physical=np.array([arrays['targets'][i] for i in ids]);Y=physical_to_normalized(physical);final=models_for_training(X,F,Y,physical)
 save(P/'frozen_FE_only_inverse_models.json',{'version':'run055-feature-inverse-v1','feature_protocol_sha256':sha(P/'feature_protocol.md'),'training_ids':ids,'feature_names':NAMES,'models':final,'experiment_used_for_fit_or_selection':False,'no_material_or_Hollomon_refitting':True})
 save(P/'cv_completion.json',{'at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat(),'primary_groups':len(ids),'outer_predictions':len(out),'strict24_predictions':len(strict),'duration_s':time.perf_counter()-t,'outer_target_never_in_training':True,'feature_and_hyperparameter_selection':'innerLOO only; fold-local standardization','experimental_application_allowed_only_after_this_checkpoint':True,'frozen_model_sha256':sha(P/'frozen_FE_only_inverse_models.json'),'inverse_cv_sha256':sha(P/'inverse_cv_results.csv'),'reporting_scope':'PARTIAL small-sample FE parameter recovery, no experimental material truth'})
 print(json.dumps({'summary':summary,'elapsed_s':time.perf_counter()-t}),flush=True)
if __name__=='__main__':main()
