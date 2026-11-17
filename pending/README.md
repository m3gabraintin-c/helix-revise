# Pending review

New VCE Units 1 & 2 questions that were drafted but **not yet reviewed**. They are NOT on the site.

File: `vce12-unreviewed.json` (one object per question, with its subtopic `slug`).

| Subject | Unreviewed drafts | Site total now | Still needed for 1000 |
|---|---|---|---|
| Chemistry | 0 | 961 | 39 |
| Biology | 77 | 922 | 78 |
| Psychology | 79 | 919 | 81 |
| Mathematical Methods | 0 | 988 | 12 |
| Physics | 533 | 467 | 533 |

Next step: have Opus review each draft (accuracy, answer key, format, subtopic fit, no duplicates against index.html),
merge the passes into `DATA.Q` in `index.html` without exceeding 1000 per subject, then run
`python3 scripts/build_questions.py && python3 scripts/verify.py` and delete this folder.
