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

# C열(URL), F열(날짜), G열(작성자)를 API 한 번(batch_get)으로 읽는다.
# 행 번호 = 리스트 인덱스 + 1 이 되도록 1행부터 읽는다
raw_columns = worksheet.batch_get(["C1:C", "F1:F", "G1:G"])


def flatten(values):

    # 중간의 빈 셀은 [](빈 리스트)로 오므로 ""로 바꿔 한 줄짜리 리스트로 만든다
    return [row[0] if row else "" for row in values]


urls, dates, authors = (flatten(values) for values in raw_columns)

# gspread가 뒷부분 빈 셀은 반환하지 않으므로 urls 길이에 맞춰 채운다
while len(dates) < len(urls):
    dates.append("")

while len(authors) < len(urls):
    authors.append("")

target_urls = []
target_rows = []

for row in range(start_row, len(urls) + 1):

    url = urls[row - 1].strip()

    date = dates[row - 1] if row - 1 < len(dates) else ""
    author = authors[row - 1] if row - 1 < len(authors) else ""

    if not url:
        continue

    if "dcinside" not in url:
        continue

    # 삭제된 글은 작성자가 빈 값이라 아래 조건에 걸리므로, 먼저 제외한다
    # (안 그러면 삭제된 글을 실행할 때마다 다시 요청한다)
    if date == "삭제됨":
        continue

    # 아직 크롤링 안 됨(날짜/작성자 비어있음) 또는 지난 실행에서 실패해 "retry"로 남은 경우
    # ("retry" 행은 작성자가 항상 빈 값이라 이 조건에 함께 걸린다)
    if date == "" or author == "":
        target_urls.append(url)
        target_rows.append(row)

print("크롤링 대상 개수 :", len(target_urls))

for row, url in zip(target_rows, target_urls):
    print(row, url)

# ---------------------------------------------
# 최대 3회까지 실패한 URL만 재시도
# ---------------------------------------------

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 5
current_try = 0

pending_urls = target_urls[:]
pending_rows = target_rows[:]

while pending_urls and current_try < MAX_RETRIES:

    print(f"\n===== {current_try + 1}차 시도 =====")

    batch_start = time.time()

    # 동시 요청 부하를 줄이기 위해 worker 수를 낮게 유지
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(extract_nickdate, pending_urls))

    batch_time = time.time() - batch_start

    print(
        f"[전체] {len(pending_urls)}개 URL 병렬 처리 완료 : "
        f"{batch_time:.2f}초",
        flush=True
    )

    next_pending_urls = []
    next_pending_rows = []

    for row, url, result in zip(pending_rows, pending_urls, results):

        if result["deleted"]:
            dates[row - 1] = "삭제됨"
            authors[row - 1] = ""
            continue

        if result["date"] and result["author"]:
            dates[row - 1] = result["date"]
            authors[row - 1] = result["author"]
            continue

        print(f"재시도 대상 : {url}")

        next_pending_urls.append(url)
        next_pending_rows.append(row)

    pending_urls = next_pending_urls
    pending_rows = next_pending_rows

    current_try += 1

    # 곧바로 다시 요청하면 차단/제한이 풀리지 않은 채 또 실패하므로 잠시 기다린다 (5초, 10초)
    if pending_urls and current_try < MAX_RETRIES:

        wait = RETRY_WAIT_SECONDS * 2 ** (current_try - 1)

        print(f"{wait}초 뒤 재시도합니다", flush=True)

        time.sleep(wait)

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

# F열, G열을 API 한 번(batch_update)으로 쓴다 (update와 마찬가지로 값을 그대로 저장)
updates = []

if date_values:
    updates.append({
        "range": f"F{start_row}:F{start_row + len(date_values) - 1}",
        "values": date_values
    })

if author_values:
    updates.append({
        "range": f"G{start_row}:G{start_row + len(author_values) - 1}",
        "values": author_values
    })

if updates:
    worksheet.batch_update(updates)

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
