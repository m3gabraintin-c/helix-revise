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

**Error log** (`#errors`): every question, or part of a multi-part question, where you lose marks is saved automatically (this can be switched off). For each entry you can record why you lost marks and a note to yourself, practise the open entries again as a quiz, and tick them off as resolved. Questions you got right can be added by hand. The log lives in `localStorage` under `helix-errors-v1`.

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
