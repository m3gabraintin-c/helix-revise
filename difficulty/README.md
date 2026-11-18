# Question difficulty ratings

Every quiz question gets 1–5 stars and an estimated percentage of students who would answer it correctly. Ratings come from VCAA examination-report statistics where they exist and are marked as estimates where they don't.

## Pipeline

```bash
python3 scripts/difficulty_batches.py --remaining --prefix r3-   # unrated questions -> difficulty/batches/<course>/r3-NNN.json + manifest-remaining.json
# run difficulty/rate.workflow.js with args {root, packs: [[pack, needsResearch]], courses: [[course, pack|null, [batch paths from the manifest]]], qaOnly?}
python3 scripts/build_difficulty.py                  # ratings -> checks -> `const DIFF = {...};` line in index.html
```

Run `build_difficulty.py` again after any re-rating. Questions without a rating show no chip. Use a new `--prefix` each round, so a new batch never takes the name of an older one (the script checks). `--remaining` never re-batches a question that is already rated, and keeps batches that have judge files in `work/` (in progress) in the manifest. Every step writes its result to disk, and the workflow merges what is already on disk before it judges, so a stopped run resumes by running these commands again: only missing judges and tie-breaks run.

## Who does what

Orchestrators plan and review; Haiku workers do all per-batch and per-chunk work. Workers read their input from files, write their output to files, and return only counts, so orchestrator context stays small.

| Step | Who | Job | Output |
|---|---|---|---|
| Orchestrate | Opus (main session + `rate.workflow.js`) | Splits work into batches and evidence chunks, dispatches workers, re-dispatches failures, reports status | — |
| Research | Haiku | Builds an evidence pack from VCAA examination reports (live, or Internet Archive copies of the VCAA URL): each question's printed statistic, skill and common error in its own words, and the source URL | `evidence/<pack>.json` |
| Fetch and list | code (`fetch_reports.py`, `verify_evidence.py`, `evidence_tasks.py`) | Caches each cited report with its exact source (matched by archive digest), code-checks MCQ % in `.docx` tables, and lists what is still open: unverified entries per report, wording copied from a report (8-word overlap), placeholder skills, unclassified areas | `reports/<pack>/`, task list |
| Evidence chunks | Haiku | Verify up to 40 entries against one cached report, reword copied text, or fix skills and areas. Each writes a patch file only | `work/evidence/<pack>/*.json` |
| Apply | code (`apply_evidence_patches.py`) | Applies whitelisted patch fields (never numbers or URLs), records where each entry was checked, recomputes base rates from verified entries | `evidence/<pack>.json` |
| Evidence review | Sonnet | Accepts the pack or returns issues; one Haiku fixer patches them, then one more review | — |
| Judge ×2 | Haiku, independently | Estimate `p` and confidence for every question in a batch, citing verified evidence | `work/<course>/<batch>.a.json`, `.b.json` |
| Merge | code (`merge_judges.py`) | Agreeing judges (star gap ≤1 and `p` within 12): mean `p`, weaker confidence, union of evidence. Missing items are re-judged; disagreements go to the tie-break. A tie-break older than a re-judge is ignored. | `ratings/<course>/<batch>.json` |
| Tie-break | Haiku | Reads both judges' outputs for disputed questions and decides | `.tie.json` |
| QA | Sonnet | Reviews rating files in groups of 6; flagged batches are re-judged once with the reason | — |
| Enforce | `build_difficulty.py` | Turns `p` into stars, downgrades to `low` any rating whose cited evidence is not verified, VCAA-hosted and numeric, caps confidence by course, and embeds the result | `index.html` |

The models never output stars. Stars come from `p` in code, so the bands are applied the same way everywhere.

## Star bands

`p` = estimated % of the students who sit that course's exam who answer fully correctly. For a written question it is the expected mean score as a % of the marks.

| Stars | Estimated % correct |
|---|---|
| ★☆☆☆☆ | 85% or more |
| ★★☆☆☆ | 70–84% |
| ★★★☆☆ | 50–69% |
| ★★★★☆ | 30–49% |
| ★★★★★ | under 30% |

## Differences between courses

`p` is measured against each course's own cohort. Judges start from that course's base rates in its evidence pack, such as Specialist's average MCQ success rate as against Psychology's, and adjust from there. So the same skill can rate differently in two courses.

| Course group | Evidence | Highest confidence |
|---|---|---|
| VCE Units 3&4 | That subject's VCAA exam reports | high |
| VCE Units 1&2 | No VCAA exam, so no statistics. The Units 3&4 pack is used for similar skills, rated for a Year 11 student. | medium |
| GCSE Biology | VCAA data does not apply | low |

## Confidence

- **high**: a verified VCAA statistic for the same skill, in the same format and at similar demand.
- **medium**: verified statistics for the same area of study or type of skill, but no close match.
- **low**: no VCAA statistic fits, so `p` is a reasoned estimate based on the number of steps, the distractors and common errors. The quiz labels these "est.".

## Schemas

`evidence/<subject>.json`
```json
{"subject": "methods", "built_by": "sonnet",
 "entries": [{"eid": "methods-2023-e2-A7", "year": 2023, "exam": "Exam 2", "question": "Section A Q7",
              "area": "Calculus", "skill": "...", "format": "mcq", "marks": 1,
              "pct_correct": 41, "mean_mark": null, "examiner_note": "...", "url": "https://www.vcaa.vic.edu.au/...",
              "verified": true, "verified_by": "code", "checked_via": "https://web.archive.org/web/...id_/..."}],
 "base_rates": {"mcq_mean_pct": 0, "written_mean_pct_of_marks": 0, "by_area": {}, "n_entries": 0, "method": "..."},
 "gaps": "..."}
```

`ratings/<course>/NNN.json`
```json
{"batch": "difficulty/batches/methods/000.json",
 "items": [{"id": "methods-1-1-1", "p": 82, "confidence": "high", "evidence": ["methods-2023-e2-A7"],
            "basis": "one sentence", "judges": {"a": [80, "high"], "b": [84, "high"]}, "resolved_by": "agree" | "tiebreak"}]}
```

Embedded in `index.html` (compact): `const DIFF = {"methods-1-1-1": [2, 82, "h"], ...};` which holds stars, % and confidence `h|m|l`.

## Prompts

The full prompts for research, verification, both judges and the reconciler are in `rate.workflow.js` (`RULES`, `researchPrompt`, `verifyPrompt`, `judgePrompt` and `reconcilePrompt`). All the agents share one `RULES` block, so they work from the same definitions.

## Why reports are cached

During the pilot (November 2026), vcaa.vic.edu.au served a maintenance page and the old report URLs returned 404. WebFetch also refuses web.archive.org. So `fetch_reports.py` downloads the reports with curl. `checked_via` records the exact copy each number was checked against.
