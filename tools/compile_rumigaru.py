"""Convert separate generated PNG assets to indexed, socketed device assets.

Only technical alpha trimming, size normalization and palette quantization.
Each source is a separately generated part, never a slice of a full monster.
"""
from pathlib import Path
import sys,json,struct,zlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'releases/v0.13-rumigaru'
sys.path.insert(0,str(RELEASE/'firmware'))
from fish_palette import colors
PAL=colors(7)
SPECS={
 'head':('魚頭_ルミガル',(28,27),(30,25),(35,35),{'eyes':[45,34],'horns':[40,28]}),
 'body':('魚体_ルミガル',(31,23),(5,27),(25,36),{'head':[35,35],'arms':[29,38],'legs':[28,43],'tail':[14,36],'wings':[28,29]}),
 'arms':('魚ヒレ_ルミガル',(16,12),(20,39),(29,38),{}),
 'horns':('魚角_ルミガル',(18,17),(38,12),(40,28),{}),
}
OUT=RELEASE/'firmware/assets/rumigaru';OUT.mkdir(parents=True,exist_ok=True)
ART=RELEASE/'art/parts/魚';ART.mkdir(parents=True,exist_ok=True)
for slot,(name,size,origin,pivot,sockets) in SPECS.items():
    source=Image.open(ROOT/'art/original-monsters-20260926/parts-source'/(name+'.png')).convert('RGBA')
    # Ignore nearly transparent antialias pixels when computing the asset bounds.
    bbox=source.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
    im=source.crop(bbox).resize(size,Image.Resampling.NEAREST)
    values=[]
    for r,g,b,a in im.getdata():
        values.append(0 if a<128 else min(range(1,12),key=lambda i:sum((x-y)**2 for x,y in zip((r,g,b),PAL[i]))))
    data=bytes(values)
    meta={'size':list(size),'origin':list(origin),'pivot':list(pivot),'sockets':sockets,'native_rig':'fish_v2'}
    header=json.dumps(meta,separators=(',',':')).encode()
    (OUT/(slot+'.part')).write_bytes(b'RP1'+struct.pack('<H',len(header))+header+zlib.compress(data,9))
    indexed=Image.new('RGBA',size);indexed.putdata([PAL[i]+(255 if i else 0,) for i in values])
    indexed.save(ART/(name+'.png'))
    (ART/(name+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('4 independent Rumigaru parts compiled')
