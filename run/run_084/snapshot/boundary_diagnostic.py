from analyze_h4 import *
import itertools

def boundary(base,out):
 base=Path(base);out=Path(out);q=rows(base/'target_Q_981.csv');ids=['I06_L2']+[r['candidate_id'] for r in rows(base/'jobs.csv')];Q={i:np.array([float(r[i+'_MPa']) for r in q]) for i in ids};fd=rows(base/'fd_actual_241.csv');dist={i:rms([float(r[i+'_N'])-float(r['I06_L2_N']) for r in fd]) for i in ids};shape={i:{} for i in ids}
 for r in rows(base/'shape_features.csv'):
  if r['case'] in ids:shape[r['case']][fid(float(r['r1_mm']),float(r['r2_mm']),float(r['target_u_mm']))]=1000*float(r['shape_mm'])
 feature=load(out/'metrics.json')['exploratory_best']['feature'];num=max(float(x['abs_change_um']) for x in rows(out/'numerical_shape_changes.csv') if x['feature']==feature);result=[]
 for tf,tw,sign in itertools.product([4.5,5.,10.],[.1,.25,.5,1.],[-1,0,1]):
  eff=max(0.,tw+sign*num);mem=[i for i in ids if dist[i]<=tf and abs(shape[i][feature]-shape['I06_L2'][feature])<=eff];d=diameter(mem,Q);result.append({'feature':feature,'tau_F_N':tf,'nominal_feature_tolerance_um':tw,'observed_3material_drift_um':num,'direction':sign,'diagnostic_effective_tolerance_um':eff,'members':';'.join(mem),'Q_count':d['distinct_Q'],'D_Q_MPa':d['D_Q_MPa'],'diameter_geometric_MPa':d['geometric_diameter_MPa'],'not_error_bound_or_acceptance_rule':True})
 write(out/'boundary_sensitivity.csv',result)
