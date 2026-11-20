#!/usr/bin/env python3
"""Extract machine-checkable single-number answers from the DATA line of index.html.

Writes content/answers.json and content/answers.review.md. Stdlib only, rerunnable.
  python3 scripts/extract_answers.py            # extract
  python3 scripts/extract_answers.py --selftest # unit checks

Principle: when in doubt, exclude. Only an answer whose WHOLE text is a single
sentence ending in exactly one number (+ optional unit) is kept, and only when
the question asks for one value.

Tolerance (tol), by how the model answer is written:
  * d decimal places           -> tol = 0.5 * 10^-d
  * sci notation m x 10^k      -> tol = 0.5 * 10^(k-d), d = decimals of m
  * integer                    -> tol = 0.5, or 0 if an exact count is asked (how many / number of)
  * question says "n significant figures" -> tol = 0.5 * 10^(floor(log10|v|)-n+1),
    i.e. anything that rounds to the same n s.f. (answer must itself have n s.f.,
    else excluded); same check for "n decimal places"
  * fraction a/b               -> tol 1e-9 if it terminates as a decimal, else 5e-4
  * percentages are stored as the number (93.3) with unit "%".
Integers hedged with about/approximately are excluded (rounding unknown).
"""
import json, math, os, random, re, sys
from collections import Counter, defaultdict
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUP = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
SUPR = {v: k for k, v in SUP.items()}


def norm(t):
    t = re.sub(r'\\[()\[\]]', '', t)
    t = re.sub(r'\\(?:times|cdot)', '×', t)
    t = t.replace('\\div', '÷').replace('\\approx', '≈').replace('\\%', '%').replace('\\$', '$')
    t = t.replace('\\circ', '°').replace('\\mu', 'µ').replace('\\Omega', 'Ω').replace('{,}', ',')
    t = re.sub(r'\\[dt]?frac\{(\d+)\}\{(\d+)\}', r'\1/\2', t)
    t = re.sub(r'\\(?:text|textrm|mathrm)\{([^{}]*)\}', r'\1', t)
    t = re.sub(r'\\[,;! ]|\\quad|\\qquad', ' ', t)
    t = re.sub(r'\^\{([^{}]*)\}', r'^\1', t)
    t = re.sub('[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+', lambda m: '^' + ''.join(SUP[c] for c in m.group()), t)
    t = t.replace('−', '-').replace('·', ' ').replace('×', ' × ')
    t = re.sub(r'\[\d+\]|\(\d+ marks?\)', '', t)
    t = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', t)  # thousands separators
    return re.sub(r'\s+', ' ', t).strip()


TOK = r'[A-Za-zµΩ°]{1,12}(?:\^-?\d)?'
STOP = {'to', 'or', 'and', 'is', 'are', 'of', 'the', 'at', 'in', 'for', 'so', 'if', 'but', 'when', 'with', 'by', 'from', 'then'}
NUM = r'(?P<sci>\d+(?:\.\d+)? ?× ?10\^-?\d+)|(?P<frac>\d+/\d+)|(?P<dec>\d+(?:\.\d+)?)'
FINAL = re.compile(r'^(?P<cur>[$£€]?)(?P<sign>[+-]?)(?:' + NUM + r')(?P<pct> ?%)?(?: ?(?P<unit>°?' + TOK + r'(?:[ /]' + TOK + r'){0,2}))?$')
HEDGE = re.compile(r'^(?:about|approximately|approx\.?|around|roughly|≈|~) ?', re.I)


def unit_variants(u):
    if not u:
        return None, []
    groups, neg = [], False
    for part in u.split('/'):
        for tk in part.split():
            m = re.match(r'(.+?)(?:\^(-?\d))?$', tk)
            e = int(m.group(2) or 1)
            groups.append((m.group(1), -e if neg else e))
        neg = True
    fmt = lambda b, e, uni: b + ('' if e == 1 else (''.join(SUPR[c] for c in str(e)) if uni else '^%d' % e))
    A = ' '.join(fmt(b, e, 0) for b, e in groups)
    B = ' '.join(fmt(b, e, 1) for b, e in groups)
    pos = [fmt(b, e, 0) for b, e in groups if e > 0]
    ng = [fmt(b, -e, 0) for b, e in groups if e < 0]
    out = [A, B] + (['/'.join([' '.join(pos), ' '.join(ng)])] if pos and ng else [])
    return A, list(dict.fromkeys(out))


ASK = re.compile(r'\b(calculate|find|determine|evaluate|how many|how much|what is|what was|what mass|what volume|how far|how long|how fast|predict|estimate|compute|work out|what percentage|what fraction|what proportion|what number)\b', re.I)
BAD_Q = re.compile(r'\b(show that|sketch|graph|explain|describe|state|write|name|solve|differentiate|integrate|exact|express|simplify|factorise|expand|compare|justify|prove|identify|list|both|hence|respectively|coordinates|interval|range|domain|which)\b|nearest (?:ten|hundred|thousand|\d)|(?:^|\s)\([a-z]\)', re.I)
MULTI_Q = re.compile(r'\band (?:the|its|find|calculate|determine|state|then|also)\b|\bhow many\b.*\bhow many\b', re.I)
EXACT_COUNT = re.compile(r'\bhow many\b|\bnumber of\b|\bcount\b', re.I)
SF = re.compile(r'(\d+|one|two|three|four|five) (?:significant figures?|sig\.? ?figs?\.?|s\.f\.?)', re.I)
DP = re.compile(r'(\d+|one|two|three|four|five) decimal places?', re.I)
WORDN = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
cnt = lambda s: int(s) if s.isdigit() else WORDN[s.lower()]


def final_number(ans):
    """Return (clause, reason): normalised text of the single final value, or (None, reason)."""
    s = norm(ans)
    s = re.sub(r'\s*\.$', '', s)
    # trailing numeric working in brackets, e.g. "1350 (1000 + 5 x 70)"
    s = re.sub(r'\s*\((?![^()]*\b[A-Za-z]{4,})[^()]*\)$', '', s)
    if re.search(r';|\band\b|\bor\b|\bto\b|\bboth\b|[<>≤≥±]|\.\s', s):
        return None, 'multiple_values_or_sentences'
    if re.search(r',(?!\s*(?:so|hence|therefore|giving|thus|which gives)\b)', s):
        return None, 'multiple_values_or_sentences'
    s = re.split(r'\b(?:so|hence|therefore|giving|thus|gives|which gives)\b', s)[-1]
    s = re.split(r'[=≈]', s)[-1].strip(' ,')
    h = HEDGE.match(s)
    return (s, None) if not h else (s[h.end():] + '\x00', None)  # \x00 marks a hedge


def extract(prompt, answer):
    """Return (item_dict, None) or (None, reason)."""
    q = norm(prompt)
    if not ASK.search(q):
        return None, 'question_not_single_value'
    if BAD_Q.search(q) or MULTI_Q.search(q) or len(ASK.findall(q)) > 1:
        return None, 'question_multi_or_symbolic'
    s, why = final_number(answer)
    if why:
        return None, why
    hedged = s.endswith('\x00')
    s = s.rstrip('\x00')
    m = FINAL.match(s)
    if not m:
        return None, 'not_a_single_number'
    unit = m.group('unit')
    if unit and (any(w in STOP for w in re.split(r'[ /]', unit)) or re.search(r'[A-Za-z]{3,}.*[A-Za-z]{3,}.*[A-Za-z]{3,}', unit)
                 or (re.search(r'[ /]', unit) and re.search(r'[A-Za-z]{5,}', unit))):  # e.g. "m/s upward"; words only as a lone unit
        return None, 'not_a_single_number'
    sign = -1 if m.group('sign') == '-' else 1
    if m.group('sci'):
        mant, ex = re.split(r' ?× ?10\^', m.group('sci'))
        v = sign * float(mant) * 10 ** int(ex)
        dp = len(mant.split('.')[1]) if '.' in mant else 0
        tol = 0.5 * 10 ** (int(ex) - dp)
        digits = mant.replace('.', '').lstrip('0')
    elif m.group('frac'):
        a, b = map(int, m.group('frac').split('/'))
        if b == 0 or hedged:
            return None, 'not_a_single_number'
        v = sign * a / b
        k = Fraction(a, b).denominator
        while k % 2 == 0:
            k //= 2
        while k % 5 == 0:
            k //= 5
        tol = 1e-9 if k == 1 else 5e-4
        digits, dp = None, None
    else:
        t = m.group('dec')
        v = sign * float(t)
        dp = len(t.split('.')[1]) if '.' in t else 0
        digits = t.replace('.', '').lstrip('0')
        if dp == 0 and hedged:
            return None, 'hedged_integer'
        tol = 0.5 * 10 ** -dp
        if dp == 0 and EXACT_COUNT.search(q):
            tol = 0
    sf = SF.search(q)
    if sf:
        n = cnt(sf.group(1))
        trailing0 = not m.group('sci') and dp == 0 and digits.endswith('0') and len(digits) > 1
        if digits is None or v == 0 or len(digits) != n or trailing0:
            return None, 'sig_fig_mismatch'
        tol = 0.5 * 10 ** (math.floor(math.log10(abs(v))) - n + 1)
    dpq = DP.search(q)
    if dpq and (dp is None or dp != cnt(dpq.group(1))):
        return None, 'dp_mismatch'
    if m.group('pct'):
        unit = '%'
    elif m.group('cur'):
        unit = m.group('cur')
    if unit in ('%', '$', '£', '€'):
        u, variants = unit, [unit] + (['percent'] if unit == '%' else [])
    else:
        u, variants = unit_variants(unit)
    item = {'v': float('%.12g' % v), 'tol': float('%.10g' % tol)}
    if u:
        item.update(unit=u, units=variants)
    return item, None


def load():
    l = next(l for l in open(os.path.join(ROOT, 'index.html'), encoding='utf-8') if l.startswith('const DATA = '))
    return json.loads(l[len('const DATA = '):].rstrip().rstrip(';'))


def candidates(d):
    """Yield (subject, key, prompt, answer)."""
    ids = sorted((s[0] for s in d['S']), key=len, reverse=True)
    owner = {st[0]: s[0] for s in d['S'] for ch in s[4] for st in ch[2]}

    def multi(subj, row):
        n = 0
        for p in row['pieces']:
            if p.get('kind') == 'part':
                yield subj, '%s#%d' % (row['id'], n), p['question'], p.get('answer') or ''
                n += 1

    for slug, rows in d['Q'].items():
        subj = owner.get(slug) or next((i for i in ids if slug.startswith(i)), '?')
        for r in rows:
            if isinstance(r, dict):
                yield from multi(subj, r)
            elif r[1] == 1:
                yield subj, r[0], r[2], r[3]
    for subj, rows in d['X'].items():
        for r in rows:
            yield from multi(subj, r)


def main():
    d = load()
    out, why, info, meta = {}, defaultdict(Counter), defaultdict(Counter), {}
    for subj, key, prompt, ans in candidates(d):
        info[subj]['candidates'] += 1
        item, reason = extract(prompt, ans)
        if item:
            out[key] = item
            meta[key] = (prompt, ans)
            info[subj]['included'] += 1
        else:
            why[subj][reason] += 1
    os.makedirs(os.path.join(ROOT, 'content'), exist_ok=True)
    with open(os.path.join(ROOT, 'content', 'answers.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    for subj in sorted(info):
        print('%-14s candidates=%-5d included=%-4d excluded: %s' % (subj, info[subj]['candidates'], info[subj]['included'], dict(why[subj])))
    print('TOTAL included', len(out), 'of', sum(i['candidates'] for i in info.values()))
    random.seed(20240607)
    keys = sorted(out)
    lines = ['# answers.json review sample (%d of %d)\n' % (min(40, len(keys)), len(keys))]
    for k in random.sample(keys, min(40, len(keys))):
        lines += ['## %s' % k, '- Question: %s' % meta[k][0], '- Model answer: %s' % meta[k][1],
                  '- Extracted: `%s`\n' % json.dumps(out[k], ensure_ascii=False)]
    with open(os.path.join(ROOT, 'content', 'answers.review.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def selftest():
    def ok(p, a, **kw):
        it, r = extract(p, a)
        assert it, (p, a, r)
        for k, v in kw.items():
            assert (abs(it[k] - v) < 1e-12) if isinstance(v, float) else it[k] == v, (a, it)
        return it

    def no(p, a):
        it, r = extract(p, a)
        assert not it, (p, a, it)

    it = ok('Calculate the acceleration.', 'a = 5.0 / 2.0 = 2.5 m s^{-2}.', v=2.5, tol=0.05, unit='m s^-2')
    assert 'm/s^2' in it['units'] and 'm s⁻²' in it['units'], it
    ok('Calculate the speed.', 'About 6.5 × 10³ m/s', v=6500.0, tol=50.0)
    ok('Find the value.', '\\(3.2 \\times 10^{-4}\\) mol', v=3.2e-4, tol=0.5e-5)
    ok('Find the probability.', '\\(\\dfrac{3}{8}\\)', v=0.375, tol=1e-9)
    ok('Find the probability.', '1/3', tol=5e-4)
    ok('Calculate the percentage yield.', 'Yield = 28.0 ÷ 30.0 × 100 = 93.3%', v=93.3, unit='%')
    ok('Find the remainder when P(x) is divided by x + 2.', '-55', v=-55.0, tol=0.5)
    ok('Find the temperature change.', '\\(-4.5\\) °C', v=-4.5)
    ok('How many runners finish?', '125 runners', tol=0)
    ok('Calculate the mass to 3 significant figures.', '12.3 g', tol=0.05)
    ok('Find the cost.', '$1,235.50', v=1235.5)
    ok('Find y.', '1350 (1000 + 5 × 70).', v=1350.0)
    no('Solve for x.', 'x = 2')
    no('Find x.', 'x = 2 or x = -3')
    no('Find x and y.', 'x = 5 and y = -4')
    no('Find x.', 'x = 3, y = 5')
    no('Find the exact value.', '\\(\\frac{\\pi}{3}\\)')
    no('Find the angle.', '\\(\\frac{\\pi}{3} + k\\pi\\)')
    no('Find the length.', '\\(3\\sqrt{2}\\)')
    no('Find x.', 'x = 2x + 1')
    no('Find the range of k.', '-2 < k < 2')
    no('Find the stationary point.', '(1, 2)')
    no('Find the mean and the standard deviation.', '12')
    no('Calculate the speed.', 'About 125')
    no('Explain why the sky is blue.', 'Scattering')
    no('Show that the area is 12.', '12')
    no('Find the value to 3 significant figures.', '12.34')
    no('Find x.', 'Mean = 12; standard deviation ≈ 3.81')
    print('selftest OK')


if __name__ == '__main__':
    selftest() if '--selftest' in sys.argv else main()
