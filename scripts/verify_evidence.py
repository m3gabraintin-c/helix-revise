# Deterministic evidence check, run after scripts/fetch_reports.py. For MCQ entries whose report has a text copy, find
# the row "<n> | <key> | %A | %B ..." and compare the keyed % with pct_correct. Sets verified + verified_by="code".
# Entries it cannot check are left as they are (the Haiku verifier handles them; its results are kept on re-runs).
# Run: python3 scripts/verify_evidence.py
import glob, json, os, sys, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = re.compile(r"^(\d+) \| ([A-E]) \| (\d+) \| (\d+) \| (\d+) \| (\d+)(?: \| (\d+))?", re.M)

def rows(text):  # question number -> (key, % choosing key); first table wins (Section A)
    out = {}
    for m in ROW.finditer(text):
        n, key = int(m.group(1)), m.group(2)
        pcts = [int(g) for g in m.groups()[2:] if g is not None]
        if n not in out and "ABCDE".index(key) < len(pcts): out[n] = (key, pcts["ABCDE".index(key)])
    return out

def check(text_rows, e):
    m = re.search(r"Q\s*(\d+)", e.get("question", ""))
    if not m or int(m.group(1)) not in text_rows: return None
    key, pct = text_rows[int(m.group(1))]
    return pct == e.get("pct_correct"), key, pct

# optional args: pack ids to limit to (parallel verifiers each pass their own, so they never write the same file)
for f in sorted(glob.glob(os.path.join(ROOT, "difficulty", "evidence", "%s.json" % (sys.argv[1] if len(sys.argv) > 1 else "*")))):
    pack = json.load(open(f, encoding="utf-8"))
    ip = os.path.join(ROOT, "difficulty", "reports", pack["subject"], "index.json")
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    cache, stats = {}, {"ok": 0, "mismatch": 0, "left_for_agent": 0}
    for e in pack["entries"]:
        rel = (idx.get(e["url"]) or {}).get("file")
        r = None
        if e["format"] == "mcq" and rel and rel.endswith(".txt"):
            if rel not in cache: cache[rel] = rows(open(os.path.join(ROOT, rel), encoding="utf-8").read())
            r = check(cache[rel], e)
        if r is None:  # keep any Haiku verification already saved
            if e.get("verified_by") != "haiku": stats["left_for_agent"] += 1
            continue
        for k in ("verified", "verify_note", "verified_by", "key_unconfirmed", "checked_via"): e.pop(k, None)
        ok, key, pct = r
        e.update(verified=ok, verified_by="code", checked_via=(idx[e["url"]]["fetched_from"]))
        if not ok: e["verify_note"] = "report prints %s%% for key %s" % (pct, key)
        stats["ok" if ok else "mismatch"] += 1
    json.dump(pack, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(pack["subject"], stats)

assert rows("1 | E | 2 | 16 | 2 | 3 | 77 | 0 | x\n2 | A | 53 | 29 | 3 | 6 | 8 | 0 |") == {1: ("E", 77), 2: ("A", 53)}
