import csv
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# 설정
# ============================================================

SOURCE_FILE = "source.html"

OUTPUT_CSV = "battlecats_links.csv"
OUTPUT_TXT = "battlecats_links.txt"

TARGET_DOMAIN = "battlecats-db.com"

# 목차 링크: #s-3.1, #s-3.2, #s-4.1 ...
TOC_PATTERN = re.compile(r"^#s-(\d+(?:\.\d+)+)$")

# 캐릭터 ID: 076-1, 076-2, ...
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
# 기본 유틸
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


def is_battlecats_url(url):
    if not url:
        return False

    try:
        host = urlparse(url).netloc.lower()
        return (
            host == TARGET_DOMAIN
            or host.endswith("." + TARGET_DOMAIN)
        )
    except Exception:
        return TARGET_DOMAIN in url.lower()


def is_character_id(text):
    return bool(
        text and ID_PATTERN.fullmatch(normalize_text(text))
    )


# ============================================================
# 문서 순서대로 모든 a 태그 가져오기
# ============================================================

def get_anchor_nodes(parser):
    return [
        node
        for node in parser.all_nodes
        if node.tag == "a"
    ]


# ============================================================
# 목차에서 캐릭터 목록 추출
# ============================================================

def extract_toc_characters(parser):
    """
    목차에 있는 #s-3.1, #s-3.2, #s-4.1 ...
    링크를 그대로 캐릭터 목록으로 사용한다.

    예:
        #s-3.1 -> 바람의 신・윈디
        #s-3.2 -> 번개의 신・산디아
    """

    characters = []

    for node in get_anchor_nodes(parser):
        href = node.attrs.get("href", "")
        match = TOC_PATTERN.fullmatch(href.strip())

        if not match:
            continue

        section_id = match.group(1)
        name = get_node_text(node)

        # 목차 번호는 href에 있으므로 텍스트에서 제거
        name = re.sub(
            r"^\s*\d+(?:\.\d+)*\.?\s*",
            "",
            name
        ).strip()

        if not name:
            continue

        characters.append({
            "section": section_id,
            "name": name,
            "node": node,
        })

    # 같은 section이 중복으로 들어오는 경우 제거
    unique = []
    seen = set()

    for item in characters:
        if item["section"] in seen:
            continue

        seen.add(item["section"])
        unique.append(item)

    return unique


# ============================================================
# 실제 본문의 heading 추출
# ============================================================

def find_section_headings(parser, sections):
    """
    목차의 #s-X 링크와 실제 본문의 id="s-X" heading을 연결한다.
    """

    section_ids = {
        item["section"]
        for item in sections
    }

    headings = {}

    for node in parser.all_nodes:
        if node.tag not in {
            "h1", "h2", "h3", "h4", "h5", "h6"
        }:
            continue

        # heading 내부 또는 자식 a의 id를 확인
        for child in [node] + node.children:
            node_id = child.attrs.get("id", "")

            if node_id in {
                f"s-{section}"
                for section in section_ids
            }:
                headings[node_id[2:]] = node
                break

    return headings


# ============================================================
# Node 순회
# ============================================================

def walk_nodes(node):
    yield node

    for child in node.children:
        yield from walk_nodes(child)


# ============================================================
# heading의 다음 섹션까지 탐색
# ============================================================

def document_order_nodes(parser):
    """
    DOM tree를 문서 순서대로 1차원 배열로 만든다.
    """

    result = []

    def walk(node):
        for child in node.children:
            result.append(child)
            walk(child)

    walk(parser.root)

    return result


def collect_battlecats_links_between_headings(
    ordered_nodes,
    heading_node,
    next_heading_node=None
):
    """
    현재 캐릭터 heading부터 다음 캐릭터 heading 직전까지
    battlecats-db 링크를 모두 찾는다.

    특정 class 이름에는 의존하지 않는다.
    """

    try:
        start_index = ordered_nodes.index(heading_node)
    except ValueError:
        return []

    if next_heading_node is not None:
        try:
            end_index = ordered_nodes.index(next_heading_node)
        except ValueError:
            end_index = len(ordered_nodes)
    else:
        end_index = len(ordered_nodes)

    links = []

    for node in ordered_nodes[start_index:end_index]:
        if node.tag != "a":
            continue

        href = node.attrs.get("href", "")

        if not is_battlecats_url(href):
            continue

        link_text = get_node_text(node)

        # 광고 등 battlecats 일반 링크는 제외
        if not is_character_id(link_text):
            continue

        links.append({
            "id": normalize_text(link_text),
            "url": href,
            "node": node,
        })

    return links


# ============================================================
# 최종 데이터 생성
# ============================================================

def build_records(parser):
    toc_characters = extract_toc_characters(parser)
    heading_map = find_section_headings(
        parser,
        toc_characters
    )

    ordered_nodes = document_order_nodes(parser)

    records = []

    for index, character in enumerate(toc_characters):
        section = character["section"]
        name = character["name"]

        heading = heading_map.get(section)

        if heading is None:
            print(
                f"[경고] 본문 heading을 찾지 못함: "
                f"{section} {name}"
            )
            continue

        # 다음 목차 항목의 본문 heading
        next_heading = None

        for next_character in toc_characters[index + 1:]:
            candidate = heading_map.get(
                next_character["section"]
            )

            if candidate is not None:
                next_heading = candidate
                break

        links = collect_battlecats_links_between_headings(
            ordered_nodes,
            heading,
            next_heading
        )

        for link in links:
            records.append({
                "character_name": name,
                "section": section,
                "id": link["id"],
                "url": link["url"],
            })

        print(
            f"[매칭] {section}. {name} "
            f"→ {len(links)}개 ID"
        )

    return records, toc_characters


# ============================================================
# 중복 제거
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

def print_results(records, toc_characters):
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
    print(f"목차 캐릭터 수 : {len(toc_characters):,}")
    print(f"추출 ID 수     : {len(records):,}")


# ============================================================
# CSV
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
# TXT
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
# source.html
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

    data = path.read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")

    return data.decode(
        "utf-8",
        errors="replace"
    )


# ============================================================
# 실행
# ============================================================

def main():
    start_time = time.time()

    print(f"[읽기] {SOURCE_FILE}")

    html = load_source()

    print(
        f"[정보] HTML 크기 : {len(html):,} 문자"
    )

    print("[분석] HTML 파싱 중...")

    parser = DOMParser()
    parser.feed(html)

    print(
        f"[분석] DOM 요소 : {len(parser.all_nodes):,}"
    )

    print(
        "[추출] 목차의 캐릭터 목록과 "
        "본문의 battlecats ID 연결 중..."
    )

    records, toc_characters = build_records(parser)

    records = deduplicate_records(records)

    print_results(
        records,
        toc_characters
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
