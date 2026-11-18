"""MAIN independently parses STA/MSG/DAT; not copied from ODB Agent result."""
from common import *
import re
sys.path.insert(0,str(R/'run/run_056/artifacts'))
from review_science import parse_trials

audit=read(P/'execution_audit.json');out=[]
for point in audit['records']:
    event=parse_trials(point['files'])
    dat=(R/point['files']['dat']['path']).read_text(errors='replace').splitlines()
    datblocks=[{'line':i+1,'text':'\n'.join(dat[i:i+8])} for i,line in enumerate(dat) if re.match(r'\s*\*{3}(WARNING|ERROR)',line,re.I)]
    event.update(candidate_id=point['candidate_id'],DAT_warning_blocks=datblocks)
    save(P/(point['candidate_id']+'_main_raw_events.json'),event)
    out.append(event)
save(P/'main_numerical_audit.json',{'records':out,'scope':'MAIN independent raw event mapping; accepted trial warning is not automatically a final converged state physical failure'})
print(json.dumps([{k:v for k,v in x.items() if k in ['candidate_id','accepted_increments','rejected_attempts','cutback_count','warning_counts']} for x in out]))
