"""Simulate MAIN -> CAE -> ODB -> MAIN through independent SQLite poller processes."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HUBDIR=ROOT/'agenthub_sp_invopt'; sys.path.insert(0,str(HUBDIR))
from hub import Hub,HubError
DB=HUBDIR/'runtime'/'sp_invopt.sqlite3'; POLL=HUBDIR/'poll.py'; JOB='SPIO_R008_Q200_N010_Candidate'
INP=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/JOB/(JOB+'.inp')
ODB=ROOT/'CAE'/'Models'/'Sanity'/'Job-1.odb'; ODBJSON=ROOT/'run'/'run_008'/'artifacts'/'historical_odb_interface.json'
PROJ=HUBDIR/'abqjobpilot_project'/'project.json'; QUEUE=HUBDIR/'abqjobpilot_project'/'runtime'/'queue.json'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def poll(role,name,*,messages=False):
    args=[sys.executable,'-B',str(POLL),'--db',str(DB),'--role',role,'--name',name,'--seconds','0']
    if messages: args.append('--messages-only')
    r=subprocess.run(args,capture_output=True,text=True,check=True,timeout=20)
    return json.loads(r.stdout)
def main():
    if DB.exists(): raise SystemExit('REFUSE_EXISTING_SP_INVOPT_LEDGER')
    if not all(p.is_file() for p in (INP,ODB,ODBJSON,PROJ,QUEUE)): raise SystemExit('REQUIRED_CANDIDATE_PROJECT_OR_ODB_EVIDENCE_MISSING')
    qbefore=sha(QUEUE); h=Hub(DB); main_id=h.register('MAIN','run_008_controller')
    cae=h.create_task(main_id['agent_id'],'CAE','candidate_inp_generation',{'candidate_inp':str(INP.relative_to(ROOT)).replace('\\','/'),'job_name':JOB,'settings':'UNKNOWN; preflight and dry-run blocked'},'run008-candidate-inp-v1')
    task=cae['task_id']; h.message(task,main_id['agent_id'],'CAE',{'objective':'Register and validate the run_008 candidate INP; Abq preview only if verified Settings exist.'},'main-to-cae-v1')
    h.approve(task,main_id['agent_id'],'generate_inp')
    claimed=poll('CAE','run_008_cae_worker'); lease=claimed['lease']
    h.require_approval(task,'generate_inp')
    inp_art=h.artifact(task,lease['agent_id'],INP,{'source':'generated in this run from historical Job-1 input; *Plastic replaced','candidate_model':'true-total Hollomon, not physically validated'})
    cae_result={'role':'CAE','execution_status':'COMPLETED','evidence_status':'RECORDED','science_status':'WARNING','candidate_inp':str(INP.relative_to(ROOT)).replace('\\','/'),'job_name':JOB,'working_directory':str(INP.parent.relative_to(ROOT)).replace('\\','/'),'inp_sha256':inp_art['sha256'],'abqjobpilot_project_id':json.loads(PROJ.read_text(encoding='utf-8'))['project_id'],'preflight':'BLOCKED_SETTINGS_UNKNOWN','dry_run_enqueue':'BLOCKED_SETTINGS_UNKNOWN','queue_write':'NOT_AUTHORIZED','solver':'NOT_AUTHORIZED'}
    h.finish(lease,cae_result,evidence_state='RECORDED',science_state='WARNING'); h.message(task,lease['agent_id'],'MAIN',cae_result,'cae-to-main-result-v1')
    odbtask=h.create_task(main_id['agent_id'],'ODB','historical_odb_interface_regression',{'odb':'CAE/Models/Sanity/Job-1.odb','purpose':'read-only reader API regression only','candidate_solve_claim':False},'run008-historical-odb-v1',[task])
    o_task=odbtask['task_id']; h.message(o_task,main_id['agent_id'],'ODB',{'objective':'Verify read-only U2/RF2 history interface on historical Job-1.odb; do not infer candidate response.'},'main-to-odb-v1')
    oc=poll('ODB','run_008_odb_worker'); ol=oc['lease']
    ajson=h.artifact(o_task,ol['agent_id'],ODBJSON,{'source':'Abaqus 2024 SMAPython readOnly=True interface scan','role':'ODB metadata and history count'})
    aodb=h.artifact(o_task,ol['agent_id'],ODB,{'source':'historical immutable ODB; readOnly=True','role':'reader regression input; not candidate result'})
    odb_result={'role':'ODB','execution_status':'COMPLETED','evidence_status':'RECORDED','science_status':'NOT_EVALUATED','interface':'PASS_INTERFACE_ONLY','history_samples':181,'candidate_solve':'NOT_PERFORMED','odb_sha256':aodb['sha256'],'interface_evidence_sha256':ajson['sha256']}
    h.finish(ol,odb_result,evidence_state='RECORDED',science_state='NOT_EVALUATED'); h.message(o_task,ol['agent_id'],'MAIN',odb_result,'odb-to-main-result-v1')
    received=poll('MAIN','run_008_main_receiver',messages=True)
    denies={}
    for action in ('enqueue','start_solver'):
        try: h.authorize_external_action(task,action); denies[action]='UNEXPECTED_ALLOW'
        except HubError as exc: denies[action]=str(exc)
    try: h.require_approval(task,'recover_retry'); denies['recover_retry']='UNEXPECTED_ALLOW'
    except HubError as exc: denies['recover_retry']=str(exc)
    qafter=sha(QUEUE); summary={'simulation':'PASS_LOCAL_PROCESS_HANDOFF_WITH_MANUAL_CODEX_HANDOFF_RETAINED','task_ids':{'cae':task,'odb':o_task},'claims':{'cae':claimed,'odb':oc},'main_received_messages':received.get('messages',[]),'cae_result':cae_result,'odb_result':odb_result,'task_states':{'cae':h.task(task),'odb':h.task(o_task)},'authorization_denials':denies,'abqjobpilot_queue_sha256_before':qbefore,'abqjobpilot_queue_sha256_after':qafter,'queue_unchanged':qbefore==qafter,'audit_hash_chain_valid':h.verify_chain(),'scientific_result':'NOT_EVALUATED','codex_cross_session_delivery':'NOT_IMPLEMENTED; role polls are tested in real local processes; manual Handoff remains required'}
    if not summary['queue_unchanged'] or not summary['audit_hash_chain_valid'] or len(summary['main_received_messages'])!=2: raise SystemExit('END_TO_END_ACCEPTANCE_FAILED')
    out=ROOT/'run'/'run_008'/'artifacts'/'end_to_end_simulation.json'; out.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
