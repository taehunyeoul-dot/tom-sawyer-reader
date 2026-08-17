#!/usr/bin/env python3
"""
15단계: 뉴스 기사에도 튜터 분석 + 정밀 확인을 붙인다.

소설(09→PROMPT→14)과 같은 흐름을 기사용으로 옮긴 것이다. 다른 점은
기사가 매일 새로 들어온다는 것뿐이라, 아직 분석이 없는 기사만 골라 뽑아 준다.

  1) 작업 뽑기   python scripts/15_news_tutor.py out
       분석이 없는 기사를 골라 tutor/news/work/ 에 입력을 만든다.
       특정 기사만: python scripts/15_news_tutor.py out 3f2a1b9c

  2) 서브에이전트에게 tutor/news/TUTOR_PROMPT.md 를 읽히고 기사 하나씩 맡긴다.
       결과: tutor/news/an_<기사id>.json   (튜터 분석)
             tutor/news/ck_<기사id>.json   (정밀 확인)

  3) 합치기     python scripts/15_news_tutor.py merge
       원문 대조로 검증한 뒤 data/news_tutor.json 으로 합친다.
       그다음 python scripts/08_build_reader.py

문장 번호는 앱과 같은 규칙을 쓴다:  <기사id>|<문단>.<문장>
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
WORK = D('tutor', 'news', 'work')
TYPES = {'neg', 'who', 'pron', 'mod', 'time'}

# 기사는 짧고 완결된 글이라 **모든 문장**을 다룬다(소설처럼 어려운 것만 고르지 않는다).
# 다만 해석할 것이 없는 부속물은 뺀다 — 기자·사진 크레딧, 연락처 블록, 링크 안내 토막.
# 명령문("Grab a camera and join…")은 어엿한 문장이므로 반드시 포함할 것.
BOILER = re.compile(
    r'[\w.+-]+@[\w.-]+'                      # 이메일이 든 줄 = 연락처 블록
    r'|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b'      # 전화번호
    r'|^\s*(Story|Text|Photos?|Video|Images?|NASA photos?|Caption)\s+by\s',  # 크레딧 줄
    re.I)


def worth(s):
    """해석해 볼 값어치가 있는 문장인가."""
    if BOILER.search(s):
        return False
    if s.rstrip().endswith(':'):             # "…, visit:" 처럼 링크를 여는 토막
        return False
    return True

norm = lambda t: re.sub(r'\s+', ' ', t).strip()
loose = lambda t: re.sub(r'\s', '', t)


def load(p):
    return json.load(open(p, encoding='utf-8'))


def save(p, o, compact=False):
    with open(p, 'w', encoding='utf-8') as f:
        if compact:
            json.dump(o, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(o, f, ensure_ascii=False, indent=1)


def articles():
    return load(D('data', 'news.json'))['articles']


def picks(a):
    """이 기사에서 다룰 문장 — 부속물만 빼고 전부."""
    out = []
    for pi, para in enumerate(a['paras']):
        for si, s in enumerate(para):
            if not worth(s):
                continue
            sy = (a['syn'][pi] or [])[si] if pi < len(a['syn']) else None
            sv = ['', '']
            if sy:
                for k in (0, 1):
                    r = sy[k]
                    if isinstance(r, (list, tuple)) and len(r) == 2:
                        sv[k] = s[r[0]:r[1]]
            out.append({'id': f"{a['id']}|{pi}.{si}", 'en': s,
                        'auto_s': sv[0], 'auto_v': sv[1]})
    return out


def do_out(only):
    os.makedirs(WORK, exist_ok=True)
    todo = []
    for a in articles():
        if only and a['id'] not in only:
            continue
        done = set()
        p = D('tutor', 'news', f"an_{a['id']}.json")
        if os.path.exists(p):
            try:
                done = {x['id'] for x in load(p)}
            except Exception:
                done = set()
        need = [r for r in picks(a) if r['id'] not in done]
        if not only and not need:
            continue
        todo.append((a, done, need))
    if not todo:
        print('빠진 문장이 없다. 특정 기사를 다시 하려면 기사 id 를 인자로 줄 것.')
        return
    for a, done, need in todo:
        rows = picks(a)
        save(D(WORK, f"in_{a['id']}.json"), rows)
        if done:
            save(D(WORK, f"todo_{a['id']}.json"), need)
        with open(D(WORK, f"art_{a['id']}.txt"), 'w', encoding='utf-8') as f:
            f.write(f"{a['title']}\n{a['source']} · {a['date']}\n{a['url']}\n\n")
            for pi, para in enumerate(a['paras']):
                for si, s in enumerate(para):
                    f.write(f"[{pi}.{si}] {s}\n")
                f.write('\n')
        n = sum(len(p) for p in a['paras'])
        tail = f"이미 끝낸 {len(done)}개 + **더 할 {len(need)}개**" if done else f"{len(rows)}개 전부 새로"
        print(f"{a['id']}  {a['title'][:40]:<40} 문장 {n:>3}개 중 다룰 것 {len(rows):>3}개 — {tail}")
    print(f"\n기사 {len(todo)}건. tutor/news/TUTOR_PROMPT.md 를 읽혀 하나씩 맡길 것.")
    if any(d for _, d, _ in todo):
        print("이미 한 문장은 todo_*.json 에 빠진 것만 따로 담아 두었다. "
              "기존 an_*/ck_* 항목은 그대로 두고 빠진 것만 더할 것.")


def do_merge():
    arts = {a['id']: a for a in articles()}
    SENT = {}
    for a in arts.values():
        for pi, para in enumerate(a['paras']):
            for si, s in enumerate(para):
                SENT[f"{a['id']}|{pi}.{si}"] = s

    analyses, checks, warn = [], {}, 0

    for fn in sorted(glob.glob(D('tutor', 'news', 'an_*.json'))):
        aid = os.path.basename(fn)[3:-5]
        if aid not in arts:
            print(f"  · {aid} 기사가 이제 없다 — 건너뜀 (오래돼 정리된 기사)"); continue
        try:
            arr = load(fn)
        except Exception as e:
            print(f"  ! {os.path.basename(fn)} JSON 오류: {e}"); warn += 1; continue
        for a in arr:
            i = a.get('id')
            orig = SENT.get(i)
            if orig is None:
                print(f"  ! {i} 기사에 없는 문장 — 버림"); warn += 1; continue
            if loose(a.get('en', '')) != loose(orig):
                print(f"  ! {i} 원문 불일치 — 원문으로 교체"); warn += 1
            a['en'] = orig
            joined = ' '.join(c.get('en', '') for c in a.get('chunks', []))
            if loose(joined) != loose(orig):
                print(f"  ! {i} 의미 단위가 원문과 다름"); warn += 1
            for k in ('s', 'v'):
                if a.get(k) and a[k] not in orig:
                    print(f"  ! {i} {k}='{a[k]}' 가 문장에 없음 → 비움"); warn += 1; a[k] = ''
            if not a.get('ko', '').strip() or not a.get('why', '').strip():
                print(f"  ! {i} 번역이나 설명이 비어 있음"); warn += 1
            a.setdefault('st', [])
            analyses.append(a)

    ids = {a['id'] for a in analyses}
    for fn in sorted(glob.glob(D('tutor', 'news', 'ck_*.json'))):
        aid = os.path.basename(fn)[3:-5]
        if aid not in arts:
            continue
        try:
            data = load(fn)
        except Exception as e:
            print(f"  ! {os.path.basename(fn)} JSON 오류: {e}"); warn += 1; continue
        for sid, items in data.items():
            if sid not in ids:
                print(f"  ! {sid} 튜터 분석이 없는 문장 — 건너뜀"); warn += 1; continue
            keep = []
            for it in items:
                if it.get('t') not in TYPES:
                    print(f"  ! {sid} 유형 '{it.get('t')}' 이 다섯 종류가 아님 — 버림"); warn += 1; continue
                if not str(it.get('q', '')).strip() or not str(it.get('a', '')).strip():
                    print(f"  ! {sid} 묻는 말이나 답이 비어 있음 — 버림"); warn += 1; continue
                # <b>로 감싼 영어가 원문에 실제로 있는지
                for frag in re.findall(r'<b>(.*?)</b>', it['q'], re.S):
                    f2 = norm(re.sub(r'<[^>]+>', '', frag))
                    if not re.search(r'[A-Za-z]{2}', f2):
                        continue
                    src = norm(SENT[sid])
                    parts = [norm(x) for x in re.split(r'\.\.\.|…', f2) if norm(x)]
                    if parts and all(p in src for p in parts):
                        continue
                    print(f"  ! {sid} 인용 '{f2[:40]}' 가 원문에 없음"); warn += 1
                keep.append({'t': it['t'], 'q': it['q'], 'a': it['a'], 'tip': it.get('tip', '')})
            if keep:
                checks[sid] = keep

    order = {a['id']: k for k, a in enumerate(analyses)}
    analyses.sort(key=lambda a: (a['id'].split('|')[0],
                                 [int(x) for x in a['id'].split('|')[1].split('.')]))
    checks = {k: checks[k] for k in sorted(checks, key=lambda s: (
        s.split('|')[0], [int(x) for x in s.split('|')[1].split('.')]))}

    save(D('data', 'news_tutor.json'), {'analyses': analyses, 'checks': checks}, compact=True)
    n_items = sum(len(v) for v in checks.values())
    n_arts = len({a['id'].split('|')[0] for a in analyses})
    print(f"\ndata/news_tutor.json : 기사 {n_arts}건 · 분석 {len(analyses)}문장 · "
          f"정밀 확인 {len(checks)}문장 {n_items}항목 / 경고 {warn}건")

    missing = [a['id'] for a in articles() if a['id'] not in {x['id'].split('|')[0] for x in analyses}]
    if missing:
        print(f"아직 분석이 없는 기사 {len(missing)}건: {', '.join(missing)}")
        print("  → python scripts/15_news_tutor.py out  으로 작업을 뽑을 것")
    if not warn:
        print("이제 python scripts/08_build_reader.py 로 재빌드하면 된다.")


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'out':
        do_out(set(sys.argv[2:]))
    elif mode == 'merge':
        do_merge()
    else:
        print(__doc__); sys.exit(1)
