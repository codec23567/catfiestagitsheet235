import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


OUTPUT_FILE = Path("crawled.html")


def crawl_html(url: str, output_file: Path = OUTPUT_FILE) -> None:
    options = Options()

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 화면을 크게 잡아서 lazy-loading 이미지가 최대한 로딩되도록 한다.
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        start = time.time()

        print(f"[접속] {url}")
        driver.get(url)

        # --------------------------------------------------
        # 1. 기본 페이지 로딩 완료 대기
        # --------------------------------------------------
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        print("[완료] 기본 페이지 로딩")

        # --------------------------------------------------
        # 2. 페이지를 아래까지 천천히 스크롤
        #
        # loading="lazy" 이미지가 있기 때문에
        # 페이지 전체를 한 번씩 화면에 노출시킨다.
        # --------------------------------------------------
        print("[진행] 페이지 전체 스크롤")

        driver.execute_script("""
            window.scrollTo({
                top: 0,
                behavior: 'instant'
            });
        """)

        time.sleep(1)

        page_height = driver.execute_script(
            "return document.body.scrollHeight"
        )

        current_position = 0
        scroll_step = 800

        while current_position < page_height:
            current_position += scroll_step

            driver.execute_script(
                "window.scrollTo(0, arguments[0]);",
                current_position
            )

            # lazy-loading 처리 시간을 조금 준다.
            time.sleep(0.3)

            # 페이지 높이가 동적으로 늘어날 수 있으므로 다시 확인
            page_height = driver.execute_script(
                "return document.body.scrollHeight"
            )

        # 마지막 부분까지 확실히 노출
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        time.sleep(2)

        print("[완료] 페이지 전체 스크롤")

        # --------------------------------------------------
        # 3. 이미지 로딩 대기
        # --------------------------------------------------
        print("[진행] 이미지 로딩 확인")

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("""
                const images = Array.from(document.images);

                if (images.length === 0) {
                    return true;
                }

                return images.every(img => {
                    return img.complete;
                });
            """)
        )

        print("[완료] 이미지 로딩 확인")

        # --------------------------------------------------
        # 4. 페이지 최상단으로 복귀
        # --------------------------------------------------
        driver.execute_script(
            "window.scrollTo(0, 0);"
        )

        time.sleep(1)

        # --------------------------------------------------
        # 5. 최종 DOM 저장
        # --------------------------------------------------
        html = driver.page_source

        output_file.write_text(
            html,
            encoding="utf-8"
        )

        print(f"[완료] HTML 저장: {output_file}")
        print(f"[크기] {len(html):,} 문자")
        print(f"[시간] {time.time() - start:.2f}초")

    finally:
        driver.quit()


if __name__ == "__main__":
    url = input("크롤링할 URL : ").strip()

    if not url:
        print("URL이 입력되지 않았습니다.")
    else:
        crawl_html(url)
