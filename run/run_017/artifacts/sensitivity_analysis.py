"""Pure offline five-curve analysis; imports no solver, queue, or optimizer."""
import math
import numpy as np


def analyze_five_curves(force_by_point, force_reference_n, h=.2):
    """All vectors MUST be on the same frozen grid, in N, already quality-gated.

    Inputs P01=center, P02=x-, P03=x+, P04=y-, P05=y+.
    SVD uses J/sqrt(number of samples), so singular values have RMS scaling.
    No point selection or experimental zero adjustment is performed.
    """
    expected = {'P01','P02','P03','P04','P05'}
    if set(force_by_point) != expected:
        raise ValueError('Exactly the five complete point identities are required')
    if not math.isfinite(force_reference_n) or force_reference_n <= 0 or not math.isfinite(h) or h <= 0:
        raise ValueError('Finite positive force reference and perturbation required')
    data = {k:np.asarray(v,dtype=float) for k,v in force_by_point.items()}
    shape = data['P01'].shape
    if len(shape) != 1 or shape[0] < 2 or any(v.shape != shape or not np.isfinite(v).all() for v in data.values()):
        raise ValueError('Paired finite vectors on one fixed grid required')
    a = (data['P03']-data['P02'])/(2*h*force_reference_n)
    b = (data['P05']-data['P04'])/(2*h*force_reference_n)
    jac = np.column_stack((a,b))
    singular = np.linalg.svd(jac/math.sqrt(shape[0]),compute_uv=False)
    threshold = max(jac.shape)*np.finfo(float).eps*singular[0]
    rank = int(np.sum(singular>threshold)) if singular[0] else 0
    condition = float(singular[0]/singular[1]) if rank == 2 else None
    norms = [float(np.linalg.norm(a)),float(np.linalg.norm(b))]
    cosine = float(np.dot(a,b)/(norms[0]*norms[1])) if all(norms) else None
    cosine = max(-1.,min(1.,cosine)) if cosine is not None else None
    def rms(x):return float(np.sqrt(np.mean(x*x)))
    return dict(status='LOCAL_FINITE_DIFFERENCE_DIAGNOSTIC_ONLY',
                normalized_jacobian=jac.tolist(),
                rms_sensitivity_x=rms(a),rms_sensitivity_y=rms(b),
                correlation_definition='uncentered cosine of sensitivity vectors; not Pearson correlation',
                sensitivity_cosine=cosine,singular_values=singular.tolist(),numerical_rank=rank,
                condition_number=condition,condition_number_null_reason=None if rank==2 else 'rank deficient',
                curvature_rms_x=rms((data['P03']+data['P02']-2*data['P01'])/(h*h*force_reference_n)),
                curvature_rms_y=rms((data['P05']+data['P04']-2*data['P01'])/(h*h*force_reference_n)),
                weak_identifiability_flag=(rank<2 or condition>100 or (cosine is not None and abs(cosine)>.95)),
                statistical_confidence_interval=None,global_uniqueness_proven=False,
                note='h=0.2 is a finite secant interval; curvature, FE noise and model bias limit differential interpretation')
