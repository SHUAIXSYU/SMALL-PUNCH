"""Pre-frozen future B4 comparator. No file I/O, fitting, solver or data reveal."""
import numpy as np
SEGMENTS=((0,60),(60,120),(120,180),(180,241))
REFERENCE_RMS_N=.4326779144080392
def rms(v):return float(np.sqrt(np.mean(np.asarray(v,dtype=float)**2)))
def fd_metrics(v,grid_mm):
 v=np.asarray(v,dtype=float);g=np.asarray(grid_mm);assert v.shape==g.shape==(241,) and np.isfinite(v).all()
 i=int(np.argmax(abs(v)));return {'RMS_N':rms(v),'max_abs_N':float(max(abs(v))),'at_mm':float(g[i]),'mean_N':float(np.mean(v)),'segments':[{'indices':[a,b],'RMS_N':rms(v[a:b]),'max_abs_N':float(max(abs(v[a:b])))} for a,b in SEGMENTS]}
def evaluate(center,zero_controls,actual,predicted,targets,grid_mm):
 # Only actual admitted FE belongs in these arrays; caller must preserve audit.
 required={'B4_01','B4_02','B4_03','B4_04'}
 if set(actual)!=required:raise ValueError('Incomplete quartet; complete experiment NOT_EVALUABLE')
 c=np.asarray(center);actual={k:np.asarray(v) for k,v in actual.items()};out={}
 for key,f in actual.items():
  if f.shape!=(241,) or not np.isfinite(f).all():raise ValueError('Invalid response')
  ctl='B2_S2_P' if key in ['B4_01','B4_03'] else 'B2_S2_M';d=f-c;prediction=np.asarray(predicted[key]);error=f-prediction
  change=rms(zero_controls[ctl]-c)-rms(d);eratio=rms(error)/rms(prediction-c) if rms(prediction-c)>0 else None
  out[key]={'relative_reference':fd_metrics(d,grid_mm),'primary_prediction_error':fd_metrics(error,grid_mm),'prediction_error_ratio':eratio,'prediction_ratio_label':'UNRESOLVED' if eratio is None else 'LE_0p25' if eratio<=.25 else 'LE_0p5' if eratio<=.5 else 'LE_1' if eratio<=1 else 'GT_1','RMS_reduction_vs_zero_N':change,'directional_reference_margin':'EXCEEDS_EXPLORATORY_REFERENCE' if abs(change)>REFERENCE_RMS_N else 'UNRESOLVED_AT_REFERENCE_SCALE','actual_tau_membership':[tau for tau in [1,2,5,10] if rms(d)<=tau],'tau_margin_flags':{str(tau):abs(rms(d)-tau)<=REFERENCE_RMS_N for tau in [1,2,5,10]}}
 pairs={}
 for label,positive,negative in [('opposed','B4_01','B4_02'),('same_sign','B4_03','B4_04')]:
  o=(actual[positive]-actual[negative])/2;e=(actual[positive]+actual[negative])/2-c
  pairs[label]={'positive_c2':positive,'negative_c2':negative,'odd':fd_metrics(o,grid_mm),'even':fd_metrics(e,grid_mm),'even_over_odd':rms(e)/rms(o) if rms(o)>0 else None}
 pool={'I06_REFINED':c,**zero_controls,**actual};fixed=['I06_REFINED',*zero_controls];sets=[]
 for tau in [1,2,5,10]:
  row={'tau_N':tau}
  for family,ids in [('fixed',fixed),('free',list(pool))]:
   good=[k for k in ids if rms(pool[k]-c)<=tau];dist=[(k,l,rms(np.asarray(targets[k])-targets[l])) for i,k in enumerate(good) for l in good[i+1:]];diam=max(dist,key=lambda v:v[2]) if dist else None
   row[family]={'members':good,'count':len(good),'state':'EMPTY' if not good else 'SINGLETON' if len(good)==1 else 'MULTIPLE','d_Q_diameter_MPa':diam[2] if diam else None,'diameter_pair':list(diam[:2]) if diam else None,'max_pointwise_envelope_width_MPa':float(np.max(np.ptp(np.asarray([targets[k] for k in good]),axis=0))) if len(good)>1 else None}
  # Distinguish a singleton diameter from evidence for material uniqueness.
  df=row['free']['d_Q_diameter_MPa'];dx=row['fixed']['d_Q_diameter_MPa'];row['finite_diameter_increase_MPa']=(df or 0)-(dx or 0);row['not_global_uncertainty_bound']=True;sets.append(row)
 return {'candidates':out,'pairs':pairs,'compatibility':sets,'numerical_reference_not_error_bound':True,'actual_FE_only':True}
