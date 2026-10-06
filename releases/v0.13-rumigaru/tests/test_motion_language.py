import os, sys, unittest, json
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','firmware'))
from pet_motion import leap, PHASE_MS
from pet_language import LABELS, japanese


class DisplayTests(unittest.TestCase):
    def test_leap_returns_and_stays_in_bounds(self):
        self.assertEqual(leap(PHASE_MS),(0,0))
        self.assertEqual(leap(PHASE_MS+100),(0,0))
        self.assertEqual(leap(300),(20,0))
        self.assertLess(leap(180)[1],0)
        for t in range(PHASE_MS+1):
            dx,dy=leap(t)
            for x,y in ((16+dx,34+dy),(68-dx,34+dy)):
                self.assertTrue(0<=x and x+36<=120)
                self.assertTrue(0<=y and y+36<=72)

    def test_all_display_glyphs_exist(self):
        font=json.loads((Path(__file__).resolve().parent.parent/'firmware/assets/japanese.json').read_text(encoding='utf-8'))
        samples=list(LABELS.values())+[japanese(v) for v in ('HP36/36','LV 20','FOE 20','DEX 32','HIT -24','OUCH -9','SCAN 100%','HEAL +25','EXP +8','ITEM +1')]
        for text in samples:
            self.assertTrue(set(text)<=set(font),text)
            self.assertTrue(all(not ('A'<=c<='Z') for c in text),text)
        for key in ('HIT','SCAN','HP','RUN','ZAP','BITE','CLAW','TAIL'):
            self.assertLessEqual(len(japanese(key))*8,40 if key in ('HIT','SCAN','ZAP','BITE') else 32)


if __name__=='__main__': unittest.main()
