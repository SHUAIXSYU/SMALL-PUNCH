"""Frozen H4 heldout arithmetic. No fitting or feature/threshold selection."""
from pathlib import Path
import json,csv,itertools
import numpy as np

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def write(p,r):
 if not r:return
 with Path(p).open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(r[0]),lineterminator='\n');w.writeheader();w.writerows(r)
def rms(x):return float(np.sqrt(np.mean(np.asarray(x,dtype=float)**2)))
def diameter(ids,Q):
 if not ids:return {'n':0,'Q_n':0,'D_Q_MPa':None,'geometric_D_Q_MPa':None,'status':'EMPTY','pair':[]}
 n=len({tuple(np.round(Q[i],10)) for i in ids})
 if n==1:return {'n':len(ids),'Q_n':1,'D_Q_MPa':None,'geometric_D_Q_MPa':0.,'status':'SINGLE_TARGET_NOT_UNIQUENESS','pair':[]}
 d,i,j=max((rms(Q[i]-Q[j]),i,j) for i,j in itertools.combinations(ids,2));return {'n':len(ids),'Q_n':n,'D_Q_MPa':d,'geometric_D_Q_MPa':d,'status':'FINITE_POOL','pair':[i,j]}
def analyze(data,out):
 D=Path(data);O=Path(out);O.mkdir(exist_ok=True,parents=True);jobs=rows(D/'jobs.csv');ids=['I06_L2']+[r['candidate_id'] for r in jobs];fd=rows(D/'fd_actual_241.csv');u=np.array([float(r['u_mm']) for r in fd]);F={i:np.array([float(r[i+'_N']) for r in fd]) for i in ids};qr=rows(D/'target_Q_981.csv');eps=np.array([float(r['true_total_strain']) for r in qr]);Q={i:np.array([float(r[i+'_MPa']) for r in qr]) for i in ids};sh=rows(D/'shape_actual.csv');g={i:float(next(r for r in sh if r['case']==i and float(r['target_u_mm'])==1.2)['shape_mm'])*1000 for i in ids};pf=rows(D/'frozen_FD_241.csv');pred={i:np.array([float(r[i+'_predicted_N']) for r in pf]) for i in ids if i!='I06_L2'};pred['I06_L2']=F['I06_L2'];pg=rows(D/'frozen_shape_stages.csv');ghat={i:1000*float(next(r for r in pg if r['candidate_id']==i and float(r['target_u_mm'])==1.2)['predicted_g_mm']) for i in ids if i!='I06_L2'};ghat['I06_L2']=g['I06_L2'];fixed={'I06_L2'}|{r['candidate_id'] for r in jobs if float(r['c3'])==0};summary=[];seg=[];segments=[(0,.3),(.3,.6),(.6,.9),(.9,1.2)]
 dist={i:rms(F[i]-F['I06_L2']) for i in ids};pdist={i:rms(pred[i]-F['I06_L2']) for i in ids};gd={i:g[i]-g['I06_L2'] for i in ids};pd={i:ghat[i]-g['I06_L2'] for i in ids};pe=[]
 for job in jobs:
  i=job['candidate_id'];diff=F[i]-F['I06_L2'];err=F[i]-pred[i];j=int(np.argmax(abs(diff)));summary.append({**job,'actual_FD_RMS_to_I06_N':dist[i],'predicted_FD_RMS_to_I06_N':pdist[i],'actual_minus_predicted_RMS_N':dist[i]-pdist[i],'curve_prediction_RMSE_N':rms(err),'max_curve_prediction_error_N':float(max(abs(err))),'actual_max_abs_diff_N':float(abs(diff[j])),'actual_max_abs_diff_u_mm':float(u[j]),'actual_g_um':g[i],'actual_g_minus_I06_um':gd[i],'predicted_g_um':ghat[i],'predicted_g_minus_I06_um':pd[i],'g_prediction_error_um':g[i]-ghat[i],'d_Q_to_I06_MPa':rms(Q[i]-Q['I06_L2']),'actual_max_force_N':float(F[i].max()),'max_force_at_mm':float(u[np.argmax(F[i])])})
  for lo,hi in segments:
   mask=(u>=lo-1e-12)&(u<=hi+1e-12);seg.append({'candidate_id':i,'u_min_mm':lo,'u_max_mm':hi,'points':int(mask.sum()),'actual_RMS_to_I06_N':rms(diff[mask]),'predicted_RMS_to_I06_N':rms((pred[i]-F['I06_L2'])[mask]),'prediction_curve_RMSE_N':rms(err[mask]),'max_abs_diff_N':float(max(abs(diff[mask]))),'mean_signed_diff_N':float(diff[mask].mean())})
  for uu in [.3,.6,.9,1.2]:
   a=next(r for r in sh if r['case']==i and float(r['target_u_mm'])==uu);p=next(r for r in pg if r['candidate_id']==i and float(r['target_u_mm'])==uu);pe.append({'candidate_id':i,'punch_u_mm':uu,'actual_w1_mm':float(a['w1_mm']),'actual_w2_mm':float(a['w2_mm']),'actual_g_mm':float(a['shape_mm']),'frozen_predicted_g_mm':float(p['predicted_g_mm']),'prediction_error_um':1000*(float(a['shape_mm'])-float(p['predicted_g_mm']))})
 write(O/'results.csv',summary);write(O/'segment_comparison.csv',seg);write(O/'shape_predictions_vs_actual.csv',pe)
 pair=[]
 for i,j in itertools.combinations(ids,2):
  df=F[i]-F[j];ix=int(np.argmax(abs(df)));dq=Q[i]-Q[j];eq=int(np.argmax(abs(dq)));pair.append({'case_a':i,'case_b':j,'a_FD_RMS_to_I06_N':dist[i],'b_FD_RMS_to_I06_N':dist[j],'direct_pair_FD_RMS_N':rms(df),'direct_max_force_difference_N':float(abs(df[ix])),'max_force_diff_at_mm':float(u[ix]),'direct_shape_difference_um':abs(g[i]-g[j]),'signed_shape_difference_um':g[i]-g[j],'direct_d_Q_MPa':rms(dq),'max_target_stress_difference_MPa':float(abs(dq[eq])),'max_target_diff_strain':float(eps[eq])})
 write(O/'pairwise_distances.csv',pair)
 scenarios=[];members=[];margins=[];envelope_rows=[{'true_total_strain':float(e)} for e in eps];classification=[];maxchecks=0
 for tf,tw,fam in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.],['fixed','free']):
  family=[i for i in ids if fam=='free' or i in fixed];fdids=[i for i in family if dist[i]<=tf];joint=[i for i in fdids if abs(gd[i])<=tw];pre_fd=[i for i in family if pdist[i]<=tf];pre_joint=[i for i in pre_fd if abs(pd[i])<=tw];d0=diameter(fdids,Q);d1=diameter(joint,Q);eligible=d0['Q_n']>=2;D0=d0['geometric_D_Q_MPa'];D1=d1['geometric_D_Q_MPa'];red=D0-D1 if D0 is not None and D1 is not None else None
  scenarios.append({'tau_F_N':tf,'tau_g_um':tw,'family':fam,'FD_n':d0['n'],'FD_Q_count':d0['Q_n'],'FD_D_Q_MPa':d0['D_Q_MPa'],'FD_ids':';'.join(fdids),'joint_n':d1['n'],'joint_Q_count':d1['Q_n'],'joint_D_Q_MPa':d1['D_Q_MPa'],'joint_geometric_diameter_MPa':D1,'joint_ids':';'.join(joint),'excluded_by_shape':';'.join(i for i in fdids if i not in joint),'D_Q_reduction_MPa':red,'D_Q_reduction_percent':100*red/D0 if D0 and red is not None else None,'H4_gain_evaluation':'EVALUABLE_FINITE_POOL_ELIMINATION' if eligible else 'NOT_EVALUABLE_FD_POOL_SINGLE_TARGET','joint_status':d1['status'],'predicted_FD_ids':';'.join(pre_fd),'predicted_joint_ids':';'.join(pre_joint),'FD_classification_matches_forecast':pre_fd==fdids,'joint_classification_matches_forecast':pre_joint==joint})
  for obs,actual,predicted in [('FD',fdids,pre_fd),('FD_plus_shape',joint,pre_joint)]:
   classification.append({'tau_F_N':tf,'tau_g_um':tw,'family':fam,'observation':obs,'frozen_predicted_ids':';'.join(predicted),'actual_ids':';'.join(actual),'all_membership_matches':actual==predicted})
   prefix=f'{fam}_F{tf:g}_g{tw:g}_{obs}';arr=np.array([Q[i] for i in actual])
   for k,row in enumerate(envelope_rows):row[prefix+'_min_MPa']=float(arr[:,k].min()) if len(arr) else None;row[prefix+'_max_MPa']=float(arr[:,k].max()) if len(arr) else None
  for i in ids:
   members.append({'tau_F_N':tf,'tau_g_um':tw,'family':fam,'candidate_id':i,'belongs_family':i in family,'actual_FD_member':i in fdids,'actual_joint_member':i in joint,'predicted_FD_member':i in pre_fd,'predicted_joint_member':i in pre_joint})
   if fam=='free':margins.append({'tau_F_N':tf,'tau_g_um':tw,'candidate_id':i,'actual_FD_RMS_N':dist[i],'FD_signed_inside_margin_N':tf-dist[i],'actual_g_residual_um':gd[i],'g_signed_inside_margin_um':tw-abs(gd[i]),'history_observed_absolute_g_drift_um':.10498610224004779,'shape_exclusion_margin_over_observed_drift':(abs(gd[i])-tw)/.10498610224004779,'not_error_bound':True})
  assert d1['n']<=d0['n'];assert red is None or red>=-1e-10;maxchecks+=2
 write(O/'compatibility_scenarios.csv',scenarios);write(O/'membership.csv',members);write(O/'candidate_margins.csv',margins);write(O/'classification_comparison.csv',classification);write(O/'target_envelopes_981.csv',envelope_rows)
 for sc in scenarios:
  if sc['family']=='fixed':
   free=next(r for r in scenarios if r['family']=='free' and r['tau_F_N']==sc['tau_F_N'] and r['tau_g_um']==sc['tau_g_um']);assert set(sc['FD_ids'].split(';'))<=set(free['FD_ids'].split(';'));assert set(sc['joint_ids'].split(';'))<=set(free['joint_ids'].split(';'));maxchecks+=2
 for s in ['M','P']:assert np.array_equal(Q[f'H4_HO_{s}_FIXED'],Q[f'H4_HO_{s}_FREE']);maxchecks+=1
 stats={'cases':4,'pool_total':5,'normalization':'no scalar mixing N/um/MPa; fullFD241 and sameprimaryshape block','forecast_accuracy_acceptance':'no frozen quantitativepass threshold; report descriptiveerror and frozenclassifications only','classification_rule_checks':len(classification),'classification_matches':sum(r['all_membership_matches'] for r in classification),'curve_prediction_RMSE_range_N':[min(r['curve_prediction_RMSE_N'] for r in summary),max(r['curve_prediction_RMSE_N'] for r in summary)],'shape_prediction_abs_error_range_um':[min(abs(r['g_prediction_error_um']) for r in summary),max(abs(r['g_prediction_error_um']) for r in summary)],'checks_passed':maxchecks,'source':'actual qualifiedsame-tier FE only; no experimental data or parameter fitting','thresholds_F_N':[2,4.5,5,10],'thresholds_g_um':[.1,.25,.5,1.],'main_shape':'.5/1mm materialreference radius atpunch1.2','all_singletons_not_uniqueness':True,'new_solver':0,'new_datacheck':0,'new_queue':0,'new_retry':0};dump(O/'metrics.json',stats);print(json.dumps(summary,ensure_ascii=False));print(json.dumps(stats))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args();analyze(a.data,a.out)
