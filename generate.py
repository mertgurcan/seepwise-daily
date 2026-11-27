"""Seepwise günlük bulmaca üreticisi.

Her çalıştırmada [bugün-1, bugün+3] aralığındaki eksik günleri üretir
(UTC'ye göre; bu pencere UTC-12 ile UTC+14 arasındaki her saat dilimini
kapsar). Yayınlanmış bir gün ASLA yeniden yazılmaz. Çıktı:
  docs/v1/days/YYYY-MM-DD.json  — tek gün (arşiv)
  docs/v1/upcoming.json         — uygulamanın çektiği pencere

Kurallar, Kolay/Orta/Zor serilerinin kurallarıyla aynı (engine.TIERS +
17 Kasım kuralları); ek olarak hedef şekil ve damla çevresi düzeni ne
paketteki 310 bölümde ne de daha önce yayınlanmış bir günlükte geçebilir.

Kullanım: python3 generate.py [--today YYYY-MM-DD] [--ahead N]
"""
import argparse, datetime as dt, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import *  # noqa: E402,F401
from pattern import pattern_key  # noqa: E402

DAYS = os.path.join(HERE, "docs", "v1", "days")
UPCOMING = os.path.join(HERE, "docs", "v1", "upcoming.json")
SCHEMA = 1
CANDIDATES = 7          # her gün için bu kadar geçerli aday; skoru ortanca olan seçilir
MAX_ATTEMPTS = 3000
# Uygulamadaki DailySchedule ile aynı: Pzt-Sal kolay, Çar-Per orta, Cum-Paz zor.
TIER_BY_WEEKDAY = {0: "easy", 1: "easy", 2: "medium", 3: "medium", 4: "hard", 5: "hard", 6: "hard"}


def to_board(d):
    fib = {(f["row"], f["col"]): f["dir"] for f in d["fibers"]}
    return Board(d["size"], [tuple(w) for w in d["wax"]], fib)


def keys_of(d):
    b = to_board(d)
    sol = {tuple(s) for s in d["solution"]}
    target = run(sol, d["turns"], b)
    return (shape_key(target, len(sol), d["turns"]),
            pattern_key(sol, set(b.wax), dict(b.fibers), d["turns"]))


def to_definition(g, day):
    return dict(
        id=int(day.strftime("%Y%m%d")), size=g["size"], turns=g["turns"],
        solution=[list(p) for p in g["solution"]], wax=[list(p) for p in g["wax"]],
        fibers=[dict(row=p[0], col=p[1], dir=d) for p, d in g["fibers"]], hint="")


def check(d, tier):
    """verify.py'deki denetimlerin aynısı; geçmezse yayınlanmaz."""
    p = TIERS[tier]
    b = to_board(d)
    sol = {tuple(s) for s in d["solution"]}
    n = len(sol)
    T = run(sol, d["turns"], b)
    cands = candidates(T, d["turns"], b)
    w, f = set(b.wax), dict(b.fibers)
    errs = []
    if not (exact_solutions(T, n, d["turns"], b) == 1 and swift_count_max(T, n, d["turns"], b) == 1):
        errs.append("tek")
    if not all(impact(e, sol, d["turns"], d["size"], w, f) >= 2 for e in w | set(f)):
        errs.append("etki")
    if len(w) + len(f) < p["min_el"]:
        errs.append("oge")
    if len(cands) - n < p["min_decoys"]:
        errs.append("celdirici")
    if p["inference"] and sol <= forced(T, cands, d["turns"], b):
        errs.append("cikarim")
    if len(T) / d["size"] ** 2 > p["max_ratio"]:
        errs.append("oran")
    if (w & set(f)) or (w & sol):
        errs.append("mumlif_ayri")
    if len(f) != len(d["fibers"]):
        errs.append("lif_tekrar")
    return errs


def banned_keys():
    shapes, patterns = set(), set()
    sources = [os.path.join(HERE, "bundled", n) for n in ("levels.json", "generated_levels.json")]
    for path in sources:
        for d in json.load(open(path)):
            s, pk = keys_of(d)
            shapes.add(s); patterns.add(pk)
    for name in sorted(os.listdir(DAYS)):
        if name.endswith(".json"):
            d = json.load(open(os.path.join(DAYS, name)))["level"]
            s, pk = keys_of(d)
            shapes.add(s); patterns.add(pk)
    return shapes, patterns


def generate_day(day, shapes, patterns):
    tier = TIER_BY_WEEKDAY[day.weekday()]
    found, seen = [], set()
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(f"seepwise-daily-v1-{day.isoformat()}-{attempt}")
        g = try_generate(tier, rng)
        if not g or g["key"] in shapes or g["key"] in seen:
            continue
        d = to_definition(g, day)
        _, pk = keys_of(d)
        if pk in patterns or check(d, tier):
            continue
        seen.add(g["key"])
        found.append((g["metrics"]["score"], attempt, d))
        if len(found) >= CANDIDATES:
            break
    if not found:
        raise SystemExit(f"{day}: {tier} için geçerli bulmaca üretilemedi")
    found.sort(key=lambda x: (x[0], x[1]))
    score, attempt, d = found[len(found) // 2]
    return dict(date=day.isoformat(), tier=tier, level=d), score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="YYYY-MM-DD (varsayılan: UTC bugün)")
    ap.add_argument("--ahead", type=int, default=3)
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(dt.timezone.utc).date()
    os.makedirs(DAYS, exist_ok=True)

    shapes, patterns = banned_keys()
    window = [today + dt.timedelta(days=i) for i in range(-1, a.ahead + 1)]
    created = 0
    for day in window:
        path = os.path.join(DAYS, f"{day.isoformat()}.json")
        if os.path.exists(path):
            continue
        entry, score = generate_day(day, shapes, patterns)
        s, pk = keys_of(entry["level"])
        shapes.add(s); patterns.add(pk)
        with open(path, "w") as fh:
            json.dump(entry, fh, separators=(",", ":"))
        created += 1
        lv = entry["level"]
        print(f"{day} {entry['tier']:6} size={lv['size']} damla={len(lv['solution'])} "
              f"kare={lv['turns']} skor={score:.1f}", flush=True)

    puzzles = []
    for day in window:
        path = os.path.join(DAYS, f"{day.isoformat()}.json")
        entry = json.load(open(path))
        assert entry["date"] == day.isoformat()
        assert not check(entry["level"], entry["tier"]), f"{day} denetimden geçmedi"
        puzzles.append(entry)
    feed = dict(schema=SCHEMA, generatedAt=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                puzzles=puzzles)
    with open(UPCOMING, "w") as fh:
        json.dump(feed, fh, separators=(",", ":"))
    print(f"yeni gün: {created}, upcoming: {window[0]} … {window[-1]}")


if __name__ == "__main__":
    main()
