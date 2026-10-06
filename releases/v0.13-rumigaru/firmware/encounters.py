import time
from protocol import advertise, parse


class Encounters:
    def __init__(self, token):
        import bluetooth
        self.token = token
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.queue = []
        self.seen = {}
        self.ble.irq(self._irq)

    def _irq(self, event, data):
        if event == 5 and len(self.queue) < 16:
            # MicroPython callback buffers expire on return. Copy immediately.
            if data[3] >= -80:
                self.queue.append(bytes(data[4]))

    def start(self, species, duration_ms):
        self.ble.gap_advertise(250000, adv_data=advertise(self.token, species), connectable=False)
        self.ble.gap_scan(duration_ms, 30000, 30000, False)

    def stop(self):
        self.ble.gap_scan(None)
        self.ble.gap_advertise(None)

    def poll(self):
        now = time.ticks_ms()
        self.seen = {k: v for k, v in self.seen.items() if time.ticks_diff(now, v) < 300000}
        found = 0
        while self.queue:
            item = parse(self.queue.pop(0))
            if item and item[0] != self.token and item[0] not in self.seen:
                if len(self.seen) >= 64:
                    continue
                self.seen[item[0]] = now
                found += 1
        return found
