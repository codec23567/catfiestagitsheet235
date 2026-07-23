import os
import json

import gspread
from google.oauth2.service_account import Credentials


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
# 작업 목록 생성
# -------------------------------------------------

rows = worksheet.get("H5:H")

jobs = []

for idx, row in enumerate(rows, start=5):

    text = (row[0] if row else "").strip()

    # H열이 비어있으면 건너뜀
    if not text:
        continue

    # URL도 있어야 함
    url = (worksheet.acell(f"G{idx}").value or "").strip()

    if not url:
        continue

    jobs.append({
        "row": idx
    })


# -------------------------------------------------
# GitHub Matrix 출력
# -------------------------------------------------

print(json.dumps({
    "include": jobs
}))
