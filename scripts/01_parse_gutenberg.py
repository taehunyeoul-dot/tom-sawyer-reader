#!/usr/bin/env python3
"""
1단계: Project Gutenberg 텍스트(eBook #74, The Adventures of Tom Sawyer)를
'장(章) → 문단 → 문장' 구조로 쪼갠다.

하는 일
  1) 구텐베르크 머리말/꼬리말(라이선스 안내)을 떼어내고 본문만 남긴다
  2) CONTENTS 에서 장 제목("CHAPTER I. Y-o-u-u Tom—Aunt Polly Decides…")을 읽어 둔다
  3) 'CHAPTER I' ~ 'CHAPTER XXXV' + 'CONCLUSION' 을 장으로 나눈다 (총 36개)
  4) 빈 줄 기준으로 문단을 나누고, 줄바꿈을 공백으로 잇는다
  5) _단어_ 로 표시된 이탤릭은 밑줄을 없앤다 (뜻은 같고 강조 표시일 뿐)
  6) 문단을 문장으로 나눈다
  7) 각주([*] …)는 문단 뒤에 'note' 로 붙여 둔다

결과물
  data/book.json   {"title","author","chapters":[{"n":1,"roman":"I","title":"…","paras":[["문장",…],…]},…]}
  data/source.txt  본문만 모은 텍스트 (어휘 통계용)

외부 라이브러리를 쓰지 않는다.
"""
import re, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'gutenberg_74.txt')
OUT = os.path.join(ROOT, 'data', 'book.json')
TXT = os.path.join(ROOT, 'data', 'source.txt')

ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV','XVI','XVII','XVIII','XIX','XX',
         'XXI','XXII','XXIII','XXIV','XXV','XXVI','XXVII','XXVIII','XXIX','XXX','XXXI','XXXII','XXXIII','XXXIV','XXXV']

ABBR = re.compile(r"\b(Mr|Mrs|Ms|Dr|St|Prof|Sgt|Lt|Capt|Rev|Jr|Sr|vs|etc|e\.g|i\.e|a\.m|p\.m|No)\.$")

def split_sentences(p):
    """문단 → 문장. 마침표/물음표/느낌표(+닫는 따옴표·괄호) 뒤에 공백, 그 뒤 대문자·따옴표·괄호가 오면 자른다."""
    parts = re.split(r"(?<=[.!?][’'\"”)\]])\s+(?=[A-Z‘“'\"(\[_])|(?<=[.!?])\s+(?=[A-Z‘“'\"(\[_])", p)
    out = []
    for s in parts:
        s = s.strip()
        if not s: continue
        if out and (ABBR.search(out[-1]) or len(out[-1]) < 3):
            out[-1] = out[-1] + ' ' + s
        else:
            out.append(s)
    return out


def main():
    raw = open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
    # 1) 본문 범위: 'CHAPTER I' 가 (목차 다음에) 단독 줄로 나오는 곳부터 END 표시 전까지
    lines = raw.split('\n')
    start = next(i for i, l in enumerate(lines) if l.strip() == 'CHAPTER I')
    end = next(i for i, l in enumerate(lines) if l.startswith('*** END OF THE PROJECT GUTENBERG'))
    # 2) 목차에서 장 제목 읽기 (CONTENTS ~ PREFACE 사이, "CHAPTER I. 제목" 이 여러 줄에 걸칠 수 있음)
    c0 = next(i for i, l in enumerate(lines) if l.strip() == 'CONTENTS')
    c1 = next(i for i, l in enumerate(lines) if l.strip() == 'PREFACE')
    titles, cur = {}, None
    for l in lines[c0 + 1:c1]:
        m = re.match(r'CHAPTER ([IVXL]+)\.\s*(.*)', l.strip())
        if m:
            cur = m.group(1); titles[cur] = m.group(2).strip()
        elif l.strip() and cur:
            titles[cur] += ' ' + l.strip()
        elif not l.strip():
            cur = None
    print(f"목차 제목 {len(titles)}개")

    body = lines[start:end]
    # 3) 장 나누기
    chapters, cur = [], None
    for l in body:
        s = l.strip()
        m = re.fullmatch(r'CHAPTER ([IVXL]+)', s)
        if m or s == 'CONCLUSION':
            if cur: chapters.append(cur)
            r = m.group(1) if m else 'CONCLUSION'
            cur = {'roman': r, 'title': titles.get(r, 'Conclusion' if not m else ''), 'lines': []}
            continue
        if cur is not None: cur['lines'].append(l)
    if cur: chapters.append(cur)
    print(f"장 {len(chapters)}개")

    all_text = []
    out = []
    for k, c in enumerate(chapters):
        # 4) 문단
        paras, buf = [], []
        for l in c['lines'] + ['']:
            if l.strip():
                buf.append(l.strip())
            else:
                if buf: paras.append(' '.join(buf)); buf = []
        # 5) 이탤릭 밑줄 제거, 공백 정리
        paras = [re.sub(r'_([^_]+)_', r'\1', p) for p in paras]
        paras = [re.sub(r'\s+', ' ', p).strip() for p in paras]
        # 7) 각주 문단([*] …)은 앞 문단의 note 로
        notes = {}
        clean = []
        for p in paras:
            if p.startswith('[*]'):
                if clean: notes[len(clean) - 1] = p[3:].strip()
                continue
            clean.append(p)
        # 6) 문장
        plist = []
        for i, p in enumerate(clean):
            sents = split_sentences(p)
            if not sents: continue
            item = {'s': sents}
            if i in notes: item['note'] = notes[i]
            plist.append(item)
        # 앱이 쓰기 쉽게: paras = [[문장,…],…], notes = {문단번호: 각주}
        out.append({'n': k + 1, 'roman': c['roman'], 'title': c['title'],
                    'paras': [x['s'] for x in plist],
                    'notes': {str(i): x['note'] for i, x in enumerate(plist) if 'note' in x}})
        all_text.append('\n\n'.join(clean))

    nsent = sum(len(p) for c in out for p in c['paras'])
    npara = sum(len(c['paras']) for c in out)
    ntok = sum(len(re.findall(r"[A-Za-z]+", s)) for c in out for p in c['paras'] for s in p)
    json.dump({'title': 'The Adventures of Tom Sawyer', 'author': 'Mark Twain', 'year': 1876,
               'source': 'Project Gutenberg eBook #74 (public domain)', 'chapters': out},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    open(TXT, 'w', encoding='utf-8').write('\n\n\n'.join(all_text))
    print(f"문단 {npara:,} / 문장 {nsent:,} / 단어(연인원) {ntok:,}")
    print(f"저장: {OUT}\n저장: {TXT}")
    for c in out[:2] + out[-1:]:
        print(f"  [{c['n']}] {c['roman']} — {c['title'][:50]} | 첫 문장: {c['paras'][0][0][:60]}")


if __name__ == '__main__':
    main()
