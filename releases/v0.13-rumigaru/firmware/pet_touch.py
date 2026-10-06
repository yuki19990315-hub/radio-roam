import time
from machine import I2C, Pin


class Touch:
    """CST816: one action on release, no repeated taps while held."""
    def __init__(self):
        self.i2c = I2C(0, scl=Pin(7), sda=Pin(6), freq=400000)
        self.rst = Pin(13, Pin.OUT)
        self.rst.value(0)
        time.sleep_ms(2)
        self.rst.value(1)
        time.sleep_ms(60)
        self.i2c.writeto_mem(0x15, 0xFE, b'\x01')
        self.i2c.writeto_mem(0x15, 0xFA, b'\x71')
        self.down = False
        self.start = (0, 0)
        self.last = (0, 0)
        self.errors = 0
        self.started_at = 0
        self.gesture = None

    def poll(self):
        self.gesture = None
        try:
            p = self.i2c.readfrom_mem(0x15, 0x02, 5)
        except OSError:
            self.errors += 1
            return None
        if p[0] & 15:
            x, y = ((p[1]&15)<<8) | p[2], ((p[3]&15)<<8) | p[4]
            if not 0 <= x < 240 or not 0 <= y < 240:
                return None
            self.last = (x//2, y//2)
            if not self.down:
                self.start = self.last
                self.started_at = time.ticks_ms()
            self.down = True
        elif self.down:
            self.down = False
            from power_control import gesture
            self.gesture = gesture(self.start,self.last,time.ticks_diff(time.ticks_ms(),self.started_at))
            if self.gesture == 'tap':
                return self.last
        return None
