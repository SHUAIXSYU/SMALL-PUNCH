import unittest
import numpy as np
from validation_metrics import score,ValidationUnavailable

class ValidationTests(unittest.TestCase):
 def setUp(self):self.g=np.linspace(.002,.1,981);self.x=np.array([0.,.1]);self.y=np.array([100e6,200e6])
 def call(self,p=None,**kwargs):
  args=dict(uniform_limit_true=.1,definitions_confirmed=True,material_state_matched=True,pre_necking_confirmed=True)
  args.update(kwargs);return score(self.x,self.y if p is None else p,self.x,self.y,self.g,**args)
 def test_identical(self):self.assertEqual(self.call()['rmse_mpa'],0)
 def test_constant_error(self):
  r=self.call(self.y+10e6);self.assertAlmostEqual(r['rmse_mpa'],10);self.assertAlmostEqual(r['normalized_mse'],.0004)
 def test_incomplete_necking(self):
  with self.assertRaises(ValidationUnavailable):self.call(uniform_limit_true=.08)
 def test_no_extrapolation(self):
  with self.assertRaises(ValidationUnavailable):score([.01,.1],self.y,self.x,self.y,self.g,uniform_limit_true=.1,definitions_confirmed=True,material_state_matched=True,pre_necking_confirmed=True)
 def test_unknown_material(self):
  with self.assertRaises(ValidationUnavailable):self.call(material_state_matched=False)
 def test_illegal_definition(self):
  with self.assertRaises(ValidationUnavailable):self.call(strain_definition='engineering')
 def test_illegal_units(self):
  with self.assertRaises(ValidationUnavailable):self.call(stress_unit='MPa')
 def test_nan(self):
  with self.assertRaises(ValidationUnavailable):self.call([float('nan'),1])
 def test_nonmonotonic(self):
  with self.assertRaises(ValidationUnavailable):score([.1,0],self.y,self.x,self.y,self.g,uniform_limit_true=.1,definitions_confirmed=True,material_state_matched=True,pre_necking_confirmed=True)
 def test_different_density(self):
  r=score(np.linspace(0,.1,101),np.linspace(100e6,200e6,101),self.x,self.y,self.g,uniform_limit_true=.1,definitions_confirmed=True,material_state_matched=True,pre_necking_confirmed=True);self.assertLess(r['rmse_mpa'],1e-12)
 def test_relative_floor(self):
  r=score(self.x,[1e6,1e6],self.x,[0,0],self.g,uniform_limit_true=.1,definitions_confirmed=True,material_state_matched=True,pre_necking_confirmed=True);self.assertAlmostEqual(r['max_regularized_relative_error'],.02)
if __name__=='__main__':unittest.main(verbosity=2)
