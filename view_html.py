from pathlib import Path
import re

from bs4 import BeautifulSoup


HTML_FILE = Path("crawled.html")


def load_html():
    if not HTML_FILE.exists():
        print(f"HTML 파일이 없습니다: {HTML_FILE}")
        return None

    with HTML_FILE.open("r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


def normalize_url(url):
    """
    나무위키의 //i.namu.wiki/... 형태를
    https://i.namu.wiki/... 형태로 변환한다.
    """
    if not url:
        return None

    url = url.strip()

    if url.startswith("//"):
        return "https:" + url

    return url


def is_character_heading(tag):
    """
    캐릭터 제목인지 확인한다.

    현재 확인된 구조:
        <h4>
            ...
            <span id="무녀공주 미타마">
                ...
                [편집]
            </span>
        </h4>
    """
    if tag.name != "h4":
        return False

    text = tag.get_text(" ", strip=True)

    return "[편집]" in text


def get_character_name(heading):
    """
    캐릭터 제목 h4에서 캐릭터 이름을 가져온다.
    """
    span = heading.find("span", id=True)

    if span:
        name = span.get_text(" ", strip=True)
    else:
        name = heading.get_text(" ", strip=True)

    name = name.replace("[편집]", "").strip()

    # 앞쪽 번호가 제목에 포함되는 경우 제거
    # 예:
    # "2.1.2. 무녀공주 미타마"
    name = re.sub(r"^\d+(?:\.\d+)*\.\s*", "", name)

    return name.strip()


def get_character_headings(soup):
    """
    페이지에서 캐릭터 제목들을 찾는다.
    """
    characters = []

    for heading in soup.find_all("h4"):
        if not is_character_heading(heading):
            continue

        name = get_character_name(heading)

        if not name:
            continue

        characters.append({
            "name": name,
            "heading": heading,
        })

    return characters


def get_tables_for_character(heading, next_heading=None):
    """
    현재 캐릭터 제목과 다음 캐릭터 제목 사이에 있는
    상세 테이블들을 찾는다.

    특정 캐릭터의 ID나 이미지 URL을 하드코딩하지 않는다.
    """

    tables = []

    # 현재 heading 이후의 table들을 순서대로 확인
    for element in heading.find_all_next(["table", "h4"]):

        # 다음 캐릭터 제목을 만나면 종료
        if element.name == "h4":
            if next_heading is None or element is next_heading:
                break

        if element.name != "table":
            continue

        # 캐릭터 상세 테이블인지 확인
        if is_character_detail_table(element):
            tables.append(element)

    return tables


def is_character_detail_table(table):
    """
    캐릭터 상세 테이블인지 판단한다.

    현재 확인된 구조에서는
    'ID' 라벨과 캐릭터 이미지가 함께 존재한다.

    class 이름 하나에만 의존하지 않는다.
    """

    text = table.get_text(" ", strip=True)

    # ID 정보가 있어야 함
    if "ID" not in text:
        return False

    # 캐릭터 이미지가 있어야 함
    for img in table.find_all("img"):
        alt = img.get("alt", "")

        if "냥코 대전쟁 캐릭터" in alt:
            return True

    return False


def get_value_by_label(table, label):
    """
    상세 테이블에서

        <td>ID</td>
        <td>319-1</td>

    같은 구조를 찾아 값을 반환한다.
    """

    for tr in table.find_all("tr"):
        cells = tr.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        first_text = cells[0].get_text(" ", strip=True)

        if first_text == label:
            return cells[1].get_text(" ", strip=True)

    return None


def get_character_images(table):
    """
    현재 형태 테이블에 포함된 캐릭터 이미지를 찾는다.

    예:
        alt="냥코 대전쟁 캐릭터 319-1"

    src와 data-src를 모두 고려한다.
    """

    images = []

    for img in table.find_all("img"):
        alt = img.get("alt", "")

        if "냥코 대전쟁 캐릭터" not in alt:
            continue

        # alt에서 캐릭터 ID 추출
        match = re.search(
            r"냥코\s*대전쟁\s*캐릭터\s+(\d+-\d+)",
            alt
        )

        if not match:
            continue

        character_id = match.group(1)

        # 실제 이미지 주소
        image_url = (
            img.get("data-src")
            or img.get("src")
        )

        image_url = normalize_url(image_url)

        if not image_url:
            continue

        images.append({
            "id": character_id,
            "url": image_url,
            "alt": alt,
        })

    return images


def get_form_name(table, character_id):
    """
    이미지가 들어있는 행에서 형태 이름을 찾는다.

    현재 구조는 대략:

        <tr>
            <td>
                <img ...>
            </td>
            <td>
                무녀공주 미타마
                巫女姫ミタマ
                Miko Mitama
            </td>
        </tr>

    형태이므로 이미지 ID와 같은 행의 두 번째 td를 확인한다.
    """

    for img in table.find_all("img"):
        alt = img.get("alt", "")

        if character_id not in alt:
            continue

        tr = img.find_parent("tr")

        if tr is None:
            continue

        cells = tr.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        name_text = cells[1].get_text(" ", strip=True)

        if name_text:
            return name_text

    return None


def extract_form_data(table):
    """
    하나의 캐릭터 형태 테이블에서 정보를 추출한다.
    """

    character_id = get_value_by_label(table, "ID")

    images = get_character_images(table)

    # ID 정보가 테이블에 없으면 이미지 ID를 이용
    if not character_id and images:
        character_id = images[0]["id"]

    form_name = None

    if character_id:
        form_name = get_form_name(table, character_id)

    # 형태 번호 추출
    form_number = None

    if character_id:
        match = re.search(r"-(\d+)$", character_id)

        if match:
            form_number = int(match.group(1))

    return {
        "id": character_id,
        "form": form_number,
        "name": form_name,
        "images": images,
        "max_level": get_value_by_label(table, "최대 Lv"),
        "update": get_value_by_label(table, "업데이트"),
        "obtain": get_value_by_label(table, "입수 방법"),
    }


def extract_character_data(characters, index):
    """
    선택한 캐릭터 하나의 데이터를 추출한다.
    """

    current = characters[index]

    # 다음 캐릭터 제목
    if index + 1 < len(characters):
        next_heading = characters[index + 1]["heading"]
    else:
        next_heading = None

    tables = get_tables_for_character(
        current["heading"],
        next_heading
    )

    forms = []

    for table in tables:
        form = extract_form_data(table)

        # 완전히 의미 없는 테이블은 제외
        if not form["id"] and not form["images"]:
            continue

        forms.append(form)

    return {
        "name": current["name"],
        "forms": forms,
    }


def print_character(character):
    """
    선택한 캐릭터 정보를 보기 좋게 출력한다.
    """

    print()
    print("=" * 80)
    print(f"캐릭터: {character['name']}")
    print("=" * 80)

    if not character["forms"]:
        print()
        print("캐릭터 형태 정보를 찾지 못했습니다.")
        return

    for form in character["forms"]:
        print()
        print("-" * 80)

        if form["form"] is not None:
            print(f"[제{form['form']}형태]")
        else:
            print("[형태]")

        print("-" * 80)

        print(f"이름: {form['name'] or '(찾지 못함)'}")
        print(f"ID: {form['id'] or '(찾지 못함)'}")

        if form["max_level"]:
            print(f"최대 Lv: {form['max_level']}")

        if form["update"]:
            print(f"업데이트: {form['update']}")

        if form["obtain"]:
            print(f"입수 방법: {form['obtain']}")

        print()

        if form["images"]:
            print("이미지:")

            for image in form["images"]:
                print(f"  ID: {image['id']}")
                print(f"  URL: {image['url']}")
        else:
            print("이미지: 찾지 못함")

    print()
    print("=" * 80)


def main():
    soup = load_html()

    if soup is None:
        return

    characters = get_character_headings(soup)

    if not characters:
        print("캐릭터를 찾지 못했습니다.")
        return

    print()
    print("=" * 80)
    print("캐릭터 목록")
    print("=" * 80)
    print()

    for i, character in enumerate(characters, 1):
        print(f"{i}. {character['name']}")

    print()

    while True:
        try:
            choice = int(input("번호를 선택하세요: "))

            if 1 <= choice <= len(characters):
                break

            print(f"1~{len(characters)} 사이의 번호를 입력하세요.")

        except ValueError:
            print("번호를 입력하세요.")

    character = extract_character_data(
        characters,
        choice - 1
    )

    print_character(character)


if __name__ == "__main__":
    main()
