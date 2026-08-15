#!/usr/bin/env python3
"""
3단계: 한국어 뜻풀이가 필요한 단어를 조각내 나눈다.

  · 이미 뜻풀이가 있는 단어(gloss_raw/*.tsv 에 있거나, 옆 폴더 silkworm-project 의 vocab.json 에 있는 것)는 빼고
  · 나머지를 빈도순으로 정렬해 조각(chunks/T01.txt …)당 약 430단어씩 나눈다
  · 각 줄: 단어<TAB>빈도

이 조각들을 서브에이전트(클로드)에게 맡겨 `단어<TAB>품사<TAB>한국어뜻<TAB>레벨` 로 채우게 하고
결과를 gloss_raw/T01.tsv … 로 저장한다 (프롬프트: PROMPTS.md).

사용법: python scripts/03_make_chunks.py            # 처음
        python scripts/03_make_chunks.py --missing  # 뜻풀이 안 된 것만 다시
"""
import json, os, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
SILK = os.path.join(os.path.dirname(ROOT), 'silkworm-project', 'data', 'vocab.json')
PER = 430

L = json.load(open(D('data', 'lemma.json'), encoding='utf-8'))
g = L['g']

have = set()
for fn in glob.glob(D('gloss_raw', '*.tsv')):
    for line in open(fn, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 4: have.add(p[0].strip())
reuse = {}
if os.path.exists(SILK):
    for r in json.load(open(SILK, encoding='utf-8')):
        if r['w'] in g and r['w'] not in have and r['l'] != 0:
            reuse[r['w']] = {'p': r['p'], 'm': r['m'], 'l': r['l']}
json.dump(reuse, open(D('data', 'reused_gloss.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f"원형 {len(g):,} / 이미 뜻풀이 있음 {len(have):,} / Silkworm 에서 재사용 {len(reuse):,}")

todo = sorted((w for w in g if w not in have and w not in reuse), key=lambda w: (-g[w], w))
print(f"뜻풀이 필요 {len(todo):,}개")
if '--missing' in sys.argv:
    prefix = 'M'
    for fn in glob.glob(D('chunks', 'M*.txt')): os.remove(fn)
else:
    prefix = 'T'
os.makedirs(D('chunks'), exist_ok=True)
for k in range(0, len(todo), PER):
    name = f"{prefix}{k // PER + 1:02d}.txt"
    with open(D('chunks', name), 'w', encoding='utf-8') as f:
        f.write('\n'.join(f"{w}\t{g[w]}" for w in todo[k:k + PER]) + '\n')
    print(f"  chunks/{name}: {min(PER, len(todo) - k)}단어")
