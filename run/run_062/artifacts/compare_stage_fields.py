"""Paired IP diagnostics at nearest actual stages, with explicit displacement mismatch."""
from common62 import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
 base='0a544fd06f0c0de630946173314ba980085a8a464ef4027e715bfb46e3d3b45a'
 folders=[p.parent for p in (P/'odb/I06_REFINED').rglob('spatial_extraction.json')]
 old=[p for p in folders if read(p/'spatial_extraction.json')['source_odb_sha256']=='9c8cfee50698b98e63215db665e5aa1e8afaabdd2d5f8e40eb0e4e690f89d7aa']
 new=[p for p in folders if read(p/'spatial_extraction.json')['source_odb_sha256']==read(P/'execution_audit.json')['record']['files']['odb']['sha256']]
 assert len(old)==len(new)==1,'Two traceable real spatial extractions required'
 paths={'original':old[0],'refined':new[0]};raw={k:rows(p/'spatial_ips.csv') for k,p in paths.items()};meta={k:read(p/'spatial_extraction.json') for k,p in paths.items()};out=[];allrows=[]
 fig,axes=plt.subplots(2,2,figsize=(10,6));arrays={}
 for index,target in enumerate([.3,.6,.9,1.2]):
  by={k:{(r['instance'],int(r['element_label']),int(r['integration_point'])):r for r in rs if float(r['target_displacement_mm'])==target} for k,rs in raw.items()}
  assert set(by['original'])==set(by['refined']) and len(by['original'])==2376
  keys=sorted(by['original']);o=[by['original'][k] for k in keys];n=[by['refined'][k] for k in keys];v=np.array([float(r['volume_ref_m3']) for r in o]);pv=np.array([float(r['volume_ref_m3']) for r in n]);assert np.array_equal(v,pv) and np.all(v>0)
  p=np.array([float(r['PEEQ']) for r in o]);q=np.array([float(r['PEEQ']) for r in n]);delta=q-p;w=v/sum(v);stages={k:next(s for s in m['stages'] if s['target_displacement_mm']==target) for k,m in meta.items()}
  offsets={k:s['actual_displacement_mm']-target for k,s in stages.items()};exact=stages['original']['actual_displacement_mm']==stages['refined']['actual_displacement_mm'];ip=int(np.argmax(abs(delta)))
  out.append({'target_mm':target,'status':'EXACT_STROKE_PAIRED_IP_DIAGNOSTIC' if exact else 'APPROXIMATE_NEAR_STAGE_DIAGNOSTIC_NOT_EXACT_FIELD_ERROR','actual_stages':stages,'offset_mm':offsets,'both_within_3um_review':all(abs(x)<=.003 for x in offsets.values()),'paired_IPs':2376,'reference_volume_m3':float(sum(v)),'axisymmetric_weighting':'2*pi*r*detJ, verified same reference weights','PEEQ_reference_volume_weighted_difference_RMSE':float(np.sqrt(np.sum(w*delta**2))),'PEEQ_max_abs_IP_difference':float(max(abs(delta))),'max_difference_IP_key':keys[ip],'original_max_PEEQ_at_stage':float(max(p)),'refined_max_PEEQ_at_stage':float(max(q)),'reference_volume_fractions_original':{str(t):float(sum(w[p>t])) for t in [.1,.3,.5]},'reference_volume_fractions_refined':{str(t):float(sum(w[q>t])) for t in [.1,.3,.5]},'nearest_stage_ALLPD_original_J':stages['original']['energy_history'].get('ALLPD'),'nearest_stage_ALLPD_refined_J':stages['refined']['energy_history'].get('ALLPD'),'cannot_equate_volume_fraction_to_RF2_contribution':True})
  for key,a,b,d,vv in zip(keys,p,q,delta,v):allrows.append({'target_mm':target,'instance':key[0],'element':key[1],'IP':key[2],'original_PEEQ':float(a),'refined_PEEQ':float(b),'difference':float(d),'reference_volume_m3':float(vv),'actual_original_u_mm':stages['original']['actual_displacement_mm'],'actual_refined_u_mm':stages['refined']['actual_displacement_mm'],'exact_same_displacement':exact})
  ax=axes.flat[index];x=np.array([float(r['r_ref_m'])*1000 for r in o]);z=np.array([float(r['z_ref_m'])*1000 for r in o]);lim=max(float(max(abs(delta))),1e-7);h=ax.scatter(x,z,c=delta,s=5,cmap='coolwarm',vmin=-lim,vmax=lim);fig.colorbar(h,ax=ax,label='PEEQ difference');ax.set(xlabel='Reference r (mm)',ylabel='Reference z (mm)',title=f'{target:.1f} mm: '+('same stroke' if exact else 'nearest-stage, approximate'))
 fig.suptitle('Refined - original: paired IPs, real saved frames, no field interpolation');fig.tight_layout();fig.savefig(P/'nearest_stage_PEEQ_difference.png',dpi=180);plt.close(fig)
 save(P/'PEEQ_stage_field_comparison.json',{'at':now(),'scope':'nearest real saved frames; scalar maximum interpolation is separate frozen diagnostic; nonidentical strokes not exact field errors','sources':{k:{'metadata':rel(p/'spatial_extraction.json'),'metadata_sha256':sha(p/'spatial_extraction.json'),'IPs':rel(p/'spatial_ips.csv'),'IPs_sha256':sha(p/'spatial_ips.csv')} for k,p in paths.items()},'stages':out});csvsave(P/'PEEQ_paired_nearest_stage_IPs.csv',allrows)
 print(json.dumps([{'target_mm':x['target_mm'],'status':x['status'],'offset_mm':x['offset_mm'],'weighted_RMSE':x['PEEQ_reference_volume_weighted_difference_RMSE'],'max_abs':x['PEEQ_max_abs_IP_difference']} for x in out]))
if __name__=='__main__':main()
