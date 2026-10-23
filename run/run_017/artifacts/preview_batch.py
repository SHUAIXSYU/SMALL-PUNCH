"""Public AbqJobPilot preview only. The sole enqueue call fixes dry_run=True."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'run/run_017/artifacts'
ABQ=Path(r'D:\Projects\abqjobpilot')
PROJECT=ROOT/'agenthub_sp_invopt/abqjobpilot_project'
PID='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ABQ))
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot import config


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,value):
    with p.open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def now():return datetime.now().astimezone().isoformat()
def git(*args):return subprocess.check_output(['git',*args],cwd=ABQ,text=True).strip()


def inspect_settings():
    api=AbqJobPilotClient()
    caps=api.capabilities()
    assert caps['application_version']=='0.2.2'
    settings=api.get_project_settings(project_id=PID).to_dict()
    assert settings['status']=='PERSISTED' and settings['persisted'] is True and not settings['defaulted_fields']
    assert not settings['errors'] and settings['project_id']==PID
    assert Path(settings['project_path']).resolve()==PROJECT.resolve()
    assert Path(settings['runtime_dir']).resolve()==(PROJECT/'runtime').resolve()
    assert Path(settings['settings_file']).resolve()==(PROJECT/'runtime/settings.json').resolve()
    stored=settings['settings'];assert stored==read(PROJECT/'runtime/settings.json')==settings['effective_settings']
    required={'abaqus_cmd':r'D:\ABAQUS2024\Commands\abq2024.bat','default_cpus':14,'default_gpus':0,
              'use_gpu':False,'run_datacheck':True,'run_full':True,'auto_shutdown_enabled':False}
    assert all(type(stored[k]) is type(v) and stored[k]==v for k,v in required.items())
    assert Path(stored['abaqus_cmd']).is_file() and config.ABAQUS_CMD==stored['abaqus_cmd']
    info=api.show_project(project_id=PID).to_dict()
    assert info['status']=='OK' and info['project']['project_id']==PID==read(PROJECT/'project.json')['project_id']
    scoped=api.for_project(project_id=PID)
    assert Path(scoped.runtime_dir).resolve()==(PROJECT/'runtime').resolve()
    return scoped,dict(observed_at=now(),settings_response=settings,capabilities=caps,project=info,
                      abaqus_command_exists=True,abaqus_command_sha256=sha(Path(stored['abaqus_cmd'])),
                      source_version=caps['application_version'],source_head=git('rev-parse','HEAD'),
                      source_working_tree=git('status','--short'),source_path=str(ABQ))


def main():
    scoped,setting=inspect_settings()
    if '--settings-only' in sys.argv:
        save(OUT/'abq_settings_verification.json',setting)
        print(json.dumps({'settings':'PERSISTED','project_id':PID,'version':setting['source_version']}))
        return
    prior=read(OUT/'abq_settings_verification.json')
    assert setting['settings_response']['settings']==prior['settings_response']['settings']
    design=read(OUT/'parameter_design.json')
    # MAIN verifies each frozen design path directly, independently of CAE manifest schema.
    protected=[PROJECT/'project.json',PROJECT/'project.db',PROJECT/'runtime/settings.json',PROJECT/'runtime/queue.json',
               PROJECT/'runtime/live_status.json',Path.home()/'.abqjobpilot/recent_projects.json',
               Path.home()/'.abqjobpilot/app_settings.json']
    before={str(p):sha(p) for p in protected}
    queue_before=scoped.list_jobs()
    assert queue_before['status']=='OK'
    active={'QUEUED','DATACHECK_RUNNING','DATACHECK_OK','FULL_RUNNING','UNKNOWN_INTERRUPTED'}
    assert not [j for j in queue_before['jobs'] if j['status'] in active]
    results=[]
    preview_dir=OUT/'previews';preview_dir.mkdir(exist_ok=False)
    for point in design['points']:
        inp=ROOT/point['inp_path'];work=ROOT/point['working_dir']
        assert inp.is_file() and work.is_dir() and not any(work.iterdir())
        assert inp.stem==point['job_name']
        assert not any(j.get('job_name')==point['job_name'] for j in queue_before['jobs'])
        digest=sha(inp)
        request=JobRequest(inp_path=str(inp),job_name=point['job_name'],cpus=14,gpus=0,
             working_dir=str(work),run_datacheck=True,run_full=True,
             submission_mode='preview_only',allow_solver_submit=False,
             batch='SPIO_run017_sensitivity_PREVIEW',strategy='frozen_five_point_cross',
             metadata={'run':'run_017','point_id':point['point_id'],'project_id':PID,
                       'inp_sha256':digest,'settings_sha256':sha(PROJECT/'runtime/settings.json'),
                       'authorized_jobs':0})
        pre=scoped.preflight(request).to_dict()
        dry=scoped.enqueue(request,dry_run=True).to_dict()
        record=dict(point_id=point['point_id'],job_name=point['job_name'],request=request.to_dict(),
                    inp_sha256=digest,preflight=pre,dry_run=dry,observed_at=now())
        save(preview_dir/(point['point_id']+'.json'),record)
        assert pre['status']=='PREVIEW_READY' and not pre['errors']
        assert dry['status']=='DRY_RUN_READY' and not dry['errors'] and dry['job_id'] is None
        assert not any(dry[k] for k in ('queue_file_mutated','solver_started','runner_started','forbidden_mutations_detected'))
        assert Path(pre['expected_odb_path']).resolve()==(ROOT/point['expected_odb']).resolve()
        assert sha(inp)==digest and not any(work.iterdir())
        assert f'cpus=14' in pre['command_preview'] and 'gpus=' not in pre['command_preview']
        results.append(dict(point_id=point['point_id'],job_name=point['job_name'],inp_path=point['inp_path'],
                            sha256=digest,working_dir=point['working_dir'],expected_odb=point['expected_odb'],
                            preflight=pre['status'],dry_run=dry['status'],queue_id=None))
    after={str(p):sha(p) for p in protected};queue_after=scoped.list_jobs()
    assert before==after and queue_before==queue_after
    assert git('rev-parse','HEAD')==setting['source_head'] and git('status','--short')==setting['source_working_tree']
    save(OUT/'private/abq_integrity.json',dict(observed_at=now(),before=before,after=after,
             unchanged=True,queue_before=queue_before,queue_after=queue_after))
    save(OUT/'batch_preview_result.json',dict(status='PASS_PREPARATION_ONLY',observed_at=now(),
         project_id=PID,settings='PERSISTED',candidates=results,
         queue_unchanged=True,existing_queue_records=len(queue_before['jobs']),new_queue_records=0,
         no_other_pending_jobs=True,solver_started=False,datacheck_started=False,settings_changed=False,
         preview_limitations=['preflight checks request/path identity and command generation; not Abaqus syntax, license or convergence',
                              'dry-run does not exercise actual enqueue-time Runner ownership/recovery checks; recheck before authorization execution']))
    print(json.dumps({'status':'PASS_PREPARATION_ONLY','candidate_count':len(results),'queue_unchanged':True},indent=2))


if __name__=='__main__':
    try:main()
    except Exception:
        stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')
        (OUT/'private'/('preview_failure_'+stamp+'.txt')).write_text(traceback.format_exc(),encoding='utf8')
        raise
