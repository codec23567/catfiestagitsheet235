import requests
import time


def crawl_html(url):

    total_start = time.time()

    try:

        # -------------------------
        # HTTP 요청
        # -------------------------

        request_start = time.time()

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30
        )

        print(
            f"[시간] HTTP 요청 : {time.time() - request_start:.2f}초",
            flush=True
        )

        print(
            f"[응답] 상태={response.status_code}, "
            f"바이트={len(response.content)}",
            flush=True
        )

        # -------------------------
        # 삭제된 페이지
        # -------------------------

        if response.status_code == 404:

            print(
                f"[삭제됨] {url}",
                flush=True
            )

            return {
                "url": url,
                "html": "",
                "status_code": response.status_code,
                "deleted": True
            }

        # -------------------------
        # HTTP 오류 확인
        # -------------------------

        response.raise_for_status()

        # -------------------------
        # HTML
        # -------------------------

        html = response.text

        print(
            f"[결과] HTML 문자 수 : {len(html)}",
            flush=True
        )

        print(
            f"[시간] 전체 : {time.time() - total_start:.2f}초",
            flush=True
        )

        return {
            "url": url,
            "html": html,
            "status_code": response.status_code,
            "deleted": False
        }

    except requests.exceptions.Timeout:

        print(
            f"[오류] 요청 시간 초과 : {url}",
            flush=True
        )

        raise

    except requests.exceptions.RequestException as e:

        print(
            f"[오류] HTTP 요청 실패 : {url}",
            flush=True
        )

        print(
            e,
            flush=True
        )

        raise

    except Exception as e:

        print(
            f"[오류] {url}",
            flush=True
        )

        print(
            e,
            flush=True
        )

        raise


# ==================================================
# 실행
# ==================================================

if __name__ == "__main__":

    url = input("URL 입력 : ").strip()

    if not url:
        print("[오류] URL이 입력되지 않았습니다.")
        exit()

    result = crawl_html(url)

    if result["deleted"]:

        print("[결과] 삭제된 페이지입니다.")

    else:

        print()
        print("=" * 80)
        print("HTML")
        print("=" * 80)

        print(result["html"])

        print("=" * 80)

        # -------------------------
        # HTML 파일 저장
        # -------------------------

        with open(
            "crawled.html",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(result["html"])

        print()
        print("[저장] crawled.html")
