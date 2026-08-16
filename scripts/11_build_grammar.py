#!/usr/bin/env python3
"""
11단계: 문법 해설(튜터가 쓴 것)과 본문 예문(10번이 찾은 것)을 합친다.

  · 해설(왜 필요한지·설명·공식·읽는 요령·흔한 실수)은 tutor/grammar/done_*.json 에서
  · 영어 예문은 data/grammar_hits.json (= 소설 원문에서 기계로 찾은 것)에서

검증
  · 해설이 가리키는 예문 번호(id)가 실제로 그 주제의 예문 목록에 있는지
  · 그 번호의 문장이 book.json 의 문장과 정확히 같은지
    → 튜터가 영어 문장을 지어내거나 바꿔 쓸 수 없게 막는 장치다.

결과물: data/grammar.json  (앱이 그대로 읽는 형식)
"""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)

book = json.load(open(D('data', 'book.json'), encoding='utf-8'))
hits = json.load(open(D('data', 'grammar_hits.json'), encoding='utf-8'))

# 예문 목록은 '튜터에게 실제로 건넨 배치 파일'을 기준으로 삼는다.
# (10번을 다시 돌리면 표본이 달라질 수 있으므로, 튜터가 본 것과 대조해야 맞다)
given = {}
for fn in sorted(glob.glob(D('tutor', 'grammar', 'batch_*.json'))):
    for code, v in json.load(open(fn, encoding='utf-8')).items():
        given[code] = v.get('ex', [])


def sent(sid):
    try:
        n, pi, si = map(int, sid.split('.'))
        return book['chapters'][n - 1]['paras'][pi][si]
    except Exception:
        return None


expl = {}
for fn in sorted(glob.glob(D('tutor', 'grammar', 'done_*.json'))):
    try:
        expl.update(json.load(open(fn, encoding='utf-8')))
    except Exception as e:
        print(f"  ! {os.path.basename(fn)} 읽기 실패: {e}")
print(f"해설 {len(expl)}개 / 주제 {len(hits)}개")

out, warn = [], 0
for code, h in sorted(hits.items(), key=lambda kv: kv[1].get('order', 999)):
    e = expl.get(code)
    if not e:
        print(f"  ! 해설 없음: {code} ({h['name']})"); warn += 1; continue
    by_id = {x['id']: x['en'] for x in (given.get(code) or h['ex'])}
    ex = []
    for item in e.get('ex', []):
        sid = item.get('id')
        if sid not in by_id:
            print(f"  ! {code}: 예문 목록에 없는 번호 {sid} — 건너뜀"); warn += 1; continue
        real = sent(sid)
        if real is None or real != by_id[sid]:
            print(f"  ! {code}: {sid} 문장이 원문과 다름 — 건너뜀"); warn += 1; continue
        ex.append({'id': sid, 'en': real, 'ko': item.get('ko', ''), 'note': item.get('note', '')})
    if not ex:
        print(f"  ! {code}: 쓸 수 있는 예문이 없음"); warn += 1; continue
    out.append({'code': code, 'group': h['group'], 'name': h['name'], 'count': h['count'],
                'why': e.get('why', ''), 'explain': e.get('explain', ''), 'formula': e.get('formula', ''),
                'read': e.get('read', ''), 'trap': e.get('trap', ''),
                'ex': ex, 'quiz': h.get('quiz', []), 'all': h.get('all', [])})

groups = []
for t in out:
    if t['group'] not in groups: groups.append(t['group'])
json.dump({'groups': groups, 'topics': out}, open(D('data', 'grammar.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print(f"저장: {D('data', 'grammar.json')} — 주제 {len(out)}개 / 묶음 {len(groups)}개 / 예문 {sum(len(t['ex']) for t in out)}개 / 경고 {warn}건")
