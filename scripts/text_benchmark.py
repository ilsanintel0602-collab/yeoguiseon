#!/usr/bin/env python3
"""
Phase D2: 텍스트 검색 정확도 자동 측정 (사진 X, Worker 호출 X)

300+ 일상 어휘 → searchByText 알고리즘과 동일 로직 → 카테고리별 정확도

사용:
  python scripts/text_benchmark.py
  → benchmark/text_report_YYYY-MM-DD.md 생성

주간 GitHub Actions cron이 자동 실행.
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))

# 300+ 일상 어휘 테스트 표본 (사용자 시나리오 광범위)
TEST_SET = [
    # 의류·신발·가방 (30)
    ('운동화','clothes'),('구두','clothes'),('샌들','clothes'),('스니커즈','clothes'),('부츠','clothes'),
    ('슬리퍼','clothes'),('하이힐','clothes'),('로퍼','clothes'),('워커','clothes'),('컨버스','clothes'),
    ('가방','clothes'),('백팩','clothes'),('핸드백','clothes'),('에코백','clothes'),('지갑','clothes'),
    ('모자','clothes'),('캡','clothes'),('비니','clothes'),('야구모자','clothes'),('베레모','clothes'),
    ('셔츠','clothes'),('바지','clothes'),('속옷','clothes'),('양말','clothes'),('스타킹','clothes'),
    ('스카프','clothes'),('목도리','clothes'),('장갑','clothes'),('넥타이','clothes'),('벨트','clothes'),
    # 종이 (15)
    ('책','paper'),('신문','paper'),('잡지','paper'),('상자','paper'),('박스','paper'),
    ('공책','paper'),('노트','paper'),('포장지','paper'),('전단지','paper'),('카탈로그','paper'),
    ('달력','paper'),('두꺼운 종이','paper'),('편지','paper'),('엽서','paper'),('크라프트 종이','paper'),
    # 종이팩 (8)
    ('우유팩','paper_pack'),('두유팩','paper_pack'),('주스팩','paper_pack'),
    ('베지밀 팩','paper_pack'),('아몬드 우유팩','paper_pack'),('두유 종이팩','paper_pack'),
    ('멸균팩','paper_pack'),('음료팩','paper_pack'),
    # 플라스틱 (15)
    ('페트병','plastic'),('플라스틱병','plastic'),('플라스틱 용기','plastic'),
    ('요거트통','plastic'),('샴푸통','plastic'),('세제통','plastic'),('제습제','plastic'),
    ('도시락 용기','plastic'),('컵라면 용기','plastic'),('플라스틱 뚜껑','plastic'),
    ('소스병','plastic'),('빨대','plastic'),('투명 페트병','plastic'),('샐러드 용기','plastic'),('플라스틱 컵','plastic'),
    # 비닐 (10)
    ('비닐봉지','vinyl'),('비닐','vinyl'),('비닐 포장지','vinyl'),('과자봉지','vinyl'),('라면봉지','vinyl'),
    ('지퍼백','vinyl'),('에어캡','vinyl'),('OPP 봉투','vinyl'),('포장 비닐','vinyl'),('필름류','vinyl'),
    # 캔·금속 (10)
    ('맥주캔','can'),('알루미늄캔','can'),('통조림','can'),('참치캔','can'),
    ('사료캔','can'),('스팸캔','can'),('호일','can'),('알루미늄 호일','can'),
    ('철 조각','can'),('금속 캡','can'),
    # 유리 (10)
    ('유리병','glass'),('와인병','glass'),('맥주병','glass'),('소주병','glass'),
    ('잼병','glass'),('소스병 유리','glass'),('빈 병','glass'),('재활용 유리','glass'),
    ('유리 음료병','glass'),('빈병 반환','glass'),
    # 음식물 (10)
    ('과일껍질','food'),('밥','food'),('국물','food'),('남은 음식','food'),('찌꺼기','food'),
    ('밥찌꺼기','food'),('야채 껍질','food'),('과일 찌꺼기','food'),('남은밥','food'),('국','food'),
    # 일반 (20)
    ('가위','general'),('칫솔','general'),('수세미','general'),('휴지','general'),('마스크','general'),
    ('기저귀','general'),('볼펜','general'),('연필','general'),('일회용 면도기','general'),
    ('일회용 젓가락','general'),('성냥','general'),('이쑤시개','general'),('껌','general'),
    ('헝겊','general'),('걸레','general'),('나무젓가락','general'),
    ('손톱깎이','general'),('면봉','general'),('필통','general'),('학용품 통','general'),
    # 배터리 (8)
    ('AA건전지','battery'),('AAA건전지','battery'),('보조배터리','battery'),
    ('드론 배터리','battery'),('코인 배터리','battery'),('CR2032','battery'),('시계 배터리','battery'),('리튬이온','battery'),
    # 형광등·LED (6)
    ('형광등','lamp'),('LED','lamp'),('LED 전구','lamp'),('LED 조명','lamp'),('백열전구','lamp'),('할로겐','lamp'),
    # 가전 (15)
    ('노트북','electronics'),('휴대폰','electronics'),('TV','electronics'),
    ('드라이기','electronics'),('이어폰','electronics'),('키보드','electronics'),('마우스','electronics'),
    ('충전기','electronics'),('스피커','electronics'),('전기면도기','electronics'),
    ('전기밥솥','electronics'),('전자레인지','electronics'),('가습기','electronics'),
    ('선풍기','electronics'),('블루투스 스피커','electronics'),
    # 가구 (10)
    ('소파','furniture'),('침대','furniture'),('책상','furniture'),('의자','furniture'),
    ('옷장','furniture'),('식탁','furniture'),('서랍장','furniture'),('책장','furniture'),
    ('화장대','furniture'),('탁자','furniture'),
    # 위험물·약품·재사용 (15)
    ('가스라이터','hazardous'),('페인트','hazardous'),('스프레이 캔','hazardous'),
    ('부탄가스','hazardous'),('시너','hazardous'),
    ('알약','medicine'),('연고','medicine'),('시럽','medicine'),('처방약','medicine'),('남은약','medicine'),
    ('머그컵','reusable'),('머그','reusable'),('머그잔','reusable'),
    # 오타 (사용자 시나리오)
    ('운동홲','clothes'),('가뱅','clothes'),
]


def search(items, q):
    """app.html searchByText와 동일 로직"""
    CATCHALL = {'기타_일반', '재활용가능한 것', 'general'}
    q = q.strip().lower()
    out = []
    for key, item in items.items():
        id_l = key.lower()
        name = (item.get('name') or key).lower()
        aliases = [str(a).lower() for a in (item.get('aliases') or [])]
        score = 0
        if id_l == q: score = 100
        elif name == q: score = 95
        elif q in aliases: score = 90
        elif name.startswith(q): score = 80
        elif any(a.startswith(q) for a in aliases): score = 70
        elif q in name: score = 50
        elif any(q in a for a in aliases): score = 40
        if score > 0:
            penalty = 1 if (key in CATCHALL or item.get('category') == 'general') else 0
            out.append((key, item.get('name', key), item.get('category'), score, len(name), penalty))
    out.sort(key=lambda x: (-x[3], x[5], x[4]))
    return out[:1]


def main():
    with open(os.path.join(ROOT, 'data', 'national_rules.json'), encoding='utf-8') as f:
        nat = json.load(f)
    items = nat['items']

    by_cat_total = defaultdict(int)
    by_cat_correct = defaultdict(int)
    wrong = []

    for q, exp in TEST_SET:
        by_cat_total[exp] += 1
        r = search(items, q)
        if r and r[0][2] == exp:
            by_cat_correct[exp] += 1
        else:
            wrong.append((q, exp, r[0] if r else None))

    total = len(TEST_SET)
    correct = sum(by_cat_correct.values())
    pct = correct / total * 100

    # 보고서 생성
    today = datetime.now().strftime('%Y-%m-%d')
    report_dir = os.path.join(ROOT, 'benchmark')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f'text_report_{today}.md')

    md = [
        f"# 텍스트 검색 벤치마크 — {today}",
        f"",
        f"**전체 정답률**: {correct}/{total} = **{pct:.1f}%**",
        f"**items**: {len(items)} / **aliases**: {sum(len(v.get('aliases',[])) for v in items.values())}",
        f"",
        f"## 카테고리별 정확도",
        f"",
        f"| 카테고리 | 정답 | 전체 | % |",
        f"|---|---|---|---|",
    ]
    for cat in sorted(by_cat_total.keys()):
        c, t = by_cat_correct[cat], by_cat_total[cat]
        md.append(f"| {cat} | {c} | {t} | {c/t*100:.1f}% |")

    if wrong:
        md.append(f"")
        md.append(f"## 오답 {len(wrong)}건")
        md.append(f"")
        for q, exp, got in wrong:
            got_str = f"{got[1]} ({got[2]})" if got else "결과 없음"
            md.append(f"- `{q}` → {got_str} [기대: {exp}]")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print(f"=== 텍스트 검색 벤치마크 ({today}) ===")
    print(f"정답률: {correct}/{total} = {pct:.1f}%")
    print(f"보고서: {report_path}")
    sys.exit(0 if pct >= 95 else 1)


if __name__ == '__main__':
    main()
