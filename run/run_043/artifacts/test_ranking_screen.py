import unittest
from ranking_screen import screen


class RankingTests(unittest.TestCase):
    def test_unchanged(self):
        r=screen(.001,.0011,.001,.0011)
        self.assertEqual(r['ratio_to_original_gap'],0)
        self.assertEqual(r['observed_refined_ranking'],'D01_FIRST')
    def test_reversal(self):
        r=screen(.001,.0011,.0012,.00105)
        self.assertEqual(r['screen'],'RANKING_SENSITIVE_REVIEW')
        self.assertEqual(r['observed_refined_ranking'],'I08_FIRST')
    def test_conservative_not_equivalent_to_reversal(self):
        r=screen(.001,.0011,.0012,.0013)
        self.assertEqual(r['screen'],'RANKING_SENSITIVE_REVIEW')
        self.assertEqual(r['observed_refined_ranking'],'D01_FIRST')
    def test_invalid_or_unfrozen(self):
        for args in ((.001,.0011,None,.001),(.001,.0011,float('nan'),.001),(.0011,.001,.001,.001)):
            with self.assertRaises(ValueError):screen(*args)


if __name__=='__main__':unittest.main(verbosity=2)
