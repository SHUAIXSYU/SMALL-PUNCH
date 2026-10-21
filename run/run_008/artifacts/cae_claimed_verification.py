"""A fresh CAE role process claims and validates the already-generated INP."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HUBDIR=ROOT/'agenthub_sp_invopt'; sys.path.insert(0,str(HUBDIR))
from hub import Hub
DB=HUBDIR/'runtime'/'sp_invopt.sqlite3'; POLL=HUBDIR/'poll.py'; JOB='SPIO_R008_Q200_N010_Candidate'
INP=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/JOB/(JOB+'.inp'); AUDIT=ROOT/'run'/'run_008'/'artifacts'/'private'/'candidate_source_audit.json'; PARSE=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp_parse.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def poll(role,name,**opts):
    args=[sys.executable,'-B',str(POLL),'--db',str(DB),'--role',role,'--name',name,'--seconds','0']
    for k,v in opts.items():
        if isinstance(v,bool):
            if v: args.append('--'+k.replace('_','-'))
        else: args.extend(['--'+k.replace('_','-'),str(v)])
    r=subprocess.run(args,capture_output=True,text=True,check=True,timeout=20); return json.loads(r.stdout)
def main():
    h=Hub(DB,workspace_root=ROOT); identity=h.register('MAIN','run_008_verification_controller')
    with h.connect() as c: parent=c.execute("SELECT task_id FROM tasks WHERE idempotency_key='run008-candidate-inp-v1'").fetchone()['task_id']
    task=h.create_task(identity['agent_id'],'CAE','candidate_inp_verification',{'inp':str(INP.relative_to(ROOT)).replace('\\','/'),'expected_parser_status':'PASS_ABAQUS_INPUT_PARSE','scope':'static material block, unique job identity and Abaqus 2024 input syntax'},'run008-candidate-verify-v1',[parent])
    tid=task['task_id']
    if task['execution_state']=='PENDING':
        h.message(tid,identity['agent_id'],'CAE',{'objective':'Verify the candidate INP hash, material table and Abaqus parser evidence.'},'run008-verify-instruction-v1'); h.approve(tid,identity['agent_id'],'verify_inp')
        claimed=poll('CAE','run_008_cae_verification_worker'); lease=claimed['lease']; h.require_approval(tid,'verify_inp')
        audit=json.loads(AUDIT.read_text(encoding='utf-8')); parsed=json.loads(PARSE.read_text(encoding='utf-8')); lines=INP.read_text(encoding='utf-8').splitlines()
        assert INP.stem==JOB and INP.parent.name==JOB and sha(INP)==audit['output_sha256']
        p=lines.index('*Plastic'); rows=[]
        for line in lines[p+1:]:
            if line.lstrip().startswith('*'): break
            if line.strip() and not line.lstrip().startswith('**'): rows.append([float(x.strip()) for x in line.split(',')])
        assert parsed['status']=='PASS_ABAQUS_INPUT_PARSE' and len(rows)==35 and rows[0]==[200000000.0,0.0] and abs(rows[-1][1]-.9)<1e-12
        report={'status':'PASS_CAE_CANDIDATE_VERIFY','role':'CAE','execution_status':'COMPLETED','evidence_status':'RECORDED','science_status':'WARNING','task_id':tid,'job_name':JOB,'input_sha256':sha(INP),'abaqus_syntax':'PASS_ABAQUS_INPUT_PARSE','material_rows':len(rows),'final_plastic_strain':rows[-1][1],'physical_validation':'NOT_PERFORMED','settings':'UNKNOWN; AbqJobPilot preflight/dry-run skipped'}
        out=ROOT/'run'/'run_008'/'artifacts'/'cae_candidate_verification.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        h.artifact(tid,lease['agent_id'],INP,{'role':'candidate INP verified by claimed CAE process','sha256':sha(INP)})
        h.artifact(tid,lease['agent_id'],PARSE,{'role':'Abaqus 2024 parser result','scope':'syntax only'})
        art=h.artifact(tid,lease['agent_id'],out,{'role':'structured CAE task result','scope':'candidate syntax and table contract'})
        report['verification_result_sha256']=art['sha256']; h.finish(lease,report,evidence_state='RECORDED',science_state='WARNING'); h.message(tid,lease['agent_id'],'MAIN',report,'run008-verify-result-v1')
    elif task['execution_state']=='COMPLETED':
        report=json.loads(task['result'])
        claimed={'task_id':tid,'claim':'PREVIOUS_CAE_PROCESS_ALREADY_COMPLETED','agent_id':task['lease_agent'],'session_id':task['lease_session'],'generation':task['generation']}
    else: raise RuntimeError('verification task already active or requires recovery; no duplicate worker will claim it')
    with h.connect() as c:
        row=c.execute("SELECT s.session_id FROM sessions s JOIN agents a ON a.agent_id=s.agent_id WHERE a.name='run_008_main_receiver' AND s.closed IS NULL ORDER BY s.opened DESC LIMIT 1").fetchone()
        if not row: raise RuntimeError('existing MAIN receiver session missing')
        main_session=row['session_id']
    with h.connect() as c:
        rows=c.execute("SELECT m.* FROM messages m JOIN message_receipts r ON r.message_id=m.message_id WHERE m.task_id=? AND m.direction='INBOX' AND m.idempotency_key='run008-verify-result-v1' AND r.session_id=?",(tid,main_session)).fetchall()
    received={'identity':h.session_identity(main_session),'messages':[dict(row) for row in rows]}
    if not received['messages']: received=poll('MAIN','run_008_main_receiver',session_id=main_session,messages_only=True)
    result={'verification_task':h.task(tid),'cae_claim':claimed,'main_received_verification':received.get('messages',[]),'audit_hash_chain_valid':h.verify_chain(),'status':report['status']}
    dest=ROOT/'run'/'run_008'/'artifacts'/'cae_verification_handoff.json'; dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
