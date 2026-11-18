"""MAIN independent axisymmetric quadrature, energy attribution and global-work review."""
from pathlib import Path
import json,csv,sys,math,hashlib,importlib.util
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_053/artifacts/private';OUT=P/'main'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]),lineterminator='\n');w.writeheader();w.writerows(rs)
def material_work(tab,p):
 x,y=tab;assert 0<=p<=x[-1];i=min(int(np.searchsorted(x,p,side='right')-1),len(x)-1)
 v=float(np.sum((y[:i]+y[1:i+1])*.5*np.diff(x[:i+1]))) if i else 0.
 if i<len(x)-1:
  dx=p-x[i];last=y[i]+(y[i+1]-y[i])*dx/(x[i+1]-x[i]);v+=float((y[i]+last)*dx*.5)
 return v

def main():
 newmanifest=read(P/'odb/manifest.json')
 for v in newmanifest['files']:assert sha(R/v['path'])==v['sha256']
 oldmanifest=read(R/'run/run_050/artifacts/private/odb/manifest.json');oldhash={v['path']:v['sha256'] for v in oldmanifest['files']}
 paths={'D01':R/'run/run_050/artifacts/private/odb/D01','H01':P/'odb/H01','H02':P/'odb/H02'}
 for name in ['spatial_ips.csv','energy_estimate.json','energy_strain_stage_v2.json','spatial_extraction.json','estimated_ip_cumulative_energy.csv']:
  f=paths['D01']/name;assert sha(f)==oldhash[f.relative_to(R).as_posix()]
 helper=R/'run/run_050/artifacts/main_material_scope.py';spec=importlib.util.spec_from_file_location('run050_geometry_definitions',helper);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 contract=read(R/'run/run_051/artifacts/material_contract.json');nodes,els=mod.specimen_mesh((R/contract['source_inp']).read_text(encoding='utf-8'))
 gp={1:(-1,-1),2:(1,-1),3:(-1,1),4:(1,1)};expected={}
 for label,conn in els.items():
  xy=np.array([nodes[k] for k in conn])
  for ip,(sx,sy) in gp.items():
   xi=sx/math.sqrt(3);eta=sy/math.sqrt(3);N=np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])/4;grad=np.array([[-(1-eta),-(1-xi)],[(1-eta),-(1+xi)],[(1+eta),(1+xi)],[-(1+eta),(1-xi)]])/4;rz=N@xy;expected[label,ip]=(rz,2*math.pi*rz[0]*float(np.linalg.det(xy.T@grad)))
 records=[];table=[];comparison=[]
 for cid,folder in paths.items():
  raw=rows(folder/'spatial_ips.csv');peeqwork=rows(folder/'estimated_ip_cumulative_energy.csv');smeta=read(folder/'spatial_extraction.json');v1=read(folder/'energy_estimate.json');v2=read(folder/'energy_strain_stage_v2.json')
  fdpath=R/'run/run_045/artifacts/private/odb/D01/force_displacement.csv' if cid=='D01' else folder/'force_displacement.csv';epath=R/'run/run_045/artifacts/private/odb/D01/energy_history.csv' if cid=='D01' else folder/'energy_history.csv'
  fds=rows(fdpath);e=rows(epath);u=np.array([float(v['displacement_m']) for v in fds]);force=np.array([float(v['force_n']) for v in fds]);work=np.r_[0,np.cumsum((force[:-1]+force[1:])*.5*np.diff(u))];assert len(e)==len(fds)
  mpath=R/'run/run_046/artifacts/private/freeze/D01_abaqus_yield_stress_plastic_strain.csv' if cid=='D01' else R/f'run/run_051/artifacts/private/{cid}/yield_stress_plastic_strain.csv';mr=rows(mpath);tab=(np.array([float(v['equivalent_plastic_strain']) for v in mr]),np.array([float(v['yield_stress_pa']) for v in mr]))
  stages=[]
  for target in [.3,.6,.9,1.2]:
   d=[v for v in raw if float(v['target_displacement_mm'])==target];er=[v for v in peeqwork if float(v['target_displacement_mm'])==target];assert len(d)==len(er)==2376
   keys={(int(v['element_label']),int(v['integration_point'])) for v in d};assert len(keys)==2376
   maxerr=0
   for v in d:
    rz,weight=expected[int(v['element_label']),int(v['integration_point'])];r0=float(v['r_ref_m']);z0=float(v['z_ref_m']);vr=float(v['volume_ref_m3']);vc=float(v['volume_current_m3']);assert np.max(abs(rz-[r0,z0]))<3e-10;maxerr=max(maxerr,abs(vr/weight-1))
    assert float(v['detJ_ref_m2'])>0 and float(v['detJ_current_m2'])>0 and float(v['PEEQ'])<.9
    assert abs(vr/(2*math.pi*r0*float(v['detJ_ref_m2']))-1)<1e-12 and abs(vc/(2*math.pi*float(v['r_current_m'])*float(v['detJ_current_m2']))-1)<1e-12
   assert maxerr<3e-6
   total=math.fsum(float(v['volume_ref_m3']) for v in d);assert abs(total/(math.pi*.005**2*.0005)-1)<1e-6
   s=next(v for v in smeta['stages'] if v['target_displacement_mm']==target);one=next(v for v in v1['stages'] if v['target_displacement_mm']==target);two=next(v for v in v2['stages'] if v['target_displacement_mm']==target);ix=int(d[0]['frame_index']);direct=float(e[ix]['ALLPD']);wk=float(e[ix]['ALLWK']);assert direct==s['energy_history']['ALLPD']==two['ALLPD_direct_history_j']
   cumulative=math.fsum(float(v['cumulative_reconstructed_work_j']) for v in er);assert abs(cumulative-one['reconstructed_sigma_mises_dPEEQ_reference_volume_j'])<1e-12
   assert abs(math.fsum(two['strain_interval_cumulative_work_j'].values())-cumulative)<1e-12
   f2=two['fraction_by_strain_interval'];low=f2.get('p_0_to_0p1',f2.get('p_0_to_actual_switch',0)+f2.get('p_actual_switch_to_0p1',0));bins=[low,f2['p_0p1_to_0p3'],f2['p_0p3_to_0p5'],f2['p_above_0p5']];assert abs(sum(bins)-1)<1e-12
   thresholds=[]
   for threshold in [.1,.3,.5]:
    vr=math.fsum(float(v['volume_ref_m3']) for v in d if float(v['PEEQ'])>threshold);w=math.fsum(float(v['cumulative_reconstructed_work_j']) for v in er if float(v['PEEQ_at_stage'])>threshold);stored=one['terminal_peeq_region_attribution'][str(threshold)]
    assert abs(w-stored['cumulative_estimated_energy_j'])<1e-12
    thresholds.append({'threshold':threshold,'reference_volume_fraction':vr/total,'terminal_region_all_prior_estimated_work_fraction':w/cumulative})
   potential=math.fsum(float(v['volume_ref_m3'])*material_work(tab,float(v['PEEQ'])) for v in d)
   rr={'target_mm':target,'actual_mm':s['actual_displacement_mm'],'saved_frame':ix,'max_peeq':s['max_peeq'],'reference_volume_m3':total,'current_volume_m3':s['current_volume_m3'],'thresholds':thresholds,'direct_ALLPD_J':direct,'direct_ALLWK_J':wk,'RP_integral_work_J':float(work[ix]),'RP_work_relative_difference_to_ALLWK':float(work[ix]/wk-1),'reconstructed_reference_work_J':cumulative,'reconstruction_relative_difference_to_ALLPD':cumulative/direct-1,'frozen_table_reference_work_index_J':potential,'model_index_relative_difference_to_actual_saved_frame_reconstruction':potential/cumulative-1,'common_work_interval_fractions':dict(zip(['0_to_0p1','0p1_to_0p3','0p3_to_0p5','above0p5'],bins)),'work_after_p0p1_fraction':1-low,'work_after_p0p5_fraction':f2['p_above_0p5'],'contact':s['contact']}
   stages.append(rr);row={'candidate_id':cid,'target_mm':target,'max_peeq':s['max_peeq'],'ALLPD_J':direct,'ALLWK_J':wk,'estimated_work_after_p0p1_fraction':1-low,'estimated_work_after_p0p5_fraction':f2['p_above_0p5'],'estimated_cumulative_reference_work_J':cumulative,'reconstruction_difference_relative_to_ALLPD':cumulative/direct-1}
   for q in thresholds:row[f"volume_ref_fraction_gt_{q['threshold']}"]=q['reference_volume_fraction'];row[f"terminal_region_work_fraction_gt_{q['threshold']}"]=q['terminal_region_all_prior_estimated_work_fraction']
   table.append(row)
  records.append({'candidate_id':cid,'source_folder':folder.relative_to(R).as_posix(),'stages':stages})
 save(OUT/'spatial_energy_independent_review.json',{'records':records,'ODB_manifest_files_verified':len(newmanifest['files']),'CAX4_GP_identity':'1(-,-),2(+,-),3(-,+),4(+,+);2pi*r*detJ;whole specimen denominator','reference_measure_not_current_measure':'all work estimates use reference IP volume, all volume fractions labeled reference','volume_threshold_checks':36,'neither_energy_definition_is_RF2_share':True,'actual_switch_extra_bins_for_H_not_silently_substituted_for_D01_p0p1':True})
 csvsave(OUT/'spatial_energy_summary.csv',table)
 final=[v for v in table if v['target_mm']==1.2]
 fig,axes=plt.subplots(1,3,figsize=(13,4))
 for ax,t in zip(axes,[.1,.3,.5]):
  for cid in paths:
   d=[v for v in table if v['candidate_id']==cid];ax.plot([v['target_mm'] for v in d],[100*v[f'volume_ref_fraction_gt_{t}'] for v in d],'o-',label=cid)
  ax.set(xlabel='Punch displacement (mm)',ylabel='Whole reference volume (%)',title=f'PEEQ > {t}');ax.legend();ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(OUT/'reference_volume_fraction_comparison.png',dpi=180);plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(13,4))
 axes[0].bar([v['candidate_id'] for v in final],[v['ALLPD_J'] for v in final]);axes[0].set(title='Direct global ALLPD',ylabel='Energy (J)')
 x=np.arange(3);width=.35;axes[1].bar(x-width/2,[100*v['estimated_work_after_p0p1_fraction'] for v in final],width,label='work accrued after p>.1');axes[1].bar(x+width/2,[100*v['terminal_region_work_fraction_gt_0.1'] for v in final],width,label='all prior work in final p>.1 region');axes[1].set(xticks=x,xticklabels=[v['candidate_id'] for v in final],ylabel='Fraction of reconstructed work (%)',title='Different definitions; not RF2 shares');axes[1].legend(fontsize=7)
 bottoms=np.zeros(3)
 for label,idx in [('0–.1',0),('.1–.3',1),('.3–.5',2),('>.5',3)]:
  vals=np.array([list(v['stages'][-1]['common_work_interval_fractions'].values())[idx] for v in records])*100;axes[2].bar(x,vals,bottom=bottoms,label=label);bottoms+=vals
 axes[2].set(xticks=x,xticklabels=list(paths),ylabel='Reconstructed work (%)',title='PEEQ-at-work interval');axes[2].legend(fontsize=7)
 fig.tight_layout();fig.savefig(OUT/'plastic_work_comparison.png',dpi=180);plt.close(fig)
 print(json.dumps({'finals':final,'checks':36},ensure_ascii=False))
if __name__=='__main__':main()
