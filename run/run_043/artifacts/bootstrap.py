"""Revalidate two existing FE results, freeze tests and dispatch byte-only CAE edits."""
from __future__ import annotations
import csv,hashlib,json,subprocess,sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r"E:\Projects\SMALL-PUNCH");RUN=ROOT/"run/run_043";ART=RUN/"artifacts";PRIVATE=ART/"private"
sys.path[:0]=[str(ROOT),r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from agenthub_sp_invopt.hub import Hub

def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for b in iter(lambda:stream.read(1048576),b''):h.update(b)
    return h.hexdigest()
def now():return datetime.now().astimezone().isoformat()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as stream:json.dump(v,stream,ensure_ascii=False,indent=2);stream.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def main():
    assert not (RUN/'run.json').exists()
    start={'at':now(),'git':{'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short')}}
    save(RUN/'checkpoints/start.json',start)
    binding=read(ROOT/'run/run_030/artifacts/loss_contract_binding.json')
    for key,hkey in [('target_path','target_sha256'),('implementation_path','implementation_sha256'),('config_path','config_sha256')]:
        assert sha(ROOT/binding[key])==binding[hkey]
    prepared=read(ROOT/'run/run_033/artifacts/prepared_batch.json')
    initial=read(ROOT/'run/run_040/artifacts/private/initial_dataset.json')
    old=read(ROOT/'run/run_027/artifacts/comparison_contract.json')
    assert sha(ROOT/old['comparison_implementation_path'])==old['comparison_implementation_sha256']
    api=AbqJobPilotClient();PID=prepared['project_id'];scoped=api.for_project(project_id=PID)
    queue=scoped.list_jobs();history=api.list_project_jobs(project_id=PID).to_dict()
    assert queue['status']==history['status']=='OK'
    records=[]
    for pid in ['D01','I08']:
        p=next(p for p in prepared['points'] if p['point_id']==pid)
        base=next(r for r in initial['valid'] if r['point_id']==pid)
        result_path=ROOT/base['result_path'];result=read(result_path)
        assert sha(result_path)==base['result_sha256']
        inp=ROOT/p['inp_path'];work=ROOT/p['working_dir'];odb=ROOT/p['expected_odb']
        assert sha(inp)==p['inp_sha256']==result['inp_sha256']
        assert sha(odb)==result['odb_sha256']==base['odb_sha256']
        assert not (work/f"{p['job_name']}.lck").exists()
        j=next(j for j in queue['jobs'] if j['queue_id']==result['queue_id'])
        assert j['raw_status']=='COMPLETED_WITH_WARNINGS' and j['return_code']==0 and j['final_verdict']=='SUCCESS'
        assert j['job_name']==p['job_name'] and Path(j['inp_path']).resolve()==inp.resolve()
        hh=[h for h in history['jobs'] if h['job_name']==p['job_name']]
        assert len(hh)==1 and hh[0]['run_count']==1
        detail=api.show_job(hh[0]['job_id'],project_id=PID).to_dict()
        assert len(detail['runs'])==1 and detail['runs'][0]['queue_id']==result['queue_id']
        for path,digest in result['artifact_hashes'].items():assert sha(ROOT/path)==digest
        assert not result['numerical_blocking_issues']
        assert result['max_saved_peeq']<result['material_table_max_plastic_strain']==.9
        assert all(w['class']=='ZERO_MOMENT' for w in result['warning_events_by_accepted_or_rejected']['accepted'])
        assert inp.read_bytes().count(b'0.001, 1., 1e-12, 0.0025')==1
        files={ext:{'path':rel(work/f"{p['job_name']}.{ext}"),'sha256':sha(work/f"{p['job_name']}.{ext}")} for ext in ['odb','sta','msg','dat','log']}
        cid=f'V_{pid}';job=f'SPIO_R043_{cid}_M00125'
        records.append({'point_id':pid,'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'source_job_name':p['job_name'],
                        'source_inp':p['inp_path'],'source_inp_sha256':p['inp_sha256'],'source_odb':rel(odb),'source_odb_sha256':result['odb_sha256'],
                        'queue_id':result['queue_id'],'public_status':j,'history_detail':detail,'files':files,
                        'result_path':rel(result_path),'result_sha256':sha(result_path),'fd_path':result['positive_fd_csv'],'fd_sha256':sha(ROOT/result['positive_fd_csv']),
                        'loss':base['loss'],'max_saved_peeq':result['max_saved_peeq'],'cutback':result['cutback_increments'],
                        'baseline_quality':'WARNING_REVIEWED_PROVISIONAL','candidate_id':cid,'job_name':job,
                        'inp_path':f'run/run_043/artifacts/candidates/{job}/{job}.inp','parameters_path':f'run/run_043/artifacts/candidates/{job}/parameters.json',
                        'working_dir':f'run/run_043/artifacts/solver/{job}','expected_odb':f'run/run_043/artifacts/solver/{job}/{job}.odb'})
    save(PRIVATE/'baseline_audit.json',{'at':now(),'project_id':PID,'records':records,'sealed_tensile_access':False,'no_new_execution':True})
    with (ROOT/binding['target_path']).open(encoding='utf-8-sig',newline='') as stream:target=list(csv.DictReader(stream))[:241]
    gap=records[1]['loss']-records[0]['loss']
    contract={'version':'run043-two-point-adjacent-refinement-v1','frozen_at':now(),'status':'FROZEN_BEFORE_ANY_SOLVE',
              'loss_version':binding['version'],'loss_binding_sha256':sha(ROOT/'run/run_030/artifacts/loss_contract_binding.json'),
              'target_path':binding['target_path'],'target_sha256':binding['target_sha256'],'point_count':241,
              'grid_m':[float(r['displacement_m']) for r in target],'force_reference_n':1428.9,
              'relative_force_floor_n':old['relative_force_floor_n'],'relative_denominator':'max(abs(original force at each frozen grid point),71.445 N)',
              'thresholds':old['thresholds'],
              'comparison_implementation_path':old['comparison_implementation_path'],'comparison_implementation_sha256':old['comparison_implementation_sha256'],
              'comparison_tests_path':old['tested_by'],'comparison_tests_sha256':old['tests_sha256'],
              'ranking_implementation_path':rel(ART/'ranking_screen.py'),'ranking_implementation_sha256':sha(ART/'ranking_screen.py'),
              'ranking_tests_path':rel(ART/'test_ranking_screen.py'),'ranking_tests_sha256':sha(ART/'test_ranking_screen.py'),
              'baseline_gap_i08_minus_d01':gap,'ranking_screen':{'quantity':'abs(delta_L_D01)+abs(delta_L_I08)',
                  'screen_clear':'sum < original gap and both individually qualified; report actual refined gap too',
                  'screen_sensitive':'sum >= original gap or either point unqualified/unknown',
                  'limitation':'two observed changes are not rigorous numerical error bounds or proof of true ordering'},
              'numeric_source':'run030-standard-m0025-hollomon-v1','numeric_candidate':'run043-standard-m00125-pending-v1',
              'allowed_change':{'initial_increment':.001,'maximum_increment_old':.0025,'maximum_increment_new':.00125,'step_time':1,'minimum_increment':1e-12,'maximum_increments':999999},
              'per_point_gate':'all five thresholds and identity/window/material coverage, plus no unexplained blocking numerical issue',
              'local_diagnostic':old['local_diagnostic'],'ranking_gate_is_separate_from_individual_accuracy_gate':True,
              'decision':'Point-level increment check only; no mesh/physical/global convergence claim. No automatic further refinement or budget transfer.',
              'solver_authorization':False,'enqueue_authorization':False,'pairs':records}
    save(ART/'comparison_contract.json',contract)
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    actor=hub.register('MAIN','codex-main-run043-identifiability')
    freeze=hub.create_task(actor['agent_id'],'MAIN','freeze_two_low_loss_baselines_and_comparison',
          {'run':'run_043','baseline_audit_sha256':sha(PRIVATE/'baseline_audit.json'),'contract_sha256':sha(ART/'comparison_contract.json')},'run043-freeze-v1')
    lease=hub.claim(freeze['task_id'],actor,'run043-main-freeze-claim-v1');save(PRIVATE/'freeze_lease.json',lease)
    for path in [PRIVATE/'baseline_audit.json',ART/'comparison_contract.json']:
        hub.artifact(freeze['task_id'],actor['agent_id'],path,{'run':'run_043','scope':'baseline read-only and pre-solve frozen criteria'},version='run043-v1')
    hub.finish(lease,{'baseline_count':2,'historical_loss_gap':gap,'new_solver':False},evidence_state='RECORDED',science_state='WARNING')
    payload={'run':'run_043','kind':'two_existing_inputs_exact_max_increment_edit','baseline_audit_path':rel(PRIVATE/'baseline_audit.json'),
             'baseline_audit_sha256':sha(PRIVATE/'baseline_audit.json'),'comparison_contract_path':rel(ART/'comparison_contract.json'),
             'comparison_contract_sha256':sha(ART/'comparison_contract.json'),'pairs':records,
             'allowed_byte_edit':{'old':'0.001, 1., 1e-12, 0.0025','new':'0.001, 1., 1e-12, 0.00125','occurrences':1},
             'all_other_bytes_unchanged':True,'no_added_INP_comments':True,'do_not_regenerate_material':True,
             'project_id':PID,'project_path':'agenthub_sp_invopt/abqjobpilot_project','cpus':14,'gpus':0,
             'preflight_and_dry_run_only':True,'enqueue':False,'datacheck':False,'solver':False,'holdout_access':False}
    cae=hub.create_task(actor['agent_id'],'CAE','prepare_two_low_loss_increment_validation_inputs',payload,'run043-cae-two-increment-inputs-v1',depends=(freeze['task_id'],))
    hub.approve(cae['task_id'],actor['agent_id'],'generate_inp');hub.approve(cae['task_id'],actor['agent_id'],'verify_inp')
    hub.message(cae['task_id'],actor['agent_id'],'CAE',payload,'run043-main-to-cae-v1')
    review=hub.create_task(actor['agent_id'],'MAIN','review_low_loss_identifiability_and_two_previews',{'run':'run_043','cae_task_id':cae['task_id']},'run043-main-review-v1',depends=(cae['task_id'],))
    save(ART/'task_ids.json',{'identity':actor,'freeze_task_id':freeze['task_id'],'cae_task_id':cae['task_id'],'review_task_id':review['task_id']})
    assert hub.verify_chain()
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_043','stage':'Low-Loss identifiability and point-specific numerical qualification preparation',
          'objective':'Compare D01/I08 SPT residuals and predicted constitutive laws; prepare only two exact increment refinements',
          'status':'RUNNING','start_time':start['at'],'end_time':None,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'git':start['git'],
          'python_interpreter':sys.executable,'inputs':[{'path':'run/run_039/artifacts/private/main/main_review.json','role':'DOE reviewed data'},
          {'path':'run/run_042/artifacts/private/main/main_analysis.json','role':'combined pilot analysis'}],
          'outputs':[{'path':rel(PRIVATE/'baseline_audit.json'),'role':'two baselines revalidated'},{'path':rel(ART/'comparison_contract.json'),'role':'frozen future comparison'}],
          'validation':[{'check':'baseline_source_and_ODB_hash_identity','status':'PASS','evidence':'both completed once, prior extraction hashes and numerical qualification rechecked'}],'errors':[]})
    (RUN/'summary.md').write_text('# run_043 — 低Loss可识别性与数值资格准备\n\nRUNNING：两点身份已复核、比较协议已冻结，真实CAE任务已登记。\n',encoding='utf-8')
    print(json.dumps({'run':'run_043','cae_task_id':cae['task_id'],'comparison_contract_sha256':sha(ART/'comparison_contract.json'),'loss_gap':gap},ensure_ascii=False))

if __name__=='__main__':main()
