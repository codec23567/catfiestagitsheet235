import requests
import re
import html as html_module
import time


def extract_nickdate(url):

    total_start = time.time()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        # -------------------------
        # HTTP 요청
        # -------------------------

        request_start = time.time()

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        request_time = time.time() - request_start

        html = response.text

        print(
            f"[응답] 상태={response.status_code}, "
            f"바이트={len(response.content)}, "
            f"URL={url}",
            flush=True
        )

        print(
            f"[시간] HTTP 요청 : {request_time:.4f}초",
            flush=True
        )

        # 삭제된 글 판정
        deleted = response.status_code == 404

        if deleted:
            return {
                "date": "삭제됨",
                "author": "",
                "deleted": True
            }

        date = ""
        author = ""

        # -------------------------
        # gallview_head 영역 추출
        # -------------------------

        head_start_time = time.time()

        head_part = html

        head_start = html.find(
            '<div class="gallview_head"'
        )

        if head_start != -1:

            head_end = html.find(
                '<div class="gallview_contents"',
                head_start
            )

            if head_end != -1:
                head_part = html[
                    head_start:head_end
                ]
            else:
                head_part = html[
                    head_start:
                ]

        head_time = time.time() - head_start_time

        print(
            f"[시간] 헤더 추출 : {head_time:.6f}초",
            flush=True
        )

        # -------------------------
        # 작성자 추출
        # -------------------------

        author_start_time = time.time()

        author_match = re.search(
            r'data-nick="([^"]+)"'
            r'(?:\s+data-uid="([^"]*)")?'
            r'(?:\s+data-ip="([^"]*)")?',
            head_part
        )

        if author_match:

            nick = html_module.unescape(
                author_match.group(1)
            )

            uid = (
                author_match.group(2)
                if author_match.group(2)
                else (author_match.group(3) or "")
            )

            if uid:
                author = f"{nick}({uid})"
            else:
                author = nick

        author_time = time.time() - author_start_time

        print(
            f"[시간] 작성자 추출 : {author_time:.6f}초",
            flush=True
        )

        # -------------------------
        # 날짜 추출
        # -------------------------

        date_start_time = time.time()

        date_match = (
            re.search(
                r'<span class="gall_date" title="([^"]+)">',
                head_part
            )
            or
            re.search(
                r'<span class="date">([^<]+)</span>',
                head_part
            )
        )

        if date_match:

            raw_date = (
                date_match.group(1)
                .strip()
                .split(" ")[0]
            )

            date = re.sub(
                r"\.([^ ])",
                r". \1",
                raw_date.replace("-", ". ")
            )

        date_time = time.time() - date_start_time

        print(
            f"[시간] 날짜 추출 : {date_time:.6f}초",
            flush=True
        )

        total_time = time.time() - total_start

        print(
            f"[결과] 날짜={date}, "
            f"작성자={author}",
            flush=True
        )

        print(
            f"[시간] 총 소요 : {total_time:.4f}초",
            flush=True
        )

        # HTML은 받았지만 날짜 또는 작성자 추출 실패
        if not date or not author:
            return {
                "date": "",
                "author": "",
                "deleted": False
            }

        return {
            "date": date,
            "author": author,
            "deleted": False
        }

    except Exception as e:

        print(
            f"[오류] URL={url}, 오류={e}",
            flush=True
        )

        return {
            "date": "",
            "author": "",
            "deleted": False
        }
