"""Bounded frozen-source and real-response audit. No Abaqus or queue interface."""
from common63 import *
import numpy as np,scipy,matplotlib
sys.path.insert(0,str(R/'run/run_055/artifacts'))
from feature_core import extract,FIXED2,FIXED5,NAMES,physical_to_normalized
from agenthub_sp_invopt.hub import Hub

def main():
 assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
 start={'at':now(),'python':sys.executable,'python_version':sys.version,'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')}}
 save(RUN/'checkpoints/start.json',start)
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_063','stage':'offline local parameter coupling and resolution analysis','objective':'verified FE responses; local SVD/bands/features; deterministic perturbation scenarios; no new inverse fit or FE','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
 sources={}
 def bind(path,expected=None):
  p=R/path;h=sha(p)
  if expected:assert h==expected,path
  sources[path]={'path':path,'sha256':h,'bytes':p.stat().st_size};return p
 for num in ['055','056','057','059','060','062']:
  bind(f'run/run_{num}/run.json');bind(f'run/run_{num}/summary.md')
  for f in read(R/f'run/run_{num}/run.json')['outputs']:bind(f['path'],f.get('sha256'))
 # Only the explicit source manifests already restricted to SPT/model evidence.
 for path,h in read(R/'run/run_062/artifacts/private/protected_sources_before.json').items():bind(path,h)
 manifest=read(R/'run/run_062/artifacts/private/evidence_manifest.json')
 for f in manifest['files']:bind(f['path'],f['sha256'])
 for num in ['055','057','059']:
  for f in read(R/f'run/run_{num}/artifacts/private/evidence_manifest.json')['files']:bind(f['path'],f['sha256'])
 frozen=read(bind('run/run_057/artifacts/prepared_batch.json'));cc=read(bind(frozen['comparison_contract_path'],frozen['comparison_contract_sha256']))
 bind(frozen['protocol_path'],frozen['protocol_sha256']);bind(cc['parent_contract'],cc['parent_contract_sha256']);bind(frozen['predictor_package_path'],frozen['predictor_package_sha256'])
 modelroot=R/'run/run_057/artifacts/private/frozen_predictor';meta=read(modelroot/'predictor_contract.json');bind(rel(modelroot/'frozen_FE_only_inverse_models.json'),meta['original_models_sha256']);bind(rel(modelroot/'training_25.json'),meta['training_data_sha256'])
 data=read(bind('run/run_059/artifacts/private/verified_response_arrays.json'));matrix=read(bind('run/run_059/artifacts/private/study_A_local_secants.json'));quality=read(bind('run/run_059/artifacts/private/main_independent_checks.json'));execution=read(bind('run/run_059/artifacts/private/execution_audit.json'))
 records=[];curves={};features={};native={};grid=np.array(data['grid_m'])
 pointmap={p['candidate_id']:p for p in frozen['points']};pointmap['I06']=cc['baseline'];pointmap['I06']['candidate_id']='I06'
 for name in ['I06','P01','P02','P03','P04']:
  p=pointmap[name];folder=(R/p['fd_path']).parent if name=='I06' else R/f'run/run_059/artifacts/private/odb/{name}'
  result=read(bind(rel(folder/'result.json')));diag=read(bind(rel(folder/'diagnostics.json')))
  for path,h in result['artifact_hashes'].items():bind(path,h)
  bind(p['inp_path'],p['inp_sha256']);fs=diag['provenance']['source_files']
  for f in fs.values():
   if f.get('path') and f.get('sha256'):bind(f['path'],f['sha256'])
  assert result['inp_sha256']==p['inp_sha256'] and result['odb_sha256']==fs['odb']['sha256']
  inp=(R/p['inp_path']).read_text(encoding='utf8');assert '0.001, 1., 1e-12, 0.0025' in inp and 'RF2, U2' in inp
  fd=rows(folder/'force_displacement.csv');u=np.array([float(r['displacement_m']) for r in fd]);f=np.array([float(r['force_n']) for r in fd]);feat,aligned,_=extract(u,f)
  np.testing.assert_allclose(aligned,data['curves'][name],rtol=0,atol=1e-11);np.testing.assert_allclose(feat,data['features'][name],rtol=1e-12,atol=1e-11)
  if name!='I06':
   q=next(q for q in quality['records'] if q['candidate_id']==name);assert q['SCIENTIFIC_SCOREABILITY']=='SCOREABLE_EXPLORATORY'
   actual=next(q for q in execution['records'] if q['candidate_id']==name);assert actual['single_attempt_confirmed'] and actual['safe_for_readonly_odb']
  else:q=cc['baseline']
  assert result['max_saved_peeq']<.9
  records.append({'sample_id':name,'sigma_y_MPa':p['sigma_y_mpa'],'n':p['n'],'inp_path':p['inp_path'],'inp_sha256':p['inp_sha256'],'ODB_path':fs['odb']['path'],'ODB_sha256':fs['odb']['sha256'],'FD_path':rel(folder/'force_displacement.csv'),'FD_sha256':sha(folder/'force_displacement.csv'),'RP':result['punch_rp_identity']['region'],'raw_points':len(fd),'initial_increment':.001,'maximum_increment':.0025,'complete_window':True,'max_PEEQ':result['max_saved_peeq'],'quality':'QUALIFIED_WITH_LIMITATIONS' if name=='I06' else 'SCOREABLE_EXPLORATORY_WITH_WARNINGS','warning_counts':q.get('warning_counts'),'cutbacks':q.get('cutbacks',q.get('cutback_count')),'coordinate':physical_to_normalized([[p['sigma_y_mpa'],p['n']]])[0].tolist()})
  curves[name]=aligned.tolist();features[name]=feat.tolist();native[name]={'u':u.tolist(),'F':f.tolist()}
 refinement=read(bind('run/run_062/artifacts/private/refinement_metrics.json'));delta=read(bind('run/run_062/artifacts/private/verified_plot_arrays.json'))
 e=np.interp(grid,delta['refined_native_u_m'],delta['refined_native_force_N'])-np.interp(grid,delta['original_native_u_m'],delta['original_native_force_N'])
 assert abs(np.sqrt(np.mean(e*e))-refinement['force_difference_RMSE_N'])<1e-10
 preservation=read(R/'run/run_061/checkpoints/start.json');assert start['git']['staged']==preservation['git']['staged'] and sha(R/'.gitignore')==preservation['gitignore_sha256']
 bind('.gitignore',preservation['gitignore_sha256'])
 for f in preservation['local_CAE']:bind(f['path'],f['sha256'])
 save(P/'source_manifest.json',{'at':now(),'scope':'bounded explicit SPT/FE/predictor sources only; no tensile data or sealed validation reports','sources':list(sources.values())})
 save(P/'verified_local_data.json',{'grid_m':grid.tolist(),'curves_N':curves,'features':features,'native':native,'records':records,'observed_center_refinement_delta_N_on_run059_grid':e.tolist(),'refinement_RMSE_reference_N':refinement['force_difference_RMSE_N'],'run059_matrix_sha256':sha(R/'run/run_059/artifacts/private/study_A_local_secants.json'),'normalization':cc['parameter_normalization'],'I06_status':'QUALIFIED_WITH_LIMITATIONS','preserve_old_max_increment':.0025,'center_refinement_max_increment':.00125,'no_refined_center_substitution_in_old_J':True})
 csvsave(P/'FE_response_inventory.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in x.items()} for x in records])
 protocol='''# run063 offline local analysis protocol

No new FE, parameter estimation from experiment, regression retraining, or changes to old outputs. Use normalized x=ln(sigma/150)/ln(1000/150), y=(n-.02)/.48; old I06 and four arms retain max dt=.0025 and h=.025. Center refinement .00125 enters ONLY as an observed deterministic response pattern/scale.

Reconstruct central secants from native curves on the run059 241-point grid. For each interval use J=A/(1428.9*sqrt(N_interval)), where A has units N per normalized coordinate. Thus singular values describe normalized RMS per unit parameter norm; half-step physical RMS=h*1428.9*s. Disjoint intervals [0,.3),[.3,.6),[.6,.9),[.9,1.2]mm plus full interval. Report interval's own strong/weak direction AND response to the same full-curve weak direction, absolute amplitude, and local observed center difference. No numerical admissibility threshold invented.

Feature views use the exact old row scales: Fref for load, Fref/1.2 for N/mm slope, Fref*.0003 or Fref*.0012 for N*m area; divide by sqrt(number of rows). Row weighting is a declared analysis metric, not a measured noise covariance. Conditions and amplitudes across views are not a statistical information percentage. Examine all17 feature response gradients for descriptive redundancy; primary2/5 definitions unchanged. Any additional combination is exploratory only, no new validation performance claim.

Sign convention: strong vector x positive, weak vector x negative/y positive. Report physical differential and exact coordinate-mapped conceptual half-step locations. Only four axis perturbations are actually evaluated; a mixed weak-direction response is a linearized prediction, not a measured FE curve or global valley.

SCENARIO ANALYSIS: deterministic response shapes, not random Gaussian draws. Amplitudes {0.25,0.5,1,2} times observed center RMSE .4326779144080392 N. Shapes: signed old strong left singular mode; signed weak mode; coherent displacement ramp; localized Gaussian-shaped bump at .98mm with width .01mm (shape only, not Gaussian noise); plus actual center refinement pattern and its sign reversal. Each synthetic shape is normalized to stated RMS on the241 grid. Spatial correlation is perfectly coherent for each fixed shape, no independence/covariance assumption. Use frozen local linear pseudoinverse solely as response-to-parameter sensitivity diagnostic, never as a new material inversion or corrected parameter estimate. Report delta normalized/physical tangent coordinates and residual projection. These are not bias estimates, confidence bounds, actual errors at four arms, or experiment precision.

No Fisher confidence interval, no strict differential-step convergence or D01 local Jacobian claim. No new feature-based formula, no re-ranking historical fits. Future FE designs are proposals only, not input generation or authorization.
'''
 write(P/'analysis_protocol.md',protocol)
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run063-coupling-analysis');task=hub.create_task(actor['agent_id'],'MAIN','offline_parameter_coupling_and_resolution',{'run':'run_063','source_manifest':rel(P/'source_manifest.json'),'source_manifest_sha256':sha(P/'source_manifest.json'),'protocol_path':rel(P/'analysis_protocol.md'),'protocol_sha256':sha(P/'analysis_protocol.md'),'new_FE':0,'no_material_inversion_or_retraining':True},'run063-offline-coupling-v1');lease=hub.claim(task['task_id'],actor,'run063-analysis-claim-v1');save(P/'hub_identity_lease.json',{'identity':actor,'task_id':task['task_id'],'lease':lease})
 assert hub.verify_chain();print(json.dumps({'run':'run_063','source_files_verified':len(sources),'actual_FE_points':len(records),'task_id':task['task_id'],'baseline_and_arms_contract':'max .0025','center_refinement_is_not_replaced_into_J':True}))
if __name__=='__main__':main()
