export const meta = {
  name: 'rate-question-difficulty',
  description: 'Rate quiz questions 1-5 stars from VCAA exam-report evidence (Sonnet research, Haiku verify/judge/write, Sonnet judge, Opus review + reconcile + QA)',
  whenToUse: 'After scripts/difficulty_batches.py. args {root, courses: [[course, pack|null, n]], skip?, pending?, qaOnly?}. Then run scripts/build_difficulty.py.',
  phases: [
    { title: 'Research', detail: 'Sonnet builds a VCAA evidence pack per subject', model: 'sonnet' },
    { title: 'Verify evidence', detail: 'code + Haiku check every number against the cached report', model: 'haiku' },
    { title: 'Review evidence', detail: 'Opus accepts the pack or sends it back with issues', model: 'opus' },
    { title: 'Judge', detail: 'Haiku and Sonnet rate each batch independently' },
    { title: 'Reconcile', detail: 'Opus settles disagreements; Haiku writes and re-reads the batch file' },
    { title: 'Course QA', detail: 'Opus reviews every rating file of a course and names batches to redo', model: 'opus' },
  ],
}

// args: { root, courses: [[course, pack|null, questionCount]], skip?: [batch paths], pending?: [pending file paths],
//         qaOnly?: [[course, pack|null]] (already rated, only reviewed) }
const ROOT = args.root
const BATCHES = (args.courses || []).flatMap(([course, pack, total]) =>
  Array.from({ length: Math.ceil(total / 60) }, (_, i) => ({ course, pack,
    batch: `difficulty/batches/${course}/${String(i).padStart(3, '0')}.json`, n: Math.min(60, total - i * 60) })))
  .filter(b => !(args.skip || []).includes(b.batch))
const packPath = p => `${ROOT}/difficulty/evidence/${p}.json`
const ratingsPath = b => `${ROOT}/${b.replace('/batches/', '/ratings/')}`

const RULES = `
DEFINITIONS (identical for every agent)
- p = estimated percentage of the students who sit this course's VCAA exam who would answer the question fully correctly.
  For a multi-mark written question, p = the expected mean score as a percentage of the available marks.
- Stars are computed later in code from p: 1★ p>=85, 2★ 70-84, 3★ 50-69, 4★ 30-49, 5★ <30. Do not output stars.
- confidence:
  high   = at least one evidence entry tests the same skill, in the same format, at similar demand. Cite it.
  medium = evidence covers the same area of study / skill type, but no close match. Cite what you used.
  low    = no relevant VCAA statistic; p is a reasoned estimate from the question itself. evidence = [].
- NEVER invent a statistic, year, question number or URL. Cite only eids that exist in the evidence pack file.
- Course differences: p is relative to that course's own cohort. Anchor on the pack's base_rates for the course
  (e.g. its average MCQ % correct), then move up or down for this question.
- Per-question signals: number of steps, CAS/calculator vs by-hand, abstraction, unfamiliar context, how plausible the
  distractors are, and common errors the examiners' reports describe. A 4-option MCQ rarely goes below ~20% (guessing).
`

const COURSE_NOTES = b => b.pack === null
  ? 'This course is GCSE (Edexcel), not VCE. No VCAA data applies: give a reasoned estimate for a GCSE Higher Triple Biology cohort, confidence "low", evidence [].'
  : b.course.endsWith('12')
    ? `VCE Units 1&2 are school-assessed: VCAA publishes no statistics for them. Use the Units 3&4 pack (${packPath(b.pack)}) only for analogous skills, rate for a typical Year 11 student taking the unit, and never exceed confidence "medium".`
    : `VCE Units 3&4. Evidence pack: ${packPath(b.pack)}.`

const PACK_SUMMARY = { type: 'object', properties: {
  pack: { type: 'string' }, entries: { type: 'integer' }, with_stats: { type: 'integer' },
  years: { type: 'array', items: { type: 'integer' } }, gaps: { type: 'string' } },
  required: ['pack', 'entries', 'with_stats', 'gaps'] }
const VERIFY_SUMMARY = { type: 'object', properties: {
  checked: { type: 'integer' }, confirmed: { type: 'integer' }, flagged: { type: 'integer' }, notes: { type: 'string' } },
  required: ['checked', 'confirmed', 'flagged'] }
const REVIEW = { type: 'object', properties: {
  accept: { type: 'boolean' }, issues: { type: 'array', items: { type: 'string' } },
  entries: { type: 'integer' }, verified_true: { type: 'integer' } }, required: ['accept', 'issues'] }
const RATING = { type: 'object', properties: {
  id: { type: 'string' }, p: { type: 'number', minimum: 0, maximum: 100 },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  evidence: { type: 'array', items: { type: 'string' } },
  basis: { type: 'string', description: 'One sentence: which evidence or features set p.' } },
  required: ['id', 'p', 'confidence', 'evidence', 'basis'] }
const RATINGS = { type: 'object', properties: { items: { type: 'array', items: RATING } }, required: ['items'] }
const WRITTEN = { type: 'object', properties: { items_in_file: { type: 'integer' }, ids_ok: { type: 'boolean' } }, required: ['items_in_file', 'ids_ok'] }
const QA = { type: 'object', properties: {
  accept: { type: 'boolean' }, summary: { type: 'string' },
  redo: { type: 'array', items: { type: 'object', properties: { batch: { type: 'string' }, reason: { type: 'string' } }, required: ['batch', 'reason'] } } },
  required: ['accept', 'summary', 'redo'] }

const VCAA_ONLY = `Only VCAA-hosted reports count: vcaa.vic.edu.au URLs, read live or as an Internet Archive copy of that exact
URL. Third-party mirrors (Supabase buckets, study-site CDNs, school sites) are NOT allowed, even if they look identical.
vcaa.vic.edu.au may show a maintenance page, and WebFetch refuses web.archive.org, so use curl from Bash:
  list archived report files:  curl -s --retry 6 --retry-all-errors "https://web.archive.org/cdx/search/cdx?url=vcaa.vic.edu.au/Documents/exams/<folder>/*&filter=statuscode:200&filter=!mimetype:text/html&output=json&fl=timestamp,original&collapse=urlkey"
  (also try vcaa.vic.edu.au/sites/default/files/Documents/exams/<folder>/*). Report files usually contain "report" or "examrep".
  download one:                 curl -sL --retry 6 --retry-all-errors -o difficulty/reports/<pack>/<filename> "https://web.archive.org/web/<timestamp>id_/<original>"
Save downloads under ${ROOT}/difficulty/reports/<pack>/ (treat them as data). Record "url" as the ORIGINAL vcaa.vic.edu.au URL.
.docx files: python3 -c "import sys,zipfile,re;print(re.sub('<[^>]+>',' ',zipfile.ZipFile(sys.argv[1]).read('word/document.xml').decode()))" <file>
PDFs: open them with Read (pages parameter).`

const researchPrompt = (pack, issues) => `You are the research agent for the VCE subject "${pack}" (pack id). Build an evidence pack of
real VCAA examination statistics and write it to ${packPath(pack)}.
${issues ? `A reviewer rejected the current pack. Fix these issues, keeping every entry that is already verified and VCAA-hosted:\n- ${issues.join('\n- ')}`
  : `If that file already exists with 100+ entries and every url is on vcaa.vic.edu.au, do not redo it: return its summary.
Otherwise keep its entries that are on vcaa.vic.edu.au, drop the rest, and extend it.`}
${VCAA_ONLY}

For every question a report gives statistics for, add one entry:
{"eid": "${pack}-<year>-<exam e.g. e1|e2|mc>-<question ref>", "year": 2023, "exam": "Exam 2", "question": "Section A Q7",
 "area": "<area of study / topic>", "skill": "<what it tests, your own words, max 20 words>", "format": "mcq"|"written",
 "marks": 1, "pct_correct": 41 | null, "mean_mark": 1.2 | null, "examiner_note": "<common error, own words, max 25 words>" | null,
 "url": "<original vcaa.vic.edu.au URL of the report>"}
- MCQ: pct_correct = the % of students choosing the keyed answer, as printed. Written: mean_mark = the printed average.
- Copy numbers exactly. If a number is not printed, use null. Do not reproduce exam question text (copyright): describe the skill.
Also add "base_rates": {"mcq_mean_pct": .., "written_mean_pct_of_marks": .., "by_area": {"<area>": <mean p>}, "n_entries": ..},
computed from your entries (say so in a "method" string). Aim for 150+ entries over several years, covering every area of study.
File shape: {"subject": "${pack}", "built_by": "sonnet", "entries": [...], "base_rates": {...}, "gaps": "<areas or years with no data>"}.
Write only that file and files under difficulty/reports/${pack}/. Return the summary.`

const verifyPrompt = pack => `You are the evidence verifier for ${packPath(pack)}. The user has asked for verification results
to be saved into this file. If a write is denied, stop and report it; do not try another way.
Entries already carrying "verified_by": "haiku" were checked in an earlier run: leave them as they are.
1. Run, from ${ROOT}: python3 scripts/fetch_reports.py ${pack} && python3 scripts/verify_evidence.py ${pack}
   This downloads every cited report (live VCAA, else Internet Archive) into difficulty/reports/${pack}/, writes
   index.json (url -> local "file", "fetched_from"), and code-checks MCQ rows in .docx reports (verified_by: "code").
2. Open the pack. For every entry WITHOUT "verified_by", open its local report file from index.json with Read
   (PDFs: use the pages parameter; the statistics tables are near each question's comments). Do not use WebFetch.
   Does the report print that pct_correct / mean_mark for that question? Set "verified": true if it matches, else
   "verified": false plus "verify_note". If index.json has no file for the url, or the url is not on vcaa.vic.edu.au,
   set "verified": false with the reason. Add "verified_by": "haiku" and "checked_via": <fetched_from>. For an MCQ, also
   confirm the keyed answer (it may be shown only by cell shading); if you cannot, add "key_unconfirmed": true.
   Never correct a number from memory. Leave verified_by "code" entries untouched.
Save the file in place (same shape), editing it with a small Python script. Return counts over ALL entries.`

const reviewPrompt = pack => `You are the Opus reviewer for the evidence pack ${packPath(pack)} (reports index:
${ROOT}/difficulty/reports/${pack}/index.json). Check it, do not edit it:
- every url is on vcaa.vic.edu.au, and index.json shows where each report was fetched from;
- eids are unique; pct_correct values are 0-100 and mean_mark <= marks;
- every entry has a "verified" field; at least 80% of entries with numbers are verified true;
- base_rates match a quick recomputation from the verified entries (within ~3 points) and cover the areas of study;
- skills and notes are in the agent's own words (no copied exam text);
- spot-check 5 verified entries (from different reports) against the cached report files yourself.
accept = true only if the pack is fit to be cited. Otherwise list concrete, fixable issues.`

const judgePrompt = (b, who, note) => `You are difficulty judge "${who}". Rate every question in ${ROOT}/${b.batch} (read it).
${COURSE_NOTES(b)}
${b.pack ? `Read the evidence pack at ${packPath(b.pack)}. Ignore entries that are not "verified": true.` : ''}
${RULES}
${note ? `NOTE: ${note}\n` : ''}Rate independently; another judge is rating the same batch. Return one item per question id, all ${b.n} of them.`

const reconcilePrompt = (b, disputes, src) => `You are the Opus reconciler for ${ROOT}/${b.batch}. Two judges (haiku, sonnet)
disagreed on some questions, or one of them skipped them. Read the batch file${b.pack ? ` and the evidence pack ${packPath(b.pack)}` : ''},
check which judge's cited evidence actually supports its p, and decide the final rating for each disputed question.
${COURSE_NOTES(b)}
${RULES}
If neither judge's evidence holds up, rate it yourself with confidence "low".
${src ? `The disputed items (both judges' outputs) are under "disputes" in ${src}. Disputed ids: ${disputes.map(d => d.id).join(', ')}.` : `Disputed items (judges' outputs): ${JSON.stringify(disputes)}`}
Return one item per disputed id.`

const qaPrompt = (course, pack, files) => `You are the Opus QA reviewer for course "${course}". Review these rating files
(each is {batch, items:[{id, p, confidence, evidence, basis, judges, resolved_by}]}) against their batch files
(same path with /ratings/ -> /batches/)${pack ? ` and the evidence pack ${packPath(pack)}` : ''}:
${files.map(f => `- ${f}`).join('\n')}
${COURSE_NOTES({ course, pack })}
${RULES}
Check: every question in each batch has exactly one rating; p is plausible for the question; similar questions across
batches get consistent p; confidence matches the evidence cited (cited eids exist and are verified; "high" needs a close
match); bases are specific, not boilerplate. Sample at least 8 items per file. Do not edit files.
Put a batch in "redo" only for a real defect (missing items, systematic bias, evidence misuse, broken file), with the reason.`

const STAR = p => p >= 85 ? 1 : p >= 70 ? 2 : p >= 50 ? 3 : p >= 30 ? 4 : 5
const LV = ['low', 'medium', 'high']
const LOW = (a, c) => LV[Math.min(LV.indexOf(a), LV.indexOf(c))]
const stats = { retries: [], failed: [] }

// Code check of a model's ratings: right ids, nothing missing, p a number. Re-dispatch once with the gap named.
async function checked(run, wantIds, label) {
  let r = await run(null)
  for (let attempt = 0; attempt < 1; attempt++) {
    const got = new Set((r?.items || []).filter(x => typeof x.p === 'number').map(x => x.id))
    const miss = wantIds.filter(i => !got.has(i))
    if (!miss.length) break
    stats.retries.push(`${label}: missing ${miss.length}`)
    r = await run(`Your previous attempt missed these ids: ${miss.join(', ')}. Return all of them.`)
  }
  return r
}

async function writeBatch(b, items, pendingFile) {
  const out = ratingsPath(b.batch)
  const body = pendingFile
    ? `Read ${pendingFile}. Write {"batch": "${b.batch}", "items": <its "agreed" list followed by the items below>} to ${out}.\nItems: ${JSON.stringify(items)}`
    : `Write this JSON exactly to ${out} (create folders as needed):\n${JSON.stringify({ batch: b.batch, items })}`
  for (let attempt = 0; attempt < 2; attempt++) {
    const w = await agent(`${body}\nThen check it with python3 (json.load the file; compare its item ids with the question ids in ${ROOT}/${b.batch}) and report.`,
      { label: `write:${b.batch}${attempt ? ':retry' : ''}`, phase: 'Reconcile', model: 'haiku', effort: 'low', schema: WRITTEN })
    if (w?.ids_ok && w.items_in_file === b.n) return true
    stats.retries.push(`write ${b.batch}: ${JSON.stringify(w)}`)
  }
  stats.failed.push(`write ${b.batch}`)
  return false
}

async function rateBatch(b, ids, note) {
  const judge = (who, model) => checked(n => agent(judgePrompt(b, who, [note, n].filter(Boolean).join(' ')),
    { label: `judge:${who}:${b.batch}${n ? ':retry' : ''}`, phase: 'Judge', model, schema: RATINGS, agentType: 'general-purpose' }), ids, `judge ${who} ${b.batch}`)
  const [h, s] = await Promise.all([judge('haiku', 'haiku'), judge('sonnet', 'sonnet')])
  const H = Object.fromEntries((h?.items || []).map(x => [x.id, x])), S = Object.fromEntries((s?.items || []).map(x => [x.id, x]))
  const final = [], disputes = []
  for (const id of ids) {
    const a = H[id], c = S[id]
    // Agreement: both present, stars within 1 and p within 12 points -> average, keep the weaker confidence.
    if (a && c && Math.abs(STAR(a.p) - STAR(c.p)) <= 1 && Math.abs(a.p - c.p) <= 12) {
      final.push({ id, p: Math.round((a.p + c.p) / 2), confidence: LOW(a.confidence, c.confidence),
        evidence: [...new Set([...a.evidence, ...c.evidence])], basis: c.basis,
        judges: { haiku: [a.p, a.confidence], sonnet: [c.p, c.confidence] }, resolved_by: 'agree' })
    } else disputes.push({ id, haiku: a || null, sonnet: c || null })
  }
  if (disputes.length) final.push(...await reconcile(b, disputes))
  if (final.length !== b.n) stats.failed.push(`${b.batch}: only ${final.length}/${b.n} rated, not written`)
  return { batch: b.batch, rated: final.length, disputes: disputes.length, written: final.length === b.n && await writeBatch(b, final) }
}

async function reconcile(b, disputes, src) {
  const r = await checked(n => agent(reconcilePrompt(b, disputes, src) + (n ? `\n${n}` : ''),
    { label: `reconcile:${b.batch}${n ? ':retry' : ''}`, phase: 'Reconcile', model: 'opus', schema: RATINGS, agentType: 'general-purpose' }),
    disputes.map(d => d.id), `reconcile ${b.batch}`)
  const seen = new Set()  // models sometimes repeat an id; keep the first
  return (r?.items || []).filter(x => disputes.some(d => d.id === x.id) && !seen.has(x.id) && seen.add(x.id)).map(x => {
    const d = disputes.find(y => y.id === x.id)
    return { ...x, judges: { haiku: d.haiku && [d.haiku.p, d.haiku.confidence], sonnet: d.sonnet && [d.sonnet.p, d.sonnet.confidence] }, resolved_by: 'opus' }
  })
}

// Batch question ids are read by a cheap agent once, so code can check every later output against them.
const IDS = { type: 'object', properties: { ids: { type: 'array', items: { type: 'string' } } }, required: ['ids'] }
const batchIds = b => agent(`Run: python3 -c "import json;print(json.dumps([q['id'] for q in json.load(open('${ROOT}/${b.batch}'))['questions']]))" and return that list as ids.`,
  { label: `ids:${b.batch}`, phase: 'Judge', model: 'haiku', effort: 'low', schema: IDS }).then(r => r?.ids?.length === b.n ? r.ids : null)

async function evidence(pack) {
  let sum = await agent(researchPrompt(pack), { label: `research:${pack}`, phase: 'Research', model: 'sonnet', schema: PACK_SUMMARY, agentType: 'general-purpose' })
  let review
  for (let round = 0; round < 2; round++) {
    const v = await agent(verifyPrompt(pack), { label: `verify:${pack}${round ? ':retry' : ''}`, phase: 'Verify evidence', model: 'haiku', schema: VERIFY_SUMMARY, agentType: 'general-purpose' })
    review = await agent(reviewPrompt(pack), { label: `review:${pack}${round ? ':retry' : ''}`, phase: 'Review evidence', model: 'opus', schema: REVIEW, agentType: 'general-purpose' })
    log(`${pack}: ${sum?.entries ?? '?'} entries, verifier flagged ${v?.flagged ?? '?'}, review ${review?.accept ? 'ACCEPTED' : 'rejected: ' + (review?.issues || []).join('; ')}`)
    if (review?.accept || round === 1) break
    stats.retries.push(`research ${pack}`)
    sum = await agent(researchPrompt(pack, review?.issues || ['review failed']), { label: `research:${pack}:retry`, phase: 'Research', model: 'sonnet', schema: PACK_SUMMARY, agentType: 'general-purpose' })
  }
  // A rejected pack still feeds the judges: the build only trusts entries marked verified, so weak evidence becomes "est.".
  if (!review?.accept) stats.failed.push(`evidence ${pack} not accepted: ${(review?.issues || []).join('; ')}`)
  return { sum, review }
}

async function rateCourse(course, pack, batches, alreadyRated) {
  const results = await parallel(batches.map(b => async () => {
    const ids = await batchIds(b)
    if (!ids) { stats.failed.push(`ids ${b.batch}`); return null }
    return rateBatch(b, ids)
  }))
  const files = [...new Set([...alreadyRated, ...batches.map(b => b.batch)])].map(ratingsPath)
  // QA in groups of 6 files so each Opus reviewer can actually read what it is judging.
  const groups = Array.from({ length: Math.ceil(files.length / 6) }, (_, i) => files.slice(i * 6, i * 6 + 6))
  const qas = (await parallel(groups.map((g, i) => () => agent(qaPrompt(course, pack, g),
    { label: `qa:${course}:${i}`, phase: 'Course QA', model: 'opus', schema: QA, agentType: 'general-purpose' })))).filter(Boolean)
  if (qas.length < groups.length) stats.failed.push(`qa ${course}: ${groups.length - qas.length} group(s) returned nothing`)
  const qa = { accept: qas.length === groups.length && qas.every(q => q.accept), summary: qas.map(q => q.summary).join(' | '), redo: qas.flatMap(q => q.redo) }
  log(`${course}: QA ${qa.accept ? 'accepted' : 'flagged ' + qa.redo.length + ' batch(es)'}`)
  const redo = await parallel((qa?.redo || []).map(r => async () => {
    const path = r.batch.replace(`${ROOT}/`, '').replace('/ratings/', '/batches/')
    const m = path.match(/\/(\d{3})\.json$/)
    const b = m && { course, pack, batch: path, n: batches.find(x => x.batch === path)?.n ?? 60 }
    if (!b) return null
    stats.retries.push(`qa redo ${path}: ${r.reason}`)
    const ids = await batchIds(b); if (!ids) return null
    b.n = ids.length
    return rateBatch(b, ids, `A reviewer rejected the previous rating of this batch: ${r.reason}`)
  }))
  return { course, rated: results.filter(Boolean).length, qa: qa && { accept: qa.accept, summary: qa.summary, redo: qa.redo.length }, redone: redo.filter(Boolean).length }
}

const courses = [...new Set(BATCHES.map(b => b.course))].map(c => ({ course: c, pack: BATCHES.find(b => b.course === c).pack }))
const packs = [...new Set(courses.map(c => c.pack).filter(Boolean))]
const skipFor = c => (args.skip || []).filter(s => s.includes(`/${c}/`))

const out = await Promise.all([
  // Each pack: research -> verify -> review, then all its courses' batches. No barrier between packs.
  pipeline(packs, pack => evidence(pack),
    (ev, pack) => parallel(courses.filter(c => c.pack === pack).map(c => () =>
      rateCourse(c.course, pack, BATCHES.filter(b => b.course === c.course), skipFor(c.course)))).then(r => ({ pack, evidence: ev.review, courses: r }))),
  parallel(courses.filter(c => !c.pack).map(c => () => rateCourse(c.course, null, BATCHES.filter(b => b.course === c.course), skipFor(c.course)))),
  // Batches whose judges finished in an earlier run: only the reconcile + write remain.
  parallel((args.pending || []).map(p => async () => {
    const batch = `difficulty/batches/${p.course}/${p.idx}.json`
    const b = { course: p.course, pack: p.pack, batch, n: p.n }
    const items = await reconcile(b, p.disputeIds.map(id => ({ id })), `${ROOT}/${p.file}`)
    return { batch, reconciled: items.length, written: items.length === p.disputeIds.length && await writeBatch(b, items, `${ROOT}/${p.file}`) }
  })),
])
// Already-rated courses that only need Opus QA (e.g. salvaged from an interrupted run).
const qaOnly = await parallel((args.qaOnly || []).map(([course, pack, n]) => () => rateCourse(course, pack, [],
  Array.from({ length: Math.ceil(n / 60) }, (_, i) => `difficulty/batches/${course}/${String(i).padStart(3, '0')}.json`))))
return { results: out, qaOnly, retries: stats.retries, failed: stats.failed }
