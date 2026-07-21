import requests
import re
import html as html_module
import time


def extract_nickdate(url):

    start = time.time()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        html = response.text

        print(
            f"[응답] 상태={response.status_code}, "
            f"바이트={len(response.content)}, "
            f"URL={url}",
            flush=True
        )

        # 삭제된 글 판정
        # 정상 HTML에도 '삭제'라는 단어가 들어갈 수 있으므로
        # 우선 HTTP 404만 삭제된 글로 판정
        deleted = response.status_code == 404

        if deleted:
            return {
                "date": "삭제됨",
                "author": "",
                "deleted": True
            }

        date = ""
        author = ""

        # 작성자 추출
        author_match = re.search(
            r'data-nick="([^"]+)"'
            r'(?:\s+data-uid="([^"]*)")?'
            r'(?:\s+data-ip="([^"]*)")?',
            html
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

        # 날짜 추출
        date_match = (
            re.search(
                r'<span class="gall_date" title="([^"]+)">',
                html
            )
            or
            re.search(
                r'<span class="date">([^<]+)</span>',
                html
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

        print(
            f"[결과] 날짜={date}, "
            f"작성자={author}, "
            f"시간={time.time() - start:.2f}초",
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
