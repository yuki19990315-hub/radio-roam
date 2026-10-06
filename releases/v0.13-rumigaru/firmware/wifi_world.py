"""Privacy-preserving Wi-Fi identity and environment generation."""
import hashlib
import struct

COOLDOWN_SCANS = 5
EVENT_NAMES = ('CALM','BLOOM','CACHE','SURGE','ANOMALY')


def identity_gene(row):
    ssid, bssid = bytes(row[0]), bytes(row[1])
    source = b'RR2' + struct.pack('>H', len(ssid)) + ssid + struct.pack('>H', len(bssid)) + bssid
    return hashlib.sha256(source).digest()


def hexed(raw):
    return ''.join('%02x' % value for value in raw)


def _rows(rows):
    unique = {}
    for row in rows:
        if len(row) < 4 or not -127 <= row[3] <= 0: continue
        bssid = bytes(row[1]); current = unique.get(bssid)
        if current is None or row[3] > current[3]: unique[bssid] = row
    return list(unique.values())


def snapshot(rows, previous_ids=None):
    rows = _rows(rows); previous_ids = set(previous_ids or ())
    records=[]; ssids={}; channels=set(); strong=0; hidden=0
    for row in rows:
        raw=identity_gene(row); token=hexed(raw[:8]); rssi=int(row[3]); channel=int(row[2])
        ssid=bytes(row[0]); ssids[ssid]=ssids.get(ssid,0)+1
        channels.add(channel); strong += 1 if rssi >= -60 else 0
        hidden += 1 if len(row)>5 and bool(row[5]) else 0
        records.append({'row':row,'raw':raw,'id':token,'rssi':rssi,'channel':channel})
    current_ids=set(record['id'] for record in records); union=current_ids|previous_ids
    change=(100*len(current_ids^previous_ids)//len(union)) if union and previous_ids else 0
    count=len(records); mean=sum(record['rssi'] for record in records)//count if count else -100
    clusters=sum(1 for amount in ssids.values() if amount>=2)
    for record in records:
        record['colony']=ssids.get(bytes(record['row'][0]),0)>=2
    payload=bytearray(b'RR-ENV2')
    for record in sorted(records,key=lambda item:item['id']):
        payload.extend(record['raw'][:8])
        payload.extend((max(0,min(100,record['rssi']+100))//10,record['channel']&255))
    seed=hashlib.sha256(payload).digest()
    features={'count':count,'mean':mean,'strong':strong,'channels':len(channels),
              'change':change,'clusters':clusters,'hidden':hidden}
    if count==0: biome=0
    elif change>=60 and count>=2: biome=8
    elif count>=18 or strong>=8: biome=7
    elif hidden>=2: biome=5
    elif count<=2: biome=(0,2,4)[seed[0]%3]
    elif mean>=-55: biome=1
    else: biome=seed[0]%7
    features['biome']=biome
    return features,current_ids,seed,sorted(records,key=lambda item:item['rssi'],reverse=True)


def event_reward(environment_seed, monster_gene, scan_serial, colony=False):
    serial=struct.pack('>I',scan_serial&0xffffffff)
    raw=hashlib.sha256(b'RR-EVENT2'+environment_seed+monster_gene+serial).digest()
    roll=raw[0]
    none_limit=115 if colony else 128
    xp_limit=166 if colony else 179
    item_limit=217 if colony else 230
    if roll < none_limit: return {'kind':'none'}
    if roll < xp_limit: return {'kind':'experience','amount':10+raw[1]*31//256}
    if roll < item_limit:
        return {'kind':'item','item':raw[1]%4,'amount':1+raw[2]*4//256}
    return {'kind':'dungeon','seed':hexed(raw),'theme':raw[1]>>4,
            'layout':raw[1]&15,'reward':raw[2]%4,
            'difficulty':max(2 if colony else 1,1+raw[3]*3//256)}


def habitat_for(monster_gene):
    """Return the permanent region attached to one privacy-safe AP genome."""
    raw=hashlib.sha256(b'RR-HABITAT3'+monster_gene).digest()
    dungeon=hashlib.sha256(b'RR-HABITAT-DUNGEON3'+monster_gene).digest()
    return {'id':hexed(raw[:8]),'biome':raw[8]%8,'theme':raw[9]>>4,
            'layout':raw[9]&15,'reward':raw[10]%4,
            'difficulty':1+raw[11]*3//256,'dungeon_seed':hexed(dungeon)}


def environment_event(features,environment_seed,scan_serial):
    """Turn volatile radio conditions into one scan-wide gameplay event."""
    serial=struct.pack('>I',scan_serial&0xffffffff)
    raw=hashlib.sha256(b'RR-WORLD-EVENT3'+environment_seed+serial).digest()
    if features.get('change',0)>=60: code=3
    elif features.get('hidden',0)>=2: code=4
    elif features.get('clusters',0)>=2: code=1
    elif features.get('count',0)>=18: code=2
    else: code=raw[0]%5
    intensity=1+raw[1]*3//256
    return {'code':code,'intensity':intensity,'token':hexed(raw[:4])}
