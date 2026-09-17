import requests
import re
import time
import sys


def extract_namu_section_images(url):

    total_start = time.time()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=30)

    print(f"[응답] 상태={response.status_code}, 바이트={len(response.content)}", flush=True)

    html = response.text

    # -------------------------
    # h4 제목(캐릭터 단위) 위치 찾기
    # -------------------------
    heading_regex = re.compile(r'<h4[^>]*>(.*?)</h4>', re.S)

    headings = []

    for m in heading_regex.finditer(html):
        raw_title = re.sub('<[^>]+>', '', m.group(1)).strip()
        # "2.1.1. 요수 가오[편집]" -> "요수 가오"
        title = re.sub(r'^[\d.]+\s*', '', raw_title)
        title = re.sub(r'(&#91;편집&#93;|\[편집\])\s*$', '', title).strip()

        headings.append({
            "title": title,
            "start": m.end()   # 제목이 끝나는 지점부터 본문 시작
        })

    print(f"[결과] h4 제목 수 : {len(headings)}", flush=True)

    # -------------------------
    # 구간 경계용: h2/h3/h4 전부의 "여는 태그 시작 위치" 수집
    # (h4끼리만 자르면, 카테고리에 h4가 하나뿐일 때
    #  다음 대분류까지 통째로 삼켜버리는 문제가 생김)
    # -------------------------
    all_heading_starts = [
        m.start() for m in re.finditer(r'<h[2-4][^>]*>', html)
    ]
    all_heading_starts.sort()

    # -------------------------
    # 이미지 정규식 (기존과 동일)
    # -------------------------
    img_regex = re.compile(
        r'(?:data-src|src)=[\'"](//i\.namu\.wiki/i/[^\'"]+\.(?:webp|jpg|jpeg|png|gif))[\'"]',
        re.IGNORECASE
    )

    results = []

    for i, h in enumerate(headings):

        section_start = h["start"]

        # section_start 이후에 나오는 가장 가까운 h2/h3/h4 시작점을 찾음
        section_end = len(html)
        for pos in all_heading_starts:
            if pos > section_start:
                section_end = pos
                break

        section_html = html[section_start:section_end]

        matches = img_regex.findall(section_html)

        seen = set()
        images = []
        for src in matches:
            if src in seen:
                continue
            seen.add(src)
            images.append("https:" + src)

        second_image = images[1] if len(images) > 1 else None

        results.append({
            "title": h["title"],
            "image_count_in_section": len(images),
            "second_image": second_image
        })

    print(f"[시간] 전체 : {time.time() - total_start:.2f}초", flush=True)

    return results


if __name__ == "__main__":

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("테스트할 나무위키 URL 입력: ").strip()

    results = extract_namu_section_images(test_url)

    print("\n----- 제목별 두 번째 이미지 -----")
    for r in results:
        print(f'[{r["title"]}] (구간 내 이미지 {r["image_count_in_section"]}개)')
        print(f'  -> {r["second_image"]}')
