"""Fixed-grid metrics for intentional material contrasts, not refinement PASS gates."""
import math
import numpy as np
from inverse.fd_loss import Curve,ScientificEvidence,evaluate,interpolate

def assess_curve(target,curve,baseline_aligned,*,software_status,numerical_accepted):
    aligned=np.array(interpolate(curve,target.curve.displacement),dtype=float)
    evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True,numerical_quality_accepted=numerical_accepted)
    result=evaluate(target,curve,fe_status=software_status,evidence=evidence,mode='PROVISIONAL') if numerical_accepted else None
    u=np.array(target.curve.displacement);exp=np.array(target.curve.force);base=np.array(baseline_aligned);delta=aligned-base;residual=aligned-exp
    metrics={'loss':None if result is None else result['loss'],'loss_scope':'frozen exploratory/provisional SPT target; no formal physical validation','RMSE_to_experiment_N':None if result is None else float(np.sqrt(np.mean(residual**2))),'NRMSE_to_experiment':None if result is None else float(np.sqrt(np.mean(residual**2))/target.force_reference_n),'RMSE_vs_D01_N':float(np.sqrt(np.mean(delta**2))),'max_abs_force_difference_N':float(np.max(abs(delta))),'max_abs_force_difference_at_mm':float(u[np.argmax(abs(delta))]*1000),'signed_bias_vs_D01_N':float(np.mean(delta)),'max_regularized_relative_difference':float(np.max(abs(delta)/np.maximum(abs(base),71.445))),'raw_order_delta_positive_points':int(np.sum(delta>0)),'raw_order_delta_negative_points':int(np.sum(delta<0)),'raw_order_zero_points':int(np.sum(delta==0)),'first_frozen_max_effect_flag_exceedance_mm':float(u[np.flatnonzero(abs(delta)>7.1445)[0]]*1000) if np.any(abs(delta)>7.1445) else None,'effect_flag_note':'7.1445N frozen engineering response marker; not statistical significance or uncertainty bound','F_at_1p2mm_N':float(aligned[-1]),'diagnostic_only_if_unscoreable':not numerical_accepted}
    metrics['bands']=[];masks=[]
    for ix,(lo,hi) in enumerate([(0,.0003),(.0003,.0006),(.0006,.0009),(.0009,.0012)]):
        mask=(u>=lo-1e-15)&((u<hi-1e-15) if ix<3 else (u<=hi+1e-15));masks.append(mask);d=delta[mask];r=residual[mask]
        metrics['bands'].append({'range_mm':[lo*1000,hi*1000],'points':int(np.sum(mask)),'RMSE_vs_D01_N':float(np.sqrt(np.mean(d*d))),'max_abs_force_difference_N':float(np.max(abs(d))),'mean_signed_difference_N':float(np.mean(d)),'RMSE_to_experiment_N':None if result is None else float(np.sqrt(np.mean(r*r))),'loss_contribution_full_window':None if result is None else float(np.sum((r/target.force_reference_n)**2)/241),'mean_signed_residual_to_experiment_N':float(np.mean(r))})
    assert np.all(sum(mask.astype(int) for mask in masks)==1) and sum(v['points'] for v in metrics['bands'])==241
    if result is not None:
        manual=math.fsum(((float(a)-float(b))/target.force_reference_n)**2 for a,b in zip(aligned,exp))/241
        assert abs(manual-result['loss'])<1e-15
        assert abs(sum(v['loss_contribution_full_window'] for v in metrics['bands'])-result['loss'])<1e-15
    return metrics,aligned,delta,residual

def pair_symmetry(low,high,baseline):
    lo=np.array(low)-np.array(baseline);hi=np.array(high)-np.array(baseline);mid=(lo+hi)/2;scale=np.linalg.norm(lo)+np.linalg.norm(hi)
    return {'midpoint_response_RMSE_vs_D01_N':float(np.sqrt(np.mean(mid*mid))),'midpoint_response_max_abs_N':float(np.max(abs(mid))),'relative_antisymmetry_defect':float(np.linalg.norm(lo+hi)/scale) if scale else None,'definition':'||deltaH02+deltaH01||/(||deltaH02||+||deltaH01||),0 exactly opposing equal responses; finite-amplitude nonlinear diagnostic only','H02_below_H01_raw_grid_count':int(np.sum(np.array(high)<np.array(low))),'maximum_order_inversion_N':float(max(0,np.max(np.array(low)-np.array(high)))),'not_global_identifiability_or_error_bound':True}
