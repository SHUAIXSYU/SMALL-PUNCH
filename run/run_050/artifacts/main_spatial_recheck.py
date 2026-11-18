"""MAIN independently checks actual exported IP weights and threshold volumes."""
from pathlib import Path
import json,csv,math
import numpy as np
from main_material_scope import specimen_mesh
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_050/artifacts/private'
def load(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
gauss={1:(-1,-1),2:(1,-1),3:(-1,1),4:(1,1)}
nodes,els=specimen_mesh((R/'run/run_043/artifacts/candidates/SPIO_R043_V_D01_M00125/SPIO_R043_V_D01_M00125.inp').read_text())
expected={}
for label,conn in els.items():
 xy=np.array([nodes[n] for n in conn])
 for ip,(sx,sy) in gauss.items():
  xi=sx/math.sqrt(3);eta=sy/math.sqrt(3)
  N=np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])/4
  grad=np.array([[-(1-eta),-(1-xi)],[(1-eta),-(1+xi)],[(1+eta),(1+xi)],[-(1+eta),(1-xi)]])/4
  rz=N@xy;det=float(np.linalg.det(xy.T@grad));expected[label,ip]=(rz,2*math.pi*rz[0]*det)
out=[];table=[]
for pid in ['D01','I08']:
 raw=load(P/f'odb/{pid}/spatial_ips.csv');meta=json.loads((P/f'odb/{pid}/spatial_extraction.json').read_text());stages=[]
 assert len(raw)==4*594*4
 for target in [.3,.6,.9,1.2]:
  data=[v for v in raw if float(v['target_displacement_mm'])==target];assert len(data)==2376
  assert len({(int(v['element_label']),int(v['integration_point'])) for v in data})==2376
  max_coord_err=0;max_rel_weight=0
  for v in data:
   rz,w=expected[int(v['element_label']),int(v['integration_point'])];rr=float(v['r_ref_m']);zz=float(v['z_ref_m']);vr=float(v['volume_ref_m3']);vc=float(v['volume_current_m3'])
   max_coord_err=max(max_coord_err,float(max(abs(rz-np.array([rr,zz])))));max_rel_weight=max(max_rel_weight,abs(vr/w-1))
   assert abs(vr/(2*math.pi*rr*float(v['detJ_ref_m2']))-1)<1e-12
   assert abs(vc/(2*math.pi*float(v['r_current_m'])*float(v['detJ_current_m2']))-1)<1e-12
  assert max_coord_err<3e-10 and max_rel_weight<3e-6
  total0=math.fsum(float(v['volume_ref_m3']) for v in data);total=math.fsum(float(v['volume_current_m3']) for v in data)
  free=math.fsum(float(v['volume_ref_m3']) for v in data if float(v['r_ref_m'])<.002)
  thresholds=[]
  for threshold in [.1,.3,.5]:
   high=[v for v in data if float(v['PEEQ'])>threshold];v0=math.fsum(float(v['volume_ref_m3']) for v in high);vv=math.fsum(float(v['volume_current_m3']) for v in high)
   regions={name:math.fsum(float(v['volume_ref_m3']) for v in high if lo<=float(v['r_ref_m'])<hi)/v0 if v0 else None for name,lo,hi in [('punch_radius_projection',0,.00125),('free_annulus_1p25_to_2mm',.00125,.002),('clamped_ring_2_to_5mm',.002,.005000001)]}
   bands={name:math.fsum(float(v['volume_ref_m3']) for v in high if lo<=float(v['z_ref_m'])<hi)/v0 if v0 else None for name,lo,hi in [('bottom_quarter',0,.000125),('middle_half',.000125,.000375),('top_quarter',.000375,.000500001)]}
   q={'threshold':threshold,'ip_count':len(high),'volume_ref_m3':v0,'volume_current_m3':vv,'whole_specimen_ref_fraction':v0/total0,'whole_specimen_current_fraction':vv/total,'within_r_lt_2mm_ref_fraction':math.fsum(float(v['volume_ref_m3']) for v in high if float(v['r_ref_m'])<.002)/free,'high_region_reference_radial_partition':regions,'high_region_reference_thickness_partition':bands}
   if high:q['reference_r_range_mm']=[min(float(v['r_ref_m']) for v in high)*1000,max(float(v['r_ref_m']) for v in high)*1000]
   thresholds.append(q);table.append({'candidate_id':pid,'target_mm':target,'threshold':threshold,'whole_reference_volume_fraction':v0/total0,'whole_current_volume_fraction':vv/total,'active_span_reference_fraction':q['within_r_lt_2mm_ref_fraction'],'high_reference_volume_m3':v0})
  stages.append({'target_mm':target,'frame':int(data[0]['frame_index']),'reference_volume_m3':total0,'current_volume_m3':total,'reference_r_lt_2mm_volume_fraction':free/total0,'max_reference_coordinate_error_m':max_coord_err,'max_reference_weight_relative_difference_to_INP':max_rel_weight,'thresholds':thresholds})
 out.append({'candidate_id':pid,'stages':stages})
save(P/'main_spatial_independent_check.json',{'records':out,'scope':'MAIN own CAX4 IP mapping/coordinate/weight check against actual INP and threshold sum from actual ODB export; current weight formula verified, no independent current-node reconstruction','radial_partition_note':'punch radius projection is a geometric region, not identical to observed active contact footprint; r<2mm active-span denominator explicitly separate from whole specimen','volume_region_resolution':'integration point classification only, not exact threshold interface or per-element maximum assignment'})
with (P/'main_threshold_volumes.csv').open('x',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
print(json.dumps({'rows':len(table),'final_stage':[v for v in table if v['target_mm']==1.2]}))
