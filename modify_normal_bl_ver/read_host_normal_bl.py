import json
import os
import re

import gspread
from google.oauth2.service_account import Credentials

from login_modify_multiple import create_driver, login, modify_post


# -------------------------------------------------
# Google Sheets 인증
# -------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

credentials = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_CREDENTIALS"]),
    scopes=SCOPES,
)

gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(
    "13Hp2IqBFzHE5L4xqGpieu-GVu0mA79fV06xYuFfnSB0"
)

worksheet = spreadsheet.worksheet(
    os.environ["TARGET_SHEET"]
)


# -------------------------------------------------
# GitHub Secrets
# -------------------------------------------------

user_id = os.environ["CAT_ID"]
user_pw = os.environ["CAT_PW"]


# -------------------------------------------------
# URL 변환
# -------------------------------------------------

def to_modify_url(url):
    url = str(url or "").strip()

    # 모바일 게시글 URL
    # https://m.dcinside.com/board/catfiesta/58
    match = re.fullmatch(
        r"https://m\.dcinside\.com/board/([^/]+)/(\d+)",
        url,
    )

    if match:
        gallery_id = match.group(1)
        post_no = match.group(2)

        return (
            "https://gall.dcinside.com/mgallery/board/modify/"
            f"?id={gallery_id}&no={post_no}"
        )

    # 이미 PC 수정 URL인 경우 등은 그대로 사용
    return url


# -------------------------------------------------
# G/H열에서 작업 대상 찾기
# -------------------------------------------------

rows = worksheet.get("G:H")
tasks = []

for status_row, row in enumerate(rows, start=1):
    g_value = str(row[0] if len(row) >= 1 else "").strip()

    # G열이 불일치인 행만 처리
    if g_value != "불일치":
        continue

    # 첫 행에는 바로 위 행이 없으므로 건너뜀
    if status_row == 1:
        print("G1은 불일치 상태로 처리할 수 없습니다.", flush=True)
        continue

    # 바로 위 행의 G/H를 가져옴
    previous_row = rows[status_row - 2]

    post_url = str(
        previous_row[0] if len(previous_row) >= 1 else ""
    ).strip()

    post_text = str(
        previous_row[1] if len(previous_row) >= 2 else ""
    ).replace("§", "\n\n")

    modify_url = to_modify_url(post_url)

    if not modify_url:
        print(
            f"G{status_row}: 바로 위 행의 게시글 URL이 비어 있어 건너뜁니다.",
            flush=True,
        )
        continue

    tasks.append(
        {
            "status_row": status_row,
            "modify_url": modify_url,
            "text": post_text,
        }
    )


# -------------------------------------------------
# 작업할 항목이 없으면 종료
# -------------------------------------------------

if not tasks:
    print("처리할 '불일치' 작업이 없습니다.", flush=True)
    raise SystemExit(0)

print(f"처리할 작업 수: {len(tasks)}개", flush=True)


# -------------------------------------------------
# Chrome 실행 및 로그인: 전체 작업에서 1회
# -------------------------------------------------

driver = None

try:
    driver = create_driver()
    login(driver, user_id, user_pw)

    # -------------------------------------------------
    # 게시글 순차 수정
    # -------------------------------------------------

    for task in tasks:
        status_row = task["status_row"]
        modify_url = task["modify_url"]
        text = task["text"]

        print(
            f"===== G{status_row} 작업 시작 =====",
            flush=True,
        )
        print(f"수정 URL: {modify_url}", flush=True)

        result = modify_post(
            driver,
            modify_url,
            text,
        )

        # 성공한 경우에만 상태 셀을 작업완료로 변경
        if result.get("success", False):
            worksheet.update(
                range_name=f"G{status_row}",
                values=[["작업완료"]],
            )

            print(
                f"G{status_row}: 작업완료",
                flush=True,
            )

        # 실패하면 불일치 상태를 그대로 둠
        else:
            message = result.get(
                "message",
                "알 수 없는 오류",
            )

            print(
                f"G{status_row}: 실패. "
                f"'불일치' 상태를 유지합니다. {message}",
                flush=True,
            )

finally:
    if driver:
        driver.quit()
        print("Chrome 종료", flush=True)
