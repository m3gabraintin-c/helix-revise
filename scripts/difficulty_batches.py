# Export every question in index.html's DATA into judge-sized batches: difficulty/batches/<course>/NNN.json
# plus difficulty/batches/manifest.json (what the rating workflow takes as args). Run: python3 scripts/difficulty_batches.py [size]
import json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "difficulty", "batches")
SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 60
line = next(l for l in open(os.path.join(ROOT, "index.html"), encoding="utf-8") if l.startswith("const DATA = "))
d = json.loads(line[len("const DATA = "):].rstrip().rstrip(";"))

# course id -> VCAA evidence pack (Units 1&2 have no VCAA exam, so they borrow the 3&4 pack; GCSE has none).
# Deliberately strict: a new subject must be added here, or this script stops with a KeyError.
PACK = {"methods": "methods", "general": "general", "specialist": "specialist", "chem": "chem", "physics": "physics",
        "vce-bio34": "biology", "vce-psych34": "psychology", "vce-english34": "english", "vce-chinese-sl34": "chinese-sl", "vce-chem12": "chem", "vce-bio12": "biology",
        "vce-psych12": "psychology", "vce-methods12": "methods", "vce-physics12": "physics", "gcse-bio": None}
MARKS = re.compile(r"\((\d+) marks?\)\s*$")

if os.path.exists(OUT): shutil.rmtree(OUT)
manifest, total = [], 0
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
    os.makedirs(os.path.join(OUT, sid))
    for b in range(0, len(qs), SIZE):
        rel = "difficulty/batches/%s/%03d.json" % (sid, b // SIZE)
        json.dump({"course": sid, "course_name": "%s (%s)" % (name, label), "pack": PACK[sid], "questions": qs[b:b + SIZE]},
                  open(os.path.join(ROOT, rel), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        manifest.append({"course": sid, "pack": PACK[sid], "batch": rel, "n": len(qs[b:b + SIZE])})
    total += len(qs)
assert sum(m["n"] for m in manifest) == total == sum(len(v) for v in d["Q"].values())
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print(len(manifest), "batches,", total, "questions")
