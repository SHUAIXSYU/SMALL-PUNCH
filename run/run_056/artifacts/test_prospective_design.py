"""Offline design sanity tests; no generated materials, models or Jobs."""
import json,unittest,sys
from pathlib import Path
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_056/artifacts/private';sys.path.insert(0,str(R/'run/run_055/artifacts'))
from feature_core import physical_to_normalized,normalized_to_physical
class DesignTests(unittest.TestCase):
 def setUp(self):self.c=json.loads((P/'prospective_design_contract.json').read_text(encoding='utf-8'))
 def test_four_unique_points_no_files(self):
  pts=self.c['points'];self.assertEqual(len(pts),4);self.assertEqual(len({(p['sigma_y_mpa'],p['n']) for p in pts}),4)
  for p in pts:self.assertIsNone(p['INP_path']);self.assertIsNone(p['INP_sha256']);self.assertIsNone(p['job_name'])
 def test_physical_normalization_roundtrip(self):
  for p in self.c['points']:np.testing.assert_allclose(physical_to_normalized([[p['sigma_y_mpa'],p['n']]])[0],[p['x'],p['y']],atol=1e-14)
 def test_symmetric_axes_not_linear_sigma_symmetry(self):
  pts=self.c['points'];c=self.c['parameter_normalization'];self.assertEqual(c['central_secant_denominator'],.05)
  for ax in ['x','y']:
   values=sorted(p[ax] for p in pts if p['axis']==ax);self.assertAlmostEqual(sum(values)/2,c['center_'+ax]);self.assertAlmostEqual(values[1]-values[0],.05)
 def test_bounds_and_no_duplicate_existing(self):
  a=json.loads((R/'run/run_055/artifacts/private/feature_arrays.json').read_text(encoding='utf-8'));Y=physical_to_normalized([a['targets'][x] for x in a['primary_ids']])
  for p in self.c['points']:
   self.assertTrue(150<=p['sigma_y_mpa']<=1000 and .02<=p['n']<=.5);self.assertGreater(np.linalg.norm(Y-[p['x'],p['y']],axis=1).min(),1e-6)
 def test_uses_frozen_models_no_retraining(self):
  b=self.c['evaluation_B'];self.assertTrue(b['no_new_points_in_training_until_all_B_complete']);self.assertTrue(b['no_restandardization_selection_or_tuning']);self.assertTrue(self.c['frozen_models']['no_retraining'])
 def test_budget_zero_and_future_limit_four(self):
  self.assertEqual(self.c['budget']['current_authorized_new_FE'],0);self.assertEqual(self.c['budget']['future_proposed_unique_new_jobs'],4);self.assertEqual(self.c['budget']['automatic_retries'],0)
 def test_constant_center_cannot_pass_resolution_goal(self):
  g=self.c['evaluation_B']['engineering_target'];h=self.c['parameter_normalization']['h_x']
  self.assertLess(g['eachpoint_eachcoordinate_abs_normalized_error_le'],h);self.assertFalse(g['constant_I06_passes'])
  center=np.array([self.c['parameter_normalization']['center_x'],self.c['parameter_normalization']['center_y']]);truth=np.array([[p['x'],p['y']] for p in self.c['points']]);score=np.sqrt(np.mean(((truth-center)/h)**2));self.assertAlmostEqual(score,np.sqrt(.5))
if __name__=='__main__':unittest.main(verbosity=2)
