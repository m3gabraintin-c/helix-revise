# Shared reader/writer for the site's question data, which lives in data/ (not in index.html):
#   data/index.json      catalogue loaded at startup: S (subjects/topics/subtopics), E, C, M, plus N (per-subtopic
#                        [question count, marks]), X (exam-style stubs [id, title, tech, marks, parts, topic slugs] per subject), P (id stem -> subject index), D (rated count)
#   data/<subjectId>.json   that subject's Q {slug: [question]}, X [exam-style questions], T {id: meta}, DIFF {id: [..]}
# read_data() / read_diff() rebuild exactly the DATA and DIFF objects that used to be inlined in index.html.
# write_data(d) / write_diff(diff) split them back into the files. Run `python3 scripts/helix_data.py` for a self-check.
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data")
CATALOGUE = os.path.join(DIR, "index.json")


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def stem(qid):
    return re.sub(r"\d+$", "", qid)  # ids are unique per stem across subjects (checked in write_data)


def _sub2sid(S):
    return {sub[0]: s[0] for s in S for t in s[4] for sub in t[2]}


def _marks(q):
    return sum(p["marks"] for p in q["pieces"] if p.get("kind") == "part") if isinstance(q, dict) else 1


def _qid(q):
    return q["id"] if isinstance(q, dict) else q[0]


def read_catalogue():
    return _load(CATALOGUE)


def read_data():
    cat = read_catalogue()
    d = {"S": cat["S"], "Q": {}, "X": {}, "C": cat["C"], "M": cat["M"], "T": {}, "E": cat["E"]}
    for s in cat["S"]:
        f = _load(os.path.join(DIR, s[0] + ".json"))
        d["Q"].update(f["Q"])
        if "X" in f:
            d["X"][s[0]] = f["X"]
        d["T"].update(f["T"])
    return d


def read_diff():
    out = {}
    for s in read_catalogue()["S"]:
        out.update(_load(os.path.join(DIR, s[0] + ".json")).get("DIFF", {}))
    return out


def write_data(d, diff=None):
    """Split DATA into the files. diff=None keeps the ratings already on disk."""
    os.makedirs(DIR, exist_ok=True)
    if diff is None:
        diff = read_diff() if os.path.exists(CATALOGUE) else {}
    S = d["S"]; sub2sid = _sub2sid(S); sidx = {s[0]: i for i, s in enumerate(S)}
    owner = {}  # question id -> subject id
    for slug, lst in d["Q"].items():
        for q in lst:
            owner[_qid(q)] = sub2sid[slug]
    for sid, lst in d.get("X", {}).items():
        for q in lst:
            owner[q["id"]] = sid
    stems = {}
    for i, sid in owner.items():
        assert stems.setdefault(stem(i), sid) == sid, f"id stem {stem(i)!r} used by two subjects"
    N = {slug: [len(lst), sum(_marks(q) for q in lst)] for slug, lst in d["Q"].items()}
    X = {sid: [[q["id"], q.get("title") or "Multi-part question", q.get("tech") or "", _marks(q), sum(1 for p in q["pieces"] if p.get("kind") == "part"), list(dict.fromkeys(p["topic"] for p in q["pieces"] if p.get("kind") == "part"))] for q in lst]
         for sid, lst in d.get("X", {}).items() if lst}
    diff = {i: v for i, v in diff.items() if i in owner}
    cat = {"S": S, "E": d["E"], "C": d["C"], "M": d["M"], "N": N, "X": X, "P": {k: sidx[v] for k, v in sorted(stems.items())}, "D": len(diff)}
    _dump(CATALOGUE, cat)
    for s in S:
        sid = s[0]
        f = {"Q": {slug: d["Q"][slug] for slug in d["Q"] if sub2sid[slug] == sid}}
        if sid in d.get("X", {}):
            f["X"] = d["X"][sid]
        f["T"] = {i: v for i, v in d["T"].items() if owner.get(i) == sid}
        f["DIFF"] = {i: v for i, v in diff.items() if owner[i] == sid}
        _dump(os.path.join(DIR, sid + ".json"), f)
    assert all(i in owner for i in d["T"]), "T has an id with no question"


def write_diff(diff):
    write_data(read_data(), diff)


if __name__ == "__main__":
    d, df = read_data(), read_diff()
    write_data(d, df)
    assert read_data() == d and read_diff() == df
    print("ok:", len(d["Q"]), "subtopics,", len(d["T"]), "T,", len(df), "DIFF")
