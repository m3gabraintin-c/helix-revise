# List the remaining work on one evidence pack as small, independent chunks for worker agents (prints one JSON line).
#   python3 scripts/evidence_tasks.py <pack>
# unverified: entries without "verified", grouped by local report file
# copied:     skill / examiner_note sharing an 8-word run with the report text (.txt copies only; PDFs are listed as pdf_unchecked)
# placeholder / unclassified: generic skills, missing or "Unclassified" areas
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK = 40
GENERIC = {"written response", "multiple-choice item", "multiple choice item", "mcq", "written", "multiple choice"}

def words(t): return re.findall(r"[a-z0-9]+", (t or "").lower())
def shingles(t, n=8):
    w = words(t)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
def chunks(xs): return [xs[i:i + CHUNK] for i in range(0, len(xs), CHUNK)]

def tasks(pack):
    p = json.load(open(os.path.join(ROOT, "difficulty", "evidence", pack + ".json"), encoding="utf-8"))
    ip = os.path.join(ROOT, "difficulty", "reports", pack, "index.json")
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    texts, unverified, copied, pdf_unchecked, placeholder, unclassified = {}, {}, [], 0, [], []
    for e in p["entries"]:
        f = (idx.get(e["url"]) or {}).get("file")
        if "verified" not in e: unverified.setdefault(f or "MISSING", []).append(e["eid"])
        if f and f.endswith(".txt"):
            if f not in texts: texts[f] = shingles(open(os.path.join(ROOT, f), encoding="utf-8").read())
            if (shingles(e.get("skill")) | shingles(e.get("examiner_note"))) & texts[f]: copied.append(e["eid"])
        else: pdf_unchecked += 1
        if len(words(e.get("skill"))) < 3 or (e.get("skill") or "").strip().lower().rstrip(".") in GENERIC: placeholder.append(e["eid"])
        if not e.get("area") or e["area"].strip().lower() == "unclassified": unclassified.append(e["eid"])
    return {"pack": pack, "entries": len(p["entries"]),
            "unverified": [{"report": f, "eids": c} for f, ids in sorted(unverified.items()) for c in chunks(ids)],
            "copied": chunks(copied), "placeholder": placeholder, "unclassified": unclassified, "pdf_unchecked": pdf_unchecked,
            "counts": {"unverified": sum(map(len, unverified.values())), "copied": len(copied), "placeholder": len(placeholder), "unclassified": len(unclassified)}}

assert shingles("a b c d e f g h") == {"a b c d e f g h"} and not shingles("too short")
if __name__ == "__main__":
    print(json.dumps(tasks(sys.argv[1])))
