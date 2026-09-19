import requests
import re
import time
from html import unescape
from urllib.parse import urljoin


def extract_images(url):

    total_start = time.time()

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        request_start = time.time()

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        print(
            f"[시간] HTTP 요청 : {time.time() - request_start:.2f}초",
            flush=True
        )

        print(
            f"[응답] 상태={response.status_code}, 바이트={len(response.content)}",
            flush=True
        )

        # 우리 사이트(catfiestasite)에서는 없는 페이지에 404 반환
        if response.status_code == 404:
            print(f"[삭제됨] {url}", flush=True)
            return {
                "images": [],
                "characters": [],
                "deleted": True
            }

        response.encoding = "utf-8"
        html = response.text

        # 본문(<main>) 영역만 잘라내서 이후 정규식 검사 범위를 좁힌다
        # (헤더 등 <main> 밖의 이미지는 대상이 아니다)
        body_part = html

        body_start = html.find("<main")

        if body_start != -1:

            body_end = html.find("</main>", body_start)

            if body_end != -1:
                body_part = html[body_start:body_end]
            else:
                body_part = html[body_start:]

        regex_start = time.time()

        img_regex = re.compile(
            r'<img[^>]*\ssrc=["\']([^"\']+)["\']',
            re.IGNORECASE
        )

        def to_tag(src):

            src = unescape(src)

            # 상대 경로면 페이지 주소를 기준으로 절대 주소로 바꾼다
            src = urljoin(url, src)

            return f'<img src="{src}">'

        images = [
            to_tag(src)
            for src in img_regex.findall(body_part)
        ]

        # 캐릭터 카드(class="card") 하나가 캐릭터 한 명이고,
        # 카드 안의 이미지들이 그 캐릭터의 폼(1폼, 2폼, ...)이다.
        # 카드가 없는 페이지면 이미지 하나를 캐릭터 한 명으로 본다.
        card_parts = body_part.split('class="card"')[1:]

        characters = []

        for part in card_parts:

            forms = [
                to_tag(src)
                for src in img_regex.findall(part)
            ]

            if forms:
                characters.append(forms)

        if not card_parts:
            characters = [[tag] for tag in images]

        print(
            f"[시간] 정규식 : {time.time() - regex_start:.4f}초",
            flush=True
        )

        print(
            f"[결과] 캐릭터 수 : {len(characters)}, 이미지 수 : {len(images)}",
            flush=True
        )

        print(
            f"[시간] 전체 : {time.time() - total_start:.2f}초",
            flush=True
        )

        # select_organize_image.py와의 계약 일치를 위해 dict로 반환
        # ({"images": [...], "characters": [[폼, ...], ...], "deleted": bool})
        #  - images     : 모든 이미지를 한 줄로 이은 목록
        #  - characters : 캐릭터별로 묶은 폼 목록 (페이지에 나온 순서)
        return {
            "images": images,
            "characters": characters,
            "deleted": False
        }

    except Exception as e:

        print(f"[오류] {url}", flush=True)
        print(e, flush=True)

        raise
