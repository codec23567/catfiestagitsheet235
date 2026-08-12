import os
import json

import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor

from regex_test import extract_images


# Google Sheets API 권한
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# GitHub Secret 인증
credentials = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_CREDENTIALS"]),
    scopes=SCOPES
)

gc = gspread.authorize(credentials)

# 스프레드시트 열기
spreadsheet = gc.open_by_key(
    "13Hp2IqBFzHE5L4xqGpieu-GVu0mA79fV06xYuFfnSB0"
)

worksheet = spreadsheet.worksheet(
    os.environ["TARGET_SHEET"]
)


# -------------------------------------------------
# K3:T3 링크 읽기
# -------------------------------------------------

row3 = worksheet.row_values(3)

requests = []

# K열(11) ~ T열(20)
for col in range(11, 21):

    index = col - 1

    if index >= len(row3):
        continue

    url = row3[index].strip()

    if not url:
        continue

    if "dcinside" not in url:
        continue

    requests.append(url)

print("이미지 추출 대상 :", len(requests))

for url in requests:
    print(url)


# -------------------------------------------------
# 병렬 이미지 추출
# -------------------------------------------------

img_list = []

if requests:

    with ThreadPoolExecutor(max_workers=10) as executor:

        results = list(
            executor.map(
                extract_images,
                requests
            )
        )

    for images in results:

        if images:
            img_list.extend(images)


# 기존 Apps Script와 동일한 처리

if len(img_list) == 0:
    img_list = ["본문 이미지 없음"]


# -------------------------------------------------
# B/K 읽기
# -------------------------------------------------

start_row = 5

last_row = len(worksheet.col_values(2))

if last_row < start_row:
    last_row = start_row

num_rows = last_row - start_row + 1

b_values = worksheet.get(
    f"B{start_row}:B{last_row}"
)

k_values = worksheet.get(
    f"K{start_row}:K{last_row}"
)

j_values = worksheet.get(
    f"J{start_row}:J{last_row}"
)


# 길이 보정

while len(b_values) < num_rows:
    b_values.append([""])

while len(k_values) < num_rows:
    k_values.append([""])

while len(j_values) < num_rows:
    j_values.append([""])

# J열의 빈 행([])을 [""]로 보정
for i in range(num_rows):
    if len(j_values[i]) == 0:
        j_values[i] = [""]

# -------------------------------------------------
# 기존 validBCount 매칭
# -------------------------------------------------

valid_b_count = 0

for i in range(num_rows):

    b = b_values[i][0] if b_values[i] else ""
    k = k_values[i][0] if k_values[i] else ""

    if b and str(b).strip():

        valid_b_count += 1

        if k and str(k).strip():

            if valid_b_count <= len(img_list):

                j_values[i][0] = img_list[valid_b_count - 1]

            else:

                j_values[i][0] = ""

    else:

        if k and str(k).strip():
            j_values[i][0] = ""


# -------------------------------------------------
# Google Sheets 저장
# -------------------------------------------------

worksheet.update(
    range_name=f"J{start_row}:J{last_row}",
    values=j_values
)

print("완료")
