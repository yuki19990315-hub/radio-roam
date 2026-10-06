import sys,os,json,tempfile,unittest,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'firmware'))
from custom_assets import CustomParts
from phone_link import PhoneLink
from world_store import WorldStore
import world


class PhoneTests(unittest.TestCase):
    def setUp(self):
        self.old=os.getcwd(); self.tmp=tempfile.TemporaryDirectory(); os.chdir(self.tmp.name)
        self.custom=CustomParts(); self.state=world.initial(); world.choose_starter(self.state,0)
        self.state['pet']['fullness']=50
        self.app=SimpleNamespace(state=self.state,store=WorldStore(),battle=None,phase=None,
            display_asleep=False,screen=SimpleNamespace(art=SimpleNamespace(custom=self.custom,cache={},scaled_cache={})))
        self.phone=PhoneLink.__new__(PhoneLink); self.phone.app=self.app; self.phone.token='session'; self.phone.receipts=[]
        time.ticks_ms=lambda:100

    def tearDown(self):
        os.chdir(self.old); self.tmp.cleanup()

    def upload(self,**changes):
        data=dict(slot='head',name='テスト',frames=2,pixels='03'*4096+'04'*4096); data.update(changes)
        return self.custom.install(data)

    def test_upload_equipment_persists_and_removes_without_gene_changes(self):
        original=json.dumps(self.state); p=self.state['pet']; identity=self.upload()
        self.custom.equip(p,'head',identity)
        restored=CustomParts(); self.assertEqual(restored.read(p,'head',1),bytearray([4]*4096))
        self.assertEqual(restored.read(p,'head',2),bytearray([3]*4096))
        self.assertIsNone(restored.read(dict(p,evolution=1),'head',0))
        restored.equip(p,'head',None); self.assertIsNone(restored.read(p,'head',0))
        self.assertEqual(json.dumps(self.state),original)
        restored.equip(p,'head',identity); restored.delete(identity)
        self.assertIsNone(CustomParts().read(p,'head',0))

    def test_reject_invalid_upload_before_file_writes(self):
        for changes in ({'slot':'../../main.py'},{'frames':5},{'pixels':'zz'*8192},
                        {'pixels':'ff'*8192},{'pixels':'00'*8192},{'name':'x'*25}):
            with self.assertRaises(ValueError): self.upload(**changes)
        self.assertEqual(self.custom.data['items'],[])
        self.assertFalse(os.path.exists('custom_parts'))

    def test_auth_and_duplicate_action(self):
        body=json.dumps({'action':'feed','request_id':'one'}).encode()
        status,_,_=self.phone.dispatch('POST','/api/action',{},body)
        self.assertTrue(status.startswith('403')); self.assertEqual(self.app.state['pet']['fullness'],50)
        headers={'content-type':'application/json','x-roam-token':'session'}
        status,_,_=self.phone.dispatch('POST','/api/action',headers,body); self.assertTrue(status.startswith('200'))
        food=self.app.state['inventory']['food']; fullness=self.app.state['pet']['fullness']
        self.phone.dispatch('POST','/api/action',headers,body)
        self.assertEqual(self.app.state['inventory']['food'],food)
        self.assertEqual(WorldStore().load()['pet']['fullness'],fullness)
        self.app.battle=True
        status,_,_=self.phone.dispatch('POST','/api/action',headers,json.dumps({'action':'rest','request_id':'two'}).encode())
        self.assertTrue(status.startswith('400'))

    def test_unknown_monster_and_part_rejected(self):
        identity=self.upload()
        with self.assertRaises(ValueError): self.custom.equip(self.state['pet'],'tail',identity)
        with self.assertRaises(ValueError): self.phone.mutate('/api/parts/equip',{'uid':'missing','stage':0,'slot':'head','id':identity})

    def test_rename_roundtrip_and_reset_keeps_genes(self):
        p=self.app.state['pet'];uid=p['uid'];genes=p['genome']
        self.phone.mutate('/api/action',{'action':'rename','uid':uid,'stage':0,'nickname':'  そらまる  '})
        restored=WorldStore().load()
        self.assertTrue(world.valid(restored));self.assertEqual(world.display_name(restored['pet']),'そらまる')
        self.assertEqual(restored['pet']['genome'],genes)
        self.assertEqual(world.public_state(restored)['pet']['display_name'],'そらまる')
        self.phone.mutate('/api/action',{'action':'rename','uid':uid,'stage':0,'nickname':''})
        self.assertEqual(world.display_name(self.app.state['pet']),world.species_name(p))

    def test_rename_invalid_inputs_do_not_change_save(self):
        p=self.app.state['pet']
        for name in ('123456789','<script>','名前','a\nb',None):
            with self.assertRaises(ValueError):
                self.phone.mutate('/api/action',{'action':'rename','uid':p['uid'],'stage':0,'nickname':name})
        self.assertNotIn('nickname',self.app.state['pet'])

    def test_corrupt_part_metadata_and_missing_pixels_recover(self):
        identity=self.upload();p=self.state['pet'];self.custom.equip(p,'head',identity)
        self.custom.equip(p,'tail',None)
        with open('custom_parts/index.json','w') as f:f.write('{broken')
        restored=CustomParts();self.assertEqual(restored.selection(p)['head'],identity)
        with open('custom_parts/'+identity+'.idx','wb') as f:f.write(b'bad')
        self.assertIsNone(restored.read(p,'head',0))
        os.remove('custom_parts/'+identity+'.idx')
        self.assertIsNone(restored.read(p,'head',0))

    def test_phone_hatch_uses_stable_egg_id(self):
        child=world.assign_uid(self.app.state,world.make_creature(world.digest_for('egg')))
        self.app.state['eggs']=[{'child':child,'remaining':0}]
        self.phone.mutate('/api/action',{'action':'hatch','egg_uid':child['uid']})
        self.assertEqual(len(self.app.state['eggs']),0)
        self.assertTrue(any(p['uid']==child['uid'] for p in world.roster(WorldStore().load())))
        with self.assertRaises(ValueError):self.phone.mutate('/api/action',{'action':'hatch','egg_uid':child['uid']})

    def test_evolved_moves_work_and_sleeping_training_is_blocked(self):
        p=self.app.state['pet'];p['level']=20;world.evolve(self.app.state,p['uid'])
        enemy=world.make_creature(world.digest_for('opponent'))
        battle=world.Battle(self.app.state,enemy)
        self.assertTrue(world.move_unlocked(p,1));self.assertTrue(battle.act('hit',1))
        self.assertFalse(world.move_unlocked(p,-1));self.assertFalse(world.move_unlocked(p,4))
        self.app.state['sleeping']=True;self.app.state['elapsed']=100
        before=world.clone(p);world.care(self.app.state,'train')
        self.assertEqual(p,before)

if __name__=='__main__': unittest.main()
