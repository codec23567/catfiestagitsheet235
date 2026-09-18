from pathlib import Path
import re

from bs4 import BeautifulSoup


INPUT_DIR = Path("extracted_sections")
OUTPUT_FILE = Path("unit_ids.txt")


def extract_unit_ids(html_file):
    """
    하나의 캐릭터 HTML에서 유닛 ID를 추출한다.

    예:
        ID → 043-1
        ID → 043-2
        ID → 043-3

    결과:
        ["043-1", "043-2", "043-3"]
    """

    html = html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    unit_ids = []

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td", recursive=False)

        if len(cells) < 2:
            continue

        label = cells[0].get_text(" ", strip=True)

        if label != "ID":
            continue

        value = cells[1].get_text(" ", strip=True)

        # 유닛 번호 형태:
        # 043-1
        # 319-2
        # 123-3
        match = re.search(r"\b(\d+)-(\d+)\b", value)

        if not match:
            continue

        unit_id = f"{match.group(1)}-{match.group(2)}"

        if unit_id not in unit_ids:
            unit_ids.append(unit_id)

    return unit_ids


def main():
    if not INPUT_DIR.exists():
        print(f"폴더가 없습니다: {INPUT_DIR}")
        return

    html_files = sorted(
        INPUT_DIR.glob("s-*.html")
    )

    if not html_files:
        print("추출된 HTML 파일이 없습니다.")
        return

    print()
    print("=" * 70)
    print("유닛 번호 추출")
    print("=" * 70)
    print()

    all_results = []

    for html_file in html_files:

        unit_ids = extract_unit_ids(html_file)

        print(f"{html_file.name}")

        if not unit_ids:
            print("  → 유닛 번호를 찾지 못함")
            print()
            continue

        for unit_id in unit_ids:
            print(f"  → {unit_id}")

            all_results.append({
                "file": html_file.name,
                "unit_id": unit_id,
            })

        print()

    # 결과 저장
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        for result in all_results:
            f.write(
                f"{result['file']}\t"
                f"{result['unit_id']}\n"
            )

    print("=" * 70)
    print("완료")
    print("=" * 70)
    print(f"총 유닛 수: {len(all_results)}")
    print(f"결과 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
