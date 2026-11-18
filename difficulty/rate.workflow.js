export const meta = {
  name: 'rate-question-difficulty',
  description: 'Rate quiz questions 1-5 stars from VCAA report evidence: Haiku workers (research, verify, rewrite, judge, tie-break), Sonnet reviewers, code merges',
  whenToUse: 'After scripts/difficulty_batches.py --remaining. args {root, packs, courses: [[course, pack, [batches]]], qaOnly?}. Then run scripts/build_difficulty.py.',
  phases: [
    { title: 'Evidence', detail: 'Haiku workers research, fetch, verify and reword; code applies patches', model: 'haiku' },
    { title: 'Evidence review', detail: 'Sonnet accepts each pack or returns issues for a Haiku fixer', model: 'sonnet' },
    { title: 'Judge', detail: 'two independent Haiku judges per batch, Haiku tie-break, code merge', model: 'haiku' },
    { title: 'QA', detail: 'Sonnet reviews rating files in groups of 6; flagged batches are re-judged', model: 'sonnet' },
  ],
}

// args: { root,
//   packs: [[pack, needsResearch]]                       evidence packs to finish before their courses are judged
//   courses: [[course, pack|null, [batch paths]]]        batches to rate, from manifest-remaining.json (any prefix)
//   qaOnly?: [[course, pack|null, [batch paths]]]        rated earlier, only reviewed now }
// Workers read and write files themselves and return only small counts, so this script's state stays small.
const ROOT = args.root
const packPath = p => `${ROOT}/difficulty/evidence/${p}.json`
const workDir = p => `${ROOT}/difficulty/work/evidence/${p}`
const stats = { retries: [], failed: [] }
const H = (prompt, label, phase, schema, effort) => agent(prompt, { label, phase, model: 'haiku', schema, effort, agentType: 'general-purpose' })

const RULES = `
DEFINITIONS
- p = estimated percentage of the students who sit this course's VCAA exam who would answer the question fully correctly.
  For a multi-mark or multi-part question, p = the expected mean score as a percentage of the available marks.
- Stars are computed later in code from p: 1★ p>=85, 2★ 70-84, 3★ 50-69, 4★ 30-49, 5★ <30. Do not output stars.
- confidence: high = a verified evidence entry tests the same skill, same format, similar demand (cite it);
  medium = verified evidence on the same area or skill type, no close match (cite it); low = no relevant statistic, evidence [].
- NEVER invent a statistic. Cite only eids that exist in the pack with "verified": true.
- Anchor on the pack's base_rates for the course, then adjust for: number of steps, by-hand vs technology, abstraction,
  unfamiliar context, plausibility of distractors, common errors in examiner notes. 4-option MCQs rarely go below ~20%.`

const COURSE_NOTES = (course, pack) => !pack
  ? 'GCSE (Edexcel), not VCE. No VCAA data applies: reasoned estimate for a GCSE Higher Triple Biology cohort, confidence "low", evidence [].'
  : course.endsWith('12')
    ? `VCE Units 1&2: VCAA publishes no statistics. Use the Units 3&4 pack ${packPath(pack)} only for analogous skills, rate for a typical Year 11 student, confidence at most "medium".`
    : `VCE Units 3&4. Evidence pack: ${packPath(pack)}.`

const VCAA_ONLY = `Only VCAA-hosted reports count: vcaa.vic.edu.au URLs, read live or as an Internet Archive copy of that exact
URL. No third-party mirrors. vcaa.vic.edu.au may show a maintenance page and WebFetch refuses web.archive.org, so use curl:
  list:     curl -s --retry 6 --retry-all-errors "https://web.archive.org/cdx/search/cdx?url=vcaa.vic.edu.au/Documents/exams/<folder>/*&filter=statuscode:200&filter=!mimetype:text/html&output=json&fl=timestamp,original&collapse=urlkey"
  download: curl -sL --retry 6 --retry-all-errors -o <file> "https://web.archive.org/web/<timestamp>id_/<original>"
Record "url" as the ORIGINAL vcaa.vic.edu.au URL. .docx text: python3 -c "import sys,zipfile,re;print(re.sub('<[^>]+>',' ',zipfile.ZipFile(sys.argv[1]).read('word/document.xml').decode()))" <file>`

// ---------- small schemas: workers report counts, not content ----------
const COUNT = { type: 'object', properties: { done: { type: 'integer' }, note: { type: 'string' } }, required: ['done'] }
const TASKS = { type: 'object', properties: {
  counts: { type: 'object', properties: { unverified: { type: 'integer' }, copied: { type: 'integer' }, placeholder: { type: 'integer' }, unclassified: { type: 'integer' } } },
  unverified: { type: 'array', items: { type: 'object', properties: { report: { type: 'string' }, eids: { type: 'array', items: { type: 'string' } } } } },
  copied: { type: 'array', items: { type: 'array', items: { type: 'string' } } },
  placeholder: { type: 'array', items: { type: 'string' } }, unclassified: { type: 'array', items: { type: 'string' } },
  entries: { type: 'integer' } }, required: ['counts', 'unverified', 'copied', 'placeholder', 'unclassified', 'entries'] }
const COUNT_ANY = { type: 'object', properties: { applied: { type: 'integer' }, verified_true: { type: 'integer' }, rejected: { type: 'array', items: { type: 'string' } } }, required: ['applied'] }
const REVIEW = { type: 'object', properties: { accept: { type: 'boolean' }, issues: { type: 'array', items: { type: 'string' } } }, required: ['accept', 'issues'] }
const MERGE = { type: 'object', properties: { n: { type: 'integer' }, missing_a: { type: 'array', items: { type: 'string' } },
  missing_b: { type: 'array', items: { type: 'string' } }, disputes: { type: 'array', items: { type: 'string' } }, written: { type: 'boolean' } },
  required: ['n', 'missing_a', 'missing_b', 'disputes', 'written'] }
const QA = { type: 'object', properties: { accept: { type: 'boolean' }, summary: { type: 'string' },
  redo: { type: 'array', items: { type: 'object', properties: { batch: { type: 'string' }, reason: { type: 'string' } }, required: ['batch', 'reason'] } } },
  required: ['accept', 'summary', 'redo'] }

const runJson = (cmd, label, phase, schema) => H(`Run from ${ROOT}: ${cmd}\nRun it in the foreground with the Bash timeout set to 600000 ms (report downloads can take minutes); never background it. It prints one JSON line at the end. Return exactly that JSON (as the structured output). Do nothing else.`, label, phase, schema, 'low')
const patchRule = (pack, name) => `Write ONLY the patch file ${workDir(pack)}/${name}.json as {"patches": {"<eid>": {<fields>}}} (create the folder).
Allowed fields: skill, examiner_note, area, verified, verify_note, verified_by, key_unconfirmed, key_note. Never change numbers or urls,
and do not edit the pack itself (code applies patches). Return {"done": <entries patched>}.`

// ---------- evidence: research (if needed) -> fetch + code checks -> Haiku chunks -> apply -> Sonnet review ----------
async function evidence(pack, needsResearch) {
  if (needsResearch) {
    await H(`Research agent for VCE subject pack "${pack}". Build ${packPath(pack)} from VCAA examination reports.
${VCAA_ONLY}
Save reports under ${ROOT}/difficulty/reports/${pack}/. If the pack file already has entries on vcaa.vic.edu.au, keep them and extend.
For every question a report gives statistics for: {"eid": "${pack}-<year>-<exam>-<q>", "year", "exam", "question", "area" (study-design area),
 "skill" (what it tests, YOUR OWN words, max 20 words, never copied from the report or exam), "format": "mcq"|"written", "marks",
 "pct_correct" (MCQ: % choosing the key, as printed) | null, "mean_mark" (written: printed average) | null,
 "examiner_note" (own words, max 25) | null, "url": original vcaa.vic.edu.au URL}. Copy numbers exactly; null if not printed.
Prefer the current study design; several recent years; 150+ entries if the reports allow. File: {"subject": "${pack}", "built_by": "haiku", "entries": [...], "gaps": "..."}.
Return {"done": <entries>, "note": "<years covered, gaps>"}.`, `research:${pack}`, 'Evidence', COUNT)
  }
  // Up to 3 rounds of worker chunks, re-listing after each apply so only what is still open gets re-dispatched.
  for (let round = 0; round < 3; round++) {
    const t = await runJson(`python3 scripts/fetch_reports.py ${pack} && python3 scripts/verify_evidence.py ${pack} && python3 scripts/evidence_tasks.py ${pack}`,
      `tasks:${pack}:${round}`, 'Evidence', TASKS)
    if (!t) { stats.failed.push(`evidence ${pack}: task listing failed`); return false }
    if (!t.entries) { stats.failed.push(`evidence ${pack}: pack is empty`); return false }
    const jobs = [
      ...t.unverified.map((u, k) => () => H(`Evidence verifier. Pack ${packPath(pack)}; local report ${ROOT}/${u.report}.
For each of these eids, find the question in the report and check the printed % choosing the keyed answer (MCQ) or the average
mark (written) against the entry's pct_correct / mean_mark. Match: {"verified": true, "verified_by": "haiku"}. Otherwise
{"verified": false, "verified_by": "haiku", "verify_note": "<what the report shows>"}. Report "MISSING" or not on vcaa.vic.edu.au:
verified false with that reason. MCQ key not confirmable from text: add "key_unconfirmed": true. Never fix numbers.
eids: ${u.eids.join(', ')}
${patchRule(pack, `verify-${round}-${k}`)}`, `verify:${pack}:${round}:${k}`, 'Evidence', COUNT)),
      ...t.copied.map((ids, k) => () => H(`Evidence editor. Pack ${packPath(pack)}. These entries' "skill" or "examiner_note" copy wording from
the VCAA report. Rewrite both in your own words (skill max 20 words: what the question tests, not its answer; note max 25
words or null). No run of 8+ words may match the report. eids: ${ids.join(', ')}
${patchRule(pack, `reword-${round}-${k}`)}`, `reword:${pack}:${round}:${k}`, 'Evidence', COUNT)),
      ...(t.placeholder.length || t.unclassified.length ? [() => H(`Evidence editor. Pack ${packPath(pack)}.
Placeholder skills (give each a real skill description, own words, max 20 words; read the report if needed): ${t.placeholder.join(', ') || 'none'}
Missing or "Unclassified" areas (set the VCE study-design area of study): ${t.unclassified.join(', ') || 'none'}
${patchRule(pack, `fix-${round}`)}`, `fix:${pack}:${round}`, 'Evidence', COUNT)] : []),
    ]
    if (!jobs.length) break
    if (round) stats.retries.push(`evidence ${pack}: chunk round ${round + 1} (${jobs.length} chunk(s) still open)`)
    await parallel(jobs)
    await runJson(`python3 scripts/apply_evidence_patches.py ${pack}`, `apply:${pack}:${round}`, 'Evidence', COUNT_ANY)
  }
  // Sonnet review; a rejection goes to one Haiku fixer, then one more review.
  let review = null
  for (let round = 0; round < 2; round++) {
    review = await agent(`You are the Sonnet reviewer for evidence pack ${packPath(pack)} (reports index ${ROOT}/difficulty/reports/${pack}/index.json).
Do not edit anything. Check: every url on vcaa.vic.edu.au and index.json records where each report came from; eids unique; numbers
in range (pct 0-100, mean_mark <= marks); spot-check 6 verified entries from different reports against the cached files; skills
and notes are in own words and describe skills, not answers; areas are study-design areas; base_rates were recomputed by code.
Ignore files in the reports folder that index.json does not list. accept=true if fit to cite; else concrete fixable issues with eids.`,
      { label: `review:${pack}:${round}`, phase: 'Evidence review', model: 'sonnet', schema: REVIEW, agentType: 'general-purpose' })
    if (review?.accept) return true
    if (round === 1) break
    stats.retries.push(`evidence ${pack}: review rejected (${(review?.issues || []).length} issues)`)
    await H(`Evidence fixer for ${packPath(pack)}. A reviewer listed these issues; fix the ones a patch can fix:
- ${(review?.issues || ['review failed']).join('\n- ')}
Entries whose number is wrong or unverifiable: set "verified": false with a verify_note (never edit the number).
${patchRule(pack, `review-${round}`)}`, `fixreview:${pack}:${round}`, 'Evidence', COUNT)
    await runJson(`python3 scripts/apply_evidence_patches.py ${pack}`, `apply:${pack}:r${round}`, 'Evidence', COUNT_ANY)
  }
  // Not accepted: judging still runs, but the build only trusts verified VCAA entries, so weak evidence shows as "est.".
  stats.failed.push(`evidence ${pack} not accepted: ${(review?.issues || ['no review']).slice(0, 3).join('; ')}`)
  return false
}

// ---------- one batch: judge a + judge b -> code merge -> (re-judge missing) -> tie-break -> code merge ----------
async function rateBatch(course, pack, batch, note) {
  const work = `${ROOT}/difficulty/work/${course}/${batch.split('/').pop().replace('.json', '')}`
  const judge = (who, extra) => H(`Difficulty judge "${who}". Rate EVERY question in ${ROOT}/${batch}.
${COURSE_NOTES(course, pack)}${pack ? `\nRead ${packPath(pack)}; use only entries with "verified": true.` : ''}
${RULES}
${[note, extra].filter(Boolean).map(x => `NOTE: ${x}`).join('\n')}
Write ${work}.${who}.json as {"items": [{"id", "p", "confidence", "evidence": [eids], "basis": "<one short sentence>"}]} with one item per question
(create the folder). Work independently. Return {"done": <items written>}.`, `judge:${who}:${batch}`, 'Judge', COUNT)
  const merge = tag => runJson(`python3 scripts/merge_judges.py ${batch}`, `merge:${batch}:${tag}`, 'Judge', MERGE)

  // Resume: a fresh run (no note) merges what is on disk first and only judges what is missing. A QA redo judges anew.
  let m = note ? null : await merge('pre')
  if (m?.written) return { batch, written: true }
  if (!m || m.missing_a.length || m.missing_b.length) {
    await Promise.all([(!m || m.missing_a.length) && judge('a'), (!m || m.missing_b.length) && judge('b')].filter(Boolean))
    m = await merge(0)
  }
  if (m && (m.missing_a.length || m.missing_b.length)) {
    stats.retries.push(`${batch}: re-judge (${m.missing_a.length}/${m.missing_b.length} missing)`)
    await Promise.all([m.missing_a.length && judge('a', `A previous attempt missed ${m.missing_a.length} questions. Write the complete file again.`),
                       m.missing_b.length && judge('b', `A previous attempt missed ${m.missing_b.length} questions. Write the complete file again.`)].filter(Boolean))
    m = await merge(1)
  }
  if (m && !m.written && m.disputes.length) {
    await H(`Tie-break judge for ${ROOT}/${batch}. Two judges disagreed on the questions in ${work}.disputes.json (both outputs included).
${COURSE_NOTES(course, pack)}${pack ? `\nEvidence: ${packPath(pack)} (verified entries only).` : ''}
${RULES}
Check which judge's evidence and reasoning holds up and give a final rating for each disputed id.
Write ${work}.tie.json as {"items": [...]} (same item shape). Return {"done": <items>}.`, `tie:${batch}`, 'Judge', COUNT)
    m = await merge(2)
  }
  if (!m?.written) stats.failed.push(`${batch}: not written (${m ? `${m.missing_a.length + m.missing_b.length} missing, ${m.disputes.length} disputes` : 'merge failed'})`)
  return { batch, written: !!m?.written }
}

// ---------- Sonnet QA in groups of 6 rating files; flagged batches re-judged once ----------
async function qaCourse(course, pack, batches) {
  const groups = Array.from({ length: Math.ceil(batches.length / 6) }, (_, i) => batches.slice(i * 6, i * 6 + 6))
  const qas = await parallel(groups.map((g, i) => () => agent(`Sonnet QA reviewer for course "${course}". Do not edit files.
Rating files (each {batch, items:[{id, p, confidence, evidence, basis, ...}]}), with their batch files at the same path under /batches/:
${g.map(b => `- ${ROOT}/${b.replace('/batches/', '/ratings/')}`).join('\n')}
${COURSE_NOTES(course, pack)}
${RULES}
Check per file: one rating per question; p plausible for the question (sample 8+); similar questions get consistent p across files;
confidence fits cited evidence (cited eids exist and are verified; "high" needs a close match); bases are specific.
Put a batch (its /batches/ path) in redo only for a real defect, with a one-line reason. Keep summary under 40 words.`,
    { label: `qa:${course}:${i}`, phase: 'QA', model: 'sonnet', schema: QA, agentType: 'general-purpose' })))
  const ok = qas.filter(Boolean)
  if (ok.length < groups.length) stats.failed.push(`qa ${course}: ${groups.length - ok.length} group(s) failed`)
  const redo = ok.flatMap(q => q.redo).map(r => ({ ...r, batch: r.batch.replace(`${ROOT}/`, '').replace('/ratings/', '/batches/') }))
    .filter(r => batches.includes(r.batch))
  const redone = await parallel(redo.map(r => () => { stats.retries.push(`qa redo ${r.batch}: ${r.reason}`); return rateBatch(course, pack, r.batch, `A reviewer rejected the previous rating: ${r.reason}`) }))
  return { course, qa_groups: ok.length, accepted: ok.every(q => q.accept), redo: redo.length, redone_ok: redone.filter(x => x?.written).length }
}

async function course(c, pack, batches) {
  const rated = await parallel(batches.map(b => () => rateBatch(c, pack, b)))
  const qa = await qaCourse(c, pack, batches.filter((_, i) => rated[i]?.written))
  return { course: c, batches: batches.length, written: rated.filter(x => x?.written).length, ...qa }
}

const packs = args.packs || []
const out = await Promise.all([
  pipeline(packs, ([pack, research]) => evidence(pack, research).then(accepted => ({ pack, accepted })),
    ev => parallel((args.courses || []).filter(([, p]) => p === ev.pack).map(([c, p, bs]) => () => course(c, p, bs))).then(cs => ({ ...ev, courses: cs }))),
  parallel((args.courses || []).filter(([, p]) => !p || !packs.some(([q]) => q === p)).map(([c, p, bs]) => () => course(c, p, bs))),
  parallel((args.qaOnly || []).map(([c, p, bs]) => () => qaCourse(c, p, bs))),
])
return { results: out, retries: stats.retries, failed: stats.failed }
