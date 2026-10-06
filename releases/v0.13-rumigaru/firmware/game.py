"""Portable game rules. No machine, network, or file dependencies."""
BIOMES = ('QUIET', 'GROVE', 'CITY', 'STORM')


def features(rows, previous=None):
    # WLAN rows: ssid, bssid, channel, rssi, security, hidden.
    aps = {}
    for row in rows:
        if len(row) >= 4 and -127 <= row[3] <= 0:
            key = bytes(row[1])
            if key not in aps or row[3] > aps[key][1]:
                aps[key] = (row[2], row[3])
    values = list(aps.values())
    count = len(values)
    result = {'count': count,
              'mean': sum(v[1] for v in values) // count if count else -100,
              'strong': sum(1 for v in values if v[1] >= -60),
              'channels': len(set(v[0] for v in values)), 'change': 0}
    if previous is not None:
        union = set(aps) | previous
        result['change'] = (100 * len(set(aps) ^ previous) // len(union)) if union else 0
    return result, set(aps)


def generate(f, seed):
    biome = 0 if f['count'] < 4 else (1 if f['count'] < 15 else 2)
    if f['count'] >= 4 and f['change'] >= 60:
        biome = 3
    # Explicit 32-bit mixing, reproducible on CPython and MicroPython.
    x = (seed ^ (f['count'] << 16) ^ ((f['mean'] + 127) << 8)
         ^ f['strong'] ^ (f['channels'] << 4)) & 0xffffffff
    x = (1664525 * x + 1013904223) & 0xffffffff
    return {'species': biome * 8 + x % 8, 'biome': BIOMES[biome],
            'power': 10 + (x >> 8) % 91,
            'kind': 'RARE' if x % 20 == 0 else 'FOUND'}


def initial_state():
    return {'version': 1, 'seq': 0, 'total': 0, 'collection': [], 'last': None}


def valid_state(s):
    if not isinstance(s, dict) or s.get('version') != 1:
        return False
    for k in ('seq', 'total'):
        if type(s.get(k)) is not int or s[k] < 0:
            return False
    c = s.get('collection')
    if not isinstance(c, list) or len(c) > 32 or any(type(i) is not int or not 0 <= i < 32 for i in c):
        return False
    e = s.get('last')
    return e is None or (isinstance(e, dict) and type(e.get('species')) is int
        and 0 <= e['species'] < 32 and e.get('biome') in BIOMES
        and type(e.get('power')) is int and 10 <= e['power'] <= 100
        and e.get('kind') in ('RARE', 'FOUND'))


def apply_event(state, event):
    result = dict(state)
    result['collection'] = list(state['collection'])
    if event['species'] not in result['collection']:
        result['collection'].append(event['species'])
    result['last'] = event
    result['total'] += 1
    result['seq'] += 1
    return result
