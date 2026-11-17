# Question difficulty ratings

Every quiz question gets 1–5 stars and an estimated percentage of students who would answer it correctly. Ratings come from VCAA examination-report statistics where they exist and are marked as estimates where they don't.

## Pipeline

```bash
python3 scripts/difficulty_batches.py      # DATA -> difficulty/batches/<course>/NNN.json + manifest.json (60 questions per batch)
# run difficulty/rate.workflow.js with args {root, batches: <entries from manifest.json>}
#   (its verifier step itself runs: python3 scripts/fetch_reports.py <subject> && python3 scripts/verify_evidence.py <subject>)
python3 scripts/build_difficulty.py        # ratings -> checks -> `const DIFF = {...};` line in index.html
```

Run `build_difficulty.py` again after any re-rating. Questions without a rating show no chip.

## Who does what

| Step | Model | Job | Output |
|---|---|---|---|
| Orchestrate | Opus (main session + `rate.workflow.js`) | Splits questions into batches, maps each course to its evidence pack, fans out agents, merges judges' results in code | — |
| Research | Sonnet | Reads VCAA examination reports for one subject and records each question's printed statistic (MCQ % correct, written mean mark), its skill, the examiners' common errors, and the source URL. Computes base rates per course and per area of study. | `evidence/<subject>.json` |
| Fetch reports | code (`fetch_reports.py`) | Downloads every cited report from the live VCAA site or, failing that, the newest real Internet Archive copy (CDX lookup). `.docx` reports also get a `.txt` copy. Records where each file came from. | `reports/<subject>/` + `index.json` |
| Verify evidence | code (`verify_evidence.py`), then Haiku | Code checks each MCQ % in the `.docx` tables against the pack exactly. Haiku reads the local copies (PDF pages) for the rest. Each entry gets `verified`, `verified_by` and `checked_via`. Unverified entries are ignored by the judges and by the build. | same file |
| Judge ×2 | Haiku and Sonnet, independently | Estimate `p` and confidence for every question in a batch and cite the evidence entries used | in memory |
| Reconcile | Opus | Called only for questions where judges disagree (star gap ≥2, or `p` differs by more than 12 points, or a judge skipped it). Checks whose evidence holds up and decides. | in memory |
| Merge | code | Agreeing judges: mean `p`, the weaker confidence, union of evidence | `ratings/<course>/NNN.json` |
| Enforce | `build_difficulty.py` | Turns `p` into stars, downgrades to `low` any rating whose cited evidence is missing, unverified or has no number, caps confidence by course, and embeds the result | `index.html` |

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
            "basis": "one sentence", "judges": {"haiku": [80, "high"], "sonnet": [84, "high"]}, "resolved_by": "agree"}]}
```

Embedded in `index.html` (compact): `const DIFF = {"methods-1-1-1": [2, 82, "h"], ...};` which holds stars, % and confidence `h|m|l`.

## Prompts

The full prompts for research, verification, both judges and the reconciler are in `rate.workflow.js` (`RULES`, `researchPrompt`, `verifyPrompt`, `judgePrompt` and `reconcilePrompt`). All the agents share one `RULES` block, so they work from the same definitions.

## Why reports are cached

During the pilot (November 2026), vcaa.vic.edu.au served a maintenance page and the old report URLs returned 404. WebFetch also refuses web.archive.org. So `fetch_reports.py` downloads the reports with curl. `checked_via` records the exact copy each number was checked against.
