"""Meaningful math, deployed-table identity and failure-path tests; no FE."""
import csv,json,hashlib,math,unittest
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from highp_envelope import Envelope,ramp,ramp_derivative,plastic_block,table_fragment
R=Path(r'E:\Projects\SMALL-PUNCH');F=R/'run/run_046/artifacts/private/freeze'
PARAM=json.loads((F/'D01_parameters.json').read_text(encoding='utf-8-sig'));RAW=(R/PARAM['source_inp']).read_bytes();PREFIX,SUFFIX,ROWS,TEXTS=plastic_block(RAW)
SY=PARAM['sigma_y_mpa']*1e6;E=PARAM['E_pa'];N=PARAM['n'];SIGMA_AT_010=SY*(E*.1/SY)**N;SWITCH=.1-SIGMA_AT_010/E
LOW=Envelope(ROWS,SWITCH,sign=-1);HIGH=Envelope(ROWS,SWITCH,sign=1)
def csv_rows(path):
 with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

class EnvelopeTests(unittest.TestCase):
 def test_frozen_source_identity(self):
  self.assertEqual(hashlib.sha256(RAW).hexdigest(),PARAM['source_inp_sha256'])
  t=csv_rows(F/'D01_abaqus_yield_stress_plastic_strain.csv')
  self.assertEqual(ROWS,[(float(q['yield_stress_pa']),float(q['equivalent_plastic_strain'])) for q in t])
 def test_switch_from_prediction_not_experiment(self):
  curve=csv_rows(F/'D01_true_total_curve.csv');q=min(curve,key=lambda x:abs(float(x['true_total_strain'])-.1))
  self.assertLess(abs(SIGMA_AT_010-float(q['true_stress_pa'])),1e-6)
  self.assertAlmostEqual(SWITCH+SIGMA_AT_010/E,.1,15)
  self.assertGreater(abs(SWITCH-.09719169904460113),1e-4)
 def test_low_branch_exact_function(self):
  for p in np.linspace(0,SWITCH,2001):
   self.assertEqual(LOW.stress(p),LOW.baseline(p));self.assertEqual(HIGH.stress(p),HIGH.baseline(p))
 def test_original_low_row_text_retained(self):
  for model in [LOW,HIGH]:
   table,_=model.sample();frag=table_fragment(table,TEXTS,SWITCH)
   for _,p in ROWS:
    if p<=SWITCH:self.assertIn(TEXTS[p],frag)
 def test_only_plastic_block_replacement(self):
  table,_=LOW.sample();candidate=PREFIX+table_fragment(table,TEXTS,SWITCH)+SUFFIX
  a,b,_,_=plastic_block(candidate);self.assertEqual(a,PREFIX);self.assertEqual(b,SUFFIX)
 def test_switch_stress_and_tangent_match(self):
  for model in [LOW,HIGH]:
   self.assertEqual(model.stress(SWITCH),model.baseline(SWITCH))
   self.assertEqual(model.hardening(SWITCH),model.slopes[model.index(SWITCH)])
   h=1e-7;left=(model.stress(SWITCH)-model.stress(SWITCH-h))/h;right=(model.stress(SWITCH+h)-model.stress(SWITCH))/h
   self.assertLess(abs(right/left-1),1e-6)
 def test_quintic_join_derivatives(self):
  self.assertEqual(ramp(0),0);self.assertEqual(ramp(1),1);self.assertEqual(ramp_derivative(0),0);self.assertEqual(ramp_derivative(1),0)
  self.assertEqual(ramp_derivative(.5),1.875)
 def test_settled_rate_factors(self):
  for model in [LOW,HIGH]:
   for p in np.linspace(SWITCH+.05,.9,200):
    self.assertAlmostEqual(model.hardening(p)/model.slopes[model.index(p)],1+model.sign*.5,14)
 def test_envelope_order_and_symmetry(self):
  for p in np.linspace(SWITCH,.9,2001):
   lo,hi,base=LOW.stress(p),HIGH.stress(p),LOW.baseline(p)
   self.assertLessEqual(lo,base);self.assertGreaterEqual(hi,base);self.assertLess(abs((lo+hi)*.5-base),1e-6)
 def test_positive_tangents(self):
  for model in [LOW,HIGH]:self.assertTrue(all(model.hardening(p)>0 for p in np.linspace(0,.9,10001)))
 def test_coverage_and_table_monotonicity(self):
  for model in [LOW,HIGH]:
   table,_=model.sample();a=np.array(table);self.assertEqual(a[0,1],0);self.assertEqual(a[-1,1],.9);self.assertEqual(a[0,0],SY)
   self.assertTrue(np.all(np.diff(a[:,0])>0));self.assertTrue(np.all(np.diff(a[:,1])>0))
 def test_certified_interpolation_error(self):
  for model in [LOW,HIGH]:
   table,bounds=model.sample();a=np.array(table)
   self.assertLessEqual(max(v['relative_stress_bound'] for v in bounds),1e-5)
   for bound in bounds:
    lo,hi=bound['p0'],bound['p1']
    for p in np.linspace(lo,hi,17):
     err=abs(float(np.interp(p,a[:,1],a[:,0]))-model.stress(p))
     self.assertLessEqual(err,bound['absolute_stress_bound_pa']+2e-6)
 def test_deployed_low_branch_interpolation(self):
  for model in [LOW,HIGH]:
   table,_=model.sample();a=np.array(table);p=np.linspace(0,SWITCH,4001);baseline=np.interp(p,[r[1] for r in ROWS],[r[0] for r in ROWS]);new=np.interp(p,a[:,1],a[:,0])
   self.assertLess(float(np.max(abs(new-baseline))),1e-6)
 def test_integral_against_independent_quadrature(self):
  points=sorted(set([p for p in LOW.p if SWITCH<p<.9]+[SWITCH+.05]))
  exact,_=quad(lambda q:ramp((q-SWITCH)/.05)*LOW.slopes[LOW.index(q)],SWITCH,.9,points=points,epsabs=.001,epsrel=1e-11,limit=400)
  self.assertLess(abs(LOW.modulation_integral(.9)-exact),.001)
 def test_nonfinite_or_out_of_range_p_rejected(self):
  for p in [float('nan'),float('inf'),-.001,.9001,True,'0.1']:
   with self.assertRaises(ValueError):LOW.stress(p)
 def test_invalid_amplitude_and_width_rejected(self):
  for a,w in [(0,.05),(1,.05),(-.1,.05),(.5,0),(.5,-.01),(.5,1),(.5,float('nan'))]:
   with self.assertRaises(ValueError):Envelope(ROWS,SWITCH,amplitude=a,width=w)
 def test_invalid_base_or_sign_rejected(self):
  for rows in [[(100,0),(90,.1)],[(100,.1),(200,.2)],[(100,0),(200,0)]]:
   with self.assertRaises(ValueError):Envelope(rows,.05)
  for sign in [0,2,True]:
   with self.assertRaises(ValueError):Envelope(ROWS,SWITCH,sign=sign)
 def test_energy_partition_definition(self):
  p=R/'run/run_050/artifacts/private/odb'
  for pid in ['D01','I08']:
   v1=json.loads((p/pid/'energy_estimate.json').read_text(encoding='utf-8-sig'))['stages'][-1];v2=json.loads((p/pid/'energy_strain_stage_v2.json').read_text(encoding='utf-8-sig'))['stages'][-1]
   self.assertAlmostEqual(sum(v2['fraction_by_strain_interval'].values()),1,13)
   self.assertGreater(v1['terminal_peeq_region_attribution']['0.1']['fraction_of_reconstructed_total'],1-v2['fraction_by_strain_interval']['p_0_to_0p1'])
   self.assertLess(abs(v2['sum_intervals_j']-v2['v1_reconstructed_reference_volume_j']),1e-12)

if __name__=='__main__':unittest.main(verbosity=2)
