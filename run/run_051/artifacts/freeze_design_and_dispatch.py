"""Test, freeze two material scenarios and hand off to the real CAE session."""
import sys,csv,json,hashlib,subprocess,math
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from highp_envelope import Envelope,plastic_block,table_fragment,VERSION
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_051';A=RUN/'artifacts';P=A/'private';F=R/'run/run_046/artifacts/private/freeze';sys.path.insert(0,str(R))
from inverse.hollomon import stress_from_total_strain
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(R).as_posix()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]),lineterminator='\n');w.writeheader();w.writerows(rs)

def main():
 test=subprocess.run([sys.executable,'-B',str(A/'test_envelope.py')],cwd=R,text=True,capture_output=True)
 save(P/'unit_test_run.json',{'at':now(),'command':[sys.executable,'-B',rel(A/'test_envelope.py')],'return_code':test.returncode,'stdout':test.stdout,'stderr':test.stderr,'tests':18,'source_sha256':sha(A/'test_envelope.py')})
 assert test.returncode==0 and 'Ran 18 tests' in test.stderr
 par=read(F/'D01_parameters.json');intent=read(A/'design_intent.json');assert intent['amplitude_a']==.5 and intent['transition_width_plastic_strain']==.05
 for f in read(F/'frozen_manifest.json')['files']:assert sha(R/f['path'])==f['sha256']
 source=R/par['source_inp'];assert sha(source)==par['source_inp_sha256'];raw=source.read_bytes();prefix,suffix,base,texts=plastic_block(raw)
 stress010=stress_from_total_strain(.1,par['sigma_y_mpa'],par['n']);switch=.1-stress010/par['E_pa'];width=.05
 helper=Envelope(base,switch);deployed_anchor=helper.baseline(switch)
 descriptor={'version':VERSION,'frozen_at':now(),'status':'FROZEN_BEFORE_ANY_CANDIDATE_SOLVE','design_intent_path':rel(A/'design_intent.json'),'design_intent_sha256':sha(A/'design_intent.json'),'reference_parameters_path':rel(F/'D01_parameters.json'),'reference_parameters_sha256':sha(F/'D01_parameters.json'),'source_inp':rel(source),'source_inp_sha256':sha(source),'implementation':rel(A/'highp_envelope.py'),'implementation_sha256':sha(A/'highp_envelope.py'),'p_switch':switch,'p_switch_total_strain':.1,'p_switch_D01_analytic_stress_pa':stress010,'p_switch_method':'frozen D01 Hollomon predicted sigma(.10); p=.10-sigma/E, not released tensile stress','deployed_anchor_stress_pa':deployed_anchor,'analytic_minus_deployed_anchor_pa':stress010-deployed_anchor,'anchor_note':'switch coordinate from analytic frozen D01; stress anchor from exact deployed table to preserve low-p FE baseline. Existing baseline interpolation discrepancy not corrected','E_pa':par['E_pa'],'nu':par['nu'],'low_branch_sigma_y_mpa':par['sigma_y_mpa'],'low_branch_n':par['n'],'amplitude_a':.5,'transition_width':width,'transition_end':switch+width,'curve_definition':intent['formula'],'ramp':intent['ramp'],'post_transition_hardening_ratios':[.5,1.5],'scope':'exploratory dimensionless hardening-rate perturbation, not new fitted Hollomon parameters or true material bounds','coverage':[0,.9],'baseline_knot_slope_jumps_retained':True,'new_modulation_join_stress_and_tangent_continuous':True,'linear_table_interpolation_relative_error_bound':1e-5,'solver_authorized':False,'enqueue_authorized':False,'points':[]}
 grids=np.unique(np.r_[np.linspace(0,.9,3001),[switch,switch+width]])
 figure,ax=plt.subplots(1,3,figsize=(15,4.6));baseline=np.array([helper.baseline(float(p)) for p in grids]);ax[0].plot(grids,baseline/1e6,'k',label='D01 deployed baseline');ax[1].plot(grids,np.zeros_like(grids),'k',label='D01');ax[2].plot(grids,np.ones_like(grids),'k',label='D01 ratio=1')
 sample_rows=[];validation=[]
 for pid,sign,job in [('H01',-1,'SPIO_R051_H01_LOW'),('H02',1,'SPIO_R051_H02_HIGH')]:
  model=Envelope(base,switch,amplitude=.5,width=width,sign=sign);table,bounds=model.sample(1e-5);arr=np.array(table)
  dense=np.unique(np.r_[grids,np.linspace(switch,switch+width,10001)]);exact=np.array([model.stress(float(p)) for p in dense]);linear=np.interp(dense,arr[:,1],arr[:,0]);relative=abs(linear-exact)/exact
  pdir=P/pid;pdir.mkdir();tablepath=pdir/'yield_stress_plastic_strain.csv';fragpath=pdir/'plastic_rows.inc'
  csvsave(tablepath,[{'yield_stress_pa':s,'equivalent_plastic_strain':p} for s,p in table]);fragment=table_fragment(table,texts,switch,newline=b'\r\n' if b'\r\n' in raw else b'\n')
  with fragpath.open('xb') as f:f.write(fragment)
  # Any split of the last original low segment must be collinear, not a re-fit.
  lowgrid=np.linspace(0,switch,10001);lowerr=float(max(abs(np.interp(lowgrid,arr[:,1],arr[:,0])-np.interp(lowgrid,[v[1] for v in base],[v[0] for v in base]))))
  record={'candidate_id':pid,'job_name':job,'sign':sign,'post_transition_hardening_multiplier':1+sign*.5,'table_path':rel(tablepath),'table_sha256':sha(tablepath),'plastic_rows_path':rel(fragpath),'plastic_rows_sha256':sha(fragpath),'table_rows':len(table),'rows_at_or_below_switch':int(np.sum(arr[:,1]<=switch)),'original_low_numeric_rows_preserved':sum(p<=switch for _,p in base),'max_certified_relative_interpolation_bound':max(b['relative_stress_bound'] for b in bounds),'max_dense_relative_interpolation_error':float(max(relative)),'max_low_deployed_interpolation_difference_pa':lowerr,'initial_yield_stress_pa':float(arr[0,0]),'coverage':[float(arr[0,1]),float(arr[-1,1])],'intended_inp_path':f'run/run_051/artifacts/candidates/{job}/{job}.inp','working_dir':f'run/run_051/artifacts/solver/{job}','expected_odb':f'run/run_051/artifacts/solver/{job}/{job}.odb'}
  assert record['max_certified_relative_interpolation_bound']<=1e-5 and record['max_dense_relative_interpolation_error']<=1e-5 and lowerr<1e-6
  assert arr[0,0]==base[0][0] and arr[-1,1]==base[-1][1]==.9 and np.all(np.diff(arr[:,0])>0)
  save(pdir/'interpolation_bounds.json',bounds);save(pdir/'table_validation.json',record);descriptor['points'].append(record);validation.append(record)
  for p in [switch,switch+width,.2,.3,.5,.6114587783813477,.9]:sample_rows.append({'candidate_id':pid,'plastic_strain':p,'D01_stress_MPa':model.baseline(p)/1e6,'scenario_stress_MPa':model.stress(p)/1e6,'stress_difference_MPa':(model.stress(p)-model.baseline(p))/1e6,'hardening_ratio':model.hardening(p)/model.slopes[model.index(p)]})
  values=np.array([model.stress(float(p)) for p in grids]);ratio=np.array([model.hardening(float(p))/model.slopes[model.index(p)] for p in grids]);ax[0].plot(grids,values/1e6,label=pid);ax[1].plot(grids,(values-baseline)/1e6,label=pid);ax[2].plot(grids,ratio,label=pid)
 ax[0].set(xlabel='Equivalent plastic strain p',ylabel='Yield stress (MPa)',title='Frozen D01 vs exploratory envelopes');ax[1].set(xlabel='p',ylabel='Stress difference vs D01 (MPa)',title='Low branch unchanged');ax[2].set(xlabel='p',ylabel='H_scenario / H_D01',title='Hardening-rate ratio; not stress ratio')
 for a in ax:a.axvline(switch,color='grey',ls='--',lw=.8);a.axvline(switch+width,color='grey',ls=':',lw=.8);a.grid(alpha=.2);a.legend(fontsize=8)
 figure.tight_layout();figure.savefig(P/'material_envelope_comparison.png',dpi=170);plt.close(figure)
 csvsave(P/'material_scenario_samples.csv',sample_rows);save(P/'material_validation_summary.json',{'tests_passed':18,'points':validation,'p_switch':switch,'deployed_anchor_stress_pa':deployed_anchor})
 save(A/'material_contract.json',descriptor)
 loss=read(R/'run/run_030/artifacts/loss_contract_binding.json');old=read(R/'run/run_027/artifacts/comparison_contract.json')
 for k in ['target','config','implementation']:assert sha(R/loss[k+'_path'])==loss[k+'_sha256']
 assert sha(R/old['comparison_implementation_path'])==old['comparison_implementation_sha256']
 original_result=read(R/'run/run_045/artifacts/private/odb/D01/result.json')
 protocol={'version':'run051-highp-hardening-sensitivity-comparison-v1','frozen_at':now(),'status':'FROZEN_BEFORE_SOLVE','baseline_job':par['source_odb'],'baseline_odb_sha256':par['source_odb_sha256'],'baseline_result_path':'run/run_045/artifacts/private/odb/D01/result.json','baseline_fd_path':original_result['positive_fd_csv'],'baseline_fd_sha256':sha(R/original_result['positive_fd_csv']),'baseline_SPT_loss':par['SPT_loss'],'material_contract_path':rel(A/'material_contract.json'),'material_contract_sha256':sha(A/'material_contract.json'),'loss_binding':loss,'comparison_implementation_path':old['comparison_implementation_path'],'comparison_implementation_sha256':old['comparison_implementation_sha256'],'FD_grid':'fixed experimental0–1.2mm,241points,linear interpolation,no extrapolation/shift/smoothing/deletion','FD_bands_mm':[[0,.3],[.3,.6],[.6,.9],[.9,1.2]],'metrics':['frozen Loss,RMSE_to_experiment,NRMSE','deltaFD_RMSE,max_abs_and_location,signed_bias,regularized_relative_with71.445N_floor','deltaLoss','maximum PEEQ and actual table coverage','direct ALLPD and reference/current IP-volume distributions','cumulative-region vs increment-by-strain energy with thresholds actual p_switch,.1,.3,.5','contact footprint/CPRESS/COPEN sentinel treatment,1.10–1.16mm raw accepted frame review','cutback,accepted/rejected warnings,solve wall-clock and allocated CPU cost'],
 'causal_scope':'only high-p material changes; significant response implies sensitivity to this continuation, not unique cause of experimental error','numerical_vs_sensitivity':'old refinement small-difference PASS thresholds are NOT acceptance thresholds on intentional material response changes','descriptive_effect_flags':{'FD_RMSE_over_N':2,'FD_max_over_N':7.1445,'use':'predeclared engineering effect flags, not statistical significance, physical accuracy, guaranteed numerical error bound or new model numerical PASS'},'baseline_observed_adjacent_increment_changes':{'rmse_N':.3383060028573848,'max_abs_N':1.8028578477856172,'deltaLoss':-4.1638053551687915e-6,'not_parameter_domain_error_bound':True},
 'eligibility':['Datacheck and Full actual complete identities and readable safe ODB','full fixed window coverage','max savedPEEQ within actual0-.9 table','no unexplained accepted-state strain/contact instability or substantial force recoil','local response changes must be compared with warnings,energy and contact history; outcome may remain inconclusive without further numerical qualification'],
 'failure_rule':'keep failed/unknown/unscoreable Loss=null,started attempt consumed,no auto retry or extra candidate','if_both_low_sensitivity':'only this +/-50% tangent and switch/width is screened; prioritize measured fixture-boundary uncertainty before more same-model parameter valley points, then orthogonal identification if justified','physical_bounds':'no claim that engineered upper/lower rates are confidence bounds','authorization':'no solver/datacheck/enqueue in run051'}
 save(A/'comparison_contract.json',protocol)
 session=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
 payload={'run_id':'run_051','task':'generate_exactly_two_frozen_highp_material_candidates','material_contract_path':rel(A/'material_contract.json'),'material_contract_sha256':sha(A/'material_contract.json'),'comparison_contract_path':rel(A/'comparison_contract.json'),'comparison_contract_sha256':sha(A/'comparison_contract.json'),'source_inp':rel(source),'source_inp_sha256':sha(source),'points':descriptor['points'],'output_subtree':'run/run_051/artifacts/private/cae','limits':['real CAE identity/session claims this task','replace numeric rows of sole Plastic block using frozen fragments only; every outside byte identical, including headings/comments/material name','unique actual job name from filename/API; leave historical job-name comment untouched to preserve source bytes','E210GPa,nu.3,geometry,mesh,BC,contact,friction,loading,all outputs and maximum increment.00125 unchanged','no original edits or overwrite; new directories only','public AbqJobPilot0.2.2 preflight/dry-run only;PERSISTED settings14CPU0GPU datacheck/full configured but never executed','no enqueue/Solver/datacheck/retry;no environment or infrastructure changes','do not read original/old leaked/released tensile numeric datasets; no new fit','do not modify MAIN/global Run files; own candidate directories and private/cae outputs only'], 'public_project_id':'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae','project_path':'agenthub_sp_invopt/abqjobpilot_project','resources':intent['future_numeric_controls'],'no_solver_authorized':True}
 task=hub.create_task(session['identity']['agent_id'],'CAE','prepare_frozen_highp_hardening_envelope_inps',payload,'run051-cae-two-candidates-v1');hub.approve(task['task_id'],session['identity']['agent_id'],'generate_inp');hub.approve(task['task_id'],session['identity']['agent_id'],'verify_inp')
 hub.message(task['task_id'],session['identity']['agent_id'],'CAE',{'payload_path':'run/run_051/artifacts/cae_task_payload.json','task_id':task['task_id'],'no_enqueue_or_solver':True},'run051-cae-dispatch-v1')
 save(A/'cae_task_payload.json',payload);save(P/'cae_task_identity.json',{'task_id':task['task_id'],'dispatch_time':now(),'expected_real_session':'SP-InvOpt CAE'})
 print(json.dumps({'cae_task_id':task['task_id'],'p_switch':switch,'analytic_D01_sigma_at_total0p1_MPa':stress010/1e6,'deployed_anchor_MPa':deployed_anchor/1e6,'points':[{'id':v['candidate_id'],'rows':v['table_rows'],'bound':v['max_certified_relative_interpolation_bound']} for v in validation],'tests_passed':18}))
if __name__=='__main__':main()
