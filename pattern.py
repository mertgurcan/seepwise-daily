from engine import DIRS
ROT = {}
def tf(tr, dr, dc):
    if tr & 1: dr, dc = dc, dr
    if tr & 2: dr = -dr
    if tr & 4: dc = -dc
    return dr, dc
NAME = {v: k for k, v in DIRS.items()}
def pattern_key(sol, wax, fibers, turns):
    """Damlaların çevresindeki öğe düzeni (döndürme/yansıtmadan bağımsız)."""
    els = [(p, 'w') for p in wax] + [(p, d) for p, d in fibers.items()]
    best = None
    for tr in range(8):
        per = []
        for s in sol:
            loc = []
            for (p, t) in els:
                dr, dc = p[0] - s[0], p[1] - s[1]
                if abs(dr) + abs(dc) <= turns:
                    r, c = tf(tr, dr, dc)
                    if t != 'w':
                        t = NAME[tf(tr, *DIRS[t])]
                    loc.append((r, c, t))
            per.append(tuple(sorted(loc)))
        k = (len(sol), turns, tuple(sorted(per)))
        if best is None or k < best:
            best = k
    return best
