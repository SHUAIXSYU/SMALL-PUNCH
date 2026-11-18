"""Exclusive run registration and preservation checks before candidate creation."""
from common import *
import platform, numpy as np, scipy
sys.path.insert(0, str(R))
from agenthub_sp_invopt.hub import Hub

at = now()
assert max(int(p.name.split('_')[1]) for p in (R/'run').glob('run_[0-9]*') if p.is_dir())==57
gv=read(R/'run/run_056/artifacts/private/git_hygiene_verified.json')
assert sha(R/'.gitignore')==gv['gitignore_sha256']
models=gv['local_models']
for m in models: assert sha(R/m['path'])==m['sha256']
staged=git('diff','--cached','--name-status')
assert set(staged.splitlines())=={'D\t'+m['path'] for m in models}
assert not git('ls-files','--','*.cae','*.cae.*','*.odb','*.sim','*.lck')
assert git('check-ignore','--no-index','probe.cae','probe.cae.1','probe.odb','probe.lck').splitlines()==['probe.cae','probe.cae.1','probe.odb','probe.lck']
contract=read(R/'run/run_056/artifacts/private/prospective_design_contract.json')
assert sha(R/'run/run_056/artifacts/private/prospective_design_contract.json')=='a3f8cae3896e2c5079d6796e95122109ecfa8075850dfb617778d023f7f828d0'
sources={}
for s in read(R/'run/run_056/artifacts/private/source_manifest.json')['sources']:
    assert sha(R/s['path'])==s['sha256'],s['path']
    sources[s['path']]={'path':s['path'],'sha256':s['sha256']}
for path in ['run/run_056/artifacts/private/prospective_design_contract.json','run/run_056/artifacts/private/prospective_evaluation_protocol.md','run/run_056/artifacts/private/scientific_report.md']:
    sources[path]={'path':path,'sha256':sha(R/path)}
baseline=contract['baseline']
for k in ['inp','odb','params']:
    assert sha(R/baseline[k+'_path'])==baseline[k+'_sha256']
    sources[baseline[k+'_path']]={'path':baseline[k+'_path'],'sha256':baseline[k+'_sha256']}
for key in ['result_path','diagnostics_path','fd_path']:
    path=baseline[key]; sources[path]={'path':path,'sha256':sha(R/path)}
save(P/'source_manifest.json', {'scope':'bounded FE-only prior evidence; no holdout files or sealed analyses', 'sources':list(sources.values())})
state={'at':at,'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'status':git('status','--short'),'staged':staged,'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':models,'python':{'executable':sys.executable,'version':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}}
save(RUN/'checkpoints/start.json',state)
save(P/'git_preservation_start.json',state)
save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_057','stage':'Prospective Identification Batch Preparation','objective':'Freeze four I06-local INPs and unchanged FE-only predictors; preview only','status':'RUNNING','start_time':at,'end_time':None,'python_interpreter':sys.executable,'git_branch':state['branch'],'git_head':state['head'],'inputs':[],'outputs':[],'validation':[],'errors':[],'new_FE':0,'new_queue':0})
hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
identity=hub.register('MAIN','codex-main-run057-preparation')
payload={'run':'run_057','user_authorization':'prepare and freeze four run056 points only; no enqueue, Solver/datacheck or retry','design_sha256':sha(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'points':contract['points'],'scope':'MAIN performs authorized offline file preparation and review in current session; no separate CAE Codex handoff or receipt claimed','outputs':['four candidate INPs','frozen predictor reuse package','preflight/dry-run evidence','prospective protocol'],'new_FE_budget':0}
task=hub.create_task(identity['agent_id'],'MAIN','prospective_input_and_predictor_freeze',payload,'run057-preparation-v1')
hub.approve(task['task_id'],identity['agent_id'],'generate_inp')
hub.approve(task['task_id'],identity['agent_id'],'verify_inp')
lease=hub.claim(task['task_id'],identity,'run057-main-preparation-claim-v1')
save(P/'hub_session.json',{'identity':identity,'lease':lease,'task_id':task['task_id']})
assert hub.verify_chain()
print(json.dumps({'run':'run_057','task_id':task['task_id'],'git_preserved':True,'baseline_input_ODB_hashes_verified':True,'prior_source_count':len(sources)}))
