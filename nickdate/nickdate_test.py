import re
import time

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def extract_nickdate(url):

    total_start = time.time()

    try:

        request_start = time.time()

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        request_time = time.time() - request_start

        # 삭제된 글 판정
        if response.status_code == 404:
            print(f"[삭제됨] {url}", flush=True)
            return {
                "date": "삭제됨",
                "author": "",
                "deleted": True
            }

        # 404 외의 오류(403, 429, 5xx 등)는 예외로 알려서 재시도 대상이 되게 한다
        # (오류/차단 페이지를 그대로 파싱해서 엉뚱한 값을 뽑지 않도록)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 글 머리(작성자/날짜) 영역만 대상으로 한다
        # 페이지 전체에는 댓글 작성자의 data-nick도 많으므로,
        # 이 영역을 못 찾았을 때 전체에서 찾으면 엉뚱한 사람이 잡힌다
        head = soup.select_one("div.gallview_head")

        if head is None:
            raise ValueError(
                "gallview_head 영역을 찾지 못했습니다 "
                "(차단 페이지이거나 사이트 구조가 바뀜)"
            )

        date = ""
        author = ""

        # -------------------------
        # 작성자
        # -------------------------
        # data-uid(고정닉/아이디)가 있으면 그것을, 없으면 data-ip(유동)를 붙인다

        writer = head.select_one("[data-nick]")

        if writer and writer.get("data-nick"):

            nick = writer["data-nick"]

            uid = writer.get("data-uid") or writer.get("data-ip") or ""

            author = f"{nick}({uid})" if uid else nick

        # -------------------------
        # 날짜
        # -------------------------

        date_tag = head.select_one("span.gall_date[title]")

        if date_tag:
            raw_date = date_tag["title"]
        else:
            date_tag = head.select_one("span.date")
            raw_date = date_tag.get_text() if date_tag else ""

        if raw_date:

            raw_date = raw_date.strip().split(" ")[0]

            date = re.sub(
                r"\.([^ ])",
                r". \1",
                raw_date.replace("-", ". ")
            )

        # 한 글당 한 줄로 요약 (스레드 여러 개가 동시에 돌아도 URL로 구분된다)
        print(
            f"[결과] {url} : 날짜={date}, 작성자={author}, "
            f"상태={response.status_code}, 바이트={len(response.content)} "
            f"(요청 {request_time:.2f}초, 전체 {time.time() - total_start:.2f}초)",
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

        print(f"[오류] {url} : {e}", flush=True)

        return {
            "date": "",
            "author": "",
            "deleted": False
        }
