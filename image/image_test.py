import requests
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def extract_images(url):

    total_start = time.time()

    try:

        request_start = time.time()

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        request_time = time.time() - request_start

        # 우리 사이트(catfiestasite)에서는 없는 페이지에 404 반환
        if response.status_code == 404:
            print(f"[삭제됨] {url}", flush=True)
            return {
                "images": [],
                "characters": [],
                "deleted": True
            }

        # 404 외의 오류(403, 429, 5xx 등)는 예외로 알려서 재시도 대상이 되게 한다
        # (오류 페이지를 그대로 파싱해서 엉뚱한 이미지를 뽑지 않도록)
        response.raise_for_status()

        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        # 본문(<main>) 영역만 대상으로 한다
        # (헤더 등 <main> 밖의 이미지는 대상이 아니다)
        # <main>이 없는 페이지면 문서 전체를 본다
        body = soup.find("main") or soup

        def to_tag(img):

            src = (img.get("src") or "").strip()

            if not src:
                return None

            # 상대 경로면 페이지 주소를 기준으로 절대 주소로 바꾼다
            return f'<img src="{urljoin(url, src)}">'

        def to_tags(imgs):

            tags = [to_tag(img) for img in imgs]

            return [tag for tag in tags if tag]

        images = to_tags(body.find_all("img"))

        # 캐릭터 카드(class="card") 하나가 캐릭터 한 명이고,
        # 카드 안의 이미지들이 그 캐릭터의 폼(1폼, 2폼, ...)이다.
        # 카드가 없는 페이지면 이미지 하나를 캐릭터 한 명으로 본다.
        cards = body.select(".card")

        characters = []

        for card in cards:

            forms = to_tags(card.find_all("img"))

            if forms:
                characters.append(forms)

            else:
                # 이미지 없는 카드는 건너뛰므로 뒤 캐릭터 순서가 한 칸씩 앞당겨진다
                name = card.select_one(".name")
                name = name.get_text(strip=True) if name else "이름 없음"

                print(
                    f"[경고] {url} : '{name}' 카드에 이미지가 없어 건너뜁니다 "
                    f"(뒤 캐릭터 순서가 밀릴 수 있음)",
                    flush=True
                )

        if not cards:
            characters = [[tag] for tag in images]

        # 한 페이지당 한 줄로 요약 (스레드 여러 개가 동시에 돌아도 URL로 구분된다)
        print(
            f"[결과] {url} : 상태={response.status_code}, "
            f"바이트={len(response.content)}, "
            f"캐릭터 {len(characters)}명, 이미지 {len(images)}개 "
            f"(요청 {request_time:.2f}초, 전체 {time.time() - total_start:.2f}초)",
            flush=True
        )

        # select_organize_image.py와의 계약 일치를 위해 dict로 반환
        # ({"images": [...], "characters": [[폼, ...], ...], "deleted": bool})
        #  - images     : 모든 이미지를 한 줄로 이은 목록
        #  - characters : 캐릭터별로 묶은 폼 목록 (페이지에 나온 순서)
        return {
            "images": images,
            "characters": characters,
            "deleted": False
        }

    except Exception as e:

        print(f"[오류] {url} : {e}", flush=True)

        raise
