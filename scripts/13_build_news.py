#!/usr/bin/env python3
"""
13단계: 받아 온 기사를 소설과 똑같은 학습 자료로 가공한다.

  1) 문단을 문장으로 나눈다 (01번과 같은 방식)
  2) 모든 문장을 spaCy 로 구문 분석한다 (06번과 같은 방식)
     → 주어·동사 위치, 의미 단위 경계와 역할, 무엇이 무엇을 꾸미는지
  3) 기사마다 어휘를 훑어 커버리지와 새 단어 목록을 만든다 (07번과 같은 방식)
     사전(vocab.json + news_gloss.json)에 없는 단어는 따로 모아 보고한다

결과물: data/news.json  {articles:[{id,title,url,date,source,paras,syntax,words,tok,...}]}
"""
import json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
D = lambda *p: os.path.join(ROOT, 'data', *p)
SRC = D('news_src')

from importlib import import_module
P1 = import_module('01_parse_gutenberg')       # split_sentences
P6 = import_module('06_parse_syntax')          # analyse_part / split_parts

vocab = json.load(open(D('vocab.json'), encoding='utf-8'))
lem = json.load(open(D('lemma.json'), encoding='utf-8'))
extra = json.load(open(D('news_gloss.json'), encoding='utf-8')) if os.path.exists(D('news_gloss.json')) else {}

# 단어 → 어휘 번호 (소설 어휘 + 뉴스 보충 어휘)
idx_of = {r['w']: i for i, r in enumerate(vocab)}
forms = {}
for lemma, fs in lem['forms'].items():
    if lemma in idx_of:
        forms[lemma] = idx_of[lemma]
        for f in fs: forms.setdefault(f, idx_of[lemma])
news_vocab = []
for w, g in sorted(extra.items()):
    news_vocab.append({'w': w, 'p': g['p'], 'm': g['m'], 'l': g.get('l', 2), 'n': 0, 'f': g.get('f', []), 'e': '', 'c': ''})
base = len(vocab)
for k, r in enumerate(news_vocab):
    forms.setdefault(r['w'], base + k)
    for f in r['f']: forms.setdefault(f, base + k)


def look(w):
    w = w.lower().strip("'-")
    if w in forms: return forms[w]
    if w.endswith("'s") and w[:-2] in forms: return forms[w[:-2]]
    for suf, cut in (('s', 1), ('es', 2), ('ed', 2), ('ing', 3), ('d', 1)):
        if w.endswith(suf) and len(w) - cut >= 3:
            b = w[:-cut]
            if b in forms: return forms[b]
            if b + 'e' in forms: return forms[b + 'e']
    return -1


def main():
    files = sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []
    if not files:
        print("받아 둔 기사가 없습니다. 먼저 scripts/12_fetch_nasa.py 를 실행하세요."); return
    arts, unknown = [], collections.Counter()
    for fn in files:
        rec = json.load(open(os.path.join(SRC, fn), encoding='utf-8'))
        paras = [P1.split_sentences(p) for p in rec['paras']]
        paras = [p for p in paras if p]
        # 구문 분석
        syn = []
        for para in paras:
            row = []
            for s in para:
                chunks, S, V, fin = [], None, None, 0
                for j, (off, part) in enumerate(P6.split_parts(s)):
                    doc = P6.nlp(part)
                    Sp, Vp, ch, f = P6.analyse_part(doc, off)
                    b = len(chunks)
                    if j == 0: S, V = Sp, Vp
                    chunks.extend([[c, r if j == 0 else ('K>' + r if not r.startswith('K') else r),
                                    (hk + b if hk is not None and hk >= 0 else -1)] for c, r, hk in ch])
                    fin += f
                if chunks: chunks[0][0] = 0
                row.append([S, V, chunks, fin] if chunks else None)
            syn.append(row)
        # 어휘
        tok = kn = 0
        cnt = collections.Counter()
        for para in paras:
            for s in para:
                for w in re.findall(r"[A-Za-z][A-Za-z'-]*", s):
                    tok += 1
                    i = look(w)
                    if i < 0:
                        unknown[w.lower()] += 1
                        continue
                    v = vocab[i] if i < base else news_vocab[i - base]
                    if v['l'] == 1: kn += 1
                    cnt[i] += 1
        words = sorted(((i, c) for i, c in cnt.items()
                        if (vocab[i]['l'] if i < base else news_vocab[i - base]['l']) in (2, 3)),
                       key=lambda x: -x[1])
        arts.append({'id': rec['id'], 'title': rec['title'], 'url': rec['url'], 'date': rec['date'],
                     'source': rec['source'], 'paras': paras, 'syn': syn,
                     'tok': tok, 'l1': kn, 'words': [[i, c] for i, c in words[:120]]})
        print(f"  {rec['date']}  {rec['title'][:44]:<46} 문장 {sum(len(p) for p in paras):>3} · 단어 {tok:>4}")
    arts.sort(key=lambda a: a['date'], reverse=True)
    json.dump({'articles': arts, 'vocab': news_vocab},
              open(D('news.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"\n저장: {D('news.json')} — 기사 {len(arts)}건")
    if unknown:
        top = unknown.most_common(40)
        json.dump({w: n for w, n in unknown.most_common(400)},
                  open(D('news_unknown.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"사전에 없는 단어 {len(unknown)}종 (연 {sum(unknown.values())}회). 자주 나오는 것:")
        print('  ' + ', '.join(f"{w}({n})" for w, n in top[:24]))
        print(f"  → data/news_unknown.json 에 저장. 뜻을 붙여 data/news_gloss.json 에 넣으면 사전에 추가됩니다.")


if __name__ == '__main__':
    main()
