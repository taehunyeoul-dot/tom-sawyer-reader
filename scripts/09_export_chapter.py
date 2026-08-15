#!/usr/bin/env python3
"""
9단계(보조): 튜터 분석을 맡길 장(章)의 입력 파일을 만든다.

사용법:  python scripts/09_export_chapter.py 6 7 8
  → tutor/work/chapter_06.txt  (장 전문, 문장마다 [장.문단.문장] 번호)
    tutor/work/hard_06.txt     (분석할 어려운 문장 후보 22개 — 길거나 복잡한 구조가 있는 문장)
    tutor/work/vocab_06.txt    (그 장의 레벨 2·3 단어 목록)

그 다음 tutor/PROMPT.md 의 지시대로 서브에이전트에게 맡기고,
결과 analyses_NN.json / guide_NN.json 을 tutor/ 에 저장한 뒤 08번을 다시 돌린다.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
book = json.load(open(D('data', 'book.json'), encoding='utf-8'))
rd = json.load(open(D('data', 'reader_data.json'), encoding='utf-8'))
vocab = json.load(open(D('data', 'vocab.json'), encoding='utf-8'))
HARD = {3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16}   # '어렵다'고 볼 구조 유형
N_HARD = 22

os.makedirs(D('tutor', 'work'), exist_ok=True)
chs = [int(x) for x in sys.argv[1:]] or [1]
for n in chs:
    c = book['chapters'][n - 1]; rc = rd['chapters'][n - 1]
    tagmap = {(pi, si): ids for pi, si, ids in rc['tags']}
    cands = []
    for pi, para in enumerate(c['paras']):
        for si, s in enumerate(para):
            L = len(s.split()); ids = tagmap.get((pi, si), [])
            hard = len(HARD & set(ids))
            if L >= 18 or (hard and L >= 12):
                cands.append((L + 5 * hard, pi, si, s, ids))
    cands.sort(reverse=True)
    top = sorted(cands[:N_HARD], key=lambda x: (x[1], x[2]))
    with open(D('tutor', 'work', f'chapter_{n:02d}.txt'), 'w', encoding='utf-8') as f:
        f.write(f"CHAPTER {n} ({c['roman']}) — {c['title']}\n\n")
        for pi, para in enumerate(c['paras']):
            for si, s in enumerate(para):
                f.write(f"[{n}.{pi}.{si}] {s}\n")
            f.write('\n')
    with open(D('tutor', 'work', f'hard_{n:02d}.txt'), 'w', encoding='utf-8') as f:
        for score, pi, si, s, ids in top:
            f.write(f"[{n}.{pi}.{si}] (tags={ids}) {s}\n")
    with open(D('tutor', 'work', f'vocab_{n:02d}.txt'), 'w', encoding='utf-8') as f:
        for i, cnt in rc['words'][:80]:
            v = vocab[i]
            f.write(f"{v['w']}\t{v['p']}\t{v['m']}\tL{v['l']}\t이장{cnt}회/전체{v['n']}회\n")
    print(f"{n}장: 후보 {len(cands)}개 중 {len(top)}개 → tutor/work/chapter_{n:02d}.txt, hard_{n:02d}.txt, vocab_{n:02d}.txt")
