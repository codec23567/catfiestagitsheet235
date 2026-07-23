import requests
import re
import time


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

        html = response.text

        # -------------------------
        # write_div 영역만 추출
        # -------------------------

        body_part = html

        body_start = html.find('class="write_div"')

        if body_start != -1:

            body_end = html.find(
                '<script id="mg_numbering-tmpl"',
                body_start
            )

            if body_end == -1:
                body_end = html.find(
                    '<script',
                    body_start
                )

            if body_end != -1:
                body_part = html[body_start:body_end]
            else:
                body_part = html[body_start:]

        # -------------------------
        # 이미지 추출
        # -------------------------

        regex_start = time.time()

        img_regex = re.compile(
            r'<img[^>]*(?:src|data-src|data-original)=["\']([^"\']*viewimage\.php[^"\']*)["\']',
            re.IGNORECASE
        )

        matches = img_regex.findall(body_part)

        images = []

        for src in matches:

            if src.startswith("/"):
                src = "https://www.dcinside.com" + src

            src = src.replace("&amp;", "&")

            images.append(
                f'<img src="{src}">'
            )

        print(
            f"[시간] 정규식 : {time.time() - regex_start:.4f}초",
            flush=True
        )

        print(
            f"[결과] 이미지 수 : {len(images)}",
            flush=True
        )

        print(
            f"[시간] 전체 : {time.time() - total_start:.2f}초",
            flush=True
        )

        return images

    except Exception as e:

        print(f"[오류] {url}", flush=True)
        print(e, flush=True)

        return []
