"""Post-validation offline assessment. No solver, enqueue, optimization or fitting of material parameters."""
import csv,hashlib,json,math,re,subprocess,sys,itertools
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy.stats import pearsonr,spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_049';ART=RUN/'artifacts';P=ART/'private'
sys.path.insert(0,str(ROOT))
from inverse.hollomon import stress_from_total_strain
from agenthub_sp_invopt.hub import Hub

def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(p,data):
 with Path(p).open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def fd(p):
 r=rows(p);u=np.array([float(v['displacement_m']) for v in r]);f=np.array([float(v['force_n']) for v in r]);assert np.isfinite(u).all() and np.isfinite(f).all() and np.all(np.diff(u)>0);return u,f

def main():
 assert not (RUN/'run.json').exists() and sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
 start={'at':now(),'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short')},'python':sys.executable,'versions':{'numpy':np.__version__}}
 save(RUN/'checkpoints/start.json',start)
 guards=[ROOT/p for p in ['run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip','run/run_046/artifacts/private/freeze/independent_validation_protocol.json','run/run_047/artifacts/private/independent_validation_report.md','run/run_048/artifacts/private/independent_reassessment_report.md']]
 before={rel(p):sha(p) for p in guards};save(P/'protected_before.json',before)
 assert before[rel(guards[0])]=='d439ef3ae696d9711aa3a3d4fa989f61710adf3cd9a73c9935b9432131dddc3a'
 h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=h.register('MAIN','codex-main-run049-post-validation-assessment')
 payload={'run':'run_049','scope':'offline A parameter compensation, B candidate model families, C boundary uncertainty designs; no new FE or fit','protected_evidence':before,'formal_independent_validation':'NOT_EVALUABLE_UNCHANGED','calibration_data_role':'any new tensile-informed model selection is development use, not unused holdout'}
 task=h.create_task(identity['agent_id'],'MAIN','post_validation_scientific_assessment_and_design',payload,'run049-scientific-assessment-v1');lease=h.claim(task['task_id'],identity,'run049-main-claim-v1')
 save(P/'hub_session.json',{'identity':identity,'task_id':task['task_id'],'lease':lease})
 save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_049','stage':'Post-validation scientific assessment and next-study design','objective':payload['scope'],'status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'inputs':[],'outputs':[],'validation':[],'errors':[]})
 binding=read(ROOT/'run/run_030/artifacts/loss_contract_binding.json')
 for k in ['target','implementation','config']:assert sha(ROOT/binding[k+'_path'])==binding[k+'_sha256']
 target=rows(ROOT/binding['target_path'])[:241];u=np.array([float(r['displacement_m']) for r in target]);exp=np.array([float(r['force_n']) for r in target]);ref=1428.9
 initial=read(ROOT/'run/run_040/artifacts/private/initial_dataset.json');pilot=read(ROOT/'run/run_042/artifacts/private/main/main_analysis.json')
 dataset=[];curves={};provenance=[]
 for r in initial['valid']:
  assert r['numeric_version']=='run030-standard-m0025-hollomon-v1' and r['loss_version']=='run017-exploratory-fd-v1'
  dataset.append({**r,'candidate_id':r['point_id'],'region_or_branch':'DOE','fd_path':r['fd_path'],'fd_sha256':r['fd_sha256'],'source_result':r['result_path']})
 for r in pilot['rows']:
  if r['loss'] is None:continue
  result=read(ROOT/r['result_path']);assert sha(ROOT/r['result_path'])==r['result_sha256']
  path=result['positive_fd_csv'];dataset.append({'candidate_id':r['candidate_id'],'point_id':r['candidate_id'],'sigma_y_mpa':r['sigma_y_mpa'],'n':r['n'],'x':r['x'],'y':r['y'],'loss':r['loss'],'runtime_s':r['actual_runtime_s'],'cutback':r['cutback'],'numerical_quality':r['quality'],'region_or_branch':r['algorithm'],'fd_path':path,'fd_sha256':sha(ROOT/path),'source_result':r['result_path'],'numeric_version':'run030-standard-m0025-hollomon-v1','loss_version':'run017-exploratory-fd-v1'})
 assert len(dataset)==24 and len({r['candidate_id'] for r in dataset})==24
 for r in dataset:
  path=ROOT/r['fd_path'];assert sha(path)==r['fd_sha256'];ux,fy=fd(path);assert ux[0]<=u[0] and ux[-1]>=u[-1]
  curves[r['candidate_id']]=np.interp(u,ux,fy)
  value=math.fsum(((float(a)-float(b))/ref)**2 for a,b in zip(curves[r['candidate_id']],exp))/241
  assert abs(value-r['loss'])<1e-12
  assert abs(r['x']-math.log(r['sigma_y_mpa']/150)/math.log(1000/150))<1e-14 and abs(r['y']-(r['n']-.02)/.48)<1e-14
  provenance.append({'candidate_id':r['candidate_id'],'fd_path':r['fd_path'],'fd_sha256':r['fd_sha256'],'result_path':r['source_result'],'result_sha256':sha(ROOT/r['source_result'])})
 dataset.sort(key=lambda r:r['loss']);best=dataset[0]['loss'];lowsets={}
 for label,limit in [('twice_best_observed',2*best),('less_or_equal_0p002',.002),('less_or_equal_0p01',.01)]:
  selected=sorted([r for r in dataset if r['loss']<=limit],key=lambda r:r['x']);xy=np.array([[r['x'],r['y']] for r in selected])
  gaps=np.linalg.norm(np.diff(xy,axis=0),axis=1).tolist()
  lowsets[label]={'descriptive_threshold':limit,'ids':[r['candidate_id'] for r in selected],'count':len(selected),'normalized_adjacent_gaps_by_x':gaps,
   'max_gap':max(gaps) if gaps else None,'pearson_xy':float(pearsonr(xy[:,0],xy[:,1]).statistic) if len(selected)>=3 else None,
   'spearman_xy':float(spearmanr(xy[:,0],xy[:,1]).statistic) if len(selected)>=3 else None,
   'interpretation':'post hoc descriptive selection, not a confidence region; connecting samples does not evaluate intervening FE'}
 pairs=[]
 low=[r for r in dataset if r['loss']<=.01]
 for a,b in itertools.combinations(low,2):
  d=curves[b['candidate_id']]-curves[a['candidate_id']]
  pairs.append({'a':a['candidate_id'],'b':b['candidate_id'],'normalized_parameter_distance':math.hypot(a['x']-b['x'],a['y']-b['y']),
   'fd_rmse_n':float(np.sqrt(np.mean(d*d))),'fd_max_abs_n':float(np.max(abs(d))),'absolute_loss_gap':abs(a['loss']-b['loss'])})
 refined=read(ROOT/'run/run_045/artifacts/private/main/analysis.json');refined_curves={};peeqscope=[]
 source48=read(ROOT/'run/run_048/artifacts/private/reassessment_metrics.json');source_stress=source48['landmarks']['0.1']['origin_mpa']*1e6
 p_limit=.1-source_stress/210e9
 for p in refined['points']:
  pid=p['point_id'];folder=ROOT/'run/run_045/artifacts/private/odb'/pid;result=read(folder/'result.json');assert result['max_saved_peeq']==p['max_saved_peeq']
  for path,digest in result['artifact_hashes'].items():
   if Path(path).name in ['force_displacement.csv','peeq_saved_frames.csv']:assert sha(ROOT/path)==digest
  ux,fy=fd(folder/'force_displacement.csv');refined_curves[pid]=np.interp(u,ux,fy)
  history={int(v['frame_index']):v for v in rows(folder/'force_displacement.csv')};peeq=rows(folder/'peeq_saved_frames.csv')
  assert max(float(v['max_peeq']) for v in peeq)==p['max_saved_peeq']
  exceed=[v for v in peeq if float(v['max_peeq'])>p_limit];first=exceed[0]
  peeqscope.append({'candidate_id':pid,'max_saved_peeq':p['max_saved_peeq'],'conditional_tensile_uniform_plastic_limit':p_limit,'ratio_max_to_tensile_limit':p['max_saved_peeq']/p_limit,
   'first_saved_exceedance_displacement_mm':float(history[int(first['frame_index'])]['displacement_m'])*1000,'first_saved_exceedance_time':float(first['step_time']),
   'first_saved_exceedance_increment':int(first['increment']),'fraction_saved_frames_with_a_max_exceeding_limit':len(exceed)/len(peeq),
   'caveat':'Conditional tensile plastic strain derived under confirmed-axis/elastic convention; PEEQ maximum is multiaxial model index, not measured uniaxial total strain, volume fraction or proof of F-D dominance',
   'rows':peeq,'fd_history':history})
 # Existing source-confirmed residual decomposition; no new model calibration.
 strain_rows=rows(ROOT/'run/run_048/artifacts/private/restricted_pointwise_comparison.csv');ee=np.array([float(r['assumed_log_true_total_strain']) for r in strain_rows]);assert len(ee)==981
 residue={pid:np.array([float(r[pid+'_minus_source_MPa']) for r in strain_rows]) for pid in ['D01','I08']};plateau_mask=ee<=.01+1e-15
 tensile_diagnostics=[]
 for pid,r in residue.items():
  tensile_diagnostics.append({'candidate_id':pid,'full_source_confirmed_rmse_mpa':float(np.sqrt(np.mean(r*r))),'plateau_containing_band_points':int(sum(plateau_mask)),
   'plateau_containing_band_rmse_mpa':float(np.sqrt(np.mean(r[plateau_mask]**2))),'plateau_containing_band_squared_error_fraction':float(np.sum(r[plateau_mask]**2)/np.sum(r*r)),
   'post_band_start_true_strain':float(ee[~plateau_mask][0]),'post_band_points':int(sum(~plateau_mask)),'post_band_rmse_mpa':float(np.sqrt(np.mean(r[~plateau_mask]**2))),
   'all_negative_residuals':bool(np.all(r<0)),'scope':'supplementary source-confirmed diagnostic; not formal validation, exact plateau boundaries not established; no score window modified'})
 # Read only the actual constraint blocks needed for C, not a new full model audit.
 inp=ROOT/'run/run_043/artifacts/candidates/SPIO_R043_V_D01_M00125/SPIO_R043_V_D01_M00125.inp';raw=inp.read_text(encoding='utf8');lines=raw.splitlines();nodes={};inside=False;sets={}
 for line in lines:
  if line.lower().startswith('*part, name=part_specimen'):inside=True
  elif inside and line.lower().startswith('*end part'):inside=False
  elif inside and line.strip() and not line.startswith('*'):
   vals=[v.strip() for v in line.split(',')]
   if len(vals)==3 and vals[0].isdigit() and any('.' in v or 'e' in v.lower() for v in vals[1:]):nodes.setdefault(int(vals[0]),(float(vals[1]),float(vals[2])))
 for name in ['set_specimen_clamped_top','set_specimen_clamped_bot']:
  j=next(i for i,line in enumerate(lines) if line.lower().startswith('*nset, nset='+name));labels=[]
  for line in lines[j+1:]:
   if line.startswith('*'):break
   labels.extend(int(v.strip()) for v in line.split(',') if v.strip())
  rr=[nodes[l][0] for l in labels];yy=[nodes[l][1] for l in labels]
  sets[name]={'nodes':labels,'count':len(labels),'radius_m':[min(rr),max(rr)],'height_m':[min(yy),max(yy)],'constrained_dofs':[1,2]}
 boundary={'input_path':rel(inp),'input_sha256':sha(inp),'clamped_sets':sets,'punch_specimen_friction_coefficient':.1,'slip_tolerance':.005,
  'contact_pairs':[line for i,line in enumerate(lines) if i>0 and lines[i-1].lower().startswith('*contact pair')],
  'facts':'Both top/bottom annular face node sets have U1=U2=0. Actual INP has one punch/specimen contact pair, not force-controlled finite clamp/die contact.',
  'unknown_actual_fixture':['upper/lower clamp inner/outer radius and fillet','clamping force or torque-to-force calibration','contact pressure distribution and surface lubrication/friction','fixture compliance and specimen radial draw-in']}
 # No new fit. Exact stress crossing of the two already-frozen analytic laws.
 d,i=refined['points'];nd,ni=d['n'],i['n'];sd,si=d['sigma_y_mpa'],i['sigma_y_mpa']
 crossing=math.exp(((1-ni)*math.log(si)-(1-nd)*math.log(sd))/(nd-ni)-math.log(210000.))
 assert abs(stress_from_total_strain(crossing,sd,nd)-stress_from_total_strain(crossing,si,ni))<1e-4
 zd=np.array([math.log(sd/150)/math.log(1000/150),(nd-.02)/.48]);zi=np.array([math.log(si/150)/math.log(1000/150),(ni-.02)/.48]);direction=(zi-zd)/np.linalg.norm(zi-zd);normal=np.array([-direction[1],direction[0]]);mid=(zd+zi)/2
 proposals=[]
 for label,z,purpose in [('A_T_MINUS',zd+(zi-zd)/3,'one-third bridge, negative tangent contrast'),('A_T_PLUS',zd+2*(zi-zd)/3,'two-thirds bridge, positive tangent contrast'),('A_N_MINUS',mid-.05*normal,'transverse negative, center not evaluated'),('A_N_PLUS',mid+.05*normal,'transverse positive, center not evaluated')]:
  assert np.all((z>=0)&(z<=1))
  proposals.append({'design_id':label,'x':float(z[0]),'y':float(z[1]),'sigma_y_mpa':150*math.exp(float(z[0])*math.log(1000/150)),'n':.02+.48*float(z[1]),'purpose':purpose,'status':'FUTURE_DESIGN_ONLY_NOT_INP_OR_AUTHORIZATION'})
 local22=read(ROOT/'run/run_022/artifacts/private/analysis/sensitivity.json')
 findings={'version':'run049-offline-assessment-v1','at':now(),'common_contract_24_point_count':24,'common_numeric_contract':'run030-standard-m0025-hollomon-v1','loss_contract':'run017-exploratory-fd-v1',
  'excluded_unscoreable_ids':[v['point_id'] for v in initial['invalid']]+[v['candidate_id'] for v in pilot['rows'] if v['loss'] is None],
  'low_loss_sets':lowsets,'pairwise_low_loss_curves':pairs,'refined_two_points_separate_numeric_contract':'run043-standard-m00125-pending-v1',
  'refined_pair_fd':refined['refined_pair'],'refinement_not_pooled_as_additional_parameter_samples':True,'crossing_true_total_strain':crossing,
  'conditional_tensile_uniform_plastic_limit':p_limit,'peeq_scope':[{k:v for k,v in r.items() if k not in ['rows','fd_history']} for r in peeqscope],
  'source_confirmed_tensile_error_decomposition':tensile_diagnostics,'boundary':boundary,'future_parameter_design':{'midpoint_normalized':mid.tolist(),'tangent_unit':direction.tolist(),'normal_unit':normal.tolist(),'tangent_half_step':float(np.linalg.norm(zi-zd)/6),'normal_half_step':.05,'points':proposals,
  'prospective_check':'If authorized later, bridge values <=2*max(frozen refined endpoint Loss) is a descriptive continuity screen only; gaps remain and no global valley is proved',
  'prospective_descriptive_loss_limit':2*max(v['validation_loss'] for v in refined['points']),
  'derivative_rule':'S_t=(F_Tplus-F_Tminus)/(2*h_t); S_n=(F_Nplus-F_Nminus)/0.1; J_xy=[S_t,S_n]*[t,n]^T. No evaluated midpoint means no symmetric-curvature check.',
  'not_new_optimization_or_material_fit':True},'prior_run022_scope':'local center200MPa/.1, different/coarser increment contract; not transplanted to D01/I08 neighborhood','prior_run022_sensitivity':local22,
  'formal_tensile_validation':'NOT_EVALUABLE_UNCHANGED','continuous_valley_proven':False,'new_fe':0,'new_inp':0,'new_optimization_or_fit':False}
 save(P/'analysis.json',findings);save(P/'curve_provenance.json',provenance);save(P/'proposed_parameter_design.json',findings['future_parameter_design'])
 csvsave(P/'evaluated_24_points.csv',[{k:r[k] for k in ['candidate_id','sigma_y_mpa','n','x','y','loss','numerical_quality','runtime_s','cutback','numeric_version','loss_version']} for r in dataset])
 csvsave(P/'pairwise_low_loss_comparison.csv',pairs);csvsave(P/'source_confirmed_error_decomposition.csv',tensile_diagnostics)
 csvsave(P/'peeq_range_scope.csv',[{k:v for k,v in row.items() if k not in ['rows','fd_history']} for row in peeqscope])
 # Actual points only: no interpolated Loss contour or off-grid FE prediction.
 fig,ax=plt.subplots(1,3,figsize=(16,4.8),layout='constrained')
 sc=ax[0].scatter([r['x'] for r in dataset],[r['y'] for r in dataset],c=np.log10([r['loss'] for r in dataset]),cmap='viridis',s=55,edgecolors='black')
 fig.colorbar(sc,ax=ax[0],label='log10(actual frozen Loss)');ax[0].set(xlabel='x = log-normalized sigma_y',ylabel='y = normalized n',title='24 actual comparable FE points',xlim=(-.02,1.02),ylim=(-.02,1.02))
 for r in low:ax[1].scatter(r['x'],r['y'],s=55,color='tab:blue');ax[1].annotate(r['candidate_id'],(r['x'],r['y']),xytext=(4,4),textcoords='offset points',fontsize=8)
 for r in proposals:ax[1].scatter(r['x'],r['y'],marker='x',s=65,color='red')
 ax[1].plot([zd[0],zi[0]],[zd[1],zi[1]],'--',color='gray',lw=1,label='Uncomputed bridge, not FE evidence')
 ax[1].set(xlabel='x',ylabel='y',title='Low-Loss samples and proposed diagnostics');ax[1].legend(fontsize=7)
 ax[2].plot(u*1000,exp,'k',lw=2,label='SPT experiment')
 for pid,col in [('D01','tab:blue'),('I08','tab:orange')]:ax[2].plot(u*1000,curves[pid],'--',color=col,label=pid+' m0025');ax[2].plot(u*1000,refined_curves[pid],color=col,label=pid+' m00125')
 ax[2].set(xlabel='Punch displacement (mm)',ylabel='Force (N)',title='Competing curves, contracts labeled');ax[2].legend(fontsize=7)
 fig.savefig(P/'parameter_compensation_evidence.png',dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
 for record in peeqscope:
  hh=record['fd_history'];pp=record['rows'];x=[float(hh[int(v['frame_index'])]['displacement_m'])*1000 for v in pp]
  ax.plot(x,[float(v['max_peeq']) for v in pp],label=record['candidate_id']+' refined: saved frame max')
 ax.axhline(p_limit,color='red',ls='--',label='Source-confirmed tensile p limit (conditional mapping)')
 ax.set(xlabel='Punch displacement (mm)',ylabel='Maximum saved PEEQ',title='Hardening-range demand, not volume-weighted strain or validation');ax.legend(fontsize=8);ax.grid(alpha=.2)
 fig.savefig(P/'hardening_range_demand.png',dpi=170);plt.close(fig)
 after={rel(p):sha(p) for p in guards};assert before==after;save(P/'protected_after_analysis.json',after)
 print(json.dumps({'common_FE':24,'lowsets':lowsets,'crossing_true_strain':crossing,'peeq_scope':findings['peeq_scope'],'tensile_decomposition':tensile_diagnostics,'BC':boundary,'design':proposals},ensure_ascii=False))
if __name__=='__main__':main()
