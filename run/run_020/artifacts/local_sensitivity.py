"""Offline finite differences on an already gated fixed grid, no file/solver I/O.

Caller must enforce frozen identities, SI and full fixed-window coverage before
supplying vectors. Missing pairs remain missing. This function is not executed
on invented results during preparation.
"""
import math
import numpy as np

def analyze(force_by_point, displacement_m, *, force_reference_n=1428.9, h=.05):
    u=np.asarray(displacement_m,dtype=float)
    if u.ndim!=1 or len(u)!=241 or not np.isfinite(u).all() or not np.all(np.diff(u)>0):
        raise ValueError('Finite increasing frozen 241-point grid required')
    if u[0]!=0 or not np.isclose(u[-1],.0012,rtol=0,atol=1e-15):
        raise ValueError('Frozen 0-1.2 mm window required')
    if h!=.05 or force_reference_n!=1428.9:raise ValueError('Frozen h and force reference required')
    if not set(force_by_point)<= {'C','L01','L02','L03','L04'}:raise ValueError('Unknown point')
    data={k:np.asarray(v,dtype=float) for k,v in force_by_point.items()}
    if any(v.shape!=u.shape or not np.isfinite(v).all() for v in data.values()):raise ValueError('Paired finite forces required')
    sx=(data['L02']-data['L01'])/(2*h) if {'L01','L02'}<=data.keys() else None
    sy=(data['L04']-data['L03'])/(2*h) if {'L03','L04'}<=data.keys() else None
    rms=lambda v:float(np.sqrt(np.mean(v*v)))
    def matrix(a,b):
        j=np.column_stack((a,b));sv=np.linalg.svd(j,compute_uv=False)
        rank=int(np.sum(sv>max(j.shape)*np.finfo(float).eps*sv[0])) if sv[0] else 0
        norms=np.linalg.norm(j,axis=0)
        cos=float(np.clip(np.dot(a,b)/np.prod(norms),-1,1)) if np.all(norms>0) else None
        return dict(norms_n=norms.tolist(),rms_n=[rms(a),rms(b)],cosine=cos,angle_degrees=math.degrees(math.acos(cos)) if cos is not None else None,
            singular_values_raw=sv.tolist(),singular_values_normalized_rms=(sv/(force_reference_n*math.sqrt(len(a)))).tolist(),
            condition_number=float(sv[0]/sv[1]) if rank==2 else None,numerical_rank=rank)
    result=dict(status='EXPLORATORY_LOCAL_SECANTS_ONLY',Sx_n=None if sx is None else sx.tolist(),Sy_n=None if sy is None else sy.tolist(),
        matrix=None,intervals=[],curvature_rms_n={},global_uniqueness_proven=False,confidence_interval=None,numerical_error_bound=None)
    for name,minus,plus in [('x','L01','L02'),('y','L03','L04')]:
        if {'C',minus,plus}<=data.keys():result['curvature_rms_n'][name]=rms((data[plus]+data[minus]-2*data['C'])/h**2)
    if sx is not None and sy is not None:
        result['matrix']=matrix(sx,sy)
        for a,b in [(0,.0004),(.0004,.0008),(.0008,.0012)]:
            mask=(u>=a)&((u<b) if b<.0012 else (u<=b))
            result['intervals'].append(dict(range_m=[a,b],count=int(mask.sum()),**matrix(sx[mask],sy[mask])))
    return result
