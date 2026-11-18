"""Small linear inverse baselines with fold-local transformations and nested tuning."""
import numpy as np
from itertools import combinations
from feature_core import physical_to_normalized,normalized_to_physical,FIXED2,FIXED5
LAMBDAS=(1e-4,.01,1.,100.)
def standardize(X):
 X=np.asarray(X,dtype=float);mu=X.mean(0);sd=X.std(0);sd=np.where(sd>1e-12,sd,1.)
 return (X-mu)/sd,mu,sd
def ridge_fit(Z,Y,lam):
 yc=Y.mean(0);C=Y-yc;n,p=Z.shape
 if p<n:B=np.linalg.solve(Z.T@Z+lam*n*np.eye(p),Z.T@C)
 else:B=Z.T@np.linalg.solve(Z@Z.T+lam*n*np.eye(n),C)
 return B,yc
def ridge_predict(X,Y,q,lam):
 Z,mu,sd=standardize(X);B,yc=ridge_fit(Z,Y,lam)
 return (q-mu)/sd@B+yc
def inner_cache(X,Y):
 packs=[]
 for i in range(len(X)):
  ix=np.arange(len(X))!=i;z,mu,sd=standardize(X[ix]);packs.append((z,Y[ix],(X[i]-mu)/sd,Y[i]))
 return packs
def inner_score(cache,cols,lam):
 errs=[];cols=list(cols)
 for z,y,q,truth in cache:
  B,yc=ridge_fit(z[:,cols],y,lam);pred=q[cols]@B+yc;errs.append(np.mean((pred-truth)**2))
 return float(np.mean(errs))
def tune(cache,candidates):
 best=None
 for cols in candidates:
  for lam in LAMBDAS:
   score=inner_score(cache,cols,lam);key=(score,-lam,tuple(cols))
   if best is None or key<best[0]:best=(key,tuple(cols),lam)
 return {'columns':list(best[1]),'lambda':best[2],'inner_normalized_MSE':best[0][0]}
def select_views(X,Y):
 cache=inner_cache(X,Y)
 two=tune(cache,combinations(range(8),2));current=two
 for k in [3,4]:
  candidates=[tuple(sorted(current['columns']+[j])) for j in range(X.shape[1]) if j not in current['columns']]
  current=tune(cache,candidates)
 return {'nested_two_ridge':two,'nested_four_ridge':current,'two_ridge':tune(cache,[FIXED2]),'five_ridge':tune(cache,[FIXED5])}
def fit_model(X,Y,kind,columns=None,lam=None,physical=None):
 cols=list(range(X.shape[1])) if columns is None else list(columns);xx=X[:,cols];z,mu,sd=standardize(xx)
 m={'kind':kind,'columns':cols,'mean':mu.tolist(),'scale':sd.tolist(),'training_N':len(X),'lambda':lam}
 if kind=='ridge':
  B,yc=ridge_fit(z,Y,lam);s=np.linalg.svd(z,compute_uv=False);m.update(coefficients=B.tolist(),target_intercept=yc.tolist(),effective_df=float(np.sum(s*s/(s*s+len(z)*lam))))
 elif kind=='nn':m.update(training_standardized=z.tolist(),training_targets=Y.tolist())
 elif kind in ['mean','median']:
  agg=np.mean(physical,0) if kind=='mean' else np.median(physical,0);m['constant_physical']=agg.tolist()
 else:raise ValueError('unknown baseline')
 return m
def predict_model(m,q):
 q=np.atleast_2d(q);cols=m['columns'];z=(q[:,cols]-np.array(m['mean']))/np.array(m['scale'])
 if m['kind']=='ridge':return z@np.array(m['coefficients'])+np.array(m['target_intercept'])
 if m['kind']=='nn':
  dist=np.sum((z[:,None,:]-np.array(m['training_standardized'])[None,:,:])**2,axis=2);return np.array(m['training_targets'])[np.argmin(dist,axis=1)]
 return physical_to_normalized(np.tile(m['constant_physical'],(len(q),1)))
def support(m,Xtrain,q):
 c=m['columns'];xx=Xtrain[:,c];z=(xx-np.array(m['mean']))/np.array(m['scale']);qz=(q[c]-np.array(m['mean']))/np.array(m['scale']);dim=max(1,len(c));dd=np.sqrt(np.mean((z[:,None,:]-z[None,:,:])**2,axis=2));np.fill_diagonal(dd,np.inf);threshold=float(np.quantile(dd.min(1),.95));d=np.sqrt(np.mean((z-qz)**2,axis=1));idx=int(np.argmin(d));marginal=int(np.sum((q[c]<xx.min(0)-1e-10)|(q[c]>xx.max(0)+1e-10)))
 return {'nearest_train_index':idx,'distance_RMS_standardized':float(d[idx]),'train_nearest_LOO_distance_q95':threshold,'distance_exceeds_q95':bool(d[idx]>threshold),'feature_marginal_outside_count':marginal}
