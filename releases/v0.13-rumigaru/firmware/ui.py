class Screen:
    def __init__(self):
        import framebuf
        from lcd_driver import Display
        self.lcd = Display()
        self.bits = bytearray(240 * 240 // 8)
        self.fb = framebuf.FrameBuffer(self.bits, 240, 240, framebuf.MONO_HLSB)

    def show(self, state, status, f=None, peers=0):
        b = self.fb
        b.fill(0)
        lines = ['RADIO ROAM', status, 'DEX %d/32' % len(state['collection'])]
        e = state['last']
        if e:
            lines += [e['biome'], 'MON %02d  PWR %d' % (e['species'], e['power'])]
        if f:
            lines += ['AP %d  RSSI %d' % (f['count'], f['mean'])]
        lines += ['PEERS %d' % peers]
        for i, line in enumerate(lines):
            b.text(line, (240 - len(line) * 8) // 2, 40 + i * 16, 1)
        if e:
            x = 100
            b.fill_rect(x, 161, 40, 24, 1)
            b.fill_rect(x + 8, 166, 5, 5, 0)
            b.fill_rect(x + 27, 166, 5, 5, 0)
        row = bytearray(480)
        for y in range(240):
            for x in range(240):
                on = b.pixel(x, y)
                row[2*x] = 0x07 if on else 0
                row[2*x+1] = 0xff if on else 0
            self.lcd.write_pixels(0, y, 240, 1, row)
