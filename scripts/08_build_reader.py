#!/usr/bin/env python3
"""
8단계: 읽기 앱(웹페이지 한 파일, index.html)을 조립한다.

넣는 데이터
  data/book.json         본문 (07번)
  data/vocab.json        어휘 8,989개 (04번)
  data/reader_data.json  장별 주석 (07번)
  data/syntax.json       모든 문장의 자동 구문 분석 (06번)
  data/structures.json   문장구조 18유형 해설
  tutor/analyses_*.json  튜터가 쓴 어려운 문장 분석 (장별 파일, 없어도 됨)
  tutor/guide_*.json     튜터가 쓴 장 가이드·확인 질문 (장별 파일, 없어도 됨)

검증
  · 분석 문장(en)이 book.json 의 해당 위치 문장과 같은지
  · 의미 단위(chunks)를 이어 붙이면 원문과 같은지 — 띄어쓰기만 다르면 자동으로 고친다
  · 주어(s)·동사(v)가 문장 안에 실제로 있는지
  틀린 항목은 경고만 내고 그대로 넣는다(앱에서는 텍스트로만 쓰이므로 깨지지 않는다).

결과물: index.html (저장소 루트 — GitHub Pages 가 바로 서비스한다)
"""
import json, os, glob, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

book = json.load(open(D('data', 'book.json'), encoding='utf-8'))
vocab = json.load(open(D('data', 'vocab.json'), encoding='utf-8'))
rd = json.load(open(D('data', 'reader_data.json'), encoding='utf-8'))
syntax = json.load(open(D('data', 'syntax.json'), encoding='utf-8'))
grammar = json.load(open(D('data', 'grammar.json'), encoding='utf-8')) if os.path.exists(D('data', 'grammar.json')) else {'groups': [], 'topics': []}
news = json.load(open(D('data', 'news.json'), encoding='utf-8')) if os.path.exists(D('data', 'news.json')) else {'articles': [], 'vocab': []}
checks = json.load(open(D('data', 'checks.json'), encoding='utf-8')) if os.path.exists(D('data', 'checks.json')) else {}
# 뉴스 어휘를 어휘 목록 뒤에 붙인다. 13번이 '소설 어휘 개수 + k' 로 번호를 매겼으므로 순서가 중요하다.
for k, r in enumerate(news.get('vocab', [])):
    idx = len(vocab)
    vocab.append(r)
    rd['forms'][r['w']] = idx
    for f in r.get('f', []): rd['forms'].setdefault(f, idx)
if news.get('vocab'): print(f"뉴스 어휘 {len(news['vocab'])}개를 사전에 추가")
structs = json.load(open(D('data', 'structures.json'), encoding='utf-8'))


def sent(id_):
    n, pi, si = map(int, id_.split('.'))
    return book['chapters'][n - 1]['paras'][pi][si]


# --- 튜터 분석 모으기 + 검증 -------------------------------------------------
analyses, guides = [], []
warn = 0
for fn in sorted(glob.glob(D('tutor', 'analyses_*.json'))):
    try:
        arr = json.load(open(fn, encoding='utf-8'))
    except Exception as e:
        print(f"  ! {os.path.basename(fn)} JSON 오류: {e}"); continue
    for a in arr:
        try:
            orig = sent(a['id'])
        except Exception:
            print(f"  ! {a.get('id')} 위치 없음 — 건너뜀"); warn += 1; continue
        if a['en'] != orig:
            # 따옴표 종류·공백 차이만이면 원문으로 교체
            if re.sub(r"[\s’‘'\"“”]", '', a['en']) == re.sub(r"[\s’‘'\"“”]", '', orig):
                a['en'] = orig
            else:
                print(f"  ! {a['id']} 문장 불일치 — 원문으로 교체"); warn += 1; a['en'] = orig
        # 의미 단위 검증/보정
        joined = ' '.join(c['en'] for c in a['chunks'])
        if joined != a['en']:
            if joined.replace(' ', '') == a['en'].replace(' ', ''):
                # 띄어쓰기만 다름 → 원문을 chunk 글자 수대로 다시 자른다
                pos, fixed = 0, []
                text = a['en']
                for c in a['chunks']:
                    target = c['en'].replace(' ', '')
                    k, buf = 0, ''
                    while pos < len(text) and k < len(target):
                        ch = text[pos]; buf += ch; pos += 1
                        if ch != ' ': k += 1
                    while pos < len(text) and text[pos] == ' ': pos += 1
                    c['en'] = buf.strip()
            else:
                print(f"  ! {a['id']} 의미 단위가 원문과 다름 (그대로 둠)"); warn += 1
        for key in ('s', 'v'):
            if a.get(key) and a[key] not in a['en']:
                print(f"  ! {a['id']} {key}='{a[key]}' 가 문장에 없음 → 비움"); warn += 1; a[key] = ''
        analyses.append(a)
for fn in sorted(glob.glob(D('tutor', 'guide_*.json'))):
    try:
        guides.append(json.load(open(fn, encoding='utf-8')))
    except Exception as e:
        print(f"  ! {os.path.basename(fn)} JSON 오류: {e}")

n_topics = len(grammar.get('topics', []))
n_news = len(news.get('articles', []))
n_checks = len(checks)
print(f"튜터 분석 {len(analyses)}문장 / 장 가이드 {len(guides)}개 / 문법 주제 {n_topics}개 / 뉴스 {n_news}건 / 정밀 확인 {n_checks}문장 / 경고 {warn}건")

# --- 아포스트로피 축약형(’bout, ’em …)을 어휘 목록 뒤에 덧붙인다 -----------
#     본문에서 이런 형태를 누르면 앞의 아포스트로피가 잘려 엉뚱한 단어로 연결되던 것을 막는다.
import collections as _c
cpath = D('data', 'contractions.json')
n_contr = 0
if os.path.exists(cpath):
    text_all = ' '.join(s for c in book['chapters'] for pa in c['paras'] for s in pa)
    norm_all = text_all.replace('’', "'")
    sent_at = {}
    for c in book['chapters']:
        for pi, pa in enumerate(c['paras']):
            for si, sn in enumerate(pa):
                sent_at.setdefault(sn.replace('’', "'").lower(), f"{c['n']}.{pi}.{si}")
    for w, gl in json.load(open(cpath, encoding='utf-8'))['words'].items():
        n = len(re.findall(re.escape(w) + r"[A-Za-z]*", norm_all, re.I))
        if not n: continue
        ex, cid = '', ''
        for sn_l, sid in sent_at.items():
            if re.search(re.escape(w) + r"[A-Za-z]*", sn_l, re.I) and 40 < len(sn_l) < 220:
                # 원문 그대로를 찾아 넣는다
                nn, pi, si = sid.split('.')
                ex = book['chapters'][int(nn) - 1]['paras'][int(pi)][int(si)][:220]; cid = sid; break
        idx = len(vocab)
        vocab.append({'w': w, 'p': gl['p'], 'm': gl['m'], 'l': gl['l'], 'n': n, 'f': [], 'e': ex, 'c': cid})
        rd['forms'][w] = idx
        rd['first'][str(idx)] = int(cid.split('.')[0]) if cid else 1
        n_contr += 1
print(f"축약형 {n_contr}개를 어휘에 추가")

# --- HTML 조립 ---------------------------------------------------------------
tpl = open(D('reader_template.html'), encoding='utf-8').read()
J = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
html = (tpl.replace('/*__BOOK__*/', J(book))
           .replace('/*__VOCAB__*/', J(vocab))
           .replace('/*__RD__*/', J(rd))
           .replace('/*__STRUCT__*/', J(structs))
           .replace('/*__ANALYSES__*/', J(analyses))
           .replace('/*__GUIDES__*/', J(guides))
           .replace('/*__SYNTAX__*/', J(syntax))
           .replace('/*__GRAMMAR__*/', J(grammar))
           .replace('/*__NEWS__*/', J(news))
           .replace('/*__CHECKS__*/', J(checks)))
out = D('index.html')
# 서비스 워커의 캐시 버전을 빌드 시각으로 바꿔 옛 캐시가 남지 않게 한다
import time as _t
_sw = D('sw.js')
if os.path.exists(_sw):
    _src = open(_sw, encoding='utf-8').read()
    _src = re.sub(r"const VERSION = 'ts-reader-[^']*';", f"const VERSION = 'ts-reader-{_t.strftime('%Y%m%d%H%M%S')}';", _src)
    open(_sw, 'w', encoding='utf-8').write(_src)
open(out, 'w', encoding='utf-8').write(html)
print(f"저장: {out}  ({os.path.getsize(out)/1e6:.1f} MB)")
