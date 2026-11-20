"""Frozen B2 finite-response metrics. Inputs in N, m and Pa; no fitting."""
import numpy as np
SEGMENTS=((0,60),(60,120),(120,180),(180,241))
STRAINS=np.linspace(.002,.10,981)
SIX=np.array([.002,.005,.01,.02,.05,.10])
def rms(x):return float(np.sqrt(np.mean(np.asarray(x,dtype=float)**2)))
def aligned(u,f,grid):
 u=np.asarray(u);f=np.asarray(f);g=np.asarray(grid)
 if len(u)!=len(f) or np.any(np.diff(u)<=0) or not np.isfinite(u).all() or not np.isfinite(f).all():raise ValueError('Invalid native history')
 if u[0]>g[0] or u[-1]<g[-1]:raise ValueError('No extrapolation allowed')
 return np.interp(g,u,f)
def metrics(d,grid):
 d=np.asarray(d);grid=np.asarray(grid);i=int(np.argmax(abs(d)))
 def single(x):return {'RMS_N':rms(x),'mean_signed_N':float(np.mean(x)),'min_N':float(min(x)),'max_N':float(max(x)),'max_abs_N':float(max(abs(x)))}
 return {**single(d),'max_abs_at_mm':float(grid[i]*1000),'max_abs_index':i,'segment_metrics':[{'indices':[a,b],**single(d[a:b]),'squared_response_fraction':float(np.sum(d[a:b]**2)/np.sum(d**2)) if np.sum(d**2)>0 else None} for a,b in SEGMENTS]}
def pair(minus,plus,base,grid,c):
 odd=(np.asarray(plus)-minus)/2;even=(np.asarray(plus)+minus)/2-base;k=odd/c
 return {'odd':odd,'even':even,'K':k,'summary':{'minus':metrics(minus-base,grid),'plus':metrics(plus-base,grid),'paired_plus_minus':metrics(plus-minus,grid),'odd':metrics(odd,grid),'even':metrics(even,grid),'even_over_odd':rms(even)/rms(odd) if rms(odd)>0 else None,'finite_log_rate_secant_RMS_N':rms(k)}}
def target_Q(table,strains=STRAINS,E=210e9):
 t=np.asarray(table);p=t[:,1];s=t[:,0];x=np.r_[0,p+s/E];y=np.r_[0,s]
 if p[0]!=0 or np.any(np.diff(p)<=0) or np.any(np.diff(s)<0):raise ValueError('Invalid plastic table')
 if np.min(strains)<0 or np.max(strains)>x[-1]:raise ValueError('No target extrapolation')
 return np.interp(strains,x,y)/1e6
def compatibility(curves,targets,base):
 ids=list(curves);out=[]
 for tau in [1,2,5,10]:
  good=[k for k in ids if rms(curves[k]-base)<=tau];pairs=[(a,b,rms(targets[a]-targets[b])) for i,a in enumerate(good) for b in good[i+1:]]
  diam=max(pairs,key=lambda v:v[2]) if pairs else None
  out.append({'tau_N':tau,'candidate_ids':good,'count':len(good),'set_state':'EMPTY' if not good else 'SINGLETON_NO_PAIRWISE_DIAMETER' if len(good)==1 else 'FINITE_MULTIPLE','d_Q_diameter_MPa':diam[2] if diam else None,'diameter_pair':list(diam[:2]) if diam else None,'max_pointwise_envelope_width_MPa':float(np.max(np.ptp(np.array([targets[x] for x in good]),axis=0))) if len(good)>1 else None,'scope':'finite evaluated candidate pool only; not uncertainty upper bound or uniqueness'})
 return out
