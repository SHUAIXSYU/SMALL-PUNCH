"""MAIN independently reconstructs signs/field consistency and scores only eligible complete curves."""
from pathlib import Path
import json,csv,sys,hashlib,math,traceback
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_053/artifacts/private';OUT=P/'main';sys.path.insert(0,str(R))
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
from sensitivity_metrics import assess_curve,pair_symmetry
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]),lineterminator='\n');w.writeheader();w.writerows(rs)

def main():
 OUT.mkdir(exist_ok=False)
 cc=read(R/'run/run_051/artifacts/comparison_contract.json');binding=cc['loss_binding'];refcheck=read(P/'D01_reference_check.json');assert refcheck['status']=='PASS_FROZEN_REFERENCE_IDENTITY_AND_LOSS'
 for k in ['target','config','implementation']:assert sha(R/binding[k+'_path'])==binding[k+'_sha256']
 oldgrid=read(R/'run/run_027/artifacts/comparison_contract.json')['grid_m'];data=rows(R/binding['target_path'])[:241];u=np.array([float(v['displacement_m']) for v in data]);exp=np.array([float(v['force_n']) for v in data]);assert tuple(u)==tuple(oldgrid)
 target=Target(Curve(tuple(u),tuple(exp),'m','N'),(1.,)*241,1428.9,binding['version'])
 rawD=rows(R/cc['baseline_fd_path']);base_curve=Curve(tuple(float(v['displacement_m']) for v in rawD),tuple(float(v['force_n']) for v in rawD),'m','N');base=np.array(interpolate(base_curve,u))
 dmetrics,_,_,dres=assess_curve(target,base_curve,base,software_status='COMPLETED_WITH_WARNINGS',numerical_accepted=True);assert abs(dmetrics['loss']-cc['baseline_SPT_loss'])<1e-15
 ref_result=read(R/cc['baseline_result_path']);recordD={'candidate_id':'D01','job_name':ref_result['job_name'],'scoreability':'SCOREABLE_EXPLORATORY','qualification_scope':'prior point-level adjacent time-increment qualification, not mesh/global convergence','max_saved_peeq':ref_result['max_saved_peeq'],'runtime_s':ref_result['actual_runtime_s'],'cutback':ref_result['cutback_increments'],'numerical_warnings':ref_result['numerical_review_warnings'] if 'numerical_review_warnings' in ref_result else [],**dmetrics}
 allmetrics=[recordD];aligned={'D01':base};curves={'D01':base_curve};raw_ends={'D01':{'u':np.array(base_curve.displacement),'f':np.array(base_curve.force)}};audit=read(P/'execution_audit.json');numeric=read(P/'main_numeric_event_audit.json');checks=[];sources=[]
 for p in audit['records']:
  cid=p['candidate_id'];folder=P/'odb'/cid
  try:
   result=read(folder/'result.json');ex=read(folder/'odb_extraction.json');fd=rows(folder/'force_displacement.csv');raw=rows(folder/'raw_history.csv');peeq=rows(folder/'peeq_saved_frames.csv');eng=rows(folder/'energy_history.csv');num=next(x for x in numeric['records'] if x['candidate_id']==cid)
   for name,digest in result['artifact_hashes'].items():assert sha(R/name)==digest
   step=ex['steps']['Step_Punch_Displacement'];rp=step['history_regions']['Node ASM_SPT.1'];hist=rp['outputs'];frames=step['frame_diagnostics'];histU=hist['U2']['data'];histF=hist['RF2']['data'];n=len(fd)
   assert ex['source_sha256_before']==ex['source_sha256_after']==p['files']['odb']['sha256']==result['odb_sha256']
   assert result['inp_sha256']==p['inp_sha256'] and result['queue_id']==p['queue_id'] and result['job_name']==p['job_name'] and result['project_id']==audit['project_id']
   assert n==len(raw)==len(peeq)==len(frames)==len(histU)==len(histF)==step['frame_count']==num['accepted_increments']+1
   assert 'SET_PUNCH_RP' in rp['description'] and result['punch_rp_identity']['instance']=='ASM_SPT' and result['punch_rp_identity']['node_label']==1
   uu=[];ff=[];field_errors=[]
   for i,(q,r,hU,hF,frame,pr) in enumerate(zip(fd,raw,histU,histF,frames,peeq)):
    assert q['step']==r['step']=='Step_Punch_Displacement' and int(q['frame_index'])==int(r['frame_index'])==i
    assert float(r['U2_raw_m'])==hU[1] and float(r['RF2_raw_n'])==hF[1] and float(r['step_time'])==hU[0]==hF[0]==frame['time']
    assert float(q['displacement_m'])==-hU[1] and float(q['force_n'])==-hF[1]
    assert frame['peeq_count_integration_point']==2376 and float(pr['max_peeq'])==frame['peeq_max']
    field_errors.append([abs(frame['rp_field']['U'][1]-hU[1]),abs(frame['rp_field']['RF'][1]-hF[1])]);uu.append(float(q['displacement_m']));ff.append(float(q['force_n']))
   assert max(v[0] for v in field_errors)==max(v[1] for v in field_errors)==0
   curve=Curve(tuple(uu),tuple(ff),'m','N');assert uu[0]<=u[0] and uu[-1]>=u[-1] and float(raw[-1]['step_time'])==1
   actualmax=max(float(v['max_peeq']) for v in peeq);assert actualmax==result['max_saved_peeq'] and actualmax<result['material_table_max_plastic_strain']==.9
   serious=[v for v in num['warning_events'] if v['outcome']=='ACCEPTED' and v['class'] not in ['ZERO_MOMENT']]
   recoil=[{'index':i+1,'u_mm':uu[i+1]*1000,'delta_force_N':b-a} for i,(a,b) in enumerate(zip(ff,ff[1:])) if b<a]
   blockers=[]
   if not p['software_completed'] or not p['single_attempt_confirmed']:blockers.append('EXECUTION_OR_ATTEMPT_IDENTITY')
   if ex['diagnostic_data']['jobStatus']!='JOB_STATUS_COMPLETED_SUCCESSFULLY' or ex['diagnostic_data']['numberOfAnalysisErrors']!=0:blockers.append('ODB_NOT_SUCCESSFUL')
   if serious:blockers.append('UNEXPLAINED_ACCEPTED_WARNING')
   if recoil:blockers.append('FORCE_RECOIL_REQUIRES_REVIEW')
   if result['numerical_blocking_issues']:blockers+=result['numerical_blocking_issues']
   eligible=not blockers
   m,fy,delta,residual=assess_curve(target,curve,base,software_status='COMPLETED_WITH_WARNINGS',numerical_accepted=eligible)
   if eligible and result['loss_or_null'] is not None:assert abs(m['loss']-result['loss_or_null'])<1e-14
   m.update(candidate_id=cid,job_name=p['job_name'],queue_id=p['queue_id'],software_completed=p['software_completed'],software_state=p['software_phase'],scoreability='SCOREABLE_EXPLORATORY' if eligible else 'UNSCOREABLE',numerical_qualification='ACCEPTED_FOR_THIS_EXPLORATORY_COMPARISON_WITH_WARNINGS' if eligible else 'BLOCKED_REVIEW_REQUIRED',not_mesh_or_asymptotic_numerical_validation=True,blocking_issues=blockers,max_saved_peeq=actualmax,runtime_s=p['actual_runtime_s'],cutback=num['cutback_increment_count'],numerical_warnings=result['numerical_review_warnings'],raw_point_count=n,force_recoil_events=recoil)
   if eligible:
    m['deltaLoss_vs_D01']=m['loss']-cc['baseline_SPT_loss'];m['deltaLoss_over_D01']=m['deltaLoss_vs_D01']/cc['baseline_SPT_loss']
   else:m['deltaLoss_vs_D01']=m['deltaLoss_over_D01']=None
   m['response_RMSE_over_observed_D01_increment_change']=m['RMSE_vs_D01_N']/.3383060028573848;m['max_force_difference_over_observed_D01_increment_change']=m['max_abs_force_difference_N']/1.8028578477856172;m['regularized_relative_over_observed_D01_increment_change']=m['max_regularized_relative_difference']/.012270485783721178
   allmetrics.append(m);aligned[cid]=fy;curves[cid]=curve;raw_ends[cid]={'u':np.array(uu),'f':np.array(ff)}
   checks.append({'candidate_id':cid,'INP_SHA256':result['inp_sha256'],'ODB_SHA256':result['odb_sha256'],'RP':'Node ASM_SPT.1','raw_to_history_and_sign_all_points':'PASS','field_history_max_errors':[0,0],'full_window':'PASS','material_table':'PASS','accepted_warning_classes':num['warning_counts_by_outcome']['ACCEPTED'],'recoil_count':len(recoil),'gate':m['scoreability']})
   sources.append({'candidate_id':cid,'result_path':str((folder/'result.json').relative_to(R)),'result_sha256':sha(folder/'result.json'),'FD_sha256':sha(folder/'force_displacement.csv'),'raw_history_sha256':sha(folder/'raw_history.csv'),'extraction_sha256':sha(folder/'odb_extraction.json')})
  except Exception as exc:
   allmetrics.append({'candidate_id':cid,'job_name':p['job_name'],'scoreability':'UNSCOREABLE','loss':None,'reason':str(exc),'traceback':traceback.format_exc()})
 if len(aligned)==3:
  symmetry=pair_symmetry(aligned['H01'],aligned['H02'],base)
 else:symmetry={'status':'NOT_EVALUABLE_MISSING_COMPLETE_CANDIDATE'}
 save(OUT/'independent_fd_checks.json',{'records':checks,'sources':sources,'no_new_solver_or_input':True})
 save(OUT/'response_metrics.json',{'version':'run053-main-independent-hardening-sensitivity-v1','loss_contract':binding['version'],'baseline_loss':cc['baseline_SPT_loss'],'grid_points':241,'reference_increment_RMSE_N':.3383060028573848,'reference_increment_max_difference_N':1.8028578477856172,'reference_increment_regularized_relative':.012270485783721178,'increment_changes_not_candidate_error_bounds':True,'records':allmetrics,'pair_symmetry':symmetry})
 table=[]
 for m in allmetrics:table.append({k:m.get(k) for k in ['candidate_id','job_name','scoreability','loss','RMSE_to_experiment_N','NRMSE_to_experiment','RMSE_vs_D01_N','max_abs_force_difference_N','max_regularized_relative_difference','deltaLoss_vs_D01','max_saved_peeq','cutback','runtime_s']})
 csvsave(OUT/'response_metrics.csv',table)
 bands=[]
 for m in allmetrics:
  for b in m.get('bands',[]):bands.append({'candidate_id':m['candidate_id'],'lower_mm':b['range_mm'][0],'upper_mm':b['range_mm'][1],**{k:v for k,v in b.items() if k!='range_mm'}})
 csvsave(OUT/'band_sensitivity.csv',bands)
 csvsave(OUT/'aligned_241_three_models.csv',[{'displacement_m':float(x),'experimental_force_N':float(exp[i]),**{f'{cid}_force_N':float(f[i]) for cid,f in aligned.items()}} for i,x in enumerate(u)])
 fig,ax=plt.subplots(figsize=(7,5));ax.plot(u*1000,exp,'k--',label='SPT experiment')
 for cid,d in raw_ends.items():ax.plot(d['u']*1000,d['f'],label=cid)
 ax.set(xlabel='Punch displacement (mm)',ylabel='Force (N)',title='Actual FE curves; frozen target and definitions');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'three_model_FD.png',dpi=180);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.2))
 for cid,fy in aligned.items():
  if cid=='D01':continue
  d=fy-base;axes[0].plot(u*1000,d,label=cid);axes[1].plot(u*1000,100*d/np.maximum(abs(base),71.445),label=cid)
 for ax in axes:ax.axhline(0,color='grey',lw=.7);ax.legend();ax.grid(alpha=.2);ax.set_xlabel('Punch displacement (mm)')
 axes[0].set_ylabel('Force difference vs D01 (N)');axes[1].set_ylabel('Signed regularized difference (%)');fig.tight_layout();fig.savefig(OUT/'force_difference_vs_D01.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4.5))
 for cid,fy in aligned.items():ax.plot(u*1000,fy-exp,label=cid)
 ax.axhline(0,color='grey');ax.set(xlabel='Punch displacement (mm)',ylabel='FE minus experiment (N)',title='Unshifted, unsmoothed residuals');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'experimental_residuals.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(6,4));valid=[m for m in allmetrics if m.get('loss') is not None];ax.bar([m['candidate_id'] for m in valid],[m['loss'] for m in valid]);ax.set(ylabel='Frozen normalized MSE Loss',title='Scoreable exploratory results only');fig.tight_layout();fig.savefig(OUT/'loss_comparison.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4.7))
 for cid in ['D01','H01','H02']:
  path=R/'run/run_046/artifacts/private/freeze/D01_abaqus_yield_stress_plastic_strain.csv' if cid=='D01' else R/f'run/run_051/artifacts/private/{cid}/yield_stress_plastic_strain.csv';r=rows(path);ax.plot([float(v['equivalent_plastic_strain']) for v in r],[float(v['yield_stress_pa'])/1e6 for v in r],label=cid)
 ax.axvline(.09774053167903649,ls='--',color='grey',label='p_switch');ax.set(xlabel='Equivalent plastic strain',ylabel='Yield stress (MPa)',title='Frozen deployed tables, no refitting');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'material_three_models.png',dpi=180);plt.close(fig)
 print(json.dumps({'records':table,'symmetry':symmetry},ensure_ascii=False))
if __name__=='__main__':main()
