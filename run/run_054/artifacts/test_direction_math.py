"""Synthetic checks of finite-contrast and residual diagnostics, no FE."""
import unittest
import numpy as np
from direction_math import alpha_vectors,cosine,span_comparison,loss_decomposition,band_masks,rms

class DirectionTests(unittest.TestCase):
 def test_linear_centered_secant(self):
  b=np.array([10.,20.,30.]);s=np.array([1.,2.,4.]);a=alpha_vectors(b-.5*s,b,b+.5*s)
  np.testing.assert_allclose(a['secant'],s);np.testing.assert_allclose(a['even'],0)
 def test_even_component_not_hidden(self):
  b=np.array([4.,8.]);s=np.array([2.,3.]);e=np.array([.2,.4]);a=alpha_vectors(b-.5*s+e,b,b+.5*s+e)
  np.testing.assert_allclose(a['secant'],s);np.testing.assert_allclose(a['even'],e)
  self.assertGreater(rms(a['forward']-a['backward']),0)
 def test_cosine_ignores_parameter_units(self):
  a=np.array([1.,2.,3.]);b=np.array([3.,1.,2.]);self.assertAlmostEqual(cosine(a,b),cosine(a*1e6,b*.001))
 def test_zero_direction_not_defined(self):self.assertIsNone(cosine([0,0],[1,2]))
 def test_span_residual_preserves_unrepresented_shape(self):
  p=span_comparison([[1,0,0],[0,1,0]],[0,0,1]);self.assertAlmostEqual(p['relative_unrepresented_norm'],1)
  self.assertAlmostEqual(p['represented_squared_norm_fraction'],0)
 def test_collinear_span_does_not_claim_rank_two(self):
  p=span_comparison([[1,2,3],[2,4,6]],[1,2,3]);self.assertEqual(p['rank'],1);self.assertLess(p['relative_unrepresented_norm'],1e-12)
 def test_loss_identity_including_overshoot(self):
  r=np.array([1.,2.,3.]);d=4*r;v=loss_decomposition(d,r,10.)
  self.assertGreater(v['cosine_to_needed_correction'],.99)
  self.assertGreater(v['delta_loss'],0)
  self.assertAlmostEqual(v['delta_loss'],float(np.mean(((d-r)/10)**2)-np.mean((r/10)**2)))
 def test_241_bands_are_disjoint_and_complete(self):
  ms=band_masks(np.linspace(0,.0012,241));self.assertEqual([int(sum(m)) for m in ms],[60,60,60,61]);self.assertTrue(np.all(sum(m.astype(int) for m in ms)==1))
 def test_invalid_step(self):
  with self.assertRaises(ValueError):alpha_vectors([0],[0],[1],0)

if __name__=='__main__':unittest.main(verbosity=2)
