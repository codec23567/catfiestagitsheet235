import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("extracted_sections")


def fetch_html(url: str) -> str:
    """
    URL의 HTML을 requests로 가져온다.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    }

    print(f"[접속] {url}")

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    # requests가 알아낸 인코딩 사용
    response.encoding = response.apparent_encoding

    html = response.text

    print(f"[완료] HTML 가져오기")
    print(f"[크기] {len(html):,} 문자")

    return html


def find_character_links(soup: BeautifulSoup):
    """
    목차에서 캐릭터 항목을 찾는다.

    현재 확인한 페이지 구조:

        3.1. 고양이 아이스
        3.2. 고양이 머신
        ...
        3.12. 변신소녀 단
        4.1. 원더 모모코

    목차 링크는:

        <a href="#s-3.1">3.1.</a>

    형태이다.

    따라서 실제 캐릭터 이름은 링크 주변의 텍스트에서 가져오고,
    이동 대상은 href를 이용한다.
    """

    characters = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "")

        # #s-3.1
        # #s-3.2
        # ...
        # #s-4.1
        match = re.fullmatch(r"#s-(3\.\d+|4\.1)", href)

        if not match:
            continue

        section_number = match.group(1)

        # 목차의 <a>는 "3.1." 부분만 가지고 있으므로
        # 부모 요소에서 전체 텍스트를 가져온다.
        parent = a.parent

        if parent is not None:
            text = parent.get_text(" ", strip=True)
        else:
            text = a.get_text(" ", strip=True)

        characters.append({
            "section": section_number,
            "href": href,
            "target_id": href[1:],
            "text": text,
        })

    # 같은 링크가 여러 곳에 존재할 경우 중복 제거
    unique = []
    seen = set()

    for character in characters:

        key = character["target_id"]

        if key in seen:
            continue

        seen.add(key)
        unique.append(character)

    return unique


def find_target(soup: BeautifulSoup, target_id: str):
    """
    목차 href가 가리키는 실제 HTML 위치를 찾는다.

    예:

        href="#s-3.1"

        ↓

        id="s-3.1"
    """

    target = soup.find(id=target_id)

    return target


def extract_section(target):
    """
    캐릭터 제목부터 다음 같은 단계의 제목이 나오기 전까지
    HTML을 추출한다.

    우선 현재 target 주변 구조를 그대로 저장한다.
    """

    # target이 <a id="s-3.1"> 같은 경우
    heading = target

    # target이 h4 안에 들어있는 경우
    if target.name != "h4":
        parent_heading = target.find_parent("h4")

        if parent_heading is not None:
            heading = parent_heading

    parts = []

    # heading부터 다음 h4 전까지 형제 요소를 가져온다.
    current = heading

    while current is not None:

        # 다음 h4가 나오면 현재 캐릭터 영역 종료
        if (
            current is not heading
            and current.name == "h4"
        ):
            break

        parts.append(str(current))

        current = current.find_next_sibling()

    return "\n".join(parts)


def save_section(section_number, html):
    """
    캐릭터 섹션 HTML을 파일로 저장한다.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = f"s-{section_number}.html"

    output_file = OUTPUT_DIR / filename

    output_file.write_text(
        html,
        encoding="utf-8"
    )

    return output_file


def main():
    url = input("크롤링할 URL : ").strip()

    if not url:
        print("URL이 입력되지 않았습니다.")
        return

    try:
        html = fetch_html(url)

    except requests.RequestException as e:
        print()
        print("[오류] 페이지를 가져오지 못했습니다.")
        print(e)
        return

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print()
    print("[진행] 목차 분석")

    characters = find_character_links(soup)

    if not characters:
        print("[실패] 캐릭터 목차를 찾지 못했습니다.")
        return

    print()
    print("=" * 70)
    print("찾은 캐릭터")
    print("=" * 70)

    for i, character in enumerate(characters, 1):
        print(
            f"{i}. "
            f"{character['section']} "
            f"{character['text']} "
            f"→ #{character['target_id']}"
        )

    print()
    print(f"총 {len(characters)}개")
    print()

    print("[진행] 캐릭터 HTML 추출")

    success = 0

    for character in characters:

        target = find_target(
            soup,
            character["target_id"]
        )

        if target is None:
            print(
                f"[실패] "
                f"{character['section']} "
                f"→ id='{character['target_id']}' 없음"
            )
            continue

        section_html = extract_section(target)

        if not section_html.strip():
            print(
                f"[실패] "
                f"{character['section']} "
                f"→ HTML 없음"
            )
            continue

        output_file = save_section(
            character["section"],
            section_html
        )

        print(
            f"[완료] "
            f"{character['section']} "
            f"→ {output_file}"
        )

        success += 1

    print()
    print("=" * 70)
    print("작업 완료")
    print("=" * 70)
    print(f"성공: {success}")
    print(f"실패: {len(characters) - success}")
    print(f"저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
