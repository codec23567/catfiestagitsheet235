import os
import json

import gspread
from google.oauth2.service_account import Credentials
from nickdate_test import extract_nickdate
from concurrent.futures import ThreadPoolExecutor

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

worksheet = spreadsheet.sheet1



start_row = 5

urls = worksheet.col_values(3)      # C열
dates = worksheet.col_values(5)     # E열
authors = worksheet.col_values(6)   # F열

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

    is_clear = (date == "") or (author == "")
    is_retry = (date == "retry")

    if is_clear or is_retry:
        requests.append(url)
        target_rows.append(row)

print("크롤링 대상 개수 :", len(requests))

for row, url in zip(target_rows, requests):
    print(row, url)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(extract_nickdate, requests))
    
print(f"결과 개수: {len(results)}")   # 추가

for row, result in zip(target_rows, results):
    print(row, result)

print("완료")

