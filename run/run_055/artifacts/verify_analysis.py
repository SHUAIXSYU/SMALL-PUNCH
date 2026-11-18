"""Independent source/OOF arithmetic checks and inventory-only metadata addendum."""
from pathlib import Path
import json,csv,hashlib,os
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_055/artifacts/private'
from feature_core import physical_to_normalized,normalized_to_physical,FIXED2,FIXED5
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 keys=list(dict.fromkeys(k for row in rs for k in row))
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)
def main():
 inv=read(P/'sample_inventory.json');a=read(P/'feature_arrays.json');ids=a['primary_ids'];X=np.array([a['features'][i] for i in ids]);F=np.array([a['curves'][i] for i in ids]);T=np.array([a['targets'][i] for i in ids]);Y=physical_to_normalized(T)
 protocol=read(P/'cv_protocol_identity.json');assert sha(P/'feature_protocol.md')==protocol['feature_protocol_sha256'] and sha(P/'feature_arrays.json')==protocol['feature_array_sha256'] and sha(P/'sample_inventory.json')==protocol['inventory_sha256']
 folds=read(P/'outer_fold_details.json');pred=rows(P/'inverse_cv_results.csv');assert len(pred)==250 and len(folds)==25
 for fold in folds:
  pid=fold['test_parameter_group'];assert pid not in fold['train_parameter_groups'];assert sorted(fold['train_parameter_groups'])==sorted(x for x in ids if x!=pid)
  g=[a['targets'][x] for x in fold['train_parameter_groups']];truth=a['targets'][pid];assert all(abs(p[0]-truth[0])>1e-8 or abs(p[1]-truth[1])>1e-12 for p in g)
 errors=[]
 for rec in pred:
  i=ids.index(rec['sample_id']);mask=np.arange(len(ids))!=i;kind=rec['model'];A=F if kind.startswith('full') else X;cols=json.loads(rec['selected_columns']);target=T[mask]
  if kind in ['mean','median']:p=np.mean(target,0) if kind=='mean' else np.median(target,0)
  else:
   xx=A[mask][:,cols];q=A[i,cols];mu=xx.mean(0);sd=xx.std(0);sd[sd<1e-12]=1;z=(xx-mu)/sd;qz=(q-mu)/sd
   if kind.endswith('_nn'):pn=Y[mask][np.argmin(np.sum((z-qz)**2,axis=1))]
   else:
    # SVD closed-form independent of the production normal/dual solve.
    yc=Y[mask].mean(0);u,s,vt=np.linalg.svd(z,full_matrices=False);lam=float(rec['lambda']);B=vt.T@((s/(s*s+len(z)*lam))[:,None]*(u.T@(Y[mask]-yc)));pn=qz@B+yc
   p=normalized_to_physical([pn])[0]
  e=float(max(abs(p[0]-float(rec['pred_sigma_y_mpa'])),abs(p[1]-float(rec['pred_n']))));assert e<1e-5,(rec['sample_id'],kind,e);errors.append(e)
 sources=[]
 for s in inv['sources']:assert sha(R/s['path'])==s['sha256'];sources.append(s)
 # Preserve original model-input identity; add omitted coarse-study Loss/ODB metadata only to final CSV.
 lc=read(R/'run/run_022/artifacts/private/analysis/loss_results.json');lossmap={r['point_id']:r['loss'] for r in lc['rows']};prev=read(R/'run/run_054/artifacts/private/input_compatibility_audit.json');prevsrc={x['path']:x for x in prev['sources']};records=inv['records']
 for rec in records:
  if rec['sample_id'] in ['L01','L02','L03','L04']:
   rec['loss']=lossmap[rec['sample_id']];rec['loss_version']='run017-exploratory-fd-v1';meta=prevsrc[rec['odb_path']];assert sha(R/meta['path'])==meta['sha256'];rec['odb_sha256']=meta['sha256'];sources.append(meta)
 original_csv=P/'fe_sample_inventory.csv';cp=P/'checkpoints';cp.mkdir(exist_ok=True);(cp/'fe_sample_inventory_initial.csv').write_bytes(original_csv.read_bytes());temp=P/'fe_sample_inventory.csv.tmp';csvsave(temp,records);os.replace(temp,original_csv)
 # Original D09 interrupted record remains distinct from final recovered-but-unscoreable material sample.
 original20=rows(R/'run/run_039/artifacts/private/main/original_20_execution_audit.csv');d09=[x for x in original20 if x['point_id']=='D09'];assert len(d09)==1;csvsave(P/'D09_original_attempt_exclusion.csv',d09)
 save(P/'inventory_metadata_addendum.json',{'reason':'Fill historical coarse-study existing Loss and ODB identity fields; primary sample IDs, arrays and nested CV frozen inputs unchanged','original_inventory_sha256_for_CV':sha(P/'sample_inventory.json'),'source_manifest':sources,'primary_ids_unchanged':ids==inv['primary_ids'],'final_inventory_csv_sha256':sha(original_csv),'D09_note':'recorded run033 original interruption plus run038 replacement null retained; no assertion this reconstructs all legacy resubmission history','historical_24_and_6_disjoint':set(inv['historical24_ids']).isdisjoint(inv['historical_null6_ids'])})
 csvsave(P/'heldout_prediction_independent_checks.csv',[{'row':i,'max_physical_prediction_difference':e} for i,e in enumerate(errors)])
 save(P/'independent_analysis_checks.json',{'unique_primary_groups':25,'OOF_rows':250,'OOF_group_leakage_check':'PASS','production_vs_independent_SVD_all_predictions':'PASS','max_physical_prediction_difference':max(errors),'all_bounded_original_sources_unchanged':True,'source_records_checked':len(sources),'CV_input_identity_unchanged':True,'SPT_not_used_in_CV':read(P/'experimental_application_provenance.json')['CV_complete_before_experiment_read'],'synthetic_tests':read(P/'synthetic_tests.json')['returncode']==0})
 print(json.dumps({'OOF_verified':len(pred),'max_difference':max(errors),'sources':len(sources),'leakage':'PASS','metadata_only_addendum':True}))
if __name__=='__main__':main()
