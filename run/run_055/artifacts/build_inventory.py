"""Bounded audit of actual existing results; never imports a Solver or optimizer."""
from pathlib import Path
import json,csv,hashlib,re,sys
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_055/artifacts/private';sys.path.insert(0,str(R))
from feature_core import extract,NAMES,GRID,physical_to_normalized
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
 p=R/path
 if path not in SOURCES:
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  SOURCES[path]={'path':path,'sha256':h.hexdigest(),'bytes':p.stat().st_size}
 if expected is not None:assert SOURCES[path]['sha256']==expected,(path,'HASH_MISMATCH')
 return p
def controls(path):
 ls=path.read_text(encoding='utf-8-sig').splitlines();static=[];keep=[];plastic=False
 for i,l in enumerate(ls):
  t=l.strip()
  if t.lower().startswith('*static'):static=[float(x) for x in ls[i+1].split(',')]
  if t.startswith('*') and not t.startswith('**'):
   plastic=t.lower().startswith('*plastic')
   if plastic:keep.append('*Plastic');continue
  if plastic:continue
  if i>0 and ls[i-1].strip().lower().startswith('*static'):keep.append('<STATIC_NUMERICAL_FIELDS>');continue
  if t and not t.startswith('**'):keep.append(t)
 assert len(static)==4
 return {'initial_increment':static[0],'step_time':static[1],'minimum_increment':static[2],'maximum_increment':static[3],'physical_skeleton_sha256':hashlib.sha256('\n'.join(keep).encode()).hexdigest()}
def curve(path):
 v=rows(path);uk='displacement_m' if 'displacement_m' in v[0] else 'displacement_model_length';fk='force_n' if 'force_n' in v[0] else 'force_model_force'
 return np.array([float(x[uk]) for x in v]),np.array([float(x[fk]) for x in v])
def result_record(pid,sy,n,path,loss,quality,fd_override=None,fd_sha=None,material='standard_Hollomon',inp_fallback=None):
 result=read(source(path));arts=result.get('artifact_hashes',{});fd=fd_override or result.get('positive_fd_csv',result.get('curve_path'))
 assert fd;source(fd,fd_sha or arts.get(fd))
 diagpath=result.get('diagnostics_path')
 if not diagpath:
  found=[k for k in arts if k.endswith('/diagnostics.json')];assert len(found)==1,(pid,'diag identity unavailable');diagpath=found[0]
 diag=read(source(diagpath,arts.get(diagpath)));prov=diag['provenance'];ip=prov.get('inp',{})
 inppath=ip.get('path',diag.get('inp_path',inp_fallback));inphash=ip.get('sha256',diag.get('inp_sha256',result.get('inp_sha256')))
 assert inppath;inp=source(inppath,inphash);co=controls(inp)
 pp=prov.get('parameters',{});parampath=pp.get('path',diag.get('parameters_path'));paramhash=pp.get('sha256',diag.get('parameters_sha256'))
 if parampath:
  params=read(source(parampath,paramhash))
  if 'inp_sha256' in params:assert params['inp_sha256']==inphash
  if 'sigma_y_mpa' in params:assert abs(params['sigma_y_mpa']-float(sy))<1e-8
  if 'n' in params:assert abs(params['n']-float(n))<1e-12
 files=prov['source_files']
 for kind,f in files.items():source(f['path'],f['sha256'])
 assert result.get('odb_sha256',files['odb']['sha256'])==files['odb']['sha256']
 if result.get('inp_sha256'):assert result['inp_sha256']==inphash
 rp=result.get('punch_rp_identity',diag.get('rp',{}));assert rp.get('node_label',1)==1 and rp.get('instance','ASM_SPT')=='ASM_SPT';assert 'ASM_SPT.1' in rp.get('region','Node ASM_SPT.1')
 u,f=curve(R/fd);features,grid,fd_diag=extract(u,f)
 rawpath=result.get('raw_u2_rf2_step_time_csv',result.get('raw_history_path'))
 if rawpath:
  source(rawpath,arts.get(rawpath));raw=rows(R/rawpath)
  uf=next((k for k in raw[0] if k in ['U2_raw_m','U2','u2']),None);rf=next((k for k in raw[0] if k in ['RF2_raw_n','RF2','rf2']),None)
  if uf and rf:
   assert len(raw)==len(u) and np.allclose(u,[-float(x[uf]) for x in raw],rtol=0,atol=1e-15) and np.allclose(f,[-float(x[rf]) for x in raw],rtol=0,atol=1e-9)
 # Exact metadata checks retain independent prior extraction's material/field-history checks.
 ex=diag.get('execution',{});status=ex.get('phase',ex.get('software_state','COMPLETED_WITH_WARNINGS'));maxpe=result.get('max_saved_peeq',result.get('max_peeq',diag.get('peeq',{}).get('saved_frame_max')))
 rec={'sample_id':pid,'sigma_y_mpa':float(sy),'n':float(n),'material_type':material,'job_name':result['job_name'],'queue_id':result['queue_id'],'inp_path':inppath,'inp_sha256':SOURCES[inppath]['sha256'],'odb_path':files['odb']['path'],'odb_sha256':files['odb']['sha256'],'result_path':path,'result_sha256':SOURCES[path]['sha256'],'fd_path':fd,'fd_sha256':SOURCES[fd]['sha256'],'raw_points':len(u),'full_window':True,'solver_status':status,'loss':loss,'loss_version':'run017-exploratory-fd-v1','quality':quality,'max_saved_peeq':maxpe,'cutback':result.get('cutback_increments',ex.get('increments_with_cutback',ex.get('rejected_attempts'))),'numerical_warnings':json.dumps(result.get('numerical_review_warnings',diag.get('warnings',{})),ensure_ascii=False),'rp_sign':'Node ASM_SPT.1;u=-U2,F=-RF2;m/N;no2pi','numerical_contract':'run030-standard-m0025-hollomon-v1' if co['maximum_increment']==.0025 and co['initial_increment']==.001 else 'different_controls','exclusion_reason':'','included_primary':False,**co}
 return rec,features,grid,fd_diag
def main():
 protocol=source('run/run_055/artifacts/private/feature_protocol.md');old=read(source('run/run_039/artifacts/private/main/main_review.json'));pilot=read(source('run/run_042/artifacts/private/main/main_analysis.json'));table=rows(source('run/run_049/artifacts/private/evaluated_24_points.csv'));excluded=read(source('run/run_049/artifacts/private/numerically_unscoreable_observations.json'));pr=read(source('run/run_049/artifacts/private/curve_provenance.json'))
 base=old['rows']+pilot['rows'];valid=[r for r in base if r['loss'] is not None];null=[r for r in base if r['loss'] is None]
 idof=lambda r:r.get('point_id',r.get('candidate_id'))
 assert len(base)==30 and len(valid)==24 and len(null)==6 and {idof(r) for r in valid}=={r['candidate_id'] for r in table}
 assert {idof(r) for r in null}=={r['candidate_id'] for r in excluded}=={'D07','D09','D10','BO01','BO02','DE02'}
 provenance={r['candidate_id']:r for r in pr};recs=[];data={};diagnostics={};frozen={}
 for row in base:
  pid=idof(row);rp=row['result_path'];source(rp,row['result_sha256']);frozen[pid]=row['loss'];pv=provenance.get(pid)
  rec,fe,g,d=result_record(pid,row['sigma_y_mpa'],row['n'],rp,row['loss'],row.get('numerical_quality',row.get('quality','NUMERICAL_WARNING')),fd_override=pv['fd_path'] if pv else None,fd_sha=pv['fd_sha256'] if pv else None)
  if 'inp_sha256' in row:assert rec['inp_sha256']==row['inp_sha256']
  if 'odb_sha256' in row:assert rec['odb_sha256']==row['odb_sha256']
  rec['in_historical_30']=True;rec['region']=row.get('region',row.get('algorithm'));rec['exclusion_reason']='NULL_LOSS_NUMERICAL_BLOCKER' if row['loss'] is None else ''
  if row['loss'] is None:rec['quality']='EXCLUDED_UNSCOREABLE';rec['blocking_issues']=json.dumps(row.get('blocking_issues',[]))
  recs.append(rec);data[pid]=(fe,g);diagnostics[pid]=d
 # Add the previously validated, matching-control center, not another DOE attempt.
 center=read(source('run/run_029/artifacts/private/odb/result.json'));review=read(source('run/run_029/artifacts/private/main_review.json'));man=read(source('run/run_029/artifacts/private/odb/manifest.json'));m={x['path']:x['sha256'] for x in man['files']}
 centerloss=review['loss']['candidate']
 rec,fe,g,d=result_record('C200',200.,.1,'run/run_029/artifacts/private/odb/result.json',centerloss,'POINT_ADJACENT_INCREMENT_PASS_WITH_WARNINGS',fd_override=center['curve_path'],fd_sha=m[center['curve_path']]);assert co_match(rec)
 rec['in_historical_30']=False;rec['region']='PREVIOUS_CENTER';recs.append(rec);data['C200']=(fe,g);diagnostics['C200']=d
 # Existing refined duplicates and envelopes are external nuisance/precision diagnostics.
 replicas=[]
 for pid in ['D01','I08']:
  original=next(r for r in recs if r['sample_id']==pid);respath=f'run/run_045/artifacts/private/odb/{pid}/result.json';res=read(source(respath));lossrow=next(x for x in read(source('run/run_045/artifacts/private/main/analysis.json'))['points'] if x['point_id']==pid)
  rec,fe,g,d=result_record(pid+'_REFINED',original['sigma_y_mpa'],original['n'],respath,lossrow['validation_loss'],'DUPLICATE_POINT_REFINEMENT_PASS');rec['parameter_group_id']=pid;rec['exclusion_reason']='DUPLICATE_PARAMETERS_DIFFERENT_MAX_INCREMENT';replicas.append(rec);data[rec['sample_id']]=(fe,g);diagnostics[rec['sample_id']]=d
 hb=read(source('run/run_051/artifacts/prepared_batch.json'));d01=next(x for x in recs if x['sample_id']=='D01')
 for point in hb['points']:
  pid=point['candidate_id'];respath=f'run/run_053/artifacts/private/odb/{pid}/result.json';res=read(source(respath))
  rec,fe,g,d=result_record(pid,d01['sigma_y_mpa'],d01['n'],respath,res['loss_or_null'],'ENVELOPE_ONLY_NOT_STANDARD_PARAMETERS',material='high_p_envelope_alpha_'+('.5' if pid=='H01' else '1.5'));rec['exclusion_reason']='NONSTANDARD_MATERIAL_FAMILY';replicas.append(rec);data[pid]=(fe,g);diagnostics[pid]=d
 # Old local study supplies only same-center historical feature secants, never D01 derivatives.
 oldlocal=read(source('run/run_054/artifacts/private/input_compatibility_audit.json'))
 for x in oldlocal['records']:
  if x['id'].startswith('L'):
   pid=x['id'];source(x['inp']);source(x['fd']);fd=curve(R/x['fd']);fe,g,d=extract(*fd);rec={'sample_id':pid,'sigma_y_mpa':x['sigma_y_mpa'],'n':x['n'],'material_type':'standard_Hollomon','job_name':'SPIO_R020_'+{'L01':'L01_SYM','L02':'L02_SYP','L03':'L03_NM','L04':'L04_NP'}[pid],'inp_path':x['inp'],'inp_sha256':SOURCES[x['inp']]['sha256'],'odb_path':x['odb'],'queue_id':x['queue_id'],'fd_path':x['fd'],'fd_sha256':SOURCES[x['fd']]['sha256'],'raw_points':len(fd[0]),'full_window':True,'solver_status':x['software'],'quality':x['numerical_quality'],'numerical_warnings':'historical37-47cutbacks/accepted-state and process gaps retained','cutback':x['cutback'],'loss':None,'included_primary':False,'exclusion_reason':'DIFFERENT_NUMERICAL_CONTRACT','in_historical_30':False,**controls(R/x['inp'])};recs.append(rec);data[pid]=(fe,g);diagnostics[pid]=d
 # Earlier P01 is an additional unique point, but coarse time controls prevent training pooling.
 p01loss=read(source('run/run_019/artifacts/private/main_analysis/loss_results.json'));p01row=p01loss['rows'][0];mp=read(source('run/run_017/artifacts/prepared_batch.json'));pt=next(x for x in mp['points'] if x.get('point_id')=='P01');ip=source(pt['inp_path'],pt['inp_sha256']);co=controls(ip)
 handoff=read(source('run/run_019/artifacts/private/odb_handoff_verified.json'));art=[a for a in handoff['artifacts'] if a['path'].endswith('p01_force_displacement.csv')];assert len(art)==1
 p01_fd=Path(art[0]['path']).relative_to(R).as_posix();source(p01_fd,art[0]['sha256']);u,f=curve(R/p01_fd);fe,g,d=extract(u,f)
 out=read(source('run/run_019/artifacts/private/execution_audit.json'));pa=next(x for x in out['records'] if x['point']['point_id']=='P01')
 for kind,x in pa['files'].items():
  if x.get('exists'):source(x['path'],x.get('sha256'))
 rec={'sample_id':'P01','sigma_y_mpa':p01row['sigma_y_mpa'],'n':p01row['n'],'material_type':'standard_Hollomon','job_name':pt['job_name'],'queue_id':pa['queue_id'],'inp_path':pt['inp_path'],'inp_sha256':pt['inp_sha256'],'odb_path':pa['files']['odb']['path'],'odb_sha256':pa['files']['odb']['sha256'],'fd_path':p01_fd,'fd_sha256':SOURCES[p01_fd]['sha256'],'raw_points':len(u),'full_window':True,'solver_status':p01row['status'],'loss':p01loss['P01']['loss'],'quality':'COARSE_EXISTING_SCORING_ONLY','in_historical_30':False,'included_primary':False,'exclusion_reason':'DIFFERENT_NUMERICAL_CONTRACT',**co};recs.append(rec);data['P01']=(fe,g);diagnostics['P01']=d
 skeletons={r['physical_skeleton_sha256'] for r in recs if r.get('loss') is not None and co_match(r)};assert len(skeletons)==1
 primary=[]
 for r in recs:
  if r['material_type']=='standard_Hollomon' and r.get('loss') is not None and co_match(r):r['included_primary']=True;primary.append(r['sample_id'])
 assert len(primary)==25 and set(primary)=={idof(x) for x in valid}|{'C200'}
 # Unique physical parameter groups (roundoff tolerance does not alter stored full precision).
 for i,x in enumerate(recs):
  for y in recs[:i]:assert abs(x['sigma_y_mpa']-y['sigma_y_mpa'])>1e-8 or abs(x['n']-y['n'])>1e-12,'duplicate unique sample entry'
 recs.sort(key=lambda x:x['sample_id']);primary.sort()
 save(P/'sample_inventory.json',{'records':recs,'replicates_and_material_variants':replicas,'primary_ids':primary,'historical24_ids':sorted(idof(x) for x in valid),'historical_null6_ids':sorted(idof(x) for x in null),'historical30_count':30,'primary_count':len(primary),'unique_standard_points':len(recs),'grouping_tolerance':'absolute1e-8MPa,1e-12n; full parameter precision retained','exclusions_are_not_loss_penalties':True,'sources':list(SOURCES.values()),'protocol_sha256':SOURCES['run/run_055/artifacts/private/feature_protocol.md']['sha256']})
 csvsave(P/'fe_sample_inventory.csv',recs);csvsave(P/'execution_variant_inventory.csv',recs+replicas)
 csvsave(P/'feature_matrix.csv',[{'sample_id':r['sample_id'],'sigma_y_mpa':r['sigma_y_mpa'],'n':r['n'],'included_primary':r['included_primary'],**dict(zip(NAMES,map(float,data[r['sample_id']][0])))} for r in recs if r['sample_id'] in data])
 csvsave(P/'primary_aligned_curves.csv',[{'sample_id':pid,**{f'F{i:03d}':float(x) for i,x in enumerate(data[pid][1])}} for pid in primary])
 save(P/'extraction_quality.json',diagnostics)
 save(P/'feature_arrays.json',{'names':NAMES,'grid_m':GRID.tolist(),'primary_ids':primary,'features':{pid:data[pid][0].tolist() for pid in data},'curves':{pid:data[pid][1].tolist() for pid in data},'targets':{r['sample_id']:[r['sigma_y_mpa'],r['n']] for r in recs},'external_targets':{r['sample_id']:[r['sigma_y_mpa'],r['n']] for r in replicas},'experiment_not_extracted':True})
 print(json.dumps({'historical_scoreable':len(valid),'historical_null':len(null),'unique_standard':len(recs),'primary_matching_controls':len(primary),'primary_extra':'C200','excluded_null_ids':sorted(idof(r) for r in null),'hashes':len(SOURCES)}))
def co_match(r):return r.get('initial_increment')==.001 and r.get('maximum_increment')==.0025 and r.get('minimum_increment')==1e-12 and r.get('step_time')==1.
if __name__=='__main__':main()
