"""Small, standard-library-only SQLite AgentHub scoped to SP-InvOpt."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROLES = {"MAIN", "CAE", "ODB", "AGENTHUB"}
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS agents(agent_id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN ('MAIN','CAE','ODB')), name TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents, opened REAL NOT NULL, closed REAL);
CREATE TABLE IF NOT EXISTS maintenance_agents(agent_id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role='AGENTHUB'), name TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS maintenance_sessions(session_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES maintenance_agents, opened REAL NOT NULL, closed REAL);
CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY, created_by TEXT NOT NULL REFERENCES agents, assigned_role TEXT NOT NULL CHECK(assigned_role IN ('MAIN','CAE','ODB')), kind TEXT NOT NULL, payload TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, execution_state TEXT NOT NULL, evidence_state TEXT NOT NULL, science_state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, lease_agent TEXT, lease_session TEXT, lease_token TEXT, lease_until REAL, generation INTEGER NOT NULL DEFAULT 0, result TEXT);
CREATE TABLE IF NOT EXISTS dependencies(task_id TEXT NOT NULL REFERENCES tasks, depends_on TEXT NOT NULL REFERENCES tasks, PRIMARY KEY(task_id,depends_on), CHECK(task_id<>depends_on));
CREATE TABLE IF NOT EXISTS approvals(task_id TEXT NOT NULL REFERENCES tasks, action TEXT NOT NULL, approved_by TEXT NOT NULL REFERENCES agents, approved REAL NOT NULL, PRIMARY KEY(task_id,action));
CREATE TABLE IF NOT EXISTS messages(message_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks, sender TEXT NOT NULL REFERENCES agents, recipient_role TEXT NOT NULL CHECK(recipient_role IN ('MAIN','CAE','ODB')), direction TEXT NOT NULL CHECK(direction IN ('INBOX','OUTBOX')), idempotency_key TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL, UNIQUE(task_id,direction,idempotency_key));
CREATE TABLE IF NOT EXISTS message_receipts(message_id TEXT NOT NULL REFERENCES messages, session_id TEXT NOT NULL REFERENCES sessions, received REAL NOT NULL, PRIMARY KEY(message_id,session_id));
CREATE TABLE IF NOT EXISTS artifacts(artifact_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks, producer TEXT NOT NULL REFERENCES agents, path TEXT NOT NULL, sha256 TEXT NOT NULL, provenance TEXT NOT NULL, created REAL NOT NULL, UNIQUE(task_id,path,sha256));
CREATE TABLE IF NOT EXISTS failures(failure_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks, agent_id TEXT NOT NULL REFERENCES agents, generation INTEGER NOT NULL, code TEXT NOT NULL, detail TEXT NOT NULL, retryable INTEGER NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, actor TEXT NOT NULL, event TEXT NOT NULL, data TEXT NOT NULL, at REAL NOT NULL, at_iso TEXT, prev_hash TEXT NOT NULL, hash TEXT NOT NULL UNIQUE);
"""

class HubError(RuntimeError): pass

class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()

class Hub:
    def __init__(self, db: str | Path, *, lease_seconds: int = 30, workspace_root: str | Path | None = None):
        self.path = Path(db)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if workspace_root is not None: self.workspace_root=Path(workspace_root).resolve()
        elif self.path.parent.name=='runtime' and self.path.parent.parent.name=='agenthub_sp_invopt': self.workspace_root=self.path.parent.parent.parent.resolve()
        else: self.workspace_root=self.path.parent.resolve()
        self.lease_seconds = lease_seconds
        with self.connect() as c: c.executescript(SCHEMA)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            columns={r['name'] for r in c.execute("PRAGMA table_info(events)")}
            if 'at_iso' not in columns: c.execute("ALTER TABLE events ADD COLUMN at_iso TEXT")
            columns={r['name'] for r in c.execute("PRAGMA table_info(artifacts)")}
            if 'version' not in columns: c.execute("ALTER TABLE artifacts ADD COLUMN version TEXT NOT NULL DEFAULT '1'")

    def connect(self):
        c = sqlite3.connect(self.path, timeout=5, isolation_level=None, factory=_ClosingConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        return c

    @staticmethod
    def _event(c, task, actor, name, data):
        prev = c.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev_hash = prev[0] if prev else "0"*64
        at = time.time(); payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        iso=datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(f"{prev_hash}|{task}|{actor}|{name}|{payload}|{at:.9f}|{iso}".encode()).hexdigest()
        c.execute("INSERT INTO events(task_id,actor,event,data,at,at_iso,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?)", (task,actor,name,payload,at,iso,prev_hash,digest))

    @staticmethod
    def _identity(c, identity):
        row=c.execute("SELECT a.role,s.closed FROM agents a JOIN sessions s ON s.agent_id=a.agent_id WHERE a.agent_id=? AND s.session_id=?",(identity.get('agent_id'),identity.get('session_id'))).fetchone()
        if row is None and identity.get('role')=='AGENTHUB':
            row=c.execute("SELECT a.role,s.closed FROM maintenance_agents a JOIN maintenance_sessions s ON s.agent_id=a.agent_id WHERE a.agent_id=? AND s.session_id=?",(identity.get('agent_id'),identity.get('session_id'))).fetchone()
        if not row or row['closed'] is not None or row['role']!=identity.get('role'): raise HubError('SESSION_IDENTITY_INVALID')

    def register(self, role, name):
        if role not in ROLES: raise HubError("ROLE_DENIED")
        aid = f"{role}:{name}"
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            agent_table = 'maintenance_agents' if role=='AGENTHUB' else 'agents'
            session_table = 'maintenance_sessions' if role=='AGENTHUB' else 'sessions'
            c.execute(f"INSERT OR IGNORE INTO {agent_table} VALUES(?,?,?,?)", (aid,role,name,time.time()))
            sid = str(uuid.uuid4()); c.execute(f"INSERT INTO {session_table} VALUES(?,?,?,NULL)",(sid,aid,time.time()))
            self._event(c,None,aid,"SESSION_OPENED",{"session_id":sid,"role":role})
            return {"agent_id":aid,"session_id":sid,"role":role}

    def session_identity(self, session_id):
        with self.connect() as c:
            row=c.execute("SELECT a.agent_id,a.role,s.session_id FROM agents a JOIN sessions s ON s.agent_id=a.agent_id WHERE s.session_id=? AND s.closed IS NULL",(session_id,)).fetchone()
            if row is None:
                row=c.execute("SELECT a.agent_id,a.role,s.session_id FROM maintenance_agents a JOIN maintenance_sessions s ON s.agent_id=a.agent_id WHERE s.session_id=? AND s.closed IS NULL",(session_id,)).fetchone()
            if not row: raise HubError('SESSION_IDENTITY_INVALID')
            return dict(row)

    def create_task(self, actor, role, kind, payload, key, depends=()):
        if role not in ROLES or actor.split(":",1)[0] != "MAIN": raise HubError("CREATE_DENIED")
        if not key: raise HubError("IDEMPOTENCY_KEY_REQUIRED")
        depends=tuple(depends)
        body=json.dumps(payload,sort_keys=True,separators=(",",":"))
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM agents WHERE agent_id=? AND role='MAIN'",(actor,)).fetchone() is None: raise HubError("CREATE_DENIED")
            old=c.execute("SELECT * FROM tasks WHERE idempotency_key=?",(key,)).fetchone()
            if old:
                old_deps=tuple(r[0] for r in c.execute("SELECT depends_on FROM dependencies WHERE task_id=? ORDER BY depends_on",(old["task_id"],)))
                if old["payload"]!=body or old["assigned_role"]!=role or old["kind"]!=kind or old_deps!=tuple(sorted(depends)): raise HubError("IDEMPOTENCY_CONFLICT")
                return dict(old)
            tid=str(uuid.uuid4())
            c.execute("INSERT INTO tasks(task_id,created_by,assigned_role,kind,payload,idempotency_key,execution_state,evidence_state,science_state) VALUES(?,?,?,?,?,?,?,?,?)",(tid,actor,role,kind,body,key,"PENDING","NONE","NOT_EVALUATED"))
            for dep in depends: c.execute("INSERT INTO dependencies VALUES(?,?)",(tid,dep))
            self._event(c,tid,actor,"TASK_CREATED",{"role":role,"kind":kind,"depends":list(depends),"key":key})
            return dict(c.execute("SELECT * FROM tasks WHERE task_id=?",(tid,)).fetchone())

    def claim(self, task, identity, key, *, now=None):
        if not key: raise HubError('CLAIM_IDEMPOTENCY_KEY_REQUIRED')
        at=time.time() if now is None else now; role=identity["role"]
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self._identity(c,identity)
            row=c.execute("SELECT * FROM tasks WHERE task_id=?",(task,)).fetchone()
            if not row or row["assigned_role"]!=role: raise HubError("CLAIM_DENIED")
            if row["execution_state"]=="CLAIMED" and row["lease_until"]<=at:
                c.execute("UPDATE tasks SET execution_state='RECOVERY_REQUIRED',revision=revision+1 WHERE task_id=?",(task,)); self._event(c,task,identity["agent_id"],"LEASE_EXPIRED",{"generation":row["generation"]}); c.commit(); raise HubError("RECOVERY_REQUIRED")
            if row["execution_state"]!="PENDING": raise HubError("TASK_NOT_CLAIMABLE")
            unmet=c.execute("SELECT COUNT(*) FROM dependencies d JOIN tasks p ON p.task_id=d.depends_on WHERE d.task_id=? AND p.execution_state!='COMPLETED'",(task,)).fetchone()[0]
            if unmet: raise HubError("DEPENDENCY_BLOCKED")
            token=uuid.uuid4().hex; until=at+self.lease_seconds
            c.execute("UPDATE tasks SET execution_state='CLAIMED',lease_agent=?,lease_session=?,lease_token=?,lease_until=?,generation=generation+1,revision=revision+1 WHERE task_id=?",(identity["agent_id"],identity["session_id"],token,until,task))
            self._event(c,task,identity["agent_id"],"TASK_CLAIMED",{"generation":row["generation"]+1,"session":identity["session_id"],"idempotency_key":key})
            return {"task_id":task,"agent_id":identity["agent_id"],"session_id":identity["session_id"],"token":token,"generation":row["generation"]+1,"lease_until":until}

    def heartbeat(self, lease):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE"); row=c.execute("SELECT * FROM tasks WHERE task_id=?",(lease["task_id"],)).fetchone()
            self._valid(row,lease); until=time.time()+self.lease_seconds
            c.execute("UPDATE tasks SET lease_until=?,revision=revision+1 WHERE task_id=?",(until,lease["task_id"]))
            self._event(c,lease["task_id"],lease["agent_id"],"HEARTBEAT",{"until":until})
            return until

    @staticmethod
    def _valid(row,lease):
        if not row or row["execution_state"]!="CLAIMED" or row["lease_token"]!=lease["token"] or row["lease_agent"]!=lease["agent_id"] or row["lease_session"]!=lease["session_id"] or row["generation"]!=lease["generation"] or row["lease_until"]<time.time(): raise HubError("LEASE_INVALID")

    def recover(self, task, actor, *, worker_stopped_confirmed):
        if not worker_stopped_confirmed: raise HubError("WORKER_STATUS_UNCONFIRMED")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM agents WHERE agent_id=? AND role='MAIN'",(actor,)).fetchone() is None: raise HubError('RECOVERY_DENIED')
            row=c.execute("SELECT * FROM tasks WHERE task_id=?",(task,)).fetchone()
            if not row or row["execution_state"]!="RECOVERY_REQUIRED": raise HubError("RECOVERY_NOT_REQUIRED")
            if c.execute("SELECT 1 FROM approvals WHERE task_id=? AND action='recover_retry'",(task,)).fetchone() is None: raise HubError("TASK_APPROVAL_REQUIRED:recover_retry")
            c.execute("UPDATE tasks SET execution_state='PENDING',lease_agent=NULL,lease_session=NULL,lease_token=NULL,lease_until=NULL,revision=revision+1 WHERE task_id=?",(task,))
            self._event(c,task,actor,"RECOVERY_CONFIRMED",{"worker_stopped_confirmed":True})

    def message(self, task, sender, recipient_role, body, key, direction="OUTBOX"):
        if not key: raise HubError('MESSAGE_IDEMPOTENCY_KEY_REQUIRED')
        if recipient_role not in ROLES or direction not in ("OUTBOX","INBOX"): raise HubError("MESSAGE_SCOPE_DENIED")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE"); old=c.execute("SELECT * FROM messages WHERE task_id=? AND direction=? AND idempotency_key=?",(task,direction,key)).fetchone()
            task_row=c.execute("SELECT assigned_role,created_by,lease_agent FROM tasks WHERE task_id=?",(task,)).fetchone()
            agent=c.execute("SELECT role FROM agents WHERE agent_id=?",(sender,)).fetchone()
            if not task_row or not agent or agent['role'] not in {'MAIN',task_row['assigned_role']} or recipient_role not in {'MAIN',task_row['assigned_role']}: raise HubError('MESSAGE_SCOPE_DENIED')
            if sender not in (task_row['created_by'],task_row['lease_agent']): raise HubError('MESSAGE_TASK_DENIED')
            text=json.dumps(body,sort_keys=True,separators=(",",":"))
            if old:
                if old["body"]!=text or old['sender']!=sender or old['recipient_role']!=recipient_role: raise HubError("MESSAGE_IDEMPOTENCY_CONFLICT")
                return dict(old)
            if direction!="OUTBOX": raise HubError("SEND_DIRECTION_MUST_BE_OUTBOX")
            now=time.time(); out_id=str(uuid.uuid4()); in_id=str(uuid.uuid4())
            c.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)",(out_id,task,sender,recipient_role,"OUTBOX",key,text,now))
            c.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)",(in_id,task,sender,recipient_role,"INBOX",key,text,now))
            self._event(c,task,sender,"MESSAGE_PERSISTED",{"outbox_id":out_id,"inbox_id":in_id,"to":recipient_role,"key":key})
            return dict(c.execute("SELECT * FROM messages WHERE message_id=?",(out_id,)).fetchone())

    def poll_messages(self, identity):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            self._identity(c,identity)
            rows=c.execute("SELECT m.* FROM messages m JOIN tasks t ON t.task_id=m.task_id WHERE m.direction='INBOX' AND m.recipient_role=? AND t.execution_state IN ('PENDING','CLAIMED','COMPLETED') AND NOT EXISTS (SELECT 1 FROM message_receipts r WHERE r.message_id=m.message_id AND r.session_id=?) ORDER BY m.created",(identity['role'],identity['session_id'])).fetchall()
            output=[]
            for row in rows:
                c.execute("INSERT INTO message_receipts VALUES(?,?,?)",(row['message_id'],identity['session_id'],time.time()))
                self._event(c,row['task_id'],identity['agent_id'],"MESSAGE_RECEIVED",{"message_id":row['message_id'],'session_id':identity['session_id']})
                output.append(dict(row))
            return output

    def approve(self, task, actor, action):
        if actor.split(":",1)[0]!="MAIN" or action not in {"generate_inp","verify_inp","enqueue","start_solver","recover_retry"}: raise HubError("APPROVAL_DENIED")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM agents WHERE agent_id=? AND role='MAIN'",(actor,)).fetchone() is None: raise HubError("APPROVAL_DENIED")
            c.execute("INSERT OR IGNORE INTO approvals VALUES(?,?,?,?)",(task,action,actor,time.time()))
            self._event(c,task,actor,"TASK_APPROVAL",{"action":action})

    def require_approval(self, task, action):
        with self.connect() as c:
            ok=c.execute("SELECT 1 FROM approvals WHERE task_id=? AND action=?",(task,action)).fetchone()
            if not ok: raise HubError("TASK_APPROVAL_REQUIRED:"+action)

    def authorize_external_action(self, task, action):
        if action not in {"enqueue","start_solver","recover_retry"}: raise HubError("EXTERNAL_ACTION_UNKNOWN")
        self.require_approval(task,action)
        raise HubError("EXTERNAL_ACTION_DISABLED_IN_RUN008")

    def task(self, task):
        with self.connect() as c:
            row=c.execute("SELECT * FROM tasks WHERE task_id=?",(task,)).fetchone()
            return dict(row) if row else None

    def artifact(self, task, producer, path, provenance, *, version="1"):
        if not version: raise HubError('ARTIFACT_VERSION_REQUIRED')
        p=Path(path).resolve()
        if not p.is_relative_to(self.workspace_root): raise HubError('ARTIFACT_OUTSIDE_WORKSPACE')
        sh=hashlib.sha256()
        with p.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): sh.update(chunk)
        digest=sh.hexdigest()
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE"); task_row=c.execute("SELECT assigned_role,lease_agent,execution_state FROM tasks WHERE task_id=?",(task,)).fetchone(); agent=c.execute("SELECT role FROM agents WHERE agent_id=?",(producer,)).fetchone()
            if not task_row or not agent or agent['role'] not in {'MAIN',task_row['assigned_role']}: raise HubError('ARTIFACT_SCOPE_DENIED')
            if task_row['lease_agent']!=producer or task_row['execution_state']!='CLAIMED': raise HubError('ARTIFACT_LEASE_REQUIRED')
            old=c.execute("SELECT * FROM artifacts WHERE task_id=? AND path=? AND sha256=?",(task,str(p),digest)).fetchone()
            if old:
                if old['version']!=version: raise HubError('ARTIFACT_VERSION_CONFLICT')
                return dict(old)
            aid=str(uuid.uuid4()); c.execute("INSERT INTO artifacts(artifact_id,task_id,producer,path,sha256,provenance,created,version) VALUES(?,?,?,?,?,?,?,?)",(aid,task,producer,str(p),digest,json.dumps(provenance,sort_keys=True),time.time(),version))
            self._event(c,task,producer,"ARTIFACT_REGISTERED",{"path":str(p),"sha256":digest,"version":version,"provenance":provenance})
            return dict(c.execute("SELECT * FROM artifacts WHERE artifact_id=?",(aid,)).fetchone())

    def finish(self, lease, result, *, evidence_state="RECORDED", science_state="NOT_EVALUATED"):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE"); row=c.execute("SELECT * FROM tasks WHERE task_id=?",(lease["task_id"],)).fetchone(); self._valid(row,lease)
            encoded=json.dumps(result,sort_keys=True,separators=(",",":"))
            c.execute("UPDATE tasks SET execution_state='COMPLETED',evidence_state=?,science_state=?,result=?,revision=revision+1,lease_token=NULL,lease_until=NULL WHERE task_id=?",(evidence_state,science_state,encoded,lease["task_id"]))
            self._event(c,lease["task_id"],lease["agent_id"],"TASK_COMPLETED",{"execution":"COMPLETED","evidence":evidence_state,"science":science_state,"result":result})

    def fail(self, lease, code, detail, *, retryable=False, evidence_state="INCOMPLETE", science_state="NOT_EVALUATED"):
        if not code or not detail: raise HubError('FAILURE_DIAGNOSIS_REQUIRED')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM tasks WHERE task_id=?',(lease['task_id'],)).fetchone()
            self._valid(row,lease)
            fid=str(uuid.uuid4())
            c.execute('INSERT INTO failures VALUES(?,?,?,?,?,?,?,?)',(fid,lease['task_id'],lease['agent_id'],lease['generation'],code,detail,int(retryable),time.time()))
            c.execute("UPDATE tasks SET execution_state='FAILED',evidence_state=?,science_state=?,revision=revision+1,lease_token=NULL,lease_until=NULL WHERE task_id=?",(evidence_state,science_state,lease['task_id']))
            self._event(c,lease['task_id'],lease['agent_id'],'TASK_FAILED',{'failure_id':fid,'code':code,'detail':detail,'retryable':retryable})
            return fid

    def diagnostics(self, task):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM failures WHERE task_id=? ORDER BY created',(task,))]

    def inbox(self, identity):
        with self.connect() as c:
            self._identity(c,identity)
            rows=c.execute("SELECT task_id,kind,payload,execution_state FROM tasks WHERE assigned_role=? AND execution_state='PENDING' ORDER BY rowid",(identity['role'],)).fetchall()
            return [dict(r) for r in rows]

    def verify_chain(self):
        prev="0"*64
        with self.connect() as c:
            for r in c.execute("SELECT * FROM events ORDER BY seq"):
                base=f"{prev}|{r['task_id']}|{r['actor']}|{r['event']}|{r['data']}|{r['at']:.9f}"
                if r['at_iso'] is not None: base+=f"|{r['at_iso']}"
                expected=hashlib.sha256(base.encode()).hexdigest()
                if r["prev_hash"]!=prev or r["hash"]!=expected: return False
                prev=r["hash"]
        return True
