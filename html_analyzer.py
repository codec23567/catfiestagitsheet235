import csv
import re
import time
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


# ============================================================
# 설정
# ============================================================

SOURCE_FILE = "source.html"

# 결과 파일
OUTPUT_CSV = "battlecats_links.csv"
OUTPUT_TXT = "battlecats_links.txt"

# battlecats-db 링크로 인정할 도메인
TARGET_DOMAIN = "battlecats-db.com"

# ID 형식
# 예: 076-1, 076-2, 123-1
ID_PATTERN = re.compile(r"^\d+-\d+$")


# ============================================================
# DOM Node
# ============================================================

class Node:
    def __init__(self, tag=None, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []
        self.text_parts = []

    def add_text(self, text):
        self.text_parts.append(text)


# ============================================================
# HTML Parser
# ============================================================

class DOMParser(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr",
        "img", "input", "link", "meta", "param",
        "source", "track", "wbr"
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.root = Node("document")
        self.current = self.root
        self.all_nodes = []

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)

        self.current.children.append(node)
        self.all_nodes.append(node)

        if tag not in self.VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.current)

        self.current.children.append(node)
        self.all_nodes.append(node)

    def handle_endtag(self, tag):
        current = self.current

        while current is not self.root:
            if current.tag == tag:
                self.current = current.parent
                return

            current = current.parent

    def handle_data(self, data):
        if data.strip():
            self.current.add_text(data)


# ============================================================
# 텍스트 처리
# ============================================================

def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def get_node_text(node):
    parts = []

    def walk(current):
        for text in current.text_parts:
            if text.strip():
                parts.append(text)

        for child in current.children:
            walk(child)

    walk(node)

    return normalize_text(" ".join(parts))


# ============================================================
# battlecats 링크 찾기
# ============================================================

def is_target_url(url):
    if not url:
        return False

    return TARGET_DOMAIN in url.lower()


def extract_links(parser):
    """
    source.html 전체에서 battlecats-db 링크를 찾는다.

    결과:
        [
            {
                "id": "076-1",
                "url": "https://battlecats-db.com/unit/076.html",
                "link_text": "076-1",
                "node": Node(...)
            },
            ...
        ]
    """

    results = []

    for node in parser.all_nodes:
        if node.tag != "a":
            continue

        href = node.attrs.get("href", "")

        if not is_target_url(href):
            continue

        link_text = get_node_text(node)

        # 실제 캐릭터 ID가 링크 텍스트인 경우를 우선 처리
        character_id = None

        if ID_PATTERN.match(link_text):
            character_id = link_text

        results.append({
            "id": character_id,
            "url": href,
            "link_text": link_text,
            "node": node,
        })

    return results


# ============================================================
# 캐릭터 이름 추정
# ============================================================

def find_nearest_character_name(node):
    """
    battlecats 링크에서 가까운 부모 영역을 따라가면서
    캐릭터 이름을 찾는다.

    우선순위:
    1. 가장 가까운 h1~h6
    2. 가까운 부모 영역의 텍스트 중 후보
    3. 없으면 빈 문자열

    현재 페이지 구조에 특정 class 이름을 사용하지 않는다.
    """

    current = node.parent

    for _ in range(20):
        if current is None:
            break

        # 가까운 heading
        if current.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = get_node_text(current)

            if text:
                # "3.1. 바람의 신・윈디" 같은 경우
                text = re.sub(
                    r"^\s*\d+(?:\.\d+)*\.?\s*",
                    "",
                    text
                )

                return text.strip()

        current = current.parent

    return ""


# ============================================================
# 더 정확한 캐릭터 영역 추정
# ============================================================

def find_character_context(node):
    """
    링크 주변에서 캐릭터명 후보를 찾는다.

    나무위키 구조가 페이지마다 조금 달라질 수 있기 때문에
    특정 class 이름에 의존하지 않고 heading / 부모 구조를 사용한다.
    """

    # 먼저 heading을 찾는다.
    heading_name = find_nearest_character_name(node)

    if heading_name:
        return heading_name

    # heading이 바로 부모 구조에 없는 경우,
    # 가까운 부모들의 텍스트에서 너무 큰 영역을 제외하고 후보를 찾는다.
    current = node.parent

    for _ in range(10):
        if current is None:
            break

        text = get_node_text(current)

        if 0 < len(text) <= 500:
            lines = [
                normalize_text(x)
                for x in re.split(r"[\n\r]+", text)
                if normalize_text(x)
            ]

            if lines:
                # ID 자체가 아닌 첫 번째 의미 있는 텍스트를 후보로 사용
                for line in lines:
                    if not ID_PATTERN.match(line):
                        if "battlecats-db.com" not in line:
                            return line

        current = current.parent

    return ""


# ============================================================
# 중복 제거
# ============================================================

def deduplicate_links(results):
    """
    동일한 ID + URL은 한 번만 남긴다.
    """

    seen = set()
    unique = []

    for item in results:
        key = (
            item["id"] or "",
            item["url"]
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# ============================================================
# 결과 정리
# ============================================================

def build_records(results):
    records = []

    for item in results:
        character_id = item["id"]
        url = item["url"]
        link_text = item["link_text"]

        character_name = find_character_context(
            item["node"]
        )

        # 링크 텍스트가 ID가 아닌 경우에도 기록은 남긴다.
        records.append({
            "character_name": character_name,
            "id": character_id or link_text,
            "url": url,
        })

    return records


# ============================================================
# 화면 출력
# ============================================================

def print_results(records):
    print()
    print("=" * 80)
    print("battlecats-db 캐릭터 링크")
    print("=" * 80)

    if not records:
        print("battlecats-db 링크를 찾지 못했습니다.")
        return

    for index, record in enumerate(records, start=1):
        name = record["character_name"] or "(캐릭터명 확인 필요)"

        print(
            f"[{index:3}] "
            f"{name} | "
            f"{record['id']}"
        )

        print(
            f"      {record['url']}"
        )

    print()
    print("-" * 80)
    print(f"총 링크 수 : {len(records):,}")

    valid_ids = [
        record for record in records
        if ID_PATTERN.match(record["id"])
    ]

    print(f"ID 형식 확인 : {len(valid_ids):,}")


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
                "id",
                "url",
            ]
        )

        writer.writeheader()
        writer.writerows(records)

    print(
        f"[저장] CSV : {OUTPUT_CSV}"
    )


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
                f"{record['id']}\t"
                f"{record['url']}\n"
            )

    print(
        f"[저장] TXT : {OUTPUT_TXT}"
    )


# ============================================================
# 페이지별 캐릭터 요약
# ============================================================

def print_group_summary(records):
    """
    ID의 앞부분을 기준으로 묶는다.

    예:
        076-1
        076-2
        076-3

    -> 076 그룹
    """

    groups = defaultdict(list)

    for record in records:
        match = re.match(
            r"^(\d+)-(\d+)$",
            record["id"]
        )

        if not match:
            continue

        unit_number = match.group(1)
        groups[unit_number].append(record)

    print()
    print("=" * 80)
    print("캐릭터 번호별 진화 형태 요약")
    print("=" * 80)

    for unit_number, items in groups.items():
        ids = [item["id"] for item in items]

        names = [
            item["character_name"]
            for item in items
            if item["character_name"]
        ]

        name = names[0] if names else "(캐릭터명 확인 필요)"

        print(
            f"{unit_number} | "
            f"{name} | "
            f"{', '.join(ids)}"
        )

    print()
    print(f"캐릭터 그룹 수 : {len(groups):,}")


# ============================================================
# source.html 읽기
# ============================================================

def load_source():
    path = Path(SOURCE_FILE)

    if not path.exists():
        print(
            f"[오류] {SOURCE_FILE} 파일이 없습니다."
        )
        print(
            "html_crawler.py를 먼저 실행하세요."
        )
        raise SystemExit(1)

    try:
        data = path.read_bytes()

        if data.startswith(b"\xef\xbb\xbf"):
            return data.decode(
                "utf-8-sig"
            )

        return data.decode(
            "utf-8",
            errors="replace"
        )

    except Exception as e:
        print(
            f"[오류] HTML 읽기 실패: {e}"
        )
        raise SystemExit(1)


# ============================================================
# 실행
# ============================================================

def main():
    start_time = time.time()

    print(
        f"[읽기] {SOURCE_FILE}"
    )

    html = load_source()

    print(
        f"[정보] HTML 크기 : {len(html):,} 문자"
    )

    print(
        "[분석] HTML 파싱 중..."
    )

    parser = DOMParser()
    parser.feed(html)

    print(
        f"[분석] DOM 요소 : {len(parser.all_nodes):,}"
    )

    print(
        "[검색] battlecats-db 링크 검색 중..."
    )

    results = extract_links(parser)

    print(
        f"[검색] 발견 : {len(results):,}개"
    )

    results = deduplicate_links(results)

    print(
        f"[정리] 중복 제거 후 : {len(results):,}개"
    )

    records = build_records(results)

    print_results(records)
    print_group_summary(records)

    save_csv(records)
    save_txt(records)

    elapsed = time.time() - start_time

    print()
    print(
        f"[완료] 전체 소요 : {elapsed:.2f}초"
    )


if __name__ == "__main__":
    main()
