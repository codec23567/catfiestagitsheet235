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

urls = worksheet.col_values(3)
dates = worksheet.col_values(5)
authors = worksheet.col_values(6)

# urls 길이에 맞게 부족한 부분 채우기
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

    if result["deleted"]:
        dates[row - 1] = "삭제됨"
        authors[row - 1] = ""

    elif result["date"] and result["author"]:
        dates[row - 1] = result["date"]
        authors[row - 1] = result["author"]

date_values = [[d] for d in dates[start_row - 1:]]
author_values = [[a] for a in authors[start_row - 1:]]

worksheet.update(
    range_name=f"E{start_row}:E{start_row + len(date_values) - 1}",
    values=date_values
)

worksheet.update(
    range_name=f"F{start_row}:F{start_row + len(author_values) - 1}",
    values=author_values
)



print("완료")

