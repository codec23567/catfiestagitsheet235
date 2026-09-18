import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


# -------------------------------------------------
# 설정
# -------------------------------------------------

SOURCE_FILE = "source.html"

# 검색 결과에서 주변 텍스트를 표시할 최대 문자 수
TEXT_PREVIEW_LENGTH = 300

# 검색된 요소에서 부모를 몇 단계까지 보여줄지
MAX_ANCESTORS = 15


# -------------------------------------------------
# HTML DOM 파서
# -------------------------------------------------

class Node:
    def __init__(self, tag=None, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []
        self.text_parts = []

    def add_text(self, text):
        self.text_parts.append(text)

    def text(self):
        return " ".join(
            part.strip()
            for part in self.text_parts
            if part.strip()
        ).strip()


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
        self.tag_counter = Counter()
        self.class_counter = Counter()
        self.id_counter = Counter()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)

        self.current.children.append(node)
        self.all_nodes.append(node)

        self.tag_counter[tag] += 1

        classes = node.attrs.get("class", "")
        for class_name in classes.split():
            if class_name:
                self.class_counter[class_name] += 1

        node_id = node.attrs.get("id")
        if node_id:
            self.id_counter[node_id] += 1

        if tag not in self.VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.current)

        self.current.children.append(node)
        self.all_nodes.append(node)

        self.tag_counter[tag] += 1

        classes = node.attrs.get("class", "")
        for class_name in classes.split():
            if class_name:
                self.class_counter[class_name] += 1

        node_id = node.attrs.get("id")
        if node_id:
            self.id_counter[node_id] += 1

    def handle_endtag(self, tag):
        node = self.current

        while node is not self.root:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        if data.strip():
            self.current.add_text(data)

            # 텍스트는 모든 조상에게 누적하지 않고,
            # 검색 시 별도로 자식 텍스트를 계산한다.


# -------------------------------------------------
# 유틸리티
# -------------------------------------------------

def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def get_node_text(node):
    parts = []

    def walk(current):
        for part in current.text_parts:
            if part.strip():
                parts.append(part)

        for child in current.children:
            walk(child)

    walk(node)

    return normalize_text(" ".join(parts))


def get_direct_text(node):
    return normalize_text(" ".join(node.text_parts))


def node_description(node):
    if node is None:
        return "(없음)"

    result = node.tag

    node_id = node.attrs.get("id")
    classes = node.attrs.get("class")

    if node_id:
        result += f"#{node_id}"

    if classes:
        class_names = classes.split()
        result += "".join(f".{name}" for name in class_names[:5])

        if len(class_names) > 5:
            result += f"...(+{len(class_names) - 5})"

    return result


def short_text(text, length=TEXT_PREVIEW_LENGTH):
    text = normalize_text(text)

    if len(text) <= length:
        return text

    return text[:length] + "..."


def node_depth(node):
    depth = 0
    current = node.parent

    while current is not None:
        depth += 1
        current = current.parent

    return depth


def element_child_count(node):
    return len(node.children)


# -------------------------------------------------
# 기본 정보
# -------------------------------------------------

def print_basic_info(html, parser):
    print()
    print("=" * 70)
    print("HTML 기본 정보")
    print("=" * 70)

    print(f"파일              : {SOURCE_FILE}")
    print(f"파일 크기         : {Path(SOURCE_FILE).stat().st_size:,} bytes")
    print(f"HTML 문자 수      : {len(html):,}")
    print(f"태그 수           : {len(parser.all_nodes):,}")

    title_nodes = [
        node for node in parser.all_nodes
        if node.tag == "title"
    ]

    if title_nodes:
        print(f"TITLE             : {short_text(get_node_text(title_nodes[0]), 200)}")
    else:
        print("TITLE             : 없음")


# -------------------------------------------------
# 태그 통계
# -------------------------------------------------

def print_tag_stats(parser):
    print()
    print("=" * 70)
    print("주요 태그 통계")
    print("=" * 70)

    for tag, count in parser.tag_counter.most_common(30):
        print(f"{tag:15} : {count:,}")


# -------------------------------------------------
# class 통계
# -------------------------------------------------

def print_class_stats(parser):
    print()
    print("=" * 70)
    print("class 통계 TOP 50")
    print("=" * 70)

    if not parser.class_counter:
        print("class 없음")
        return

    for class_name, count in parser.class_counter.most_common(50):
        print(f"{class_name:40} : {count:,}")


# -------------------------------------------------
# id 통계
# -------------------------------------------------

def print_id_stats(parser):
    print()
    print("=" * 70)
    print("id 목록")
    print("=" * 70)

    if not parser.id_counter:
        print("id 없음")
        return

    for node_id, count in parser.id_counter.most_common(100):
        print(f"{node_id:50} : {count:,}")


# -------------------------------------------------
# 텍스트 검색
# -------------------------------------------------

def search_text(parser, keyword):
    keyword_normalized = normalize_text(keyword).lower()

    results = []

    for node in parser.all_nodes:
        text = get_node_text(node)

        if not text:
            continue

        if keyword_normalized in text.lower():
            results.append(node)

    return results


def print_ancestor_chain(node):
    print()
    print("부모 구조")
    print("-" * 70)

    current = node

    for level in range(MAX_ANCESTORS):
        if current is None:
            break

        text = get_node_text(current)

        print(
            f"[{level}] "
            f"{node_description(current)} "
            f"| 자식={element_child_count(current)} "
            f"| 전체텍스트={len(text):,}자"
        )

        if text:
            print(f"     텍스트: {short_text(text, 180)}")

        current = current.parent


def print_search_results(results, keyword):
    print()
    print("=" * 70)
    print(f"텍스트 검색 결과: {keyword}")
    print("=" * 70)

    if not results:
        print("검색 결과가 없습니다.")
        return

    # 같은 텍스트가 여러 부모에서 검색되는 문제를 줄이기 위해
    # 가장 작은 요소부터 우선 표시한다.
    results = sorted(
        results,
        key=lambda node: len(get_node_text(node))
    )

    print(f"검색된 요소 수: {len(results):,}")
    print()

    # 지나치게 많은 중복 부모 요소는 처음 20개까지만 표시
    for index, node in enumerate(results[:20], start=1):
        text = get_node_text(node)

        print("-" * 70)
        print(f"[검색 결과 {index}]")
        print(f"태그       : {node_description(node)}")
        print(f"깊이       : {node_depth(node)}")
        print(f"자식 수    : {element_child_count(node)}")
        print(f"텍스트 길이: {len(text):,}")
        print(f"텍스트     : {short_text(text)}")

        print_ancestor_chain(node)


# -------------------------------------------------
# 제목 태그 구조
# -------------------------------------------------

def print_headings(parser):
    print()
    print("=" * 70)
    print("문서 제목 구조 (h1 ~ h6)")
    print("=" * 70)

    headings = [
        node for node in parser.all_nodes
        if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
    ]

    if not headings:
        print("h1~h6 태그가 없습니다.")
        return

    for node in headings:
        text = get_node_text(node)

        if not text:
            continue

        print(
            f"{node.tag:3} | "
            f"{short_text(text, 120)} | "
            f"{node_description(node)}"
        )


# -------------------------------------------------
# 테이블 정보
# -------------------------------------------------

def print_tables(parser):
    print()
    print("=" * 70)
    print("TABLE 정보")
    print("=" * 70)

    tables = [
        node for node in parser.all_nodes
        if node.tag == "table"
    ]

    if not tables:
        print("table 없음")
        return

    print(f"table 수: {len(tables):,}")
    print()

    for index, table in enumerate(tables[:30], start=1):
        text = get_node_text(table)

        tr_count = sum(
            1 for node in table.children
            if node.tag == "tr"
        )

        print(
            f"[{index}] "
            f"{node_description(table)} | "
            f"텍스트={len(text):,}자 | "
            f"직접 tr={tr_count}"
        )

        print(f"     {short_text(text, 200)}")


# -------------------------------------------------
# 분석기 실행
# -------------------------------------------------

def load_source():
    path = Path(SOURCE_FILE)

    if not path.exists():
        print(f"[오류] {SOURCE_FILE} 파일이 없습니다.")
        print("html_crawler.py를 먼저 실행하세요.")
        raise SystemExit(1)

    try:
        # 크롤러가 저장한 원본 bytes를 그대로 읽은 후
        # HTMLParser가 처리할 수 있도록 디코딩한다.
        data = path.read_bytes()

        # 일반적인 HTML 인코딩 우선순위.
        # 필요하면 나중에 사이트별 인코딩 처리를 추가할 수 있다.
        if data.startswith(b"\xef\xbb\xbf"):
            html = data.decode("utf-8-sig")
        else:
            html = data.decode("utf-8", errors="replace")

        return html

    except Exception as e:
        print(f"[오류] HTML 읽기 실패: {e}")
        raise SystemExit(1)


def main():
    html = load_source()

    print("[분석] source.html 읽는 중...", flush=True)

    parser = DOMParser()

    start_time = __import__("time").time()

    parser.feed(html)

    parse_time = __import__("time").time() - start_time

    print(f"[분석] DOM 파싱 완료 : {parse_time:.2f}초", flush=True)

    print_basic_info(html, parser)
    print_tag_stats(parser)
    print_class_stats(parser)
    print_id_stats(parser)
    print_headings(parser)
    print_tables(parser)

    while True:
        print()
        print("=" * 70)
        print("텍스트 검색")
        print("=" * 70)
        print("검색할 텍스트를 입력하세요.")
        print("종료하려면 Enter만 누르세요.")

        keyword = input("> ").strip()

        if not keyword:
            break

        results = search_text(parser, keyword)

        print_search_results(results, keyword)

    print()
    print("[완료]")


if __name__ == "__main__":
    main()
