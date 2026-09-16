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

        # -------------------------
        # 삭제된 글 판정
        # -------------------------
        # [추가] nickdate_test.py와 동일하게 404를 "삭제된 글"로 명시적
        # 구분한다. 삭제된 글은 재시도해도 결과가 바뀌지 않으므로,
        # 여기서 즉시 확정해서 select_organize_image.py의 재시도
        # 대상에서 빠지게 한다.
        if response.status_code == 404:
            print(f"[삭제됨] {url}", flush=True)
            return {
                "images": [],
                "deleted": True
            }

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

        # [변경] 리스트 대신 dict로 반환 (select_organize_image.py와
        # 계약 일치: {"images": [...], "deleted": bool})
        return {
            "images": images,
            "deleted": False
        }

    except Exception as e:

        print(f"[오류] {url}", flush=True)
        print(e, flush=True)

        # 에러를 조용히 삼키지 않고 그대로 다시 던져서(raise), 이 실패가
        # 호출한 쪽(select_organize_image.py)까지 확실히 전달되게 한다.
        # -> 호출부의 재시도 로직이 이 예외를 잡아 재시도 대상으로 처리한다.
        raise
