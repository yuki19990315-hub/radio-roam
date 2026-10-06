"""Local Android companion. Bounded JSON requests and session-token writes."""
import socket,time,os,json
import world


class PhoneLink:
    def __init__(self,app):
        import network
        self.app=app
        token=os.urandom(4)
        self.ssid='Roam-%02x%02x'%(token[0],token[1])
        self.password='%08d'%(int.from_bytes(token,'little')%100000000)
        self.ap=network.WLAN(network.AP_IF)
        self.ap.active(True)
        self.server=None
        try:
            self.ap.config(essid=self.ssid,password=self.password,authmode=network.AUTH_WPA2_PSK)
            self.server=socket.socket()
            self.server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            self.server.bind(('0.0.0.0',80)); self.server.listen(2); self.server.setblocking(False)
        except Exception:
            if self.server: self.server.close()
            self.ap.active(False)
            raise
        self.clients=[]
        self.token=world.hexed(os.urandom(16)); self.receipts=[]

    def pet(self,body):
        p=next((p for p in world.roster(self.app.state) if p['uid']==body.get('uid')),None)
        if p is None or p['evolution']!=body.get('stage'): raise ValueError('仲間を再同期してください')
        return p

    def mutate(self,path,body):
        if not isinstance(body,dict): raise ValueError('入力が不正です')
        a=self.app
        if a.battle or a.phase or a.display_asleep: raise ValueError('バトル終了後に操作してください')
        if path=='/api/action':
            action=body.get('action')
            if action in ('feed','play','train','rest','potion'):
                operation=lambda s:world.care(s,action)
            elif action=='switch':
                p=self.pet(body); operation=lambda s:world.switch(s,p['uid'])
            elif action=='evolve':
                p=self.pet(body); operation=lambda s:world.evolve(s,p['uid'])
            elif action=='rename':
                p=self.pet(body); operation=lambda s:world.rename(s,p['uid'],body.get('nickname'))
            elif action in ('hatch','incubate'):
                uid=body.get('egg_uid')
                index=next((i for i,e in enumerate(a.state['eggs']) if e['child']['uid']==uid),None)
                if index is None:raise ValueError('卵を再同期してください')
                operation=lambda s:(world.hatch if action=='hatch' else world.incubate)(s,index)
            else: raise ValueError('未対応の操作です')
            candidate,result=a.store.transaction(a.state,operation)
            a.state=candidate; a.save_pending=False; a.last_save=time.ticks_ms()
            return {'message':result if isinstance(result,str) else '反映しました'}
        custom=a.screen.art.custom
        if path=='/api/parts/upload':
            return {'message':'パーツを保存しました。装着先を選んでください','id':custom.install(body)}
        if path=='/api/parts/equip':
            custom.equip(self.pet(body),body.get('slot'),body.get('id'))
        elif path=='/api/parts/delete': custom.delete(body.get('id'))
        else: raise ValueError('未対応の操作です')
        a.screen.art.cache.clear(); a.screen.art.scaled_cache.clear()
        return {'message':'反映しました'}

    def dispatch(self,method,path,headers,raw):
        if method=='GET':
            content,body=self.response(path)
            return ('200 OK' if content else '404 Not Found'),content or 'text/plain',body
        content='application/json; charset=utf-8'
        if method!='POST' or headers.get('x-roam-token')!=self.token or headers.get('content-type','').split(';')[0]!='application/json':
            return '403 Forbidden',content,b'{"error":"Reconnect to the device"}'
        try:
            body=json.loads(raw)
            if not isinstance(body,dict): raise ValueError('入力が不正です')
            request_id=body.get('request_id')
            if not isinstance(request_id,str) or not 1<=len(request_id)<=64: raise ValueError('操作IDが不正です')
            for old_path,old_id,result in self.receipts:
                if old_id==request_id:
                    if old_path!=path: raise ValueError('操作IDが重複しています')
                    return '200 OK',content,result
            result=json.dumps(self.mutate(path,body)).encode()
            self.receipts.append((path,request_id,result)); self.receipts=self.receipts[-8:]
            return '200 OK',content,result
        except (ValueError,TypeError,KeyError) as exc:
            return '400 Bad Request',content,json.dumps({'error':str(exc)}).encode()
        except OSError:
            return '503 Service Unavailable',content,json.dumps({'error':'保存できませんでした。空き容量と接続を確認してください'}).encode()

    def response(self,path):
        if path=='/phone_controls.js':
            with open('assets/phone_controls.js','rb') as f: return 'application/javascript; charset=utf-8',f.read()
        if path=='/':
            with open('assets/phone.html','rb') as f: return 'text/html; charset=utf-8',f.read()
        if path=='/api/state':
            data=world.public_state(self.app.state)
            data['art_revision']='rumigaru13:%d'%self.app.screen.art.custom.data['revision']
            data['phone_busy']=bool(self.app.battle or self.app.phase)
            return 'application/json; charset=utf-8',json.dumps(data).encode()
        if path=='/api/session':
            return 'application/json',json.dumps({'token':self.token}).encode()
        if path=='/api/parts':
            return 'application/json',json.dumps(self.app.screen.art.custom.data).encode()
        if path.startswith('/api/layers?'):
            values={pair.split('=',1)[0]:pair.split('=',1)[1] for pair in path.split('?',1)[1].split('&') if '=' in pair}
            p=next((p for p in world.roster(self.app.state) if p['uid']==values.get('id')),None)
            if p and values.get('slot') in world.PARTS:
                return 'application/json',json.dumps(self.app.screen.art.layers(p,values['slot'])).encode()
        if path.startswith('/api/sprite?id='):
            query=path.split('?',1)[1]
            values={pair.split('=',1)[0]:pair.split('=',1)[1] for pair in query.split('&') if '=' in pair}
            uid=values.get('id','')
            try: stage=int(values['stage']) if 'stage' in values else None
            except ValueError: stage=None
            pets=world.roster(self.app.state)+self.app.state['dex']+[e['child'] for e in self.app.state['eggs']]
            p=next((p for p in pets if p['uid']==uid and p['evolution']==stage),None) if stage is not None else None
            if p is None: p=next((p for p in pets if p['uid']==uid),None)
            if p: return 'application/json',json.dumps(self.app.screen.export_sprite(p)).encode()
        return None,b'Not found'

    def poll(self):
        try:
            c,_=self.server.accept()
            c.setblocking(False)
            if len(self.clients)>=2: c.close()
            else: self.clients.append({'s':c,'request':b'','output':None,'at':time.ticks_ms(),'sent':0})
        except OSError: pass
        for client in self.clients[:]:
            try:
                if time.ticks_diff(time.ticks_ms(),client['at'])>20000: raise ValueError('timeout')
                if client['output'] is None:
                    try: chunk=client['s'].recv(512)
                    except OSError: continue
                    if not chunk: raise ValueError('closed')
                    client['request']+=chunk
                    client['at']=time.ticks_ms()
                    if len(client['request'])>40000: raise ValueError('request too big')
                    if b'\r\n\r\n' not in client['request']:
                        if len(client['request'])>2048: raise ValueError('headers too big')
                        continue
                    head,raw=client['request'].split(b'\r\n\r\n',1)
                    if len(head)>2048: raise ValueError('headers too big')
                    lines=head.decode().split('\r\n'); line=lines[0].split()
                    if len(line)!=3: raise ValueError('bad request')
                    headers={}
                    for entry in lines[1:]:
                        k,v=entry.split(':',1); headers[k.lower().strip()]=v.strip()
                    size=int(headers.get('content-length','0'))
                    if size<0 or size>36000 or 'transfer-encoding' in headers: raise ValueError('body too big')
                    if len(raw)<size: continue
                    status,content,body=self.dispatch(line[0],line[1],headers,raw[:size])
                    headers=('HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n'%(status,content or 'text/plain',len(body))).encode()
                    client['output']=headers+body
                    client['request']=b''
                try:
                    n=client['s'].send(memoryview(client['output'])[client['sent']:client['sent']+2048])
                except OSError: continue
                client['sent']+=n; client['at']=time.ticks_ms()
                if client['sent']>=len(client['output']): raise ValueError('done')
            except (ValueError,OSError,UnicodeError):
                client['s'].close(); self.clients.remove(client)

    def close(self):
        for c in self.clients: c['s'].close()
        self.clients=[]; self.server.close(); self.ap.active(False)
