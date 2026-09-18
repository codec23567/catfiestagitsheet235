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

        # 사이트에서는 삭제된 글에 404 반환
        if response.status_code == 404:
            print(f"[삭제됨] {url}", flush=True)
            return {
                "images": [],
                "deleted": True
            }

        html = response.text

        # 본문(write_div) 영역만 잘라내서 이후 정규식 검사 범위를 좁힌다
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

        # select_organize_image.py와의 계약 일치를 위해 dict로 반환
        # ({"images": [...], "deleted": bool})
        return {
            "images": images,
            "deleted": False
        }

    except Exception as e:

        print(f"[오류] {url}", flush=True)
        print(e, flush=True)

        raise
