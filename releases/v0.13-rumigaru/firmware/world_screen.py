import time
import world
from pet_screen import Screen as BaseScreen, INK,WHITE,TEAL,RED,upscale_mirror
from world import max_hp
from pet_motion import leap
from world_art import Art


class Screen(BaseScreen):
    def __init__(self):
        super().__init__(False)
        self.art=Art()
        self.biome=-1

    def creature(self,p,frame,x,y,size=64,mirror=False):
        self.art.draw(self.fb,p,frame,x,y,size,mirror)

    def export_sprite(self,p):
        return self.art.export(p)

    def pet_name(self,p,y,badge=False):
        value=world.display_name(p);x=(120-len(value)*8)//2
        if badge:self.fb.fill_rect(x-4,y-2,len(value)*8+8,12,WHITE)
        # A player's nickname is text, never a localization command such as HP.
        self.font.draw(self.fb,value,x,y,INK)

    def egg(self,x,y,now,size=26):
        bob=1 if (now//500)%2 else 0
        self.fb.ellipse(x+size//2,y+size//2+bob,size//2-2,size//2,INK,True)
        self.fb.ellipse(x+size//2,y+size//2+bob,size//2-3,size//2-1,WHITE,True)
        self.fb.fill_rect(x+7,y+8+bob,5,5,TEAL)
        self.fb.fill_rect(x+15,y+18+bob,4,4,TEAL)

    def footer(self,back='home',next_key=None):
        self.button(back,'モドル',24,100,34)
        if next_key: self.button(next_key,'ツギ',64,100,32)

    def listing(self,app,title,items):
        self.badge(title,11)
        start=app.list_offset*4
        for i,(key,label) in enumerate(items[start:start+4]):
            self.button(key,label,24,30+i*16,72,14)
        if not items: self.text('まだないよ',51)
        self.footer('menu' if app.page!='menu' else 'home','list_next' if len(items)>4 else None)

    def draw(self,a,now):
        s=a.state; p=s['pet']; page=a.page
        if s['biome']!=self.biome:
            with open('assets/biome%d.rgb'%s['biome'],'rb') as f: self.background=f.read()
            self.biome=s['biome']
        self.buf[:]=self.background; self.buttons=[]
        frame=2 if (now//250)%16==10 else (0,1,0,3)[(now//250)%4]
        if page=='starter':
            self.badge('さいしょの3たい',10)
            q=a.selected_starter()
            if q:
                self.creature(q,frame,33,23,54)
                self.text('%s  %s'%(q.get('starter_name',''),world.TYPES[q['type']]),78)
                self.text('%d / 3'%(a.index%3+1),89)
            self.button('starter_prev','マエ',8,100,28,12)
            self.button('choose_starter','エラブ',40,100,40,12)
            self.button('starter_next','ツギ',84,100,28,12)
        elif page=='home':
            if p:self.pet_name(p,10,True)
            else:self.badge(world.BIOMES[s['biome']],10)
            if p:
                condition=('おやすみ' if s['sleeping'] else 'かいふく' if p['hp']<max_hp(p)//3 else
                           'ごはん' if p['fullness']<20 else 'きゅうけい' if p['energy']<20 else 'げんき')
                self.text('L%02d %s'%(p['level'],condition),23)
                self.creature(p,7 if s['sleeping'] else (6 if a.happy else frame),28,27)
                self.hp(36,87,48,p['hp'],max_hp(p))
                self.buttons.append(('play',28,34,64,49))
            else:
                self.egg(45,43,now,32)
                self.text('たまごをまとう',82)
            self.button('explore','サガス',22,98,34)
            self.button('menu','メニュー',60,98,40)
        elif page in ('menu','care','bag','dungeons','habitats','fusion_lock','eggs','battlebag'):
            self.listing(a,a.page_title(),a.page_items())
            if page=='battlebag':
                self.buttons=[b for b in self.buttons if b[0]!='menu']
                self.button('battle','モドル',24,100,34)
        elif page=='signals':
            self.badge('シグナルをえらぶ',10)
            for i,signal in enumerate(a.signals[:3]):
                y=26+i*23; strength=max(0,min(99,(signal['rssi']+100)*2))
                self.creature(signal['pet'],frame,7,y-3,22)
                mark='G' if signal.get('colony') else ' '
                self.button('signal:%d'%i,'%s%s%02d'%(world.TYPE_SHORT[signal['pet']['type']],mark,strength),31,y,78,18)
            self.text(world.WORLD_EVENTS[s['world_event']['code']],91)
            self.text('G=ムレ AP%d'%s['environment']['count'],99)
            self.button('home','モドル',40,108,40,11)
        elif page in ('roster','dex','parent_a','parent_b'):
            entries=a.entries()
            title={'roster':'なかま','dex':'ズカン','parent_a':'おやをえらぶ1','parent_b':'おやをえらぶ2'}[page]
            self.badge(title,10)
            if entries:
                q=entries[a.index%len(entries)]
                self.text('%s %02d'%(world.TYPES[q['type']],q['level']),23)
                self.creature(q,frame,42,31,36)
                self.pet_name(q,75)
                if page=='roster':
                    self.button('select','ツレル',18,88,40,11)
                    self.button('stats','ノウリョク',62,88,40,11)
                elif page.startswith('parent'):
                    self.button('select_parent','エラブ',39,88,42,11)
                self.button('menu','モドル',27,100,32,11)
                self.button('next','ツギ',62,100,30,11)
            else:
                self.text('レベル20から' if page.startswith('parent') else 'まだいないよ',50)
                self.footer('menu')
        elif page=='stats':
            q=a.selected_pet()
            self.badge('%s %s'%(world.TYPES[q['type']],world.evolution_name(q)),10)
            values=world.stats(q)
            for i,(label,value) in enumerate((('たいりょく',q['hp']),('こうげき',values['attack']),
                    ('ぼうぎょ',values['defense']),('とくしゅ',values['special']),('すばやさ',values['speed']))):
                self.text('%s %d'%(label,value),28+i*12)
            self.text('%s %s'%(world.trait_name(q),world.evolution_route_name(q)),89)
            self.footer('roster')
        elif page=='evolution':
            self.badge('しんか',10)
            if p:
                if p['evolution']<world.MAX_EVOLUTION:
                    future=world.clone(p); future['evolution']+=1
                    self.creature(p,frame,12,26,42)
                    self.creature(future,frame,66,26,42)
                    self.text('%s から %sへ'%(world.evolution_name(p),world.evolution_name(future)),68)
                    self.text('ルート '+world.evolution_route_name(p,True),79)
                    self.text('レベル20 → レベル1',89)
                    self.button('evolve','シンカ',62,99,40,12,world.can_evolve(p))
                else:
                    self.creature(p,frame,32,24,56)
                    self.text('せいたい・しんかかんりょう',83)
            self.button('menu','モドル',18,99,38,12)
        elif page=='care_status':
            self.badge('ようす',10)
            if p:
                for i,(label,key) in enumerate((('おなか','fullness'),('きげん','mood'),('げんき','energy'))):
                    self.text('%s %d'%(label,p[key]),30+i*19)
                    self.hp(28,40+i*19,64,p[key],100)
            self.footer('care')
        elif page=='fusion_confirm':
            self.badge('ごうせい',10)
            q,r=world.get_pet(s,a.parent_a),world.get_pet(s,a.parent_b)
            if q and r:
                self.creature(q,frame,7,28,28)
                self.creature(r,frame,85,28,28,True)
            if a.fusion_preview:
                self.creature(a.fusion_preview,frame,43,22,36)
            lock='オマカセ' if a.fusion_lock<0 else ('アタマ','カラダ','ウデ','アシ','ツノ','シッポ','メ','ハネ')[a.fusion_lock]
            self.text('ヒキツギ '+lock,61)
            self.text('おやはきえる',74,RED)
            self.button('menu','ヤメル',22,99,34)
            self.button('fuse','ゴウセイ',61,99,38)
        elif page=='egg_detail':
            self.badge('たまご',10)
            if s['eggs']:
                e=s['eggs'][a.index%len(s['eggs'])]
                self.egg(43,30,now,34)
                self.text('あと %d びょう'%e['remaining'],72)
                self.button('hatch','カエス',20,88,40,11,e['remaining']==0)
                self.button('incubate','ハヤメル',62,88,40,11)
            self.footer('eggs')
        elif page in ('battle','moves'):
            b=a.battle
            self.badge(('ボス ' if b.enemy.get('boss') else 'テキ ')+str(b.enemy['level']),10)
            self.hp(67,24,34,b.enemy['hp'],max_hp(b.enemy))
            pf,ef=frame,frame; px,py,ex,ey=16,34,68,34
            elapsed=time.ticks_diff(now,a.phase_at); contact=270<=elapsed<350
            if a.phase=='attack':
                dx,dy=leap(elapsed); px+=dx; py+=dy; pf=4; ef=5 if contact else frame
            elif a.phase=='reply':
                dx,dy=leap(elapsed); ex-=dx; ey+=dy; ef=4; pf=5 if contact else frame
            elif b.result=='caught': pf=ef=6
            self.creature(p,pf,px,py,36)
            self.creature(b.enemy,ef,ex,ey,36,True)
            if a.phase=='scan': self.fb.hline(68,34+(now//30)%32,36,TEAL)
            self.hp(18,72,33,p['hp'],max_hp(p))
            self.font.draw(self.fb,'%d%%'%b.scan,69,68,INK)
            self.badge(b.message,78)
            ready=a.phase is None and b.result is None
            if b.result: self.button('finish','つぎへ',40,99,40,12,a.phase is None)
            else:
                labels=world.moves(p) if page=='moves' else ('コウゲキ','スキャン','ドウグ','ニゲル')
                keys=['move%d'%i for i in range(4)] if page=='moves' else ['moves','scan','battlebag','run']
                for i in range(4):
                    x=18+(i%2)*44 if i<2 else 27+(i%2)*34
                    enabled=ready and (page!='moves' or world.move_unlocked(p,i))
                    self.button(keys[i],labels[i],x,88+i//2*12,40 if i<2 else 32,11,enabled)
                if page=='moves': self.buttons.append(('battle',20,4,80,24))
        elif page=='phone':
            self.badge('スマホれんけい',11)
            for i,line in enumerate(('Wi-Fiにつなぐ',a.phone.ssid,'パスワード',a.phone.password,'192.168.4.1')):
                self.text(line,31+i*12)
            self.button('phone_close','オワル',40,100,40)
        elif page=='peers':
            self.badge('すれちがい',10)
            self.text('であい %d'%s['peers'],38)
            self.text('オン' if s['ble'] else 'オフ',56)
            self.button('ble_toggle','キリカエ',37,76,46,14)
            self.footer('menu')
        elif page=='part_dex':
            self.badge('パーツズカン',10)
            self.text('ハッケン %d / 2304'%world.part_dex_count(s),25)
            for kind in range(6):
                self.text('%s %d/384'%(world.TYPE_SHORT[kind],world.part_dex_type_count(s,kind)),40+kind*10)
            self.footer('menu')
        elif page=='search':
            self.badge('たんさくちゅう',12)
            if p: self.creature(p,frame,28,28)
        elif page=='dungeon_detail':
            self.badge('ダンジョンしょうさい',10)
            if 0<=a.index<len(s['dungeons']):
                d=s['dungeons'][a.index]; info=world.dungeon_summary(d)
                self.text('%s %d/3'%(world.BIOMES[d['biome']],d['floor']+1),28)
                self.text('テーマ '+info['theme'],42)
                self.text('ケイジョウ '+info['layout'],55)
                self.text('ムズカシサ '+'*'*info['difficulty'],68)
                self.text('ホウシュウ '+info['reward'],81)
                self.button('dungeon_enter','ハイル',63,99,39,12)
            self.button('dungeons','モドル',18,99,39,12)
        else:
            self.badge('おしらせ',10)
            if a.hatch_pet: self.creature(a.hatch_pet,6,28,23)
            elif p: self.creature(p,6 if a.happy else frame,32,25,56)
            else: self.egg(47,30,now,26)
            lines=[a.notice[i:i+10] for i in range(0,len(a.notice),10)]
            for i,line in enumerate(lines[:2]): self.text(line,74+i*11)
            self.button('home','つぎへ',40,100,40)
        if a.panel:
            self.fb.fill(WHITE); self.buttons=[]
            self.badge('でんげん',13)
            value=a.battery.level
            self.text('でんち めやす',33)
            self.text('-- %' if value is None else '%d %%'%value,47)
            self.hp(32,60,56,value or 0,100)
            self.button('screen_sleep','スリープ',28,73,64,17)
            self.text('2タップでふっき',94)
            self.button('power_close','モドル',40,105,40,11)
        if a.save_pending: self.badge('ほぞんリトライ',12)
        upscale_mirror(self.buf,self.tx)
        self.lcd.set_window(0,0,239,239); self.lcd.dc.value(1); self.lcd.cs.value(0)
        self.lcd.spi.write(self.tx); self.lcd.cs.value(1)
