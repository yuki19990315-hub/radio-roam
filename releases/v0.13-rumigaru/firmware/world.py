"""Portable v6 world: modular genetics, Wi-Fi ecology and progression."""
import json
import hashlib
from pet_game import make_pet, Battle as BaseBattle
from gene_schema import (GENE_SCHEMA_VERSION, decode as decode_gene,
                         encode_v2, supported as supported_gene)
from versions import SAVE_SCHEMA_VERSION, PUBLIC_CATALOG_VERSION
from part_catalog import (TYPE_BASE_STATS, TYPE_STRONG_AGAINST, PALETTE_NAMES,
                          part_stat_bonus)
import wifi_world

TYPES = ('ケモノ', 'トリ', 'リュウ', 'サカナ', 'ヒト', 'ショクブツ')
TYPE_SHORT = ('ケモ','トリ','リュ','サカ','ヒト','ショク')
SUBTYPES = (('イヌ','ネコ','ウサギ','ヨロイジュウ'),
            ('ヒナ','タカ','フクロウ','カラス'),
            ('ヨウリュウ','スイリュウ','ヒリュウ','コウリュウ'),
            ('ハリセン','アンコウ','サメ','カイリュウ'),
            ('ゴーレム','コアクマ','ロボ','キシ'),
            ('マンドラ','キノコ','サボテン','ロウボク'))
SPECIES_NAMES = (('コロファン','ミケル','ラピット','ガルドン'),
                 ('ピヨル','ファルノ','ホロウル','クロバネ'),
                 ('ドラル','ミズリュ','フレイガ','ガンリュ'),
                 ('プクロン','ルミアン','シャルク','ウズリオ'),
                 ('ゴロム','リルガ','ギアト','アルディ'),
                 ('ネムリフ','ポコノコ','トゲル','モリジイ'))
BIOMES = ('ソウゲン', 'ジャングル', 'スナハマ', 'ウミ', 'サバク', 'ドウクツ',
          'マグマ', 'マチ', 'デンパアラシ')
PARTS = ('head','body','arms','legs','horns','tail','eyes','wings')
ITEMS = ('food','potion','scanner','incubator')
MOVE_TABLE = (
    ('トツゲキ','ツツク','ブレス','ミズダマ','ケンゲキ','ツルムチ'),
    ('カミツキ','ズツキ','オンパ','ニラミ'),
    ('ツメ','パンチ','ツバサ','ヒレ'),
    ('シッポ','ドクバリ','ナギハラ','ガード'))
BODY_MOVES = ('タイアタリ','カタメル','トゲガード','チャージ')
STARTER_ROLE_BONUS = {'スピード':(0,1,0,0,2), 'パワー':(2,2,0,0,0),
                      'サポート':(1,0,1,2,0)}
DUNGEON_THEMES = ('ハナ','キノコ','ツタ','コケ','コオリ','カゼ','ホノオ','スナ',
                  'ホシ','キカイ','ホネ','スイショウ','ドク','カミナリ','ヤミ','ニジ')
DUNGEON_LAYOUTS = ('イッポン','エダワカレ','ワッカ','メイロ','ヒロバ','カイダン','アナ','ハシ',
                   'シマ','タワー','スイロ','ネッコ','ハチノス','カイロウ','ワープ','ランダム')
DUNGEON_REWARDS = ('フカソウチ','カイフク','ゴハン','スキャナ')
WORLD_EVENTS = ('セイジャク','カイカ','タカラバ','デンパゲキリュウ','ノイズヘンイ')
EVOLUTION_ROUTES = ('セントウ','タンサク','キズナ','イヘン')
CAPACITY = 33
FUSION_LEVEL = 20
EVOLUTION_LEVEL = 20
MAX_EVOLUTION = 2
EVOLUTION_NAMES = ('ヨウタイ', 'チュウカン', 'セイタイ')
HATCH_SECONDS = 180
PART_DEX_HEX_LENGTH = 576


def clone(value):
    return json.loads(json.dumps(value))


def digest_for(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).digest()


def hexed(raw):
    return ''.join('%02x'%b for b in raw)


def _part_totals(p):
    totals=[0,0,0,0,0]
    present=p.get('present',[True,True,True,True,True,True,True,True])
    for index,(name,value) in enumerate(zip(PARTS,p['parts'])):
        bonus=part_stat_bonus(name,value,present[index])
        for i in range(5): totals[i]+=bonus[i]
    return totals


def max_hp(p):
    base=TYPE_BASE_STATS[p.get('type',0)][0]
    part_hp=_part_totals(p)[0] if 'parts' in p else 0
    return max(20,base+p['level']*5+p.get('evolution',0)*10+p.get('mastery',0)*2+part_hp)


def gain_xp(p,amount):
    p['xp']+=max(0,int(amount))
    while p['level']<20 and p['xp']>=p['level']*12:
        p['xp']-=p['level']*12; p['level']+=1; p['hp']=max_hp(p)
    if p['level']==20: p['xp']=min(p['xp'],239)


def _upgrade_pet(p):
    version=p.get('gene_version',1)
    if 'present' not in p:
        values=p.get('parts',[0]*8)
        p['present']=[True,True,True,True,values[4]!=0,values[5]!=0,True,values[7]!=0]
    p['mastery']=p.get('mastery',p.get('evolution',0))
    traits=p.get('traits') or {'personality':0,'temperament':0,'rare':0}
    traits['combat']=traits.get('combat',traits.get('rare',0)&15); p['traits']=traits
    p['growth']=p.get('growth',{'battle':0,'explore':0,'care':0,'anomaly':0})
    for key in ('battle','explore','care','anomaly'): p['growth'][key]=p['growth'].get(key,0)
    p['evolution_paths']=p.get('evolution_paths',[])
    p['memories']=p.get('memories',{'birthplace':'','habitats':0,'bosses':0})
    for key,value in (('birthplace',''),('habitats',0),('bosses',0)):
        p['memories'][key]=p['memories'].get(key,value)
    if version==1: p['palette']=min(15,p.get('palette',0))
    p['hp']=min(p.get('hp',max_hp(p)),max_hp(p))
    return p


def make_creature(raw, level=1, uid='', legacy=False, version=GENE_SCHEMA_VERSION):
    decoded=decode_gene(raw,version)
    p=make_pet(hexed(raw[:8]), decoded['palette'], max(1,min(20,level)))
    p.update({'uid':uid, 'genome':hexed(raw), 'gene_version':decoded['schema_version'],
              'type':decoded['type'], 'parts':decoded['parts'], 'present':decoded['present'],
              'traits':{'personality':decoded['personality'],
                        'temperament':decoded['temperament'],
                        'rare':decoded['rare_trait'],
                        'combat':decoded.get('combat_trait',0)},
              'generation':1,'parents':[], 'fullness':80,'mood':80,'energy':80,
              'evolution':0, 'mastery':0, 'legacy':legacy,
              'last_play':-60, 'last_train':-60,
              'growth':{'battle':0,'explore':0,'care':0,'anomaly':0},
              'evolution_paths':[],
              'memories':{'birthplace':'','habitats':0,'bosses':0}})
    p['hp']=max_hp(p)
    return p


def starter_choices():
    """Three modular starters with distinct early-game roles."""
    specs=(('コロ',0,(1,2,0,3,1,2,0,3),0,(0,1,0),'スピード',12),
           ('ヒリュ',2,(9,10,8,11,9,10,8,11),1,(1,1,1),'パワー',0),
           ('メブ',5,(5,6,4,7,5,6,4,7),2,(1,0,0),'サポート',8))
    choices=[]
    for label,kind,parts,palette,optional,role,combat in specs:
        seed=digest_for('RR5-STARTER-'+label)
        present=[True,True,True,True,bool(optional[0]),bool(optional[1]),True,bool(optional[2])]
        raw=encode_v2(seed,kind,parts,palette,present,personality=kind+2,
                      temperament=4+kind,rare_trait=seed[7],combat_trait=combat)
        p=make_creature(raw)
        p['uid']='starter-%d'%len(choices)
        p['starter_name']=label; p['starter_role']=role
        choices.append(p)
    return choices


def assign_uid(state, pet):
    state['serial']+=1
    pet['uid']='p%08x'%state['serial']
    return pet


def record(state,p):
    # Permanent discovered forms survive parent consumption; bounded journal.
    if not any(x['genome']==p['genome'] and x.get('evolution',0)==p['evolution']
               for x in state['dex']):
        state['dex'].append(clone(p))
        state['dex']=state['dex'][-256:]
    mark_part_dex(state,p)


def _part_dex_index(p,slot):
    return (((p['type']*3+p.get('evolution',0))*8+slot)*16+p['parts'][slot])


def mark_part_dex(state,p):
    """Record discovered parts as a compact 2304-bit hexadecimal catalog."""
    value=state.get('part_dex','0'*PART_DEX_HEX_LENGTH)
    if len(value)!=PART_DEX_HEX_LENGTH: value='0'*PART_DEX_HEX_LENGTH
    chars=list(value)
    for slot in range(8):
        index=_part_dex_index(p,slot); nibble=index//4; bit=index%4
        chars[nibble]='%x'%(int(chars[nibble],16)|(1<<bit))
    state['part_dex']=''.join(chars)


def part_dex_count(state):
    return sum(bin(int(char,16)).count('1') for char in state.get('part_dex',''))


def part_dex_type_count(state,kind):
    start=kind*96; text=state.get('part_dex','')[start:start+96]
    return sum(bin(int(char,16)).count('1') for char in text)


def migrate(old):
    s={'version':SAVE_SCHEMA_VERSION,'seq':0,'serial':0,'pet':None,'caught':[], 'eggs':[], 'dex':[],
       'starter_options':[],
       'family':[], 'inventory':{'food':10,'potion':old.get('items',3),'scanner':2,'incubator':1},
       'items':old.get('items',3), 'wins':old.get('wins',0),'discoveries':old.get('discoveries',0),
       'elapsed':0,'care_remainder':0,'sleeping':False,'biome':0,'dungeons':[],
       'peers':0,'ble':True,'scan_serial':0,'signal_history':[],'last_scan_ids':[],
       'environment':empty_environment(),'world_event':empty_world_event(),
       'habitats':[],'part_dex':'0'*PART_DEX_HEX_LENGTH}
    for i,original in enumerate([old['pet']]+old.get('caught',[])):
        p=make_creature(digest_for(original['id']),original['level'],legacy=True)
        for k in ('id','name','level','xp','hp','palette'): p[k]=original[k]
        p['type']=2
        assign_uid(s,p)
        if i==0: s['pet']=p
        else: s['caught'].append(p)
        record(s,p)
    return s


def migrate_v3(old):
    """Keep every v3 monster/save value and add v5 fields."""
    s=clone(old)
    s['version']=SAVE_SCHEMA_VERSION
    s['starter_options']=[]
    pets=([s['pet']] if s.get('pet') else [])+s.get('caught',[])+s.get('dex',[])
    pets += [e['child'] for e in s.get('eggs',[]) if isinstance(e,dict) and 'child' in e]
    for p in pets:
        p['evolution']=p.get('evolution',0); _upgrade_pet(p)
    s['scan_serial']=0; s['signal_history']=[]; s['last_scan_ids']=[]
    s['environment']=empty_environment(); _upgrade_state_v6(s)
    return s


def migrate_v4(old):
    s=clone(old); s['version']=SAVE_SCHEMA_VERSION
    pets=([s['pet']] if s.get('pet') else [])+s.get('caught',[])+s.get('dex',[])
    pets += [e['child'] for e in s.get('eggs',[]) if isinstance(e,dict) and 'child' in e]
    for p in pets: _upgrade_pet(p)
    s['scan_serial']=s.get('scan_serial',0); s['signal_history']=s.get('signal_history',[])
    s['last_scan_ids']=s.get('last_scan_ids',[]); s['environment']=s.get('environment',empty_environment())
    _upgrade_state_v6(s)
    return s


def migrate_v5(old):
    """Preserve v5 progress and add v6 ecology/progression indexes."""
    s=clone(old); s['version']=SAVE_SCHEMA_VERSION
    _upgrade_state_v6(s)
    return s


def _upgrade_state_v6(s):
    s['world_event']=s.get('world_event',empty_world_event())
    s['habitats']=s.get('habitats',[])
    s['part_dex']=s.get('part_dex','0'*PART_DEX_HEX_LENGTH)
    pets=([s['pet']] if s.get('pet') else [])+s.get('caught',[])+s.get('dex',[])
    pets += [e['child'] for e in s.get('eggs',[]) if isinstance(e,dict) and 'child' in e]
    pets += s.get('starter_options',[])
    for p in pets: _upgrade_pet(p)
    # Rebuild the compact catalog from all forms retained by the old save.
    s['part_dex']='0'*PART_DEX_HEX_LENGTH
    for p in pets: mark_part_dex(s,p)


def empty_environment():
    return {'count':0,'mean':-100,'strong':0,'channels':0,'change':0,
            'clusters':0,'hidden':0,'biome':0}


def empty_world_event():
    return {'code':0,'intensity':1,'token':'00000000'}


def initial():
    return {'version':SAVE_SCHEMA_VERSION,'seq':0,'serial':0,'pet':None,'caught':[], 'eggs':[], 'dex':[],
            'starter_options':starter_choices(), 'family':[],
            'inventory':{'food':10,'potion':3,'scanner':2,'incubator':1},
            'items':3,'wins':0,'discoveries':0,'elapsed':0,'care_remainder':0,
            'sleeping':False,'biome':0,'dungeons':[], 'peers':0,'ble':True,
            'scan_serial':0,'signal_history':[],'last_scan_ids':[],
            'environment':empty_environment(),'world_event':empty_world_event(),
            'habitats':[],'part_dex':'0'*PART_DEX_HEX_LENGTH}


def roster(s):
    return ([s['pet']] if s['pet'] else [])+s['caught']


def occupied(s):
    return len(roster(s))+len(s['eggs'])


def get_pet(s,uid):
    return next((p for p in roster(s) if p['uid']==uid),None)


def choose_starter(s,index):
    if s['pet'] or s['caught'] or len(s['starter_options'])!=3:
        raise ValueError('もうえらんでいる')
    if not 0<=index<3: raise ValueError('3たいからえらぶ')
    chosen=clone(s['starter_options'][index])
    s['serial']+=1
    chosen['uid']='p%08x'%s['serial']
    s['pet']=chosen
    s['starter_options']=[]
    record(s,chosen)
    return chosen


def valid_pet(p):
    return (isinstance(p,dict) and isinstance(p.get('id'),str) and 0<len(p['id'])<=64
            and p.get('name')=='AURI' and isinstance(p.get('uid'),str) and bool(p['uid'])
            and valid_nickname(p.get('nickname',''))
            and isinstance(p.get('genome'),str) and len(p['genome'])==64
            and all(c in '0123456789abcdef' for c in p['genome'])
            and type(p.get('type')) is int and 0<=p['type']<len(TYPES)
            and type(p.get('palette')) is int and 0<=p['palette']<len(PALETTE_NAMES)
            and type(p.get('level')) is int and 1<=p['level']<=20
            and type(p.get('xp')) is int and 0<=p['xp']<p['level']*12
            and type(p.get('hp')) is int and 0<=p['hp']<=max_hp(p)
            and isinstance(p.get('parts'),list) and len(p['parts'])==8
            and all(type(x) is int and 0<=x<16 for x in p['parts'])
            and isinstance(p.get('present'),list) and len(p['present'])==8
            and all(isinstance(x,bool) for x in p['present'])
            and all(p['present'][i] for i in (0,1,2,3,6))
            and all(type(p.get(k)) is int and 0<=p[k]<=100 for k in ('fullness','mood','energy'))
            and type(p.get('evolution')) is int and 0<=p['evolution']<=MAX_EVOLUTION
            and type(p.get('mastery')) is int and 0<=p['mastery']<=MAX_EVOLUTION
            and type(p.get('generation')) is int and 1<=p['generation']<=1000000
            and isinstance(p.get('parents'),list) and len(p['parents'])<=2
            and all(isinstance(x,str) for x in p['parents'])
            and type(p.get('gene_version',1)) is int and supported_gene(p.get('gene_version',1))
            and (p.get('traits') is None or (isinstance(p['traits'],dict)
                and all(type(p['traits'].get(k)) is int for k in ('personality','temperament','rare','combat'))
                and 0<=p['traits']['personality']<16 and 0<=p['traits']['temperament']<16
                and 0<=p['traits']['rare']<256 and 0<=p['traits']['combat']<16))
            and type(p.get('last_play')) is int and type(p.get('last_train')) is int
            and isinstance(p.get('growth'),dict)
            and all(type(p['growth'].get(k)) is int and 0<=p['growth'][k]<=1000000
                    for k in ('battle','explore','care','anomaly'))
            and isinstance(p.get('evolution_paths'),list) and len(p['evolution_paths'])<=2
            and all(type(x) is int and 0<=x<4 for x in p['evolution_paths'])
            and isinstance(p.get('memories'),dict)
            and isinstance(p['memories'].get('birthplace'),str) and len(p['memories']['birthplace'])<=16
            and all(type(p['memories'].get(k)) is int and 0<=p['memories'][k]<=1000000
                    for k in ('habitats','bosses'))
            and isinstance(p.get('legacy'),bool))


def valid(s):
    try:
        if s['version']!=SAVE_SCHEMA_VERSION or not all(type(s[k]) is int and s[k]>=0 for k in
               ('seq','serial','wins','discoveries','elapsed','care_remainder','peers','items','scan_serial')): return False
        if not isinstance(s['caught'],list) or not isinstance(s['eggs'],list): return False
        if occupied(s)>CAPACITY or len(s['eggs'])>3: return False
        if not all(valid_pet(p) for p in roster(s)): return False
        starters=s['starter_options']
        if not isinstance(starters,list) or len(starters) not in (0,3): return False
        if not all(valid_pet(p) for p in starters): return False
        if starters and (s['pet'] or s['caught'] or s['eggs'] or s['dex'] or s['family']): return False
        ids=[p['uid'] for p in roster(s)]+[p['uid'] for p in starters]
        for e in s['eggs']:
            if not valid_pet(e['child']) or type(e['remaining']) is not int or not 0<=e['remaining']<=HATCH_SECONDS: return False
            ids.append(e['child']['uid'])
        if len(set(ids))!=len(ids): return False
        if not all(type(s['inventory'][k]) is int and 0<=s['inventory'][k]<=99 for k in ITEMS): return False
        if not 0<=s['biome']<len(BIOMES) or not isinstance(s['sleeping'],bool) or not isinstance(s['ble'],bool): return False
        if not isinstance(s['last_scan_ids'],list) or len(s['last_scan_ids'])>64: return False
        if not all(isinstance(x,str) and len(x)==16 for x in s['last_scan_ids']): return False
        if not isinstance(s['signal_history'],list) or len(s['signal_history'])>64: return False
        if not all(isinstance(x,list) and len(x)==2 and isinstance(x[0],str) and len(x[0])==16
                   and type(x[1]) is int and 0<=x[1]<=s['scan_serial'] for x in s['signal_history']): return False
        environment=s['environment']
        if not isinstance(environment,dict) or not all(type(environment.get(k)) is int for k in
               ('count','mean','strong','channels','change','clusters','hidden','biome')): return False
        if not 0<=environment['biome']<len(BIOMES): return False
        event=s['world_event']
        if (not isinstance(event,dict) or type(event.get('code')) is not int or not 0<=event['code']<len(WORLD_EVENTS)
                or type(event.get('intensity')) is not int or not 1<=event['intensity']<=3
                or not isinstance(event.get('token'),str) or len(event['token'])!=8): return False
        if (not isinstance(s['part_dex'],str) or len(s['part_dex'])!=PART_DEX_HEX_LENGTH
                or any(char not in '0123456789abcdef' for char in s['part_dex'])): return False
        if not isinstance(s['habitats'],list) or len(s['habitats'])>64: return False
        for habitat in s['habitats']:
            if (not isinstance(habitat.get('id'),str) or len(habitat['id'])!=16
                    or type(habitat.get('biome')) is not int or not 0<=habitat['biome']<8
                    or type(habitat.get('visits')) is not int or not 1<=habitat['visits']<=1000000
                    or type(habitat.get('theme')) is not int or not 0<=habitat['theme']<16
                    or type(habitat.get('layout')) is not int or not 0<=habitat['layout']<16): return False
        if len(s['dex'])>256 or not all(valid_pet(p) for p in s['dex']): return False
        if len(s['family'])>128 or len(s['dungeons'])>8: return False
        for d in s['dungeons']:
            if not isinstance(d['seed'],str) or len(d['seed'])!=64 or not all(c in '0123456789abcdef' for c in d['seed']): return False
            if not 0<=d['floor']<=3 or not 0<=d['biome']<len(BIOMES) or not 1<=d['level']<=20: return False
            if 'gene_version' in d:
                if not supported_gene(d['gene_version']): return False
                if not all(type(d.get(k)) is int for k in ('theme','layout','reward','difficulty')): return False
                if not 0<=d['theme']<16 or not 0<=d['layout']<16 or not 0<=d['reward']<4 or not 1<=d['difficulty']<=3: return False
        return True
    except (KeyError,TypeError,ValueError):
        return False


def stats(p):
    level=p['level']; stage=p['evolution']; base=TYPE_BASE_STATS[p['type']]; bonus=_part_totals(p)
    role=STARTER_ROLE_BONUS.get(p.get('starter_role',''),(0,0,0,0,0))
    result={'hp':max_hp(p), 'attack':base[1]+level*2+stage*8+bonus[1]+role[1],
            'defense':base[2]+level+stage*6+bonus[2]+role[2],
            'special':base[3]+level*2+stage*8+bonus[3]+role[3],
            'speed':base[4]+level+stage*4+bonus[4]+role[4]}
    trait=p['traits']['combat'] if p.get('traits') else 0
    result[('attack','defense','special','speed')[trait//4]]+=2
    route=p.get('evolution_paths',[])[-1] if p.get('evolution_paths') else None
    if route is not None:
        key=('attack','speed','special','defense')[route]
        result[key]+=4*p.get('evolution',0)
    return result


def moves(p):
    tail=(MOVE_TABLE[3][p['parts'][5]%4] if p.get('present',[True]*8)[5]
          else BODY_MOVES[p['parts'][1]%4])
    return [MOVE_TABLE[0][p['type']], MOVE_TABLE[1][p['parts'][0]%4],
            MOVE_TABLE[2][p['parts'][2]%4], tail]


def move_unlocked(p,index):
    from pet_game import MOVE_LEVELS
    return 0<=index<4 and p['level']+p.get('evolution',0)*5>=MOVE_LEVELS[index]


def palette_name(p):
    return PALETTE_NAMES[p['palette']]


def trait_name(p):
    return ('ゴウリキ','コウカク','シュウチュウ','シュンソク')[p['traits']['combat']//4]


def subtype(p):
    return SUBTYPES[p['type']][p['parts'][0]//4]


def species_name(p):
    return SPECIES_NAMES[p['type']][p['parts'][0]//4]


def display_name(p):
    return p.get('nickname') or species_name(p)


def valid_nickname(name):
    return isinstance(name,str) and len(name)<=8 and all(
        'ぁ'<=c<='ん' or 'ァ'<=c<='ヶ' or c in 'ー・ ' or
        'A'<=c<='Z' or 'a'<=c<='z' or '0'<=c<='9' for c in name)


def rename(s,uid,name):
    if not isinstance(name,str): raise ValueError('名前を入力してください')
    name=name.strip().replace('ゔ','ヴ').replace('ゕ','ヵ').replace('ゖ','ヶ')
    if not valid_nickname(name): raise ValueError('ひらがな・カタカナ・英数字で8文字以内にしてください')
    pet=next((p for p in roster(s) if p['uid']==uid),None)
    if pet is None: raise ValueError('仲間が見つかりません')
    pet['nickname']=name
    for p in s['dex']:
        if p['uid']==uid:p['nickname']=name
    return '名前を変更しました' if name else '種族名に戻しました'


def evolution_name(p):
    return EVOLUTION_NAMES[p['evolution']]


def evolution_route(p):
    growth=p.get('growth',{})
    values=(growth.get('battle',0),growth.get('explore',0),growth.get('care',0),growth.get('anomaly',0))
    best=max(values)
    tied=[i for i,value in enumerate(values) if value==best]
    return tied[p['traits']['personality']%len(tied)]


def evolution_route_name(p,preview=False):
    route=evolution_route(p) if preview or not p.get('evolution_paths') else p['evolution_paths'][-1]
    return EVOLUTION_ROUTES[route]


def visual_part_value(p,slot):
    """Apply route markings without changing the immutable Wi-Fi genome."""
    value=p['parts'][slot]
    if not p.get('evolution_paths') or not p.get('evolution',0): return value
    route=p['evolution_paths'][-1]; stage=p['evolution']
    affected=((2,4),(5,7),(0,6),(0,2,4,6))[route]
    return (value//4)*4+((value+stage+route+1)%4) if slot in affected else value


def can_evolve(p):
    return p['evolution']<MAX_EVOLUTION and p['level']>=EVOLUTION_LEVEL


def evolve(s,uid):
    p=get_pet(s,uid)
    if p is None: raise ValueError('なかまがいない')
    if p['evolution']>=MAX_EVOLUTION: raise ValueError('もうせいたい')
    if p['level']<EVOLUTION_LEVEL: raise ValueError('レベル20から')
    route=evolution_route(p)
    p['evolution']+=1; p['mastery']=p['evolution']; p['evolution_paths'].append(route)
    p['level']=1; p['xp']=0; p['hp']=max_hp(p)
    p['growth']={'battle':0,'explore':0,'care':0,'anomaly':0}
    record(s,p)
    return p


def care(s,action):
    p=s['pet']
    if p is None: return 'たまごをまとう'
    if s['sleeping'] and action in ('play','train'): return 'おこしてからね'
    if action=='feed':
        if not s['inventory']['food']: return 'ごはんがない'
        if p['fullness']>=100: return 'おなかいっぱい'
        s['inventory']['food']-=1
        p['fullness']=min(100,p['fullness']+35)
        p['mood']=min(100,p['mood']+5)
        p['growth']['care']=min(1000000,p['growth']['care']+2)
        return 'ごちそうさま！'
    if action=='play':
        if s['elapsed']-p['last_play']<20: return 'すこしまってね'
        p['last_play']=s['elapsed']
        p['mood']=min(100,p['mood']+15)
        p['energy']=max(0,p['energy']-3)
        gain_xp(p,2)
        p['growth']['care']=min(1000000,p['growth']['care']+3)
        return 'たのしい！'
    if action=='train':
        if s['elapsed']-p['last_train']<30: return 'すこしまってね'
        if p['energy']<20 or p['fullness']<10: return 'ごはんときゅうけい'
        p['last_train']=s['elapsed']
        p['energy']-=20; p['fullness']-=10
        gain_xp(p,20+p['level']*3)
        p['growth']['battle']=min(1000000,p['growth']['battle']+2)
        return 'くんれんせいこう'
    if action=='rest':
        s['sleeping']=not s['sleeping']
        return 'おやすみ' if s['sleeping'] else 'おはよう'
    if action=='potion':
        if not s['inventory']['potion']: return 'アイテムがない'
        if p['hp']>=max_hp(p): return 'たいりょくまんたん'
        s['inventory']['potion']-=1
        p['hp']=min(max_hp(p),p['hp']+25)
        return 'かいふくした'
    return 'できない'


def advance(s,seconds):
    seconds=max(0,int(seconds))
    s['elapsed']+=seconds
    for egg in s['eggs']: egg['remaining']=max(0,egg['remaining']-seconds)
    total=s['care_remainder']+seconds
    minutes=total//60
    s['care_remainder']=total%60
    for p in roster(s):
        p['fullness']=max(0,p['fullness']-minutes)
        asleep=s['sleeping'] and s['pet'] and p['uid']==s['pet']['uid']
        p['energy']=min(100,p['energy']+minutes*15) if asleep else max(0,p['energy']-minutes)
        if asleep: p['hp']=min(max_hp(p),p['hp']+minutes*15)
        if p['fullness']==0: p['mood']=max(0,p['mood']-minutes)


def switch(s,uid):
    if s['pet'] and s['pet']['uid']==uid: return
    selected=get_pet(s,uid)
    if selected is None: raise ValueError('なかまがいない')
    remaining=[p for p in roster(s) if p['uid']!=uid]
    s['pet']=selected; s['caught']=remaining; s['sleeping']=False


def fusion_child(a,b,random_bytes,lock_part=-1):
    raw=bytearray(digest_for(random_bytes))
    inherited=[(a if raw[i]&1 else b)['parts'][i] for i in range(8)]
    present=[(a if raw[16+i]&1 else b).get('present',[True]*8)[i] for i in range(8)]
    kind=(a if raw[8]&1 else b)['type']
    palette=(a if raw[9]&1 else b)['palette']
    personality=(a if raw[13]&1 else b)['traits']['personality']
    temperament=(a if raw[14]&1 else b)['traits']['temperament']
    rare=(a if raw[15]&1 else b)['traits']['rare']
    combat=(a if raw[21]&1 else b)['traits']['combat']
    if raw[10]<13:
        changed=raw[11]%8; inherited[changed]=raw[12]%16
        if changed in (4,5,7) and raw[20]&1: present[changed]=not present[changed]
    if 0<=lock_part<8:
        inherited[lock_part]=a['parts'][lock_part]
        present[lock_part]=a.get('present',[True]*8)[lock_part]
    for index in (0,1,2,3,6): present[index]=True
    encoded=encode_v2(raw,kind,inherited,palette,present,personality,temperament,
                      rare,combat,raw[22]&15)
    return make_creature(encoded)


def fusion_preview(s,uid_a,uid_b,random_bytes,lock_part=-1):
    a,b=get_pet(s,uid_a),get_pet(s,uid_b)
    if not a or not b or uid_a==uid_b: return None
    child=fusion_child(a,b,random_bytes,lock_part); child['uid']='fusion-preview'
    child['generation']=max(a['generation'],b['generation'])+1
    child['parents']=[uid_a,uid_b]
    return child


def fuse(s,uid_a,uid_b,random_bytes,lock_part=-1):
    a,b=get_pet(s,uid_a),get_pet(s,uid_b)
    if not a or not b or uid_a==uid_b: raise ValueError('おやをふたりえらぶ')
    if min(a['level'],b['level'])<FUSION_LEVEL: raise ValueError('レベル20から')
    if len(s['eggs'])>=3: raise ValueError('たまごがいっぱい')
    child=assign_uid(s,fusion_child(a,b,random_bytes,lock_part))
    child['generation']=max(a['generation'],b['generation'])+1
    child['parents']=[uid_a,uid_b]
    remaining=[p for p in roster(s) if p['uid'] not in (uid_a,uid_b)]
    s['pet']=remaining[0] if remaining else None
    s['caught']=remaining[1:]
    s['eggs'].append({'child':child,'remaining':HATCH_SECONDS})
    s['family'].append({'child':child['uid'],'parents':[uid_a,uid_b],
                        'generation':child['generation'],'parent_types':[a['type'],b['type']]})
    s['family']=s['family'][-128:]
    s['sleeping']=False
    return child


def hatch(s,index):
    if not 0<=index<len(s['eggs']): raise ValueError('たまごがない')
    egg=s['eggs'][index]
    if egg['remaining']>0: raise ValueError('まだうまれない')
    child=egg['child']
    if s['pet'] is None: s['pet']=child
    else: s['caught'].append(child)
    del s['eggs'][index]
    record(s,child)
    return child


def incubate(s,index):
    if not 0<=index<len(s['eggs']): raise ValueError('たまごがない')
    if not s['inventory']['incubator']: raise ValueError('アイテムがない')
    if s['eggs'][index]['remaining']==0: raise ValueError('もううまれるよ')
    s['inventory']['incubator']-=1
    s['eggs'][index]['remaining']=max(0,s['eggs'][index]['remaining']-90)


def discover(s,raw,version=GENE_SCHEMA_VERSION):
    """Compatibility entry point. V2 identities always create a battle."""
    decoded=decode_gene(raw,version)
    if version>=2:
        s['discoveries']+=1
        level=s['pet']['level'] if s['pet'] else 1
        return ('battle',make_creature(raw,level,version=version))
    s['biome']=decoded['biome']
    s['discoveries']+=1
    level=s['pet']['level'] if s['pet'] else 1
    if decoded['event_kind']=='battle':
        enemy_level=max(1,min(20,level+decoded['enemy_level_delta']))
        return ('battle',make_creature(raw,enemy_level,version=version))
    if decoded['event_kind']=='experience':
        amount=decoded['xp_amount']
        if s['pet']: gain_xp(s['pet'],amount)
        return ('notice','けいけんち +%d'%amount)
    if decoded['event_kind']=='item':
        item=ITEMS[decoded['item_code']%len(ITEMS)]
        amount=decoded['item_amount']
        before=s['inventory'][item]
        s['inventory'][item]=min(99,before+amount)
        return ('notice','アイテム +%d'%(s['inventory'][item]-before))
    key=hexed(raw)
    if not any(d['seed']==key for d in s['dungeons']):
        s['dungeons']=[d for d in s['dungeons'] if d['floor']<3]
        if len(s['dungeons'])>=8: return ('notice','ダンジョンいっぱい')
        s['dungeons'].append({'seed':key,'gene_version':decoded['schema_version'],
                              'floor':0,'biome':s['biome'],'level':level,
                              'theme':decoded['dungeon_theme'],
                              'layout':decoded['dungeon_layout'],
                              'reward':decoded['dungeon_reward'],
                              'difficulty':decoded['dungeon_difficulty']})
    return ('notice','ダンジョンはっけん')


def scan_signals(s,rows):
    features,current_ids,environment_seed,records=wifi_world.snapshot(rows,s['last_scan_ids'])
    s['scan_serial']+=1; s['last_scan_ids']=sorted(current_ids)[-64:]
    s['environment']=features; s['biome']=features['biome']
    event=wifi_world.environment_event(features,environment_seed,s['scan_serial'])
    s['world_event']=event
    history={entry[0]:entry[1] for entry in s['signal_history']}
    choices=[]
    for record in records:
        last=history.get(record['id'],-wifi_world.COOLDOWN_SCANS)
        if s['scan_serial']-last<wifi_world.COOLDOWN_SCANS: continue
        base_level=s['pet']['level'] if s['pet'] else 1
        level=base_level+(1 if record['rssi']>=-50 else 0)
        if event['code']==3: level+=event['intensity']
        pet=make_creature(record['raw'],min(20,level))
        habitat=wifi_world.habitat_for(record['raw'])
        pet['memories']['birthplace']=habitat['id']
        reward=wifi_world.event_reward(environment_seed,record['raw'],s['scan_serial'],record['colony'])
        if reward['kind']=='none' and event['code']==1:
            reward={'kind':'experience','amount':8+event['intensity']*6}
        elif reward['kind']=='none' and event['code']==2:
            reward={'kind':'item','item':event['intensity']%4,'amount':event['intensity']}
        choices.append({'id':record['id'],'raw':record['raw'],'rssi':record['rssi'],
                        'channel':record['channel'],'colony':record['colony'],
                        'pet':pet,'reward':reward,'habitat':habitat,'event':event})
        if len(choices)==3: break
    return choices


def claim_signal(s,signal):
    token=signal['id']; s['signal_history']=[entry for entry in s['signal_history'] if entry[0]!=token]
    s['signal_history'].append([token,s['scan_serial']]); s['signal_history']=s['signal_history'][-64:]
    s['discoveries']+=1
    _discover_habitat(s,signal['habitat'])
    if s.get('pet'):
        p=s['pet']; p['growth']['explore']=min(1000000,p['growth']['explore']+1)
        p['memories']['habitats']=min(1000000,p['memories']['habitats']+1)
        if signal.get('event',{}).get('code')==4:
            p['growth']['anomaly']=min(1000000,p['growth']['anomaly']+signal['event']['intensity'])
    return signal['pet'],signal['reward']


def _discover_habitat(s,habitat):
    found=next((item for item in s['habitats'] if item['id']==habitat['id']),None)
    if found:
        found['visits']=min(1000000,found['visits']+1)
        return False
    s['habitats'].append({'id':habitat['id'],'biome':habitat['biome'],'visits':1,
                          'theme':habitat['theme'],'layout':habitat['layout']})
    s['habitats']=s['habitats'][-64:]
    key=habitat['dungeon_seed']
    if not any(d['seed']==key for d in s['dungeons']):
        s['dungeons']=[d for d in s['dungeons'] if d['floor']<3]
        if len(s['dungeons'])<8:
            level=s['pet']['level'] if s.get('pet') else 1
            s['dungeons'].append({'seed':key,'gene_version':GENE_SCHEMA_VERSION,'floor':0,
                                  'biome':habitat['biome'],'level':level,'theme':habitat['theme'],
                                  'layout':habitat['layout'],'reward':habitat['reward'],
                                  'difficulty':habitat['difficulty'],'habitat_id':habitat['id']})
    return True


def _add_dungeon(s,reward):
    key=reward['seed']
    if any(d['seed']==key for d in s['dungeons']): return False
    s['dungeons']=[d for d in s['dungeons'] if d['floor']<3]
    if len(s['dungeons'])>=8: return False
    level=s['pet']['level'] if s['pet'] else 1
    s['dungeons'].append({'seed':key,'gene_version':GENE_SCHEMA_VERSION,'floor':0,
                          'biome':s['biome'],'level':level,'theme':reward['theme'],
                          'layout':reward['layout'],'reward':reward['reward'],
                          'difficulty':reward['difficulty']})
    return True


def apply_signal_reward(s,reward):
    kind=reward.get('kind','none')
    if kind=='none': return ''
    if kind=='experience':
        gain_xp(s['pet'],reward['amount']); return 'ボーナスEXP +%d'%reward['amount']
    if kind=='item':
        item=ITEMS[reward['item']%len(ITEMS)]; before=s['inventory'][item]
        s['inventory'][item]=min(99,before+reward['amount'])
        return 'ボーナスアイテム +%d'%(s['inventory'][item]-before)
    if kind=='dungeon':
        return 'ダンジョンはっけん' if _add_dungeon(s,reward) else 'ダンジョンいっぱい'
    return ''


def dungeon_summary(d):
    return {'theme':DUNGEON_THEMES[d.get('theme',0)],
            'layout':DUNGEON_LAYOUTS[d.get('layout',0)],
            'reward':DUNGEON_REWARDS[d.get('reward',0)],
            'difficulty':d.get('difficulty',1)}


def dungeon_enemy(d):
    if 'gene_version' in d:
        source='RR-DUNGEON-%d:%s:%d:%d:%d'%(d['gene_version'],d['seed'],d['layout'],d['theme'],d['floor'])
    else:
        source=d['seed']+str(d['floor'])
    raw=bytearray(digest_for(source))
    if d['floor']==2:
        raw[0]|=8
        for i in (1,2,3): raw[i]|=136
        raw[4]|=128
    difficulty=d.get('difficulty',1)
    version=d.get('gene_version',1)
    p=make_creature(raw,min(20,d['level']+d['floor']+difficulty-1),version=version)
    if d['floor']==2:
        if version>=2:
            parts=[max(8,value) for value in p['parts']]
            raw=encode_v2(raw,p['type'],parts,p['palette'],[True]*8,
                          p['traits']['personality'],p['traits']['temperament'],
                          p['traits']['rare'],p['traits']['combat'])
            p=make_creature(raw,min(20,d['level']+d['floor']+difficulty-1),version=version)
        p['boss']=True
        p['hp']=max_hp(p)
    return p


def dungeon_reward(d):
    """Return item, quantity, XP and an optional extra reward."""
    if 'gene_version' not in d:
        return ('incubator',1,40,('potion',2))
    rewards=(('incubator',1,40,None),('potion',3,50,None),
             ('food',5,60,None),('scanner',2,45,('potion',1)))
    return rewards[d['reward']]


class Battle(BaseBattle):
    def __init__(self,profile,enemy,practice=False,dungeon=None,signal_reward=None):
        super().__init__(profile,enemy,practice)
        self.enemy=clone(enemy)
        self.dungeon=dungeon
        self.signal_reward=signal_reward; self.reward_message=''
        self.guard=0; self.poison=0; self.scanner_bonus=False
        self.settled=False

    def act(self,command,move=0):
        if self.result or self.await_reply: return False
        if command=='hit':
            if not move_unlocked(self.player,move):
                self.message='LOCKED'; return False
            atk,defense=stats(self.player),stats(self.enemy)
            value=atk['special'] if move in (0,1) else atk['attack']
            damage=max(2,value+move*2-defense['defense']//2)
            if TYPE_STRONG_AGAINST[self.player['type']]==self.enemy['type']: damage=damage*6//5
            if self.player['energy']<15 or self.player['fullness']<15: damage=max(2,damage*3//4)
            source=(self.player['parts'][5] if self.player.get('present',[True]*8)[5]
                    else self.player['parts'][1])
            if move==3 and source%4==3: self.guard=2
            if move==3 and source%4==1: self.poison=3
            self.enemy['hp']=max(0,self.enemy['hp']-damage)
            if self.player.get('starter_role')=='サポート' and move==0:
                self.player['hp']=min(max_hp(self.player),self.player['hp']+max(2,atk['special']//5))
            self.player['energy']=max(0,self.player['energy']-1)
            self.message='HIT -%d'%damage
            if not self.enemy['hp']: self.result='win'
        elif command=='scan':
            if occupied(self.profile)>=CAPACITY:
                self.message='DEX FULL'; return False
            lost=max_hp(self.enemy)-self.enemy['hp']
            amount=15+60*lost//max_hp(self.enemy)+(25 if self.scanner_bonus else 0)
            self.scan=min(100,self.scan+amount)
            self.scanner_bonus=False
            self.message='SCAN %d%%'%self.scan
            if self.scan==100: self.result='caught'
        elif command in ('item','scanner'):
            item='potion' if command=='item' else 'scanner'
            if not self.profile['inventory'][item]: self.message='NO ITEMS'; return False
            if item=='potion' and self.player['hp']==max_hp(self.player): self.message='HP FULL'; return False
            self.profile['inventory'][item]-=1
            if item=='potion':
                self.player['hp']=min(max_hp(self.player),self.player['hp']+25)
                self.message='HEAL +25'
            else:
                self.scanner_bonus=True
                self.message='スキャンきょうか'
        elif command=='run': self.result='escaped'; self.message='ESCAPED'
        else: return False
        self.await_reply=self.result is None
        return True

    def reply(self):
        if self.result or not self.await_reply: return
        if self.poison:
            self.enemy['hp']=max(0,self.enemy['hp']-3); self.poison-=1
            if not self.enemy['hp']:
                self.result='win'; self.await_reply=False; return
        damage=max(2,stats(self.enemy)['attack']//2-stats(self.player)['defense']//3)
        if self.enemy.get('boss'): damage=damage*3//2
        if self.guard: damage=max(1,damage//2); self.guard-=1
        self.player['hp']=max(0,self.player['hp']-damage)
        self.message='OUCH -%d'%damage
        self.await_reply=False
        if not self.player['hp']: self.result='lost'

    def settle(self):
        if not self.result or self.settled: return
        s=self.profile
        if self.result in ('win','caught'):
            gain_xp(self.player,12+self.enemy['level']*6)
            self.player['growth']['battle']=min(1000000,self.player['growth']['battle']+1)
            if self.result=='win': s['wins']+=1
            else:
                child=assign_uid(s,clone(self.enemy)); child.pop('boss',None)
                child['hp']=max_hp(child); s['caught'].append(child); record(s,child)
            if self.dungeon is not None:
                d=s['dungeons'][self.dungeon]; d['floor']+=1
                if self.enemy.get('boss'):
                    self.player['memories']['bosses']=min(1000000,self.player['memories']['bosses']+1)
                if d['floor']==3:
                    item,amount,xp,extra=dungeon_reward(d)
                    s['inventory'][item]=min(99,s['inventory'][item]+amount)
                    if extra:
                        other,quantity=extra
                        s['inventory'][other]=min(99,s['inventory'][other]+quantity)
                    gain_xp(self.player,xp)
            if self.signal_reward: self.reward_message=apply_signal_reward(s,self.signal_reward)
        self.settled=True


def public_state(s):
    data=clone(s)
    data['catalog_version']=PUBLIC_CATALOG_VERSION
    pets=roster(data)+data['dex']+data['starter_options']+[e['child'] for e in data['eggs']]
    for p in pets:
        p['stats']=stats(p); p['moves']=moves(p); p['type_name']=TYPES[p['type']]
        p['subtype']=subtype(p); p['evolution_name']=evolution_name(p)
        p['species_name']=species_name(p);p['display_name']=display_name(p)
        p['palette_name']=palette_name(p); p['trait_name']=trait_name(p)
        p['evolution_route']=evolution_route_name(p,not bool(p.get('evolution_paths')))
        p['gene_id']=p['genome'][:16]; p.pop('genome',None)
    for d in data['dungeons']:
        d['dungeon_id']=d['seed'][:16]; d.pop('seed',None)
    data['part_dex_count']=part_dex_count(data); data.pop('part_dex',None)
    data['world_event']['name']=WORLD_EVENTS[data['world_event']['code']]
    return data
