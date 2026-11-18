"""Run059 local read-only analysis helpers."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,subprocess,sys,csv
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_059';A=RUN/'artifacts';P=A/'private'
sys.dont_write_bytecode=True
def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rel(p):return Path(p).resolve().relative_to(R.resolve()).as_posix()
def save(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,v):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(v)
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(p,v):
 with Path(p).open('x',encoding='utf-8',newline='') as f:
  keys=list(dict.fromkeys(k for r in v for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(v)
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
