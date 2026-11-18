"""Public API preview/dry-run only. Never use enqueue with dry_run=False."""
from common import *
sys.path[:0]=[r'D:\Projects\abqjobpilot',str(R)]
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
import abqjobpilot

def main():
    pid='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae';project=R/'agenthub_sp_invopt/abqjobpilot_project'
    batch=read(P/'candidate_generation.json')
    guards=[project/'project.json',project/'project.db',project/'runtime/settings.json',project/'runtime/queue.json',R/'.gitignore']
    before={rel(p):sha(p) for p in guards}
    api=AbqJobPilotClient();scope=api.for_project(project_id=pid)
    capabilities=api.capabilities();settings=api.get_project_settings(project_id=pid).to_dict()
    show=api.show_project(project_id=pid).to_dict()
    queue=scope.list_jobs()
    runtime=assess_runtime(project/'runtime',project_db=project/'project.db')
    save(P/'abqjobpilot_environment_before.json',{'at':now(),'runtime_import':abqjobpilot.__file__,'api_source':r'D:\Projects\abqjobpilot\abqjobpilot\api\client.py','api_source_sha256':sha(Path(r'D:\Projects\abqjobpilot\abqjobpilot\api\client.py')),'capabilities':capabilities,'settings':settings,'project':show,'queue':queue,'runtime_assessment':runtime,'protected_hashes':before,'actions_requested':'preflight/dry_run only'})
    assert read(project/'project.json')['project_id']==pid
    assert settings['project_id']==pid and Path(settings['project_path']).resolve()==project.resolve()
    assert settings['status']=='PERSISTED' and settings['persisted'] and not settings['defaulted_fields'] and not settings['errors']
    s=settings['settings'];assert s==settings['effective_settings']==read(project/'runtime/settings.json')
    expected={'abaqus_cmd':r'D:\ABAQUS2024\Commands\abq2024.bat','default_cpus':14,'default_gpus':0,'use_gpu':False,'run_datacheck':True,'run_full':True,'auto_shutdown_enabled':False}
    assert all(type(s[k]) is type(v) and s[k]==v for k,v in expected.items()) and Path(s['abaqus_cmd']).is_file()
    assert queue['status']=='OK' and not queue['errors']
    executable={'QUEUED','DATACHECK_OK','RUNNING','DATACHECK_RUNNING','FULL_RUNNING','READY','PENDING'}
    active=[j for j in queue['jobs'] if j.get('status') in executable or j.get('raw_status') in executable]
    assert not active,'Other executable queue entries: stop'
    assert runtime['status']=='CLEAN' and runtime['owner']['state']=='ABSENT',runtime['status']
    baseline=read(R/'run/run_056/artifacts/private/prospective_design_contract.json')['baseline']
    baseline_status=scope.status(job_id=baseline['queue_id']).to_dict()
    baseline_outputs=scope.locate_outputs(job_id=baseline['queue_id']).to_dict()
    save(P/'I06_public_API_recheck.json',{'at':now(),'status':baseline_status,'outputs':baseline_outputs,'authority':'current public API evidence supplements hash-bound historical extraction; no history repair'})
    results=[]
    for point in batch['points']:
        inp=R/point['inp_path'];work=R/point['working_dir']
        assert sha(inp)==point['inp_sha256'] and inp.stem==point['job_name']
        assert not any(work.iterdir())
        assert not any(j.get('job_name')==point['job_name'] or str(j.get('inp_path','')).replace('\\','/').lower()==str(inp).replace('\\','/').lower() for j in queue['jobs'])
        request=JobRequest(inp_path=str(inp),job_name=point['job_name'],working_dir=str(work),cpus=14,gpus=0,run_datacheck=True,run_full=True,submission_mode='preview_only',allow_solver_submit=False,batch='SPIO_R057_PROSPECTIVE_PREVIEW_ONLY',strategy='run056-frozen-I06-local-design',metadata={'run':'run_057','candidate_id':point['candidate_id'],'inp_sha256':point['inp_sha256'],'execution_authorized':False,'new_FE_budget':0})
        pre=scope.preflight(request).to_dict();dry=scope.enqueue(request,dry_run=True).to_dict()
        item={'candidate_id':point['candidate_id'],'job_name':point['job_name'],'request':request.to_dict(),'preflight':pre,'dry_run':dry,'working_dir_empty':not any(work.iterdir()),'duplicate_current_or_history_identity':False}
        save(P/(point['candidate_id']+'_preview.json'),item)
        assert pre['status']=='PREVIEW_READY' and not pre['errors']
        assert dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
        assert all(not dry[k] for k in ['queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'])
        assert Path(pre['expected_odb_path']).resolve()==(R/point['expected_odb']).resolve()
        assert 'cpus=14' in pre['command_preview'] and 'gpus=' not in pre['command_preview']
        assert not any(work.iterdir())
        results.append(item)
    after={rel(p):sha(p) for p in guards};qafter=scope.list_jobs()
    assert before==after and queue==qafter
    save(P/'preflight_dry_run_results.json',{'at':now(),'preflight_passed':4,'dry_run_passed':4,'results':results,'protected_before':before,'protected_after':after,'queue_before':queue,'queue_after':qafter,'queue_unchanged':True,'settings_unchanged':True,'new_queue_records':0,'solver_started':False,'datacheck_started':False,'runner_started':False,'runtime':'CLEAN','settings_status':'PERSISTED','resources':expected,'AUTO_STOP_UNAVAILABLE':'historically confirmed; no automatic stop claim or runner modification; future execution needs explicit mode authorization','scope':'public API preview is not actual Abaqus syntax, license, convergence or physical verification'})
    print(json.dumps({'preflight':'4/4 PREVIEW_READY','dry_run':'4/4 DRY_RUN_READY','settings':'PERSISTED','version':capabilities['application_version'],'queue_unchanged':True,'runtime':runtime['status'],'solver_datacheck_started':False}))

if __name__=='__main__':main()
