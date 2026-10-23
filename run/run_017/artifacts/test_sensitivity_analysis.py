"""Synthetic-only tests; never load experimental or FE files."""
import unittest
from sensitivity_analysis import analyze_five_curves


class SensitivityTests(unittest.TestCase):
    def design(self,a,b):
        center=[5.,5.,5.]
        return {'P01':center,'P02':[c-.2*x for c,x in zip(center,a)],
                'P03':[c+.2*x for c,x in zip(center,a)],
                'P04':[c-.2*y for c,y in zip(center,b)],
                'P05':[c+.2*y for c,y in zip(center,b)]}

    def test_independent_vectors(self):
        r=analyze_five_curves(self.design([1,0,0],[0,1,0]),1)
        self.assertEqual(r['numerical_rank'],2)
        self.assertAlmostEqual(r['sensitivity_cosine'],0)
        self.assertAlmostEqual(r['condition_number'],1)

    def test_collinear_vectors(self):
        r=analyze_five_curves(self.design([1,2,3],[2,4,6]),1)
        self.assertEqual(r['numerical_rank'],1)
        self.assertIsNone(r['condition_number'])
        self.assertTrue(r['weak_identifiability_flag'])

    def test_insensitive_parameter(self):
        r=analyze_five_curves(self.design([0,0,0],[1,2,3]),1)
        self.assertIsNone(r['sensitivity_cosine'])
        self.assertTrue(r['weak_identifiability_flag'])

    def test_zero_both(self):
        r=analyze_five_curves(self.design([0,0,0],[0,0,0]),1)
        self.assertEqual(r['numerical_rank'],0)

    def test_constant_force_offset_invariant(self):
        d=self.design([1,0,0],[0,1,0]);other={k:[v+100 for v in vs] for k,vs in d.items()}
        a=analyze_five_curves(d,1);b=analyze_five_curves(other,1)
        self.assertAlmostEqual(a['rms_sensitivity_x'],b['rms_sensitivity_x'])

    def test_missing_point(self):
        d=self.design([1,0,0],[0,1,0]);del d['P05']
        with self.assertRaises(ValueError):analyze_five_curves(d,1)

    def test_nan_or_wrong_grid_length(self):
        for v in ([1,float('nan'),3],[1,2]):
            d=self.design([1,0,0],[0,1,0]);d['P02']=v
            with self.assertRaises(ValueError):analyze_five_curves(d,1)

    def test_invalid_reference(self):
        for ref in (0,-1,float('nan')):
            with self.assertRaises(ValueError):analyze_five_curves(self.design([1,0,0],[0,1,0]),ref)

    def test_no_global_or_statistical_claim(self):
        r=analyze_five_curves(self.design([1,0,0],[0,1,0]),1)
        self.assertFalse(r['global_uniqueness_proven'])
        self.assertIsNone(r['statistical_confidence_interval'])


if __name__=='__main__':unittest.main(verbosity=2)
