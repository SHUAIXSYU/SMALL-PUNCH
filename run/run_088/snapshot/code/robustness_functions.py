from analyze_holdout import *

def diameter(ids,Q):
 from analyze_holdout import diameter as original
 d=original(ids,Q);d['geom_D_Q_MPa']=d['geometric_D_Q_MPa'];return d
def G(p,d1=0.,d2=0.):
 x,w=p;assert x[0]<=.5+d1<=x[-1] and x[0]<=1.+d2<=x[-1];return 1000*float(np.interp(.5+d1,x,w)-np.interp(1.+d2,x,w))
def breakpoints(p,d):
 x=p[0];return np.unique(np.r_[-d,0,d,x[(x>=.5-d)&(x<=.5+d)]-.5,x[(x>=1-d)&(x<=1+d)]-1])
def feature_range(p,d):
 x,w=p;vals=[]
 for rr in [.5,1.]:
  z=np.unique(np.r_[rr-d,rr+d,x[(x>=rr-d)&(x<=rr+d)]]);v=np.interp(z,x,w);vals.append([float(v.min()),float(v.max())])
 return (1000*(vals[0][0]-vals[1][1]),1000*(vals[0][1]-vals[1][0]))
def common_calibration_pools(ids,profiles,Q,dist,fixed,d,tf,tw,family):
 allowed=[i for i in ids if dist[i]<=tf and (family=='free' or i in fixed)];knots=np.unique(np.concatenate([breakpoints(profiles[i],d) for i in ids]));res={i:np.array([G(profiles[i],z,z)-G(profiles['I06_L2'],z,z) for z in knots]) for i in ids};roots=list(knots)
 for i in allowed:
  for j in range(len(knots)-1):
   l,h=res[i][j:j+2]
   if abs(h-l)>1e-16:
    for limit in [-tw,tw]:
     a=(limit-l)/(h-l)
     if 0<a<1:roots.append(float(knots[j]+a*(knots[j+1]-knots[j])))
 roots=np.unique(roots);test=np.unique(np.r_[roots,(roots[:-1]+roots[1:])/2]);pools=[]
 for z in test:
  r0=G(profiles['I06_L2'],z,z);mem=[i for i in allowed if abs(G(profiles[i],z,z)-r0)<=tw+1e-10];v=diameter(mem,Q);pools.append({'shift_mm':float(z),'members':mem,**v})
 hi=max(pools,key=lambda r:r['geom_D_Q_MPa'] if r['geom_D_Q_MPa'] is not None else -1);lo=min(pools,key=lambda r:r['geom_D_Q_MPa'] if r['geom_D_Q_MPa'] is not None else -1);union=[i for i in allowed if any(i in pp['members'] for pp in pools)];guarantee=[i for i in allowed if all(i in pp['members'] for pp in pools)];return {'possible_ids':union,'guaranteed_ids':guarantee,'max_simultaneous_D_Q_MPa':hi['D_Q_MPa'],'max_simultaneous_geom_MPa':hi['geom_D_Q_MPa'],'min_simultaneous_geom_MPa':lo['geom_D_Q_MPa'],'max_witness_shift_mm':hi['shift_mm'],'max_witness_members':hi['members'],'possible_pool_D_Q_MPa':diameter(union,Q)['D_Q_MPa'],'guaranteed_pool_D_Q_MPa':diameter(guarantee,Q)['D_Q_MPa'],'scenario_points':len(test)}
def independent_pools(ids,Q,dist,fixed,bounds,tf,tw,family):
 allowed=[i for i in ids if dist[i]<=tf and (family=='free' or i in fixed)];lo0,hi0=bounds['I06_L2'];kn=[lo0,hi0]
 for i in allowed:
  lo,hi=bounds[i]
  for v in [lo-tw,hi+tw]:
   if lo0<=v<=hi0:kn.append(v)
 kn=np.unique(kn);test=np.unique(np.r_[kn,(kn[:-1]+kn[1:])/2]);pp=[]
 for ref in test:
  mem=[i for i in allowed if i=='I06_L2' or bounds[i][0]-tw-1e-10<=ref<=bounds[i][1]+tw+1e-10];pp.append({'reference_shape_um':float(ref),'members':mem,**diameter(mem,Q)})
 hi=max(pp,key=lambda r:r['geom_D_Q_MPa'] if r['geom_D_Q_MPa'] is not None else -1);union=[i for i in allowed if any(i in p['members'] for p in pp)];guarantee=[i for i in allowed if i=='I06_L2' or max(abs(bounds[i][0]-hi0),abs(bounds[i][1]-lo0))<=tw+1e-10];return {'possible_ids':union,'guaranteed_ids':guarantee,'max_simultaneous_D_Q_MPa':hi['D_Q_MPa'],'max_simultaneous_geom_MPa':hi['geom_D_Q_MPa'],'min_simultaneous_geom_MPa':None,'max_witness_reference_shape_um':hi['reference_shape_um'],'max_witness_members':hi['members'],'possible_pool_D_Q_MPa':diameter(union,Q)['D_Q_MPa'],'guaranteed_pool_D_Q_MPa':diameter(guarantee,Q)['D_Q_MPa'],'scenario_points':len(test)}

def common_curves(ids,Q,dist,fixed,x,res,tf,tw,family):
 allowed=[i for i in ids if dist[i]<=tf and (family=='free' or i in fixed)];points=list(x)
 for i in allowed:
  for j in range(len(x)-1):
   a,b=res[i][j:j+2]
   if abs(b-a)>1e-16:
    for limit in [-tw,tw]:
     t=(limit-a)/(b-a)
     if 0<t<1:points.append(float(x[j]+t*(x[j+1]-x[j])))
 points=np.unique(points);test=np.unique(np.r_[points,(points[:-1]+points[1:])/2]);pools=[]
 for z in test:
  mem=[i for i in allowed if abs(float(np.interp(z,x,res[i])))<=tw+1e-10];pools.append({'bias_mm':float(z),'members':mem,**diameter(mem,Q)})
 valid=[p for p in pools if p['geom_D_Q_MPa'] is not None];hi=max(valid,key=lambda r:r['geom_D_Q_MPa']);lo=min(valid,key=lambda r:r['geom_D_Q_MPa']);possible=[i for i in allowed if any(i in p['members'] for p in pools)];guaranteed=[i for i in allowed if all(i in p['members'] for p in pools)];return {'max_simultaneous_D_Q_MPa':hi['D_Q_MPa'],'max_simultaneous_geom_MPa':hi['geom_D_Q_MPa'],'min_nonempty_simultaneous_geom_MPa':lo['geom_D_Q_MPa'],'max_witness_bias_mm':hi['bias_mm'],'max_witness_members':';'.join(hi['members']),'possible_ids':';'.join(possible),'guaranteed_ids':';'.join(guaranteed),'possible_pool_D_Q_MPa':diameter(possible,Q)['D_Q_MPa'],'guaranteed_pool_D_Q_MPa':diameter(guaranteed,Q)['D_Q_MPa'],'tested_breakpoints_and_intervals':len(test),'empty_realizations_checked':sum(p['n']==0 for p in pools)}
