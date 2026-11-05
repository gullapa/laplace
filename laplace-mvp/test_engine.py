import unittest
from engine import assess
class TestEngine(unittest.TestCase):
    def scene(self):return {'levels':[['present']*3 for _ in range(4)],'width_mm':25,'length_mm':75,'phase':0}
    def test_middle_removal_stands(self):self.assertEqual(assess(self.scene(),{'level':2,'slot':1})['verdict'],'PREDICTS_STAND')
    def test_one_side_unsupported(self):
        s=self.scene();s['levels'][1][1]='empty';self.assertEqual(assess(s,{'level':2,'slot':0})['verdict'],'PREDICTS_FALL')
    def test_unknown_can_change_outcome(self):
        s=self.scene();s['levels'][1][1]='unknown';result=assess(s,{'level':2,'slot':0});self.assertEqual(result['verdict'],'INCONCLUSIVE');self.assertEqual({x['verdict'] for x in result['alternatives']},{'PREDICTS_STAND','PREDICTS_FALL'})
    def test_too_many_unknowns_never_claims_complete_evaluation(self):
        s=self.scene();s['levels'][0]=['unknown']*3;s['levels'][1]=['unknown']*3;s['levels'][2]=['unknown']*3
        result=assess(s,{'level':4,'slot':1});self.assertEqual(result['verdict'],'INCONCLUSIVE');self.assertEqual(result['cases_checked'],0)
    def test_cannot_remove_absent(self):
        s=self.scene();s['levels'][1][1]='empty'
        with self.assertRaises(ValueError):assess(s,{'level':2,'slot':1})
if __name__=='__main__':unittest.main()
