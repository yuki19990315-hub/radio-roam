# coding: utf-8
import time

import machine
import config


WIDTH = 240
HEIGHT = 240
CX = WIDTH // 2
CY = HEIGHT // 2

BLACK = 0x0000
BLUE = 0x057F
DIM_BLUE = 0x02B8
WHITE = 0xFFFF


def color565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


class Display:
    """GC9A01 display driver for Waveshare ESP32-S3-Touch-LCD-1.28."""

    def __init__(self, baudrate=40_000_000):
        self.spi = machine.SPI(
            1,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=machine.Pin(config.SCK),
            mosi=machine.Pin(config.MOSI),
        )
        self.dc = machine.Pin(config.DC, machine.Pin.OUT)
        self.cs = machine.Pin(config.CS, machine.Pin.OUT)
        self.rst = machine.Pin(config.RST, machine.Pin.OUT)
        self.bl = machine.Pin(config.BL, machine.Pin.OUT)
        self._row_buffer = bytearray(WIDTH * 2)
        self._init_display()
        self.set_backlight(True)
        self.clear(BLACK)

    def _cmd(self, value):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([value]))
        self.cs.value(1)

    def _data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)

    def _init_display(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(120)

        for cmd, data in (
            (0xEF, ()), (0xEB, (0x14,)), (0xFE, ()), (0xEF, ()),
            (0xEB, (0x14,)), (0x84, (0x40,)), (0x85, (0xFF,)),
            (0x86, (0xFF,)), (0x87, (0xFF,)), (0x88, (0x0A,)),
            (0x89, (0x21,)), (0x8A, (0x00,)), (0x8B, (0x80,)),
            (0x8C, (0x01,)), (0x8D, (0x01,)), (0x8E, (0xFF,)),
            (0x8F, (0xFF,)), (0xB6, (0x00, 0x00)), (0x36, (0x00,)),
            (0x3A, (0x05,)), (0x90, (0x08, 0x08, 0x08, 0x08)),
            (0xBD, (0x06,)), (0xBC, (0x00,)), (0xFF, (0x60, 0x01, 0x04)),
            (0xC3, (0x13,)), (0xC4, (0x13,)), (0xC9, (0x22,)),
            (0xBE, (0x11,)), (0xE1, (0x10, 0x0E)),
            (0xDF, (0x21, 0x0C, 0x02)),
            (0xF0, (0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)),
            (0xF1, (0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)),
            (0xF2, (0x45, 0x09, 0x08, 0x08, 0x26, 0x2A)),
            (0xF3, (0x43, 0x70, 0x72, 0x36, 0x37, 0x6F)),
            (0xED, (0x1B, 0x0B)), (0xAE, (0x77,)), (0xCD, (0x63,)),
            (0x70, (0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03)),
            (0xE8, (0x34,)),
            (0x62, (0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70)),
            (0x63, (0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70)),
            (0x64, (0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07)),
            (0x66, (0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00)),
            (0x67, (0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98)),
            (0x74, (0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00)),
            (0x98, (0x3E, 0x07)), (0x35, ()), (0x21, ()), (0x11, ()),
        ):
            self._cmd(cmd)
            if data:
                self._data(bytes(data))
            if cmd == 0x11:
                time.sleep_ms(120)
        self._cmd(0x29)
        time.sleep_ms(20)

    def set_window(self, x0, y0, x1, y1):
        if x0 < 0:
            x0 = 0
        if y0 < 0:
            y0 = 0
        if x1 >= WIDTH:
            x1 = WIDTH - 1
        if y1 >= HEIGHT:
            y1 = HEIGHT - 1

        # Panel columns run right-to-left in this hardware orientation.
        # write_pixels also reverses each row to preserve logical x ordering.
        rx0 = WIDTH - 1 - x1
        rx1 = WIDTH - 1 - x0
        self._cmd(0x2A)
        self._data(bytes([rx0 >> 8, rx0 & 0xFF, rx1 >> 8, rx1 & 0xFF]))
        self._cmd(0x2B)
        self._data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._cmd(0x2C)

    def write_pixels(self, x, y, w, h, pixels):
        if w <= 0 or h <= 0:
            return
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.dc.value(1)
        self.cs.value(0)
        # RGB565 pixels must reverse as pairs, not as individual bytes.
        row = self._row_buffer
        for row_index in range(h):
            base = row_index * w * 2
            for col in range(w):
                src = base + (w - 1 - col) * 2
                row[col * 2] = pixels[src]
                row[col * 2 + 1] = pixels[src + 1]
            self.spi.write(memoryview(row)[:w * 2])
        self.cs.value(1)

    def fill_rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x >= WIDTH or y >= HEIGHT or w <= 0 or h <= 0:
            return
        if x + w > WIDTH:
            w = WIDTH - x
        if y + h > HEIGHT:
            h = HEIGHT - y

        hi = color >> 8
        lo = color & 0xFF
        row = bytes([hi, lo]) * w
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(h):
            self.spi.write(row)
        self.cs.value(1)

    def clear(self, color=BLACK):
        self.fill_rect(0, 0, WIDTH, HEIGHT, color)

    def set_backlight(self, on):
        self.bl.value(1 if on else 0)

