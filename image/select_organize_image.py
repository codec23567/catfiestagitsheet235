import os
import json
import sys

import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# [변경] requests -> target_urls
# (requests 라이브러리명과 겹쳐서 나중에 import requests 추가 시
#  변수가 라이브러리를 가려버리는 사고를 방지)
target_urls = []

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

    target_urls.append(url)

print("이미지 추출 대상 :", len(target_urls))

for url in target_urls:
    print(url)


# -------------------------------------------------
# 병렬 이미지 추출 + 실패한 URL만 재시도 (최대 3회)
# -------------------------------------------------
# [변경 사항 - nickdate 방식 도입]
#  1) 개별 URL이 실패해도 전체를 즉시 중단하지 않고,
#     실패한 URL만 다음 라운드에서 재시도한다 (최대 3회).
#  2) "삭제된 글"(regex_test.py가 deleted=True로 알려줌)은
#     재시도해도 의미가 없으므로 즉시 "이미지 0개"로 확정하고
#     재시도 대상에서 제외한다.
#  3) 재시도를 다 써도 여전히 실패하는 URL이 남으면,
#     J열을 쓰지 않고 sys.exit(1)로 실패를 알린다.
#     -> webhook.py가 감지해서 GitHub Actions 백업으로 전환 가능.
# -------------------------------------------------

MAX_RETRIES = 3

# url -> 최종 결과 dict
url_results = {}

pending_urls = target_urls[:]
current_try = 0

while pending_urls and current_try < MAX_RETRIES:

    print(f"\n===== 이미지 추출 {current_try + 1}차 시도 (대상 {len(pending_urls)}개) =====")

    next_pending = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {
            executor.submit(extract_images, url): url
            for url in pending_urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                url_results[url] = future.result()
            except Exception as e:
                print(f"[재시도 대상] {url} : {e}", flush=True)
                next_pending.append(url)

    pending_urls = next_pending
    current_try += 1

# 재시도를 다 써도 실패가 남았는지 확인
if pending_urls:
    print(
        f"[오류] {len(pending_urls)}개 URL이 {MAX_RETRIES}회 재시도 후에도 "
        f"실패했습니다. 시트를 갱신하지 않고 실행을 중단합니다.",
        flush=True
    )
    for url in pending_urls:
        print(f"  - 실패: {url}", flush=True)
    sys.exit(1)  # webhook.py가 감지 -> GitHub 백업으로 전환

# -------------------------------------------------
# [추가] 삭제되지 않았는데 이미지가 0개인 URL 검사
# -------------------------------------------------
# 크롤링 자체는 성공(예외 없음)했지만, 삭제된 글도 아닌데
# 정규식에 매칭되는 이미지가 하나도 없는 경우가 있다.
# - 진짜로 이미지가 없는 글일 수도 있고
# - viewimage.php가 아닌 다른 형식이라 정규식이 못 잡은 것일 수도 있다
# 둘을 구분할 방법이 아직 없으므로, 일단 "의심스러운 상황"으로 보고
# 시트를 갱신하지 않고 실패 처리해서 GitHub 백업으로 넘어가게 한다.
# -------------------------------------------------

suspicious_empty_urls = [
    url for url in target_urls
    if not url_results.get(url, {}).get("deleted", False)
    and len(url_results.get(url, {}).get("images", [])) == 0
]

if suspicious_empty_urls:
    print(
        f"[의심] 삭제되지 않았는데 이미지가 0개인 URL이 "
        f"{len(suspicious_empty_urls)}개 있습니다. 정규식이 못 잡았을 "
        f"가능성이 있어 시트를 갱신하지 않고 실행을 중단합니다.",
        flush=True
    )
    for url in suspicious_empty_urls:
        print(f"  - {url}", flush=True)
    sys.exit(1)  # webhook.py가 감지 -> GitHub 백업으로 전환

# -------------------------------------------------
# 원래 순서(target_urls) 그대로 이미지 리스트 조립
# -------------------------------------------------

img_list = []

for url in target_urls:
    result = url_results.get(url, {"images": [], "deleted": False})

    if result.get("deleted"):
        print(f"[삭제됨] {url}", flush=True)
        continue  # 삭제된 글은 이미지 0개로 확정, 리스트에 아무것도 추가 안 함

    img_list.extend(result.get("images", []))

# 위에서 이미 "삭제 안 됐는데 이미지 0개"인 경우를 걸러냈으므로,
# 여기 도달했다면 img_list가 비어있는 건 "URL 자체가 없었거나
# 전부 삭제된 글"인 경우뿐이다.
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
