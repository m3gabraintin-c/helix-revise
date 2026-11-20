# Hints and glossary check (AI-written pilot)

## Counts
- `content/hints/methods.json`: 58 hints, 10 multi-part questions (all parts covered).
- `content/hints/chem.json`: 39 hints, 6 multi-part questions (all parts covered).
- `content/glossary/chem.json`: 109 terms.
- `content/glossary/vce-psych34.json`: 102 terms.

Multi-part questions were taken from the `d['Q']` subtopics of each subject plus `d['X'][subject]`. Part index counts only `kind:"part"` pieces, in order.

## How it was checked
- Each hint was written after reading the part's question, answer, worked steps and the preceding info pieces. It was then re-read against the worked solution to confirm it names the method or relationship and states no result.
- Script checks: hint keys equal exactly the set of real `<questionId>#<partIndex>` keys (none missing, none extra); every hint is 35 words or fewer; no `$`; all JSON parses.
- Glossary: every term (or an alias) appears as a whole word in at least one question of that subject; terms are sorted and unique; every definition is 25 words or fewer; a script flagged any definition containing its own term and those were reworded.
- Terms were picked from word and phrase frequency counts over each subject's question text. Aliases that do not occur in the text were removed.
- Definitions were checked by hand against VCE Chemistry and VCE Psychology Units 3-4 usage (for example anode and cathode polarity in galvanic versus electrolytic cells, GAS stages, appraisal types, memory types).

## Limits and notes
- The check is by one author with no independent review; a teacher should skim before launch.
- Low-frequency chem terms kept (1-2 occurrences): chromatography, covalent bond, dehydration, homogeneous catalyst, theoretical yield.
- Some hints mention a formula or setup (for example Q = It, q = mcΔT, n = m ÷ M). These are named methods, not results.
- Hints for "Show that" parts point to the method only; the target value is already in the question.

## Omitted
- No hints omitted. No glossary terms omitted for uncertainty; no candidates were rejected on accuracy grounds. The psychology glossary excludes sleep-disorder details beyond delayed sleep phase.
