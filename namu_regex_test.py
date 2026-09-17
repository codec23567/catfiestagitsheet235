import requests
import re
import time


def extract_namu_images(url):

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
        # 존재하지 않는 문서 판정
        # -------------------------
        # [주의] 나무위키는 없는 문서도 200을 반환하고
        # "새 문서를 만드시겠습니까" 같은 안내 문구가 뜬다.
        # 아직 실제 케이스로 확인 못 해서 임시로 넣어둔 판정.
        # 실제로 없는 문서 URL로 한 번 테스트해보고 문구 맞는지 확인 필요.
        if response.status_code == 404 or "새 문서를 만드시겠습니까" in response.text:
            print(f"[문서 없음] {url}", flush=True)
            return {
                "images": [],
                "deleted": True
            }

        html = response.text

        # -------------------------
        # 이미지 추출
        # -------------------------
        # data-src 또는 src에 들어있는 i.namu.wiki 실제 이미지만 추출
        # (확장자로 svg 아이콘/데코 이미지는 걸러냄)

        regex_start = time.time()

        img_regex = re.compile(
            r'(?:data-src|src)=[\'"](//i\.namu\.wiki/i/[^\'"]+\.(?:webp|jpg|jpeg|png|gif))[\'"]',
            re.IGNORECASE
        )

        matches = img_regex.findall(html)

        # 같은 이미지가 플레이스홀더/완성본으로 중복 등장하므로
        # 순서를 유지하면서 중복 제거
        seen = set()
        images = []

        for src in matches:

            if src in seen:
                continue

            seen.add(src)

            full_src = "https:" + src

            images.append(
                f'<img src="{full_src}">'
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

        return {
            "images": images,
            "deleted": False
        }

    except Exception as e:

        print(f"[오류] {url}", flush=True)
        print(e, flush=True)

        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("테스트할 나무위키 URL 입력: ").strip()

    result = extract_namu_images(test_url)

    print("\n----- 추출된 이미지 -----")
    for img in result["images"]:
        print(img)
