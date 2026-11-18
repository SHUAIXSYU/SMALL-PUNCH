"""Two explicitly authorized, frozen numerical inputs; queue-only public API.

Reuses verified run_041 read-only environment/ownership/queue checks. No solver
launcher exists here. A durable marker forbids replay after partial submission.
"""
from __future__ import annotations
import json,os,re,sys,traceback
from pathlib import Path

ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_044';ART=RUN/'artifacts';PRIVATE=ART/'private';RECEIPTS=PRIVATE/'queue_receipts'
HELPER=ROOT/'run/run_041/artifacts/queue_pilot.py'
sys.path.insert(0,str(HELPER.parent))
import queue_pilot as q
from abqjobpilot.api import AbqJobPilotClient,JobRequest
from abqjobpilot.runtime_coordination import queue_transaction
from agenthub_sp_invopt.hub import Hub
read=q.read;sha=q.sha;save=q.save;now=q.now;rel=q.rel
PREPARED=ROOT/'run/run_043/artifacts/prepared_batch.json'
PROJECT=q.PROJECT;RT=q.RT;PID=q.PID
ORDER=['SPIO_R043_V_D01_M00125','SPIO_R043_V_I08_M00125']

def load_points():
    frozen=read(PREPARED);run43=read(ROOT/'run/run_043/run.json')
    expected={v['path']:v['sha256'] for v in run43['outputs']}
    assert sha(PREPARED)==expected[rel(PREPARED)]
    assert frozen['project_id']==PID and len(frozen['points'])==2 and frozen['order']==ORDER
    assert frozen['cpus']==14 and frozen['gpus']==0 and frozen['run_datacheck'] and frozen['run_full']
    contract=ROOT/frozen['comparison_contract_path']
    assert sha(contract)==frozen['comparison_contract_sha256']==expected[rel(contract)]
    cc=read(contract)
    assert sha(ROOT/cc['comparison_implementation_path'])==cc['comparison_implementation_sha256']
    assert sha(ROOT/cc['ranking_implementation_path'])==cc['ranking_implementation_sha256']
    assert sha(ROOT/cc['target_path'])==cc['target_sha256']
    points=[]
    for p in frozen['points']:
        assert p['job_name'] in ORDER
        inp=ROOT/p['inp_path'];source=ROOT/p['source_inp'];work=ROOT/p['working_dir']
        assert sha(inp)==p['inp_sha256']
        if rel(inp) in expected:assert p['inp_sha256']==expected[rel(inp)]
        assert sha(source)==p['source_sha256']
        raw=source.read_bytes();candidate=inp.read_bytes()
        old=b'0.001, 1., 1e-12, 0.0025';new=b'0.001, 1., 1e-12, 0.00125'
        assert raw.count(old)==1 and candidate==raw.replace(old,new,1)
        assert re.search(rb'(?im)^\*step\b[^\r\n]*\binc=999999\b',candidate)
        assert sha(ROOT/p['parameters_path'])==p['parameters_sha256']
        params=read(ROOT/p['parameters_path'])
        assert params['sigma_y_mpa']==p['sigma_y_mpa'] and params['n']==p['n']
        assert work.is_dir() and not any(work.iterdir())
        assert not (ROOT/p['expected_odb']).exists() and inp.stem==p['job_name']
        points.append({**p,'candidate_id':p['point_id']})
    assert [p['job_name'] for p in points]==ORDER
    assert len({p['working_dir'] for p in points})==2 and len({p['inp_sha256'] for p in points})==2
    return points

def request(p,task):
    return JobRequest(inp_path=str((ROOT/p['inp_path']).resolve()),job_name=p['job_name'],
        working_dir=str((ROOT/p['working_dir']).resolve()),cpus=14,gpus=0,run_datacheck=True,run_full=True,
        submission_mode='enqueue_only',allow_solver_submit=False,batch='run044_authorized_two_refinement',
        strategy='frozen_two_point_validation_serial_user_GUI',metadata={'project_id':PID,'task_id':task,
        'inp_sha256':p['inp_sha256'],'notes':f"run044 {p['point_id']}; inp_sha256={p['inp_sha256']}; task_id={task}; Project={PID}; one manual-GUI Datacheck+Full; 14CPU 0GPU; zero retries; AUTO_STOP_UNAVAILABLE accepted"})

def prepare():
    assert not (RUN/'run.json').exists()
    assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe' and sys.version_info[:3]==(3,11,13)
    points=load_points();start={'at':now(),'git':{'branch':q.git('branch','--show-current'),'head':q.git('rev-parse','HEAD'),
                   'remote':q.git('remote','-v'),'working_tree':q.git('status','--short')},'python':sys.executable,'helper_sha256':sha(HELPER)}
    save(RUN/'checkpoints/start.json',start)
    save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_044','stage':'Authorized two-point numerical validation queue-only execution record',
       'objective':'Register two single attempts, recheck frozen inputs and current previews, queue only, stop for manual GUI start',
       'status':'RUNNING','start_time':start['at'],'end_time':None,'git_branch':start['git']['branch'],'git_head':start['git']['head'],'git':start['git'],
       'python_interpreter':sys.executable,'inputs':[{'path':rel(PREPARED),'sha256':sha(PREPARED),'role':'immutable two-input batch'}],
       'outputs':[],'validation':[],'errors':[]})
    (RUN/'summary.md').write_text('# run_044 — 两项数值验证授权入队\n\nRUNNING：开始当前环境核验，Solver由用户手动启动。\n',encoding='utf-8')
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID)
    env=q.environment(api);runtime=q.runtime_guard(deep=True);queue=q.queue_prefix(scoped,api,points,0)
    runner=q.ABQ/'abqjobpilot/runner_core.py';code=runner.read_text(encoding='utf-8');loop=code[code.index('    def _run_loop(self)'):]
    assert '                run_next_job(job)' in loop and 'final_verdict' not in loop and 'FAILED' not in loop
    authorization={'run':'run_044','source':{'type':'explicit current human chat message','title':'SP-InvOpt｜run_043 D01/I08 数值验证 — 正式授权执行','message_id':None},
       'project_id':PID,'prepared_batch_sha256':sha(PREPARED),'comparison_contract_sha256':read(PREPARED)['comparison_contract_sha256'],
       'max_started_attempts':2,'per_input_max_datacheck':1,'per_input_max_full_after_datacheck_success':1,'automatic_retries':0,
       'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'solver_start':'USER_GUI_ONLY',
       'batch_continue_after_individual_failure_accepted':True,'auto_stop':'AUTO_STOP_UNAVAILABLE',
       'no_third_job_or_budget_transfer':True,'points':points,'queued_is_not_started':True}
    save(PRIVATE/'authorization_scope.json',authorization)
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=hub.register('MAIN','codex-main-run044-two-validation')
    budget=hub.create_task(actor['agent_id'],'MAIN','record_two_validation_authorization',authorization,'run044-two-budget-v1')
    lease=hub.claim(budget['task_id'],actor,'run044-budget-claim-v1');save(PRIVATE/'budget_lease.json',lease)
    hub.artifact(budget['task_id'],actor['agent_id'],PRIVATE/'authorization_scope.json',{'run':'run_044','scope':'explicit human authorization, GUI-only Solver start'},version='run044-v1')
    hub.finish(lease,{'authorized':2,'prepared':2,'queued':0,'started':0,'consumed':0,'automatic_retries':0},evidence_state='RECORDED',science_state='NOT_EVALUATED')
    tasks={}
    for p in points:
        task=hub.create_task(actor['agent_id'],'MAIN','queue_only_frozen_validation',{'run':'run_044','candidate':p,'authorization_sha256':sha(PRIVATE/'authorization_scope.json'),
              'project_id':PID,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'max_attempts':1,'automatic_retries':0,'solver_start':'USER_GUI_ONLY'},f"run044-queue-{p['point_id']}-v1",depends=(budget['task_id'],))
        hub.approve(task['task_id'],actor['agent_id'],'enqueue');hub.approve(task['task_id'],actor['agent_id'],'start_solver');tasks[p['point_id']]=task['task_id']
    confirm=hub.create_task(actor['agent_id'],'MAIN','confirm_two_validation_jobs_queued',{'run':'run_044','order':ORDER},'run044-confirm-two-v1',depends=tuple(tasks.values()))
    audit=hub.create_task(actor['agent_id'],'MAIN','audit_two_validation_after_user_completion',{'run':'run_044','trigger':'Only after user confirms completion; no Solver start'},'run044-future-audit-v1',depends=(confirm['task_id'],))
    odb=hub.create_task(actor['agent_id'],'ODB','extract_two_validation_safe_odb_readonly',{'run':'run_044','audit_task_id':audit['task_id'],
       'comparison_contract_path':read(PREPARED)['comparison_contract_path'],'comparison_contract_sha256':read(PREPARED)['comparison_contract_sha256'],
       'read_only':True,'holdout_access':False},'run044-future-odb-v1',depends=(audit['task_id'],))
    science=hub.create_task(actor['agent_id'],'MAIN','qualify_two_refinements_and_loss_ranking',{'run':'run_044','prepared_sha256':sha(PREPARED),'original_gap':5.5727869006435594e-5},'run044-future-science-v1',depends=(odb['task_id'],))
    save(PRIVATE/'task_ids.json',{'identity':actor,'budget_task_id':budget['task_id'],'point_tasks':tasks,'confirm_task_id':confirm['task_id'],
       'execution_audit_task_id':audit['task_id'],'odb_task_id':odb['task_id'],'science_task_id':science['task_id']})
    before={key:sha(path) for key,path in [('queue',RT/'queue.json'),('settings',RT/'settings.json'),('db',PROJECT/'project.db')]}
    previews=[]
    for p in points:
        req=request(p,tasks[p['point_id']]);pre=scoped.preflight(req).to_dict();dry=scoped.enqueue(req,dry_run=True).to_dict()
        previews.append({'point_id':p['point_id'],'request':req.to_dict(),'preflight':pre,'dry_run':dry})
        assert pre['status']=='PREVIEW_READY' and not pre['errors']
        assert dry['status']=='DRY_RUN_READY' and not dry['errors'] and not dry['queue_file_mutated']
        assert not dry['solver_started'] and not dry['runner_started']
        assert Path(pre['expected_odb_path']).resolve()==(ROOT/p['expected_odb']).resolve()
    after={key:sha(path) for key,path in [('queue',RT/'queue.json'),('settings',RT/'settings.json'),('db',PROJECT/'project.db')]}
    assert before==after
    q.queue_prefix(scoped,api,points,0);q.runtime_guard()
    save(PRIVATE/'precheck.json',{'at':now(),'status':'PASS_BOTH_CURRENT_PREVIEWS','prepared_sha256':sha(PREPARED),'environment':env,'runtime':runtime,
       'queue_before':queue,'previews':previews,'protected_before':before,'protected_after':after,'runner_auto_stop':'AUTO_STOP_UNAVAILABLE',
       'runner_source_path':str(runner),'runner_source_sha256':sha(runner),'unchanged_other_bytes':True,'new_solver_started':False})
    assert hub.verify_chain()
    print(json.dumps({'status':'PASS_BOTH_CURRENT_PREVIEWS','authorizations':2,'preflight':2,'dry_run':2,'started':0}))

def enqueue():
    if (PRIVATE/'queue_manifest.json').exists():
        manifest=read(PRIVATE/'queue_manifest.json');print(json.dumps({'status':'ALREADY_QUEUED_NO_SUBMISSION','queue_ids':manifest['queue_ids']}));return
    assert not (RUN/'checkpoints/enqueue_started.json').exists(),'Partial/uncertain outcome; read-only reconciliation required, no resubmit'
    precheck=read(PRIVATE/'precheck.json');assert precheck['status']=='PASS_BOTH_CURRENT_PREVIEWS'
    points=load_points();ids=read(PRIVATE/'task_ids.json');actor=ids['identity'];hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    api=AbqJobPilotClient();scoped=api.for_project(project_id=PID);q.environment(api);q.runtime_guard(deep=True);q.queue_prefix(scoped,api,points,0)
    save(RUN/'checkpoints/enqueue_started.json',{'at':now(),'queue_submission_attempt':1,'FE_started_attempts':0,'no_retry':True})
    receipts=[]
    for ix,p in enumerate(points):
        tid=ids['point_tasks'][p['point_id']];hub.require_approval(tid,'enqueue')
        assert hub.task(tid)['execution_state']=='PENDING'
        lease=hub.claim(tid,actor,f"run044-{p['point_id']}-queue-claim-v1");save(PRIVATE/f"lease_{p['point_id']}.json",lease)
        req=request(p,tid)
        with queue_transaction(RT):
            q.runtime_guard();q.queue_prefix(scoped,api,points,ix)
            assert sha(ROOT/p['inp_path'])==p['inp_sha256'] and not any((ROOT/p['working_dir']).iterdir())
            save(RECEIPTS/f"{ix+1}_{p['point_id']}_request.json",req.to_dict())
            save(RUN/f"checkpoints/submission_{p['point_id']}.json",{'at':now(),'queue_submission_attempt':1,'FE_attempts':0})
            response=scoped.enqueue(req,dry_run=False).to_dict();save(RECEIPTS/f"{ix+1}_{p['point_id']}_response.json",response)
            assert response['status']=='ENQUEUED' and response['job_id'] and response['queue_only'] and response['queue_file_mutated']
            assert not response['solver_started'] and not response['runner_started'] and not response['forbidden_mutations_detected']
            after=q.queue_prefix(scoped,api,points,ix+1);assert after['queue_ids'][-1]==response['job_id']
        status=scoped.status(job_id=response['job_id']).to_dict();outputs=scoped.locate_outputs(job_id=response['job_id']).to_dict()
        assert status['status']=='QUEUED' and not status['odb_exists'] and not status['lock_exists']
        receipt={'at':now(),'point_id':p['point_id'],'position':ix+1,'job_name':p['job_name'],'queue_id':response['job_id'],
           'inp_path':str(ROOT/p['inp_path']),'inp_sha256':p['inp_sha256'],'working_dir':str(ROOT/p['working_dir']),'expected_odb':str(ROOT/p['expected_odb']),
           'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'project_id':PID,'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,
           'actual_FE_attempts':0,'automatic_retries':0,'api_status':status,'api_outputs':outputs,'scientific_state':'NOT_EVALUATED'}
        path=RECEIPTS/f"{ix+1}_{p['point_id']}_receipt.json";save(path,receipt)
        hub.artifact(tid,actor['agent_id'],path,{'run':'run_044','scope':'queue-only, not a consumed FE attempt'},version='run044-v1')
        hub.finish(lease,receipt,evidence_state='RECORDED',science_state='NOT_EVALUATED');receipts.append(receipt)
        print(json.dumps({'queued':ix+1,'of':2,'job_name':p['job_name'],'queue_id':response['job_id']}),flush=True)
    final=q.queue_prefix(scoped,api,points,2);runtime=q.runtime_guard(deep=True)
    assert len(set(final['queue_ids']))==2
    assert sha(RT/'settings.json')==precheck['protected_after']['settings'] and sha(PROJECT/'project.db')==precheck['protected_after']['db']
    load_points()
    manifest={'at':now(),'status':'TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START','project_id':PID,'order':ORDER,
       'queue_ids':final['queue_ids'],'points':receipts,'queue_after':final,'runtime':runtime,'queued':2,'started_attempts':0,
       'consumed_FE_budget':0,'maximum_attempts':2,'automatic_retries':0,'other_executable_jobs':0,
       'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'solver_start':'USER_GUI_ONLY','auto_stop':'AUTO_STOP_UNAVAILABLE',
       'prepared_batch_sha256':sha(PREPARED),'comparison_contract_sha256':read(PREPARED)['comparison_contract_sha256']}
    save(PRIVATE/'queue_manifest.json',manifest)
    lease=hub.claim(ids['confirm_task_id'],actor,'run044-two-queue-confirm-v1');save(PRIVATE/'confirm_lease.json',lease)
    hub.artifact(ids['confirm_task_id'],actor['agent_id'],PRIVATE/'queue_manifest.json',{'run':'run_044','scope':'both queued, no starts'},version='run044-v1')
    hub.finish(lease,{'status':manifest['status'],'queued':2,'started':0,'consumed':0,'queue_ids':final['queue_ids']},evidence_state='RECORDED',science_state='NOT_EVALUATED')
    assert hub.verify_chain()
    print(json.dumps({'status':manifest['status'],'queue_ids':final['queue_ids'],'started':0}))

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['prepare','enqueue']
    try:{'prepare':prepare,'enqueue':enqueue}[sys.argv[1]]()
    except Exception:
        path=PRIVATE/f'{sys.argv[1]}_failure.json'
        if not path.exists():save(path,{'at':now(),'phase':sys.argv[1],'status':'BLOCKED','traceback':traceback.format_exc(),'no_automatic_retry':True,
                 'confirmed_receipts':[read(p) for p in sorted(RECEIPTS.glob('*_receipt.json'))] if RECEIPTS.exists() else []})
        raise
