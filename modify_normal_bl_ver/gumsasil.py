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
NAME_COLUMN = 2  # B열
LINK_COLUMN = 3  # C열
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


def select_targets(b_values, c_values, g_values):
    """연속된 같은 B열 그룹에서 C열 값이 3개 이상인 G열 URL만 선별한다."""
    last_row_count = max(len(b_values), len(c_values), len(g_values))
    targets = []
    index = START_ROW - 1

    while index < last_row_count:
        name = b_values[index].strip() if index < len(b_values) else ""

        # B열이 비어 있으면 그룹으로 처리하지 않고 다음 행으로 넘어간다.
        if not name:
            index += 1
            continue

        # 같은 B열 값이 연속되는 범위를 하나의 그룹으로 찾는다.
        group_end = index + 1
        while group_end < last_row_count:
            next_name = (
                b_values[group_end].strip()
                if group_end < len(b_values)
                else ""
            )
            if next_name != name:
                break
            group_end += 1

        # 그룹 내부에서 C열이 비어 있지 않은 값의 개수를 센다.
        link_count = sum(
            1
            for row_index in range(index, group_end)
            if row_index < len(c_values) and c_values[row_index].strip()
        )

        # C열 링크가 3개 이상인 그룹의 G열 URL만 처리 대상으로 추가한다.
        if link_count >= 3:
            for row_index in range(index, group_end):
                url = (
                    g_values[row_index].strip()
                    if row_index < len(g_values)
                    else ""
                )
                if url:
                    targets.append((row_index + 1, url))

        index = group_end

    return targets


def main():
    started_at = time.time()

    credentials = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    worksheet = gspread.authorize(credentials).open_by_key(
        os.getenv("SPREADSHEET_ID", DEFAULT_SPREADSHEET_ID)
    ).worksheet(os.environ["TARGET_SHEET"])

    # B/C/G열을 읽어, B열의 연속 그룹별 C열 링크 개수로 처리 대상을 선별한다.
    b_values = worksheet.col_values(NAME_COLUMN)
    c_values = worksheet.col_values(LINK_COLUMN)
    g_values = worksheet.col_values(URL_COLUMN)
    targets = select_targets(b_values, c_values, g_values)

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
