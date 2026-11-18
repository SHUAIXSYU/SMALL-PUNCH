"""Run-local utilities. No solver or queue-write functionality."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, subprocess, sys
R = Path(r'E:\Projects\SMALL-PUNCH')
RUN = R/'run/run_057'
A = RUN/'artifacts'
P = A/'private'
sys.dont_write_bytecode = True

def now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def save(p, value):
    with Path(p).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')

def write(p, text):
    with Path(p).open('x', encoding='utf-8', newline='\n') as f: f.write(text)

def rel(p):
    return Path(p).resolve().relative_to(R.resolve()).as_posix()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=R, text=True).strip()

def split_plastic(raw):
    lines = raw.splitlines(keepends=True)
    hits = [i for i,l in enumerate(lines) if l.strip().upper() == b'*PLASTIC']
    if len(hits) != 1: raise ValueError('expected exactly one Plastic block')
    i = hits[0]+1
    j = i
    while j<len(lines) and not lines[j].lstrip().startswith(b'*'): j += 1
    values = [tuple(map(float,l.strip().split(b','))) for l in lines[i:j] if l.strip()]
    return b''.join(lines[:i]), b''.join(lines[j:]), values

def effective_skeleton(raw):
    pre, post, _ = split_plastic(raw)
    return b'\n'.join(l.strip() for l in (pre+post).splitlines() if l.strip() and not l.strip().startswith(b'**'))
