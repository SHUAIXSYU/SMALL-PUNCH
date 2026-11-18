"""MAIN aligns each accepted STA attempt to its own MSG block and contact frames."""
from common import *
import re

audit=read(P/'execution_audit.json');checks=read(P/'main_independent_checks.json');out=[]
for point in audit['records']:
 cid=point['candidate_id'];msg=(R/point['files']['msg']['path']).read_text(errors='replace');sta=(R/point['files']['sta']['path']).read_text(errors='replace')
 accepted=[]
 for line in sta.splitlines():
  words=line.split()
  if len(words)>=9 and words[0].isdigit() and words[1].isdigit() and re.fullmatch(r'\d+',words[2]):accepted.append((int(words[1]),int(words[2])))
 hits=list(re.finditer(r'INCREMENT\s+(\d+)\s+STARTS\.\s+ATTEMPT NUMBER\s+(\d+)',msg,re.I));blocks={}
 for i,hit in enumerate(hits):blocks[tuple(map(int,hit.groups()))]=msg[hit.start():hits[i+1].start() if i+1<len(hits) else len(msg)]
 equilibrium=[]
 for inc,attempt in accepted:
  text=blocks[(inc,attempt)];final_force=[line.strip() for line in text.splitlines() if 'FORCE' in line and ('EQUILIBRIUM' in line or 'EQUILIB.' in line or 'RESIDUALS ARE ZERO' in line)]
  equilibrium.append({'increment':inc,'attempt':attempt,'completed_marker':'TIME INCREMENT COMPLETED' in text,'final_force_message':final_force[-1] if final_force else None,'force_equilibrium_converged':'THE FORCE     EQUILIBRIUM EQUATIONS HAVE CONVERGED' in text,'accepted_based_on_small_residual_and_estimated_correction':'FORCE     EQUILIB. ACCEPTED BASED ON SMALL RESIDUAL AND ESTIMATED CORRECTION' in text,'all_force_residuals_zero':'ALL FORCE' in text and 'RESIDUALS ARE ZERO' in text,'contact_outside_tolerance_mentions':len(re.findall(r'CONTACT FORCE ERROR.*OUTSIDE',text,re.I))})
 ex=read(P/'odb'/cid/'odb_extraction.json');frames=ex['steps']['Step_Punch_Displacement']['frame_diagnostics'];top=next(x for x in checks['records'] if x['candidate_id']==cid)['local_slope_peaks']
 local=[]
 for peak in top:
  i=peak['index'];f=frames[i];prev=frames[i-1];ev=next(v for v in equilibrium if v['increment']==f['increment'])
  local.append({**peak,'accepted_attempt_equilibrium':ev,'previous_node23_contact':prev['contact'].get('topology_node_values'),'current_node23_contact':f['contact'].get('topology_node_values'),'mechanism':'contact evolution association only; no unique causal attribution from saved samples'})
 out.append({'candidate_id':cid,'accepted_attempts':len(accepted),'completed_markers':sum(v['completed_marker'] for v in equilibrium),'force_equilibrium_converged_count':sum(v['force_equilibrium_converged'] for v in equilibrium),'small_residual_and_estimated_correction_acceptance_count':sum(v['accepted_based_on_small_residual_and_estimated_correction'] for v in equilibrium),'equilibrium_missing_or_unconfirmed':[v for v in equilibrium if not (v['completed_marker'] and (v['force_equilibrium_converged'] or v['accepted_based_on_small_residual_and_estimated_correction'] or v['all_force_residuals_zero']))],'local_events':local,'accepted_trial_records':equilibrium,'no_rejected_attempt_substituted_for_accepted':True})
save(P/'accepted_equilibrium_and_local_contact_v2.json',{'records':out,'scope':'accepted STA attempt-specific MSG equilibrium; raw contact pressure changes are not a numerical error bound','parser_addendum':'v1 exact-string scan left7 cases unconfirmed; actual MSG explicitly records small residual/estimated-correction acceptance in those7. v1 retained, no Solver threshold or scientific gate altered.'})
print(json.dumps([{k:v for k,v in r.items() if k in ['candidate_id','accepted_attempts','completed_markers','force_equilibrium_converged_count','equilibrium_missing_or_unconfirmed']} for r in out]))
