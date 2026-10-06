"""Display sleep gestures and approximate single-cell battery gauge."""

def gesture(start,end,duration):
    dx=end[0]-start[0]; dy=end[1]-start[1]
    if start[1]<=30 and dy>=25 and abs(dx)<max(20,dy) and duration<1800:
        return 'swipe_down'
    if abs(dx)+abs(dy)<18 and duration<650: return 'tap'
    return None


class WakeTaps:
    def __init__(self): self.first=None
    def tap(self,now,x,y,diff):
        previous=self.first
        self.first=(now,x,y)
        if previous:
            dt=diff(now,previous[0])
            if 70<=dt<=500 and abs(x-previous[1])+abs(y-previous[2])<=30:
                self.first=None
                return True
        return False


def percent(mv):
    if mv<2500 or mv>4400: return None
    curve=((3200,0),(3500,5),(3600,10),(3700,25),(3800,50),(3900,70),(4000,85),(4200,100))
    if mv<=curve[0][0]: return 0
    for (a,p),(b,q) in zip(curve,curve[1:]):
        if mv<=b: return p+(mv-a)*(q-p)//(b-a)
    return 100


class Battery:
    # Waveshare schematic: GPIO1, divider 200k / 100k -> ADC voltage x3.
    def __init__(self):
        from machine import ADC,Pin
        self.adc=ADC(Pin(1)); self.adc.atten(ADC.ATTN_11DB)
        self.mv=None; self.level=None
        self.update()

    def update(self):
        try:
            values=sorted(self.adc.read_uv() for _ in range(9))
            mv=values[4]*3//1000
            self.mv=mv if self.mv is None else (self.mv*3+mv)//4
            self.level=percent(self.mv)
        except (OSError,AttributeError): self.level=None
        return self.level
