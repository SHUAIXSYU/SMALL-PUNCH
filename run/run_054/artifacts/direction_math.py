"""Offline vector diagnostics. Cosine/projections do not assert a joint Jacobian."""
import numpy as np
def rms(a):return float(np.sqrt(np.mean(np.asarray(a,dtype=float)**2)))
def cosine(a,b):
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);d=np.linalg.norm(a)*np.linalg.norm(b)
 return float(np.clip(a@b/d,-1,1)) if d else None
def angle(a,b):
 c=cosine(a,b);return float(np.degrees(np.arccos(c))) if c is not None else None
def alpha_vectors(low,base,high,halfstep=.5):
 if halfstep<=0:raise ValueError('positive alpha halfstep required')
 low,base,high=map(lambda a:np.asarray(a,dtype=float),(low,base,high))
 dm=low-base;dp=high-base;s=(high-low)/(2*halfstep);even=(high+low)/2-base
 return {'minus':dm,'plus':dp,'secant':s,'even':even,'odd':halfstep*s,'forward':dp/halfstep,'backward':-dm/halfstep}
def span_comparison(columns,target):
 A=np.column_stack(columns).astype(float);y=np.asarray(target,dtype=float);norm=np.linalg.norm(A,axis=0)
 if np.any(norm==0):raise ValueError('zero response column')
 U=A/norm;coef,_,rank,singular=np.linalg.lstsq(U,y/np.linalg.norm(y),rcond=None);fit=U@coef;err=y/np.linalg.norm(y)-fit
 return {'unit_shape_coefficients':coef.tolist(),'rank':int(rank),'relative_unrepresented_norm':float(np.linalg.norm(err)),'represented_squared_norm_fraction':float(1-np.linalg.norm(err)**2),'unit_two_column_singular_values':singular.tolist(),'scope':'response-shape projection across studies, not parameter update, joint rank, confidence, Fisher information, or causal confounding proof'}
def loss_decomposition(delta,needed_correction,ref=1428.9):
 d=np.asarray(delta);r=np.asarray(needed_correction);N=len(d);penalty=float(d@d/(N*ref**2));alignment=float(-2*r@d/(N*ref**2))
 return {'response_squared_penalty':penalty,'residual_alignment_term':alignment,'delta_loss':penalty+alignment,'cosine_to_needed_correction':cosine(d,r)}
def band_masks(u):
 u=np.asarray(u);out=[]
 for ix,(lo,hi) in enumerate([(0,.0003),(.0003,.0006),(.0006,.0009),(.0009,.0012)]):
  m=(u>=lo-1e-15)&((u<hi-1e-15) if ix<3 else (u<=hi+1e-15));out.append(m)
 if not np.all(sum(m.astype(int) for m in out)==1):raise ValueError('bands do not partition fixed window')
 return out
