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


def modify_post_editor(
    user_id,
    user_pw,
    modify_url,
    text
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

       # 페이지가 완전히 그려질 때까지 잠깐 대기
        time.sleep(2)


        # ============================================
        # HTML 모드로 전환
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
        # HTML 내용 전체 삭제
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
        # 다시 에디터 모드로 복귀
        # ============================================


        html_button.click()

        # 에디터가 다시 활성화될 때까지 대기
        editor = wait.until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".note-editable"
                )
            )
        )

        editor.click()

        url_pattern = re.compile(r'^https?://\S+$')

        has_url = any(
            url_pattern.match(line.strip())
            for line in text.splitlines()
        )        

        for line in text.splitlines():

            print(f"입력: [{line}]", flush=True)

            editor.send_keys(line)


            if url_pattern.match(line.strip()):

                print("URL 발견", flush=True)

                driver.execute_script("oglink('paste', false, '');")

                time.sleep(2)

                print(
                    "현재 og-div:",
                    len(driver.find_elements(By.CSS_SELECTOR, ".og-div")),
                    flush=True
                )

                print("OG 생성 완료", flush=True)

                # -----------------------------
                # HTML 모드
                # -----------------------------
                html_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[normalize-space()='HTML']"
                        )
                    )
                )
                html_button.click()

                html_area = wait.until(
                    EC.visibility_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".note-codable"
                        )
                    )
                )

                # HTML 끝에 . 추가
                html_area.send_keys(".")

                # -----------------------------
                # 다시 에디터 모드
                # -----------------------------
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


            editor.send_keys(Keys.SHIFT, Keys.ENTER)
        
        # ============================================
        # 수정 버튼
        # ============================================
      
      
        if has_url:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".og-div")
                )
            )

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
        print(traceback.format_exc(), flush=True)

        return {
            "success": False,
            "message": str(e)
        }

    finally:
        elapsed = time.perf_counter() - start
        print(f"[modify_post] 실행시간: {elapsed:.2f}초")
        driver.quit()
        
