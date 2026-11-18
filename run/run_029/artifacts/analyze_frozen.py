"""Apply the pre-solve frozen 241-point loss/comparison to an accepted real ODB CSV."""
import argparse,csv,hashlib,importlib.util,json,math,sys
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_029/artifacts';P=A/'private'
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
from inverse.fd_loss import Curve,Target,interpolate
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def curve(p,x='displacement_m',y='force_n'):
 data=rows(p);return Curve(tuple(float(r[x]) for r in data),tuple(float(r[y]) for r in data),'m','N')
def writecsv(p,fields,data):
 with p.open('x',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(fields);w.writerows(data)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fd',required=True);ap.add_argument('--max-peeq',type=float,required=True);args=ap.parse_args()
 out=P/'comparison';out.mkdir(parents=True,exist_ok=True)
 assert not (out/'frozen_comparison.json').exists()
 contract_path=ROOT/'run/run_027/artifacts/comparison_contract.json';c=read(contract_path)
 assert c['version']=='run027-adjacent-refinement-v1' and sha(contract_path)=='e189ab1551f775f085fc0208e0550784db85fa3b258b6164db1f8a20c148d42a'
 base=read(ROOT/c['run023_contract_path']);assert sha(ROOT/c['run023_contract_path'])==c['run023_contract_sha256']
 assert sha(ROOT/c['comparison_implementation_path'])==c['comparison_implementation_sha256']
 assert sha(ROOT/c['loss_implementation_path'])==c['loss_implementation_sha256']
 assert sha(ROOT/c['target_path'])==c['target_sha256']
 assert sha(ROOT/c['primary']['original_fd_path'])==c['primary']['original_fd_sha256']
 assert sha(ROOT/c['auxiliary']['fd_path'])==c['auxiliary']['fd_sha256']
 fd=Path(args.fd).resolve();assert fd.is_file() and fd.is_relative_to(P/'odb')
 target_data=rows(ROOT/c['target_path'])[:241];grid=tuple(base['grid_m']);assert len(target_data)==len(grid)==241
 assert all(abs(float(r['displacement_m'])-u)<1e-17 for r,u in zip(target_data,grid))
 target=Target(Curve(grid,tuple(float(r['force_n']) for r in target_data),'m','N'),tuple([1.]*241),1428.9,'run017-exploratory-fd-v1')
 v=curve(ROOT/c['primary']['original_fd_path']);old=curve(ROOT/c['auxiliary']['fd_path'],'displacement_model_length','force_model_force');new=curve(fd)
 spec=importlib.util.spec_from_file_location('frozen_compare',ROOT/c['comparison_implementation_path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 p=m.compare(target,v,new,base,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
 aux=m.compare(target,old,new,base,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
 previous=m.compare(target,old,v,base,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
 assert math.isclose(previous['force_rmse_n'],3.9987751586240563,abs_tol=1e-11)
 assert math.isclose(previous['max_absolute_force_n'],19.558200999730843,abs_tol=1e-11)
 v_interp=interpolate(v,grid);n_interp=interpolate(new,grid);c_interp=interpolate(old,grid)
 d=[x-y for x,y in zip(n_interp,v_interp)]
 assert math.isclose(math.sqrt(math.fsum(x*x for x in d)/241),p['force_rmse_n'],abs_tol=1e-11)
 assert max(abs(x) for x in d)==p['max_absolute_force_n']
 loss_v=p['original_loss'];loss_n=p['validation_loss']
 # Independent explicit fixed formula check, not a changed objective.
 exp=target.curve.force
 direct_v=math.fsum(((f-e)/1428.9)**2 for f,e in zip(v_interp,exp))/241
 direct_n=math.fsum(((f-e)/1428.9)**2 for f,e in zip(n_interp,exp))/241
 assert math.isclose(loss_v,direct_v,abs_tol=1e-15) and math.isclose(loss_n,direct_n,abs_tol=1e-15)
 v_peeq=read(ROOT/'run/run_025/artifacts/private/main_comparison.json')['peeq']['validation']
 peeq_delta=args.max_peeq-v_peeq
 peeq={'V01':v_peeq,'candidate':args.max_peeq,'delta':peeq_delta,'absolute_delta':abs(peeq_delta),'threshold':c['thresholds']['max_saved_peeq_absolute_change'],'delta_pass':abs(peeq_delta)<=c['thresholds']['max_saved_peeq_absolute_change'],'material_table_upper':0.9,'within_table':args.max_peeq<=0.9}
 checks={**p['checks'],'saved_peeq_delta':peeq['delta_pass'],'saved_peeq_within_table':peeq['within_table']}
 local=[i for i,u in enumerate(grid) if 0.00110<=u<=0.00116]
 local_data={'points':len(local),'max_abs_diff_n':max(abs(d[i]) for i in local),'rmse_n':math.sqrt(math.fsum(d[i]**2 for i in local)/len(local)),'max_at_mm':grid[max(local,key=lambda i:abs(d[i]))]*1000}
 writecsv(out/'aligned_241.csv',['displacement_m','experimental_force_n','run014_force_n','V01_force_n','candidate_force_n','candidate_minus_V01_n','candidate_minus_run014_n'],zip(grid,exp,c_interp,v_interp,n_interp,d,(n-c for n,c in zip(n_interp,c_interp))))
 fig,axes=plt.subplots(2,1,figsize=(8.5,8),sharex=True)
 axes[0].plot([x*1000 for x in grid],c_interp,label='run014',lw=1.5)
 axes[0].plot([x*1000 for x in grid],v_interp,label='V01',lw=1.5)
 axes[0].plot([x*1000 for x in grid],n_interp,label='new 0.0025',lw=1.5)
 axes[0].set_ylabel('Punch force (N)');axes[0].legend();axes[0].grid(alpha=.2)
 axes[1].plot([x*1000 for x in grid],d,label='new minus V01',lw=1.4)
 axes[1].axhline(7.1445,color='r',ls='--',alpha=.6);axes[1].axhline(-7.1445,color='r',ls='--',alpha=.6)
 axes[1].set(xlabel='Punch displacement (mm)',ylabel='Force difference (N)');axes[1].grid(alpha=.2)
 fig.tight_layout();fig.savefig(out/'full_comparison.png',dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4.5));xx=[grid[i]*1000 for i in local]
 ax.plot(xx,[v_interp[i] for i in local],label='V01');ax.plot(xx,[n_interp[i] for i in local],label='new 0.0025');ax.plot(xx,[c_interp[i] for i in local],label='run014',alpha=.7)
 ax.set(xlabel='Punch displacement (mm)',ylabel='Punch force (N)',title='1.10–1.16 mm accepted-history interpolation');ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(out/'focus_110_116.png',dpi=190);plt.close(fig)
 result={'at':datetime.now().astimezone().isoformat(),'contract_version':c['version'],'contract_sha256':sha(contract_path),'implementation_sha256':c['comparison_implementation_sha256'],'loss_version':c['loss_version'],'candidate_fd_path':str(fd.relative_to(ROOT)).replace('\\','/'),'candidate_fd_sha256':sha(fd),'candidate_points':len(new.displacement),'candidate_range_m':[new.displacement[0],new.displacement[-1]],'primary_V01':p,'auxiliary_run014':aux,'prior_run014_to_V01':previous,'peeq':peeq,'checks':checks,'all_quantitative_pass':all(checks.values()),'local_110_116':local_data,'formal_qualification':'PENDING_NUMERICAL_DIAGNOSTIC_REVIEW','no_resampling_window_change':True}
 with (out/'frozen_comparison.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({'primary':p,'peeq':peeq,'local':local_data,'all_quantitative_pass':result['all_quantitative_pass']},ensure_ascii=False))
if __name__=='__main__':main()
