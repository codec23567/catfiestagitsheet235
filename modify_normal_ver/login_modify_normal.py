from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import re
import traceback

LOGIN_URL = (
    "https://sign.dcinside.com/login"
    "?s_url=https://www.dcinside.com/"
)


def modify_post(
    user_id,
    user_pw,
    modify_url,
    text
):
    print("★★★★★ modify_post 시작 ★★★★★", flush=True)
    start = time.perf_counter()

    t = time.perf_counter()

    options = Options()

    options.binary_location = "/usr/bin/google-chrome"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Chrome 최적화
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--disable-default-apps")

    # 이미지 로딩 차단
    options.add_experimental_option(
        "prefs",
        {
            "profile.managed_default_content_settings.images": 2
        }
    )

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, 5)
    short_wait = WebDriverWait(driver, 5)

    try:

        # ============================================
        # 로그인
        # ============================================

        driver.get(LOGIN_URL)

        id_input = wait.until(
            EC.visibility_of_element_located(
                (By.NAME, "user_id")
            )
        )

        id_input.clear()
        id_input.send_keys(user_id)

        pw_input = wait.until(
            EC.visibility_of_element_located(
                (By.NAME, "pw")
            )
        )

        pw_input.clear()
        pw_input.send_keys(user_pw)

        login_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[type='submit']")
            )
        )

        login_button.click()

        wait.until(
            EC.url_changes(LOGIN_URL)
        )

        print(f"[시간] 로그인 : {time.perf_counter()-t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # 수정 페이지 이동
        # ============================================

        driver.get(modify_url)

        html_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='HTML']"
                )
            )
        )

        print(f"[시간] 수정페이지 : {time.perf_counter()-t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # HTML 모드
        # ============================================

        html_button.click()

        # ============================================
        # HTML 내용 삭제
        # ============================================

        html_area = wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".note-codable"
                )
            )
        )

        html_area.clear()

        # ============================================
        # 일반 에디터 모드
        # ============================================

        html_button.click()

        editor = wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".note-editable"
                )
            )
        )

        editor.click()

        url_pattern = re.compile(r"^https?://\S+$")

        for line in text.splitlines():

            print(f"입력: [{line}]", flush=True)

            editor.send_keys(line)

            if url_pattern.match(line.strip()):

                print("URL 발견", flush=True)

                driver.execute_script(
                    "oglink('paste', false, '');"
                )

                short_wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".og-div"
                        )
                    )
                )

                print("OG 생성 완료", flush=True)

            editor.send_keys(Keys.SHIFT, Keys.ENTER)

        print(f"[시간] 본문입력 : {time.perf_counter()-t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # 수정 버튼
        # ============================================

        write_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "button.btn_blue.write"
                )
            )
        )

        write_button.click()

        print(f"[시간] 저장 : {time.perf_counter()-t:.2f}초", flush=True)

        return {
            "success": True
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        elapsed = time.perf_counter() - start

        print(
            f"[modify_post] 실행시간: {elapsed:.2f}초"
        )

        driver.quit()
