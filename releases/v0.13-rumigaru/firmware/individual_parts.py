"""Independent image files with explicit parent attachment sockets."""
import json,os
from world import PARTS,visual_part_value
KINDS=('beast','bird','dragon','fish','humanoid','plant')


class PartLibrary:
    def __init__(self,root='assets/modular_v1'):
        try:os.stat(root)
        except OSError:
            if root!='assets/modular_v1':raise
            root='/assets/modular_v1'
        self.root=root;self.cache={}

    def variant(self,p,name):
        gene=visual_part_value(p,PARTS.index(name))
        return gene%4 if name=='eyes' else gene//4

    def load(self,p,name):
        stage=p.get('evolution',0);variant=self.variant(p,name)
        key=(p['type'],name,variant,stage)
        if key in self.cache:return self.cache[key]
        path='%s/%s/%s_%02d_%d.part'%(self.root,KINDS[p['type']],name,variant+1,stage)
        if p['type']==0:
            path='%s/../beast_v2/%s_%02d_%d.part'%(self.root,name,variant+1,stage)
        if p['type']==3:
            path='%s/../fish_v2/%s_%02d_%d.part'%(self.root,name,variant+1,stage)
            # Add independent concept-derived parts to four inherited slots.
            if (name,variant) in (('head',1),('body',3),('arms',0),('horns',0)):
                path='%s/../rumigaru/%s.part'%(self.root,name)
        with open(path,'rb') as f:
            if f.read(3)!=b'RP1':raise ValueError('Bad part header')
            size=f.read(2);length=size[0]|size[1]<<8
            if length>1024:raise ValueError('Bad part metadata')
            meta=json.loads(f.read(length));w,h=meta['size']
            if not(1<=w<=64 and 1<=h<=64):raise ValueError('Bad part dimensions')
            try:import deflate
            except ImportError:
                import zlib
                data=bytearray(zlib.decompress(f.read()))
            else:
                with deflate.DeflateIO(f,deflate.ZLIB) as stream:data=bytearray(stream.read(w*h+1))
            if len(data)!=w*h or any(v>11 for v in data):raise ValueError('Bad part pixels')
        from body_plan import fit
        if meta.get('native_rig') not in ('beast_v2','fish_v2'):meta,data=fit(p['type'],name,meta,data)
        if len(self.cache)>=32:self.cache.clear()
        self.cache[key]=(meta,data)
        return meta,data

    def positioned(self,p,name):
        meta,data=self.load(p,name);x,y=meta['origin'];w,h=meta['size']
        if name!='body':
            parent='head' if name in ('eyes','horns') else 'body'
            parent_meta,_=self.load(p,parent)
            _,_,px,py=self.positioned(p,parent)
            sx,sy=parent_meta['sockets'][name]
            sx+=px-parent_meta['origin'][0];sy+=py-parent_meta['origin'][1]
            x+=sx-meta['pivot'][0];y+=sy-meta['pivot'][1]
        x=max(0,min(64-w,x));y=max(2,min(64-h,y))
        return meta,data,x,y
