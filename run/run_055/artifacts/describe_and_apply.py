"""Post-CV descriptive analyses and frozen-model SPT application, no tuning."""
from pathlib import Path
import csv,json,hashlib,os,itertools
from collections import Counter
import numpy as np
from scipy.stats import pearsonr,spearmanr
from scipy.spatial import Delaunay
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_055/artifacts/private';os.environ['MPLCONFIGDIR']=str(P/'mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from feature_core import NAMES,FIXED2,FIXED5,GRID,LOAD_MM,AREA_MM,extract,physical_to_normalized,normalized_to_physical
from inverse_baselines import predict_model,support
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def residualize(y,x):
 A=np.column_stack([np.ones(len(x)),x]);return y-A@np.linalg.lstsq(A,y,rcond=None)[0]
def main():
 arrays=read(P/'feature_arrays.json');inv=read(P/'sample_inventory.json');ids=arrays['primary_ids'];X=np.array([arrays['features'][i] for i in ids]);F=np.array([arrays['curves'][i] for i in ids]);T=np.array([arrays['targets'][i] for i in ids]);Y=physical_to_normalized(T)
 corrs=[];interactions=[]
 targets={'sigma_y_mpa':T[:,0],'n':T[:,1],'x':Y[:,0],'y':Y[:,1],'x_times_y':Y[:,0]*Y[:,1]}
 for j,name in enumerate(NAMES):
  for target,v in targets.items():corrs.append({'feature':name,'target':target,'Pearson':float(pearsonr(X[:,j],v).statistic),'Spearman':float(spearmanr(X[:,j],v).statistic),'sample_count':len(ids),'scope':'DESCRIPTIVE_NONRANDOM_DESIGN_NOT_IDENTIFIABILITY'})
  z=(X[:,j]-X[:,j].mean())/X[:,j].std();D=np.column_stack([np.ones(len(Y)),Y[:,0],Y[:,1],Y[:,0]*Y[:,1]]);B=np.linalg.lstsq(D,z,rcond=None)[0]
  interactions.append({'feature':name,'partial_Pearson_x_controlling_y':float(pearsonr(residualize(X[:,j],Y[:,1]),residualize(Y[:,0],Y[:,1])).statistic),'partial_Pearson_y_controlling_x':float(pearsonr(residualize(X[:,j],Y[:,0]),residualize(Y[:,1],Y[:,0])).statistic),'descriptive_forward_x_coefficient':float(B[1]),'descriptive_forward_y_coefficient':float(B[2]),'descriptive_forward_xy_coefficient':float(B[3]),'not_out_of_sample_prediction':True})
 csvsave(P/'feature_parameter_correlations.csv',corrs);csvsave(P/'feature_partial_associations.csv',interactions)
 redundancy=np.corrcoef(X,rowvar=False);csvsave(P/'feature_redundancy_matrix.csv',[{'feature':name,**{k:float(redundancy[i,j]) for j,k in enumerate(NAMES)}} for i,name in enumerate(NAMES)])
 # Pair ambiguity criteria were fixed before CV; do not interpret as measured noise.
 pairs=[]
 for i,j in itertools.combinations(range(len(ids)),2):
  dp=float(np.linalg.norm(Y[i]-Y[j]));v2=float(np.sqrt(np.mean((X[i,list(FIXED2)]-X[j,list(FIXED2)])**2)));full=float(np.sqrt(np.mean((F[i]-F[j])**2)))
  pairs.append({'id_a':ids[i],'id_b':ids[j],'sigma_a':float(T[i,0]),'sigma_b':float(T[j,0]),'n_a':float(T[i,1]),'n_b':float(T[j,1]),'normalized_parameter_distance':dp,'two_load_RMS_difference_N':v2,'full_curve_RMS_difference_N':full,'two_ambiguity_flag':bool(v2/1428.9<=.02 and dp>=.15),'full_ambiguity_flag':bool(full/1428.9<=.02 and dp>=.15),'relative_force_floor_not_noise':.02})
 pairs.sort(key=lambda x:(not x['two_ambiguity_flag'],x['two_load_RMS_difference_N']));csvsave(P/'parameter_ambiguity_pairs.csv',pairs)
 # Old local same-center/secant matrix, with feature-specific physical scaling.
 oldfe={k:np.array(arrays['features'][k]) for k in ['L01','L02','L03','L04']};sx=(oldfe['L02']-oldfe['L01'])/.1;sy=(oldfe['L04']-oldfe['L03'])/.1
 scales=np.array([1428.9]*8+[1428.9/1.2]*4+[1428.9*(b-a)/1000 for a,b in AREA_MM]);local=[]
 for c in itertools.combinations(range(8),2):
  J=np.column_stack([sx[list(c)],sy[list(c)]])/scales[list(c),None];sv=np.linalg.svd(J,compute_uv=False);local.append({'features':json.dumps([NAMES[k] for k in c]),'condition_number_old_center_only':float(sv[0]/sv[-1]),'singular_value_1':float(sv[0]),'singular_value_2':float(sv[-1]),'scope':'EXPLORATORY_200MPa_n.1_initial.01_max.1;notD01Jacobian/FIM'})
 local.sort(key=lambda x:x['condition_number_old_center_only']);csvsave(P/'old_center_feature_secants.csv',local)
 # CV domains are diagnostics after prediction, never information available during training.
 cv=rows(P/'inverse_cv_results.csv');domain=[]
 for r in cv:
  pid=r['sample_id'];idx=ids.index(pid);train=Y[np.arange(len(ids))!=idx];hull=Delaunay(train);pred=physical_to_normalized([[float(r['pred_sigma_y_mpa']),float(r['pred_n'])]])[0]
  domain.append({'sample_id':pid,'model':r['model'],'true_parameter_outside_train_hull':bool(hull.find_simplex(Y[idx])<0),'pred_parameter_outside_train_hull':bool(hull.find_simplex(pred)<0),'outer_point_not_used_for_prediction':True})
 csvsave(P/'cv_parameter_support.csv',domain)
 frozen=read(P/'frozen_FE_only_inverse_models.json');completion=read(P/'cv_completion.json');assert sha(P/'frozen_FE_only_inverse_models.json')==completion['frozen_model_sha256'] and sha(P/'inverse_cv_results.csv')==completion['inverse_cv_sha256']
 # Only here, after CV and model freeze, read already public-for-inversion SPT.
 binding=read(R/'run/run_051/artifacts/comparison_contract.json')['loss_binding'];target=R/binding['target_path'];assert sha(target)==binding['target_sha256'];exp=rows(target);u=np.array([float(x['displacement_m']) for x in exp]);f=np.array([float(x['force_n']) for x in exp]);ef,eg,ediag=extract(u,f)
 application=[];nuisance=[];hull=Delaunay(Y)
 for name,v in frozen['models'].items():
  A=F if v['input']=='full' else X;q=eg if v['input']=='full' else ef;m=v['model'];pn=predict_model(m,q)[0];pp=normalized_to_physical([pn])[0]
  sup=support(m,A,q) if name not in ['mean','median'] else {'nearest_train_index':0,'distance_RMS_standardized':None,'train_nearest_LOO_distance_q95':None,'distance_exceeds_q95':False,'feature_marginal_outside_count':0}
  outside=bool(np.any(pn<0)|np.any(pn>1));ph=bool(hull.find_simplex(pn)<0);flag=outside or ph or sup['distance_exceeds_q95'] or sup['feature_marginal_outside_count']>0
  application.append({'model':name,'sigma_y_estimate_MPa':float(pp[0]),'n_estimate':float(pp[1]),'pred_outside_parameter_bounds':outside,'pred_outside_parameter_training_hull':ph,'applicability':'OUT_OF_DOMAIN' if flag else 'UNRESOLVED_NO_MATERIAL_VALIDATION','nearest_train_id':ids[sup['nearest_train_index']] if name not in ['mean','median'] else None,**{k:x for k,x in sup.items() if k!='nearest_train_index'},'experiment_used_for_tuning':False,'scope':'exploratorySPTinput;nottrueSA508parameters'})
  # High-strain envelopes are known different material family even if features look in-domain.
  for vid in ['H01','H02']:
   qv=np.array(arrays['curves'][vid] if v['input']=='full' else arrays['features'][vid]);pv=normalized_to_physical(predict_model(m,qv))[0]
   nuisance.append({'variant':vid,'model':name,'apparent_sigma_MPa':float(pv[0]),'apparent_n':float(pv[1]),'family':'OUT_OF_DOMAIN_BY_MATERIAL_FORM','never_training_or_material_parameter_accuracy_score':True})
 csvsave(P/'experimental_feature_application.csv',application);csvsave(P/'high_strain_nuisance_predictions.csv',nuisance);save(P/'experimental_application_provenance.json',{'model_sha256_before':completion['frozen_model_sha256'],'model_sha256_after':sha(P/'frozen_FE_only_inverse_models.json'),'CV_complete_before_experiment_read':True,'target_path':binding['target_path'],'target_sha256':binding['target_sha256'],'raw_experimental_rows':len(exp),'features':dict(zip(NAMES,map(float,ef))),'extraction':ediag,'no_tensile_used':True})
 selections=Counter()
 for fold in read(P/'outer_fold_details.json'):
  for name in ['nested_two_ridge','nested_four_ridge']:
   for col in fold['models'][name]['selection']['columns']:selections[(name,NAMES[col])]+=1
 csvsave(P/'nested_selection_frequencies.csv',[{'model':k[0],'feature':k[1],'outer_training_folds_selected':v} for k,v in selections.items()])
 # All plots describe FE/test predictions, not training goodness of fit.
 fig,ax=plt.subplots(figsize=(8,4.8));k=ids.index('D01');ax.plot(GRID*1000,F[k],label='D01 actual FE');ax.scatter(LOAD_MM,np.interp(np.array(LOAD_MM)/1000,GRID,F[k]),c='red',label='preset load features')
 for x in [.3,.6,.9]:ax.axvline(x,color='grey',lw=.7,ls='--')
 ax.set(xlabel='Displacement (mm)',ylabel='Force (N)',title='Feature locations; unshifted, unsmoothed FE curve');ax.legend();fig.tight_layout();fig.savefig(P/'feature_locations.png',dpi=170);plt.close(fig)
 for col,label,other in [(0,'sigma_y (MPa)',T[:,1]),(1,'n',T[:,0])]:
  fig,axes=plt.subplots(3,6,figsize=(18,10));axes=axes.ravel()
  for j,name in enumerate(NAMES):
   im=axes[j].scatter(T[:,col],X[:,j],c=other,cmap='viridis',s=18);axes[j].set(xlabel=label,ylabel=name)
  axes[-1].axis('off');fig.suptitle('FE associations; color = other parameter; nonrandom designed cohort');fig.tight_layout();fig.savefig(P/('feature_scatter_sigma.png' if col==0 else 'feature_scatter_n.png'),dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(redundancy,vmin=-1,vmax=1,cmap='coolwarm');ax.set_xticks(range(17),NAMES,rotation=90,fontsize=7);ax.set_yticks(range(17),NAMES,fontsize=7);fig.colorbar(im,ax=ax,label='Pearson (descriptive)');fig.tight_layout();fig.savefig(P/'feature_redundancy_heatmap.png',dpi=170);plt.close(fig)
 met=rows(P/'inverse_cv_metrics.csv');chosen=['mean','two_nn','two_ridge','five_ridge','nested_two_ridge','nested_four_ridge','full_nn','full_ridge'];mm={x['model']:x for x in met};fig,axs=plt.subplots(1,2,figsize=(13,4.8))
 for ax,key,label in [(axs[0],'sigma_MAE_MPa','sigma MAE (MPa)'),(axs[1],'n_MAE','n MAE')]:ax.bar(range(len(chosen)),[float(mm[n][key]) for n in chosen]);ax.set_xticks(range(len(chosen)),chosen,rotation=45,ha='right');ax.set_ylabel(label)
 fig.suptitle('Outer leave-one-parameter-out errors; inner tuning only');fig.tight_layout();fig.savefig(P/'inverse_cv_errors.png',dpi=170);plt.close(fig)
 fig,axs=plt.subplots(2,3,figsize=(12,8))
 for j,name in enumerate(['two_ridge','five_ridge','full_ridge']):
  rr=[x for x in cv if x['model']==name]
  for i,(t,p,label) in enumerate([('true_sigma_y_mpa','pred_sigma_y_mpa','sigma_y (MPa)'),('true_n','pred_n','n')]):
   a=axs[i,j];tr=np.array([float(x[t]) for x in rr]);pr=np.array([float(x[p]) for x in rr]);a.scatter(tr,pr);lim=[min(tr.min(),pr.min()),max(tr.max(),pr.max())];a.plot(lim,lim,'k--');a.set(xlabel='Held-out true '+label,ylabel='Out-of-fold prediction',title=name)
 fig.tight_layout();fig.savefig(P/'true_vs_heldout_parameters.png',dpi=170);plt.close(fig)
 case=next(x for x in pairs if {x['id_a'],x['id_b']}=={'D01','I08'});fig,axs=plt.subplots(1,2,figsize=(11,4.5))
 for pid in ['D01','I08']:
  ix=ids.index(pid);axs[0].plot(GRID*1000,F[ix],label=pid);axs[1].scatter(T[ix,0],T[ix,1],label=pid,s=80)
 axs[0].set(xlabel='Displacement (mm)',ylabel='Actual FE force (N)');axs[1].set(xlabel='sigma_y (MPa)',ylabel='n')
 for ax in axs:ax.legend();ax.grid(alpha=.2)
 fig.suptitle('Competitive constitutive parameters; close FE responses, not uniqueness proof');fig.tight_layout();fig.savefig(P/'parameter_ambiguity_D01_I08.png',dpi=170);plt.close(fig)
 standardized=(X-X.mean(0))/X.std(0);sv=np.linalg.svd(standardized,compute_uv=False);nullareas=float(np.max(abs(X[:,16]-X[:,12:16].sum(1))))
 summary={'parameter_design_Pearson_x_y':float(pearsonr(Y[:,0],Y[:,1]).statistic),'parameter_design_Pearson_sigma_n':float(pearsonr(T[:,0],T[:,1]).statistic),'primary_bounds':{'sigma_min_max':T[:,0].min().item().__class__ and [float(T[:,0].min()),float(T[:,0].max())],'n_min_max':[float(T[:,1].min()),float(T[:,1].max())]},'redundancy_pairs_abs_corr_above_0p98':int(np.sum(np.abs(redundancy[np.triu_indices(17,1)])>.98)),'redundancy_total_pairs':136,'feature_standardized_singular_values':sv.tolist(),'slopes_exactly_dependent_on_load_endpoints':True,'area_total_minus_bands_max_abs_J':nullareas,'ambiguous_two_force_pairs':sum(x['two_ambiguity_flag'] for x in pairs),'ambiguous_full_curve_pairs':sum(x['full_ambiguity_flag'] for x in pairs),'D01_I08_pair':case,'old_center_feature_secant_min_condition':local[0],'old_center_fixed2_condition':next(x for x in local if json.loads(x['features'])==[NAMES[j] for j in FIXED2]),'formal_D01_Jacobian':'NOT_EVALUABLE','formal_Fisher':'NOT_EVALUABLE','formal_confidence_intervals':'NOT_EVALUABLE','experimental_application_status_counts':dict(Counter(x['applicability'] for x in application)),'experimental_models_not_retuned':True}
 save(P/'descriptive_summary.json',summary)
 print(json.dumps({'summary':summary,'application':[x for x in application if x['model'] in ['two_ridge','five_ridge','full_ridge']]}))
if __name__=='__main__':main()
