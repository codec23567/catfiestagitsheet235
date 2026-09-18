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
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        start = time.time()

        print(f"[접속] {url}")
        driver.get(url)

        # 1. 기본 페이지 로딩 완료 대기
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        print("[완료] 기본 페이지 로딩")

        # 2. 페이지 전체를 스크롤해서
        #    lazy-loading 영역을 최대한 활성화
        print("[진행] 페이지 전체 스크롤")

        driver.execute_script("""
            window.scrollTo({
                top: 0,
                behavior: 'instant'
            });
        """)

        time.sleep(1)

        current_position = 0
        scroll_step = 800

        while True:
            page_height = driver.execute_script(
                "return document.body.scrollHeight"
            )

            if current_position >= page_height:
                break

            current_position += scroll_step

            driver.execute_script(
                "window.scrollTo(0, arguments[0]);",
                current_position
            )

            time.sleep(0.3)

        # 페이지 최하단까지 이동
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

        time.sleep(2)

        print("[완료] 페이지 전체 스크롤")

        # 3. 모든 이미지의 다운로드 완료를 기다리지는 않는다.
        #    DOM의 src / data-src 등을 확보하는 것이 목적이므로
        #    렌더링이 안정화될 정도만 기다린다.
        print("[대기] 페이지 렌더링 안정화")

        time.sleep(3)

        print("[완료] 페이지 렌더링 안정화")

        # 4. 최상단으로 복귀
        driver.execute_script(
            "window.scrollTo(0, 0);"
        )

        time.sleep(1)

        # 5. 최종 렌더링 DOM 저장
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
