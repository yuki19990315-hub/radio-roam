"""Portable first playable rules. Original v1 saves remain untouched."""
import hashlib

MAX_COLLECTION = 32
MOVE_LEVELS = (1, 5, 10, 15)
MOVE_NAMES = ('SPARK', 'BITE', 'CLAW', 'TAIL')


def max_hp(pet):
    return 30 + pet['level'] * 6


def make_pet(identity='starter', palette=0, level=1):
    return {'id': identity, 'palette': palette, 'level': level,
            'xp': 0, 'hp': 30 + level*6, 'name': 'AURI'}


def initial():
    return {'version': 2, 'seq': 0, 'pet': make_pet(), 'caught': [],
            'items': 3, 'wins': 0, 'discoveries': 0}


def valid_pet(p):
    return (isinstance(p, dict) and isinstance(p.get('id'), str)
            and 0 < len(p['id']) <= 64 and p.get('name') == 'AURI'
            and type(p.get('palette')) is int and 0 <= p['palette'] <= 2
            and type(p.get('level')) is int and 1 <= p['level'] <= 20
            and type(p.get('xp')) is int and 0 <= p['xp'] < p['level']*12
            and type(p.get('hp')) is int and 0 <= p['hp'] <= max_hp(p))


def valid(s):
    if not isinstance(s, dict) or s.get('version') != 2 or not valid_pet(s.get('pet')):
        return False
    for k in ('seq', 'items', 'wins', 'discoveries'):
        if type(s.get(k)) is not int or not 0 <= s[k] <= 100000000:
            return False
    c = s.get('caught')
    return isinstance(c, list) and len(c) <= MAX_COLLECTION and all(valid_pet(p) for p in c)


def gain_xp(pet, amount):
    pet['xp'] += amount
    while pet['level'] < 20 and pet['xp'] >= pet['level']*12:
        pet['xp'] -= pet['level']*12
        pet['level'] += 1
        pet['hp'] = max_hp(pet)
    if pet['level'] == 20:
        pet['xp'] = min(pet['xp'], 239)


def gene(row):
    from wifi_world import identity_gene
    return identity_gene(row)


def encounter(digest, level):
    identity = ''.join('%02x' % x for x in digest[:8])
    event = bool(digest[0] & 128)
    # The visual prototype intentionally has a single dragon body, three palettes.
    return {'id': identity, 'kind': 'event' if event else 'battle',
            'reward': 'xp' if digest[6] < 128 else 'item',
            'enemy': make_pet(identity, digest[4] % 3, max(1, min(20, level + digest[7]%3 - 1)))}


class Battle:
    def __init__(self, profile, enemy, practice=False):
        self.profile = profile
        self.enemy = dict(enemy)
        self.player = profile['pet']
        self.scan = 0
        self.result = None
        self.await_reply = False
        self.practice = practice
        self.message = 'YOUR TURN'

    def act(self, command, move=0):
        if self.result or self.await_reply:
            return False
        if command == 'hit':
            if not 0 <= move < 4 or self.player['level'] < MOVE_LEVELS[move]:
                self.message = 'LOCKED'
                return False
            damage = max(2, 7 + self.player['level']*2 + move*3 - self.enemy['level'])
            self.enemy['hp'] = max(0, self.enemy['hp']-damage)
            self.message = 'HIT -%d' % damage
            if not self.enemy['hp']:
                self.result = 'win'
                self.profile['wins'] += 1
                gain_xp(self.player, 8 + self.enemy['level']*4)
        elif command == 'scan':
            if len(self.profile['caught']) >= MAX_COLLECTION:
                self.message = 'DEX FULL'
                return False
            lost = max_hp(self.enemy) - self.enemy['hp']
            self.scan = min(100, self.scan + 15 + 60*lost//max_hp(self.enemy))
            self.message = 'SCAN %d%%' % self.scan
            if self.scan == 100:
                self.result = 'caught'
                caught = dict(self.enemy)
                caught['hp'] = max_hp(caught)
                self.profile['caught'].append(caught)
                gain_xp(self.player, 6)
        elif command == 'item':
            if self.profile['items'] == 0:
                self.message = 'NO ITEMS'
                return False
            if self.player['hp'] == max_hp(self.player):
                self.message = 'HP FULL'
                return False
            self.profile['items'] -= 1
            self.player['hp'] = min(max_hp(self.player), self.player['hp']+25)
            self.message = 'HEAL +25'
        elif command == 'run':
            self.result = 'escaped'
            self.message = 'ESCAPED'
        else:
            return False
        self.await_reply = self.result is None
        return True

    def reply(self):
        if not self.await_reply or self.result:
            return
        damage = max(2, 4 + self.enemy['level'] - self.player['level']//2)
        self.player['hp'] = max(0, self.player['hp']-damage)
        self.message = 'OUCH -%d' % damage
        self.await_reply = False
        if not self.player['hp']:
            self.result = 'lost'
