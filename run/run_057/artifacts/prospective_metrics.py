"""Frozen A/B metrics. Inputs are already-admitted responses, never solver commands."""
import numpy as np

def local_secants(center, syminus, syplus, nminus, nplus, row_scales, h=.025):
    phi=np.asarray([center,syminus,syplus,nminus,nplus],dtype=float)
    if phi.ndim!=2 or not np.isfinite(phi).all():raise ValueError('five finite response vectors required')
    scale=np.asarray(row_scales,dtype=float)
    if scale.shape!=(phi.shape[1],) or np.any(scale<=0):raise ValueError('explicit positive row scales required')
    z=phi/scale/np.sqrt(phi.shape[1]);v0,sm,sp,nm,np_=z
    j=np.column_stack([(sp-sm)/(2*h),(np_-nm)/(2*h)])
    singular=np.linalg.svd(j,compute_uv=False);tol=max(j.shape)*np.finfo(float).eps*singular[0]
    rank=int(np.sum(singular>tol));norms=np.linalg.norm(j,axis=0)
    cosine=float(j[:,0]@j[:,1]/np.prod(norms)) if np.prod(norms)>0 else None
    condition=float(singular[0]/singular[-1]) if rank==2 else None
    axes={}
    for name,minus,plus in [('x',sm,sp),('y',nm,np_)]:
        even=(plus+minus)/2-v0;odd=(plus-minus)/2;den=np.linalg.norm(odd)
        axes[name]={'positive_slope':((plus-v0)/h).tolist(),'negative_slope':((v0-minus)/h).tolist(),'even_odd_ratio':float(np.linalg.norm(even)/den) if den>0 else None}
    return {'J':j.tolist(),'column_norms':norms.tolist(),'cosine':cosine,'angle_deg':float(np.degrees(np.arccos(np.clip(cosine,-1,1)))) if cosine is not None else None,'singular_values':singular.tolist(),'rank_tolerance':float(tol),'rank':rank,'condition_number':condition,'condition_status':'FINITE' if rank==2 else 'SINGULAR','axes':axes,'h':h,'derivative_scope':'same-base same-contract central finite secant; not strict converged differential derivative','step_convergence':'NOT_EVALUABLE','Fisher_CI':'NOT_EVALUABLE'}

def normalized(physical):
    p=np.asarray(physical,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or not np.isfinite(p).all() or np.any(p[:,0]<=0):raise ValueError('finite sigma>0 and n required')
    return np.column_stack([np.log(p[:,0]/150)/np.log(1000/150),(p[:,1]-.02)/.48])

def recovery_score(predicted, truth, center=(.24,.16), h=.025):
    p=np.asarray(predicted,dtype=float);t=np.asarray(truth,dtype=float)
    if p.shape!=t.shape or p.shape!=(4,2):raise ValueError('four paired unique parameter points required')
    q=normalized(p);qt=normalized(t);dq=q-qt;delta=qt-np.array(center)
    active=np.argmax(abs(delta),axis=1)
    # Roundoff zero only, not prediction recentering or an acceptance tolerance.
    def direction(v):return 0 if abs(v)<=1e-12 else int(np.sign(v))
    sign=[bool(direction(q[i,a]-center[a])==direction(delta[i,a])) for i,a in enumerate(active)]
    e=p-t;local=float(np.sqrt(np.mean((dq/h)**2)));constant=float(2**-.5)
    halfstep=bool(np.all(abs(dq)<=h/2+1e-12))
    return {'raw_predictions_MPa_n':p.tolist(),'errors_MPa_n':e.tolist(),'relative_absolute_errors':(abs(e)/abs(t)).tolist(),'MAE_MPa_n':np.mean(abs(e),axis=0).tolist(),'RMSE_MPa_n':np.sqrt(np.mean(e*e,axis=0)).tolist(),'max_abs_error_MPa_n':np.max(abs(e),axis=0).tolist(),'normalized_errors':dq.tolist(),'each_coordinate_within_half_step':halfstep,'active_axis_sign_correct':sign,'E_local':local,'constant_I06_E_local':constant,'beats_constant_I06':bool(local<constant-1e-12),'engineering_resolution_goal_met':bool(halfstep and all(sign) and local<constant-1e-12),'scope':'preregistered local resolution goal only; not material accuracy acceptance or statistical significance'}
