import json
import os
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(HERE/'agenthub_sp_invopt'))
from hub import Hub, HubError

class HubTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.h=Hub(self.root/'ledger.sqlite3',lease_seconds=2)
        self.main=self.h.register('MAIN','test'); self.cae=self.h.register('CAE','worker'); self.odb=self.h.register('ODB','worker')
    def tearDown(self): self.temp.cleanup()
    def task(self,role='CAE',key='one',depends=()): return self.h.create_task(self.main['agent_id'],role,'candidate',{'x':1},key,depends)['task_id']
    def test_e2e_roles_approval_messages_and_separate_states(self):
        t=self.task(); self.h.message(t,self.main['agent_id'],'CAE',{'instruction':'generate'},'msg1')
        self.assertEqual(self.h.message(t,self.main['agent_id'],'CAE',{'instruction':'generate'},'msg1')['message_id'],self.h.message(t,self.main['agent_id'],'CAE',{'instruction':'generate'},'msg1')['message_id'])
        with self.assertRaisesRegex(HubError,'APPROVAL_REQUIRED'): self.h.require_approval(t,'generate_inp')
        self.h.approve(t,self.main['agent_id'],'generate_inp'); self.h.require_approval(t,'generate_inp')
        lease=self.h.claim(t,self.cae,'claim1'); self.h.heartbeat(lease)
        evidence=self.root/'candidate.inp'; evidence.write_text('*Heading\n',encoding='utf-8')
        a=self.h.artifact(t,self.cae['agent_id'],evidence,{'source':'test fixture','role':'candidate INP'})
        self.assertEqual(a['sha256'],self.h.artifact(t,self.cae['agent_id'],evidence,{'source':'test fixture','role':'candidate INP'})['sha256'])
        self.h.finish(lease,{'execution':'completed','scientific':'unvalidated'},science_state='WARNING')
        child=self.task('ODB','two',[t]); ol=self.h.claim(child,self.odb,'odb-read'); self.h.finish(ol,{'historical_odb':'read-only interface fixture'},science_state='NOT_EVALUATED')
        row=self.h.task(child); self.assertEqual((row['execution_state'],row['evidence_state'],row['science_state']),('COMPLETED','RECORDED','NOT_EVALUATED'))
    def test_idempotency_claim_exclusion_and_message_conflict(self):
        t=self.task(); self.assertEqual(self.task(),t)
        with self.assertRaisesRegex(HubError,'IDEMPOTENCY_CONFLICT'): self.h.create_task(self.main['agent_id'],'CAE','candidate',{'x':2},'one')
        lease=self.h.claim(t,self.cae,'one')
        with self.assertRaisesRegex(HubError,'TASK_NOT_CLAIMABLE'): self.h.claim(t,self.cae,'two')
        self.h.message(t,self.main['agent_id'],'CAE',{'instruction':'original'},'msg1')
        with self.assertRaisesRegex(HubError,'MESSAGE_IDEMPOTENCY_CONFLICT'): self.h.message(t,self.main['agent_id'],'CAE',{'instruction':'different'},'msg1')
        self.assertTrue(self.h.verify_chain())
    def test_lease_crash_recovery_requires_confirmed_worker_exit(self):
        t=self.task(); lease=self.h.claim(t,self.cae,'first',now=10)
        with self.assertRaisesRegex(HubError,'RECOVERY_REQUIRED'): self.h.claim(t,self.cae,'second',now=lease['lease_until']+1)
        self.assertEqual(self.h.task(t)['execution_state'],'RECOVERY_REQUIRED')
        with self.assertRaisesRegex(HubError,'WORKER_STATUS_UNCONFIRMED'): self.h.recover(t,self.main['agent_id'],worker_stopped_confirmed=False)
        with self.assertRaisesRegex(HubError,'TASK_APPROVAL_REQUIRED'): self.h.recover(t,self.main['agent_id'],worker_stopped_confirmed=True)
        self.h.approve(t,self.main['agent_id'],'recover_retry')
        self.h.recover(t,self.main['agent_id'],worker_stopped_confirmed=True)
        self.assertEqual(self.h.task(t)['execution_state'],'PENDING')
        self.assertEqual(self.h.claim(t,self.cae,'retry')['generation'],2)
    def test_distinct_enqueue_solver_retry_approvals(self):
        t=self.task()
        for action in ('enqueue','start_solver','recover_retry'):
            with self.assertRaises(HubError): self.h.require_approval(t,action)
        self.h.approve(t,self.main['agent_id'],'enqueue')
        self.h.require_approval(t,'enqueue')
        for action in ('start_solver','recover_retry'):
            with self.assertRaises(HubError): self.h.require_approval(t,action)
        with self.assertRaisesRegex(HubError,'EXTERNAL_ACTION_DISABLED'): self.h.authorize_external_action(t,'enqueue')
        with self.assertRaisesRegex(HubError,'TASK_APPROVAL_REQUIRED'): self.h.authorize_external_action(t,'start_solver')
        self.h.approve(t,self.main['agent_id'],'start_solver')
        with self.assertRaisesRegex(HubError,'EXTERNAL_ACTION_DISABLED'): self.h.authorize_external_action(t,'start_solver')
        with self.assertRaisesRegex(HubError,'APPROVAL_DENIED'): self.h.approve(t,self.cae['agent_id'],'start_solver')
    def test_real_poll_process_claims_only_once(self):
        t=self.task(); script=HERE/'agenthub_sp_invopt'/'poll.py'; db=self.h.path
        cmd=[sys.executable,'-B',str(script),'--db',str(db),'--role','CAE','--name','poll-process','--seconds','0']
        first=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=15)
        self.assertEqual(json.loads(first.stdout)['task']['task_id'],t)
        second=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=15)
        self.assertEqual(json.loads(second.stdout)['poll'],'TIMEOUT_NO_TASK')
        self.assertTrue(self.h.verify_chain())
    def test_persistent_inbox_receipt_is_distinct_from_outbox_and_claim(self):
        t=self.task(role='ODB'); self.h.message(t,self.main['agent_id'],'ODB',{'handoff':'read historical ODB'},'odb-msg')
        polled=self.h.poll_messages(self.odb)
        self.assertEqual(len(polled),1); self.assertEqual(polled[0]['direction'],'INBOX')
        self.assertEqual(self.h.poll_messages(self.odb),[])
        self.assertEqual(self.h.poll_messages(self.h.session_identity(self.odb['session_id'])),[])
        self.assertEqual(self.h.inbox(self.odb)[0]['task_id'],t)

    def test_two_concurrent_sessions_have_exactly_one_claim_winner(self):
        t=self.task(); workers=[self.h.register('CAE','race-a'),self.h.register('CAE','race-b')]; gate=threading.Barrier(2)
        def run(item):
            gate.wait()
            try: return ('CLAIMED',self.h.claim(t,item,'race'))
            except HubError as exc: return ('DENIED',str(exc))
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(run,workers))
        self.assertEqual(sum(x[0]=='CLAIMED' for x in outcomes),1)
        self.assertEqual(sum(x[0]=='DENIED' for x in outcomes),1)

    def test_role_scope_rejects_forged_sessions_and_cross_role_evidence(self):
        t=self.task()
        forged=dict(self.cae,session_id='not-a-session')
        with self.assertRaisesRegex(HubError,'SESSION_IDENTITY_INVALID'): self.h.claim(t,forged,'forged')
        fixture=self.root/'evidence.txt'; fixture.write_text('test',encoding='utf-8')
        with self.assertRaisesRegex(HubError,'ARTIFACT_SCOPE_DENIED'): self.h.artifact(t,self.odb['agent_id'],fixture,{'source':'forbidden'})

if __name__=='__main__': unittest.main(verbosity=2)
