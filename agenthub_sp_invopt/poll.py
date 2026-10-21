"""Bounded role inbox poller; persistent claim is explicit and never notifies Codex."""
import argparse, json, time
from pathlib import Path
from hub import Hub, HubError

def main():
    p=argparse.ArgumentParser(); p.add_argument('--db',required=True); p.add_argument('--role',required=True,choices=('MAIN','CAE','ODB')); p.add_argument('--name',required=True); p.add_argument('--session-id'); p.add_argument('--seconds',type=int,default=0); p.add_argument('--interval',type=float,default=1.0); p.add_argument('--messages-only',action='store_true'); a=p.parse_args()
    if a.seconds<0 or a.seconds>3600 or not 0.1<=a.interval<=60: p.error('poll bounds: seconds 0..3600, interval 0.1..60')
    h=Hub(a.db); identity=h.session_identity(a.session_id) if a.session_id else h.register(a.role,a.name)
    if identity['role']!=a.role: p.error('session does not match requested role')
    deadline=time.monotonic()+a.seconds
    while True:
        messages=h.poll_messages(identity)
        if messages and a.messages_only:
            print(json.dumps({'identity':identity,'messages':messages},ensure_ascii=False),flush=True); return 0
        if a.messages_only and time.monotonic()>=deadline:
            print(json.dumps({'identity':identity,'poll':'TIMEOUT_NO_MESSAGE'}),flush=True); return 0
        for task in h.inbox(identity):
            try:
                lease=h.claim(task['task_id'],identity,'poll:'+identity['session_id'])
                print(json.dumps({'identity':identity,'messages':messages,'task':task,'lease':lease},ensure_ascii=False),flush=True); return 0
            except HubError as exc:
                print(json.dumps({'identity':identity,'task_id':task['task_id'],'claim':'NOT_CLAIMED','reason':str(exc)}),flush=True)
        if time.monotonic()>=deadline:
            print(json.dumps({'identity':identity,'poll':'TIMEOUT_NO_TASK'}),flush=True); return 0
        time.sleep(min(a.interval,max(0,deadline-time.monotonic())))

if __name__=='__main__': raise SystemExit(main())
