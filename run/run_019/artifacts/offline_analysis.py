"""MAIN independent offline loss/log verification. No execution/queue interfaces."""
import sys,os,json,csv,hashlib,math,re
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_019/artifacts/private';AN=OUT/'main_analysis'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(OUT/'mplconfig')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    assert not p.exists(),p
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8');read(t);t.replace(p)
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,cols,rows):
    with p.open('x',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(cols);w.writerows(rows)
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat()

def audit_logs(rec):
    if rec['execution']=='NOT_FOUND':return dict(point=rec['point']['point_id'],status='NOT_FOUND')
    msg=(ROOT/rec['files']['msg']['path']).read_text(errors='replace');log=(ROOT/rec['files']['log']['path']).read_text(errors='replace');sta=(ROOT/rec['files']['sta']['path']).read_text(errors='replace')
    summary=msg.split('ANALYSIS SUMMARY:')[-1]
    def count(regex):
        m=re.search(regex,summary);return int(m.group(1)) if m else None
    phases={}
    for phase in ('DATACHECK_RUNNING','FULL_RUNNING'):
        start=re.search(r'\[([^]]+)\] START '+phase,log);end=re.search(r'\[([^]]+)\] END '+phase+r' return_code=(-?\d+)',log)
        phases[phase]=dict(start=start[1] if start else None,end=end[1] if end else None,return_code=int(end[2]) if end else None,duration_sec=(datetime.fromisoformat(end[1])-datetime.fromisoformat(start[1])).total_seconds() if start and end else None)
    attempts=[]
    for m in re.finditer(r'INCREMENT\s+(\d+) STARTS\. ATTEMPT NUMBER\s+(\d+)',msg):
        attempts.append(dict(increment=int(m[1]),attempt=int(m[2]),offset=m.start()))
    warnings=[]
    for m in re.finditer(r'\*\*\*WARNING:[^\n]*(?:\n +[^\n]*)?',msg):
        a=next((a for a in reversed(attempts) if a['offset']<m.start()),None)
        nexta=next((z for z in attempts if z['offset']>m.start()),None)
        end=nexta['offset'] if nexta else len(msg)
        accepted='TIME INCREMENT COMPLETED' in msg[m.start():end]
        warnings.append(dict(line=msg[:m.start()].count('\n')+1,text=m.group().strip(),increment=a['increment'] if a else None,attempt=a['attempt'] if a else None,attempt_accepted=accepted))
    rows=[s.split() for s in sta.splitlines() if re.match(r'^\s*\d+\s+\d+\s+\d+U?\s+',s)]
    return dict(point=rec['point']['point_id'],status=rec['execution'],phases=phases,queue_duration_sec=rec['duration_sec'],allocated_core_hours=rec['duration_sec']*14/3600,
        increments=count(r'TOTAL OF\s+(\d+)\s+INCREMENTS'),cutbacks=count(r'(\d+)\s+CUTBACKS'),iterations=count(r'(\d+)\s+ITERATIONS INCLUDING'),
        negative_eigenvalue_warning_count=count(r'(\d+)\s+ANALYSIS WARNINGS ARE NEGATIVE EIGENVALUE'),numerical_problem_warning_count=count(r'(\d+)\s+ANALYSIS WARNINGS ARE NUMERICAL PROBLEM'),
        solver_errors=count(r'(\d+)\s+ERROR MESSAGES'),warning_events=warnings,sta_rejected_rows=sum('U' in s[2] for s in rows),
        distortion_keyword_lines=[dict(line=i+1,text=s) for i,s in enumerate(msg.splitlines()) if 'distort' in s.lower()],
        cost_note='Queue phase wallclock includes launcher/processor/wrap-up; allocated core hours are not measured CPU consumption')

def main():
    assert len(sys.argv)==2,'Pass reviewed ODB FD CSV path'
    fdpath=Path(sys.argv[1]).resolve();assert fdpath.is_relative_to(OUT/'odb')
    AN.mkdir(exist_ok=False)
    identity=read(ROOT/'run/run_017/artifacts/loss_contract_identity.json');configpath=ROOT/identity['path'];assert sha(configpath)==identity['sha256']
    cfg=read(configpath);assert sha(ROOT/cfg['implementation'])==identity['implementation_sha256']==cfg['implementation_sha256']
    targetpath=ROOT/cfg['target'];assert sha(targetpath)==cfg['target_sha256']
    source=csvrows(targetpath);selected=[r for r in source if cfg['window_m'][0]<=float(r['displacement_m'])<=cfg['window_m'][1]]
    assert len(source)==339 and len(selected)==241 and cfg['force_reference_n']==1428.9 and cfg['version']=='run017-exploratory-fd-v1'
    u=np.array([float(r['displacement_m']) for r in selected]);f=np.array([float(r['force_n']) for r in selected])
    target=Target(Curve(tuple(u),tuple(f),'m','N'),tuple([1.]*len(u)),cfg['force_reference_n'],cfg['version'])
    rows=csvrows(fdpath)
    # Explicit supported schemas, never positional column guesses.
    if {'displacement_m','force_n'}<=rows[0].keys(): uk,fk='displacement_m','force_n'
    elif {'displacement_model_length','force_model_force'}<=rows[0].keys():uk,fk='displacement_model_length','force_model_force'
    else: raise ValueError('Unreviewed CSV columns: '+str(rows[0].keys()))
    curve=Curve(tuple(float(r[uk]) for r in rows),tuple(float(r[fk]) for r in rows),'m','N')
    evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True,measurement_aligned=False,conditions_matched=False,numerical_quality_accepted=False)
    score=evaluate(target,curve,fe_status='COMPLETED_WITH_WARNINGS',evidence=evidence,mode='PROVISIONAL')
    pred=np.array(interpolate(curve,u));rmse=float(np.sqrt(np.mean((pred-f)**2)));assert math.isclose(score['loss'],(rmse/cfg['force_reference_n'])**2,rel_tol=1e-13)
    score.update(rmse_n=rmse,nrmse=rmse/cfg['force_reference_n'],fd_points=len(rows),displacement_range_m=[curve.displacement[0],curve.displacement[-1]],fd_sha256=sha(fdpath),contract_sha256=sha(configpath),target_sha256=sha(targetpath),implementation_sha256=sha(ROOT/cfg['implementation']),scope='FROZEN_EXPLORATORY_COMPARISON; numerical qualification reviewed separately')
    reference=read(ROOT/'run/run_017/artifacts/private/reference_loss.json');refpath=ROOT/reference['fe_source'];assert sha(refpath)==reference['fe_sha256']
    old=csvrows(refpath);oldcurve=Curve(tuple(float(r['displacement_model_length']) for r in old),tuple(float(r['force_model_force']) for r in old),'m','N')
    oldscore=evaluate(target,oldcurve,fe_status='COMPLETED_WITH_WARNINGS',evidence=evidence,mode='PROVISIONAL');assert math.isclose(oldscore['loss'],reference['loss'],rel_tol=1e-14)
    score['run014_reference_loss_recomputed']=oldscore['loss'];score['run014_same_contract']=True
    audit=read(OUT/'execution_audit.json');logs=[audit_logs(r) for r in audit['records']]
    table=[]
    for r in audit['records']:
        p=r['point'];valid=p['point_id']=='P01'
        table.append(dict(point_id=p['point_id'],job_name=p['job_name'],sigma_y_mpa=p['sigma_y_mpa'],n=p['n'],loss=score['loss'] if valid else None,rmse_n=rmse if valid else None,nrmse=score['nrmse'] if valid else None,status=r['execution'],duration_sec=r.get('duration_sec')))
    missing=[r['point_id'] for r in table if r['loss'] is None]
    sensitivity=dict(status='NOT_COMPUTABLE_MISSING_PERTURBATIONS',available_points=['P01'],missing_points=missing,Sx=None,Sy=None,J=None,norms=None,cosine=None,angle=None,singular_values=None,condition_number=None,informative_displacement_interval=None,
        reason='P02/P03 and P04/P05 pairs absent; a center curve or run014 with both parameters changed cannot identify partial derivatives',
        requested_units='N per unit normalized x/y; normalized J additionally divides by fixed F_ref; SVD RMS scaling as run017 protocol',global_uniqueness_proven=False)
    writecsv(AN/'loss_comparison.csv',list(table[0]),[list(r.values()) for r in table])
    writecsv(AN/'aligned_p01_experiment.csv',['displacement_m','experimental_force_n','p01_interpolated_force_n','residual_n'],zip(u,f,pred,pred-f))
    save(AN/'loss_results.json',dict(observed_at=now(),P01=score,rows=table,reference=oldscore,best_available_batch_point='P01',best_including_historical='P01' if score['loss']<oldscore['loss'] else 'run014'))
    save(AN/'numerical_audit.json',logs);save(AN/'sensitivity_diagnostic.json',sensitivity)
    plt.rcParams.update({'font.size':11,'figure.dpi':140})
    fig,ax=plt.subplots(figsize=(8,5));ax.plot(u*1000,f,color='black',label='SA508 SPT (frozen target)');ax.plot(np.array(curve.displacement)*1000,curve.force,label='P01, completed');ax.plot(np.array(oldcurve.displacement)*1000,oldcurve.force,'--',label='run014, historical test');ax.set(xlabel='Punch displacement (mm)',ylabel='Force (N)',title='Available results only: P02–P05 missing',xlim=(0,1.2));ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(AN/'available_fd_overlay.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));ax.bar([0],[score['loss']],color='#2563a6');ax.bar([5],[oldscore['loss']],color='#888888');ax.set_xticks(range(6),['P01','P02','P03','P04','P05','run014']);ax.set(ylabel='Frozen normalized MSE (dimensionless)',title='Exploratory loss; missing jobs have no score');
    for i in range(1,5):ax.text(i,max(score['loss'],oldscore['loss'])*.1,'Not run',ha='center',rotation=90,color='#777777')
    fig.tight_layout();fig.savefig(AN/'loss_comparison.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));ax.plot(u*1000,pred-f);ax.axhline(0,color='black',lw=.7);ax.set(xlabel='Punch displacement (mm)',ylabel='P01 − experiment (N)',title='Residual on the unchanged 241-point grid');ax.grid(alpha=.25);fig.tight_layout();fig.savefig(AN/'p01_residual.png');plt.close(fig)
    print(json.dumps(dict(P01=score,missing=missing,logs=logs),ensure_ascii=False))
if __name__=='__main__':main()
