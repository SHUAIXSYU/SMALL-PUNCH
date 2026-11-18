"""MAIN standalone STA/MSG/DAT event audit, independent of returned ODB summaries."""
from pathlib import Path
from collections import Counter
import json,re
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_053/artifacts/private'
audit=json.loads((P/'execution_audit.json').read_text(encoding='utf-8-sig'));records=[]
for r in audit['records']:
 paths={k:R/v['path'] for k,v in r['files'].items()};sta=paths['sta'].read_text(encoding='utf-8',errors='replace').splitlines();trials=[]
 for i,line in enumerate(sta,1):
  f=line.split()
  if len(f)>=9 and f[0].isdigit() and f[1].isdigit() and re.fullmatch(r'\d+U?',f[2]):
   trials.append({'line':i,'increment':int(f[1]),'attempt':int(f[2].rstrip('U')),'accepted':not f[2].endswith('U'),'severe_discontinuity_iterations':int(f[3]),'equilibrium_iterations':int(f[4]),'step_time_printed':float(f[7]),'dt_printed':float(f[8])})
 outcomes={(v['increment'],v['attempt']):v['accepted'] for v in trials};events=[];current=None
 msg=paths['msg'].read_text(encoding='utf-8',errors='replace').splitlines()
 for i,line in enumerate(msg,1):
  m=re.search(r'INCREMENT\s+(\d+)\s+STARTS\.\s+ATTEMPT NUMBER\s+(\d+)',line,re.I)
  if m:current=tuple(map(int,m.groups()))
  if not ('***WARNING' in line.upper() or '***ERROR' in line.upper()):continue
  u=line.upper();kind='ERROR' if '***ERROR' in u else 'NEGATIVE_EIGENVALUES' if 'NEGATIVE EIGENVALUES' in u else 'EXCESSIVE_DISTORTION' if 'EXCESSIVE DISTORTION' in u else 'LARGE_STRAIN_INCREMENT' if 'STRAIN INCREMENT HAS EXCEEDED' in u else 'PLASTICITY_NOT_ATTEMPTED' if 'STRAIN INCREMENT IS SO LARGE' in u else 'ZERO_MOMENT' if 'ZERO MOMENT' in u else 'CONTACT_WARNING' if 'CONTACT' in u else 'OTHER_WARNING'
  accepted=outcomes.get(current);events.append({'line':i,'increment':current[0] if current else None,'attempt':current[1] if current else None,'outcome':'ACCEPTED' if accepted is True else 'REJECTED' if accepted is False else 'UNKNOWN','class':kind,'text':line.strip()})
 dat=paths['dat'].read_text(encoding='utf-8',errors='replace').splitlines();datblocks=[]
 for i,line in enumerate(dat):
  if re.match(r'\s*\*{3}(WARNING|ERROR)',line,re.I):datblocks.append({'line':i+1,'context':'\n'.join(dat[i:i+8])})
 accepted=[v for v in trials if v['accepted']];rejected=[v for v in trials if not v['accepted']]
 assert accepted and accepted[-1]['step_time_printed']==1 and 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in '\n'.join(sta)
 rec={'candidate_id':r['candidate_id'],'accepted_increments':len(accepted),'rejected_attempts':len(rejected),'cutback_increment_count':len({v['increment'] for v in rejected}),'accepted_total_equilibrium_iterations':sum(v['equilibrium_iterations'] for v in accepted),'accepted_total_severe_discontinuity_iterations':sum(v['severe_discontinuity_iterations'] for v in accepted),'warning_counts_by_outcome':{o:dict(Counter(v['class'] for v in events if v['outcome']==o)) for o in ['ACCEPTED','REJECTED','UNKNOWN']},'warning_events':events,'DAT_warning_blocks':datblocks,'rejected_STA_trials':rejected,'accepted_warning_scope':'warns in a trial eventually accepted; not necessarily converged final iteration physical state','no_automatic_scoring_decision':True}
 records.append(rec)
with (P/'main_numeric_event_audit.json').open('x',encoding='utf-8') as f:json.dump({'records':records,'scope':'independent MAIN raw STA/MSG/DAT parse; rejected-trial warnings not accepted physical results'},f,indent=2,allow_nan=False)
print(json.dumps([{k:v for k,v in r.items() if k in ['candidate_id','accepted_increments','rejected_attempts','cutback_increment_count','warning_counts_by_outcome']} for r in records]))
