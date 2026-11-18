"""One I06 numerical-only candidate and future comparison freeze; preview only."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,sys,hashlib,csv,re,subprocess,difflib
import numpy as np,scipy
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_060';A=RUN/'artifacts';P=A/'private'
sys.dont_write_bytecode=True
sys.path[:0]=[str(R),str(A),str(R/'run/run_056/artifacts'),r'D:\Projects\abqjobpilot']
from review_science import parse_trials
from agenthub_sp_invopt.hub import Hub
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
from resolution_metrics import stage_peeq

def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,v):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(v)
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def rel(p):return Path(p).resolve().relative_to(R.resolve()).as_posix()
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
def plastic(raw):
 lines=raw.splitlines(keepends=True);i=next(i for i,l in enumerate(lines) if l.strip().upper()==b'*PLASTIC')+1;j=i
 while j<len(lines) and not lines[j].lstrip().startswith(b'*'):j+=1
 return b''.join(lines[i:j]),[tuple(map(float,l.strip().split(b','))) for l in lines[i:j] if l.strip()]

def main():
 assert not (RUN/'run.json').exists()
 at=now();start={'at':at,'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status')},'python':{'interpreter':sys.executable,'version':sys.version,'numpy':np.__version__,'scipy':scipy.__version__}}
 save(RUN/'checkpoints/start.json',start)
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_060','stage':'I06 numerical resolution qualification preparation','objective':'one max increment .00125 candidate and frozen weak-signal comparison; no execution','status':'RUNNING','start_time':at,'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
 oldgit=read(R/'run/run_057/checkpoints/start.json');assert start['git']['staged']==oldgit['staged'] and sha(R/'.gitignore')==oldgit['gitignore_sha256']
 for item in oldgit['local_CAE']:assert sha(R/item['path'])==item['sha256']
 sources={}
 def source(path,expected=None):
  path=Path(path);path=path if path.is_absolute() else R/path;h=sha(path)
  if expected:assert h==expected,rel(path)
  sources[rel(path)]={'path':rel(path),'sha256':h,'bytes':path.stat().st_size};return path
 for rid in range(55,60):
  for filename in ['run.json','summary.md']:source(f'run/run_{rid:03d}/'+filename)
 for path in ['run/run_055/artifacts/private/scientific_report.md','run/run_056/artifacts/private/prospective_design_contract.json','run/run_056/artifacts/private/prospective_evaluation_protocol.md','run/run_057/artifacts/prepared_batch.json','run/run_057/artifacts/private/comparison_contract.json','run/run_057/artifacts/private/scientific_report.md','run/run_058/artifacts/private/queue_manifest.json','run/run_058/artifacts/private/evidence_manifest.json','run/run_059/artifacts/private/scientific_report.md','run/run_059/artifacts/private/study_A_local_secants.json','run/run_059/artifacts/private/study_B_frozen_parameter_recovery.json','run/run_059/artifacts/private/scientific_decision.json']:
  source(path)
 old59=read(R/'run/run_059/run.json')
 for item in old59['outputs']:source(item['path'],item['sha256'])
 frozen57=read(R/'run/run_057/artifacts/prepared_batch.json');source(frozen57['predictor_package_path'],frozen57['predictor_package_sha256'])
 for item in read(R/'run/run_057/artifacts/private/frozen_predictor/package_manifest.json')['files']:source('run/run_057/artifacts/private/frozen_predictor/'+item['path'],item['sha256'])
 design=read(R/'run/run_056/artifacts/private/prospective_design_contract.json');b=design['baseline'];raw=source(b['inp_path'],b['inp_sha256']).read_bytes();source(b['odb_path'],b['odb_sha256']);source(b['params_path'],b['params_sha256'])
 result=read(source(b['result_path']));diag=read(source(b['diagnostics_path']));params=read(R/b['params_path'])
 for item in diag['provenance']['source_files'].values():source(item['path'],item['sha256'])
 for path,digest in result['artifact_hashes'].items():source(path,digest)
 assert params['sigma_y_mpa']==b['sigma_y_mpa']==236.49902622197678 and params['n']==b['n']==.0968
 assert result['inp_sha256']==b['inp_sha256'] and result['odb_sha256']==b['odb_sha256']
 assert result['full_status']['odb_job_status']=='JOB_STATUS_COMPLETED_SUCCESSFULLY' and result['full_status']['return_code']==result['datacheck_status']['return_code']==0
 assert not result['numerical_blocking_issues']
 numeric=parse_trials(diag['provenance']['source_files']);assert numeric['accepted_increments']==439 and numeric['cutback_count']==18 and numeric['warning_counts']['ACCEPTED_TRIAL']=={'ZERO_MOMENT':1}
 assert all(diag['identity_checks'].values())
 fd=rows(R/b['fd_path']);history=rows(R/result['raw_u2_rf2_step_time_csv']);peeq=rows(R/'run/run_034/artifacts/private/odb/I06/peeq_saved_frames.csv');assert len(fd)==len(history)==len(peeq)==440
 u=np.array([float(x['displacement_m']) for x in fd]);f=np.array([float(x['force_n']) for x in fd]);p=np.array([float(x['max_peeq']) for x in peeq])
 np.testing.assert_array_equal(u,-np.array([float(x['U2_raw_m']) for x in history]));np.testing.assert_array_equal(f,-np.array([float(x['RF2_raw_n']) for x in history]));assert np.all(np.diff(u)>0) and np.all(np.diff(f)>0)
 assert max(p)==result['max_saved_peeq']==.7027503848075867 and max(p)<.9
 mat_bytes,table=plastic(raw);assert len(table)==34 and table[0]==(236499026.22197679,0) and table[-1][1]==.9
 assert re.findall(rb'(?im)^\*Static\s*\r?\n([^\r\n]+)',raw)==[b'0.001, 1., 1e-12, 0.0025']
 assert b' 2.1e+11, 0.3' in raw and b'inc=999999' in raw and b'RF2, U2' in raw
 binding=read(source('run/run_030/artifacts/loss_contract_binding.json'))
 for key in ['target','config','implementation']:source(binding[key+'_path'],binding[key+'_sha256'])
 exp=rows(R/binding['target_path'])[:241];grid=[float(r['displacement_m']) for r in exp];expF=[float(r['force_n']) for r in exp]
 assert grid[0]==0 and grid[-1]==.0012 and len(grid)==241
 target=Target(Curve(tuple(grid),tuple(expF),'m','N'),(1.,)*241,1428.9,binding['version']);curve=Curve(tuple(u),tuple(f),'m','N')
 loss=evaluate(target,curve,fe_status='COMPLETED_WITH_WARNINGS',evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True,numerical_quality_accepted=True),mode='PROVISIONAL')['loss'];assert abs(loss-b['recorded_loss'])<1e-15
 native_stages=stage_peeq(u,p)
 weak_source=read(R/'run/run_059/artifacts/private/study_A_local_secants.json');weak=weak_source['views']['full241']['weak_half_step_force_RMS_N'];assert abs(weak-3.092632613282926)<1e-14
 assert abs(.025*1428.9*weak_source['views']['full241']['singular_values'][-1]-weak)<1e-14
 save(P/'I06_baseline_audit.json',{'at':now(),'qualification':'QUALIFIED_WITH_LIMITATIONS','baseline':b,'source_material_table_rows':len(table),'material_table_bytes_sha256':hashlib.sha256(mat_bytes).hexdigest(),'recomputed_loss':loss,'raw_history_points':440,'complete_window':True,'grid_m':grid,'RP_sign_rule':result['punch_rp_identity'],'max_saved_PEEQ':float(max(p)),'stage_PEEQ':native_stages,'numerical_events':numeric,'retained_warnings':result['numerical_review_warnings'],'independent_time_step_convergence':False,'old_process_provenance_gap_retained':True})
 job='SPIO_R060_I06_M00125';folder=A/'candidates'/job;folder.mkdir(parents=True,exist_ok=False);work=A/'solver'/job;work.mkdir(parents=True,exist_ok=False)
 old=b'0.001, 1., 1e-12, 0.0025';new=b'0.001, 1., 1e-12, 0.00125';assert raw.count(old)==1
 candidate=raw.replace(old,new,1)
 changes=[(b'** Job name: Job-1 Model name: Model-1',f'** Job name: {job} Model name: Model-1'.encode()),(b'** RUN_030 POINT I06; job=SPIO_R030_I06_L; offline candidate only',f'** RUN_060 I06 increment refinement; job={job}; preparation only'.encode())]
 for before,after in changes:assert candidate.count(before)==1;candidate=candidate.replace(before,after,1)
 restored=candidate.replace(new,old,1)
 for before,after in changes:restored=restored.replace(after,before,1)
 assert restored==raw and plastic(candidate)[0]==mat_bytes and plastic(candidate)[1]==table
 assert not re.search(rb'(?im)^\*(?:include|import|restart\s*,\s*read)\b',candidate)
 inp=folder/(job+'.inp')
 with inp.open('xb') as stream:stream.write(candidate)
 write(folder/'source_difference.patch',''.join(difflib.unified_diff(raw.decode().splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile='original_I06',tofile=job)))
 point={'candidate_id':'I06_M00125','job_name':job,'sigma_y_mpa':b['sigma_y_mpa'],'n':b['n'],'E_pa':210e9,'nu':.3,'material_model':params['material_model'],'material_generator':params['generator'],'material_generator_sha256':params['generator_sha256'],'max_plastic_strain':.9,'material_rows':34,'material_table_bytes_sha256':hashlib.sha256(mat_bytes).hexdigest(),'source_inp':b['inp_path'],'source_inp_sha256':b['inp_sha256'],'source_odb':b['odb_path'],'source_odb_sha256':b['odb_sha256'],'inp_path':rel(inp),'inp_absolute_path':str(inp),'inp_sha256':sha(inp),'working_dir':rel(work),'working_dir_absolute':str(work),'expected_odb':rel(work/(job+'.odb')),'expected_odb_absolute':str(work/(job+'.odb')),'numerics':{'solver':'Abaqus/Standard2024','initial_increment':.001,'maximum_increment':.00125,'minimum_increment':1e-12,'total_time':1.,'maximum_increments':999999},'numerical_contract':'run060-I06-adjacent-increment-m00125-v1','resources':{'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0},'queue_id':None,'solver_attempts':0,'execution_authorized':False}
 source(params['generator'],params['generator_sha256']);save(folder/'parameters.json',point);point['parameters_path']=rel(folder/'parameters.json');point['parameters_sha256']=sha(folder/'parameters.json')
 save(P/'input_byte_audit.json',{'status':'PASS','source_inp_sha256':sha(R/b['inp_path']),'candidate_inp_sha256':sha(inp),'old_static_data':old.decode(),'new_static_data':new.decode(),'comment_replacements':[{'old':a.decode(),'new':z.decode()} for a,z in changes],'exact_source_recovered_by_undoing_only_allowlisted_changes':restored==raw,'plastic_table_byte_identical':True,'all_other_physical_and_output_bytes_identical':True,'no_relative_dependencies':True,'independent_workdir_empty':True})
 cc={'version':'run060-I06-numerical-resolution-comparison-v1','frozen_at':now(),'status':'FROZEN_BEFORE_NEW_SOLVE','baseline':b,'candidate':point,'baseline_status_retained':'QUALIFIED_WITH_LIMITATIONS','loss_binding':binding,'grid_m':grid,'point_count':241,'window_m':[0,.0012],'units':'m,N,Pa,dimensionless plastic strain','sign':'u=-U2,F=-RF2,no2pi','sampling':'linear native FE to exact frozen experimental grid; no extrapolation','no_smoothing_zero_shift_point_deletion_or_recorrection':True,'relative_force_floor_N':71.445,'relative_difference_definition':'max_i abs(F_refined-F_original)/max(abs(F_original),71.445N); report location','metrics_implementation':rel(A/'resolution_metrics.py'),'metrics_implementation_sha256':sha(A/'resolution_metrics.py'),'metrics':['F-D RMSE N','max absolute force difference N and stroke','max regularized relative difference and stroke','frozen original/refined SPT Loss and signed/absolute change','max all-saved-frame PEEQ and signed/absolute change','PEEQ at common .3/.6/.9/1.2mm strokes','accepted/rejected trials,cutback,warning classes,final acceptance criteria','raw contact/force evolution and local jumps;availableenergy,cost,identity'],
 'weak_reference':{'value_RMS_N':weak,'rounded_display_N':3.09,'source_path':'run/run_059/artifacts/private/study_A_local_secants.json','source_sha256':sha(R/'run/run_059/artifacts/private/study_A_local_secants.json'),'json_field':'views.full241.weak_half_step_force_RMS_N','meaning':'finite-secant linearized unit weak direction, normalized halfstep .025 under run059 physical row scaling; not experimental noise or physical resolution limit'},
 'risk_ratios':{'primary':'R_RMSE=RMSE(F_refined-F_original)/3.092632613282926 N','intervals':[{'lower_inclusive':0.,'upper_inclusive':.1,'label':'SMALL_OBSERVED_CHANGE'},{'lower_exclusive':.1,'upper_inclusive':.25,'label':'NONNEGLIGIBLE'},{'lower_exclusive':.25,'upper_inclusive':.5,'label':'SUBSTANTIAL_WEAK_SIGNAL_RISK'},{'lower_exclusive':.5,'upper_inclusive':None,'label':'HIGH_WEAK_SIGNAL_RISK'}],'equivalent_RMSE_N_boundaries':[weak*v for v in [.1,.25,.5]],'meaning':'predeclared exploratory engineering risk flags, not validated convergence/acceptance/noise thresholds','max_diff_over_weak_RMS':'report descriptive mixed-statistic ratio separately, never assign the primary RMSE-risk bands to it'},
 'PEEQ_stages':{'stages_m':[.0003,.0006,.0009,.0012],'method':'linear interpolation of scalar max-per-saved-frame PEEQ on each own native punch stroke; record both bracketing frames; no extrapolation; also nearest actual frame fields','nearest_frame_rule':'minimum absolute stroke offset; earliest frame on ties; record offset and frame/increment/time','nearest_offset_review_limit_m':3e-6,'limit_scope':'sampling mismatch review flag, not PEEQ convergence threshold','maximum_field_rule':'global max over all saved frames/IPs, not final-only or percentile','warning':'scalar-max interpolation is not reconstructed field or same material-point response; nearest-stage field comparison is approximate and missing is NOT_EVALUABLE'},
 'local_diagnostic':{'fixed_window_mm':[1.10,1.16],'all_native_accepted_frames':True,'contact_node23_and_topological_neighbors':True,'compare_CPRES_COPEN_and_pressure_build_up':True,'contact_transition_elsewhere':'review global raw peaks and .68-.70/.85-.88/.97-.99mm as prior observed associations, not exclusion windows','COPEN_rule':'abs>=1e30 or nonfinite is unavailable/sentinel, never treat as gap; preserve original values','CPRESS_positive':'contact proxy, not full status proof','warnings':'map actual accepted STA attempt to its own MSG block; distinguish final converged or explicit small-residual acceptance from rejected warnings'},
 'hard_admission':['exact frozen input/job/project/output identity','one successful DC then one successful Full if separately authorized','safe terminal ODB with no active lock or process','actualRP/sign/unit and complete0-1.2mm;finite monotoneu/noextrapolation','PEEQ<.9 and actual table unchanged;>=.85 review','unexplained accepted serious warnings/force recoil or contact anomalies stop quantitative admission until reviewed'],
 'decision':{'formal_numerical_convergence_thresholds':None,'risk_band_is_not_automatic_PASS':True,'single_refinement_not_strict_error_bound':True,'center_only_not_P01_P04_Jacobian_qualification':True,'D01_changes_not_used_as_I06_error_bound':True,'small_R_and_no_blocker':'supports only small observed center adjacent-increment change relative to frozen weak signal; no asymptotic/global/material claim','large_R_or_unresolved':'hold weak-direction quantitative interpretation; report diagnostics, no automatic newrefinement/retry/parameterfit','fixed_future_protocol_no_after_result_retrofit':True},
 'protection':{'run055_CV':'unchanged','run056_design':'unchanged','run057_predictor':'unchanged','run058_queue':'unchanged','run059_results':'unchanged','REAL_MATERIAL_VALIDATION':'NOT_EVALUABLE'},'current_authority':{'candidate_INP':1,'new_FE':0,'enqueue':False,'datacheck_start':False,'solver_start':False,'automatic_retry':False,'future_solver_authorization_required':True}}
 save(A/'comparison_contract.json',cc)
 point['comparison_contract_path']=rel(A/'comparison_contract.json');point['comparison_contract_sha256']=sha(A/'comparison_contract.json')
 save(P/'candidate_identity.json',point)
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=hub.register('MAIN','codex-main-run060-I06-preparation')
 task=hub.create_task(identity['agent_id'],'MAIN','prepare_single_I06_numeric_refinement',{'run':'run_060','authorization':'current user permits one INP and frozen comparison/previews only; noFE/enqueue','candidate':point,'baseline_status':'QUALIFIED_WITH_LIMITATIONS'},'run060-I06-single-preparation-v1');hub.approve(task['task_id'],identity['agent_id'],'generate_inp');hub.approve(task['task_id'],identity['agent_id'],'verify_inp');lease=hub.claim(task['task_id'],identity,'run060-main-offline-claim-v1');save(P/'hub_session.json',{'identity':identity,'task_id':task['task_id'],'lease':lease,'no_independent_CAE_session_claim':True})
 pid='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';project=R/'agenthub_sp_invopt/abqjobpilot_project';api=AbqJobPilotClient();scope=api.for_project(project_id=pid)
 guards=[project/'project.json',project/'project.db',project/'runtime/settings.json',project/'runtime/queue.json'];before={rel(x):sha(x) for x in guards}
 cap=api.capabilities();settings=api.get_project_settings(project_id=pid).to_dict();proj=api.show_project(project_id=pid).to_dict();queue=scope.list_jobs();hist=api.list_project_jobs(project_id=pid).to_dict();runtime=assess_runtime(project/'runtime',project_db=project/'project.db')
 assert proj['status']=='OK' and proj['project']['project_id']==pid and Path(proj['project']['path']).resolve()==project.resolve()
 assert settings['status']=='PERSISTED' and settings['persisted'] and not settings['defaulted_fields'] and not settings['errors'] and settings['project_id']==pid
 s=settings['effective_settings'];assert s==settings['settings']==read(project/'runtime/settings.json') and Path(settings['project_path']).resolve()==project.resolve()
 assert (s['default_cpus'],s['default_gpus'],s['use_gpu'],s['run_datacheck'],s['run_full'])==(14,0,False,True,True) and Path(s['abaqus_cmd']).is_file() and Path(s['abaqus_cmd']).resolve()==Path(r'D:\ABAQUS2024\Commands\abq2024.bat').resolve()
 assert cap['application_version']=='0.2.2' and queue['status']==hist['status']=='OK'
 assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT' and not runtime['running_queue_ids']
 assert not [j for j in queue['jobs'] if j['raw_status'] in ['QUEUED','DATACHECK_OK','RUNNING','DATACHECK_RUNNING','FULL_RUNNING']]
 for j in queue['jobs']+hist['jobs']:
  assert j['job_name'].casefold()!=job.casefold() and Path(j['inp_path']).resolve()!=inp.resolve()
  if j.get('work_dir'):assert Path(j['work_dir']).resolve()!=work.resolve()
 assert not any(work.iterdir())
 request=JobRequest(inp_path=str(inp),job_name=job,working_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='preview_only',allow_solver_submit=False,batch='run060_I06_numeric_PREVIEW_ONLY',strategy='single_I06_adjacent_increment_weak_signal_resolution',metadata={'run':'run_060','task_id':task['task_id'],'inp_sha256':sha(inp),'authorized_FE':0,'automatic_retries':0})
 pre=scope.preflight(request).to_dict();dry=scope.enqueue(request,dry_run=True).to_dict()
 save(P/'public_preflight_dry_run.json',{'at':now(),'capabilities':cap,'settings':settings,'project':proj,'queue_before':queue,'history':hist,'runtime':runtime,'request':request.to_dict(),'preflight':pre,'dry_run':dry,'protected_before':before,'protected_after':{rel(x):sha(x) for x in guards},'new_queue':0,'new_FE':0,'no_actual_datacheck_or_solver':True})
 assert pre['status']=='PREVIEW_READY' and not pre['errors'] and dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
 assert not any(dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
 assert Path(pre['expected_odb_path']).resolve()==(work/(job+'.odb')).resolve() and before=={rel(x):sha(x) for x in guards} and queue==scope.list_jobs() and not any(work.iterdir())
 source(A/'resolution_metrics.py');source('inverse/fd_loss.py',binding['implementation_sha256'])
 save(P/'source_manifest.json',{'sources':list(sources.values()),'scope':'bounded existing FE and frozen SPT-only evidence; no tensile data or sealed analyses'})
 save(A/'prepared_batch.json',{'version':'run060-one-I06-numeric-refinement-prepared-v1','frozen_at':now(),'status':'PREPARED_PREVIEW_PASSED_NOT_ENQUEUED','project_id':pid,'project_path':rel(project),'project_absolute_path':str(project),'baseline_status':'QUALIFIED_WITH_LIMITATIONS','baseline':b,'comparison_contract_path':rel(A/'comparison_contract.json'),'comparison_contract_sha256':sha(A/'comparison_contract.json'),'order':[job],'points':[point],'resources':point['resources'],'preflight_passed':1,'dry_run_passed':1,'queue_id':None,'new_FE_authorized':0,'new_queue':0,'solver_datacheck_started':False,'future_independent_authorization_required':True})
 print(json.dumps({'job':job,'inp_sha256':sha(inp),'only_numerical_change':'max increment .0025 -> .00125','material_bytes_unchanged':True,'preflight':'PREVIEW_READY','dry_run':'DRY_RUN_READY','weak_RMS_N':weak,'risk_RMS_boundaries_N':[weak*x for x in [.1,.25,.5]],'baseline_status':'QUALIFIED_WITH_LIMITATIONS','task_id':task['task_id'],'new_FE':0,'new_queue':0}))

if __name__=='__main__':main()
