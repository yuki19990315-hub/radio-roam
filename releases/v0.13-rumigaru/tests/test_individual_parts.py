import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware'))
import world
from individual_parts import PartLibrary


class IndividualPartTests(unittest.TestCase):
    def setUp(self):self.library=PartLibrary(str(ROOT/'firmware/assets/modular_v1'))
    def pet(self,typ=0,stage=0):
        p=world.make_creature(world.digest_for('parts-test'))
        p.update(type=typ,evolution=stage,parts=[0]*8,uid='test')
        return p

    def test_all_576_pngs_have_individual_runtime_files(self):
        manifest=json.loads((ROOT/'art/parts/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest),576)
        self.assertEqual(len(set(i['runtime'] for i in manifest)),576)
        for item in manifest:
            self.assertTrue((ROOT/item['png']).is_file())
            p=self.pet(item['type'],item['stage']);slot=world.PARTS.index(item['slot'])
            p['parts'][slot]=(item['variant']-1)*(1 if item['slot']=='eyes' else 4)
            meta,data=self.library.load(p,item['slot'])
            self.assertEqual(len(data),meta['size'][0]*meta['size'][1])

    def test_part_gene_selects_its_own_file(self):
        p=self.pet();before=[self.library.load(p,n) for n in world.PARTS]
        for slot,name in enumerate(world.PARTS):
            q=world.clone(p);q['parts'][slot]=1 if name=='eyes' else 4
            self.assertEqual(self.library.variant(q,name),1)
            for other in world.PARTS:
                if other!=name:self.assertEqual(self.library.load(q,other),before[world.PARTS.index(other)])

    def test_every_eye_style_fits_every_head_and_body(self):
        for typ in range(6):
            for stage in range(3):
                for head in range(4):
                    for body in range(4):
                        for eye in range(4):
                            p=self.pet(typ,stage);p['parts'][0]=head*4;p['parts'][1]=body*4;p['parts'][6]=eye
                            hm,hd,hx,hy=self.library.positioned(p,'head')
                            em,ed,ex,ey=self.library.positioned(p,'eyes')
                            hw,hh=hm['size'];ew,eh=em['size']
                            for i,v in enumerate(ed):
                                if not v:continue
                                x=ex+i%ew-hx;y=ey+i//ew-hy
                                self.assertTrue(0<=x<hw and 0<=y<hh and hd[y*hw+x],(typ,stage,head,body,eye,x,y))

    def test_quadruped_body_has_separate_front_and_rear_support(self):
        for typ in (0,2):
            for stage in range(3):
                for variant in range(4):
                    p=self.pet(typ,stage);p['parts']=[variant*4]*8
                    body,_=self.library.load(p,'body')
                    w,h=body['size'];s=body['sockets']
                    self.assertGreater(w,h)
                    self.assertGreaterEqual(s['arms'][0]-s['legs'][0],10)
                    self.assertEqual(s['arms'][1],s['legs'][1])
                    self.assertGreater(s['arms'][1],s['head'][1])

    def test_fish_retains_basic_tail_when_optional_tail_is_absent(self):
        p=self.pet(3);p['parts']=[4,15,2,5,0,3,3,2]
        p['present']=[True,True,True,True,True,False,True,True]
        meta,data=self.library.load(p,'body')
        self.assertEqual(meta.get('native_rig'),'fish_v2')
        w,h=meta['size']
        self.assertTrue(any(data[y*w] for y in range(h)))
        head,_=self.library.load(p,'head')
        self.assertEqual(head.get('native_rig'),'fish_v2')

if __name__=='__main__':unittest.main()
