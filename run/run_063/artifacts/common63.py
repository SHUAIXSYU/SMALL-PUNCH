"""Local utilities for the offline run063 study."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,json,csv,hashlib,subprocess
sys.dont_write_bytecode=True
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_063';A=RUN/'artifacts';P=A/'private'
sys.path.insert(0,str(R))
def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rel(p):return Path(p).resolve().relative_to(R.resolve()).as_posix()
def save(p,v):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,v):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(v)
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(p,rs):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('x',encoding='utf-8',newline='') as f:
  keys=list(dict.fromkeys(k for r in rs for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
