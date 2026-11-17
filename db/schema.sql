-- Helix Revise question database (SQLite). Build it with: python scripts/db.py build
-- db/data.sql holds the rows; db/helix.sqlite is built from schema.sql + data.sql and is not committed.
-- See db/README.md for how the tables fit together and how they map to index.html's DATA.
PRAGMA foreign_keys = ON;

-- ---------- courses, study designs and the syllabus tree ----------

-- A course as the site lists it, e.g. Mathematical Methods, VCE Units 3 & 4.
CREATE TABLE subject (
  id          TEXT PRIMARY KEY,                       -- site id: 'methods', 'vce-bio12', 'gcse-bio'
  name        TEXT NOT NULL,
  label       TEXT NOT NULL,                          -- 'VCE · Units 3 & 4'
  grp         TEXT NOT NULL,                          -- the heading the site groups it under
  curriculum  TEXT NOT NULL CHECK (curriculum IN ('VCE', 'GCSE')),
  unit_from   INTEGER CHECK (unit_from BETWEEN 1 AND 4),  -- 3 for Units 3 & 4; NULL when the course has no VCE units
  unit_to     INTEGER CHECK (unit_to BETWEEN 1 AND 4),
  discipline  TEXT NOT NULL,                          -- links a course's Units 1 & 2 and 3 & 4: 'methods', 'chemistry'
  position    INTEGER NOT NULL UNIQUE,
  CHECK ((unit_from IS NULL) = (unit_to IS NULL) AND (unit_from IS NULL OR unit_from <= unit_to))
);

-- One row per version of a subject's study design (or exam specification). When VCAA accredits a new
-- design, add a 'draft' version, copy or rebuild its syllabus tree, map old subtopics to new ones in
-- subtopic_successor, re-tag questions, then make it 'current' and the old one 'retired'.
CREATE TABLE study_design (
  id               INTEGER PRIMARY KEY,
  subject_id       TEXT NOT NULL REFERENCES subject(id),
  version          TEXT NOT NULL,                     -- e.g. '2023-2027'
  title            TEXT NOT NULL,
  accredited_from  INTEGER,                           -- first year of accreditation; NULL until confirmed
  accredited_to    INTEGER,
  status           TEXT NOT NULL CHECK (status IN ('draft', 'current', 'retired')),
  source_url       TEXT,
  notes            TEXT,
  UNIQUE (subject_id, version),
  CHECK (accredited_from IS NULL OR accredited_to IS NULL OR accredited_from <= accredited_to)
);
CREATE UNIQUE INDEX study_design_one_current ON study_design(subject_id) WHERE status = 'current';

-- A VCAA area of study (or a GCSE topic area). code is NULL until it has been checked against the study design.
CREATE TABLE area_of_study (
  id               INTEGER PRIMARY KEY,
  study_design_id  INTEGER NOT NULL REFERENCES study_design(id),
  unit             INTEGER CHECK (unit BETWEEN 1 AND 4),  -- NULL when it spans units or is not yet known
  code             TEXT,                                -- 'Unit 3 AOS 1'
  name             TEXT NOT NULL,
  position         INTEGER NOT NULL,
  UNIQUE (study_design_id, position)
);

-- A topic heading on the site (Topic 1, Topic 2, ...), inside one area of study.
CREATE TABLE topic (
  id               INTEGER PRIMARY KEY,
  study_design_id  INTEGER NOT NULL REFERENCES study_design(id),
  area_of_study_id INTEGER REFERENCES area_of_study(id),  -- NULL only for the Challenge questions topic
  number           INTEGER NOT NULL,
  name             TEXT NOT NULL,
  UNIQUE (study_design_id, number)
);

-- A subtopic: the unit that quizzes, exam relevance and prerequisites hang off. kind 'collection' is a
-- list of questions that is not itself a syllabus point (the Challenge set).
CREATE TABLE subtopic (
  id             INTEGER PRIMARY KEY,
  slug           TEXT NOT NULL UNIQUE,                -- the site route, #<slug>
  topic_id       INTEGER NOT NULL REFERENCES topic(id),
  position       INTEGER NOT NULL,
  name           TEXT NOT NULL,
  kind           TEXT NOT NULL DEFAULT 'syllabus' CHECK (kind IN ('syllabus', 'collection')),
  triple_only    INTEGER NOT NULL DEFAULT 0 CHECK (triple_only IN (0, 1)),
  exam_weight    INTEGER CHECK (exam_weight BETWEEN 1 AND 3),  -- exam relevance: 3 high, 2 medium, 1 low
  prior_knowledge TEXT NOT NULL DEFAULT '',           -- knowledge needed from outside the site
  format_note    TEXT,                                -- replaces the subject's format wording (English essays, Chinese tasks)
  UNIQUE (topic_id, position),
  CHECK (kind = 'collection' OR exam_weight IS NOT NULL)
);

-- Prerequisite relationships between subtopics, possibly across courses (Methods 3 & 4 needs Methods 1 & 2).
CREATE TABLE subtopic_prerequisite (
  subtopic_id      INTEGER NOT NULL REFERENCES subtopic(id) ON DELETE CASCADE,
  prerequisite_id  INTEGER NOT NULL REFERENCES subtopic(id),
  position         INTEGER NOT NULL,
  PRIMARY KEY (subtopic_id, prerequisite_id),
  CHECK (subtopic_id <> prerequisite_id)
);

-- When a study design changes: which new subtopic(s) replace an old one.
CREATE TABLE subtopic_successor (
  old_subtopic_id  INTEGER NOT NULL REFERENCES subtopic(id),
  new_subtopic_id  INTEGER NOT NULL REFERENCES subtopic(id),
  note             TEXT,
  PRIMARY KEY (old_subtopic_id, new_subtopic_id)
);

-- How each course words exam relevance (DATA.E).
CREATE TABLE relevance_wording (
  subject_id  TEXT PRIMARY KEY REFERENCES subject(id),
  w_low TEXT NOT NULL, w_medium TEXT NOT NULL, w_high TEXT NOT NULL,
  mcq TEXT NOT NULL, short TEXT NOT NULL, multi TEXT NOT NULL,
  free TEXT                                           -- technology-free extended response, where the course has one
);

-- ---------- question types ----------

CREATE TABLE question_type (
  code         TEXT PRIMARY KEY,                      -- 'calc'
  name         TEXT NOT NULL UNIQUE,                  -- 'Calculation'
  description  TEXT NOT NULL,
  position     INTEGER NOT NULL UNIQUE
);
-- Which types make sense for which course (speaking only in Chinese, proof only in maths, ...).
CREATE TABLE subject_question_type (
  subject_id  TEXT NOT NULL REFERENCES subject(id),
  type_code   TEXT NOT NULL REFERENCES question_type(code),
  PRIMARY KEY (subject_id, type_code)
);

-- ---------- questions ----------

CREATE TABLE question (
  id               TEXT PRIMARY KEY,
  subject_id       TEXT NOT NULL REFERENCES subject(id),
  format           TEXT NOT NULL CHECK (format IN ('mcq', 'written', 'multi')),
  -- where the site lists it: in a subtopic quiz, or (exam_position set) in the subject's exam-style section
  home_subtopic_id INTEGER REFERENCES subtopic(id),
  home_position    INTEGER,
  exam_position    INTEGER,
  prompt           TEXT NOT NULL,                     -- the question; for multi-part questions, the title
  answer           TEXT,                              -- written: model answer
  explanation      TEXT,                              -- mcq and written
  higher_only      INTEGER NOT NULL DEFAULT 0 CHECK (higher_only IN (0, 1)),
  tech             TEXT CHECK (tech IN ('free', 'active')),
  steps_label      TEXT,
  is_challenge     INTEGER NOT NULL DEFAULT 0 CHECK (is_challenge IN (0, 1)),
  -- metadata
  exam_marks       INTEGER NOT NULL CHECK (exam_marks >= 0),  -- marks in an exam (0: marked as a whole)
  minutes          REAL NOT NULL CHECK (minutes > 0),
  area_label       TEXT,                              -- syllabus area for a Challenge-set question that tests no single subtopic
  -- source and provenance
  source           TEXT,                              -- label shown with multi-part questions
  origin           TEXT NOT NULL DEFAULT 'original' CHECK (origin IN ('original', 'adapted', 'past-paper-style')),
  ai_assisted      TEXT NOT NULL DEFAULT 'unknown' CHECK (ai_assisted IN ('yes', 'no', 'unknown')),
  author           TEXT,
  reviewed_by      TEXT,
  reviewed_at      TEXT,
  provenance_note  TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  CHECK ((home_subtopic_id IS NULL) <> (exam_position IS NULL)),
  CHECK ((home_subtopic_id IS NULL) = (home_position IS NULL)),
  CHECK (exam_position IS NULL OR format = 'multi'),
  CHECK (format <> 'mcq' OR exam_marks = 1),
  CHECK (format = 'written' OR answer IS NULL)
);
CREATE UNIQUE INDEX question_home_order ON question(home_subtopic_id, home_position) WHERE home_subtopic_id IS NOT NULL;
CREATE UNIQUE INDEX question_exam_order ON question(subject_id, exam_position) WHERE exam_position IS NOT NULL;

-- A question can belong to several subtopics. 'primary' is the subtopic it mainly tests (one per study
-- design); 'secondary' covers the other subtopics of integrated questions. Tagging is per study design
-- version, so a question can be re-tagged for a new design without losing the old tags.
CREATE TABLE question_topic (
  question_id      TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  subtopic_id      INTEGER NOT NULL REFERENCES subtopic(id),
  study_design_id  INTEGER NOT NULL REFERENCES study_design(id),
  role             TEXT NOT NULL CHECK (role IN ('primary', 'secondary')),
  PRIMARY KEY (question_id, subtopic_id)
);
CREATE UNIQUE INDEX question_topic_one_primary ON question_topic(question_id, study_design_id) WHERE role = 'primary';

CREATE TABLE question_question_type (
  question_id  TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  type_code    TEXT NOT NULL REFERENCES question_type(code),
  position     INTEGER NOT NULL,                      -- main type first
  PRIMARY KEY (question_id, type_code),
  UNIQUE (question_id, position)
);

CREATE TABLE mcq_option (
  question_id  TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL,                      -- 0 = A
  text         TEXT NOT NULL,
  is_correct   INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
  PRIMARY KEY (question_id, position)
);
CREATE UNIQUE INDEX mcq_option_one_correct ON mcq_option(question_id) WHERE is_correct = 1;

-- The context and parts of a multi-part question, in order.
CREATE TABLE question_piece (
  id              INTEGER PRIMARY KEY,
  question_id     TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  position        INTEGER NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('info', 'part')),
  text            TEXT,                               -- info text
  table_json      TEXT,                               -- info table: {"rows": [[...]]}
  diagram_svg     TEXT,
  diagram_alt     TEXT,
  label           TEXT,                               -- part: 'a', 'b', 'e.i'
  part_question   TEXT,
  marks           INTEGER CHECK (marks >= 1),
  answer          TEXT,
  mistake         TEXT,
  subtopic_id     INTEGER REFERENCES subtopic(id),    -- the subtopic the part tests
  sample_json     TEXT,                               -- sample response paragraphs, as a JSON list
  UNIQUE (question_id, position),
  CHECK (kind = 'info' OR (label IS NOT NULL AND part_question IS NOT NULL AND marks IS NOT NULL AND answer IS NOT NULL AND subtopic_id IS NOT NULL)),
  CHECK ((diagram_svg IS NULL) = (diagram_alt IS NULL))
);

-- Marking rubric. For a multi-part question each part's criteria are its worked-solution steps; MCQ and
-- written questions have question-level criteria. needs_review marks criteria generated during migration.
CREATE TABLE rubric_criterion (
  id            INTEGER PRIMARY KEY,
  question_id   TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  piece_id      INTEGER REFERENCES question_piece(id) ON DELETE CASCADE,
  position      INTEGER NOT NULL,
  description   TEXT NOT NULL,
  marks         INTEGER NOT NULL CHECK (marks >= 0),
  needs_review  INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1))
);
CREATE UNIQUE INDEX rubric_order ON rubric_criterion(question_id, ifnull(piece_id, -1), position);

-- Every metadata change made through the admin page.
CREATE TABLE question_revision (
  id           INTEGER PRIMARY KEY,
  question_id  TEXT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  changed_at   TEXT NOT NULL,
  changed_by   TEXT NOT NULL,
  field        TEXT NOT NULL,
  old_value    TEXT,
  new_value    TEXT
);

-- ---------- consistency triggers (scripts/db.py validate checks the rules that span several rows) ----------

-- A question's tags must be subtopics of its own subject, in the study design version the tag names.
CREATE TRIGGER question_topic_same_subject BEFORE INSERT ON question_topic
WHEN NOT EXISTS (SELECT 1 FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id
                 JOIN question q ON q.id = NEW.question_id
                 WHERE s.id = NEW.subtopic_id AND d.id = NEW.study_design_id AND d.subject_id = q.subject_id AND s.kind = 'syllabus')
BEGIN SELECT RAISE(ABORT, 'question_topic: the subtopic must be a syllabus subtopic of the question''s subject and study design'); END;
CREATE TRIGGER question_topic_same_subject_upd BEFORE UPDATE ON question_topic
WHEN NOT EXISTS (SELECT 1 FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id
                 JOIN question q ON q.id = NEW.question_id
                 WHERE s.id = NEW.subtopic_id AND d.id = NEW.study_design_id AND d.subject_id = q.subject_id AND s.kind = 'syllabus')
BEGIN SELECT RAISE(ABORT, 'question_topic: the subtopic must be a syllabus subtopic of the question''s subject and study design'); END;

-- Types must be allowed for the question's subject.
CREATE TRIGGER question_type_allowed BEFORE INSERT ON question_question_type
WHEN NOT EXISTS (SELECT 1 FROM subject_question_type a JOIN question q ON q.subject_id = a.subject_id
                 WHERE q.id = NEW.question_id AND a.type_code = NEW.type_code)
BEGIN SELECT RAISE(ABORT, 'question type is not allowed for this subject'); END;

-- A question listed in a subtopic quiz belongs to that subtopic's subject.
CREATE TRIGGER question_home_subject BEFORE INSERT ON question
WHEN NEW.home_subtopic_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id
  WHERE s.id = NEW.home_subtopic_id AND d.subject_id = NEW.subject_id)
BEGIN SELECT RAISE(ABORT, 'question: home subtopic belongs to another subject'); END;

-- A prerequisite may not come from a later unit (a Units 1 & 2 subtopic cannot require Units 3 & 4).
CREATE TRIGGER prerequisite_not_later BEFORE INSERT ON subtopic_prerequisite
WHEN (SELECT sp.unit_from FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id
      JOIN subject sp ON sp.id = d.subject_id WHERE s.id = NEW.prerequisite_id)
   > (SELECT sb.unit_to FROM subtopic s JOIN topic t ON t.id = s.topic_id JOIN study_design d ON d.id = t.study_design_id
      JOIN subject sb ON sb.id = d.subject_id WHERE s.id = NEW.subtopic_id)
BEGIN SELECT RAISE(ABORT, 'prerequisite comes from a later unit'); END;

-- ---------- views for filtering ----------

-- One row per question with everything the admin page filters on.
CREATE VIEW question_overview AS
SELECT q.id, q.subject_id, sj.name AS subject_name, sj.label AS subject_label, sj.unit_from, sj.unit_to,
       q.format, q.is_challenge, q.higher_only, q.tech, q.exam_marks, q.minutes, q.origin, q.ai_assisted,
       q.source, q.prompt, q.area_label, q.home_subtopic_id, q.exam_position,
       pt.subtopic_id AS primary_subtopic_id, ps.slug AS primary_slug, ps.name AS primary_name, ps.exam_weight AS primary_weight,
       pt.study_design_id,
       (SELECT group_concat(type_code, ',') FROM (SELECT type_code FROM question_question_type WHERE question_id = q.id ORDER BY position)) AS types,
       (SELECT count(DISTINCT t.area_of_study_id) FROM question_topic x JOIN subtopic s ON s.id = x.subtopic_id JOIN topic t ON t.id = s.topic_id
         WHERE x.question_id = q.id) AS area_count,
       (SELECT count(*) FROM question_topic x WHERE x.question_id = q.id) AS topic_count,
       (SELECT count(*) FROM rubric_criterion r WHERE r.question_id = q.id AND r.needs_review = 1) AS rubric_to_review
FROM question q
JOIN subject sj ON sj.id = q.subject_id
LEFT JOIN question_topic pt ON pt.question_id = q.id AND pt.role = 'primary'
  AND pt.study_design_id = (SELECT id FROM study_design WHERE subject_id = q.subject_id AND status = 'current')
LEFT JOIN subtopic ps ON ps.id = pt.subtopic_id;

-- Questions whose subtopics span more than one area of study.
CREATE VIEW integrated_question AS
SELECT x.question_id, count(DISTINCT t.area_of_study_id) AS areas
FROM question_topic x JOIN subtopic s ON s.id = x.subtopic_id JOIN topic t ON t.id = s.topic_id
GROUP BY x.question_id HAVING count(DISTINCT t.area_of_study_id) > 1;
