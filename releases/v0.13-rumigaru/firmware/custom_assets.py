"""Optional visual attachments, separate from monster genes and saves."""
import os,json,binascii
from world import PARTS


class CustomParts:
    def __init__(self,folder='custom_parts'):
        self.folder=folder
        self.data={'revision':0,'items':[],'equipped':{}}
        for filename in ('index.json','index.backup'):
            try:
                with open(folder+'/'+filename) as f:data=json.load(f)
                if not self.valid(data):continue
                self.data=data;break
            except (OSError,ValueError,TypeError):pass

    def valid(self,data):
        if not isinstance(data,dict) or type(data.get('revision')) is not int or data['revision']<0:return False
        items=data.get('items');equipped=data.get('equipped')
        if not isinstance(items,list) or len(items)>24 or not isinstance(equipped,dict):return False
        ids=[]
        for item in items:
            if not isinstance(item,dict):return False
            uid=item.get('id','')
            if not isinstance(uid,str) or len(uid)!=17 or uid[0]!='p' or any(c not in '0123456789abcdef' for c in uid[1:]):return False
            if uid in ids or item.get('slot') not in PARTS or type(item.get('frames')) is not int or not 1<=item['frames']<=4:return False
            if not isinstance(item.get('name'),str):return False
            ids.append(uid)
        return all(isinstance(key,str) and isinstance(value,dict) and
                   all(slot in PARTS and uid in ids for slot,uid in value.items()) for key,value in equipped.items())

    def key(self,p): return p['uid']+':'+str(p.get('evolution',0))

    def selection(self,p): return self.data['equipped'].get(self.key(p),{})

    def commit(self,data):
        try: os.mkdir(self.folder)
        except OSError: pass
        data['revision']=self.data['revision']+1
        if not self.valid(data):raise ValueError('パーツ情報が不正です')
        replace=getattr(os,'replace',os.rename)
        with open(self.folder+'/backup.tmp','w') as f:json.dump(self.data,f)
        replace(self.folder+'/backup.tmp',self.folder+'/index.backup')
        with open(self.folder+'/index.tmp','w') as f: json.dump(data,f)
        replace(self.folder+'/index.tmp',self.folder+'/index.json')
        self.data=data

    def install(self,body):
        slot=body.get('slot'); name=body.get('name','')
        frames=body.get('frames',1); pixels=body.get('pixels','')
        if slot not in PARTS or not isinstance(name,str) or not 1<=len(name)<=24:
            raise ValueError('部位と名前を確認してください')
        if type(frames) is not int or not 1<=frames<=4 or not isinstance(pixels,str) or len(pixels)!=8192*frames:
            raise ValueError('64×64、1〜4コマの画像が必要です')
        if len(self.data['items'])>=24: raise ValueError('追加パーツは24個までです')
        try: raw=binascii.unhexlify(pixels)
        except (ValueError,TypeError): raise ValueError('画像データが不正です')
        if len(raw)!=4096*frames or any(v>11 for v in raw) or not any(raw):
            raise ValueError('画像の色または透明部分を確認してください')
        data=json.loads(json.dumps(self.data))
        identity='p'+binascii.hexlify(os.urandom(8)).decode()
        try: os.mkdir(self.folder)
        except OSError: pass
        with open(self.folder+'/'+identity+'.idx','wb') as f: f.write(raw)
        data['items'].append({'id':identity,'name':name,'slot':slot,'frames':frames})
        try: self.commit(data)
        except Exception:
            os.remove(self.folder+'/'+identity+'.idx')
            raise
        return identity

    def equip(self,p,slot,identity):
        if slot not in PARTS: raise ValueError('部位が不正です')
        if identity and not any(i['id']==identity and i['slot']==slot for i in self.data['items']):
            raise ValueError('この部位に使えるパーツを選んでください')
        data=json.loads(json.dumps(self.data)); key=self.key(p)
        selected=data['equipped'].get(key,{})
        if identity: selected[slot]=identity
        else: selected.pop(slot,None)
        data['equipped'][key]=selected; self.commit(data)

    def delete(self,identity):
        if not any(i['id']==identity for i in self.data['items']): raise ValueError('パーツがありません')
        data=json.loads(json.dumps(self.data))
        for selected in data['equipped'].values():
            for slot in list(selected):
                if selected[slot]==identity: selected.pop(slot)
        data['items']=[i for i in data['items'] if i['id']!=identity]
        self.commit(data)
        os.remove(self.folder+'/'+identity+'.idx')

    def read(self,p,slot,frame):
        identity=self.selection(p).get(slot)
        item=next((i for i in self.data['items'] if i['id']==identity),None)
        if not item: return None
        try:
            with open(self.folder+'/'+identity+'.idx','rb') as f:
                f.seek((frame%item['frames'])*4096);data=bytearray(f.read(4096))
            if len(data)==4096 and not any(v>11 for v in data):return data
        except OSError:pass
        return None
