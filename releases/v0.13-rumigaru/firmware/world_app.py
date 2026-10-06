import os,time,gc
import world
from world_store import WorldStore
from world_screen import Screen
from pet_touch import Touch
from scanner import Scanner
from pet_motion import PHASE_MS


class App:
    def __init__(self):
        self.store=WorldStore(); self.state=self.store.load()
        self.screen=Screen(); self.touch=Touch(); self.scanner=Scanner()
        self.page='starter' if self.state['starter_options'] else 'home'
        self.list_offset=0; self.index=0
        self.notice=''; self.hatch_pet=None; self.happy=False; self.happy_at=0
        self.battle=None; self.phase=None; self.phase_at=0
        self.parent_a=None; self.parent_b=None
        self.fusion_seed=None; self.fusion_preview=None; self.fusion_lock=-1; self.signals=[]
        now=time.ticks_ms()
        self.last_scan=now; self.last_frame=now; self.clock_at=now; self.last_save=now
        self.save_pending=False; self.phone=None
        self.ble=None; self.ble_running=False; self.ble_at=now
        from power_control import Battery,WakeTaps
        self.battery=Battery(); self.battery_at=now
        self.display_asleep=False; self.panel=False; self.sleep_at=now
        self.wake_taps=WakeTaps()
        try:
            from encounters import Encounters
            self.ble=Encounters(int.from_bytes(os.urandom(4),'little'))
        except (ImportError,OSError) as exc: print('BLE unavailable',exc)

    def go(self,page):
        self.page=page; self.list_offset=0
        if page=='home': self.hatch_pet=None

    def tell(self,text):
        self.notice=text; self.go('notice')

    def save(self):
        try:
            saved=self.store.commit(self.state)
            self.state['seq']=saved['seq']; self.save_pending=False; self.last_save=time.ticks_ms()
        except OSError as exc:
            self.save_pending=True; self.last_save=time.ticks_ms(); print('SAVE RETRY',exc)

    def transaction(self,operation):
        try:
            state,result=self.store.transaction(self.state,operation)
            self.state=state; self.save_pending=False; self.last_save=time.ticks_ms()
            return True,result
        except (ValueError,OSError) as exc:
            self.tell(str(exc) if isinstance(exc,ValueError) else 'ほぞんできない')
            return False,None

    def stop_ble(self):
        if self.ble and self.ble_running:
            self.ble.stop(); self.ble_running=False

    def page_title(self):
        return {'menu':'メニュー','care':'おせわ','bag':'どうぐ','battlebag':'どうぐ',
                'eggs':'たまご','dungeons':'ダンジョン','habitats':'セイソクチ',
                'fusion_lock':'ヒキツグパーツ'}[self.page]

    def page_items(self):
        if self.page=='menu':
            return [('care','おせわ'),('roster','なかま'),('evolution','しんか'),
                    ('fusion','ごうせい'),('eggs','たまご'),
                    ('dungeons','ダンジョン'),('habitats','セイソクチ'),('dex','モンスターズカン'),
                    ('part_dex','パーツズカン'),('bag','どうぐ'),('practice','れんしゅう'),
                    ('peers','すれちがい'),('phone','スマホ')]
        if self.page=='care':
            return [('care_status','ようす'),('feed','ごはん'),('play','あそぶ'),('train','くんれん'),
                    ('rest','おきる' if self.state['sleeping'] else 'やすむ')]
        if self.page in ('bag','battlebag'):
            labels=(('potion','カイフク'),('scanner','スキャナ')) if self.page=='battlebag' else (('food','ごはん'),('potion','カイフク'),('scanner','スキャナ'),('incubator','ふかそうち'))
            return [('use_'+k,'%s %d'%(label,self.state['inventory'][k])) for k,label in labels]
        if self.page=='eggs':
            return [('egg:%d'%i,'たまご%d %d'%(i+1,e['remaining'])) for i,e in enumerate(self.state['eggs'])]
        if self.page=='dungeons':
            return [('dungeon:%d'%i,'%s %d/3'%(world.BIOMES[d['biome']],d['floor']+1))
                    for i,d in enumerate(self.state['dungeons']) if d['floor']<3]
        if self.page=='habitats':
            return [('home','%s %dカイ'%(world.BIOMES[h['biome']],h['visits']))
                    for h in self.state['habitats']]
        if self.page=='fusion_lock':
            labels=('オマカセ','アタマ','カラダ','ウデ','アシ','ツノ','シッポ','メ','ハネ')
            return [('lock:%d'%(i-1),label) for i,label in enumerate(labels)]
        return []

    def entries(self):
        if self.page=='dex': return self.state['dex']
        pets=world.roster(self.state)
        if self.page.startswith('parent'):
            pets=[p for p in pets if p['level']>=world.FUSION_LEVEL and (self.page!='parent_b' or p['uid']!=self.parent_a)]
        return pets

    def selected_pet(self):
        entries=self.entries()
        return entries[self.index%len(entries)] if entries else None

    def selected_starter(self):
        choices=self.state['starter_options']
        return choices[self.index%len(choices)] if choices else None

    def selected_signal(self):
        return self.signals[self.index%len(self.signals)] if self.signals else None

    def start_battle(self,p,practice=False,dungeon=None,signal_reward=None):
        if not self.state['pet'] or not self.state['pet']['hp']:
            self.tell('やすんでかいふく'); return
        self.stop_ble(); self.state['sleeping']=False
        self.battle=world.Battle(self.state,p,practice,dungeon,signal_reward)
        self.phase=None; self.go('battle')

    def explore(self):
        self.stop_ble(); self.go('search'); self.screen.draw(self,time.ticks_ms())
        try: rows=self.scanner.scan()
        except OSError:
            self.last_scan=time.ticks_ms(); self.tell('でんぱエラー'); return
        self.last_scan=time.ticks_ms(); self.signals=world.scan_signals(self.state,rows); self.index=0
        self.save()
        if self.signals: self.go('signals'); print('WORLD scan choices',len(self.signals))
        else: self.tell('べつのばしょへ' if rows else 'でんぱがない')

    def command(self,key):
        if not key: return
        if key=='power_close': self.panel=False; return
        if key=='screen_sleep':
            self.save()
            if self.save_pending: return
            self.stop_ble()
            if self.phone: self.phone.close(); self.phone=None; self.go('home')
            self.panel=False; self.display_asleep=True; self.sleep_at=time.ticks_ms()
            self.wake_taps.first=None
            self.screen.lcd.set_backlight(False)
            self.screen.lcd._cmd(0x28)
            self.screen.lcd._cmd(0x10)
            return
        if key in ('home','menu','care','care_status','bag','dungeons','habitats','part_dex','eggs','dex','roster','peers','battle','moves','battlebag','signals','dungeon_detail'):
            self.go(key)
            if key in ('dex','roster'): self.index=0
        elif key=='list_next': self.list_offset=(self.list_offset+1)%max(1,(len(self.page_items())+3)//4)
        elif key=='next': self.index+=1
        elif key=='starter_next': self.index=(self.index+1)%3
        elif key=='starter_prev': self.index=(self.index-1)%3
        elif key=='choose_starter':
            choice=self.index%3
            ok,result=self.transaction(lambda s:world.choose_starter(s,choice))
            if ok:
                self.index=0; self.hatch_pet=result; self.tell('キミにきめた！')
        elif key=='explore': self.explore()
        elif key.startswith('signal:'):
            index=int(key.split(':')[1])
            if 0<=index<len(self.signals):
                signal=self.signals[index]
                ok,result=self.transaction(lambda s:world.claim_signal(s,signal))
                if ok:
                    self.signals=[]; self.start_battle(result[0],signal_reward=result[1])
        elif key in ('feed','play','train','rest'):
            ok,message=self.transaction(lambda s:world.care(s,key))
            if ok:
                if key=='play': self.happy=True; self.happy_at=time.ticks_ms()
                if key=='rest': self.go('home')
                else: self.tell(message)
        elif key=='select':
            p=self.selected_pet()
            if p:
                ok,_=self.transaction(lambda s:world.switch(s,p['uid']))
                if ok: self.go('home')
        elif key=='stats': self.go('stats')
        elif key=='evolution': self.go('evolution')
        elif key=='evolve':
            uid=self.state['pet']['uid'] if self.state['pet'] else ''
            ok,result=self.transaction(lambda s:world.evolve(s,uid))
            if ok:
                self.hatch_pet=result; self.tell('%sへしんか！ レベル1'%world.evolution_name(result))
        elif key=='fusion':
            self.parent_a=None; self.parent_b=None; self.fusion_seed=None; self.fusion_preview=None
            self.fusion_lock=-1
            self.index=0; self.go('parent_a')
        elif key=='select_parent':
            p=self.selected_pet()
            if p:
                if self.page=='parent_a': self.parent_a=p['uid']; self.index=0; self.go('parent_b')
                else:
                    self.parent_b=p['uid']; self.index=0; self.go('fusion_lock')
        elif key.startswith('lock:'):
            self.fusion_lock=int(key.split(':')[1]); self.fusion_seed=os.urandom(32)
            self.fusion_preview=world.fusion_preview(self.state,self.parent_a,self.parent_b,
                                                     self.fusion_seed,self.fusion_lock)
            self.go('fusion_confirm')
        elif key=='fuse':
            seed=self.fusion_seed or os.urandom(32)
            ok,_=self.transaction(lambda s:world.fuse(s,self.parent_a,self.parent_b,seed,self.fusion_lock))
            if ok:
                self.fusion_seed=None; self.fusion_preview=None; self.tell('たまごがうまれた！')
        elif key.startswith('egg:'): self.index=int(key.split(':')[1]); self.go('egg_detail')
        elif key in ('hatch','incubate'):
            op=world.hatch if key=='hatch' else world.incubate
            ok,result=self.transaction(lambda s:op(s,self.index))
            if ok:
                if key=='hatch': self.hatch_pet=result; self.tell('うまれた！')
        elif key=='practice':
            level=self.state['pet']['level'] if self.state['pet'] else 1
            self.start_battle(world.make_creature(os.urandom(32),level),True)
        elif key.startswith('dungeon:'):
            self.index=int(key.split(':')[1]); self.go('dungeon_detail')
        elif key=='dungeon_enter':
            i=self.index; d=self.state['dungeons'][i]
            if d['floor']<3:
                self.state['biome']=d['biome']; self.start_battle(world.dungeon_enemy(d),dungeon=i)
        elif key=='finish':
            if self.phase is None:
                self.battle.settle(); reward=self.battle.reward_message
                self.save(); self.battle=None
                if reward: self.tell(reward)
                else: self.go('home')
        elif key.startswith('use_'):
            item=key[4:]
            if self.page=='battlebag': self.battle_action('item' if item=='potion' else 'scanner')
            elif item in ('food','potion'):
                ok,msg=self.transaction(lambda s:world.care(s,'feed' if item=='food' else 'potion'))
                if ok: self.tell(msg)
            elif item=='incubator': self.go('eggs')
            else: self.tell('バトルでつかう')
        elif key in ('scan','run') or key.startswith('move'):
            self.battle_action('hit' if key.startswith('move') else key,int(key[-1]) if key.startswith('move') else 0)
        elif key=='ble_toggle':
            self.state['ble']=not self.state['ble']; self.stop_ble(); self.save()
        elif key=='phone':
            self.stop_ble()
            try:
                from phone_link import PhoneLink
                self.phone=PhoneLink(self); self.go('phone')
            except OSError as exc: print('PHONE',exc); self.tell('れんけいエラー')
        elif key=='phone_close':
            if self.phone: self.phone.close(); self.phone=None
            self.go('home'); self.last_scan=time.ticks_ms()

    def battle_action(self,action,move=0):
        if self.battle and self.phase is None and self.battle.act(action,move):
            self.go('battle'); self.phase='attack' if action=='hit' else ('scan' if action=='scan' else 'item')
            self.phase_at=time.ticks_ms()

    def tick(self,now):
        seconds=time.ticks_diff(now,self.clock_at)//1000
        if seconds>0:
            world.advance(self.state,seconds); self.clock_at=time.ticks_add(self.clock_at,seconds*1000)
        if time.ticks_diff(now,self.battery_at)>=30000:
            self.battery.update(); self.battery_at=now
        if self.display_asleep:
            if time.ticks_diff(now,self.last_save)>=60000: self.save()
            return
        if self.phase and self.battle and time.ticks_diff(now,self.phase_at)>=PHASE_MS:
            if self.battle.await_reply:
                self.battle.reply(); self.phase='reply'; self.phase_at=now
            else:
                self.phase=None
                if self.battle.result:
                    self.battle.settle()
                    self.battle.message={'win':'かった！','caught':'なかまになった！','lost':'やすんでかいふく','escaped':'にげきった！'}[self.battle.result]
                    self.save()
        if self.happy and time.ticks_diff(now,self.happy_at)>1200: self.happy=False
        if time.ticks_diff(now,self.last_save)> (10000 if self.save_pending else 60000): self.save()
        if self.phone: self.phone.poll()
        # Wi-Fi scans are manual. network.WLAN.scan() is synchronous on the
        # target firmware, so a background auto-scan would unexpectedly freeze
        # the home screen.
        if self.ble:
            if self.ble_running and time.ticks_diff(now,self.ble_at)>5000: self.stop_ble()
            if self.ble_running:
                found=self.ble.poll()
                if found: self.state['peers']+=found; self.save()
            if self.state['ble'] and not self.phone and self.page=='home' and not self.ble_running and time.ticks_diff(now,self.ble_at)>20000:
                try:
                    self.ble.start(self.state['pet']['type'] if self.state['pet'] else 0,5000)
                    self.ble_running=True; self.ble_at=now
                except OSError as exc: print('BLE RETRY',exc); self.ble_at=now

    def run(self):
        self.screen.draw(self,time.ticks_ms()); print('WORLD_READY heap',gc.mem_free())
        while True:
            now=time.ticks_ms()
            point=self.touch.poll()
            if self.display_asleep:
                if point and self.wake_taps.tap(now,point[0],point[1],time.ticks_diff):
                    self.display_asleep=False
                    if self.phase: self.phase_at=time.ticks_add(self.phase_at,time.ticks_diff(now,self.sleep_at))
                    self.last_scan=now; self.ble_at=now
                    self.screen.lcd._cmd(0x11); time.sleep_ms(120); self.screen.lcd._cmd(0x29)
                    self.screen.draw(self,now); self.screen.lcd.set_backlight(True)
            elif self.touch.gesture=='swipe_down':
                self.panel=True; self.battery.update()
            elif point: self.command(self.screen.hit(*point))
            self.tick(now)
            if not self.display_asleep and time.ticks_diff(now,self.last_frame)>=80:
                self.screen.draw(self,now); self.last_frame=now
            time.sleep_ms(20)


def run():
    print('Radio Roam WORLD v0.13 Rumigaru boot')
    App().run()
