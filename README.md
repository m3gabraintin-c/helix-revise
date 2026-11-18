# Helix Revise

A free, independent revision site, built as a single self-contained HTML page.

**Live site: https://m3gabraintin-c.github.io/helix-revise/** · Found a wrong answer? [Report it](https://github.com/m3gabraintin-c/helix-revise/issues/new).

## What's inside

Topic-by-topic practice quizzes for:

- **VCE Units 3 & 4:** Mathematical Methods, General Mathematics, Specialist Mathematics, Chemistry, Physics, Biology, Psychology, English and EAL, Chinese Second Language
- **VCE Units 1 & 2:** Chemistry, Biology, Psychology, Mathematical Methods, Physics
- **GCSE (Edexcel, Triple Higher):** Biology

Each subject is split into topics and subtopics. You can quiz one subtopic at a time or use **Build a quiz** to mix several. Progress is stored only in your browser (`localStorage`). Nothing is sent to a server.

Question types:

- **Multiple choice**, marked instantly, with an explanation.
- **Written**, where you compare your answer with a model answer and its explanation, then mark yourself.
- **Multi-part** (SAC-style, inside a subtopic quiz): a short context followed by parts a, b, c… Each part has a model answer, a worked solution whose steps show the marks they earn, and a common mistake. You give yourself the marks you earned for each part.
- **Exam-style** (listed at the bottom of each subject page): long multi-part questions where one context runs through several topics, like the extended-response section of a VCE exam. Each opens on its own page (`#x-<id>`), and **Full exam-style test** (`#test-<subject>`) puts all of a subject's exam-style questions on one page. The results show marks by question and which subtopics lost marks. Every VCE maths and science subject, plus Biology and Psychology (Units 1 & 2 and Units 3 & 4), has six, two of them Challenge questions; Units 3 & 4 Mathematical Methods has seven. English and EAL and Chinese Second Language keep their long tasks (essays, argument analysis, reading passages, writing tasks) inside their subtopics instead. GCSE Biology has none, so its page has no exam-style section.
- **Challenge** questions are harder than the rest and carry a Challenge tag wherever they appear. Every subtopic ends with one, every subject ends with a **Challenge questions** topic holding a 10-question Challenge set, and every subject with an exam-style section has two Challenge exam-style questions (666 challenge questions in all).

Scores are counted in marks: multiple-choice and written questions are worth 1 mark each, multi-part questions the sum of their parts.

**Question info**: under every question a collapsible panel gives six things:

- **Topic**: the subtopic the question tests, linked to its quiz, and its topic. Exam-style questions list every subtopic their parts test.
- **Marks**: the marks it would be worth in an exam. This is 1 for multiple choice and the sum of the parts for multi-part questions. For written questions it is an estimate, taken from the "(n marks)" in the prompt where there is one; they still score 1 mark on the site. Chinese conversation questions are marked as a whole.
- **Estimated time**: roughly the exam's pace per mark, plus reading time for long stimulus material.
- **Exam relevance**: how often the subtopic comes up (High, Medium or Low) and how close the question is to the exam's format, for example "Multiple choice, as in Exam 2 Section A". For Units 1 & 2, which have no external exam, it says how central the subtopic is and how much Units 3 & 4 build on it.
- **Prerequisites**: earlier subtopics, linked, sometimes from the Units 1 & 2 subject, plus any outside knowledge needed.
- **Question type**: one or more of recall, conceptual, calculation, application, data analysis, evaluation, proof, investigation design, text analysis, extended writing, reading comprehension, language use and speaking.

Marks, times and relevance are estimates, not predictions. Question types were tagged by rules and checked by sampling, so a few may be debatable; corrections are welcome.

**Error log** (`#errors`): every question, or part of a multi-part question, where you lose marks is saved automatically (this can be switched off). For each entry you can pick what went wrong and write a note to yourself, practise the open entries again as a quiz, and tick them off as resolved. Questions you got right can be added by hand. The log lives in `localStorage` under `helix-errors-v1`.

**Mistake analysis** (`#mistakes`, a tab beside the error log): every attempt that loses marks is recorded automatically with its subject, topic and subtopic, whether or not the error log is on.

Straight after a wrong answer, a panel asks what went wrong. The student can pick any number of these seven categories, or none, and add to them at any time:

- conceptual misunderstanding
- knowledge or formula recall
- application error
- calculation or algebra error (not offered in English or Chinese)
- question interpretation
- time management
- incomplete answer

They can also add optional details:

- **Any question:** what confused them.
- **Multiple choice:** why they chose that option. The option chosen is recorded automatically.
- **Written questions:** where they got stuck (the model answer's points), and their answer side by side with those points.
- **Multi-part questions:** which step of the worked solution they got stuck on. Each part that lost marks has its own panel.

The page shows:

- the most frequent categories (a mistake can count towards several);
- mistakes by subject and by topic;
- recurring mistakes (the same question wrong more than once, and the same category in the same subtopic);
- questions still to get right, with a practice button;
- questions corrected on a later attempt;
- the wrong options chosen, with repeats flagged;
- the full mistake history, which can be filtered to unclassified mistakes and classified there.

Everything can be filtered by date, subject and topic.

Records live in `localStorage` under `helix-mistakes-v1` and are never deleted by the site, so the history is kept. Only the oldest are dropped, past 3,000 records, and only the newest 300 keep the student's own working. The first time the page loads, it imports what is already on the device:

- incorrect answers from the activity history;
- error log entries, with their old single reason mapped to a category (for example "Wrong method or formula" becomes "Application error"), plus their chosen option and working.

Writes merge with what is stored (the later edit wins), so two open tabs never undo each other.

**Dashboard** (`#dashboard`): a personal overview built from what is saved on the device:

- **Overall performance**: questions completed, overall accuracy (marks got out of marks answered, including self-marked answers), study time, subjects practised, and accuracy for each of the last eight weeks.
- **Subject overview**: for each subject practised:
  - accuracy;
  - mastery and exam readiness, both from the topic mastery engine below;
  - coverage: the share of the subject's marks you have shown you can get;
  - questions in the last seven days;
  - mastery for each topic.
- **Topic mastery**: practised subtopics grouped as Beginning, Developing, Secure, Mastered or Not enough data yet. Each shows a rounded score with a likely range, its reliability, and its change since last week.
- **Difficulty analysis**: accuracy on easy, medium and difficult questions against the typical success rate, once the difficulty ratings (`const DIFF`) are on the site.
- **Recent activity**: recent questions, recent questions that lost marks, and completed quizzes and exam pages.
- **Recommended next steps**: the weakest subtopics, questions due for revision, and suggested practice. A question that lost marks comes back a day later, and once it is right it comes back a week later; ticking Resolved in the error log stops it.

A figure only shows once it has enough data behind it; otherwise the page says how much more is needed:

| Figure | Minimum |
|---|---|
| Accuracy | 10 marks |
| A week in the trend | 10 marks |
| A subtopic rating | 6 marks from 3 different questions |
| A difficulty band | 10 marks |

The history behind it is in `localStorage` under `helix-activity-v1`. It holds one row per marked question or part (question, subtopic, marks, seconds and session) and one row per finished quiz or exam page. Study time counts only while a question is on screen and the tab is visible, capped at three times the question's estimated time. Writes are batched, and each write adds to what is already stored, so two open tabs do not undo each other. Nothing is sent anywhere, and the history can be deleted from the bottom of the dashboard. History starts when this version is first opened, so earlier quizzes count towards mastery but not towards accuracy, time or trends.

## Topic mastery

`#mastery` explains the model to students and lists every practised subtopic's figures. The engine is a block in `index.html`, between `/* <mastery-engine> */` and `/* </mastery-engine> */`. It is pure: it has no page, storage or DOM, so the unit tests load it on its own. It is a transparent weighted statistical model, not machine learning:

```
M = 0.45 P + 0.25 R + 0.15 D + 0.15 K        (each 0-100)
```

- **P, performance:** recency-weighted accuracy on the subtopic.
  - An attempt's weight halves every 30 days.
  - Each different question counts once. A repeat adds only 25% of a question's weight, for at most two repeats, so drilling one question cannot inflate mastery.
  - A question counts for at most 3 marks.
  - A right answer the student says they guessed counts as half right.
- **R, delayed retention:** accuracy on attempts made at least 3 days after the subtopic was last practised. It is kept apart from immediate accuracy.
- **D, difficulty-adjusted:** P, moved up or down by how much harder or easier the questions were than one that 60% of students get right. This uses the difficulty ratings (`DIFF`).
- **K, consistency:** the share of practice days in the subtopic (days with at least 2 marks) at 60% or more.

**Smoothing and missing data:**
- Every component is Bayesian-smoothed: a Beta prior worth 5 marks at 50%, so three right answers give about 69, not 100.
- A component with no data (no delayed attempts, no ratings, or one practice day) is left out, and the other weights are rescaled. It is never counted as zero.

**When a score is shown:**
- **Not enough data:** no score until 3 different questions worth 6 marks. Repeats of a question do not count towards this.
- **Display:** scores are rounded down to a multiple of 5, with an 80% range widened to multiples of 5. They are never shown as precise numbers.
- **Levels:**

  | Level | M |
  |---|---|
  | Beginning | under 40 |
  | Developing | 40 to 59 |
  | Secure | 60 to 79 |
  | Mastered | 80 or more |

  Mastered also needs R of at least 70 and at least moderate reliability; otherwise the subtopic is capped at Secure.
- **Reliability:**
  - low: under 6 questions, or no delayed attempt;
  - moderate: from 6 questions and 1 delayed attempt;
  - good: from 12 questions, 3 delayed attempts and 3 practice days.

**Exam readiness** is separate from mastery. It covers every examinable subtopic in the course, weighted by its exam relevance (`DATA.M`). A subtopic without a rating counts as 0. The result is scaled from 85% to 100% by the share of answers within 1.5 times their estimated time. Units 1 & 2 have no external exam, so they show mastery only.

The engine also tracks:
- recent (21-day) and all-time accuracy;
- accuracy by question type (`DATA.T`);
- pace.

**Inputs and storage.** Every input is in the browser:

- **`helix-activity-v1`:** each attempt's marks, time and confidence, plus the number of attempts. Before a multiple-choice or written question, students can optionally say how sure they are: guessing, unsure or sure.
- **`DATA.T` and `DATA.M`:** question types, time estimates and exam weights, exported from the question database.
- **`DIFF`:** question difficulty.

Mastery is worked out again shortly after every answer, and cached until the history changes. A snapshot is saved once a day in `helix-mastery-v1` (up to 180 days), so the dashboard can show change since last week.

**Configuration.** Every weight and threshold is in `MasteryEngine.DEFAULTS`. Override them in one place, `MASTERY_CONFIG`; weights are rescaled to add up to 1.

**Tests:**

```bash
node --test tests/*.test.mjs
```

The 21 tests cover these properties:

- **Small samples:** smoothing, and one right answer not counting as mastery.
- **Repeats:** they do not inflate mastery or count towards enough data.
- **Accuracy:** recent and all-time are reported separately, and difficulty adjustment works.
- **Retention:** it is tracked separately, with a configurable gap.
- **Consistency and confidence:** good practice days and guessed answers count as described.
- **Weights:** configurable, and missing components are rescaled rather than counted as zero.
- **Levels and display:** Mastered needs retention, and scores are rounded with a range.
- **Recalculation:** a new attempt changes the result.
- **Long questions:** they are capped at 3 marks.
- **Tracking:** question types and pace are recorded.
- **Groups and readiness:** group mastery and exam readiness are calculated correctly.
- **Snapshots:** saved and replaced as described.

## Question files

`questions/` holds every question as Markdown, one folder per subject (`questions.md` + `answers.md`). It is generated from the `DATA` block in `index.html`, so after editing questions there, regenerate and check it:

```bash
python3 scripts/build_questions.py && python3 scripts/verify.py
```

## Question database and admin page

Questions and their metadata are also kept in a SQLite database. It covers:

- question types, prerequisites and exam relevance;
- study design versions and areas of study;
- source and provenance, and a marking rubric for every question;
- questions tagged to several subtopics, and a history of edits.

`db/data.sql` is the tracked copy. A local admin page (`python admin/server.py`) filters questions by every attribute and edits their metadata, refusing any change that breaks a consistency rule. **Publish to files** writes the result back into `index.html` and `questions/`. See [db/README.md](db/README.md).

```bash
python scripts/db.py build && python admin/server.py
```

## Running it

No build step. Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000. Web fonts load from Google Fonts. Without a connection the page falls back to system fonts.

The one third-party script is [KaTeX](https://katex.org/) 0.19.1 (MIT licence), which typesets maths. It loads from the jsDelivr CDN at a pinned version with subresource integrity hashes; to upgrade, change the version and the three `integrity` values together. Without a connection the quizzes still work, but maths shows as raw LaTeX.

## Hosting

`index.html` sits at the repo root, so GitHub Pages works as is: **Settings → Pages → Deploy from a branch → `main` / root**.

## Accessibility

The site targets WCAG 2.1 AA: semantic headings, a skip link, full keyboard use with visible focus, focus moved to the new heading on every page change, AA colour contrast in light and dark themes, text (not just colour) for right and wrong answers, labelled form controls, and no animation when the system asks for reduced motion. Please report any barrier as an issue.

## Contributing

Corrections and new questions are welcome as [issues](https://github.com/m3gabraintin-c/helix-revise/issues) or pull requests. Edit questions in the `DATA` block of `index.html`, then regenerate `questions/` with the command above.

`DATA.Q` maps each subtopic slug to its questions. Multiple-choice and written questions are positional arrays (see the comment above the data mapping in `index.html`). Multi-part questions are objects with named fields, and they also make up `DATA.X`, the exam-style questions keyed by subject id:

```json
{"id": "methods-6-3-m1", "type": "multi", "title": "Area between a parabola and a line",
 "source": "Original SAC-style question", "tech": "free",
 "pieces": [
  {"kind": "info", "text": "The graphs of \\(f(x) = 4x - x^2\\) and \\(g(x) = x\\) intersect at two points."},
  {"kind": "part", "label": "a", "question": "Find the coordinates of the two points of intersection.", "marks": 1,
   "answer": "\\((0, 0)\\) and \\((3, 3)\\)",
   "steps": [{"working": "Solve \\(4x - x^2 = x\\) ...", "marks": 0}, {"working": "The points are ...", "marks": 1}],
   "mistake": "Dividing both sides by \\(x\\), which loses the solution \\(x = 0\\).", "topic": "methods-6-3"}]}
```

- `tech` is `"free"` (technology-free) or `"active"` (CAS allowed). Leave it out for subjects without that split, such as Chemistry and Physics. Info pieces can also carry a `table` (`{"rows": [[...], ...]}`, first cell of each row is its heading) or a `diagram` (`{"svg": "<svg aria-hidden=\"true\" ...>", "alt": "text alternative"}`), and can sit between parts.
- A part's step marks must add up to its `marks`; the question's total is the sum of its parts. `topic` is the subtopic slug that the part tests, which is how results show where marks were lost.
- Write maths in LaTeX between `\( \)` (inline) or `\[ \]` (display). `$` is not a maths delimiter, because many questions use it for money. In the JSON every LaTeX backslash must be doubled (`\\frac`, not `\frac`, which JSON reads as a form feed); `scripts/verify.py` reports any string holding a control character.
- A part can also have `sample`, a list of paragraphs shown as a "Sample response" (used for essays and writing tasks); its steps are then headed "Marking guide". A question can set `steps_label` (for example `"Marking points"`) to replace the default "Worked solution" heading, as English and Chinese do.
- `DATA.C` lists the ids of the challenge questions. The quiz, exam-style and full-test pages tag those questions "Challenge", and `questions.md` marks them with *Challenge question*. `scripts/verify.py` checks that every listed id exists and that the marks in `questions.md` match the list.
- Question info lives in three maps:
  - `DATA.M` maps each subtopic slug to `[weight, [prerequisite slugs], "prior knowledge", "format note"?]`. The weight is 3 (high), 2 (medium) or 1 (low). The optional format note replaces the subject's wording for the question format, as the English essay subtopics do.
  - `DATA.T` maps each question id to `[type or [types], exam marks, minutes]`. The types are the codes in `QTYPES` in `index.html`. Challenge-set questions add a fourth element: the subtopic slug they test, or the name of a syllabus area that has no subtopic.
  - `DATA.E` maps each subject id to `{"w": [low, medium, high], "mcq", "short", "multi", "free"?}`, how that subject words exam relevance.

  A new question needs an entry in `DATA.T`, and a new subtopic an entry in `DATA.M`. `scripts/verify.py` checks all three maps and the *Info* line that `questions.md` prints under each question.
- Vary the position of the correct option in multiple-choice questions, and keep distractors about as long and detailed as the answer, so the answer is not given away by its position or length.
- Chinese text needs no markup: the page wraps runs of Chinese characters in `lang="zh-Hans"` so screen readers pronounce them correctly.
- Source labels must not claim a question is a VCAA question. Write original questions; past papers and textbooks may only guide the style.
- English quotations must be exact. Quotes from *Jane Eyre*, *Twelfth Night* and *My Brilliant Career* were checked word for word against the Project Gutenberg texts; quotes from in-copyright texts are kept short and few, were checked against published quote collections, and their cards ask students to confirm the page in their own edition.

## Licence

- Code: [MIT](LICENSE)
- Questions and answers: [CC BY-NC 4.0](LICENSE-QUESTIONS.md)

## Disclaimer

Not affiliated with or endorsed by the VCAA, Pearson Edexcel or any other exam board or revision provider. Questions are original and were written for this site; some were drafted with AI help and then reviewed.
