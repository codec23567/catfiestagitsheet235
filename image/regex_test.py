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

        # [변경] 여기서 빈 목록([])을 반환하면 "이미지가 원래 없었다"는
        # 것과 "요청/처리 중 에러가 나서 못 가져왔다"는 것을 구분할 수
        # 없게 된다. 그러면 실제로는 실패한 건데 시트에는 마치 정상적으로
        # "이미지 없음"인 것처럼 잘못 기록될 수 있다.
        # 에러를 조용히 삼키지 않고 그대로 다시 던져서(raise), 이 실패가
        # 호출한 쪽(select_organize_image.py)까지 확실히 전달되게 한다.
        raise
        
