"""Initialize authorized offline envelope preparation, not solver execution."""
import sys,json,hashlib,subprocess
from pathlib import Path
from datetime import datetime
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_051';P=RUN/'artifacts/private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
start={'at':now(),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short'),'python':sys.executable}
save(RUN/'checkpoints/start.json',start)
paths=['run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip','run/run_046/artifacts/private/freeze/frozen_manifest.json','run/run_048/artifacts/private/independent_reassessment_report.md','run/run_050/artifacts/private/scientific_report.md','inverse/hollomon.py','run/run_043/artifacts/candidates/SPIO_R043_V_D01_M00125/SPIO_R043_V_D01_M00125.inp']
save(P/'protected_before.json',{p:sha(R/p) for p in paths})
h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=h.register('MAIN','codex-main-run051-hardening-envelope')
t=h.create_task(identity['agent_id'],'MAIN','offline_high_strain_hardening_envelope_preparation',{'run':'run_051','scope':'verify energy attribution; freeze exploratory D01 high-p tangent envelopes; tests then real CAE two-INP preparation; official preflight/dry-run only','solver_authorized':False,'enqueue_authorized':False,'no_tensile_based_fit':True},'run051-main-v1');lease=h.claim(t['task_id'],identity,'run051-main-claim-v1')
save(P/'hub_session.json',{'identity':identity,'main_task_id':t['task_id'],'lease':lease})
save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_051','stage':'Exploratory high-strain hardening envelope preparation','objective':'D01 low-strain-preserving H01/H02, energy-basis audit, material tests, real CAE preparation and public preflight/dry-run','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['branch'],'git_head':start['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
# Design intent is fixed before producing curves or seeing any new FE response.
intent={'version':'run051-exploratory-hardening-intent-v1','at':now(),'reference':'exact deployed D01 piecewise-linear stress-plastic table, not a regenerated analytic low-strain table','p_switch':'0.10 - frozen analytic D01 sigma(true_total=0.10)/E; never use measured tensile stress or run050 illustrative experimental marker','amplitude_a':0.5,'settled_hardening_multipliers':{'H01':0.5,'H02':1.5},'transition_width_plastic_strain':0.05,'ramp':'S(t)=6t^5-15t^4+10t^3 clipped to0/1 outside t in[0,1]','formula':'sigma_H(p)=sigma_D01_deployed(p) +/- a*integral_p_switch^p S((q-p_switch)/width)*H_D01_deployed(q)dq; unchanged for p<=p_switch','selection_basis':'predeclared symmetric +/-50% hardening-rate scenario: positive minimum tangent; 3:1 separation of settled rates; gradual0.05 transition. Engineering sensitivity amplitude, NOT inferred from tensile or a physical confidence envelope','interpolation_relative_error_bound':1e-5,'coverage':[0,0.9],'low_rows':'preserve original INP material-row text below switch; only add a mathematically collinear switch row if needed','continuity_scope':'new modulation joins with equal tangent at switch; baseline piecewise-table slope jumps remain; Abaqus table remains piecewise linear','future_numeric_controls':{'initial_increment':.001,'maximum_increment':.00125,'minimum_increment':1e-12,'step_time':1,'maximum_increments':999999,'cpus':14,'gpus':0},'authorization':'prepare up to2 INP only;0 solver/datacheck/queue'}
save(RUN/'artifacts/design_intent.json',intent)
energy=[]
for pid in ['D01','I08']:
 folder=R/f'run/run_050/artifacts/private/odb/{pid}';v1=read(folder/'energy_estimate.json');v2=read(folder/'energy_strain_stage_v2.json');last1=v1['stages'][-1];last2=v2['stages'][-1]
 assert sha(folder/'energy_estimate.json')==v2['source_v1_sha256']
 assert abs(sum(last2['strain_interval_cumulative_work_j'].values())-last2['sum_intervals_j'])<1e-12
 energy.append({'candidate_id':pid,'post_threshold_incremental_work_fraction_gt_p0p1':1-last2['fraction_by_strain_interval']['p_0_to_0p1'],'terminal_high_peeq_region_all_prior_work_fraction_gt_p0p1':last1['terminal_peeq_region_attribution']['0.1']['fraction_of_reconstructed_total'],'source_v1_sha256':sha(folder/'energy_estimate.json'),'source_v2_sha256':sha(folder/'energy_strain_stage_v2.json'),'saved_frame_count':v1['saved_frame_count'],'reference_volume_estimate_relative_difference_to_direct_ALLPD':last2['relative_difference_to_ALLPD']})
save(P/'energy_basis_audit.json',{'records':energy,'answer':'70.98%/69.26% are v2 incremental work after p>.1, NOT terminal-region classification; v1 terminal-region values are95.84%/94.93%','sufficient_existing_fields':'S.Mises and PEEQ at all CAX4 integration points in805/802 saved frames; quadrature reference weights, direct ALLPD history','source_script':'run/run_050/artifacts/private/odb/estimate_energy_stage.py','source_script_sha256':sha(R/'run/run_050/artifacts/private/odb/estimate_energy_stage.py'),'limitations':['saved-frame linear stress-versus-PEEQ approximation','reference-volume weighting; not direct local plastic-dissipation output','neither fraction is Punch RF2 share','p>.1 is not the new exact p_switch; do not relabel it as post-switch work']})
print(json.dumps({'run':'run_051','main_task_id':t['task_id'],'energy':energy},ensure_ascii=False))
