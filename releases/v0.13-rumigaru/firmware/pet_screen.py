import json
import framebuf
import micropython
import time
from lcd_driver import Display
from pet_game import max_hp, MOVE_LEVELS
from pet_language import japanese
from pet_font import JapaneseFont
from pet_motion import leap


def rgb(r, g, b):
    c = ((r & 248)<<8) | ((g & 252)<<3) | (b>>3)
    return ((c & 255)<<8) | (c>>8)


@micropython.viper
def upscale_mirror(source, target):
    src = ptr16(source)
    dst = ptr16(target)
    for y in range(120):
        for x in range(120):
            value = src[y*120+x]
            at = y*480 + 238-x*2
            dst[at] = value
            dst[at+1] = value
            dst[at+240] = value
            dst[at+241] = value


INK = rgb(29, 48, 57)
WHITE = rgb(250, 250, 235)
TEAL = rgb(20, 130, 122)
RED = rgb(189, 67, 69)


class Screen:
    def __init__(self,load_legacy_art=True):
        self.lcd = Display()
        with open('assets/grassland.rgb', 'rb') as f:
            self.background = f.read()
        self.atlas = bytearray()
        if load_legacy_art:
            with open('assets/dragon.idx', 'rb') as f: self.atlas = bytearray(f.read())
        assert len(self.background) == 28800 and (not load_legacy_art or len(self.atlas) == 32768)
        self.buf = bytearray(self.background)
        self.fb = framebuf.FrameBuffer(self.buf, 120, 120, framebuf.RGB565)
        self.tx = bytearray(240*240*2)
        self.frames = []
        self.font = JapaneseFont()
        self.small = []
        self.mirrored = []
        for i in range(8 if load_legacy_art else 0):
            data = memoryview(self.atlas)[i*4096:(i+1)*4096]
            self.frames.append(framebuf.FrameBuffer(data, 64, 64, framebuf.GS8))
            small, mirror = bytearray(36*36), bytearray(36*36)
            for y in range(36):
                for x in range(36):
                    value = data[(y*64//36)*64+x*64//36]
                    small[y*36+x] = value
                    mirror[y*36+35-x] = value
            self.small.append(framebuf.FrameBuffer(small, 36, 36, framebuf.GS8))
            self.mirrored.append(framebuf.FrameBuffer(mirror, 36, 36, framebuf.GS8))
        self.palettes = []
        if load_legacy_art:
            with open('assets/palette.json') as f: colors = json.load(f)
            for variant in range(3):
                p = framebuf.FrameBuffer(bytearray(512), 256, 1, framebuf.RGB565)
                for i, (r,g,b) in enumerate(colors):
                    if variant and g > r*1.3 and b > r*1.3:
                        if variant == 1: r,g,b = g, int(r*.8), int(b*.65)
                        else: r,g,b = min(245, int(g*.7+75)), min(230, int(b*.65+75)), min(250, int(g*.8+65))
                    p.pixel(i, 0, rgb(r,g,b))
                self.palettes.append(p)
        self.buttons = []

    def text(self, value, y, color=INK):
        value = japanese(value)
        self.font.draw(self.fb, value, (120-len(value)*8)//2, y, color)

    def badge(self, value, y):
        value = japanese(value)
        width = len(value)*8+8
        self.fb.fill_rect((120-width)//2, y-2, width, 12, WHITE)
        self.text(value, y)

    def button(self, key, label, x, y, w=38, h=12, active=True):
        label = japanese(label)
        self.fb.fill_rect(x, y, w, h, TEAL if active else INK)
        self.font.draw(self.fb, label, x+(w-len(label)*8)//2, y+2, WHITE)
        if active:
            self.buttons.append((key, x, y, w, h))

    def hit(self, x, y):
        for key, bx, by, w, h in self.buttons:
            if bx <= x < bx+w and by <= y < by+h:
                return key
        return None

    def hp(self, x, y, w, value, total):
        self.fb.fill_rect(x, y, w, 5, INK)
        n = (w-2)*value//total
        self.fb.fill_rect(x+1, y+1, n, 3, TEAL if value*3>total else RED)

    def sprite(self, frame, palette, x, y, small=False, mirror=False):
        source = (self.mirrored if mirror else self.small)[frame] if small else self.frames[frame]
        self.fb.blit(source, x, y, 0, self.palettes[palette])

    def draw(self, app, now):
        self.buf[:] = self.background
        self.buttons = []
        state, pet = app.state, app.state['pet']
        cycle = (now//250) % 16
        idle = 2 if cycle == 10 else (0,1,0,3)[cycle%4]
        page = app.page
        if page == 'home':
            self.badge('AURI', 10)
            self.text('LV %02d' % pet['level'], 24)
            frame = 7 if app.sleeping else (6 if app.happy else idle)
            self.sprite(frame, pet['palette'], 28, 27)
            self.hp(36, 87, 48, pet['hp'], max_hp(pet))
            self.button('explore', 'GO', 22, 98, 34)
            self.button('menu', 'MENU', 60, 98, 40)
            self.buttons.append(('pet', 28, 36, 64, 47))
        elif page == 'menu':
            self.badge('MENU', 10)
            self.text('HP%02d/%02d' % (pet['hp'], max_hp(pet)), 23)
            self.button('rest', 'REST', 24, 36, 72, 15)
            self.button('practice', 'TRAIN', 24, 54, 72, 15)
            self.button('dex', 'DEX', 24, 72, 72, 15)
            self.button('home', 'BACK', 35, 93, 50, 14)
        elif page == 'dex':
            self.badge('DEX %02d' % len(state['caught']), 12)
            if state['caught']:
                p = state['caught'][app.dex_index % len(state['caught'])]
                self.sprite(idle, p['palette'], 28, 25)
                self.text('レベル%02d いろ%d' % (p['level'], p['palette']+1), 86)
                self.button('next', 'NEXT', 20, 99, 40)
            else:
                self.badge('SCAN TO', 48)
                self.badge('COLLECT', 60)
            self.button('home', 'BACK', 64, 99, 38)
        elif page in ('battle', 'moves'):
            b = app.battle
            self.badge('FOE %02d' % b.enemy['level'], 10)
            self.hp(67, 24, 34, b.enemy['hp'], max_hp(b.enemy))
            pf, ef = idle, idle
            px, py, ex, ey = 16, 34, 68, 34
            elapsed = time.ticks_diff(now, app.phase_at)
            contact = 270 <= elapsed < 350
            if app.phase == 'attack':
                dx, dy = leap(elapsed)
                px, py = px+dx, py+dy
                pf = 4
                ef = 5 if contact else idle
                if contact:
                    ex += 2
            elif app.phase == 'reply':
                dx, dy = leap(elapsed)
                ex, ey = ex-dx, ey+dy
                ef = 4
                pf = 5 if contact else idle
                if contact:
                    px -= 2
            elif b.result == 'caught':
                pf, ef = 6, 6
            if app.phase == 'attack':
                self.sprite(ef, b.enemy['palette'], ex, ey, True, True)
                self.sprite(pf, pet['palette'], px, py, True)
            else:
                self.sprite(pf, pet['palette'], px, py, True)
                self.sprite(ef, b.enemy['palette'], ex, ey, True, True)
            if app.phase in ('attack', 'reply') and contact:
                sx = 69 if app.phase == 'attack' else 49
                self.fb.line(sx-3, 43, sx+3, 49, WHITE)
                self.fb.line(sx+3, 43, sx-3, 49, WHITE)
            self.hp(18, 72, 33, pet['hp'], max_hp(pet))
            if app.phase == 'scan':
                y = 30 + (now//30)%38
                self.fb.hline(68, y, 36, TEAL)
            self.badge(b.message[:13], 78)
            ready = app.phase is None and b.result is None
            if b.result:
                self.button('finish', 'OK', 42, 99, 36, active=app.phase is None)
            elif page == 'moves':
                labels = ('ZAP', 'BITE', 'CLAW', 'TAIL')
                for i, label in enumerate(labels):
                    bx = 18+(i%2)*44 if i < 2 else 27+(i%2)*34
                    self.button('move%d'%i, label, bx, 88+(i//2)*12,
                                40 if i<2 else 32, 11, ready and pet['level']>=MOVE_LEVELS[i])
                self.buttons.append(('battle', 20, 4, 80, 24))
            else:
                self.button('moves', 'HIT', 18, 88, 40, 11, ready)
                self.button('scan', 'SCAN', 62, 88, 40, 11, ready)
                self.button('item', 'HP', 27, 100, 32, 11, ready)
                self.button('run', 'RUN', 61, 100, 32, 11, ready)
        elif page == 'notice':
            self.sprite(6, pet['palette'], 28, 25)
            self.badge(app.notice[:13], 82)
            self.button('home', 'OK', 42, 99, 36)
        elif page == 'search':
            self.sprite(idle, pet['palette'], 28, 27)
            self.badge('SEARCHING', 14)
            self.badge('WI-FI', 85)
        if app.save_pending:
            self.badge('SAVE RETRY', 12)
        upscale_mirror(self.buf, self.tx)
        self.lcd.set_window(0, 0, 239, 239)
        self.lcd.dc.value(1)
        self.lcd.cs.value(0)
        self.lcd.spi.write(self.tx)
        self.lcd.cs.value(1)
