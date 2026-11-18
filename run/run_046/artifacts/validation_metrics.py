"""Pure frozen tensile-validation scoring. No file, model fitting, or solver access."""
import math
import numpy as np

class ValidationUnavailable(ValueError):pass

def checked_curve(strain,stress,*,strain_definition='true_log_total',stress_unit='Pa'):
    if strain_definition!='true_log_total' or stress_unit!='Pa':raise ValidationUnavailable('Explicit logarithmic true-total strain and true stress Pa required')
    x=np.asarray(strain,dtype=float);y=np.asarray(stress,dtype=float)
    if x.ndim!=1 or y.ndim!=1 or len(x)!=len(y) or len(x)<2:raise ValidationUnavailable('Paired one-dimensional data required')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not (np.diff(x)>0).all():raise ValidationUnavailable('Finite strictly increasing strain required; no auto sorting/deletion')
    return x,y

def score(predicted_strain,predicted_stress,experimental_strain,experimental_stress,grid,*,uniform_limit_true,
          definitions_confirmed,material_state_matched,pre_necking_confirmed,stress_reference_pa=500e6,relative_floor_pa=50e6,
          strain_definition='true_log_total',stress_unit='Pa'):
    if not all(v is True for v in [definitions_confirmed,material_state_matched,pre_necking_confirmed]):raise ValidationUnavailable('Qualification gates unresolved; diagnostic comparison only, no formal validation rank')
    x,p=checked_curve(predicted_strain,predicted_stress,strain_definition=strain_definition,stress_unit=stress_unit)
    u,e=checked_curve(experimental_strain,experimental_stress,strain_definition=strain_definition,stress_unit=stress_unit)
    g=np.asarray(grid,dtype=float)
    if g.ndim!=1 or len(g)<2 or not np.isfinite(g).all() or not (np.diff(g)>0).all():raise ValidationUnavailable('Fixed valid grid required')
    if not math.isfinite(uniform_limit_true) or g[-1]>uniform_limit_true or g[0]<max(x[0],u[0]) or g[-1]>min(x[-1],u[-1]):raise ValidationUnavailable('Incomplete pre-necking coverage; no extrapolation or automatic shorter primary window')
    if not math.isfinite(stress_reference_pa) or stress_reference_pa<=0 or not math.isfinite(relative_floor_pa) or relative_floor_pa<=0:raise ValidationUnavailable('Positive fixed scales required')
    prediction=np.interp(g,x,p);measurement=np.interp(g,u,e);r=prediction-measurement
    relative=np.abs(r)/np.maximum(np.abs(measurement),relative_floor_pa)
    return {'points':len(g),'rmse_mpa':float(np.sqrt(np.mean(r*r))/1e6),'mae_mpa':float(np.mean(abs(r))/1e6),
            'bias_mpa':float(np.mean(r)/1e6),'max_absolute_error_mpa':float(max(abs(r))/1e6),
            'max_absolute_error_at_true_strain':float(g[np.argmax(abs(r))]),
            'mean_regularized_relative_error':float(np.mean(relative)),'max_regularized_relative_error':float(max(relative)),
            'normalized_mse':float(np.mean((r/stress_reference_pa)**2)),'stress_reference_pa':stress_reference_pa,'relative_floor_pa':relative_floor_pa,
            'rank_metric':'rmse_mpa; equivalent fixed-scale normalized_mse','physical_tolerance_pass':None}
