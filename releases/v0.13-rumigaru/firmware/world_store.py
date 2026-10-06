import json,os
import world
from storage import Store


class WorldStore:
    def __init__(self,prefix='roam_world_v6'):
        self.store=Store(prefix,world.valid,world.initial)
        self.prefix=prefix

    def legacy_v3(self):
        candidates=[]
        for i in (0,1):
            try:
                with open('roam_world_v3%d.json'%i) as f: old=json.load(f)
                if old.get('version')==3:
                    state=world.migrate_v3(old)
                    if world.valid(state): candidates.append(state)
            except (OSError,ValueError,TypeError,AttributeError):
                pass
        return max(candidates,key=lambda s:s['seq']) if candidates else None

    def legacy_v4(self):
        candidates=[]
        for i in (0,1):
            try:
                with open('roam_world_v4%d.json'%i) as f: old=json.load(f)
                if old.get('version')==4:
                    state=world.migrate_v4(old)
                    if world.valid(state): candidates.append(state)
            except (OSError,ValueError,TypeError,AttributeError):
                pass
        return max(candidates,key=lambda s:s['seq']) if candidates else None

    def legacy_v5(self):
        candidates=[]
        for i in (0,1):
            try:
                with open('roam_world_v5%d.json'%i) as f: old=json.load(f)
                if old.get('version')==5:
                    state=world.migrate_v5(old)
                    if world.valid(state): candidates.append(state)
            except (OSError,ValueError,TypeError,AttributeError):
                pass
        return max(candidates,key=lambda s:s['seq']) if candidates else None

    def load(self):
        exists=any(self.prefix+str(i)+'.json' in os.listdir() for i in (0,1))
        if exists: return self.store.load()
        state=self.legacy_v5() or self.legacy_v4() or self.legacy_v3()
        if state is not None:
            state['seq']+=1
            self.store.save(state)
            return state
        old_exists=any('roam_pet_v2%d.json'%i in os.listdir() for i in (0,1))
        if not old_exists: return world.initial()
        from pet_game import initial,valid
        old=Store('roam_pet_v2',valid,initial).load()
        state=world.migrate(old)
        state['seq']=1
        self.store.save(state)
        return state

    def commit(self,state):
        candidate=world.clone(state)
        candidate['seq']+=1
        if not world.valid(candidate): raise ValueError('Invalid v6 state')
        self.store.save(candidate)
        return candidate

    def transaction(self,state,operation):
        candidate=world.clone(state)
        result=operation(candidate)
        return self.commit(candidate),result
