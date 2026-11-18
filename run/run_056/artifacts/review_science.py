"""Read-only review of source evidence and numerical admissibility; no Solver API."""
from pathlib import Path
from collections import Counter
import json,csv,hashlib,re,sys
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_056/artifacts/private';sys.path.insert(0,str(R/'run/run_055/artifacts'))
from feature_core import GRID,physical_to_normalized
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 keys=list(dict.fromkeys(k for row in rs for k in row))
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)
SOURCES={}
def source(path,expected=None):
 if path not in SOURCES:
  h=hashlib.sha256();p=R/path
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  SOURCES[path]={'path':path,'sha256':h.hexdigest(),'bytes':p.stat().st_size}
 if expected:assert SOURCES[path]['sha256']==expected,path
 return R/path
def parse_trials(files):
 sta=(R/files['sta']['path']).read_text(encoding='utf-8',errors='replace').splitlines();trials=[]
 for i,line in enumerate(sta,1):
  f=line.split()
  if len(f)>=9 and f[0].isdigit() and f[1].isdigit() and re.fullmatch(r'\d+U?',f[2]):trials.append({'line':i,'increment':int(f[1]),'attempt':int(f[2].rstrip('U')),'accepted':not f[2].endswith('U'),'time':float(f[7]),'dt':float(f[8]),'equilibrium_iterations':int(f[4])})
 outcome={(x['increment'],x['attempt']):x['accepted'] for x in trials};ev=[];current=None
 for i,line in enumerate((R/files['msg']['path']).read_text(encoding='utf-8',errors='replace').splitlines(),1):
  m=re.search(r'INCREMENT\s+(\d+)\s+STARTS\.\s+ATTEMPT NUMBER\s+(\d+)',line,re.I)
  if m:current=tuple(map(int,m.groups()))
  u=line.upper()
  if '***WARNING' not in u and '***ERROR' not in u:continue
  kind='ERROR' if '***ERROR' in u else 'NEGATIVE_EIGENVALUES' if 'NEGATIVE EIGENVALUES' in u else 'EXCESSIVE_DISTORTION' if 'EXCESSIVE DISTORTION' in u else 'LARGE_STRAIN_INCREMENT' if 'STRAIN INCREMENT HAS EXCEEDED' in u else 'PLASTICITY_NOT_ATTEMPTED' if 'STRAIN INCREMENT IS SO LARGE' in u else 'ZERO_MOMENT' if 'ZERO MOMENT' in u else 'CONTACT_WARNING' if 'CONTACT' in u else 'OTHER_WARNING';accepted=outcome.get(current)
  ev.append({'line':i,'increment':current[0] if current else None,'attempt':current[1] if current else None,'outcome':'ACCEPTED_TRIAL' if accepted is True else 'REJECTED_TRIAL' if accepted is False else 'UNKNOWN','class':kind,'text':line.strip()})
 good=[x for x in trials if x['accepted']];bad=[x for x in trials if not x['accepted']]
 assert good[-1]['time']==1 and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in '\n'.join(sta)
 return {'accepted_increments':len(good),'rejected_attempts':len(bad),'cutback_count':len({x['increment'] for x in bad}),'warning_counts':{o:dict(Counter(x['class'] for x in ev if x['outcome']==o)) for o in ['ACCEPTED_TRIAL','REJECTED_TRIAL','UNKNOWN']},'events':ev,'warning_scope':'inside a trial ultimately accepted, not proof the warning describes final converged physical state'}
def main():
 em=read(source('run/run_055/artifacts/private/evidence_manifest.json'));assert len(em['files'])>=40
 for f in em['files']:source(f['path'],f['sha256'])
 published=read(source('run/run_055/artifacts/manifest.json'))
 for f in published['files']:source(f['path'],f['sha256'])
 inv=read(source('run/run_055/artifacts/private/sample_inventory.json'));cv=rows(source('run/run_055/artifacts/private/inverse_cv_results.csv'));folds=read(source('run/run_055/artifacts/private/outer_fold_details.json'));cvmeta=read(source('run/run_055/artifacts/private/cv_protocol_identity.json'));models=read(source('run/run_055/artifacts/private/frozen_FE_only_inverse_models.json'));comp=read(source('run/run_055/artifacts/private/cv_completion.json'))
 assert len(inv['primary_ids'])==25 and len(cv)==250 and len(set(x['sample_id'] for x in cv))==25
 assert len(inv['historical24_ids'])==24 and len(inv['historical_null6_ids'])==6 and not set(inv['historical24_ids'])&set(inv['historical_null6_ids'])
 assert source('run/run_055/artifacts/private/frozen_FE_only_inverse_models.json',comp['frozen_model_sha256']) and source('run/run_055/artifacts/private/inverse_cv_results.csv',comp['inverse_cv_sha256'])
 for x in folds:assert x['test_parameter_group'] not in x['train_parameter_groups'] and set(x['train_parameter_groups'])==set(inv['primary_ids'])-{x['test_parameter_group']}
 assert not {'H01','H02','D01_REFINED','I08_REFINED'}&set(models['training_ids']) and set(models['training_ids'])==set(inv['primary_ids'])
 # Recompute primary reporting metrics, not model fitting.
 metrics=[]
 for name in ['two_ridge','five_ridge','full_ridge']:
  rs=[r for r in cv if r['model']==name];sy=np.array([float(r['sigma_error_MPa']) for r in rs]);ne=np.array([float(r['n_error']) for r in rs]);metrics.append({'model':name,'sigma_MAE_MPa':float(np.mean(abs(sy))),'sigma_RMSE_MPa':float(np.sqrt(np.mean(sy**2))),'n_MAE':float(np.mean(abs(ne))),'n_RMSE':float(np.sqrt(np.mean(ne**2)))})
 old=read(source('run/run_039/artifacts/private/main/main_review.json'));pilot=read(source('run/run_042/artifacts/private/main/main_analysis.json'));parent=old['rows']+pilot['rows'];audits=[]
 for pid in ['D07','D09','D10','BO01','BO02','DE02','I06']:
  row=next(x for x in parent if x.get('point_id',x.get('candidate_id'))==pid);result=read(source(row['result_path'],row.get('result_sha256')));diagpath=result.get('diagnostics_path') or next(x for x in result['artifact_hashes'] if x.endswith('/diagnostics.json'));diag=read(source(diagpath,result['artifact_hashes'].get(diagpath)));prov=diag['provenance'];files=prov['source_files']
  for k,x in files.items():source(x['path'],x['sha256'])
  ip=prov.get('inp',{});inppath=ip.get('path',diag.get('inp_path'));inpsha=ip.get('sha256',diag.get('inp_sha256'));source(inppath,inpsha);assert inpsha==result['inp_sha256'] and files['odb']['sha256']==result['odb_sha256']
  fdpath=result['positive_fd_csv'];fd=rows(source(fdpath,result['artifact_hashes'][fdpath]));u=np.array([float(x['displacement_m']) for x in fd]);force=np.array([float(x['force_n']) for x in fd]);delta=np.diff(force);neg=[{'index':i+1,'u_start_mm':float(u[i]*1000),'u_end_mm':float(u[i+1]*1000),'delta_force_N':float(v)} for i,v in enumerate(delta) if v<0];trials=parse_trials(files)
  assert u[0]<=0 and u[-1]>=.0012 and np.all(np.diff(u)>0);assert result['datacheck_status']['return_code']==result['full_status']['return_code']==0
  assert result['full_status']['odb_job_status']=='JOB_STATUS_COMPLETED_SUCCESSFULLY'
  record={'sample_id':pid,'sigma_y_mpa':row['sigma_y_mpa'],'n':row['n'],'job_name':result['job_name'],'queue_id':result['queue_id'],'result_path':row['result_path'],'diagnostics_path':diagpath,'inp_path':inppath,'inp_sha256':inpsha,'odb_path':files['odb']['path'],'odb_sha256':files['odb']['sha256'],'fd_path':fdpath,'software_state':result['full_status']['phase'],'datacheck_success':True,'full_success':True,'complete_window':True,'raw_points':len(fd),'max_saved_peeq':result['max_saved_peeq'],'material_table_max':result['material_table_max_plastic_strain'],'recorded_loss':row['loss'],'frozen_blockers':result['numerical_blocking_issues'],'warning_counts':trials['warning_counts'],'accepted_increments':trials['accepted_increments'],'rejected_attempts':trials['rejected_attempts'],'cutbacks':trials['cutback_count'],'negative_force_steps':neg,'min_force_step_N':float(delta.min()),'negative_force_count':len(neg),'severe_accepted_warning_count':sum(v for k,v in trials['warning_counts']['ACCEPTED_TRIAL'].items() if k not in ['ZERO_MOMENT']),'history_process_gap_retained':'HISTORICAL_RUNNER_PROCESS_EVIDENCE_UNCONFIRMED' in result['numerical_review_warnings'],'classification':'COMPLETED_BUT_FROZEN_NUMERICAL_SCORE_GATE_UNMET' if pid!='I06' else 'ELIGIBLE_EXPLORATORY_LOCAL_ANCHOR_WITH_WARNINGS','cause_not_established':'association with low n does not prove n causes Solver failure or unique instability mechanism','source_attempt':row.get('source_attempt','original'),'not_incomplete_or_window_failure':True,'material_upper_bound_not_exceeded':result['max_saved_peeq']<.9}
  audits.append(record);save(P/(pid+'_raw_event_review.json'),{'summary':record,'events':trials['events']})
 base=next(x for x in audits if x['sample_id']=='I06');assert not base['frozen_blockers'] and not base['severe_accepted_warning_count'] and base['negative_force_count']==0 and base['max_saved_peeq']<.85
 # Revalidate exact I06 manifest and numerical controls.
 manifest=read(source('run/run_030/artifacts/prepared_batch.json'));point=next(x for x in manifest['points'] if x['point_id']=='I06');assert point['sigma_y_mpa']==base['sigma_y_mpa'] and point['n']==base['n'] and point['inp_sha256']==base['inp_sha256']
 text=(R/base['inp_path']).read_text(encoding='utf-8-sig');s=re.search(r'(?im)^\*Static[^\n]*\n([^*\n]+)',text);static=[float(x) for x in s[1].split(',')];assert static==[.001,1.,1e-12,.0025] and re.search(r'(?i)\*Step[^\n]*inc=999999',text)
 params=read(source(point['parameters_path'],point['parameters_sha256']));assert (params['E_pa'],params['nu'],params['max_plastic_strain'])==(210e9,.3,.9)
 base.update(initial_increment=.001,maximum_increment=.0025,minimum_increment=1e-12,step_time=1.,maximum_increments=999999,E_pa=210e9,nu=.3,plastic_table_coverage=[0,.9],params_path=point['parameters_path'],params_sha256=point['parameters_sha256'],baseline_scope='same-model exploratory anchor; NOT independently time-step-converged or physical validation',if_strict_numerical_reference_required='I06_NOT_QUALIFIED_AS_NUMERICAL_ERROR_BOUND; alternative D01/I08 already point-refined, requires different-center/control redesign, no automatic substitution')
 arr=read(source('run/run_055/artifacts/private/feature_arrays.json'));ids=arr['primary_ids'];physical=np.array([arr['targets'][x] for x in ids]);xy=physical_to_normalized(physical);edges=np.linspace(0,1,5);counts=np.histogram2d(xy[:,0],xy[:,1],bins=(edges,edges))[0].astype(int)
 coverage={'25_unique_ids':ids,'sigma_min_max_MPa':[float(physical[:,0].min()),float(physical[:,0].max())],'n_min_max':[float(physical[:,1].min()),float(physical[:,1].max())],'original_bounds':{'sigma_MPa':[150,1000],'n':[.02,.50]},'normalized_grid_edges':edges.tolist(),'four_by_four_counts_x_then_y':counts.tolist(),'empty_bins':int(np.sum(counts==0)),'missing_lower_n':'no successful comparable point n<.08; all6frozen-null points n<.043; this is numerically filtered nonrandom data','missing_high_sigma':'no point sigma>817.023544MPa although planned bound1000','not_global_validation':'25designed/adaptively acquired samples and local duplicates do not certify arbitrary parameter regions'}
 save(P/'run055_recheck.json',{'historical24_plus6_verified':True,'primary25_verified':True,'H_and_repeats_excluded':True,'fold_membership_checked':25,'nested_transforms_rule_verified_by_source_hash':True,'metrics_independently_recomputed':metrics,'coverage':coverage,'formal_material_formula':'PARTIAL_NOT_VALIDATED'})
 save(P/'low_n_and_I06_audit.json',{'records':audits,'all6readable_representatives_software_completed':True,'null_meaning':'scientific numerical-admission gate, not proof of Solver failure','D09_original':'prior run033 record UNKNOWN_INTERRUPTED; final run038 replacement completed but null; no new retry authorised','low_n_causal_inference':'NOT_ESTABLISHED','I06':base})
 csvsave(P/'six_null_mechanisms.csv',[{k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in x.items()} for x in audits if x['sample_id']!='I06']);save(P/'source_manifest.json',{'sources':list(SOURCES.values())})
 print(json.dumps({'six_null_software_completed':6,'I06':{k:base[k] for k in ['classification','cutbacks','accepted_increments','max_saved_peeq','negative_force_count','severe_accepted_warning_count']},'coverage_bins':counts.tolist(),'low_n_negative_steps':{r['sample_id']:{'count':r['negative_force_count'],'min_N':r['min_force_step_N'],'accepted_severe':r['severe_accepted_warning_count']} for r in audits if r['sample_id']!='I06'},'verified_sources':len(SOURCES)}))
if __name__=='__main__':main()
