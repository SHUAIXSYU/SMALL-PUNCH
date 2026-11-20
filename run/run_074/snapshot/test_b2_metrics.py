"""Synthetic unit fixtures only; never mixed with FE or experimental outputs."""
import unittest
import numpy as np
from b2_metrics import *
class Tests(unittest.TestCase):
 def test_alignment_no_extrapolation(self):
  np.testing.assert_allclose(aligned([0,1],[2,4],[0,.5,1]),[2,3,4])
  with self.assertRaises(ValueError):aligned([.1,1],[2,4],[0,.5,1])
  with self.assertRaises(ValueError):aligned([0,0,1],[2,2,4],[0,.5,1])
 def test_odd_even(self):
  b=np.ones(241)*10;v=np.arange(241)*.01;e=np.ones(241)*.2;z=pair(b-v+e,b+v+e,b,np.linspace(0,.0012,241),.1)
  np.testing.assert_allclose(z['odd'],v,atol=1e-14);np.testing.assert_allclose(z['even'],e,atol=1e-14);np.testing.assert_allclose(z['K'],v/.1,atol=1e-13)
 def test_segments_partition(self):self.assertEqual([i for a,b in SEGMENTS for i in range(a,b)],list(range(241)))
 def test_table_conversion(self):
  t=np.array([[200e6,0],[400e6,.1]]);s=np.array([0,200e6/210e9,.1+400e6/210e9]);np.testing.assert_allclose(target_Q(t,s),[0,200,400])
 def test_empty_singleton_sets(self):
  v=compatibility({'a':np.ones(241)*3},{'a':np.ones(981)},np.zeros(241));self.assertEqual(v[0]['set_state'],'EMPTY');self.assertEqual(v[2]['set_state'],'SINGLETON_NO_PAIRWISE_DIAMETER');self.assertIsNone(v[2]['d_Q_diameter_MPa'])
if __name__=='__main__':unittest.main()
