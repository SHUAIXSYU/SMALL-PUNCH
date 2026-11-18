"""Independent MAIN data checks and execution of the frozen run060 comparator."""
from common62 import *
import numpy as np,math
from agenthub_sp_invopt.hub import Hub
from inverse.fd_loss import Curve,Target,interpolate
sys.path.insert(0,str(R/'run/run_060/artifacts'))
from resolution_metrics import compare_responses,stage_peeq

def verify(folder,expected,counts):
 result=read(folder/'result.json');ex=read(folder/'odb_extraction.json');fd=rows(folder/'force_displacement.csv');raw=rows(folder/'raw_history.csv');peeq=rows(folder/'peeq_saved_frames.csv')
 for path,h in result['artifact_hashes'].items():assert sha(R/path)==h,path
 assert result['inp_sha256']==expected['inp_sha256'] and result['odb_sha256']==expected['odb_sha256']
 assert ex['source_sha256_before']==ex['source_sha256_after']==expected['odb_sha256'] and ex['odb']['isReadOnly']
 assert ex['diagnostic_data']['jobStatus']=='JOB_STATUS_COMPLETED_SUCCESSFULLY' and ex['diagnostic_data']['numberOfAnalysisErrors']==0
 step=ex['steps']['Step_Punch_Displacement'];rp=step['history_regions']['Node ASM_SPT.1'];h=rp['outputs'];frames=step['frame_diagnostics']
 assert 'SET_PUNCH_RP' in rp['description']
 n=len(fd);assert n==len(raw)==len(peeq)==len(frames)==len(h['U2']['data'])==len(h['RF2']['data'])==counts['accepted_increments']+1
 u=[];f=[];maxp=[];field=[]
 for i,(a,b,c,hu,hf,frame) in enumerate(zip(fd,raw,peeq,h['U2']['data'],h['RF2']['data'],frames)):
  assert int(a['frame_index'])==int(b['frame_index'])==frame['frame_index']==i
  assert float(b['U2_raw_m'])==hu[1] and float(b['RF2_raw_n'])==hf[1]
  assert float(b['step_time'])==hu[0]==hf[0]==frame['time']
  assert float(a['displacement_m'])==-hu[1] and float(a['force_n'])==-hf[1]
  assert float(c['max_peeq'])==frame['peeq_max'] and frame['peeq_count_integration_point']==2376
  field.append([abs(frame['rp_field']['U'][1]-hu[1]),abs(frame['rp_field']['RF'][1]-hf[1])]);u.append(-hu[1]);f.append(-hf[1]);maxp.append(frame['peeq_max'])
 assert np.max(field,axis=0).tolist()==[0.,0.]
 curve=Curve(tuple(u),tuple(f),'m','N');assert u[0]<=0 and u[-1]>=.0012 and h['U2']['data'][-1][0]==1
 assert max(maxp)==result['max_saved_peeq']<.9
 # Match the full ODB material table to source INP, not only endpoints.
 inp=(R/expected['inp_path']).read_bytes();ls=inp.splitlines();i=next(i for i,l in enumerate(ls) if l.strip().upper()==b'*PLASTIC')+1;k=i
 while k<len(ls) and not ls[k].lstrip().startswith(b'*'):k+=1
 table=[list(map(float,l.split(b','))) for l in ls[i:k] if l.strip()];ms=ex['material_summary']['Q200N01']
 assert hashlib.sha256(json.dumps(table,sort_keys=True).encode()).hexdigest()==ms['plastic']['table_sha256']
 assert ms['elastic']['first_row']==[210e9,.3] and table[-1][1]==.9 and len(table)==34
 events=[];peaks=[]
 for i in range(1,n):
  c=frames[i].get('contact',{});before=frames[i-1].get('contact',{});df=f[i]-f[i-1];du=u[i]-u[i-1]
  if c.get('available') and before.get('available'):
   added=set(c['positive_cpress_node_labels'])-set(before['positive_cpress_node_labels']);lost=set(before['positive_cpress_node_labels'])-set(c['positive_cpress_node_labels'])
   if added or lost:events.append({'frame_index':i,'increment':frames[i]['increment'],'u_mm':u[i]*1000,'delta_F_N':df,'new_positive_nodes':sorted(added),'lost_positive_nodes':sorted(lost)})
  peaks.append({'frame_index':i,'increment':frames[i]['increment'],'step_time':frames[i]['time'],'u_before_mm':u[i-1]*1000,'u_mm':u[i]*1000,'delta_F_N':df,'secant_N_per_mm':df/(du*1000),'previous_contact':before.get('topology_node_values'),'current_contact':c.get('topology_node_values')})
 recoil=[p for p in peaks if p['delta_F_N']<0]
 severe=[v for v in counts['events'] if v['outcome']=='ACCEPTED_TRIAL' and v['class']!='ZERO_MOMENT']
 blockers=[]
 if severe:blockers.append('UNEXPLAINED_ACCEPTED_SERIOUS_WARNING')
 if counts['unconfirmed_accepted_equilibrium']:blockers.append('UNCONFIRMED_ACCEPTED_EQUILIBRIUM')
 check={'raw_points':n,'RP':'Node ASM_SPT.1','step':'Step_Punch_Displacement','u=-U2_F=-RF2_all_native_points':True,'units':'m,N; no2pi','Field_History_max_errors':[0.,0.],'all_saved_frame_PEEQ_max':max(maxp),'end_u_m':u[-1],'coverage_complete':True,'table_byte_identity_verified_in_execution_audit':True,'ODB_full_material_digest_matches_INP':True,'table_max_p':.9,'force_recoil':recoil,'blockers':blockers,'SCIENTIFIC_SCOREABILITY':'SCOREABLE' if not blockers else 'UNRESOLVED','NUMERICAL_QUALITY':'WARNING','native_force_largest_steps':sorted(peaks,key=lambda x:abs(x['delta_F_N']),reverse=True)[:10],'contact_positive_proxy_events':events,'artifact_hash_count':len(result['artifact_hashes']),'result_sha256':sha(folder/'result.json')}
 return curve,np.array(maxp),ex,check

def main():
 ids=read(P/'task_ids.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3');task=hub.task(ids['odb_task_id']);assert task['execution_state']=='COMPLETED','Real ODB task must finish before MAIN analysis'
 assert task['lease_agent']=='ODB:ODB-real-run062' and task['generation']==1
 assert hub.session_identity(task['lease_session'])['role']=='ODB' and hub.verify_chain()
 ccpath=R/'run/run_060/artifacts/comparison_contract.json';cc=read(ccpath);expected=read(R/'run/run_060/artifacts/prepared_batch.json');assert sha(ccpath)==expected['comparison_contract_sha256']
 for key in ['metrics_implementation']:assert sha(R/cc[key])==cc[key+'_sha256']
 binding=cc['loss_binding']
 for k in ['target','config','implementation']:assert sha(R/binding[k+'_path'])==binding[k+'_sha256']
 assert sha(R/cc['weak_reference']['source_path'])==cc['weak_reference']['source_sha256']
 old=cc['baseline'];actual=read(P/'execution_audit.json')['record'];new={**cc['candidate'],'odb_sha256':actual['files']['odb']['sha256']}
 nums=read(P/'MAIN_independent_raw_numerical_audit.json');oldc,oldp,oldex,ocheck=verify((R/old['fd_path']).parent,old,nums['original']);newc,newp,newex,ncheck=verify(P/'odb/I06_REFINED',new,nums['refined'])
 checks={'at':now(),'actual_ODB_agent_id':task['lease_agent'],'actual_ODB_session':task['lease_session'],'formal_task_id':ids['odb_task_id'],'original':ocheck,'refined':ncheck,'source_review':'MAIN independently recomputed from raw histories, fields, INP and STA/MSG, not copied ODB conclusions','audit_chain_valid':True}
 save(P/'MAIN_independent_data_review.json',checks)
 assert not ocheck['blockers'] and not ncheck['blockers'],'Unsafe candidate cannot be scored'
 exp=rows(R/binding['target_path'])[:241];grid=np.array([float(x['displacement_m']) for x in exp]);ef=np.array([float(x['force_n']) for x in exp]);assert grid.tolist()==cc['grid_m']
 target=Target(Curve(tuple(grid),tuple(ef),'m','N'),(1.,)*241,1428.9,binding['version'])
 weak=cc['weak_reference']['value_RMS_N'];metrics=compare_responses(target,oldc,newc,weak_RMS_N=weak)
 a=np.array(interpolate(oldc,grid));b=np.array(interpolate(newc,grid));delta=b-a
 # Independent NumPy arithmetic versus the previously frozen Python fsum comparator.
 assert abs(np.sqrt(np.mean(delta**2))-metrics['force_difference_RMSE_N'])<1e-12
 for name,f in [('original',a),('refined',b)]:assert abs(float(np.mean(((f-ef)/1428.9)**2))-metrics[name+'_loss'])<1e-15
 assert abs(metrics['original_loss']-old['recorded_loss'])<1e-15
 segments=[]
 for lo,hi in [(0,.3),(.3,.6),(.6,.9),(.9,1.2)]:
  mask=(grid*1000>=lo-1e-10)&((grid*1000<hi-1e-10) if hi<1.2 else (grid*1000<=hi+1e-10));ix=np.flatnonzero(mask);di=delta[mask];i=ix[np.argmax(abs(di))]
  segments.append({'lower_mm':lo,'upper_mm':hi,'partition':'left closed, right open; final includes1.2','points':len(ix),'RMSE_N':float(np.sqrt(np.mean(di**2))),'max_abs_N':float(np.max(abs(di))),'max_at_mm':float(grid[i]*1000),'sum_squares_fraction':float(np.sum(di**2)/np.sum(delta**2)) if np.any(delta) else 0.,'mean_signed_N':float(np.mean(di)),'original_experiment_RMSE_N':float(np.sqrt(np.mean((a[mask]-ef[mask])**2))),'refined_experiment_RMSE_N':float(np.sqrt(np.mean((b[mask]-ef[mask])**2)))})
 assert sum(x['points'] for x in segments)==241
 csvsave(P/'aligned_241_difference.csv',[{'u_m':float(u),'u_mm':float(u*1000),'original_force_N':float(x),'refined_force_N':float(y),'experiment_force_N':float(e),'difference_refined_minus_original_N':float(y-x),'regularized_relative_abs':float(abs(y-x)/max(abs(x),71.445))} for u,x,y,e in zip(grid,a,b,ef)])
 csvsave(P/'segment_metrics.csv',segments)
 stages=[];oldstage=stage_peeq(oldc.displacement,oldp);newstage=stage_peeq(newc.displacement,newp)
 for x,y in zip(oldstage,newstage):stages.append({'target_m':x['target_m'],'original':x,'refined':y,'delta_interpolated_scalar_max':y['interpolated_frame_max_peeq']-x['interpolated_frame_max_peeq'],'exact_same_material_point_field_difference':False})
 i=int(np.argmax(abs(delta)));location=float(grid[i]*1000)
 context={}
 for name,curve,ex in [('original',oldc,oldex),('refined',newc,newex)]:
  u=np.array(curve.displacement)*1000;frames=ex['steps']['Step_Punch_Displacement']['frame_diagnostics'];around=np.flatnonzero((u>=location-.012)&(u<=location+.012));local=np.flatnonzero((u>=1.10)&(u<=1.16))
  def frame_info(k):
   frame=frames[k];return {'frame_index':int(k),'increment':frame['increment'],'time':frame['time'],'u_mm':float(u[k]),'force_N':curve.force[k],'PEEQ_max':frame['peeq_max'],'contact':frame.get('contact')}
  context[name]={'around_max241_difference':list(map(frame_info,around)),'all_1p10_to_1p16_native_accepted_frames':list(map(frame_info,local)),'native_frames':len(frames),'max241_difference_location_mm':location}
 save(P/'contact_and_peak_context.json',{'at':now(),'context':context,'contact_relationship':'association from saved pressure/gap and force histories only; no unique mechanism proved','COPEN_missing_rule':'abs>=1e30 sentinel; never interpret as gap'})
 for name,ex in [('original',oldex),('refined',newex)]:
  regions=ex['steps']['Step_Punch_Displacement']['history_regions'];energy=regions.get('Assembly ASSEMBLY',{}).get('outputs',{});save(P/(name+'_energy_summary.json'),{'outputs':{k:{'points':len(v.get('data',[])),'first':v.get('data',[None])[0],'last':v.get('data',[None])[-1]} for k,v in energy.items()},'scope':'available global histories, no decomposition into Punch RF2 contribution'})
 oldA=read(R/cc['weak_reference']['source_path']);J=np.array(oldA['views']['full241']['J']);U,s,V=np.linalg.svd(J,full_matrices=False);zn=delta/1428.9/np.sqrt(241)
 projection={'status':'EXPLORATORY_ONLY_NOT_A_NEW_JACOBIAN','projection_on_old_weak_left_direction_RMS_N':float(abs(U[:,-1]@zn)*1428.9),'fraction_of_difference_norm_in_weak_left_direction':float(abs(U[:,-1]@zn)/np.linalg.norm(zn)) if np.any(zn) else None,'weak_left_projection_over_frozen_weak_RMS':float(abs(U[:,-1]@zn)*1428.9/weak),'old_run059_J_unchanged':True,'not_parameter_bias_or_confidence_interval':True}
 metrics.update(max_absolute_at_mm=metrics['max_absolute_at_m']*1000,max_regularized_relative_at_mm=metrics['max_regularized_relative_at_m']*1000,max_difference_over_weak_RMS_descriptive=metrics['max_absolute_force_difference_N']/weak,original_max_PEEQ=float(max(oldp)),refined_max_PEEQ=float(max(newp)),delta_global_max_PEEQ=float(max(newp)-max(oldp)),original_vs_refined_runtime_s=[294,actual['actual_runtime_s']],segments=segments,PEEQ_stages=stages,exploratory_weak_projection=projection,numerics={'original':{k:v for k,v in nums['original'].items() if k in ['accepted_increments','cutback_count','rejected_attempts','warning_counts','total_equilibrium_iterations_all_trials']},'refined':{k:v for k,v in nums['refined'].items() if k in ['accepted_increments','cutback_count','rejected_attempts','warning_counts','total_equilibrium_iterations_all_trials']}},scoreability={'original':'SCOREABLE_WITH_LIMITATIONS','refined':'SCOREABLE_WITH_WARNINGS'},unchanged_run059_conditions={k:{'condition_number':oldA['views'][k]['condition_number'],'cosine':oldA['views'][k]['cosine']} for k in ['two_loads','five_features','full241']})
 save(P/'refinement_metrics.json',metrics);save(P/'verified_plot_arrays.json',{'grid_m':grid.tolist(),'original_N':a.tolist(),'refined_N':b.tolist(),'experiment_N':ef.tolist(),'original_native_u_m':list(oldc.displacement),'original_native_force_N':list(oldc.force),'refined_native_u_m':list(newc.displacement),'refined_native_force_N':list(newc.force),'old_max_PEEQ':oldp.tolist(),'new_max_PEEQ':newp.tolist()})
 print(json.dumps({k:metrics[k] for k in ['force_difference_RMSE_N','max_absolute_force_difference_N','max_absolute_at_mm','max_regularized_relative_difference','original_loss','refined_loss','delta_loss','R_RMSE','risk_band','original_max_PEEQ','refined_max_PEEQ']}))
if __name__=='__main__':main()
