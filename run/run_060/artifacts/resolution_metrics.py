"""Prospective I06 adjacent-increment diagnostics; no fitted or formal convergence threshold."""
import math
from bisect import bisect_left
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate

def risk_band(ratio):
    if not math.isfinite(ratio) or ratio<0:raise ValueError('finite nonnegative ratio required')
    if ratio<=.1:return 'R_LE_0p10_SMALL_OBSERVED_CHANGE'
    if ratio<=.25:return 'R_0p10_TO_0p25_NONNEGLIGIBLE'
    if ratio<=.5:return 'R_0p25_TO_0p50_SUBSTANTIAL_WEAK_SIGNAL_RISK'
    return 'R_GT_0p50_HIGH_WEAK_SIGNAL_RISK'

def compare_responses(target,original,refined,*,weak_RMS_N,relative_floor_N=71.445,original_status='COMPLETED_WITH_WARNINGS',refined_status='COMPLETED_WITH_WARNINGS'):
    if weak_RMS_N<=0 or not math.isfinite(weak_RMS_N):raise ValueError('positive frozen weak signal required')
    if target.configuration_id!='run017-exploratory-fd-v1' or target.force_reference_n!=1428.9 or len(target.curve.force)!=241 or any(w!=1 for w in target.weights):raise ValueError('frozen target contract mismatch')
    if relative_floor_N!=71.445:raise ValueError('regularized denominator contract mismatch')
    grid=target.curve.displacement
    a=interpolate(original,grid);b=interpolate(refined,grid);d=[y-x for x,y in zip(a,b)]
    rms=math.sqrt(math.fsum(v*v for v in d)/len(d));i=max(range(len(d)),key=lambda i:abs(d[i]));relative=[abs(v)/max(abs(x),relative_floor_N) for x,v in zip(a,d)];j=max(range(len(d)),key=relative.__getitem__)
    evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True)
    old=evaluate(target,original,fe_status=original_status,evidence=evidence,mode='PROVISIONAL');new=evaluate(target,refined,fe_status=refined_status,evidence=evidence,mode='PROVISIONAL')
    ratio=rms/weak_RMS_N
    return {'force_difference_RMSE_N':rms,'max_absolute_force_difference_N':abs(d[i]),'max_absolute_at_m':grid[i],'max_regularized_relative_difference':relative[j],'max_regularized_relative_at_m':grid[j],'regularized_force_floor_N':relative_floor_N,'original_loss':old['loss'],'refined_loss':new['loss'],'delta_loss':new['loss']-old['loss'],'absolute_delta_loss':abs(new['loss']-old['loss']),'weak_reference_RMS_N':weak_RMS_N,'R_RMSE':ratio,'risk_band':risk_band(ratio),'formal_numerical_convergence':'NOT_ESTABLISHED_BY_A_SINGLE_REFINEMENT','metrics_are_not_a_solver_or_scoring_admission_gate':True}

def stage_peeq(native_u,frame_max_peeq,stages_m=(.0003,.0006,.0009,.0012)):
    x=tuple(float(v) for v in native_u);p=tuple(float(v) for v in frame_max_peeq)
    if len(x)!=len(p) or len(x)<2 or not all(math.isfinite(v) for v in x+p) or any(b<=a for a,b in zip(x,x[1:])) or any(v<0 for v in p):raise ValueError('invalid accepted-frame scalar history')
    output=[]
    for q in stages_m:
        if q<x[0] or q>x[-1]:raise ValueError('stage extrapolation prohibited')
        j=bisect_left(x,q);i=max(0,j-1);j=min(j,len(x)-1)
        if x[j]==q:i=j
        t=0 if i==j else (q-x[i])/(x[j]-x[i]);estimate=(1-t)*p[i]+t*p[j]
        nearest=min([i,j],key=lambda k:(abs(x[k]-q),k))
        output.append({'target_m':q,'left_index':i,'right_index':j,'left_u_m':x[i],'right_u_m':x[j],'interpolated_frame_max_peeq':estimate,'nearest_frame_index':nearest,'nearest_u_m':x[nearest],'nearest_frame_max_peeq':p[nearest],'nearest_offset_m':x[nearest]-q,'within_predeclared_stage_offset_3um':abs(x[nearest]-q)<=3e-6,'scope':'interpolated scalar maximum diagnostic only, not a new FE field or same material-point comparison'})
    return output
