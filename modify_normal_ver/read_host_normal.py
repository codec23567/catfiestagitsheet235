import os
import json

import gspread
from google.oauth2.service_account import Credentials

from login_modify_normal import modify_post


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
# 시트 데이터 읽기
# -------------------------------------------------

modify_url = worksheet.acell("M3").value

if modify_url:
    modify_url = modify_url.strip()

    # 모바일 게시글 URL을 PC 수정 URL로 변환
    match = re.fullmatch(
        r"https://m\.dcinside\.com/board/([^/]+)/(\d+)",
        modify_url
    )

    if match:
        gallery_id = match.group(1)
        post_no = match.group(2)

        modify_url = (
            "https://gall.dcinside.com/mgallery/board/modify/"
            f"?id={gallery_id}&no={post_no}"
        )
else:
    modify_url = ""

text = (worksheet.acell("M4").value or "").replace("§", "\n\n")


# URL이 없으면 종료
if not modify_url:
    print("수정 URL이 없습니다.")
    exit()


# -------------------------------------------------
# 게시글 수정
# -------------------------------------------------

result = modify_post(
    user_id,
    user_pw,
    modify_url,
    text
)


# -------------------------------------------------
# 결과 기록
# -------------------------------------------------

if result["success"]:

    worksheet.update(
        range_name="M7",
        values=[["완료"]]
    )

    print("완료")

else:

    message = result.get("message", "알 수 없는 오류")

    worksheet.update(
        range_name="M7",
        values=[[f"실패 : {message}"]]
    )

    print(f"실패 : {message}")
