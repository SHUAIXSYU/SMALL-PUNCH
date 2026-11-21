"""Frozen prospective finite-pool comparison; accepts real, separately qualified responses.

No ODB access, solver call, optimization, feature selection, or parameter update.
"""
import numpy as np
SEGMENTS=((0,60),(60,120),(120,180),(180,241));TAUS=(2.,5.,10.);BUFFERS=(0.,.25,.5)
def rms(v):return float(np.sqrt(np.mean(np.asarray(v,dtype=float)**2)))
def met(d,u):
 d=np.asarray(d);i=int(np.argmax(abs(d)));return {'RMS_N':rms(d),'max_abs_N':float(max(abs(d))),'max_at_mm':float(u[i]),'mean_N':float(np.mean(d)),'segments':[{'indices':[a,b],'RMS_N':rms(d[a:b]),'max_abs_N':float(max(abs(d[a:b])))} for a,b in SEGMENTS]}
def pool(ids,targets):
 mat=np.array([targets[k] for k in ids]);pairs=[(i,j,rms(targets[i]-targets[j])) for a,i in enumerate(ids) for j in ids[a+1:]];mx=max(pairs,key=lambda z:z[2]) if pairs else None
 return {'members':ids,'state':'SINGLETON_NOT_UNIQUENESS' if len(ids)==1 else 'FINITE_MULTIPLE' if ids else 'EMPTY_NOT_INFORMATION','D_Q_MPa':mx[2] if mx else None,'diameter_pair':list(mx[:2]) if mx else None,'envelope_min_MPa':mat.min(axis=0).tolist() if ids else None,'envelope_max_MPa':mat.max(axis=0).tolist() if ids else None,'envelope_max_width_MPa':float(max(mat.max(axis=0)-mat.min(axis=0))) if ids else None}
def evaluate(actual,center,targets,parameters,predicted,grid):
 grid=np.asarray(grid);center=np.asarray(center);assert center.shape==(241,) and np.allclose(grid,np.linspace(0,1.2,241),rtol=0,atol=1e-14)
 if set(actual)!=set(parameters):raise ValueError('Incomplete or unqualified responses: complete 18-case primary comparison NOT_EVALUABLE; report partial matched branches separately')
 assert len(actual)==18
 for k,v in actual.items():
  assert np.shape(v)==(241,) and np.isfinite(v).all() and np.shape(targets[k])==(981,)
  assert np.shape(predicted[k])==(241,) and np.isfinite(targets[k]).all()
 actual={k:np.asarray(v) for k,v in actual.items()};targets={k:np.asarray(v) for k,v in targets.items()};response={k:met(v-center,grid) for k,v in actual.items()};results={};branches=[]
 for k,v in actual.items():
  delta=np.asarray(predicted[k])-center;p=met(v-predicted[k],grid);ratio=p['RMS_N']/rms(delta) if rms(delta)>0 else None
  results[k]={'response':response[k],'primary_prediction_error':p,'prediction_error_ratio':ratio,'exploratory_prediction_label':'NOT_EVALUABLE' if ratio is None else '<=0.25' if ratio<=.25 else '(0.25,0.5]' if ratio<=.5 else '(0.5,1]' if ratio<=1 else '>1_PREDICTION_FAILURE','labels_are_not_statistical_tests':True}
 for group in sorted({p['m2'] for p in parameters.values()}):
  ks=[k for k,p in parameters.items() if p['m2']==group];fixed=next(k for k in ks if parameters[k]['variant']=='fixed_high')
  for k in ks:
   if k==fixed:continue
   branches.append({'m2':group,'fixed':fixed,'free':k,'fixed_RMS_N':response[fixed]['RMS_N'],'free_RMS_N':response[k]['RMS_N'],'RMS_reduction_N':response[fixed]['RMS_N']-response[k]['RMS_N'],'d_Q_same_low_MPa':rms(targets[k]-targets[fixed]),'Q_preservation_required_before_scoring':True})
 zeros=[k for k,p in parameters.items() if p['variant']=='fixed_high'];allresp={'I06_L2':center,**actual};allQ=targets;scenarios=[]
 for tau in TAUS:
  for buffer in BUFFERS:
   # These buffered pools are deterministic scenarios, not error bounds/confidence sets.
   inside=lambda k: k=='I06_L2' or response[k]['RMS_N']<=tau-buffer
   fixed_ids=['I06_L2']+[k for k in zeros if inside(k)];free_ids=['I06_L2']+[k for k in actual if inside(k)];fixed=pool(fixed_ids,allQ);free=pool(free_ids,allQ)
   admissions=[{'fixed':b['fixed'],'free':b['free'],'fixed_outside_margin_N':response[b['fixed']]['RMS_N']-tau,'free_inside_margin_N':tau-response[b['free']]['RMS_N']} for b in branches if response[b['fixed']]['RMS_N']>tau+buffer and response[b['free']]['RMS_N']<=tau-buffer]
   # A singleton's mathematical diameter is zero, but its reported scientific status stays singleton.
   gain=(free['D_Q_MPa'] or 0)-(fixed['D_Q_MPa'] or 0)
   scenarios.append({'tau_N':tau,'buffer_N':buffer,'priority':'DIAGNOSTIC_ONLY' if tau==2 else 'CO_PRIMARY_SCENARIO','fixed':fixed,'free_includes_fixed':True,'free':free,'matched_low_out_to_in':admissions,'D_Q_gain_MPa':gain,'outcome':'FINITE_POOL_EXPANSION_OBSERVED' if admissions and gain>1e-9 else 'COMPENSATION_WITHOUT_DEMONSTRATED_TARGET_DIAMETER_GAIN','not_convergence_proof':True})
 parity=[]
 for magnitude in [1.5,2.,3.]:
  for var in ['fixed_high','opposed_equal','opposed_1p2']:
   kp=next(k for k,p in parameters.items() if p['m2']==magnitude and p['variant']==var);km=next(k for k,p in parameters.items() if p['m2']==-magnitude and p['variant']==var);odd=(actual[kp]-actual[km])/2;even=(actual[kp]+actual[km])/2-center
   parity.append({'abs_m2':magnitude,'variant':var,'plus':kp,'minus':km,'odd':met(odd,grid),'even':met(even,grid),'even_over_odd':rms(even)/rms(odd) if rms(odd)>0 else None,'nonlinearity_review_flag':rms(even)>.25*rms(odd),'not_pure_material_nonlinearity_or_error_decomposition':True})
 return {'candidates':results,'matched_branches':branches,'scenarios':scenarios,'parity':parity,'conditions':'real same-tier qualified curves and per-candidate Q preservation required; no full-domain inference','strict_numerical_convergence':False,'real_material_validation':'NOT_EVALUABLE'}
