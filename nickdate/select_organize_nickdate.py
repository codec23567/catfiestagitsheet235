import os
import json
import time

import gspread
from google.oauth2.service_account import Credentials
from nickdate_test import extract_nickdate
from concurrent.futures import ThreadPoolExecutor

# 프로그램 시작 시간
program_start = time.time()

# Google Sheets API 권한
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# GitHub Secret에 저장한 서비스 계정 정보로 인증
credentials = Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_CREDENTIALS"]),
    scopes=SCOPES
)

gc = gspread.authorize(credentials)

# 작업할 스프레드시트 열기
spreadsheet = gc.open_by_key(
    "13Hp2IqBFzHE5L4xqGpieu-GVu0mA79fV06xYuFfnSB0"
)

worksheet = spreadsheet.worksheet(
    os.environ["TARGET_SHEET"]
)

# 실제 데이터가 시작되는 행
start_row = 5

# C열(URL), F열(날짜), G열(작성자) 읽기
# [새 구조] 날짜 E열 -> F열, 작성자 F열 -> G열로 이동
urls = worksheet.col_values(3)
dates = worksheet.col_values(6)
authors = worksheet.col_values(7)

# F/G열 길이가 부족하면 빈 문자열로 맞춰줌
while len(dates) < len(urls):
    dates.append("")

while len(authors) < len(urls):
    authors.append("")

# 크롤링 대상 URL과 행 번호 저장
requests = []
target_rows = []

# 크롤링 대상 찾기
for row in range(start_row, len(urls) + 1):

    url = urls[row - 1].strip()

    date = dates[row - 1] if row - 1 < len(dates) else ""
    author = authors[row - 1] if row - 1 < len(authors) else ""

    # URL이 없으면 건너뜀
    if not url:
        continue

    # 디시인사이드 URL만 처리
    if "dcinside" not in url:
        continue

    # 날짜나 작성자가 비어있는 경우
    is_clear = (date == "") or (author == "")

    # 이전 실행에서 retry로 남은 경우
    is_retry = (date == "retry")

    # 크롤링 대상 추가
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

# 처음에는 전체 대상이 재시도 목록
pending_requests = requests[:]
pending_rows = target_rows[:]

while pending_requests and current_try < MAX_RETRIES:

    print(f"\n===== {current_try + 1}차 시도 =====")

    batch_start = time.time()

    # 병렬 크롤링
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(extract_nickdate, pending_requests))

    batch_time = time.time() - batch_start

    print(
        f"[전체] {len(pending_requests)}개 URL 병렬 처리 완료 : "
        f"{batch_time:.2f}초",
        flush=True
    )

    # 다음 재시도 대상
    next_pending_requests = []
    next_pending_rows = []

    # 결과 처리
    for row, url, result in zip(pending_rows, pending_requests, results):

        # 삭제된 게시물
        if result["deleted"]:
            dates[row - 1] = "삭제됨"
            authors[row - 1] = ""
            continue

        # 정상 크롤링 성공
        if result["date"] and result["author"]:
            dates[row - 1] = result["date"]
            authors[row - 1] = result["author"]
            continue

        # 실패 → 다음 재시도 목록으로 이동
        print(f"재시도 대상 : {url}")

        next_pending_requests.append(url)
        next_pending_rows.append(row)

    # 다음 반복에서 실패한 URL만 다시 시도
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

# [새 구조] 날짜 -> F열, 작성자 -> G열
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
