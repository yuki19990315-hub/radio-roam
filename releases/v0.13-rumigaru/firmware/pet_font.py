import json
import framebuf


class JapaneseFont:
    def __init__(self):
        with open('assets/japanese.json') as f:
            data=json.load(f)
        self.glyphs={ch:framebuf.FrameBuffer(bytearray.fromhex(bits),8,8,framebuf.MONO_HLSB)
                     for ch,bits in data.items()}
        self.palette=framebuf.FrameBuffer(bytearray(4),2,1,framebuf.RGB565)

    def draw(self, target, text, x, y, color):
        self.palette.pixel(1,0,color)
        for ch in text:
            glyph=self.glyphs.get(ch,self.glyphs['?'])
            target.blit(glyph,x,y,0,self.palette)
            x+=8
