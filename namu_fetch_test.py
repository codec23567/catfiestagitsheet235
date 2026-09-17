import requests
import sys
import time


def test_fetch(url):

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    start = time.time()

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        elapsed = time.time() - start

        print(f"[요청 시간] {elapsed:.2f}초")
        print(f"[상태 코드] {response.status_code}")
        print(f"[응답 바이트] {len(response.content)}")
        print(f"[Content-Type] {response.headers.get('Content-Type')}")

        html = response.text

        # 클라우드플레어/봇 차단 페이지인지 대략 확인
        block_markers = [
            "cf-browser-verification",
            "Attention Required",
            "Just a moment",
            "captcha",
        ]

        blocked = any(marker.lower() in html.lower() for marker in block_markers)

        print(f"[봇 차단 의심] {blocked}")

        # 실제 문서 내용이 있는지 확인 (나무위키 본문 영역 마커)
        has_content = (
            'wiki-heading' in html
            or 'wiki-inner-content' in html
            or '<article' in html
        )

        print(f"[본문 마커 발견] {has_content}")

        # HTML 앞부분 미리보기 (구조 확인용)
        print("\n----- HTML 앞부분 미리보기 (2000자) -----")
        print(html[:2000])

        # 저장해서 나중에 img 태그 구조 살펴보기 쉽게
        with open("namu_sample.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("\n[저장 완료] namu_sample.html")

    except Exception as e:
        print(f"[오류] {e}")


if __name__ == "__main__":

    # 실행 방법 1: python3 namu_fetch_test.py "https://namu.wiki/w/문서명"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        # 실행 방법 2: 인자 없이 실행하면 직접 입력받음
        test_url = input("테스트할 나무위키 URL 입력: ").strip()

    if not test_url:
        print("[오류] URL이 입력되지 않았습니다.")
        sys.exit(1)

    test_fetch(test_url)
