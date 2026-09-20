import os
import re
import json
import sys

import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed

from regex_test import extract_images


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# K3:T3 링크 중 이 글자가 들어 있는 링크(우리 사이트 catfiestasite 페이지)만 대상으로 한다
SITE_URL_MARKER = "catfiestasite"


# -------------------------------------------------
# 폼 고르기
# -------------------------------------------------
# 사이트의 캐릭터 카드에는 그 캐릭터의 모든 폼(1폼, 2폼, ...)이 들어 있다.
# 시트 D열(육성도) 값을 보고 그중 하나만 고른다.
#   - "2진", "3진", "4진" ... : N번째 폼 (폼 수보다 크면 경고 후 마지막 폼)
#   - "초본", "본능"          : 3번째 폼 (폼이 3개 미만이면 경고 후 마지막 폼)
#   - 빈 값                   : 마지막(최종) 폼
#   - 그 밖의 값              : 경고 후 마지막 폼
# -------------------------------------------------

def pick_form(forms, d_value, name=""):

    d_value = str(d_value or "").strip()

    match = re.fullmatch(r"(\d+)진", d_value)

    if match:

        number = int(match.group(1))

        if 1 <= number <= len(forms):
            return forms[number - 1]

        print(
            f"[경고] {name} : '{d_value}' 인데 폼이 {len(forms)}개뿐이라 "
            f"마지막 폼을 넣습니다",
            flush=True
        )
        return forms[-1]

    if d_value in ("초본", "본능"):

        if len(forms) >= 3:
            return forms[2]

        print(
            f"[경고] {name} : '{d_value}' 인데 폼이 {len(forms)}개뿐이라 "
            f"마지막 폼을 넣습니다",
            flush=True
        )
        return forms[-1]

    if d_value == "":
        return forms[-1]

    print(
        f"[경고] {name} : 알 수 없는 육성도 '{d_value}' 이라 마지막 폼을 넣습니다",
        flush=True
    )
    return forms[-1]


# -------------------------------------------------
# 육성도 찾기
# -------------------------------------------------
# 캐릭터의 링크 영역 = 캐릭터 이름(B열)이 있는 행부터
# 다음 캐릭터 이름이 나오기 전까지의 행들.
# 그 영역의 C열 중에서 링크가 있는 가장 위 행의 D열(육성도) 값을 쓴다.
# (링크가 하나도 없으면 이름이 있는 행의 D열 값을 쓴다)
# -------------------------------------------------

def find_growth(start, b_values, c_values, d_values):

    def cell(values, i):
        return values[i][0] if i < len(values) and values[i] else ""

    end = start + 1

    while end < len(b_values) and not str(cell(b_values, end)).strip():
        end += 1

    for i in range(start, end):

        if str(cell(c_values, i)).strip():
            return cell(d_values, i)

    return cell(d_values, start)


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


# -------------------------------------------------
# K3:T3 링크 읽기
# -------------------------------------------------

row3 = worksheet.row_values(3)

target_urls = []

# K열(11) ~ T열(20): col-1을 인덱스로 사용해 row3에서 값을 찾는다
for col in range(11, 21):

    index = col - 1

    if index >= len(row3):
        continue

    url = row3[index].strip()

    if not url:
        continue

    if SITE_URL_MARKER not in url:
        continue

    target_urls.append(url)

print("이미지 추출 대상 :", len(target_urls))

for url in target_urls:
    print(url)


# -------------------------------------------------
# 병렬 이미지 추출 + 실패한 URL만 재시도 (최대 3회)
# -------------------------------------------------
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

url_results = {}

pending_urls = target_urls[:]
current_try = 0

while pending_urls and current_try < MAX_RETRIES:

    print(f"\n===== 이미지 추출 {current_try + 1}차 시도 (대상 {len(pending_urls)}개) =====")

    next_pending = []

    with ThreadPoolExecutor(max_workers=4) as executor:
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
# 삭제되지 않았는데 이미지가 0개인 URL 검사
# -------------------------------------------------
# 크롤링 자체는 성공(예외 없음)했지만, 삭제된 글도 아닌데
# 정규식에 매칭되는 이미지가 하나도 없는 경우,
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
# 원래 순서(target_urls) 그대로 캐릭터 리스트 조립
# -------------------------------------------------
# character_list[n] = n번째 캐릭터의 폼 목록 (예: [1폼, 2폼, 3폼])
# -------------------------------------------------

character_list = []

for url in target_urls:
    result = url_results.get(url, {"characters": [], "deleted": False})

    if result.get("deleted"):
        print(f"[삭제됨] {url}", flush=True)
        continue  # 삭제된 페이지는 캐릭터 0명으로 확정, 리스트에 추가하지 않음

    character_list.extend(result.get("characters", []))

# 위에서 "삭제 안 됐는데 이미지 0개"인 경우는 이미 걸러졌으므로,
# 여기서 character_list가 비었다면 URL이 없었거나 전부 삭제된 페이지인 경우뿐이다
if len(character_list) == 0:
    character_list = [["본문 이미지 없음"]]


# -------------------------------------------------
# B/C/D/J/K 열 읽기
#  - D열 = 육성도, 어느 폼을 넣을지 정하는 데 쓴다
#  - C열 = 링크, 캐릭터의 링크 영역에서 맨 위 링크 행을 찾는 데 쓴다
# -------------------------------------------------

start_row = 5

COLUMNS = "BCDJK"

# 5개 열을 API 한 번(batch_get)으로 읽는다.
# "B5:B" 처럼 끝 행을 정하지 않으면 각 열의 마지막 값이 있는 행까지만 돌아온다.
raw_columns = worksheet.batch_get(
    [f"{col}{start_row}:{col}" for col in COLUMNS]
)

# 마지막 행 = B열(이름)의 마지막 값이 있는 행
last_row = max(start_row, start_row + len(raw_columns[0]) - 1)

num_rows = last_row - start_row + 1


def normalize(values):

    # B열 기준 num_rows까지만 사용한다 (다른 열이 더 길어도 무시)
    values = list(values)[:num_rows]

    # gspread가 뒷부분 빈 행은 아예 반환하지 않으므로 num_rows에 맞춰 채워준다
    values += [[""] for _ in range(num_rows - len(values))]

    # 중간의 빈 행은 [](빈 리스트)로 오므로 [""]로 맞춰준다
    return [list(row) if row else [""] for row in values]


b_values, c_values, d_values, j_values, k_values = (
    normalize(values) for values in raw_columns
)

# -------------------------------------------------
# B열 기준으로 유효 행을 세면서 이미지 매칭
# -------------------------------------------------

valid_b_count = 0

for i in range(num_rows):

    b = b_values[i][0] if b_values[i] else ""
    k = k_values[i][0] if k_values[i] else ""

    if b and str(b).strip():

        valid_b_count += 1

        if k and str(k).strip():

            if valid_b_count <= len(character_list):

                d = find_growth(i, b_values, c_values, d_values)

                j_values[i][0] = pick_form(
                    character_list[valid_b_count - 1],
                    d,
                    str(b).strip()
                )

            else:

                j_values[i][0] = ""

        else:

            j_values[i][0] = ""

    else:

        if k and str(k).strip():
            j_values[i][0] = ""


worksheet.update(
    range_name=f"J{start_row}:J{last_row}",
    values=j_values
)

print("완료")
