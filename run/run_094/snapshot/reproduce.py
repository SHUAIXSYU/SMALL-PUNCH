"""Reproduce released FD/PEEQ plots and scalar checks; no Abaqus or solver calls."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load(p):
    with p.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def reproduce(root,output):
    raw=load(root/'data/fd_native.csv');fd=load(root/'data/fd_241.csv');pe=load(root/'data/peeq_saved_frames.csv')
    u=np.array([float(r['u_mm']) for r in raw]);F=np.array([float(r['force_N']) for r in raw]);g=np.array([float(r['u_mm']) for r in fd]);f=np.array([float(r['force_N']) for r in fd])
    assert len(fd)==241 and np.all(np.diff(u)>0) and u[0]<=0 and u[-1]>=1.2
    assert np.max(np.abs(np.interp(g,u,F)-f))<1e-8
    pu=np.array([float(r['u_mm']) for r in pe]);p=np.array([float(r['max_PEEQ']) for r in pe])
    output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'figure.facecolor':'white','axes.facecolor':'white','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
    fig,ax=plt.subplots(figsize=(6.5,3.7),layout='constrained');ax.plot(u,F,color='.70',lw=1.8,label='Native FE history');ax.plot(g,f,color='#0072B2',lw=1.2,label='Frozen 241-point grid');ax.set(xlabel='Punch displacement (mm)',ylabel='Punch force (N)',title='I06, nominal 1.0 mm: actual FE',xlim=(0,max(u[-1],1.2)));ax.grid(alpha=.2);ax.legend(frameon=False);fig.savefig(output/'fd.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.5,3.7),layout='constrained');ax.plot(pu,p,color='#009E73',lw=1.5,label='Max PEEQ in each saved frame');ax.axhline(.9,color='#D55E00',ls='--',lw=1.2,label='Material-table upper p = 0.9');ax.set(xlabel='Punch displacement (mm)',ylabel='Equivalent plastic strain, PEEQ',title='Saved-state material-domain check',xlim=(0,max(pu[-1],1.2)),ylim=(0,.95));ax.grid(alpha=.2);ax.legend(frameon=False);fig.savefig(output/'peeq.png');plt.close(fig)
    return {'raw_points':len(raw),'grid_points':len(fd),'end_u_mm':float(u[-1]),'max_force_N':float(F.max()),'max_saved_PEEQ':float(p.max()),'reference_F_RMS_N':float(np.sqrt(np.mean(f*f))),'native_punch_work_J':float(np.trapezoid(F,u)/1000)}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--snapshot-dir',type=Path,default=Path(__file__).resolve().parent);a.add_argument('--output-dir',type=Path);x=a.parse_args();print(json.dumps(reproduce(x.snapshot_dir,x.output_dir or x.snapshot_dir/'reproduced'),indent=2))
