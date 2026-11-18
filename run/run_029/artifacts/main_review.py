"""MAIN checks real ODB evidence and applies the frozen center-pair gate."""
import hashlib,json,math,sqlite3,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_029/artifacts';P=A/'private'
sys.path[:0]=[str(ROOT),r'D:\Projects\abqjobpilot'];sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
from abqjobpilot.api import AbqJobPilotClient
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
s=read(P/'main_session.json');hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
hub.heartbeat(s['lease']);t=hub.task(s['odb_task_id'])
assert t['execution_state']=='COMPLETED' and t['evidence_state']=='RECORDED' and t['science_state']=='NOT_EVALUATED' and t['generation']==2 and t['lease_agent'].startswith('ODB:')
hub.poll_messages(s['identity'])
with sqlite3.connect(hub.path.as_uri()+'?mode=ro',uri=True) as con:
 con.row_factory=sqlite3.Row
 received=[dict(r) for r in con.execute("SELECT m.message_id,m.body FROM messages m JOIN message_receipts r ON r.message_id=m.message_id WHERE m.task_id=? AND m.sender=? AND m.direction='INBOX' AND r.session_id=?",(s['odb_task_id'],t['lease_agent'],s['identity']['session_id'])) if 'EXTRACTED_WITH_NUMERICAL_WARNINGS' in r['body']]
 arts=[dict(r) for r in con.execute('SELECT artifact_id,path,sha256,producer FROM artifacts WHERE task_id=?',(s['odb_task_id'],))]
assert received,'MAIN did not receive real ODB completion message'
assert len(arts)==35
for x in arts:
 p=Path(x['path']).resolve();assert p.is_relative_to(P/'odb') and x['producer']==t['lease_agent'] and sha(p)==x['sha256']
assert hub.verify_chain()
audit=read(P/'execution_audit.json');diag=read(P/'odb/diagnostics.json');worker=read(P/'odb/result.json');comp=read(P/'comparison/frozen_comparison_exact.json');focus=read(P/'odb/contact_focus_diagnostics.json');prior=read(ROOT/'run/run_025/artifacts/private/main_comparison.json');contract=read(ROOT/'run/run_027/artifacts/comparison_contract.json')
assert worker['task_id']==diag['task_id']==s['odb_task_id'] and worker['queue_id']==audit['queue_id']
assert all(diag['identity_checks'].values())
assert diag['odb']['sha256_before']==diag['odb']['sha256_after']==audit['files']['odb']['sha256']
assert comp['contract_sha256']==sha(ROOT/'run/run_027/artifacts/comparison_contract.json')
assert comp['implementation_sha256']==contract['comparison_implementation_sha256']
assert comp['candidate_fd_sha256']==sha(P/'odb/force_displacement.csv') and comp['candidate_points']==444
assert comp['candidate_range_m'][0]==0 and comp['candidate_range_m'][1]>=.0012
assert comp['all_quantitative_pass'] and all(comp['checks'].values())
assert math.isclose(comp['primary_V01']['original_loss'],prior['comparison']['validation_loss'],abs_tol=1e-14)
assert diag['peeq']['max_saved_frame']==worker['max_peeq']==comp['peeq']['candidate']<.9
assert diag['execution']['accepted_increments']==443 and diag['execution']['rejected_attempts']==19
assert focus['frame_count']==20 and focus['missing_contact_frame_count']==0 and focus['node23_direct_edge_neighbors']==[22,24,230]
assert focus['contact_pressure_onset_by_topology_node']['23']['increment']==418
assert focus['top_abs_force_steps'][0]['increment']==419 and focus['top_abs_force_steps'][0]['rejected_attempts']==0 and not focus['top_abs_force_steps'][0]['warning_classes']
for x in audit['files'].values():assert sha(ROOT/x['path'])==x['sha256']
assert sha(ROOT/'run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp')==audit['inp_sha256']
q=AbqJobPilotClient().for_project(project_id='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae').list_jobs();assert q['status']=='OK'
js=[x for x in q['jobs'] if x['queue_id']==audit['queue_id']];assert len(js)==1
j=js[0];assert j['status']=='COMPLETED' and j['raw_status']=='COMPLETED_WITH_WARNINGS' and j['return_code']==0 and j['final_verdict']=='SUCCESS'
assert not any(x['job_name']=='SPIO_R023_V02_NP' for x in q['jobs'])
assert all(x['status'] in ('COMPLETED','FAILED','CANCELLED','SKIPPED') for x in q['jobs'])
nw=diag['warnings']['msg_classes_by_outcome'];ow=prior['numerical_counts']['V01']['warning_counts']
accepted_new={k:v.get('ACCEPTED',0) for k,v in nw.items() if v.get('ACCEPTED',0)}
accepted_old={k:v.get('ACCEPTED',0) for k,v in ow.items() if v.get('ACCEPTED',0)}
assert accepted_new==accepted_old=={'ZERO_MOMENT':1}
assert not any(nw.get(k,{}).get('ACCEPTED',0) for k in ('NEGATIVE_EIGENVALUES','EXCESSIVE_DISTORTION','LARGE_STRAIN_INCREMENT'))
old_rej=prior['numerical_counts']['V01']['cutbacks'];old_acc=prior['numerical_counts']['V01']['accepted_increments'];new_rej=19;new_acc=443
assert new_rej/new_acc<old_rej/old_acc and audit['duration_sec']<5*prior['cost']['validation_total_sec']
assert diag['odb']['diagnostic_data']['numberOfAnalysisErrors']==0
v=comp['primary_V01'];p=comp['peeq'];aux=comp['auxiliary_run014'];old=comp['prior_run014_to_V01']
review={'at':datetime.now().astimezone().isoformat(),'decision':'PASS_CENTER_ADJACENT_REFINEMENT_ONLY','run_status':'WARNING','main_task_id':s['main_task_id'],'odb_task_id':s['odb_task_id'],'odb_generation':2,'queue_id':audit['queue_id'],'real_odb_artifact_count':len(arts),'real_odb_artifacts_verified':True,'main_received_completion_message_ids':[x['message_id'] for x in received],'metrics':{'rmse_n':v['force_rmse_n'],'rmse_limit_n':2,'max_abs_n':v['max_absolute_force_n'],'max_abs_limit_n':7.1445,'max_abs_at_mm':1000*v['max_absolute_at_m'],'max_regularized_relative':v['max_regularized_relative'],'max_regularized_relative_limit':.05,'abs_loss_change':abs(v['loss_change']),'abs_loss_change_limit':.00065,'max_saved_peeq_abs_change':p['absolute_delta'],'max_saved_peeq_limit':.02},'loss':{'V01':v['original_loss'],'candidate':v['validation_loss'],'run014':aux['original_loss']},'auxiliary':{'run014_to_V01_rmse_n':old['force_rmse_n'],'run014_to_candidate_rmse_n':aux['force_rmse_n'],'run014_to_V01_max_n':old['max_absolute_force_n'],'run014_to_candidate_max_n':aux['max_absolute_force_n'],'historical_run025_blocked_unchanged':True},'execution':{'datacheck_s':audit['phases']['DATACHECK_RUNNING']['duration_sec'],'full_s':audit['phases']['FULL_RUNNING']['duration_sec'],'total_s':audit['duration_sec'],'accepted':new_acc,'rejected':new_rej,'cutback_rate':new_rej/new_acc,'V01_accepted':old_acc,'V01_rejected':old_rej,'V01_cutback_rate':old_rej/old_acc,'warnings_by_outcome':nw,'accepted_warning_classes_new':accepted_new,'accepted_warning_classes_V01':accepted_old,'queue_warning_count':j['warning_count'],'odb_warning_count':diag['warnings']['odb_analysis_warning_count']},'contact':{'window_mm':[1.1,1.16],'accepted_frames':20,'node23_onset_mm':focus['contact_pressure_onset_by_topology_node']['23']['displacement_mm'],'node23_edge_neighbors':[22,24,230],'largest_local_delta_force_n':focus['top_abs_force_steps'][0]['delta_force_n'],'largest_local_increment':419,'node23_cpress_before_pa':focus['top_abs_force_steps'][0]['node23_cpress_before_pa'],'node23_cpress_after_pa':focus['top_abs_force_steps'][0]['node23_cpress_after_pa'],'COPEN_node23':'SENTINEL_MISSING','causality':'Pressure and force rise together in saved accepted frames; unique cause unproven'},'numerical_gates':{'five_metrics':True,'full_window':True,'material_table_coverage':True,'no_new_accepted_warning_class':True,'no_accepted_negative_or_distortion':True,'cutback_rate_decreased':True,'local_contact_event_reviewed':True,'no_new_blocking_issue_in_scope':True},'run025_original_qualification':'BLOCKED_V01_NUMERICAL_QUALIFICATION_UNCHANGED','original_four_point_jacobian_qualified':False,'mesh_converged':False,'experimentally_validated':False,'V02_queued':False,'new_solver_jobs':0,'historical_process_identity_gap':'UNCONFIRMED_RETAINED'}
path=P/'main_review.json';assert not path.exists();path.write_text(json.dumps(review,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'decision':review['decision'],'metrics':review['metrics'],'worker_artifacts':len(arts),'audit_chain':True},ensure_ascii=False))
