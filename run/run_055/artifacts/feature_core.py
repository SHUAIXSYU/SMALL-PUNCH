"""Fixed physical features of an existing piecewise-linear force curve."""
import numpy as np
LOAD_MM=(.15,.30,.45,.60,.75,.90,1.05,1.20)
SLOPE_MM=((.15,.30),(.30,.60),(.60,.90),(.90,1.20))
AREA_MM=((0,.3),(.3,.6),(.6,.9),(.9,1.2),(0,1.2))
def tag(x):return f'{x:.2f}'.replace('.','p')
NAMES=tuple('F_'+tag(x) for x in LOAD_MM)+tuple('K_'+tag(a)+'_'+tag(b) for a,b in SLOPE_MM)+tuple('W_'+tag(a)+'_'+tag(b) for a,b in AREA_MM)
FIXED2=(0,5)
FIXED5=(0,1,3,5,16)
GRID=np.linspace(0,.0012,241)
def validate(u,f):
 u=np.asarray(u,dtype=float);f=np.asarray(f,dtype=float)
 if u.ndim!=1 or u.shape!=f.shape or len(u)<2 or not np.isfinite(u).all() or not np.isfinite(f).all():raise ValueError('invalid/NaN FD')
 if np.any(np.diff(u)<=0):raise ValueError('nonmonotone displacement')
 if u[0]>0 or u[-1]<.0012:raise ValueError('incomplete fixed window; no extrapolation')
 return u,f
def interp(u,f,q):
 q=np.asarray(q,dtype=float)
 if np.min(q)<u[0] or np.max(q)>u[-1]:raise ValueError('extrapolation forbidden')
 return np.interp(q,u,f)
def area(u,f,lo,hi):
 a,b=lo/1000,hi/1000
 if a>=b:raise ValueError('invalid integration band')
 mids=u[(u>a)&(u<b)];x=np.r_[a,mids,b];y=interp(u,f,x)
 return float(np.trapezoid(y,x))
def extract(u,f):
 u,f=validate(u,f);loads=interp(u,f,np.array(LOAD_MM)/1000)
 slopes=[float((interp(u,f,[b/1000])[0]-interp(u,f,[a/1000])[0])/(b-a)) for a,b in SLOPE_MM]
 areas=[area(u,f,a,b) for a,b in AREA_MM];g=interp(u,f,GRID)
 brackets=[]
 for q in np.array(LOAD_MM)/1000:
  k=int(np.searchsorted(u,q));i=max(0,k-1);j=min(k,len(u)-1)
  brackets.append({'q_m':float(q),'left_index':i,'right_index':j,'left_u_m':float(u[i]),'right_u_m':float(u[j]),'bracket_width_mm':float((u[j]-u[i])*1000),'exact_sample':bool(u[j]==q)})
 slopes_grid=np.diff(g)/.005;turns=int(np.sum(np.diff(slopes_grid)>0))
 return np.r_[loads,slopes,areas],g,{'force_brackets':brackets,'curvature_status':'UNSTABLE_NOT_USED_FOR_INVERSION','raw_points':len(u),'grid_slope_change_RMS_N_per_mm':float(np.sqrt(np.mean(np.diff(slopes_grid)**2))),'positive_slope_changes':turns,'no_smoothing':True}
def physical_to_normalized(y):
 y=np.asarray(y,dtype=float);return np.column_stack([np.log(y[:,0]/150)/np.log(1000/150),(y[:,1]-.02)/.48])
def normalized_to_physical(y):
 y=np.asarray(y,dtype=float);return np.column_stack([150*np.exp(y[:,0]*np.log(1000/150)),.02+.48*y[:,1]])
