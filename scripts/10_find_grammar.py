#!/usr/bin/env python3
"""
10단계: 문법 주제마다 톰 소여 본문에서 '진짜 예문'을 찾는다.

왜 이렇게 하나
  시중 문법책의 설명·예문은 저작권이 있어 그대로 쓸 수 없다. 그래서
  '무엇을 배울지'(주제 이름과 순서 — 일반적인 문법 교육 과정)만 참고하고,
  예문은 저작권이 만료된 이 소설 본문에서 기계적으로 뽑는다.
  지어낸 문장이 아니라 지금 읽고 있는 소설의 문장이라 맥락이 살아 있다.

하는 일
  1) 문법 주제(TOPICS)마다 판별기를 돌려 해당하는 문장을 모은다
     - 간단한 것은 정규식, 구조를 봐야 하는 것은 spaCy 의존구문으로 판별
  2) 주제별로 '길이가 적당하고(8~26단어) 대표성 있는' 예문을 골라 저장
  3) 예문이 너무 적은 주제(기본 5개 미만)는 경고를 띄운다
     — 이 소설에 거의 없는 문법이라 굳이 다루지 않는 편이 낫다

결과물: data/grammar_hits.json
  {주제코드: {"name","group","count","ex":[{"id","en"}...]}}
  id 는 "장.문단.문장" 이라 앱이 눌렀을 때 본문 그 자리로 이동할 수 있다.
"""
import json, os, re, sys, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, 'data', *p)
MIN_EX = 5          # 이보다 예문이 적은 주제는 다루지 않는다
N_EX = 8            # 주제당 저장할 예문 수

try:
    import spacy
    nlp = spacy.load('en_core_web_sm', disable=['ner', 'lemmatizer'])
except Exception:
    sys.exit("spaCy 가 필요합니다:  pip install spacy  +  en_core_web_sm")

# ── 판별기 도우미 ─────────────────────────────────────────────────────
def rx(pattern, flags=0):
    """정규식 판별기"""
    c = re.compile(pattern, flags)
    return lambda s, d: bool(c.search(s))

def dep(fn):
    """spaCy 의존구문 판별기 (문장 분석 결과 d 를 받는다)"""
    return lambda s, d: bool(d) and fn(d)

def has(d, test):
    return any(test(t) for t in d)

PP = ('VBN',)          # 과거분사
ING = ('VBG',)         # -ing

# ── 문법 주제 ─────────────────────────────────────────────────────────
#    코드, 묶음, 이름, 판별기
TOPICS = [
 # 시제
 ('past_prog', '시제', '과거진행 — was/were + ~ing', rx(r"\b(?:was|were)\s+(?:not\s+|n't\s+)?[a-z]+ing\b")),
 ('pres_perf', '시제', '현재완료 — have/has + 과거분사',
  dep(lambda d: has(d, lambda t: t.lower_ in ('have','has') and t.dep_=='aux' and t.head.tag_ in PP and t.head.tag_!='VBD'))),
 ('past_perf', '시제', '과거완료 — had + 과거분사 (그보다 더 이전)',
  dep(lambda d: has(d, lambda t: t.lower_=='had' and t.dep_=='aux' and t.head.tag_ in PP))),
 ('past_perf_prog', '시제', '과거완료진행 — had been + ~ing', rx(r"\bhad\s+been\s+[a-z]+ing\b")),
 ('used_to', '시제', 'used to / would — 예전에 늘 하던 일', rx(r"\bused\s+to\s+[a-z]+\b|\bwould\s+(?:often|always|sometimes)\s+[a-z]+\b")),
 ('future', '시제', 'will / be going to — 앞으로 할 일', rx(r"\b(?:will|'ll)\s+(?:not\s+)?[a-z]+\b|\b(?:is|are|was|were)\s+going\s+to\s+[a-z]+\b")),
 # 동사 뒤에 오는 것
 ('to_purpose', '동사 뒤', 'to부정사 — ~하기 위해(목적)',
  dep(lambda d: has(d, lambda t: t.dep_=='advcl' and t.tag_=='VB' and any(c.lower_=='to' and c.dep_=='aux' for c in t.children)))),
 ('to_obj', '동사 뒤', 'to부정사 — ~하는 것을(목적어·보어)',
  dep(lambda d: has(d, lambda t: t.dep_ in ('xcomp','ccomp') and t.tag_=='VB' and any(c.lower_=='to' for c in t.children)))),
 ('gerund', '동사 뒤', '동명사 ~ing — ~하는 것(주어·목적어)',
  dep(lambda d: has(d, lambda t: t.tag_ in ING and t.dep_ in ('nsubj','dobj','pobj','csubj')))),
 ('v_o_to', '동사 뒤', '동사 + 목적어 + to부정사 (want him to go)',
  dep(lambda d: has(d, lambda t: t.dep_=='xcomp' and t.tag_=='VB'
        and any(c.lower_=='to' for c in t.children) and any(c.dep_ in ('dobj','nsubj') for c in t.head.children)))),
 ('causative', '동사 뒤', '사역동사 make/let/have + 목적어 + 동사원형',
  rx(r"\b(?:make|makes|made|let|lets|have|has|had)\s+(?:him|her|them|me|us|it|the\s+[a-z]+|[A-Z][a-z]+)\s+[a-z]+\b")),
 ('perception', '동사 뒤', '지각동사 see/hear/feel + 목적어 + 동사/~ing',
  rx(r"\b(?:see|saw|seen|hear|heard|feel|felt|watch|watched|notice|noticed)\s+(?:him|her|them|me|us|it|the\s+[a-z]+|[A-Z][a-z]+)\s+[a-z]+(?:ing)?\b")),
 # 태·조동사
 ('passive', '태·조동사', '수동태 — be + 과거분사 (~해지다·~당하다)',
  dep(lambda d: has(d, lambda t: t.dep_=='auxpass') )),
 ('modal_can', '태·조동사', 'can / could — 할 수 있다', rx(r"\b(?:can|could|ca)\s*(?:not|n't)?\s+[a-z]+\b")),
 ('modal_must', '태·조동사', 'must / have to — 해야 한다', rx(r"\bmust\s+(?:not\s+)?[a-z]+\b|\b(?:have|has|had)\s+to\s+[a-z]+\b")),
 ('modal_may', '태·조동사', 'may / might — 아마 ~일 것이다', rx(r"\b(?:may|might)\s+(?:not\s+)?[a-z]+\b")),
 ('modal_should', '태·조동사', 'should / ought to — ~하는 게 좋다', rx(r"\bshould\s+(?:not\s+)?[a-z]+\b|\bought\s+to\s+[a-z]+\b")),
 ('modal_perf', '태·조동사', 'would/could/must have + 과거분사 — ~했을 것이다',
  rx(r"\b(?:would|could|might|must|should)\s+(?:not\s+)?have\s+[a-z]+(?:ed|en)\b|\b(?:would|could|might|must)\s+have\s+been\b")),
 # 절 잇기
 ('rel_that', '절 잇기', '관계대명사 who/which/that — 앞 명사를 설명',
  dep(lambda d: has(d, lambda t: t.dep_=='relcl'))),
 ('rel_comma', '절 잇기', '쉼표 + who/which — 덧붙여 설명하기', rx(r",\s*(?:who|which)\b")),
 ('rel_whose', '절 잇기', 'whose — 누구의 ○○', rx(r"\bwhose\b")),
 ('rel_where', '절 잇기', '관계부사 where/when — 장소·때를 설명', rx(r"\b(?:place|house|room|spot|town|village|day|time|night|moment|hour)\s+(?:where|when)\b")),
 ('that_clause', '절 잇기', 'that절 — ~라는 것을 (생각·말의 내용)',
  dep(lambda d: has(d, lambda t: t.dep_=='ccomp' and t.pos_ in ('VERB','AUX')))),
 ('indirect_q', '절 잇기', '간접의문문 — 의문사 + 주어 + 동사',
  rx(r"\b(?:know|knew|wonder|wondered|ask|asked|see|saw|tell|told|understand|remember)\b[^.;?]{0,20}\b(?:what|where|when|why|how|who|whether|if)\s+(?:he|she|they|it|I|we|you|the|[A-Z][a-z]+)\b")),
 ('adv_time', '절 잇기', '시간 부사절 — when/while/as/before/after/until',
  rx(r"\b(?:when|while|as soon as|before|after|until|till)\s+(?:he|she|they|it|I|we|you|the|a|[A-Z][a-z]+)\b")),
 ('adv_reason', '절 잇기', '이유 부사절 — because/since/for (~때문에)',
  rx(r"\bbecause\b|\bsince\s+(?:he|she|they|it|I|we|the)\b|,\s*for\s+(?:he|she|they|it|there|the|his|her|I|we)\b")),
 ('adv_cond', '절 잇기', '조건 부사절 — if / unless (~라면)', rx(r"\bif\b|\bunless\b")),
 ('adv_concess', '절 잇기', '양보 절 — though/although/even if (~이지만)', rx(r"\b(?:though|although|even though|even if)\b")),
 ('so_that', '절 잇기', 'so ~ that / such ~ that — 너무 …해서 ~하다',
  rx(r"\bso\s+[a-z]+\s+that\b|\bsuch\s+(?:a\s+)?[a-z]+\s+[a-z]*\s*that\b|\bso\s+that\b")),
 # 가정법
 ('cond_2', '가정법', 'if + 과거 → would — 지금 사실과 반대',
  rx(r"\bif\b[^,.;]{2,45},?\s*[^.;]{0,25}\b(?:would|could|might)\s+[a-z]+\b")),
 ('cond_3', '가정법', 'if + had p.p. → would have p.p. — 과거 사실과 반대',
  rx(r"\bif\b[^,.;]{0,40}\bhad\s+[a-z]+(?:ed|en)\b|\bwould\s+have\s+[a-z]+(?:ed|en)\b")),
 ('wish', '가정법', 'wish — ~라면 좋을 텐데', rx(r"\bwish(?:ed|es)?\b")),
 ('as_if', '가정법', 'as if / as though — 마치 ~인 것처럼', rx(r"\bas\s+(?:if|though)\b")),
 # 분사
 ('part_lead', '분사', '분사구문 — ~ing 로 시작하는 문장 (~하면서)',
  rx(r"^(?!The |A |An |He |She |It |They |Nothing |Something |Everything |Morning |Evening )[A-Z][a-z]+ing\b[^.]{4,70},")),
 ('part_pp_lead', '분사', '과거분사로 시작하는 문장 (~된 채로)',
  rx(r"^[A-Z][a-z]+(?:ed|en)\b[^.]{0,60}?,\s*(?:he|she|they|it|Tom|Huck|the|his|her)\b")),
 ('part_post', '분사', '명사 뒤에서 꾸미는 ~ing / 과거분사',
  dep(lambda d: has(d, lambda t: t.dep_=='acl' and t.tag_ in (ING+PP)))),
 ('part_abs', '분사', '독립분사구문 — , his hands trembling', rx(r",\s*(?:his|her|its|their)\s+[a-z]+(?:\s+[a-z]+)?\s+[a-z]+ing\b")),
 # 비교
 ('comp', '비교', '비교급 — -er than / more ~ than', rx(r"\b[a-z]{3,}er\s+than\b|\bmore\s+[a-z]+\s+than\b")),
 ('sup', '비교', '최상급 — the -est / the most ~', rx(r"\bthe\s+[a-z]{3,}est\b|\bthe\s+most\s+[a-z]+\b")),
 ('as_as', '비교', 'as ~ as — 만큼 ~한', rx(r"\bas\s+[a-z]+\s+as\b")),
 # 명사·대명사
 ('reflexive', '명사·대명사', '재귀대명사 — himself / herself (자기 자신)', rx(r"\b(?:himself|herself|itself|themselves|myself|yourself|ourselves)\b")),
 ('it_dummy', '명사·대명사', '가주어·가목적어 it — It is ~ to …',
  rx(r"\bit\s+(?:is|was|'s)\s+(?:no\s+|not\s+)?[a-z]+\s+to\s+[a-z]+\b", re.I)),
 ('there_be', '명사·대명사', 'there is / there was — ~이 있다', rx(r"\b[Tt]here\s+(?:is|was|were|are|had\s+been|would\s+be)\b")),
 ('quantifier', '명사·대명사', 'some / any / much / many / a few — 수량 표현',
  rx(r"\b(?:some|any|much|many|a\s+few|a\s+little|several|plenty\s+of|a\s+great\s+deal\s+of)\b")),
 # 부사·전치사
 ('freq_adv', '부사·전치사', '빈도부사 — always/never/often 의 자리',
  rx(r"\b(?:always|never|often|sometimes|usually|seldom|rarely|generally)\b")),
 ('prep_ing', '부사·전치사', '전치사 + ~ing (without saying, after eating)',
  rx(r"\b(?:of|in|on|at|for|after|before|without|by|about|from|with)\s+[a-z]+ing\b")),
 ('phrasal', '부사·전치사', '구동사 — 동사 + 부사 (put out, give up)',
  dep(lambda d: has(d, lambda t: t.dep_=='prt'))),
 # 특수 구문
 ('inversion', '특수 구문', '도치 — 부정어·부사가 앞에 오고 동사가 먼저',
  rx(r"^(?:Never|Not once|Not until|Nor|Neither|Seldom|Rarely|Hardly|Scarcely|Little|Only)\b[^.]{0,40}\b(?:had|did|was|were|could|would|has|have|is|are)\s+(?:he|she|it|they|I|we|you|the|a|[A-Z][a-z]+)\b")),
 ('cleft', '특수 구문', '강조 구문 — It was ~ that …', rx(r"\b[Ii]t\s+(?:was|is)\s+[^,.]{2,40}?\s+that\b")),
 ('tag_q', '특수 구문', '부가의문문 — ~죠? (…, isn\'t it?)',
  rx(r",\s*(?:isn't|ain't|aren't|wasn't|weren't|don't|doesn't|didn't|won't|can't|couldn't|wouldn't|hasn't|haven't|hadn't|shan't|is|was|do|did|can|will|would|have|has)\s+(?:it|he|she|they|you|I|we|there)\s*\?")),
 ('imperative', '특수 구문', '명령문 — 동사로 시작하는 문장',
  dep(lambda d: len(d) > 2 and d[0].tag_=='VB' and d[0].dep_=='ROOT' and not any(c.dep_=='nsubj' for c in d[0].children))),
 ('exclam', '특수 구문', '감탄문 — How ~! / What a ~!', rx(r"^(?:How|What)\b[^.?]{2,50}!")),
]


def main():
    book = json.load(open(D('book.json'), encoding='utf-8'))
    items = []
    for c in book['chapters']:
        for pi, para in enumerate(c['paras']):
            for si, s in enumerate(para):
                items.append((f"{c['n']}.{pi}.{si}", s))
    print(f"문장 {len(items):,}개에서 문법 주제 {len(TOPICS)}개를 찾습니다…")

    # spaCy 판별기가 필요한 문장만 분석 (전체 한 번)
    docs = list(nlp.pipe([s for _, s in items], batch_size=256))

    rnd_ex, rnd_qz = random.Random(11), random.Random(29)   # 표본끼리 난수 상태가 섞이지 않게 분리
    out, thin = {}, []
    for code, group, name, test in TOPICS:
        hits = []
        for (sid, s), d in zip(items, docs):
            try:
                if test(s, d): hits.append((sid, s))
            except Exception:
                pass
        good = [(i, s) for i, s in hits if 8 <= len(s.split()) <= 26]
        pool = good or hits
        ex = rnd_ex.sample(pool, min(N_EX, len(pool)))
        ex.sort(key=lambda x: [int(v) for v in x[0].split('.')])
        # 퀴즈용: 정답으로 쓸 문장(길이가 적당한 것)과, 오답을 고를 때 걸러낼 '해당 문장 전체 목록'
        #   전체 목록이 있어야 '이 문법이 안 쓰인 문장'을 확실하게 뽑을 수 있다.
        quiz = [i for i, _ in rnd_qz.sample(pool, min(40, len(pool)))]
        out[code] = {'name': name, 'group': group, 'count': len(hits),
                     'ex': [{'id': i, 'en': s} for i, s in ex], 'quiz': quiz,
                     'all': [i for i, _ in hits]}
        mark = '' if len(pool) >= MIN_EX else '   ← 예문 부족'
        print(f"  {group:<8}{name[:36]:<38}{len(hits):>5,}회 (쓸 만한 것 {len(good):>4}){mark}")
        if len(pool) < MIN_EX: thin.append(code)

    if thin:
        print(f"\n예문이 {MIN_EX}개 미만인 주제 {len(thin)}개: {thin}")
        print("  → 이 소설에 거의 없는 문법입니다. data/grammar.json 에서 빼는 것을 권합니다.")
    json.dump(out, open(D('grammar_hits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n저장: {D('grammar_hits.json')} — 주제 {len(out)}개")


if __name__ == '__main__':
    main()
