#!/usr/bin/env python3
"""
읽기 앱 자동 점검: 브라우저(Playwright)로 index.html 을 열어
자바스크립트 오류가 없는지, 주요 화면이 그려지는지 확인하고 스크린샷을 남긴다.

사용법:  python scripts/check_reader.py
필요:    playwright (이 PC에는 이미 설치돼 있음)
결과:    임시폴더에 스크린샷 + 콘솔 요약
"""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'index.html')
SHOT = lambda name: os.path.join(os.environ.get('TEMP', ROOT), f'check_reader_{name}.png')
errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={'width': 1280, 'height': 900}).new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.dismiss())
    pg.goto('file:///' + OUT.replace('\\', '/'))
    pg.wait_for_timeout(1500)
    pg.evaluate("localStorage.removeItem('ts_reader_v1')"); pg.reload(); pg.wait_for_timeout(1200)   # 깨끗한 상태로 점검
    print('장 목록:', pg.locator('#chl button').count(), '개')
    print('1장 미리보기 단어:', pg.locator('#pretb tr').count(), '행 /', pg.inner_text('#covnow'))
    pg.screenshot(path=SHOT('pre'))
    pg.click('#startRead'); pg.wait_for_timeout(700)
    print('본문 단어 span:', pg.locator('#text .tk').count(), '/ 문장:', pg.locator('#text .s').count(),
          '/ 튜터 분석 문장:', pg.locator('#text .s.hasan').count())
    print('구조 가이드 — 주어 표시:', pg.locator('#text .tk.gS').count(), '/ 동사 표시:', pg.locator('#text .tk.gV').count(),
          '/ 의미 단위 경계:', pg.locator('#text .gb').count())
    pg.evaluate("document.querySelectorAll('#text .s')[8].click()"); pg.wait_for_timeout(400)
    print('문장 패널:', pg.inner_text('#drc h3'), '/ 역할 표 줄:', pg.locator('#drc .roles-table tr').count())
    pg.screenshot(path=SHOT('read'))
    pg.click('#drawer .x')
    for t in ['srs', 'struct', 'stats', 'help']:
        pg.click(f'nav button[data-t="{t}"]'); pg.wait_for_timeout(300)
    print('문장구조 카드:', pg.locator('#sw .sc').count())
    pg.evaluate("localStorage.removeItem('ts_reader_v1')")   # 점검용 기록은 남기지 않는다
    b.close()
print('자바스크립트 오류:', errs or '없음')
