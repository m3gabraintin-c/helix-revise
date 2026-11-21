# Independent check that questions/ matches data/, and that multi-part questions are well formed.
# Run from anywhere: python3 scripts/verify.py
import json, os, re
import helix_data

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = helix_data.read_data()
X = d.get("X", {})
errs = []
TECH = {"free": "Technology-free", "active": "Technology-active (CAS)"}
mk = lambda n: "%d mark%s" % (n, "" if n == 1 else "s")
qid = lambda r: r["id"] if isinstance(r, dict) else r[0]

expect, subj_of, subname = {}, {}, {}  # id -> (folder, row); slug -> subject id; slug -> name
for sid, name, label, g, T in d["S"]:
    folder = "_unsorted" if label.startswith("GCSE") else name.replace(" ", "-")
    for n, tn, subs in T:
        for slug, sn, tr in subs:
            subj_of[slug], subname[slug] = sid, sn
            for r in d["Q"].get(slug, []):
                expect[qid(r)] = (folder, r)
    for r in X.get(sid, []):
        expect[qid(r)] = (folder, r)
for sid in X:
    if not any(s[0] == sid for s in d["S"]): errs.append(f"DATA.X: unknown subject {sid}")

# ---- no string may hold a control character ----
# (A control character usually means a LaTeX backslash was not doubled in the JSON: "\frac" is a form feed plus "rac".)
def strings(o, path):
    if isinstance(o, str): yield path, o
    elif isinstance(o, list):
        for i, x in enumerate(o): yield from strings(x, f"{path}[{i}]")
    elif isinstance(o, dict):
        for k, x in o.items(): yield from strings(x, f"{path}.{k}")
CTRL = re.compile(r"[\x00-\x1f\x7f]")
for path, s in strings({"Q": d["Q"], "X": X}, "DATA"):
    bad = CTRL.search(s)
    if bad: errs.append("%s: control character %r" % (path, bad.group()))
    if s.count("\\(") != s.count("\\)") or s.count("\\[") != s.count("\\]"): errs.append(f"{path}: unbalanced \\( \\) or \\[ \\]")
ids = [qid(r) for rows in d["Q"].values() for r in rows] + [qid(r) for rows in X.values() for r in rows]
if len(ids) != len(set(ids)): errs.append("duplicate question ids across DATA.Q and DATA.X")
# DATA.C lists the ids of challenge questions (shown with a "Challenge" tag); every id must exist, once.
CH = d.get("C", [])
if not isinstance(CH, list) or len(CH) != len(set(CH)): errs.append("DATA.C must be a list of unique question ids")
elif set(CH) - set(ids): errs.append(f"DATA.C has unknown ids: {sorted(set(CH) - set(ids))[:5]}")
CH = set(CH) if isinstance(CH, list) else set()

# ---- question info: DATA.M (per subtopic), DATA.T (per question), DATA.E (per subject) ----
M, T, E = d.get("M", {}), d.get("T", {}), d.get("E", {})
QTYPES = {"recall": "Recall", "concept": "Conceptual", "calc": "Calculation", "apply": "Application", "data": "Data analysis",
          "eval": "Evaluation", "proof": "Proof", "design": "Investigation design", "text": "Text analysis", "write": "Extended writing",
          "read": "Reading comprehension", "lang": "Language use", "speak": "Speaking"}
isint = lambda x: isinstance(x, int) and not isinstance(x, bool)
loc_of = {qid(r): slug for slug, rows in d["Q"].items() for r in rows}
for sid, *_ in d["S"]:
    e = E.get(sid)
    if not (isinstance(e, dict) and isinstance(e.get("w"), list) and len(e["w"]) == 3 and all(isinstance(e.get(k), str) and e[k] for k in ("mcq", "short", "multi"))
            and all(isinstance(x, str) and x for x in e["w"]) and set(e) <= {"w", "mcq", "short", "multi", "free"}):
        errs.append(f"DATA.E[{sid}]: needs w (three strings), mcq, short and multi (and optionally free)")
for slug in subj_of:
    m = M.get(slug)
    if m is None:
        if not slug.endswith("-challenge"): errs.append(f"DATA.M: no entry for subtopic {slug}")
        continue
    if not (isinstance(m, list) and len(m) in (3, 4) and isint(m[0]) and 1 <= m[0] <= 3 and isinstance(m[1], list) and isinstance(m[2], str)
            and (len(m) == 3 or (isinstance(m[3], str) and m[3]))):
        errs.append(f"DATA.M[{slug}]: must be [weight 1-3, [prerequisite slugs], prior knowledge, format note?]"); continue
    for x in m[1]:
        if x not in subj_of or x == slug: errs.append(f"DATA.M[{slug}]: bad prerequisite {x}")
if set(M) - set(subj_of): errs.append(f"DATA.M has unknown subtopics: {sorted(set(M) - set(subj_of))[:5]}")
xrows = {qid(r): r for rows in X.values() for r in rows}
for i in ids:
    t, r = T.get(i), (xrows.get(i) or next(rr for rr in d["Q"][loc_of[i]] if qid(rr) == i))
    if t is None: errs.append(f"DATA.T: no entry for {i}"); continue
    types = t[0] if isinstance(t[0], list) else [t[0]] if isinstance(t, list) and t else None
    if not (isinstance(t, list) and len(t) in (3, 4) and types and all(x in QTYPES for x in types) and len(set(types)) == len(types)
            and isint(t[1]) and t[1] >= 0 and isinstance(t[2], (int, float)) and not isinstance(t[2], bool) and t[2] > 0):
        errs.append(f"DATA.T[{i}]: must be [type or [types], exam marks, minutes, topic?] with types from {list(QTYPES)}"); continue
    if isinstance(r, dict):
        if t[1] != sum(p["marks"] for p in r["pieces"] if p.get("kind") == "part"): errs.append(f"DATA.T[{i}]: marks must equal the sum of the parts")
    elif r[1] == 0 and t[1] != 1: errs.append(f"DATA.T[{i}]: a multiple-choice question is worth 1 mark")
    elif r[1] == 1 and t[1] == 0 and t[0] != "speak": errs.append(f"DATA.T[{i}]: only speaking questions may have 0 marks")
    in_set = i in loc_of and loc_of[i].endswith("-challenge")
    if in_set != (len(t) == 4): errs.append(f"DATA.T[{i}]: Challenge-set questions (and only those) give the topic they test")
    elif in_set:
        if t[3] in subj_of:
            if subj_of[t[3]] != subj_of[loc_of[i]] or t[3].endswith("-challenge"): errs.append(f"DATA.T[{i}]: topic {t[3]} is not a subtopic of this subject")
        elif not (isinstance(t[3], str) and t[3].strip() and loc_of[i] in M): errs.append(f"DATA.T[{i}]: a topic that is not a subtopic needs DATA.M[{loc_of[i]}]")
if set(T) - set(ids): errs.append(f"DATA.T has unknown ids: {sorted(set(T) - set(ids))[:5]}")

# ---- multi-part question structure ----
LABEL = re.compile(r"^[a-z](\.[ivx]+)?$")
def check_multi(r, where, subject):
    w = f"{where} {r.get('id')}"
    for f in ("id", "title", "source"):
        if not (isinstance(r.get(f), str) and r[f].strip()): errs.append(f"{w}: missing {f}")
    if r.get("type") != "multi": errs.append(f"{w}: type must be 'multi'")
    if "tech" in r and r["tech"] not in TECH: errs.append(f"{w}: tech must be one of {list(TECH)}")
    if set(r) - {"id", "type", "title", "source", "tech", "steps_label", "pieces"}: errs.append(f"{w}: unknown fields {set(r) - {'id', 'type', 'title', 'source', 'tech', 'steps_label', 'pieces'}}")
    if "steps_label" in r and not (isinstance(r["steps_label"], str) and r["steps_label"].strip()): errs.append(f"{w}: steps_label must be a non-empty string")
    pieces = r.get("pieces")
    if not (isinstance(pieces, list) and pieces): errs.append(f"{w}: no pieces"); return
    labels = []
    for k, p in enumerate(pieces):
        pw = f"{w} piece {k}"
        if p.get("kind") == "info":
            if set(p) - {"kind", "text", "table", "diagram"}: errs.append(f"{pw}: unknown fields")
            if not any(p.get(f) for f in ("text", "table", "diagram")): errs.append(f"{pw}: empty info")
            if "text" in p and not (isinstance(p["text"], str) and p["text"].strip()): errs.append(f"{pw}: text must be non-empty")
            if "table" in p:
                rows = p["table"].get("rows") if isinstance(p["table"], dict) else None
                if not (rows and all(isinstance(x, list) and len(x) == len(rows[0]) and all(isinstance(c, str) and "|" not in c for c in x) for x in rows)):
                    errs.append(f"{pw}: table.rows must be equal-length lists of strings without '|'")
            if "diagram" in p:
                dg = p["diagram"]
                if not (isinstance(dg, dict) and isinstance(dg.get("svg"), str) and isinstance(dg.get("alt"), str) and dg["alt"].strip()): errs.append(f"{pw}: diagram needs svg and alt")
                else:
                    sv = dg["svg"]
                    if not (sv.startswith("<svg") and sv.endswith("</svg>") and 'aria-hidden="true"' in sv): errs.append(f"{pw}: diagram svg must be one <svg aria-hidden=\"true\"> element")
                    if re.search(r"<script|<foreignObject|\son\w+\s*=|javascript:|href", sv, re.I): errs.append(f"{pw}: diagram svg has scripts, event handlers or links")
        elif p.get("kind") == "part":
            if set(p) - {"sample"} != {"kind", "label", "question", "marks", "answer", "steps", "mistake", "topic"}: errs.append(f"{pw}: fields must be kind, label, question, marks, answer, steps, mistake, topic (and optionally sample)")
            if "sample" in p and not (isinstance(p["sample"], list) and p["sample"] and all(isinstance(x, str) and x.strip() for x in p["sample"])): errs.append(f"{pw}: sample must be a non-empty list of paragraphs")
            for f in ("question", "answer", "mistake"):
                if not (isinstance(p.get(f), str) and p[f].strip()): errs.append(f"{pw}: missing {f}")
            if not (isinstance(p.get("label"), str) and LABEL.match(p["label"])): errs.append(f"{pw}: label must look like a, b or e.i")
            labels.append(p.get("label"))
            m = p.get("marks")
            if not (isinstance(m, int) and not isinstance(m, bool) and m >= 1): errs.append(f"{pw}: marks must be a positive whole number"); continue
            st = p.get("steps")
            if not (isinstance(st, list) and st and all(isinstance(x, dict) and set(x) == {"working", "marks"} and isinstance(x["working"], str) and x["working"].strip()
                                                       and isinstance(x["marks"], int) and not isinstance(x["marks"], bool) and x["marks"] >= 0 for x in st)):
                errs.append(f"{pw}: steps must be a list of {{working, marks}}"); continue
            if sum(x["marks"] for x in st) != m: errs.append(f"{pw}: step marks add to {sum(x['marks'] for x in st)}, part is worth {m}")
            if p.get("topic") not in subj_of: errs.append(f"{pw}: unknown topic {p.get('topic')}")
            elif subj_of[p["topic"]] != subject: errs.append(f"{pw}: topic {p['topic']} is not in subject {subject}")
        else:
            errs.append(f"{pw}: kind must be info or part")
    if not labels: errs.append(f"{w}: no parts")
    if len(labels) != len(set(labels)): errs.append(f"{w}: repeated part labels")
for slug, rows in d["Q"].items():
    for r in rows:
        if isinstance(r, dict): check_multi(r, f"DATA.Q[{slug}]", subj_of.get(slug))
for sid, rows in X.items():
    for r in rows:
        if isinstance(r, dict): check_multi(r, f"DATA.X[{sid}]", sid)
        else: errs.append(f"DATA.X[{sid}]: exam-style questions must be multi-part objects")
if errs:  # the markdown comparison below assumes well-formed rows
    print("ERRORS", len(errs)); print("\n".join(errs[:30])); raise SystemExit("verification failed")

# ---- questions/ files against DATA ----
root = os.path.join(repo, "questions")
seen_q, seen_a = {}, {}
QRE = re.compile(r"^\*\*Q(\d+)\.\*\* (.*)$"); ARE = re.compile(r"^\*\*A(\d+)\.\*\* (.*)$")
IDRE = re.compile(r"^<!-- id: (.+) -->$"); OPT = re.compile(r"^- ([A-Z])\. (.*)$")
PART = re.compile(r"^\*\*([a-z](?:\.[ivx]+)?)\.\*\* (.*) \*\((\d+) marks?\)\*$")
STEP = re.compile(r"^(\d+)\. (.*?)(?: \*\((\d+) marks?\)\*)?$")

def blocks(lines, head):
    # [number, head text, id, lines after the id line]; a block ends at the next marker or heading
    out, cur = [], None
    for i, l in enumerate(lines):
        m = head.match(l)
        if m:
            idm = IDRE.match(lines[i + 1]) if i + 1 < len(lines) else None
            cur = [int(m.group(1)), m.group(2), idm.group(1) if idm else None, []]; out.append(cur)
        elif l.startswith("#"): cur = None
        elif cur is not None and not IDRE.match(l): cur[3].append(l)
    return out

def multi_q_tokens(r):
    meta = "*%s*" % " · ".join(x for x in ("Multi-part question", mk(sum(p["marks"] for p in r["pieces"] if p["kind"] == "part")), TECH.get(r.get("tech"), ""), r["source"]) if x)
    toks = [("meta", meta)]
    for p in r["pieces"]:
        if p["kind"] == "part": toks.append(("part", p["label"], p["question"], p["marks"]))
        else:
            if p.get("text"): toks.append(("text", p["text"]))
            if p.get("table"): toks.append(("table", p["table"]["rows"]))
            if p.get("diagram"): toks.append(("diagram", p["diagram"]["alt"]))
    return toks
def parse_multi_q(lines):
    toks, table = [], None
    for l in [x for x in lines if x.strip()]:
        if l.startswith("|"):
            if re.match(r"^\|( --- \|)+$", l): continue
            cells = [c.strip() for c in l.strip("|").split(" | ")]
            if table is None: table = []; toks.append(("table", table))
            table.append(cells); continue
        table = None
        pm, dm = PART.match(l), re.match(r"^\*\[Diagram: (.*)\]\*$", l)
        if not toks: toks.append(("meta", l))
        elif pm: toks.append(("part", pm.group(1), pm.group(2), int(pm.group(3))))
        elif dm: toks.append(("diagram", dm.group(1)))
        else: toks.append(("text", l))
    return toks
def parse_multi_a(lines):
    lines = [x for x in lines if x.strip()]
    meta, parts = lines[0], []
    for l in lines[1:]:
        pm, sm = PART.match(l), STEP.match(l)
        if pm: parts.append({"label": pm.group(1), "answer": pm.group(2), "marks": int(pm.group(3)), "steps": [], "mistake": None, "topic": None})
        elif l in ("Sample response:", ">"): continue
        elif l.startswith("> "): parts[-1].setdefault("sample", []).append(l[2:])
        elif l.startswith("Common mistake: "): parts[-1]["mistake"] = l[len("Common mistake: "):]
        elif l.startswith("Topic: "): parts[-1]["topic"] = re.search(r"\(([^()]+)\)$", l).group(1)
        elif sm: parts[-1]["steps"].append({"working": sm.group(2), "marks": int(sm.group(3) or 0)})
        else: parts.append({"stray": l})
    return meta, parts

# The expected "*Info: ...*" line under each question in questions.md, built independently of scripts/build_questions.py.
REL = ["Low", "Medium", "High"]
low = lambda s: s[:1].lower() + s[1:]
xsubj = {qid(r): sid for sid, rows in X.items() for r in rows}
def want_info(i, r):
    t = T[i]; types = t[0] if isinstance(t[0], list) else [t[0]]
    kind = "multi" if isinstance(r, dict) else "mcq" if r[1] == 0 else "short"
    if i in loc_of:
        sid = subj_of[loc_of[i]]
        m = M[t[3]] if len(t) == 4 and t[3] in subj_of else M[loc_of[i]]
        w, note = m[0], (m[3] if len(m) == 4 else "")
    else:
        sid = xsubj[i]; ps = [p for p in r["pieces"] if p["kind"] == "part"]
        w = int(sum(M[p["topic"]][0] * p["marks"] for p in ps) / sum(p["marks"] for p in ps) + 0.5); note = ""
    e = E[sid]
    fmt = note or (e["free"] if kind == "multi" and r.get("tech") == "free" and "free" in e else e[kind])
    rel = [f"{REL[w - 1]} ({low(e['w'][w - 1])})", low(fmt)] + (["harder than most exam questions"] if i in CH else [])
    marks = ("marked as part of the conversation" if t[1] == 0 else "about " + mk(t[1])) if kind == "short" else mk(t[1])
    bits = [", ".join(QTYPES[x] for x in types), marks, "about %g min" % t[2], "Exam relevance: " + "; ".join(rel)]
    if len(t) == 4: bits.append("Topic: " + (subname[t[3]] if t[3] in subj_of else t[3]))
    if i not in loc_of: bits.append("Topics: " + ", ".join(dict.fromkeys(subname[p["topic"]] for p in r["pieces"] if p["kind"] == "part")))
    return "*Info: %s*" % " · ".join(bits)

folders = sorted(x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)))
for fo in folders:
    qs = blocks(open(os.path.join(root, fo, "questions.md"), encoding="utf-8").read().split("\n"), QRE)
    as_ = blocks(open(os.path.join(root, fo, "answers.md"), encoding="utf-8").read().split("\n"), ARE)
    if [q[0] for q in qs] != list(range(1, len(qs) + 1)): errs.append(f"{fo}: Q numbering not 1..N")
    if [a[0] for a in as_] != list(range(1, len(as_) + 1)): errs.append(f"{fo}: A numbering not 1..N")
    if [q[2] for q in qs] != [a[2] for a in as_]: errs.append(f"{fo}: Q/A id order mismatch")
    for n, head, id_, body in qs:
        seen_q[id_] = seen_q.get(id_, 0) + 1
        f, r = expect.get(id_, (None, None))
        if r is None: errs.append(f"{fo} Q{n}: unknown id {id_}"); continue
        if f != fo: errs.append(f"{fo} Q{n}: {id_} expected in {f}")
        marked = "*Challenge question*" in body
        if marked != (id_ in CH): errs.append(f"{fo} Q{n}: challenge marker {'present' if marked else 'missing'} for {id_}")
        body = [x for x in body if x != "*Challenge question*"]
        infos = [x for x in body if x.startswith("*Info: ")]
        if infos != [want_info(id_, r)]: errs.append(f"{fo} Q{n}: info line differs for {id_}")
        body = [x for x in body if not x.startswith("*Info: ")]
        if isinstance(r, dict):
            if head != r["title"]: errs.append(f"{fo} Q{n}: title differs")
            if parse_multi_q(body) != multi_q_tokens(r): errs.append(f"{fo} Q{n}: multi-part question text differs")
            continue
        if head != r[2]: errs.append(f"{fo} Q{n}: prompt differs")
        opts = [OPT.match(x).group(2) for x in body if OPT.match(x)]
        if r[1] == 0 and opts != r[3]: errs.append(f"{fo} Q{n}: options differ")
    for n, head, id_, body in as_:
        seen_a[id_] = seen_a.get(id_, 0) + 1
        f, r = expect.get(id_, (None, None))
        if r is None: continue
        if isinstance(r, dict):
            if head != r["title"]: errs.append(f"{fo} A{n}: title differs")
            meta, parts = parse_multi_a(body)
            want = [{"label": p["label"], "answer": p["answer"], "marks": p["marks"], "steps": p["steps"], "mistake": p["mistake"], "topic": p["topic"], **({"sample": p["sample"]} if p.get("sample") else {})} for p in r["pieces"] if p["kind"] == "part"]
            if meta != "*Multi-part question · %s*" % mk(sum(p["marks"] for p in want)): errs.append(f"{fo} A{n}: header differs")
            if parts != want: errs.append(f"{fo} A{n}: multi-part answers differ")
            continue
        exl = next((x for x in body if x.startswith("Explanation:")), None)
        if exl is None: errs.append(f"{fo} A{n}: no Explanation line"); continue
        ex = exl[len("Explanation:"):].lstrip(" ") if exl != "Explanation:" else ""
        want = f"{chr(65 + r[4])}. {r[3][r[4]]}" if r[1] == 0 else r[3]
        wex = r[5] if r[1] == 0 else r[4]
        if head != want: errs.append(f"{fo} A{n}: answer differs")
        if ex != wex: errs.append(f"{fo} A{n}: explanation differs")
    nm = sum(isinstance(expect.get(q[2], (0, 0))[1], dict) for q in qs)
    print(f"{fo}: {len(qs)} Q / {len(as_)} A" + (f" ({nm} multi-part)" if nm else ""))

missing = [k for k in expect if seen_q.get(k) != 1 or seen_a.get(k) != 1]
print("total ids", len(expect), "| Q seen", sum(seen_q.values()), "| A seen", sum(seen_a.values()))
print("missing/duplicated", len(missing), missing[:10])
print("ERRORS", len(errs)); print("\n".join(errs[:30]))
assert not errs and not missing, "verification failed"
print("VERIFIED OK")
