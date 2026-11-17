# Regenerate questions/ from the DATA block in index.html. Run from anywhere: python3 scripts/build_questions.py
import json, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "questions")
PREFIX = "const DATA = "
line = next(l for l in open(os.path.join(ROOT, "index.html"), encoding="utf-8") if l.startswith(PREFIX))
d = json.loads(line[len(PREFIX):].rstrip().rstrip(";"))
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

def qblock(n, r):
    if isinstance(r, dict):
        return "**Q%d.** %s\n<!-- id: %s -->\n" % (n, r["title"], r["id"]) + (CHL if r["id"] in CH else "") + mq_body(r)
    s = "**Q%d.** %s\n<!-- id: %s -->\n" % (n, r[2], r[0])
    if r[0] in CH: s += CHL
    if r[-1]: s += "*Higher tier only*\n"
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
                for r in d["Q"].get(slug, []):
                    order.append(r)
                    t += qblock(len(order), r) if kind == "q" else ablock(len(order), r)
        if X.get(s[0]):
            t += "### Exam-style questions (mixed topics)\n\n"
            for r in X[s[0]]:
                order.append(r)
                t += qblock(len(order), r) if kind == "q" else ablock(len(order), r)
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

rd = "# Questions\n\nThese files are generated from index.html's DATA; question and answer text is verbatim. Maths is written in LaTeX between \\( \\) or \\[ \\], which the website typesets.\n\n"
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
            if isinstance(r, dict):
                assert pre == r["title"]
                exp = ((CHL if id_ in CH else "") + mq_body(r) if kind == "q" else ma_body(r)).rstrip("\n")
            elif kind == "q":
                assert pre == r[2]
                exp = (CHL if id_ in CH else "") + ("*Higher tier only*\n" if r[-1] else "") + "\n"
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
