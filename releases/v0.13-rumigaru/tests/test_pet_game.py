import json
import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'firmware'))
from pet_game import Battle, initial, valid, make_pet, gene, encounter, max_hp, gain_xp
from storage import Store


class PetTests(unittest.TestCase):
    def test_gene_identity_and_privacy(self):
        row = (b'example', b'123456', 1, -60, 0, 0)
        self.assertEqual(gene(row), gene(row[:3]+(-30,0,0)))
        self.assertNotEqual(gene(row), gene((b'example', b'abcdef', 1,-60,0,0)))
        for first in range(256):
            e = encounter(bytes([first])+bytes(31), 1)
            self.assertEqual(e['kind'], 'event' if first&128 else 'battle')
            self.assertTrue(valid({'version':2, 'seq':0, 'pet':e['enemy'], 'caught':[], 'items':0,'wins':0,'discoveries':0}))

    def test_weakening_increases_scan_and_capture(self):
        state = initial()
        b = Battle(state, make_pet('enemy',1))
        b.act('scan')
        low = b.scan
        b.reply()
        b.enemy['hp'] = 1
        b.act('scan')
        self.assertGreater(b.scan-low, low)
        b.reply()
        b.act('scan')
        self.assertEqual(b.result, 'caught')
        self.assertEqual(len(state['caught']), 1)
        self.assertEqual(state['caught'][0]['hp'], max_hp(b.enemy))
        self.assertFalse(b.act('scan'))
        self.assertEqual(len(state['caught']), 1)

    def test_turn_gate_and_kill(self):
        s = initial()
        b = Battle(s, make_pet('enemy'))
        b.act('hit')
        hp = b.enemy['hp']
        self.assertFalse(b.act('hit'))
        self.assertEqual(b.enemy['hp'], hp)
        b.reply()
        b.enemy['hp'] = 1
        b.act('hit')
        self.assertEqual(b.result, 'win')
        self.assertFalse(b.act('scan'))
        self.assertEqual(s['caught'], [])

    def test_locks_heal_loss_and_run(self):
        s = initial()
        b = Battle(s, make_pet('enemy'))
        self.assertFalse(b.act('hit', 1))
        self.assertFalse(b.act('item'))
        self.assertEqual(s['items'], 3)
        s['pet']['hp'] = 1
        b.act('item')
        self.assertEqual(s['pet']['hp'], 26)
        self.assertEqual(s['items'], 2)
        b.reply()
        b.act('run')
        self.assertEqual(b.result, 'escaped')
        b = Battle(s, make_pet('enemy'))
        b.act('scan')
        s['pet']['hp'] = 1
        b.reply()
        self.assertEqual(b.result, 'lost')

    def test_full_dex(self):
        s = initial()
        s['caught'] = [make_pet(str(i)) for i in range(32)]
        b = Battle(s, make_pet('enemy'))
        self.assertFalse(b.act('scan'))
        self.assertEqual(b.scan, 0)

    def test_level_and_save_recovery(self):
        s = initial()
        gain_xp(s['pet'], 100000)
        self.assertEqual(s['pet']['level'], 20)
        self.assertTrue(valid(s))
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d,'pet'), valid, initial)
            self.assertEqual(store.load(), initial())
            s['seq'] = 1
            store.save(s)
            self.assertEqual(store.load(), s)
            bad = dict(s, seq=2, pet={'level':99})
            with open(store.prefix+'0.json','w') as f:
                json.dump(bad,f)
            self.assertEqual(store.load(), s)


if __name__ == '__main__':
    unittest.main()
