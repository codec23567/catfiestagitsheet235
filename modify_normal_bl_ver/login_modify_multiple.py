from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import re
import time
import traceback
import html

LOGIN_URL = (
    "https://sign.dcinside.com/login"
    "?s_url=https://www.dcinside.com/"
)


def create_driver():
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Chrome 실행 속도를 위한 부가 기능 비활성화
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

    return webdriver.Chrome(options=options)


def login(driver, user_id, user_pw):
    print("★★★★★ 로그인 시작 ★★★★★", flush=True)

    start = time.perf_counter()

    wait = WebDriverWait(driver, 15)

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

    print(
        f"[시간] 로그인 : {time.perf_counter() - start:.2f}초",
        flush=True,
    )


def modify_post(driver, modify_url, text):
    print("★★★★★ 게시글 수정 시작 ★★★★★", flush=True)

    start = time.perf_counter()
    t = time.perf_counter()

    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 20)

    # html_button을 누를 때마다 HTML 모드 ⇄ 일반 에디터 모드가 토글된다.
    # HTML 모드에서 본문을 직접 조작한 뒤에는 다시 눌러 일반 모드로 복귀한다.

    try:
        # 수정 페이지 이동
        driver.get(modify_url)

        html_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='HTML']"),
            )
        )

        print(
            f"[시간] 수정페이지 : {time.perf_counter() - t:.2f}초",
            flush=True,
        )
        t = time.perf_counter()

        # 기존 본문 삭제
        html_button.click()

        html_area = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-codable"),
            )
        )

        html_area.clear()

        html_button.click()

        editor = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-editable"),
            )
        )

        # 커서를 맨 끝으로 이동
        editor.click()
        editor.send_keys(Keys.CONTROL, Keys.END)

        # 한 줄 전체가 URL인 경우에만 OG 카드를 생성한다
        url_pattern = re.compile(r"^https?://\S+$")
        lines = text.splitlines()

        for index, line in enumerate(lines):
            is_url = bool(url_pattern.fullmatch(line.strip()))
            is_last_line = index == len(lines) - 1

            print(f"입력: [{line}]", flush=True)

            # 일반 텍스트
            if not is_url:

                if not line:
                    # 빈 줄 → <p><br></p> 삽입
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

                    editor.click()
                    editor.send_keys(Keys.CONTROL, Keys.END)

                else:
                    # 일반 텍스트: 22pt + Bold로 스타일 추가
                    escaped_line = html.escape(line)  # HTML 특수문자 안전 처리

                    styled_html = (
                        '<p>'
                        '<span style="font-size: 22pt; '
                        'font-weight: 700;">'
                        f'{escaped_line}'
                        '</span>'
                        '</p>'
                    )

                    html_button.click()

                    html_area = wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".note-codable"),
                        )
                    )

                    driver.execute_script(
                        """
                        const area = arguments[0];
                        const html = arguments[1];

                        area.value += html;

                        area.dispatchEvent(
                            new Event('input', { bubbles: true })
                        );

                        area.dispatchEvent(
                            new Event('change', { bubbles: true })
                        );
                        """,
                        html_area,
                        styled_html,
                    )

                    html_button.click()

                    editor = wait.until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".note-editable"),
                        )
                    )

                    # HTML 삽입 후에도 반드시 맨 끝으로 이동
                    editor.click()
                    editor.send_keys(Keys.CONTROL, Keys.END)

                continue

            # URL: 일반 에디터에서 그대로 입력해 OG 카드를 생성한다
            print("URL 발견 - OG 카드 생성 시작", flush=True)

            # OG 카드 생성 여부를 확인하기 위해 현재 개수를 먼저 기록
            og_count_before = len(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    ".og-div",
                )
            )

            editor.click()
            editor.send_keys(line)

            driver.execute_script(
                "oglink('paste', false, '');"
            )

            # 새로운 OG 카드가 실제로 추가될 때까지 대기 (호출 성공 != 생성 성공)
            try:
                short_wait.until(
                    lambda d: len(
                        d.find_elements(
                            By.CSS_SELECTOR,
                            ".og-div",
                        )
                    ) > og_count_before
                )

            except Exception:
                current_og_count = len(
                    driver.find_elements(
                        By.CSS_SELECTOR,
                        ".og-div",
                    )
                )

                print(
                    f"OG 카드 생성 실패: "
                    f"기존 {og_count_before}개 / "
                    f"현재 {current_og_count}개",
                    flush=True,
                )

                print(
                    "===== OG 생성 실패 시점 HTML =====",
                    flush=True,
                )

                print(
                    editor.get_attribute("innerHTML"),
                    flush=True,
                )

                raise

            print("OG 생성 완료", flush=True)

            # URL 뒤에 다음 내용이 있으면 빈 문단 추가
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

                editor.click()
                editor.send_keys(Keys.CONTROL, Keys.END)

            # URL 뒤에는 Enter를 보내지 않음
            continue

        print(
            f"[시간] 본문입력 : "
            f"{time.perf_counter() - t:.2f}초",
            flush=True,
        )
        t = time.perf_counter()

        # 저장 전 디버그용 HTML 로그
        html_button.click()

        html_area = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-codable"),
            )
        )

        print(
            "===== 저장 직전 HTML =====",
            flush=True,
        )

        print(
            html_area.get_attribute("value"),
            flush=True,
        )

        html_button.click()

        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".note-editable"),
            )
        )

        # 저장 버튼 클릭
        write_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn_blue.write"),
            )
        )

        before_url = driver.current_url
        print(f"[클릭 전 URL] {before_url}", flush=True)

        write_button.click()

        # 최종적으로 저장이 성공했다고 볼 수 있는지 여부.
        # 아래 확인 과정에서 문제가 발견되면 False로 바뀐다.
        save_confirmed = False
        failure_reason = None

        # "확실히 정상적인 절차의 일부"라고 알려진 경고창 문구 목록.
        # 여기 있는 것만 안전하게 통과시킨다.
        # 새로운 정상 경고창을 발견하면 이 목록에 문구(일부)를 추가하면 된다.
        SAFE_ALERT_KEYWORDS = [
            "유튜브 링크가 포함되어 있습니다",
        ]

        # 1) 브라우저 네이티브 alert(경고창) 발생 여부 확인
        try:
            alert = WebDriverWait(driver, 3).until(
                EC.alert_is_present()
            )
            alert_text = alert.text
            print(f"[경고창 감지] {alert_text}", flush=True)
            alert.accept()

            # 알려진 안전한 경고창(예: 유튜브 링크 변환 확인창)이면
            # 확인만 하고 정상 진행. 그 외 낯선 경고창은 무슨 뜻인지
            # 모르므로 안전하게 실패로 처리.
            if any(keyword in alert_text for keyword in SAFE_ALERT_KEYWORDS):
                print(
                    "[정상 절차로 확인된 경고창] "
                    "확인만 하고 계속 진행합니다.",
                    flush=True,
                )
            else:
                failure_reason = (
                    f"알 수 없는 경고창 발생 (확인 필요): {alert_text}"
                )

        except Exception:
            print("[경고창 없음]", flush=True)

        # 2) URL 변경 여부 확인 (저장 성공 시 상세 페이지로 이동)
        try:
            WebDriverWait(driver, 10).until(
                EC.url_changes(before_url)
            )

            print(
                f"[클릭 후 URL 변경됨] {driver.current_url}",
                flush=True,
            )

            # URL이 바뀌었다면 저장 성공으로 간주
            save_confirmed = True

        except Exception:
            print(
                f"[URL 변경 없음] 현재 URL: {driver.current_url}",
                flush=True,
            )

            # 3) URL이 안 바뀐 경우, 페이지 내 에러 메시지 확인
            #    (실제 마크업에 맞게 선택자 조정 필요)
            error_elements = driver.find_elements(
                By.CSS_SELECTOR,
                ".error_msg, .alert_msg, .layer_error",
            )

            if error_elements:
                for el in error_elements:
                    print(f"[에러 메시지 감지] {el.text}", flush=True)

                # 에러 메시지가 실제로 화면에 보였다면 명백한 실패
                failure_reason = (
                    "저장 후 에러 메시지 감지: "
                    + " / ".join(el.text for el in error_elements)
                )
            else:
                print("[에러 메시지 요소 없음]", flush=True)

                # URL도 안 바뀌고 에러 메시지도 없다면,
                # 저장이 실제로 성공했다고 확신할 근거가 없으므로
                # 안전하게 실패로 처리한다.
                if failure_reason is None:
                    failure_reason = (
                        "저장 후 URL 변경 확인 실패 (에러 메시지도 없음)"
                    )

        # 4) 최종 상태 로그
        print(f"[최종 페이지 제목] {driver.title}", flush=True)
        print(f"[최종 URL] {driver.current_url}", flush=True)

        print(
            f"[시간] 저장 : "
            f"{time.perf_counter() - t:.2f}초",
            flush=True,
        )

        # 무조건 True를 반환하지 않고,
        # 실제로 저장이 확인됐는지에 따라 결과를 나눈다.
        if save_confirmed and failure_reason is None:
            return {
                "success": True,
            }
        else:
            return {
                "success": False,
                "message": failure_reason or "저장 확인 실패",
            }

    except Exception as e:
        traceback.print_exc()

        return {
            "success": False,
            "message": str(e),
        }

    finally:
        elapsed = time.perf_counter() - start

        print(
            f"[게시글 수정] 실행시간: "
            f"{elapsed:.2f}초",
            flush=True,
        )
