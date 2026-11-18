"""Contact/force associations on native accepted frames, without causal overclaim."""
from common62 import *
import numpy as np
def main():
 d=read(P/'verified_plot_arrays.json');u=np.array(d['grid_m'])*1000;delta=np.array(d['refined_N'])-np.array(d['original_N']);total=float(delta@delta)
 ranges=[]
 for lo,hi in [(0,.03),(.68,.70),(.85,.88),(.97,.99),(1.10,1.16)]:
  mask=(u>=lo-1e-10)&(u<=hi+1e-10);dd=delta[mask];xx=u[mask]
  ranges.append({'lo_mm':lo,'hi_mm':hi,'points':int(mask.sum()),'RMSE_N':float(np.sqrt(np.mean(dd**2))),'max_abs_N':float(max(abs(dd))),'max_at_mm':float(xx[np.argmax(abs(dd))]),'global_sum_squares_fraction':float(dd@dd/total),'scope':'overlapping supplementary windows; not alternative scoring windows'})
 folders={'original':R/'run/run_034/artifacts/private/odb/I06','refined':P/'odb/I06_REFINED'};out={}
 nums=read(P/'MAIN_independent_raw_numerical_audit.json')
 for name,path in folders.items():
  ex=read(path/'odb_extraction.json');fd=rows(path/'force_displacement.csv');frames=ex['steps']['Step_Punch_Displacement']['frame_diagnostics'];uu=np.array([float(x['displacement_m'])*1000 for x in fd]);ff=np.array([float(x['force_n']) for x in fd]);notes=[]
  for lo,hi,node in [(.97,.99,24),(1.10,1.16,23)]:
   indices=[i for i in range(len(uu)) if lo<=uu[i]<=hi];positive=[]
   for i in indices:
    val=next((n for n in frames[i]['contact'].get('topology_node_values',[]) if n['node_label']==node),None)
    if val and val.get('cpress') is not None and val['cpress']>0:positive.append(i)
   first=positive[0] if positive else None
   peaks=sorted([i for i in indices if i>0],key=lambda i:abs(ff[i]-ff[i-1]),reverse=True)[:4]
   notes.append({'window_mm':[lo,hi],'node':node,'saved_frame_count':len(indices),'first_positive_pressure_sample':None if first is None else {'frame':first,'u_mm':float(uu[first]),'cpress_Pa':next(n['cpress'] for n in frames[first]['contact']['topology_node_values'] if n['node_label']==node),'previous_frame_u_mm':float(uu[first-1]) if first else None,'not_exact_contact_onset':True},'largest_native_steps':[{'frame':i,'u_before_mm':float(uu[i-1]),'u_mm':float(uu[i]),'force_before_N':float(ff[i-1]),'force_N':float(ff[i]),'delta_force_N':float(ff[i]-ff[i-1]),'increment':frames[i]['increment'],'accepted_equilibrium':next(v for v in nums[name]['accepted_trial_equilibrium'] if v['increment']==frames[i]['increment'])} for i in peaks]})
  out[name]=notes
 # Locate the largest paired IP difference (not the same as global max PEEQ change).
 f=read(P/'PEEQ_stage_field_comparison.json');locations=[]
 for label,source in f['sources'].items():
  rs=rows(R/source['IPs']);r=next(x for x in rs if float(x['target_displacement_mm'])==1.2 and int(x['element_label'])==378 and int(x['integration_point'])==2)
  locations.append({'model':label,'stage_mm':1.2,'element':378,'IP':2,'r_ref_mm':float(r['r_ref_m'])*1000,'z_ref_mm':float(r['z_ref_m'])*1000,'PEEQ':float(r['PEEQ']),'reference_volume_m3':float(r['volume_ref_m3'])})
 save(P/'MAIN_contact_mechanism_review.json',{'at':now(),'supplementary_windows':ranges,'native_contact_samples':out,'largest_final_IP_difference_locations':locations,'judgment':'max fixed-grid difference at.98mm coincides with node24 positive-pressure establishment and rapid force increase in both histories; differences in accepted path and sampling/interpolation are associated. Saved evidence does not uniquely separate path error from interpolation effects or prove contact is the only cause. Node23 builds pressure again in1.10-1.16mm; this is not the largest frozen-grid difference. COPEN sentinel remains missing. No force recoil in either model.'})
 print(json.dumps({'windows':ranges,'onsets':{k:[v['first_positive_pressure_sample'] for v in vs] for k,vs in out.items()},'final_IP_locations':locations}))
if __name__=='__main__':main()
