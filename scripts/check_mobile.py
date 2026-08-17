#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
휴대폰 폭(390px)에서 화면이 옆으로 삐져나가지 않는지 모든 탭을 훑어 확인한다.

`check_reader.py` 는 PC 폭(1280px)만 보므로 이 문제를 잡지 못한다.
**reader_template.html 의 레이아웃을 건드렸으면 08번 재빌드 뒤 이 검사를 돌릴 것.**

    python scripts/08_build_reader.py
    python scripts/check_mobile.py

무엇을 잡나: 어떤 요소가 390px 밖으로 나가면 브라우저가 뷰포트를 넓혀 버려
화면 전체가 축소된다(글씨가 작아진다). 실제로 두 번 겪었다.
  1. 절대 위치 역할 이름표가 오른쪽으로 삐져나감
  2. display:grid 자식이 min-width:auto 라 칸이 내용 최소 폭 아래로 안 줄어듦
"""
import os, sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit('playwright 가 없습니다:  pip install playwright && playwright install chromium')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + os.path.join(ROOT, 'index.html').replace('\\', '/')
W = 390

# 스스로 넘치는 가장 안쪽 요소만 (부모까지 같이 넘치면 부모가 원인)
OVER_JS = """() => {
  const W = %d, out = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.right <= W + 1 || r.width === 0) continue;
    if ([...el.children].some(k => k.getBoundingClientRect().right > W + 1)) continue;
    out.push(el.tagName + '.' + (el.className || '(무)') + ' → ' + Math.round(r.right) + 'px');
  }
  return [...new Set(out)].slice(0, 6);
}""" % W

bad, errs = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={'width': W, 'height': 844},
                       device_scale_factor=3, is_mobile=True).new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1500)

    def measure(label):
        sw = pg.evaluate('document.documentElement.scrollWidth')
        ok = sw <= W
        if not ok:
            bad.append(label)
        print(f'  {label:<20} {sw}px  [{"OK" if ok else "삐져나감"}]')
        if not ok:
            for o in pg.evaluate(OVER_JS):
                print(f'      {o}')

    def go(sel, label, wait=1000):
        try:
            pg.click(sel, timeout=4000); pg.wait_for_timeout(wait); measure(label)
        except Exception:
            print(f'  {label:<20} (버튼 없음 — 건너뜀)')

    measure('읽기 전')
    go('button[data-p="read"]', '읽기 · 소설책')
    go('button[data-m="struct"]', '읽기 · 구조분석')
    go('button[data-p="post"]', '읽은 후')
    go('button[data-t="read"]', '읽기 탭 복귀', 800)
    go('button[data-s="news"]', '뉴스 목록', 1500)
    for t, label in (('srs', '단어'), ('struct', '문법'), ('stats', '기록'), ('help', '사용법')):
        go(f'button[data-t="{t}"]', label)

    print('\n자바스크립트 오류:', errs if errs else '없음')
    b.close()

print(f'\n뷰포트 {W}px 유지: ' + ('통과' if not bad else f'실패 — {", ".join(bad)}'))
sys.exit(1 if bad else 0)
