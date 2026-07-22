from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time


LOGIN_URL = (
    "https://sign.dcinside.com/login"
    "?s_url=https://www.dcinside.com/"
)


def modify_post(
    user_id,
    user_pw,
    modify_url,
    html
):
    print("★★★★★ modify_post 시작 ★★★★★", flush=True)
    start = time.perf_counter()
    options = Options()

    options.binary_location = "/usr/bin/google-chrome"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

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

        # ============================================
        # 수정 페이지 이동
        # ============================================

        driver.get(modify_url)

    
        # ============================================
        # HTML 모드
        # ============================================

        html_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='HTML']"
                )
            )
        )

        html_button.click()

        


        # ============================================
        # 본문 교체
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
        html_area.send_keys(html)


        # ============================================
        # 수정 버튼
        # ============================================

        write_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn_blue.write")
            )
        )        

        write_button.click()

        

        return {
            "success": True
        }


    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


    finally:
        elapsed = time.perf_counter() - start
        print(f"[modify_post] 실행시간: {elapsed:.2f}초")
        driver.quit()
