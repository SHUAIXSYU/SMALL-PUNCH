"""Synthetic tests; no FE or real experimental values."""
import unittest
import numpy as np
from feature_core import extract,area,validate,physical_to_normalized,normalized_to_physical,NAMES
from inverse_baselines import standardize,ridge_fit,ridge_predict,inner_cache,fit_model,predict_model,support
class FeatureTests(unittest.TestCase):
 def test_linear_loads_slopes_and_work_units(self):
  u=np.array([0,.0001,.0004,.0008,.0012]);f=1e6*u;v,g,d=extract(u,f)
  self.assertAlmostEqual(v[0],150);self.assertAlmostEqual(v[7],1200);np.testing.assert_allclose(v[8:12],1000)
  self.assertAlmostEqual(v[12],.045);self.assertAlmostEqual(v[16],.72);self.assertAlmostEqual(sum(v[12:16]),v[16]);self.assertEqual(len(g),241)
 def test_piecewise_exact_insertion(self):
  u=np.array([0,.0004,.0012]);f=np.array([0,400,400]);self.assertAlmostEqual(area(u,f,0,1.2),.4)
 def test_same_polyline_different_density(self):
  a=np.array([0,.0004,.0012]);f=np.array([0,400,400]);b=np.array([0,.0002,.0004,.0006,.0012]);fb=np.interp(b,a,f)
  np.testing.assert_allclose(extract(a,f)[0],extract(b,fb)[0])
 def test_invalid_nan_nonmonotonic_partial(self):
  for u,f in [([0,.001],[0,1]),([0,.0012,.0008],[0,1,2]),([0,.0012],[0,np.nan])]:
   with self.assertRaises(ValueError):validate(u,f)
 def test_parameter_transform_roundtrip(self):
  y=np.array([[150,.02],[1000,.50],[250,.15]]);np.testing.assert_allclose(normalized_to_physical(physical_to_normalized(y)),y)
 def test_training_scaler_does_not_read_query(self):
  train=np.array([[1.,5.],[3.,5.],[5.,5.]]);z,m,s=standardize(train);np.testing.assert_allclose(m,[3,5]);self.assertEqual(s[1],1)
  model=fit_model(train,np.array([[0,0],[.5,.5],[1,1]]),'ridge',lam=.01);before=list(model['mean']);predict_model(model,[1e9,-1e9]);self.assertEqual(model['mean'],before)
 def test_inner_heldout_target_absent(self):
  X=np.arange(20.).reshape(5,4);Y=np.arange(10.).reshape(5,2);cache=inner_cache(X,Y)
  for i,(z,y,q,t) in enumerate(cache):np.testing.assert_array_equal(y,Y[np.arange(5)!=i]);np.testing.assert_array_equal(t,Y[i])
 def test_ridge_primal_dual_agreement(self):
  rng=np.random.default_rng(55);X=rng.normal(size=(8,3));Z,_,_=standardize(X);Y=rng.normal(size=(8,2));B,mu=ridge_fit(Z,Y,.01);dual=Z.T@np.linalg.solve(Z@Z.T+.08*np.eye(8),Y-Y.mean(0));np.testing.assert_allclose(B,dual,rtol=1e-10,atol=1e-10)
 def test_nn_returns_training_parameters(self):
  X=np.array([[1.,2.],[2.,5.],[3.,8.]]);Y=np.array([[0,.2],[.5,.7],[1,1]]);m=fit_model(X,Y,'nn');np.testing.assert_array_equal(predict_model(m,X[1]),Y[1:2])
 def test_constant_baseline_training_mean_only(self):
  X=np.zeros((3,2));physical=np.array([[150,.1],[200,.2],[250,.3]]);m=fit_model(X,np.zeros((3,2)),'mean',[],physical=physical);np.testing.assert_allclose(normalized_to_physical(predict_model(m,[[999,999]])),[[200,.2]])
if __name__=='__main__':unittest.main(verbosity=2)
