import requests
import re
import sys
import time


def extract_all_images(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    start = time.time()

    response = requests.get(url, headers=headers, timeout=30)

    print(f"[응답] 상태={response.status_code}, 바이트={len(response.content)}", flush=True)

    html = response.text

    # -------------------------
    # src 또는 data-src를 가진 img 태그를 전부 추출
    # (도메인, 확장자 필터 없음 - data:image/... base64도 포함됨)
    # -------------------------
    img_regex = re.compile(
        r'<img[^>]*?(?:src|data-src)=[\'"]([^\'"]+)[\'"][^>]*>',
        re.IGNORECASE
    )

    matches = img_regex.findall(html)

    seen = set()
    images = []

    for src in matches:

        if src in seen:
            continue
        seen.add(src)

        # 프로토콜 없는 URL(//로 시작) 보정
        if src.startswith("//"):
            src = "https:" + src
        # 루트 상대경로(/로 시작) 보정
        elif src.startswith("/") and not src.startswith("//"):
            from urllib.parse import urljoin
            src = urljoin(url, src)

        images.append(f'<img src="{src}">')

    print(f"[결과] 이미지 수 : {len(images)}", flush=True)
    print(f"[시간] 전체 : {time.time() - start:.2f}초", flush=True)

    return images


if __name__ == "__main__":

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("테스트할 URL 입력: ").strip()

    images = extract_all_images(test_url)

    print("\n----- 추출된 이미지 -----")
    for img in images:
        print(img)

    # 브라우저 확인용 미리보기 파일
    with open("all_images_preview.html", "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'></head><body>\n")
        f.write("\n".join(images))
        f.write("\n</body></html>")

    print("\n[저장 완료] all_images_preview.html")
