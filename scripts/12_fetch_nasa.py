#!/usr/bin/env python3
"""
12단계: NASA 기사를 받아 온다. (매일 자동으로 도는 부분)

왜 NASA 인가
  · 미국 정부가 만든 자료라 저작권이 없다(퍼블릭 도메인). 앱에 넣어 공개해도 된다.
  · RSS 피드 안에 본문이 통째로 들어 있어 기사 페이지를 따로 긁을 필요가 없다.
    (VOA·RFA 는 본문을 받을 수 없어 쓰지 못했다.)
  · 매일 여러 건이 올라오고 길이가 다양해 난이도를 고를 수 있다.

하는 일
  1) NASA RSS 피드에서 기사 목록과 본문을 받는다
  2) HTML 을 걷어내고 문단만 남긴다 (사진·설명글·캡션은 버린다 — 사진은 저작권이 따로 있을 수 있다)
  3) 이미 받아 둔 기사는 건너뛴다 (guid 기준)
  4) data/news_src/<날짜>_<번호>.json 으로 저장하고, 오래된 것은 정리한다

결과물: data/news_src/*.json  {id,title,url,date,source,paras:[문단…]}
사용법: python scripts/12_fetch_nasa.py [받을최대건수]
"""
import json, os, re, sys, html, gzip, urllib.request, datetime, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'news_src')
FEEDS = [
    ('NASA', 'https://www.nasa.gov/feed/'),
]
KEEP = 60          # 보관할 최대 기사 수 (오래된 것부터 지운다)
MIN_WORDS = 120    # 이보다 짧은 글은 공부거리가 못 되니 건너뛴다
MAX_WORDS = 1600

UA = {'User-Agent': 'Mozilla/5.0 (compatible; TomSawyerReader/1.0; personal study tool)',
      'Accept-Encoding': 'gzip'}


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as f:
        raw = f.read()
        if f.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
        return raw.decode('utf-8', 'ignore')


def tag(item, name):
    m = re.search(rf'<{name}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>', item, re.S)
    return m.group(1).strip() if m else ''


def to_paras(body_html):
    """기사 HTML → 문단 목록. 사진·캡션·자막·링크 목록은 버린다."""
    h = body_html
    h = re.sub(r'<(figure|figcaption|table|script|style|iframe|aside)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
    h = re.sub(r'<(ul|ol)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)   # 목록은 문장이 아니라 제외
    paras = re.findall(r'<p[^>]*>(.*?)</p>', h, re.S | re.I) or h.split('\n')
    out = []
    for p in paras:
        t = html.unescape(re.sub(r'<[^>]+>', ' ', p))
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t.split()) < 8:                       # 너무 짧은 줄(캡션·크레딧)은 버린다
            continue
        if re.match(r'^(image credit|credit|photo|caption|download|read more|explanation)\b', t, re.I):
            continue
        # Earth Observatory 처럼 <p> 없는 페이지는 줄로 자르는데, 그때 페이지 머리의 메뉴 글자
        # ("About Search", "Skip to content" …)가 첫 문장 앞에 딸려 붙는다. 대문자로 시작하는
        # 짧은 메뉴 단어가 앞에 연달아 있으면 떼어 낸다.
        t = re.sub(r'^(?:(?:About|Search|Menu|Home|Skip to (?:main )?content|Share|Explore|Topics)\s+){1,4}'
                   r'(?=[A-Z])', '', t)
        out.append(t)
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(SRC, exist_ok=True)
    seen = set()
    for fn in os.listdir(SRC):
        if fn.endswith('.json'):
            try: seen.add(json.load(open(os.path.join(SRC, fn), encoding='utf-8')).get('guid', ''))
            except Exception: pass

    added, skipped = 0, 0
    for source, url in FEEDS:
        try:
            feed = fetch(url)
        except Exception as e:
            print(f"  ! {source} 피드를 받지 못했습니다: {e}"); continue
        for item in re.findall(r'<item>(.*?)</item>', feed, re.S):
            if added >= limit: break
            guid = tag(item, 'guid') or tag(item, 'link')
            if not guid or guid in seen: skipped += 1; continue
            body = (re.search(r'<content:encoded>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</content:encoded>', item, re.S) or [None, ''])
            body = body.group(1) if hasattr(body, 'group') else ''
            if not body: body = tag(item, 'description')
            paras = to_paras(body)
            n = sum(len(p.split()) for p in paras)
            title = html.unescape(re.sub(r'<[^>]+>', '', tag(item, 'title'))).strip()
            if not (MIN_WORDS <= n <= MAX_WORDS):
                skipped += 1
                print(f"    건너뜀({n}단어): {title[:52]}")
                continue
            pub = tag(item, 'pubDate')
            try:
                dt = datetime.datetime.strptime(pub[:25].strip(), '%a, %d %b %Y %H:%M:%S')
            except Exception:
                dt = datetime.datetime.now(datetime.timezone.utc)
            aid = hashlib.md5(guid.encode()).hexdigest()[:8]
            rec = {'id': aid, 'guid': guid, 'title': title, 'url': tag(item, 'link'),
                   'date': dt.strftime('%Y-%m-%d'), 'source': source, 'paras': paras, 'words': n}
            out = os.path.join(SRC, f"{rec['date']}_{aid}.json")
            json.dump(rec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            seen.add(guid); added += 1
            print(f"    받음({n}단어): {title[:52]}")

    # 오래된 기사 정리
    files = sorted(os.listdir(SRC))
    if len(files) > KEEP:
        for fn in files[:len(files) - KEEP]:
            os.remove(os.path.join(SRC, fn))
        print(f"  오래된 기사 {len(files) - KEEP}건 정리")
    print(f"새로 받은 기사 {added}건 / 건너뜀 {skipped}건 / 보관 중 {len(os.listdir(SRC))}건")


if __name__ == '__main__':
    main()
