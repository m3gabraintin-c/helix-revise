# Download every report cited in difficulty/evidence/*.json into difficulty/reports/<pack>/ so the verifier can read it
# locally. Tries the live VCAA URL, then the Internet Archive raw copy. .docx reports also get a .txt copy (tables kept
# as "a | b | c" rows) because agents cannot open .docx. Run: python3 scripts/fetch_reports.py
import base64, glob, hashlib, json, os, sys, re, subprocess, zipfile
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURL = ["curl", "-sfL", "--retry", "6", "--retry-all-errors", "--retry-delay", "5"]  # archive.org refuses connections in bursts

def get(u):
    # curl, not urllib: macOS python.org builds often lack CA certs
    r = subprocess.run(CURL + ["--max-time", "120", u], capture_output=True)
    return r.stdout if r.returncode == 0 and r.stdout[:4] in (b"%PDF", b"PK\x03\x04") else None  # maintenance pages are HTML

def captures(u):
    # CDX lists captures; keep real 200 documents (later captures can be the maintenance page), oldest first
    q = "https://web.archive.org/cdx/search/cdx?url=%s&filter=statuscode:200&filter=!mimetype:text/html&output=json&fl=timestamp,original,digest" % u.split("://", 1)[1]
    return json.loads(subprocess.run(CURL + ["--max-time", "60", q], capture_output=True).stdout or b"[]")[1:]

def snapshot(u, rows=None):
    rows = captures(u) if rows is None else rows
    return "https://web.archive.org/web/%sid_/%s" % (rows[-1][0], rows[-1][1]) if rows else None

def sha1_b32(b): return base64.b32encode(hashlib.sha1(b).digest()).decode()

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
def docx_text(path):
    body = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml")).find(W + "body")
    para = lambda el: "".join(t.text or "" for t in el.iter(W + "t"))
    lines = []
    for el in body:
        if el.tag == W + "p": lines.append(para(el))
        elif el.tag == W + "tbl":
            for tr in el.iter(W + "tr"):
                lines.append(" | ".join(para(tc) for tc in tr.iter(W + "tc")))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))

# optional args: pack ids to limit to (parallel verifiers each pass their own, so they never write the same file)
for f in sorted(glob.glob(os.path.join(ROOT, "difficulty", "evidence", "%s.json" % (sys.argv[1] if len(sys.argv) > 1 else "*")))):
    pack = json.load(open(f, encoding="utf-8"))
    d = os.path.join(ROOT, "difficulty", "reports", pack["subject"])
    os.makedirs(d, exist_ok=True)
    ip = os.path.join(d, "index.json")
    old = json.load(open(ip)) if os.path.exists(ip) else {}
    idx = {}
    for url in sorted({e["url"] for e in pack["entries"]}):
        rel = "difficulty/reports/%s/%s" % (pack["subject"], url.rstrip("/").split("/")[-1])
        path = os.path.join(ROOT, rel)
        src = old.get(url, {}).get("fetched_from")
        if src is None or src.startswith("unrecorded"):
            # A file saved by an agent has no recorded source: match its SHA-1 against the archive's capture digests,
            # so provenance is exact and the numbers already verified against it stay valid. Never overwrite it.
            have = open(path, "rb").read() if os.path.exists(path) else None
            rows = captures(url)
            src = None
            if have is not None:
                hit = [r for r in rows if r[2] == sha1_b32(have)]
                if hit: src = "https://web.archive.org/web/%sid_/%s" % (hit[0][0], hit[0][1])
                elif get(url) == have: src = url
                else: src = "unrecorded (matches no archived capture)"; print("WARN", rel, src)
            else:
                for cand in filter(None, [url, snapshot(url, rows)]):
                    b = get(cand)
                    if b: open(path, "wb").write(b); src = cand; break
        if src and path.endswith(".docx"):
            open(path[:-5] + ".txt", "w", encoding="utf-8").write(docx_text(path))
            rel = rel[:-5] + ".txt"
        idx[url] = {"file": rel if src else None, "fetched_from": src}
        print(pack["subject"], "OK  " if src else "MISS", rel)
    json.dump(idx, open(ip, "w"), indent=1)
