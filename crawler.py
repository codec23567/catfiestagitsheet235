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

        # 페이지의 기본 DOM이 준비될 때까지 대기
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # JS로 이미지/DOM이 바뀌는 사이트를 고려해 잠시 추가 대기
        time.sleep(2)

        html = driver.page_source

        output_file.write_text(html, encoding="utf-8")

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
