#!/usr/bin/env python3
"""
4단계: 뜻풀이를 합치고, 각 단어에 소설 속 실제 예문을 붙인다.

  1) data/reused_gloss.json (옆 프로젝트 Silkworm 에서 가져온 뜻) + gloss_raw/*.tsv (이 소설용으로 새로 받은 뜻)
     → 단어별 품사·뜻·레벨.  gloss_raw 가 있으면 그것이 우선.
  2) 본문(book.json)을 문장 단위로 훑어, 각 단어(변화형 포함)가 들어 있는 문장 중 14단어에 가까운 것을 예문으로.
  3) 빈도 1회짜리도 예문을 붙인다 (이 책은 작아서 용량 부담이 없다)

결과물: data/vocab.json  각 항목: w=단어 p=품사 m=한국어뜻 l=레벨 n=빈도 f=변화형 e=예문 c=예문 위치(장.문단.문장)
"""
import json, re, os, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
L = json.load(open(D('data', 'lemma.json'), encoding='utf-8'))
g, forms = L['g'], L['forms']
g_all = set(g)

gloss = {}
reused = json.load(open(D('data', 'reused_gloss.json'), encoding='utf-8')) if os.path.exists(D('data', 'reused_gloss.json')) else {}
gloss.update(reused)
n_new = 0
for fn in sorted(glob.glob(D('gloss_raw', '*.tsv'))):
    src = D('chunks', os.path.basename(fn).replace('.tsv', '.txt'))
    if not os.path.exists(src):
        print(f"  경고: 짝이 되는 청크 파일이 없습니다 - {fn}"); continue
    srcw = [l.split('\t')[0].strip() for l in open(src, encoding='utf-8').read().strip().split('\n')]
    out = [l for l in open(fn, encoding='utf-8').read().strip().split('\n') if l.strip()]
    if len(out) != len(srcw):
        print(f"  경고: 줄 수 불일치 {os.path.basename(fn)} — 결과 {len(out)} vs 입력 {len(srcw)}")
    for i, line in enumerate(out):
        p = line.split('\t')
        if len(p) < 4 or i >= len(srcw): continue
        gloss[srcw[i]] = {'p': p[1].strip(), 'm': p[2].strip(), 'l': int(re.sub(r'\D', '', p[3]) or 2)}
        n_new += 1
# --- 수정표(gloss_fix.json)를 맨 마지막에 덮어쓴다 ---
#     재사용한 뜻이 이 소설과 맞지 않는 것을 바로잡는다. 여기가 최우선.
fixp = D('data', 'gloss_fix.json')
n_fix = 0
if os.path.exists(fixp):
    for w, fx in json.load(open(fixp, encoding='utf-8'))['words'].items():
        if w in g_all:                      # 본문에 실제로 있는 단어만
            gloss[w] = fx; n_fix += 1
print(f"뜻풀이 {len(gloss):,}개 (재사용 {len(reused):,} + 새로 {n_new:,} + 수정 {n_fix:,})")
missing = [w for w in g if w not in gloss]
if missing:
    print(f"  ! 뜻풀이 없는 단어 {len(missing)}개 — scripts/03_make_chunks.py --missing 를 실행하세요: {missing[:20]}")

book = json.load(open(D('data', 'book.json'), encoding='utf-8'))
sents = []
for c in book['chapters']:
    for pi, p in enumerate(c['paras']):
        for si, s in enumerate(p):
            sents.append((f"{c['n']}.{pi}.{si}", s))
index = collections.defaultdict(list)
for i, (sid, s) in enumerate(sents):
    for w in set(re.findall(r"[A-Za-z][A-Za-z'’-]*", s.lower().replace('’', "'"))):
        index[w.strip("'-")].append(i)

final = []
for w, n in g.items():
    if w not in gloss: continue
    e, cid = '', ''
    cand = [i for f in ([w] + forms.get(w, [])) for i in index.get(f, [])]
    if cand:
        best = min(cand, key=lambda i: abs(len(sents[i][1].split()) - 14))
        cid, e = sents[best][0], sents[best][1][:220]
    r = dict(gloss[w])
    r.update({'w': w, 'n': n, 'f': [x for x in forms.get(w, []) if x != w][:6], 'e': e, 'c': cid})
    final.append(r)
final.sort(key=lambda r: -r['n'])
out = D('data', 'vocab.json')
json.dump(final, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"저장: {out} — {len(final):,}개 (레벨별 {dict(sorted(collections.Counter(r['l'] for r in final).items()))})")
