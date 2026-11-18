"""Synthetic math plus real frozen identity tests; never invokes Abaqus."""
import sys,json,unittest,hashlib
from pathlib import Path
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');A=R/'run/run_060/artifacts';P=A/'private';sys.path[:0]=[str(R),str(A)]
from inverse.fd_loss import Curve,Target
from resolution_metrics import compare_responses,risk_band,stage_peeq
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class ResolutionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.c=read(A/'comparison_contract.json');cls.grid=tuple(cls.c['grid_m']);cls.weak=cls.c['weak_reference']['value_RMS_N'];cls.zero=Curve(cls.grid,(0.,)*241,'m','N');cls.target=Target(cls.zero,(1.,)*241,1428.9,'run017-exploratory-fd-v1')
 def test_identical_curves_zero_change(self):
  r=compare_responses(self.target,self.zero,self.zero,weak_RMS_N=self.weak)
  self.assertEqual(r['force_difference_RMSE_N'],0);self.assertEqual(r['delta_loss'],0);self.assertEqual(r['R_RMSE'],0)
  self.assertEqual(r['formal_numerical_convergence'],'NOT_ESTABLISHED_BY_A_SINGLE_REFINEMENT')
 def test_known_force_offset_and_denominator(self):
  offset=.75;new=Curve(self.grid,(offset,)*241,'m','N');r=compare_responses(self.target,self.zero,new,weak_RMS_N=self.weak)
  self.assertAlmostEqual(r['force_difference_RMSE_N'],offset);self.assertAlmostEqual(r['max_absolute_force_difference_N'],offset)
  self.assertAlmostEqual(r['max_regularized_relative_difference'],offset/71.445)
  self.assertAlmostEqual(r['refined_loss'],(offset/1428.9)**2);self.assertAlmostEqual(r['R_RMSE'],offset/self.weak)
 def test_predeclared_risk_intervals(self):
  self.assertEqual(risk_band(.1),'R_LE_0p10_SMALL_OBSERVED_CHANGE');self.assertEqual(risk_band(.25),'R_0p10_TO_0p25_NONNEGLIGIBLE');self.assertEqual(risk_band(.5),'R_0p25_TO_0p50_SUBSTANTIAL_WEAK_SIGNAL_RISK');self.assertEqual(risk_band(.50001),'R_GT_0p50_HIGH_WEAK_SIGNAL_RISK')
  for x in [-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):risk_band(x)
 def test_incomplete_window_and_failed_FE_rejected(self):
  short=Curve((0.,.001),(0.,1.),'m','N')
  with self.assertRaises(ValueError):compare_responses(self.target,self.zero,short,weak_RMS_N=self.weak)
  with self.assertRaises(ValueError):compare_responses(self.target,self.zero,self.zero,weak_RMS_N=self.weak,refined_status='FAILED')
 def test_bad_units_and_target_contract(self):
  with self.assertRaises(ValueError):Curve(self.grid,(0.,)*241,'mm','N')
  wrong=Target(self.zero,(1.,)*241,1.,'run017-exploratory-fd-v1')
  with self.assertRaises(ValueError):compare_responses(wrong,self.zero,self.zero,weak_RMS_N=self.weak)
 def test_stage_peeq_brackets_and_nearest(self):
  r=stage_peeq([0.,.0002,.0004,.0006,.0009,.0012],[0,.1,.2,.3,.45,.6])
  self.assertAlmostEqual(r[0]['interpolated_frame_max_peeq'],.15);self.assertEqual(r[1]['nearest_frame_index'],3);self.assertAlmostEqual(r[-1]['interpolated_frame_max_peeq'],.6)
  self.assertFalse(r[0]['within_predeclared_stage_offset_3um'])
  with self.assertRaises(ValueError):stage_peeq([0.,.001],[0,.1])
 def test_exact_allowlisted_input_change(self):
  p=self.c['candidate'];raw=(R/p['source_inp']).read_bytes();candidate=(R/p['inp_path']).read_bytes();audit=read(P/'input_byte_audit.json')
  restored=candidate.replace(audit['new_static_data'].encode(),audit['old_static_data'].encode(),1)
  for x in audit['comment_replacements']:restored=restored.replace(x['new'].encode(),x['old'].encode(),1)
  self.assertEqual(restored,raw);self.assertEqual(sha(R/p['inp_path']),p['inp_sha256'])
  self.assertEqual(self.c['weak_reference']['source_sha256'],sha(R/self.c['weak_reference']['source_path']))
 def test_no_queue_or_solver_and_empty_workdir(self):
  p=self.c['candidate'];self.assertFalse(any((R/p['working_dir']).iterdir()));self.assertIsNone(p['queue_id']);self.assertFalse(p['execution_authorized'])
  pre=read(P/'public_preflight_dry_run.json');self.assertEqual(pre['preflight']['status'],'PREVIEW_READY');self.assertEqual(pre['dry_run']['status'],'DRY_RUN_READY');self.assertEqual(pre['protected_before'],pre['protected_after']);self.assertFalse(pre['dry_run']['solver_started']);self.assertFalse(pre['dry_run']['queue_file_mutated'])

if __name__=='__main__':unittest.main()
