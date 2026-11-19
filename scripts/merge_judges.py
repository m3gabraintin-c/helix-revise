# Merge two independent judges' files (+ optional tie-break) for one batch into its ratings file.
#   python3 scripts/merge_judges.py difficulty/batches/<course>/<name>.json
# Reads difficulty/work/<course>/<name>.{a,b,tie}.json ({"items": [...]}) and prints one JSON line:
#   {"batch", "n", "missing_a", "missing_b", "disputes", "written"}
# Disputed items (with both judges' outputs) are saved to <name>.disputes.json for the tie-break judge.
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LV = ["low", "medium", "high"]
def star(p): return 1 if p >= 85 else 2 if p >= 70 else 3 if p >= 50 else 4 if p >= 30 else 5

def load(path, ids):
    try: items = json.load(open(path, encoding="utf-8"))["items"]
    except (OSError, ValueError, KeyError, TypeError): return {}
    good = {}
    for x in items if isinstance(items, list) else []:
        ok = (isinstance(x, dict) and x.get("id") in ids and isinstance(x.get("p"), (int, float)) and 0 <= x["p"] <= 100
              and x.get("confidence") in LV and isinstance(x.get("evidence", []), list))
        if ok and x["id"] not in good: good[x["id"]] = x  # first valid item per id wins
    return good

def merge(batch):
    ids = [q["id"] for q in json.load(open(os.path.join(ROOT, batch), encoding="utf-8"))["questions"]]
    idset = set(ids)
    work = os.path.join(ROOT, "difficulty", "work", batch.split("/")[-2], os.path.basename(batch)[:-5])
    A, B, T = load(work + ".a.json", idset), load(work + ".b.json", idset), load(work + ".tie.json", idset)
    mt = lambda f: os.path.getmtime(f) if os.path.exists(f) else 0
    if mt(work + ".tie.json") < max(mt(work + ".a.json"), mt(work + ".b.json")): T = {}  # tie-break predates a re-judge: stale
    final, disputes = [], []
    for i in ids:
        a, b = A.get(i), B.get(i)
        if a and b and abs(star(a["p"]) - star(b["p"])) <= 1 and abs(a["p"] - b["p"]) <= 12:
            c = LV[min(LV.index(a["confidence"]), LV.index(b["confidence"]))]
            final.append({"id": i, "p": round((a["p"] + b["p"]) / 2), "confidence": c,  # low means no statistic: evidence []
                          "evidence": [] if c == "low" else sorted(set(a.get("evidence", [])) | set(b.get("evidence", []))), "basis": b.get("basis") or a.get("basis", ""),
                          "judges": {"a": [a["p"], a["confidence"]], "b": [b["p"], b["confidence"]]}, "resolved_by": "agree"})
        elif a and b and i in T:
            final.append({**{k: T[i][k] for k in ("id", "p", "confidence", "evidence") if k in T[i]},
                          **({"evidence": []} if T[i]["confidence"] == "low" else {}), "basis": T[i].get("basis", ""),
                          "judges": {"a": [a["p"], a["confidence"]], "b": [b["p"], b["confidence"]]}, "resolved_by": "tiebreak"})
        elif a and b:
            disputes.append({"id": i, "a": a, "b": b})
    missing_a, missing_b = [i for i in ids if i not in A], [i for i in ids if i not in B]
    written = len(final) == len(ids)
    if written:
        out = os.path.join(ROOT, batch.replace("/batches/", "/ratings/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"batch": batch, "items": final}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    elif disputes:
        json.dump({"batch": batch, "disputes": disputes}, open(work + ".disputes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"batch": batch, "n": len(ids), "missing_a": missing_a, "missing_b": missing_b, "disputes": [d["id"] for d in disputes], "written": written}

if __name__ == "__main__":
    print(json.dumps(merge(sys.argv[1])))
