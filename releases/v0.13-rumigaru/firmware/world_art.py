"""Exact modular semantic-colour renderer for 64x64 monsters."""
import framebuf
from world import PARTS,visual_part_value
from pet_screen import rgb
from part_catalog import SEMANTIC_PALETTES


class Art:
    def __init__(self):
        from individual_parts import PartLibrary
        self.library=PartLibrary()
        self.palettes=[]
        for colors in SEMANTIC_PALETTES:
            palette=framebuf.FrameBuffer(bytearray(512),256,1,framebuf.RGB565)
            for index,(red,green,blue) in enumerate(colors):
                palette.pixel(index,0,rgb(red,green,blue))
            self.palettes.append(palette)
        from beast_palette import colors as beast_colors
        self.beast_palettes=[]
        for n in range(len(SEMANTIC_PALETTES)):
            palette=framebuf.FrameBuffer(bytearray(512),256,1,framebuf.RGB565)
            for index,(red,green,blue) in enumerate(beast_colors(n)):
                palette.pixel(index,0,rgb(red,green,blue))
            self.beast_palettes.append(palette)
        from fish_palette import colors as fish_colors
        self.fish_palettes=[]
        for n in range(3):
            palette=framebuf.FrameBuffer(bytearray(512),256,1,framebuf.RGB565)
            for index,(red,green,blue) in enumerate(fish_colors(n)):
                palette.pixel(index,0,rgb(red,green,blue))
            self.fish_palettes.append(palette)
        self.cache={}; self.scaled_cache={}; self.ink=1
        from custom_assets import CustomParts
        self.custom=CustomParts()

    def palette_for(self,p):
        palettes=self.fish_palettes if p['type']==3 else self.beast_palettes if p['type']==0 else self.palettes
        return palettes[p.get('palette',0)%len(palettes)]

    def rgb_palette_for(self,p):
        if p['type']==3:
            from fish_palette import colors
            return [list(color) for color in colors(p.get('palette',0))]
        if p['type']==0:
            from beast_palette import colors
            return [list(color) for color in colors(p.get('palette',0))]
        return [list(color) for color in SEMANTIC_PALETTES[p.get('palette',0)%len(SEMANTIC_PALETTES)]]

    def _part(self,p,name,stage):
        meta,data,x,y=self.library.positioned(p,name)
        w,h=meta['size']
        return data,(0,w,h,x,y),framebuf.FrameBuffer(data,w,h,framebuf.GS8)

    def order(self,p):
        return ('wings','tail','legs','body','arms','horns','head','eyes')

    def compose(self,p,frame=0,only=None):
        stage=p.get('evolution',0)
        present=tuple(p.get('present',[True]*8))
        key=(p['type'],tuple(p['parts']),present,stage,tuple(p.get('evolution_paths',())),frame,
             self.custom.key(p),self.custom.data['revision'],only)
        if key in self.cache: return self.cache[key]
        buf=bytearray(4096); fb=framebuf.FrameBuffer(buf,64,64,framebuf.GS8)
        order=self.order(p)
        for name in order:
            if only is not None and name not in only: continue
            index=PARTS.index(name)
            custom=self.custom.read(p,name,frame)
            if custom is not None:
                fb.blit(framebuf.FrameBuffer(custom,64,64,framebuf.GS8),0,0,0)
                continue
            if not present[index]: continue
            part_data,entry,source=self._part(p,name,stage)
            _,w,h,x,y=entry
            if p['type']==3:
                # Swim as one continuous body; do not detach the face from it.
                if frame in (1,3,6):y-=1
                elif frame==4:x+=3
                elif frame==7:y+=2
            elif p['type']==0 and frame==7:
                # Dedicated resting layout: paws tucked below a lowered body,
                # face resting at chest height rather than sleeping upright.
                if name in ('arms','legs'):
                    part_data=part_data[(h-4)*w:];h=4;y=49
                    source=framebuf.FrameBuffer(part_data,w,h,framebuf.GS8)
                elif name in ('head','eyes','horns'):y+=13
                else:y+=6
            elif frame==1 and name not in ('legs','tail'): y-=1
            elif frame==3 and name in ('tail','wings'): y-=2
            elif frame==4 and name in ('head','arms','horns','eyes'): x+=2; y-=1
            elif frame==5 and name not in ('legs','tail'): x-=1
            elif frame==6: y-=2
            elif frame==7 and name in ('head','eyes','horns'): y+=2
            if name=='eyes' and frame in (2,5,7):
                fb.hline(x,y+h//2,w,self.ink)
            else: fb.blit(source,x,y,0)
        if len(self.cache)>=24: self.cache.clear()
        self.cache[key]=(buf,fb); return buf,fb

    def draw(self,target,p,frame,x,y,size=64,mirror=False):
        buf,source=self.compose(p,frame); palette=self.palette_for(p)
        if size==64 and not mirror:
            target.blit(source,x,y,0,palette); return
        key=(p['type'],tuple(p['parts']),tuple(p.get('present',[True]*8)),
             p.get('evolution',0),tuple(p.get('evolution_paths',())),frame,size,mirror,
             self.custom.key(p),self.custom.data['revision'])
        if key not in self.scaled_cache:
            data=bytearray(size*size); scaled=framebuf.FrameBuffer(data,size,size,framebuf.GS8)
            for yy in range(size):
                for xx in range(size):
                    source_x=(size-1-xx)*64//size if mirror else xx*64//size
                    scaled.pixel(xx,yy,source.pixel(source_x,yy*64//size))
            if len(self.scaled_cache)>=32: self.scaled_cache.clear()
            self.scaled_cache[key]=(data,scaled)
        target.blit(self.scaled_cache[key][1],x,y,0,palette)

    def export(self,p):
        from world import hexed
        data,_=self.compose(p)
        return {'width':64,'height':64,'pixels':hexed(data),'palette':self.rgb_palette_for(p)}

    def layers(self,p,slot):
        from world import hexed
        order=self.order(p)
        i=order.index(slot)
        return {'behind':hexed(self.compose(p,0,order[:i])[0]),
                'front':hexed(self.compose(p,0,order[i+1:])[0]),'palette':self.rgb_palette_for(p)}
