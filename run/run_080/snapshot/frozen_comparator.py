"""Prospective B3 two-level comparison, no mixed-level fixed/free family inference."""
import numpy as np
KEYS=('B4_01','B4_02','I06_REFINED')
SEGMENTS=((0,60),(60,120),(120,180),(180,241))
TAU=(1.,2.,5.,10.)
def rms(v):return float(np.sqrt(np.mean(np.asarray(v,dtype=float)**2)))
def check(d):
 if set(d)!=set(KEYS):raise ValueError('All three same-tier responses required; otherwise PARTIAL/NOT_EVALUABLE')
 for v in d.values():
  if np.asarray(v).shape!=(241,) or not np.isfinite(v).all():raise ValueError('Invalid241 response')
def metrics(v,u):
 v=np.asarray(v);i=int(np.argmax(abs(v)))
 return {'RMS_N':rms(v),'max_abs_N':float(max(abs(v))),'max_at_mm':float(u[i]),'mean_signed_N':float(np.mean(v)),'segments':[{'indices':[a,b],'RMS_N':rms(v[a:b]),'max_abs_N':float(max(abs(v[a:b])))} for a,b in SEGMENTS]}
def ratio(a,b):return float(a/b) if b>0 else None
def compare(old,new,grid_mm,targets):
 check(old);check(new);u=np.asarray(grid_mm);assert u.shape==(241,) and np.allclose(u,np.linspace(0,1.2,241),rtol=0,atol=1e-14)
 old={k:np.asarray(v,dtype=float) for k,v in old.items()};new={k:np.asarray(v,dtype=float) for k,v in new.items()};delta={k:new[k]-old[k] for k in KEYS};out={}
 for k in KEYS:out[k]={'same_point_two_level_difference':metrics(delta[k],u)}
 for k in KEYS[:2]:
  a=old[k]-old['I06_REFINED'];b=new[k]-new['I06_REFINED'];change=b-a;r1=rms(a);r2=rms(b);signal=rms(change)
  out[k].update({'L1_relative_same_level_I06':metrics(a,u),'L2_relative_same_level_I06':metrics(b,u),'change_of_relative_response':metrics(change,u),'relative_response_change_over_L1_signal':ratio(signal,r1),'same_point_change_over_L1_signal':ratio(rms(delta[k]),r1),'reference_point_change_RMS_N':rms(delta['I06_REFINED']),'RMS_change_signed_N':r2-r1,'observed_triangle_screen_N':rms(delta[k])+rms(delta['I06_REFINED']),'observed_triangle_inequality_holds':abs(r2-r1)<=signal+1e-12 and signal<=rms(delta[k])+rms(delta['I06_REFINED'])+1e-12,'not_true_discretization_error_bound':True,'thresholds':[{ 'tau_N':t,'L1_inside':r1<=t,'L2_inside':r2<=t,'L1_signed_margin_N':t-r1,'L2_signed_margin_N':t-r2,'membership_changed':(r1<=t)!=(r2<=t),'relative_response_change_over_old_margin':ratio(signal,abs(t-r1)),'relative_response_change_over_new_margin':ratio(signal,abs(t-r2)),'same_point_change_over_old_margin':ratio(rms(delta[k]),abs(t-r1)),'risk_flag':'UNRESOLVED' if (r1<=t)!=(r2<=t) or abs(t-r2)<=signal else 'NO_FLAG_FROM_THIS_OBSERVED_TWO_LEVEL_SCREEN','risk_flag_not_convergence_or_confidence':True} for t in TAU]})
 pools=[]
 for tier,d in [('L1',old),('L2',new)]:
  for t in TAU:
   ids=[k for k in KEYS if rms(d[k]-d['I06_REFINED'])<=t];pairs=[(a,b,rms(np.asarray(targets[a])-targets[b])) for i,a in enumerate(ids) for b in ids[i+1:]];mx=max(pairs,key=lambda v:v[2]) if pairs else None;pools.append({'tier':tier,'tau_N':t,'members':ids,'state':'SINGLETON_NOT_UNIQUENESS' if len(ids)==1 else 'FINITE_MULTIPLE','d_Q_diameter_MPa':mx[2] if mx else None,'diameter_pair':list(mx[:2]) if mx else None,'scope':'available same-level center+two joint candidates only; not full fixed/free continuation family'})
 return {'per_point':out,'direct_joint_pair':{'L1':metrics(old['B4_01']-old['B4_02'],u),'L2':metrics(new['B4_01']-new['B4_02'],u),'change':metrics(delta['B4_01']-delta['B4_02'],u),'target_d_Q_MPa':rms(np.asarray(targets['B4_01'])-targets['B4_02'])},'available_same_level_candidate_pools':pools,'full_fixed_free_H2_comparison':'NOT_EVALUABLE_WITHOUT_FINE_S2_ZERO_CONTROLS','strict_numerical_convergence_proven':False}
