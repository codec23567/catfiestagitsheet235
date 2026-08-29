import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

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
# B/H열에서 작업 대상 찾기
#
# 구조: H{그룹시작행}=모음집 링크 / H{그룹시작행+1}=게시할 내용 / H{그룹시작행+2}=완료 날짜
# - B열에 값이 있는 행 = 그룹 시작 행
# - H(그룹시작행)에 링크가 없으면 대상 아님
# - H(그룹시작행+2)에 값(완료 날짜)이 있으면 이미 처리된 것으로 보고 건너뜀
# - gumsa(링크 일치 검증) 로직은 폐기 — 완료 날짜 유무만으로 판단
# -------------------------------------------------

START_ROW = 5
NAME_COL = 2  # B열
H_COL = 8     # H열

b_values = worksheet.col_values(NAME_COL)
h_values = worksheet.col_values(H_COL)

# 길이 보정
last_row = max(len(b_values), len(h_values), START_ROW)
while len(b_values) < last_row:
    b_values.append("")
while len(h_values) < last_row:
    h_values.append("")

tasks = []

for idx in range(START_ROW - 1, last_row):
    name = str(b_values[idx]).strip() if idx < len(b_values) else ""

    if not name:
        continue  # 그룹 시작 행이 아니면 건너뜀

    group_start_row = idx + 1  # 1-indexed 실제 시트 행 번호

    link = str(h_values[idx]).strip() if idx < len(h_values) else ""
    if not link:
        continue  # 모음집 링크가 없는 그룹은 대상 아님

    content_idx = idx + 1
    date_idx = idx + 2

    date_value = (
        str(h_values[date_idx]).strip()
        if date_idx < len(h_values)
        else ""
    )

    if date_value:
        continue  # 완료 날짜가 있으면 이미 처리된 것으로 간주, 건너뜀

    content_value = (
        str(h_values[content_idx]).strip()
        if content_idx < len(h_values)
        else ""
    )

    modify_url = to_modify_url(link)

    if not modify_url:
        print(
            f"{name} (H{group_start_row}): 모음집 링크 변환 실패, 건너뜁니다.",
            flush=True,
        )
        continue

    tasks.append(
        {
            "name": name,
            "date_row": date_idx + 1,  # 완료 날짜를 기록할 실제 시트 행 번호
            "modify_url": modify_url,
            "text": content_value.replace("§", "\n\n"),
        }
    )


# -------------------------------------------------
# 작업할 항목이 없으면 종료
# -------------------------------------------------

if not tasks:
    print("처리할 '모음집관리' 작업이 없습니다.", flush=True)
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
        name = task["name"]
        date_row = task["date_row"]
        modify_url = task["modify_url"]
        text = task["text"]

        print(
            f"===== {name} (H{date_row}) 작업 시작 =====",
            flush=True,
        )
        print(f"수정 URL: {modify_url}", flush=True)

        # 작업 시작 상태 - 완료 날짜 셀에 임시로 "실행중" 기록
        worksheet.update(
            range_name=f"H{date_row}",
            values=[["실행중"]],
        )

        print(f"{name}: 실행중", flush=True)

        result = modify_post(
            driver,
            modify_url,
            text,
        )

        # 성공한 경우: 완료 날짜 셀에 실제 완료 시각 기록
        if result.get("success", False):

            completed_at = datetime.now(
                ZoneInfo("Asia/Seoul")
            ).strftime("%m/%d %H:%M:%S")

            worksheet.update(
                range_name=f"H{date_row}",
                values=[[completed_at]],
            )

            print(
                f"{name}: 완료 / {completed_at}",
                flush=True,
            )

        # 실패한 경우: 완료 날짜 셀을 다시 비워서 다음 실행 때 재시도 대상이 되게 함
        else:
            message = result.get(
                "message",
                "알 수 없는 오류",
            )

            worksheet.update(
                range_name=f"H{date_row}",
                values=[[""]],
            )

            print(
                f"{name}: 실패. 완료 날짜를 비워 다음 실행 시 재시도되게 합니다. "
                f"{message}",
                flush=True,
            )

finally:
    if driver:
        driver.quit()
        print("Chrome 종료", flush=True)
