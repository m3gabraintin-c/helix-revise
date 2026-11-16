# Independent check that questions/ matches index.html. Run from anywhere: python3 scripts/verify.py
import json, os, re

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
line = next(l for l in open(os.path.join(repo, "index.html"), encoding="utf-8") if l.startswith("const DATA = "))
d = json.loads(line[len("const DATA = "):].rstrip().rstrip(";"))

expect = {}  # id -> (folder, row)
for sid, name, label, g, T in d["S"]:
    folder = "_unsorted" if label.startswith("GCSE") else name.replace(" ", "-")
    for n, tn, subs in T:
        for slug, sn, tr in subs:
            for r in d["Q"].get(slug, []):
                expect[r[0]] = (folder, r)

root = os.path.join(repo, "questions")
seen_q, seen_a, errs = {}, {}, []
QRE = re.compile(r"^\*\*Q(\d+)\.\*\* (.*)$"); ARE = re.compile(r"^\*\*A(\d+)\.\*\* (.*)$")
IDRE = re.compile(r"^<!-- id: (.+) -->$"); OPT = re.compile(r"^- ([A-Z])\. (.*)$")
folders = sorted(x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)))
for fo in folders:
    ql = open(os.path.join(root, fo, "questions.md"), encoding="utf-8").read().split("\n")
    al = open(os.path.join(root, fo, "answers.md"), encoding="utf-8").read().split("\n")
    qs, as_ = [], []
    i = 0
    while i < len(ql):
        m = QRE.match(ql[i])
        if m:
            idm = IDRE.match(ql[i + 1]); qid = idm.group(1)
            opts = []; j = i + 2
            while j < len(ql) and not QRE.match(ql[j]) and not ql[j].startswith("#"):
                om = OPT.match(ql[j])
                if om: opts.append(om.group(2))
                j += 1
            qs.append((int(m.group(1)), qid, m.group(2), opts)); i = j; continue
        i += 1
    for i, l in enumerate(al):
        m = ARE.match(l)
        if m:
            qid = IDRE.match(al[i + 1]).group(1)
            ex = next(x for x in al[i + 2:i + 6] if x.startswith("Explanation:"))
            as_.append((int(m.group(1)), qid, m.group(2), ex[len("Explanation:"):].lstrip(" ") if ex != "Explanation:" else ""))
    if [q[0] for q in qs] != list(range(1, len(qs) + 1)): errs.append(f"{fo}: Q numbering not 1..N")
    if [a[0] for a in as_] != list(range(1, len(as_) + 1)): errs.append(f"{fo}: A numbering not 1..N")
    if [q[1] for q in qs] != [a[1] for a in as_]: errs.append(f"{fo}: Q/A id order mismatch")
    for n, qid, prompt, opts in qs:
        seen_q[qid] = seen_q.get(qid, 0) + 1
        f, r = expect.get(qid, (None, None))
        if r is None: errs.append(f"{fo} Q{n}: unknown id {qid}"); continue
        if f != fo: errs.append(f"{fo} Q{n}: {qid} expected in {f}")
        if prompt != r[2]: errs.append(f"{fo} Q{n}: prompt differs")
        if r[1] == 0 and opts != r[3]: errs.append(f"{fo} Q{n}: options differ")
    for n, qid, ans, ex in as_:
        seen_a[qid] = seen_a.get(qid, 0) + 1
        f, r = expect.get(qid, (None, None))
        if r is None: continue
        want = f"{chr(65 + r[4])}. {r[3][r[4]]}" if r[1] == 0 else r[3]
        wex = r[5] if r[1] == 0 else r[4]
        if ans != want: errs.append(f"{fo} A{n}: answer differs")
        if ex != wex: errs.append(f"{fo} A{n}: explanation differs")
    print(f"{fo}: {len(qs)} Q / {len(as_)} A")

missing = [k for k in expect if seen_q.get(k) != 1 or seen_a.get(k) != 1]
print("total ids", len(expect), "| Q seen", sum(seen_q.values()), "| A seen", sum(seen_a.values()))
print("missing/duplicated", len(missing), missing[:10])
print("ERRORS", len(errs)); print("\n".join(errs[:30]))
assert not errs and not missing, "verification failed"
print("VERIFIED OK")
