"""In-memory tests of installed QueueRunner; all execution and storage mocked."""
import sys,json,hashlib
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\Projects\abqjobpilot')
from abqjobpilot import runner_core as rc
OUT=Path(__file__).resolve().parent
results=[]
def scenario(status,mode=None):
    queue=[{'queue_id':str(i),'status':'QUEUED'} for i in range(4)]
    runner=rc.QueueRunner();called=[]
    def fake(job):
        called.append(job['queue_id'])
        if mode=='exception':raise RuntimeError('synthetic crash')
        job['status']=status
        if mode=='stop_during':runner.request_stop_after_current()
        return {'ok':status=='COMPLETED_OK','job':job}
    original_next=runner._next_queued_job
    def racing_next():
        job=original_next();runner.request_stop_after_current();return job
    with ExitStack() as stack:
        for name,value in {'load_queue':lambda:queue,'run_next_job':fake,'_write_live_status':lambda **kw:None,'read_json':lambda *a:{},'write_json':lambda *a:None}.items():stack.enter_context(patch.object(rc,name,value))
        stack.enter_context(patch.object(rc.subprocess,'Popen',side_effect=AssertionError('FORBIDDEN process launch')))
        if mode=='boundary_race':stack.enter_context(patch.object(runner,'_next_queued_job',racing_next))
        try:runner._run_loop()
        except RuntimeError:
            assert mode=='exception'
    expect=1 if mode else 4
    assert len(called)==expect
    results.append(dict(synthetic_status=status,mode=mode,executed_fake_jobs=len(called),unexecuted_queued=sum(q['status']=='QUEUED' for q in queue),expected_pass=True))
for status in ['DATACHECK_FAILED','FAILED_NUMERICAL','COMPLETED_WITH_WARNINGS']:scenario(status)
scenario('COMPLETED_OK','stop_during')
scenario('COMPLETED_OK','boundary_race')
scenario('COMPLETED_OK','exception')
# Exercise actual per-job branch with every side effect replaced; datacheck
# failure must not invoke the Full phase even though the outer loop continues.
job={'queue_id':'fake','status':'QUEUED','run_datacheck':True,'run_full':True};phases=[]
def update(qid,values):job.update(values);return job.copy()
with ExitStack() as s:
    replacements={'_refresh_job_paths':lambda j:j,'update_job':update,'load_queue':lambda:[job],
       '_run_command':lambda j,p,c:phases.append(p) or 1,'build_abaqus_datacheck_command':lambda j:['FAKE'],
       '_read_text':lambda p:'','classify_datacheck_attempt':lambda t,c:{'status':'DATACHECK_FAILED'},
       '_odb_size':lambda j:None,'_write_live_status':lambda *a,**kw:None,'_write_report':lambda j:None}
    for k,v in replacements.items():s.enter_context(patch.object(rc,k,v))
    s.enter_context(patch.object(rc.subprocess,'Popen',side_effect=AssertionError('FORBIDDEN')))
    result=rc.run_next_job(job)
assert not result['ok'] and phases==['DATACHECK_RUNNING']
results.append(dict(case='failed_datacheck_blocks_same_job_full',phases=phases,expected_pass=True))
sources={name:hashlib.sha256((Path(r'D:\Projects\abqjobpilot')/name).read_bytes()).hexdigest() for name in ['abqjobpilot/runner_core.py','abqjobpilot/gui_app.py','run_gui.py']}
out=dict(status='AUTO_STOP_UNAVAILABLE',test_count=len(results),tests=results,source_hashes=sources,
    no_real_runner_start=True,no_solver_process=True,no_runtime_io=True,
    limitations='Deterministic fake scheduling demonstrates boundary race; no real GUI timing or Solver tested.')
with (OUT/'runner_fake_tests.json').open('x',encoding='utf8') as f:json.dump(out,f,indent=2)
print(json.dumps(out))
