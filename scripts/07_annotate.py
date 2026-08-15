#!/usr/bin/env python3
"""
7단계: 읽기 앱이 쓸 '장(章)별 주석 데이터'를 만든다.

  1) 본문의 모든 단어(표면형)를 원형(vocab.json 항목)에 연결하는 표  forms: {"looked": 123, ...}
  2) 장마다: 총 단어 수, 기초어휘(레벨1)·고유명사·미확인 단어 수(커버리지 계산용),
             이 장에 나오는 레벨 2·3 단어와 장 안 출현 횟수,
             문장구조 18유형에 해당하는 문장 표시 (05_find_patterns.py 의 PATTERNS 를 그대로 씀)
  3) 각 단어가 처음 등장하는 장 번호

결과물: data/reader_data.json
"""
import re, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
D = lambda *p: os.path.join(ROOT, 'data', *p)
from importlib import import_module
P = import_module('05_find_patterns')
CPATS = P.CPATS

book = json.load(open(D('book.json'), encoding='utf-8'))
lem = json.load(open(D('lemma.json'), encoding='utf-8'))
vocab = json.load(open(D('vocab.json'), encoding='utf-8'))

idx_of = {r['w']: i for i, r in enumerate(vocab)}
forms = {}
for lemma, fs in lem['forms'].items():
    if lemma not in idx_of: continue
    i = idx_of[lemma]
    forms[lemma] = i
    for f in fs: forms.setdefault(f, i)
propn = set(w.lower() for w in lem['propn'])
print(f"표면형 {len(forms):,}개 → 어휘 {len(vocab):,}개 / 고유명사 {len(propn)}")


def tokens(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return [w.lower().strip("'-") for w in re.findall(r"[A-Za-z][A-Za-z'-]*", s)]


def lookup(w):
    if w in forms: return forms[w]
    if w.endswith("'s") and w[:-2] in forms: return forms[w[:-2]]
    if w.endswith("s'") and w[:-1] in forms: return forms[w[:-1]]
    return -1


first, chapters_out, tagcount = {}, [], collections.Counter()
for c in book['chapters']:
    tok = l1 = pn = un = 0
    cnt = collections.Counter(); tags = []
    for pi, para in enumerate(c['paras']):
        for si, sent in enumerate(para):
            for w in tokens(sent):
                if not w: continue
                tok += 1
                if w in propn or (w.endswith("'s") and w[:-2] in propn): pn += 1; continue
                i = lookup(w)
                if i < 0: un += 1; continue
                if vocab[i]['l'] == 1: l1 += 1
                cnt[i] += 1
                first.setdefault(i, c['n'])
            ns = sent.replace('_', '')
            ids = [k for k, p in CPATS.items() if p.search(ns)]
            if ids:
                tags.append([pi, si, ids])
                for k in ids: tagcount[k] += 1
    words = sorted(((i, n) for i, n in cnt.items() if vocab[i]['l'] in (2, 3)),
                   key=lambda x: (-x[1], -vocab[x[0]]['n']))
    chapters_out.append({'n': c['n'], 'tok': tok, 'l1': l1, 'pn': pn, 'un': un,
                         'words': [[i, n] for i, n in words], 'tags': tags})
    cov = (l1 + pn) / tok * 100 if tok else 0
    print(f"  {c['n']:>2}장  단어 {tok:>5,}  기초+고유명사 커버 {cov:5.1f}%  레벨2·3 종류 {len(words):>4}  구조태그 {len(tags):>4}")

out = {'forms': forms, 'first': {str(k): v for k, v in first.items()}, 'chapters': chapters_out,
       'tagcount': {str(k): v for k, v in tagcount.items()}}
json.dump(out, open(D('reader_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"저장: {D('reader_data.json')}")
