"""Mürekkep motorunun Python kopyası (Simulator, Solver, Generator kuralları)."""
import random
from itertools import combinations

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
DIR_NAMES = ["up", "down", "left", "right"]


class Board:
    def __init__(self, size, wax=(), fibers=None):
        self.size = size
        self.wax = frozenset(wax)
        self.fibers = dict(fibers or {})

    def inside(self, p):
        return 0 <= p[0] < self.size and 0 <= p[1] < self.size

    def positions(self):
        return [(r, c) for r in range(self.size) for c in range(self.size)]


def step(ink, board):
    nxt = set(ink)
    for p in ink:
        dirs = [board.fibers[p]] if p in board.fibers else DIR_NAMES
        for d in dirs:
            dr, dc = DIRS[d]
            q = (p[0] + dr, p[1] + dc)
            if board.inside(q) and q not in board.wax:
                nxt.add(q)
    return nxt


def run(drops, turns, board):
    cur = set(drops)
    for _ in range(turns):
        cur = step(cur, board)
    return cur


def candidates(target, turns, board):
    return {p for p in board.positions() if p not in board.wax and run([p], turns, board) <= target}


def comb_upto(n, k, upto):
    if k < 0 or k > n or upto <= 0:
        return 0
    if k == 0:
        return 1
    res = 1
    for i in range(k):
        res = res * (n - i) // (i + 1)
        if res >= upto:
            return upto
    return res


def swift_count_max(target, drop_count, turns, board, limit=2):
    """Swift Solver.countSolutions'ın birebir kopyası; ama pivot eşitliklerinde
    (Swift'te Set sırasına bağlı) TÜM seçenekleri dener ve en büyük sayıyı
    döner. Böylece cihazdaki sonuç sıradan bağımsız olarak 1 çıkar."""
    cands = candidates(target, turns, board)
    if not cands or drop_count <= 0 or drop_count > len(cands):
        return 0
    spread = {c: run([c], turns, board) for c in cands}
    cov = {t: [c for c in cands if t in spread[c]] for t in target}
    if any(not v for v in cov.values()):
        return 0
    ncand = len(cands)

    def search(remaining, chosen, excluded):
        if not remaining:
            return comb_upto(ncand - chosen, drop_count - chosen, limit)
        if chosen >= drop_count:
            return 0
        m = min(len(cov[t]) for t in remaining)
        best = 0
        for pivot in [t for t in remaining if len(cov[t]) == m]:
            count = 0
            for c in cov[pivot]:
                if c in excluded:
                    continue
                count += search(remaining - spread[c], chosen + 1, excluded | {c})
                if count >= limit:
                    break
            best = max(best, count)
            if best >= limit:
                return best
        return best

    return search(frozenset(target), 0, frozenset())


def exact_solutions(target, drop_count, turns, board, limit=2):
    cands = sorted(candidates(target, turns, board))
    spread = {c: run([c], turns, board) for c in cands}
    n = 0
    for combo in combinations(cands, drop_count):
        u = set()
        for c in combo:
            u |= spread[c]
        if u == target:
            n += 1
            if n >= limit:
                break
    return n


def forced(target, cands, turns, board):
    spread = {c: run([c], turns, board) for c in cands}
    out = set()
    for t in target:
        cs = [c for c in cands if t in spread[c]]
        if len(cs) == 1:
            out.add(cs[0])
    return out


def impact(el, sol, turns, size, wax, fibers):
    t = run(sol, turns, Board(size, wax, fibers))
    w = set(wax) - {el}
    f = {k: v for k, v in fibers.items() if k != el}
    t2 = run(sol, turns, Board(size, w, f))
    return len(t ^ t2)


def prune(sol, turns, size, wax, fibers):
    removed = True
    while removed:
        removed = False
        for el in sorted(set(wax) | set(fibers)):
            if impact(el, sol, turns, size, wax, fibers) < 2:
                wax.discard(el)
                fibers.pop(el, None)
                removed = True
                break


def shape_key(target, drop_count, turns):
    best = None
    for tr in range(8):
        pts = []
        for r, c in target:
            if tr & 1:
                r, c = c, r
            if tr & 2:
                r = -r
            if tr & 4:
                c = -c
            pts.append((r, c))
        mr = min(p[0] for p in pts)
        mc = min(p[1] for p in pts)
        flat = sorted((p[0] - mr, p[1] - mc) for p in pts)
        flat = [x for p in flat for x in p]
        if best is None or flat < best:
            best = flat
    return f"{drop_count}|{turns}|" + ",".join(map(str, best))


def neighborhood(cells, size):
    res = set(cells)
    for (r, c) in cells:
        for dr, dc in DIRS.values():
            q = (r + dr, c + dc)
            if 0 <= q[0] < size and 0 <= q[1] < size:
                res.add(q)
    return res


TIERS = {
    "easy": dict(size=(6, 7), turns=(1, 2), drops=(1, 2), elems=(2, 4), min_el=1, wax_share=0.55,
                 min_decoys=2, inference=False, max_ratio=0.7),
    "medium": dict(size=(7, 8), turns=(2, 2), drops=(2, 4), elems=(4, 8), min_el=2, wax_share=0.5,
                   min_decoys=2, inference=True, max_ratio=0.7),
    "hard": dict(size=(8, 9), turns=(2, 3), drops=(3, 6), elems=(6, 10), min_el=3, wax_share=0.45,
                 min_decoys=3, inference=True, max_ratio=0.6),
}


def metrics(target, cands, sol, ratio, turns, board):
    f = forced(target, cands, turns, board)
    decoys = len(cands - set(sol))
    score = decoys * 2 + (len(cands) - len(f)) - ratio * 10
    return dict(candidates=len(cands), decoys=decoys, forced=len(f), ratio=ratio, score=score)


def try_generate(tier, rng):
    p = TIERS[tier]
    size = rng.randint(*p["size"])
    turns = rng.randint(*p["turns"])
    dc = rng.randint(*p["drops"])
    empty = Board(size)
    sol = set(rng.sample(empty.positions(), dc))
    zone = run(sol, turns - 1, empty)
    if turns == 1:
        zone |= neighborhood(run(sol, 1, empty), size)
    zone = sorted(zone)
    wax, fibers = set(), {}
    for _ in range(rng.randint(*p["elems"])):
        pos = rng.choice(zone)
        is_wax = rng.random() < p["wax_share"]
        d = rng.choice(DIR_NAMES)
        if pos in wax or pos in fibers:
            continue
        if is_wax and pos not in sol:
            wax.add(pos)
        else:
            fibers[pos] = d
    prune(sol, turns, size, wax, fibers)
    if len(wax) + len(fibers) < p["min_el"]:
        return None
    board = Board(size, wax, fibers)
    target = run(sol, turns, board)
    if not target:
        return None
    ratio = len(target) / (size * size)
    if ratio > p["max_ratio"]:
        return None
    cands = candidates(target, turns, board)
    if len(cands) - dc < p["min_decoys"]:
        return None
    if p["inference"] and sol <= forced(target, cands, turns, board):
        return None
    if exact_solutions(target, dc, turns, board) != 1:
        return None
    if swift_count_max(target, dc, turns, board) != 1:
        return None
    m = metrics(target, cands, sol, ratio, turns, board)
    return dict(size=size, turns=turns, solution=sorted(sol), wax=sorted(wax),
                fibers=sorted(fibers.items()), target=target, metrics=m,
                key=shape_key(target, dc, turns))
