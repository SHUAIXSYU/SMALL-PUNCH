"""Verify bounded, existing FE evidence; no Abaqus/API solver use."""
from pathlib import Path
import hashlib,json,re,csv,sys
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_054/artifacts/private'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def readcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
SOURCES={}
def check(path,expected=None,role='input'):
 p=R/path;d=sha(p)
 if expected is not None:assert d==expected,(path,d,expected)
 SOURCES[path]={'path':path,'sha256':d,'bytes':p.stat().st_size,'role':role};return p
def controls(path):
 s=path.read_text(encoding='utf-8-sig');ls=s.splitlines();out=[];sk=[];skip=False
 for ix,line in enumerate(ls):
  t=line.strip()
  if t.lower().startswith('*static'):
   v=[float(x) for x in ls[ix+1].split(',')];out.append({'initial':v[0],'total_time':v[1],'minimum':v[2],'maximum':v[3]})
  if t.lower().startswith('*step'):step=t
  if t.startswith('*') and not t.startswith('**'):
   skip=t.lower().startswith('*plastic')
   if skip:sk.append('*Plastic');continue
  if skip:continue
  if ix>0 and ls[ix-1].strip().lower().startswith('*static'):sk.append('<STATIC_NUMERICAL_FIELDS>');continue
  if t.startswith('**'):continue
  if t:sk.append(t)
 assert len(out)==1
 return {'static':out[0],'step':step,'physical_skeleton_sha256_excluding_plastic_and_static_numbers':hashlib.sha256('\n'.join(sk).encode()).hexdigest()}
def fdcheck(path):
 rs=readcsv(path);uf='displacement_m' if 'displacement_m' in rs[0] else 'displacement_model_length';ff='force_n' if 'force_n' in rs[0] else 'force_model_force'
 u=[float(x[uf]) for x in rs];f=[float(x[ff]) for x in rs]
 assert u[0]<=0 and u[-1]>=.0012 and all(b>a for a,b in zip(u,u[1:]))
 return {'point_count':len(u),'u_start_m':u[0],'u_end_m':u[-1],'full_window':True,'strictly_increasing_u':True,'unit':'m/N','force_start_N':f[0],'force_end_N':f[-1]}
def main():
 old=read(check('run/run_020/artifacts/prepared_batch.json'));mapping=read(check('run/run_022/artifacts/private/reviewed_fd_inputs.json'));audit=read(check('run/run_022/artifacts/private/execution_audit_completed.json'));previous=read(check('run/run_022/artifacts/private/analysis/sensitivity.json'))
 cc=read(check('run/run_051/artifacts/comparison_contract.json'));mc=read(check(cc['material_contract_path'],cc['material_contract_sha256']));new=read(check('run/run_053/artifacts/private/main/response_metrics.json'));na=read(check('run/run_053/artifacts/private/execution_audit.json'))
 ev=read(check('run/run_053/artifacts/private/evidence_manifest.json'));evmap={r['path']:r['sha256'] for r in ev['files']}
 records=[]
 for point in old['points']:
  pid=point['point_id'];dr=read(check(mapping[pid]['diagnostics_path']));inp=check(point['inp_path'],point['inp_sha256']);check(point['parameters_path'],point['parameters_sha256']);fd=check(mapping[pid]['path'],mapping[pid]['sha256']);ar=next(a for a in audit['records'] if a['point']['point_id']==pid)
  for k,v in dr['provenance']['source_files'].items():check(v['path'],v['sha256'],'historical solver '+k)
  assert dr['provenance']['inp_sha256']==point['inp_sha256'] and dr['provenance']['source_files']['odb']['sha256']==ar['files']['odb']['sha256']
  assert all(dr['material']['numeric_identity_checks'].values()) and dr['fd']['covers_fixed_0_to_1p2mm_window']
  records.append({'id':pid,'basepoint':'run014 center(200MPa,.1)','sigma_y_mpa':point['sigma_y_mpa'],'n':point['n'],'alpha':1.,'inp':point['inp_path'],'fd':mapping[pid]['path'],'queue_id':dr['queue_id'],'odb':dr['provenance']['source_files']['odb']['path'],'controls':controls(inp),'fd_check':fdcheck(fd),'rp':dr['rp'],'software':dr['execution']['phase'],'accepted':dr['execution']['accepted_increments'],'cutback':dr['execution']['rejected_attempts'],'numerical_quality':'historical warnings, not point-level refinement qualified','historic_process_identity_gap':dr['read_safety']['historical_gap_retained'],'max_saved_peeq':dr['peeq']['saved_frame_max'],'scope':'WITHIN_OLD_STUDY_SECANT_ONLY'})
 dres=read(check(cc['baseline_result_path']));inp=check(mc['source_inp'],mc['source_inp_sha256']);check(cc['baseline_job'],cc['baseline_odb_sha256'],'refined baseline ODB');fd=check(cc['baseline_fd_path'],cc['baseline_fd_sha256'])
 assert dres['odb_sha256']==cc['baseline_odb_sha256'] and dres['inp_sha256']==mc['source_inp_sha256']
 records.append({'id':'D01','basepoint':'D01','sigma_y_mpa':mc['low_branch_sigma_y_mpa'],'n':mc['low_branch_n'],'alpha':1.,'inp':mc['source_inp'],'fd':cc['baseline_fd_path'],'queue_id':dres['queue_id'],'odb':cc['baseline_job'],'controls':controls(inp),'fd_check':fdcheck(fd),'software':'COMPLETED_WITH_WARNINGS','cutback':dres['cutback_increments'],'numerical_quality':'prior adjacent-increment PASS only; historical process-evidence gap retained','scope':'REFERENCE_FOR_ALPHA_SECANT'})
 hb=read(check('run/run_051/artifacts/prepared_batch.json'))
 for point in hb['points']:
  pid=point['candidate_id'];r=read(check(f'run/run_053/artifacts/private/odb/{pid}/result.json',evmap[f'run/run_053/artifacts/private/odb/{pid}/result.json']));ar=next(a for a in na['records'] if a['candidate_id']==pid);inp=check(point['inp_path'],point['inp_sha256']);fdpath=f'run/run_053/artifacts/private/odb/{pid}/force_displacement.csv';fd=check(fdpath,evmap[fdpath])
  for k,v in ar['files'].items():check(v['path'],v['sha256'],'hardening source '+k)
  assert ar['inp_sha256']==r['inp_sha256']==point['inp_sha256'] and ar['files']['odb']['sha256']==r['odb_sha256']
  records.append({'id':pid,'basepoint':'D01','sigma_y_mpa':mc['low_branch_sigma_y_mpa'],'n':mc['low_branch_n'],'alpha':.5 if pid=='H01' else 1.5,'inp':point['inp_path'],'fd':fdpath,'queue_id':r['queue_id'],'odb':ar['files']['odb']['path'],'controls':controls(inp),'fd_check':fdcheck(fd),'rp':r['punch_rp_identity'],'software':ar['software_phase'],'cutback':r['cutback_increments'],'numerical_quality':'exploratory reviewed; own adjacent-increment validation unavailable; H01 local pressure-build warning retained','scope':'SAME_D01_SAME_NUMERICS_MATERIAL_CONTRAST'})
 center=read(check('run/run_017/artifacts/private/reference_loss.json'));check(center['fe_source'],center['fe_sha256'],'old center FD');check('run/run_022/artifacts/private/analysis/aligned_curves.csv');check('run/run_053/artifacts/private/main/aligned_241_three_models.csv',evmap['run/run_053/artifacts/private/main/aligned_241_three_models.csv'])
 for k in ['target','config','implementation']:check(cc['loss_binding'][k+'_path'],cc['loss_binding'][k+'_sha256'])
 check('inverse/hollomon.py',old['generator_sha256'],'original constitutive generator')
 check(mc['implementation'],mc['implementation_sha256'],'frozen high-p envelope implementation')
 for path in ['run/run_045/artifacts/private/main/analysis.json','run/run_050/artifacts/private/main_review_checks.json','run/run_050/artifacts/private/scientific_report.md','run/run_053/artifacts/private/scientific_report.md','run/run_053/artifacts/private/main/spatial_energy_summary.csv','run/run_051/artifacts/private/REPORT.md']:
  check(path,evmap.get(path))
 skeletons={r['id']:r['controls']['physical_skeleton_sha256_excluding_plastic_and_static_numbers'] for r in records}
 assert len(set(skeletons.values()))==1,'Physical non-plastic model differs; investigate before direction comparison'
 result={'version':'run054-audit-existing-only-v1','records':records,'loss_binding':cc['loss_binding'],'physical_skeleton_all_equal_excluding_only_material_plastic_and_static_numbers':True,'alpha_study_same_reference_numerics':all(r['controls']==records[4]['controls'] for r in records[4:]),'cross_study_same_basepoint':False,'cross_study_same_numerical_controls':False,'old_center_sigma_y_mpa':200.,'old_center_n':.1,'old_center_fd':center['fe_source'],'D01_sigma_y_mpa':mc['low_branch_sigma_y_mpa'],'D01_n':mc['low_branch_n'],'comparison_scope':'EXPLORATORY_RESPONSE_SHAPE_TRANSFER_ONLY','formal_three_parameter_jacobian':'NOT_EVALUABLE','formal_joint_Fisher_information':'NOT_EVALUABLE','formal_joint_condition_number':None,'missing':'same-D01, .001 initial/.00125 max numerical settings, symmetric sigma_y and n perturbations','sources':list(SOURCES.values()),'historical_matrix_reference':previous['matrix'],'protected_previous_report_SHA256':sha(R/'run/run_053/artifacts/private/scientific_report.md')}
 save(P/'input_compatibility_audit.json',result);save(P/'source_hash_manifest.json',{'sources':list(SOURCES.values()),'no_tensile_data_access':True})
 print(json.dumps({'responses':len(records),'source_files':len(SOURCES),'old_static':records[0]['controls']['static'],'new_static':records[4]['controls']['static'],'same_physics':len(set(skeletons.values()))==1,'formal_joint':'NOT_EVALUABLE'}))
if __name__=='__main__':main()
