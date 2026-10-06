class Scanner:
    def scan(self):
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        try:
            return wlan.scan()
        finally:
            wlan.active(False)
