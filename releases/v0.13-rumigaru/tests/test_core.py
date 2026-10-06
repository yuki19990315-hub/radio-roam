import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'firmware'))
from game import features, generate, initial_state, apply_event
from storage import Store
from protocol import advertise, parse


def ap(bssid, rssi=-70, channel=1):
    return (b'not-saved', bytes([bssid])*6, channel, rssi, 0, 0)


class CoreTests(unittest.TestCase):
    def test_empty(self):
        f, ids = features([])
        self.assertEqual(f['mean'], -100)
        self.assertEqual(generate(f, 1)['biome'], 'QUIET')
        self.assertEqual(ids, set())

    def test_dedup_and_change(self):
        f, ids = features([ap(1), ap(1, -50), ap(2)])
        self.assertEqual(f['count'], 2)
        self.assertEqual(f['mean'], -60)
        self.assertEqual(f['strong'], 1)
        self.assertEqual(features([ap(2), ap(3)], ids)[0]['change'], 66)

    def test_biomes_and_bounds(self):
        for n, expected in ((0, 'QUIET'), (4, 'GROVE'), (15, 'CITY')):
            f, _ = features([ap(i) for i in range(n)])
            for seed in range(100):
                e = generate(f, seed)
                self.assertEqual(e['biome'], expected)
                self.assertTrue(0 <= e['species'] < 32)
                self.assertTrue(10 <= e['power'] <= 100)
                self.assertEqual(e, generate(f, seed))
        f['change'] = 100
        self.assertEqual(generate(f, 1)['biome'], 'STORM')

    def test_save_restart_and_interrupted_write(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, 'save'))
            s = store.load()
            event = generate(features([])[0], 1)
            first = apply_event(s, event)
            store.save(first)
            second = apply_event(first, event)
            store.save(second)
            self.assertEqual(store.load(), second)
            self.assertEqual(len(second['collection']), 1)
            with open(store.prefix + '0.json', 'w') as f:
                f.write('{broken')
            self.assertEqual(store.load(), first)
            self.assertNotIn('not-saved', str(first))

    def test_ble_protocol(self):
        p = advertise(0x12345678, 31)
        self.assertLessEqual(len(p), 31)
        self.assertEqual(parse(p), (0x12345678, 31))
        for n in range(len(p)):
            self.assertIsNone(parse(p[:n]))
        self.assertIsNone(parse(advertise(1, 32)))
        self.assertIsNone(parse(b'\xff\x21'))


if __name__ == '__main__':
    unittest.main()
