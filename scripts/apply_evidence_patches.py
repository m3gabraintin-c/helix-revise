# Apply worker patch files to one evidence pack, then fill checked_via and recompute base_rates (prints one JSON line).
#   python3 scripts/apply_evidence_patches.py <pack>
# Patch files: difficulty/work/evidence/<pack>/*.json = {"patches": {"<eid>": {"<field>": value, ...}}}
# Only the fields in ALLOWED can change; numbers (pct_correct, mean_mark, marks) and urls never come from a patch.
# Applied patch files are renamed *.applied so a re-run does not apply them twice.
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = {"skill", "examiner_note", "area", "verified", "verify_note", "verified_by", "key_unconfirmed", "key_note"}

def apply(pack):
    path = os.path.join(ROOT, "difficulty", "evidence", pack + ".json")
    p = json.load(open(path, encoding="utf-8"))
    by = {e["eid"]: e for e in p["entries"]}
    applied, rejected = 0, []
    for f in sorted(glob.glob(os.path.join(ROOT, "difficulty", "work", "evidence", pack, "*.json"))):
        try: patches = json.load(open(f, encoding="utf-8"))["patches"]
        except (ValueError, KeyError, TypeError): rejected.append(os.path.basename(f) + ": unreadable"); continue
        for eid, fields in patches.items():
            if eid not in by or not isinstance(fields, dict): rejected.append(eid); continue
            bad = set(fields) - ALLOWED
            if bad or ("verified" in fields and not isinstance(fields["verified"], bool)): rejected.append("%s: %s" % (eid, sorted(bad) or "verified")); continue
            by[eid].update(fields); applied += 1
        os.rename(f, f + ".applied")
    ip = os.path.join(ROOT, "difficulty", "reports", pack, "index.json")
    idx = json.load(open(ip)) if os.path.exists(ip) else {}
    for e in p["entries"]:  # where each verified number was checked: the exact cached copy
        if "verified" in e and str(e.get("checked_via", "unrecorded")).startswith("unrecorded"):
            e["checked_via"] = (idx.get(e["url"]) or {}).get("fetched_from") or "unrecorded"
    ok = [e for e in p["entries"] if e.get("verified") is True]
    pct = lambda e: e["pct_correct"] if e.get("pct_correct") is not None else (100 * e["mean_mark"] / e["marks"] if e.get("mean_mark") is not None and e.get("marks") else None)
    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    areas = {}
    for e in ok:
        if pct(e) is not None: areas.setdefault(e.get("area") or "Unclassified", []).append(pct(e))
    p["base_rates"] = {"mcq_mean_pct": mean([pct(e) for e in ok if e["format"] == "mcq" and pct(e) is not None]),
                       "written_mean_pct_of_marks": mean([pct(e) for e in ok if e["format"] == "written" and pct(e) is not None]),
                       "by_area": {a: mean(v) for a, v in sorted(areas.items())}, "n_entries": len(ok),
                       "method": "Recomputed by scripts/apply_evidence_patches.py from verified entries only (written: mean_mark / marks)."}
    json.dump(p, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"pack": pack, "applied": applied, "rejected": rejected[:20], "verified_true": len(ok), "entries": len(p["entries"])}

if __name__ == "__main__":
    print(json.dumps(apply(sys.argv[1])))
