from bs4 import BeautifulSoup


HTML_FILE = "crawled.html"


def load_html():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


def find_characters(soup):
    characters = []

    for title in soup.select("h4 span[id]"):
        if "[편집]" not in title.get_text():
            continue

        name = title.get_text(" ", strip=True)
        name = name.replace("[편집]", "").strip()

        characters.append({
            "name": name,
            "title": title,
        })

    return characters


def find_detail_table(title):
    # 현재 캐릭터 제목 이후에 나오는 table 중
    # ID 항목을 가진 테이블을 상세 테이블로 사용
    for table in title.find_all_next("table", class_="msqFhi2m"):
        labels = []

        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)

            if tds:
                labels.append(tds[0].get_text(" ", strip=True))

        if "ID" in labels:
            return table

    return None


def main():
    soup = load_html()
    characters = find_characters(soup)

    if not characters:
        print("캐릭터를 찾지 못했습니다.")
        return

    print()
    print("===== 캐릭터 목록 =====")
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

    selected = characters[choice - 1]

    print()
    print("=" * 80)
    print(f"선택한 캐릭터: {selected['name']}")
    print("=" * 80)

    detail_table = find_detail_table(selected["title"])

    if detail_table is None:
        print("캐릭터 상세 영역을 찾지 못했습니다.")
        return

    # 선택한 캐릭터의 상세 HTML만 출력
    print()
    print(str(detail_table))


if __name__ == "__main__":
    main()
