import requests
import time


# -------------------------------------------------
# 설정
# -------------------------------------------------

OUTPUT_FILE = "source.html"
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# -------------------------------------------------
# HTML 크롤링
# -------------------------------------------------

def crawl_html(url):
    total_start = time.time()

    try:
        print(f"[요청] {url}", flush=True)

        request_start = time.time()

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        request_time = time.time() - request_start

        content_type = response.headers.get("Content-Type", "")
        encoding = response.encoding or "확인 불가"
        received_size = len(response.content)

        print(
            f"[응답] 상태={response.status_code}, "
            f"바이트={received_size:,}, "
            f"인코딩={encoding}",
            flush=True
        )

        print(
            f"[응답] Content-Type={content_type}",
            flush=True
        )

        print(
            f"[응답] 최종 URL={response.url}",
            flush=True
        )

        print(
            f"[시간] HTTP 요청 : {request_time:.2f}초",
            flush=True
        )

        # HTTP 오류
        response.raise_for_status()

        # -------------------------------------------------
        # HTML 저장
        # -------------------------------------------------

        save_start = time.time()

        with open(OUTPUT_FILE, "wb") as file:
            file.write(response.content)

        save_time = time.time() - save_start

        saved_size = len(response.content)

        print(
            f"[저장] 파일={OUTPUT_FILE}, "
            f"바이트={saved_size:,}",
            flush=True
        )

        print(
            f"[시간] HTML 저장 : {save_time:.4f}초",
            flush=True
        )

        total_time = time.time() - total_start

        print(
            f"[완료] 전체 소요 : {total_time:.2f}초",
            flush=True
        )

        return {
            "url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": content_type,
            "encoding": encoding,
            "size": saved_size,
            "filepath": OUTPUT_FILE,
        }

    except requests.Timeout:
        print(
            f"[오류] 요청 시간 초과 ({TIMEOUT}초): {url}",
            flush=True
        )
        raise

    except requests.RequestException as e:
        print(
            f"[HTTP 오류] URL={url}",
            flush=True
        )
        print(
            f"[오류 내용] {e}",
            flush=True
        )
        raise

    except Exception as e:
        print(
            f"[오류] URL={url}",
            flush=True
        )
        print(
            f"[오류 내용] {e}",
            flush=True
        )
        raise


# -------------------------------------------------
# 실행
# -------------------------------------------------

if __name__ == "__main__":

    url = input("크롤링할 URL을 입력하세요: ").strip()

    if not url:
        print("[오류] URL이 입력되지 않았습니다.", flush=True)
        raise SystemExit(1)

    crawl_html(url)
