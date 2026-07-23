import os
import json

import gspread
from google.oauth2.service_account import Credentials

from login_modify_normal_bl import modify_post


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = Credentials.from_service_account_info(
    creds_info,
    scopes=SCOPES
)

gc = gspread.authorize(creds)

spreadsheet = gc.open(
    os.environ["SPREADSHEET_NAME"]
)

worksheet = spreadsheet.worksheet(
    os.environ["TARGET_SHEET"]
)

user_id = os.environ["CAT_ID"]
user_pw = os.environ["CAT_PW"]

# 작업할 행 번호
row = int(os.environ["ROW"])

# G열 : 수정 URL
modify_url = worksheet.acell(f"G{row}").value

# H열 : 수정 본문
text = worksheet.acell(f"H{row}").value

# 내용이 없으면 작업하지 않음
if not (text or "").strip():
    print(f"H{row}가 비어 있어 작업을 건너뜁니다.")
    exit()

text = text.replace("§", "\n\n")

# URL도 없으면 작업하지 않음
if not (modify_url or "").strip():
    worksheet.update(
        range_name=f"I{row}",
        values=[["실패 : URL 없음"]]
    )
    exit()

result = modify_post(
    user_id,
    user_pw,
    modify_url,
    text
)

if result["success"]:
    worksheet.update(
        range_name=f"I{row}",
        values=[["완료"]]
    )
else:
    worksheet.update(
        range_name=f"I{row}",
        values=[[f"실패 : {result.get('message', '알 수 없는 오류')}"]]
    )
