"""Independent frozen two-refinement comparison; consumes real ODB Agent CSVs only."""
import csv,json,hashlib,sys,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_045';OUT=RUN/'artifacts/private/main'
sys.path[:0]=[str(ROOT),str(ROOT/'run/run_023/artifacts'),str(ROOT/'run/run_043/artifacts')]
from inverse.fd_loss import Curve,Target,interpolate
from inverse.hollomon import stress_from_total_strain
from compare_validation import compare
from ranking_screen import screen
from agenthub_sp_invopt.hub import Hub

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def curve(p):
 r=rows(p);return Curve(tuple(float(v['displacement_m']) for v in r),tuple(float(v['force_n']) for v in r),'m','N')
def write_csv(p,r):
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)

def main():
 OUT.mkdir(exist_ok=True,parents=True)
 ids=read(RUN/'artifacts/task_ids.json');hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3')
 assert hub.task(ids['odb_task_id'])['execution_state'] in ('CLAIMED','COMPLETED') and hub.verify_chain() # frozen files can be independently reviewed before formal role finish; finalizer requires COMPLETED
 manifest=read(RUN/'artifacts/private/odb/manifest.json')
 for item in manifest['files']:assert sha(ROOT/item['path'])==item['sha256']
 frozen=read(ROOT/'run/run_043/artifacts/prepared_batch.json');cc=read(ROOT/frozen['comparison_contract_path'])
 assert sha(ROOT/frozen['comparison_contract_path'])==frozen['comparison_contract_sha256']
 for k in ['comparison_implementation','ranking_implementation','comparison_tests','ranking_tests']:
  assert sha(ROOT/cc[k+'_path'])==cc[k+'_sha256']
 binding=read(ROOT/'run/run_030/artifacts/loss_contract_binding.json')
 assert sha(ROOT/'run/run_030/artifacts/loss_contract_binding.json')==cc['loss_binding_sha256']
 for k in ['target','implementation','config']:assert sha(ROOT/binding[k+'_path'])==binding[k+'_sha256']
 tr=rows(ROOT/cc['target_path'])[:241];u=np.array(cc['grid_m']);exp=np.array([float(r['force_n']) for r in tr]);ref=cc['force_reference_n']
 assert tuple(float(r['displacement_m']) for r in tr)==tuple(u)
 target=Target(Curve(tuple(u),tuple(exp),'m','N'),tuple([1.]*241),ref,cc['loss_version'])
 audit=read(RUN/'artifacts/private/execution_audit.json');records={r['point_id']:r for r in audit['records']}
 summaries=[];curves={};allgrid=[];intervals=[];provenance=[]
 for p in frozen['points']:
  pid=p['point_id'];od=RUN/'artifacts/private/odb'/pid;result=read(od/'result.json');base=read(ROOT/p['baseline_result_path']);record=records[pid]
  assert result['queue_id']==record['queue_id'] and result['job_name']==p['job_name']
  assert result['inp_sha256']==p['inp_sha256']==sha(ROOT/p['inp_path'])
  assert result['odb_sha256']==record['files']['odb']['sha256']==sha(ROOT/p['expected_odb'])
  assert sha(ROOT/p['baseline_fd_path'])==p['baseline_fd_sha256'] and sha(ROOT/p['baseline_result_path'])==p['baseline_result_sha256']
  assert sha(ROOT/p['baseline_odb_path'])==p['baseline_odb_sha256']
  old=(ROOT/p['source_inp']).read_bytes();new=(ROOT/p['inp_path']).read_bytes()
  assert new==old.replace(b'0.001, 1., 1e-12, 0.0025',b'0.001, 1., 1e-12, 0.00125',1)
  for path,digest in result.get('artifact_hashes',{}).items():assert sha(ROOT/path)==digest
  rawhistory=rows(od/'raw_history.csv');fdrows=rows(od/'force_displacement.csv')
  assert len(rawhistory)==len(fdrows)
  for raw,fd in zip(rawhistory,fdrows):
   assert float(fd['displacement_m'])==-float(raw['U2_raw_m']) and float(fd['force_n'])==-float(raw['RF2_raw_n'])
   assert raw['increment']==fd['increment'] and float(raw['step_time'])==float(fd['step_time'])
  diagnostic=read(od/'diagnostics.json')
  assert all(diagnostic['identity_checks'].values())
  original=curve(ROOT/p['baseline_fd_path']);refined=curve(od/'force_displacement.csv')
  metric=compare(target,original,refined,cc,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
  a=np.array(interpolate(original,u));b=np.array(interpolate(refined,u));delta=b-a;res=b-exp
  independent_loss=math.fsum((float(v)/ref)**2 for v in res)/241
  assert abs(independent_loss-metric['validation_loss'])<1e-14
  if result.get('loss_or_null') is not None:assert abs(result['loss_or_null']-independent_loss)<1e-12
  peeq=result['max_saved_peeq'];basepeeq=base['max_saved_peeq'];metric['max_saved_peeq_absolute_change']=abs(peeq-basepeeq)
  metric['checks']['max_saved_peeq']=abs(peeq-basepeeq)<=cc['thresholds']['max_saved_peeq_absolute_change']
  blockers=result.get('numerical_blocking_issues',[])
  gates=all(metric['checks'].values());coverage=peeq<=result['material_table_max_plastic_strain']
  qualification='PASS' if gates and coverage and not blockers and record['safe_for_readonly_odb'] else 'BLOCKED'
  summary={**metric,'point_id':pid,'job_name':p['job_name'],'queue_id':record['queue_id'],'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],
    'qualification':qualification,'max_saved_peeq':peeq,'baseline_max_saved_peeq':basepeeq,'material_coverage':coverage,
    'numerical_blockers':blockers,'numeric_warnings':result.get('numerical_review_warnings',[]),
    'cutback':result.get('rejected_attempts'),'accepted_increments':result.get('accepted_increments'),'actual_runtime_s':record['actual_runtime_s'],
    'refined_rmse_to_experiment_n':float(np.sqrt(np.mean(res**2))),'refined_bias_n':float(np.mean(res)),
    'warnings_by_outcome':result.get('warning_events_by_accepted_or_rejected'),
    'contact_review':result.get('contact_transition_review'),'local_jump_review':result.get('local_fd_jump_review')}
  focus=read(od/'focus_1p10_to_1p16mm.json');node_summary={}
  for label in [22,23,24,230]:
   values=[next((v for v in fr['contact']['topology_node_values'] if v['node_label']==label),{}) for fr in focus['frames']]
   cp=[v['cpress'] for v in values if v.get('cpress') is not None];op=[v['copen_valid'] for v in values if v.get('copen_valid') is not None]
   first=next((fr['displacement_mm'] for fr,v in zip(focus['frames'],values) if v.get('cpress') is not None and v['cpress']>0),None)
   node_summary[str(label)]={'cpress_range_pa':[min(cp),max(cp)] if cp else None,'copen_valid_range_m':[min(op),max(op)] if op else None,
    'copen_valid_count':len(op),'copen_sentinel_count':sum(v.get('copen_sentinel',False) for v in values),'first_positive_saved_mm_in_window':first}
  summary['focus_summary']={'window_mm':focus['window_mm'],'frames':focus['frame_count'],'max_abs_step':focus['max_abs_step'],
    'negative_force_steps':focus['negative_force_steps'],'node_values':node_summary,'interpretation':'Saved values only; CPRESS positive proxy, COPEN sentinel missing; no unique causal attribution'}
  summaries.append(summary);curves[pid]=(a,b)
  for j in range(241):allgrid.append({'point_id':pid,'displacement_m':float(u[j]),'experiment_force_n':float(exp[j]),'original_force_n':float(a[j]),'refined_force_n':float(b[j]),'refined_minus_original_n':float(delta[j]),'refined_residual_n':float(res[j])})
  for k,(lo,hi) in enumerate([(0,.0003),(.0003,.0006),(.0006,.0009),(.0009,.0012)]):
   mask=(u>=lo-1e-15)&((u<hi-1e-15) if k<3 else (u<=hi+1e-15))
   intervals.append({'point_id':pid,'lo_mm':lo*1000,'hi_mm':hi*1000,'count':int(mask.sum()),'refinement_rmse_n':float(np.sqrt(np.mean(delta[mask]**2))),
    'refined_residual_rmse_n':float(np.sqrt(np.mean(res[mask]**2))),'refined_bias_n':float(np.mean(res[mask])),
    'loss_contribution':float(np.sum((res[mask]/ref)**2)/241),'loss_fraction':float(np.sum(res[mask]**2)/np.sum(res**2))})
  provenance.append({'point_id':pid,'result_path':str((od/'result.json').relative_to(ROOT)),'result_sha256':sha(od/'result.json'),
    'fd_path':str((od/'force_displacement.csv').relative_to(ROOT)),'fd_sha256':sha(od/'force_displacement.csv'),'input_sha256':p['inp_sha256'],'odb_sha256':result['odb_sha256']})
 rank=screen(summaries[0]['original_loss'],summaries[1]['original_loss'],summaries[0]['validation_loss'],summaries[1]['validation_loss'])
 mutual=curves['I08'][1]-curves['D01'][1]
 pair={'refined_mutual_fd_rmse_n':float(np.sqrt(np.mean(mutual**2))),'refined_max_abs_difference_n':float(np.max(np.abs(mutual))),
       'max_abs_at_mm':float(u[np.argmax(np.abs(mutual))]*1000)}
 assert sha(ROOT/'inverse/hollomon.py')=='d937664f7fc7f845a9ed7a75a004275bf38d11a1b3f68975a05961adb9b16363'
 pred=[]
 for e in [0,.001,.002,.01,.1,.4]:
  stress=[stress_from_total_strain(e,p['sigma_y_mpa'],p['n'])/1e6 for p in frozen['points']]
  pred.append({'true_total_strain':e,'D01_mpa':stress[0],'I08_mpa':stress[1],'difference_mpa':stress[1]-stress[0]})
 result={'version':'run045-main-independent-refinement-v1','comparison_contract_sha256':frozen['comparison_contract_sha256'],
  'points':summaries,'ranking':rank,'refined_pair':pair,'residual_intervals':intervals,'predicted_constitutive_samples':pred,'provenance':provenance,
  'scope':'Pointwise adjacent increment qualification only. Two competing observed candidates; no global uniqueness, mesh convergence, physical validation or strict numerical error bounds.'}
 result['observed_refinement_signal_ratio']=(summaries[0]['force_rmse_n']+summaries[1]['force_rmse_n'])/pair['refined_mutual_fd_rmse_n']
 save(OUT/'candidate_constitutive_set.json',{'version':'run045-exploratory-two-candidate-set-v1','status':'EXPLORATORY_SET_NOT_UNIQUE_FINAL_LAW',
  'law':'candidate true-total Hollomon','E_pa':210e9,'nu':.3,'generator_path':'inverse/hollomon.py','generator_sha256':sha(ROOT/'inverse/hollomon.py'),
  'loss_version':cc['loss_version'],'numeric_version':cc['numeric_candidate'],'unblind_authorized':False,
  'candidates':[{'point_id':s['point_id'],'sigma_y_mpa':s['sigma_y_mpa'],'n':s['n'],'refined_loss':s['validation_loss'],'qualification':s['qualification'],'inp_sha256':p['inp_sha256'],'baseline_numeric_contract':cc['numeric_source']} for s,p in zip(summaries,frozen['points'])],
  'limitations':['No unique law or strict confidence interval established','D01 near retained lower boundary','Only two pointwise refinements','Historical holdout exposure retained; sealed validation not accessed']})
 save(OUT/'analysis.json',result);write_csv(OUT/'frozen_grid_comparison.csv',allgrid);write_csv(OUT/'residual_intervals.csv',intervals);write_csv(OUT/'predicted_constitutive_samples.csv',pred)
 fig,ax=plt.subplots(3,1,figsize=(10,10),sharex=True,layout='constrained')
 ax[0].plot(u*1000,exp,'k',lw=2,label='SPT experiment')
 for pid,(a,b) in curves.items():
  color={'D01':'tab:blue','I08':'tab:orange'}[pid]
  ax[0].plot(u*1000,a,'--',color=color,alpha=.6,label=pid+' original');ax[0].plot(u*1000,b,color=color,label=pid+' refined')
  ax[1].plot(u*1000,b-a,color=color,label=pid);ax[2].plot(u*1000,b-exp,color=color,label=pid)
 for aa in ax:aa.legend();aa.grid(alpha=.2)
 ax[0].set(ylabel='Force (N)',title='Real FE and frozen experiment; no smoothing/shift')
 ax[1].set(ylabel='Refined - original (N)');ax[2].set(xlabel='Punch displacement (mm)',ylabel='FE - experiment (N)')
 fig.savefig(OUT/'fd_refinement_residuals.png',dpi=170);plt.close(fig)
 fig,ax=plt.subplots(1,3,figsize=(15,4),layout='constrained')
 for a,limit in zip(ax,[.003,.2,.66]):
  ee=np.linspace(0,limit,1001)
  for p in frozen['points']:a.plot(ee,[stress_from_total_strain(float(e),p['sigma_y_mpa'],p['n'])/1e6 for e in ee],label=p['point_id'])
  a.set(xlabel='Predicted true total strain',ylabel='Predicted true stress (MPa)');a.legend()
 fig.suptitle('Unchanged SPT-derived candidate laws; no tensile validation used')
 fig.savefig(OUT/'predicted_constitutive_curves.png',dpi=170);plt.close(fig)
 print(json.dumps({'points':[{k:s[k] for k in ['point_id','qualification','force_rmse_n','max_absolute_force_n','max_regularized_relative','loss_change','max_saved_peeq_absolute_change','validation_loss']} for s in summaries],'ranking':rank,'pair':pair}))
if __name__=='__main__':main()
