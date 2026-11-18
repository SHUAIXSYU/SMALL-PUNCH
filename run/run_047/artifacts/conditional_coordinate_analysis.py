"""Descriptive coordinate comparison only; no formal tensile validation gates asserted."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT/'run/run_046/artifacts/private/freeze'
PRIV = ROOT/'run/run_047/artifacts/private'
raw = json.loads((PRIV/'origin_extract.json').read_text(encoding='utf-8'))
sheet = raw['workbooks'][0]['sheets'][0]
x = np.asarray(sheet['data_columns'][0], dtype=float)
y = np.asarray(sheet['data_columns'][1], dtype=float)
grid = np.loadtxt(FREEZE/'validation_primary_grid.csv', delimiter=',', skiprows=1, usecols=0)
pred = {}
for cid in ('D01','I08'):
    with (FREEZE/f'{cid}_true_total_curve.csv').open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    px=np.array([float(z['true_total_strain']) for z in rows])
    py=np.array([float(z['true_stress_pa'])/1e6 for z in rows])
    pred[cid]={'x':px,'y':py,'grid':np.interp(grid,px,py)}

def metrics(g,obs,calc):
    r=calc-obs
    rel=np.abs(r)/np.maximum(np.abs(obs),50)
    rawmask=np.abs(obs)>=50
    return {'points':int(len(g)), 'rmse_coordinate_mpa_if_assumptions':float(np.sqrt(np.mean(r*r))),
            'mae_coordinate_mpa_if_assumptions':float(np.mean(np.abs(r))),
            'signed_bias_coordinate_mpa_if_assumptions':float(np.mean(r)),
            'max_abs_coordinate_mpa_if_assumptions':float(np.max(np.abs(r))),
            'max_abs_at_x':float(g[np.argmax(np.abs(r))]),
            'mean_regularized_relative_coordinate_error':float(np.mean(rel)),
            'max_regularized_relative_coordinate_error':float(np.max(rel)),
            'unregularized_relative_count':int(np.sum(rawmask)),
            'mean_unregularized_relative_error':float(np.mean(np.abs(r[rawmask])/np.abs(obs[rawmask]))) if rawmask.any() else None,
            'normalized_mse_if_assumptions':float(np.mean((r/500)**2))}

checks={'finite':bool(np.isfinite(x).all() and np.isfinite(y).all()),
        'x_strictly_increasing':bool(np.all(np.diff(x)>0)),
        'y_non_decreasing':bool(np.all(np.diff(y)>=0)),
        'x_min':float(x.min()),'x_max':float(x.max()),
        'y_min':float(y.min()),'y_max':float(y.max()),
        'first_n_exact_E210':int(np.sum(np.isclose(y[:20],210000*x[:20],rtol=1e-10,atol=1e-9))),
        'first_10_y':y[:10].tolist(),
        'first_10_x':x[:10].tolist(),
        'last_point_is_max_y':bool(np.argmax(y)==len(y)-1)}
result={'observed_at':datetime.now().astimezone().isoformat(),
        'status':'CONDITIONAL_COORDINATE_COMPARISON_ONLY',
        'five_statuses':{'FREEZE_INTEGRITY':'PASS',
                         'TENSILE_DATA_READABILITY':'PASS_PRESENT_OPJU_NUMERIC_CONTENT',
                         'MATERIAL_COMPARABILITY':'UNRESOLVED',
                         'MAIN_VALIDATION_SCORE':'NOT_EVALUABLE',
                         'INDEPENDENT_VALIDATION':'NOT_ESTABLISHED'},
        'formal_main_score':None,
        'formal_primary':{'D01':{'rmse_mpa':None,'reason':'qualification gates unresolved'},
                          'I08':{'rmse_mpa':None,'reason':'qualification gates unresolved'},
                          'rank':None},
        'formal_bands':None,
        'replicate_evidence':{'numeric_traces_in_project':1,'confirmed_distinct_specimens':None},
        'reason':'Column meaning, stress unit, specimen provenance/state, and uniform pre-necking range unverified',
        'assumptions_for_coordinate_arithmetic':['Origin graph X label TRUE STRAIN is true total logarithmic strain',
           'Origin graph Y label TRUE STRESS values are MPa','same material state as SPT','0.002–0.10 is uniform pre-necking'],
        'these_assumptions_are_not_verified':True,
        'experimental_numeric_checks':checks,
        'observed_coordinate_values':{str(q):float(np.interp(q,x,y)) for q in (.002,.005,.01,.02,.05,.10)},
        'observed_coordinate_secants':{f'{a:.3f}-{b:.3f}':float((np.interp(b,x,y)-np.interp(a,x,y))/(b-a))
                                        for a,b in ((.005,.01),(.01,.02),(.02,.05),(.05,.10))},
        'primary_grid_sha256':hashlib.sha256((FREEZE/'validation_primary_grid.csv').read_bytes()).hexdigest(),
        'coordinate_window':{'x_start':float(grid[0]),'x_end':float(grid[-1]),'points':len(grid)},
        'conditional_primary':{},'conditional_bands':{}}
if checks['finite'] and checks['x_strictly_increasing'] and x[0]<=grid[0] and x[-1]>=grid[-1]:
    obs=np.interp(grid,x,y)
    for cid in pred:
        result['conditional_primary'][cid]=metrics(grid,obs,pred[cid]['grid'])
    result['conditional_rank_if_all_assumptions']='I08_FIRST'
    result['conditional_rank_vs_frozen_SPT']='DISCORDANT_IF_ALL_ASSUMPTIONS; SPT D01_FIRST'
    for a,b in ((0,.002),(.002,.01),(.01,.02),(.02,.05),(.05,.10),(.10,.20)):
        name=f'{a:.3f}-{b:.3f}'
        if x[0]>a or x[-1]<b:
            result['conditional_bands'][name]={'status':'INCOMPLETE_COORDINATE_COVERAGE','metrics':None}
            continue
        g=np.arange(round(a*10000),round(b*10000)+1)/10000
        o=np.interp(g,x,y)
        result['conditional_bands'][name]={cid:metrics(g,o,np.interp(g,pred[cid]['x'],pred[cid]['y'])) for cid in pred}

out=PRIV/'validation_metrics.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
with (PRIV/'tensile_validation_results.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['true_total_strain_assumed','Origin_B_assumed_MPa','D01_frozen_MPa','I08_frozen_MPa',
                'D01_minus_Origin_conditional_MPa','I08_minus_Origin_conditional_MPa','status'])
    for i,g in enumerate(grid):
        w.writerow([format(g,'.17g'),format(obs[i],'.17g'),format(pred['D01']['grid'][i],'.17g'),
                    format(pred['I08']['grid'][i],'.17g'),format(pred['D01']['grid'][i]-obs[i],'.17g'),
                    format(pred['I08']['grid'][i]-obs[i],'.17g'),'CONDITIONAL_NOT_FORMAL_SCORE'])

fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
xx=np.linspace(0,.125,1000)
axs[0,0].plot(x,y,'k.',markersize=2,label='Origin A/B (unit/definition unverified)')
for cid,color in (('D01','#1664a4'),('I08','#c24c34')):
    axs[0,0].plot(xx,np.interp(xx,pred[cid]['x'],pred[cid]['y']),color=color,label=f'{cid} frozen prediction')
axs[0,0].axvspan(.002,.10,color='gold',alpha=.15,label='preregistered primary window')
axs[0,0].set(xlabel='X coordinate / assumed true total strain',ylabel='Y coordinate / assumed MPa',title='Conditional overlay: definitions and material state unverified')
axs[0,0].legend(fontsize=8)
for cid,color in (('D01','#1664a4'),('I08','#c24c34')):
    axs[0,1].plot(grid,pred[cid]['grid']-obs,color=color,label=f'{cid} minus Origin B')
axs[0,1].axhline(0,color='gray',lw=.7)
axs[0,1].set(xlabel='Assumed true total strain',ylabel='Conditional coordinate residual / MPa',title='Residuals only if graph labels/MPa are valid')
axs[0,1].legend()
axs[1,0].plot(grid,pred['I08']['grid']-pred['D01']['grid'],color='#6d3999')
axs[1,0].set(xlabel='True total strain',ylabel='I08 − D01 / MPa',title='Frozen prediction difference')
axs[1,1].axvspan(x.min(),x.max(),color='gray',alpha=.35,label='Origin coordinate extent; uniformity unknown')
axs[1,1].axvspan(.002,.10,color='gold',alpha=.45,label='preregistered primary window')
axs[1,1].set(xlim=(0,.2),ylim=(0,1),xlabel='X coordinate / assumed true total strain',yticks=[],title='Coordinate coverage does not establish necking coverage')
axs[1,1].legend(fontsize=8)
fig.suptitle('SP-InvOpt run047 — descriptive, NOT_EVALUABLE as independent validation',fontsize=14)
fig.savefig(PRIV/'constitutive_validation_comparison.png',dpi=160)
print(out)
