"""Offline increment-refinement comparison, no solver or queue interface.

Call compare only with a provenance-reviewed frozen target and matching contract.
Curve tests are not overall numerical/physical qualification.
"""
import math
from inverse.fd_loss import Curve, Target, ScientificEvidence, evaluate, interpolate

def compare(target, original, validation, contract, *, original_status, validation_status):
    if target.configuration_id != contract['loss_version']:
        raise ValueError('Loss version mismatch')
    if target.force_reference_n != contract['force_reference_n']:
        raise ValueError('Force normalization mismatch')
    if len(target.curve.force) != contract['point_count'] or any(w != 1 for w in target.weights):
        raise ValueError('Fixed equal-weight grid required')
    expected=contract['grid_m']
    if tuple(expected)!=target.curve.displacement:
        raise ValueError('Frozen displacement grid mismatch')
    ev=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True)
    a=evaluate(target,original,fe_status=original_status,evidence=ev,mode='PROVISIONAL')
    b=evaluate(target,validation,fe_status=validation_status,evidence=ev,mode='PROVISIONAL')
    old=interpolate(original,expected);new=interpolate(validation,expected)
    delta=[v-o for o,v in zip(old,new)];absolute=[abs(v) for v in delta]
    rmse=math.sqrt(math.fsum(v*v for v in delta)/len(delta))
    maxidx=max(range(len(delta)),key=absolute.__getitem__)
    floor=contract['relative_force_floor_n']
    relative=[abs(d)/max(abs(f),floor) for d,f in zip(delta,old)]
    ridx=max(range(len(delta)),key=relative.__getitem__)
    eligible=[j for j,f in enumerate(old) if abs(f)>=floor]
    rawidx=max(eligible,key=lambda j:absolute[j]/abs(old[j])) if eligible else None
    thresholds=contract['thresholds']
    checks={'force_rmse':rmse<=thresholds['force_rmse_n'],
        'max_absolute_force':absolute[maxidx]<=thresholds['max_absolute_force_n'],
        'max_regularized_relative':relative[ridx]<=thresholds['max_regularized_relative'],
        'absolute_loss_change':abs(b['loss']-a['loss'])<=thresholds['absolute_loss_change']}
    return dict(status='CURVE_GATE_PASS' if all(checks.values()) else 'CURVE_GATE_FAIL',
        checks=checks,force_rmse_n=rmse,max_absolute_force_n=absolute[maxidx],
        max_absolute_at_m=expected[maxidx],max_regularized_relative=relative[ridx],
        max_regularized_relative_at_m=expected[ridx],relative_force_floor_n=floor,
        max_raw_relative_above_floor=None if rawidx is None else absolute[rawidx]/abs(old[rawidx]),
        max_raw_relative_above_floor_at_m=None if rawidx is None else expected[rawidx],
        raw_relative_excluded_count=len(delta)-len(eligible),
        original_loss=a['loss'],validation_loss=b['loss'],loss_change=b['loss']-a['loss'],
        qualification='PENDING_EXECUTION_PROVENANCE_AND_NUMERICAL_DIAGNOSTIC_REVIEW')
