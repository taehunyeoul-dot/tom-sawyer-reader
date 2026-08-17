#!/usr/bin/env python3
"""
14단계: '정밀 확인' 입력 만들기 + 결과 합치기.

지금까지 손으로 하던 두 단계를 자동화한다.

  1) 입력 만들기   python scripts/14_build_checks.py in 13 14 15
       tutor/analyses_NN.json → tutor/checks/in_NN.json
       (튜터 분석에서 id·en·s·v·ko·chunks 만 뽑은 것)

  2) 결과 합치기   python scripts/14_build_checks.py merge
       tutor/checks/out_*.json 전부 → data/checks.json
       합치면서 아래를 검사한다. 문제가 있으면 그 항목은 버리고 경고를 낸다.
         · 문장 번호가 튜터 분석에 실제로 있는가
         · 유형 t 가 neg/who/pron/mod/time 다섯 중 하나인가
         · 묻는 말 q 와 답 a 가 비어 있지 않은가

그다음 python scripts/08_build_reader.py 로 재빌드한다.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
KEYS = ('id', 'en', 's', 'v', 'ko', 'chunks')
TYPES = {'neg', 'who', 'pron', 'mod', 'time'}


def load(path):
    return json.load(open(path, encoding='utf-8'))


def save(path, obj, compact=False):
    # data/checks.json 은 앱에 통째로 박히는 생성물이라 한 줄짜리 압축본으로,
    # tutor/checks/in_NN.json 은 사람이 들여다보므로 들여쓰기해서 쓴다.
    with open(path, 'w', encoding='utf-8') as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)


def make_inputs(nums):
    os.makedirs(D('tutor', 'checks'), exist_ok=True)
    for n in nums:
        src = D('tutor', f'analyses_{n:02d}.json')
        if not os.path.exists(src):
            print(f"{n:>2}장: 튜터 분석이 없다 — 09번·PROMPT.md 먼저"); continue
        rows = [{k: a[k] for k in KEYS} for a in load(src)]
        dst = D('tutor', 'checks', f'in_{n:02d}.json')
        save(dst, rows)
        print(f"{n:>2}장: {len(rows)}문장 → tutor/checks/in_{n:02d}.json")


def merge():
    ids = set()
    for fn in glob.glob(D('tutor', 'analyses_*.json')):
        ids |= {a['id'] for a in load(fn)}

    out, warn, n_files = {}, 0, 0
    for fn in sorted(glob.glob(D('tutor', 'checks', 'out_*.json'))):
        n_files += 1
        try:
            data = load(fn)
        except Exception as e:
            print(f"  ! {os.path.basename(fn)} JSON 오류: {e}"); warn += 1; continue
        for sid, items in data.items():
            if sid not in ids:
                print(f"  ! {sid} 튜터 분석에 없는 문장 — 건너뜀"); warn += 1; continue
            if sid in out:
                print(f"  ! {sid} 가 여러 파일에 중복 — 나중 것으로 덮어씀"); warn += 1
            keep = []
            for it in items:
                if it.get('t') not in TYPES:
                    print(f"  ! {sid} 유형 '{it.get('t')}' 이 다섯 종류가 아님 — 버림"); warn += 1; continue
                if not str(it.get('q', '')).strip() or not str(it.get('a', '')).strip():
                    print(f"  ! {sid} 묻는 말이나 답이 비어 있음 — 버림"); warn += 1; continue
                # 도움말이 없으면 빈 칸으로 채운다(앱은 어느 쪽이든 같게 동작하지만 형식을 통일)
                keep.append({'t': it['t'], 'q': it['q'], 'a': it['a'], 'tip': it.get('tip', '')})
            if keep:
                out[sid] = keep

    # 튜터 분석은 있는데 확인 항목이 없는 장을 알려 준다 (조용히 빠지는 것을 막는다)
    todo = {}
    for fn in sorted(glob.glob(D('tutor', 'analyses_*.json'))):
        for a in load(fn):
            if a['id'] not in out:
                todo.setdefault(int(a['id'].split('.')[0]), 0)
                todo[int(a['id'].split('.')[0])] += 1
    if todo:
        print("\n확인 항목이 아직 없는 문장:")
        for ch in sorted(todo):
            print(f"  {ch:>2}장 {todo[ch]}문장")

    out = {k: out[k] for k in sorted(out, key=lambda s: [int(x) for x in s.split('.')])}
    save(D('data', 'checks.json'), out, compact=True)
    n_items = sum(len(v) for v in out.values())
    chs = sorted({int(k.split('.')[0]) for k in out})
    rng = f"{chs[0]}~{chs[-1]}장" if chs else "없음"
    print(f"\n파일 {n_files}개 → data/checks.json : {len(out)}문장 · {n_items}항목 ({rng}) / 경고 {warn}건")
    if not warn:
        print("이제 python scripts/08_build_reader.py 로 재빌드하면 된다.")


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'in':
        nums = [int(x) for x in sys.argv[2:]]
        if not nums:
            nums = sorted(int(m.group(1)) for f in os.listdir(D('tutor'))
                          if (m := re.fullmatch(r'analyses_(\d+)\.json', f)))
        make_inputs(nums)
    elif mode == 'merge':
        merge()
    else:
        print(__doc__)
        sys.exit(1)
