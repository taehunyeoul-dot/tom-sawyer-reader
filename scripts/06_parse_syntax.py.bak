#!/usr/bin/env python3
"""
6단계: 소설의 '모든 문장'에 문장구조 안내를 붙인다 (자동 구문 분석).

무엇을 만드나
  문장마다
    · 주절의 주어(S)와 동사(V)가 글자 몇 번째~몇 번째인지
    · 문장을 '의미 단위'로 자른 경계와, 각 단위의 역할(주어/동사/목적어/전치사구/부사절/분사구문/관계절/인용 …)
  → data/syntax.json  (앱이 '구조 가이드' 모드와 '주어·동사 찾기 퀴즈'에 쓴다)

어떻게
  spaCy(영어 의존구문 분석기, en_core_web_sm)로 문장을 분석해 단어들 사이의 관계(누가 주어인지, 어느 구가 어느 동사에
  붙는지)를 얻고, 그 관계를 학습자용 역할 이름으로 바꾼다.
  ※ 기계 분석이라 100% 정확하지 않다(대략 9할). 앱에는 "자동 분석"이라고 표시한다.
  ※ 튜터(클로드)가 직접 쓴 분석(tutor/analyses_*.json)이 있는 문장은 앱에서 그것이 우선한다.

역할 코드 (앱의 ROLE 표와 같아야 한다)
  S 주어  V 동사  O 목적어  C 보어  P 전치사구  A 부사(구)  M 수식어  R 관계절  N 명사구(동격·호격)
  Q 인용(대사)  T 전달동사(said …)  J 접속사  I 삽입·감탄  D 부사절(종속절)  G 분사구문  K 대등절
  Z 목적어절(that절 등)  E to부정사·보어절  X 기타
  안쪽 절의 성분은 "D>S"(부사절 안의 주어)처럼 '>'로 잇는다.

준비: pip install spacy  +  en_core_web_sm 모델
"""
import json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, 'data', *p)

try:
    import spacy
except ImportError:
    sys.exit("spaCy가 없습니다:  pip install spacy  그리고  en_core_web_sm 모델을 설치하세요")
nlp = spacy.load('en_core_web_sm', disable=['ner', 'lemmatizer'])

SPEECH = set('''said says say saying cried cry cries replied reply asked ask answered answer exclaimed shouted
 muttered whispered added continued called remarked murmured observed retorted sighed groaned sobbed roared yelled
 laughed gasped pleaded urged protested insisted begged inquired demanded snapped growled thundered moaned mused
 ejaculated ventured suggested drawled chuckled snarled screamed sneered faltered stammered wailed whimpered mumbled
 agreed responded interrupted returned resumed began pursued put'''.split())
VERB_GROUP = {'aux', 'auxpass', 'neg', 'prt'}
CLAUSE_ROLES = {'D', 'K', 'Z', 'E', 'R', 'G', 'Q', 'I', 'T'}


def role_of(tok, head):
    d = tok.dep_
    if d in ('nsubj', 'nsubjpass', 'csubj', 'csubjpass', 'expl'): return 'S'
    if d in ('dobj', 'obj', 'dative', 'iobj'): return 'O'
    if d in ('attr', 'acomp', 'oprd'): return 'C'
    if d in ('prep', 'agent'): return 'P'
    if d in ('advmod', 'npadvmod'): return 'A'
    if d == 'advcl':
        has_subj = any(c.dep_ in ('nsubj', 'nsubjpass') for c in tok.children)
        if tok.tag_ in ('VBG', 'VBN') and not has_subj: return 'G'
        return 'D'
    if d == 'ccomp':
        if is_quote(tok): return 'Q'
        # 머리 동사보다 앞에 오고 제 주어가 있는 ccomp 는 사실상 앞선 독립절 → 대등절로 표시
        if tok.i < head.i and any(c.dep_ in ('nsubj', 'nsubjpass', 'expl') for c in tok.children): return 'K'
        return 'Z'
    if d == 'xcomp': return 'E'
    if d == 'conj': return 'K' if tok.pos_ in ('VERB', 'AUX') else 'N'
    if d in ('cc', 'mark', 'preconj'): return 'J'
    if d == 'relcl': return 'R'
    if d in ('acl', 'amod', 'nummod', 'poss', 'det', 'compound', 'quantmod', 'predet'): return 'M'
    if d in ('appos', 'vocative', 'nmod'): return 'N'
    if d in ('intj', 'discourse'): return 'I'
    if d == 'parataxis':
        return 'T' if any(t.lower_ in SPEECH for t in tok.subtree) else 'I'
    if d in ('pobj', 'pcomp'): return 'P'
    return 'X'


def is_quote(tok):
    st = list(tok.subtree)
    return st and st[0].text in ('“', '‘', '"', "'")


def segments(head, depth=0):
    """절의 머리(동사) 기준으로 그 절을 의미 단위로 나눈다. 반환: [(시작토큰i, 끝토큰i, 역할)] (끝 포함)."""
    kids = sorted(head.children, key=lambda t: t.i)
    vg = [head] + [c for c in kids if c.dep_ in VERB_GROUP]
    vg_i = sorted(t.i for t in vg)
    segs = []
    # 동사 묶음: 연속이면 하나, 아니면 조각조각
    run = [vg_i[0]]
    for i in vg_i[1:]:
        if i == run[-1] + 1: run.append(i)
        else: segs.append((run[0], run[-1], 'V')); run = [i]
    segs.append((run[0], run[-1], 'V'))
    for c in kids:
        if c.dep_ in VERB_GROUP or c.dep_ == 'punct': continue
        st = list(c.subtree)
        lo, hi = st[0].i, st[-1].i
        r = role_of(c, head)
        # 큰 절 덩어리는 한 단계 더 쪼갠다 (안쪽 성분에 'D>S' 식으로 표시)
        if depth == 0 and r in CLAUSE_ROLES and hi - lo + 1 >= 8 and c.pos_ in ('VERB', 'AUX'):
            inner = segments(c, depth + 1)
            for a, b, rr in inner:
                segs.append((a, b, f"{r}>{rr}"))
        else:
            segs.append((lo, hi, r))
    segs.sort()
    return segs


def cover(segs, lo, hi):
    """조각들이 [lo,hi]를 빈틈·겹침 없이 덮도록 정리한다."""
    out = []
    cur = lo
    for a, b, r in segs:
        if b < cur: continue
        a = max(a, cur)
        if out and a > cur:            # 틈(문장부호 등)은 앞 조각에 붙인다
            pa, pb, pr = out[-1]; out[-1] = (pa, a - 1, pr)
        elif not out and a > cur:
            out.append((cur, a - 1, 'X'))
        out.append((a, b, r)); cur = b + 1
    if out and cur <= hi:
        pa, pb, pr = out[-1]; out[-1] = (pa, hi, pr)
    elif not out:
        out.append((lo, hi, 'X'))
    return out


def analyse_part(doc, off):
    """spaCy Doc(문장의 한 부분) → (S, V, segs(글자 위치), finite_count). off = 이 부분의 문장 내 글자 시작 위치"""
    toks = list(doc)
    if not toks: return None, None, [], 0
    all_segs = []
    S = V = None
    fin = 0
    for sent in doc.sents:                     # spaCy 가 문장을 더 쪼갤 수도 있다
        root = sent.root
        if root.pos_ not in ('VERB', 'AUX'):
            vs = [t for t in sent if t.pos_ in ('VERB', 'AUX') and t.head == root]
            if not vs:
                all_segs.append((sent.start, sent.end - 1, 'N' if root.pos_ in ('NOUN', 'PROPN', 'PRON') else 'X'))
                continue
        segs = cover(segments(root), sent.start, sent.end - 1)
        all_segs.extend(segs)
        if V is None and root.pos_ in ('VERB', 'AUX'):
            # 주절 후보: 뿌리 동사, 그리고 뿌리보다 앞에 놓인(제 주어를 가진) ccomp/parataxis 절 → 가장 앞의 것을 고른다
            cands = [root] + [c for c in root.children if c.dep_ in ('ccomp', 'parataxis') and c.i < root.i
                              and c.pos_ in ('VERB', 'AUX') and not is_quote(c)
                              and any(x.dep_ in ('nsubj', 'nsubjpass', 'expl') for x in c.children)]
            root = min(cands, key=lambda t: t.i)
            vg = [root] + [c for c in root.children if c.dep_ in VERB_GROUP]
            idx = set(t.i for t in vg)
            run = [root.i]
            while run[0] - 1 in idx: run.insert(0, run[0] - 1)
            while run[-1] + 1 in idx: run.append(run[-1] + 1)
            V = [off + toks[run[0]].idx, off + toks[run[-1]].idx + len(toks[run[-1]].text)]
            subj = [c for c in root.children if c.dep_ in ('nsubj', 'nsubjpass', 'csubj', 'expl')]
            if not subj:
                for c in root.children:
                    if c.dep_ == 'conj':
                        subj = [x for x in c.children if x.dep_ in ('nsubj', 'nsubjpass')]
                        if subj: break
            if subj:
                st = list(subj[0].subtree)
                if len(st) > 8:
                    st = [t for t in st if t.i <= subj[0].i]
                S = [off + st[0].idx, off + st[-1].idx + len(st[-1].text)]
        fin += sum(1 for t in sent if t.pos_ in ('VERB', 'AUX') and t.dep_ in ('ROOT', 'conj', 'advcl', 'ccomp', 'relcl', 'parataxis')
                   and any(c.dep_ in ('nsubj', 'nsubjpass', 'expl') for c in t.children))
    chunks = []
    for a, b, r in all_segs:
        first = next((t for t in toks[a:b + 1] if re.match(r"[A-Za-z0-9]", t.text)), None)
        if first is None: continue
        cs = off + first.idx
        if chunks and chunks[-1][0] == cs: continue
        chunks.append([cs, r])
    return S, V, chunks, fin


def split_parts(s):
    """세미콜론으로 이어진 독립절은 따로 분석한다. 반환: [(글자시작, 부분문자열)]"""
    parts, pos = [], 0
    for m in re.finditer(r';\s+', s):
        parts.append((pos, s[pos:m.start() + 1])); pos = m.end()
    parts.append((pos, s[pos:]))
    return [(o, t) for o, t in parts if t.strip()]


def main():
    book = json.load(open(D('book.json'), encoding='utf-8'))
    items = [(c['n'], pi, si, s) for c in book['chapters'] for pi, p in enumerate(c['paras']) for si, s in enumerate(p)]
    print(f"문장 {len(items):,}개 분석 시작 (spaCy en_core_web_sm)")
    t0 = time.time()
    # 세미콜론 기준으로 부분을 나눠 한꺼번에 분석
    parts = []      # (item_index, part_index, offset, text)
    for k, (n, pi, si, s) in enumerate(items):
        for j, (o, t) in enumerate(split_parts(s)):
            parts.append((k, j, o, t))
    docs = nlp.pipe([t for *_, t in parts], batch_size=256)
    per_item = {}
    for (k, j, o, t), doc in zip(parts, docs):
        per_item.setdefault(k, []).append((j, analyse_part(doc, o)))
    out = {}
    for k, (n, pi, si, s) in enumerate(items):
        res = sorted(per_item.get(k, []))
        S = V = None; chunks = []; fin = 0
        for j, (Sp, Vp, ch, f) in res:
            if j == 0: S, V = Sp, Vp
            # 두 번째 부분부터는 '세미콜론 뒤 대등절'(K)로 표시
            chunks.extend([[c, r if j == 0 else ('K>' + r if not r.startswith('K') else r)] for c, r in ch])
            fin += f
        if chunks: chunks[0][0] = 0
        a = {'s': S, 'v': V, 'c': chunks, 'f': fin} if chunks else None
        out.setdefault(str(n), {}).setdefault(str(pi), {})[str(si)] = a
    print(f"완료 {time.time() - t0:.0f}초")
    # 압축 저장: 장 → 문단 → 문장 리스트
    compact = {}
    for n, paras in out.items():
        compact[n] = []
        for pi in range(len(book['chapters'][int(n) - 1]['paras'])):
            row = []
            for si in range(len(book['chapters'][int(n) - 1]['paras'][pi])):
                a = paras.get(str(pi), {}).get(str(si))
                row.append([a['s'], a['v'], a['c'], a['f']] if a else None)
            compact[n].append(row)
    json.dump(compact, open(D('syntax.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"저장: {D('syntax.json')} ({os.path.getsize(D('syntax.json'))/1e6:.2f} MB)")
    # 표본 출력
    c1 = book['chapters'][0]
    for pi, si in [(6, 0), (6, 1), (8, 0), (11, 0)]:
        s = c1['paras'][pi][si]; a = compact['1'][pi][si]
        print('\n', s[:160])
        if a and a[0]: print('   S =', s[a[0][0]:a[0][1]], '| V =', s[a[1][0]:a[1][1]] if a[1] else None)
        if a:
            starts = [x[0] for x in a[2]] + [len(s)]
            print('   ' + ' / '.join(f"[{r}] {s[starts[k]:starts[k+1]].strip()}" for k, (st, r) in enumerate(a[2])))


if __name__ == '__main__':
    main()
