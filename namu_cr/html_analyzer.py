import csv
import html
import re
import time
from pathlib import Path


# ============================================================
# 설정
# ============================================================

SOURCE_FILE = "source.html"

OUTPUT_CSV = "battlecats_links.csv"
OUTPUT_TXT = "battlecats_links.txt"

TARGET_DOMAIN = "battlecats-db.com"

# 목차의 섹션 링크
# 예: <a href="#s-3.1">3.1.</a>
TOC_PATTERN = re.compile(
    r'<a\b[^>]*href=["\']#s-(\d+(?:\.\d+)+)["\'][^>]*>.*?</a>'
    r'(.*?)</span>',
    re.IGNORECASE | re.DOTALL
)

# 본문 섹션 시작점
# 예: <a id="s-3.1" href="#toc">3.1.</a>
SECTION_PATTERN = re.compile(
    r'<a\b[^>]*id=["\']s-(\d+(?:\.\d+)+)["\'][^>]*>',
    re.IGNORECASE
)

# battlecats 링크
BATTLECATS_LINK_PATTERN = re.compile(
    r'<a\b[^>]*href=["\'](https?://(?:www\.)?battlecats-db\.com/[^"\']*)["\'][^>]*>'
    r'(.*?)</a>',
    re.IGNORECASE | re.DOTALL
)

# 캐릭터 ID
ID_PATTERN = re.compile(r"^\d+-\d+$")


# ============================================================
# 텍스트 정리
# ============================================================

def strip_tags(text):
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def normalize_text(text):
    text = strip_tags(text)
    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# source.html 읽기
# ============================================================

def load_source():
    path = Path(SOURCE_FILE)

    if not path.exists():
        print(f"[오류] {SOURCE_FILE} 파일이 없습니다.")
        print("html_crawler.py를 먼저 실행하세요.")
        raise SystemExit(1)

    data = path.read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")

    return data.decode("utf-8", errors="replace")


# ============================================================
# 목차 캐릭터 추출
# ============================================================

def extract_toc_characters(source):
    """
    페이지의 목차에서 캐릭터 목록을 가져온다.

    현재 나무위키 구조처럼:

        <span>
            <a href="#s-3.1">3.1.</a>
            "바람의 신・윈디"
        </span>

    형태를 기준으로 한다.

    특정 class 이름은 사용하지 않는다.
    """

    characters = []
    seen = set()

    for match in TOC_PATTERN.finditer(source):
        section = match.group(1)
        raw_name = match.group(2)

        name = normalize_text(raw_name)

        # 혹시 목차 번호가 같이 남는 경우 제거
        name = re.sub(
            r"^\s*\d+(?:\.\d+)+\.?\s*",
            "",
            name
        ).strip()

        if not name:
            continue

        if section in seen:
            continue

        seen.add(section)

        characters.append({
            "section": section,
            "name": name,
        })

    return characters


# ============================================================
# 본문 섹션 위치
# ============================================================

def extract_section_positions(source):
    positions = {}

    for match in SECTION_PATTERN.finditer(source):
        section = match.group(1)

        if section not in positions:
            positions[section] = match.start()

    return positions


# ============================================================
# battlecats 링크 추출
# ============================================================

def extract_battlecats_links(section_source):
    results = []

    for match in BATTLECATS_LINK_PATTERN.finditer(
        section_source
    ):
        url = html.unescape(match.group(1))
        link_text = normalize_text(match.group(2))

        # battlecats-db의 일반 링크/광고 링크 제외
        if not ID_PATTERN.fullmatch(link_text):
            continue

        results.append({
            "id": link_text,
            "url": url,
        })

    return results


# ============================================================
# 캐릭터 + ID 연결
# ============================================================

def build_records(source):
    characters = extract_toc_characters(source)
    section_positions = extract_section_positions(source)

    print(
        f"[목차] 캐릭터 목록 : {len(characters):,}개"
    )

    records = []

    for index, character in enumerate(characters):
        section = character["section"]
        name = character["name"]

        start = section_positions.get(section)

        if start is None:
            print(
                f"[경고] 본문 섹션 없음: "
                f"{section} {name}"
            )
            continue

        # 다음 목차 캐릭터의 본문 섹션 위치
        end = len(source)

        for next_character in characters[index + 1:]:
            next_start = section_positions.get(
                next_character["section"]
            )

            if next_start is not None and next_start > start:
                end = next_start
                break

        section_source = source[start:end]

        links = extract_battlecats_links(
            section_source
        )

        # 같은 섹션에서 같은 ID가 반복되면 한 번만 기록
        seen_ids = set()

        for link in links:
            key = (
                link["id"],
                link["url"]
            )

            if key in seen_ids:
                continue

            seen_ids.add(key)

            records.append({
                "character_name": name,
                "section": section,
                "id": link["id"],
                "url": link["url"],
            })

        print(
            f"[매칭] {section}. {name} "
            f"→ {len(seen_ids)}개 ID"
        )

    return characters, records


# ============================================================
# 전체 중복 제거
# ============================================================

def deduplicate_records(records):
    seen = set()
    result = []

    for record in records:
        key = (
            record["character_name"],
            record["section"],
            record["id"],
            record["url"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


# ============================================================
# 결과 출력
# ============================================================

def print_results(characters, records):
    print()
    print("=" * 80)
    print("캐릭터 + battlecats ID")
    print("=" * 80)

    if not records:
        print("추출된 캐릭터 ID가 없습니다.")
        return

    current_section = None

    for record in records:
        if record["section"] != current_section:
            current_section = record["section"]

            print()
            print(
                f"[{record['section']}] "
                f"{record['character_name']}"
            )

        print(
            f"    {record['id']} "
            f"→ {record['url']}"
        )

    print()
    print("-" * 80)
    print(f"목차 캐릭터 수 : {len(characters):,}")
    print(f"추출 ID 수     : {len(records):,}")


# ============================================================
# CSV 저장
# ============================================================

def save_csv(records):
    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "character_name",
                "section",
                "id",
                "url",
            ]
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"[저장] CSV : {OUTPUT_CSV}")


# ============================================================
# TXT 저장
# ============================================================

def save_txt(records):
    with open(
        OUTPUT_TXT,
        "w",
        encoding="utf-8"
    ) as f:
        for record in records:
            f.write(
                f"{record['character_name']}\t"
                f"{record['section']}\t"
                f"{record['id']}\t"
                f"{record['url']}\n"
            )

    print(f"[저장] TXT : {OUTPUT_TXT}")


# ============================================================
# 실행
# ============================================================

def main():
    start_time = time.time()

    print(f"[읽기] {SOURCE_FILE}")

    source = load_source()

    print(
        f"[정보] HTML 크기 : {len(source):,} 문자"
    )

    print(
        "[추출] 목차 → 본문 섹션 → battlecats ID"
    )

    characters, records = build_records(source)

    records = deduplicate_records(records)

    print_results(
        characters,
        records
    )

    save_csv(records)
    save_txt(records)

    elapsed = time.time() - start_time

    print()
    print(
        f"[완료] 전체 소요 : {elapsed:.2f}초"
    )


if __name__ == "__main__":
    main()
