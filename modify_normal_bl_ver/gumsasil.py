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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import gspread
from google.oauth2.service_account import Credentials

from gumsa import extract_links


START_ROW = 5
NAME_COLUMN = 2  # B열: 그룹 시작 이름
LINK_COLUMN = 3  # C열: 개별 링크
URL_COLUMN = 7  # G열: 모음집 링크
DEFAULT_SPREADSHEET_ID = "13Hp2IqBFzHE5L4xqGpieu-GVu0mA79fV06xYuFfnSB0"


def process_url(row: int, url: str):
    """행 번호를 보존한 채 gumsa.extract_links를 실행한다."""
    try:
        return row, url, extract_links(url), None
    except Exception as error:
        return row, url, None, error


def result_links(result) -> list[str]:
    """extract_links 결과를 비교 가능한 링크 목록으로 정리한다."""
    if result is None:
        return []

    if isinstance(result, (list, tuple, set)):
        return [str(value).strip() for value in result if str(value).strip()]

    # extract_links가 줄바꿈 문자열을 반환하는 경우도 처리한다.
    return [value.strip() for value in str(result).splitlines() if value.strip()]


def select_targets(b_values, c_values, g_values):
    """B열 그룹별 C열 링크와 G열 모음집 링크를 처리 대상으로 선별한다."""
    last_row_count = max(len(b_values), len(c_values), len(g_values))
    targets = []
    group_start = START_ROW - 1

    while group_start < last_row_count:
        group_name = (
            b_values[group_start].strip()
            if group_start < len(b_values)
            else ""
        )

        # B열이 빈 행은 이전 그룹에 포함되므로 그룹 시작점으로 처리하지 않는다.
        if not group_name:
            group_start += 1
            continue

        # 다음 B열 이름이 나오기 직전까지를 하나의 그룹으로 잡는다.
        group_end = group_start + 1
        while group_end < last_row_count:
            next_name = (
                b_values[group_end].strip()
                if group_end < len(b_values)
                else ""
            )
            if next_name:
                break
            group_end += 1

        # 그룹 전체 C열의 비어 있지 않은 링크를 모은다.
        c_links = [
            c_values[row_index].strip()
            for row_index in range(group_start, group_end)
            if row_index < len(c_values) and c_values[row_index].strip()
        ]

        # 모음집 링크는 그룹 시작 행의 G열에 있다고 본다.
        group_url = (
            g_values[group_start].strip()
            if group_start < len(g_values)
            else ""
        )

        # C열 링크가 3개 이상이고, G열 모음집 링크가 있을 때만 처리한다.
        if len(c_links) >= 3 and group_url:
            targets.append(
                {
                    "row": group_start + 1,
                    "url": group_url,
                    "c_links": c_links,
                }
            )

        group_start = group_end

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

    # B열 그룹과 C열 링크 수를 기준으로 G열 조사 대상을 선정한다.
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
    status_updates = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_url, target["row"], target["url"]): target
            for target in targets
        }

        for future in as_completed(futures):
            target = futures[future]
            row, url, result, error = future.result()

            if error is not None:
                failed += 1
                print(f"실패 | {row}행 | {url} | {error}")
                continue

            succeeded += 1
            extracted_links = result_links(result)

            # 순서와 중복 개수까지 포함해 C열 링크와 조사 결과를 비교한다.
            if Counter(extracted_links) == Counter(target["c_links"]):
                status_updates.append((row, "작업 완료"))
                print(f"작업 완료 | {row}행 | C열 링크와 결과가 일치")
            else:
                status_updates.append((row, "불일치"))
                print(
                    f"불일치 | {row}행 | "
                    f"C열 {len(target['c_links'])}개 / 결과 {len(extracted_links)}개"
                )

    # G열의 조사 링크 바로 아래 행에 비교 결과를 기록한다.
    for row, status in status_updates:
        worksheet.update(range_name=f"G{row + 1}", values=[[status]])

    elapsed = time.time() - started_at
    print(f"완료: 성공 {succeeded}개, 실패 {failed}개, 소요 {elapsed:.2f}초")


if __name__ == "__main__":
    main()
