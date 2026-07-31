from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import re
import time
import traceback

LOGIN_URL = (
    "https://sign.dcinside.com/login"
    "?s_url=https://www.dcinside.com/"
)


def modify_post(user_id, user_pw, modify_url, text):
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
            "profile.managed_default_content_settings.images": 2,
        },
    )

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, 5)
    short_wait = WebDriverWait(driver, 20)

    try:
        # ============================================
        # 로그인
        # ============================================
        driver.get(LOGIN_URL)

        id_input = wait.until(
            EC.visibility_of_element_located(
                (By.NAME, "user_id"),
            )
        )
        id_input.clear()
        id_input.send_keys(user_id)

        pw_input = wait.until(
            EC.visibility_of_element_located(
                (By.NAME, "pw"),
            )
        )
        pw_input.clear()
        pw_input.send_keys(user_pw)

        login_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[type='submit']"),
            )
        )
        login_button.click()

        wait.until(EC.url_changes(LOGIN_URL))

        print(f"[시간] 로그인 : {time.perf_counter() - t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # 수정 페이지 이동
        # ============================================
        driver.get(modify_url)

        html_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='HTML']"),
            )
        )

        print(f"[시간] 수정페이지 : {time.perf_counter() - t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # 기존 본문 삭제
        # ============================================
        html_button.click()

        html_area = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-codable"),
            )
        )
        html_area.clear()

        # 일반 에디터 모드로 복귀
        html_button.click()

        editor = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-editable"),
            )
        )
        
        # 비운 본문의 맨 끝에서 입력을 시작한다.
        editor.click()
        editor.send_keys(Keys.CONTROL, Keys.END)

        # 한 줄 전체가 URL인 경우에만 OG 카드 생성
        url_pattern = re.compile(r"^https?://\S+$")
        lines = text.splitlines()

        # ============================================
        # 본문 입력
        # ============================================
        for index, line in enumerate(lines):
            is_url = bool(url_pattern.fullmatch(line.strip()))
            is_last_line = index == len(lines) - 1

            print(f"입력: [{line}]", flush=True)

            # 빈 줄은 텍스트를 입력하지 않고 Enter만 처리
            if line:
                editor.send_keys(line)

            if is_url:
                print("URL 발견 - OG 카드 생성 시작", flush=True)

                # 이미 존재하는 OG 카드 수를 기록한다.
                # 단순히 .og-div의 존재만 기다리면 두 번째 URL부터는
                # 기존 카드 때문에 즉시 통과하는 문제가 생긴다.
                og_count_before = len(
                    driver.find_elements(By.CSS_SELECTOR, ".og-div")
                )

                driver.execute_script("oglink('paste', false, '');")

                # 새 OG 카드가 실제로 하나 추가될 때까지 대기
                try:
                    short_wait.until(
                        lambda d: len(
                            d.find_elements(By.CSS_SELECTOR, ".og-div")
                        ) > og_count_before
                    )
                except Exception:
                    # OG 카드가 생성되지 않았을 때 상태를 로그에 남긴다.
                    current_og_count = len(
                        driver.find_elements(By.CSS_SELECTOR, ".og-div")
                    )
                
                    print(
                        f"OG 카드 생성 실패: 기존 {og_count_before}개 / "
                        f"현재 {current_og_count}개",
                        flush=True,
                    )
                
                    print("===== OG 생성 실패 시점 HTML =====", flush=True)
                    print(editor.get_attribute("innerHTML"), flush=True)
                
                    raise

                print("OG 생성 완료", flush=True)

                # OG 카드 뒤에는 일반 모드에서 커서가 안정적으로 놓이지
                # 않을 수 있다. HTML 모드에서 다음 내용을 위한 빈 문단을
                # 직접 추가한 뒤 다시 일반 에디터 모드로 돌아온다.
                if not is_last_line:
                    html_button.click()

                    html_area = wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".note-codable"),
                        )
                    )

                    driver.execute_script(
                        """
                        const area = arguments[0];
                        area.value += '<p><br></p>';
                        area.dispatchEvent(
                            new Event('input', { bubbles: true })
                        );
                        area.dispatchEvent(
                            new Event('change', { bubbles: true })
                        );
                        """,
                        html_area,
                    )

                    html_button.click()

                    editor = wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".note-editable"),
                        )
                    )
                    
                    # HTML 모드 전환 후에도 다음 빈 문단의 끝에서 계속 입력한다.
                    editor.click()
                    editor.send_keys(Keys.CONTROL, Keys.END)

                # URL 뒤에는 별도의 Enter를 보내지 않는다.
                # 위에서 추가한 <p><br></p>가 다음 입력 위치를 만든다.
                continue

            # 일반 텍스트와 빈 줄은 다음 줄로 이동한다.
            # 마지막 줄 뒤에는 불필요한 줄바꿈을 넣지 않는다.
            if not is_last_line:
                editor.send_keys(Keys.ENTER)

        print(f"[시간] 본문입력 : {time.perf_counter() - t:.2f}초", flush=True)
        t = time.perf_counter()

        # ============================================
        # 저장 전 HTML 확인
        # ============================================
        html_button.click()

        html_area = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-codable"),
            )
        )

        print("===== 저장 직전 HTML =====", flush=True)
        print(html_area.get_attribute("value"), flush=True)

        # 저장 전 일반 에디터 모드로 복귀하여 HTML 변경 내용을 확정한다.
        html_button.click()

        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-editable"),
            )
        )

        # ============================================
        # 수정 버튼 클릭
        # ============================================
        write_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn_blue.write"),
            )
        )
        write_button.click()

        print(f"[시간] 저장 : {time.perf_counter() - t:.2f}초", flush=True)

        return {
            "success": True,
        }

    except Exception as e:
        traceback.print_exc()

        return {
            "success": False,
            "message": str(e),
        }

    finally:
        elapsed = time.perf_counter() - start

        print(f"[modify_post] 실행시간: {elapsed:.2f}초", flush=True)

        driver.quit()
