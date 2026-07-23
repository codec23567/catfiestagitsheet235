import os
import json
from urllib.parse import urlparse

import gspread
from google.oauth2.service_account import Credentials

from login_modify_normal_bl import modify_post


# -------------------------------------------------
# 모바일 URL -> 수정 URL 변환
# -------------------------------------------------

def convert_modify_url(url: str) -> str:
    path = urlparse(url).path.strip("/").split("/")

    # https://m.dcinside.com/board/{gallery_id}/{post_no}
    if len(path) >= 3 and path[0] == "board":
        gallery_id = path[1]
        post_no = path[2]

        return (
            f"https://gall.dcinside.com/mgallery/board/modify/"
            f"?id={gallery_id}&no={post_no}"
        )

    raise ValueError(f"지원하지 않는 URL 형식: {url}")


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
    "1_4rB1Tk248VBqkMT6MhywlV-_m0hitwWv2MkiQ9hzAU"
)

worksheet = spreadsheet.worksheet(
    os.environ["TARGET_SHEET"]
)


# -------------------------------------------------
# GitHub Secrets
# -------------------------------------------------

user_id = os.environ["CAT_ID"]
user_pw = os.environ["CAT_PW"]

row = int(os.environ["ROW"])


# -------------------------------------------------
# 시트 데이터 읽기
# -------------------------------------------------

modify_url = (worksheet.acell(f"G{row}").value or "").strip()

text = (
    worksheet.acell(f"H{row}").value or ""
).replace("§", "\n\n")


# URL이 없으면 종료

if not modify_url:
    worksheet.update(
        range_name=f"I{row}",
        values=[["URL 없음"]]
    )

    print(f"{row}행 : URL 없음")
    exit()


# -------------------------------------------------
# URL 변환
# -------------------------------------------------

try:
    modify_url = convert_modify_url(modify_url)

except Exception as e:

    worksheet.update(
        range_name=f"I{row}",
        values=[[f"URL 오류 : {e}"]]
    )

    print(f"{row}행 URL 오류 : {e}")
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
        range_name=f"I{row}",
        values=[["완료"]]
    )

    print(f"{row}행 완료")

else:

    message = result.get("message", "알 수 없는 오류")

    worksheet.update(
        range_name=f"I{row}",
        values=[[f"실패 : {message}"]]
    )

    print(f"{row}행 실패 : {message}")
