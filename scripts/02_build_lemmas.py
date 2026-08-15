#!/usr/bin/env python3
"""
2단계(톰 소여): 단어를 세고, 변화형을 원형으로 묶는다(표제어화).

하는 일
  1) 텍스트를 단어 단위로 쪼갠다
  2) 대문자로만 쓰이는 단어는 고유명사(인명·지명)로 보고 따로 뺀다
  3) 변화형을 원형으로 묶는다  (staring/stared/stares -> stare)
  4) 결과를 data/lemma.json 에 저장

표제어화 규칙 (직접 만든 규칙 기반 — 외부 라이브러리 불필요)
  · 불규칙 동사/명사는 IRREGULAR 표에서 직접 매핑 (went->go, men->man)
  · -s / -es 는 원형을 그대로 자른 형태만 인정한다
      ※ 'stars' 에 e를 붙여 'stare' 로 만드는 식의 오작동을 막기 위함
  · -ed / -ing / -d 는 e를 붙이거나(hoped->hope) 겹자음을 푸는 것(running->run)까지 허용
  · -er / -est / -ly 는 <다루지 않는다>
      ※ number->numb, cover->cove, barely->bare 처럼 뜻이 완전히 달라지는
        잘못된 묶임이 실제로 발생했기 때문에 의도적으로 제외한 것.
        이 규칙을 되살리려면 반드시 결과를 눈으로 검수할 것.

결과물: data/lemma.json  {"g": {원형: 빈도}, "forms": {원형: [변화형...]}, "propn": [고유명사...]}
"""
import re, json, collections, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'source.txt')
OUT = os.path.join(ROOT, 'data', 'lemma.json')

IRREGULAR = {
 'went':'go','gone':'go','done':'do','said':'say','had':'have','has':'have','was':'be','were':'be',
 'been':'be','is':'be','are':'be','am':'be','men':'man','women':'woman','children':'child','feet':'foot',
 'teeth':'tooth','knew':'know','known':'know','saw':'see','seen':'see','took':'take','taken':'take',
 'came':'come','got':'get','gotten':'get','made':'make','thought':'think','told':'tell','felt':'feel',
 'left':'leave','kept':'keep','held':'hold','stood':'stand','sat':'sit','ran':'run','began':'begin',
 'begun':'begin','brought':'bring','bought':'buy','caught':'catch','chose':'choose','chosen':'choose',
 'drew':'draw','drawn':'draw','drove':'drive','driven':'drive','fell':'fall','fallen':'fall','found':'find',
 'gave':'give','given':'give','grew':'grow','grown':'grow','heard':'hear','led':'lead','lay':'lie',
 'lain':'lie','lost':'lose','met':'meet','paid':'pay','put':'put','read':'read','rose':'rise','risen':'rise',
 'sent':'send','shook':'shake','shaken':'shake','shone':'shine','shot':'shoot','showed':'show','shown':'show',
 'shut':'shut','sang':'sing','sung':'sing','slept':'sleep','spoke':'speak','spoken':'speak','spent':'spend',
 'stuck':'stick','struck':'strike','swept':'sweep','swore':'swear','sworn':'swear','threw':'throw',
 'thrown':'throw','understood':'understand','woke':'wake','woken':'wake','wore':'wear','worn':'wear',
 'won':'win','wrote':'write','written':'write','lit':'light','fled':'flee','flew':'fly','flown':'fly',
 'hung':'hang','laid':'lay','built':'build','burnt':'burn','dealt':'deal','dreamt':'dream','crept':'creep',
 'clung':'cling','dug':'dig','fed':'feed','fought':'fight','forgot':'forget','forgotten':'forget',
 'froze':'freeze','frozen':'freeze','hid':'hide','hidden':'hide','learnt':'learn','leapt':'leap',
 'meant':'mean','rang':'ring','rung':'ring','sold':'sell','slid':'slide','spat':'spit','split':'split',
 'spread':'spread','sprang':'spring','stole':'steal','stolen':'steal','swung':'swing','tore':'tear',
 'torn':'tear','wept':'weep','wound':'wind','bit':'bite','bitten':'bite','blew':'blow','blown':'blow',
 'broke':'break','broken':'break','ate':'eat','eaten':'eat','drank':'drink','drunk':'drink','rode':'ride',
 'ridden':'ride','sank':'sink','sunk':'sink','sought':'seek','taught':'teach','wrung':'wring',
 'strode':'stride','strove':'strive','slunk':'slink','flung':'fling','stung':'sting','swum':'swim','swam':'swim',
}

def normalize(t):
    t = (t.replace('’', "'").replace('‘', "'")
           .replace('“', '"').replace('”', '"'))
    return re.sub(r'-\n\s*', '', t)          # 줄 끝에서 하이픈으로 잘린 단어를 붙인다

def main():
    text = normalize(open(SRC, encoding='utf-8', errors='ignore').read())
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    freq = collections.Counter(w.lower().strip("'-") for w in tokens)
    V = set(freq)

    # 고유명사 판별: 3회 이상 나오면서, '문장 첫머리가 아닌 자리'에서 85% 이상 대문자로 시작하는 단어
    #   (문장 첫 단어는 누구나 대문자라서 세지 않는다. I, I'm 같은 대명사는 제외한다)
    cap = collections.Counter()
    for m in re.finditer(r"[A-Za-z][A-Za-z'-]*", text):
        w = m.group(0)
        if not w[0].isupper(): continue
        before = text[max(0, m.start() - 3):m.start()]
        QUOTES = "\"“‘'—"          # " “ ‘ ' —
        if m.start() == 0 or not before.strip() or re.search(r"[.!?][\s\"“‘']*$", before) or before.strip()[-1] in QUOTES:
            continue                       # 문장/대사 첫머리는 무시
        cap[w.lower().strip("'-")] += 1
    PRON = {'i', "i'd", "i'll", "i'm", "i've", 'ah', 'oh', 'hello', 'certainly', 'well', 'yes', 'no', 'lord'}
    propn = {w for w, n in freq.items()
             if n >= 3 and w not in PRON and cap.get(w, 0) / n > 0.6}

    def lemma(w):
        if w.endswith("'s") and len(w) > 3:
            return lemma(w[:-2])
        if w in IRREGULAR and IRREGULAR[w] in V:
            return IRREGULAR[w]
        c = []
        for suf, rep in [("ies", "y"), ("ied", "y"), ("ves", "f"), ("ves", "fe")]:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                x = w[:-len(suf)] + rep
                if x in V: c.append(x)
        for suf in ["s", "es"]:                       # 복수/3인칭 — 자른 형태만
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                x = w[:-len(suf)]
                if x in V and x != w: c.append(x)
        for suf in ["ed", "ing", "d"]:                # 과거/진행 — +e, 겹자음 허용
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                b = w[:-len(suf)]
                opts = [b, b + "e"]
                if len(b) > 3 and b[-1] == b[-2] and b[-1] not in 'aeiou':
                    opts.append(b[:-1])
                for x in opts:
                    if x in V and x != w: c.append(x)
        return max(c, key=lambda x: freq.get(x, 0)) if c else w

    lem = {w: lemma(w) for w in V}
    for w in list(lem):                               # A->B->C 연쇄를 끝까지 따라간다
        seen, x = set(), w
        while lem.get(x, x) != x and x not in seen:
            seen.add(x); x = lem.get(x, x)
        lem[w] = x

    g, forms = collections.Counter(), collections.defaultdict(set)
    for w, n in freq.items():
        g[lem[w]] += n
        forms[lem[w]].add(w)
    g = {w: n for w, n in g.items() if w not in propn and not (forms[w] & propn)}

    json.dump({'g': g,
               'forms': {k: sorted(v) for k, v in forms.items() if k in g},
               'propn': sorted(propn)},
              open(OUT, 'w'), ensure_ascii=False)
    print(f"전체 토큰 {sum(freq.values()):,} / 표면형 {len(V):,} / 원형 {len(g):,} / 고유명사 {len(propn):,}")
    print(f"저장: {OUT}")

if __name__ == '__main__':
    main()
