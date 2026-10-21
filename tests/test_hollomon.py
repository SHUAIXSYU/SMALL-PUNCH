"""Standard-library unit tests; analytic oracles, no Abaqus or private inputs."""
import math
import unittest
from inverse.hollomon import (generate_hollomon_table, stress_from_total_strain,
    stress_at_plastic_strain, suggest_plastic_coverage, SamplingError,
    YOUNGS_MODULUS_PA as E, POISSON_RATIO)


class HollomonTests(unittest.TestCase):
    def test_yield_anchor_units_and_elastic_continuity(self):
        table=generate_hollomon_table(200,.1,max_plastic_strain=.9)
        self.assertEqual(table.rows[0],(200e6,0.))
        self.assertEqual(table.youngs_modulus_pa,210e9)
        self.assertEqual(POISSON_RATIO,.3)
        ey=200e6/E
        self.assertAlmostEqual(stress_from_total_strain(ey/2,200,.1),100e6)
        self.assertAlmostEqual(stress_from_total_strain(ey,200,.1),200e6)
        self.assertLess(abs(stress_from_total_strain(ey*(1+1e-8),200,.1)-200e6),1.)
        self.assertFalse(table.physically_validated)

    def test_sqrt_hardening_closed_form_oracle(self):
        # For n=1/2, z=sqrt(r): p/ey=z*z-z, so z is a quadratic root.
        ey=350e6/E
        for p in [0,1e-12,1e-8,1e-4,.01,.1,.9,2.]:
            exact=350e6*(1+math.sqrt(1+4*p/ey))/2
            self.assertAlmostEqual(stress_at_plastic_strain(p,350,.5)/exact,1.,places=12)

    def test_reconstruction_all_generated_points(self):
        for q,n in [(200,.1),(500,.3),(800,.5),(200,.01),(200,.95)]:
            table=generate_hollomon_table(q,n,max_plastic_strain=.9)
            for s,p in table.rows:
                epsilon=p+s/E
                expected=E*(q*1e6/E)**(1-n)*epsilon**n
                self.assertAlmostEqual(s/expected,1.,places=11)
            self.assertEqual(table.rows[-1][1],.9)
            self.assertTrue(all(b[0]>a[0] and b[1]>a[1] for a,b in zip(table.rows,table.rows[1:])))

    def test_dense_interpolation_against_closed_form(self):
        table=generate_hollomon_table(350,.5,max_plastic_strain=.9,relative_tolerance=2e-4)
        ey=350e6/E
        for i in range(5001):
            p=.9*(i/5000)**3
            exact=350e6*(1+math.sqrt(1+4*p/ey))/2
            self.assertLessEqual(abs(table.interpolate(p)/exact-1),2e-4*(1+1e-9))
        self.assertLessEqual(table.max_normalized_error_bound,1.)

    def test_adaptive_near_yield_and_tighter_tolerance(self):
        loose=generate_hollomon_table(200,.1,max_plastic_strain=.9,relative_tolerance=1e-3)
        tight=generate_hollomon_table(200,.1,max_plastic_strain=.9,relative_tolerance=1e-4)
        self.assertGreater(len(tight.rows),len(loose.rows))
        self.assertLess(loose.rows[1][1],.001)
        self.assertLess(loose.rows[1][1],loose.rows[-1][1]-loose.rows[-2][1])

    def test_fixed_offset_is_not_used(self):
        epsilon=.02; sigma=210000*(200/210000)**.9*epsilon**.1
        p=epsilon-sigma/210000
        self.assertAlmostEqual(stress_at_plastic_strain(p,200,.1)/1e6,sigma,places=9)
        wrong_p=epsilon-200/210000
        self.assertGreater(stress_at_plastic_strain(wrong_p,200,.1)/1e6,sigma)

    def test_absolute_tolerance_and_point_budget(self):
        table=generate_hollomon_table(200,.1,max_plastic_strain=.9,
                                     relative_tolerance=0,absolute_tolerance_pa=10000)
        self.assertLessEqual(table.max_absolute_chord_error_pa,10000)
        with self.assertRaises(SamplingError):
            generate_hollomon_table(200,.1,max_plastic_strain=.9,max_points=2)

    def test_illegal_parameters(self):
        for q in [0,-1,float('nan'),float('inf'),True,'200',1e308]:
            with self.subTest(q=q),self.assertRaises(ValueError):
                generate_hollomon_table(q,.1,max_plastic_strain=.9)
        for n in [0,-.1,1,2,float('nan'),float('inf'),True,'0.1']:
            with self.subTest(n=n),self.assertRaises(ValueError):
                generate_hollomon_table(200,n,max_plastic_strain=.9)
        for maximum in [0,-1,float('nan'),float('inf'),True]:
            with self.subTest(maximum=maximum),self.assertRaises(ValueError):
                generate_hollomon_table(200,.1,max_plastic_strain=maximum)
        for kwargs in [dict(relative_tolerance=-1),dict(absolute_tolerance_pa=-1),
                       dict(relative_tolerance=0,absolute_tolerance_pa=0),
                       dict(max_points=True),dict(max_points=2.5),dict(max_points=1)]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                generate_hollomon_table(200,.1,max_plastic_strain=.9,**kwargs)

    def test_no_silent_extrapolation(self):
        table=generate_hollomon_table(200,.1,max_plastic_strain=.9)
        for p in [-.001,.900001,float('nan'),float('inf')]:
            with self.subTest(p=p),self.assertRaises(ValueError):table.interpolate(p)
        self.assertEqual(table.interpolate(0),200e6)
        self.assertEqual(table.interpolate(.9),table.rows[-1][0])

    def test_serialization_roundtrip_and_no_job(self):
        table=generate_hollomon_table(200,.1,max_plastic_strain=.9)
        text=table.abaqus_plastic_text()
        self.assertIn('NOT PHYSICALLY VALIDATED',text)
        self.assertEqual([line for line in text.splitlines() if line.startswith('*') and not line.startswith('**')],['*Plastic'])
        rows=tuple(tuple(float(x) for x in line.split(',')) for line in text.splitlines() if not line.startswith('*'))
        self.assertEqual(rows,table.rows)

    def test_coverage_requires_positive_observation(self):
        # Synthetic maximum, independent of any private ODB.
        self.assertAlmostEqual(suggest_plastic_coverage(.68),.9)
        self.assertGreaterEqual(suggest_plastic_coverage(.68),.68*1.25)
        for maximum in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):suggest_plastic_coverage(maximum)
        with self.assertRaises(ValueError):suggest_plastic_coverage(.68,safety_factor=1)


if __name__=='__main__':
    unittest.main()
