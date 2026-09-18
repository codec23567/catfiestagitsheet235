import os
import json
import sys
import time

import gspread
from google.oauth2.service_account import Credentials
from nickdate_test import extract_nickdate
from concurrent.futures import ThreadPoolExecutor

program_start = time.time()

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

# 1~4행은 헤더/설정용이라 실제 데이터는 5행부터 시작
start_row = 5

# C열(URL), F열(날짜), G열(작성자)
urls = worksheet.col_values(3)
dates = worksheet.col_values(6)
authors = worksheet.col_values(7)

# gspread가 뒷부분 빈 셀은 반환하지 않으므로 urls 길이에 맞춰 채운다
while len(dates) < len(urls):
    dates.append("")

while len(authors) < len(urls):
    authors.append("")

requests = []
target_rows = []

for row in range(start_row, len(urls) + 1):

    url = urls[row - 1].strip()

    date = dates[row - 1] if row - 1 < len(dates) else ""
    author = authors[row - 1] if row - 1 < len(authors) else ""

    if not url:
        continue

    if "dcinside" not in url:
        continue

    # 아직 크롤링 안 됨(날짜/작성자 비어있음) 또는 지난 실행에서 실패해 "retry"로 남은 경우
    is_clear = (date == "") or (author == "")
    is_retry = (date == "retry")

    if is_clear or is_retry:
        requests.append(url)
        target_rows.append(row)

print("크롤링 대상 개수 :", len(requests))

for row, url in zip(target_rows, requests):
    print(row, url)

# ---------------------------------------------
# 최대 3회까지 실패한 URL만 재시도
# ---------------------------------------------

MAX_RETRIES = 3
current_try = 0

pending_requests = requests[:]
pending_rows = target_rows[:]

while pending_requests and current_try < MAX_RETRIES:

    print(f"\n===== {current_try + 1}차 시도 =====")

    batch_start = time.time()

    # 동시 요청 부하를 줄이기 위해 worker 수를 낮게 유지
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(extract_nickdate, pending_requests))

    batch_time = time.time() - batch_start

    print(
        f"[전체] {len(pending_requests)}개 URL 병렬 처리 완료 : "
        f"{batch_time:.2f}초",
        flush=True
    )

    next_pending_requests = []
    next_pending_rows = []

    for row, url, result in zip(pending_rows, pending_requests, results):

        if result["deleted"]:
            dates[row - 1] = "삭제됨"
            authors[row - 1] = ""
            continue

        if result["date"] and result["author"]:
            dates[row - 1] = result["date"]
            authors[row - 1] = result["author"]
            continue

        print(f"재시도 대상 : {url}")

        next_pending_requests.append(url)
        next_pending_rows.append(row)

    pending_requests = next_pending_requests
    pending_rows = next_pending_rows

    current_try += 1

# ---------------------------------------------
# 3번 시도 후에도 실패하면 retry 기록
# ---------------------------------------------

for row in pending_rows:
    dates[row - 1] = "retry"
    authors[row - 1] = ""

# ---------------------------------------------
# 결과를 Google Sheets에 저장
# ---------------------------------------------

sheet_start = time.time()

date_values = [[d] for d in dates[start_row - 1:]]
author_values = [[a] for a in authors[start_row - 1:]]

worksheet.update(
    range_name=f"F{start_row}:F{start_row + len(date_values) - 1}",
    values=date_values
)

worksheet.update(
    range_name=f"G{start_row}:G{start_row + len(author_values) - 1}",
    values=author_values
)

sheet_time = time.time() - sheet_start

print(
    f"[전체] Google Sheets 저장 : {sheet_time:.2f}초",
    flush=True
)

print(
    f"[전체] 프로그램 실행 : {time.time() - program_start:.2f}초",
    flush=True
)

print("완료")

# 3회 재시도 후에도 실패한 항목이 있으면 실패로 종료
# -> webhook.py가 감지해서 깃허브 백업으로 전환 가능
# "retry" 표시는 그대로 남아서 다음 실행 때도 재시도 대상이 된다
if pending_rows:
    print(
        f"[경고] {len(pending_rows)}개 항목이 "
        f"{MAX_RETRIES}회 재시도 후에도 실패했습니다.",
        flush=True
    )
    sys.exit(1)
