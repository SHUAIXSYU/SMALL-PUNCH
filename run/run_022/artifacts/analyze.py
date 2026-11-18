"""Frozen-target analysis of reviewed existing ODB CSVs; never calls Abaqus."""
import sys,os,json,csv,hashlib,math,re,importlib.util
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_022/artifacts';P=OUT/'private';AN=P/'analysis'
os.environ['MPLCONFIGDIR']=str(P/'mplconfig');sys.path.insert(0,str(ROOT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvout(p,headers,data):
    with p.open('x',encoding='utf8',newline='') as f:w=csv.writer(f);w.writerow(headers);w.writerows(data)
def curve(path):
    rs=rows(path)
    if {'displacement_m','force_n'}<=rs[0].keys():uk,fk='displacement_m','force_n'
    elif {'displacement_model_length','force_model_force'}<=rs[0].keys():uk,fk='displacement_model_length','force_model_force'
    else:raise ValueError('Unreviewed FD schema')
    return Curve(tuple(float(r[uk]) for r in rs),tuple(float(r[fk]) for r in rs),'m','N')
def logs(rec):
    if not rec['files']['msg']['exists']:return dict(status=rec['execution'],cutbacks=None,warnings=None,duration_sec=rec['duration_sec'])
    msg=(ROOT/rec['files']['msg']['path']).read_text(errors='replace');log=(ROOT/rec['files']['log']['path']).read_text(errors='replace');sta=(ROOT/rec['files']['sta']['path']).read_text(errors='replace')
    summary=msg.split('ANALYSIS SUMMARY:')[-1]
    def count(pattern):
        m=re.search(pattern,summary);return int(m[1]) if m else None
    phases={}
    for ph in ['DATACHECK_RUNNING','FULL_RUNNING']:
        starts=list(re.finditer(r'\[([^]]+)\] START '+ph,log));ends=list(re.finditer(r'\[([^]]+)\] END '+ph+r' return_code=(-?\d+)',log))
        phases[ph]=dict(start_count=len(starts),end_count=len(ends),return_code=int(ends[0][2]) if len(ends)==1 else None,duration_sec=(datetime.fromisoformat(ends[0][1])-datetime.fromisoformat(starts[0][1])).total_seconds() if len(starts)==len(ends)==1 else None)
    attempts=list(re.finditer(r'INCREMENT\s+(\d+) STARTS\. ATTEMPT NUMBER\s+(\d+)',msg));warnings=[]
    for m in re.finditer(r'\*\*\*WARNING:[^\n]*(?:\n +[^\n]*)?',msg):
        a=next((a for a in reversed(attempts) if a.start()<m.start()),None);end=next((a.start() for a in attempts if a.start()>m.start()),len(msg))
        warnings.append(dict(text=m.group().strip(),line=msg[:m.start()].count('\n')+1,increment=int(a[1]) if a else None,attempt=int(a[2]) if a else None,attempt_accepted='TIME INCREMENT COMPLETED' in msg[m.start():end]))
    dat=(ROOT/rec['files']['dat']['path']).read_text(errors='replace')
    return dict(status=rec['execution'],duration_sec=rec['duration_sec'],allocated_core_hours=rec['duration_sec']*14/3600 if rec['duration_sec'] is not None else None,phases=phases,increments=count(r'TOTAL OF\s+(\d+)\s+INCREMENTS'),cutbacks=count(r'(\d+)\s+CUTBACKS'),negative_eigenvalue_warning_count=count(r'(\d+)\s+ANALYSIS WARNINGS ARE NEGATIVE EIGENVALUE'),errors=count(r'(\d+)\s+ERROR MESSAGES'),warnings=warnings,distortion_headers=sum('EXCESSIVE DISTORTION' in w['text'].upper() for w in warnings),negative_headers=sum('NEGATIVE EIGENVALUES' in w['text'].upper() for w in warnings),dat_warning_lines=[l for l in dat.splitlines() if 'WARNING' in l or 'TRACKING' in l],sta_complete='THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in sta)
def main():
    mapping=read(P/'reviewed_fd_inputs.json');audit=read(P/'execution_audit_completed.json')
    AN.mkdir(exist_ok=False)
    ident=read(ROOT/'run/run_017/artifacts/loss_contract_identity.json');cfg=read(ROOT/ident['path'])
    assert sha(ROOT/ident['path'])==ident['sha256'] and sha(ROOT/ident['implementation'])==ident['implementation_sha256']
    assert sha(ROOT/cfg['target'])==cfg['target_sha256'] and cfg['version']=='run017-exploratory-fd-v1'
    exp=rows(ROOT/cfg['target']);selected=[r for r in exp if 0<=float(r['displacement_m'])<=.0012];assert len(exp)==339 and len(selected)==241
    u=np.array([float(r['displacement_m']) for r in selected]);fe=np.array([float(r['force_n']) for r in selected]);ref=cfg['force_reference_n'];assert ref==1428.9
    target=Target(Curve(tuple(u),tuple(fe),'m','N'),tuple([1.]*len(u)),ref,cfg['version'])
    ev=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True)
    center=read(ROOT/'run/run_017/artifacts/private/reference_loss.json');assert sha(ROOT/center['fe_source'])==center['fe_sha256']
    c=curve(ROOT/center['fe_source']);curves={'C':c};sources={'C':dict(path=center['fe_source'],sha256=center['fe_sha256'])}
    for key,v in mapping.items():
        assert key in {'L01','L02','L03','L04'} and sha(ROOT/v['path'])==v['sha256']
        assert v['review_status']=='ACCEPTED_FOR_EXPLORATORY_SCORING'
        curves[key]=curve(ROOT/v['path']);sources[key]=v
    scores={};pred={}
    for key,c in curves.items():
        score=evaluate(target,c,fe_status='COMPLETED_WITH_WARNINGS',evidence=ev,mode='PROVISIONAL')
        pred[key]=np.array(interpolate(c,u));rmse=float(np.sqrt(np.mean((pred[key]-fe)**2)))
        assert math.isclose(score['loss'],(rmse/ref)**2,rel_tol=1e-13)
        score.update(rmse_n=rmse,nrmse=rmse/ref,fd_points=len(c.force));scores[key]=score
    assert math.isclose(scores['C']['loss'],center['loss'],rel_tol=1e-14)
    design=read(ROOT/'run/run_020/artifacts/prepared_batch.json');table=[dict(point_id='C',job_name='SPIO_R014_Q200_N010',sigma_y_mpa=200.,n=.1,status='COMPLETED_WITH_WARNINGS',duration_sec=165,**scores['C'])]
    numerics={}
    for rec in audit['records']:
        p=rec['point'];key=p['point_id'];score=scores.get(key,dict(loss=None,rmse_n=None,nrmse=None,fd_points=None))
        table.append(dict(point_id=key,job_name=p['job_name'],sigma_y_mpa=p['sigma_y_mpa'],n=p['n'],status=rec['execution'],duration_sec=rec['duration_sec'],**score));numerics[key]=logs(rec)
    spec=importlib.util.spec_from_file_location('frozen_local',ROOT/'run/run_020/artifacts/local_sensitivity.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    sensitivity=mod.analyze(pred,u)
    sensitivity['symmetry']={}
    for name,minus,plus in [('x','L01','L02'),('y','L03','L04')]:
        if {minus,plus}<=pred.keys():
            a=pred[plus]-pred['C'];b=pred['C']-pred[minus]
            rms=lambda v:float(np.sqrt(np.mean(v*v)))
            sensitivity['symmetry'][name]=dict(positive_response_rms_n=rms(a),negative_response_rms_n=rms(b),even_component_rms_n=rms((a-b)/2),odd_component_rms_n=rms((a+b)/2),even_to_odd_ratio=rms(a-b)/rms(a+b) if rms(a+b)>0 else None)
    if {'L01','L02','L03','L04'}<=pred.keys():
        J=np.column_stack(((pred['L02']-pred['L01'])/.1,(pred['L04']-pred['L03'])/.1));gram=J.T@J;sv=np.sqrt(np.maximum(0,np.linalg.eigvalsh(gram)))[::-1]
        assert np.allclose(sv,sensitivity['matrix']['singular_values_raw'],rtol=1e-9,atol=1e-9)
        _,_,vt=np.linalg.svd(J,full_matrices=False);sensitivity['weakest_normalized_parameter_direction']=vt[-1].tolist();sensitivity['gram_crosscheck_passed']=True
        sensitivity['physical_derivative_rms']=dict(sigma_y_N_per_MPa=float(np.sqrt(np.mean((J[:,0]/(200*math.log(1000/150)))**2))),n_N_per_n=float(np.sqrt(np.mean((J[:,1]/.48)**2))))
        csvout(AN/'sensitivities.csv',['displacement_m','Sx_N_per_normalized_x','Sy_N_per_normalized_y'],zip(u,J[:,0],J[:,1]))
        fig,ax=plt.subplots(figsize=(8,4));ax.plot(u*1000,J[:,0]/ref,label='Sx / F_ref');ax.plot(u*1000,J[:,1]/ref,label='Sy / F_ref');ax.set(xlabel='Punch displacement (mm)',ylabel='Normalized force sensitivity',title='Local secants, h=0.05');ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(AN/'sensitivity.png',dpi=160);plt.close(fig)
    save(AN/'sensitivity.json',sensitivity);save(AN/'numerical_audit.json',numerics)
    result=dict(observed_at=datetime.now().astimezone().isoformat(),contract=cfg['version'],contract_sha256=ident['sha256'],target_sha256=cfg['target_sha256'],implementation_sha256=ident['implementation_sha256'],rows=table,best_available=min(scores,key=lambda k:scores[k]['loss']),sources=sources,scope='FROZEN_EXPLORATORY_COMPARISON_NOT_PHYSICAL_VALIDATION')
    save(AN/'loss_results.json',result)
    headers=['point_id','job_name','sigma_y_mpa','n','loss','rmse_n','nrmse','status','duration_sec'];csvout(AN/'loss_comparison.csv',headers,[[r.get(k) for k in headers] for r in table])
    csvout(AN/'aligned_curves.csv',['displacement_m','experimental_force_n']+[k+'_force_n' for k in pred],zip(u,fe,*pred.values()))
    fig,ax=plt.subplots(figsize=(8,5));ax.plot(u*1000,fe,'k-',lw=2,label='SA508 experiment (fixed)')
    for k,c in curves.items():ax.plot(np.array(c.displacement)*1000,c.force,label=k+(' run014' if k=='C' else ''))
    ax.set(xlabel='Punch displacement (mm)',ylabel='Force (N)',xlim=(0,1.2),title='Existing FE results vs frozen experiment');ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(AN/'fd_overlay.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for k in pred:
        if k!='C':ax.plot(u*1000,pred[k]-pred['C'],label=k)
    ax.axhline(0,color='gray',lw=.8);ax.set(xlabel='Punch displacement (mm)',ylabel='Force difference from center (N)');ax.grid(alpha=.25)
    if len(pred)>1:ax.legend()
    fig.tight_layout();fig.savefig(AN/'center_differences.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));ax.bar(list(scores),[s['loss'] for s in scores.values()]);ax.set(ylabel='Normalized MSE (dimensionless)',title='Frozen exploratory Loss');fig.tight_layout();fig.savefig(AN/'loss_comparison.png',dpi=160);plt.close(fig)
    print(json.dumps(dict(losses={k:v['loss'] for k,v in scores.items()},sensitivity=sensitivity['matrix'],symmetry=sensitivity['symmetry']),ensure_ascii=False))
if __name__=='__main__':main()
