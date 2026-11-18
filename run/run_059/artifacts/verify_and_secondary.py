"""Independent actual-data checks and preregistered secondary frozen-model diagnostics."""
from common import *
import numpy as np
sys.path[:0]=[str(R),str(R/'run/run_057/artifacts'),str(R/'run/run_057/artifacts/private/frozen_predictor/code')]
from prospective_metrics import recovery_score
from inverse_baselines import predict_model
from feature_core import normalized_to_physical
from agenthub_sp_invopt.hub import Hub

ids=read(P/'task_ids.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3');receipt=read(P/'odb/handoff_receipts.json');actor=hub.session_identity(receipt['session']['session_id'])
assert actor['role']=='ODB' and actor['agent_id']=='ODB:ODB-real-run059'
hashes=0
for rec in receipt['records']:
 task=hub.task(rec['task_id']);assert task['execution_state']=='COMPLETED' and task['lease_agent']==actor['agent_id'] and task['lease_session']==actor['session_id'] and task['generation']==1
 for f in rec['artifacts']:assert sha(R/f['path'])==f['sha256'];hashes+=1
for f in read(P/'odb/manifest.json')['files']:assert sha(R/f['path'])==f['sha256']
assert hub.verify_chain()
save(P/'MAIN_real_ODB_receipt_verification.json',{'at':now(),'status':'PASS','task_ids':ids['odb_task_ids'],'real_ODB_identity':actor,'receipt_artifact_hashes_verified':hashes,'MAIN_retrieved_via':'formal Hub.task completed results plus exact task-scoped file/hash receipts; no unrelated inbox poll','cross_session_dispatch':'existing SP-InvOpt ODB Codex chat activated by explicitly authorized message; completed real turn','audit_chain_valid':True})
a=read(P/'study_A_local_secants.json');b=read(P/'study_B_frozen_parameter_recovery.json');assert len(a['views'])==5
verifications=[]
for name,v in a['views'].items():
 J=np.array(v['J']);gram=J.T@J;eig=np.linalg.eigvalsh(gram);independent=np.sqrt(np.maximum(eig[::-1],0));np.testing.assert_allclose(independent,v['singular_values'],rtol=1e-12,atol=1e-12)
 assert abs(np.linalg.norm(J[:,0])-v['column_norms'][0])<1e-12
 assert abs(independent[0]/independent[1]-v['condition_number'])<1e-9
 verifications.append({'view':name,'independent_Gram_singular_values':independent.tolist(),'condition_match':True})
assert b['frozen_model_sha256_before']==b['frozen_model_sha256_after']
primary={v['model']:v for v in b['metrics']};assert not primary['full_ridge']['engineering_resolution_goal_met'] and primary['full_ridge']['beats_constant_I06'] and all(primary['full_ridge']['active_axis_sign_correct'])
assert not primary['full_ridge']['each_coordinate_within_half_step']
for name in ['two_ridge','five_ridge']:assert not primary[name]['beats_constant_I06']
assert abs(primary['constant_I06_parameters']['E_local']-2**-.5)<1e-14
eq=read(P/'accepted_equilibrium_and_local_contact_v2.json');assert all(not r['equilibrium_missing_or_unconfirmed'] for r in eq['records'])
save(P/'independent_metric_verification.json',{'at':now(),'status':'PASS','real_ODB_artifact_checks':hashes,'five_views_Gram_vs_SVD_checks':verifications,'unchanged_frozen_model':True,'constant_baseline_exact_Elocal_verified':True,'fullcurve_improvement_not_misreported_as_halfstep_PASS':True,'accepted_trial_equilibrium_resolved':True,'no_Fisher_CI_or_statistical_significance':True})
bundle=R/'run/run_057/artifacts/private/frozen_predictor';models=read(bundle/'frozen_FE_only_inverse_models.json');d=read(P/'verified_response_arrays.json');batch=read(R/'run/run_057/artifacts/prepared_batch.json')
truth=np.array([[p['sigma_y_mpa'],p['n']] for p in batch['points']]);secondary=[];predictionrows=[]
for name,spec in models['models'].items():
 if name in ['two_ridge','five_ridge','full_ridge']:continue
 D=np.array([d['curves'][p['candidate_id']] if spec['input']=='full' else d['features'][p['candidate_id']] for p in batch['points']])
 physical=normalized_to_physical(predict_model(spec['model'],D));metric=recovery_score(physical,truth);metric.update(model=name,role='PREREGISTERED_SECONDARY_ONLY_NO_PROMOTION_TO_PRIMARY',selected_in_run055=spec['selection']);secondary.append(metric)
 for p,pred in zip(batch['points'],physical):predictionrows.append({'candidate_id':p['candidate_id'],'model':name,'pred_sigma_MPa':float(pred[0]),'pred_n':float(pred[1]),'true_sigma_MPa':p['sigma_y_mpa'],'true_n':p['n']})
save(P/'secondary_frozen_model_diagnostics.json',{'status':'EXPLORATORY_SECONDARY_FROZEN_ONLY','models':secondary,'no_new_model_or_selection':True,'not_used_to_replace_primary_comparison':True})
csvsave(P/'secondary_frozen_predictions.csv',predictionrows)
print(json.dumps({'real_ODB_receipts_verified':hashes,'Gram_checks':5,'secondary_models_evaluated':len(secondary),'primary_fullcurve_status':'IMPROVES_BUT_FAILS_FROZEN_HALFSTEP_GOAL'}))
