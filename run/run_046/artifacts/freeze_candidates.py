"""Freeze SPT-only candidate predictions and preregister future independent validation.
No Abaqus import, subprocess Solver, queue client, or holdout read exists here.
"""
import csv,hashlib,json,math,subprocess,sys
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_046';ART=RUN/'artifacts';P=ART/'private';F=P/'freeze'
sys.path.insert(0,str(ROOT))
from inverse.hollomon import stress_from_total_strain,stress_at_plastic_strain,generate_hollomon_table,MODEL_ID
from agenthub_sp_invopt.hub import Hub

def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,fields,rows):
 with Path(p).open('x',encoding='utf-8',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(fields)
  for row in rows:w.writerow([format(float(v),'.17g') if isinstance(v,(float,np.floating)) else v for v in row])
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def plastic(p):
 lines=p.read_text(encoding='utf8').splitlines();i=next(i for i,s in enumerate(lines) if s.strip().lower()=='*plastic');a=[]
 for s in lines[i+1:]:
  if s.lstrip().startswith('*'):break
  if s.strip():a.append(tuple(float(v) for v in s.split(',')))
 return np.array(a)
def proof(sy,n):
 # Diagnostic 0.2% offset intersection in engineering coordinates with fixed E210.
 def g(t):return stress_from_total_strain(t,sy,n)*math.exp(-t)-210e9*(math.expm1(t)-.002)
 lo,hi=0.,.1
 assert g(lo)>0 and g(hi)<0
 for _ in range(100):
  m=(lo+hi)/2
  if g(m)>0:lo=m
  else:hi=m
 t=(lo+hi)/2;return {'true_total_strain':t,'engineering_strain':math.expm1(t),'engineering_stress_pa':stress_from_total_strain(t,sy,n)*math.exp(-t),'definition':'R0.2_E210 common-reference diagnostic; not certified experimental Rp0.2 and not initial sigma_y'}

def main():
 assert not (RUN/'run.json').exists()
 assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
 F.mkdir(exist_ok=False)
 start={'at':now(),'git':{k:git(*v) for k,v in {'branch':('branch','--show-current'),'head':('rev-parse','HEAD'),'remote':('remote','-v'),'working_tree':('status','--short')}.items()},'python':sys.executable,'python_version':sys.version,'numpy':np.__version__,'matplotlib':matplotlib.__version__}
 save(RUN/'checkpoints/start.json',start)
 source=ROOT/'inverse/hollomon.py';assert sha(source)=='d937664f7fc7f845a9ed7a75a004275bf38d11a1b3f68975a05961adb9b16363'
 baseline=read(ROOT/'run/run_045/artifacts/private/main/analysis.json');prepared=read(ROOT/'run/run_043/artifacts/prepared_batch.json');meta45=read(ROOT/'run/run_045/run.json')
 expected={v['path']:v['sha256'] for v in meta45['outputs']};assert sha(ROOT/'run/run_045/artifacts/private/main/analysis.json')==expected['run/run_045/artifacts/private/main/analysis.json']
 assert meta45['decision']=='PASS_TWO_POINT_ADJACENT_REFINEMENT_ONLY'
 for p in baseline['points']:assert p['qualification']=='PASS' and all(p['checks'].values())
 binding=read(ROOT/'run/run_030/artifacts/loss_contract_binding.json')
 for k in ['target','implementation','config']:assert sha(ROOT/binding[k+'_path'])==binding[k+'_sha256']
 hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=hub.register('MAIN','codex-main-run046-constitutive-freeze')
 payload={'run':'run_046','scope':'freeze two SPT candidates and prospective independent validation protocol; no holdout access, FE, optimizer, or unblinding',
  'source_run045_analysis_sha256':sha(ROOT/'run/run_045/artifacts/private/main/analysis.json'),'generator_sha256':sha(source)}
 task=hub.create_task(identity['agent_id'],'MAIN','freeze_candidates_and_predeclare_validation',payload,'run046-candidate-freeze-v1');lease=hub.claim(task['task_id'],identity,'run046-main-claim-v1')
 save(P/'hub_session.json',{'identity':identity,'task_id':task['task_id'],'lease':lease})
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_046','stage':'Exploratory candidate constitutive freeze and independent validation preparation','objective':payload['scope'],'status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
 # Pin both source code and its .17g output format before any holdout access.
 (F/'hollomon_frozen.py').write_bytes(source.read_bytes());(F/'validation_metrics_frozen.py').write_bytes((ART/'validation_metrics.py').read_bytes())
 grid=sorted(set([i/100000 for i in range(2001)]+[i/10000 for i in range(201,9001)]+[p['sigma_y_mpa']/210000 for p in prepared['points']]))
 csvsave(F/'true_total_strain_grid.csv',['true_total_strain'],[(e,) for e in grid])
 primary=[i/10000 for i in range(20,1001)]
 csvsave(F/'validation_primary_grid.csv',['true_total_strain'],[(e,) for e in primary])
 candidates=[];curves={};tables={};samples=[]
 for old,p in zip(baseline['points'],prepared['points']):
  pid=p['point_id'];assert old['point_id']==pid
  sy=p['sigma_y_mpa'];n=p['n'];assert (sy,n)==(old['sigma_y_mpa'],old['n'])
  assert sha(ROOT/p['inp_path'])==p['inp_sha256'] and sha(ROOT/p['parameters_path'])==p['parameters_sha256']
  generated=generate_hollomon_table(sy,n,max_plastic_strain=.9,relative_tolerance=.001)
  deployed=plastic(ROOT/p['inp_path']);assert np.array_equal(deployed,np.array(generated.rows))
  table_csv=F/(pid+'_abaqus_yield_stress_plastic_strain.csv')
  csvsave(table_csv,['yield_stress_pa','equivalent_plastic_strain'],generated.rows)
  assert max(abs(stress_at_plastic_strain(float(p0),sy,n)-s)/s for s,p0 in deployed)<1e-12
  e_nodes=np.r_[0.,deployed[:,1]+deployed[:,0]/210e9];s_nodes=np.r_[0.,deployed[:,0]]
  true=np.array([stress_from_total_strain(e,sy,n) for e in grid]);implemented=np.interp(grid,e_nodes,s_nodes)
  plastic_u=np.array([0. if e<=sy/210000 else e-s/210e9 for e,s in zip(grid,true)])
  assert min(plastic_u)>=0 and max(plastic_u)<=.9 and max(grid)<=max(e_nodes)
  csvsave(F/(pid+'_true_total_curve.csv'),['true_total_strain','true_stress_pa','uniaxial_plastic_strain','abaqus_piecewise_true_stress_pa'],zip(grid,true,plastic_u,implemented))
  params={'version':'run046-frozen-candidate-parameters-v1','candidate_id':pid,'designation':'current_best_evaluated_candidate' if pid=='D01' else 'competitive_alternative_candidate',
    'sigma_y_mpa':sy,'n':n,'E_pa':210e9,'nu':.3,'model_id':MODEL_ID,'yield_true_total_strain':sy/210000,
    'formula':'sigma=E*epsilon for epsilon<=sigma_y/E; otherwise sigma_y*(epsilon/(sigma_y/E))**n; p=epsilon-sigma/E',
    'strain_definition':'uniaxial logarithmic true total strain, dimensionless','stress_unit':'Pa','candidate_true_total_interpretation':True,
    'primary_validation_prediction':'analytic true-total curve; deployed piecewise table realization secondary only',
    'true_total_sampling':{'start':0.,'end':.9,'segments':[{'start':0,'end':.02,'step':1e-5},{'start':.0201,'end':.9,'step':1e-4}],'include_both_exact_yield_strains':True,'points':len(grid),'grid_path':rel(F/'true_total_strain_grid.csv'),'grid_sha256':sha(F/'true_total_strain_grid.csv')},
    'plastic_sampling':{'coverage':[0.,.9],'mode':'existing deterministic adaptive material rows, exactly equal to evaluated INP','rows':len(deployed),'relative_tolerance':.001,'conservative_relative_bound':generated.conservative_relative_error_bound},
    'generator_path':rel(source),'generator_sha256':sha(source),'generator_snapshot_sha256':sha(F/'hollomon_frozen.py'),'git_head':start['git']['head'],
    'source_inp':p['inp_path'],'source_inp_sha256':p['inp_sha256'],'source_odb':p['expected_odb'],'source_odb_sha256':next(r for r in read(ROOT/'run/run_045/artifacts/private/execution_audit.json')['records'] if r['point_id']==pid)['files']['odb']['sha256'],
    'queue_id':old['queue_id'],'SPT_loss':old['validation_loss'],'SPT_loss_status':'EXPLORATORY','numerical_qualification':'PASS_TWO_POINT_ADJACENT_REFINEMENT_ONLY',
    'max_saved_peeq':old['max_saved_peeq'],'proof_stress_common_reference':proof(sy,n),'physical_validation':'NOT_YET_EVALUATED',
    'extrapolation_warning':'Stored 0–0.9 true-total strain range is a mathematical candidate envelope, not experimentally validated uniform strain or a PEEQ-to-uniaxial history conversion'}
  save(F/(pid+'_parameters.json'),params);candidates.append(params);curves[pid]=true;tables[pid]=deployed
  for e in [sy/210000,.002,.01,.1,.4,.9]:samples.append({'candidate_id':pid,'true_total_strain':e,'true_stress_mpa':stress_from_total_strain(e,sy,n)/1e6})
 csvsave(F/'constitutive_samples.csv',['candidate_id','true_total_strain','true_stress_mpa'],[(r['candidate_id'],r['true_total_strain'],r['true_stress_mpa']) for r in samples])
 # Independent protocol choices are engineering preregistration assumptions, not derived from the hidden data.
 protocol={'version':'run046-independent-tensile-validation-v1','frozen_at':now(),'status':'PREREGISTERED_NO_UNBLIND_AUTHORIZATION','purpose':'compare frozen SPT-only predictions against held-out tensile measurements without feedback tuning',
  'independence':{'historical_run015_exposure':True,'strict_never_unblinded_claim':False,'preferred_reviewer':'person who has not accessed tensile contents, or isolated process supplied only this package and later explicitly authorized raw measurement','do_not_share_historical_tensile_or_mixed_reports':True,'new_unblinding_authorization_required':True},
  'qualification_gates':['explicit user authorization before any source/derivative read or rehash','verify all freeze hashes before data access','record source file/sheet/sample and hash after authorization only','SA508 grade alone insufficient: establish batch/heat/treatment/state, direction, temperature and strain rate correspondence','confirm units, strain definition and gauge location, calibration and zero/compliance provenance','identify uniform pre-necking segment independently of candidate fit'],
  'input_priority':['traceable gauge Force–Extension plus A0/L0 and extensometer definition','traceable engineering stress/strain with original dimensions and processing','direct true stress/log-total strain only with documented derivation, local area/gauge and uniformity'],
  'not_inferable':['never use SPT specimen dimensions for tensile geometry','no crosshead extension conversion without documented compliance/gauge correction','no assumption percent strain is dimensionless, or plastic strain is total strain','missing area/gauge length/strain definition -> no invented conversion'],
  'transformations':{'engineering_stress_pa':'F_N/A0_m2','engineering_strain':'gauge_extension_m/L0_m','true_total_strain':'log1p(engineering_strain)','true_stress_pa':'engineering_stress_pa*(1+engineering_strain)','plastic_strain_diagnostic':'true_total_strain-true_stress_pa/210e9; no negative-value clipping for measurements','assumptions':'monotonic uniaxial uniform deformation, isotropic approximate volume conservation in engineering-to-true conversion','units':'explicit Pa/MPa, m/mm, dimensionless/% conversion recorded; tension positive only after definition verification'},
  'necking':{'engineering_conversion_cutoff':'first global maximum Force or engineering stress on traceable monotonic loading; no data beyond that point in ordinary conversion','peak_not_observed_or_peak_is_last':'uniformity not proven; require independent documentation, otherwise formal necking qualification unresolved','post_necking':'archive separately; no conventional global engineering-to-true conversion as constitutive ground truth; no ad hoc correction or fitting','direct_true_data':'still verify local/multiaxial meaning; necked geometry stress not automatically homogeneous uniaxial material law'},
  'sampling':{'prediction_grid':rel(F/'true_total_strain_grid.csv'),'prediction_grid_sha256':sha(F/'true_total_strain_grid.csv'),'interpolation':'linear on frozen predictions and measured true-total loading curve; no sorting, smoothing, extrapolation, deleting points, fit-based zero shift or per-candidate window','primary_grid':rel(F/'validation_primary_grid.csv'),'primary_grid_sha256':sha(F/'validation_primary_grid.csv'),'primary_interval_true_total':[.002,.1],'primary_points':981,'primary_incomplete':'primary error/rank null; do not shorten window; still report fully covered preregistered bands as partial diagnostics only','fixed_bands_true_total':[[0,.002],[.002,.01],[.01,.02],[.02,.05],[.05,.1],[.1,.2]],'band_grid_step':1e-4,'bands_must_be_fully_covered_and_pre_necking':True,'prediction_domain_max':.9,'range_selection_basis':'engineering preregistration before unblinding, not a claim concerning withheld uniform elongation'},
  'error_metrics':{'absolute':['RMSE_MPa','MAE_MPa','signed_bias_MPa','max_absolute_error_MPa_and_strain'],'relative':['mean and maximum abs residual/max(abs experimental stress,50 MPa)','unregularized relative errors only for |stress_exp|>=50 MPa, report count; do not silently substitute for regularized metrics'],'stress_reference_pa':500e6,'relative_floor_pa':50e6,'primary_normalized_mse':'mean(((sigma_pred-sigma_exp)/500e6)**2)','primary_rank':'lowest full-window RMSE_MPa, with numerical ties <=1e-6 MPa; no statistical significance implied','physical_accuracy_PASS_threshold':None,'no_retroactive_PASS_threshold':'no acceptable experimental/model discrepancy supplied; report error magnitude and rank, not invented material-validation PASS; future tolerances declared after reading are post hoc'},
  'replicates':{'keep_all':'all traceable loading curves are kept with specimen identity; no best-fit specimen selection','same_state_complete_primary':'equal-weight mean of per-specimen primary MSE; report each replicate and coverage before aggregate','partial_primary':'do not aggregate unequal windows or silently drop incomplete tests; complete-only subset descriptive and labeled','different_batches_or_states':'separate groups, do not merge; unmatched groups external transfer comparison rather than same-material independent validation'},
  'yield_comparison':{'initial_sigma_y':'true first-yield parameter at p=0, compare to reported onset only if same definition; not Rp0.2','Rp0p2':'retain reported proof stress definition and standard; never equate with initial sigma_y','common_reference_R0p2_E210':'first intersection engineering stress=210GPa*(engineering strain-0.002), using engineering conversion of both predictions and measurements, within qualified uniform coverage; fixed-reference diagnostic, not a certified experimental proof-stress procedure','E_check':'compare traceable measured/reported E with fixed210GPa; do not refit frozen candidate E','optional_E_diagnostic':'OLS stress versus true strain on fixed [0.0001,0.0005], >=10 raw points and R2>=0.995; retain intercept without shifting measurements; otherwise null; no certified-standard claim'},
  'hardening_comparison':{'secant_moduli_intervals_true_total':[[.005,.01],[.01,.02],[.02,.05],[.05,.1]],'plastic_axis':'p=epsilon_true_total-sigma_true/210GPa, small-elastic-strain convention, separately labeled','fixed_plastic_evaluation_points':[0,.002,.01,.05],'plastic_axis_invalid_or_nonmonotonic':'preserve raw; secondary plastic comparison null, no sorting/clipping/smoothing','n_diagnostic':'optional apparent log(sigma)-log(true total strain) slope over fixed [.01,.05], no fitting back to candidates; plastic-strain fit exponent not interchangeable'},
  'prediction_views':{'primary':'analytic candidate true-total law frozen CSV','secondary':'actual Abaqus piecewise-linear material realization frozen companion column; never select view based on which wins'},
  'report_requirements':['D01/I08 per-test and qualified aggregate errors, ranking and prediction/experiment coverage','compare tensile ranking against D01-before-I08 SPT ranking without changing either','report unresolved identity, measurement, experimental uncertainty and numerical limitations','if ranking difference is comparable to measurement uncertainty, report unresolved statistical preference; single refinement is not a universal numerical bound','mismatch remains mismatch; archive frozen predictions, no feedback parameter/curve/Loss/window/score edits','no formal parameter confidence interval or global uniqueness conclusion from two curves'],
  'method_source':{'title':'SIMULIA Defining plasticity in Abaqus','url':'https://docs.software.vt.edu/abaqusv2025/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm','consulted_at':now(),'scope':'engineering/true and total/plastic definitions, pre-necking limit; not authority for any SA508 property or validation tolerance'},
  'implementation_path':rel(ART/'validation_metrics.py'),'implementation_sha256':sha(ART/'validation_metrics.py'),'test_path':rel(ART/'test_validation_metrics.py'),'test_sha256':sha(ART/'test_validation_metrics.py')}
 save(F/'independent_validation_protocol.json',protocol)
 # Freeze source ledger with explicit uncertainty, rather than invent an exact historic FE total.
 prior=read(ROOT/'run/run_039/artifacts/private/main/main_review.json');old_audit=read(ROOT/'run/run_039/artifacts/private/execution_audit.json');pilot=read(ROOT/'run/run_042/artifacts/private/execution_audit.json')
 ledger={'scope':'SPT exploration run030/run033 DOE, run040 pilot, run043 refinements; historical earlier forward checks referenced separately',
 'DOE_distinct_parameters':22,'DOE_scoreable_original_settings':19,'pilot_new_attempts':8,'pilot_scoreable':5,'refinement_new_attempts':2,'refinement_qualified':2,
 'unique_parameter_points_in_DOE_plus_pilot':30,'scoreable_distinct_parameter_points':24,'refinement_is_not_new_parameter_point':True,
 'known_completed_software_attempts_in_scope':22+8+2,'documented_D09_attempt_identities':old_audit['total_d09_attempts'],
 'exact_all_started_attempts':None,'exact_all_attempt_cost':None,'unresolved_reason':'Original interrupted D09 and prior retry history status UNKNOWN retained; no reconstructing unobserved starts/durations',
 'completed_DOE_wall_seconds':prior['totals']['runtime_sum_22_completed_s'],'completed_pilot_wall_seconds':sum(r['actual_runtime_s'] for r in pilot['records']),'completed_refinement_wall_seconds':sum(r['actual_runtime_s'] for r in baseline['points']),
 'formal_parameter_confidence_interval':None,'parameter_uncertainty_status':'two competing observed candidates; no formal interval or global uniqueness proof',
 'current_run_new_FE_calls':0,'new_solve_authorization':0,'source_references':['run/run_039/artifacts/private/execution_audit.json','run/run_039/artifacts/private/main/main_review.json','run/run_042/artifacts/private/execution_audit.json','run/run_045/artifacts/private/execution_audit.json']}
 save(F/'exploration_call_cost_ledger.json',ledger)
 result={'version':'run046-frozen-SPT-inversion-candidate-results-v1','frozen_at':now(),'optimization_phase':'CLOSED_NO_MORE_AUTOMATIC_BO_DE','candidates':candidates,
 'best_label_scope':'D01 best evaluated exploratory SPT candidate, not true material answer; no off-grid global optimum claim','alternative_label':'I08 competitive alternative, not confidence bound',
 'SPT_loss_version':binding['version'],'SPT_target_identity':{k:binding[k] for k in ['target_path','target_sha256','implementation_path','implementation_sha256','config_path','config_sha256']},
 'SPT_units':'force N; actual punch displacement m converted from confirmed mm; frozen experiment241points0–1.2mm; no zero/compliance adjustment',
 'baseline_numeric_contract':'run030-standard-m0025-hollomon-v1','refined_numeric_contract':'run043-standard-m00125-pending-v1, pointwise PASS only; old identifier retained',
 'refined_numeric_controls':{'initial':.001,'maximum':.00125,'minimum':1e-12,'time':1,'max_increments':999999,'cpus':14,'gpus':0},
 'SPT_evidence':{'source_analysis':'run/run_045/artifacts/private/main/analysis.json','source_analysis_sha256':sha(ROOT/'run/run_045/artifacts/private/main/analysis.json'),'ranking':baseline['ranking'],'mutual_refined_fd':baseline['refined_pair'],'compensation':'similar scalar SPT Loss with different residual shapes and predicted constitutive laws; supported competing samples, not proven continuous/global nonuniqueness'},
 'limitations':['idealised fixed clamping annulus, not validated real fixture equivalence','E210GPa and nu0.3 fixed assumptions, not independently tensile-verified','true-total Hollomon candidate interpretation; no damage/necking constitutive validation','no mesh convergence or parameter-domain-wide numerical qualification','no repeated-experiment uncertainty distribution or formal parameter CI','D01 near retained lower sigma_y boundary150MPa','historical run015 MAIN/ODB tensile exposure retained; no strictly never-unblinded claim','D09 historical incomplete cost/attempt details remain UNKNOWN','previous run025 BLOCKED history unchanged'],
 'freeze_policy':'No retrospective alteration after tensile access; changes require a new explicitly labeled non-independent development study preserving this package',
 'validation_protocol_path':rel(F/'independent_validation_protocol.json'),'validation_protocol_sha256':sha(F/'independent_validation_protocol.json'),'call_cost_ledger_path':rel(F/'exploration_call_cost_ledger.json'),'unblind_authorization':False}
 save(F/'frozen_inversion_results.json',result)
 fig,ax=plt.subplots(1,3,figsize=(15,4.8),layout='constrained')
 for a,limit in zip(ax[:2],[.003,.2]):
  mask=np.array(grid)<=limit
  for pid in ['D01','I08']:a.plot(np.array(grid)[mask],curves[pid][mask]/1e6,label=pid)
  a.set(xlabel='True total strain',ylabel='Predicted true stress (MPa)');a.legend();a.grid(alpha=.2)
 ax[0].set_title('Yield neighborhood');ax[1].set_title('Fixed frozen predictions')
 for pid in ['D01','I08']:ax[2].plot(tables[pid][:,1],tables[pid][:,0]/1e6,label=pid,marker='.',ms=3)
 ax[2].set(xlabel='Equivalent plastic strain',ylabel='Yield stress (MPa)',title='Exact evaluated Abaqus material rows');ax[2].legend();ax[2].grid(alpha=.2)
 fig.suptitle('SPT-derived candidates frozen before new tensile access; no tensile validation performed')
 fig.savefig(F/'candidate_constitutive_comparison.png',dpi=170);plt.close(fig)
 # Immutable predictive evidence links; no ODB duplicate or protected tensile access.
 source_files=[source,ROOT/'run/run_043/artifacts/prepared_batch.json',ROOT/'run/run_043/artifacts/comparison_contract.json',ROOT/'run/run_045/run.json',ROOT/'run/run_045/artifacts/private/main/analysis.json',ROOT/'run/run_030/artifacts/loss_contract_binding.json',ROOT/binding['target_path']]
 save(F/'input_provenance.json',{'frozen_at':now(),'files':[{'path':rel(p),'sha256':sha(p)} for p in source_files],'license':'existing project SPT sources, collaborator-private; no public redistribution of recoverable data','processing':'only existing law evaluated and existing evidence bound; raw measurements unmodified'})
 # Self-contained protocol prose and boundary checklist, authored before data access.
 protocol_md='''# 独立拉伸验证预注册协议 — run046-v1\n\n本协议与JSON同时冻结。候选与评分不得因新数据不匹配而修改。\n\n1. 用户明确解盲授权前，任何角色不得读取或重哈希原始拉伸及封存派生内容。建议由未接触旧数据的人员，在不继承混合历史报告的隔离上下文审核；历史MAIN/ODB信息暴露不能被删除。\n2. 授权后先核验冻结清单；再只读登记拉伸样本、来源/公式/单位、原始面积A0、标距L0、测量位置、材料炉批/热处理/方向/温度/应变率、校正及颈缩证据。仅同称SA508不足以证明同一材料状态。无法对应时保留外部可迁移性比较，不能冒称同材独立验证。\n3. 工程应变取有效标距延伸/L0；真总应变ln(1+e)，真应力s(1+e)。只在确认的颈缩前均匀单轴段使用，保留体积近似；不能用横梁位移或SPT几何猜拉伸尺寸。颈缩后全局工程转换禁止作材料真值。\n4. 主要预测为冻结解析真总应变曲线；实际Abaqus分段表实现只作预先指定的辅助比较。固定主评分真总应变0.002–0.10、步长0.0001、981点；两候选同一实验轴、线性插值、无平滑/移零/删点/外推。若实验均匀段无法完整覆盖，主评分与主排序null，不缩窗；仅报告预注册完整子区间诊断。\n5. 固定分区0–.002、.002–.01、.01–.02、.02–.05、.05–.10、.10–.20，全部用步长1e-4，分别报告RMSE/MAE/偏差/最大差MPa及相对误差。正则分母max(|实验应力|,50MPa)，独立归一化尺度500MPa。主排序依完整窗RMSE；不把此拉伸评分叫原SPT Loss。\n6. σy为真初始屈服参数，并非0.2%规定塑性延伸强度。保留实验报告的定义；另给固定E210的工程0.2%偏移交点R0.2_E210作同口径诊断，不能冒称标准认证Rp0.2。硬化端点差/斜率和总/塑性应变分别记录，不能混用n。实验E只用于核验固定210的假设，不回调预测。\n7. 重复试样逐条保存，不挑最贴合曲线，不先平均原始曲线；同状态且完整覆盖者可按每试样MSE等权汇总，并明示不完整及不同批次的结果。多候选仅按共同合格试样比较。\n8. 预先未获得可接受的材料预测误差阈值，因此不杜撰物理PASS线；只报告误差、证据等级及排序。若以后才设阈值，应明示事后标准，不追溯改此冻结方案。量测不确定性不足时不能宣称两个误差差距统计显著。\n9. 比较拉伸排序与已冻结SPT排序D01优先，不预设两者一致。发生不匹配也不修改参数、Loss、曲线、区间或权重；任何新开发须另立非独立研究及授权。\n\n技术定义依据：[SIMULIA原始文档](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEGSARefMap/simagsa-c-matdefining.htm)。这仅支持转换定义与颈缩限制，不提供SA508参数或误差准入值。\n\n0–0.9存储域是候选数学曲线范围，不代表整段为实验均匀变形或物理验证区。PEEQ也不直接等于单轴真总应变。解盲读取尚未授权，本Run结束即停止。\n'''
 (F/'independent_validation_protocol.md').write_text(protocol_md,encoding='utf8')
 tests=subprocess.run([sys.executable,'-B',str(ART/'test_validation_metrics.py')],capture_output=True,text=True,cwd=ROOT)
 save(P/'validation_tests.json',{'at':now(),'exit_code':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr,'synthetic_only':True});assert tests.returncode==0
 print(json.dumps({'task_id':task['task_id'],'points':len(grid),'table_rows':[len(tables[p]) for p in ['D01','I08']],'source_table_exact':True,'tests':11,'freeze_directory':rel(F)},ensure_ascii=False))

if __name__=='__main__':main()
