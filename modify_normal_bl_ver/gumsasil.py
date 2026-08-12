"""G열의 URL을 병렬로 처리하는 실행 스크립트.

필수 환경 변수:
  GOOGLE_CREDENTIALS : 서비스 계정 JSON 문자열
  TARGET_SHEET       : 처리할 워크시트 이름

선택 환경 변수:
  SPREADSHEET_ID     : 대상 스프레드시트 ID
  MAX_WORKERS        : 동시 실행 수 (기본 20)
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import gspread
from google.oauth2.service_account import Credentials

from gumsa import extract_links


START_ROW = 5
URL_COLUMN = 7  # G열
DEFAULT_SPREADSHEET_ID = "1_4rB1Tk248VBqkMT6MhywlV-_m0hitwWv2MkiQ9hzAU"


def process_url(row: int, url: str):
    """행 번호를 보존한 채 gumsa.extract_links를 실행한다."""
    try:
        return row, url, extract_links(url), None
    except Exception as error:  # 한 URL 실패가 전체 실행을 멈추지 않게 함
        return row, url, None, error


def result_value(result) -> str:
    """extract_links의 반환값을 같은 행의 L열에 기록할 문자열로 변환한다."""
    if result is None:
        return "결과 없음"

    if isinstance(result, (list, tuple, set)):
        values = [str(value) for value in result if value is not None]
        return "\n".join(values) if values else "결과 없음"

    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)

    return str(result)


def main():
    started_at = time.time()

    credentials = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(
        os.getenv("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)
    ).worksheet(os.environ["TARGET_SHEET"])

    # G열을 읽고, 5행 이후에서 URL이 있는 행만 선별한다.
    g_values = worksheet.col_values(URL_COLUMN)
    targets = [
        (row, value.strip())
        for row, value in enumerate(g_values[START_ROW - 1 :], start=START_ROW)
        if value.strip()
    ]

    print(f"처리 대상: {len(targets)}개")
    if not targets:
        return

    max_workers = int(os.getenv("MAX_WORKERS", "20"))
    succeeded = 0
    failed = 0
    completed_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_url, row, url) for row, url in targets]

        for future in as_completed(futures):
            row, url, result, error = future.result()
            if error is not None:
                failed += 1
                print(f"실패 | {row}행 | {url} | {error}")
                continue

            succeeded += 1
            print(f"완료 | {row}행 | {url} | {result}")
            completed_results.append((row, result_value(result)))

    # 결과는 원본 URL이 있는 행의 L열에 기록한다.
    for row, value in completed_results:
        worksheet.update(range_name=f"L{row}", values=[[value]])

    elapsed = time.time() - started_at
    print(f"완료: 성공 {succeeded}개, 실패 {failed}개, 소요 {elapsed:.2f}초")


if __name__ == "__main__":
    main()
