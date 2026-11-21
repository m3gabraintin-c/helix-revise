# Export every question in data/ into judge-sized batches: difficulty/batches/<course>/NNN.json
# plus difficulty/batches/manifest.json (what the rating workflow takes as args). Run: python3 scripts/difficulty_batches.py [size]
# --remaining --prefix rN-: only questions not yet rated, as <prefix>NNN.json + manifest-remaining.json. Use a new prefix
# each round so a new batch can never take the name of an older one. Kept: batch files that have a ratings file (QA reads
# them) and batch files with judge work in difficulty/work/ (in progress; listed in the manifest again so the run finishes
# them). Other old batch files are stale and removed. Nothing rated or in progress is redone.
import glob, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "difficulty", "batches")
REMAINING = "--remaining" in sys.argv
PREFIX = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else ""
args = [a for i, a in enumerate(sys.argv[1:], 1) if a not in ("--remaining", "--prefix") and sys.argv[i - 1] != "--prefix"]
SIZE = int(args[0]) if args else 60
if REMAINING and not re.fullmatch(r"r\d+-", PREFIX): sys.exit("--remaining needs --prefix rN- (a prefix not used before, e.g. r3-)")
rated = {it["id"] for f in glob.glob(os.path.join(ROOT, "difficulty", "ratings", "*", "*.json"))
         for it in json.load(open(f, encoding="utf-8"))["items"]} if REMAINING else set()
work = lambda f: os.path.join(ROOT, "difficulty", "work", os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-5])
rating = lambda f: f.replace(os.sep + "batches" + os.sep, os.sep + "ratings" + os.sep)
import helix_data
d = helix_data.read_data()

# course id -> VCAA evidence pack (Units 1&2 have no VCAA exam, so they borrow the 3&4 pack; GCSE has none).
# Deliberately strict: a new subject must be added here, or this script stops with a KeyError.
PACK = {"methods": "methods", "general": "general", "specialist": "specialist", "chem": "chem", "physics": "physics",
        "vce-bio34": "biology", "vce-psych34": "psychology", "vce-english34": "english", "vce-chinese-sl34": "chinese-sl", "vce-chem12": "chem", "vce-bio12": "biology",
        "vce-psych12": "psychology", "vce-methods12": "methods", "vce-physics12": "physics", "gcse-bio": None}
MARKS = re.compile(r"\((\d+) marks?\)\s*$")

manifest, total, skipped, held = [], 0, 0, set()
if REMAINING:
    for f in sorted(glob.glob(os.path.join(OUT, "*", "*.json"))):
        if os.path.exists(rating(f)): continue
        if os.path.exists(work(f) + ".a.json") or os.path.exists(work(f) + ".b.json"):  # in progress: keep and finish
            b = json.load(open(f, encoding="utf-8"))
            held |= {q["id"] for q in b["questions"]}
            manifest.append({"course": b["course"], "pack": b["pack"], "batch": os.path.relpath(f, ROOT), "n": len(b["questions"]), "in_progress": True})
        else: os.remove(f)
elif os.path.exists(OUT): shutil.rmtree(OUT)
held -= rated
for sid, name, label, group, T in d["S"]:
    qs = []
    for num, tname, subs in T:
        for slug, sname, _ in subs:
            for r in d["Q"].get(slug, []):
                if isinstance(r, dict):  # multi-part question: {id, title, pieces: [{kind: info|part, ...}]}
                    parts = [p for p in r["pieces"] if p["kind"] == "part"]
                    qs.append({"id": r["id"], "topic": tname, "subtopic": sname, "type": "multipart", "title": r.get("title"),
                               "stem": " ".join(p.get("text", "") for p in r["pieces"] if p["kind"] == "info"),
                               "parts": [{"label": p.get("label"), "question": p.get("question"), "marks": p.get("marks"), "answer": p.get("answer")} for p in parts],
                               "marks": sum(p.get("marks") or 0 for p in parts)})
                    continue
                q = {"id": r[0], "topic": tname, "subtopic": sname}
                if r[1] == 0:
                    q.update(type="mcq", prompt=r[2], options=r[3], answer="ABCDEFGH"[r[4]], marks=1)
                else:
                    m = MARKS.search(r[2])
                    q.update(type="written", prompt=r[2], model_answer=r[3], marks=int(m.group(1)) if m else 1)
                qs.append(q)
    skipped += sum(q["id"] in rated or q["id"] in held for q in qs)
    qs = [q for q in qs if q["id"] not in rated and q["id"] not in held]
    os.makedirs(os.path.join(OUT, sid), exist_ok=True)
    for b in range(0, len(qs), SIZE):
        rel = "difficulty/batches/%s/%s%03d.json" % (sid, PREFIX, b // SIZE)
        f = os.path.join(ROOT, rel)  # a new batch must never reuse the name of a rated or in-progress one
        assert not (os.path.exists(f) or os.path.exists(rating(f)) or glob.glob(work(f) + ".*")), "name collision: " + rel
        json.dump({"course": sid, "course_name": "%s (%s)" % (name, label), "pack": PACK[sid], "questions": qs[b:b + SIZE]},
                  open(os.path.join(ROOT, rel), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        manifest.append({"course": sid, "pack": PACK[sid], "batch": rel, "n": len(qs[b:b + SIZE])})
    total += len(qs)
new = [m for m in manifest if not m.get("in_progress")]
assert sum(m["n"] for m in new) == total and total + skipped == sum(len(v) for v in d["Q"].values())
json.dump(manifest, open(os.path.join(OUT, "manifest-remaining.json" if REMAINING else "manifest.json"), "w"), indent=1)
print(len(new), "new batches,", total, "questions;", len(manifest) - len(new), "in-progress batches kept;",
      "%d questions already rated or in progress" % skipped if REMAINING else "")
