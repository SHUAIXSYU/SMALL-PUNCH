"""Freeze the next, adjacent-refinement comparison before the candidate can be solved."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_027/artifacts'
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now().astimezone().isoformat()
base=ROOT/'run/run_023/artifacts/private/comparison_contract.json'
implementation=ROOT/'run/run_023/artifacts/compare_validation.py'
tests=ROOT/'run/run_023/artifacts/test_compare_validation.py'
loss=ROOT/'inverse/fd_loss.py'
target=ROOT/'run/run_017/artifacts/private/canonical_fd_source_confirmed.csv'
v01=ROOT/'run/run_025/artifacts/private/odb/force_displacement.csv'
orig=ROOT/'run/run_014/artifacts/odb/punch_force_displacement.csv'
assert sha(base)=='2a4a50ab116b979d7b3263768e83be8cc9f8bf4e1c1cb042baadb74b178b0a17'
assert sha(implementation)=='0a8e9d70716385292153613d8ca823f956b6142c2acaa67e8903fa2565a82a36'
assert sha(loss)=='48d8d900f9eb453bdf1c896fea734c589ca8ab22d47e9dd98b165353ee794fb0'
prior=json.loads(base.read_text(encoding='utf8'))
assert sha(target)==prior['target_sha256'] and len(prior['grid_m'])==241
assert prior['thresholds']=={'force_rmse_n':2.0,'max_absolute_force_n':7.144500000000001,'max_regularized_relative':0.05,'absolute_loss_change':0.00065,'max_saved_peeq_absolute_change':0.02}
assert sha(orig)=='6af133606aab305f2d6b9cdb3c49efb4fd33c01cb45d7444dbd384f640a323f0'
v01_sha=sha(v01)
identity={'version':'run027-adjacent-refinement-v1','frozen_at':now(),'status':'FROZEN_BEFORE_CANDIDATE_SOLVE','run023_contract_path':str(base.relative_to(ROOT)).replace('\\','/'),'run023_contract_sha256':sha(base),'comparison_implementation_path':str(implementation.relative_to(ROOT)).replace('\\','/'),'comparison_implementation_sha256':sha(implementation),'tested_by':str(tests.relative_to(ROOT)).replace('\\','/'),'tests_sha256':sha(tests),'loss_implementation_path':str(loss.relative_to(ROOT)).replace('\\','/'),'loss_implementation_sha256':sha(loss),'loss_version':'run017-exploratory-fd-v1','target_path':str(target.relative_to(ROOT)).replace('\\','/'),'target_sha256':sha(target),'primary':{'original_job':'SPIO_R023_V01_CTR','original_fd_path':str(v01.relative_to(ROOT)).replace('\\','/'),'original_fd_sha256':v01_sha,'new_job':'SPIO_R027_CTR_M0025','candidate_status':'NOT_SOLVED'},'auxiliary':{'original_job':'SPIO_R014_Q200_N010','fd_path':str(orig.relative_to(ROOT)).replace('\\','/'),'fd_sha256':sha(orig),'purpose':'trend only; run025 original-v01 BLOCKED remains'},'grid_m':prior['grid_m'],'window_m':[0.0,0.0012],'point_count':241,'force_reference_n':1428.9,'weights':'equal','interpolation':'linear_no_extrapolation','displacement_rule':'u=-U2, m','force_rule':'F=-RF2, N','zero_shift_m':0.0,'smoothing':False,'drop_points':False,'secondary_compliance_correction':False,'relative_definition':prior['relative_definition'],'relative_force_floor_n':71.445,'thresholds':prior['thresholds'],'peeq_rule':'max across all saved frames; compare absolute difference to V01 and check candidate table upper bound 0.9','evidence_gates':['exact INP/source ODB and job identity','one datacheck and full analysis success if later authorized','accepted-frame RP U2/RF2 and full 0-1.2mm coverage','no missing force values or extrapolation','material table remains within PEEQ coverage','review accepted warnings, cutbacks, contact events and energy; no unexplained blocking issue'],'local_diagnostic':{'window_mm':[1.10,1.16],'raw_accepted_frame_force_and_displacement':True,'contact_outputs':['CPRESS','COPEN'],'node_23':True,'neighbor_nodes':'derive from ODB mesh/contact topology, do not assume node labels imply adjacency','events':['accepted/rejected increment','cutback','contact open-to-closed','contact-force tolerance','iteration and warning outcome'],'missing_copen_rule':'abs(COPEN)>=1e30 is sentinel/missing, not physical gap','contact_proxy_rule':'CPRESS>0 is positive-pressure proxy, not a complete contact-status proof','effect_on_decision':'supplementary diagnostics; cannot replace full-window thresholds'},'decision':{'all_metrics_pass_and_no_blocking_evidence':'PASS_CENTER_ADJACENT_REFINEMENT_ONLY; may propose a separately authorized uniform-settings exploratory plan','metric_fail':'BLOCKED; report primary V01, auxiliary run014 trend and failed gates; no automatic further increment reduction','identity_or_window_missing':'BLOCKED_OR_INDETERMINATE; no scoring by cropped window','no_threshold_retrofit':True,'run025_status_unchanged':'BLOCKED_V01_NUMERICAL_QUALIFICATION','original_four_point_jacobian_qualified':False,'mesh_or_experiment_validated':False,'future_uniform_numerical_contract_required':True,'historic_coarse_results_provenance_separate':True},'new_solver_authorization':False,'enqueue_authorization':False,'V02_authorization_transfer':False}
path=A/'comparison_contract.json';assert not path.exists()
path.write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'version':identity['version'],'sha256':sha(path),'V01_fd_sha256':v01_sha,'run023_implementation_sha256':sha(implementation),'tests_sha256':sha(tests)}))
