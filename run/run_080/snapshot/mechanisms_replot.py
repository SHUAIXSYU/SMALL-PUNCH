"""Reproduce FE-only mechanism figures from aggregate CSVs; no ODB/source access.
Usage: python mechanisms_replot.py --input FOLDER --output FOLDER
"""
from pathlib import Path
import argparse
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=True)
 b=pd.read_csv(a.input/'PEEQ_volume_bins.csv');su=pd.read_csv(a.input/'surface_stress_proxies.csv');s=pd.read_csv(a.input/'stage_metrics.csv');c=pd.read_csv(a.input/'contact_profile_aggregate.csv');sh=pd.read_csv(a.input/'shape_pair_differences.csv');sp=pd.read_csv(a.input/'PEEQ_spatial_binned.csv')
 fig,axs=plt.subplots(2,4,figsize=(16,6),constrained_layout=True)
 for j,t in enumerate([.3,.6,.9,1.2]):
  x=sp[(sp.case=='B3_I06')&(sp.target_u_mm==t)];im=axs[0,j].scatter(x.r_center_mm,x.z_center_mm,c=x.mean_PEEQ,s=24,marker='s',vmin=0,vmax=.72,cmap='magma');axs[0,j].set(title=f'L2 I06 target u={t} mm',xlabel='Reference r (mm)',ylabel='Reference z (mm)');z=b[(b.case=='B3_I06')&(b.target_u_mm==t)];axs[1,j].bar(['0-.03','.03-.0983','.0983-.3','.3-.6','>.6'],z.reference_volume_fraction);axs[1,j].tick_params(axis='x',labelrotation=55);axs[1,j].set(ylabel='Reference volume fraction',ylim=(0,1))
 fig.colorbar(im,ax=list(axs[0]),label='Binned saved IP PEEQ');fig.suptitle('Real saved IPs: reference-volume spatial bin means and occupancy');fig.savefig(a.output/'PEEQ_binned_summary.png',dpi=180);plt.close(fig)
 fig,axs=plt.subplots(2,4,figsize=(16,6),constrained_layout=True)
 for j,t in enumerate([.3,.6,.9,1.2]):
  for i,comp in enumerate(['S11_Pa','S33_Pa']):
   z=su[(su.case=='B3_I06')&(su.target_u_mm==t)&(su.stress_component==comp)&(su.r_lower_mm<2.5)];r=(z.r_lower_mm+z.r_upper_mm)/2;ax=axs[i,j];ax.plot(r,z.lower_mean_MPa,'o-',label='Lower near-surface');ax.plot(r,z.upper_mean_MPa,'s-',label='Upper near-surface');ax.plot(r,z.through_reference_thickness_mean_MPa,'k--',label='Thickness mean');ax.axhline(0,color='.6',lw=.7);ax.set(xlabel='Reference radial bin center (mm)',ylabel=comp[:3]+' Cauchy stress (MPa)',title=f'Target u={t} mm');ax.legend(fontsize=7)
 fig.suptitle('Reference-volume stress descriptions: membrane/bending clues, not resultants');fig.savefig(a.output/'stress_surface_profiles.png',dpi=180);plt.close(fig)
 fig,axs=plt.subplots(1,4,figsize=(16,3.5),constrained_layout=True)
 for (cid,t),z in c.groupby(['case','target_u_mm']):
  ax=axs[[.3,.6,.9,1.2].index(t)];z=z.sort_values('reference_r_mm');ax.plot(z.reference_r_mm,z.CPRESS_MPa,label=cid);ax.set(xlabel='Reference r (mm)',ylabel='CPRESS (MPa)',title=f'Target u={t} mm');ax.legend(fontsize=7)
 fig.suptitle('Punch contact: actual nearest saved frames, radial order');fig.savefig(a.output/'contact_profiles.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
 for (aa,bb,k),z in sh.groupby(['case_A','case_B','kind']):ax.plot(z.target_u_mm,z.shape_A_minus_B_um,'o-',label=f'{aa} minus {bb}')
 ax.set(xlabel='Aligned target u (mm)',ylabel='Virtual shape difference (um)',title='Bottom w(r=0.5) - w(r=1.5): interpolation diagnostic');ax.legend(fontsize=6);fig.savefig(a.output/'virtual_shape_differences.png',dpi=180);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
 for cid,z in s.groupby('case'):
  style='--' if cid.startswith('B3') else '-';axs[0].plot(z.actual_u_mm,z.ALLPD_J,style+'o',label=cid);axs[1].plot(z.actual_u_mm,z.force_N,style+'o',label=cid)
 axs[0].set(xlabel='Actual saved u (mm)',ylabel='Global ALLPD (J)');axs[1].set(xlabel='Actual saved u (mm)',ylabel='Punch force (N)');axs[0].legend(fontsize=6,ncol=2);fig.savefig(a.output/'global_energy_force.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
