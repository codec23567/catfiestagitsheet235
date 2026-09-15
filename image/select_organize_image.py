import os
import json
import sys

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

    # [변경] regex_test.py의 extract_images()가 이제 실패 시 조용히
    # []을 반환하지 않고 예외를 그대로 던지도록(raise) 바뀌었다.
    # 그 예외가 여기까지 전달되면, 로그에 명확히 남기고 sys.exit(1)로
    # 이번 실행이 실패했음을 확실히 알린다.
    # (참고: try/except로 감싸지 않아도 예외가 나면 파이썬은 기본적으로
    #  비정상 종료(exit code 1)되지만, 여기서는 실패 상황임을 로그에
    #  명확히 남기기 위해 명시적으로 처리한다.)
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:

            results = list(
                executor.map(
                    extract_images,
                    requests
                )
            )

    except Exception as e:
        print(f"[오류] 이미지 추출 중 실패로 이번 실행을 중단합니다: {e}", flush=True)
        sys.exit(1)  # [추가] 실패로 명확히 알림 -> webhook.py가 감지 가능

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
