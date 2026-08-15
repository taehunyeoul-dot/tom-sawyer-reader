#!/usr/bin/env python3
"""
5단계(보조): 이 소설(톰 소여)에서 자주 나오는 문장구조 유형을 정규식으로 찾아 실제 예문을 뽑는다.

  · 문장구조 해설(data/structures.json)은 사람이/튜터가 쓰지만, 그 예문은 여기서 원문에서 기계적으로 고른다.
  · 07_annotate.py 가 같은 PATTERNS 를 써서 본문 문장마다 구조 태그를 붙인다 (import 해서 씀).

사용법: python scripts/05_find_patterns.py            → data/pattern_hits.json
        python scripts/05_find_patterns.py '정규식'   → 임의 패턴 시험
"""
import json, re, os, sys, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, 'data', *p)

NAMES = r"(?:Tom|Huck|Huckleberry|Joe|Becky|Sid|Mary|Polly|Aunt Polly|the widow|the Welshman|Injun Joe|Potter|Muff Potter|the judge|Judge Thatcher|Mr\. [A-Z][a-z]+|Mrs\. [A-Z][a-z]+|the (?:boy|boys|old lady|teacher|master|minister|doctor|stranger|man|girl|children)|[A-Z][a-z]+)"
SPEECH = r"(?:said|cried|replied|asked|answered|exclaimed|shouted|muttered|whispered|added|continued|called|remarked|murmured|observed|retorted|sighed|groaned|sobbed|roared|yelled|laughed|gasped|pleaded|urged|protested|insisted|begged|inquired|demanded|snapped|growled|thundered|moaned|mused|ejaculated|ventured|suggested|drawled|chuckled|snarled|screamed|sneered|faltered|stammered|wailed|whimpered|mumbled|agreed|responded|interrupted|returned|resumed|began|pursued)"
DIALECT = r"\b(?:warn't|ain't|hain't|gwine|'bout|becuz|t'other|kin|git|reckon|'em|dasn't|dast|feller|fellers|'twas|'tain't|tain't|dunno|sorter|kinder|nuther|'nough|'spect|s'pose|'low|'lowed|druther|ruther|shucks|jings|lemme|gimme|ole|yaller|hunderd|blame|blamed|dern|derned|consound|goner|bully|hooky|jest|jist|'a'|hyer|thar|whar|ye|hain't|sho'|sh'd|c'n|wisht|didn'|couldn'|wouldn'|nuff|nuffn|'deed|'long|'way|'most|'bout|'cause|'lection|'tis|'twould|'twill|hev|thish-yer)\b"
PATTERNS = {
 1:  (r"[,?!.—]”\s*" + SPEECH + r" " + NAMES, "인용 뒤 도치된 전달동사 (said Tom / cried Huck)"),
 2:  (DIALECT, "19세기 미국 사투리·구어 철자 (warn't, gwine, 'bout, kin)"),
 3:  (r"; [a-z“]", "세미콜론으로 이어 붙인 절"),
 4:  (r"—[^—]{4,90}—|[A-Za-z,]—”|—”$", "대시(—) 삽입·말 끊김"),
 5:  (r": [a-z“]", "콜론(:) — 뒤에서 풀어 말하기"),
 6:  (r", (?:[a-z]+ )?[a-z]+ing\b(?! (?:was|were|is|are))", "문장 뒤에 붙는 ~ing (…, feeling sore and drowsy) — '~하면서'"),
 7:  (r"^[A-Z][a-z]+(?:ed|en|t)\b(?: by| with| at| in| of| and [a-z]+)?.{0,60}?, (?:he|she|they|Tom|Huck|the|his|her|it)\b", "과거분사·형용사로 시작하는 문장"),
 8:  (r"^(?:When|While|As|After|Before|By the time|Just as|Because|If|Although|Though|Since|Until|Whenever|Once)\b[^,]{3,70},", "부사절이 앞에 오는 문장 (When …, / If …, / As …,)"),
 9:  (r", which\b|\bwhose\b|, (?:some|all|most|none|one|both) of (?:which|whom)\b", "쉼표+which / whose — 덧붙이는 관계절"),
 10: (r"\bas (?:if|though)\b", "as if / as though — 마치 ~인 듯"),
 11: (r"^(?:Never|Not once|Not until|Nor|Neither|Only (?:when|then|after|once)|Seldom|Rarely|Nowhere|Hardly|Scarcely|Little|So|Such|Then|Now|Out|Down|Up|Away|In|Here|There|Presently|Away)\b.{0,40}?\b(?:had|did|was|were|do|does|could|would|is|are|has|have|came|went|stood|sat|lay|rose|ran|rushed) (?:he|she|it|they|I|we|you|Tom|Huck|the|a|an|his|her|two|three|Aunt|Injun)\b", "도치 — 부사·부정어가 앞에 오고 동사가 주어보다 먼저"),
 12: (r"\bif [^,;]{2,45}?(?:would|could|might|should|had|were)\b|\b(?:would|could|might|should) have [a-z]+(?:ed|en)\b|\b(?:were|had) (?:he|she|it|they|I|we|you|Tom) \b", "가정법 (if … would / would have p.p.)"),
 13: (r", for (?:he|she|it|they|there|the|his|her|this|that|nobody|no|every|I|we|you|Tom|Huck|a|an|in|by|when|if|now|now)\b", "쉼표 + for = because (이유를 뒤에 붙임)"),
 14: (r"\band\b[^.;]*\band\b[^.;]*\band\b[^.;]*\band\b", "and … and … and — 길게 잇는 나열"),
 15: (r"\b(?:Why|What|How|Where|Who|When) (?:on earth |in the world |the mischief |the dickens )?(?:had|did|was|were|would|could|should|must) (?:he|she|they|it|I)\b[^“”]*[?!]", "자유간접화법 — 인물의 속생각이 의문문·감탄문으로"),
 16: (r"(?:ain't it|hain't it|don't you|didn't you|won't you|wouldn't you|ain't you|can't you|will you|do you|hey|did you|would you|couldn't you|is it|was it|don't it|ain't they|ain't he|ain't she|hain't you|hain't he|didn't he|didn't they)\?", "부가의문문·되묻기 (…, ain't it? / hey?)"),
 17: (r"^It was [^,.]{2,45}? (?:that|who|which)\b|^What (?:[a-z’]+ ){2,8}was\b|^(?:There|Here) (?:was|were|is|are|came|stood|lay|sat|rose)\b", "It was … that / What … was / There was — 강조·존재 구문"),
 18: (r"^(?:The|A|An|His|Her|Their|Its|This|That|These|Those|Every|Some|Many|Two|Three) (?:[a-z’-]+ ){1,4}(?:of|in|with|that|who|which|whom|on|at|from|by) [^,;]{4,60}? (?:was|were|had|is|are|would|could|did|began|came|went|seemed|made|took|stood|lay|sat|rose|fell|grew|got|kept|found)\b", "긴 주어 — 주어 뒤에 꾸밈말이 붙어 동사가 멀리 있음"),
}
CPATS = {k: re.compile(v[0]) for k, v in PATTERNS.items()}


def norm(s):
    return s.replace('_', '')


if __name__ == '__main__':
    book = json.load(open(D('book.json'), encoding='utf-8'))
    sents = [(c['n'], s) for c in book['chapters'] for p in c['paras'] for s in p]
    random.seed(7)
    pats = PATTERNS
    if len(sys.argv) > 1:
        pats = {0: (sys.argv[1], '사용자 입력')}
    result = {}
    for k, (pat, name) in pats.items():
        rx = re.compile(pat)
        hits = [(n, s) for n, s in sents if rx.search(norm(s))]
        short = [(n, s) for n, s in hits if 7 <= len(s.split()) <= 26] or hits
        ex = random.sample(short, min(6, len(short)))
        result[k] = {'name': name, 'count': len(hits), 'examples': [{'ch': n, 'en': s} for n, s in ex]}
        print(f"\n■ {k}. {name}: {len(hits):,}회")
        for n, s in ex[:3]: print(f"   [{n}장] {s[:150]}")
    if len(sys.argv) == 1:
        json.dump(result, open(D('pattern_hits.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"\n저장: {D('pattern_hits.json')}")
