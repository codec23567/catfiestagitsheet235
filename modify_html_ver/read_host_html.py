import os
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

from login_modify_html import modify_post


# -------------------------------------------------
# 모바일 게시글 URL → PC 수정 URL 변환
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
# Google Sheets 인증
# -------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

credentials = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_CREDENTIALS"]),
    scopes=SCOPES
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
# 실행 상태 기록
# -------------------------------------------------

worksheet.update(
    range_name="I9",
    values=[["실행중"]]
)

print("실행중")


# -------------------------------------------------
# 시트 데이터 읽기
# -------------------------------------------------

modify_url = worksheet.acell("C3").value

if modify_url:
    modify_url = modify_url.strip()
else:
    modify_url = ""

html = worksheet.acell("I5").value or ""


# URL이 없으면 종료
if not modify_url:
    print("수정 URL이 없습니다.")
    exit()


# -------------------------------------------------
# 수정 URL 변환
# -------------------------------------------------

modify_url = to_modify_url(modify_url)

print(f"수정 URL: {modify_url}")


# -------------------------------------------------
# 게시글 수정
# -------------------------------------------------

result = modify_post(
    user_id,
    user_pw,
    modify_url,
    html
)


# -------------------------------------------------
# 결과 기록
# -------------------------------------------------

if result["success"]:

    # 한국 시간 기준 완료 시각
    completed_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime("%m/%d %H:%M:%S")

    worksheet.update(
        range_name="I9",
        values=[["완료"]]
    )

    worksheet.update(
        range_name="I10",
        values=[[completed_at]]
    )

    print(f"완료 : {completed_at}")

else:

    message = result.get("message", "알 수 없는 오류")

    worksheet.update(
        range_name="I9",
        values=[[f"실패 : {message}"]]
    )

    print(f"실패 : {message}")