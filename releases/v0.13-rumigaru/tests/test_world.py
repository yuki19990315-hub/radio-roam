import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware'))
import gene_schema,pet_game,wifi_world,world
from world_store import WorldStore


class WorldTests(unittest.TestCase):
    def started(self,index=0):
        state=world.initial(); world.choose_starter(state,index); return state

    def parents(self):
        state=self.started(); state['pet']['level']=20
        raw=gene_schema.encode_v2(world.digest_for('parent-b'),3,list(range(8)),7,[True]*8,3,4,5,6)
        pet=world.assign_uid(state,world.make_creature(raw,20)); state['caught'].append(pet); world.record(state,pet)
        return state,state['pet']['uid'],pet['uid']

    def rows(self,count=6,prefix='net',start=0,rssi=-40):
        return [((prefix+str(i//2)).encode(),bytes((2,4,6,8,(start+i)//256,(start+i)%256)),
                 1+i%11,rssi-i,3,False) for i in range(count)]

    def test_initial_starters_and_roles(self):
        state=world.initial(); self.assertTrue(world.valid(state)); self.assertEqual(state['version'],6)
        self.assertEqual([p['starter_role'] for p in state['starter_options']],['スピード','パワー','サポート'])
        chosen=world.choose_starter(state,2)
        self.assertEqual((chosen['type'],chosen['evolution'],chosen['level']),(5,0,1))
        self.assertEqual(state['starter_options'],[]); self.assertTrue(world.valid(state))

    def test_gene_v2_exact_mapping_and_balanced_types(self):
        parts=[15,0,12,3,9,6,1,14]; present=[True,True,True,True,False,True,True,False]
        raw=gene_schema.encode_v2(bytes(range(32)),4,parts,13,present,2,11,207,7,9)
        decoded=gene_schema.decode(raw)
        self.assertEqual(decoded['schema_version'],2); self.assertEqual(decoded['type'],4)
        self.assertEqual(decoded['parts'],parts); self.assertEqual(decoded['present'],present)
        self.assertEqual((decoded['palette'],decoded['personality'],decoded['temperament']),(13,2,11))
        counts=[sum(gene_schema.decode(bytes((roll,))+bytes(31))['type']==kind for roll in range(256)) for kind in range(6)]
        self.assertLessEqual(max(counts)-min(counts),1)

    def test_gene_v1_remains_readable(self):
        raw=bytes([0x23,0x45,0x67,0x89,0xab,0xcd,0xef,0x12,0x34,0x56,0x78,0x9a,0xbc,0xde]+[0]*18)
        decoded=gene_schema.decode(raw,1)
        self.assertEqual(decoded['parts'],[3,4,5,6,7,8,9,10]); self.assertEqual(decoded['schema_version'],1)
        pet=world.make_creature(raw,version=1); pet['uid']='legacy'; self.assertTrue(world.valid_pet(pet))

    def test_versioned_layout_and_documentation(self):
        self.assertTrue(gene_schema.validate_layout(gene_schema.FIELD_LAYOUT_V1))
        self.assertTrue(gene_schema.validate_layout(gene_schema.FIELD_LAYOUT_V2))
        self.assertEqual(gene_schema.RESERVED_BITS_V2,184)
        design=json.loads((ROOT/'data/game_design.json').read_text())
        documented=[(f['name'],f['offset'],f['bits']) for f in design['gene']['fields'] if f['name']!='reserved_for_future']
        self.assertEqual(documented,list(gene_schema.FIELD_LAYOUT_V2))

    def test_part_stats_are_explicit_and_non_monotonic(self):
        raw_a=gene_schema.encode_v2(bytes(32),0,[0]*8,0,[True]*8)
        raw_b=gene_schema.encode_v2(bytes(32),0,[15]*8,0,[True]*8)
        a,b=world.make_creature(raw_a),world.make_creature(raw_b)
        self.assertNotEqual(world.stats(a),world.stats(b))
        self.assertFalse(all(world.stats(a)[key]<=world.stats(b)[key] for key in ('attack','defense','special','speed')))

    def test_absent_tail_uses_body_move(self):
        raw=gene_schema.encode_v2(bytes(32),0,[1,7,2,3,4,5,6,7],0,
                                  [True,True,True,True,False,False,True,False])
        pet=world.make_creature(raw)
        self.assertEqual(world.moves(pet)[3],world.BODY_MOVES[7%4])

    def test_evolution_resets_level_but_keeps_mastery_and_moves(self):
        state=self.started(2); pet=state['pet']; pet['level']=20; pet['xp']=239; pet['hp']=1
        world.evolve(state,pet['uid'])
        self.assertEqual((pet['evolution'],pet['mastery'],pet['level'],pet['xp']),(1,1,1,0))
        self.assertEqual(pet['hp'],world.max_hp(pet)); self.assertTrue(world.move_unlocked(pet,1))
        pet['level']=20; world.evolve(state,pet['uid'])
        self.assertEqual((pet['evolution'],pet['mastery'],pet['level']),(2,2,1))
        self.assertTrue(world.move_unlocked(pet,2)); self.assertTrue(world.valid(state))

    def test_growth_selects_evolution_route_and_changes_route_markings(self):
        state=self.started(); pet=state['pet']; pet['level']=20
        pet['growth'].update({'battle':2,'explore':9,'care':1,'anomaly':0})
        before=[world.visual_part_value(pet,i) for i in range(8)]
        world.evolve(state,pet['uid'])
        self.assertEqual(pet['evolution_paths'],[1])
        self.assertEqual(world.evolution_route_name(pet),'タンサク')
        self.assertNotEqual(before,[world.visual_part_value(pet,i) for i in range(8)])
        self.assertEqual(pet['growth'],{'battle':0,'explore':0,'care':0,'anomaly':0})

    def test_fusion_preview_matches_result_and_inherits_traits(self):
        state,a,b=self.parents(); seed=b'fixed-fusion-seed'
        preview=world.fusion_preview(state,a,b,seed); parents=world.clone(world.roster(state))
        child=world.fuse(state,a,b,seed)
        for key in ('genome','parts','present','palette','type','traits'):
            self.assertEqual(child[key],preview[key])
        self.assertEqual(child['generation'],2); self.assertEqual(child['parents'],[a,b])
        self.assertLessEqual(sum(child['parts'][i] not in [p['parts'][i] for p in parents] for i in range(8)),1)
        self.assertTrue(world.valid(state))

    def test_fusion_can_lock_one_parent_part(self):
        state,a,b=self.parents(); parent=world.get_pet(state,a); locked=5
        preview=world.fusion_preview(state,a,b,b'lock-test',locked)
        self.assertEqual(preview['parts'][locked],parent['parts'][locked])
        self.assertEqual(preview['present'][locked],parent['present'][locked])
        child=world.fuse(state,a,b,b'lock-test',locked)
        self.assertEqual(child['parts'][locked],parent['parts'][locked])

    def test_scan_offers_three_monsters_and_city_environment(self):
        state=self.started(); signals=world.scan_signals(state,self.rows(25))
        self.assertEqual(len(signals),3); self.assertEqual(state['environment']['biome'],7)
        self.assertEqual(state['environment']['clusters'],12)
        self.assertTrue(all(signal['pet']['gene_version']==2 for signal in signals))
        self.assertTrue(all(signal['reward']['kind'] in ('none','experience','item','dungeon') for signal in signals))
        self.assertTrue(world.valid(state))

    def test_wifi_habitat_is_stable_and_creates_fixed_dungeon(self):
        first=self.started(); second=self.started(); rows=self.rows(1,prefix='home')
        one=world.scan_signals(first,rows)[0]; two=world.scan_signals(second,rows)[0]
        self.assertEqual(one['habitat'],two['habitat'])
        world.claim_signal(first,one)
        self.assertEqual(first['habitats'][0]['id'],one['habitat']['id'])
        self.assertEqual(first['dungeons'][0]['seed'],one['habitat']['dungeon_seed'])
        self.assertTrue(world.valid(first))

    def test_part_dex_uses_compact_catalog_bits(self):
        state=self.started(); self.assertEqual(world.part_dex_count(state),8)
        state['pet']['level']=20; world.evolve(state,state['pet']['uid'])
        self.assertEqual(world.part_dex_count(state),16)
        self.assertEqual(len(state['part_dex']),world.PART_DEX_HEX_LENGTH)

    def test_environment_change_creates_storm(self):
        state=self.started(); world.scan_signals(state,self.rows(6,'old',0))
        world.scan_signals(state,self.rows(6,'new',100))
        self.assertEqual(state['environment']['change'],100); self.assertEqual(state['biome'],8)

    def test_signal_cooldown_survives_state_clone(self):
        state=self.started(); rows=self.rows(1)
        signal=world.scan_signals(state,rows)[0]; world.claim_signal(state,signal)
        restarted=world.clone(state)
        for _ in range(wifi_world.COOLDOWN_SCANS-1): self.assertEqual(world.scan_signals(restarted,rows),[])
        self.assertEqual(len(world.scan_signals(restarted,rows)),1); self.assertTrue(world.valid(restarted))

    def test_each_signal_always_starts_with_a_monster(self):
        state=self.started(); signals=world.scan_signals(state,self.rows(12))
        for signal in signals:
            pet,reward=world.claim_signal(state,signal)
            battle=world.Battle(state,pet,signal_reward=reward)
            self.assertIsNotNone(battle.enemy); self.assertEqual(len(battle.enemy['parts']),8)

    def test_all_secondary_rewards_apply_after_success(self):
        state=self.started(); environment=bytes(range(32)); monster=bytes(reversed(range(32)))
        found={}
        for serial in range(1,2000):
            reward=wifi_world.event_reward(environment,monster,serial); found.setdefault(reward['kind'],reward)
            if len(found)==4: break
        self.assertEqual(set(found),{'none','experience','item','dungeon'})
        for reward in found.values(): world.apply_signal_reward(state,reward)
        self.assertTrue(world.valid(state)); self.assertEqual(len(state['dungeons']),1)

    def test_dungeon_summary_boss_and_rewards(self):
        state=self.started(); reward={'kind':'dungeon','seed':'ab'*32,'theme':10,'layout':11,'reward':2,'difficulty':3}
        world.apply_signal_reward(state,reward); dungeon=state['dungeons'][0]; dungeon['floor']=2
        self.assertEqual(world.dungeon_summary(dungeon),{'theme':'ホネ','layout':'ネッコ','reward':'ゴハン','difficulty':3})
        pet=world.dungeon_enemy(dungeon); self.assertTrue(pet['boss']); self.assertTrue(all(pet['present']))
        rebuilt=world.make_creature(bytes.fromhex(pet['genome']),version=pet['gene_version'])
        self.assertEqual(pet['parts'],rebuilt['parts'])
        battle=world.Battle(state,pet,dungeon=0); battle.result='win'; battle.settle(); battle.settle()
        self.assertEqual(dungeon['floor'],3); self.assertTrue(world.valid(state))

    def test_capture_and_reward_settle_only_once(self):
        state=self.started(); signal=world.scan_signals(state,self.rows(1))[0]
        pet,reward=world.claim_signal(state,signal); battle=world.Battle(state,pet,signal_reward=reward)
        battle.result='caught'; battle.settle(); snapshot=world.clone(state); battle.settle()
        self.assertEqual(state,snapshot); self.assertEqual(len(state['caught']),1); self.assertTrue(world.valid(state))

    def test_public_state_removes_full_hashes(self):
        state=self.started(); signal=world.scan_signals(state,self.rows(1))[0]
        reward={'kind':'dungeon','seed':'cd'*32,'theme':0,'layout':0,'reward':0,'difficulty':1}
        world.apply_signal_reward(state,reward); public=world.public_state(state); text=json.dumps(public)
        self.assertNotIn('genome',text); self.assertNotIn('"seed"',text)
        self.assertIn('gene_id',text); self.assertIn('dungeon_id',text)

    def test_v4_save_migration_and_slot_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            current=os.getcwd(); os.chdir(temp)
            try:
                state=self.started(); old=world.clone(state); old['version']=4
                for key in ('scan_serial','signal_history','last_scan_ids','environment'): old.pop(key)
                for pet in world.roster(old)+old['dex']: pet.pop('present'); pet.pop('mastery'); pet['traits'].pop('combat')
                Path('roam_world_v40.json').write_text(json.dumps(old))
                store=WorldStore(); loaded=store.load(); self.assertEqual(loaded['version'],6); self.assertTrue(world.valid(loaded))
                before=store.commit(loaded); original=store.store.save
                store.store.save=lambda state: (_ for _ in ()).throw(OSError('full'))
                with self.assertRaises(OSError): store.transaction(before,lambda state:world.care(state,'play'))
                store.store.save=original; self.assertEqual(store.load(),before)
                new,_=store.transaction(before,lambda state:world.care(state,'play'))
                Path('roam_world_v6%d.json'%(new['seq']%2)).write_text('{broken')
                self.assertEqual(store.load(),before)
            finally: os.chdir(current)

    def test_v5_save_migrates_without_losing_roster(self):
        with tempfile.TemporaryDirectory() as temp:
            current=os.getcwd(); os.chdir(temp)
            try:
                old=self.started(); old['version']=5
                for key in ('world_event','habitats','part_dex'): old.pop(key)
                for pet in world.roster(old)+old['dex']:
                    for key in ('growth','evolution_paths','memories'): pet.pop(key,None)
                Path('roam_world_v50.json').write_text(json.dumps(old))
                loaded=WorldStore().load()
                self.assertEqual(loaded['version'],6)
                self.assertEqual(len(world.roster(loaded)),1)
                self.assertEqual(world.part_dex_count(loaded),8)
                self.assertTrue(world.valid(loaded))
            finally: os.chdir(current)

    def test_asset_catalog_has_2304_exact_parts(self):
        meta=json.loads((ROOT/'tests/fixtures/legacy_parts/parts.json').read_text()); blob=(ROOT/'tests/fixtures/legacy_parts/parts.idx').read_bytes()
        self.assertEqual(meta['version'],5); self.assertFalse(meta['runtime_scaling']); self.assertEqual(len(meta['catalog']),2304)
        self.assertLess(len(blob),1500000)
        self.assertEqual((ROOT/'tests/fixtures/legacy_parts/parts.cat').stat().st_size,2304*8)
        for typ in range(6):
            for value in range(16):
                for stage in range(3):
                    for name in world.PARTS:
                        entry=meta['catalog']['%d:%d:%d:%s'%(typ,value,stage,name)]
                        offset,width,height,x,y=entry
                        self.assertLessEqual(x+width,64); self.assertLessEqual(y+height,64)
                        self.assertLessEqual(offset+width*height,len(blob))

    def test_each_micro_variant_has_distinct_pixels(self):
        meta=json.loads((ROOT/'tests/fixtures/legacy_parts/parts.json').read_text()); blob=(ROOT/'tests/fixtures/legacy_parts/parts.idx').read_bytes()
        for typ in range(6):
            for family in range(4):
                for stage in range(3):
                    for name in world.PARTS:
                        hashes=[]
                        for variant in range(4):
                            entry=meta['catalog']['%d:%d:%d:%s'%(typ,family*4+variant,stage,name)]
                            offset,width,height,_,_=entry; hashes.append(hashlib.sha256(blob[offset:offset+width*height]).digest())
                        self.assertEqual(len(set(hashes)),4,(typ,family,stage,name))


if __name__=='__main__': unittest.main()
