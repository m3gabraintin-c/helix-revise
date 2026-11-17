# Question database

All questions and their metadata live in a SQLite database:

- `schema.sql`: the tables, constraints, triggers and views.
- `data.sql`: every row, one per line. This is what git tracks, so changes show up as readable diffs.
- `helix.sqlite`: built locally from the two files above. It is not committed.

The website is unchanged. It is still one static page, and `scripts/db.py export` writes the database into `index.html`'s `DATA` block. Your friend's difficulty scripts (`scripts/build_difficulty.py` and others) keep reading `DATA` as before, and the export leaves the `const DIFF` line alone.

## Everyday use

```bash
python scripts/db.py build        # first time, or after pulling: build db/helix.sqlite from data.sql
python admin/server.py            # open the address it prints, edit, then press "Publish to files"
git add db/data.sql index.html questions && git commit
```

**Publish to files** runs a full validation. It then writes `db/data.sql`, `index.html` and `questions/`, and runs `build_questions.py` and `verify.py`.

If you edit question text in `index.html` directly, or a script regenerates `DATA`, pull the change into the database:

```bash
python scripts/db.py sync         # imports DATA, keeps database-only fields, checks the round trip, rewrites data.sql
```

Other commands:

| Command | What it does |
|---|---|
| `python scripts/db.py validate` | Checks every consistency rule. |
| `python scripts/db.py check` | Confirms the database reproduces `DATA` exactly. |
| `python scripts/db.py export` | Database to `index.html` and `questions/`, without the admin page. |

## Structure

The syllabus tree, one per study design version:

- **subject** (a course, with its units and discipline)
  - **study_design** (one version: `draft`, `current` or `retired`; exactly one is current)
    - **area_of_study** (code such as "Unit 3 AOS 1", plus unit and name)
      - **topic** (a topic heading on the site)
        - **subtopic** (has exam relevance, prior knowledge and a format note; it can name its own area of study when its topic spans two, and the `subtopic_area` view gives every subtopic's area)
          - **subtopic_prerequisite** links to other subtopics, possibly in another course
          - **subtopic_successor** maps an old subtopic to its replacement when the study design changes

The questions and what hangs off each one:

- **question**: the content, where it is listed, exam marks, minutes, and source and provenance.
  - **question_topic** (`primary` or `secondary`, per study design)
  - **question_question_type** (ordered; the main type comes first)
  - **mcq_option** (exactly one correct)
  - **question_piece** (the context and parts of a multi-part question; each part tests a subtopic)
  - **rubric_criterion** (question-level for MCQ and written questions, per part for multi-part ones)
  - **question_revision** (every edit made in the admin page: who, when, and the old and new values)

Supporting tables:

- `question_type`: the types and their descriptions.
- `subject_question_type`: which types each course may use.
- `relevance_wording`: how each course words exam relevance.

### How the requirements are met

**Question metadata**
- **Question type.** `question_question_type` gives a question one or more types. `subject_question_type` limits which types each course may use; speaking, for example, is only allowed in Chinese.
- **Prerequisite topics.** `subtopic_prerequisite` links subtopics, and `subtopic.prior_knowledge` holds anything outside the site.
- **Exam relevance.** `subtopic.exam_weight` gives a 1–3 rating per subtopic. `relevance_wording` and `subtopic.format_note` give the wording for each course and format.
- **Study design version.** Each `study_design` version has its own tree: areas of study, topics and subtopics. `question_topic.study_design_id` records which version a tag belongs to.
- **Source and provenance.** Each question has these columns: `source`, `origin`, `ai_assisted`, `author`, `reviewed_by`, `reviewed_at` and `provenance_note`. `question_revision` keeps the history of edits.
- **Marking rubric.** Each `rubric_criterion` row has a description and marks, plus `needs_review` for generated criteria.

**Structure**
- **Questions in several topics.** `question_topic` gives a question one primary subtopic per study design and any number of secondary ones.
- **Integrated questions.** A multi-part question's parts each test a subtopic, and all of them are tagged on the question. The `integrated_question` view lists the 51 questions whose subtopics span more than one area of study.
- **Filtering.** The `question_overview` view backs the admin page's filters:
  - subject, unit, study design, area of study, subtopic (primary or any tag) and prerequisite;
  - type, format, challenge, exam relevance, marks and time;
  - origin, AI-assisted, reviewer and rubric status;
  - integrated, tagged to several subtopics, and free text.

**Editing and change**
- **Admin interface.** `admin/server.py` runs on your own computer and is reachable only from it. Each session prints a new token, and every request needs it.
- **Study design changes.** Add a `draft` design with its new areas, topics and subtopics, and map old subtopics to new ones in `subtopic_successor`. Then tag questions in the new design: a question's tags in the old design stay as they are. Finally, make the new design `current` and the old one `retired`. Retired designs stay in the database, so history is kept.

**Migration and validation**
- **Existing questions kept.** `db.py sync` imported all 10 938 questions and their metadata. `db.py check` proves the export reproduces `DATA` exactly.
- **Metadata consistent with subject and unit.** Some rules are enforced the moment data is written, by CHECK constraints, unique indexes and triggers:
  - a tag must be a subtopic of the question's own subject and study design;
  - each question and study design has one primary tag;
  - a type must be allowed for the subject;
  - a question listed under a subtopic must belong to that subtopic's subject;
  - a prerequisite cannot come from a later unit;
  - a multiple-choice question is worth 1 mark and has exactly one correct option.

  `db.py validate` also checks the rules that span several rows:
  - an area of study's unit must lie within the course's units;
  - there are no prerequisite cycles;
  - prerequisites come from the same curriculum and are not retired;
  - rubric marks add up to the question's or part's marks;
  - a multi-part question's marks equal the sum of its parts;
  - every part's subtopic is tagged on the question;
  - tech labels are only on maths questions;
  - "Higher" is only on GCSE questions;
  - a Challenge-set question has either a primary subtopic or an area label.

  The admin page refuses any edit that adds a problem.

## What the migration filled in, and what still needs a person

- **Study designs** have their version, accreditation years and a link to the official document. They were checked on 18 November 2026 against VCAA's own study design documents and Pearson's specification, as archived by the Internet Archive, because the VCAA website was down for maintenance. The Biology study design (2022–2026) expires at the end of 2026, so check VCAA for its successor.
- **Areas of study** are the official ones: 81 across the 15 courses. Every subtopic is mapped to one, and a subtopic carries its own area where its site topic spans two. Maths courses list their areas for Units 3 and 4 as a whole, as the study design does.
  - **Specialist Mathematics:** two flagged areas have no code, because their content is not an area of the 2023–2027 design. One covers reciprocal circular functions and compound-angle identities, assumed from Units 1 and 2. The other covers Newton's laws, friction and momentum, which the current design does not include.
- **Rubrics**: multi-part questions use their worked-solution steps, which were already checked. MCQ rubrics are exact ("Chooses B: ..."). Written-question rubrics (3 581) were generated by splitting the model answer into as many criteria as the question's estimated exam marks. They are flagged `needs_review`, and the admin page's Rubric filter finds them.
- **Provenance**: every question is marked `origin = original` and `ai_assisted = unknown`, with a note that it was imported. Set the author, reviewer and AI-assisted status as questions are reviewed.
- **Difficulty** is not in the database. It comes from your friend's pipeline (`const DIFF`). If you later want to filter by difficulty, add a table fed from `difficulty/ratings/`.
