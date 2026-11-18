"""Saved-frame context for early ordering reversals and the predefined local window."""
from pathlib import Path
import csv,json
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_053/artifacts/private';OUT=P/'main'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
aligned=rows(OUT/'aligned_241_three_models.csv');inversions=[{'u_mm':float(v['displacement_m'])*1000,'H02_minus_H01_N':float(v['H02_force_N'])-float(v['H01_force_N'])} for v in aligned if float(v['H02_force_N'])<float(v['H01_force_N'])]
folders={'D01':R/'run/run_045/artifacts/private/odb/D01','H01':P/'odb/H01','H02':P/'odb/H02'};summaries=[];ugrids={}
for cid,folder in folders.items():
 fd=rows(folder/'force_displacement.csv');ex=read(folder/'odb_extraction.json');frames=ex['steps']['Step_Punch_Displacement']['frame_diagnostics'];u=np.array([float(v['displacement_m']) for v in fd]);f=np.array([float(v['force_n']) for v in fd]);ugrids[cid]=u
 active=[i for i in range(len(u)) if 1.10-1e-12<=u[i]*1000<=1.16+1e-12];first_switch=next((i for i,v in enumerate(frames) if v['peeq_max']>.09774053167903649),None)
 i=int(np.argmin(abs(u*1000-.26)));local=[(f[j]-f[j-1],j) for j in active if j>0]
 summaries.append({'candidate_id':cid,'first_any_IP_above_actual_switch_mm':None if first_switch is None else float(u[first_switch]*1000),'not_a_volume_or_force_contribution':True,'near_max_early_order_inversion':{'saved_frame':i,'u_mm':float(u[i]*1000),'force_N':float(f[i]),'positive_contact_node_count':frames[i]['contact']['positive_cpress_node_count'],'positive_contact_node_labels':frames[i]['contact']['positive_cpress_node_labels'],'max_cpress_Pa':frames[i]['contact']['max_cpress']},'focus_1p10_to_1p16mm':{'saved_frames':len(active),'first_mm':float(u[active[0]]*1000),'last_mm':float(u[active[-1]]*1000),'positive_contact_node_counts':sorted({frames[j]['contact']['positive_cpress_node_count'] for j in active}),'max_raw_force_step_N':float(max(local,key=lambda v:abs(v[0]))[0]),'raw_step_location_mm':float(u[max(local,key=lambda v:abs(v[0]))[1]]*1000),'all_force_steps_nonnegative':all(v[0]>=0 for v in local),'COPEN_sentinel_note':'missing diagnostic values retained, not interpreted as penetration'}})
result={'early_order_inversions':inversions,'maximum_order_inversion_N':max([-v['H02_minus_H01_N'] for v in inversions],default=0),'inversion_scope':'all observed on fixed grid before .3mm; all individual force curves remain monotonically increasing','saved_frame_context':summaries,'raw_displacement_grid_same_length':len({len(v) for v in ugrids.values()})==1,'raw_u_grid_max_pair_difference_m':{cid:float(np.max(abs(ugrids[cid]-ugrids['D01']))) for cid in ['H01','H02']},'cause_limit':'contact state/pressure differences are correlation evidence only; no unique cause of tiny early ordering inversions or local slope jumps assigned'}
with (OUT/'contact_and_ordering_context.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps({'same_raw_u_grid':result['raw_u_grid_max_pair_difference_m'],'contexts':summaries},ensure_ascii=False))
