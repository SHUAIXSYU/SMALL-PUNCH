"""H4 actual-FE finite-pool arithmetic; no estimator fitting or execution API."""
from pathlib import Path
import json,csv,itertools,math
import numpy as np

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,x):
 with Path(p).open('w',encoding='utf8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def write(p,x):
 if not x:return
 with Path(p).open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(x[0]),lineterminator='\n');w.writeheader();w.writerows(x)
def rms(x):return float(np.sqrt(np.mean(np.asarray(x,dtype=float)**2)))
def fid(r1,r2,u):return f'r{r1:g}_r{r2:g}_u{u:g}'
def diameter(ids,Q):
 if not ids:return {'n':0,'distinct_Q':0,'D_Q_MPa':None,'geometric_diameter_MPa':None,'status':'EMPTY','pair':None}
 distinct=len({tuple(np.round(Q[i],10)) for i in ids})
 if distinct==1:return {'n':len(ids),'distinct_Q':1,'D_Q_MPa':None,'geometric_diameter_MPa':0.,'status':'SINGLE_TARGET_NOT_UNIQUENESS','pair':None}
 pairs=[(rms(Q[i]-Q[j]),i,j) for i,j in itertools.combinations(ids,2)];d,i,j=max(pairs)
 return {'n':len(ids),'distinct_Q':distinct,'D_Q_MPa':d,'geometric_diameter_MPa':d,'status':'FINITE_POOL','pair':[i,j]}
def analyze(base,out):
 base=Path(base);out=Path(out);out.mkdir(exist_ok=True,parents=True)
 job=rows(base/'jobs.csv');ids=['I06_L2']+[x['candidate_id'] for x in job];Qraw=rows(base/'target_Q_981.csv');Q={i:np.array([float(r[i+'_MPa']) for r in Qraw]) for i in ids};fdraw=rows(base/'fd_actual_241.csv');FD={i:np.array([float(r[i+'_N']) for r in fdraw]) for i in ids};dist={i:rms(FD[i]-FD['I06_L2']) for i in ids};fixed={'I06_L2'}|{x['candidate_id'] for x in job if abs(float(x['c3']))<1e-15}
 sh=rows(base/'shape_features.csv');M={};fields={}
 for r in sh:
  key=fid(float(r['r1_mm']),float(r['r2_mm']),float(r['target_u_mm']));M.setdefault(r['case'],{})[key]=float(r['shape_mm'])*1000;fields[key]={'r1_mm':float(r['r1_mm']),'r2_mm':float(r['r2_mm']),'u_mm':float(r['target_u_mm'])}
 keys=sorted(fields,key=lambda k:(fields[k]['r1_mm'],fields[k]['r2_mm'],fields[k]['u_mm']));assert len(keys)==12
 for i in ids:assert set(M[i])==set(keys)
 delta={i:{k:M[i][k]-M['I06_L2'][k] for k in keys} for i in ids}
 baseline=fid(.5,1.5,1.2)
 numeric=[];matched=[('I06_L1','I06_L2'),('B4_01_L1','B4_01_L2'),('B4_02_L1','B4_02_L2')]
 for lo,hi in matched:
  for k in keys:
   assert lo in M and hi in M,(lo,hi,list(M));d=M[hi][k]-M[lo][k];corrected=None if lo=='I06_L1' else (M[hi][k]-M['I06_L2'][k])-(M[lo][k]-M['I06_L1'][k])
   numeric.append({'material':lo.replace('_L1',''),'feature':k,'coarse_shape_um':M[lo][k],'fine_shape_um':M[hi][k],'fine_minus_coarse_um':d,'abs_change_um':abs(d),'center_relative_change_um':corrected,'not_error_upper_bound':True})
 write(out/'numerical_shape_changes.csv',numeric)
 maxnum={k:max(r['abs_change_um'] for r in numeric if r['feature']==k) for k in keys}
 scenarios=[];members=[];envelopes=[]
 def scenario(label,ks,tauF,tauW,family):
  allowed=ids if family=='free' else [i for i in ids if i in fixed];before=[i for i in allowed if dist[i]<=tauF];after=[i for i in before if all(abs(delta[i][k])<=tauW+1e-12 for k in ks)];d0=diameter(before,Q);d1=diameter(after,Q);b=d0['geometric_diameter_MPa'];a=d1['geometric_diameter_MPa'];gain=b-a if b is not None and a is not None else None;percent=100*gain/b if b is not None and b>0 else None
  rec={'observation':label,'features':';'.join(ks),'tau_F_N':tauF,'tau_w_feature_um':tauW,'family':family,'before_n':len(before),'after_n':len(after),'before_Q_count':d0['distinct_Q'],'after_Q_count':d1['distinct_Q'],'before_D_Q_MPa':d0['D_Q_MPa'],'after_D_Q_MPa':d1['D_Q_MPa'],'after_status':d1['status'],'D_Q_reduction_MPa':gain,'reduction_percent':percent,'retained_ids':';'.join(after),'diameter_pair':';'.join(d1['pair'] or []),'max_observed_coarse_fine_um':max([maxnum[k] for k in ks] or [0]),'selection_not_independent_validation':True};scenarios.append(rec)
  for i in ids:members.append({'observation':label,'tau_F_N':tauF,'tau_w_feature_um':tauW,'family':family,'candidate_id':i,'FD_RMS_N':dist[i],'max_abs_shape_residual_um':max([abs(delta[i][k]) for k in ks] or [0]),'FD_member':i in before,'joint_member':i in after})
  if False: # envelopes regenerated below for primary screen and bounded public size
   for j,e in enumerate(Qraw):
    v=[Q[i][j] for i in after];envelopes.append({'observation':label,'tau_F_N':tauF,'tau_w_feature_um':tauW,'true_total_strain':float(e['true_total_strain']),'Q_min_MPa':min(v) if v else None,'Q_max_MPa':max(v) if v else None,'members':len(after),'independent_validation':False})
  return rec
 obs={'FD_only':[], 'baseline_single':[baseline], 'baseline_two_stage':[fid(.5,1.5,.6),baseline]}
 obs.update({'single_'+k:[k] for k in keys})
 for label,ks in obs.items():
  for tf,tw,fam in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.],['fixed','free']):scenario(label,ks,tf,tw,fam)
 rank=[]
 for k in keys:
  rr=[r for r in scenarios if r['observation']=='single_'+k and r['family']=='free' and r['tau_F_N'] in [4.5,5,10] and r['tau_w_feature_um'] in [.25,.5,1.]]
  score=float(np.mean([r['reduction_percent'] for r in rr]));rank.append({'feature':k,**fields[k],'mean_D_Q_reduction_percent':score,'max_observed_coarse_fine_um':maxnum[k],'worst_case_Q_count':max(r['after_Q_count'] for r in rr),'selection_status':'EXPLORATORY_R18_SCREEN_ONLY'})
 rank.sort(key=lambda r:(-r['mean_D_Q_reduction_percent'],-(r['r2_mm']-r['r1_mm']),r['u_mm']));best=rank[0];bk=[fid(best['r1_mm'],best['r2_mm'],.6),fid(best['r1_mm'],best['r2_mm'],1.2)]
 for tf,tw,fam in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.],['fixed','free']):scenario('selected_pair_two_stage',bk,tf,tw,fam)
 envelopes=[]
 for rec in scenarios:
  if rec['family']!='free' or rec['tau_F_N'] not in [5.,10.] or rec['observation'] not in ['baseline_single','single_'+best['feature'],'selected_pair_two_stage']:continue
  selected=rec['retained_ids'].split(';') if rec['retained_ids'] else []
  for j,e in enumerate(Qraw):
   v=[Q[i][j] for i in selected];envelopes.append({'observation':rec['observation'],'tau_F_N':rec['tau_F_N'],'tau_w_feature_um':rec['tau_w_feature_um'],'true_total_strain':float(e['true_total_strain']),'Q_min_MPa':min(v) if v else None,'Q_max_MPa':max(v) if v else None,'members':len(selected),'independent_validation':False})
 write(out/'observation_ranking.csv',rank);write(out/'compatibility_scenarios.csv',scenarios);write(out/'joint_membership.csv',members);write(out/'target_envelopes.csv',envelopes)
 pairs=[]
 for i,j,tf in [('R18_02','R18_14',5.),('R18_05','R18_15',4.5),('R18_02','R18_17',10.)]:
  for k in keys:pairs.append({'case_a':i,'case_b':j,'known_reference_tau_N':tf,'FD_a_to_I06_N':dist[i],'FD_b_to_I06_N':dist[j],'direct_pair_FD_RMS_N':rms(FD[i]-FD[j]),'direct_d_Q_MPa':rms(Q[i]-Q[j]),'feature':k,'a_shape_um':M[i][k],'b_shape_um':M[j][k],'pair_shape_difference_um':abs(M[i][k]-M[j][k]),'a_minus_I06_um':delta[i][k],'b_minus_I06_um':delta[j][k],'max_observed_coarse_fine_um':maxnum[k]})
 write(out/'priority_pair_signals.csv',pairs)
 write(out/'shape_residuals.csv',[{'candidate_id':i,'feature':k,**fields[k],'shape_um':M[i][k],'shape_minus_I06_um':delta[i][k],'FD_RMS_to_I06_N':dist[i]} for i in ids for k in keys])
 timing=[]
 for r in sh:
  if r['case'] not in ids:continue
  den=float(r['upper_u_mm'])-float(r['lower_u_mm']);slope=(float(r['upper_shape_mm'])-float(r['lower_shape_mm']))/den if den>1e-12 else None
  timing.append({'case':r['case'],'feature':fid(float(r['r1_mm']),float(r['r2_mm']),float(r['target_u_mm'])),'d_feature_d_punch_mm_per_mm':slope,'hypothetical_punch_error_um':1.,'linearized_feature_error_um':abs(slope) if slope is not None else None,'not_measurement_error_model':True})
 write(out/'synchronization_scenarios.csv',timing)
 # Radial mislocation applied to each tracked reference point independently: deterministic endpoint bound, no statistical model.
 profiles=rows(base/'bottom_profiles.csv');radial=[]
 for i in ids:
  for u in [.3,.6,.9,1.2]:
   pp=[r for r in profiles if r['case']==i and abs(float(r['target_u_mm'])-u)<1e-10];pp=sorted(pp,key=lambda r:float(r['r_ref_mm']));x=np.array([float(r['r_ref_mm']) for r in pp]);w=np.array([float(r['w_mm']) for r in pp]);assert len(x)>2 and np.all(np.diff(x)>0)
   for r1,r2 in [[.5,1.5],[.5,1],[1,1.5]]:
    for dr in [.01,.025]:
     assert r1-dr>=x[0] and r2+dr<=x[-1]
     d1=max(abs(float(np.interp(r1+t,x,w)-np.interp(r1,x,w))) for t in [-dr,dr]);d2=max(abs(float(np.interp(r2+t,x,w)-np.interp(r2,x,w))) for t in [-dr,dr]);radial.append({'case':i,'feature':fid(r1,r2,u),'hypothetical_radius_error_mm':dr,'sum_endpoint_linear_interpolation_deviation_um':1000*(d1+d2),'not_verified_device_tolerance':True})
 write(out/'radial_location_scenarios.csv',radial)
 checks=0
 for r in scenarios:
  assert r['after_n']<=r['before_n'];assert r['D_Q_reduction_MPa'] is None or r['D_Q_reduction_MPa']>=-1e-10;checks+=2
 for tf in [2.,4.5,5.,10.]:
  subset=sorted([r for r in scenarios if r['observation']=='baseline_single' and r['family']=='free' and r['tau_F_N']==tf],key=lambda r:r['tau_w_feature_um']);assert all(a['after_n']<=b['after_n'] for a,b in zip(subset,subset[1:]));checks+=1
 for label in ['baseline_single','baseline_two_stage','selected_pair_two_stage']:
  for tf,tw in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.]):
   a=next(r for r in scenarios if r['observation']==label and r['family']=='fixed' and r['tau_F_N']==tf and r['tau_w_feature_um']==tw);b=next(r for r in scenarios if r['observation']==label and r['family']=='free' and r['tau_F_N']==tf and r['tau_w_feature_um']==tw);assert set(a['retained_ids'].split(';'))<=set(b['retained_ids'].split(';'));checks+=1
 assert abs(diameter([i for i in ids if dist[i]<=5],Q)['D_Q_MPa']-8.739697717005779)<1e-8;checks+=1
 assert abs(diameter([i for i in ids if dist[i]<=4.5],Q)['D_Q_MPa']-7.300862506819214)<1e-8;checks+=1
 assert abs(diameter([i for i in ids if dist[i]<=10],Q)['D_Q_MPa']-11.030806192776833)<1e-8;checks+=1
 metrics={'source':'actual existing ODB shape and already qualified same-tier run083 FE/Q; selection only','baseline_feature':baseline,'exploratory_best':best,'observations':obs,'ranked_features':rank,'checks_passed':checks,'shape_rows':len(sh),'actual_FE_cases_in_pools':len(ids),'all_results_selection_not_validation':True,'tau_feature_contract':'derived difference bounds, per-point delta implies at most2delta feature bound, no Gaussian independence','numerical_error_not_bound':True,'no_new_execution':True}
 dump(out/'metrics.json',metrics);print(json.dumps(metrics,ensure_ascii=False))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args();analyze(a.data,a.out)
