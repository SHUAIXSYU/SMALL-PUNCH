"""Solver-free F-D loss on a frozen target grid; SI only, no extrapolation.

No sorting, averaging, zero shift, smoothing or data deletion occurs here.
Provisional mode is explicit and never grants permission to run an optimizer.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math
from numbers import Real


class InvalidCurve(ValueError):
    pass


class ScientificGateError(ValueError):
    pass


def _finite(values, name):
    result = tuple(values)
    if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(v)
           for v in result):
        raise InvalidCurve(f'{name}: finite real values required')
    return tuple(float(v) for v in result)


@dataclass(frozen=True)
class Curve:
    displacement: tuple
    force: tuple
    displacement_unit: str
    force_unit: str

    def __post_init__(self):
        if (self.displacement_unit, self.force_unit) != ('m', 'N'):
            raise InvalidCurve('Explicit SI units m and N required; convert upstream')
        u = _finite(self.displacement, 'displacement')
        f = _finite(self.force, 'force')
        if len(u) != len(f) or len(u) < 2:
            raise InvalidCurve('At least two paired points required')
        if any(b <= a for a, b in zip(u, u[1:])):
            raise InvalidCurve('Displacement must strictly increase; split branches upstream')
        object.__setattr__(self, 'displacement', u)
        object.__setattr__(self, 'force', f)


@dataclass(frozen=True)
class Target:
    curve: Curve
    weights: tuple
    force_reference_n: float
    configuration_id: str

    def __post_init__(self):
        w = _finite(self.weights, 'weights')
        ref = _finite((self.force_reference_n,), 'reference')[0]
        if len(w) != len(self.curve.force) or any(v <= 0 for v in w):
            raise InvalidCurve('One positive fixed weight per target point required')
        if ref <= 0 or not self.configuration_id:
            raise InvalidCurve('Positive fixed force reference and configuration ID required')
        object.__setattr__(self, 'weights', w)
        object.__setattr__(self, 'force_reference_n', ref)


@dataclass(frozen=True)
class ScientificEvidence:
    provenance_verified: bool = False
    units_and_sign_verified: bool = False
    measurement_aligned: bool = False
    conditions_matched: bool = False
    numerical_quality_accepted: bool = False

    def unresolved(self):
        return tuple(k for k, v in self.__dict__.items() if v is not True)


def interpolate(fe: Curve, target_u):
    """Linear interpolation at specified points; coverage cannot change the target."""
    points = _finite(target_u, 'target displacement')
    x, y = fe.displacement, fe.force
    if any(u < x[0] or u > x[-1] for u in points):
        raise InvalidCurve('FE does not cover frozen target; no extrapolation or auto-crop')
    result = []
    for u in points:
        j = min(max(bisect_right(x, u) - 1, 0), len(x) - 2)
        t = (u - x[j]) / (x[j+1] - x[j])
        result.append((1-t) * y[j] + t * y[j+1])
    return tuple(result)


def evaluate(target: Target, fe: Curve, *, fe_status, evidence: ScientificEvidence,
             mode='FORMAL'):
    if fe_status not in ('COMPLETED', 'COMPLETED_WITH_WARNINGS'):
        raise InvalidCurve('Failed, pending or unknown FE result cannot be scored')
    if mode not in ('FORMAL', 'PROVISIONAL'):
        raise ValueError('mode must be FORMAL or PROVISIONAL')
    missing = evidence.unresolved()
    if mode == 'FORMAL' and missing:
        raise ScientificGateError('Unresolved: ' + ', '.join(missing))
    predicted = interpolate(fe, target.curve.displacement)
    w = target.weights
    # Normalize before squaring and normalize weights to reduce overflow risk.
    max_w = max(w)
    scaled_w = tuple(v / max_w for v in w)
    residual = tuple((p-e)/target.force_reference_n
                     for p, e in zip(predicted, target.curve.force))
    try:
        value = math.fsum(v*r*r for v, r in zip(scaled_w, residual)) / math.fsum(scaled_w)
    except (OverflowError, ValueError) as exc:
        raise InvalidCurve('Nonfinite residual arithmetic') from exc
    if not math.isfinite(value):
        raise InvalidCurve('Nonfinite loss')
    return {'loss': value, 'mode': mode, 'configuration_id': target.configuration_id,
            'point_count': len(predicted), 'unresolved': list(missing),
            'fe_status': fe_status, 'interpolation': 'linear_no_extrapolation'}
