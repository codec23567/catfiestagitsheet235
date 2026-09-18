import html
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests


# ============================================================
# 설정
# ============================================================

TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

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
    r'<a\b[^>]*href=["\']'
    r'(https?://(?:www\.)?battlecats-db\.com/[^"\']*)'
    r'["\'][^>]*>'
    r'(.*?)</a>',
    re.IGNORECASE | re.DOTALL
)

# 캐릭터 ID
ID_PATTERN = re.compile(r"^\d+-\d+$")


# ============================================================
# 텍스트 처리
# ============================================================

def strip_tags(text):
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"<[^>]+>", "", text)

    return html.unescape(text)


def normalize_text(text):
    text = strip_tags(text)
    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# URL 확인
# ============================================================

def is_namu_url(url):
    try:
        host = urlparse(url).netloc.lower()

        return (
            host == "namu.wiki"
            or host.endswith(".namu.wiki")
        )

    except Exception:
        return False


def is_battlecats_url(url):
    try:
        host = urlparse(url).netloc.lower()

        return (
            host == TARGET_DOMAIN
            or host.endswith("." + TARGET_DOMAIN)
        )

    except Exception:
        return False


# ============================================================
# HTML 크롤링
# ============================================================

def crawl_html(url):
    print()
    print("=" * 80)
    print("HTML 크롤링")
    print("=" * 80)

    print(f"[요청] {url}")

    start_time = time.time()

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        request_time = time.time() - start_time

        print(
            f"[응답] 상태={response.status_code}, "
            f"바이트={len(response.content):,}, "
            f"인코딩={response.encoding}"
        )

        print(
            f"[응답] Content-Type="
            f"{response.headers.get('Content-Type', '')}"
        )

        print(
            f"[응답] 최종 URL={response.url}"
        )

        print(
            f"[시간] HTTP 요청 : {request_time:.2f}초"
        )

        response.raise_for_status()

        # 기존 crawler와 동일하게 bytes를 UTF-8로 해석한다.
        if response.content.startswith(b"\xef\xbb\xbf"):
            source = response.content.decode(
                "utf-8-sig"
            )
        else:
            source = response.content.decode(
                "utf-8",
                errors="replace"
            )

        return source

    except requests.Timeout:
        print("[오류] HTTP 요청 시간 초과")
        return None

    except requests.RequestException as e:
        print(f"[오류] HTTP 요청 실패: {e}")
        return None

    except Exception as e:
        print(f"[오류] 크롤링 실패: {e}")
        return None


# ============================================================
# 목차 캐릭터 추출
# ============================================================

def extract_toc_characters(source):
    """
    나무위키 목차에서 캐릭터 목록을 추출한다.

    예:
        #s-3.1 → 바람의 신・윈디
        #s-3.2 → 번개의 신・산디아

    특정 class 이름에는 의존하지 않는다.
    """

    characters = []
    seen = set()

    for match in TOC_PATTERN.finditer(source):
        section = match.group(1)
        raw_name = match.group(2)

        name = normalize_text(raw_name)

        # 목차 번호가 같이 들어온 경우 제거
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
# battlecats ID 추출
# ============================================================

def extract_battlecats_links(section_source):
    results = []

    for match in BATTLECATS_LINK_PATTERN.finditer(
        section_source
    ):
        url = html.unescape(match.group(1))
        link_text = normalize_text(match.group(2))

        # 광고/일반 링크 제외
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

def extract_character_ids(source):
    characters = extract_toc_characters(source)
    section_positions = extract_section_positions(source)

    print()
    print(
        f"[목차] 캐릭터 목록 : "
        f"{len(characters):,}개"
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

        # 다음 캐릭터 섹션 직전까지가 현재 캐릭터 영역
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

        # 같은 캐릭터 영역에서 동일 ID가 반복되는 경우 제거
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
                "id": link["id"],
            })

        print(
            f"[매칭] {section}. {name} "
            f"→ {len(seen_ids)}개 ID"
        )

    return characters, records


# ============================================================
# 결과 출력
# ============================================================

def print_results(characters, records):
    print()
    print("=" * 80)
    print("최종 결과")
    print("=" * 80)

    if not records:
        print("추출된 캐릭터 ID가 없습니다.")
        return

    current_section = None

    for record in records:
        section = record.get("section")

        # records에는 section을 출력용으로 별도 저장하지 않으므로
        # 이름 변경 시점을 기준으로 출력한다.
        if record["character_name"] != current_section:
            current_section = record["character_name"]

            print()
            print(
                f"[{current_section}]"
            )

        print(
            f"    {record['id']}"
        )

    print()
    print("-" * 80)
    print(
        f"목차 캐릭터 수 : "
        f"{len(characters):,}"
    )
    print(
        f"추출 ID 수     : "
        f"{len(records):,}"
    )


# ============================================================
# 실행
# ============================================================

def main():
    print("=" * 80)
    print("나무위키 캐릭터 ID 추출기")
    print("=" * 80)

    url = input(
        "크롤링할 URL을 입력하세요: "
    ).strip()

    if not url:
        print("[오류] URL이 입력되지 않았습니다.")
        return

    if not is_namu_url(url):
        print(
            "[경고] namu.wiki URL이 아닙니다."
        )
        print(
            "그래도 계속하려면 URL을 다시 입력하세요."
        )
        return

    source = crawl_html(url)

    if source is None:
        return

    start_time = time.time()

    print()
    print(
        "[분석] HTML에서 "
        "캐릭터명 + battlecats ID 추출 중..."
    )

    characters, records = extract_character_ids(
        source
    )

    print_results(
        characters,
        records
    )

    elapsed = time.time() - start_time

    print()
    print(
        f"[시간] HTML 분석 : {elapsed:.2f}초"
    )
    print(
        "[완료] 파일 저장 없이 "
        "메모리에서 처리했습니다."
    )


if __name__ == "__main__":
    main()
