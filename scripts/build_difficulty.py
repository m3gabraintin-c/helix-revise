# Merge difficulty/ratings/**.json, enforce the evidence rules, and write it into the DIFF part of each data/<subject>.json.
# Run: python3 scripts/build_difficulty.py   (safe to re-run; unrated questions simply show no chip)
import glob, json, os
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import helix_data
d = helix_data.read_data()

# Star bands on p = estimated % of that course's exam cohort answering fully correctly (mean % of marks for multi-mark).
BANDS = [(85, 1), (70, 2), (50, 3), (30, 4), (0, 5)]
def stars(p): return next(s for lo, s in BANDS if p >= lo)
RANK = {"low": 0, "medium": 1, "high": 2}

rid = lambda r: r["id"] if isinstance(r, dict) else r[0]  # multi-part rows are dicts
course_of = {rid(r): sid for sid, *_, T in d["S"] for _, _, subs in T for slug, _, _ in subs for r in d["Q"].get(slug, [])}
# Units 1&2 are school-assessed (no VCAA exam stats) and GCSE is not VCAA at all, so their confidence is capped.
CAP = {sid: ("low" if sid == "gcse-bio" else "medium" if sid.startswith("vce-") and sid.endswith("12") else "high") for sid, *_ in d["S"]}

evidence = {}
for f in glob.glob(os.path.join(ROOT, "difficulty", "evidence", "*.json")):
    for e in json.load(open(f, encoding="utf-8"))["entries"]:
        evidence[e["eid"]] = e
def usable(eid):  # verified, has a number, and comes from VCAA itself (no third-party mirrors)
    e = evidence.get(eid)
    return bool(e and urlparse(e.get("url", "")).hostname in ("vcaa.vic.edu.au", "www.vcaa.vic.edu.au")
                and e.get("verified") is True and (e.get("pct_correct") is not None or e.get("mean_mark") is not None))

out, notes = {}, {"downgraded_no_evidence": 0, "capped": 0, "unknown_id": 0, "bad_p": 0}
for f in sorted(glob.glob(os.path.join(ROOT, "difficulty", "ratings", "*", "*.json"))):
    for it in json.load(open(f, encoding="utf-8"))["items"]:
        qid, p, c = it["id"], it.get("p"), it.get("confidence", "low")
        if qid not in course_of: notes["unknown_id"] += 1; continue
        if not isinstance(p, (int, float)) or not 0 <= p <= 100: notes["bad_p"] += 1; continue
        if c != "low" and not any(usable(e) for e in it.get("evidence", [])):
            c = "low"; notes["downgraded_no_evidence"] += 1  # no traceable VCAA statistic -> it is an estimate
        if RANK[c] > RANK[CAP[course_of[qid]]]:
            c = CAP[course_of[qid]]; notes["capped"] += 1
        out[qid] = [stars(p), round(p), c[0]]

helix_data.write_diff(out)

missing = [q for q in course_of if q not in out]
by = {}
for q, (s, p, c) in out.items(): by.setdefault(course_of[q], []).append((s, c))
for sid, v in sorted(by.items()):
    print("%-14s %5d rated | stars %s | conf h/m/l %s" % (sid, len(v), [sum(1 for s, _ in v if s == k) for k in range(1, 6)],
          [sum(1 for _, c in v if c == k) for k in "hml"]))
print("rated %d / %d, missing %d" % (len(out), len(course_of), len(missing)), notes)

# self-check: band edges and the embedded line round-trips
assert [stars(p) for p in (100, 85, 84.9, 70, 69, 50, 49, 30, 29, 0)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
assert helix_data.read_diff() == out
