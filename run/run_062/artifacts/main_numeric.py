"""MAIN independently maps each accepted STA attempt to its own MSG block."""
from common62 import *
import re
sys.path.insert(0,str(R/'run/run_056/artifacts'));from review_science import parse_trials

def audit(files):
 event=parse_trials(files);sta=(R/files['sta']['path']).read_text(errors='replace');msg=(R/files['msg']['path']).read_text(errors='replace')
 trials=[]
 for lineno,line in enumerate(sta.splitlines(),1):
  w=line.split()
  if len(w)>=9 and w[0].isdigit() and w[1].isdigit() and re.fullmatch(r'\d+U?',w[2]):
   trials.append({'line':lineno,'increment':int(w[1]),'attempt':int(w[2].rstrip('U')),'accepted':not w[2].endswith('U'),'step_time':float(w[7]),'dt':float(w[8]),'equilibrium_iterations':int(w[4])})
 hits=list(re.finditer(r'INCREMENT\s+(\d+)\s+STARTS\.\s+ATTEMPT NUMBER\s+(\d+)',msg,re.I));blocks={}
 for i,h in enumerate(hits):blocks[tuple(map(int,h.groups()))]=msg[h.start():hits[i+1].start() if i+1<len(hits) else len(msg)]
 accepted=[]
 for v in trials:
  if not v['accepted']:continue
  b=blocks[(v['increment'],v['attempt'])];lines=[x.strip() for x in b.splitlines() if 'FORCE' in x and ('EQUILIB' in x or 'RESIDUALS ARE ZERO' in x)]
  convergence=('THE FORCE     EQUILIBRIUM EQUATIONS HAVE CONVERGED' in b);small=('FORCE     EQUILIB. ACCEPTED BASED ON SMALL RESIDUAL AND ESTIMATED CORRECTION' in b);zero='ALL FORCE' in b and 'RESIDUALS ARE ZERO' in b
  accepted.append({**v,'completed_marker':'TIME INCREMENT COMPLETED' in b,'force_equilibrium_converged':convergence,'small_residual_correction_acceptance':small,'zero_force_residual':zero,'final_force_message':lines[-1] if lines else None,'contact_outside_tolerance_iterations':len(re.findall(r'CONTACT FORCE ERROR.*OUTSIDE',b,re.I)),'final_acceptance_explicit':('TIME INCREMENT COMPLETED' in b) and (convergence or small or zero)})
 dat=(R/files['dat']['path']).read_text(errors='replace').splitlines();warnings=[{'line':i+1,'text':'\n'.join(dat[i:i+9])} for i,l in enumerate(dat) if re.match(r'\s*\*{3}(WARNING|ERROR)',l,re.I)]
 return {**event,'STA_trials':trials,'accepted_trial_equilibrium':accepted,'unconfirmed_accepted_equilibrium':[v for v in accepted if not v['final_acceptance_explicit']],'DAT_warning_blocks':warnings,'total_equilibrium_iterations_all_trials':sum(v['equilibrium_iterations'] for v in trials),'accepted_equilibrium_iterations':sum(v['equilibrium_iterations'] for v in accepted),'scope':'actual STA acceptance and exact MSG trial block; intermediate contact iterations and rejected warnings are not final accepted physical states'}

def main():
 a=read(P/'execution_audit.json');new=a['record']['files'];cc=read(R/'run/run_060/artifacts/comparison_contract.json');diag=read(R/cc['baseline']['diagnostics_path']);old=diag['provenance']['source_files']
 for fs in [old,new]:
  for f in fs.values():
   if 'path' in f and f.get('sha256'):assert sha(R/f['path'])==f['sha256']
 o=audit(old);n=audit(new);save(P/'MAIN_independent_raw_numerical_audit.json',{'at':now(),'original':o,'refined':n,'no_ODB_summary_copied':True})
 print(json.dumps({k:{'accepted':x['accepted_increments'],'cutbacks':x['cutback_count'],'rejected':x['rejected_attempts'],'warnings':x['warning_counts'],'unconfirmed_equilibrium':len(x['unconfirmed_accepted_equilibrium']),'iterations':x['total_equilibrium_iterations_all_trials'],'dat_warning_blocks':len(x['DAT_warning_blocks'])} for k,x in [('original',o),('refined',n)]}))
if __name__=='__main__':main()
