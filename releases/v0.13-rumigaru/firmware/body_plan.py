"""Species-specific rig proportions, independent of inherited part numbers."""

def fit(kind, name, meta, pixels):
    if kind not in (0, 1, 2, 3):
        return meta, pixels
    oldw, oldh = meta['size']
    ox, oy = meta['origin']
    # Small creatures retain their smaller source proportions.
    if name == 'body':
        w, h = (min(36, oldw + 4), max(12, oldh * 3 // 5)) if kind != 1 else (oldw * 4 // 5, oldh * 3 // 4)
    elif name == 'head':
        w, h = max(1, oldw * 9 // 10), max(1, oldh * 9 // 10)
    elif name in ('arms', 'legs'):
        if kind == 3:
            w, h = max(8, oldw * 2 // 3), max(5, oldh // 3)
        elif kind == 1:
            w, h = max(8, oldw // 2), max(8, oldh // 2)
        else:
            w, h = max(10, oldw * 2 // 3), max(10, oldh // 2)
    elif name in ('tail', 'wings') and kind != 1:
        w, h = max(1, oldw * 3 // 4), max(1, oldh * 3 // 4)
    else:
        return meta, pixels
    def point(p):
        return [ox + (p[0] - ox) * w // oldw, oy + (p[1] - oy) * h // oldh]
    result = dict(meta)
    result['size'] = [w, h]
    result['pivot'] = point(meta['pivot'])
    result['sockets'] = {k: point(v) for k, v in meta['sockets'].items()}
    data = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            data[y * w + x] = pixels[(y * oldh // h) * oldw + x * oldw // w]
    if name == 'body':
        x, y = (18, 31) if kind != 1 else (23, 28)
        dx, dy = x - ox, y - oy
        result['origin'] = [x, y]
        result['pivot'] = [result['pivot'][0] + dx, result['pivot'][1] + dy]
        if kind == 1:
            sockets = {'head':[x+w-5,y+5], 'arms':[x+w//2,y+h//2],
                       'legs':[x+w//2,y+h-2], 'tail':[x+3,y+h//2], 'wings':[x+w//2,y+5]}
        else:
            sockets = {'head':[x+w-5,y+4], 'arms':[x+w-6,y+h-3],
                       'legs':[x+5,y+h-3], 'tail':[x+2,y+h//2], 'wings':[x+w//2,y+3]}
        result['sockets'] = sockets
    return result, data
