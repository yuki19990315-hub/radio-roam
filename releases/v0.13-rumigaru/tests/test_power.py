import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'firmware'))
from power_control import gesture,WakeTaps,percent

class PowerTests(unittest.TestCase):
    def test_swipe_and_taps(self):
        self.assertEqual(gesture((60,8),(62,65),400),'swipe_down')
        self.assertIsNone(gesture((60,50),(60,100),400))
        self.assertIsNone(gesture((60,8),(60,8),2000))
        self.assertEqual(gesture((60,50),(60,52),120),'tap')
    def test_double_tap_only(self):
        taps=WakeTaps(); diff=lambda a,b:a-b
        self.assertFalse(taps.tap(0,60,60,diff))
        self.assertTrue(taps.tap(200,62,61,diff))
        self.assertFalse(taps.tap(300,60,60,diff))
        self.assertFalse(taps.tap(1200,60,60,diff))
        self.assertFalse(taps.tap(1300,100,100,diff))
        self.assertTrue(taps.tap(1500,100,100,diff))
    def test_battery_bounds(self):
        self.assertIsNone(percent(0)); self.assertIsNone(percent(5000))
        self.assertEqual(percent(3200),0);self.assertEqual(percent(4200),100)
        self.assertLess(percent(3700),percent(3900))
