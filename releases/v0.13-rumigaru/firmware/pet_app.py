import time
import os
import gc
from storage import Store
from scanner import Scanner
from pet_game import initial, valid, max_hp, gain_xp, gene, encounter, Battle
from pet_screen import Screen
from pet_touch import Touch
from pet_motion import PHASE_MS


class App:
    def __init__(self):
        self.store = Store('roam_pet_v2', valid, initial)
        self.state = self.store.load()
        self.screen = Screen()
        try:
            self.touch = Touch()
            print('ROAM touch ready')
        except OSError as exc:
            self.touch = None
            print('ROAM touch unavailable', exc)
        self.scanner = Scanner()
        self.page = 'home'
        self.notice = ''
        self.battle = None
        self.phase = None
        self.phase_at = 0
        self.last_scan = time.ticks_ms()
        self.last_frame = self.last_scan
        self.sleeping = False
        self.happy = False
        self.happy_at = 0
        self.dex_index = 0
        self.seen = {}
        self.save_pending = False
        self.retry_at = 0

    def save(self):
        candidate = dict(self.state)
        candidate['seq'] += 1
        try:
            self.store.save(candidate)
            self.state['seq'] = candidate['seq']
            self.save_pending = False
            print('ROAM v2 saved', candidate['seq'])
        except OSError as exc:
            self.save_pending = True
            self.retry_at = time.ticks_ms()
            print('ROAM save retry required', exc)

    def tell(self, text):
        self.notice = text
        self.page = 'notice'

    def start_battle(self, enemy, practice=False):
        if not self.state['pet']['hp']:
            self.tell('REST FIRST')
            return
        self.battle = Battle(self.state, enemy, practice)
        self.page = 'battle'
        self.phase = None

    def explore(self):
        self.page = 'search'
        self.screen.draw(self, time.ticks_ms())
        try:
            rows = self.scanner.scan()
            print('ROAM scan AP=%d' % len(rows))
        except OSError as exc:
            self.tell('SCAN FAILED')
            print('ROAM scan failed', exc)
            self.last_scan = time.ticks_ms()
            return
        now = time.ticks_ms()
        self.last_scan = now
        self.seen = {k:v for k,v in self.seen.items() if time.ticks_diff(now,v)<300000}
        if not rows:
            self.tell('NO SIGNAL')
            return
        chosen = None
        for row in sorted(rows, key=lambda r: r[3], reverse=True):
            e = encounter(gene(row), self.state['pet']['level'])
            if e['id'] not in self.seen:
                chosen = e
                break
        if chosen is None:
            self.tell('TRY NEW AREA')
            return
        if len(self.seen) >= 64:
            self.seen.clear()
        self.seen[chosen['id']] = now
        self.state['discoveries'] += 1
        if chosen['kind'] == 'battle':
            self.start_battle(chosen['enemy'])
        elif chosen['reward'] == 'xp':
            gain_xp(self.state['pet'], 8)
            self.tell('EXP +8')
        else:
            self.state['items'] = min(99, self.state['items']+1)
            self.tell('ITEM +1')
        self.save()

    def command(self, key):
        if key is None:
            return
        if key == 'home':
            self.page = 'home'
        elif key == 'menu':
            self.page = 'menu'
        elif key == 'rest':
            self.state['pet']['hp'] = max_hp(self.state['pet'])
            self.sleeping = True
            self.page = 'home'
            self.save()
        elif key == 'pet':
            self.sleeping = False
            self.happy = True
            self.happy_at = time.ticks_ms()
        elif key == 'explore':
            self.sleeping = False
            self.explore()
        elif key == 'dex':
            self.page = 'dex'
        elif key == 'next':
            self.dex_index += 1
        elif key == 'practice':
            e = encounter(os.urandom(32), self.state['pet']['level'])
            self.start_battle(e['enemy'], True)
        elif key == 'battle':
            self.page = 'battle'
        elif key == 'moves':
            self.page = 'moves'
        elif key == 'finish':
            if self.phase is not None:
                return
            self.save()
            self.page = 'home'
            self.battle = None
        elif self.battle and (key in ('scan', 'item', 'run') or key.startswith('move')):
            move = int(key[-1]) if key.startswith('move') else 0
            action = 'hit' if key.startswith('move') else key
            if self.battle.act(action, move):
                self.page = 'battle'
                self.phase = 'attack' if action == 'hit' else ('scan' if action == 'scan' else 'item')
                self.phase_at = time.ticks_ms()

    def tick(self, now):
        if self.battle and self.phase and time.ticks_diff(now, self.phase_at) >= PHASE_MS:
            if self.battle.await_reply:
                self.battle.reply()
                self.phase = 'reply'
                self.phase_at = now
            else:
                self.phase = None
                if self.battle.result:
                    self.battle.message = {'win':'VICTORY!', 'caught':'GOT AURI!',
                                           'lost':'REST TO HEAL', 'escaped':'ESCAPED'}[self.battle.result]
                    self.save()
        if self.save_pending and time.ticks_diff(now, self.retry_at) > 10000:
            self.save()
        if self.happy and time.ticks_diff(now, self.happy_at) > 1200:
            self.happy = False
        if self.page == 'home' and not self.sleeping and time.ticks_diff(now, self.last_scan) >= 60000:
            self.explore()

    def run(self):
        self.screen.draw(self, time.ticks_ms())
        print('ROAM playable ready heap=%d' % gc.mem_free())
        while True:
            now = time.ticks_ms()
            if self.touch:
                point = self.touch.poll()
                if point:
                    self.command(self.screen.hit(*point))
            self.tick(now)
            if time.ticks_diff(now, self.last_frame) >= 60:
                self.screen.draw(self, now)
                self.last_frame = now
            time.sleep_ms(20)


def run():
    print('Radio Roam PLAYABLE v0.2 boot')
    App().run()
