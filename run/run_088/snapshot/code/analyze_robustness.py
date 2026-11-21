"""Secondary operator-nuisance scenarios, not changed primary H4 thresholds."""
from robustness_functions import *

def robustness(data,out):
 D=Path(data);O=Path(out);O.mkdir(exist_ok=True,parents=True);ids=['I06_L2']+[r['candidate_id'] for r in rows(D/'jobs.csv')];qr=rows(D/'target_Q_981.csv');Q={i:np.array([float(r[i+'_MPa']) for r in qr]) for i in ids};ff=rows(D/'fd_actual_241.csv');dist={i:rms([float(r[i+'_N'])-float(r['I06_L2_N']) for r in ff]) for i in ids};fixed={'I06_L2'}|{r['candidate_id'] for r in rows(D/'jobs.csv') if float(r['c3'])==0};pp=rows(D/'bottom_profiles.csv');lp=rows(D/'local_profiles.csv');profiles={};local={};stages={}
 for i in ids:
  rr=sorted([r for r in pp if r['case']==i and float(r['target_u_mm'])==1.2],key=lambda r:float(r['r_ref_mm']));profiles[i]=(np.array([float(r['r_ref_mm']) for r in rr]),np.array([float(r['w_mm']) for r in rr]));times=sorted({float(r['actual_u_mm']) for r in lp if r['case']==i});stages[i]=np.array(times)
  for t in times:
   rr=sorted([r for r in lp if r['case']==i and float(r['actual_u_mm'])==t],key=lambda r:float(r['r_ref_mm']));local[(i,t)]=(np.array([float(r['r_ref_mm']) for r in rr]),np.array([float(r['w_mm']) for r in rr]))
 def g_at(i,u):
  if u==1.2:return G(profiles[i])
  ts=stages[i];j=int(np.searchsorted(ts,u));assert 0<j<len(ts);l,h=float(ts[j-1]),float(ts[j]);a=(u-l)/(h-l);return (1-a)*G(local[(i,l)])+a*G(local[(i,h)])
 det=[];sc=[]
 for d in [.001,.0025,.005,.01]:
  bounds={i:feature_range(profiles[i],d) for i in ids};knots=np.unique(np.concatenate([breakpoints(profiles[i],d) for i in ids]));ref=profiles['I06_L2'];r0=G(ref)
  for i in ids:
   g=G(profiles[i]);delta=g-r0;vals=np.array([G(profiles[i],z,z) for z in knots]);rr=np.array([G(profiles[i],z,z)-G(ref,z,z) for z in knots]);l,h=bounds[i];l0,h0=bounds['I06_L2'];det.append({'candidate_id':i,'radius_bound_mm':d,'absolute_shared_radius_error_um':float(max(abs(vals-g))),'relative_shared_radius_error_um':float(max(abs(rr-delta))),'absolute_independent_points_error_um':max(abs(l-g),abs(h-g)),'relative_independent_specimen_points_error_um':0. if i=='I06_L2' else max(abs(l-h0-delta),abs(h-l0-delta)),'scenario_not_measured_accuracy':True})
  for tf,tg,fam in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.],['fixed','free']):
   allowed=[i for i in ids if dist[i]<=tf and (fam=='free' or i in fixed)];dq=diameter(allowed,Q)['D_Q_MPa']
   for label,result in [('shared_uniform_radius_shift',common_calibration_pools(ids,profiles,Q,dist,fixed,d,tf,tg,fam)),('independent_specimen_point_position',independent_pools(ids,Q,dist,fixed,bounds,tf,tg,fam))]:
    rr={'error_scenario':label,'error_bound_mm':d,'tau_F_N':tf,'tau_g_um':tg,'family':fam,'FD_only_D_Q_MPa':dq}
    for k,v in result.items():rr[k]=';'.join(v) if isinstance(v,list) else v
    sc.append(rr)
 tdet=[]
 for d in [.001,.0025,.005]:
  knots=np.unique(np.r_[-d,0,*[stages[i][(stages[i]>=1.2-d)&(stages[i]<=1.2)]-1.2 for i in ids]]);val={i:np.array([g_at(i,1.2+float(z)) for z in knots]) for i in ids};res={i:val[i]-val['I06_L2'] for i in ids};bounds={i:(float(val[i].min()),float(val[i].max())) for i in ids}
  for i in ids:
   g=G(profiles[i]);delta=g-G(profiles['I06_L2']);l,h=bounds[i];l0,h0=bounds['I06_L2'];tdet.append({'candidate_id':i,'backward_phase_bound_mm':d,'absolute_phase_error_um':float(max(abs(val[i]-g))),'relative_shared_phase_error_um':float(max(abs(res[i]-delta))),'relative_independent_phase_error_um':0. if i=='I06_L2' else max(abs(l-h0-delta),abs(h-l0-delta)),'positive_phase_not_available_no_extrapolation':True})
  for tf,tg,fam in itertools.product([2.,4.5,5.,10.],[.1,.25,.5,1.],['fixed','free']):
   allowed=[i for i in ids if dist[i]<=tf and (fam=='free' or i in fixed)];dq=diameter(allowed,Q)['D_Q_MPa']
   for label,result in [('shared_backward_phase',common_curves(ids,Q,dist,fixed,knots,res,tf,tg,fam)),('independent_specimen_backward_phase',independent_pools(ids,Q,dist,fixed,bounds,tf,tg,fam))]:
    rr={'error_scenario':label,'error_bound_mm':d,'tau_F_N':tf,'tau_g_um':tg,'family':fam,'FD_only_D_Q_MPa':dq}
    for k,v in result.items():rr[k]=';'.join(v) if isinstance(v,list) else v
    sc.append(rr)
 keys=list(dict.fromkeys(k for r in sc for k in r));write(O/'robustness_pool_scenarios.csv',[{k:r.get(k) for k in keys} for r in sc]);write(O/'position_absolute_vs_residual.csv',det);write(O/'phase_absolute_vs_residual.csv',tdet);dump(O/'robustness_metrics.json',{'scenario_count':len(sc),'protocol':'run085 shared-versus-independent operator-error scenarios unchanged; candidate-relative residual, same shared reference across each feasible pool','position_bounds_um':[1,2.5,5,10],'backward_punch_phase_bounds_um':[1,2.5,5],'same_nominal_frozen_feature':True,'tau_g':'separate supplementary operator scenario contract; do not doublecountif1umalreadyincludesposition/timing uncertainty','not_error_bounds_or_measured_noise':True,'no_new_feature_selection':True});print('robustness',len(sc))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args();robustness(a.data,a.out)
