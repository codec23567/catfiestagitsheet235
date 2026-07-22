import requests
import re
import time


def extract_images(url):

    total_start = time.time()

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
    body_part = html

    body_start = html.find('class="writing_view_box"')

    if body_start == -1:
        body_start = html.find('class="writeview_contents"')

    if body_start == -1:
        body_start = html.find('class="thum-txt"')

    if body_start != -1:

        body_end = html.find(
            'class="comment_wrap"',
            body_start
        )

        if body_end == -1:
            body_end = html.find(
                'class="view_comment"',
                body_start
            )

        if body_end != -1:
            body_part = html[body_start:body_end]
        else:
            body_part = html[body_start:]


    regex_start = time.time()

    img_regex = re.compile(
        r'<img[^>]*(?:src|data-src|data-original)=["\']([^"\']*viewimage\.php[^"\']*)["\'][^>]*',
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
