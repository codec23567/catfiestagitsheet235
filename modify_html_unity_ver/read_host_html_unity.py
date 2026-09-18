import os
import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

from login_modify_html_unity import modify_post
from workflow_config import WORKFLOW_CELLS


def to_modify_url(url):
    url = str(url or "").strip()

    # 모바일 게시글 URL 형식: https://m.dcinside.com/board/catfiesta/58
    match = re.fullmatch(
        r"https://m\.dcinside\.com/board/([^/]+)/(\d+)",
        url,
    )

    if match:
        gallery_id = match.group(1)
        post_no = match.group(2)

        return (
            "https://gall.dcinside.com/mgallery/board/modify/"
            f"?id={gallery_id}&no={post_no}"
        )

    # 이미 PC 수정 URL인 경우 등은 변환하지 않고 그대로 사용
    return url


def run(workflow_name):

    if workflow_name not in WORKFLOW_CELLS:
        print(f"알 수 없는 워크플로우: {workflow_name}")
        sys.exit(1)

    cells = WORKFLOW_CELLS[workflow_name]

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

    user_id = os.environ["CAT_ID"]
    user_pw = os.environ["CAT_PW"]

    worksheet.update(
        range_name=cells["status_cell"],
        values=[["실행중"]]
    )

    print("실행중")

    modify_url = worksheet.acell(cells["url_cell"]).value

    if modify_url:
        modify_url = modify_url.strip()
    else:
        modify_url = ""

    html = worksheet.acell(cells["html_cell"]).value or ""

    # "정상적으로 할 일이 없어서 끝남"이 아니라
    # 원래 있어야 할 URL이 없는 비정상 상황이므로 실패로 처리한다.
    if not modify_url:
        print("수정 URL이 없습니다.")

        worksheet.update(
            range_name=cells["status_cell"],
            values=[["실패 : 수정 URL이 없습니다."]]
        )

        sys.exit(1)

    modify_url = to_modify_url(modify_url)

    print(f"수정 URL: {modify_url}")

    result = modify_post(
        user_id,
        user_pw,
        modify_url,
        html
    )

    if result["success"]:

        # 한국 시간 기준 완료 시각
        completed_at = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%m/%d %H:%M:%S")

        worksheet.update(
            range_name=cells["status_cell"],
            values=[["완료"]]
        )

        worksheet.update(
            range_name=cells["done_cell"],
            values=[[completed_at]]
        )

        print(f"완료 : {completed_at}")

    else:

        message = result.get("message", "알 수 없는 오류")

        worksheet.update(
            range_name=cells["status_cell"],
            values=[[f"실패 : {message}"]]
        )

        print(f"실패 : {message}")

        sys.exit(1)  # webhook.py가 감지해서 깃허브 백업으로 전환 가능


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 read_host_html_unity.py <workflow_name>")
        sys.exit(1)

    run(sys.argv[1])
