"""Candidate true-total Hollomon law; NOT a physically validated material model.

Fixed E=210 GPa, nu=0.3. Input yield stress is MPa; output rows are
(true yield stress in Pa, dimensionless equivalent plastic strain).
The uniaxial conversion assumes small elastic strain and monotonic J2 loading.
No Abaqus imports, solver calls, file writes, or third-party dependencies.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math
from numbers import Real

YOUNGS_MODULUS_PA = 210_000_000_000.0
POISSON_RATIO = 0.3
MPA_TO_PA = 1_000_000.0
MODEL_ID = 'candidate-true-total-hollomon-v1'


class SamplingError(RuntimeError):
    """Requested interpolation tolerance cannot be met within numerical limits."""


def _number(name, value, *, minimum=0.0, strict=True):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a real number, not bool or a string')
    try:
        value = float(value)
    except (OverflowError, TypeError) as exc:
        raise ValueError(f'{name} is outside representable numerical range') from exc
    if not math.isfinite(value) or (value <= minimum if strict else value < minimum):
        relation = '>' if strict else '>='
        raise ValueError(f'{name} must be finite and {relation} {minimum}')
    return value


def _parameters(sigma_y_mpa, n):
    sigma_y_mpa = _number('sigma_y_mpa', sigma_y_mpa)
    n = _number('n', n)
    if n >= 1:
        raise ValueError('This hardening candidate requires 0 < n < 1')
    sy = sigma_y_mpa * MPA_TO_PA
    ey = sy / YOUNGS_MODULUS_PA
    if not math.isfinite(sy) or not math.isfinite(ey) or ey <= 0:
        raise ValueError('Yield stress is outside representable numerical range')
    return sy, ey, n


@dataclass(frozen=True)
class _Point:
    t: float  # log(epsilon_total / epsilon_y)
    p: float
    stress: float


def _at_t(t, sy, ey, n):
    try:
        power = math.exp(n*t)
        # Stable equivalent of ey * (r-r**n), especially immediately after yield.
        p = ey * power * math.expm1((1-n)*t)
        stress = sy * power
    except OverflowError as exc:
        raise ValueError('Requested material range overflows floating point') from exc
    if not math.isfinite(p) or not math.isfinite(stress):
        raise ValueError('Nonfinite material state')
    return _Point(t, p, stress)


def _at_p(p, sy, ey, n):
    if p == 0:
        return _Point(0., 0., sy)
    scaled = p / ey / (1-n)
    if not math.isfinite(scaled):
        raise ValueError('Plastic strain / yield strain ratio is too large')
    # Concavity of r**n gives r-r**n >= (1-n)*(r-1), hence this upper bracket.
    lo, hi = 0., math.log1p(scaled)
    for _ in range(180):
        mid = (lo+hi)*.5
        if mid == lo or mid == hi:
            break
        point = _at_t(mid, sy, ey, n)
        if point.p < p:
            lo = mid
        else:
            hi = mid
    point = _at_t((lo+hi)*.5, sy, ey, n)
    if abs(point.p-p) > 1e-12*p:
        raise SamplingError('Plastic strain inversion failed relative residual check')
    return _Point(point.t, p, point.stress)


def stress_at_plastic_strain(plastic_strain, sigma_y_mpa, n):
    """Return analytic candidate stress (Pa); no table interpolation/extrapolation."""
    sy, ey, n = _parameters(sigma_y_mpa, n)
    p = _number('plastic_strain', plastic_strain, strict=False)
    return _at_p(p, sy, ey, n).stress


def stress_from_total_strain(total_strain, sigma_y_mpa, n):
    """Full monotonic tensile piecewise law in true total strain, returning Pa."""
    sy, ey, n = _parameters(sigma_y_mpa, n)
    epsilon = _number('total_strain', total_strain, strict=False)
    if epsilon <= ey:
        return YOUNGS_MODULUS_PA*epsilon
    result = sy * math.exp(n*(math.log(epsilon)-math.log(ey)))
    if not math.isfinite(result):
        raise ValueError('Nonfinite material stress')
    return result


def _segment_peak(left, right, sy, ey, n):
    """Maximum absolute chord error for concave stress(p), in float arithmetic.

    d(stress)/dp = E*n/(exp((1-n)*t)-n), a decreasing derivative.
    The unique interior maximum satisfies derivative = chord slope.
    """
    slope = (right.stress-left.stress)/(right.p-left.p)
    if slope <= 0:
        raise SamplingError('Unresolved positive hardening at floating-point precision')
    t = (math.log(n)+math.log1p(YOUNGS_MODULUS_PA/slope))/(1-n)
    if not left.t < t < right.t:
        raise SamplingError('Cannot resolve analytic chord-error maximum; relax tolerance/range')
    point = _at_t(t, sy, ey, n)
    if not left.p < point.p < right.p:
        raise SamplingError('Cannot resolve interior plastic strain; relax tolerance/range')
    chord = left.stress+slope*(point.p-left.p)
    return point, max(0., point.stress-chord)


@dataclass(frozen=True)
class MaterialTable:
    """Immutable candidate rows and numerical guarantees on their covered interval."""
    sigma_y_mpa: float
    n: float
    max_plastic_strain: float
    rows: tuple
    relative_tolerance: float
    absolute_tolerance_pa: float
    max_absolute_chord_error_pa: float
    conservative_relative_error_bound: float
    max_normalized_error_bound: float
    model_id: str = MODEL_ID
    physically_validated: bool = False
    youngs_modulus_pa: float = YOUNGS_MODULUS_PA
    poisson_ratio: float = POISSON_RATIO

    def interpolate(self, plastic_strain):
        """Linear interpolation; reject out-of-coverage queries rather than extrapolate."""
        p = _number('plastic_strain', plastic_strain, strict=False)
        if p > self.max_plastic_strain:
            raise ValueError('Plastic strain exceeds table coverage; regenerate explicitly')
        coordinates = [row[1] for row in self.rows]
        i = min(bisect_right(coordinates, p), len(self.rows)-1)
        if i == 0:
            return self.rows[0][0]
        s0,p0 = self.rows[i-1]; s1,p1 = self.rows[i]
        return s0+(s1-s0)*(p-p0)/(p1-p0)

    def abaqus_plastic_text(self):
        """Material-only fragment, not a Job; returns text and writes no files."""
        comments = (
            f'** CANDIDATE ONLY: {self.model_id}; NOT PHYSICALLY VALIDATED\n'
            '** True total Hollomon; p = epsilon_total - sigma/E\n'
            '** Stress: Pa; plastic strain: dimensionless\n'
            '** Companion elastic constants: E=210000000000 Pa, nu=0.3\n'
            f'** Coverage p <= {self.max_plastic_strain:.17g}; do not assume future adequacy\n'
            '*Plastic\n'
        )
        return comments + ''.join(f'{s:.17g}, {p:.17g}\n' for s,p in self.rows)


def generate_hollomon_table(sigma_y_mpa, n, *, max_plastic_strain,
                            relative_tolerance=1e-3, absolute_tolerance_pa=0.,
                            max_points=10000):
    """Generate adaptive (yield stress Pa, equivalent plastic strain) rows.

    Coverage must be supplied explicitly. Inputs use MPa solely for sigma_y_mpa;
    E is fixed at 210 GPa. Valid hardening exponent: 0 < n < 1.
    Each segment is split at its analytic maximum absolute chord error until
    error <= absolute_tolerance_pa + relative_tolerance * left_endpoint_stress.
    Since stress increases, this conservatively bounds error at every point by
    absolute_tolerance_pa + relative_tolerance * analytic_stress(point).
    The bound concerns the chosen mathematical law in double precision, not
    physical validity, solver convergence, or multi-axial F-D accuracy.
    """
    sy, ey, n = _parameters(sigma_y_mpa, n)
    maximum = _number('max_plastic_strain', max_plastic_strain)
    rtol = _number('relative_tolerance', relative_tolerance, strict=False)
    atol = _number('absolute_tolerance_pa', absolute_tolerance_pa, strict=False)
    if rtol == 0 and atol == 0:
        raise ValueError('At least one interpolation tolerance must be positive')
    if isinstance(max_points,bool) or not isinstance(max_points,int) or max_points < 2:
        raise ValueError('max_points must be an integer >= 2')
    first, last = _Point(0.,0.,sy), _at_p(maximum,sy,ey,n)
    pending = [(first,last)]
    accepted = []
    count = 2
    while pending:
        left,right = pending.pop()
        point,error = _segment_peak(left,right,sy,ey,n)
        budget = atol+rtol*left.stress
        if error <= budget:
            accepted.append((left,right,error,budget))
        else:
            if count >= max_points:
                raise SamplingError(f'Tolerance needs more than max_points={max_points}; no partial table returned')
            count += 1
            pending.extend([(point,right),(left,point)])
    accepted.sort(key=lambda item:item[0].p)
    points = [accepted[0][0]]+[segment[1] for segment in accepted]
    rows = tuple((point.stress,point.p) for point in points)
    for a,b in zip(rows,rows[1:]):
        if not (b[0]>a[0] and b[1]>a[1]):
            raise SamplingError('Table is not strictly monotone')
    return MaterialTable(float(sigma_y_mpa),n,maximum,rows,rtol,atol,
                         max(item[2] for item in accepted),
                         max(item[2]/item[0].stress for item in accepted),
                         max(item[2]/item[3] for item in accepted))


def suggest_plastic_coverage(observed_max_peeq, *, safety_factor=1.25, round_step=.1):
    """Numerical coverage proposal, NOT a material-validity or future-solve bound.

    Uses the full stored-frame maximum, never a percentile. All-zero histories
    cannot establish a plastic range and are rejected. Caller records provenance.
    """
    observed = _number('observed_max_peeq',observed_max_peeq)
    factor = _number('safety_factor',safety_factor,minimum=1.)
    step = _number('round_step',round_step)
    target = observed*factor
    if not math.isfinite(target/step):
        raise ValueError('Coverage proposal is outside numerical range')
    return math.ceil(target/step)*step
