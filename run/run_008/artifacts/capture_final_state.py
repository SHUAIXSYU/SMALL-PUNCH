import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def git(root,*args): return subprocess.run(['git',*args],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
initial=json.loads((ROOT/'run'/'run_008'/'checkpoints'/'initial_state.json').read_text(encoding='utf-8'))
audit=json.loads((ROOT/'run'/'run_008'/'artifacts'/'private'/'candidate_source_audit.json').read_text(encoding='utf-8'))
odb=json.loads((ROOT/'run'/'run_008'/'artifacts'/'historical_odb_interface.json').read_text(encoding='utf-8'))
mcp=json.loads((ROOT/'run'/'run_008'/'artifacts'/'mcp_readonly_results.json').read_text(encoding='utf-8'))
q=ROOT/'agenthub_sp_invopt'/'abqjobpilot_project'/'runtime'/'queue.json'
abq=Path(r'D:\Projects\abqjobpilot')
placeholder=ROOT/'run'/'run_009'
state={'observed_at':__import__('datetime').datetime.now().astimezone().isoformat(),'main_git':{'branch':git(ROOT,'branch','--show-current'),'head':git(ROOT,'rev-parse','HEAD'),'same_head_as_start':git(ROOT,'rev-parse','HEAD')==initial['git']['head'],'status':git(ROOT,'status','--short','--branch').splitlines()},'preexisting_dirty_inputs':{'CAE/Models/Sanity/SP_InvOpt_Sanity_model.cae':'remained pre-existing modified; not opened or written during run_008; no clean baseline hash existed','CAE/Models/Sanity/SP_InvOpt_Sanity_model.rec':'remained pre-existing deleted; not restored or written during run_008'},'historical_job_inp_sha256':sha(ROOT/'CAE'/'Models'/'Sanity'/'Job-1.inp'),'historical_job_inp_matches_generation_source':sha(ROOT/'CAE'/'Models'/'Sanity'/'Job-1.inp')==audit['source_sha256'],'historical_odb_sha256_after':sha(ROOT/'CAE'/'Models'/'Sanity'/'Job-1.odb'),'historical_odb_matches_before_after':odb['source_sha256_before']==odb['source_sha256_after'],'abqjobpilot_source':{'branch':git(abq,'branch','--show-current'),'head':git(abq,'rev-parse','HEAD'),'same_head_as_start':git(abq,'rev-parse','HEAD')==initial['abqjobpilot']['head'],'status':git(abq,'status','--short','--branch').splitlines()},'abqjobpilot_queue':{'sha256':sha(q),'same_before_after_mcp':mcp['queue_unchanged'],'empty':json.loads(q.read_text(encoding='utf-8'))['jobs']==[]},'stage5_agenthub':'No production database/Project/source writes or enqueue calls made; only selected docs and Python source were read.','parallel_run009_unowned_content':{'exists':placeholder.exists(),'artifacts_directory_nonempty':any((placeholder/'artifacts').iterdir()) if (placeholder/'artifacts').exists() else None,'checkpoints_directory_nonempty':any((placeholder/'checkpoints').iterdir()) if (placeholder/'checkpoints').exists() else None,'appeared_during_run008':placeholder.exists(),'content_inspected':False,'action':'preserved; not reused, modified, or included in this Run'},'solver_invoked':False,'datacheck_invoked':False,'queue_write_performed':False,'recovery_or_retry_performed':False,'commit_performed':False,'push_performed':False}
out=ROOT/'run'/'run_008'/'checkpoints'/'final_state.json'; out.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(state,ensure_ascii=False,indent=2))
