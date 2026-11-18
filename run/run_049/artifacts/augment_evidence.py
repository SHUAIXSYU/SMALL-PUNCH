"""Additional bounded provenance and field-range diagnostics, retaining first analysis revision."""
from pathlib import Path
import json,csv,math,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_049/artifacts/private'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
a=read(P/'analysis.json');old=P/'revisions';old.mkdir(exist_ok=False);(old/'analysis_before_supplement.json').write_bytes((P/'analysis.json').read_bytes())
initial=read(R/'run/run_040/artifacts/private/initial_dataset.json');pilot=read(R/'run/run_042/artifacts/private/main/main_analysis.json')
invalid=[{'candidate_id':v['point_id'],'sigma_y_mpa':v['sigma_y_mpa'],'n':v['n'],'x':v['x'],'y':v['y'],'loss':None,'numerical_quality':v['numerical_quality'],'blockers':v['blocking_issues']} for v in initial['invalid']]
invalid +=[{'candidate_id':v['candidate_id'],'sigma_y_mpa':v['sigma_y_mpa'],'n':v['n'],'x':v['x'],'y':v['y'],'loss':None,'numerical_quality':v['quality'],'blockers':v['blocking_issues']} for v in pilot['rows'] if v['loss'] is None]
a['unscoreable_observations']=invalid
inp=R/a['boundary']['input_path'];lines=inp.read_text(encoding='utf8').splitlines();nodes={};elements={};mode=None;part=False
for line in lines:
 if line.lower().startswith('*part, name=part_specimen'):part=True
 if line.lower().startswith('*end part'):part=False
 if line.startswith('*'):
  mode='node' if part and line.lower()=='*node' else 'element' if part and line.lower().startswith('*element, type=cax') else None;continue
 if mode and line.strip():
  v=[x.strip() for x in line.split(',') if x.strip()]
  if mode=='node':nodes[int(v[0])]=[float(x) for x in v[1:]]
  else:elements[int(v[0])]=[int(x) for x in v[1:]]
location=[]
for scope in a['peeq_scope']:
 pid=scope['candidate_id'];rr=rows(R/'run/run_045/artifacts/private/odb'/pid/'peeq_saved_frames.csv')
 for label,v in [('first_saved_positive_frame',rr[1]),('first_above_conditional_tensile_limit',next(x for x in rr if float(x['max_peeq'])>a['conditional_tensile_uniform_plastic_limit'])),('maximum_saved',max(rr,key=lambda x:float(x['max_peeq'])))]:
  elem=int(v['element_label']);coords=[nodes[n] for n in elements[elem]]
  location.append({'candidate_id':pid,'event':label,'element_label':elem,'integration_point':int(v['integration_point']),'max_peeq':float(v['max_peeq']),'reference_node_coordinates_m':coords,'reference_radius_range_mm':[min(x[0] for x in coords)*1000,max(x[0] for x in coords)*1000],'reference_height_range_mm':[min(x[1] for x in coords)*1000,max(x[1] for x in coords)*1000]})
a['max_peeq_reference_locations']=location
a['iso_stress_tradeoff_formula']='ln(sigma)=(1-n)*ln(sigma_y)+n*ln(E*epsilon); dln(sigma_y)/dn=-ln(E*epsilon/sigma_y)/(1-n), plastic branch only; illustrative analytic equivalence, not SPT likelihood.'
a['future_proposed_mechanisms']={'constitutive':'plateau/large-plastic-strain hardening form is directly suspect; numerical demand beyond traceable uniform data needs spatial weighting before attribution','boundary':'actual nodal fixed annulus is not validated finite preload contact; effect sign/magnitude unknown; no fixture coefficients copied from literature'}
temp=P/'analysis.json.tmp';temp.write_text(json.dumps(a,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');assert read(temp)==a;temp.replace(P/'analysis.json')
(P/'numerically_unscoreable_observations.json').write_text(json.dumps(invalid,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
# Separate observed null locations from valid Loss values; no fabricated penalty.
data=rows(P/'evaluated_24_points.csv');fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
for aa in ax:
 sc=aa.scatter([float(r['x']) for r in data],[float(r['y']) for r in data],c=np.log10([float(r['loss']) for r in data]),s=55,cmap='viridis',edgecolors='black')
 aa.scatter([r['x'] for r in invalid],[r['y'] for r in invalid],marker='x',c='gray',s=65,label='Not scoreable: no numeric penalty')
 aa.set(xlabel='log-normalized sigma_y (x)',ylabel='normalized n (y)');aa.grid(alpha=.15)
ax[0].set(title='30 distinct parameter locations: 24 scoreable',xlim=(-.02,1.02),ylim=(-.02,1.02));ax[0].legend(fontsize=8)
low=[r for r in data if float(r['loss'])<=.01]
for r in low:ax[1].annotate(r['candidate_id'],(float(r['x']),float(r['y'])),xytext=(4,4),textcoords='offset points',fontsize=8)
for p in a['future_parameter_design']['points']:ax[1].scatter(p['x'],p['y'],marker='+',c='red',s=75)
ax[1].set(title='Local view; red + = proposed, uncomputed',xlim=(-.03,.54),ylim=(.10,.54))
fig.colorbar(sc,ax=ax,label='log10(actual common-contract Loss)');fig.savefig(P/'parameter_coverage_with_nulls.png',dpi=170);plt.close(fig)
print(json.dumps({'unscoreable':len(invalid),'max_reference_locations':[v for v in location if v['event']=='maximum_saved']}))
