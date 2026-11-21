# Regenerate questions/ from the question data in data/ (see scripts/helix_data.py). Run from anywhere: python3 scripts/build_questions.py
import json, math, os, re, shutil
import helix_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "questions")
d = helix_data.read_data()
X = d.get("X", {})  # exam-style questions: {subjectId: [multi-part question]}
GCSE_REASON = "GCSE Edexcel Biology, not a VCE subject — needs your decision."
LET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
UNIT_ORDER = {"VCE · Units 1 & 2": 0, "VCE · Units 3 & 4": 1}
TECH = {"free": "Technology-free", "active": "Technology-active (CAS)"}
SUBNAME = {slug: name for s in d["S"] for _, _, subs in s[4] for slug, name, _ in subs}

# folder -> subjects; GCSE goes to _unsorted, VCE units merge into one folder per subject
folders = {}
for s in d["S"]:
    folders.setdefault("_unsorted" if s[2].startswith("GCSE") else s[1].replace(" ", "-"), []).append(s)
for k, ss in folders.items():
    if k != "_unsorted":
        ss.sort(key=lambda s: UNIT_ORDER[s[2]])

# Multi-part questions are objects with named fields; MCQ and written questions are positional arrays.
def mk(n): return "%d mark%s" % (n, "" if n == 1 else "s")
def mparts(r): return [p for p in r["pieces"] if p["kind"] == "part"]
def mtotal(r): return sum(p["marks"] for p in mparts(r))

def mq_body(r):
    s = "*%s*\n\n" % " · ".join(x for x in ("Multi-part question", mk(mtotal(r)), TECH.get(r.get("tech"), ""), r["source"]) if x)
    for p in r["pieces"]:
        if p["kind"] == "part":
            s += "**%s.** %s *(%s)*\n\n" % (p["label"], p["question"], mk(p["marks"]))
            continue
        if p.get("text"): s += p["text"] + "\n\n"
        if p.get("table"):
            rows = p["table"]["rows"]
            s += "| %s |\n|%s\n" % (" | ".join(rows[0]), " --- |" * len(rows[0]))
            s += "".join("| %s |\n" % " | ".join(row) for row in rows[1:]) + "\n"
        if p.get("diagram"): s += "*[Diagram: %s]*\n\n" % p["diagram"]["alt"]
    return s

def ma_body(r):
    s = "*Multi-part question · %s*\n\n" % mk(mtotal(r))
    for p in mparts(r):
        s += "**%s.** %s *(%s)*\n\n" % (p["label"], p["answer"], mk(p["marks"]))
        if p.get("sample"):  # essay or writing-task sample response, as one blockquote of paragraphs
            s += "Sample response:\n\n" + "\n>\n".join("> " + x for x in p["sample"]) + "\n\n"
        s += "".join("%d. %s%s\n" % (k + 1, st["working"], " *(%s)*" % mk(st["marks"]) if st["marks"] else "") for k, st in enumerate(p["steps"])) + "\n"
        s += "Common mistake: %s\n\nTopic: %s (%s)\n\n" % (p["mistake"], SUBNAME[p["topic"]], p["topic"])
    return s

CH = set(d.get("C", []))  # ids of challenge questions, marked in questions.md
CHL = "*Challenge question*\n"

# ---- question info: DATA.M (per subtopic), DATA.T (per question), DATA.E (per subject) ----
M, T, E = d.get("M", {}), d.get("T", {}), d.get("E", {})
SUBJ = {slug: s[0] for s in d["S"] for _, _, subs in s[4] for slug, _, _ in subs}
SLUG = {(r["id"] if isinstance(r, dict) else r[0]): slug for slug, rows in d["Q"].items() for r in rows}
SUBJ_LABEL = {s[0]: "%s, %s" % (s[1], s[2].split(" · ", 1)[-1]) for s in d["S"]}
QTYPES = {"recall": "Recall", "concept": "Conceptual", "calc": "Calculation", "apply": "Application", "data": "Data analysis",
          "eval": "Evaluation", "proof": "Proof", "design": "Investigation design", "text": "Text analysis", "write": "Extended writing",
          "read": "Reading comprehension", "lang": "Language use", "speak": "Speaking"}
REL = ["Low", "Medium", "High"]
lc = lambda s: s[:1].lower() + s[1:]
num = lambda x: ("%g" % x)
def kind_of(r): return "multi" if isinstance(r, dict) else "mcq" if r[1] == 0 else "short"
def marks_text(r, t):
    k = kind_of(r)
    if k == "short": return "marked as part of the conversation" if t[1] == 0 else "about " + mk(t[1])
    return mk(t[1])
def topic_slug(qid):
    t, loc = T[qid], SLUG.get(qid)
    return t[3] if len(t) > 3 and t[3] in SUBJ else loc
def relevance(r, sid):
    qid = r["id"] if isinstance(r, dict) else r[0]
    loc = SLUG.get(qid)
    if loc:  # a subtopic question (a Challenge-set question uses the subtopic it tests)
        m = M.get(topic_slug(qid)) or M[loc]; w, note = m[0], (m[3] if len(m) > 3 else "")
    else:  # an exam-style question: the marks-weighted mean of its parts' subtopics
        ps = mparts(r); w = int(math.floor(sum(M[p["topic"]][0] * p["marks"] for p in ps) / sum(p["marks"] for p in ps) + 0.5)); note = ""
    e = E[sid]; k = kind_of(r)
    fmt = note or (e["free"] if k == "multi" and r.get("tech") == "free" and e.get("free") else e[k])
    return "; ".join(["%s (%s)" % (REL[w - 1], lc(e["w"][w - 1])), lc(fmt)] + (["harder than most exam questions"] if qid in CH else []))
def info_line(r, sid):
    qid = r["id"] if isinstance(r, dict) else r[0]
    t = T[qid]; types = t[0] if isinstance(t[0], list) else [t[0]]
    bits = [", ".join(QTYPES[x] for x in types), marks_text(r, t), "about %s min" % num(t[2]), "Exam relevance: " + relevance(r, sid)]
    if len(t) > 3: bits.append("Topic: " + (SUBNAME[t[3]] if t[3] in SUBJ else t[3]))
    if not SLUG.get(qid): bits.append("Topics: " + ", ".join(dict.fromkeys(SUBNAME[p["topic"]] for p in mparts(r))))
    return "*Info: %s*\n" % " · ".join(bits)
def sub_line(slug):
    m = M.get(slug)
    if not m: return ""
    pre = ["%s%s" % (SUBNAME[x], "" if SUBJ[x] == SUBJ[slug] else " (%s)" % SUBJ_LABEL[SUBJ[x]]) for x in m[1]] + ([m[2]] if m[2] else [])
    return "*Exam relevance: %s (%s) · Prerequisites: %s*\n\n" % (REL[m[0] - 1], lc(E[SUBJ[slug]]["w"][m[0] - 1]), "; ".join(pre) if pre else "none")

def qblock(n, r, sid):
    if isinstance(r, dict):
        return "**Q%d.** %s\n<!-- id: %s -->\n" % (n, r["title"], r["id"]) + (CHL if r["id"] in CH else "") + info_line(r, sid) + mq_body(r)
    s = "**Q%d.** %s\n<!-- id: %s -->\n" % (n, r[2], r[0])
    if r[0] in CH: s += CHL
    if r[-1]: s += "*Higher tier only*\n"
    s += info_line(r, sid)
    if r[1] == 0:
        return s + "\n" + "\n".join("- %s. %s" % (LET[i], o) for i, o in enumerate(r[3])) + "\n\n"
    return s + "\n*Written answer*\n\n"

def ablock(n, r):
    if isinstance(r, dict):
        return "**A%d.** %s\n<!-- id: %s -->\n" % (n, r["title"], r["id"]) + ma_body(r)
    a, ex = ("%s. %s" % (LET[r[4]], r[3][r[4]]), r[5]) if r[1] == 0 else (r[3], r[4])
    return "**A%d.** %s\n<!-- id: %s -->\n\nExplanation:%s\n\n" % (n, a, r[0], (" " + ex) if ex else "")

def render(k, kind):
    title = "Unsorted" if k == "_unsorted" else k.replace("-", " ")
    if kind == "q":
        t = "# %s — Questions\n\nAnswers: [answers.md](answers.md). Question numbers match answer numbers.\n\n" % title
    else:
        t = "# %s — Answers\n\nQuestions: [questions.md](questions.md). Answer numbers match question numbers.\n\n" % title
    if k == "_unsorted":
        t += "Not placed in a VCE subject folder. Reason per section below.\n\n"
    order = []
    for s in folders[k]:
        t += "## %s\n\n" % s[2].replace(" · ", " ")
        if k == "_unsorted": t += "Reason: %s\n\n" % GCSE_REASON
        for num, tname, subtopics in s[4]:
            t += "### %s\n\n" % tname
            for slug, stname, triple in subtopics:
                t += "#### %s\n\n" % (stname + (" *(Triple only)*" if triple else ""))
                if kind == "q": t += sub_line(slug)
                for r in d["Q"].get(slug, []):
                    order.append(r)
                    t += qblock(len(order), r, s[0]) if kind == "q" else ablock(len(order), r)
        if X.get(s[0]):
            t += "### Exam-style questions (mixed topics)\n\n"
            for r in X[s[0]]:
                order.append(r)
                t += qblock(len(order), r, s[0]) if kind == "q" else ablock(len(order), r)
    return t.rstrip("\n") + "\n", order

if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
counts, orders = {}, {}
for k in sorted(folders, key=lambda x: (x == "_unsorted", x)):
    os.makedirs(os.path.join(OUT, k))
    qt, qo = render(k, "q"); at, ao = render(k, "a")
    rid = lambda r: r["id"] if isinstance(r, dict) else r[0]
    assert [rid(r) for r in qo] == [rid(r) for r in ao]
    open(os.path.join(OUT, k, "questions.md"), "w", encoding="utf-8").write(qt)
    open(os.path.join(OUT, k, "answers.md"), "w", encoding="utf-8").write(at)
    counts[k], orders[k] = len(qo), qo

rd = "# Questions\n\nThese files are generated from the data/ files; question and answer text is verbatim. Maths is written in LaTeX between \\( \\) or \\[ \\], which the website typesets.\n\n"
for k, c in counts.items():
    nm = sum(isinstance(r, dict) for r in orders[k])
    rd += "- [%s](%s/questions.md) — %d questions%s ([answers](%s/answers.md))\n" % (k, k, c, " (%d multi-part)" % nm if nm else "", k)
open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(rd)

# ---- self-check: parse files back and compare with the source ----
allq = [r for rows in d["Q"].values() for r in rows] + [r for rows in X.values() for r in rows]
allrows = {(r["id"] if isinstance(r, dict) else r[0]): r for r in allq}
tot = len(allq)
assert len(allrows) == tot, "duplicate question ids in DATA"
mark = re.compile(r"^\*\*([QA])(\d+)\.\*\* ", re.M)
seen = {"q": [], "a": []}
for k in counts:
    for kind, fn in (("q", "questions.md"), ("a", "answers.md")):
        text = open(os.path.join(OUT, k, fn), encoding="utf-8").read()
        ms = list(mark.finditer(text))
        assert len(ms) == counts[k], (k, fn, len(ms))
        for i, m in enumerate(ms):
            assert m.group(1) == kind.upper() and int(m.group(2)) == i + 1, (k, fn, i)
            body = text[m.end():ms[i + 1].start() if i + 1 < len(ms) else len(text)]
            mm = re.match(r"(?s)(.*?)\n<!-- id: (.*?) -->\n(.*)", body)
            assert mm, (k, fn, i)
            pre, id_, rest = mm.groups()
            r = orders[k][i]
            assert id_ == (r["id"] if isinstance(r, dict) else r[0]), (k, fn, i)
            seen[kind].append(id_)
            r = allrows[id_]
            sid = SUBJ[SLUG[id_]] if id_ in SLUG else next(k for k, v in X.items() if r in v)
            if isinstance(r, dict):
                assert pre == r["title"]
                exp = ((CHL if id_ in CH else "") + info_line(r, sid) + mq_body(r) if kind == "q" else ma_body(r)).rstrip("\n")
            elif kind == "q":
                assert pre == r[2]
                exp = (CHL if id_ in CH else "") + ("*Higher tier only*\n" if r[-1] else "") + info_line(r, sid) + "\n"
                exp += "\n".join("- %s. %s" % (LET[j], o) for j, o in enumerate(r[3])) if r[1] == 0 else "*Written answer*"
            else:
                assert pre == ("%s. %s" % (LET[r[4]], r[3][r[4]]) if r[1] == 0 else r[3])
                exp = "\nExplanation:" + ((" " + (r[5] if r[1] == 0 else r[4])) if (r[5] if r[1] == 0 else r[4]) else "")
            assert rest.startswith(exp) and rest[len(exp):][:1] in ("", "\n"), (k, fn, i)
for kind in seen:
    assert len(seen[kind]) == tot and set(seen[kind]) == set(allrows), kind
for k, c in counts.items(): print(k, c)
print("TOTAL", sum(counts.values()))
print("SELF-CHECK PASSED")
