"""Fresh fixed-grid calculation with explicit qualification gates; no fitting."""
import csv
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_048'
PRIVATE=RUN/'artifacts/private'
FREEZE=ROOT/'run/run_046/artifacts/private/freeze'
SOURCE=ROOT/'run/run_047/artifacts/private/origin_extract.json'
OLD=ROOT/'run/run_047/artifacts/private/validation_metrics.json'
integrity=json.loads((PRIVATE/'input_integrity.json').read_text(encoding='utf-8'))
assert integrity['status']=='PASS'
protocol=json.loads((FREEZE/'independent_validation_protocol.json').read_text(encoding='utf-8'))
assert protocol['version']=='run046-independent-tensile-validation-v1'
confirmation=PRIVATE/'collaborator_confirmation.json'
confirmation_hash=hashlib.sha256(confirmation.read_bytes()).hexdigest()

with (FREEZE/'validation_primary_grid.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==981
assert hashlib.sha256((FREEZE/'validation_primary_grid.csv').read_bytes()).hexdigest()==protocol['sampling']['primary_grid_sha256']
grid=np.array([float(row[next(iter(row))]) for row in rows])
assert abs(grid[0]-.002)<1e-14 and abs(grid[-1]-.1)<1e-14 and np.max(abs(np.diff(grid)-.0001))<1e-12

origin=json.loads(SOURCE.read_text(encoding='utf-8'))
sheet=origin['workbooks'][0]['sheets'][0]
x=np.asarray(sheet['data_columns'][0],dtype=float)
y_mpa=np.asarray(sheet['data_columns'][1],dtype=float)
assert len(x)==len(y_mpa)==355 and np.isfinite(x).all() and np.isfinite(y_mpa).all()
assert (np.diff(x)>0).all() and x[0]<=grid[0] and x[-1]>=grid[-1]

candidate={}
for cid in ('D01','I08'):
    path=FREEZE/f'{cid}_true_total_curve.csv'
    with path.open(newline='',encoding='utf-8') as f:
        rr=list(csv.DictReader(f))
    xx=np.array([float(r['true_total_strain']) for r in rr])
    yy=np.array([float(r['true_stress_pa'])/1e6 for r in rr])
    pp=np.array([float(r['abaqus_piecewise_true_stress_pa'])/1e6 for r in rr])
    assert len(xx)==10803 and (np.diff(xx)>0).all()
    candidate[cid]={'x':xx,'analytic_mpa':yy,'piecewise_mpa':pp,
                    'analytic_grid':np.interp(grid,xx,yy),
                    'piecewise_grid':np.interp(grid,xx,pp)}

qualifications={
  'explicit_unblind_authorization':{'status':'PASS','basis':'current user request authorizes readonly original tensile source'},
  'freeze_and_source_identity':{'status':'PASS','basis':'48/48 hash, CRC, path, source and extraction checks'},
  'specimen_identity_replicates':{'status':'UNRESOLVED','basis':'one project trace; no specimen identifier or replicate count'},
  'stress_unit':{'status':'SOURCE_CONFIRMED','basis':'collaborator reply says MPa'},
  'true_stress_from_engineering':{'status':'SOURCE_CONFIRMED','basis':'collaborator reply states engineering-to-true conversion'},
  'log_true_total_strain_formula':{'status':'UNRESOLVED','basis':'no explicit ln(1+e_eng), total/plastic distinction, source engineering columns or conversion implementation'},
  'gauge_and_processing':{'status':'UNRESOLVED','basis':'A0/L0, strain gauge location, calibration, zero/compliance and processing records absent'},
  'same_batch':{'status':'SOURCE_CONFIRMED','basis':'collaborator says tensile and SPT used same SA508 batch'},
  'heat_treatment_state_direction_temp_rate':{'status':'UNRESOLVED','basis':'no cross-test correspondence for treatment/state/direction/temperature/strain rate'},
  'uniform_through_0p10':{'status':'SOURCE_CONFIRMED','basis':'collaborator says true strain <=0.10 uniform; fracture near 0.12'},
  'independent_necking_measurement':{'status':'UNRESOLVED','basis':'no force maximum/local area/image record; source claim only'},
  'numeric_coordinate_coverage':{'status':'PASS','basis':'stored x covers fixed 0.002–0.10 grid without extrapolation'}
}
formal_definitions_confirmed=False
formal_material_state_matched=False
formal_pre_necking_confirmed=True # source-party uniformity statement, not independent instrument proof
spec=importlib.util.spec_from_file_location('frozen_validation',FREEZE/'validation_metrics_frozen.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
formal_gate_result=None
try:
    module.score(candidate['D01']['x'],candidate['D01']['analytic_mpa']*1e6,
                 x,y_mpa*1e6,grid,uniform_limit_true=.10,
                 definitions_confirmed=formal_definitions_confirmed,
                 material_state_matched=formal_material_state_matched,
                 pre_necking_confirmed=formal_pre_necking_confirmed)
    raise AssertionError('Frozen formal gate unexpectedly accepted unresolved evidence')
except module.ValidationUnavailable as exc:
    formal_gate_result=str(exc)

def metrics(g,observed,predicted):
    r=predicted-observed
    absr=np.abs(r)
    regularized=absr/np.maximum(abs(observed),50.0)
    rawmask=abs(observed)>=50.0
    return {'points':int(len(g)),
            'RMSE_MPa':float(np.sqrt(np.mean(r*r))),
            'MAE_MPa':float(np.mean(absr)),
            'signed_bias_MPa':float(np.mean(r)),
            'max_absolute_error_MPa':float(max(absr)),
            'max_absolute_error_at_true_strain_assumed':float(g[np.argmax(absr)]),
            'mean_regularized_relative_error':float(np.mean(regularized)),
            'max_regularized_relative_error':float(max(regularized)),
            'unregularized_relative_count':int(np.sum(rawmask)),
            'mean_unregularized_relative_error':float(np.mean(absr[rawmask]/abs(observed[rawmask]))) if rawmask.any() else None,
            'normalized_mse_at_500MPa':float(np.mean((r/500.0)**2))}

observed=np.interp(grid,x,y_mpa)
restricted={cid:metrics(grid,observed,candidate[cid]['analytic_grid']) for cid in candidate}
secondary={cid:metrics(grid,observed,candidate[cid]['piecewise_grid']) for cid in candidate}
bands=[]
for lo,hi in protocol['sampling']['fixed_bands_true_total']:
    if x[0]>lo or x[-1]<hi:
        bands.append({'start':lo,'end':hi,'status':'INCOMPLETE_COORDINATE_COVERAGE','D01':None,'I08':None})
        continue
    g=np.arange(round(lo*10000),round(hi*10000)+1)/10000
    obs=np.interp(g,x,y_mpa)
    bands.append({'start':lo,'end':hi,'status':'SOURCE_CONFIRMED_RESTRICTED_NUMERIC',
                  **{cid:metrics(g,obs,np.interp(g,candidate[cid]['x'],candidate[cid]['analytic_mpa'])) for cid in candidate}})

landmarks={str(z):{'origin_mpa':float(np.interp(z,x,y_mpa)),
                    'D01_mpa':float(np.interp(z,candidate['D01']['x'],candidate['D01']['analytic_mpa'])),
                    'I08_mpa':float(np.interp(z,candidate['I08']['x'],candidate['I08']['analytic_mpa']))}
           for z in (.002,.005,.01,.02,.05,.10)}
old=json.loads(OLD.read_text(encoding='utf-8'))
old_repro={cid:abs(restricted[cid]['RMSE_MPa']-old['conditional_primary'][cid]['rmse_coordinate_mpa_if_assumptions']) for cid in candidate}
assert max(old_repro.values())<1e-9

result={'observed_at':datetime.now().astimezone().isoformat(),
        'version':'run048-source-confirmation-reassessment-v1',
        'integrity_status':'PASS',
        'collaborator_confirmation_sha256':confirmation_hash,
        'evidence_level':'SOURCE_CONFIRMED_USER_RELAYED; NOT independent instrument verification',
        'formal_main_status':'NOT_EVALUABLE',
        'formal_score':{'D01':None,'I08':None,'rank':None,'bands':None,'physical_accuracy_PASS':None},
        'frozen_score_gate_rejection':formal_gate_result,
        'qualification_gates':qualifications,
        'restricted_numeric_scope':'Assumes A is log true total strain and cross-test material state/direction/rate correspondence; stress MPa, engineering-to-true origin, same batch and <=0.10 uniformity are source-party confirmed',
        'restricted_primary':restricted,'restricted_piecewise_secondary':secondary,
        'restricted_rank':'I08_FIRST','frozen_SPT_rank':'D01_FIRST',
        'restricted_rank_vs_SPT':'DISCORDANT_NUMERIC_RANK_WITH_UNRESOLVED_FORMAL_GATES',
        'pre_registered_bands':bands,'landmarks':landmarks,
        'run047_conditional_RMSE_reproduction_abs_difference_MPa':old_repro,
        'yield_plateau':{'source_confirmed_present':True,
                         'exact_boundaries':None,
                         'diagnostic':'use frozen 0.002–0.01 and subsequent fixed bands; no plateau point deletion or score discount'},
        'no_physical_acceptance_threshold':True}
(PRIVATE/'reassessment_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

with (PRIVATE/'restricted_pointwise_comparison.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['assumed_log_true_total_strain','source_Origin_stress_MPa','D01_frozen_analytic_MPa','I08_frozen_analytic_MPa',
                'D01_minus_source_MPa','I08_minus_source_MPa','qualification'])
    for i,g in enumerate(grid):
        w.writerow([format(g,'.17g'),format(observed[i],'.17g'),
                    format(candidate['D01']['analytic_grid'][i],'.17g'),format(candidate['I08']['analytic_grid'][i],'.17g'),
                    format(candidate['D01']['analytic_grid'][i]-observed[i],'.17g'),
                    format(candidate['I08']['analytic_grid'][i]-observed[i],'.17g'),
                    'SOURCE_CONFIRMED_RESTRICTED_NUMERIC_NOT_FORMAL'])
with (PRIVATE/'fixed_band_metrics.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['start','end','candidate','points','RMSE_MPa','MAE_MPa','bias_MPa','max_abs_MPa','mean_regularized_relative','status'])
    for b in bands:
        for cid in ('D01','I08'):
            m=b[cid]
            w.writerow([b['start'],b['end'],cid,m['points'] if m else '',m['RMSE_MPa'] if m else '',
                        m['MAE_MPa'] if m else '',m['signed_bias_MPa'] if m else '',
                        m['max_absolute_error_MPa'] if m else '',m['mean_regularized_relative_error'] if m else '',b['status']])

fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
xx=np.linspace(0,.125,1200)
axs[0,0].plot(x,y_mpa,'k.',ms=2.2,label='Origin source coordinates (MPa confirmed)')
for cid,color in (('D01','#1664a4'),('I08','#c24c34')):
    axs[0,0].plot(xx,np.interp(xx,candidate[cid]['x'],candidate[cid]['analytic_mpa']),color=color,label=f'{cid} frozen')
axs[0,0].axvspan(.002,.10,color='gold',alpha=.12)
axs[0,0].set(xlabel='Assumed log true total strain',ylabel='Stress / MPa',title='Source-confirmed restricted overlay; formal gates unresolved')
axs[0,0].legend(fontsize=8)
for cid,color in (('D01','#1664a4'),('I08','#c24c34')):
    axs[0,1].plot(grid,candidate[cid]['analytic_grid']-observed,color=color,label=cid)
axs[0,1].axhline(0,color='gray',lw=.8)
axs[0,1].set(xlabel='Assumed log true total strain',ylabel='Prediction minus source / MPa',title='Fixed 0.002–0.10 residuals, no score discount')
axs[0,1].legend()
valid_bands=[b for b in bands if b['D01'] is not None and b['start']>=.002]
loc=np.arange(len(valid_bands))
axs[1,0].bar(loc-.19,[b['D01']['RMSE_MPa'] for b in valid_bands],width=.38,color='#1664a4',label='D01')
axs[1,0].bar(loc+.19,[b['I08']['RMSE_MPa'] for b in valid_bands],width=.38,color='#c24c34',label='I08')
axs[1,0].set_xticks(loc,[f"{b['start']:.3f}–{b['end']:.3f}" for b in valid_bands],rotation=20)
axs[1,0].set(ylabel='Restricted RMSE / MPa',title='Pre-registered bands; first band includes yield plateau')
axs[1,0].legend()
axs[1,1].plot(grid,candidate['I08']['analytic_grid']-candidate['D01']['analytic_grid'],color='#6d3999')
axs[1,1].set(xlabel='True total strain (candidate definition)',ylabel='I08 − D01 / MPa',title='Frozen candidate separation')
fig.suptitle('run048: source-confirmed restricted numerical comparison — formal NOT_EVALUABLE',fontsize=14)
fig.savefig(PRIVATE/'reassessment_comparison.png',dpi=160)
print('NOT_EVALUABLE',restricted['D01']['RMSE_MPa'],restricted['I08']['RMSE_MPa'])
