import html
import re
import time
from urllib.parse import urljoin

import requests


def extract_links(url):
    total_start = time.time()

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()

        print(f"[응답] 상태={response.status_code}, 바이트={len(response.content)}",
              flush=True)

        page_html = response.text

        # 본문(write_div) 영역만 대상으로 추출
        body_part = page_html
        body_start = page_html.find('class="write_div"')

        if body_start != -1:
            body_end = page_html.find(
                '<script id="mg_numbering-tmpl"',
                body_start,
            )

            if body_end == -1:
                body_end = page_html.find("<script", body_start)

            body_part = (
                page_html[body_start:body_end]
                if body_end != -1
                else page_html[body_start:]
            )

        # <a href="..."> 또는 <a href='...'> 추출
        href_regex = re.compile(
            r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        )

        links = []
        seen = set()

        for href in href_regex.findall(body_part):
            href = html.unescape(href).strip()

            # 페이지 내부 이동, JavaScript 링크 등 제외
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # 상대 링크도 원래 게시글 주소 기준 절대 링크로 변환
            href = urljoin(url, href)

            # 중복 제거 및 http/https 링크만 유지
            if href.startswith(("http://", "https://")) and href not in seen:
                seen.add(href)
                links.append(href)

        print(f"[결과] 링크 수 : {len(links)}", flush=True)
        print(f"[시간] 전체 : {time.time() - total_start:.2f}초", flush=True)

        return links

    except requests.RequestException as error:
        print(f"[오류] {url}", flush=True)
        print(error, flush=True)
        return []
