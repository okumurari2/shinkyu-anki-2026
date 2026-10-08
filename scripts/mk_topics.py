#!/usr/bin/env python3
"""Step 2: data/topics_src/{code}.txt -> data/topics/{code}.jsonl (+ validation vs rows).
line: no|specificity|policy|flags|topic|note      (flags: '-' or comma list: disc,numeric,drug,genetic,guideline,misaligned)
Every row must have >=1 line; <=3 per row. Rows with only skip topics are skip rows."""
import csv, json, sys, collections
from pathlib import Path
R = Path(__file__).resolve().parent.parent
for code in sys.argv[1:]:
    rows = {int(r['no']): r for r in csv.DictReader(open(R/f'data/rows/{code}.csv', encoding='utf-8'))}
    per = collections.defaultdict(list)
    for ln, line in enumerate(open(R/f'data/topics_src/{code}.txt', encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'): continue
        p = line.split('|')
        assert len(p) == 6, f'{code}:{ln} fields={len(p)}: {line}'
        no, spec, pol, flags, topic, note = p
        assert spec in ('high', 'mid', 'low') and pol in ('make', 'skip'), f'{code}:{ln}'
        per[int(no)].append(dict(dept_code=code, src_no=int(no), specificity=spec, card_policy=pol,
                                 flags=[] if flags == '-' else flags.split(','), topic=topic, note=note))
    miss = [n for n in rows if n not in per]; extra = [n for n in per if n not in rows]
    assert not miss and not extra, f'{code} missing={miss} extra={extra}'
    out = []
    for n in sorted(per):
        assert len(per[n]) <= 3, f'{code} No{n} >3 topics'
        for i, t in enumerate(per[n]):
            t['topic_id'] = f'{code}-{n:02d}-{"abc"[i]}'
            if rows[n]['comment'].strip() == '': assert t['card_policy'] == 'skip', f'{code} No{n} empty comment but make'
            out.append(t)
    with open(R/f'data/topics/{code}.jsonl', 'w', encoding='utf-8') as f:
        for t in out: f.write(json.dumps(t, ensure_ascii=False) + '\n')
    c = collections.Counter((t['specificity'], t['card_policy']) for t in out)
    print(code, len(out), 'topics', dict(c))
