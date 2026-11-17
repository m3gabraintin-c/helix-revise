# Local admin page for the Helix Revise question database.
#   python admin/server.py            then open the address it prints (http://127.0.0.1:8790/...)
# It only listens on this computer, and every API call needs the token in the page, so other websites cannot use it.
# Edits go into db/helix.sqlite straight away; "Publish to files" writes db/data.sql, index.html and questions/,
# which you then commit and push as usual.
import json, os, secrets, sqlite3, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import db  # noqa: E402

TOKEN = secrets.token_urlsafe(24)
LOCK = threading.RLock()  # one request at a time touches the database
db.open_db().close()  # builds db/helix.sqlite from db/data.sql if it is missing
CON = sqlite3.connect(db.DBFILE, check_same_thread=False, isolation_level=None)  # autocommit; edits use explicit savepoints
CON.row_factory = sqlite3.Row
CON.execute("PRAGMA foreign_keys = ON")
STATE = {"unpublished": 0}

QFIELDS = ["exam_marks", "minutes", "is_challenge", "area_label", "source", "origin", "ai_assisted", "author", "reviewed_by", "reviewed_at", "provenance_note"]
SFIELDS = ["exam_weight", "prior_knowledge", "format_note"]
DFIELDS = ["version", "title", "accredited_from", "accredited_to", "status", "source_url", "notes"]

def rows(sql, *a): return [dict(r) for r in CON.execute(sql, a).fetchall()]
def one(sql, *a):
    r = CON.execute(sql, a).fetchone()
    return dict(r) if r else None

def meta():
    subjects = rows("SELECT id, name, label, curriculum, unit_from, unit_to FROM subject ORDER BY position")
    for s in subjects:
        s["designs"] = rows("SELECT id, version, title, accredited_from, accredited_to, status, source_url, notes FROM study_design WHERE subject_id=? ORDER BY id", s["id"])
        s["allowed"] = [r["type_code"] for r in rows("SELECT type_code FROM subject_question_type WHERE subject_id=?", s["id"])]
    subtopics = rows("""SELECT s.id, s.slug, s.name, s.kind, s.exam_weight, s.prior_knowledge, s.format_note, t.number AS topic_number, t.name AS topic_name,
                               t.id AS topic_id, coalesce(s.area_of_study_id, t.area_of_study_id) AS area_id, t.area_of_study_id AS topic_area_id, d.id AS design_id, d.subject_id AS subject, d.status AS design_status
                        FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id ORDER BY d.subject_id, t.number, s.position""")
    pre = {}
    for r in rows("SELECT subtopic_id, prerequisite_id FROM subtopic_prerequisite ORDER BY subtopic_id, position"): pre.setdefault(r["subtopic_id"], []).append(r["prerequisite_id"])
    for s in subtopics: s["prerequisites"] = pre.get(s["id"], [])
    return {"subjects": subjects, "subtopics": subtopics,
            "topics": rows("SELECT t.id, t.number, t.name, t.area_of_study_id AS area_id, t.study_design_id AS design_id FROM topic t ORDER BY t.study_design_id, t.number"),
            "areas": rows("SELECT id, study_design_id AS design_id, unit, code, name FROM area_of_study ORDER BY study_design_id, position"),
            "types": rows("SELECT code, name, description FROM question_type ORDER BY position"),
            "unpublished": STATE["unpublished"]}

def search(p):
    g = lambda k: (p.get(k) or [""])[0].strip()
    where, args = ["1=1"], []
    def add(cond, *a): where.append(cond); args.extend(a)
    if g("subject"): add("o.subject_id = ?", g("subject"))
    if g("unit"):
        u = int(g("unit")); add("""o.unit_from <= ? AND o.unit_to >= ? AND NOT EXISTS (SELECT 1 FROM subtopic s JOIN topic t ON t.id = s.topic_id
               JOIN area_of_study a ON a.id = coalesce(s.area_of_study_id, t.area_of_study_id) WHERE s.id = o.primary_subtopic_id AND a.unit IS NOT NULL AND a.unit <> ?)""", u, u, u)
    if g("design"): add("EXISTS (SELECT 1 FROM question_topic x WHERE x.question_id = o.id AND x.study_design_id = ?)", int(g("design")))
    if g("subtopic"):
        if g("tagged") == "any": add("EXISTS (SELECT 1 FROM question_topic x WHERE x.question_id = o.id AND x.subtopic_id = ?)", int(g("subtopic")))
        else: add("o.primary_subtopic_id = ?", int(g("subtopic")))
    if g("area"): add("""EXISTS (SELECT 1 FROM question_topic x JOIN subtopic s ON s.id = x.subtopic_id JOIN topic t ON t.id = s.topic_id
                         WHERE x.question_id = o.id AND coalesce(s.area_of_study_id, t.area_of_study_id) = ?)""", int(g("area")))
    if g("prerequisite"): add("EXISTS (SELECT 1 FROM subtopic_prerequisite sp WHERE sp.subtopic_id = o.primary_subtopic_id AND sp.prerequisite_id = ?)", int(g("prerequisite")))
    if g("type"): add("EXISTS (SELECT 1 FROM question_question_type y WHERE y.question_id = o.id AND y.type_code = ?)", g("type"))
    if g("format"): add("o.format = ?", g("format"))
    if g("challenge"): add("o.is_challenge = ?", int(g("challenge")))
    if g("weight"): add("o.primary_weight = ?", int(g("weight")))
    if g("marks"): add("o.exam_marks = ?", int(g("marks")))
    if g("maxmin"): add("o.minutes <= ?", float(g("maxmin")))
    if g("origin"): add("o.origin = ?", g("origin"))
    if g("ai"): add("o.ai_assisted = ?", g("ai"))
    if g("reviewed") == "yes": add("EXISTS (SELECT 1 FROM question q WHERE q.id = o.id AND q.reviewed_by IS NOT NULL)")
    if g("reviewed") == "no": add("EXISTS (SELECT 1 FROM question q WHERE q.id = o.id AND q.reviewed_by IS NULL)")
    if g("rubric") == "review": add("o.rubric_to_review > 0")
    if g("rubric") == "done": add("o.rubric_to_review = 0")
    if g("integrated") == "yes": add("o.area_count > 1")
    if g("multitopic") == "yes": add("o.topic_count > 1")
    if g("q"): add("(o.prompt LIKE ? OR o.id LIKE ? OR ifnull(o.source, '') LIKE ?)", *["%" + g("q") + "%"] * 3)
    w = " AND ".join(where)
    total = CON.execute(f"SELECT count(*) FROM question_overview o WHERE {w}", args).fetchone()[0]
    lim, off = min(int(g("limit") or 50), 200), int(g("offset") or 0)
    found = rows(f"""SELECT o.id, o.subject_id, o.format, substr(o.prompt, 1, 160) AS prompt, o.primary_name, o.area_label, o.types, o.exam_marks, o.minutes,
                            o.primary_weight, o.is_challenge, o.topic_count, o.area_count, o.rubric_to_review
                     FROM question_overview o WHERE {w} ORDER BY o.subject_id, o.primary_slug, o.id LIMIT ? OFFSET ?""", *args, lim, off)
    return {"total": total, "rows": found}

def question(qid):
    q = one("SELECT * FROM question WHERE id=?", qid)
    if not q: return None
    q["home_kind"] = (one("SELECT kind FROM subtopic WHERE id=?", q["home_subtopic_id"]) or {}).get("kind")
    q["options"] = rows("SELECT position, text, is_correct FROM mcq_option WHERE question_id=? ORDER BY position", qid)
    q["pieces"] = rows("SELECT id, kind, text, label, part_question, marks, answer, subtopic_id FROM question_piece WHERE question_id=? ORDER BY position", qid)
    q["types"] = [r["type_code"] for r in rows("SELECT type_code FROM question_question_type WHERE question_id=? ORDER BY position", qid)]
    q["topics"] = rows("""SELECT x.subtopic_id, x.role, x.study_design_id, s.slug, s.name FROM question_topic x JOIN subtopic s ON s.id = x.subtopic_id
                          WHERE x.question_id=? ORDER BY x.role, s.slug""", qid)
    q["rubric"] = rows("""SELECT r.id, r.piece_id, p.label AS part, r.position, r.description, r.marks, r.needs_review FROM rubric_criterion r
                          LEFT JOIN question_piece p ON p.id = r.piece_id WHERE r.question_id=? ORDER BY ifnull(p.position, -1), r.position""", qid)
    q["revisions"] = rows("SELECT changed_at, changed_by, field, old_value, new_value FROM question_revision WHERE question_id=? ORDER BY id DESC LIMIT 40", qid)
    return q

def snapshot(qid):
    q = question(qid)
    return {**{f: q[f] for f in QFIELDS}, "types": q["types"], "topics": sorted([t["subtopic_id"], t["role"]] for t in q["topics"]),
            "rubric": [[r["piece_id"], r["description"], r["marks"], r["needs_review"]] for r in q["rubric"]]}

def guarded(change):
    """Run change() in a transaction; keep it only if it adds no validation problems and breaks no constraint."""
    with LOCK:
        before = set(db.validate(CON))
        try:
            CON.execute("SAVEPOINT edit")
            extra = change() or []
            new = [e for e in db.validate(CON) if e not in before] + extra
            if new: CON.execute("ROLLBACK TO edit"); CON.execute("RELEASE edit"); return {"ok": False, "errors": new}
            CON.execute("RELEASE edit"); STATE["unpublished"] += 1
            return {"ok": True}
        except sqlite3.Error as e:
            CON.execute("ROLLBACK TO edit"); CON.execute("RELEASE edit")
            return {"ok": False, "errors": [str(e)]}

def save_question(qid, body):
    who = (body.get("changed_by") or "").strip() or "admin"
    def change():
        old = snapshot(qid); q = question(qid); errs = []
        f = {k: body["fields"][k] for k in QFIELDS if k in body.get("fields", {})}
        for k in ("area_label", "source", "author", "reviewed_by", "reviewed_at", "provenance_note"):
            if k in f and isinstance(f[k], str) and not f[k].strip(): f[k] = None
        if f: CON.execute("UPDATE question SET %s, updated_at=? WHERE id=?" % ", ".join(f"{k}=?" for k in f), (*f.values(), db.now(), qid))
        if "types" in body:
            CON.execute("DELETE FROM question_question_type WHERE question_id=?", (qid,))
            for k, code in enumerate(body["types"]): CON.execute("INSERT INTO question_question_type VALUES(?,?,?)", (qid, code, k))
        if "topics" in body:
            did = one("SELECT id FROM study_design WHERE subject_id=? AND status='current'", q["subject_id"])["id"]
            CON.execute("DELETE FROM question_topic WHERE question_id=? AND study_design_id=?", (qid, did))
            for t in body["topics"]: CON.execute("INSERT INTO question_topic VALUES(?,?,?,?)", (qid, int(t["subtopic_id"]), did, t["role"]))
            prim = [int(t["subtopic_id"]) for t in body["topics"] if t["role"] == "primary"]
            # A question is listed under its primary subtopic, so changing the primary moves it to that quiz (Challenge-set and exam-style questions stay put).
            if prim and q["home_subtopic_id"] and q["home_kind"] == "syllabus" and prim[0] != q["home_subtopic_id"]:
                pos = CON.execute("SELECT ifnull(max(home_position), -1) + 1 FROM question WHERE home_subtopic_id=?", (prim[0],)).fetchone()[0]
                CON.execute("UPDATE question SET home_subtopic_id=?, home_position=? WHERE id=?", (prim[0], pos, qid))
                # close the gap in the old quiz in two steps, so no two questions ever share a position
                CON.execute("UPDATE question SET home_position = -home_position WHERE home_subtopic_id=? AND home_position > ?", (q["home_subtopic_id"], q["home_position"]))
                CON.execute("UPDATE question SET home_position = -home_position - 1 WHERE home_subtopic_id=? AND home_position < 0", (q["home_subtopic_id"],))
        if "rubric" in body:
            CON.execute("DELETE FROM rubric_criterion WHERE question_id=?", (qid,))
            counts = {}
            for r in body["rubric"]:
                pid = r.get("piece_id"); k = counts.get(pid, 0); counts[pid] = k + 1
                if not str(r.get("description", "")).strip(): errs.append("rubric criteria need a description")
                CON.execute("INSERT INTO rubric_criterion(question_id, piece_id, position, description, marks, needs_review) VALUES(?,?,?,?,?,?)",
                            (qid, pid, k, str(r.get("description", "")).strip(), int(r.get("marks", 0)), int(bool(r.get("needs_review")))))
        new = snapshot(qid)
        for k in new:
            if new[k] != old[k]:
                CON.execute("INSERT INTO question_revision(question_id, changed_at, changed_by, field, old_value, new_value) VALUES(?,?,?,?,?,?)",
                            (qid, db.now(), who, k, json.dumps(old[k], ensure_ascii=False), json.dumps(new[k], ensure_ascii=False)))
        return errs
    return guarded(change)

def save_subtopic(sid, body):
    def change():
        f = {k: body[k] for k in SFIELDS if k in body}
        if "format_note" in f and not (f["format_note"] or "").strip(): f["format_note"] = None
        if f: CON.execute("UPDATE subtopic SET %s WHERE id=?" % ", ".join(f"{k}=?" for k in f), (*f.values(), sid))
        if "prerequisites" in body:
            CON.execute("DELETE FROM subtopic_prerequisite WHERE subtopic_id=?", (sid,))
            for k, p in enumerate(body["prerequisites"]): CON.execute("INSERT INTO subtopic_prerequisite VALUES(?,?,?)", (sid, int(p), k))
        if "area_id" in body:
            # stored on the subtopic only when it differs from its topic's area
            CON.execute("""UPDATE subtopic SET area_of_study_id = CASE WHEN ? IS (SELECT t.area_of_study_id FROM topic t WHERE t.id = subtopic.topic_id) THEN NULL ELSE ? END
                           WHERE id=?""", (body["area_id"] or None, body["area_id"] or None, sid))
    return guarded(change)

def save_design(did, body):
    def change():
        f = {k: (body[k] if body[k] != "" else None) for k in DFIELDS if k in body}
        if f: CON.execute("UPDATE study_design SET %s WHERE id=?" % ", ".join(f"{k}=?" for k in f), (*f.values(), did))
        for a in body.get("areas", []):
            CON.execute("UPDATE area_of_study SET code=?, unit=?, name=? WHERE id=? AND study_design_id=?",
                        ((a.get("code") or "").strip() or None, int(a["unit"]) if str(a.get("unit") or "").strip() else None, a["name"].strip(), int(a["id"]), did))
    return guarded(change)

def publish():
    with LOCK:
        errs = db.validate(CON)
        if errs: return {"ok": False, "errors": errs[:50]}
        import contextlib, io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                db.write_html(db.export_data(CON)); db.dump(CON); db.run_scripts()
        except SystemExit as e:
            return {"ok": False, "errors": [str(e)], "log": buf.getvalue()}
        STATE["unpublished"] = 0
        return {"ok": True, "log": buf.getvalue() + "Done. Review the changes with git, then commit and push."}

class Handler(BaseHTTPRequestHandler):
    def send(self, code, obj, ctype="application/json"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(data)
    def authorised(self):
        return secrets.compare_digest(self.headers.get("X-Admin-Token", ""), TOKEN)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            if parse_qs(u.query).get("t", [""])[0] != TOKEN: return self.send(403, b"Open the address printed by admin/server.py.", "text/plain")
            html = open(os.path.join(HERE, "admin.html"), encoding="utf-8").read().replace("__TOKEN__", TOKEN)
            return self.send(200, html.encode("utf-8"), "text/html")
        if not self.authorised(): return self.send(403, {"error": "missing token"})
        with LOCK:
            if u.path == "/api/meta": return self.send(200, meta())
            if u.path == "/api/questions": return self.send(200, search(parse_qs(u.query)))
            if u.path.startswith("/api/question/"):
                q = question(u.path[len("/api/question/"):])
                return self.send(200 if q else 404, q or {"error": "not found"})
        self.send(404, {"error": "not found"})
    def do_POST(self):
        if not self.authorised(): return self.send(403, {"error": "missing token"})
        n = int(self.headers.get("Content-Length") or 0)
        try: body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError: return self.send(400, {"error": "bad JSON"})
        p = urlparse(self.path).path
        if p.startswith("/api/question/"): r = save_question(p[len("/api/question/"):], body)
        elif p.startswith("/api/subtopic/"): r = save_subtopic(int(p[len("/api/subtopic/"):]), body)
        elif p.startswith("/api/design/"): r = save_design(int(p[len("/api/design/"):]), body)
        elif p == "/api/publish": r = publish()
        else: return self.send(404, {"error": "not found"})
        self.send(200 if r.get("ok") else 422, r)
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("HELIX_ADMIN_PORT") or os.environ.get("PORT") or "8790")
    ThreadingHTTPServer.allow_reuse_address = False  # on Windows reuse would let two servers share a port silently
    ThreadingHTTPServer.allow_reuse_port = False
    try: srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError: raise SystemExit(f"Port {port} is in use. Choose another, e.g. set HELIX_ADMIN_PORT=8791")
    print(f"Helix Revise admin: http://127.0.0.1:{port}/?t={TOKEN}")
    print("Edits are saved to db/helix.sqlite. Use 'Publish to files' to update db/data.sql, index.html and questions/. Ctrl+C to stop.")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
